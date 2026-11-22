"""Demo handler: status command."""

import logging

logger = logging.getLogger(__name__)


def handle_status(arguments: dict) -> dict:
    """Simulate a status check. Returns demo data only."""
    logger.info("Handler: handle_status arguments=%s", arguments)
    # Demonstration only — no real system commands
    return {
        "simulated": True,
        "action": "status",
        "details": "All services nominal (simulated)",
    }