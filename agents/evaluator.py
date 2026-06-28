# agents/evaluator.py
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from langchain_groq import ChatGroq

from core.evaluator_cache import get_cached_evaluator_llm, save_cached_evaluator_llm
from core.scoring import get_weights
from core.scoring import (
    fast_spec_prefilter,
    llm_spec_match,
    compute_all_scores,
    compute_final_score,
    generate_why_reasons,
)
from core.validation import validate_products, validate_profile


EVALUATOR_LLM_MODEL = "llama-3.1-8b-instant"
EVALUATOR_PROMPT_VERSION = "spec-match-batch-v1"
EVALUATOR_BATCH_SIZE = 5
EVALUATOR_BATCH_WORKERS = 1


def call_llm_with_retry(fn, *args, retries: int = 1, delay: float = 1.5, **kwargs):
    """
    Calls any LLM function with automatic retry on failure.
    Max 2 attempts (1 original + 1 retry) to keep pipeline fast.
    """
    for attempt in range(1, retries + 2):
        try:
            result = fn(*args, **kwargs)
            return result
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                wait = min(delay * attempt, 6.0)
                print(f"[Groq Rate Limit] Attempt {attempt}. Waiting {wait:.0f}s...")
                time.sleep(wait)
            elif attempt <= retries:
                time.sleep(delay)
            else:
                return {
                    "match_score": 0.5,
                    "veto": False,
                    "confirmed_specs": [],
                    "missing_specs": [],
                    "reasoning": "LLM unavailable - fallback score applied",
                }

    return {
        "match_score": 0.5,
        "veto": False,
        "confirmed_specs": [],
        "missing_specs": [],
        "reasoning": "LLM unavailable - rate limit exhaustion fallback",
    }


def _normalise_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return bool(value)


def _normalise_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item)[:120] for item in value if item is not None]


def normalise_llm_spec_result(result: Any) -> dict | None:
    """Validate and normalize one LLM spec-match result."""
    if not isinstance(result, dict):
        return None
    try:
        match_score = float(result.get("match_score", 0.5))
    except Exception:
        return None
    if match_score < 0.0 or match_score > 1.0:
        return None

    reasoning = str(result.get("reasoning", "")).strip()
    if not reasoning:
        return None

    return {
        "match_score": round(match_score, 3),
        "veto": _normalise_bool(result.get("veto", False)),
        "confirmed_specs": _normalise_str_list(result.get("confirmed_specs", [])),
        "missing_specs": _normalise_str_list(result.get("missing_specs", [])),
        "reasoning": reasoning[:240],
    }


def is_cacheable_llm_result(result: dict | None) -> bool:
    """Only cache real LLM decisions, not degraded fallback answers."""
    if not result:
        return False
    reasoning = result.get("reasoning", "").lower()
    fallback_markers = ["fallback", "unavailable", "rate limit", "groq unavailable"]
    return not any(marker in reasoning for marker in fallback_markers)


def _extract_json_payload(text: str) -> Any:
    raw = str(text or "").strip().replace("```json", "").replace("```", "").strip()
    decoder = json.JSONDecoder()
    starts = [idx for idx, char in enumerate(raw) if char in "[{"]
    for start in starts:
        try:
            payload, _ = decoder.raw_decode(raw[start:])
            return payload
        except Exception:
            continue

    object_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if object_match:
        try:
            return json.loads(object_match.group())
        except Exception:
            pass

    array_match = re.search(r"\[.*\]", raw, re.DOTALL)
    if array_match:
        try:
            return json.loads(array_match.group())
        except Exception:
            pass
    return None


def _run_llm_spec_match_batch(batch: list[tuple[dict, list[str]]], profile: dict) -> list[dict | None]:
    """Call the evaluator LLM once for a small batch, then validate each result."""
    products_payload = []
    for idx, (product, pre_matched) in enumerate(batch, start=1):
        products_payload.append(
            {
                "product_index": idx,
                "title": product.get("title", "")[:180],
                "price_inr": round(float(product.get("price", 0) or 0), 2),
                "platform": product.get("platform", ""),
                "already_confirmed_by_keyword_match": pre_matched,
            }
        )

    prompt = f"""
You are a product specification matcher for Indian e-commerce.

User's Requirements:
- Product Type: {profile.get('product_type', '')}
- Mandatory Specs: {json.dumps(profile.get('mandatory_specs', {}), ensure_ascii=False)}
- Preferred Specs: {json.dumps(profile.get('preferred_specs', {}), ensure_ascii=False)}

Products to evaluate independently:
{json.dumps(products_payload, ensure_ascii=False, indent=2)}

Your job: Check if EACH product genuinely satisfies the mandatory specs.
Do not compare products with each other. Apply the same rules independently.

VETO RULES (SMART RELAXATION):
1. NUMERICAL SPECS: Allow +/-15% tolerance. Veto if variation exceeds 15%.
2. BINARY SPECS (ANC, Waterproof, OLED): Use semantic matching. Veto ONLY if the feature is explicitly different or confirmed absent.
3. SUBJECTIVE SPECS (Premium, Good Bass, Slim): NEVER VETO on these. Use them for scoring 0.0-1.0 only.
4. TYPE MISMATCH: ALWAYS VETO if the product is an entirely different category.
5. PRODUCT VARIANTS: DO NOT VETO variants/sub-models of the same product line. Only veto if the BASE MODEL or GENERATION is different.

Return ONLY valid JSON. Return exactly one result for every product_index:
{{
  "results": [
    {{
      "product_index": 1,
      "match_score": <float 0.0-1.0>,
      "veto": <true if product clearly fails a mandatory spec or category mismatch>,
      "confirmed_specs": ["specs this product definitely has"],
      "missing_specs": ["mandatory specs this product lacks"],
      "reasoning": "<one sentence, max 15 words explaining logic>"
    }}
  ]
}}
"""
    llm = ChatGroq(model=EVALUATOR_LLM_MODEL, temperature=0, api_key=os.getenv("GROQ_API_KEY"))
    response = llm.invoke(prompt)
    payload = _extract_json_payload(response.content)
    if not isinstance(payload, dict):
        return [None] * len(batch)

    raw_results = payload.get("results")
    if not isinstance(raw_results, list):
        return [None] * len(batch)

    by_index = {}
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        try:
            product_index = int(item.get("product_index", 0))
        except Exception:
            continue
        by_index[product_index] = normalise_llm_spec_result(item)

    return [by_index.get(idx) for idx in range(1, len(batch) + 1)]


def call_batch_llm_with_retry(batch: list[tuple[dict, list[str]]], profile: dict, retries: int = 1, delay: float = 1.5):
    for attempt in range(1, retries + 2):
        try:
            return _run_llm_spec_match_batch(batch, profile)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                wait = min(delay * attempt, 6.0)
                print(f"[Groq Rate Limit] Batch attempt {attempt}. Waiting {wait:.0f}s...")
                time.sleep(wait)
            elif attempt <= retries:
                time.sleep(delay)
            else:
                return [None] * len(batch)
    return [None] * len(batch)


def apply_llm_result(product: dict, llm_result: dict) -> bool:
    product["spec_score"] = llm_result.get("match_score", 0.5)
    product["spec_veto"] = llm_result.get("veto", False)
    product["veto_reason"] = "AI confirmed mandatory spec failure" if llm_result.get("veto") else ""
    product["confirmed_specs"] = llm_result.get("confirmed_specs", [])
    product["missing_specs"] = llm_result.get("missing_specs", [])
    product["spec_reasoning"] = llm_result.get("reasoning", "")
    return bool(product["spec_veto"])


def get_single_llm_spec_result(product: dict, profile: dict, pre_matched: list[str]) -> dict:
    llm_result = call_llm_with_retry(
        llm_spec_match,
        product,
        profile,
        pre_matched,
        retries=1,
        delay=1.5,
    )
    normalised = normalise_llm_spec_result(llm_result)
    if normalised:
        return normalised
    return {
        "match_score": 0.5,
        "veto": False,
        "confirmed_specs": [],
        "missing_specs": [],
        "reasoning": "LLM unavailable - fallback score applied",
    }


def run_pending_batches(
    pending: list[tuple[dict, list[str]]],
    profile: dict,
) -> list[tuple[list[tuple[dict, list[str]]], list[dict | None]]]:
    """Run independent evaluator batches concurrently without changing decisions."""
    batches = [
        pending[start:start + EVALUATOR_BATCH_SIZE]
        for start in range(0, len(pending), EVALUATOR_BATCH_SIZE)
    ]
    if not batches:
        return []

    workers = min(EVALUATOR_BATCH_WORKERS, len(batches))
    if workers <= 1:
        results = []
        for idx, batch in enumerate(batches, start=1):
            print(f"   Matching batch {idx}/{len(batches)}...", end="\r")
            batch_results = call_batch_llm_with_retry(batch, profile, retries=1, delay=1.5)
            results.append((batch, batch_results))
        return results

    results_by_index: dict[int, tuple[list[tuple[dict, list[str]]], list[dict | None]]] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_index = {
            executor.submit(call_batch_llm_with_retry, batch, profile, 1, 1.5): idx
            for idx, batch in enumerate(batches)
        }
        for completed, future in enumerate(as_completed(future_to_index), start=1):
            idx = future_to_index[future]
            batch = batches[idx]
            print(f"   Matching batches {completed}/{len(batches)} complete...", end="\r")
            try:
                batch_results = future.result()
            except Exception:
                batch_results = [None] * len(batch)
            results_by_index[idx] = (batch, batch_results)

    return [results_by_index[idx] for idx in range(len(batches))]


def run_evaluator(products: list[dict], profile: dict) -> list[dict]:
    """
    Upgraded Evaluation Pipeline:
    Stage 1: Keyword Pre-filter (Instant)
    Stage 2: LLM Match for every Stage 1 survivor, with cache + safe batching
    Stage 3: Batch-Normalized Scoring
    Stage 4: Ranking & Deterministic Why
    """
    products = validate_products(products, "evaluator input")
    profile = validate_profile(profile, "evaluator profile")
    weights = get_weights(profile.get("category", "other"))

    # Stage 1: Fast pre-filter all candidates.
    stage1_results = []
    vetoed_count = 0

    for product in products:
        passes, quick_score, pre_matched = fast_spec_prefilter(product, profile)
        if not passes:
            product["spec_veto"] = True
            product["veto_reason"] = "Failed keyword incompatibility check"
            vetoed_count += 1
        else:
            product["spec_veto"] = False
            product["quick_score"] = quick_score
            product["pre_matched"] = pre_matched
            stage1_results.append(product)

    print(f"   Stage 1 — Keyword Filter  : {len(stage1_results)} passed, {vetoed_count} vetoed")

    # Stage 2: Deep LLM spec match on ALL Stage 1 survivors.
    rate_limit_sleep = 0.4
    stage1_results.sort(key=lambda x: x.get("quick_score", 0), reverse=True)

    llm_vetoes = 0
    llm_total = len(stage1_results)
    cache_hits = 0
    batch_calls = 0
    single_fallbacks = 0
    pending: list[tuple[dict, list[str]]] = []

    for product in stage1_results:
        pre_matched = product.get("pre_matched", [])
        cached = get_cached_evaluator_llm(
            product,
            profile,
            pre_matched,
            EVALUATOR_LLM_MODEL,
            EVALUATOR_PROMPT_VERSION,
        )
        cached_result = normalise_llm_spec_result(cached)
        if cached_result:
            cache_hits += 1
            if apply_llm_result(product, cached_result):
                llm_vetoes += 1
        else:
            pending.append((product, pre_matched))

    batch_outputs = run_pending_batches(pending, profile)
    batch_calls = len(batch_outputs)

    for batch, batch_results in batch_outputs:
        if len(batch_results) != len(batch):
            batch_results = [None] * len(batch)

        for (product, pre_matched), batch_result in zip(batch, batch_results):
            llm_result = normalise_llm_spec_result(batch_result)
            if llm_result is None:
                single_fallbacks += 1
                time.sleep(rate_limit_sleep)
                llm_result = get_single_llm_spec_result(product, profile, pre_matched)

            if is_cacheable_llm_result(llm_result):
                save_cached_evaluator_llm(
                    product,
                    profile,
                    pre_matched,
                    EVALUATOR_LLM_MODEL,
                    EVALUATOR_PROMPT_VERSION,
                    llm_result,
                )

            if apply_llm_result(product, llm_result):
                llm_vetoes += 1
                print(f"     X {product.get('title', '')[:38]:40s} -> {product['spec_reasoning'][:55]}")

    print(
        f"   Stage 2 — AI Spec Match   : {llm_total - llm_vetoes} passed, {llm_vetoes} vetoed "
        f"({cache_hits} cached, {batch_calls} batch calls, {single_fallbacks} single fallbacks)"
    )

    all_processed = stage1_results

    # Stage 3: Score everything (batch-normalized).
    scored = []
    score_total = len(all_processed)
    print(f"   Stage 3 — Scoring         : {score_total} products to normalize")

    for s_idx, product in enumerate(all_processed):
        print(f"   Scoring {s_idx+1}/{score_total}...", end="\r")
        scores = compute_all_scores(product, profile, all_processed)
        final_score, veto_reason = compute_final_score(scores, weights, product, profile)

        if veto_reason:
            continue

        product["scores"] = scores
        product["final_score"] = final_score
        product["veto_reason"] = veto_reason
        scored.append(product)

    # Stage 4: Final Ranking & deterministic why reasons.
    ranked = sorted(scored, key=lambda x: x.get("final_score", 0), reverse=True)[:10]

    for i, product in enumerate(ranked):
        product["rank"] = i + 1
        product["why"] = generate_why_reasons(product, product["scores"], profile, product["rank"])

    return validate_products(ranked, "evaluator output")
