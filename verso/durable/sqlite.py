# verso/durable/sqlite.py
from __future__ import annotations
import json
import sqlite3

from verso.durable.checkpoint import Checkpoint
from verso.durable.context import HumanRequest

DDL = "CREATE TABLE IF NOT EXISTS checkpoint (trace_id TEXT PRIMARY KEY, data TEXT NOT NULL)"
DDL_HISTORY = "CREATE TABLE IF NOT EXISTS checkpoint_history (trace_id TEXT NOT NULL, step INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY (trace_id, step))"


class SqliteCheckpointStore:
    """Stdlib-sqlite CheckpointStore — survives process restart (the point of 'durable'). One row per
    trace_id; the checkpoint is read/written whole, so it's stored as a single JSON blob. pgvector/Redis
    stores implement the same CheckpointStore contract later with zero loop change."""
    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path)
        self.db.execute(DDL)
        self.db.execute(DDL_HISTORY)
        self.db.commit()

    def save(self, cp: Checkpoint) -> None:
        p = cp.pending
        data = json.dumps({
            "version": 1,        # forward-compat marker; load() reads specific keys, tolerates its absence in old blobs.
            "trace_id": cp.trace_id, "task": cp.task, "instructions": cp.instructions,
            "history": cp.history, "usage_in": cp.usage_in, "usage_out": cp.usage_out, "step": cp.step,
            "config": cp.config,
            "pending": None if p is None else {"prompt": p.prompt, "key": p.key, "kind": p.kind,
                                               "tool_name": p.tool_name, "tool_call_id": p.tool_call_id,
                                               "human_prompt": p.human_prompt},
        })
        self.db.execute("INSERT OR REPLACE INTO checkpoint(trace_id, data) VALUES(?, ?)", (cp.trace_id, data))
        self.db.execute("INSERT OR REPLACE INTO checkpoint_history(trace_id, step, data) VALUES(?,?,?)", (cp.trace_id, cp.step, data))
        self.db.commit()

    @staticmethod
    def _decode(data: str) -> Checkpoint:
        # Forward-compat: we read specific keys below and never require `version`, so a blob WITH the
        # marker and an old blob WITHOUT it both load. (d.get("version", 1) is the schema rev when present.)
        d = json.loads(data)
        pend = d["pending"]
        return Checkpoint(
            trace_id=d["trace_id"], task=d["task"], instructions=d["instructions"],
            history=d["history"], usage_in=d["usage_in"], usage_out=d["usage_out"], step=d["step"],
            config=d.get("config"),    # old blobs lack it -> None (resume skips the drift check)
            pending=None if pend is None else HumanRequest(
                prompt=pend["prompt"], key=pend["key"], kind=pend["kind"],
                tool_name=pend["tool_name"], tool_call_id=pend["tool_call_id"],
                human_prompt=pend.get("human_prompt"),    # old blobs lack it → None (byte-identical when unset)
            ),
        )

    def load(self, trace_id: str) -> Checkpoint | None:
        row = self.db.execute("SELECT data FROM checkpoint WHERE trace_id=?", (trace_id,)).fetchone()
        if row is None:
            return None
        return self._decode(row[0])

    def history(self, trace_id: str) -> list[Checkpoint]:
        rows = self.db.execute("SELECT data FROM checkpoint_history WHERE trace_id=? ORDER BY step", (trace_id,)).fetchall()
        return [self._decode(r[0]) for r in rows]

    def delete(self, trace_id: str) -> None:
        self.db.execute("DELETE FROM checkpoint WHERE trace_id=?", (trace_id,))
        self.db.execute("DELETE FROM checkpoint_history WHERE trace_id=?", (trace_id,))
        self.db.commit()
