# verso/agent.py
from __future__ import annotations
import dataclasses
import uuid
from contextlib import contextmanager
from typing import TYPE_CHECKING, AsyncIterator, Sequence

from verso.context.bundle import ContextBundle
from verso.core.loop import build_bundle, resume_loop, run_loop
from verso.core.stream_loop import run_stream
from verso.core.stuck import StuckThresholds
from verso.durable.context import RunContext
from verso.model.base import Model
from verso.stream.events import StreamEvent
from verso.tools.coerce import CoercionError, StructuredOutputError, coerce
from verso.tools.tool import Tool
from verso.types import AgentResult

if TYPE_CHECKING:
    from verso.safety.hooks import Hooks


def _resolve(model):
    """Normalize a model spec to a Model: a 'provider:model' string -> init_model(...), a Model -> unchanged."""
    if isinstance(model, str):
        from verso import init_model      # lazy import: avoids the agent <-> __init__ import cycle
        return init_model(model)
    return model


class Agent:
    def __init__(self, model: "Model | str", tools: Sequence[Tool] = (), *,
                 instructions: str | None = None, max_steps: int = 25,
                 max_context_tokens: int | None = None, hooks: "Hooks | None" = None,
                 checkpointer: object | None = None, deps: object | None = None,
                 max_tool_retries: int = 2, tool_output_budget: int | None = None,
                 trust_tier: str = "act", max_steps_policy: str = "stop",
                 stuck_thresholds: "StuckThresholds | None" = StuckThresholds()):
        self.model = _resolve(model)
        self.tools = list(tools)
        # Trust as a construction-time capability boundary, not a call-time check: a "read"-tier agent
        # (handles untrusted input — tickets, scraped web, email) gets a registry that simply lacks the
        # privileged tools, so a prompt injection can't even request one. Stronger than a runtime
        # PermissionPolicy gate (which the injection still reaches). Default "act" → full → byte-identical.
        self.trust_tier = trust_tier
        if trust_tier == "read":
            self.tools = [t for t in self.tools if not t.privileged]
        self.instructions = instructions
        self.max_steps = max_steps
        self.max_context_tokens = max_context_tokens
        self.hooks = hooks
        self.checkpointer = checkpointer
        self.deps = deps
        self.max_tool_retries = max_tool_retries
        self.tool_output_budget = tool_output_budget
        self.max_steps_policy = max_steps_policy
        self.stuck_thresholds = stuck_thresholds

    def inspect(self, task: str) -> ContextBundle:
        """Return the exact ContextBundle the model will receive for `task` (turn 1)."""
        return build_bundle(self.tools, task, self.instructions)

    async def _run(self, task: str, model=None) -> AgentResult:
        # model=None ⇒ self.model (byte-identical to before); a per-run override resolves a string once here.
        m = _resolve(model) if model is not None else self.model
        # Always create the context; when checkpointer is None, store is None, so _checkpoint no-ops
        # and every durable branch (gated on ctx.store is not None) stays unreachable → byte-identical.
        ctx = RunContext(trace_id=uuid.uuid4().hex, deps=self.deps, store=self.checkpointer,
                         model=getattr(m, "model_id", ""), tool_output_budget=self.tool_output_budget)
        return await run_loop(m, self.tools, task, max_steps=self.max_steps,
                              instructions=self.instructions,
                              max_context_tokens=self.max_context_tokens,
                              hooks=self.hooks, ctx=ctx, max_tool_retries=self.max_tool_retries,
                              max_steps_policy=self.max_steps_policy,
                              stuck_thresholds=self.stuck_thresholds)

    async def resume(self, token: str, *, approve: bool = True, answer: object = None,
                     override_args: dict | None = None, deny_message: str | None = None,
                     skip: bool = False, model=None, allow_config_drift: bool = False) -> AgentResult:
        if self.checkpointer is None:
            raise ValueError("resume requires an Agent constructed with a checkpointer")
        # model=None ⇒ self.model; a paused/forked run can resume on a different model.
        # Resolve the model BEFORE building the ctx so ctx.model is populated for the whole resumed run
        # (matches _run/stream) — otherwise the re-dispatched tool + every later step sees ctx.model == "".
        m = _resolve(model) if model is not None else self.model
        ctx = RunContext(trace_id=token, deps=self.deps, store=self.checkpointer,
                         model=getattr(m, "model_id", ""), tool_output_budget=self.tool_output_budget)
        return await resume_loop(m, self.tools, ctx, approve, answer=answer,
                                 override_args=override_args, deny_message=deny_message, skip=skip,
                                 max_steps=self.max_steps,
                                 max_context_tokens=self.max_context_tokens, hooks=self.hooks,
                                 max_steps_policy=self.max_steps_policy,
                                 stuck_thresholds=self.stuck_thresholds,
                                 allow_config_drift=allow_config_drift,
                                 # An explicit model= IS the "resume on a different model" feature the
                                 # docstring above promises — the caller already declared the swap, so
                                 # it must not also trip the drift guard.
                                 model_overridden=model is not None)

    def history(self, token: str) -> list:
        """The per-step checkpoint trajectory of a durable run (ascending step); [] if unknown."""
        if self.checkpointer is None:
            raise ValueError("history requires an Agent constructed with a checkpointer")
        return self.checkpointer.history(token)

    def fork(self, token: str, *, at_step: int | None = None) -> str:
        """Branch a new run from `token`'s state at `at_step` (default: latest). Returns the new token.
        Clones the checkpoint under a fresh trace_id; the original is untouched. Continue the branch with
        resume(new_token, ...) — it re-runs from the fork point (no step-memoization)."""
        if self.checkpointer is None:
            raise ValueError("fork requires an Agent constructed with a checkpointer")
        if at_step is None:
            src = self.checkpointer.load(token)
        else:
            src = next((c for c in self.checkpointer.history(token) if c.step == at_step), None)
        if src is None:
            raise ValueError(f"no checkpoint to fork from token={token!r} at_step={at_step!r}")
        new_token = uuid.uuid4().hex
        self.checkpointer.save(dataclasses.replace(src, trace_id=new_token))
        return new_token

    async def run(self, task: str, *, output_type: type | None = None,
                  validators: Sequence = (), max_output_retries: int = 1,
                  model=None) -> AgentResult:
        # output_type is None ⇒ return the result unchanged; validators require a typed output to run on.
        # model= overrides this run only (and holds across structured-output reasks below).
        result = await self._run(task, model=model)
        if output_type is None:
            return result
        from verso.tools.errors import Retry
        current, attempts = result, 0
        usage_total, steps_total = current.usage, current.steps
        while True:
            try:
                parsed = coerce(current.output, output_type)
                for validator in validators:
                    validator(parsed)
            except (CoercionError, ValueError, Retry) as e:
                # Retry/ValueError from a validator and CoercionError from parsing all reask with feedback.
                feedback = e.feedback if isinstance(e, Retry) else str(e)
                if attempts >= max_output_retries:
                    name = getattr(output_type, "__name__", repr(output_type))
                    raise StructuredOutputError(
                        f"could not produce {name} after {attempts} reask(s): {feedback}"
                    ) from e
                attempts += 1
                reask = (
                    f"{task}\n\nYour previous answer was:\n{current.output}\n\n"
                    f"That was rejected: {feedback}. "
                    "Reply with ONLY valid JSON matching the requested schema — no prose, no code fences."
                )
                current = await self._run(reask, model=model)
                usage_total = usage_total + current.usage
                steps_total = steps_total + current.steps
                continue
            current.parsed = parsed
            current.usage = usage_total
            current.steps = steps_total
            return current

    async def stream(self, task: str, *, model=None) -> AsyncIterator[StreamEvent]:
        # model=None ⇒ self.model (byte-identical); a per-stream override resolves a string once here.
        m = _resolve(model) if model is not None else self.model
        # streaming is tactical (durable resume is a later seam) → ctx carries deps + trace_id for
        # ctx-aware hooks, but store=None (no checkpoint/pause on the stream path).
        ctx = RunContext(trace_id=uuid.uuid4().hex, deps=self.deps, store=None,
                         model=getattr(m, "model_id", ""), tool_output_budget=self.tool_output_budget)
        async for ev in run_stream(m, self.tools, task, max_steps=self.max_steps,
                                   instructions=self.instructions,
                                   max_context_tokens=self.max_context_tokens,
                                   hooks=self.hooks, ctx=ctx, max_tool_retries=self.max_tool_retries,
                                   max_steps_policy=self.max_steps_policy,
                                   stuck_thresholds=self.stuck_thresholds):
            yield ev

    @contextmanager
    def override(self, *, model):
        """Temporarily swap the model for runs nested in this block (tests / evals / scoped swaps).
        For a single concurrent call prefer run(..., model=...); override mutates self.model, so it is
        scoped/sequential, not for overlapping concurrent runs."""
        prev = self.model
        self.model = _resolve(model)
        try:
            yield self
        finally:
            self.model = prev
