"""Heartbeat contracts."""

from lab_messaging.contracts.heartbeat.v1 import (
    create_message as create_permissive,
    validate as validate_permissive,
    serialize as serialize_permissive,
    deserialize as deserialize_permissive,
)
from lab_messaging.contracts.heartbeat.v1_strict import (
    create_message as create_strict,
    validate as validate_strict,
    serialize as serialize_strict,
    deserialize as deserialize_strict,
)

__all__ = [
    "create_permissive",
    "validate_permissive",
    "serialize_permissive",
    "deserialize_permissive",
    "create_strict",
    "validate_strict",
    "serialize_strict",
    "deserialize_strict",
]