# scrapers/review_summary_scraper.py
"""
Deep Review Text Scraper (Extended Analysis Module)

This module scrapes individual product pages on Amazon and Flipkart to extract
human-written review summaries and key customer sentiment snippets.

It is designed to complement the Detective agent's metadata-based analysis
by providing actual review text for NLP-level fake review detection.

Usage:
    from scrapers.review_summary_scraper import get_review_summary
    summary = await get_review_summary(product_url, platform="Amazon.in")

Currently not called in the main pipeline to keep response times under 60s.
Can be enabled for deeper analysis when speed is not a constraint.
"""
import asyncio
import random
from playwright.async_api import async_playwright

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

async def get_amazon_review_summary(product_url: str) -> str:
    if not product_url or not product_url.startswith("http"): return "Not available"
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
            context = await browser.new_context(user_agent=random.choice(USER_AGENTS), locale="en-IN", viewport={"width": 1920, "height": 1080})
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
            try:
                await page.goto(product_url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(random.randint(1500, 3000))
            except Exception:
                await browser.close()
                return "Not available"
            selectors = ["[data-hook='cr-lighthouse-summary']", ".cr-lighthouse-summary", "#cr-summarization-attributes-list", "[data-hook='cr-summarization-attribute']", ".a-section.cr-lighthouse-section", "#customerReviews .a-section p", "[data-hook='review-collapsed'] span"]
            for selector in selectors:
                try:
                    el = await page.query_selector(selector)
                    if el:
                        text = (await el.inner_text()).strip()
                        if len(text) > 20:
                            await browser.close()
                            return text
                except Exception: continue
            await browser.close()
            return "Not available"
    except Exception: return "Not available"

async def get_flipkart_review_summary(product_url: str) -> str:
    if not product_url or not product_url.startswith("http"): return "Not available"
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
            context = await browser.new_context(user_agent=random.choice(USER_AGENTS), locale="en-IN", viewport={"width": 1920, "height": 1080})
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
            try:
                await page.goto(product_url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(random.randint(1500, 3000))
            except Exception:
                await browser.close()
                return "Not available"
            try:
                for sel in ["button._2KpZ6l._2doB4z", "button[class*='close']"]:
                    close_btn = await page.query_selector(sel)
                    if close_btn:
                        await close_btn.click()
                        await page.wait_for_timeout(300)
                        break
            except Exception: pass
            selectors = ["._3OrRlq", "._2-N8zT", "[class*='review-summary']", "._2nV8kG", ".RcXBOT", "._1YokD2._3Mn1Gg"]
            for selector in selectors:
                try:
                    el = await page.query_selector(selector)
                    if el:
                        text = (await el.inner_text()).strip()
                        if len(text) > 20:
                            await browser.close()
                            return text
                except Exception: continue
            await browser.close()
            return "Not available"
    except Exception: return "Not available"

async def get_review_summary(product_url: str, platform: str) -> str:
    if "amazon" in platform.lower(): return await get_amazon_review_summary(product_url)
    elif "flipkart" in platform.lower(): return await get_flipkart_review_summary(product_url)
    return "Not available"
