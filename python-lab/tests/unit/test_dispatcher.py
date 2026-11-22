"""Unit tests for command dispatcher routing."""

from __future__ import annotations

import pytest

from lab_messaging.commands.dispatcher import dispatcher


@pytest.fixture(autouse=True)
def reset_dispatcher():
    """Clear dispatcher between tests."""
    dispatcher._handlers.clear()
    yield
    dispatcher._handlers.clear()


def test_register_and_dispatch():
    calls = []

    def handler(arguments):
        calls.append(arguments)
        return {"result": "ok"}

    dispatcher.register("test_cmd", handler)
    result = dispatcher.dispatch("test_cmd", {"key": "val"})

    assert result["status"] == "ok"
    assert result["handler"] == "handler"
    assert calls == [{"key": "val"}]


def test_unknown_alias_returns_error():
    result = dispatcher.dispatch("nonexistent", {})
    assert result["status"] == "error"
    assert "Unknown command alias" in result["error"]


def test_dispatcher_aliases_property():
    def handler1(arguments):
        return {}

    def handler2(arguments):
        return {}

    dispatcher.register("alpha", handler1)
    dispatcher.register("beta", handler2)
    assert "alpha" in dispatcher.aliases
    assert "beta" in dispatcher.aliases


def test_unknown_alias_does_not_raise():
    """Unknown alias must not crash the dispatcher."""
    result = dispatcher.dispatch("does_not_exist", {})
    assert result["status"] == "error"