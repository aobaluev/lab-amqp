"""Common types and constants for JSON message contracts."""

from typing import Any

MESSAGE_TYPE_HEARTBEAT = "heartbeat"
MESSAGE_TYPE_COMMAND = "command"

CONTRACT_VERSION_1 = 1

REQUIRED_FIELDS = ("type", "version", "message_id", "timestamp", "payload")


def base_message(message_type: str, version: int, message_id: str, timestamp: str, payload: dict) -> dict:
    """Build a base message dict with common fields."""
    return {
        "type": message_type,
        "version": version,
        "message_id": message_id,
        "timestamp": timestamp,
        "payload": payload,
    }