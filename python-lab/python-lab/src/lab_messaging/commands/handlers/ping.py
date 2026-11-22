"""Demo handler: ping command."""

import logging

logger = logging.getLogger(__name__)


def handle_ping(arguments: dict) -> dict:
    """Simulate a ping. Returns pong."""
    logger.info("Handler: handle_ping arguments=%s", arguments)
    # Demonstration only
    return {
        "simulated": True,
        "action": "ping",
        "details": "pong",
    }