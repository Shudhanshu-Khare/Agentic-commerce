"""Structured logging setup for local pipeline runs."""

from __future__ import annotations

import logging
from pathlib import Path


LOG_FILE = Path("data/agentic_commerce.log")


def configure_logging() -> logging.Logger:
    """Configure a small file logger and return the project logger."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("agentic_commerce")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
