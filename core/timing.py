"""Per-agent latency instrumentation with a small persistent history."""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


TIMING_LOG = Path("data/timing_log.json")
MAX_TIMING_RUNS = 100


@contextmanager
def agent_timer(agent_name: str, timings: dict):
    """Measure one agent call and store elapsed seconds in ``timings``."""
    start = time.time()
    try:
        yield
    finally:
        timings[agent_name] = round(time.time() - start, 2)


def save_timing(timings: dict) -> None:
    """Append a timing record and keep only the most recent runs."""
    if not timings:
        return

    TIMING_LOG.parent.mkdir(parents=True, exist_ok=True)
    log = []
    if TIMING_LOG.exists():
        try:
            log = json.loads(TIMING_LOG.read_text(encoding="utf-8"))
        except Exception:
            log = []

    log.append({"timestamp": datetime.now().isoformat(timespec="seconds"), **timings})
    TIMING_LOG.write_text(
        json.dumps(log[-MAX_TIMING_RUNS:], indent=2),
        encoding="utf-8",
    )


def compute_percentiles(agent_name: str) -> dict:
    """Return P50/P95 timing stats for an agent once at least 3 runs exist."""
    if not TIMING_LOG.exists():
        return {}

    try:
        log = json.loads(TIMING_LOG.read_text(encoding="utf-8"))
    except Exception:
        return {}

    times = sorted(
        float(entry[agent_name])
        for entry in log
        if agent_name in entry and isinstance(entry.get(agent_name), (int, float))
    )
    if len(times) < 3:
        return {}

    p50_idx = len(times) // 2
    p95_idx = min(len(times) - 1, int(len(times) * 0.95))
    return {"p50": round(times[p50_idx], 2), "p95": round(times[p95_idx], 2), "runs": len(times)}
