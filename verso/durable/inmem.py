# verso/durable/inmem.py
from __future__ import annotations
import copy

from verso.durable.checkpoint import Checkpoint


class InMemoryCheckpointStore:
    """Dict-based CheckpointStore — ephemeral, dependency-free. Deep-copies on save/load so callers
    can't mutate a stored checkpoint by reference (parity with the sqlite store, which serializes)."""
    def __init__(self) -> None:
        self._cps: dict[str, Checkpoint] = {}
        self._history: dict[str, dict[int, Checkpoint]] = {}

    def save(self, cp: Checkpoint) -> None:
        self._cps[cp.trace_id] = copy.deepcopy(cp)
        self._history.setdefault(cp.trace_id, {})[cp.step] = copy.deepcopy(cp)

    def load(self, trace_id: str) -> Checkpoint | None:
        cp = self._cps.get(trace_id)
        return copy.deepcopy(cp) if cp is not None else None

    def history(self, trace_id: str) -> list[Checkpoint]:
        return [copy.deepcopy(c) for _, c in sorted(self._history.get(trace_id, {}).items())]

    def delete(self, trace_id: str) -> None:
        self._cps.pop(trace_id, None)
        self._history.pop(trace_id, None)
