# infra-vector-memory — Vector / Memory Stores
## Cluster: Turbopuffer + LanceDB

Sources: `teardowns/TURBOPUFFER.md` (11,736 lines, Rounds 1–2 + R3–R6), `teardowns/LANCEDB.md` (31,400 lines, §1–R6.10).
Both are Tier-1A (installed SDK source, cloned repos, live probes, blog verbatim).

---

## Turbopuffer

### What it is

Closed-source SaaS vector + BM25 + scalar-filter search engine.
Core thesis: object storage (S3/GCS) is the source-of-truth LSM; stateless query nodes hold a tiered DRAM + NVMe SSD cache in front of it.
"SSD-tier latency on S3 prices" — $70/TB/month vs $1,600–$3,600 for DRAM-backed competitors.
Customers include Cursor, Notion AI, Linear, Superhuman, Anthropic.
Scale (May 2026): 4 trillion documents, 10M+ writes/s, 25k+ queries/s.

### Architecture

```
client → stateless router → query node (NVMe SSD + DRAM + L3 cache)
                                │
                         object storage (GCS/S3) — LSM tree (source of truth)
                                │
                     stateless WAL broker (queue.json file)
```

Every write goes to the WAL on object storage first; any node can serve any namespace by warming from cold (~500 ms p90). Cold namespaces pay only object-storage cost (~$70/TB/month). Pinned namespaces get dedicated always-warm replicas for high-QPS workloads.

### Agent Loop / Tool Use

Turbopuffer is not an agent framework — it is a retrieval primitive. Its relevance to Verso is:

1. **It is the canonical external tool that Verso agents call for semantic retrieval.** The teardown reveals the exact call contract.
2. **It ships its own MCP server** (`turbopuffer.stlmcp.com`, Stainless-hosted) — a first-class example of how a storage layer exposes itself to LLM agents.

#### MCP server architecture (KNOWN, live probes 2026-05-24)

- Transport: MCP over HTTP+SSE (Streamable HTTP, `protocolVersion: "2024-11-05"`).
- Auth: simple bearer-via-header (`x-turbopuffer-api-key: tpuf_...`). No OAuth 2.1 on the hosted endpoint.
- Tools declared: exactly two:
  - `execute` — "Runs JavaScript code to interact with the Turbopuffer API. Define an async function named 'run' that takes a single parameter of an initialized SDK client and it will be run." Input: `{ code: string, intent: string }`. NOT marked `readOnlyHint`.
  - `search_docs` — "Search SDK documentation to find methods, parameters, and usage examples." Input: `{ query: string, language: enum[...], detail?: enum[default,verbose] }`. Marked `readOnlyHint: true`.
- Capabilities: `{ "tools": {}, "logging": {} }` — no resources, no prompts, no sampling.
- Sandbox: Deno 2.7.7 on Fly.io (Chicago, `ord`), 2 GB VM, Docker image `code-tool-sandboxes:20260429`.
- Isolation: iptables-per-VM, `--deny-net` for user code (can only reach turbopuffer SDK), `--deny-read` outside `/workspace`.
- **State**: each `execute` invocation is stateless — "Variables do not persist between calls." This is the key design choice.

#### MCP system prompt (verbatim from `initialize` response)

```
## Turbopuffer SDK — Agent Operational Guide

Turbopuffer is a vector database API for storing, searching, and filtering document embeddings.

### Hybrid ranking
rank_by: ['Sum', [
  ['Product', 0.7, ['vector', 'ANN', queryVec]],
  ['Product', 0.3, ['body', 'BM25', 'search terms']],
]]

## Important
- If you don't know what namespaces exist, list them first with `client.namespaces()`
- Before querying, check the namespace schema with `ns.schema()` to see available attributes
- Always truncate output with substring() to avoid token limits
- Do not add try-catch; the tool handles errors
- Variables do not persist between calls
```

### Query DSL (KNOWN from `types/custom.py:1-81`)

Filters are tagged tuples forming a composable boolean algebra:

```python
Filter = Union[
    Tuple[str, Literal["Eq"], ...]        # exact match
    Tuple[str, Literal["In"], Sequence]   # set membership
    Tuple[str, Literal["Gt"|"Gte"|"Lt"|"Lte"], ...]  # range
    Tuple[str, Literal["Glob"], str]      # path pattern
    Tuple[str, Literal["ContainsAllTokens"], str, ...]  # full-text, with last_as_prefix for search-as-you-type
    Tuple[Literal["Not"], Filter]
    Tuple[Literal["And"], Sequence[Filter]]
    Tuple[Literal["Or"], Sequence[Filter]]
]

RankBy = Union[
    Tuple[Literal["vector", field], Literal["ANN"], List[float]]
    Tuple[Literal["field"], Literal["BM25"], str]  # full-text score
    Tuple[Literal["Sum"], Sequence[RankBy]]
    Tuple[Literal["Product"], float, RankBy]       # weighted combination
    Filter                                          # 0/1 clause
]
```

Key architectural decision: BM25 and ANN scoring run inside the same vectorized MAXSCORE engine — not as two staged pipelines. This eliminates a round-trip and lets arbitrary linear combinations of scores run as a single query.

### Write Path (KNOWN from `resources/namespaces.py:700-815`)

The `write` endpoint is a single overloaded operation handling upserts, patches, deletes, schema updates, branch, and copy. Write modes:
1. `rows` — row-by-row upsert `[{id, vector, attr...}]`
2. `columns` — columnar batch `{col: [values]}`
3. `filter` — match-and-modify (SQL UPDATE WHERE equivalent)

Notable: `patch_by_filter` + `patch_by_filter_allow_partial` enable "update metadata without re-uploading vectors" — essential for AI-agent workflows (e.g. "mark as read", "update status").

`disable_backpressure: bool` — disables HTTP 429 throttling for bulk ingest. Server normally returns 429 when write queue exceeds threshold.

### Consistency Model (KNOWN from SDK + blog)

- Default: **strong consistency** (CORRECTION: Round 1 assumed eventual; Round 2 docs page `/docs/architecture` corrects this to strong-by-default).
- Optional `?consistency=eventual` for lower-latency reads.
- Responses expose cache state: `cache_hit_ratio: float`, `cache_temperature: "hot"|"warm"|"cold"`, `exhaustive_search_count: int`.
- Strong consistency = the WAL group-commit model: S3 `If-Match`/`If-None-Match` CAS ensures atomic broker promotion and conflict resolution.

### Exact Constants (KNOWN)

| Constant | Value | Source |
|---|---|---|
| `DEFAULT_TIMEOUT` | 60s (connect=5s) | `_constants.py` |
| `DEFAULT_MAX_RETRIES` | 4 | `_constants.py` |
| `INITIAL_RETRY_DELAY` | 0.25s | `_constants.py` |
| `MAX_RETRY_DELAY` | 8.0s | `_constants.py` |
| `max_connections` | 512 | `_constants.py` |
| `keepalive_expiry` | 60s | `_constants.py` |
| `MIN_GZIP_SIZE` | 1,024 bytes | `transport_httpx.py` |
| `gzip compresslevel` | 1 (fastest) | `transport_httpx.py` |
| `RETRY_AFTER_LIMIT_SECS` | 1,800s (30 min) | `_constants.py` |
| Cold start latency | ~500 ms p90 | blog |
| ANN p99 (100B vectors) | 200 ms | blog |
| Cluster size | 100 vectors | blog (ANN v3) |
| SPFresh branching factor | 100x | blog (ANN v3) |
| Rerank fraction | 1% of data vectors | blog (ANN v3) |
| BM25 k1 | configurable (default unlisted; turbopuffer exposes `k1/b` unlike Tantivy which hardcodes) | `full_text_search_config_param.py` |
| BM25 max_token_length | range [1, 254], default 39 | `full_text_search_config_param.py` |
| Branch cost | $0.032 per branch | docs |

### Retry / Backoff (KNOWN)

```
backoff = min(0.25 × 2^retry, 8.0) × (1 - 0.25 × random())
```
- Retry on: 408, 409, 429, 5xx — plus server-controlled `x-should-retry: true/false` header override.
- Idempotency key: `stainless-python-retry-{uuid4}` per retry, sent as `Idempotency-Key` header.
- Server can suppress retries for specific 5xx (e.g. truly broken state).

### Error Shape (KNOWN, live probes)

```json
{"error": "💔 You are not authorized ...", "status": "error"}
```

Uniform envelope: `{error: string, status: "error"}`. Emoji signatures: `🐡` for auth sentinel on health, `💔` for auth failure. Status code → exception mapping covers 400, 401, 403, 404, 409 (lock conflict), 422 (validation), 429, 5xx.

### Client-Side Telemetry (KNOWN)

Every response includes 6 client-side timing fields + server-side `server_total_ms` + `query_execution_ms` + `cache_hit_ratio` + `cache_temperature` + `exhaustive_search_count`. This is end-to-end latency attribution without a separate APM.

### Real-world Agent Use Pattern (KNOWN, SID AI case study)

SID-1 agentic-search model uses turbopuffer for RL training retrieval:
- Modified GRPO: 16 attempts/question, 256 questions/batch, 1,000+ steps
- Per step: 256 × 16 × ~20 searches ≈ 82,000 searches
- Sustained: >100 QPS; bursts: 1,000+ QPS over ~10s windows
- Agent learns to issue 4–8 concurrent searches per turn (parallelism emergence, 18–30s → 5s)
- Tools the RL model chooses from: ANN, BM25, regex, HyDE, combined with native filtering
- Corpus versioning: `branch()` = constant-time namespace fork (shared storage, independent manifest)
- Pinning during training to keep cache hot

---

## LanceDB / Lance

### What it is

Open-source columnar file format (`lance`) + table format + embedded query engine.
Lance is **not a vector database** — it is a page-based columnar file format and a Parquet-like table format designed for AI/ML workloads, with first-class vector indexes.
LanceDB is a thin Rust library layer wrapping Lance with `Connection`/`Table` API, embedding-function registry, FTS, and rerankers.

Modes: embedded (`pip install lancedb`, runs in-process) or LanceDB Cloud (SaaS, server code is closed).

### Architecture (crate hierarchy)

| Layer | Crate | Purpose |
|---|---|---|
| File format | `lance-file`, `lance-encoding` | Page-based columnar bytes-on-disk, encoding cascade |
| Table format | `lance-table` (protos) | Manifest, Fragment, Schema evolution, transaction commit |
| Dataset API | `lance` | Scanner, Writer, Dataset, ConflictResolver, Index |
| IO scheduler | `lance-io` | Object-store abstraction, IO scheduler, page cache |
| Vector/scalar indexes | `lance-index` | IVF, PQ, HNSW, FTS, BTree, Bitmap, BloomFilter, RTree |
| Vector math | `lance-linalg` | L2/Cosine/Dot/Hamming with `target_feature` SIMD dispatch |
| DataFusion glue | `lance-datafusion` | `TableProvider` impl, predicate pushdown |
| Python FFI | `python/` (PyO3) | Zero-copy Arrow bindings + async bridge |
| LanceDB layer | `lancedb/rust/lancedb/` | `Connection`/`Table`/Embedding/Reranker |
| Namespace | `lance-namespace-impls` | Multi-catalog: `DirectoryNamespace`, `ManifestNamespace`, `RestNamespace`, `RestAdapter` |

### Key Architectural Bets (KNOWN)

1. **Page-based, not row-group-based** — each column flushes pages independently based on its own size budget. True column projection: reading `embedding[5]` loads only that slice.
2. **Object store as source of truth, not append-only LSM** — each write produces new immutable data files + a new manifest version. No mandatory compaction; rewrites are explicit transactions.
3. **Stable row IDs** — rows have identity that survives deletes/updates (`rowids.proto`). Vector indexes are not rebuilt on most mutations.
4. **Indexes as plugins via `google.protobuf.Any`** — `IndexMetadata.index_details = Any` with reverse-DNS type URLs. New index types are backward-compatible.
5. **DataFusion for SQL** — Lance implements `TableProvider`/`ExecutionPlan` and delegates SQL planning to DataFusion. No custom parser.
6. **MemWAL for streaming ingest** — WAL + MemTable (`mem_wal.rs`, `ShardManifest` proto) for low-latency streaming ingest that auto-flushes to base table.

### Transaction Model — OCC Loop (KNOWN, `retry.rs:75-130`)

```rust
pub async fn execute_with_retry<E: RetryExecutor>(executor: E, dataset: Arc<Dataset>, config: RetryConfig) -> Result<E::Result> {
    while backoff.attempt() <= config.max_retries {
        let data = executor.execute_impl().await??;         // 1. execute (no commit yet)
        match executor.commit(dataset_ref, data).await? {
            Ok(result) => return Ok(result),                // 2. commit → new manifest
            Err(Error::RetryableCommitConflict) => {
                dataset_ref.checkout_latest().await?;       // 3. re-read latest
                sleep(backoff.next_backoff()).await;         // 4. exponential backoff
                continue;                                   // 5. re-execute against new state
            }
        }
    }
    Err(Error::too_much_write_contention(...))
}
```

Default config: `max_retries = 10`, `retry_timeout = 30s`.

### SlotBackoff — Contention-Aware (KNOWN, `backoff.rs:111-146`)

```rust
pub struct SlotBackoff { base: 2, unit: 50ms (then = first_attempt_elapsed * 1.1), starting_i: 2, ... }
// Attempt N: pick random slot from 0..2^(N+2), delay = slot * unit
```

Unit adapts to the actual operation duration on first conflict — each slot is ~1 operation's time, so retriers are statistically uncorrelated. `base=2, starting_i=2`: slots grow as 4, 8, 16, 32, ...

### Session / Cache Architecture (KNOWN, `session.rs`, `caches.rs`, `index_caches.rs`)

```rust
pub struct Session {
    pub(crate) index_cache: GlobalIndexCache,        // 6 GiB default, Moka-backed
    pub(crate) metadata_cache: GlobalMetadataCache,  // 1 GiB default
    pub(crate) index_extensions: HashMap<(IndexType, String), Arc<dyn IndexExtension>>,
    store_registry: Arc<ObjectStoreRegistry>,
}
```

Three-level key hierarchy:
```
GlobalMetadataCache → DSMetadataCache (prefix=dataset_uri) → FileMetadataCache (prefix=file_path)
GlobalIndexCache    → DSIndexCache    (prefix=dataset_uri) → index entry (prefix=index_uuid[-fri_uuid])
```

Metadata cache key types:
| Key | Value |
|---|---|
| `manifest/{version}/{e_tag}` | `Manifest` |
| `txn/{version}` | `Transaction` |
| `deletion/{frag}/{version}/{id}/{suffix}` | `DeletionVector` (RoaringBitmap) |
| `row_id_index/{version}` | `RowIdIndex` |
| `row_id_sequence/{frag_id}` | `RowIdSequence` |

`Session::new(0, 0, ...)` disables all caches. Two datasets opened with the same `Session` share cache entries (keyed by URI prefix). Invalidation via e_tag prevents stale manifests on table recreation.

Default: index=**6 GiB**, metadata=**1 GiB**.

### Embedding / Retrieval API (KNOWN from `lancedb/rust/lancedb/`)

```rust
pub trait EmbeddingFunction: Debug + Send + Sync {
    fn source_type(&self) -> Result<Cow<'_, DataType>>;
    fn dest_type(&self) -> Result<Cow<'_, DataType>>;
    fn compute_source_embeddings(&self, source: Arc<dyn Array>) -> Result<Arc<dyn Array>>;
    fn compute_query_embeddings(&self, input: Arc<dyn Array>) -> Result<Arc<dyn Array>>;
}
```

Asymmetric embedding supported — `compute_source_embeddings` vs `compute_query_embeddings` use different prompts/prefixes (E5, BGE-style). Adapters for OpenAI (default: `text-embedding-ada-002`, 1536d), AWS Bedrock, sentence-transformers. All feature-gated (`#[cfg(feature = "openai")]`).

### Hybrid Search + Reranker (KNOWN)

```rust
#[async_trait]
pub trait Reranker: Debug + Sync + Send {
    async fn rerank_hybrid(&self, query: &str, vector_results: RecordBatch, fts_results: RecordBatch) -> Result<RecordBatch>;
    fn merge_results(&self, vector_results: RecordBatch, fts_results: RecordBatch) -> Result<RecordBatch>;
}
```

Output must contain `_relevance_score` column. Column naming convention:
- FTS → `_score` (higher is better, BM25)
- Vector search → `_distance` (lower is better, L2/cosine)
- Hybrid output → `_relevance_score` (higher is better, RRF or normalized)

Built-in reranker: **RRF only** (`rrf.rs:84-94`):
```rust
let score = 1.0 / (rank_i as f32 + self.k);  // k = 60 (default, from original RRF paper)
rrf_score_map.entry(result_id).and_modify(|e| *e += score).or_insert(score);
```
RRF uses ranks, not raw scores — scale-invariant. Works equally well with BM25, TF-IDF, or cosine distance.

Score normalization alternative (min-max, `hybrid.rs:120-174`):
```rust
let rng = if max - min < 10e-5 { max } else { max - min };
// invert=true: score = 1 - (score - min) / rng  (flip distance to similarity)
```
`10e-5` epsilon handles "all scores equal" edge case.

### BM25 Constants (KNOWN, `scorer.rs:14-17`)

```rust
pub const K1: f32 = 1.2;
pub const B: f32 = 0.75;
```

Standard Robertson defaults, identical to Lucene/Elasticsearch. Fixed (not tunable from the public API unlike turbopuffer).

### Vector Index Defaults (KNOWN from builder code)

**HNSW** (`hnsw/builder.rs:56-91`):
```rust
max_level: 7, m: 20, ef_construction: 150, prefetch_distance: Some(2)
```

**IVF build** (`ivf/builder.rs`):
- `num_partitions`: default `sqrt(num_rows)` (square-root heuristic)
- `num_sub_vectors` (PQ): default 16

**IVF_HNSW_PQ** = recommended for medium-to-large datasets: IVF partitions + HNSW per partition + PQ residuals.

**Quantization options** (protobuf `VectorIndexDetails`): flat, PQ (8-bit), SQ (scalar quantization), RQ (RaBit Quantization with FAST or MATRIX rotation).

### IO Constants (KNOWN, `object_store.rs:60-73`)

```rust
DEFAULT_LOCAL_BLOCK_SIZE: usize = 4 * 1024     // 4 KiB
DEFAULT_CLOUD_BLOCK_SIZE: usize = 64 * 1024    // 64 KiB (min useful S3 read)
DEFAULT_CLOUD_IO_PARALLELISM: usize = 64       // concurrent S3 connections
DEFAULT_MAX_IOP_SIZE: u64 = 16 * 1024 * 1024  // 16 MiB per request (env: LANCE_MAX_IOP_SIZE)
DEFAULT_DOWNLOAD_RETRY_COUNT: usize = 3
```

### IO Scheduler (KNOWN, `scheduler.rs`)

Two-budget backpressure:
1. **IOP budget**: `iops_avail` (default 32 cloud). Concurrent S3 GETs.
2. **Byte budget**: `bytes_avail`. Bytes buffered-but-not-decoded. Can go negative for high-priority requests to prevent deadlock.

Priority queue is a `BinaryHeap` with inverted `Ord` → min-heap on priority → lower priority numbers = more urgent = dispatched first. Combined with row-offset-as-low-bits encoding, this dispatches IO requests in roughly row order (S3 sequential-access optimization).

Deadlock-avoidance: if a new request has equal-or-higher urgency than the minimum currently in-flight, it's admitted regardless of byte budget. Prevents the scenario where a consumer is blocked on indirect IO needed to decode the data it's already consuming.

### PyO3 Async Bridge (KNOWN, `executor.rs`)

```rust
pub struct BackgroundExecutor {
    runtime: tokio::runtime::Runtime,  // separate runtime in background threads
}
// 1. Release GIL via py.detach()
// 2. spawn(future) to background runtime
// 3. poll mpsc channel with 100ms signal-check interval (KeyboardInterrupt support)
// 4. Re-acquire GIL on result
```

Solves: `block_on` panics inside an existing Tokio runtime; GIL must be released before blocking. The signal-check poll loop (`SIGNAL_CHECK_INTERVAL = 100ms`) makes Ctrl-C work in Python — `handle.abort()` on signal.

### GC / Cleanup (KNOWN, `cleanup.rs:131-133`)

Conservative: never deletes the latest/tagged/newer versions. Unreferenced file is deleted only if it is ≥ **7 days old** (`UNVERIFIED_THRESHOLD_DAYS`), unless `delete_unverified=true`. Rate limiting: **1,000 files** per batch (S3) / **256** (Azure).

### Tags, Branches, Time Travel (KNOWN, `refs.rs`, `dataset.rs`)

- Tags: `_refs/tags/<tag>.json` — pins `{branch, version, manifest_size}`
- Branches: `_refs/branches/<branch>.json` — carries `BranchIdentifier` lineage chain (parent cannot be deleted while child forks from it)
- Time travel: `checkout_version()` returns new `Dataset` (history never mutated); `restore()` appends new version whose payload is the checked-out version.

### Catalog: `ManifestNamespace` (KNOWN, `dir/manifest.rs`, 4,072 lines)

The most novel catalog design: **a Lance table named `__manifest` is used AS the catalog itself**. New table creations are `merge_insert` operations on the `__manifest` table. This means the catalog is itself versioned, transactional, queryable with SQL, and stored on the same object store. No external Hive/Glue/Unity catalog dependency. Two concrete catalog backends: `DirectoryNamespace` (filesystem/cloud) and `ManifestNamespace`.

---

## Cross-System Comparison

| Dimension | Turbopuffer | LanceDB |
|---|---|---|
| **License** | Closed SaaS | Apache 2.0 |
| **Deployment** | Hosted only | Embedded or SaaS |
| **Storage model** | LSM-on-S3 (WAL + group commit + compaction) | Immutable data files + manifest versions (Iceberg-like) |
| **Write conflict** | CAS on `queue.json`, broker-mediated group commit | OCC retry loop, `RetryableCommitConflict`, 10 retries, 30s timeout |
| **Session / cache** | Per-namespace SSD cache (pinnable) + DRAM | Per-`Session` Moka caches: index (6 GiB) + metadata (1 GiB) |
| **Vector index** | SPFresh (incremental cluster split/merge) + RaBitQ binary quantization | IVF_HNSW_PQ (composite stages), also PQ/SQ/RQ |
| **FTS** | Vectorized MAXSCORE, tunable BM25 (k1, b, tokenizer v0–v3) | WAND + Block-Max, fixed k1=1.2 / b=0.75, standard tokenizer |
| **Hybrid** | Single-query algebraic combination (ANN + BM25 + Filter as RankBy DSL) | Two-pass (FTS + vector), then RRF reranker (k=60) or min-max normalize |
| **Filtering** | Native: attribute index co-designed with SPFresh cluster topology | DataFusion predicate pushdown + zone maps |
| **API style** | REST (Stainless-generated SDK, Python/JS/Go/Ruby), MCP server | Library API (Rust/Python/JS) + optional REST via `RestAdapter` |
| **MCP** | First-class: `turbopuffer.stlmcp.com` with `execute` + `search_docs` tools | No built-in MCP; access via REST adapter |
| **Streaming ingest** | WAL group commit (queue.json, brokered) | MemWAL + MemTable auto-flush |
| **Branching** | Constant-time namespace branch ($0.032 each) | Tags + branches in `_refs/` with lineage chain |
| **Cost model** | Namespace-as-corpus; inactive = object-storage cost; active = SSD cache | Embedded = free; SaaS = managed service |

---

## Verso Implications

### COPY

1. **Two-tool MCP pattern for external retrieval.** Turbopuffer's MCP server exposes exactly two tools: `execute` (mutating) and `search_docs` (read-only, annotated `readOnlyHint: true`). This minimalism is correct. Verso's built-in retrieval tool should follow the same shape: one mutating write/index tool and one read-only query/search tool, with `readOnlyHint` on the query tool.

2. **Stateless sandbox per invocation.** "Variables do not persist between calls" is an explicit MCP instruction. Verso tools should be stateless by default: each tool call gets a fresh execution context. Cross-call state must flow through Verso's memory layer (not tool-side variables), making the state explicit and observable.

3. **Server-controlled retry signal (`x-should-retry` header).** Turbopuffer's router marks specific 5xx responses as "do not retry" (broken state) and specific 4xx as "do retry" (ephemeral lock). Verso should propagate a retry hint from tool implementations back to the agent loop: tool calls that fail transiently should be retried by the loop; tool calls that fail permanently should surface as hard errors. This keeps retry policy in the right place.

4. **Cache health as first-class response metadata.** Turbopuffer returns `cache_hit_ratio`, `cache_temperature: "hot"|"warm"|"cold"`, and `exhaustive_search_count` on every query. Verso tool wrappers for external stores should surface this metadata — it's the signal for the agent to decide whether to wait for cache warmup or accept degraded retrieval quality.

5. **Lance's OCC retry pattern for Verso's memory writes.** The `execute_with_retry` loop — execute separately from commit, retry on conflict by re-executing (not just re-committing) against the latest state — is the correct pattern for concurrent agent memory writes. Verso's memory store should implement the same two-phase execute/commit with `SlotBackoff`: unit adapts to actual operation duration, exponential slot growth prevents thundering herd under high write concurrency.

6. **Three-level prefixed cache hierarchy.** Lance's `Global → Dataset → File` prefix chain (with URI-prefixed keys) is the right model for Verso's agent session cache: `Global → Session → Task`. Two agents opened with the same `Session` share cache entries; different sessions are namespace-isolated. Invalidation via e_tag prevents serving stale state after the underlying store changes.

7. **Asymmetric embedding (source vs query).** Lance's `EmbeddingFunction` trait separates `compute_source_embeddings` from `compute_query_embeddings`. Verso's memory store should preserve this distinction — the document embedding and the query embedding may use different prompts (E5, BGE-style). Collapsing them to a single function silently degrades retrieval quality for asymmetric models.

8. **RRF as default hybrid reranker.** LanceDB ships RRF (k=60) as its only built-in reranker. Verso should do the same for hybrid search in its memory layer: RRF is scale-invariant, requires no training, and the k=60 default is empirically near-optimal (cited to the original 2009 paper). Make it the default; allow pluggable `Reranker` trait for custom scoring.

9. **Schema-on-write for namespace bootstrap.** Turbopuffer's first `write` call with a `schema` parameter creates the namespace implicitly. Verso's memory store should follow the same convention: no explicit "create collection" step; the schema is inferred from the first write. This reduces setup boilerplate in agent tools.

10. **Corpus branching for versioned memory.** Turbopuffer's `branch()` = constant-time namespace fork (shared object storage, independent manifest). The SID AI case study demonstrates using this for RL training (branch corpus when training data changes, keep parent intact). Verso's long-term memory should support the same: branching the memory namespace for experiments or rollback without copying data.

11. **`ManifestNamespace` — catalog-as-table.** Lance's most novel catalog design uses a Lance table named `__manifest` as the catalog itself. No external catalog dependency. Verso's session/memory metadata store should be self-contained and stored in the same object store as the data — no separate catalog service required.

12. **GC conservatism.** Lance only deletes unreferenced files older than **7 days** unless `delete_unverified=true`. Verso's memory GC should be conservative by default: prefer keeping stale entries to incorrectly evicting live ones. Pair with explicit TTL-based cleanup on a scheduled interval rather than aggressive eager eviction.

### AVOID

1. **Pinning as a billing feature.** Turbopuffer exposes `replicas` (dedicated always-warm replicas) as a paid tier. Verso's memory store should treat cache warmth as infrastructure config, not as a product tier. Agents should not need to know about cache pinning; Verso should handle that transparently based on access patterns.

2. **Fixed BM25 constants (LanceDB pattern).** LanceDB hardcodes `K1=1.2, B=0.75`. Turbopuffer exposes these as per-namespace config. For Verso's FTS integration, the tunable-per-collection approach is correct — different corpora (code, prose, logs) have different optimal BM25 parameters.

3. **Two-pass hybrid search with a separate reranker step.** LanceDB runs FTS and vector search independently and then merges with RRF. Turbopuffer runs both inside the same MAXSCORE engine with a unified scoring algebra. For Verso's query layer, prefer the unified approach when both FTS and vector are needed: emit a single query with `rank_by: ['Sum', [['Product', 0.7, ANN], ['Product', 0.3, BM25]]]` rather than two separate queries + merge.

4. **Endpoint listing as architecture.** Both teardowns confirm that DNS/header/status-code probing reveals surface, not logic. Verso should not over-instrument the retrieval path with per-status-code business logic. The error envelope (`{error: string, status: "error"}`) is sufficient; the agent loop should classify errors as retryable/non-retryable and route accordingly.

5. **Blocking PyO3 patterns without GIL release.** Lance's `BackgroundExecutor` solves a real production problem: Rust async code called from Python deadlocks if the GIL is not released before blocking. If Verso ships Python bindings, copy the background-executor pattern exactly: separate Tokio runtime, `py.detach()` before spawning, 100ms signal-check poll loop for Ctrl-C support.

6. **Durable state inside MCP sandbox.** Turbopuffer explicitly marks sandbox state as non-persistent. Verso tool implementations should follow this: tools are pure functions over inputs. Any state that needs to persist across calls must be stored explicitly in Verso's memory layer, not in tool-local variables or sandbox globals.

### Verso Could Improve By

1. **Exposing cache health in the agent's observation.** Currently no agent framework surfaces the equivalent of turbopuffer's `cache_temperature` in the agent context. Verso could expose a standard `retrieval_quality` signal per tool call (cache hit ratio, exhaustive vs ANN, index freshness) so the agent can adapt its search strategy (e.g. fall back to exhaustive on a cold cache, hedge with broader queries).

2. **Adaptive query mode selection.** Turbopuffer's `kNN` vs `ANN` mode switch (guaranteed 100% recall at higher cost vs approximate at lower cost) is manual. Verso could auto-select based on the filter selectivity: if the filter narrows the candidate set below a threshold (~10K documents), switch to exhaustive automatically. Expose as `nprobes: "auto"` with a selectivity estimator.

3. **First-class slot-backoff for concurrent agent writes.** Lance's `SlotBackoff` (unit = first_attempt_elapsed × 1.1, slots = 2^(N+2)) adapts to the actual operation duration. Most agent frameworks use fixed-interval retry. Verso's memory write path should use adaptive slot-backoff when multiple agents write to shared memory concurrently — prevents thundering herd during burst.

4. **Hybrid search as a first-class agent primitive.** Neither LangGraph nor CrewAI treat hybrid search (dense + sparse + filter) as a first-class tool shape. Verso could ship a `HybridSearch` tool type with a declarative `rank_by` DSL (analogous to turbopuffer's) as a built-in, with pluggable backends (turbopuffer, LanceDB, Qdrant). This would let agent authors express "find by semantic similarity + keyword + metadata filter" in a single tool invocation.
