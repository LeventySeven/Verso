# verso/agent.py
from __future__ import annotations
from typing import AsyncIterator, Sequence

from verso.context.bundle import ContextBundle
from verso.core.loop import build_bundle, run_loop
from verso.core.stream_loop import run_stream
from verso.model.base import Model
from verso.stream.events import StreamEvent
from verso.tools.coerce import CoercionError, StructuredOutputError, coerce
from verso.tools.tool import Tool
from verso.types import AgentResult


class Agent:
    def __init__(self, model: Model, tools: Sequence[Tool] = (), *,
                 instructions: str | None = None, max_steps: int = 25,
                 max_context_tokens: int | None = None):
        self.model = model
        self.tools = list(tools)
        self.instructions = instructions
        self.max_steps = max_steps
        self.max_context_tokens = max_context_tokens

    def inspect(self, task: str) -> ContextBundle:
        """Return the exact ContextBundle the model will receive for `task` (turn 1)."""
        return build_bundle(self.tools, task, self.instructions)

    async def _run(self, task: str) -> AgentResult:
        return await run_loop(self.model, self.tools, task, max_steps=self.max_steps,
                              instructions=self.instructions,
                              max_context_tokens=self.max_context_tokens)

    async def run(self, task: str, *, output_type: type | None = None) -> AgentResult:
        result = await self._run(task)
        if output_type is None:
            return result
        try:
            result.parsed = coerce(result.output, output_type)
            return result
        except CoercionError as first:
            reask = (
                f"{task}\n\nYour previous answer was:\n{result.output}\n\n"
                f"That could not be parsed into the required format ({first}). "
                "Reply with ONLY valid JSON matching the requested schema — no prose, no code fences."
            )
            retry = await self._run(reask)
            try:
                retry.parsed = coerce(retry.output, output_type)
                retry.usage = result.usage + retry.usage
                retry.steps = result.steps + retry.steps
                return retry
            except CoercionError as second:
                name = getattr(output_type, "__name__", repr(output_type))
                raise StructuredOutputError(
                    f"could not produce {name} after one reask: {second}"
                ) from second

    async def stream(self, task: str) -> AsyncIterator[StreamEvent]:
        async for ev in run_stream(self.model, self.tools, task, max_steps=self.max_steps,
                                   instructions=self.instructions,
                                   max_context_tokens=self.max_context_tokens):
            yield ev
