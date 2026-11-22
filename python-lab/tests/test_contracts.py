"""Unit tests for JSON contracts: creation, serialization, validation."""

from __future__ import annotations

import json
import uuid

import pytest

from lab_messaging.contracts import (
    VALIDATION_MODES,
    get_command_module,
    get_heartbeat_module,
)
from lab_messaging.contracts.command import COMMAND_V1_ALIASES


def _make_message_id() -> str:
    return str(uuid.uuid4())


def _make_timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TestHeartbeatV1Creation:
    def test_create_heartbeat_permissive(self):
        mod = get_heartbeat_module("permissive")
        msg = mod.make_heartbeat(
            message_id=_make_message_id(),
            timestamp=_make_timestamp(),
            hostname="test-host",
            cpu_load=0.5,
            memory_used_percent=60.0,
            uptime_seconds=3600.0,
        )
        assert msg["type"] == "heartbeat"
        assert msg["version"] == 1
        assert msg["payload"]["hostname"] == "test-host"

    def test_create_heartbeat_strict(self):
        mod = get_heartbeat_module("strict")
        msg = mod.make_heartbeat(
            message_id=_make_message_id(),
            timestamp=_make_timestamp(),
            hostname="test-host",
            cpu_load=0.5,
            memory_used_percent=60.0,
            uptime_seconds=3600.0,
        )
        assert msg["type"] == "heartbeat"
        assert msg["version"] == 1

    def test_create_command_permissive(self):
        mod = get_command_module("permissive")
        msg = mod.make_command(
            message_id=_make_message_id(),
            timestamp=_make_timestamp(),
            alias="status",
            arguments={},
        )
        assert msg["type"] == "command"
        assert msg["version"] == 1
        assert msg["payload"]["alias"] == "status"

    def test_create_command_strict(self):
        mod = get_command_module("strict")
        msg = mod.make_command(
            message_id=_make_message_id(),
            timestamp=_make_timestamp(),
            alias="ping",
            arguments={},
        )
        assert msg["type"] == "command"
        assert msg["version"] == 1


class TestSerialization:
    def test_heartbeat_serialize_deserialize_roundtrip(self):
        mod = get_heartbeat_module("permissive")
        msg = mod.make_heartbeat(
            message_id=_make_message_id(),
            timestamp=_make_timestamp(),
            hostname="host",
            cpu_load=0.3,
            memory_used_percent=50.0,
            uptime_seconds=100.0,
        )
        json_str = mod.serialize(msg)
        parsed = json.loads(json_str)
        assert parsed == msg

    def test_command_serialize_deserialize_roundtrip(self):
        mod = get_command_module("permissive")
        msg = mod.make_command(
            message_id=_make_message_id(),
            timestamp=_make_timestamp(),
            alias="get_metrics",
            arguments={"key": "value"},
        )
        json_str = mod.serialize(msg)
        parsed = json.loads(json_str)
        assert parsed == msg

    def test_deserialize_invalid_json_raises(self):
        mod = get_heartbeat_module("permissive")
        with pytest.raises(ValueError, match="Invalid JSON"):
            mod.deserialize("{not valid json}")


class TestPermissiveValidation:
    def test_valid_message_passes(self):
        mod = get_heartbeat_module("permissive")
        msg = mod.make_heartbeat(
            message_id=_make_message_id(),
            timestamp=_make_timestamp(),
            hostname="host",
            cpu_load=0.5,
            memory_used_percent=60.0,
            uptime_seconds=3600.0,
        )
        result = mod.validate(msg)
        assert result == msg

    def test_extra_field_allowed_permissive(self):
        mod = get_heartbeat_module("permissive")
        msg = mod.make_heartbeat(
            message_id=_make_message_id(),
            timestamp=_make_timestamp(),
            hostname="host",
            cpu_load=0.5,
            memory_used_percent=60.0,
            uptime_seconds=3600.0,
        )
        msg["payload"]["custom_field"] = "extra info"
        # Should not raise
        result = mod.validate(msg)
        assert result["payload"]["custom_field"] == "extra info"

    def test_missing_required_field_raises(self):
        mod = get_heartbeat_module("permissive")
        msg = mod.make_heartbeat(
            message_id=_make_message_id(),
            timestamp=_make_timestamp(),
            hostname="host",
            cpu_load=0.5,
            memory_used_percent=60.0,
            uptime_seconds=3600.0,
        )
        del msg["payload"]["cpu_load"]
        with pytest.raises(ValueError, match="cpu_load"):
            mod.validate(msg)

    def test_wrong_type_raises(self):
        mod = get_heartbeat_module("permissive")
        msg = mod.make_heartbeat(
            message_id=_make_message_id(),
            timestamp=_make_timestamp(),
            hostname="host",
            cpu_load=0.5,
            memory_used_percent=60.0,
            uptime_seconds=3600.0,
        )
        msg["payload"]["hostname"] = 123
        with pytest.raises(ValueError, match="hostname"):
            mod.validate(msg)

    def test_unknown_type_raises(self):
        mod = get_heartbeat_module("permissive")
        msg = mod.make_heartbeat(
            message_id=_make_message_id(),
            timestamp=_make_timestamp(),
            hostname="host",
            cpu_load=0.5,
            memory_used_percent=60.0,
            uptime_seconds=3600.0,
        )
        msg["type"] = "unknown"
        with pytest.raises(ValueError, match="Invalid type"):
            mod.validate(msg)

    def test_unknown_version_raises(self):
        mod = get_heartbeat_module("permissive")
        msg = mod.make_heartbeat(
            message_id=_make_message_id(),
            timestamp=_make_timestamp(),
            hostname="host",
            cpu_load=0.5,
            memory_used_percent=60.0,
            uptime_seconds=3600.0,
        )
        msg["version"] = 99
        with pytest.raises(ValueError, match="Invalid version"):
            mod.validate(msg)


class TestStrictValidation:
    def test_valid_message_passes(self):
        mod = get_heartbeat_module("strict")
        msg = mod.make_heartbeat(
            message_id=_make_message_id(),
            timestamp=_make_timestamp(),
            hostname="host",
            cpu_load=0.5,
            memory_used_percent=60.0,
            uptime_seconds=3600.0,
        )
        result = mod.validate(msg)
        assert result == msg

    def test_extra_field_forbidden_strict(self):
        mod = get_heartbeat_module("strict")
        msg = mod.make_heartbeat(
            message_id=_make_message_id(),
            timestamp=_make_timestamp(),
            hostname="host",
            cpu_load=0.5,
            memory_used_percent=60.0,
            uptime_seconds=3600.0,
        )
        msg["payload"]["custom_field"] = "extra info"
        with pytest.raises(ValueError):
            mod.validate(msg)

    def test_out_of_range_value_raises_strict(self):
        mod = get_heartbeat_module("strict")
        msg = mod.make_heartbeat(
            message_id=_make_message_id(),
            timestamp=_make_timestamp(),
            hostname="host",
            cpu_load=1.5,  # > 1.0, out of range
            memory_used_percent=60.0,
            uptime_seconds=3600.0,
        )
        with pytest.raises(ValueError):
            mod.validate(msg)

    def test_unknown_alias_raises_strict_command(self):
        mod = get_command_module("strict")
        msg = mod.make_command(
            message_id=_make_message_id(),
            timestamp=_make_timestamp(),
            alias="nonexistent",
            arguments={},
        )
        with pytest.raises(ValueError, match="Unknown alias"):
            mod.validate(msg)


class TestValidationModes:
    def test_permissive_allows_extra_field(self):
        perm = get_heartbeat_module("permissive")
        strict = get_heartbeat_module("strict")

        msg = perm.make_heartbeat(
            message_id=_make_message_id(),
            timestamp=_make_timestamp(),
            hostname="host",
            cpu_load=0.5,
            memory_used_percent=60.0,
            uptime_seconds=3600.0,
        )
        msg["payload"]["extra"] = "allowed"

        # Permissive accepts
        perm.validate(msg)  # should not raise

        # Strict rejects
        with pytest.raises(ValueError):
            strict.validate(msg)

    def test_all_validation_modes_available(self):
        assert "permissive" in VALIDATION_MODES
        assert "strict" in VALIDATION_MODES


class TestCommandAliases:
    def test_all_aliases_defined(self):
        assert "status" in COMMAND_V1_ALIASES
        assert "restart_service" in COMMAND_V1_ALIASES
        assert "reload_config" in COMMAND_V1_ALIASES
        assert "get_metrics" in COMMAND_V1_ALIASES
        assert "ping" in COMMAND_V1_ALIASES
        assert len(COMMAND_V1_ALIASES) == 5