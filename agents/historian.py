# agents/historian.py
import statistics
from collections import Counter
from core.price_history import compute_historical_price_context, generate_product_id, record_price
from core.validation import validate_products

def compute_relative_price_score(product: dict, all_products: list[dict]) -> float:
    prices = [p["price"] for p in all_products if p.get("price", 0) > 0]
    if len(prices) < 3: return 0.5
    median_price = statistics.median(prices)
    current = product.get("price", median_price)
    if median_price <= 0: return 0.5
    score = (median_price - current) / median_price
    return round(max(0.0, min(1.0, 0.5 + score)), 3)

def compute_price_percentile(product: dict, all_products: list[dict]) -> str:
    prices = sorted([p["price"] for p in all_products if p.get("price", 0) > 0])
    if not prices: return "Unknown"
    current = product.get("price", 0)
    if current <= 0: return "Unknown"
    below_count = sum(1 for p in prices if p < current)
    percentile = (below_count / len(prices)) * 100
    if percentile <= 20: return "Budget-friendly (bottom 20%)"
    elif percentile <= 40: return "Below average price"
    elif percentile <= 60: return "Average price range"
    elif percentile <= 80: return "Above average price"
    else: return "Premium priced (top 20%)"

def run_historian(products: list[dict]) -> list[dict]:
    products = validate_products(products, "historian input")
    if not products: return products
    prices = [p["price"] for p in products if p.get("price", 0) > 0]
    if not prices: return products
    
    median_price = round(statistics.median(prices), 0)
    print(f"   Market Median : ₹{median_price:,}")
    
    enriched = []
    for product in products:
        historical = compute_historical_price_context(product)
        if historical:
            product["price_history_score"] = historical["score"]
            product["price_history"] = historical["history"]
            product["price_history"]["price_position"] = compute_price_percentile(product, products)
        else:
            product_id = generate_product_id(product.get("title", ""), product.get("platform", ""))
            product["price_history_score"] = compute_relative_price_score(product, products)
            product["price_history"] = {
                "method": "relative_market_comparison",
                "product_id": product_id,
                "median_market_price": median_price,
                "current_price": product.get("price", 0),
                "price_position": compute_price_percentile(product, products),
                "is_good_deal": product["price_history_score"] > 0.6,
            }
        record_price(product, product["price_history"].get("product_id"))
        enriched.append(product)
    
    # Summary of distribution
    dist = [p["price_history"]["price_position"] for p in enriched]
    counts = Counter(dist)
    short = {"Budget-friendly (bottom 20%)": "Budget", "Below average price": "Below Avg",
             "Average price range": "Average", "Above average price": "Above Avg",
             "Premium priced (top 20%)": "Premium", "Unknown": "Unknown"}
    parts = [f"{short.get(k, k)}({v})" for k, v in counts.items()]
    print(f"   Distribution  : {' | '.join(parts)}")
    
    historical_count = sum(1 for p in enriched if p.get("price_history", {}).get("method") == "historical_30day")
    if historical_count:
        print(f"   Historical    : {historical_count} products used SQLite 30-day history")
    
    return validate_products(enriched, "historian output")
