"""Evaluation metrics for ranked product results."""

from __future__ import annotations

import math
from collections import Counter


def compute_precision_at_k(relevance: list[int], k: int = 3, threshold: int = 2) -> float:
    """Fraction of top-k results whose human relevance is at least threshold."""
    if k <= 0:
        return 0.0
    top_k = relevance[:k]
    if not top_k:
        return 0.0
    return round(sum(1 for score in top_k if score >= threshold) / k, 3)


def compute_ndcg(relevance: list[int], k: int = 10) -> float:
    """Normalized discounted cumulative gain for graded relevance labels."""
    if not relevance or k <= 0:
        return 0.0

    predicted = relevance[:k]
    dcg = sum(score / math.log2(idx + 2) for idx, score in enumerate(predicted))
    ideal = sorted(predicted, reverse=True)
    idcg = sum(score / math.log2(idx + 2) for idx, score in enumerate(ideal))
    return round(dcg / idcg, 3) if idcg > 0 else 0.0


def compute_budget_compliance(results: list[dict], budget: int | float | None, k: int = 10) -> float:
    """Share of top-k results at or below budget."""
    if not budget:
        return 1.0
    top_k = results[:k]
    if not top_k:
        return 0.0
    compliant = sum(1 for product in top_k if product.get("price", 0) <= budget)
    return round(compliant / len(top_k), 3)


def compute_monotonicity(results: list[dict]) -> float:
    """Check whether final_score is non-increasing down the ranked list."""
    if len(results) < 2:
        return 1.0
    pairs = zip(results, results[1:])
    total = 0
    ordered = 0
    for left, right in pairs:
        total += 1
        if left.get("final_score", 0) >= right.get("final_score", 0):
            ordered += 1
    return round(ordered / total, 3) if total else 1.0


def compute_stability(top_runs: list[list[str]], k: int = 3) -> float:
    """Average overlap of top-k product IDs/titles across repeated runs."""
    if len(top_runs) < 2:
        return 1.0
    base = set(top_runs[0][:k])
    if not base:
        return 0.0
    overlaps = []
    for run in top_runs[1:]:
        overlaps.append(len(base.intersection(set(run[:k]))) / len(base))
    return round(sum(overlaps) / len(overlaps), 3)


def summarize_verdicts(results: list[dict]) -> dict:
    """Count review verdict labels in a ranked result set."""
    return dict(Counter(product.get("review_verdict", "Unknown") for product in results))


def evaluate_result_set(results: list[dict], relevance: list[int] | None = None, budget: int | None = None) -> dict:
    """Compute standard and system metrics for one query result set."""
    relevance = relevance or []
    metrics = {
        "budget_compliance_at_10": compute_budget_compliance(results, budget, 10),
        "monotonicity": compute_monotonicity(results),
        "verdicts": summarize_verdicts(results),
    }
    if relevance:
        metrics["precision_at_3"] = compute_precision_at_k(relevance, 3)
        metrics["ndcg_at_10"] = compute_ndcg(relevance, 10)
    return metrics
