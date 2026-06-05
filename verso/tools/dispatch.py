# verso/tools/dispatch.py
from __future__ import annotations
import inspect
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from verso.tools.tool import Tool


@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    error: str | None = None


async def dispatch(tool: Tool, arguments: dict[str, Any]) -> ToolResult:
    """Validate args, run the tool, and ALWAYS return a ToolResult — never raise."""
    try:
        validated = tool.args_model(**arguments)
    except ValidationError as e:
        return ToolResult(ok=False, error=f"ValidationError: {e}")
    try:
        result = tool.fn(**validated.model_dump())
        if inspect.isawaitable(result):
            result = await result
        return ToolResult(ok=True, data=result)
    except Exception as e:  # noqa: BLE001 — tool failures are data, not exceptions
        return ToolResult(ok=False, error=f"{type(e).__name__}: {e}")
