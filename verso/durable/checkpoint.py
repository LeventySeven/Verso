# verso/durable/checkpoint.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from verso.durable.context import HumanRequest


@dataclass
class Checkpoint:
    """A serializable snapshot of a run's resumable state — enough to rebuild the ContextBundle and
    continue from `step`. `history` holds serialized Messages. `pending` is set only when the run
    paused for a human decision; None means a plain crash-recovery checkpoint."""
    trace_id: str
    task: str
    instructions: str | None
    history: list[dict] = field(default_factory=list)
    usage_in: int = 0
    usage_out: int = 0
    step: int = 0
    pending: HumanRequest | None = None
    config: dict | None = None
    """The agent config this run was checkpointed UNDER — `{"model": str, "tools": [name, ...]}`.

    PRD §14.9: "Checkpoint pins the full config (model version + system prompt + tool set), not just
    event state; fast model-rollback is a named failure mode." `instructions` (the system prompt) was
    already pinned above; this adds the other two, so `resume` can tell that the agent it is resuming
    INTO is not the agent that paused.

    Why it matters: a resumed run replays a history produced by a different model, and re-dispatches a
    held tool call against the CURRENT tool list. Swap the model or drop a tool between pause and
    resume and the run silently continues as a different agent — the failure the PRD names.

    `None` on checkpoints written before this field existed; `resume` skips the comparison rather than
    guessing, so legacy runs resume exactly as before."""


@runtime_checkable
class CheckpointStore(Protocol):
    """The durable contract. sqlite (survives restart) / in-memory (tests) implement it; Postgres/Redis later."""
    def save(self, cp: Checkpoint) -> None: ...
    def load(self, trace_id: str) -> Checkpoint | None: ...
    def delete(self, trace_id: str) -> None: ...
    def history(self, trace_id: str) -> list[Checkpoint]: ...  # all retained per-step checkpoints, ascending by step; [] if unknown.
