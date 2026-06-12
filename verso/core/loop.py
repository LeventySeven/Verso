# verso/core/loop.py
from __future__ import annotations
import json
from typing import TYPE_CHECKING, Sequence

from verso.context.bundle import ContextBundle
from verso.context.prune import prune
from verso.durable.checkpoint import Checkpoint
from verso.durable.context import HumanRequest, RunContext  # noqa: F401  (RunContext used by callers/annotations)
from verso.durable.serde import msg_to_dict
from verso.model.base import Message, Model
from verso.tools.dispatch import dispatch
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


async def run_loop(model: Model, tools: Sequence[Tool], task: str,
                   max_steps: int = 25, instructions: str | None = None,
                   max_context_tokens: int | None = None, hooks: "Hooks | None" = None,
                   ctx: "RunContext | None" = None) -> AgentResult:
    bundle = build_bundle(tools, task, instructions)
    return await _drive(model, tools, task, bundle, Usage(), 1, max_steps,
                        max_context_tokens=max_context_tokens, hooks=hooks, ctx=ctx)


async def _drive(model: Model, tools: Sequence[Tool], task: str, bundle: ContextBundle,
                 usage: Usage, start_step: int, max_steps: int, *,
                 max_context_tokens: int | None = None, hooks: "Hooks | None" = None,
                 ctx: "RunContext | None" = None) -> AgentResult:
    from verso.safety.hooks import Hooks, PermissionDecision
    hooks = hooks or Hooks()
    tool_map = {t.name: t for t in tools}

    for step in range(start_step, max_steps + 1):
        if max_context_tokens is not None and bundle.estimate_tokens() > max_context_tokens:
            bundle.history = prune(bundle.history)

        await hooks.run_pre_model(bundle)
        resp = await model.complete(bundle.to_messages(), bundle.tools, system=bundle.system)
        await hooks.run_post_model(resp)
        usage = usage + resp.usage

        if not resp.tool_calls:
            result = AgentResult(output=resp.text, stop_reason=StopReason.END_TURN,
                                 usage=usage, steps=step)
            await hooks.run_on_stop(result)
            return result

        bundle.history.append(Message(role="assistant", content=resp.text, tool_calls=resp.tool_calls))
        for tc in resp.tool_calls:
            decision = await hooks.run_pre_tool((tc.name, tc.arguments))
            if decision != PermissionDecision.ALLOW:
                approved = (decision == PermissionDecision.ASK and hooks.ask is not None
                            and hooks.ask((tc.name, tc.arguments)))
                if approved:
                    pass  # sync-approved → fall through to run
                elif decision == PermissionDecision.ASK and ctx is not None and ctx.store is not None:
                    pending = HumanRequest(prompt=f"Approve tool '{tc.name}' with args {tc.arguments}?",
                                           tool_name=tc.name, tool_call_id=tc.id)
                    _checkpoint(ctx, bundle, task, usage, step, pending=pending)
                    paused = AgentResult(output="", stop_reason=StopReason.PAUSED, usage=usage, steps=step,
                                         resume_token=ctx.trace_id, pending=pending)
                    await hooks.run_on_stop(paused)
                    return paused
                else:
                    content = f"Tool '{tc.name}' was {decision.value} by policy; it did not run."
                    content = await hooks.run_post_tool((tc.name, tc.arguments), content)
                    bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))
                    continue
            t = tool_map.get(tc.name)
            if t is None:
                content = f"Error: unknown tool '{tc.name}'."
            else:
                result = await dispatch(t, tc.arguments)
                content = _format_result(result.data) if result.ok else f"Error: {result.error}"
                if tc.name == "done" and result.ok:
                    final = AgentResult(output=_format_result(result.data),
                                        stop_reason=StopReason.DONE, usage=usage, steps=step)
                    await hooks.run_on_stop(final)
                    return final
            content = await hooks.run_post_tool((tc.name, tc.arguments), content)
            bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))

        _checkpoint(ctx, bundle, task, usage, step)   # per-step crash-recovery checkpoint (no pending)

    result = AgentResult(output="", stop_reason=StopReason.MAX_STEPS, usage=usage, steps=max_steps)
    await hooks.run_on_stop(result)
    return result
