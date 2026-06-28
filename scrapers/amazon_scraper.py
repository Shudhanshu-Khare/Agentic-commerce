# scrapers/amazon_scraper.py
import asyncio
import re
import os
import json
import random
import time
from difflib import SequenceMatcher
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

AMAZON_SELECTORS = {
    "search_result": [
        "div.s-result-item.s-asin",
        '[data-component-type="s-search-result"]',
        '.s-result-item[data-asin]',
        '.sg-col-inner .s-result-item',
    ],
    "title": [
        "h2 a span",
        "h2 span.a-text-normal",
        "h2 span",
        ".a-size-medium.a-text-normal",
        ".a-size-base-plus.a-color-base.a-text-normal",
    ],
    "price": [
        "span.a-price-whole",
        ".a-price-whole",
        ".a-price .a-offscreen",
    ],
    "rating": [
        "span.a-icon-alt",
        ".a-icon-alt",
        '[data-cy="reviews-ratings-slot"] .a-icon-alt',
    ],
    "reviews_count": [
        "span.a-size-base.s-underline-text",
        "span.a-size-mini.s-underline-text",
        "a.a-link-normal span.a-size-base",
        "a.a-link-normal span.a-size-mini",
        '[data-cy="reviews-ratings-slot"] .a-size-base',
        '[data-cy="reviews-ratings-slot"] .a-size-mini',
    ],
    "link": [
        "h2 a.a-link-normal",
        "h2 a",
        "a.a-link-normal.s-underline-text",
    ],
    "image": [
        "img.s-image",
        ".s-image",
        "img[data-image-latency]",
    ],
}

# A small rotation of current desktop browser user agents.
AMAZON_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
]

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', description: 'PDF', length: 1 },
        { name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer', description: '', length: 1 },
        { name: 'PDF Viewer', filename: 'internal-pdf-viewer', description: '', length: 1 },
    ]
});
Object.defineProperty(navigator, 'languages', { get: () => ['en-IN', 'en-US', 'en'] });
Object.defineProperty(navigator, 'language', { get: () => 'en-IN' });
if (!window.chrome) { window.chrome = { runtime: {}, loadTimes: () => ({}), csi: () => ({}) }; }
Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
"""


# Parser helpers

async def _try_selectors(parent, selectors: list[str]):
    for selector in selectors:
        try:
            el = await parent.query_selector(selector)
            if el: return el
        except Exception: continue
    return None

async def _try_selectors_all(page, selectors: list[str]):
    for selector in selectors:
        try:
            items = await page.query_selector_all(selector)
            if items and len(items) > 2: return items
        except Exception: continue
    return []

def parse_price(text: str) -> float:
    if not text: return 0.0
    cleaned = re.sub(r'[^\d.]', '', str(text).replace(',', ''))
    try: return float(cleaned)
    except (ValueError, TypeError): return 0.0

def parse_rating(text: str) -> float:
    if not text: return 0.0
    match = re.search(r'[\d.]+', str(text))
    try:
        val = float(match.group()) if match else 0.0
        return val if val <= 5.0 else 0.0
    except (ValueError, TypeError): return 0.0

def parse_reviews(text: str) -> int:
    if not text: return 0
    
    # Flipkart often bundles text: "4.62,73,879 Ratings&9,563 Reviews128 GB ROM"
    # We want the number before "Review" or the last large number available.
    import re
    text_lower = str(text).lower()
    
    match = re.search(r'([\d,kKmM.]+)\s*review', text_lower)
    if match:
        text = match.group(1)
    elif "rating" in text_lower and "&" in text_lower:
        # If it says "Ratings & 9,563"
        parts = text_lower.split("&")
        if len(parts) > 1: text = parts[1]
    
    text = str(text).upper().replace(',', '').strip()
    multiplier = 1
    if 'K' in text: multiplier = 1000
    elif 'M' in text: multiplier = 1000000
    
    cleaned = re.sub(r'[^\d.]', '', text)
    if not cleaned: return 0
    try: 
        return int(float(cleaned) * multiplier)
    except (ValueError, TypeError): return 0

def build_amazon_url(asin: str, href: str = "") -> str:
    """Build a clean Amazon product URL from ASIN (most reliable) or href fallback."""
    if asin:
        return f"https://www.amazon.in/dp/{asin}"
    if href:
        return f"https://www.amazon.in{href}" if href.startswith("/") else href
    return ""

def _filter_and_dedup(title, price, reviews, budget, seen_titles):
    """Shared filtering logic for all strategies. Returns True if product should be kept."""
    if not title or price == 0:
        return False
        
    if reviews < 10:
        return False
        
    if budget and budget > 0:
        if price > budget * 3 or price < budget * 0.1:
            return False

    # The evaluator handles semantic title/spec matching later in the pipeline.
    
    title_norm = title.lower().strip()[:50]
    is_dup = any(SequenceMatcher(None, title_norm, s).ratio() > 0.80 for s in seen_titles)
    if is_dup:
        return False
        
    seen_titles.append(title_norm)
    return True


def _scrape_amazon_scraperapi(query: str, max_results: int = 25, budget: int = 0, product_type: str = "") -> list[dict]:
    """
    Scrape Amazon.in using ScraperAPI's proxy network.
    Handles IP rotation, CAPTCHA solving, and browser headers automatically.
    Free tier: 1000 requests/month (no credit card needed).
    """
    import requests
    from bs4 import BeautifulSoup

    api_key = os.getenv("SCRAPER_API_KEY", "").strip()
    if not api_key:
        return []  # No key configured — skip to next strategy

    products = []
    seen_titles = []
    core_keywords = [w.lower() for w in product_type.split() if len(w) > 2] if product_type else []

    # Scrape up to 2 pages via ScraperAPI (each page = 1 API credit)
    for page_num in range(1, 3):
        target_url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}&page={page_num}&ref=sr_pg_{page_num}"

        try:
            if page_num > 1:
                time.sleep(random.uniform(1.0, 2.0))

            resp = requests.get(
                "https://api.scraperapi.com/",
                params={
                    "api_key": api_key,
                    "url": target_url,
                    "country_code": "in",
                    "device_type": "desktop",
                },
                timeout=60  # ScraperAPI can take time — give it room
            )

            if resp.status_code == 401:
                print(f"  [ScraperAPI] Invalid API key")
                return []
            elif resp.status_code == 429:
                print(f"  [ScraperAPI] Monthly limit reached — falling back")
                return []
            elif resp.status_code != 200:
                print(f"  [ScraperAPI] Page {page_num}: HTTP {resp.status_code}")
                continue

            html = resp.text

            if "captcha" in html.lower():
                print(f"  [ScraperAPI] Page {page_num}: CAPTCHA (rare) — skipping")
                continue

            soup = BeautifulSoup(html, "html.parser")

            items = soup.select('div.s-result-item[data-asin]')
            if not items:
                items = soup.select('[data-component-type="s-search-result"]')

            for item in items:
                if len(products) >= max_results:
                    break

                asin = item.get("data-asin", "")
                if not asin:
                    continue

                title = ""
                for sel in AMAZON_SELECTORS["title"]:
                    el = item.select_one(sel)
                    if el and el.get_text(strip=True):
                        # Filter out badges like "Apple" or "Sponsored"
                        text = el.get_text(strip=True)
                        if len(text) > 10: 
                            title = text
                            break
                        if not title:
                            title = text
                price_el = item.select_one("span.a-price-whole")
                price = parse_price(price_el.get_text() if price_el else "0")
                rating_el = item.select_one("span.a-icon-alt") or item.select_one(".a-icon-alt")
                rating = parse_rating(rating_el.get_text() if rating_el else "0")
                reviews_el = (
                    item.select_one("span.a-size-base.s-underline-text") or
                    item.select_one("span.a-size-mini.s-underline-text") or
                    item.select_one("a.a-link-normal span.a-size-base") or
                    item.select_one("a.a-link-normal span.a-size-mini")
                )
                reviews = parse_reviews(reviews_el.get_text() if reviews_el else "0")
                img_el = item.select_one("img.s-image")
                img = img_el.get("src", "") if img_el else ""

                if not _filter_and_dedup(title, price, reviews, budget, seen_titles):
                    continue

                products.append({
                    "title": title, "price": price, "rating": rating, "reviews_count": reviews,
                    "seller": "Amazon.in", "url": build_amazon_url(asin), "thumbnail": img, "platform": "Amazon.in"
                })

            if len(products) >= max_results:
                break

        except Exception as e:
            print(f"  [ScraperAPI] Page {page_num} error: {e}")
            continue

    return products


def _scrape_amazon_requests(query: str, max_results: int = 25, budget: int = 0, product_type: str = "") -> list[dict]:
    """
    Scrape Amazon.in using plain HTTP requests + BeautifulSoup.
    This avoids all browser fingerprinting — Amazon only sees a normal HTTP request.
    """
    import requests
    from bs4 import BeautifulSoup

    products = []
    seen_titles = []  # For scrape-time dedup
    core_keywords = [w.lower() for w in product_type.split() if len(w) > 2] if product_type else []
    ua = random.choice(AMAZON_USER_AGENTS)
    headers = {
        "User-Agent": ua,
        "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Ch-Ua": '"Chromium";v="132", "Google Chrome";v="132", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    }

    # Try up to 3 pages for more candidates
    for page_num in range(1, 4):
        url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}&page={page_num}&ref=sr_pg_{page_num}"
        
        try:
            # Small delay between pages
            if page_num > 1:
                time.sleep(random.uniform(1.5, 3.0))

            session = requests.Session()
            # First hit homepage to get cookies
            if page_num == 1:
                try:
                    session.get("https://www.amazon.in", headers=headers, timeout=15)
                    time.sleep(random.uniform(0.5, 1.5))
                except Exception:
                    pass

            resp = session.get(url, headers=headers, timeout=20)

            if resp.status_code != 200:
                print(f"  [Amazon/HTTP] Page {page_num}: HTTP {resp.status_code}")
                continue

            html = resp.text
            
            # Check for CAPTCHA
            if "captcha" in html.lower() or "enter the characters" in html.lower():
                print(f"  [Amazon/HTTP] Page {page_num}: CAPTCHA detected")
                break

            soup = BeautifulSoup(html, "html.parser")

            # Find search result items
            items = soup.select('div.s-result-item[data-asin]')
            if not items:
                items = soup.select('[data-component-type="s-search-result"]')

            for item in items:
                if len(products) >= max_results:
                    break

                asin = item.get("data-asin", "")
                if not asin:
                    continue

                # Title
                title = ""
                for sel in AMAZON_SELECTORS["title"]:
                    el = item.select_one(sel)
                    if el and el.get_text(strip=True):
                        text = el.get_text(strip=True)
                        if len(text) > 10:
                            title = text
                            break
                        if not title:
                            title = text

                # Price
                price_el = item.select_one("span.a-price-whole")
                price = parse_price(price_el.get_text() if price_el else "0")

                # Rating
                rating_el = item.select_one("span.a-icon-alt") or item.select_one(".a-icon-alt")
                rating = parse_rating(rating_el.get_text() if rating_el else "0")

                # Reviews count
                reviews_el = (
                    item.select_one("span.a-size-base.s-underline-text") or
                    item.select_one("span.a-size-mini.s-underline-text") or
                    item.select_one("a.a-link-normal span.a-size-base") or
                    item.select_one("a.a-link-normal span.a-size-mini")
                )
                reviews = parse_reviews(reviews_el.get_text() if reviews_el else "0")

                # Image
                img_el = item.select_one("img.s-image")
                img = img_el.get("src", "") if img_el else ""
                # Filter 
                if not _filter_and_dedup(title, price, reviews, budget, seen_titles):
                    continue

                products.append({
                    "title": title, "price": price, "rating": rating, "reviews_count": reviews,
                    "seller": "Amazon.in", "url": build_amazon_url(asin), "thumbnail": img, "platform": "Amazon.in"
                })

            if len(products) >= max_results:
                break

        except Exception as e:
            print(f"  [Amazon/HTTP] Page {page_num} error: {e}")
            continue

    return products


async def _scrape_amazon_playwright(query: str, max_results: int = 25, budget: int = 0, product_type: str = "") -> list[dict]:
    """Playwright-based scraper with stealth — used as fallback."""
    products = []
    seen_titles = []  # For scrape-time dedup
    core_keywords = [w.lower() for w in product_type.split() if len(w) > 2] if product_type else []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--disable-gpu",
                "--window-size=1920,1080",
            ]
        )
        context = await browser.new_context(
            user_agent=random.choice(AMAZON_USER_AGENTS),
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            viewport={"width": 1920, "height": 1080},
            extra_http_headers={
                "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            },
        )
        try:
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)
            
            # Visit homepage first
            try:
                await page.goto("https://www.amazon.in", wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(random.randint(1500, 3000))
            except Exception:
                pass

            url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}&ref=nb_sb_noss"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(random.randint(2000, 4000))
            except Exception:
                return []

            # Check CAPTCHA
            captcha_check = await page.content()
            if "captcha" in captcha_check.lower():
                return []

            # Scroll to load lazy content
            for _ in range(4):
                await page.evaluate("window.scrollBy(0, window.innerHeight * 0.7)")
                await page.wait_for_timeout(random.randint(400, 900))
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)

            items = await _try_selectors_all(page, AMAZON_SELECTORS["search_result"])
            if not items:
                items = await page.query_selector_all('[data-asin]:not([data-asin=""])')
                items = [i for i in items if await i.get_attribute("data-asin")]

            for item in items:
                if len(products) >= max_results:
                    break
                try:
                    title_el = await _try_selectors(item, AMAZON_SELECTORS["title"])
                    price_el = await _try_selectors(item, AMAZON_SELECTORS["price"])
                    rating_el = await _try_selectors(item, AMAZON_SELECTORS["rating"])
                    reviews_el = await _try_selectors(item, AMAZON_SELECTORS["reviews_count"])
                    img_el = await _try_selectors(item, AMAZON_SELECTORS["image"])

                    title = (await title_el.inner_text()).strip() if title_el else ""
                    price = parse_price(await price_el.inner_text() if price_el else "0")
                    rating = parse_rating(await rating_el.inner_text() if rating_el else "0")
                    reviews = parse_reviews(await reviews_el.inner_text() if reviews_el else "0")
                    asin = await item.get_attribute("data-asin") or ""
                    img = await img_el.get_attribute("src") if img_el else ""

                    if not _filter_and_dedup(title, price, reviews, budget, seen_titles):
                        continue

                    products.append({
                        "title": title, "price": price, "rating": rating, "reviews_count": reviews,
                        "seller": "Amazon.in", "url": build_amazon_url(asin), "thumbnail": img, "platform": "Amazon.in"
                    })

                except Exception: continue
        finally:
            await browser.close()
    return products


async def scrape_amazon(query: str, max_results: int = 25, budget: int = 0, product_type: str = "") -> list[dict]:
    """
    Multi-strategy Amazon scraper with automatic fallback:
      - ScraperAPI for proxy-backed requests.
      - Plain HTTP for a lightweight direct scrape.
      - Playwright as the browser-rendered fallback.
    """
    products = []

    # Prefer ScraperAPI, then fall back to direct HTTP and finally Playwright.
    try:
        products = _scrape_amazon_scraperapi(query, max_results, budget, product_type)
        if products:
            print(f"  [Amazon] ScraperAPI returned {len(products)} products")
    except Exception as e:
        print(f"  [Amazon] ScraperAPI error: {e}")

    if len(products) < 5:
        try:
            http_products = _scrape_amazon_requests(query, max_results, budget, product_type)
            if len(http_products) > len(products):
                products = http_products
        except Exception as e:
            print(f"  [Amazon] HTTP fallback error: {e}")

    if len(products) < 5:
        await asyncio.sleep(random.uniform(1, 2))
        try:
            pw_products = await _scrape_amazon_playwright(query, max_results, budget, product_type)
            if len(pw_products) > len(products):
                products = pw_products
        except Exception as e:
            print(f"  [Amazon] Playwright error: {e}")

    return products
