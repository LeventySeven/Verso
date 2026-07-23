# verso/orchestrate/core.py
from __future__ import annotations

import asyncio
import contextvars
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Sequence

from verso.types import AgentResult, Usage

# ---------------------------------------------------------------------------------------------------
# Depth cap. "no nested orchestrators by default" (PRD §6.2): the orchestrator is depth 0, its workers
# run at depth 1, and a worker that tries to orchestrate again is refused. Tracked via a contextvar so
# the count follows the async task tree correctly across `await` — a plain int could not.
# ---------------------------------------------------------------------------------------------------
_depth: contextvars.ContextVar[int] = contextvars.ContextVar("verso_orch_depth", default=0)


class DepthCapExceeded(RuntimeError):
    """A fan_out/spawn nested deeper than `max_depth` allows.

    The default cap is 1: one level of orchestration. Nested orchestration is the fork-bomb / lost-
    ownership failure this prevents — a worker spawning workers spawning workers. Raise the cap
    explicitly (`max_depth=2`) if you genuinely need a second level and can reason about the fan-out.
    """


def orchestration_depth() -> int:
    """Current orchestration nesting depth (0 at the top level). Exposed for tests and introspection."""
    return _depth.get()


def _check_and_next(max_depth: int) -> int:
    d = _depth.get()
    if d >= max_depth:
        raise DepthCapExceeded(
            f"orchestration depth {d} would exceed max_depth={max_depth} — a worker is trying to "
            f"orchestrate. Flatten the fan-out, or pass max_depth={d + 1} if a second level is intended."
        )
    return d + 1


# ---------------------------------------------------------------------------------------------------
# fan_out — bounded concurrent execution with per-item failure isolation.
# ---------------------------------------------------------------------------------------------------
async def fan_out(
    thunks: Sequence[Callable[[], Awaitable]],
    *,
    max_concurrency: int = 6,
    return_exceptions: bool = True,
    max_depth: int = 1,
) -> list:
    """Run independent async units concurrently, capped at `max_concurrency`, preserving input order.

    `thunks` are zero-arg callables returning awaitables (`lambda: worker.run(doc)`), NOT bare
    coroutines — a thunk is only started when a concurrency slot frees, so with 100 items and
    max_concurrency=6 at most 6 model calls are ever in flight. (Bare `asyncio.gather` starts all 100
    at once; that is the trap this exists to remove.)

    `return_exceptions=True` (default) isolates failures: a thunk that raises lands as the exception
    object in its slot, and the other units still complete — one flaky worker never sinks the batch.
    Set it False to fail fast on the first error.

    Bounded by the depth cap (see DepthCapExceeded): call it from an orchestrator, not from inside a
    worker that fan_out already launched.
    """
    next_depth = _check_and_next(max_depth)
    if max_concurrency < 1:
        raise ValueError("max_concurrency must be >= 1")
    sem = asyncio.Semaphore(max_concurrency)

    async def _run(thunk: Callable[[], Awaitable]):
        async with sem:
            # Each worker runs one level deeper; the contextvar is copy-on-write per task, so sibling
            # workers do not see each other's depth and cannot lift the cap for one another.
            token = _depth.set(next_depth)
            try:
                return await thunk()
            finally:
                _depth.reset(token)

    return await asyncio.gather(
        *(_run(t) for t in thunks), return_exceptions=return_exceptions
    )


# ---------------------------------------------------------------------------------------------------
# spawn — a sub-agent as a context-isolation device.
# ---------------------------------------------------------------------------------------------------
@dataclass
class Subagent:
    """The compact result of a spawned sub-agent — a context-isolation boundary made concrete.

    The point of a sub-agent is that its tokens never enter the parent's context window; only this
    small object crosses back. `output` is the sub-agent's answer; `usage`/`steps` are for the
    parent's own budgeting. The sub-agent's full transcript stays in the child and is dropped — which
    is the whole reason to spawn one instead of inlining the work.
    """
    output: str
    usage: Usage
    steps: int
    result: AgentResult = field(repr=False)  # the full child result, if the parent needs more than output


def _forked_task(task: str, parent_history, fork: str, last_n: int) -> str:
    """Seed the child's task with parent context per the fork mode. Default `none`: the child starts
    clean (true isolation). `last_n`/`full` prepend a read-only slice of the parent's conversation as
    plain text — enough context to act, without inheriting the parent's live history object."""
    if fork == "none" or not parent_history:
        return task
    msgs = parent_history[-last_n:] if fork == "last_n" else parent_history
    lines = []
    for m in msgs:
        role = getattr(m, "role", "?")
        content = getattr(m, "content", "")
        if content:
            lines.append(f"{role}: {content}")
    if not lines:
        return task
    ctx = "\n".join(lines)
    return f"Context from the parent agent (read-only):\n{ctx}\n\n---\n\n{task}"


async def spawn(
    model,
    task: str,
    *,
    tools: Sequence = (),
    instructions: str | None = None,
    max_steps: int = 25,
    fork: str = "none",
    last_n: int = 6,
    parent_history=None,
    max_depth: int = 1,
    **agent_kwargs,
) -> Subagent:
    """Run a child agent in its own context window and return only a compact `Subagent` result.

    Use this to offload an expensive sub-task (a deep search, a long file read) so its tokens do not
    pollute the parent — the parent gets back `Subagent.output`, not the child's transcript. The child
    gets a `subset` of tools (only what you pass) and, by default, none of the parent's history
    (`fork="none"`); pass `fork="last_n"` / `"full"` with `parent_history=agent's messages` to seed it.

    Depth-capped like fan_out: a spawned agent cannot itself spawn (default). This is the "sub-agent =
    context isolation, not org-chart role-play" primitive from PRD §6.2 — no nested orchestrators, no
    parent-history inheritance by default, a typed compact return.
    """
    from verso.agent import Agent  # local import: keep `orchestrate` off the core import path

    next_depth = _check_and_next(max_depth)
    if fork not in ("none", "last_n", "full"):
        raise ValueError(f"fork must be 'none' | 'last_n' | 'full', got {fork!r}")

    child = Agent(model, tools=list(tools), instructions=instructions,
                  max_steps=max_steps, **agent_kwargs)
    seeded = _forked_task(task, parent_history, fork, last_n)

    token = _depth.set(next_depth)
    try:
        res = await child.run(seeded)
    finally:
        _depth.reset(token)
    return Subagent(output=res.output, usage=res.usage, steps=res.steps, result=res)


# ---------------------------------------------------------------------------------------------------
# Reviewer — the cross-model "rubber duck".
# ---------------------------------------------------------------------------------------------------
_DEFAULT_REVIEW_INSTRUCTIONS = (
    "You are a critical reviewer. You are given a task and another agent's answer to it. "
    "Find concrete problems: factual errors, missed requirements, unsupported claims, edge cases. "
    "Be specific and terse. If the answer is genuinely good, say so plainly rather than inventing "
    "faults."
)


@dataclass
class Review:
    """A reviewer's verdict on another agent's output."""
    feedback: str
    usage: Usage
    steps: int
    result: AgentResult = field(repr=False)


class Reviewer:
    """A critic agent, deliberately built on a DIFFERENT model from the one it reviews.

    "The cross-model reviewer hook (rubber duck) is the cheapest multi-agent win" (PRD §6.2). A model
    reviewing its own output shares its own blind spots; a reviewer from a different family catches
    what the author's family systematically misses. This is a thin wrapper — one agent, one call — not
    a subsystem: it exists so the pattern is one obvious import instead of hand-rolled each time.
    """

    def __init__(self, model, *, instructions: str | None = None, max_steps: int = 4, **agent_kwargs):
        from verso.agent import Agent
        self._agent = Agent(model, instructions=instructions or _DEFAULT_REVIEW_INSTRUCTIONS,
                            max_steps=max_steps, **agent_kwargs)

    async def review(self, task: str, answer: str) -> Review:
        """Return the reviewer's critique of `answer` as a response to `task`."""
        prompt = f"TASK:\n{task}\n\nANSWER TO REVIEW:\n{answer}\n\nYour review:"
        res = await self._agent.run(prompt)
        return Review(feedback=res.output, usage=res.usage, steps=res.steps, result=res)
