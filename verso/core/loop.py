# verso/core/loop.py
from __future__ import annotations
import json
from typing import Sequence

from verso.model.base import Message, Model
from verso.tools.dispatch import dispatch
from verso.tools.tool import Tool
from verso.types import AgentResult, StopReason, Usage


def _format_result(data) -> str:
    if isinstance(data, str):
        return data
    try:
        return json.dumps(data)
    except (TypeError, ValueError):
        return str(data)


async def run_loop(model: Model, tools: Sequence[Tool], task: str,
                   max_steps: int = 25, instructions: str | None = None) -> AgentResult:
    messages: list[Message] = []
    if instructions:
        messages.append(Message(role="user", content=instructions))
    messages.append(Message(role="user", content=task))
    tool_map = {t.name: t for t in tools}
    usage = Usage()

    for step in range(1, max_steps + 1):
        resp = await model.complete(messages, list(tools))
        usage = usage + resp.usage

        if not resp.tool_calls:
            return AgentResult(output=resp.text, stop_reason=StopReason.END_TURN,
                               usage=usage, steps=step)

        messages.append(Message(role="assistant", content=resp.text, tool_calls=resp.tool_calls))
        for tc in resp.tool_calls:
            t = tool_map.get(tc.name)
            if t is None:
                content = f"Error: unknown tool '{tc.name}'."
            else:
                result = await dispatch(t, tc.arguments)
                content = _format_result(result.data) if result.ok else f"Error: {result.error}"
                if tc.name == "done" and result.ok:
                    return AgentResult(output=_format_result(result.data),
                                       stop_reason=StopReason.DONE, usage=usage, steps=step)
            messages.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))

    return AgentResult(output="", stop_reason=StopReason.MAX_STEPS, usage=usage, steps=max_steps)
