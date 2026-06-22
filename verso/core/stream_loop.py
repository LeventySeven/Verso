# verso/core/stream_loop.py
from __future__ import annotations
from typing import TYPE_CHECKING, AsyncIterator, Sequence

from verso.context.prune import prune
from verso.core.loop import _format_result, _truncate_tool_output, build_bundle
from verso.core.stuck import StuckThresholds, detect_stuck
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
                     hooks: "Hooks | None" = None, ctx: "RunContext | None" = None,
                     max_tool_retries: int = 2, max_steps_policy: str = "stop",
                     stuck_thresholds: "StuckThresholds | None" = StuckThresholds()) -> AsyncIterator[StreamEvent]:
    from verso.safety.hooks import Hooks, PermissionDecision
    hooks = hooks or Hooks()
    bundle = build_bundle(tools, task, instructions)
    tool_map = {t.name: t for t in tools}
    usage = Usage()
    retries: dict[str, int] = {}
    verify_count = 0   # re-drives spent on on_stop vetoes at natural terminations (END_TURN / DONE)

    for step in range(1, max_steps + 1):
        yield StreamEvent(type=EventType.STEP, step=step)
        if stuck_thresholds is not None and detect_stuck(bundle.history, stuck_thresholds):
            result = AgentResult(
                output=next((m.content for m in reversed(bundle.history) if m.role == "assistant" and m.content), ""),
                stop_reason=StopReason.STUCK, usage=usage, steps=step - 1)
            await hooks.run_on_stop(result, ctx=ctx)
            yield StreamEvent(type=EventType.DONE, result=result)
            return
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
            outcome = await hooks.run_on_stop(result, ctx=ctx)
            if outcome is not None and not outcome.passed and verify_count < hooks.max_verify_retries:
                verify_count += 1
                bundle.history.append(Message(role="user",
                                              content=f"Verification failed: {outcome.detail} Address it and finish."))
                continue   # re-drive instead of terminating; the loop yields more events (run/stream parity)
            yield StreamEvent(type=EventType.DONE, result=result)
            return

        bundle.history.append(Message(role="assistant", content=text, tool_calls=tool_calls))
        reverify = False   # set by a vetoed `done`: finish this turn's tool results, then re-drive
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
                    # mirror _drive's per-tool retry budget: explicit max_attempts wins; else non-idempotent
                    # tools get 0 retries (no auto re-run of a side effect); else the global max_tool_retries.
                    allowed = (t.max_attempts - 1) if t.max_attempts is not None else (
                        max_tool_retries if t.idempotent else 0)
                    retries[tc.name] = retries.get(tc.name, 0) + 1
                    if retries[tc.name] > allowed:
                        content = f"Error: tool '{tc.name}' exceeded its retry budget ({allowed})."
                    else:
                        content = f"Retry: {r.feedback}"
                    ok = False
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
                outcome = await hooks.run_on_stop(result, ctx=ctx)
                if not (outcome is not None and not outcome.passed
                        and verify_count < hooks.max_verify_retries):
                    yield StreamEvent(type=EventType.DONE, result=result)
                    return
                # vetoed DONE under budget: keep the `done` tool result + feedback in history and
                # re-drive (the outer loop yields more events), mirroring _drive's run() behavior.
                verify_count += 1
                reverify = True
                bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))
                done_ids = {m.tool_call_id for m in bundle.history if m.role == "tool"}
                for sib in tool_calls:   # close not-yet-run siblings so the re-driven turn is well-formed
                    if sib.id not in done_ids:
                        bundle.history.append(Message(
                            role="tool", tool_call_id=sib.id, name=sib.name,
                            content=f"Tool '{sib.name}' was not run: the run is re-driving after a failed verification."))
                bundle.history.append(Message(role="user",
                                              content=f"Verification failed: {outcome.detail} Address it and finish."))
                break   # stop processing this turn's tool_calls; the outer loop re-drives
            bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))

        if reverify:
            continue   # re-drive after a vetoed DONE (bounded by max_verify_retries + max_steps)

    output = ""
    if max_steps_policy == "generate":
        grace = await model.complete(bundle.to_messages(), [], system=bundle.system)
        usage = usage + grace.usage
        output = grace.text
        if output:
            yield StreamEvent(type=EventType.MESSAGE_DELTA, text=output)
    result = AgentResult(output=output, stop_reason=StopReason.MAX_STEPS, usage=usage, steps=max_steps)
    await hooks.run_on_stop(result, ctx=ctx)
    yield StreamEvent(type=EventType.DONE, result=result)
