"""Runtime validation helpers for pipeline boundary data."""

from __future__ import annotations

from typing import Iterable

from pydantic import ValidationError

from core.schemas import Product, UserProfile


def validate_profile(profile: dict, context: str = "profile") -> dict:
    """Validate and normalize a user profile dict without hiding bad data."""
    try:
        return UserProfile(**(profile or {})).model_dump()
    except ValidationError as exc:
        raise ValueError(f"Invalid {context}: {exc}") from exc


def validate_product(product: dict, context: str = "product") -> dict:
    """Validate and normalize a product dict at an agent boundary."""
    try:
        return Product(**(product or {})).model_dump()
    except ValidationError as exc:
        title = (product or {}).get("title", "<missing title>")
        raise ValueError(f"Invalid {context} '{title}': {exc}") from exc


def validate_products(products: Iterable[dict], context: str = "products") -> list[dict]:
    """Validate a list of product dicts while preserving order."""
    return [
        validate_product(product, f"{context}[{idx}]")
        for idx, product in enumerate(products or [])
    ]
