# verso/stream/sse.py
from __future__ import annotations
import json
from typing import AsyncIterator

from verso.stream.events import StreamEvent
from verso.types import AgentResult


def _result_dict(r: AgentResult) -> dict:
    return {
        "output": r.output,
        "stop_reason": r.stop_reason.value,
        "steps": r.steps,
        "usage": {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens},
    }


def to_sse(event: StreamEvent) -> str:
    """Serialize one event as an SSE frame: `data: {json}\\n\\n`. Empty/None fields are omitted."""
    payload: dict = {"type": event.type.value}
    for key in ("text", "tool", "arguments", "ok", "content", "step", "error"):
        val = getattr(event, key)
        if val is not None and val != "":
            payload[key] = val
    if event.result is not None:
        payload["result"] = _result_dict(event.result) if isinstance(event.result, AgentResult) else event.result
    return f"data: {json.dumps(payload, default=str)}\n\n"


async def sse(events: AsyncIterator[StreamEvent]) -> AsyncIterator[str]:
    """Wrap an event stream as SSE frames, terminated by `data: [DONE]\\n\\n`."""
    async for ev in events:
        yield to_sse(ev)
    yield "data: [DONE]\n\n"
