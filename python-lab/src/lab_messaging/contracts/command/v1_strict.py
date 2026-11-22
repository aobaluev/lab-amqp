"""Command contract v1 — strict validation with Pydantic.

Strict mode: all required fields present, types match, additional fields
are forbidden, and alias must be one of the known command aliases.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from lab_messaging.contracts.common import (
    MESSAGE_TYPE_COMMAND,
    CONTRACT_VERSION_1,
)

COMMAND_V1_ALIASES = ("status", "restart_service", "reload_config", "get_metrics", "ping")


class CommandPayloadV1(BaseModel):
    """Strict payload schema for command v1."""

    alias: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}

    @field_validator("alias")
    @classmethod
    def _validate_alias(cls, v: str) -> str:
        if v not in COMMAND_V1_ALIASES:
            raise ValueError(
                f"Unknown alias '{v}'. Known aliases: {', '.join(COMMAND_V1_ALIASES)}"
            )
        return v


class CommandMessageV1(BaseModel):
    """Strict message schema for command v1."""

    type: Literal[MESSAGE_TYPE_COMMAND]
    version: int = Field(ge=1, le=1)
    message_id: str = Field(min_length=1)
    timestamp: float = Field(ge=0)
    datetime: str = Field(min_length=1)
    payload: CommandPayloadV1

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
    alias: str,
    arguments: dict | None = None,
) -> dict:
    """Create a command v1 message dict (strict, no extra fields)."""
    msg = CommandMessageV1(
        type=MESSAGE_TYPE_COMMAND,
        version=CONTRACT_VERSION_1,
        message_id=message_id,
        timestamp=timestamp,
        datetime=datetime,
        payload={
            "alias": alias,
            "arguments": arguments if arguments is not None else {},
        },
    )
    return msg.model_dump(mode="python")


def validate(data: dict) -> dict:
    """Strict validation of a command v1 message.

    Uses Pydantic to enforce:
    - all required fields present
    - correct types
    - no additional fields
    - alias must be one of known aliases
    - timestamp must be valid ISO-8601

    Returns the validated dict (normalized by Pydantic).
    Raises ValueError with a clear message on failure.
    """
    if not isinstance(data, dict):
        raise ValueError("Message must be a JSON object")

    try:
        validated = CommandMessageV1.model_validate(data)
        return validated.model_dump(mode="python")
    except ValidationError as exc:
        errors = []
        for error in exc.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            errors.append(f"{loc}: {error['msg']}")
        raise ValueError("; ".join(errors)) from exc


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