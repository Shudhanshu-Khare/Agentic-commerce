"""Offline evaluator for saved Agentic Commerce result JSON files.

Usage:
    python scripts/evaluate_rankings.py --results path/to/results.json --truth eval/ground_truth.example.json

The results file can be either:
    - a list of ranked product dicts, or
    - a cached payload containing {"ranked_products": [...], "profile": {...}}
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.eval_metrics import evaluate_result_set


def load_ranked_products(path: Path) -> tuple[list[dict], int | None]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data, None
    if isinstance(data, dict):
        budget = (data.get("profile") or {}).get("budget_inr")
        return data.get("ranked_products", []), budget
    raise ValueError("Unsupported results JSON format")


def load_truth(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data[0] if data else {}
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True, help="Saved ranked products or cached payload JSON")
    parser.add_argument("--truth", default="", help="Ground truth JSON with labels and optional budget")
    args = parser.parse_args()

    results, inferred_budget = load_ranked_products(Path(args.results))
    labels = []
    budget = inferred_budget
    if args.truth:
        truth = load_truth(Path(args.truth))
        labels = truth.get("labels", [])
        budget = truth.get("budget", budget)

    metrics = evaluate_result_set(results, labels, budget)
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
