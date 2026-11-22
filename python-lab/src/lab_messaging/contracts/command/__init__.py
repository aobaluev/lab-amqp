"""Command contracts."""

from lab_messaging.contracts.command.v1 import (
    COMMAND_V1_ALIASES,
    create_message as create_permissive,
    validate as validate_permissive,
    serialize as serialize_permissive,
    deserialize as deserialize_permissive,
)
from lab_messaging.contracts.command.v1_strict import (
    create_message as create_strict,
    validate as validate_strict,
    serialize as serialize_strict,
    deserialize as deserialize_strict,
)

__all__ = [
    "COMMAND_V1_ALIASES",
    "create_permissive",
    "validate_permissive",
    "serialize_permissive",
    "deserialize_permissive",
    "create_strict",
    "validate_strict",
    "serialize_strict",
    "deserialize_strict",
]