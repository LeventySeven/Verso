# Memory Primitive — Verso Design Resolution

**Subsystem:** `memory/`  
**PRD refs:** §5.4, §10.5  
**Teardown sources:** `03_teardowns/memory-systems.md` (Mem0, Graphiti, Hindsight, Honcho, Memobase, MemOS, Cognee, txtai), `03_teardowns/infra-retrieval-vector.md` (Qdrant, Chroma, pgvector, Weaviate, Milvus, sqlite-vec)  
**Date:** 2026-06-05  

Labels: **KNOWN** = read from RE'd source at `file:line`. **INFERRED** = derived from code behaviour. **DESIGNED** = Verso's engineering choice for the gap.

---

## Decisions Resolved

---

### Decision 1 — Write policy: Mem0 V3 additive (ADD-only) vs legacy AUDN sync-per-turn

**Choice: ADD-only extraction with buffered-async write (Mem0 V3 additive + Memobase buffer + Honcho daemon pattern).** Never run the legacy AUDN path as the default.

**Rationale:**  
The legacy Mem0 AUDN (Add/Update/Delete/None) per-turn loop causes false-positive deletions at scale: a new fact about "dislikes cheese pizza" deletes the old fact "loves cheese pizza" via a contradiction→DELETE rule (`mem0/configs/prompts.py:176-324`). This is data loss, not conflict resolution. The Mem0 V3 pipeline (`mem0/memory/main.py:662-971`) eliminated DELETE from the hot path entirely, replacing it with additive extraction + linking. HydraDB §4.1 proves the same: iterative resolve-on-write is O(N) and produces false deletes. The whole cluster has converged on additive writes; only Mem0's legacy path and nothing else deletes on contradiction.

Buffered-async (Memobase 1024-token flush trigger, `env.py:86`; Honcho daemon-thread `_async_add_to_memory`, `proxy/main.py:154-166`) means the agent never blocks on consolidation. A response is returned immediately; extraction is enqueued. `flush()` is exposed explicitly so callers can force-consolidate before a checkpoint (the durable-seam requirement).

**Evidence (KNOWN):**  
- Mem0 V3: `mem0/memory/main.py:662-971` — 8-phase pipeline, single LLM call, ADD-only; `main.py:856` `batch_add_history` still logs every event for audit even under additive policy.  
- Mem0 false-delete mechanism: `mem0/configs/prompts.py:176-324` `DEFAULT_UPDATE_MEMORY_PROMPT`, contradiction→DELETE rule (the thing the V3 pipeline explicitly removed from the hot path).  
- Memobase flush trigger: `memodb-io/memobase env.py:86` `max_chat_blob_buffer_token_size = 1024`.  
- Honcho daemon-thread write: `plastic-labs/honcho src/proxy/main.py:154-166` `_async_add_to_memory`.  

**Alternatives rejected:**  
- **Mem0 AUDN per-turn**: false-positive deletion at scale; now legacy even within Mem0.  
- **Graphiti per-episode invalidation on every write**: too expensive for high-volume chat; reserve for the audit tier (see Decision 3).  
- **Synchronous blocking consolidation**: violates the durable-seam rule "respond immediately, consolidate off the request path." Every high-volume system in the cluster converges on async-decouple.

---

### Decision 2 — Anti-hallucination map for LLM-in-the-loop mutations

**Choice: Integer-index anti-hallucination map — never let the LLM see or emit real UUIDs.**

**Rationale:**  
Both Mem0 and Graphiti independently discovered the same problem: when an LLM is asked to reference or mutate stored memories it will hallucinate, corrupt, or invent UUIDs. The fix is to present candidates as `{"id": "0", "text": ...}` with a Python-side `uuid_mapping["0"] → real_uuid`; the LLM emits only small integer ids; Python maps back. This eliminates an entire class of silent data corruption.

Graphiti extends it to two lists with a computed offset: `invalidation_idx_offset = len(related_edges)` so existing facts and invalidation candidates share one continuous integer range (`edge_operations.py:703`).

**Evidence (KNOWN):**  
- Mem0: `main.py:716-721` — `uuid_mapping` built before the extraction LLM call; LLM only receives `{"id":"0","text":...}` format.  
- Graphiti: `prompts/dedupe_edges.py:43-99` — `<EXISTING FACTS>` and `<FACT INVALIDATION CANDIDATES>` presented with continuous integer indexes; `edge_operations.py:703` `invalidation_idx_offset`.  

**Alternatives rejected:**  
- Passing real UUIDs to the LLM: both systems independently proved this causes silent corruption.

---

### Decision 3 — Conflict / temporal-invalidation model: tier-selected

**Choice: Two-tier conflict resolution. Chat tier = read-time resolution (Hindsight "latest `mentioned_at` wins"). Audit/checkpoint tier = write-time bi-temporal invalidation (Graphiti `valid_at`/`invalid_at`). Never hard-delete on contradiction.**

**Rationale:**  
This is the fundamental write-time vs read-time fork the teardown surfaces as a first-class decision. Graphiti (`getzep/graphiti graphiti_core/edges.py:263-285`) resolves conflicts at write time: a contradicting fact stamps the prior edge's `invalid_at = new.valid_at` and `expired_at = utc_now()` — the old edge is never deleted, only bounded. This is audit-clean and makes `recall_as_of(T)` a cheap interval query. Cost: every write that contradicts a prior fact requires an LLM classification + Python timestamp arithmetic.

Hindsight (`vectorize-io/hindsight engine/reflect/prompts.py:170-206`) resolves conflicts at read time: writes are additive; the reflect synthesis prompt applies the rule "the fact with the latest `mentioned_at` is AUTHORITATIVE" with a detailed double-counting guard (forced chain-of-thought: list facts in `mentioned_at` order, identify the winner, apply only events AFTER the winner, show arithmetic). Cost: cheap writes, expensive reads when the same facet has conflicting facts.

The right choice depends on the use case:  
- **Chat / high-volume memory** — read-time resolution. Writes are cheap; conflicts are infrequent; when they occur, the "latest mentioned_at wins" rule is almost always correct; the synthesized output is the product.  
- **Finance / health / checkpoint-resume** — write-time bi-temporal. Reconstructing "what the agent knew at decision time" is a hard requirement. Interval query on `(valid_at ≤ T AND (invalid_at IS NULL OR invalid_at > T) AND created_at ≤ T_record)` is the only correct mechanism.

The tier-select is driven by `MemoryType`: `scratchpad`/`episodic`/`fact` → chat tier (read-time); `fact` with `audit=True` / `procedural` / `belief` → audit tier (write-time bi-temporal).

**Evidence (KNOWN):**  
- Graphiti bi-temporal model: `graphiti_core/edges.py:263-285` — four timestamps per edge: `created_at`, `expired_at` (transaction time), `valid_at`, `invalid_at` (valid time). Invalidation arithmetic: `edge_operations.py:538-573` — Python computes `edge.invalid_at = resolved.valid_at`; LLM only classifies `{duplicate_facts, contradicted_facts}` by integer index.  
- Graphiti temporal date extraction rules: `prompts/extract_edges.py:168-175` — ISO-8601 with Z; ongoing → `valid_at = reference_time`; change/termination → set `invalid_at`; "Do NOT hallucinate temporal bounds."  
- Hindsight read-time resolution: `engine/reflect/prompts.py:170-206` — verbatim temporal-reasoning protocol: "latest `mentioned_at` is AUTHORITATIVE"; "If event ≤ authoritative date, DROP it — re-applying = double-counting"; forced chain-of-thought steps 1–6.  
- Hindsight `mentioned_at`/`occurred_start`/`occurred_end` triple: `alembic/versions/5a366d414dce_initial_schema.py:265-305`.

**Alternatives rejected:**  
- **Hard delete on contradiction** (legacy Mem0 AUDN): data loss; the query "what did the agent believe before it was corrected?" becomes unanswerable.  
- **Always write-time invalidation**: correct but prohibitively expensive for chat-tier memory (every turn requires an LLM classification pass against existing memories).

---

### Decision 4 — Taxonomy depth: 4-tier vs extensible vs fixed-13 (Memanto)

**Choice: 4-tier default (scratchpad / episodic / fact / procedural), extensible to a richer epistemic set (explicit / deductive / inductive / belief / contradiction / skill) as opt-in named constants. Not a fixed closed enum.**

**Rationale:**  
Memanto's fixed 13 types are opaque to users and hard to extend. A flat untyped fact list (many systems' default) loses epistemic status — you can't distinguish "the model said this" from "this was inferred" from "this was directly observed." The PRD locks the 4-tier for the public API (`scratchpad 1h / episodic 7d / fact ∞ / procedural ∞`); this maps naturally onto the lifecycle tiers observed across systems (MemOS WorkingMemory / LongTermMemory / UserMemory + Skill; Hindsight `fact_type` world/experience/opinion/observation; Honcho explicit/deductive/inductive).

The PRD's 4 types stay as the **user-facing enum values**. Internally, each type carries an `epistemic_class` drawn from the richer Honcho/Hindsight vocabulary:

```python
class EpistemicClass(str, Enum):
    explicit    = "explicit"      # directly stated / observed
    deductive   = "deductive"     # inferred via explicit steps
    inductive   = "inductive"     # pattern over multiple observations  
    belief      = "belief"        # consolidated belief (proof_count > 0)
    procedural  = "procedural"    # run-trace / action-result record
    skill       = "skill"         # crystallized tool trajectory
    contradiction = "contradiction"  # explicit conflict flagged, not resolved
```

The 4-tier drives TTL + capacity gating (MemOS-style hard caps). The epistemic class drives retrieval scoring (`proof_count` boost, confidence gate) and conflict handling (contradiction type surfaces to the agent instead of silently resolving).

**Evidence (KNOWN):**  
- Hindsight `fact_type` 4-way: `5a366d414dce_initial_schema.py:271` `fact_type TEXT NOT NULL DEFAULT 'world' CHECK IN ('world','bank','opinion','observation')`. `confidence_score FLOAT` required for `opinion`, NULL for others.  
- Honcho four observation classes with `source_ids` provenance chain: `src/utils/representation.py:59-111` — `ExplicitObservation`, `DeductiveObservation`, `InductiveObservation{pattern_type, confidence}`, `ContradictionObservation{source_ids}`.  
- MemOS lifecycle capacities: `src/memos/memories/textual/tree.py:81-86` `memory_size = {"WorkingMemory": 20, "LongTermMemory": 1500, "UserMemory": 480}`.  
- MemOS `SkillMemory` / `ToolTrajectoryMemory`: `src/memos/memories/textual/item.py:178-188`.

**Alternatives rejected:**  
- **Memanto fixed-13**: closed, opaque, blocks domain-specific extensions.  
- **Flat untyped list**: loses epistemic status, makes scoring and conflict routing impossible.

---

### Decision 5 — Default backend: Hindsight Postgres-only vs pluggable sqlite-vec → pgvector

**Choice: Pluggable three-tier backend (`‹edge2›`). Default dev = sqlite-vec (zero-infra). Default prod = single Postgres (Hindsight model: pgvector + pgroonga/tsvector + `memory_links` adjacency + date columns). Optional audit tier = Graphiti bi-temporal on Neo4j. Same `MemoryBackend` interface across all three. Hindsight's Postgres model is the prod default, not the only option.**

**Rationale:**  
Hindsight proves a single Postgres instance can be the entire memory backend and reach near-SOTA (91.4% LongMemEval with a large backbone, arXiv:2512.12818). pgvector (diskann/hnsw/vchordrq/scann — chosen by installed extension), pgroonga for BM25, adjacency rows for graph, date columns for temporal. Zero extra services. This is the right single-node prod default.

But Hindsight's design is rigid (one schema, one indexing path). Verso's PRD explicitly requires `‹edge2›` to be a pluggable edge — sqlite-vec for dev/CI/embedded (zero Docker, runs in tests, in WASM), Postgres for prod, and a clean seam for future graph backends. This matches Cognee's three-plane factory pattern (`graph/get_graph_engine.py:110`, `vector/create_vector_engine.py`) and Chroma's PyO3 seam (`rust/python_bindings/src/bindings.rs:79-160`): same `Frontend`/`MemoryBackend` interface, config selects the implementation.

sqlite-vec is the correct dev-tier default: `pip install sqlite-vec`, `vec.load(conn)`, `CREATE VIRTUAL TABLE memories USING vec0(embedding float[768], session_id integer partition key)`. Brute-force below ~10k vectors is correct for a dev/test agent's working memory (cf. Qdrant `full_scan_threshold = 10_000`; sqlite-vec: `chunk_size = 1024`, no HNSW, validity-bit deletes).

**Evidence (KNOWN):**  
- Hindsight single-DB proof: `alembic/versions/5a366d414dce_initial_schema.py` — pgvector ANN index switching at startup (`ensure_text_search_extension()`), pgroonga BM25 swap, `memory_links` adjacency table, `occurred_start`/`occurred_end` temporal columns.  
- Cognee pluggable factory: `cognee/infrastructure/databases/graph/get_graph_engine.py:110` — NetworkX / kuzu / neo4j / ladybug / neptune / postgres; `USE_UNIFIED_PROVIDER=pghybrid`; `cognee/infrastructure/databases/vector/create_vector_engine.py`.  
- Chroma PyO3 seam: `rust/python_bindings/src/bindings.rs:104-145` — `SysDbConfig::Sqlite`, `LogConfig::Sqlite`, `ExecutorConfig::Local`, `KnnIndex::Hnsw` in embedded; swap to `Distributed` variants for durable — same `Frontend`.  
- sqlite-vec minimal surface: `sqlite_vec/__init__.py` — `load(conn)` = one extension load; `vec0BestIndex` chunk-aligned partition keys: `sqlite-vec.c:6097-6106`.  
- pgvector HNSW defaults: `src/hnsw.h:46,49,52` — `m=16, ef_construction=64, ef_search=40`.  
- pgvectorscale StreamingDiskANN: `options.rs:23-41` — `R=50, L=100, α≤1.2, rescore=50`.  

**Alternatives rejected:**  
- **Hindsight Postgres-only (no pluggable interface)**: fails the `‹edge2›` pluggable-edge requirement; locks out dev/CI use without Docker.  
- **Milvus + Neo4j + Redis polyglot stack**: operational complexity the PRD explicitly rejects; Hindsight proves single-DB reaches near-SOTA.  
- **Neo4j as default (Graphiti-style)**: correct for the audit/temporal tier only; the overhead of a graph DB for a simple chat-tier fact store is unjustified.

---

### Decision 6 — Composite retrieval scoring and fusion

**Choice: Four-arm retrieval (semantic / BM25 / graph / temporal) fused via pool-size-adaptive RRF (k=60 for large ANN pools, k=1 for small graph pools), with Hindsight-style bounded multiplicative post-rerank boosts (recency ±10%, temporal ±10%, proof_count ±5%). Cross-encoder rerank (`bge-reranker-v2-m3`) over the final candidate budget only. Semantic gate BEFORE fusion (drop candidates below cosine threshold 0.1). Mem0's additive adaptive-divisor fusion is the fallback for the no-graph / no-temporal tier.**

**Rationale:**  
The cluster presents five fusion strategies. The cross-system signal is clear: rank-only (RRF) when dense and sparse scores are on incomparable scales (cosine vs BM25); score-normalized (DBSF/relative-score) when scores are calibrated. The k constant is a tunable: Weaviate hard-codes 60 (large BM25 candidate pools from BM25 global corpus statistics), Qdrant defaults to 2 for its query-API tree (small prefetch lists), Graphiti uses 1 for small graph candidate sets (~10-20 results per method). The pool-size rule resolves the disagreement: k≈60 when fusing hundreds of ANN candidates; k≈1 when fusing tens of graph candidates.

The bounded multiplicative boost design (Hindsight `reranking.py:12-130`) is the correct architecture for recency/temporal/freshness signals. CE relevance is the primary signal; recency and temporal proximity are multiplicative nudges capped at ±10% each so a stale-but-recent fact can never outrank a strong semantic match. The degenerate-CE guard (all CE scores identical → reseed from RRF rank mapped to [0.1, 1.0], `reranking.py:71-98`) handles cold/slim deployments.

For the no-graph / no-BM25 / dev-tier path, Mem0's additive fusion with adaptive divisor is simpler and avoids deflating pure-semantic results: `raw_combined = semantic + bm25_norm + entity_boost`, divisor grows only when those signals are present (`scoring.py:60-121`). This is the default for sqlite-vec backend which has no BM25 arm.

**Evidence (KNOWN):**  
- Hindsight TEMPR four-arm retrieval: `engine/search/retrieval.py:40-48` — `semantic`, `bm25`, `graph` (link expansion BFS), `temporal`; over-fetch 5× (min 100) for HNSW approx.  
- Hindsight RRF k=60: `fusion.py:31` `1 / (60 + rank)`.  
- Hindsight `interleave_fusion` for dedup path: `fusion.py:101-158` — round-robin arms so each arm's top hit gets a slot (RRF drops near-duplicate twins during consolidation).  
- Hindsight bounded multiplicative boosts: `reranking.py:12-130` — `recency = clamp(1 - days_ago/365, 0.1, 1.0)`, `recency_boost = 1 + 0.2*(recency - 0.5)`, `temporal_boost = 1 + 0.2*(temporal - 0.5)`, `proof_count_boost = 1 + 0.1*(proof_norm - 0.5)`, `combined_score = CE_normalized * recency_boost * temporal_boost * proof_count_boost`.  
- Hindsight degenerate CE reseed: `reranking.py:71-98`.  
- Graphiti RRF k=1: `search_utils.py:1780-1796` `rank_const=1`.  
- Mem0 additive fusion: `mem0/utils/scoring.py:60-121` — semantic gate `threshold=0.1` before fusion; adaptive divisor; `ENTITY_BOOST_WEIGHT=0.5`.  
- Mem0 semantic gate: `main.py:1343` default threshold 0.1 — applied BEFORE fusing.  
- Weaviate RRF k=60: `hybrid_fusion.go:22-81` `weights[resultSetIndex] / float64(i+60)`.  
- Qdrant RRF k=2: `reciprocal_rank_fusion.rs:14` `DEFAULT_RRF_K = 2`; weight divides position, not score: `1/((pos+1)/w + k - 1)`.  
- Cross-encoder default: Hindsight `reranking.py:138` `cross-encoder/ms-marco-MiniLM-L-6-v2`; Graphiti `bge_reranker_client.py:36` `BAAI/bge-reranker-v2-m3`.

**Alternatives rejected:**  
- **Additive normalized fusion as the universal default**: correct for Mem0's no-graph tier but loses recall on graph/temporal arms where scores aren't naturally in [0,1].  
- **Additive recency boost**: can flip a strong-semantic old fact below a weak-semantic new one. Multiplicative with ±10% cap prevents this.  
- **Always RRF k=60**: over-flattens small graph candidate sets (Graphiti proved k=1 is better for its ~10-candidate graph pools).

---

### Decision 7 — `remember` / `recall` / `recall_as_of` API + tool-callable surface

**Choice: Three tool-callable methods on the `Memory` object. Writes are ADD-only per Decision 1. `recall` uses composite scoring (Decision 6). `recall_as_of` filters on bi-temporal timestamps (Decision 3) and is only available for facts stored in the audit tier. A metadata filter operator language (≥9 operators) is exposed on `recall`.**

**Rationale:**  
Memory-as-tool-calls is the LLM-manages-its-own-memory design. Both Letta/MemGPT (PRD ref) and the Verso PRD §5.4 specify this. The Mem0 metadata filter operator language (`_process_metadata_filters`, `main.py:1239-1342`) covers `eq, ne, gt, gte, lt, lte, in, nin, contains, icontains` — 10 operators. This is the minimum filter surface needed to let an agent query by confidence threshold, by tag, by type, by date range. Verso exposes a subset (9 core operators, `contains`/`icontains` optional in v1) mapped to each backend's query syntax (SQL WHERE for Postgres, filter dicts for Qdrant, chunk-aligned metadata for sqlite-vec).

`recall_as_of(query, date)` is the audit-tier API for checkpoint-resume and finance/health use cases. It wraps the bi-temporal query: `valid_at ≤ date AND (invalid_at IS NULL OR invalid_at > date) AND created_at ≤ date`. It raises `MemoryError("audit_tier_required")` if the configured backend doesn't support bi-temporal timestamps — a clean fail-fast rather than silent approximation.

**Evidence (KNOWN):**  
- Mem0 metadata filter operators: `main.py:1239-1342` `_process_metadata_filters` — `eq, ne, gt, gte, lt, lte, in, nin, contains, icontains` (`:24-28`).  
- Graphiti bi-temporal query: `graphiti_core/edges.py:263-285` — four timestamps; `valid_at ≤ T AND (invalid_at IS NULL OR invalid_at > T) AND created_at ≤ T_record`.  
- Mem0 search top_k default 20: `main.py:1126` `search() top_k=20, threshold=0.1`.  
- Mem0 search over-fetch: `main.py:1356` `max(top_k * 4, 60)`.  
- Hindsight tag filter modes: `engine/search/tags.py:6-46` — `any`/`all`/`any_strict`/`all_strict`; untagged-inclusion semantics. Verso exposes `tag_match: Literal["any", "all", "any_strict", "all_strict"] = "any"`.

---

### Decision 8 — Async consolidation trigger: when and how

**Choice: Two-stage async cognition. Fast extraction (per-flush, off request path) + slow consolidation (accumulation-triggered: N=50 new items AND ≥8h since last, with surprisal gating at top-10% novel). Consolidation writes `belief` + `inductive` items back with `proof_count` + `source_ids` provenance. Capacity-gated tiers (working cap 20 FIFO → durable large → user-model bounded).**

**Rationale:**  
The cluster's unanimous finding: never block the agent on consolidation. Every system that handles volume converges on the same topology — fast extraction off the request path + slow consolidation triggered by accumulation. Honcho's trigger constants (`DOCUMENT_THRESHOLD = 50`, `MIN_HOURS_BETWEEN_DREAMS = 8`, `config.py:1168-1170`) are the concrete calibration, with a `DreamScheduler` that debounces and cancels stale scheduled dreams when new observations arrive for the same (observer, observed) scope.

Honcho's surprisal-gated consolidation (top 10% most novel observations by geometric distance to the existing cluster manifold, `config.py:1152` `TOP_PERCENT_SURPRISAL = 0.10`) is principled spend control: spend the consolidation LLM budget on the novel observations, not the redundant ones. The surprisal tree (`src/dreamer/surprisal.py:46-170`) is a cover-tree/RP-tree/LSH/sklearn-KNN over observation embeddings; `tree.surprisal(embedding)` = distance to existing neighbors, normalized to [0,1].

MemOS capacity-gated tiers (`tree.py:81-86`): WorkingMemory cap 20 (FIFO), LongTermMemory cap 1500, UserMemory cap 480. FIFO eviction at L1 (`remove_oldest_memory, keep_latest=20`, `manager.py:255-257`) prevents unbounded growth at the working-set tier. Verso maps these to: in-run working set (≤20, evicted FIFO) → durable extracted memories (large, bounded by budget policy) → stable user model tier (≤480).

Hindsight `reflect()` (`engine/reflect/agent.py`) as an agentic ReAct loop (max 10 iters, `agent.py:49`) with hierarchical retrieval: search `mental_models` first (consolidated beliefs), then `observations`, then raw `recall` — synthesizes and writes back `belief` items with `proof_count + source_ids` provenance. This is the consolidation loop Verso's between-run memory improvement uses.

**Evidence (KNOWN):**  
- Honcho trigger: `src/deriver/config.py:1168-1170` `DOCUMENT_THRESHOLD = 50`, `MIN_HOURS_BETWEEN_DREAMS = 8`. `src/dreamer/dream_scheduler.py:54` debounce + cancel stale.  
- Honcho surprisal: `src/dreamer/surprisal.py:46-170`; `config.py:1152` `TOP_PERCENT_SURPRISAL = 0.10`; `config.py:1156` `MIN_HIGH_SURPRISAL_FOR_REPLACE = 10`.  
- MemOS FIFO eviction: `src/memos/memories/textual/manager.py:255-257,283-285` `remove_oldest_memory(memory_type="WorkingMemory", keep_latest=20)`.  
- MemOS capacities: `src/memos/memories/textual/tree.py:81-86`.  
- Hindsight reflect loop: `engine/reflect/agent.py:49` `DEFAULT_MAX_ITERATIONS = 10`; `engine/reflect/prompts.py:96+` hierarchical search order (mental_models → observations → recall).  
- Hindsight `_FINAL_PROMPT_CONTEXT_FRACTION = 0.8`: `engine/reflect/agent.py`.  
- Memobase buffer constant: `memodb-io/memobase env.py:86` `max_chat_blob_buffer_token_size = 1024`.

---

### Decision 9 — Graph-memory tier: entity links without requiring Neo4j

**Choice: For dev and single-node prod, implement graph memory as three adjacency signals in a `memory_links` table (entity self-join, semantic kNN-at-insert, causal from extraction) — no external graph DB. Reserve Graphiti/Neo4j for the audit-tier when `recall_as_of` bi-temporal is required.**

**Rationale:**  
Hindsight's graph arm (`engine/search/link_expansion_retrieval.py:4-22`) proves that "graph memory" needs no Neo4j. The three signals:  
1. **Entity links**: self-join through `unit_entities`; `score = COUNT(DISTINCT shared entity_id)` between seed and candidate; LATERAL cap `graph_per_entity_limit=200` to stop high-fanout entities ("User") from exploding the join.  
2. **Semantic links**: precomputed kNN graph — at INSERT each new fact is linked to its top-5 most-similar existing facts with similarity ≥ 0.7 (asymmetric, checked both directions).  
3. **Causal links**: explicit chains (causes/caused_by/enables/prevents) from the 5W extraction; `score = weight + 1.0` (boosted as highest-quality signal).

This is cheaper to operate than Graphiti's Neo4j and covers entity/semantic/causal adjacency in a single Postgres CTE.

For the entity canonicalization step: Hindsight uses pg_trgm similarity (case-insensitive, `entities trgm index`) rather than an LLM call per entity — cheap dedup. Mem0 uses cosine ≥ 0.95 on the entity embedding. Verso defaults to the cheaper pg_trgm path for Postgres backend.

For the dev tier (sqlite-vec backend), the graph arm is skipped — sqlite-vec's `partition key` columns give per-session/per-agent physical partitioning but there is no kNN adjacency table. The graph arm activates only in the Postgres backend.

**Evidence (KNOWN):**  
- Hindsight three-signal graph: `engine/search/link_expansion_retrieval.py:4-22` — entity links (LATERAL self-join, `graph_per_entity_limit=200`), semantic links (kNN top-5 at insert, sim ≥ 0.7), causal links (weight + 1.0 boost).  
- Hindsight entity canonicalization: `engine/retain/entity_processing.py:52-90` pg_trgm case-insensitive trigram index.  
- Mem0 entity store: `main.py:413-535` — vector-only entity rows, adjacency via `linked_memory_ids[]`, cosine dedup threshold 0.95 (`main.py:918`).  
- Hindsight `memory_links` table: `engine/retain/link_creation.py`.  
- Graphiti Neo4j requirement: `graphiti_core/graphiti.py:980-1223` — Neo4j/FalkorDB/Kuzu as the required graph backend; `group_id` partition axis.  

**Alternatives rejected:**  
- **Neo4j as default**: zero-ops requirement for dev/single-node prod. Hindsight proves single-DB nearly matches.  
- **No graph arm**: loses entity/causal/semantic proximity signals that the TEMPR four-arm retrieval depends on; recall quality drop.

---

## Component Spec (reimplementable, attributed)

### `MemoryItem` — the core data model

**DESIGNED** (synthesized from Hindsight schema + Honcho observation classes + MemOS MemCube + Graphiti bi-temporal + Mem0 scope/hash).

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class MemoryType(str, Enum):
    """4-tier public API. TTLs enforced by the store."""
    scratchpad  = "scratchpad"   # ~1h
    episodic    = "episodic"     # ~7d
    fact        = "fact"         # permanent
    procedural  = "procedural"   # permanent — run traces + skills


class EpistemicClass(str, Enum):
    """Internal epistemic status (richer than MemoryType; drives scoring + conflict routing)."""
    explicit      = "explicit"       # directly stated/observed  [Honcho ExplicitObservation]
    deductive     = "deductive"      # inferred via explicit steps  [Honcho DeductiveObservation]
    inductive     = "inductive"      # pattern over multiple observations  [Honcho InductiveObservation]
    belief        = "belief"         # consolidated (proof_count > 0)  [Hindsight mental_model]
    procedural    = "procedural"     # run-trace action+result records  [Mem0 procedural prompt]
    skill         = "skill"          # crystallized tool trajectory  [MemOS SkillMemory]
    contradiction = "contradiction"  # explicit conflict, surfaced not resolved  [Honcho ContradictionObservation]


class MemoryStatus(str, Enum):
    """Lifecycle status. [MemOS item.py:109]"""
    active     = "active"
    resolving  = "resolving"    # mid-conflict-merge (concurrent writes)
    archived   = "archived"
    deleted    = "deleted"      # logical only — never physical row deletion


@dataclass
class MemoryScope:
    """Composable scope tags. All optional, but ≥1 required at write.
    
    Follows Mem0's composable model (main.py:231-314 _build_filters_and_metadata)
    + Honcho's peer-symmetric (observer, observed) extension for multi-agent sessions.
    """
    user_id:   str | None = None
    agent_id:  str | None = None
    run_id:    str | None = None
    observer:  str | None = None    # Honcho (observer, observed) for multi-agent
    observed:  str | None = None


@dataclass
class MemoryItem:
    # Identity
    id:          str = field(default_factory=lambda: str(uuid.uuid4()))
    scope:       MemoryScope = field(default_factory=MemoryScope)

    # Content
    text:        str = ""
    embedding:   list[float] | None = None     # dim depends on configured embedder

    # Typing
    type:        MemoryType = MemoryType.fact
    epistemic:   EpistemicClass = EpistemicClass.explicit
    status:      MemoryStatus = MemoryStatus.active

    # Temporal (Graphiti-lite bi-temporal + Hindsight triple)
    mentioned_at:     datetime | None = None   # transaction time: when the system learned this
    occurred_start:   datetime | None = None   # valid time: when the event began
    occurred_end:     datetime | None = None   # valid time: when the event ended
    valid_at:         datetime | None = None   # audit tier only: when fact became true
    invalid_at:       datetime | None = None   # audit tier only: when fact stopped being true
    expired_at:       datetime | None = None   # audit tier only: system-time expiry

    # Scoring signals
    confidence:  float | None = None     # [0,1]; required for epistemic=inductive/belief
    proof_count: int = 0                  # Hindsight: supporting observations count; drives score boost
    access_count:int = 0                  # Hindsight: frequency signal

    # Provenance (MemOS quintet)
    version:      int = 1
    history:      list[dict] = field(default_factory=list)   # archived prior versions (core info only)
    evolve_to:    list[str] = field(default_factory=list)    # ids of nodes this one evolved into
    source_ids:   list[str] = field(default_factory=list)    # supporting evidence ids (Honcho premise chain)
    covered_ids:  list[str] = field(default_factory=list)    # ids covered/superseded by this item

    # Links (Mem0/Hindsight graph-without-graph-DB)
    linked_ids:   list[str] = field(default_factory=list)    # Mem0 linked_memory_ids
    entity_ids:   list[str] = field(default_factory=list)    # Hindsight unit_entities FK

    # Metadata
    tags:         list[str] = field(default_factory=list)
    metadata:     dict[str, Any] = field(default_factory=dict)
    text_hash:    str | None = None     # md5(text) for dedup [Mem0 main.py:799]
    created_at:   datetime | None = None
    updated_at:   datetime | None = None
```

---

### SQL schema — Postgres backend (Hindsight-model, adapted)

**DESIGNED**, directly attributed to Hindsight `alembic/versions/5a366d414dce_initial_schema.py:265-305` + MemOS metadata quintet + Graphiti timestamps.

```sql
-- Main memory table
CREATE TABLE memory_items (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Scope (Mem0 composable triple, main.py:231-314)
  user_id         TEXT,
  agent_id        TEXT,
  run_id          TEXT,
  observer        TEXT,       -- Honcho peer-symmetric (observer, observed)
  observed        TEXT,

  -- Content
  text            TEXT NOT NULL,
  embedding       vector(1024),   -- pgvector; dim matches configured embedder; default 1024 (Graphiti embedder/client.py:23)
  text_lemmatized TEXT,           -- Mem0 BM25 input (main.py:808-816)
  text_hash       TEXT,           -- md5(text) dedup (Mem0 main.py:799)
  tsv             tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,

  -- Typing
  memory_type     TEXT NOT NULL DEFAULT 'fact'
                    CHECK (memory_type IN ('scratchpad','episodic','fact','procedural')),
  epistemic_class TEXT NOT NULL DEFAULT 'explicit'
                    CHECK (epistemic_class IN ('explicit','deductive','inductive','belief','procedural','skill','contradiction')),
  status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','resolving','archived','deleted')),

  -- Temporal triple (Hindsight 5a366d414dce:265-305 + Graphiti edges.py:263-285)
  mentioned_at    TIMESTAMPTZ NOT NULL DEFAULT now(),   -- transaction time (always set)
  occurred_start  TIMESTAMPTZ,                          -- valid time: event start
  occurred_end    TIMESTAMPTZ,                          -- valid time: event end
  valid_at        TIMESTAMPTZ,                          -- audit tier: when fact became true
  invalid_at      TIMESTAMPTZ,                          -- audit tier: when fact stopped being true
  expired_at      TIMESTAMPTZ,                          -- audit tier: system-time expiry

  -- Scoring signals
  confidence      FLOAT CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
  proof_count     INTEGER NOT NULL DEFAULT 0,    -- Hindsight reranking.py:17; drives ±5% boost
  access_count    INTEGER NOT NULL DEFAULT 0,    -- Hindsight; frequency signal

  -- Provenance (MemOS quintet: item.py:94-188)
  version         INTEGER NOT NULL DEFAULT 1,
  history         JSONB NOT NULL DEFAULT '[]',   -- archived prior versions
  evolve_to       UUID[] NOT NULL DEFAULT '{}',  -- ids this evolved into
  source_ids      UUID[] NOT NULL DEFAULT '{}',  -- supporting evidence (Honcho source_ids; GIN-indexed)
  covered_ids     UUID[] NOT NULL DEFAULT '{}',  -- superseded ids

  -- Links
  linked_ids      UUID[] NOT NULL DEFAULT '{}',  -- Mem0 linked_memory_ids
  entity_ids      UUID[] NOT NULL DEFAULT '{}',

  -- Metadata
  tags            TEXT[] NOT NULL DEFAULT '{}',
  metadata        JSONB NOT NULL DEFAULT '{}',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Scope constraint: at least one scope id must be set
  CONSTRAINT memory_scope_required CHECK (
    user_id IS NOT NULL OR agent_id IS NOT NULL OR run_id IS NOT NULL
  )
);

-- Indexes
CREATE INDEX ON memory_items (user_id, agent_id, run_id) WHERE status = 'active';
CREATE INDEX ON memory_items (memory_type, status);
CREATE INDEX ON memory_items (mentioned_at DESC);
CREATE INDEX ON memory_items (valid_at, invalid_at) WHERE valid_at IS NOT NULL;  -- audit tier
CREATE INDEX ON memory_items USING GIN (source_ids);   -- Hindsight p1k2l3m4n5o6:103-106
CREATE INDEX ON memory_items USING GIN (tags);
CREATE INDEX ON memory_items USING GIN (tsv);          -- tsvector BM25 fallback
-- pgroonga index (swapped in at startup if extension available — Hindsight ensure_text_search_extension())
-- CREATE INDEX ON memory_items USING pgroonga (text);

-- ANN index (chosen at startup by available pgvector extension)
-- diskann: CREATE INDEX ON memory_items USING diskann (embedding vector_cosine_ops);
-- hnsw:    CREATE INDEX ON memory_items USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);
-- Default: hnsw with pgvector defaults (src/hnsw.h:46,49,52)

-- Entity table (Hindsight engine/retain/entity_processing.py)
CREATE TABLE entities (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     TEXT,
  agent_id    TEXT,
  name        TEXT NOT NULL,
  entity_type TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON entities (lower(name), user_id, agent_id);  -- trgm similarity lookup
CREATE INDEX ON entities USING GIN (name gin_trgm_ops);     -- Hindsight case-insensitive trgm

-- entity↔memory join
CREATE TABLE unit_entities (
  memory_id   UUID NOT NULL REFERENCES memory_items(id) ON DELETE CASCADE,
  entity_id   UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  PRIMARY KEY (memory_id, entity_id)
);

-- memory_links table: the "graph without a graph DB" (Hindsight link_expansion_retrieval.py:4-22)
CREATE TABLE memory_links (
  src_id      UUID NOT NULL REFERENCES memory_items(id) ON DELETE CASCADE,
  tgt_id      UUID NOT NULL REFERENCES memory_items(id) ON DELETE CASCADE,
  link_type   TEXT NOT NULL CHECK (link_type IN ('semantic','causal','entity')),
  weight      FLOAT NOT NULL DEFAULT 1.0,
  -- causal subtypes: causes | caused_by | enables | prevents  (Hindsight 5W causal_relations)
  causal_type TEXT,
  user_id     TEXT,    -- denormalized for partition-aware queries
  agent_id    TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (src_id, tgt_id, link_type)
);
CREATE INDEX ON memory_links (src_id, link_type);
CREATE INDEX ON memory_links (tgt_id, link_type);

-- Append-only history log (Mem0 storage.py — every ADD/UPDATE even under additive policy)
CREATE TABLE memory_history (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  memory_id   UUID NOT NULL,
  event       TEXT NOT NULL CHECK (event IN ('ADD','UPDATE','INVALIDATE','ARCHIVE')),
  old_text    TEXT,
  new_text    TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON memory_history (memory_id, created_at);

-- Message buffer (Memobase buffer_zones pattern — env.py:86)
CREATE TABLE memory_buffer (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     TEXT,
  agent_id    TEXT,
  run_id      TEXT,
  content     JSONB NOT NULL,   -- raw turn blob
  token_size  INTEGER NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON memory_buffer (user_id, agent_id, created_at);
```

---

### `MemoryBackend` interface (pluggable `‹edge2›`)

**DESIGNED** (Cognee three-plane factory pattern + txtai unified surface).

```python
from abc import ABC, abstractmethod
from typing import Any, Sequence


class MemoryBackend(ABC):
    """
    Pluggable memory store edge (‹edge2›).
    
    Implementations:
      SqliteVecBackend   — dev/zero-infra; brute-force below ~10k items (sqlite-vec)
      PostgresBackend    — prod single-node; pgvector + pgroonga/tsvector + memory_links
      GraphitiBackend    — audit tier; Neo4j bi-temporal edges via graphiti_core
    """

    @abstractmethod
    async def insert(self, items: list[MemoryItem]) -> list[str]:
        """Batch ADD-only insert. Returns list of assigned ids. Never updates existing."""

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        query_text: str,
        scope: MemoryScope,
        *,
        types: list[MemoryType] | None = None,
        top_k: int = 20,              # Mem0 main.py:1126 search() default
        semantic_threshold: float = 0.1,  # Mem0 main.py:1343 gate BEFORE fusing
        alpha: float = 0.75,          # Weaviate hybrid; alpha→[alpha, 1-alpha] weights (searcher.go:75)
        rrf_k: int = 60,              # Hindsight fusion.py:31; use k=1 for graph-only queries
        tag_match: str = "any",       # Hindsight tags.py:6-46: any|all|any_strict|all_strict
        filters: dict[str, Any] | None = None,   # Mem0 operator language: eq,ne,gt,gte,lt,lte,in,nin,contains
        rerank: bool = True,
    ) -> list[tuple[MemoryItem, float]]:
        """Four-arm hybrid retrieval: semantic + BM25 + graph + temporal.
        Returns (item, score) pairs sorted descending."""

    @abstractmethod
    async def recall_as_of(
        self,
        query_embedding: list[float],
        query_text: str,
        scope: MemoryScope,
        at_time: datetime,
        top_k: int = 20,
    ) -> list[tuple[MemoryItem, float]]:
        """Bi-temporal point-in-time recall. Only Graphiti/audit-tier backend implements this;
        others raise MemoryError('audit_tier_required')."""

    @abstractmethod
    async def invalidate(self, memory_id: str, new_valid_at: datetime) -> None:
        """Audit tier only: stamp old item invalid_at = new_valid_at, expired_at = now().
        Never deletes. Raises MemoryError('audit_tier_required') on non-audit backends."""

    @abstractmethod
    async def flush_buffer(
        self,
        scope: MemoryScope,
        force: bool = False,
    ) -> int:
        """Drain buffered turns for this scope, run extraction LLM call, persist.
        force=True bypasses the token-threshold gate (used before checkpoints).
        Returns count of new MemoryItems persisted."""

    @abstractmethod
    async def get_by_id(self, memory_id: str) -> MemoryItem | None: ...

    @abstractmethod
    async def update_metadata(self, memory_id: str, **kwargs: Any) -> None:
        """Update non-content fields only (proof_count, access_count, status, tags, metadata).
        Never replaces text or embedding — those require a new ADD."""
```

---

### `Memory` — the user-facing object (tool-callable)

**DESIGNED** (synthesized from PRD §5.4 + Mem0 proxy pattern + txtai unified surface).

```python
class Memory:
    """
    One Memory object, three faces (PRD §5.4):
      - short-term: in-context working set (RunContext channel)
      - long-term: backend store, queried three ways
      - compaction: TTL and budget policies

    Tool-callable: remember / recall / recall_as_of are @tool-registered so
    the LLM manages its own memory observably.
    """

    def __init__(self, backend: MemoryBackend, scope: MemoryScope) -> None:
        self._backend = backend
        self._scope = scope
        self._working_set: list[MemoryItem] = []  # L1, cap 20 FIFO (MemOS tree.py:83)

    @classmethod
    def default(cls, scope: MemoryScope | None = None) -> "Memory":
        """Convenience constructor. Uses SqliteVecBackend if no DSN configured."""
        from verso.memory.backends.sqlite_vec import SqliteVecBackend
        return cls(backend=SqliteVecBackend(), scope=scope or MemoryScope())

    # ── Tool-callable API ──────────────────────────────────────────────

    async def remember(
        self,
        content: str,
        type: MemoryType = MemoryType.fact,
        confidence: float | None = None,
        tags: list[str] | None = None,
        # audit tier: explicit temporal anchors (Graphiti DATETIME RULES)
        occurred_start: datetime | None = None,
        occurred_end:   datetime | None = None,
    ) -> str:
        """
        ADD-only write. Enqueues to buffer; returns memory id.
        
        Write policy:
          - ADD-only: conflicting facts become new linked memories, never deletes.
          - Buffer is flushed async; call flush() before a checkpoint to force-consolidate.
          - Uses integer-index anti-hallucination map if called from an LLM-driven reconcile step.
          
        [Mem0 V3 main.py:662-971; Memobase env.py:86 buffer trigger]
        """
        item = MemoryItem(
            text=content, type=type, confidence=confidence,
            tags=tags or [], scope=self._scope,
            occurred_start=occurred_start, occurred_end=occurred_end,
            epistemic=EpistemicClass.explicit,
        )
        # Enqueue to buffer; extraction LLM call runs at flush
        await self._backend.flush_buffer(self._scope)  # check trigger; no-op if under threshold
        ids = await self._backend.insert([item])
        return ids[0]

    async def recall(
        self,
        query: str,
        types: list[MemoryType] | None = None,
        scope_override: MemoryScope | None = None,
        top_k: int = 20,
        alpha: float = 0.75,
        tag_match: str = "any",
        filters: dict[str, Any] | None = None,
        rerank: bool = True,
    ) -> list[MemoryItem]:
        """
        Hybrid recall: semantic + BM25 + graph + temporal arms, RRF k=60 fusion,
        multiplicative recency/temporal/proof boosts, cross-encoder rerank.
        
        Mem0 over-fetch: max(top_k * 4, 60) for re-scoring pool [main.py:1356].
        Semantic gate threshold 0.1 applied BEFORE fusion [main.py:1343].
        
        [Hindsight TEMPR fusion.py:31, reranking.py:12-130; Mem0 scoring.py:60-121]
        """
        from verso.memory.embedder import embed_query
        q_vec = await embed_query(query)
        scope = scope_override or self._scope
        pairs = await self._backend.search(
            q_vec, query, scope,
            types=types, top_k=top_k, alpha=alpha,
            tag_match=tag_match, filters=filters, rerank=rerank,
        )
        # Increment access_count for returned items (Hindsight frequency signal)
        for item, _ in pairs:
            await self._backend.update_metadata(item.id, access_count=item.access_count + 1)
        return [item for item, _ in pairs]

    async def recall_as_of(
        self,
        query: str,
        at_time: datetime,
        top_k: int = 20,
    ) -> list[MemoryItem]:
        """
        Audit-grade point-in-time recall. Returns items where:
          valid_at <= at_time AND (invalid_at IS NULL OR invalid_at > at_time)
          AND created_at <= at_time
        
        Only available with a bi-temporal backend (GraphitiBackend).
        Raises MemoryError('audit_tier_required') otherwise.
        
        [Graphiti edges.py:263-285; edge_operations.py:538-573]
        """
        from verso.memory.embedder import embed_query
        q_vec = await embed_query(query)
        return [item for item, _ in await self._backend.recall_as_of(
            q_vec, query, self._scope, at_time, top_k=top_k
        )]

    async def flush(self) -> int:
        """Force-consolidate buffered turns (use before checkpoints).
        Memobase: flush(batch) → summary_entry_chats + extract_profile + merge_profile + event_tag.
        Verso equivalent: batch extraction LLM call → ADD to backend.
        [Memobase controllers/buffer.py flush_buffer_by_ids]"""
        return await self._backend.flush_buffer(self._scope, force=True)
```

---

### Key constants (authoritative, attributed)

| Constant | Value | Source | Notes |
|---|---|---|---|
| Buffer flush trigger | 1024 tokens | Memobase `env.py:86` | Force-flush via `flush()` before checkpoint |
| Extraction LLM calls per flush | ~1 (additive V3) | Mem0 `main.py:662` | Single JSON-object extraction call |
| Working-set L1 cap | 20 (FIFO) | MemOS `tree.py:83` | |
| Durable tier cap | 1500 | MemOS `tree.py:84` | Bounded by budget policy |
| User-model tier cap | 480 | MemOS `tree.py:85` | |
| Consolidation trigger N | 50 new items | Honcho `config.py:1168` | AND min 8h interval |
| Consolidation trigger interval | 8 hours | Honcho `config.py:1170` | |
| Surprisal gate | top 10% novel | Honcho `config.py:1152` | geometric distance to cluster manifold |
| Surprisal min-replace threshold | 10 high-surprisal items | Honcho `config.py:1156` | |
| Search over-fetch | `max(top_k * 4, 60)` | Mem0 `main.py:1356` | Re-scoring pool |
| Semantic gate threshold | 0.1 | Mem0 `main.py:1343` | Applied BEFORE fusion |
| `ENTITY_BOOST_WEIGHT` | 0.5 | Mem0 `scoring.py:57` | |
| Entity dedup cosine threshold | 0.95 | Mem0 `main.py:918` | Entity merge gate |
| Entity boost min cosine | 0.5 | Mem0 `main.py:1478` | |
| Entity query spread attenuation | `1/(1 + 0.001*(n-1)²)` | Mem0 `main.py:1488` | Quadratic decay for high-fanout entities |
| RRF k (large ANN pools) | 60 | Hindsight `fusion.py:31`, Weaviate `hybrid_fusion.go:22` | |
| RRF k (small graph pools) | 1 | Graphiti `search_utils.py:1780` | k=1 for tens of candidates |
| RRF k (Qdrant default) | 2 | `reciprocal_rank_fusion.rs:14` | weight divides position: `1/((pos+1)/w + k-1)` |
| Recency decay window | 365 days | Hindsight `reranking.py:108` | `clamp(1 - days_ago/365, 0.1, 1.0)` |
| `_RECENCY_ALPHA` boost | 0.2 (±10%) | Hindsight `reranking.py:15` | Multiplicative; cannot override CE |
| `_TEMPORAL_ALPHA` boost | 0.2 (±10%) | Hindsight `reranking.py:16` | |
| `_PROOF_COUNT_ALPHA` boost | 0.1 (±5%) | Hindsight `reranking.py:17` | |
| CE reseed RRF floor | 0.1 | Hindsight `reranking.py:71-98` | Degenerate case guard |
| Graph entity lateral cap | 200 per entity | Hindsight `link_expansion_retrieval.py:14` | Prevents "User" entity explosion |
| Semantic kNN at insert | top-5, sim ≥ 0.7 | Hindsight `link_expansion_retrieval.py` | Pre-computed adjacency |
| Causal link score boost | weight + 1.0 | Hindsight `link_expansion_retrieval.py` | Highest-quality signal |
| Reflect loop max iters | 10 | Hindsight `agent.py:49` | Agentic consolidation loop |
| Reflect context fraction | 0.8 | Hindsight `engine/reflect/agent.py` | Budget for final synthesis |
| Hybrid alpha default | 0.75 | Weaviate `searcher.go` | Dense-favoring |
| sqlite-vec chunk size | 1024 | `sqlite-vec.c:5140` | |
| Brute-force threshold | ~10k items | Qdrant `types.rs:1872` `full_scan_threshold=10_000` | sqlite-vec stays brute-force below this |
| pgvector HNSW m | 16 | `src/hnsw.h:46` | |
| pgvector HNSW ef_construction | 64 | `src/hnsw.h:49` | Different from Qdrant's 100 |
| pgvector HNSW ef_search | 40 | `src/hnsw.h:52` | GUC `hnsw.ef_search` |
| DiskANN R / L / alpha | 50 / 100 / 1.2 | pgvectorscale `options.rs:23-41` | |
| DiskANN rescore | 50 | pgvectorscale `guc.rs` | Exact-rescore top-50 SBQ approx |
| BM25 k1 / b | 1.2 / 0.75 | Weaviate `config_handler.go:57-58` | Robertson standard values |
| Extraction context limit | 300 chars/message | Mem0 `prompts.py:965+` `PAST_MESSAGE_TRUNCATION_LIMIT` | Bounds prompt size |
| Last-messages context | 10 | Mem0 `main.py:703` | Write-time context window |
| Search query window | last 6 messages | Mem0 `proxy/main.py:168-179` | Bounds recall query length |

---

### Extraction prompt — additive write (verbatim shape, attributed)

The extraction system prompt follows Mem0's `ADDITIVE_EXTRACTION_PROMPT` shape (V3 default, `mem0/memory/main.py:724-727`). Key constraints copied verbatim from cluster consensus:

```
SYSTEM:
You are a memory extraction specialist. Extract factual information about the user/agent from the conversation.

RULES (from cluster-wide consensus — Mem0 V3, Graphiti extract_nodes.py, Hindsight fact_extraction.py):
1. NEVER extract abstract feelings, generic common nouns, pronouns, or bare kinship/pet terms.
   Extract "Nisha's dad" not "dad". Extract named entities, not "company", "school", "place".
2. NEVER generalize or paraphrase specific entities. Preserve every proper noun, brand,
   model number, quantity, color verbatim. "Nate plays games on a Gamecube" → keep "Gamecube",
   never "gaming console".
3. Extract only facts attributable to the primary entity. Do not create entries about other people.
4. Use absolute dates when possible ("June 26, 2025" not "yesterday").
5. If a fact is semantically equivalent to one already listed as linked (see EXISTING MEMORIES),
   DO NOT re-extract it. A more specific version of a listed fact IS a new fact.
6. Output format: {"memories": [{"text": "...", "linked_memory_ids": ["0", "3"], "attributed_to": "user"}]}
   Use only the integer ids shown in EXISTING MEMORIES for linked_memory_ids. Never emit UUIDs.

EXISTING MEMORIES (top-10 retrieved, indexed 0..9):
{existing_memories_as_indexed_list}
```

For agent-scoped writes, append (Mem0 `AGENT_CONTEXT_SUFFIX`, `prompts.py:947`):
```
The primary entity is an AI agent. Frame memories from the agent's perspective:
user-stated facts → "Agent was informed that [fact]";
agent actions → "Agent recommended [X]";
configuration → "Agent is configured to [behavior]".
The `attributed_to` field should still reflect the original source.
```

---

### Procedural-memory prompt — run-trace writes (verbatim structure, attributed)

For `remember(type=MemoryType.procedural)` triggered by the durable runtime at checkpoint:

Adopted almost verbatim from Mem0 `PROCEDURAL_MEMORY_SYSTEM_PROMPT` (`mem0/configs/prompts.py:326-408`):

```
## Summary of the agent's execution history
**Task Objective**: <overall goal>
**Progress Status**: <% complete, milestones>

N. **Agent Action**: <precise action + all params/targets/methods>
   **Action Result (Mandatory, Unmodified)**: <EXACT unaltered output — JSON/HTML/errors verbatim>
   **Key Findings**: ...
   **Errors & Challenges**: ...
   **Current Context**: ...

HARD RULES:
- Every output produced by the agent MUST be recorded verbatim.
- Do NOT paraphrase or summarize any output.
- Preserve exact URLs, element indexes, error messages, numeric counts ("3 out of 5 items processed"),
  and stack traces.
- If an action produced a JSON response, include the full JSON.
```

---

### Conflict-resolution prompt (read-time, chat tier) — temporal reasoning section

Adopted verbatim from Hindsight `engine/reflect/prompts.py:170-206`:

```
## Temporal Reasoning
Every memory carries: mentioned_at (when retained, always set), occurred_start/occurred_end (when it happened).

When facts about the SAME facet conflict (counts, statuses, ownership, location, preferences):
  The fact with the LATEST mentioned_at is AUTHORITATIVE. Later statements SUPERSEDE earlier ones.
  Do NOT average, sum, or favor an explicitly-dated fact over a more recent one.

For a TIMELINE, order by occurred_start/end (when things happened), NOT mentioned_at (when retained).

## Showing Your Reasoning (MANDATORY for any conflict resolution)
1. List relevant facts in mentioned_at order (oldest→newest) with asserted value.
2. Identify the authoritative fact (latest mentioned_at). Write its date.
3. List candidate events to apply on top (each with its date).
4. For EVERY event: "<event>(<date>) vs authoritative(<date>) → BEFORE/AFTER → KEEP/DROP".
   If event ≤ authoritative date, DROP it — it's already reflected; re-applying = double-counting.
   "This is the single most common mistake — do not skip this step."
5. Show arithmetic using only KEEP events.
6. If no clean winner → STOP, surface as UNRESOLVABLE ambiguity (name conflicting facts, give a range,
   never fabricate).
```

---

## Open Unknowns

1. **Embedding model / dimension choice.** The cluster spans 384 (Hindsight local ST), 1024 (Graphiti `text-embedding-3-small`, `embedder/client.py:23`), 1536 (Honcho `surprisal.py:362`). The right default for Verso depends on the model provider configured. DESIGNED default: 1024 (matches Graphiti, is within pgvectorscale SBQ's 2-bit regime for dim < 900 — actually above that threshold so SBQ drops to 1-bit). Need to dogfood to pick: `text-embedding-3-small` at 1024 (OpenAI) vs a local `all-MiniLM-L6-v2` at 384 for dev-tier. Decision: **defer to Phase 1 dogfood.**

2. **Surprisal tree implementation.** Honcho's `SurprisalTree` (`src/dreamer/surprisal.py`) uses cover tree / RP tree / LSH / sklearn KNN — which to ship in Verso's pure-Python implementation. NetworkX + scipy KNN is the simplest path but may be slow for N > 5k. Need to benchmark at the consolidation trigger (N=50 new items per fire). **Defer to Phase 1.**

3. **BM25 on sqlite-vec backend.** sqlite-vec has no BM25 arm. Options: (a) FTS5 virtual table alongside vec0 (SQLite native full-text, BM25 ranking via `bm25()` auxiliary function) — free, but requires a JOIN. (b) Sparse vectors stored in a second vec0 table (Milvus BM25-as-sparse-vector pattern). Option (a) is simpler for Phase 1. **Decide at Phase 1 sqlite-vec backend implementation.**

4. **NER strategy for entity extraction.** Cheap path = spaCy (Mem0, 4 types: PROPER/QUOTED/COMPOUND/NOUN, `entity_extraction.py:134`) or pg_trgm similarity (Hindsight). Expensive path = LLM (Graphiti, Honcho). For the additive write LLM call the entity extraction is already embedded in the prompt; spaCy post-process for the entity store / `entity_ids` field. **Start with spaCy; add LLM entity-type inference as an opt-in flag for the audit tier.**

5. **Memobase profile tier.** The two-level `topic → sub_topic → memo` profile (Memobase `user_profile_topics.py:11-77`, SQL-indexed, sub-100ms recall via keyed lookup) is a real ergonomic win for long-lived single-user relationships. It's cleanly separate from the fact/episodic store. Whether to ship it in Phase 1 or defer is unresolved. The implementation is ~200 lines + one Postgres table. **Candidate for Phase 1 if dogfood reveals the need.**

6. **Peer-symmetric `(observer, observed)` scoping for multi-agent.** The Honcho model is strictly more expressive for multi-agent memory ("what Agent-A believes about Agent-B"), but it adds complexity to the scope model and is only relevant once orchestration is in use (Phase 3). v1 can expose `observer`/`observed` fields in `MemoryScope` and `MemoryItem` (schema already includes them) but not activate the symmetric query path until the `orchestrate/` module exists. **Wire the fields now; activate the query path at Phase 3.**

7. **Consolidation LLM model choice.** The `reflect()` loop uses Hindsight's `_FINAL_PROMPT_CONTEXT_FRACTION = 0.8` and is an agentic loop (max 10 iters). Whether to use the main agent's model, a cheaper auxiliary model (Verso PRD §6.4 `AuxiliaryClient`), or a separate configured consolidation model is unresolved. Honcho's deriver uses one LLM call per batch; the dreamer uses a specialist with its own model config. **DESIGNED default: use the `AuxiliaryClient` (compression/classify role) for extraction; use the main agent's `synthesis_model` tier for the reflect loop. Verify at dogfood.**

8. **`recall_as_of` indexing.** The bi-temporal interval query (`valid_at ≤ T AND (invalid_at IS NULL OR invalid_at > T)`) needs both `valid_at` and `invalid_at` indexed. The schema adds a partial index `WHERE valid_at IS NOT NULL` but the query optimizer's behaviour on the compound interval predicate may require a composite index in practice. **Verify query plan at Phase 3 when Graphiti backend is implemented.**
