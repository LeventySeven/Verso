# verso/core/loop.py
from __future__ import annotations
import json
from typing import Sequence

from verso.context.bundle import ContextBundle
from verso.context.prune import prune
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


def build_bundle(tools: Sequence[Tool], task: str, instructions: str | None) -> ContextBundle:
    return ContextBundle(instructions=instructions,
                         history=[Message(role="user", content=task)],
                         tools=list(tools))


async def run_loop(model: Model, tools: Sequence[Tool], task: str,
                   max_steps: int = 25, instructions: str | None = None,
                   max_context_tokens: int | None = None) -> AgentResult:
    bundle = build_bundle(tools, task, instructions)
    tool_map = {t.name: t for t in tools}
    usage = Usage()

    for step in range(1, max_steps + 1):
        if max_context_tokens is not None and bundle.estimate_tokens() > max_context_tokens:
            bundle.history = prune(bundle.history)

        resp = await model.complete(bundle.to_messages(), bundle.tools, system=bundle.system)
        usage = usage + resp.usage

        if not resp.tool_calls:
            return AgentResult(output=resp.text, stop_reason=StopReason.END_TURN,
                               usage=usage, steps=step)

        bundle.history.append(Message(role="assistant", content=resp.text, tool_calls=resp.tool_calls))
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
            bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))

    return AgentResult(output="", stop_reason=StopReason.MAX_STEPS, usage=usage, steps=max_steps)
