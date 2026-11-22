"""JSON contracts re-export.

Provides a unified interface for selecting validation mode at runtime
without changing business logic.
"""

from typing import Any

from lab_messaging.contracts.heartbeat import (
    create_permissive as heartbeat_create_permissive,
    validate_permissive as heartbeat_validate_permissive,
    serialize_permissive as heartbeat_serialize_permissive,
    deserialize_permissive as heartbeat_deserialize_permissive,
    create_strict as heartbeat_create_strict,
    validate_strict as heartbeat_validate_strict,
    serialize_strict as heartbeat_serialize_strict,
    deserialize_strict as heartbeat_deserialize_strict,
)
from lab_messaging.contracts.command import (
    create_permissive as command_create_permissive,
    validate_permissive as command_validate_permissive,
    serialize_permissive as command_serialize_permissive,
    deserialize_permissive as command_deserialize_permissive,
    create_strict as command_create_strict,
    validate_strict as command_validate_strict,
    serialize_strict as command_serialize_strict,
    deserialize_strict as command_deserialize_strict,
)

VALIDATION_MODES = ("permissive", "strict")


def get_heartbeat_module(mode: str = "permissive"):
    """Return the heartbeat contract module for the given validation mode."""
    if mode == "strict":
        return _StrictModule(
            create=heartbeat_create_strict,
            validate=heartbeat_validate_strict,
            serialize=heartbeat_serialize_strict,
            deserialize=heartbeat_deserialize_strict,
        )
    return _StrictModule(
        create=heartbeat_create_permissive,
        validate=heartbeat_validate_permissive,
        serialize=heartbeat_serialize_permissive,
        deserialize=heartbeat_deserialize_permissive,
    )


def get_command_module(mode: str = "permissive"):
    """Return the command contract module for the given validation mode."""
    if mode == "strict":
        return _StrictModule(
            create=command_create_strict,
            validate=command_validate_strict,
            serialize=command_serialize_strict,
            deserialize=command_deserialize_strict,
        )
    return _StrictModule(
        create=command_create_permissive,
        validate=command_validate_permissive,
        serialize=command_serialize_permissive,
        deserialize=command_deserialize_permissive,
    )


class _StrictModule:
    """Wrapper providing a consistent interface for both validation modes."""

    def __init__(
        self,
        create,
        validate,
        serialize,
        deserialize,
    ) -> None:
        self.create = create
        self.validate = validate
        self.serialize = serialize
        self.deserialize = deserialize

    def make_heartbeat(self, **kwargs: Any) -> dict:
        return self.create(**kwargs)

    def make_command(self, **kwargs: Any) -> dict:
        return self.create(**kwargs)


__all__ = [
    "VALIDATION_MODES",
    "get_heartbeat_module",
    "get_command_module",
]