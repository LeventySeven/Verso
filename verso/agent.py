# verso/agent.py
from __future__ import annotations
from typing import Sequence

from verso.core.loop import run_loop
from verso.model.base import Model
from verso.tools.coerce import CoercionError, StructuredOutputError, coerce
from verso.tools.tool import Tool
from verso.types import AgentResult


class Agent:
    def __init__(self, model: Model, tools: Sequence[Tool] = (), *,
                 instructions: str | None = None, max_steps: int = 25):
        self.model = model
        self.tools = list(tools)
        self.instructions = instructions
        self.max_steps = max_steps

    async def run(self, task: str, *, output_type: type | None = None) -> AgentResult:
        result = await run_loop(self.model, self.tools, task,
                                max_steps=self.max_steps, instructions=self.instructions)
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
            retry = await run_loop(self.model, self.tools, reask,
                                   max_steps=self.max_steps, instructions=self.instructions)
            try:
                retry.parsed = coerce(retry.output, output_type)
                retry.usage = result.usage + retry.usage   # don't discard the first attempt
                retry.steps = result.steps + retry.steps
                return retry
            except CoercionError as second:
                name = getattr(output_type, "__name__", repr(output_type))
                raise StructuredOutputError(
                    f"could not produce {name} after one reask: {second}"
                ) from second
