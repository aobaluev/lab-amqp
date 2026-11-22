"""Command dispatcher — routes command aliases to handler functions.

Uses an explicit table (dict) rather than if/elif chains.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

Handler = Callable[[dict], dict]


class CommandDispatcher:
    """Routes commands by alias to registered handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}

    def register(self, alias: str, handler: Handler) -> None:
        """Register a handler for a command alias."""
        self._handlers[alias] = handler
        logger.info("Dispatcher registered alias=%s handler=%s", alias, handler.__name__)

    def dispatch(self, alias: str, arguments: dict) -> dict:
        """Dispatch a command to its handler.

        Returns a result dict with status and data.
        Unknown aliases return an error result without raising.
        """
        logger.info("Command received alias=%s", alias)

        handler = self._handlers.get(alias)
        if handler is None:
            logger.warning("Unknown command alias=%s", alias)
            return {
                "status": "error",
                "error": f"Unknown command alias: {alias}",
                "alias": alias,
            }

        logger.info("Alias=%s handler=%s", alias, handler.__name__)
        try:
            result = handler(arguments)
            logger.info("Alias=%s handler=%s result=success", alias, handler.__name__)
            return {
                "status": "ok",
                "alias": alias,
                "handler": handler.__name__,
                "result": result,
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("Alias=%s handler=%s error=%s", alias, handler.__name__, exc)
            return {
                "status": "error",
                "alias": alias,
                "handler": handler.__name__,
                "error": str(exc),
            }

    @property
    def aliases(self) -> list[str]:
        """Return list of registered command aliases."""
        return sorted(self._handlers.keys())


# Global dispatcher instance
dispatcher = CommandDispatcher()