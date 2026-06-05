# Retrieval + Vector/Memory Backend Edge — Verso Design Resolution

**Subsystem:** `memory/retrieval.py` + `memory/backend.py` (‹edge2›)
**Date:** 2026-06-05
**Evidence base:** `03_teardowns/infra-retrieval-vector.md` (source-first RE of Qdrant, Chroma, pgvector,
pgvectorscale, Weaviate, Milvus/Knowhere, Vespa, sqlite-vec — all cloned `--depth=1`, read line-by-line);
`03_teardowns/infra-vector-memory.md` (Turbopuffer + LanceDB); `03_teardowns/_SYNTHESIS.md` §3;
PRD v1 §5.4, §4.2, §10.

Label key: **KNOWN** = read at cited file:line. **INFERRED** = derived from code + docs. **DESIGNED** = our
engineering filling a gap.

---

## Decisions Resolved

### Decision 1 — RRF k constant: k=60 (not k=2)

**Choice:** Default `k = 60` for Verso's built-in RRF fuser, exposed as a tunable constant.

**Rationale:**
The teardown surfaces a genuine disagreement across systems: Weaviate hard-codes k=60 (`hybrid_fusion.go:31`:
`score := float32(weights[resultSetIndex] / float64(i+60))`), pgvector's SQL idiom uses k=60, LanceDB ships
k=60 as its only built-in reranker, and the 2009 Cormack paper that introduced RRF uses k=60. Qdrant's compiled
production default is k=2 (`reciprocal_rank_fusion.rs:14: pub const DEFAULT_RRF_K: usize = 2`), which was
verified at source and is a deliberate contrarian choice: with weight=1 the formula gives top-rank score = 0.5.
The synthesis brief (`_SYNTHESIS.md` §3) resolves this: "LanceDB RRF k=60 as default hybrid reranker —
everywhere." The four-system majority (Weaviate, LanceDB, LangChain `EnsembleRetriever.c=60`, pgvector SQL)
is the literature value and the community expectation. Qdrant's k=2 is an extreme that makes small rank
differences huge — useful when you want a steep top-heavy score curve but not as a user-visible default where
"k=60 matches RRF papers" is the mental model. Expose k as a parameter so power users can reproduce either
behaviour.

**Evidence:**
- Weaviate k=60 hard-coded: `hybrid_fusion.go:31` (`infra-retrieval-vector.md §Weaviate`)
- Qdrant k=2 production default: `reciprocal_rank_fusion.rs:14` + REST conversion
  `shard/src/query/conversions.rs:189-205` (`infra-retrieval-vector.md §Qdrant CORRECTION`)
- LanceDB k=60: `infra-vector-memory.md` + `_SYNTHESIS.md §3` RRF bullet
- pgvector SQL CTE uses `1/(60 + rank)` as an explicit SQL constant (`infra-retrieval-vector.md §pgvector`)

**Alternatives rejected:**
- k=2 (Qdrant default): correct at the algorithm level but will surprise every user coming from the literature
  or LangChain. Keep it as a documented alternative / "steep" preset.
- Learnable k: Weaviate Cloud roadmap; not in open-source; deferred to dogfood.

---

### Decision 2 — Hybrid fusion: ship both RRF (rank-only) AND DBSF/relative-score, not just one

**Choice:** Two built-in fusers, selected by `fusion_mode` parameter:
- `"rrf"` (default) — Reciprocal Rank Fusion, rank-only, robust to scale mismatch between cosine and BM25.
  Exact algebra (from Qdrant source, generalised): `score(pos, k, w) = 1/((pos+1)/w + k - 1)`.
  Default weight `w=1`, so rank-0 contributes `1/k`.
- `"dbsf"` — Distribution-Based Score Fusion, score-aware, for calibrated score scales.
  Per-leg Welford ±3σ normalization: `norm = (score - (mean - 3σ)) / ((mean + 3σ) - (mean - 3σ))`.
  Single-item legs collapse to 0.5. Sum normalized scores per id, sort descending.

**Rationale:**
Every system that ships hybrid search ships exactly these two fuser archetypes: Qdrant (RRF / DBSF),
Weaviate (`rankedFusion` k=60 / `relativeScoreFusion` min-max), Turbopuffer (weighted Product/Sum algebra).
The cross-system agreement is the signal — not any single vendor. RRF is the right default because cosine
similarity and BM25 scores live on incomparable scales; DBSF is the right upgrade path once scores are
calibrated (e.g. when the embedding model and BM25 are both tuned to the same corpus). Shipping only RRF
blocks the DBSF upgrade path; shipping only DBSF is wrong for new users with raw cosine+BM25.

**Evidence:**
- Qdrant two fusers: `lib/collection/src/shards/local_shard/query.rs:424-451` (dispatch),
  `lib/segment/src/common/reciprocal_rank_fusion.rs` (RRF), `lib/segment/src/common/score_fusion.rs` (DBSF)
  (`infra-retrieval-vector.md §Qdrant`)
- Weaviate two fusers: `usecases/traverser/hybrid/hybrid_fusion.go:22-81` (ranked) and `:93-182` (relative)
  (`infra-retrieval-vector.md §Weaviate`)
- `_SYNTHESIS.md §3`: "Two-tool MCP retrieval shape" + cross-system unanimous two-fuser pattern

**Alternatives rejected:**
- Turbopuffer's composable `rank_by` DSL (a full expression algebra): powerful but requires a DSL parser
  and is overkill for Verso v1. Adopt as a future "advanced hybrid" escape hatch.
- Min-max normalization (Weaviate relativeScoreFusion): subsumed by DBSF (±3σ is more robust than min-max
  when outliers exist). Weaviate's min-max collapses to 0.5 when all scores equal; DBSF handles this the
  same way. Ship DBSF only.
- Learned/neural fusion: not in any open-source repo; Weaviate Cloud roadmap only. Deferred.

---

### Decision 3 — RRF weight algebra: weight divides position (Qdrant formula), not multiplies score

**Choice:** Adopt Qdrant's exact weighting formula verbatim:
`score(pos, k, w) = 1 / ((pos + 1) / w + k - 1)`.

The `alpha` single-knob API decomposes to `weights = [alpha, 1 - alpha]` (Weaviate pattern),
default `alpha = 0.75` (favour semantic over keyword, per Weaviate default).

**Rationale:**
The Qdrant formula has a non-obvious but important property: weight does *not* multiply the final score
(which is dimensionless anyway); it *divides the position* before adding k. A weight ratio of 3:1 means
"for every 3 results from leg A, take 1 from leg B" — a clean, interpretable knob. The test
`test_rrf_scoring_weighted_ratio` in `reciprocal_rank_fusion.rs` verifies this semantics explicitly.
Weaviate's `alpha → [alpha, 1-alpha]` decomposition is the user-facing API: one dial (0=pure keyword,
1=pure semantic, 0.75=default). Behind the dial, the formula is Qdrant's. This gives Verso both the
intuitive single knob and the correct multi-weight algebra.

**Evidence:**
- Formula: `reciprocal_rank_fusion.rs:38`: `1.0 / ((position + 1) as f32 / weight + k as f32 - 1.0)`
- Semantics test: `test_rrf_scoring_weighted_ratio` in the same file
- Alpha decomposition: Weaviate `searcher.go:75-124`, weights = `[alpha, 1-alpha]`
  (`infra-retrieval-vector.md §Weaviate`)

---

### Decision 4 — Unified hybrid (Qdrant Query API / prefetch tree) vs two-pass merge

**Choice:** Adopt the **Query API prefetch-tree model** as the internal architecture of `HybridSearch`,
but expose it as a single Python call with `alpha` + `fusion_mode`. The tree is an implementation detail;
users never author prefetch nodes.

The internal representation:
```python
# internal HybridQuery — not the user-facing API
@dataclass
class HybridQuery:
    dense_leg: DenseLeg           # embedding + HNSW/brute-force
    sparse_leg: SparseLeg | None  # BM25 inverted index (opt-in per backend)
    fusion: FusionMode            # "rrf" | "dbsf"
    alpha: float                  # [0,1]; 0 = pure keyword, 1 = pure semantic
    k: int                        # RRF constant, default 60
    top_k: int                    # final result count
    filters: list[Filter]         # typed-memory filters, pushed to backend
    rerank_phase: RerankConfig | None  # optional second-phase reranker (Vespa pattern)
```

**Rationale:**
The Qdrant Query API (prefetch tree → parent fusion) is the cleanest published single-request hybrid model:
one server round-trip, no client-side merge, the tree is composable for multi-hop agents. The two-pass model
(LanceDB: run FTS → run ANN → client-side RRF) requires two network hops in the distributed case and loses
server-side score information. However, Verso v1's backends (sqlite-vec embedded, pgvector) do not natively
support server-side prefetch trees — sqlite-vec is brute-force only and pgvector's hybrid is a SQL CTE.
The right call: adopt the tree as the *internal query representation* (so Qdrant can push the whole tree
server-side when it's the backend) while falling back to a client-side merge for sqlite-vec/pgvector.
The user API never changes.

**Evidence:**
- Qdrant prefetch tree: `lib/collection/src/shards/local_shard/query.rs:424-451`; recursive `QueryRequest`
  with `prefetch: Vec<Prefetch>` (`infra-retrieval-vector.md §Qdrant`)
- Weaviate alpha decomposition runs two closures then fuses: `searcher.go:75-124` (two-pass, client-fuse)
- `_SYNTHESIS.md §3 Improve #4`: "HybridSearch tool type with a declarative rank_by DSL and pluggable
  backends"

---

### Decision 5 — Asymmetric embeddings: preserve source ≠ query embeddings at the store boundary

**Choice:** The backend adapter interface takes two separate `EmbedFn` callables:
`embed_document(text: str) -> list[float]` and `embed_query(text: str) -> list[float]`.
They are allowed to be the same function (symmetric models) but they are **never collapsed by default**.
The `Memory` class stores document embeddings at write time using `embed_document` and produces query
embeddings at search time using `embed_query`.

**Rationale:**
The synthesis brief flags this as a correctness issue: "LanceDB separates `compute_source_embeddings` from
`compute_query_embeddings` (E5/BGE prefixes differ). Collapsing them silently degrades retrieval for
asymmetric models." (`_SYNTHESIS.md §3 asymmetric bullet`). Models like E5-mistral, BGE-M3, and any
instruction-tuned bi-encoder use different prefixes for passage vs query encoding. If the framework collapses
them at the API boundary, every asymmetric model silently degrades. The fix is structural: two callables,
not one.

**Evidence:**
- LanceDB separate compute functions: `infra-vector-memory.md §LanceDB` + `_SYNTHESIS.md §3`
- E5/BGE prefix difference: documented in those model cards (INFERRED from teardown mention)

---

### Decision 6 — Embedded↔distributed storage seam: mirror Chroma's PyO3 Frontend pattern

**Choice:** `MemoryStore` is constructed from a `StoreConfig` union. The same `MemoryStore` class handles
both; the difference is **which implementations are injected at construction**:

```python
StoreConfig = EmbeddedStoreConfig | PostgresStoreConfig | QdrantStoreConfig

@dataclass
class EmbeddedStoreConfig:
    persist_path: Path | None = None   # None → pure in-memory (ephemeral)
    hnsw_cache_size: int = 256         # vectors in memory for small stores

@dataclass
class PostgresStoreConfig:
    dsn: str
    read_level: ReadLevel = ReadLevel.INDEX_AND_WAL
    # uses pgvector HNSW + ts_tsvector BM25 in a SQL CTE
    # memory rows colocated with checkpoints in the same DB

@dataclass
class QdrantStoreConfig:
    url: str
    collection: str
    api_key: str | None = None
    # uses Qdrant Query API prefetch tree server-side
    read_level: ReadLevel = ReadLevel.INDEX_AND_WAL
```

The `MemoryStore.search()` / `.remember()` / `.recall()` interface is **identical** across all three.

**Rationale:**
Chroma's PyO3 `bindings.rs:79-160` is the verified template: one `Frontend` class, four injected config
enums (`SysDbConfig`, `LogConfig`, `ExecutorConfig`, `LocalSegmentManagerConfig`) — swapping them moves
from embedded SQLite to distributed gRPC without changing the request handlers. The PRD's tactical↔durable
seam analogy applies directly: `EmbeddedStoreConfig` with `persist_path=None` is Verso's in-memory
tactical memory (test / dev / ephemeral agents); `EmbeddedStoreConfig(persist_path=...)` is the dev
persistent tier (sqlite-vec WAL); `PostgresStoreConfig` is the durable colocated tier (no new infra);
`QdrantStoreConfig` is the distributed scale tier. The user writes `Memory(store=EmbeddedStoreConfig())`
and upgrades to `Memory(store=PostgresStoreConfig(dsn=...))` without touching agent code.

**Evidence:**
- Chroma seam: `rust/python_bindings/src/bindings.rs:38-160` (`infra-retrieval-vector.md §Chroma seam`)
- PRD §4.1 tactical↔durable seam as organizing principle
- `_SYNTHESIS.md §3`: "Pluggable memory backend, no hard DB pin" + Letta anti-pattern (mandatory pgvector)

---

### Decision 7 — Default backend progression: sqlite-vec → pgvector colocated → Qdrant

**Choice:**
| Tier | Backend | When | Key property |
|---|---|---|---|
| Dev / embedded | `sqlite-vec` (EmbeddedStoreConfig) | default, zero install | no infra; brute-force below 10k is fine |
| Prod colocated | `pgvector` (PostgresStoreConfig) | user already has Postgres for checkpoints | memories share DB with HITL/checkpoint log |
| Distributed scale | `Qdrant` (QdrantStoreConfig) | >100k memories or multi-tenant | Query API prefetch tree + ACORN filtered ANN |

**Rationale:**
sqlite-vec is "the minimum viable embedded backend — adopt as-is" (teardown conclusion). `pip install sqlite-vec`,
`vec.load(conn)`, one virtual table, zero infra. Brute-force below ~10k vectors is correct and confirmed by
Qdrant's `full_scan_threshold = 10_000` constant — Qdrant itself skips HNSW for small segments. The graduation
path is deliberate: pgvector colocates memories with the Postgres checkpoint store (PRD §6.1), so a user who
has already paid the "run Postgres" infra cost gets memory for free — no new service. Qdrant is the scale
option and the only backend that natively executes the prefetch-tree hybrid server-side; it also has the
best filtered ANN (ACORN). Omitting a Chroma backend for now is intentional — Chroma's Python-embedded mode
would work but sqlite-vec is lighter and WAL3 (distributed Chroma) is not worth operating vs Qdrant.

**Evidence:**
- sqlite-vec "adopt as-is" recommendation: `infra-retrieval-vector.md §sqlite-vec For Verso`
- Qdrant `full_scan_threshold = 10_000`: `lib/segment/src/types.rs:1872` (KNOWN)
- pgvector zero-new-infra case: `infra-retrieval-vector.md §pgvector For Verso`
- PRD §5.4 explicitly lists the same three tiers
- `_SYNTHESIS.md §3`: "SQLite+sqlite-vec for dev, Postgres+pgvector for prod"

---

### Decision 8 — BM25 sparse leg: per-corpus tunable k1/b with documented defaults

**Choice:** Ship `BM25Config(k1: float = 1.2, b: float = 0.75)` as the BM25 leg configuration, attached
to the `SparseLeg` of `HybridQuery`. Both parameters are corpus-level tunables (set once per MemoryStore
collection, not per query). For the sqlite-vec embedded backend, BM25 is implemented via SQLite FTS5 with
these parameters passed as FTS5 table configuration. For pgvector, BM25 is `ts_rank_cd` (PostgreSQL full-text
search — not parametric over k1/b, but the default Robertson values are the right starting point). For Qdrant,
BM25 is the sparse-vector index (k1/b configurable at collection creation).

`k1 = 1.2` and `b = 0.75` are confirmed as Weaviate's defaults (`usecases/config/config_handler.go:57-58`)
and are the standard Robertson 1994 values used across Elasticsearch, Lucene, and Qdrant.

**Rationale:**
The synthesis brief explicitly flags "Tunable per-corpus BM25" as a required feature and "hardcoded BM25
params" as an anti-pattern (`_SYNTHESIS.md §3 Avoid #2`). Turbopuffer exposes k1/b unlike Tantivy which
hardcodes them. The teardown confirms Weaviate ships `k1=1.2, b=0.75` as configurable defaults. Verso should
adopt these defaults verbatim but expose them — "per-corpus" means set at collection/store creation, not
globally baked in.

**Evidence:**
- Weaviate `k1=1.2, b=0.75`: `usecases/config/config_handler.go:57-58` (KNOWN)
- `_SYNTHESIS.md §3 Avoid #2`: "hardcoded BM25"
- Turbopuffer k1/b configurable: `full_text_search_config_param.py` (`infra-vector-memory.md`)

---

### Decision 9 — Phased reranking: adopt Vespa's three-phase funnel as `RerankConfig`

**Choice:** The `HybridQuery.rerank_phase` field takes an optional `RerankConfig`:

```python
@dataclass
class RerankConfig:
    rerank_top_n: int = 20          # run expensive reranker over top-N from phase 1
    score_drop_limit: float | None = None  # discard below this score before rerank
    reranker: Reranker = CrossEncoderReranker()   # or LLMJudgeReranker, IdentityReranker
```

Phase 1 is the cheap hybrid (ANN + BM25 fused). Phase 2 is the reranker over `rerank_top_n` candidates.
Phase 3 (global merge across shards) is deferred — Verso v1 is single-shard.

**Rationale:**
Vespa's three declared phases (`ranksetup.h:445,448`; `GlobalPhaseRanker.java:57`) are the reference design
for "retrieve then rerank" as a first-class tunable pipeline rather than a bolted-on step. The key insight:
each phase has its own `rerank_count` + `score_drop_limit` (discard hits below a threshold *before* feeding
the next phase — Vespa's `_first_phase_rank_score_drop_limit` at `:64`). Carrying dead-weight candidates
into an expensive cross-encoder wastes compute. The teardown recommends: "phase-1 cheap ANN shortlist →
phase-2 expensive rerank over top-N with task context → optional global merge."

pgvectorscale's `query_rescore = 50` (exact-rescore the top-50 SBQ-approximate candidates) is the same
pattern at the index level — traverse on quantized codes, exact-rerank the shortlist. Verso generalises
this to any pluggable reranker.

**Evidence:**
- Vespa three phases: `searchlib/src/vespa/searchlib/fef/ranksetup.h:445,448,64,65` (KNOWN)
- pgvectorscale `query_rescore=50`: `pgvectorscale/src/access_method/guc.rs` (KNOWN)
- `_SYNTHESIS.md §3`: "Phased ranking as a declared pipeline, not a bolted-on reranker"

---

### Decision 10 — Typed-memory filters: use backend's native filtered-ANN mechanism

**Choice:** Verso's typed-memory tags (`memory_type`, `agent_id`, `session`, `run_id`) are mapped to
backend-native filter mechanisms:

| Backend | Filter mechanism | Recall strategy |
|---|---|---|
| sqlite-vec | `partition key` column (chunk-level prune) + `metadata` column (row-level filter) | brute-force, no recall collapse |
| pgvector | `WHERE` clause on indexed columns; pgvectorscale `smallint[]` labels + intersection-gated RobustPrune | label-aware graph, no recall collapse |
| Qdrant | `payload` filter + ACORN traversal when selectivity ≤ 0.4 | 2-hop ACORN expansion, no recall collapse |

The `MemoryStore.recall()` API takes typed filter kwargs (`memory_type=...`, `agent_id=...`, etc.);
the backend adapter translates these to its native filter representation before the ANN query.

**Rationale:**
"Post-filter an unfiltered ANN result" is explicitly listed as the wrong approach in the teardown
(`infra-retrieval-vector.md §Cross-System Synthesis` — all backends beat post-filtering). Each backend
has a purpose-built mechanism: sqlite-vec's `partition key` column prunes whole 1024-vector chunks for
`session_id` filters; pgvectorscale's label-aware RobustPrune keeps the graph navigable for filtered
queries; Qdrant's ACORN expands through filtered-out nodes when selectivity ≤ 40%. Verso should pass
filters to the backend rather than filtering in Python after retrieval.

**Evidence:**
- sqlite-vec partition key + metadata columns: `sqlite-vec.c:4556-4566`, `:6141-6318` (KNOWN)
- pgvectorscale label-aware prune: `graph/mod.rs:451-460`, `labels/mod.rs:192,230` (KNOWN)
- Qdrant ACORN: `lib/segment/src/index/hnsw_index/hnsw/search.rs:37-83`,
  `ACORN_MAX_SELECTIVITY_DEFAULT = 0.4` from `types.rs:556` (KNOWN)

---

### Decision 11 — Read consistency: three ReadLevels as a per-query knob (Chroma pattern)

**Choice:**
```python
class ReadLevel(enum.Enum):
    INDEX_ONLY = "index_only"           # eventual: skip WAL, fast
    INDEX_AND_WAL = "index_and_wal"     # default: full consistency, index + uncompacted log
    BOUNDED_WAL = "bounded_wal"         # bounded latency: index + up to N recent entries
```

Default: `INDEX_AND_WAL`. Agents doing a quick "do I roughly remember X" can pass `read_level=ReadLevel.INDEX_ONLY`.
Correctness-critical recalls (audit trail, HITL context) use `INDEX_AND_WAL`.

**Rationale:**
Chroma's three `ReadLevel` enum variants (`types/execution/plan.rs:550-565`) implement exactly this tradeoff
and are the verified template. The `INDEX_ONLY` path (`knn_filter.rs:355`) skips the WAL fetch entirely and
searches only compacted segments — cheaper, may miss the last few seconds of writes. `INDEX_AND_WAL` fetches
uncompacted log fragments and merges with index results. The per-query knob is the right level of abstraction:
the agent chooses per-recall, not globally.

**Evidence:**
- Chroma `ReadLevel`: `rust/types/src/execution/plan.rs:550-565` (KNOWN)
- `INDEX_ONLY` implementation: `knn_filter.rs:355` — "use empty logs" branch (KNOWN)
- `infra-retrieval-vector.md §Chroma For Verso`: "Three read levels as a per-query knob"

---

## Component Spec

### 2.1 Public interfaces

```python
# verso/memory/retrieval.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Protocol, Sequence, Any
from collections.abc import AsyncIterator

class FusionMode(Enum):
    RRF = "rrf"    # Reciprocal Rank Fusion — rank-only, default
    DBSF = "dbsf"  # Distribution-Based Score Fusion — score-aware (Qdrant pattern)

class ReadLevel(Enum):
    INDEX_ONLY = "index_only"
    INDEX_AND_WAL = "index_and_wal"   # default
    BOUNDED_WAL = "bounded_wal"

@dataclass
class BM25Config:
    k1: float = 1.2    # Robertson 1994; verified Weaviate default (config_handler.go:57)
    b: float = 0.75    # Robertson 1994; verified Weaviate default (config_handler.go:58)

@dataclass
class RerankConfig:
    rerank_top_n: int = 20                 # Vespa second-phase over top-N (ranksetup.h:448)
    score_drop_limit: float | None = None  # Vespa _first_phase_rank_score_drop_limit (:64)
    reranker: "Reranker" = field(default_factory=lambda: IdentityReranker())

@dataclass
class HybridQuery:
    text: str
    embedding: list[float] | None = None   # pre-computed; if None, embed_query() called
    alpha: float = 0.75                    # 0=pure BM25, 1=pure ANN; Weaviate default
    fusion_mode: FusionMode = FusionMode.RRF
    rrf_k: int = 60                        # RRF constant; k=60 = literature default
    top_k: int = 10
    read_level: ReadLevel = ReadLevel.INDEX_AND_WAL
    filters: dict[str, Any] = field(default_factory=dict)  # memory_type/agent_id/session etc.
    bm25: BM25Config = field(default_factory=BM25Config)
    rerank: RerankConfig | None = None

@dataclass
class MemoryHit:
    id: str
    content: str
    score: float                   # fused score (RRF or DBSF)
    memory_type: str
    agent_id: str | None
    session_id: str | None
    run_id: str | None
    valid_at: "datetime"
    confidence: float
    embedding: list[float] | None = None   # returned only if include_vectors=True
    metadata: dict[str, Any] = field(default_factory=dict)

class Reranker(Protocol):
    async def rerank(self, query: str, hits: list[MemoryHit]) -> list[MemoryHit]: ...

class BackendAdapter(Protocol):
    """‹edge2› — the pluggable backend interface."""
    async def upsert(self, items: list["MemoryItem"]) -> None: ...
    async def delete(self, ids: list[str]) -> None: ...
    async def search(self, query: HybridQuery) -> list[MemoryHit]: ...
    async def get(self, id: str) -> "MemoryItem | None": ...
    async def list_by_filter(self, filters: dict[str, Any], limit: int = 100) -> list["MemoryItem"]: ...
    async def close(self) -> None: ...
```

```python
# verso/memory/backend.py — StoreConfig union + factory

from dataclasses import dataclass
from pathlib import Path

@dataclass
class EmbeddedStoreConfig:
    """sqlite-vec — zero infra, brute-force, dev/test/ephemeral."""
    persist_path: Path | None = None  # None → in-memory (no WAL)
    hnsw_cache_size: int = 256         # vectors in HNSW cache above full_scan_threshold
    full_scan_threshold: int = 10_000  # below this → brute-force (mirrors Qdrant :1872)
    chunk_size: int = 1024             # sqlite-vec vec0 chunk size (:5140)

@dataclass
class PostgresStoreConfig:
    """pgvector colocated with checkpoint DB — no new infra."""
    dsn: str
    table_prefix: str = "verso_memory"
    # HNSW defaults from pgvector src/hnsw.h verbatim:
    hnsw_m: int = 16                  # hnsw.h:46
    hnsw_ef_construction: int = 64    # hnsw.h:49
    hnsw_ef_search: int = 40          # hnsw.h:52 — GUC hnsw.ef_search
    # DiskANN (pgvectorscale) defaults if extension available:
    diskann_num_neighbors: int = 50   # options.rs:39 sentinel → 50
    diskann_search_list: int = 100    # options.rs:39
    diskann_rescore: int = 50         # guc.rs — query_rescore
    read_level: ReadLevel = ReadLevel.INDEX_AND_WAL

@dataclass
class QdrantStoreConfig:
    """Qdrant — distributed, prefetch-tree hybrid, ACORN filtered ANN."""
    url: str
    collection: str
    api_key: str | None = None
    # HNSW defaults from Qdrant lib/segment/src/types.rs verbatim:
    hnsw_m: int = 16                   # types.rs:1411 HnswConfig.m
    hnsw_ef_construct: int = 100       # types.rs:1409 DEFAULT_HNSW_EF_CONSTRUCT
    hnsw_full_scan_threshold: int = 10_000  # types.rs:1872
    # Quantization default: scalar int8, quantile=0.99, rescore=True
    quantization_quantile: float = 0.99
    quantization_rescore: bool = True
    read_level: ReadLevel = ReadLevel.INDEX_AND_WAL

StoreConfig = EmbeddedStoreConfig | PostgresStoreConfig | QdrantStoreConfig

def make_backend(config: StoreConfig, embed_doc: "EmbedFn", embed_query: "EmbedFn") -> BackendAdapter:
    """Factory — same interface, different implementation injected. Mirrors Chroma's bindings.rs:79-160."""
    match config:
        case EmbeddedStoreConfig():
            from verso.memory.backends.sqlite_vec import SqliteVecBackend
            return SqliteVecBackend(config, embed_doc, embed_query)
        case PostgresStoreConfig():
            from verso.memory.backends.pgvector import PgvectorBackend
            return PgvectorBackend(config, embed_doc, embed_query)
        case QdrantStoreConfig():
            from verso.memory.backends.qdrant import QdrantBackend
            return QdrantBackend(config, embed_doc, embed_query)
```

---

### 2.2 Schema (sqlite-vec backend — the dev tier)

```sql
-- Created by SqliteVecBackend.initialize()
-- sqlite-vec virtual table for vector search
CREATE VIRTUAL TABLE IF NOT EXISTS verso_memory_vss USING vec0(
    embedding float[{dims}],                -- dimension from embed_doc output
    agent_id integer partition key,         -- chunk-level prune (sqlite-vec.c:4556)
    session_id integer partition key,       -- chunk-level prune
    memory_type integer metadata,           -- row-level filter (sqlite-vec.c:2388)
    importance float metadata               -- row-level filter for score boosting
);

-- Canonical memory row store (payload + temporal versioning)
CREATE TABLE IF NOT EXISTS verso_memory (
    id          TEXT PRIMARY KEY,
    content     TEXT NOT NULL,
    memory_type TEXT NOT NULL DEFAULT 'episodic',
    agent_id    TEXT,
    session_id  TEXT,
    run_id      TEXT,
    valid_at    TEXT NOT NULL,         -- ISO-8601
    invalid_at  TEXT,                  -- NULL = currently valid
    expired_at  TEXT,                  -- TTL-driven expiry
    confidence  REAL NOT NULL DEFAULT 1.0,
    importance  REAL NOT NULL DEFAULT 0.5,   -- computed once at write
    metadata    TEXT NOT NULL DEFAULT '{}'   -- JSON blob
);

-- BM25 full-text index (SQLite FTS5)
-- k1=1.2 b=0.75 are passed as FTS5 table config
CREATE VIRTUAL TABLE IF NOT EXISTS verso_memory_fts USING fts5(
    content,
    content=verso_memory,
    content_rowid=rowid,
    tokenize='porter unicode61',
    -- note: FTS5 does not expose k1/b directly; store via user_version pragma or app config
    prefix='2 3'
);

CREATE INDEX IF NOT EXISTS idx_memory_type     ON verso_memory(memory_type);
CREATE INDEX IF NOT EXISTS idx_memory_agent    ON verso_memory(agent_id);
CREATE INDEX IF NOT EXISTS idx_memory_session  ON verso_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_memory_valid    ON verso_memory(valid_at, invalid_at);
```

---

### 2.3 Schema (pgvector backend — the prod colocated tier)

```sql
-- Created by PgvectorBackend.initialize()
-- Requires: CREATE EXTENSION IF NOT EXISTS vector;
--           CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- for ts_rank_cd

CREATE TABLE IF NOT EXISTS verso_memory (
    id           TEXT PRIMARY KEY,
    content      TEXT NOT NULL,
    embedding    vector({dims}) NOT NULL,   -- pgvector type
    memory_type  TEXT NOT NULL DEFAULT 'episodic',
    agent_id     TEXT,
    session_id   TEXT,
    run_id       TEXT,
    valid_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    invalid_at   TIMESTAMPTZ,
    expired_at   TIMESTAMPTZ,
    confidence   REAL NOT NULL DEFAULT 1.0,
    importance   REAL NOT NULL DEFAULT 0.5,
    metadata     JSONB NOT NULL DEFAULT '{}',
    tsv          TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);

-- HNSW index (pgvector defaults from src/hnsw.h verbatim)
CREATE INDEX IF NOT EXISTS verso_memory_hnsw ON verso_memory
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- BM25 via tsvector (Postgres built-in; k1/b stored in app config, not SQL)
CREATE INDEX IF NOT EXISTS verso_memory_fts ON verso_memory USING GIN (tsv);

CREATE INDEX IF NOT EXISTS idx_mem_type    ON verso_memory(memory_type);
CREATE INDEX IF NOT EXISTS idx_mem_agent   ON verso_memory(agent_id);
CREATE INDEX IF NOT EXISTS idx_mem_session ON verso_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_mem_valid   ON verso_memory(valid_at, invalid_at)
    WHERE invalid_at IS NULL;
```

---

### 2.4 Hybrid search SQL (pgvector backend — the canonical two-leg RRF CTE)

```python
# Adapted from pgvector docs + infra-retrieval-vector.md §pgvector
# k=60 per Weaviate/LanceDB/LangChain majority (not Qdrant's k=2)
HYBRID_QUERY_SQL = """
WITH semantic AS (
    SELECT id,
           RANK() OVER (ORDER BY embedding <=> $1::vector) AS rank
    FROM verso_memory
    WHERE invalid_at IS NULL
      AND {filter_clause}
    ORDER BY embedding <=> $1::vector
    LIMIT {semantic_limit}
),
keyword AS (
    SELECT id,
           RANK() OVER (ORDER BY ts_rank_cd(tsv, plainto_tsquery('english', $2)) DESC) AS rank
    FROM verso_memory
    WHERE invalid_at IS NULL
      AND tsv @@ plainto_tsquery('english', $2)
      AND {filter_clause}
    LIMIT {keyword_limit}
),
fused AS (
    SELECT COALESCE(s.id, k.id) AS id,
           COALESCE({alpha}::float * (1.0 / ({rrf_k} + COALESCE(s.rank, 99999))), 0)
         + COALESCE((1.0 - {alpha}::float) * (1.0 / ({rrf_k} + COALESCE(k.rank, 99999))), 0)
           AS score
    FROM semantic s FULL OUTER JOIN keyword k USING (id)
)
SELECT m.*, f.score
FROM fused f JOIN verso_memory m ON m.id = f.id
ORDER BY f.score DESC
LIMIT $3;
"""
# Parameters: $1 = query_vector (bytes), $2 = query_text, $3 = top_k
# Templated: alpha (default 0.75), rrf_k (default 60), filter_clause, semantic_limit, keyword_limit
# semantic_limit = keyword_limit = max(top_k * 4, 40) — 4× oversample before fusion
```

---

### 2.5 RRF + DBSF fuser (client-side, for sqlite-vec backend and fallback)

```python
# verso/memory/retrieval.py — fusion implementations
# Sources: Qdrant reciprocal_rank_fusion.rs + score_fusion.rs (infra-retrieval-vector.md §Qdrant)

import math
from dataclasses import dataclass

def rrf_fuse(
    legs: list[list[tuple[str, float]]],  # list of [(id, score)] ranked lists
    weights: list[float],
    k: int = 60,                           # default 60 (literature / Weaviate / LanceDB)
) -> list[tuple[str, float]]:
    """
    Qdrant RRF formula: score(pos, k, w) = 1 / ((pos+1)/w + k - 1)
    Source: reciprocal_rank_fusion.rs:38
    Weight divides position, not multiplies score — 3:1 weight = "3 of leg A per 1 of leg B"
    Input scores are ignored; only rank order matters.
    """
    assert len(legs) == len(weights), "one weight per leg"
    accumulated: dict[str, float] = {}
    for leg, w in zip(legs, weights):
        for pos, (id_, _score) in enumerate(leg):
            contribution = 1.0 / ((pos + 1) / w + k - 1)
            accumulated[id_] = accumulated.get(id_, 0.0) + contribution
    return sorted(accumulated.items(), key=lambda x: x[1], reverse=True)


def dbsf_fuse(
    legs: list[list[tuple[str, float]]],  # list of [(id, score)] — scores used
    weights: list[float],
) -> list[tuple[str, float]]:
    """
    Qdrant DBSF: Welford ±3σ normalization per leg, then weighted sum.
    Source: score_fusion.rs ~lines 150 (distr_norm), score_fusion.rs (Sum + Distr config)
    Single-item legs → score 0.5 (no variance).
    """
    assert len(legs) == len(weights)
    accumulated: dict[str, float] = {}
    for leg, w in zip(legs, weights):
        if not leg:
            continue
        # Welford one-pass mean + variance
        n, mean, m2 = 0, 0.0, 0.0
        for _, score in leg:
            n += 1
            delta = score - mean
            mean += delta / n
            m2 += delta * (score - mean)
        variance = m2 / n if n > 1 else 0.0
        sigma = math.sqrt(variance)
        lo, hi = mean - 3 * sigma, mean + 3 * sigma
        span = hi - lo if hi != lo else 1.0
        for id_, score in leg:
            norm = (score - lo) / span if span else 0.5
            norm = max(0.0, min(1.0, norm))  # clamp to [0,1]
            accumulated[id_] = accumulated.get(id_, 0.0) + w * norm
    return sorted(accumulated.items(), key=lambda x: x[1], reverse=True)
```

---

### 2.6 Key constants (collected, do not conflate systems)

| Constant | Value | Source | Backend |
|---|---|---|---|
| `RRF_K_DEFAULT` | **60** | Weaviate `hybrid_fusion.go:31`; LanceDB; pgvector SQL; Cormack 2009 | all |
| `ALPHA_DEFAULT` | 0.75 | Weaviate `searcher.go` alpha default | all |
| `BM25_K1_DEFAULT` | 1.2 | Weaviate `config_handler.go:57` | all |
| `BM25_B_DEFAULT` | 0.75 | Weaviate `config_handler.go:58` | all |
| `FULL_SCAN_THRESHOLD` | 10 000 | Qdrant `types.rs:1872`; sqlite-vec brute-force is correct below this | sqlite-vec, Qdrant |
| `RERANK_TOP_N_DEFAULT` | 20 | DESIGNED (Vespa second-phase pattern; pgvectorscale `query_rescore=50` is higher but covers quantization error — 20 is the right floor for a cross-encoder) | all |
| `OVERSAMPLE_FACTOR` | 4× | DESIGNED (4× top_k fed to each leg before fusion) | SQL CTE |
| `CHUNK_SIZE` | 1 024 | sqlite-vec `sqlite-vec.c:5140` | sqlite-vec |
| pgvector HNSW `m` | 16 | `src/hnsw.h:46` | pgvector |
| pgvector `ef_construction` | 64 | `src/hnsw.h:49` | pgvector |
| pgvector `ef_search` | 40 | `src/hnsw.h:52` | pgvector |
| Qdrant HNSW `m` | 16, `m0=32` | `types.rs:1411` | Qdrant |
| Qdrant `ef_construct` | **100** (NOT 64) | `types.rs:1409` | Qdrant |
| Qdrant `full_scan_threshold` | 10 000 | `types.rs:1872` | Qdrant |
| ACORN selectivity gate | 0.4 | `types.rs:556` | Qdrant |
| pgvectorscale DiskANN `R` | 50 | `options.rs:39` | pgvector (w/ pgvectorscale) |
| pgvectorscale DiskANN `L` | 100 | `options.rs:39` | pgvector (w/ pgvectorscale) |
| pgvectorscale `query_rescore` | 50 | `guc.rs` | pgvector (w/ pgvectorscale) |
| Chroma WAL3 batch interval | 100 ms | `lib.rs:498` | (future distributed tier) |
| Chroma WAL3 batch size | 64 MB | `lib.rs:468` | (future distributed tier) |
| Chroma WAL3 GC grace | 3 600 s | `lib.rs:615` | (future distributed tier) |

---

### 2.7 Composite retrieval scoring

The PRD specifies: `0.5·semantic + 0.3·recency_decay(30d) + 0.2·importance`.
This is a **post-fusion re-rank**, applied to the fused hit list before the optional `RerankConfig` phase:

```python
import math
from datetime import datetime, timezone

def composite_score(
    hit: MemoryHit,
    now: datetime,
    semantic_weight: float = 0.5,
    recency_weight: float = 0.3,
    importance_weight: float = 0.2,
    recency_half_life_days: float = 30.0,
) -> float:
    """
    PRD §5.4: 0.5·semantic + 0.3·recency_decay(30d) + 0.2·importance
    recency_decay = exp(-ln2 * age_days / half_life_days)  — exponential half-life
    importance is computed once at write time and stored in the memory row.
    """
    age_days = (now - hit.valid_at.replace(tzinfo=timezone.utc)).total_seconds() / 86400.0
    recency = math.exp(-math.log(2) * age_days / recency_half_life_days)
    return (
        semantic_weight * hit.score
        + recency_weight * recency
        + importance_weight * hit.confidence * hit.metadata.get("importance", 0.5)
    )
```

This runs client-side after `BackendAdapter.search()` returns its `top_k` hits, before the optional reranker.

---

## Open Unknowns

1. **BM25 in sqlite-vec backend — SQLite FTS5 k1/b exposure.** SQLite FTS5 does not expose k1/b as table
   parameters (they are compiled in). The `BM25Config(k1, b)` will work for Qdrant and the pgvector
   `ts_rank_cd` path, but sqlite-vec dev-mode BM25 will be FTS5-default-tuned. Whether this matters for dev
   use is unknown until dogfood. Mitigation: store k1/b in `user_version` pragma or a config table and
   document the limitation; or implement a custom BM25 scoring function over FTS5 raw term frequencies.

2. **Asymmetric embed function — model selection.** The interface separates `embed_document` and
   `embed_query` but does not prescribe a default model. Verso v1 needs to pick a default (likely
   `nomic-embed-text-v1.5` or `text-embedding-3-small` + matching query prefix). The right choice requires
   dogfood benchmarking against the agent's actual memory corpus. Leave as a `ProviderProfile` field,
   defaulting to `text-embedding-3-small` symmetric until a use case requires asymmetric.

3. **DBSF vs min-max in practice.** The choice of DBSF (±3σ) over Weaviate's min-max is theoretically
   justified (more robust to outliers) but untested on Verso's memory distributions. If memories have heavy
   tails (very high-confidence facts mixed with low-confidence scratchpad entries), ±3σ normalization may
   compress the useful range. Prototype both on a real corpus before committing to DBSF as default.

4. **`score_drop_limit` calibration.** The `RerankConfig.score_drop_limit` needs empirical calibration —
   the right floor depends on the embedding model's score distribution and the corpus. Ship as `None`
   (disabled) by default; expose for power users.

5. **Distributed Chroma as a fourth backend tier.** The WAL3 architecture (object-storage fragments, CAS
   manifest, cursors, 100ms/64MB batching) is a strong fit for a multi-process Verso deployment where
   multiple agents share a memory store. Chroma embedded is already wired through the same `Frontend` —
   upgrading from `EmbeddedStoreConfig` to a Chroma-distributed backend would be adding a fifth
   `StoreConfig` variant. Deferred to Phase 3.

6. **Importance computation at write time.** The composite score uses `importance` stored in the memory row.
   The algorithm for computing importance (LLM-judge? word count? tag-based?) is not specified in the PRD.
   This is a first-class design decision that affects memory quality. Deferred to dogfood — ship 0.5
   (uniform) as the v1 default, with a hook (`on_write_importance: Callable[[MemoryItem], float] | None`)
   for overriding.

7. **RRF k=60 vs k=2 for short recall lists.** With small `top_k` (e.g. 5), k=60 compresses rank
   differences significantly: rank-0 → 1/60 = 0.017, rank-4 → 1/64 = 0.016 (only 6% difference).
   k=2 gives rank-0 → 0.5, rank-4 → 0.167 (3× difference). For Verso's default `top_k=10` this matters.
   Dogfood the k default; consider exposing a `"steep"` preset that sets k=2 for users who want strong
   rank-position weighting.
