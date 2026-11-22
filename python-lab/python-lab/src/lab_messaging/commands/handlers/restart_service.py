"""Demo handler: restart_service command."""

import logging

logger = logging.getLogger(__name__)


def handle_restart_service(arguments: dict) -> dict:
    """Simulate a service restart. No real restart is performed."""
    logger.info("Handler: handle_restart_service arguments=%s", arguments)
    # Demonstration only — no real system commands
    return {
        "simulated": True,
        "action": "restart_service",
        "details": "Service restart simulated (no actual restart)",
    }