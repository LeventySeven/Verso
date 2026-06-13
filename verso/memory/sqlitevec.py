# verso/memory/sqlitevec.py
from __future__ import annotations
import json

from verso.memory.sqlite import SqliteBackend
from verso.memory.embed import Embedder

_VEC_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS vec_memory USING vec0(embedding float[{dim}]);
-- keep the ANN index in lockstep with `memory`, exactly like memory_fts: insert adds, delete/evict removes.
CREATE TRIGGER IF NOT EXISTS memory_vec_ai AFTER INSERT ON memory BEGIN
  INSERT INTO vec_memory(rowid, embedding) VALUES (new.rowid, new.embedding);
END;
CREATE TRIGGER IF NOT EXISTS memory_vec_ad AFTER DELETE ON memory BEGIN
  DELETE FROM vec_memory WHERE rowid = old.rowid;
END;
"""


class SqliteVecBackend(SqliteBackend):
    """SqliteBackend with the brute-force vector arm replaced by a sqlite-vec (vec0) ANN index — the
    drop-in scale path for the vector half of RRF. Same MemoryBackend contract (FTS5 lexical + vector
    RRF, temporal/TTL, success-downweight, bounded, `recent`); only `_vector_rank` changes. The vec0
    index is kept in lockstep with `memory` by triggers, exactly like memory_fts.

    Requires the optional `sqlite-vec` package (`pip install 'verso[vec]'`); the brute-force
    SqliteBackend needs no extra dependency, so this is opt-in for when a corpus outgrows linear scan."""
    def __init__(self, path: str = ":memory:", *, embedder: Embedder, max_records: int = 10_000):
        try:
            import sqlite_vec
        except ImportError as e:   # pragma: no cover
            raise ImportError(
                "SqliteVecBackend needs the optional 'sqlite-vec' package — `pip install 'verso[vec]'`."
            ) from e
        super().__init__(path, embedder=embedder, max_records=max_records)  # memory + memory_fts + FTS triggers
        self.db.enable_load_extension(True)
        sqlite_vec.load(self.db)
        self.db.enable_load_extension(False)
        self.db.executescript(_VEC_DDL.format(dim=embedder.dim))            # vec0 index + its sync triggers
        self.db.commit()

    def _vector_rank(self, live, embedding) -> dict:
        # vec0's default L2 distance is rank-equivalent to cosine for the protocol's L2-normalized
        # embeddings (what HashEmbedder produces), so this fuses with the lexical arm identically.
        live_ids = {r["rowid"] for r in live}
        # KNN over the ANN index. invalidate() is a soft UPDATE, so invalidated rows still sit in
        # vec_memory — over-fetch a candidate pool and filter to live. Live rows beyond the pool fall
        # back to the RRF default rank (a vector-distant record contributes ~nothing to the fused score).
        pool = max(len(live) * 4, 64)
        rows = self.db.execute(
            "SELECT rowid FROM vec_memory WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
            (json.dumps(embedding), pool)).fetchall()
        order = [r["rowid"] for r in rows if r["rowid"] in live_ids]
        return {rid: i for i, rid in enumerate(order)}
