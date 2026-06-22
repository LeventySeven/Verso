# tests/test_tool_timeout.py
import asyncio

from verso.tools.dispatch import dispatch
from verso.tools.tool import tool


async def test_async_tool_timeout_returns_error_result_not_a_hang():
    @tool(timeout_seconds=0.01)
    async def slow(ctx) -> str:
        "Sleeps past its budget."
        await asyncio.sleep(5)
        return "done"
    res = await dispatch(slow, {}, ctx=None)
    assert res.ok is False and "timed out" in res.error      # error-as-result, never raised into the loop


async def test_fast_async_tool_within_timeout_is_fine():
    @tool(timeout_seconds=1.0)
    async def quick(ctx) -> str:
        "Returns immediately."
        return "ok"
    res = await dispatch(quick, {}, ctx=None)
    assert res.ok and res.data == "ok"


async def test_no_timeout_set_is_byte_identical():
    @tool
    async def t(ctx) -> str:
        "No timeout configured."
        return "ok"
    res = await dispatch(t, {}, ctx=None)
    assert res.ok and res.data == "ok"
