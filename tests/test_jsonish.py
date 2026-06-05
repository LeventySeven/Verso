# tests/test_jsonish.py
import pytest
from verso.tools.jsonish import parse, JsonishError


def test_strict_json():
    assert parse('{"a": 1, "b": 2}') == {"a": 1, "b": 2}


def test_json_array():
    assert parse("[1, 2, 3]") == [1, 2, 3]


def test_fenced_json_block():
    text = "Here you go:\n```json\n{\"a\": 1}\n```\nHope that helps!"
    assert parse(text) == {"a": 1}


def test_json_embedded_in_prose():
    text = 'Sure! The result is {"a": 1, "b": 2}. Let me know if you need more.'
    assert parse(text) == {"a": 1, "b": 2}


def test_trailing_comma_is_fixed():
    assert parse('{"a": 1, "b": 2,}') == {"a": 1, "b": 2}


def test_python_literals_normalized():
    assert parse('{"ok": True, "bad": False, "x": None}') == {"ok": True, "bad": False, "x": None}


def test_nested_braces_balanced_extraction():
    text = 'prefix {"a": {"b": [1, 2]}, "c": 3} suffix'
    assert parse(text) == {"a": {"b": [1, 2]}, "c": 3}


def test_unparseable_raises():
    with pytest.raises(JsonishError):
        parse("there is absolutely no json here")


def test_non_string_raises():
    with pytest.raises(JsonishError):
        parse(123)  # type: ignore[arg-type]
