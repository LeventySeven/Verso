# verso/tools/dispatch.py
from __future__ import annotations
import inspect
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from verso.durable.context import Paused
from verso.tools.tool import Tool


@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    error: str | None = None


async def dispatch(tool: Tool, arguments: dict[str, Any], ctx: object | None = None) -> ToolResult:
    """Validate args, run the tool (injecting RunContext if it declares `ctx`), and ALWAYS return a
    ToolResult — EXCEPT Paused, which is control flow (a human-in-the-loop pause) and must reach the loop."""
    try:
        validated = tool.args_model(**arguments)
    except ValidationError as e:
        return ToolResult(ok=False, error=f"ValidationError: {e}")
    try:
        kwargs = dict(validated.model_dump())
        if tool.wants_ctx:
            kwargs["ctx"] = ctx
        result = tool.fn(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return ToolResult(ok=True, data=result)
    except Paused:
        raise                              # pause request → loop handles it (durable pause)
    except Exception as e:  # noqa: BLE001 — tool failures are data, not exceptions
        return ToolResult(ok=False, error=f"{type(e).__name__}: {e}")
