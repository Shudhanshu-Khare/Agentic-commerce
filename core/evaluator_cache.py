"""Short-lived cache for Evaluator LLM spec-match decisions."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


CACHE_FILE = Path("data/evaluator_llm_cache.json")
CACHE_SCHEMA_VERSION = 1
CACHE_TTL_SECONDS = 24 * 60 * 60
MAX_CACHE_ENTRIES = 500


def _stable_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "category": profile.get("category", ""),
        "product_type": profile.get("product_type", ""),
        "budget_inr": profile.get("budget_inr"),
        "mandatory_specs": profile.get("mandatory_specs", {}),
        "preferred_specs": profile.get("preferred_specs", {}),
        "constraints": profile.get("constraints", []),
        "use_case": profile.get("use_case", ""),
        "raw_specs": profile.get("raw_specs", ""),
        "search_keywords": profile.get("search_keywords", ""),
    }


def _stable_product(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": product.get("title", ""),
        "url": product.get("url", ""),
        "platform": product.get("platform", ""),
        "price": round(float(product.get("price", 0) or 0), 2),
        "rating": round(float(product.get("rating", 0) or 0), 2),
        "reviews_count": int(product.get("reviews_count", 0) or 0),
    }


def make_evaluator_llm_key(
    product: dict[str, Any],
    profile: dict[str, Any],
    pre_matched: list[str],
    model_name: str,
    prompt_version: str,
) -> str:
    """Build a cache key that changes whenever inputs or prompt/model change."""
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "model_name": model_name,
        "prompt_version": prompt_version,
        "product": _stable_product(product),
        "profile": _stable_profile(profile),
        "pre_matched": pre_matched,
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _read_cache() -> dict[str, Any]:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_cache(cache: dict[str, Any]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def get_cached_evaluator_llm(
    product: dict[str, Any],
    profile: dict[str, Any],
    pre_matched: list[str],
    model_name: str,
    prompt_version: str,
    ttl_seconds: int = CACHE_TTL_SECONDS,
) -> dict[str, Any] | None:
    cache = _read_cache()
    key = make_evaluator_llm_key(product, profile, pre_matched, model_name, prompt_version)
    entry = cache.get(key)
    if not entry or entry.get("schema_version") != CACHE_SCHEMA_VERSION:
        return None

    age = time.time() - float(entry.get("created_at", 0))
    if age > ttl_seconds:
        return None

    result = entry.get("result")
    return result if isinstance(result, dict) else None


def save_cached_evaluator_llm(
    product: dict[str, Any],
    profile: dict[str, Any],
    pre_matched: list[str],
    model_name: str,
    prompt_version: str,
    result: dict[str, Any],
) -> None:
    cache = _read_cache()
    key = make_evaluator_llm_key(product, profile, pre_matched, model_name, prompt_version)
    cache[key] = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "created_at": time.time(),
        "result": result,
    }

    sorted_items = sorted(cache.items(), key=lambda item: item[1].get("created_at", 0), reverse=True)
    _write_cache(dict(sorted_items[:MAX_CACHE_ENTRIES]))
