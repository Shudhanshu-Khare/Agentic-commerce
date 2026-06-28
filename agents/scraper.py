# agents/scraper.py
import sys
import os
import json
import asyncio
import nest_asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from difflib import SequenceMatcher
from core.validation import validate_products

# Must be set BEFORE any asyncio usage — required for Playwright on Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def build_search_query(profile: dict) -> str:
    parts = [profile.get("product_type", "")]
    
    # 1. Use AI-optimized search keywords if the Profiler generated them
    if profile.get("search_keywords"):
        parts.append(profile["search_keywords"])
    # 2. Fallback to raw inputs
    elif profile.get("raw_specs"):
        parts.append(profile["raw_specs"])
    # 3. Fallback to dictionary values
    else:
        for val in profile.get("mandatory_specs", {}).values():
            parts.append(str(val))
    raw = " ".join(filter(None, parts))
    
    # Deduplicate words while preserving order
    # e.g. "bluetooth speaker portable 30 watt bluetooth speaker under 5000"
    #    → "bluetooth speaker portable 30 watt under 5000"
    seen = set()
    deduped = []
    for word in raw.split():
        word_lower = word.lower()
        if word_lower not in seen:
            seen.add(word_lower)
            deduped.append(word)
    return " ".join(deduped)

BACKUP_DIR = "data"

def deduplicate_products(products: list[dict]) -> list[dict]:
    """
    Groups near-duplicate products across platforms using fuzzy title matching.
    Instead of blindly tossing the second one, it keeps the 'best' variant
    based on a combination of lower price and higher rating/reviews.
    """
    import math
    SIMILARITY_THRESHOLD = 0.82
    TITLE_COMPARE_LENGTH = 80

    clusters = []

    for product in products:
        title = product.get("title", "").lower().strip()[:TITLE_COMPARE_LENGTH]
        if not title:
            clusters.append([product])
            continue

        found_cluster = False
        for cluster in clusters:
            base_title = cluster[0].get("title", "").lower().strip()[:TITLE_COMPARE_LENGTH]
            similarity = SequenceMatcher(None, title, base_title).ratio()
            if similarity >= SIMILARITY_THRESHOLD:
                cluster.append(product)
                found_cluster = True
                break
        
        if not found_cluster:
            clusters.append([product])

    unique = []
    removed = 0

    for cluster in clusters:
        if len(cluster) == 1:
            unique.append(cluster[0])
        else:
            # We have duplicates! Pick the best one.
            # Formula balances a low price against high reviews and rating.
            def get_value_score(p):
                price = max(p.get("price", 1), 1)
                revs = max(p.get("reviews_count", 0), 1)
                rating = max(p.get("rating", 0), 0.1)
                # High rating and high reviews are rewarded. High price is penalized heavily.
                return (rating * math.log10(revs * 10)) / price

            cluster.sort(key=get_value_score, reverse=True)
            
            best_product = cluster[0]
            unique.append(best_product)
            removed += (len(cluster) - 1)
            
    if removed > 0:
        print(f"   Collected  : {len(products)} products")
        print(f"   Duplicates : -{removed} removed")
        print(f"   Unique     : {len(unique)} products")
    return unique

def save_backup(products: list[dict], query: str) -> None:
    """Save scraped products so a later partial scrape can be repaired."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    safe_query = query.replace(" ", "_").replace("/", "-")[:40]
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M")
    filename   = f"{BACKUP_DIR}/{safe_query}_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"   💾 Backup saved ({len(products)} products)")

def load_backup(query: str) -> list[dict] | None:
    """Loads the most recent backup JSON for a given query."""
    if not os.path.exists(BACKUP_DIR): return None
    safe_query = query.replace(" ", "_").replace("/", "-")[:40]
    all_files  = [f for f in os.listdir(BACKUP_DIR) if f.startswith(safe_query) and f.endswith(".json")]

    if not all_files: return None
    all_files.sort(reverse=True)
    latest = os.path.join(BACKUP_DIR, all_files[0])

    with open(latest, "r", encoding="utf-8") as f:
        products = json.load(f)
    print(f"   📦 Backup loaded ({len(products)} products)")
    return products

async def _run_all_scrapers(query: str, budget: int = 0, product_type: str = ""):
    """Run Amazon and Flipkart scrapers concurrently."""
    from scrapers.amazon_scraper import scrape_amazon
    from scrapers.flipkart_scraper import scrape_flipkart
    
    results = await asyncio.gather(
        scrape_amazon(query, max_results=30, budget=budget, product_type=product_type),
        scrape_flipkart(query, max_results=30, budget=budget, product_type=product_type),
        return_exceptions=True
    )
    
    all_res = []
    platform_names = ["Amazon.in", "Flipkart"]

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"   {platform_names[i]:12s} ❌ Failed: {result}")
        elif isinstance(result, list):
            print(f"   {platform_names[i]:12s} ✅ {len(result)} products")
            all_res.extend(result)
            
    return all_res


def run_scraper(profile: dict) -> list[dict]:
    query = build_search_query(profile)
    budget = profile.get("budget_inr", 0) or 0
    product_type = profile.get("product_type", "")
    all_products = []
    
    print(f"   Search : \"{query}\"")
    
    try:
        # Streamlit may already own an event loop; nest_asyncio keeps this call reusable.
        nest_asyncio.apply()
        all_products = asyncio.run(_run_all_scrapers(query, budget, product_type))
    except Exception as e:
        print(f"   ❌ Fatal error: {e}")
        all_products = []

    # Patch missing platform data from the latest compatible backup when possible.
    amazon_count = len([p for p in all_products if p.get("platform") == "Amazon.in"])
    flipkart_count = len([p for p in all_products if p.get("platform", "").lower() == "flipkart"])

    if amazon_count < 5 or flipkart_count < 5:
        print(f"   ⚠️ Live data incomplete — attempting backup fallback...")
        backup = load_backup(query)
        
        if backup:
            if amazon_count < 5:
                amazon_backup = [p for p in backup if p.get("platform") == "Amazon.in"]
                all_products = [p for p in all_products if p.get("platform") != "Amazon.in"] + amazon_backup
                print(f"   ✅ Injected {len(amazon_backup)} Amazon products from backup")
                
            if flipkart_count < 5:
                flipkart_backup = [p for p in backup if p.get("platform", "").lower() == "flipkart"]
                all_products = [p for p in all_products if p.get("platform", "").lower() != "flipkart"] + flipkart_backup
                print(f"   ✅ Injected {len(flipkart_backup)} Flipkart products from backup")
        else:
            print(f"   ⚠️ No backup found — using live data only")

    if len(all_products) < 15:
        print(f"   ⚠️ Low product count: {len(all_products)} products")

    # Only replace a backup when both live sources returned enough data.
    if amazon_count >= 10 and flipkart_count >= 10:
        save_backup(all_products, query)

    if not all_products:
        print("   ⚠️ No products found from any platform")

    budget = profile.get("budget_inr")
    if budget:
        flexibility = profile.get("budget_flexibility", 0.25)
        max_price = budget * (1 + flexibility)
        budget_filtered = [p for p in all_products if p.get("price", 0) <= max_price]
        if len(budget_filtered) >= 5: all_products = budget_filtered
        else: all_products = sorted(all_products, key=lambda x: abs(x.get("price", 0) - budget))

    return validate_products(all_products, "scraper products")
