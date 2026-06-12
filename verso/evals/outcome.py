# verso/evals/outcome.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

from verso.evals.span import VersoSpan, VersoScore


@dataclass
class OutcomeResult:
    passed: bool
    iterations: int
    last_span: VersoSpan | None = None


async def define_outcome(agent, task: str, grader: Callable[[VersoSpan], VersoScore],
                         *, max_iterations: int = 3) -> OutcomeResult:
    """Bounded generate→grade→revise. NEVER an unbounded `while True` (Anthropic define_outcome:
    default 3, hard cap 20). `grader` takes a captured span and returns a VersoScore; on fail the
    task is re-asked with the prior output. Stops on the first pass or at `max_iterations`."""
    if not (1 <= max_iterations <= 20):
        raise ValueError("max_iterations must be in [1, 20]")
    current, span = task, None
    for i in range(1, max_iterations + 1):
        span = await VersoSpan.capture(agent, current, trace_id=f"outcome-{i}")
        score = grader(span)
        if score.passed:
            return OutcomeResult(passed=True, iterations=i, last_span=span)
        current = (f"{task}\n\nYour previous attempt was:\n{span.output}\n\n"
                   f"It did not satisfy the rubric ({score.detail}). Revise and try again.")
    return OutcomeResult(passed=False, iterations=max_iterations, last_span=span)
