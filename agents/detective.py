# agents/detective.py
import os
import json
import time
from difflib import SequenceMatcher
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from core.validation import validate_products

load_dotenv()

# Metadata signals

def signal_rating_volume_trust(rating: float, review_count: int) -> tuple[float, str | None]:
    """
    Signal 1 (PRIMARY): High rating + low review count = suspicious.
    Real popular products always accumulate criticism over time.
    Weight: 35% of heuristic total.
    """
    if review_count == 0:
        return 0.50, "No reviews at all — cannot verify authenticity"

    suspicion = 0.0
    flag = None

    # Perfect rating with very few reviews — strongest signal
    if rating >= 4.9 and review_count < 50:
        suspicion = 0.45
        flag = f"Suspicious: {rating}⭐ from only {review_count} reviews — too perfect too soon"
    elif rating >= 4.8 and review_count < 100:
        suspicion = 0.35
        flag = f"Suspicious: {rating}⭐ from only {review_count} reviews — needs more validation"
    elif rating >= 4.7 and review_count < 150:
        suspicion = 0.25
        flag = f"Caution: {rating}⭐ with only {review_count} reviews — rating may change as more users review"
    elif rating >= 4.5 and review_count < 200:
        suspicion = 0.15
        flag = f"Low confidence: {review_count} reviews for a {rating}⭐ rating — still building credibility"

    return suspicion, flag

def signal_price_rating_anomaly(price: float, rating: float, review_count: int) -> tuple[float, str | None]:
    """
    Signal 2 (PRIMARY): Expensive products with perfect ratings are statistically
    improbable. Cheap products with suspiciously high engagement also raise flags.
    Weight: 30% of heuristic total.
    """
    if price <= 0 or rating == 0:
        return 0.0, None

    # Premium products (>₹50K) — laptops, phones, TVs
    if price > 50000:
        if rating >= 4.8 and review_count < 200:
            return 0.40, f"Premium product (₹{price:,.0f}) with {rating}⭐ from only {review_count} reviews — statistically very rare"
        elif rating == 5.0:
            return 0.35, f"Perfect 5.0⭐ on a ₹{price:,.0f} product — no real product at this price has zero complaints"
        elif rating >= 4.7 and review_count < 100:
            return 0.25, f"High rating {rating}⭐ with very few reviews ({review_count}) for a premium product"

    # Mid-range products (₹10K-₹50K)
    elif price > 10000:
        if rating == 5.0 and review_count < 100:
            return 0.30, f"Perfect 5.0⭐ with only {review_count} reviews on a mid-range product — highly unlikely"
        elif rating >= 4.9 and review_count < 150:
            return 0.20, f"Near-perfect {rating}⭐ with few reviews ({review_count}) for this price tier"

    # Budget products (<₹500) — watch for listing manipulation
    elif price < 500:
        if rating >= 4.8 and review_count < 200:
            return 0.15, f"Ultra-cheap product (₹{price:,.0f}) with suspiciously high rating and low review count"

    return 0.0, None

def signal_round_number_suspicion(review_count: int) -> tuple[float, str | None]:
    """
    Signal 3: Suspiciously round review counts suggest manual manipulation or resets.
    Weight: 15% of heuristic total.
    """
    round_numbers = [100, 200, 500, 1000, 2000, 5000, 10000]
    if review_count in round_numbers:
        return 0.12, f"Review count is exactly {review_count} — possibly reset or manipulated"

    if review_count > 1000 and str(review_count).endswith("000"):
        return 0.08, f"Suspiciously round review count: {review_count}"

    return 0.0, None

def signal_cross_platform_discrepancy(product: dict, all_products: list[dict]) -> tuple[float, str | None]:
    """
    Signal 4: Large rating gaps between Amazon and Flipkart suggest manipulation on one.
    Weight: 20% of heuristic total.
    """
    title = product.get("title", "").lower()
    platform = product.get("platform", "")
    rating = product.get("rating", 0)

    for other in all_products:
        if other.get("platform") == platform:
            continue  # only compare across platforms

        other_title = other.get("title", "").lower()
        similarity = SequenceMatcher(None, title[:60], other_title[:60]).ratio()

        if similarity > 0.75:  # likely same product
            other_rating = other.get("rating", 0)
            gap = abs(rating - other_rating)

            if gap > 1.0:
                return (
                    0.25,
                    f"Same product rated {rating}⭐ on {platform} but "
                    f"{other_rating}⭐ on {other.get('platform')} — "
                    f"major rating gap of {gap:.1f} stars"
                )
            elif gap > 0.8:
                return (
                    0.15,
                    f"Rating discrepancy: {rating}⭐ on {platform} vs "
                    f"{other_rating}⭐ on {other.get('platform')} — "
                    f"gap of {gap:.1f} stars"
                )
    return 0.0, None

# Review volume is handled as confidence, not as a manipulation signal.


# LLM metadata review

def run_llm_review_analysis(product: dict) -> tuple[float, list[str]]:
    """
    Sends product metadata to Groq LLM for a quick authenticity gut-check.
    The LLM reasons from numbers and price-context alone.
    """
    prompt = f"""
You are a fake review detection expert for Indian e-commerce.
Analyze this product's review metadata for signs of manipulation.

Product: {product.get('title', '')[:100]}
Platform: {product.get('platform', '')}
Price: ₹{product.get('price', 0):,.0f}
Star Rating: {product.get('rating', 0)} / 5.0
Total Reviews: {product.get('reviews_count', 0):,}

Based purely on these numbers and your knowledge of typical Indian e-commerce patterns:
1. Is this rating/volume combination statistically plausible?
2. Does the price-to-rating ratio seem natural?
3. Are there any red flags in these numbers alone?

Return ONLY valid JSON:
{{
  "llm_fake_score": <float 0.0 to 1.0>,
  "flags": ["list of specific concerns, or empty list if none"],
  "reasoning": "<one sentence>"
}}
"""
    try:
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0, api_key=os.getenv("GROQ_API_KEY"))
        response = llm.invoke(prompt)
        raw = response.content.strip()
        
        # Strip potential markdown
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        
        result = json.loads(raw.strip())
        return result.get("llm_fake_score", 0.0), result.get("flags", [])
    except Exception as e:
        print(f"[Detective LLM] Failed: {e}")
        return 0.0, []

def run_llm_review_analysis_batch(products: list[dict]) -> list[tuple[float, list[str]]]:
    """
    Analyze up to 5 suspicious products in one Groq call.
    Returns one (fake_score, flags) tuple per input product.
    """
    if not products:
        return []

    lines = []
    for idx, product in enumerate(products, start=1):
        lines.append(
            f"Product {idx}: {product.get('title', '')[:120]} | "
            f"Platform: {product.get('platform', '')} | "
            f"Price: Rs {product.get('price', 0):,.0f} | "
            f"Rating: {product.get('rating', 0)} / 5.0 | "
            f"Reviews: {product.get('reviews_count', 0):,}"
        )

    prompt = f"""
You are a fake review detection expert for Indian e-commerce.
Analyze these products for review manipulation signs using metadata only.

{chr(10).join(lines)}

For each product, decide if the rating, review count, price tier, and platform context look statistically plausible.

Return ONLY valid JSON array, one object per product:
[
  {{"product_index": 1, "llm_fake_score": 0.0, "flags": []}},
  {{"product_index": 2, "llm_fake_score": 0.3, "flags": ["specific concern"]}}
]

Score scale: 0.0 = no concern, 1.0 = extremely likely manipulated.
"""
    fallback = [(0.0, []) for _ in products]
    try:
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0, api_key=os.getenv("GROQ_API_KEY"))
        response = llm.invoke(prompt)
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON array found in LLM response")

        parsed = json.loads(raw[start:end + 1])
        by_index = {
            int(item.get("product_index", 0)): (
                max(0.0, min(1.0, float(item.get("llm_fake_score", 0.0)))),
                list(item.get("flags", []))[:3],
            )
            for item in parsed
            if isinstance(item, dict)
        }
        return [by_index.get(idx, (0.0, [])) for idx in range(1, len(products) + 1)]
    except Exception as e:
        print(f"[Detective LLM Batch] Failed: {e}")
        try:
            return [run_llm_review_analysis(product) for product in products]
        except Exception:
            return fallback


# Public agent entry points

def run_detective_on_product(
    product: dict,
    all_products: list[dict],
    llm_score: float | None = None,
    llm_flags: list[str] | None = None,
) -> dict:
    rating       = product.get("rating", 0)
    review_count = product.get("reviews_count", 0)
    price        = product.get("price", 0)
    
    red_flags     = []
    total_suspicion = 0.0

    # 1. Run Metadata Heuristics (weighted by importance)
    signal_weights = {
        "rating_volume": 0.35,     # Primary signal — most reliable
        "price_anomaly": 0.30,     # Primary signal — strong indicator
        "round_number": 0.15,      # Supporting signal
        "cross_platform": 0.20,    # Supporting signal — valuable when available
    }

    signals = [
        ("rating_volume",   signal_rating_volume_trust(rating, review_count)),
        ("price_anomaly",   signal_price_rating_anomaly(price, rating, review_count)),
        ("round_number",    signal_round_number_suspicion(review_count)),
        ("cross_platform",  signal_cross_platform_discrepancy(product, all_products)),
    ]

    for name, (score, flag) in signals:
        weighted_score = score * signal_weights[name]
        total_suspicion += weighted_score
        if flag:
            red_flags.append(flag)

    total_suspicion = min(total_suspicion, 1.0)

    # 2. Optional Metadata LLM Analysis (batched by run_detective).
    if llm_score is None:
        llm_score = 0.0
        llm_flags = []
        combined_susp = min(total_suspicion, 1.0)
        llm_weight_used = 0.0
    else:
        llm_flags = llm_flags or []
        combined_susp = min((0.70 * total_suspicion) + (0.30 * llm_score), 1.0)
        llm_weight_used = 0.30

    red_flags.extend(llm_flags)

    # 3. Final calculations
    trust_score     = round(1.0 - combined_susp, 2)
    fake_percentage = round(combined_susp, 2)
    
    # Deduplicate flags
    red_flags = list(dict.fromkeys(red_flags))

    # Rating penalty: max 35% reduction if completely untrustworthy
    adjusted_rating = round(rating * (1 - fake_percentage * 0.35), 2)

    verdict = (
        "Highly Suspicious" if fake_percentage > 0.6 else
        "Suspicious"        if fake_percentage > 0.35 else
        "Mostly Authentic"  if fake_percentage > 0.15 else
        "Authentic"
    )

    product.update({
        "trust_score":      trust_score,
        "fake_percentage":  fake_percentage,
        "adjusted_rating":  adjusted_rating,
        "review_red_flags": red_flags,
        "review_verdict":   verdict,
        "heuristic_suspicion": total_suspicion,
        "llm_score": llm_score,
        "llm_weight_used": llm_weight_used,
    })
    return product

def run_detective(products: list[dict]) -> list[dict]:
    """Entry point for the LangGraph pipeline."""
    products = validate_products(products, "detective input")
    enriched = []
    total = len(products)
    
    print(f"   Scanning {total} products for review manipulation...")
    
    for idx, product in enumerate(products):
        print(f"   Checking {idx+1}/{total}...", end="\r")
        enriched_product = run_detective_on_product(product, products)
        enriched.append(enriched_product)

    print(f"   Checked  {total}/{total} products       ")

    suspicious = sorted(
        [p for p in enriched if p.get("heuristic_suspicion", 0) > 0.10],
        key=lambda p: p.get("heuristic_suspicion", 0),
        reverse=True,
    )[:15]

    if suspicious:
        print(f"   LLM Review : analyzing {len(suspicious)} suspicious products in batches")
        llm_by_identity = {}
        for start in range(0, len(suspicious), 5):
            batch = suspicious[start:start + 5]
            if start > 0:
                time.sleep(0.4)
            results = run_llm_review_analysis_batch(batch)
            for product, (score, flags) in zip(batch, results):
                key = (product.get("platform", ""), product.get("title", ""))
                llm_by_identity[key] = (score, flags)

        for idx, product in enumerate(enriched):
            key = (product.get("platform", ""), product.get("title", ""))
            if key in llm_by_identity:
                score, flags = llm_by_identity[key]
                enriched[idx] = run_detective_on_product(product, enriched, score, flags)
    else:
        print("   LLM Review : skipped (no products crossed suspicion threshold)")
    
    # Print verdict summary
    verdicts = {}
    for p in enriched:
        v = p.get("review_verdict", "Unknown")
        verdicts[v] = verdicts.get(v, 0) + 1
    parts = []
    for label in ["Authentic", "Mostly Authentic", "Suspicious", "Highly Suspicious"]:
        if label in verdicts:
            parts.append(f"{label}: {verdicts[label]}")
    print(f"   Results   : {' | '.join(parts)}")
            
    return validate_products(enriched, "detective output")
