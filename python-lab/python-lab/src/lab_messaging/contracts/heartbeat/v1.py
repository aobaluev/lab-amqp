"""Heartbeat contract v1 — permissive validation.

Permissive mode: required fields must be present and have correct types,
but additional fields are allowed without error.
"""

from __future__ import annotations

from typing import Any

from lab_messaging.contracts.common import (
    base_message,
    MESSAGE_TYPE_HEARTBEAT,
    CONTRACT_VERSION_1,
    REQUIRED_FIELDS,
)

HEARTBEAT_V1_PAYLOAD_FIELDS = ("hostname", "cpu_load", "memory_used_percent", "uptime_seconds")


def create_message(
    message_id: str,
    timestamp: str,
    hostname: str,
    cpu_load: float,
    memory_used_percent: float,
    uptime_seconds: float,
    **extra: Any,
) -> dict:
    """Create a heartbeat v1 message dict.

    Extra keyword arguments are included in the payload (permissive).
    """
    payload: dict[str, Any] = {
        "hostname": hostname,
        "cpu_load": cpu_load,
        "memory_used_percent": memory_used_percent,
        "uptime_seconds": uptime_seconds,
    }
    payload.update(extra)
    return base_message(
        message_type=MESSAGE_TYPE_HEARTBEAT,
        version=CONTRACT_VERSION_1,
        message_id=message_id,
        timestamp=timestamp,
        payload=payload,
    )


def validate(data: dict) -> dict:
    """Permissive validation of a heartbeat v1 message.

    Checks:
    - required top-level fields are present
    - version is 1
    - type is "heartbeat"
    - payload is a dict with required payload fields of correct types

    Additional fields are allowed. Returns the validated dict.
    Raises ValueError with a clear message on failure.
    """
    if not isinstance(data, dict):
        raise ValueError("Message must be a JSON object")

    for field in REQUIRED_FIELDS:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    if data["type"] != MESSAGE_TYPE_HEARTBEAT:
        raise ValueError(
            f"Invalid type: expected '{MESSAGE_TYPE_HEARTBEAT}', got '{data['type']}'"
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

    for field in HEARTBEAT_V1_PAYLOAD_FIELDS:
        if field not in payload:
            raise ValueError(f"Missing required payload field: {field}")

    if not isinstance(payload["hostname"], str):
        raise ValueError("payload.hostname must be a string")
    if not isinstance(payload["cpu_load"], (int, float)):
        raise ValueError("payload.cpu_load must be a number")
    if not isinstance(payload["memory_used_percent"], (int, float)):
        raise ValueError("payload.memory_used_percent must be a number")
    if not isinstance(payload["uptime_seconds"], (int, float)):
        raise ValueError("payload.uptime_seconds must be a number")

    return data


def serialize(data: dict) -> str:
    """Serialize a heartbeat message to JSON string."""
    import json
    return json.dumps(data, ensure_ascii=False)


def deserialize(json_str: str) -> dict:
    """Deserialize a JSON string into a heartbeat message dict.

    Raises ValueError on invalid JSON.
    """
    import json

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc