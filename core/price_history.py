"""SQLite-backed hybrid price history for the Historian agent."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median


DB_PATH = Path("data/price_history.db")
NOISE_WORDS = {
    "with",
    "and",
    "for",
    "the",
    "new",
    "latest",
    "edition",
    "version",
    "original",
}


def generate_product_id(title: str, platform: str) -> str:
    """Generate a stable enough ID for repeated listings across sessions."""
    normalized = re.sub(r"\s+", " ", (title or "").lower().strip())
    words = [
        re.sub(r"[^a-z0-9.]+", "", word)
        for word in normalized.split()
        if word not in NOISE_WORDS
    ]
    words = [word for word in words if len(word) > 1]
    key = " ".join(words[:8])
    raw = f"{platform or 'unknown'}:{key}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS price_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            observed_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_price_product_time ON price_observations(product_id, observed_at)"
    )
    return conn


def get_recent_prices(product_id: str, days: int = 30) -> list[float]:
    """Fetch historical prices for a product in the last ``days`` days."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT price FROM price_observations
            WHERE product_id = ? AND observed_at >= ?
            ORDER BY observed_at DESC
            """,
            (product_id, cutoff),
        ).fetchall()
    return [float(row[0]) for row in rows if row[0] and float(row[0]) > 0]


def record_price(product: dict, product_id: str | None = None) -> None:
    """Store the current observed price for future runs."""
    price = float(product.get("price", 0) or 0)
    title = product.get("title", "")
    platform = product.get("platform", "")
    if price <= 0 or not title:
        return

    product_id = product_id or generate_product_id(title, platform)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO price_observations(product_id, platform, title, price, observed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (product_id, platform, title, price, datetime.now().isoformat(timespec="seconds")),
        )


def compute_historical_price_context(product: dict, min_points: int = 3) -> dict | None:
    """Return 30-day price context if enough history exists, otherwise ``None``."""
    product_id = generate_product_id(product.get("title", ""), product.get("platform", ""))
    prices = get_recent_prices(product_id)
    if len(prices) < min_points:
        return None

    current = float(product.get("price", 0) or 0)
    historical_median = median(prices)
    if current <= 0 or historical_median <= 0:
        return None

    delta = (historical_median - current) / historical_median
    score = round(max(0.0, min(1.0, 0.5 + delta)), 3)
    return {
        "product_id": product_id,
        "score": score,
        "history": {
            "method": "historical_30day",
            "product_id": product_id,
            "historical_points": len(prices),
            "historical_median_price": round(historical_median, 0),
            "current_price": current,
            "vs_historical_median_pct": round(delta * 100, 1),
            "is_good_deal": score > 0.6,
        },
    }
