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


@runtime_checkable
class CheckpointStore(Protocol):
    """The durable contract. sqlite (survives restart) / in-memory (tests) implement it; Postgres/Redis later."""
    def save(self, cp: Checkpoint) -> None: ...
    def load(self, trace_id: str) -> Checkpoint | None: ...
    def delete(self, trace_id: str) -> None: ...
