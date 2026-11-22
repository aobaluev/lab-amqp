"""Heartbeat contract v1 — strict validation with Pydantic.

Strict mode: all required fields present, types match, additional fields
are forbidden, and values must satisfy extra constraints.
"""

from __future__ import annotations

from typing import Any

from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from lab_messaging.contracts.common import (
    MESSAGE_TYPE_HEARTBEAT,
    CONTRACT_VERSION_1,
)

HEARTBEAT_V1_PAYLOAD_FIELDS = ("hostname", "cpu_load", "memory_used_percent", "uptime_seconds")


class HeartbeatPayloadV1(BaseModel):
    """Strict payload schema for heartbeat v1."""

    hostname: str = Field(min_length=1)
    cpu_load: float = Field(ge=0.0, le=1.0)
    memory_used_percent: float = Field(ge=0.0, le=100.0)
    uptime_seconds: float = Field(ge=0.0)

    model_config = {"extra": "forbid"}


class HeartbeatMessageV1(BaseModel):
    """Strict message schema for heartbeat v1."""

    type: Literal[MESSAGE_TYPE_HEARTBEAT]
    version: int = Field(ge=1, le=1)
    message_id: str = Field(min_length=1)
    timestamp: float = Field(ge=0)
    datetime: str = Field(min_length=1)
    payload: HeartbeatPayloadV1

    model_config = {"extra": "forbid"}

    @field_validator("datetime")
    @classmethod
    def _validate_datetime(cls, v: str) -> str:
        from datetime import datetime

        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("datetime must be a valid ISO-8601 datetime")
        return v


def create_message(
    message_id: str,
    timestamp: float,
    datetime: str,
    hostname: str,
    cpu_load: float,
    memory_used_percent: float,
    uptime_seconds: float,
) -> dict:
    """Create a heartbeat v1 message dict (strict, no extra fields)."""
    msg = HeartbeatMessageV1(
        type=MESSAGE_TYPE_HEARTBEAT,
        version=CONTRACT_VERSION_1,
        message_id=message_id,
        timestamp=timestamp,
        datetime=datetime,
        payload={
            "hostname": hostname,
            "cpu_load": cpu_load,
            "memory_used_percent": memory_used_percent,
            "uptime_seconds": uptime_seconds,
        },
    )
    return msg.model_dump(mode="python")


def validate(data: dict) -> dict:
    """Strict validation of a heartbeat v1 message.

    Uses Pydantic to enforce:
    - all required fields present
    - correct types
    - no additional fields
    - value constraints (ranges, formats)

    Returns the validated dict (normalized by Pydantic).
    Raises ValueError with a clear message on failure.
    """
    if not isinstance(data, dict):
        raise ValueError("Message must be a JSON object")

    try:
        validated = HeartbeatMessageV1.model_validate(data)
        return validated.model_dump(mode="python")
    except ValidationError as exc:
        errors = []
        for error in exc.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            errors.append(f"{loc}: {error['msg']}")
        raise ValueError("; ".join(errors)) from exc


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