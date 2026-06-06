# verso/core/stream_loop.py
from __future__ import annotations
from typing import AsyncIterator, Sequence

from verso.context.prune import prune
from verso.core.loop import _format_result, build_bundle
from verso.model.base import Message, Model
from verso.model.streaming import iter_model_stream
from verso.stream.events import EventType, StreamEvent
from verso.tools.dispatch import dispatch
from verso.tools.tool import Tool
from verso.types import AgentResult, StopReason, Usage


async def run_stream(model: Model, tools: Sequence[Tool], task: str,
                     max_steps: int = 25, instructions: str | None = None,
                     max_context_tokens: int | None = None) -> AsyncIterator[StreamEvent]:
    bundle = build_bundle(tools, task, instructions)
    tool_map = {t.name: t for t in tools}
    usage = Usage()

    for step in range(1, max_steps + 1):
        yield StreamEvent(type=EventType.STEP, step=step)
        if max_context_tokens is not None and bundle.estimate_tokens() > max_context_tokens:
            bundle.history = prune(bundle.history)

        text_parts: list[str] = []
        tool_calls = []
        async for chunk in iter_model_stream(model, bundle.to_messages(), bundle.tools, system=bundle.system):
            if chunk.kind == "text":
                text_parts.append(chunk.text)
                yield StreamEvent(type=EventType.MESSAGE_DELTA, text=chunk.text)
            elif chunk.kind == "reasoning":
                yield StreamEvent(type=EventType.REASONING_DELTA, text=chunk.text)
            elif chunk.kind == "tool_call" and chunk.tool_call is not None:
                tool_calls.append(chunk.tool_call)
            elif chunk.kind == "usage" and chunk.usage is not None:
                usage = usage + chunk.usage

        text = "".join(text_parts)
        if not tool_calls:
            yield StreamEvent(type=EventType.DONE, result=AgentResult(
                output=text, stop_reason=StopReason.END_TURN, usage=usage, steps=step))
            return

        bundle.history.append(Message(role="assistant", content=text, tool_calls=tool_calls))
        for tc in tool_calls:
            yield StreamEvent(type=EventType.TOOL_START, tool=tc.name, arguments=tc.arguments)
            t = tool_map.get(tc.name)
            if t is None:
                content, ok = f"Error: unknown tool '{tc.name}'.", False
            else:
                res = await dispatch(t, tc.arguments)
                content = _format_result(res.data) if res.ok else f"Error: {res.error}"
                ok = res.ok
            yield StreamEvent(type=EventType.TOOL_RESULT, tool=tc.name, ok=ok, content=content)
            if tc.name == "done" and ok:
                yield StreamEvent(type=EventType.DONE, result=AgentResult(
                    output=content, stop_reason=StopReason.DONE, usage=usage, steps=step))
                return
            bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))

    yield StreamEvent(type=EventType.DONE, result=AgentResult(
        output="", stop_reason=StopReason.MAX_STEPS, usage=usage, steps=max_steps))
