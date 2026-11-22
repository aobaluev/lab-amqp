"""Command contract v1 — permissive validation.

Permissive mode: required fields must be present and have correct types,
but additional fields are allowed without error.
"""

from __future__ import annotations

from typing import Any

from lab_messaging.contracts.common import (
    base_message,
    MESSAGE_TYPE_COMMAND,
    CONTRACT_VERSION_1,
    REQUIRED_FIELDS,
)

COMMAND_V1_ALIASES = ("status", "restart_service", "reload_config", "get_metrics", "ping")


def create_message(
    message_id: str,
    timestamp: str,
    alias: str,
    arguments: dict | None = None,
    **extra: Any,
) -> dict:
    """Create a command v1 message dict.

    Extra keyword arguments are included in the payload (permissive).
    """
    payload: dict[str, Any] = {
        "alias": alias,
        "arguments": arguments if arguments is not None else {},
    }
    payload.update(extra)
    return base_message(
        message_type=MESSAGE_TYPE_COMMAND,
        version=CONTRACT_VERSION_1,
        message_id=message_id,
        timestamp=timestamp,
        payload=payload,
    )


def validate(data: dict) -> dict:
    """Permissive validation of a command v1 message.

    Checks:
    - required top-level fields are present
    - version is 1
    - type is "command"
    - payload is a dict with alias (string) and arguments (dict)

    Additional fields are allowed. Returns the validated dict.
    Raises ValueError with a clear message on failure.
    """
    if not isinstance(data, dict):
        raise ValueError("Message must be a JSON object")

    for field in REQUIRED_FIELDS:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    if data["type"] != MESSAGE_TYPE_COMMAND:
        raise ValueError(
            f"Invalid type: expected '{MESSAGE_TYPE_COMMAND}', got '{data['type']}'"
        )

    if data["version"] != CONTRACT_VERSION_1:
        raise ValueError(
            f"Invalid version: expected {CONTRACT_VERSION_1}, got {data['version']}"
        )

    if not isinstance(data["message_id"], str) or not data["message_id"]:
        raise ValueError("message_id must be a non-empty string")

    if not isinstance(data["timestamp"], str) or not data["timestamp"]:
        raise ValueError("timestamp must be a non-empty string")

    payload = data.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")

    if "alias" not in payload:
        raise ValueError("Missing required payload field: alias")

    if not isinstance(payload["alias"], str):
        raise ValueError("payload.alias must be a string")

    if "arguments" not in payload:
        raise ValueError("Missing required payload field: arguments")

    if not isinstance(payload["arguments"], dict):
        raise ValueError("payload.arguments must be an object")

    return data


def serialize(data: dict) -> str:
    """Serialize a command message to JSON string."""
    import json
    return json.dumps(data, ensure_ascii=False)


def deserialize(json_str: str) -> dict:
    """Deserialize a JSON string into a command message dict.

    Raises ValueError on invalid JSON.
    """
    import json

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc