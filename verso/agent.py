# verso/agent.py
from __future__ import annotations
import uuid
from typing import TYPE_CHECKING, AsyncIterator, Sequence

from verso.context.bundle import ContextBundle
from verso.core.loop import build_bundle, resume_loop, run_loop
from verso.core.stream_loop import run_stream
from verso.durable.context import RunContext
from verso.model.base import Model
from verso.stream.events import StreamEvent
from verso.tools.coerce import CoercionError, StructuredOutputError, coerce
from verso.tools.tool import Tool
from verso.types import AgentResult

if TYPE_CHECKING:
    from verso.safety.hooks import Hooks


class Agent:
    def __init__(self, model: Model, tools: Sequence[Tool] = (), *,
                 instructions: str | None = None, max_steps: int = 25,
                 max_context_tokens: int | None = None, hooks: "Hooks | None" = None,
                 checkpointer: object | None = None, deps: object | None = None,
                 max_tool_retries: int = 2):
        self.model = model
        self.tools = list(tools)
        self.instructions = instructions
        self.max_steps = max_steps
        self.max_context_tokens = max_context_tokens
        self.hooks = hooks
        self.checkpointer = checkpointer
        self.deps = deps
        self.max_tool_retries = max_tool_retries

    def inspect(self, task: str) -> ContextBundle:
        """Return the exact ContextBundle the model will receive for `task` (turn 1)."""
        return build_bundle(self.tools, task, self.instructions)

    async def _run(self, task: str) -> AgentResult:
        # Always create the context; when checkpointer is None, store is None, so _checkpoint no-ops
        # and every durable branch (gated on ctx.store is not None) stays unreachable → byte-identical.
        ctx = RunContext(trace_id=uuid.uuid4().hex, deps=self.deps, store=self.checkpointer,
                         model=getattr(self.model, "model_id", ""))
        return await run_loop(self.model, self.tools, task, max_steps=self.max_steps,
                              instructions=self.instructions,
                              max_context_tokens=self.max_context_tokens,
                              hooks=self.hooks, ctx=ctx, max_tool_retries=self.max_tool_retries)

    async def resume(self, token: str, *, approve: bool = True, answer: object = None,
                     override_args: dict | None = None, deny_message: str | None = None,
                     skip: bool = False) -> AgentResult:
        if self.checkpointer is None:
            raise ValueError("resume requires an Agent constructed with a checkpointer")
        ctx = RunContext(trace_id=token, deps=self.deps, store=self.checkpointer)
        return await resume_loop(self.model, self.tools, ctx, approve, answer=answer,
                                 override_args=override_args, deny_message=deny_message, skip=skip,
                                 max_steps=self.max_steps,
                                 max_context_tokens=self.max_context_tokens, hooks=self.hooks)

    async def run(self, task: str, *, output_type: type | None = None,
                  validators: Sequence = (), max_output_retries: int = 1) -> AgentResult:
        # output_type is None ⇒ return the result unchanged; validators require a typed output to run on.
        result = await self._run(task)
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
                current = await self._run(reask)
                usage_total = usage_total + current.usage
                steps_total = steps_total + current.steps
                continue
            current.parsed = parsed
            current.usage = usage_total
            current.steps = steps_total
            return current

    async def stream(self, task: str) -> AsyncIterator[StreamEvent]:
        # streaming is tactical (durable resume is a later seam) → ctx carries deps + trace_id for
        # ctx-aware hooks, but store=None (no checkpoint/pause on the stream path).
        ctx = RunContext(trace_id=uuid.uuid4().hex, deps=self.deps, store=None,
                         model=getattr(self.model, "model_id", ""))
        async for ev in run_stream(self.model, self.tools, task, max_steps=self.max_steps,
                                   instructions=self.instructions,
                                   max_context_tokens=self.max_context_tokens,
                                   hooks=self.hooks, ctx=ctx):
            yield ev
