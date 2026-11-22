"""Demo handler: get_metrics command."""

import logging

logger = logging.getLogger(__name__)


def handle_get_metrics(arguments: dict) -> dict:
    """Simulate metrics retrieval. Returns demo data only."""
    logger.info("Handler: handle_get_metrics arguments=%s", arguments)
    # Demonstration only — no real metrics collection
    return {
        "simulated": True,
        "action": "get_metrics",
        "details": "Metrics: cpu=42% mem=65% (simulated)",
    }