# verso/durable/sqlite.py
from __future__ import annotations
import json
import sqlite3

from verso.durable.checkpoint import Checkpoint
from verso.durable.context import HumanRequest

DDL = "CREATE TABLE IF NOT EXISTS checkpoint (trace_id TEXT PRIMARY KEY, data TEXT NOT NULL)"


class SqliteCheckpointStore:
    """Stdlib-sqlite CheckpointStore — survives process restart (the point of 'durable'). One row per
    trace_id; the checkpoint is read/written whole, so it's stored as a single JSON blob. pgvector/Redis
    stores implement the same CheckpointStore contract later with zero loop change."""
    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path)
        self.db.execute(DDL)
        self.db.commit()

    def save(self, cp: Checkpoint) -> None:
        p = cp.pending
        data = json.dumps({
            "trace_id": cp.trace_id, "task": cp.task, "instructions": cp.instructions,
            "history": cp.history, "usage_in": cp.usage_in, "usage_out": cp.usage_out, "step": cp.step,
            "pending": None if p is None else {"prompt": p.prompt, "key": p.key, "kind": p.kind,
                                               "tool_name": p.tool_name, "tool_call_id": p.tool_call_id},
        })
        self.db.execute("INSERT OR REPLACE INTO checkpoint(trace_id, data) VALUES(?, ?)", (cp.trace_id, data))
        self.db.commit()

    def load(self, trace_id: str) -> Checkpoint | None:
        row = self.db.execute("SELECT data FROM checkpoint WHERE trace_id=?", (trace_id,)).fetchone()
        if row is None:
            return None
        d = json.loads(row[0])
        pend = d["pending"]
        return Checkpoint(
            trace_id=d["trace_id"], task=d["task"], instructions=d["instructions"],
            history=d["history"], usage_in=d["usage_in"], usage_out=d["usage_out"], step=d["step"],
            pending=None if pend is None else HumanRequest(**pend),
        )

    def delete(self, trace_id: str) -> None:
        self.db.execute("DELETE FROM checkpoint WHERE trace_id=?", (trace_id,))
        self.db.commit()
