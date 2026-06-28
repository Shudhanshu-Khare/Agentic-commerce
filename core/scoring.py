# core/scoring.py
import re
import os
import json
import math
import statistics
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

# Fast keyword pre-filter

def fast_spec_prefilter(product: dict, profile: dict) -> tuple[bool, float, list[str]]:
    """
    Stage 1: Keyword-based spec check. Zero LLM calls.
    Returns: passes (bool), quick_score (float), matched (list)
    """
    title = product.get("title", "").lower()
    mandatory = profile.get("mandatory_specs", {})
    preferred = profile.get("preferred_specs", {})
    
    matched   = []
    failed    = []

    # Brand-specific searches should not be flooded by neighboring brands.
    product_type = profile.get("product_type", "").lower().strip()
    title_lower = product.get("title", "").lower()
    
    if product_type:
        identity_words = [w for w in product_type.split() if len(w) > 1]
        
        known_brands = [
            "iphone", "samsung", "galaxy", "oneplus", "xiaomi", "redmi", "poco",
            "realme", "vivo", "oppo", "motorola", "nokia", "pixel", "nothing",
            "apple", "macbook", "ipad", "airpods", "jbl", "sony", "boat", "bose",
            "hp", "dell", "lenovo", "asus", "acer",
        ]
        
        brand_in_query = [b for b in known_brands if b in product_type]
        
        if brand_in_query:
            brand_found = any(b in title_lower for b in brand_in_query)
            if not brand_found:
                return False, 0.0, [f"Vetoed: Product is not {brand_in_query[0]}"]
        else:
            # Generic searches allow a little typo tolerance in product words.
            long_words = [w for w in identity_words if len(w) > 3]
            if long_words:
                found_any = False
                for word in long_words:
                    if word in title_lower:
                        found_any = True
                        break
                    from difflib import SequenceMatcher
                    for title_word in title_lower.split():
                        if len(title_word) > 3 and SequenceMatcher(None, word, title_word).ratio() > 0.80:
                            found_any = True
                            break
                    if found_any:
                        break
                if not found_any:
                    return False, 0.0, [f"Vetoed: Product doesn't match '{product_type}'"]

    # Avoid ranking accessories unless the query explicitly asks for one.
    accessory_keywords = [
        "case", "cover", "tempered glass", "screen protector", "screen guard",
        "adapter", "cable", "charger", "charging cable", "usb cable",
        "usb drive", "flash drive", "pen drive", "memory card",
        "pouch", "sleeve", "bag", "holder", "stand", "mount", "dock",
        "skin", "film", "sticker", "protector",
        "strap", "band", "belt", "stylus", "cleaning kit",
    ]
    user_input_raw = profile.get("user_input", "")
    user_input_str = user_input_raw if isinstance(user_input_raw, str) else ""
    query_text = (product_type + " " + user_input_str).lower()
    
    is_acc = any(ak in title_lower for ak in accessory_keywords)
    query_wants_acc = any(ak in query_text for ak in accessory_keywords)
    
    if is_acc and not query_wants_acc:
        return False, 0.0, ["Vetoed: Accessory mismatch"]

    # Check mandatory specs
    for spec_key, spec_val in mandatory.items():
        val_str = str(spec_val).lower()
        terms = re.split(r'[\s/,]+', val_str)
        terms = [t for t in terms if len(t) > 1]
        
        found = any(t in title for t in terms)
        
        if found:
            matched.append(f"{spec_key}: {spec_val}")
        else:
            # Check for explicit contradictions
            incompatible_map = {
                "rtx":    ["intel iris", "radeon", "integrated", "mx550", "mx450"],
                "oled":   ["ips panel", "va panel", "tn panel"],
                "5g":     ["4g only", "non-5g"],
                "ssd":    ["hdd", "hard disk drive"],
            }
            is_incompatible = False
            for trigger, blocklist in incompatible_map.items():
                if trigger in val_str:
                    if any(b in title for b in blocklist):
                        failed.append(f"INCOMPATIBLE: title has conflicting spec for '{spec_key}'")
                        is_incompatible = True
                        break
            
            if not is_incompatible:
                pass # Not found but not contradicted - let LLM decide elsewhere

    # Score preferred specs
    preferred_hits = 0
    for spec_key, spec_val in preferred.items():
        val_str = str(spec_val).lower()
        terms = re.split(r'[\s/,]+', val_str)
        if any(t in title for t in terms if len(t) > 1):
            preferred_hits += 1
            matched.append(f"{spec_key}: {spec_val} (preferred)")

    # Veto explicit conflicts, and reject very weak title/spec overlap.
    mandatory_specs_count = max(len(mandatory), 1)
    mandatory_hit_count   = len([m for m in matched if "(preferred)" not in m])
    mandatory_hit_ratio   = mandatory_hit_count / mandatory_specs_count
    
    if mandatory_specs_count >= 2 and mandatory_hit_ratio < 0.30:
        if not any("INCOMPATIBLE" in f for f in failed):
            failed.append(f"INSUFFICIENT SPECS: title matches < 30% of mandatory specs ({mandatory_hit_count}/{mandatory_specs_count})")
    
    if failed:
        return False, 0.0, matched
    
    preferred_ratio = preferred_hits / max(len(preferred), 1)
    quick_score = (0.7 * mandatory_hit_ratio) + (0.3 * preferred_ratio)
    
    return True, quick_score, matched


# LLM spec matching

def llm_spec_match(product: dict, profile: dict, pre_matched: list[str]) -> dict:
    """Stage 2: Deep LLM spec analysis on top candidates."""
    prompt = f"""
You are a product specification matcher for Indian e-commerce.

User's Requirements:
- Product Type: {profile.get('product_type', '')}
- Mandatory Specs: {json.dumps(profile.get('mandatory_specs', {}))}
- Preferred Specs: {json.dumps(profile.get('preferred_specs', {}))}

Product Title: {product.get('title', '')[:150]}
Price: ₹{product.get('price', 0):,.0f}

Already confirmed by keyword match: {pre_matched}

Your job: Check if this product genuinely satisfies the mandatory specs.

⚠️ VETO RULES (SMART RELAXATION):
1. NUMERICAL SPECS: Allow ±15% tolerance (e.g., 17W is acceptable for a 20W requirement, but 10W is NOT). Veto if variation exceeds 15%.
2. BINARY SPECS (ANC, Waterproof, OLED): Use semantic matching. Veto ONLY if the feature is explicitly different or confirmed absent (e.g. "Membrane" when "Mechanical" was asked). 
3. SUBJECTIVE SPECS (Premium, Good Bass, Slim): NEVER VETO on these. Use them for scoring 0.0-1.0 only.
4. TYPE MISMATCH: ALWAYS VETO if the product is an entirely different category (e.g. an "Adapter" when a "Speaker" was asked).
5. PRODUCT VARIANTS: DO NOT VETO variants/sub-models of the same product line. "iPhone 17 Pro", "iPhone 17 Plus", "iPhone 17 Pro Max" are ALL valid matches for "iPhone 17". Similarly "Galaxy S25 Ultra" matches "Galaxy S25". Only veto if the BASE MODEL or GENERATION is different (e.g. "iPhone 16" when "iPhone 17" was asked).

Return ONLY valid JSON:
{{
  "match_score": <float 0.0–1.0, 1.0 = perfect match, 0.5 = minor numeric variation/subjective match>,
  "veto": <true if product clearly fails a mandatory spec or category mismatch>,
  "confirmed_specs": ["specs this product definitely has"],
  "missing_specs": ["mandatory specs this product lacks"],
  "reasoning": "<one sentence, max 15 words explaining logic>"
}}
"""
    try:
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0, api_key=os.getenv("GROQ_API_KEY"))
        response = llm.invoke(prompt)
        raw = response.content.strip()
        
        if not raw:
            raise ValueError("Empty LLM response")
        
        result = extract_json(raw)
        if result: return result
        
        # Some responses arrive fenced as Markdown despite the JSON-only prompt.
        raw_clean = raw.replace("```json","").replace("```","")
        return json.loads(raw_clean)
    except Exception as e:
        # Keep the pipeline usable if Groq is unavailable.
        title = product.get("title", "").lower()
        req_type = profile.get("product_type", "").lower()
        
        accessory_keywords = [
            "case", "cover", "tempered glass", "screen protector", "screen guard",
            "adapter", "cable", "charger", "charging cable", "usb cable",
            "pouch", "sleeve", "bag", "holder", "stand", "mount", "dock",
        ]
        is_accessory = any(kw in title for kw in accessory_keywords)
        should_veto = is_accessory and (req_type not in title)
        
        match_ratio = len(pre_matched) / max(len(profile.get("mandatory_specs", {})), 1) if pre_matched else 0.4
        
        return {
            "match_score": 0.1 if should_veto else round(max(match_ratio, 0.4), 2), 
            "veto": should_veto, 
            "confirmed_specs": pre_matched if pre_matched else [], 
            "missing_specs": [], 
            "reasoning": "Vetoed: Category mismatch" if should_veto else "Math fallback (Groq unavailable)"
        }

def extract_json(text: str) -> dict:
    """Safely extracts JSON from noisy LLM output using regex."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match: return None
    try:
        # Clean up common LLM formatting issues
        cleaned = match.group().replace('\"', '"').replace("\'", "'")
        return json.loads(cleaned)
    except Exception: return None


# Batch-normalized score components

def compute_all_scores(product: dict, profile: dict, all_products: list[dict]) -> dict:
    scores = {}
    budget = profile.get("budget_inr") or 999999
    price  = product.get("price", 0)

    # 1. Price Score (Gaussian Sweet-Spot Curve)
    #    Peak at ~85% of budget — practical shopping behavior:
    #    ₹1500 budget → sweet spot ₹1050-₹1500 (±30% below, ±20% above)
    #    ₹50000 budget → sweet spot ₹35000-₹50000 (same proportional curve)
    #    Products way below budget score LOW (likely wrong/inferior product)
    all_prices = [p["price"] for p in all_products if p.get("price", 0) > 0]
    median_price = statistics.median(all_prices) if all_prices else price
    if price <= 0:
        scores["price_score"] = 0.0
    elif price > budget * 1.5:
        scores["price_score"] = 0.0
    else:
        ratio = price / budget  # e.g., 0.15 for ₹750/₹5000
        sweet_spot = 0.85       # 85% of budget is the ideal price point

        # Asymmetric Gaussian: wider spread below sweet spot, tighter above
        if ratio <= sweet_spot:
            sigma = 0.30  # forgiving below (₹3500 for ₹5000 budget is still ok)
        else:
            sigma = 0.20  # tighter above (over budget penalized more)

        budget_alignment = math.exp(-((ratio - sweet_spot) ** 2) / (2 * sigma ** 2))

        # Small market-comparison bonus (20% influence)
        vs_median = max(0.0, min(1.0, (median_price - price) / median_price + 0.5))

        scores["price_score"] = round(0.80 * budget_alignment + 0.20 * vs_median, 3)

    # 2. Rating Score (Bayesian Weighting — stronger review-count bias)
    #    A product needs ~200+ reviews before its star rating is fully trusted.
    #    1 review @ 5★ → score 0.70 (pulled toward 3.5 average)
    #    500 reviews @ 4.5★ → score 0.86 (trusted, high score)
    adj_rating = product.get("adjusted_rating", product.get("rating", 0))
    reviews    = product.get("reviews_count", 0)
    confidence = reviews / (reviews + 200)  # was 100 — now needs 200 reviews for full trust
    bayesian   = (confidence * adj_rating) + ((1 - confidence) * 3.5)
    scores["rating_score"] = round(min(bayesian / 5.0, 1.0), 3)

    # 3. Popularity Score (Log Normalized)
    all_reviews = [p.get("reviews_count", 0) for p in all_products]
    max_reviews = max(all_reviews) if all_reviews else 1
    scores["popularity_score"] = round(math.log1p(reviews) / math.log1p(max_reviews + 1), 3)

    # 4. Spec Match Score
    scores["spec_score"] = round(product.get("spec_score", 0.5), 3)

    # 5. Price History Score
    scores["price_history_score"] = round(product.get("price_history_score", 0.5), 3)

    # 6. Seller Score
    scores["seller_score"] = round(compute_seller_score(product), 3)

    # 7. Trust Score
    scores["trust_score"] = round(product.get("trust_score", 0.5), 3)

    return scores

def compute_seller_score(product: dict) -> float:
    platform = product.get("platform", "").lower()
    seller   = product.get("seller", "").lower()
    if ("amazon" in seller and "amazon" in platform) or \
       ("flipkart" in seller and "flipkart" in platform):
        return 0.95
    if any(kw in seller for kw in ["official", "store", "brand", "authorized", "direct"]):
        return 0.80
    if seller and seller not in ["unknown", "", "amazon", "flipkart"]:
        return 0.60
    return 0.40


# Final score and hard vetoes

def compute_final_score(scores: dict, weights: dict, product: dict, profile: dict) -> tuple[float, str]:
    if product.get("spec_veto", False):
        return 0.0, f"Vetoed: {product.get('veto_reason', 'fails mandatory specs')}"
    
    budget = profile.get("budget_inr")
    price  = product.get("price", 0)
    if budget and price > budget * 1.5:
        return 0.0, f"Vetoed: {(price/budget-1)*100:.0f}% over budget"
    if price <= 0:
        return 0.0, "Vetoed: price data unavailable"

    if budget and price < budget * 0.10:
        return 0.0, f"Vetoed: ₹{price:,.0f} is only {price/budget*100:.0f}% of ₹{budget:,} budget — likely wrong product"

    review_count = product.get("reviews_count", 0)
    if review_count < 10:
        return 0.0, f"Vetoed: only {review_count} review(s) — insufficient customer validation"

    trust = scores.get("trust_score", 0.5)
    trust_cap = 40.0 if trust < 0.30 else None

    # Spec match penalty: If spec score is very low, product is a poor match
    spec_penalty = 1.0
    if scores.get("spec_score", 0.5) < 0.40:
        spec_penalty = 0.85  # -15% penalty for weak spec match

    raw_score = (
        weights.get("spec",          0.20) * scores.get("spec_score",          0.5) +
        weights.get("price",         0.20) * scores.get("price_score",         0.5) +
        weights.get("rating",        0.15) * scores.get("rating_score",        0.5) +
        weights.get("popularity",    0.10) * scores.get("popularity_score",    0.5) +
        weights.get("price_history", 0.10) * scores.get("price_history_score", 0.5) +
        weights.get("seller",        0.10) * scores.get("seller_score",        0.5) +
        weights.get("trust",         0.15) * scores.get("trust_score",         0.5)
    )

    # Preserve exact model/generation matches when the query includes one.
    exact_match_multiplier = 1.0
    product_type = profile.get("product_type", "").lower().strip()
    title_lower = product.get("title", "").lower()
    
    if product_type and product_type in title_lower:
        exact_match_multiplier = 1.15  # +15% bonus for exact phrase match
    elif product_type:
        import re
        pt_tokens = [t for t in product_type.split() if len(t) > 1]
        has_penalty = False
        for t in pt_tokens:
            # Check if token is a model/generation number (e.g., '17', 's24', '15r')
            if re.match(r'^(?:\d{1,4}|[a-z]{1,2}\d{1,3}|\d{1,3}[a-z]{1,2})$', t):
                # Check for standalone match to avoid matching '17' inside '17500mAh'
                if not re.search(r'\b' + re.escape(t) + r'(?:\b|[a-z]{1,2}\b)', title_lower):
                    exact_match_multiplier = 0.60  # -40% severe penalty for missing model number
                    has_penalty = True
                    break
        
        if not has_penalty and pt_tokens:
            matches = sum(1 for t in pt_tokens if re.search(r'\b' + re.escape(t) + r'\b', title_lower))
            if matches == len(pt_tokens):
                exact_match_multiplier = 1.10  # +10% bonus if all tokens match independently

    final = round(raw_score * spec_penalty * exact_match_multiplier * 100, 1)
    if trust_cap: final = min(final, trust_cap)
    return min(final, 100.0), ""


# Result explanations

def generate_why_reasons(product: dict, scores: dict, profile: dict, rank: int) -> list[str]:
    reasons = []
    budget = profile.get("budget_inr", 0)
    price  = product.get("price", 0)

    if scores.get("spec_score", 0) >= 0.85:
        confirmed = product.get("confirmed_specs", [])
        if confirmed: reasons.append(f"Matches requirements: {', '.join(confirmed[:2])}")
        else: reasons.append("Strong specification match")

    if scores.get("price_score", 0) >= 0.70 and budget > price:
        reasons.append(f"₹{budget-price:,.0f} under your budget")

    history_method = product.get("price_history", {}).get("method")
    if history_method == "historical_30day":
        hist = product["price_history"]
        pct = hist.get("vs_historical_median_pct", 0)
        if pct > 8:
            reasons.append(f"{round(pct)}% below its 30-day median price")
    elif history_method == "relative_market_comparison":
        hist = product["price_history"]
        median = hist.get("median_market_price", 0)
        if median and price < median * 0.92:
            reasons.append(f"{round((median-price)/median*100)}% cheaper than market median")

    if scores.get("rating_score", 0) >= 0.80:
        reasons.append(f"Authentic {product.get('adjusted_rating', product.get('rating',0)):.1f}⭐ rating")

    if scores.get("popularity_score", 0) >= 0.75:
        reasons.append(f"Highly popular ({product.get('reviews_count',0):,} reviews)")

    if scores.get("seller_score", 0) >= 0.90:
        reasons.append("Sold by verified platform official seller")

    if rank == 1:
        reasons.append("🥇 Top overall recommendation")

    fake_pct = product.get("fake_percentage", 0)
    if fake_pct > 0.35: reasons.append(f"⚠️ {int(fake_pct*100)}% of review signals are suspicious")
    
    missing = product.get("missing_specs", [])
    if missing and len(missing) > 0 and missing[0] != "AI check unavailable":
        reasons.append(f"⚠️ May not have: {', '.join(missing[:2])}")

    if scores.get("spec_score", 0.5) < 0.60 and scores.get("spec_score", 0.5) > 0:
        reasons.append("⚠️ Partial spec match — verify before buying")

    return reasons


# Category weights

CATEGORY_WEIGHTS = {
    "electronics": {"spec": 0.25, "price": 0.15, "price_history": 0.15, "rating": 0.15, "trust": 0.10, "seller": 0.05, "popularity": 0.15},
    "fashion": {"rating": 0.30, "trust": 0.20, "price": 0.15, "popularity": 0.15, "seller": 0.08, "spec": 0.05, "price_history": 0.07},
    "appliances": {"spec": 0.20, "price": 0.15, "price_history": 0.15, "rating": 0.15, "popularity": 0.15, "seller": 0.10, "trust": 0.10},
    "consumables": {"trust": 0.30, "rating": 0.20, "popularity": 0.20, "seller": 0.15, "price": 0.10, "spec": 0.03, "price_history": 0.02},
    "furniture": {"rating": 0.25, "trust": 0.20, "price": 0.15, "popularity": 0.15, "seller": 0.15, "spec": 0.07, "price_history": 0.03},
    "other": {"spec": 0.15, "price": 0.15, "rating": 0.15, "popularity": 0.15, "trust": 0.15, "seller": 0.15, "price_history": 0.10}
}

def get_weights(category: str) -> dict:
    return CATEGORY_WEIGHTS.get(category.lower(), CATEGORY_WEIGHTS["other"])
