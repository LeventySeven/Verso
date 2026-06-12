# verso/durable/serde.py
from __future__ import annotations

from verso.model.base import Message, ToolCall


def msg_to_dict(m: Message) -> dict:
    return {
        "role": m.role,
        "content": m.content,
        "tool_calls": [{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in m.tool_calls],
        "tool_call_id": m.tool_call_id,
        "name": m.name,
    }


def msg_from_dict(d: dict) -> Message:
    return Message(
        role=d["role"],
        content=d.get("content", ""),
        tool_calls=[ToolCall(id=tc["id"], name=tc["name"], arguments=tc["arguments"]) for tc in d.get("tool_calls", [])],
        tool_call_id=d.get("tool_call_id"),
        name=d.get("name"),
    )
