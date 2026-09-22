# scrapers/_utils.py
"""Shared helpers used by both Amazon and Flipkart scrapers."""

import json
import re
from typing import Any


# Playwright selector helpers

async def try_selectors(parent, selectors: list[str]):
    """Return the first element matched by any selector in the list."""
    for selector in selectors:
        try:
            el = await parent.query_selector(selector)
            if el:
                return el
        except Exception:
            continue
    return None


async def try_selectors_all(page, selectors: list[str]):
    """Return the first selector's result set that has more than 2 items."""
    for selector in selectors:
        try:
            items = await page.query_selector_all(selector)
            if items and len(items) > 2:
                return items
        except Exception:
            continue
    return []


# LLM JSON extraction

def extract_json_from_llm(text: str) -> Any:
    """
    Robustly extract JSON (object or array) from noisy LLM output.

    Handles markdown fencing, leading text, and multiple JSON fragments.
    Returns the parsed Python object, or None on failure.
    """
    raw = str(text or "").strip().replace("```json", "").replace("```", "").strip()

    # Try incremental parsing from every '{' or '[' position
    decoder = json.JSONDecoder()
    starts = [idx for idx, char in enumerate(raw) if char in "[{"]
    for start in starts:
        try:
            payload, _ = decoder.raw_decode(raw[start:])
            return payload
        except Exception:
            continue

    # Fallback: regex extraction
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
