# scrapers/flipkart_scraper.py
import asyncio
import re
import os
import random
import time
from difflib import SequenceMatcher
from playwright.async_api import async_playwright

FLIPKART_SELECTORS = {
    "card": [
        "div.jIjQ8S",
        "div.tUxRFH",
        "div.TSD49J",
        "._1AtVbE",
        "._2kHMtA",
        ".cPHDOP",
        "[data-id]",
    ],
    "title": [
        "div.RG5Slk",
        "div.KzDlHZ",
        "div.U_GKRr",
        "._4rR01T",
        ".s1Q9rs",
        ".IRpwTa",
    ],
    "price": [
        "div.hZ3P6w",
        "div.Nx937j",
        "._30jeq3",
        "._1_WHN1",
    ],
    "rating": [
        "div.MKiFS6",
        "div.XQDdHH",
        "._3LWZlK",
    ],
    "reviews_count": [
        "span.PvbNMB",
        "span.W_MuHl",
        "._2_R_DZ span",
        ".Wphh3N span",
    ],
    "link": [
        "a.k7wcnx",
        "a.CGtC98",
        "a._1fQZEK",
        "a.s1Q9rs",
        "a._2rpwqI",
        "a",
    ],
    "image": [
        "img.UCc1lI",
        "img.DByoH4",
        "img._396cs4",
        "img._2r_T1I",
        "img",
    ],
    "login_popup_close": [
        "span._30XB9F",
        "button._2KpZ6l._2doB4z",
        "button[class*='close']",
    ],
}

FLIPKART_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

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
    text = str(text).replace('\u20b9', '').replace('₹', '')
    cleaned = re.sub(r'[^\d.]', '', text.replace(',', ''))
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
    # Flipkart format: "4.62,73,879 Ratings & 9,563 Reviews"
    match = re.search(r'([\d,]+)\s*[Rr]eviews?', str(text))
    if match:
        try: return int(match.group(1).replace(',', ''))
        except Exception: pass
    matches = re.findall(r'([\d,]+)', str(text))
    if len(matches) > 1:
        try: return int(matches[-1].replace(',', ''))
        except Exception: pass
    elif matches:
        try: return int(matches[0].replace(',', ''))
        except Exception: pass
    return 0

async def dismiss_login_popup(page):
    for selector in FLIPKART_SELECTORS.get("login_popup_close", []):
        try:
            close_btn = await page.query_selector(selector)
            if close_btn:
                await close_btn.click()
                await page.wait_for_timeout(500)
                return True
        except Exception: continue
    try: await page.keyboard.press("Escape")
    except Exception: pass
    return False

def _filter_and_dedup(title, price, reviews, budget, core_keywords, seen_titles):
    """Shared filtering logic for all strategies. Returns True if product should be kept."""
    if not title or price == 0:
        return False
    if reviews < 10:
        return False
    if budget and budget > 0:
        if price > budget * 3 or price < budget * 0.1:
            return False
    
    title_norm = title.lower().strip()[:50]
    is_dup = any(SequenceMatcher(None, title_norm, s).ratio() > 0.80 for s in seen_titles)
    if is_dup:
        return False
    seen_titles.append(title_norm)
    return True


def _parse_flipkart_items_bs4(soup, max_results, budget, product_type, seen_titles, core_keywords):
    """Shared BeautifulSoup parsing for ScraperAPI and direct HTTP responses."""
    products = []

    items = []
    for sel in FLIPKART_SELECTORS["card"]:
        items = soup.select(sel)
        if len(items) > 2:
            break

    for item in items:
        if len(products) >= max_results:
            break

        # Title
        title = ""
        for sel in FLIPKART_SELECTORS["title"]:
            el = item.select_one(sel)
            if el and el.get_text(strip=True):
                title = el.get_text(strip=True)
                break

        # Price
        price = 0.0
        for sel in FLIPKART_SELECTORS["price"]:
            el = item.select_one(sel)
            if el:
                price = parse_price(el.get_text())
                if price > 0: break

        # Rating
        rating = 0.0
        for sel in FLIPKART_SELECTORS["rating"]:
            el = item.select_one(sel)
            if el:
                rating = parse_rating(el.get_text())
                if rating > 0: break

        # Reviews
        reviews = 0
        for sel in FLIPKART_SELECTORS["reviews_count"]:
            el = item.select_one(sel)
            if el:
                reviews = parse_reviews(el.get_text())
                if reviews > 0: break

        # Link
        link_el = None
        for sel in FLIPKART_SELECTORS["link"]:
            link_el = item.select_one(sel)
            if link_el: break
        href = link_el.get("href", "") if link_el else ""

        # Image
        img_el = None
        for sel in FLIPKART_SELECTORS["image"]:
            img_el = item.select_one(sel)
            if img_el and img_el.get("src"): break
        img = img_el.get("src", "") if img_el else ""

        if not _filter_and_dedup(title, price, reviews, budget, core_keywords, seen_titles):
            continue

        full_url = f"https://www.flipkart.com{href}" if href.startswith("/") else href
        products.append({
            "title": title, "price": price, "rating": rating, "reviews_count": reviews,
            "seller": "Flipkart", "url": full_url, "thumbnail": img, "platform": "Flipkart"
        })

    return products


def _scrape_flipkart_scraperapi(query: str, max_results: int = 25, budget: int = 0, product_type: str = "") -> list[dict]:
    """Scrape Flipkart using ScraperAPI — fastest and most reliable."""
    import requests
    from bs4 import BeautifulSoup

    api_key = os.getenv("SCRAPER_API_KEY", "").strip()
    if not api_key:
        return []

    seen_titles = []
    core_keywords = [w.lower() for w in product_type.split() if len(w) > 2] if product_type else []

    target_url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
    try:
        resp = requests.get(
            "https://api.scraperapi.com/",
            params={"api_key": api_key, "url": target_url, "device_type": "desktop"},
            timeout=60
        )
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        return _parse_flipkart_items_bs4(soup, max_results, budget, product_type, seen_titles, core_keywords)

    except Exception as e:
        print(f"  [Flipkart/ScraperAPI] Error: {e}")
        return []


def _scrape_flipkart_http(query: str, max_results: int = 25, budget: int = 0, product_type: str = "") -> list[dict]:
    """Scrape Flipkart using plain HTTP — fast, no browser fingerprint."""
    import requests
    from bs4 import BeautifulSoup

    seen_titles = []
    core_keywords = [w.lower() for w in product_type.split() if len(w) > 2] if product_type else []

    headers = {
        "User-Agent": random.choice(FLIPKART_USER_AGENTS),
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        return _parse_flipkart_items_bs4(soup, max_results, budget, product_type, seen_titles, core_keywords)

    except Exception as e:
        print(f"  [Flipkart/HTTP] Error: {e}")
        return []


async def _scrape_flipkart_playwright(query: str, max_results: int = 25, budget: int = 0, product_type: str = "") -> list[dict]:
    """Playwright-based scraper — full browser rendering as fallback."""
    products = []
    seen_titles = []
    core_keywords = [w.lower() for w in product_type.split() if len(w) > 2] if product_type else []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        try:
            context = await browser.new_context(user_agent=random.choice(FLIPKART_USER_AGENTS), locale="en-IN", viewport={"width": 1920, "height": 1080})
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
            
            url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(random.randint(2000, 4000))
                await dismiss_login_popup(page)
            except Exception:
                return []

            for _ in range(3):
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await page.wait_for_timeout(800)

            items = await _try_selectors_all(page, FLIPKART_SELECTORS.get("card", []))
            if not items: items = await page.query_selector_all("div[data-id]")

            for item in items:
                if len(products) >= max_results:
                    break
                    
                try:
                    title_el = await _try_selectors(item, FLIPKART_SELECTORS.get("title", []))
                    price_el = await _try_selectors(item, FLIPKART_SELECTORS.get("price", []))
                    rating_el = await _try_selectors(item, FLIPKART_SELECTORS.get("rating", []))
                    reviews_el = await _try_selectors(item, FLIPKART_SELECTORS.get("reviews_count", []))
                    link_el = await _try_selectors(item, FLIPKART_SELECTORS.get("link", []))
                    img_el = await _try_selectors(item, FLIPKART_SELECTORS.get("image", []))

                    title = (await title_el.inner_text()).strip() if title_el else ""
                    price = parse_price(await price_el.inner_text() if price_el else "0")
                    rating = parse_rating(await rating_el.inner_text() if rating_el else "0")
                    reviews = parse_reviews(await reviews_el.inner_text() if reviews_el else "0")
                    href = await link_el.get_attribute("href") if link_el else ""
                    img = await img_el.get_attribute("src") if img_el else ""

                    if not _filter_and_dedup(title, price, reviews, budget, core_keywords, seen_titles):
                        continue

                    full_url = f"https://www.flipkart.com{href}" if href.startswith("/") else href
                    products.append({
                        "title": title, "price": price, "rating": rating, "reviews_count": reviews,
                        "seller": "Flipkart", "url": full_url, "thumbnail": img, "platform": "Flipkart"
                    })
                except Exception: continue
        finally:
            await browser.close()

    return products


def _build_query_variants(query: str, product_type: str) -> list[str]:
    """Generate multiple search query variants for better Flipkart coverage."""
    variants = [query]  # Original query first
    
    # Variant 2: Just the product type (e.g., "iphone 17" instead of "iphone 17 256 gb")
    if product_type and product_type.lower() != query.lower():
        variants.append(product_type)
    
    # Variant 3: Simplified (first 2-3 words only)
    words = query.split()
    if len(words) > 3:
        variants.append(" ".join(words[:3]))
    
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for v in variants:
        v_lower = v.lower().strip()
        if v_lower not in seen:
            seen.add(v_lower)
            unique.append(v)
    
    return unique


async def scrape_flipkart(query: str, max_results: int = 25, budget: int = 0, product_type: str = "") -> list[dict]:
    """
    Multi-strategy Flipkart scraper with automatic fallback + multi-query:
      1. Tries multiple query variations for better coverage
      2. For each query: ScraperAPI → HTTP → Playwright
      3. Merges and deduplicates all results
    """
    all_products = []
    seen_titles = []
    
    query_variants = _build_query_variants(query, product_type)
    
    for q_idx, q in enumerate(query_variants):
        if len(all_products) >= max_results:
            break
            
        remaining = max_results - len(all_products)
        products = []
        
        # Prefer ScraperAPI, then fall back to direct HTTP and finally Playwright.
        try:
            products = _scrape_flipkart_scraperapi(q, remaining, budget, product_type)
            if products and q_idx == 0:
                print(f"  [Flipkart] ScraperAPI returned {len(products)} products")
        except Exception:
            pass

        if len(products) < 3:
            try:
                http_products = _scrape_flipkart_http(q, remaining, budget, product_type)
                if len(http_products) > len(products):
                    products = http_products
            except Exception:
                pass

        if len(products) < 3:
            try:
                pw_products = await _scrape_flipkart_playwright(q, remaining, budget, product_type)
                if len(pw_products) > len(products):
                    products = pw_products
            except Exception:
                pass
        
        # Merge into all_products, dedup by title
        for p in products:
            title_norm = p.get("title", "").lower().strip()[:50]
            is_dup = any(SequenceMatcher(None, title_norm, s).ratio() > 0.80 for s in seen_titles)
            if not is_dup:
                seen_titles.append(title_norm)
                all_products.append(p)
    
    if not all_products:
        print(f"  [Flipkart] 0 products across {len(query_variants)} query variants")

    return all_products

