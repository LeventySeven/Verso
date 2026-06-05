# tests/test_dispatch.py
import pytest
from verso.tools.tool import tool
from verso.tools.dispatch import dispatch, ToolResult


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


@tool
async def aadd(a: int, b: int) -> int:
    "Async add."
    return a + b


@tool
def boom(x: int) -> int:
    "Always raises."
    raise ValueError("nope")


async def test_dispatch_sync_tool():
    res = await dispatch(add, {"a": 2, "b": 3})
    assert res == ToolResult(ok=True, data=5, error=None)


async def test_dispatch_async_tool():
    res = await dispatch(aadd, {"a": 4, "b": 1})
    assert res.ok and res.data == 5


async def test_dispatch_catches_exceptions():
    res = await dispatch(boom, {"x": 1})
    assert res.ok is False
    assert "ValueError" in res.error
    assert "nope" in res.error


async def test_dispatch_validation_error_is_returned_not_raised():
    res = await dispatch(add, {"a": "not-an-int", "b": 3})
    assert res.ok is False
    assert "validation" in res.error.lower() or "int" in res.error.lower()
