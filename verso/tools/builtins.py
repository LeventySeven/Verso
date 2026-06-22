# verso/tools/builtins.py
from __future__ import annotations
from typing import Literal

from pydantic import BaseModel

from verso.tools.tool import tool


@tool
def think(thought: str) -> str:
    """Record a private reasoning step before acting. Use this to plan; it has no side effects."""
    return "noted"


@tool
def done(result: str) -> str:
    """Signal that the task is complete and return the final result to the user."""
    return result


class TodoItem(BaseModel):
    content: str
    status: Literal["pending", "in_progress", "completed"] = "pending"


_MARK = {"pending": "[ ]", "in_progress": "[~]", "completed": "[x]"}


@tool
def todo(items: list[TodoItem]) -> str:
    """Record or update your task plan as a status-marked checklist (statuses: pending / in_progress /
    completed). Lay out the steps you intend to take, then call it again to update them as you go —
    mark a step in_progress before starting it and completed the moment it's done, one at a time. It
    echoes the rendered plan back so the plan stays in view. No side effects."""
    # dispatch validates against list[TodoItem] then model_dump()s, so `items` arrives as dicts;
    # tolerate a TodoItem instance too (a direct .fn() call) so the tool is usable either way.
    if not items:
        return "(no items)"
    lines = []
    for it in items:
        d = it if isinstance(it, dict) else it.model_dump()
        lines.append(f"{_MARK.get(d.get('status', 'pending'), '[ ]')} {d.get('content', '')}")
    return "\n".join(lines)
