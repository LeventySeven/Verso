# verso/core/stream_loop.py
from __future__ import annotations
from typing import TYPE_CHECKING, AsyncIterator, Sequence

from verso.context.prune import prune
from verso.core.loop import _format_result, _truncate_tool_output, build_bundle
from verso.durable.context import Paused
from verso.model.base import Message, Model, ModelResponse
from verso.model.streaming import iter_model_stream
from verso.stream.events import EventType, StreamEvent
from verso.tools.dispatch import dispatch
from verso.tools.errors import Retry
from verso.tools.tool import Tool
from verso.types import AgentResult, StopReason, Usage

if TYPE_CHECKING:
    from verso.durable.context import RunContext
    from verso.safety.hooks import Hooks


async def run_stream(model: Model, tools: Sequence[Tool], task: str,
                     max_steps: int = 25, instructions: str | None = None,
                     max_context_tokens: int | None = None,
                     hooks: "Hooks | None" = None, ctx: "RunContext | None" = None) -> AsyncIterator[StreamEvent]:
    from verso.safety.hooks import Hooks, PermissionDecision
    hooks = hooks or Hooks()
    bundle = build_bundle(tools, task, instructions)
    tool_map = {t.name: t for t in tools}
    usage = Usage()

    for step in range(1, max_steps + 1):
        yield StreamEvent(type=EventType.STEP, step=step)
        if max_context_tokens is not None and bundle.estimate_tokens() > max_context_tokens:
            bundle.history = prune(bundle.history)

        await hooks.run_pre_model(bundle, ctx=ctx)
        text_parts: list[str] = []
        tool_calls = []
        turn_usage = Usage()
        async for chunk in iter_model_stream(model, bundle.to_messages(), bundle.tools, system=bundle.system):
            if chunk.kind == "text":
                text_parts.append(chunk.text)
                yield StreamEvent(type=EventType.MESSAGE_DELTA, text=chunk.text)
            elif chunk.kind == "reasoning":
                yield StreamEvent(type=EventType.REASONING_DELTA, text=chunk.text)
            elif chunk.kind == "tool_call" and chunk.tool_call is not None:
                tool_calls.append(chunk.tool_call)
            elif chunk.kind == "usage" and chunk.usage is not None:
                turn_usage = turn_usage + chunk.usage
                usage = usage + chunk.usage

        text = "".join(text_parts)
        resp = ModelResponse(text=text, tool_calls=tool_calls, usage=turn_usage)
        if ctx is not None:
            ctx.step, ctx.usage, ctx.messages = step, usage, bundle.history
        await hooks.run_post_model(resp, ctx=ctx)
        if not tool_calls:
            result = AgentResult(output=text, stop_reason=StopReason.END_TURN, usage=usage, steps=step)
            await hooks.run_on_stop(result, ctx=ctx)
            yield StreamEvent(type=EventType.DONE, result=result)
            return

        bundle.history.append(Message(role="assistant", content=text, tool_calls=tool_calls))
        for tc in tool_calls:
            yield StreamEvent(type=EventType.TOOL_START, tool=tc.name, arguments=tc.arguments)
            decision = await hooks.run_pre_tool((tc.name, tc.arguments), ctx=ctx)
            if decision != PermissionDecision.ALLOW:
                if decision == PermissionDecision.ASK and hooks.ask is not None and hooks.ask((tc.name, tc.arguments)):
                    pass  # sync-approved → fall through to run
                elif decision == PermissionDecision.ASK:
                    # On run() an ASK gate routes to a durable pause (when a checkpointer exists); the stream
                    # path has no durable pause (store=None by construction), so be honest + distinct rather
                    # than mislabelling it "ask by policy". Streaming durable HITL is a later seam.
                    content = (f"Tool '{tc.name}' requested human approval (ASK) but streaming HITL is not "
                               "available; it did not run.")
                    content = await hooks.run_post_tool((tc.name, tc.arguments), content, ctx=ctx)
                    yield StreamEvent(type=EventType.TOOL_RESULT, tool=tc.name, ok=False, content=content)
                    bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))
                    continue
                else:
                    content = f"Tool '{tc.name}' was {getattr(decision, 'value', decision)} by policy; it did not run."
                    content = await hooks.run_post_tool((tc.name, tc.arguments), content, ctx=ctx)
                    yield StreamEvent(type=EventType.TOOL_RESULT, tool=tc.name, ok=False, content=content)
                    bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))
                    continue
            t = tool_map.get(tc.name)
            if t is None:
                content, ok = f"Error: unknown tool '{tc.name}'.", False
            else:
                # mirror _drive's TACTICAL dispatch handling: the stream is store=None by construction, so a
                # tool that raises Retry (self-healing) or calls ctx.hitl.request (raises Paused) must NOT
                # escape the async generator — convert each to model-visible feedback exactly like _drive.
                try:
                    res = await dispatch(t, tc.arguments, ctx=ctx)
                except Retry as r:
                    content, ok = f"Retry: {r.feedback}", False
                except Paused:
                    content = (f"Tool '{tc.name}' requested human input but this run is not durable; "
                               "it did not pause.")
                    ok = False
                else:
                    content = _format_result(res.data) if res.ok else f"Error: {res.error}"
                    ok = res.ok
            content = await hooks.run_post_tool((tc.name, tc.arguments), content, ctx=ctx)
            if ctx is not None and ctx.tool_output_budget:
                content = _truncate_tool_output(content, ctx.tool_output_budget)
            yield StreamEvent(type=EventType.TOOL_RESULT, tool=tc.name, ok=ok, content=content)
            if tc.name == "done" and ok:
                result = AgentResult(output=content, stop_reason=StopReason.DONE, usage=usage, steps=step)
                await hooks.run_on_stop(result, ctx=ctx)
                yield StreamEvent(type=EventType.DONE, result=result)
                return
            bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))

    result = AgentResult(output="", stop_reason=StopReason.MAX_STEPS, usage=usage, steps=max_steps)
    await hooks.run_on_stop(result, ctx=ctx)
    yield StreamEvent(type=EventType.DONE, result=result)
