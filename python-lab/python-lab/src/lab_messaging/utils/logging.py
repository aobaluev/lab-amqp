"""Logging utilities for lab_messaging applications."""

from __future__ import annotations

import logging


def setup_logging(level: str = "INFO", name: str | None = None) -> logging.Logger:
    """Configure standard library logging and return a logger.

    Does not log any secrets (passwords, tokens).
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(name or __name__)