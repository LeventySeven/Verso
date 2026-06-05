# verso/agent.py
from __future__ import annotations
from typing import Sequence

from verso.core.loop import run_loop
from verso.model.base import Model
from verso.tools.tool import Tool
from verso.types import AgentResult


class Agent:
    def __init__(self, model: Model, tools: Sequence[Tool] = (), *,
                 instructions: str | None = None, max_steps: int = 25):
        self.model = model
        self.tools = list(tools)
        self.instructions = instructions
        self.max_steps = max_steps

    async def run(self, task: str) -> AgentResult:
        return await run_loop(
            self.model, self.tools, task,
            max_steps=self.max_steps, instructions=self.instructions,
        )
