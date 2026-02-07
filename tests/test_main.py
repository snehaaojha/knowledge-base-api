"""Tests for main app: exception handlers, _json_safe."""

import json

import pytest

from app.main import _json_safe


def test_json_safe_handles_primitives():
    """_json_safe returns primitives unchanged."""
    assert _json_safe(None) is None
    assert _json_safe("a") == "a"
    assert _json_safe(42) == 42
    assert _json_safe(3.14) == 3.14
    assert _json_safe(True) is True


def test_json_safe_handles_dicts_and_lists():
    """_json_safe recurses into dicts and lists."""
    obj = {"a": 1, "b": [2, {"c": 3}]}
    result = _json_safe(obj)
    assert result == obj
    json.dumps(result)


def test_json_safe_handles_exception():
    """_json_safe converts BaseException to str."""
    result = _json_safe(ValueError("oops"))
    assert result == "oops"
