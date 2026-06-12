# verso/memory/types.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class MemoryType(str, Enum):
    SCRATCHPAD = "scratchpad"   # TTL ~1h
    EPISODIC = "episodic"       # TTL ~7d
    FACT = "fact"               # permanent
    PROCEDURAL = "procedural"   # permanent (reserved; populated in a later plan)


# Per-type default TTL in seconds (None = permanent). Enforced by the backend.
TTL_SECONDS: dict[MemoryType, int | None] = {
    MemoryType.SCRATCHPAD: 3600,
    MemoryType.EPISODIC: 7 * 86400,
    MemoryType.FACT: None,
    MemoryType.PROCEDURAL: None,
}


@dataclass
class MemoryRecord:
    id: str
    type: MemoryType
    content: str
    scope: str = "default"              # user_id / agent_id / run_id, joined — auto-injected by Memory
    importance: float = 0.5             # written ONCE at store time, never re-scored on read
    outcome: str | None = None          # "success" | "failure" | None — success is down-weighted on recall
    valid_at: float = 0.0               # store time (epoch seconds; injected, not wall-clock-at-read)
    invalid_at: float | None = None     # set on supersession; record is never deleted, only invalidated
    embedding: list[float] = field(default_factory=list)


# The locked DDL — the durable contract. Backends implement this shape (sqlite here; pgvector later).
DDL = """
CREATE TABLE IF NOT EXISTS memory (
  id TEXT PRIMARY KEY, type TEXT NOT NULL, content TEXT NOT NULL, scope TEXT NOT NULL,
  importance REAL NOT NULL, outcome TEXT, valid_at REAL NOT NULL, invalid_at REAL, embedding TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(content, content='memory', content_rowid='rowid');
-- keep the external-content FTS index in lockstep with `memory`: insert adds terms, delete/evict removes them.
CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memory BEGIN
  INSERT INTO memory_fts(rowid, content) VALUES (new.rowid, new.content);
END;
CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memory BEGIN
  INSERT INTO memory_fts(memory_fts, rowid, content) VALUES('delete', old.rowid, old.content);
END;
CREATE INDEX IF NOT EXISTS memory_scope ON memory(scope, type);
"""
