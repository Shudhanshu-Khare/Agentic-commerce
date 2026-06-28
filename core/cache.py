"""24-hour query result cache for saving API credits on repeat searches."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


CACHE_FILE = Path("data/query_cache.json")
CACHE_TTL_SECONDS = 24 * 60 * 60
CACHE_SCHEMA_VERSION = 1


def make_cache_key(user_input: dict | str) -> str:
    """Build a stable cache key from the user-facing search input."""
    raw = json.dumps(user_input, sort_keys=True, ensure_ascii=False) if isinstance(user_input, dict) else str(user_input)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


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


def get_cached_result(user_input: dict | str, ttl_seconds: int = CACHE_TTL_SECONDS) -> dict | None:
    """Return cached pipeline output if it exists and is still fresh."""
    cache = _read_cache()
    entry = cache.get(make_cache_key(user_input))
    if not entry or entry.get("schema_version") != CACHE_SCHEMA_VERSION:
        return None

    age = time.time() - float(entry.get("created_at", 0))
    if age > ttl_seconds:
        return None

    return entry.get("payload")


def save_cached_result(user_input: dict | str, payload: dict) -> None:
    """Persist a pipeline output payload under the normalized search key."""
    cache = _read_cache()
    cache[make_cache_key(user_input)] = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "created_at": time.time(),
        "payload": payload,
    }

    # Keep the cache file small enough for local use.
    sorted_items = sorted(cache.items(), key=lambda item: item[1].get("created_at", 0), reverse=True)
    _write_cache(dict(sorted_items[:50]))
