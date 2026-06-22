# verso/core/loop.py
from __future__ import annotations
import json
from typing import TYPE_CHECKING, Sequence

from verso.context.bundle import ContextBundle
from verso.context.history import repair_history
from verso.context.prune import prune
from verso.core.stuck import StuckThresholds, detect_stuck
from verso.durable.checkpoint import Checkpoint
from verso.durable.context import HumanRequest, Paused, RunContext  # noqa: F401  (RunContext used by callers/annotations)
from verso.durable.serde import msg_from_dict, msg_to_dict
from verso.model.base import Message, Model
from verso.tools.dispatch import dispatch
from verso.tools.errors import Retry
from verso.tools.tool import Tool
from verso.types import AgentResult, StopReason, Usage

if TYPE_CHECKING:
    from verso.safety.hooks import Hooks


def _format_result(data) -> str:
    if isinstance(data, str):
        return data
    try:
        return json.dumps(data)
    except (TypeError, ValueError):
        return str(data)


def _truncate_tool_output(s: str, budget: int) -> str:
    if budget <= 0 or len(s) <= budget:
        return s
    half = budget // 2
    return f"{s[:half]}\n...[truncated {len(s) - budget} chars]...\n{s[-half:]}"


def build_bundle(tools: Sequence[Tool], task: str, instructions: str | None) -> ContextBundle:
    return ContextBundle(instructions=instructions,
                         history=[Message(role="user", content=task)],
                         tools=list(tools))


def _checkpoint(ctx, bundle, task, usage, step, pending=None):
    if ctx is None or ctx.store is None:
        return
    ctx.store.save(Checkpoint(
        trace_id=ctx.trace_id, task=task, instructions=bundle.instructions,
        history=[msg_to_dict(m) for m in bundle.history],
        usage_in=usage.input_tokens, usage_out=usage.output_tokens, step=step, pending=pending,
    ))


async def _pause(ctx, bundle, task, usage, step, hooks, resp, tc, request) -> AgentResult:
    request.tool_name = request.tool_name or tc.name
    request.tool_call_id = request.tool_call_id or tc.id
    # keep the checkpoint well-formed: unprocessed sibling tool_calls won't run before resume
    done_ids = {m.tool_call_id for m in bundle.history if m.role == "tool"}
    for sib in resp.tool_calls:
        if sib.id != tc.id and sib.id not in done_ids:
            bundle.history.append(Message(
                role="tool", tool_call_id=sib.id, name=sib.name,
                content=f"Tool '{sib.name}' was deferred pending human approval of '{tc.name}'."))
    _checkpoint(ctx, bundle, task, usage, step, pending=request)
    paused = AgentResult(output="", stop_reason=StopReason.PAUSED, usage=usage, steps=step,
                         resume_token=ctx.trace_id, pending=request)
    await hooks.run_on_stop(paused, ctx=ctx)
    return paused


async def run_loop(model: Model, tools: Sequence[Tool], task: str,
                   max_steps: int = 25, instructions: str | None = None,
                   max_context_tokens: int | None = None, hooks: "Hooks | None" = None,
                   ctx: "RunContext | None" = None, max_tool_retries: int = 2,
                   max_steps_policy: str = "stop",
                   stuck_thresholds: "StuckThresholds | None" = StuckThresholds()) -> AgentResult:
    bundle = build_bundle(tools, task, instructions)
    return await _drive(model, tools, task, bundle, Usage(), 1, max_steps,
                        max_context_tokens=max_context_tokens, hooks=hooks, ctx=ctx,
                        max_tool_retries=max_tool_retries, max_steps_policy=max_steps_policy,
                        stuck_thresholds=stuck_thresholds)


async def _drive(model: Model, tools: Sequence[Tool], task: str, bundle: ContextBundle,
                 usage: Usage, start_step: int, max_steps: int, *,
                 max_context_tokens: int | None = None, hooks: "Hooks | None" = None,
                 ctx: "RunContext | None" = None, max_tool_retries: int = 2,
                 max_steps_policy: str = "stop",
                 stuck_thresholds: "StuckThresholds | None" = StuckThresholds()) -> AgentResult:
    from verso.safety.hooks import Hooks, PermissionDecision
    hooks = hooks or Hooks()
    tool_map = {t.name: t for t in tools}
    retries: dict[str, int] = {}
    verify_count = 0   # re-drives spent on on_stop vetoes at natural terminations (END_TURN / DONE)
    # entry-guard: a crash-recovered / forked / hand-built history may carry orphan tool_calls or results;
    # repair once so every model.complete() below gets a valid payload. No-op (shape-preserving) when healthy.
    bundle.history = repair_history(bundle.history)

    for step in range(start_step, max_steps + 1):
        if not await hooks.run_should_continue(bundle, ctx=ctx):
            last = next((m.content for m in reversed(bundle.history) if m.role == "assistant" and m.content), "")
            result = AgentResult(output=last, stop_reason=StopReason.END_TURN, usage=usage, steps=step - 1)
            await hooks.run_on_stop(result, ctx=ctx)
            return result
        if stuck_thresholds is not None and detect_stuck(bundle.history, stuck_thresholds):
            last = next((m.content for m in reversed(bundle.history) if m.role == "assistant" and m.content), "")
            result = AgentResult(output=last, stop_reason=StopReason.STUCK, usage=usage, steps=step - 1)
            await hooks.run_on_stop(result, ctx=ctx)
            return result
        if max_context_tokens is not None and bundle.estimate_tokens() > max_context_tokens:
            bundle.history = prune(bundle.history)

        await hooks.run_pre_model(bundle, ctx=ctx)
        resp = await model.complete(bundle.to_messages(), bundle.tools, system=bundle.system)
        await hooks.run_post_model(resp, ctx=ctx)
        usage = usage + resp.usage
        if ctx is not None:
            ctx.step, ctx.usage, ctx.messages = step, usage, bundle.history

        if not resp.tool_calls:
            result = AgentResult(output=resp.text, stop_reason=StopReason.END_TURN,
                                 usage=usage, steps=step, truncated=resp.truncated)
            outcome = await hooks.run_on_stop(result, ctx=ctx)
            if outcome is not None and not outcome.passed and verify_count < hooks.max_verify_retries:
                verify_count += 1
                bundle.history.append(Message(role="user",
                                              content=f"Verification failed: {outcome.detail} Address it and finish."))
                continue   # re-drive instead of terminating (bounded by max_verify_retries + max_steps)
            return result

        bundle.history.append(Message(role="assistant", content=resp.text, tool_calls=resp.tool_calls))
        reverify = False   # set by a vetoed `done`: finish this turn's tool results, then re-drive
        for tc in resp.tool_calls:
            decision = await hooks.run_pre_tool((tc.name, tc.arguments), ctx=ctx)
            if decision != PermissionDecision.ALLOW:
                approved = (decision == PermissionDecision.ASK and hooks.ask is not None
                            and hooks.ask((tc.name, tc.arguments)))
                if approved:
                    pass  # sync-approved → fall through to run
                elif decision == PermissionDecision.ASK and ctx is not None and ctx.store is not None:
                    return await _pause(ctx, bundle, task, usage, step, hooks, resp, tc,
                                        HumanRequest(prompt=f"Approve tool '{tc.name}' with args {tc.arguments}?",
                                                     tool_name=tc.name, tool_call_id=tc.id, kind="approve"))
                else:
                    content = f"Tool '{tc.name}' was {getattr(decision, 'value', decision)} by policy; it did not run."
                    content = await hooks.run_post_tool((tc.name, tc.arguments), content, ctx=ctx)
                    bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))
                    continue
            t = tool_map.get(tc.name)
            if t is None:
                content = f"Error: unknown tool '{tc.name}'."
            else:
                try:
                    result = await dispatch(t, tc.arguments, ctx=ctx)
                except Paused as p:
                    if ctx is not None and ctx.store is not None:
                        return await _pause(ctx, bundle, task, usage, step, hooks, resp, tc, p.request)
                    content = f"Tool '{tc.name}' requested human input but this run is not durable; it did not pause."
                except Retry as r:
                    # per-tool budget: explicit max_attempts wins; else non-idempotent tools get 0 retries
                    # (re-running a side effect is a correctness bug); else the global max_tool_retries.
                    allowed = (t.max_attempts - 1) if t.max_attempts is not None else (
                        max_tool_retries if t.idempotent else 0)
                    retries[tc.name] = retries.get(tc.name, 0) + 1
                    if retries[tc.name] > allowed:
                        content = f"Error: tool '{tc.name}' exceeded its retry budget ({allowed})."
                    else:
                        content = f"Retry: {r.feedback}"
                else:
                    content = _format_result(result.data) if result.ok else f"Error: {result.error}"
                    if tc.name == "done" and result.ok:
                        final = AgentResult(output=_format_result(result.data), stop_reason=StopReason.DONE,
                                            usage=usage, steps=step)
                        outcome = await hooks.run_on_stop(final, ctx=ctx)
                        if not (outcome is not None and not outcome.passed
                                and verify_count < hooks.max_verify_retries):
                            return final
                        # vetoed DONE under budget: record the `done` tool result (so the assistant's
                        # tool_call is well-formed for the re-drive), append the feedback below, re-drive.
                        verify_count += 1
                        reverify = True
                        content = await hooks.run_post_tool((tc.name, tc.arguments), content, ctx=ctx)
                        if ctx is not None and ctx.tool_output_budget:
                            content = _truncate_tool_output(content, ctx.tool_output_budget)
                        bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))
                        # close any not-yet-run sibling tool_calls so the re-driven turn is well-formed
                        # (mirrors _pause): a tool_call must always be paired with a tool result.
                        done_ids = {m.tool_call_id for m in bundle.history if m.role == "tool"}
                        for sib in resp.tool_calls:
                            if sib.id not in done_ids:
                                bundle.history.append(Message(
                                    role="tool", tool_call_id=sib.id, name=sib.name,
                                    content=f"Tool '{sib.name}' was not run: the run is re-driving after a failed verification."))
                        bundle.history.append(Message(role="user",
                                                      content=f"Verification failed: {outcome.detail} Address it and finish."))
                        break   # stop processing this turn's tool_calls; the outer loop re-drives
            content = await hooks.run_post_tool((tc.name, tc.arguments), content, ctx=ctx)
            if ctx is not None and ctx.tool_output_budget:
                content = _truncate_tool_output(content, ctx.tool_output_budget)
            bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))

        if reverify:
            continue   # re-drive after a vetoed DONE (bounded by max_verify_retries + max_steps)
        _checkpoint(ctx, bundle, task, usage, step)   # per-step crash-recovery checkpoint (no pending)

    output = ""
    truncated = False
    if max_steps_policy == "generate":
        # opt-in grace call: one tool-less completion so a budget-exhausted run returns a best-effort
        # answer instead of '' (still stop_reason=MAX_STEPS — the run did hit the cap).
        grace = await model.complete(bundle.to_messages(), [], system=bundle.system)
        usage = usage + grace.usage
        output = grace.text
        truncated = grace.truncated
    result = AgentResult(output=output, stop_reason=StopReason.MAX_STEPS, usage=usage,
                         steps=max_steps, truncated=truncated)
    await hooks.run_on_stop(result, ctx=ctx)
    return result


async def resume_loop(model: Model, tools: Sequence[Tool], ctx: "RunContext", approve: bool, *,
                      answer: object = None, override_args: dict | None = None,
                      deny_message: str | None = None, skip: bool = False,
                      max_steps: int = 25, max_context_tokens: int | None = None,
                      hooks: "Hooks | None" = None, max_steps_policy: str = "stop",
                      stuck_thresholds: "StuckThresholds | None" = StuckThresholds()) -> AgentResult:
    if ctx.store is None:
        raise ValueError("resume requires a checkpointer")
    cp = ctx.store.load(ctx.trace_id)
    if cp is None:
        raise KeyError(f"no checkpoint for {ctx.trace_id}")
    bundle = ContextBundle(instructions=cp.instructions,
                           history=[msg_from_dict(d) for d in cp.history],
                           tools=list(tools))
    usage = Usage(input_tokens=cp.usage_in, output_tokens=cp.usage_out)
    if cp.pending is not None and cp.pending.tool_call_id is not None:
        tc_name, tc_id = cp.pending.tool_name, cp.pending.tool_call_id
        tool_map = {t.name: t for t in tools}
        # recover the held tool's arguments from the assistant turn already in history (bind once, always)
        args = next((c.arguments for m in reversed(bundle.history) for c in m.tool_calls if c.id == tc_id), {})
        # populate the ctx views the re-dispatched tool will read (mirror how _drive seeds them per step):
        # without this the re-run tool sees step=0, usage=Usage(0,0), messages=[] instead of the resumed state.
        if ctx is not None:
            ctx.step, ctx.usage, ctx.messages = cp.step, usage, bundle.history

        async def _redispatch(t, call_args):
            # Re-run the held tool. A second pause (the tool calls ctx.hitl.request again) is control flow,
            # not an error: re-checkpoint with the new pending and surface PAUSED instead of crashing the host.
            try:
                return await dispatch(t, call_args, ctx=ctx)
            except Paused as p:
                p.request.tool_name = p.request.tool_name or tc_name
                p.request.tool_call_id = p.request.tool_call_id or tc_id
                _checkpoint(ctx, bundle, cp.task, usage, cp.step, pending=p.request)
                paused = AgentResult(output="", stop_reason=StopReason.PAUSED, usage=usage, steps=cp.step,
                                     resume_token=ctx.trace_id, pending=p.request)
                from verso.safety.hooks import Hooks as _Hooks
                await (hooks or _Hooks()).run_on_stop(paused, ctx=ctx)
                return paused

        if cp.pending.kind == "input":
            # tool-initiated pause: pre-load the human's answer, then RE-RUN the tool (idempotent up to the request)
            ctx.hitl._resolve(cp.pending.key, answer)
            if tc_name in tool_map:
                res = await _redispatch(tool_map[tc_name], args)
                if isinstance(res, AgentResult):
                    return res                          # re-paused → surface PAUSED (do not append a tool result)
                content = _format_result(res.data) if res.ok else f"Error: {res.error}"
            else:
                content = f"Error: unknown tool '{tc_name}'."
        else:
            # pre_tool ASK gate: skip / approve(+override_args) / unknown-tool / deny(+message)
            if skip:
                content = f"Tool '{tc_name}' was skipped by the reviewer."
            elif approve and tc_name in tool_map:
                res = await _redispatch(tool_map[tc_name], override_args if override_args is not None else args)
                if isinstance(res, AgentResult):
                    return res                          # re-paused → surface PAUSED (do not append a tool result)
                content = _format_result(res.data) if res.ok else f"Error: {res.error}"
            elif approve:
                content = f"Error: unknown tool '{tc_name}'."
            else:
                content = deny_message or f"Tool '{tc_name}' was denied by the human reviewer; it did not run."
        from verso.safety.hooks import Hooks
        content = await (hooks or Hooks()).run_post_tool((tc_name, args), content, ctx=ctx)
        if ctx is not None and ctx.tool_output_budget:   # parity with _drive: budget the re-dispatched result too
            content = _truncate_tool_output(content, ctx.tool_output_budget)
        bundle.history.append(Message(role="tool", content=content, tool_call_id=tc_id, name=tc_name))
    return await _drive(model, tools, cp.task, bundle, usage, cp.step + 1, max_steps,
                        max_context_tokens=max_context_tokens, hooks=hooks, ctx=ctx,
                        max_steps_policy=max_steps_policy, stuck_thresholds=stuck_thresholds)
