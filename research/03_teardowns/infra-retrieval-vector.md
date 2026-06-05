# Retrieval & Vector Stores — Verso Research Note
## Cluster: infra-retrieval-vector
### Systems: Qdrant · Chroma · pgvector + pgvectorscale · Weaviate · Milvus + Knowhere · Vespa · sqlite-vec
*Sources: cloned `--depth=1` repos read line-by-line (2026-06-05): github.com/qdrant/qdrant, chroma-core/chroma, pgvector/pgvector, timescale/pgvectorscale, weaviate/weaviate, milvus-io/milvus, milvus-io/knowhere, vespa-engine/vespa, asg017/sqlite-vec. Cross-reference: `03_teardowns/infra-vector-memory.md` (Turbopuffer + LanceDB), `03_teardowns/infra-retrieval-tools.md` (LlamaIndex/Tavily/Exa/Firecrawl).*

> **Lens.** Verso needs a `MemoryStore` edge: a pluggable interface where agents persist/retrieve semantic memories. The design forks on four seams — (1) **embedded↔distributed** (same code in tests and prod), (2) **hybrid retrieval** (dense + sparse fused server-side), (3) **storage engine** (append-only log + compaction vs. mutable slab allocator), (4) **filtered ANN** (typed-memory filters without recall collapse). Each system below is mined for the *specific* mechanism that informs one of those seams, at reimplementable depth.

> Label key: **KNOWN** = read from source at `file:line`. **INFERRED** = derived from code + docs. **DESIGNED** = our engineering for a Verso gap.

---

## Qdrant

### What It Is

Production vector DB in Rust. Dense vectors → HNSW; sparse vectors → inverted index (`lib/sparse/`); payload + sparse data → **Gridstore**, a custom mmap slab allocator (not RocksDB anymore). The load-bearing piece for Verso is the **Query API**: one request carries a tree of `prefetch` legs, each a sub-query, merged server-side by a `FusionQuery` (RRF or DBSF) or a rescore step. This is the cleanest published "one request, multiple retrieval legs, fused on the server" model.

### Hybrid Retrieval — Query API prefetch → fuse → rescore

A `QueryRequest` is recursive. Each node has an optional `prefetch: Vec<Prefetch>` (sub-queries run first) and a `query` that consumes their merged output. The leaf queries hit segments (dense HNSW, sparse inverted, or full-scan); the parent query is a *fusion* or *rescore* over the children's `Vec<ScoredPoint>` lists.

**Fusion dispatch** (KNOWN, `lib/collection/src/shards/local_shard/query.rs:424-451`):

```rust
fn fusion_rescore(sources: Vec<Vec<ScoredPoint>>, fusion: FusionInternal, score_threshold, limit) {
    let fused = match fusion {
        FusionInternal::Rrf { k, ref weights } => rrf_scoring(sources, k, weights_slice)?,  // Reciprocal Rank Fusion
        FusionInternal::Dbsf => score_fusion(sources, ScoreFusion::dbsf()),                 // Distribution-Based Score Fusion
    };
    // then take_while(score >= score_threshold).take(limit)
}
```

#### RRF — exact algebra (KNOWN, `lib/segment/src/common/reciprocal_rank_fusion.rs`)

```rust
pub const DEFAULT_RRF_K: usize = 2;   // line 14 — NOT 60

fn position_score(position: usize, k: usize, weight: f32) -> f32 {
    if weight <= 0.0 { return 0.0; }
    1.0 / ((position + 1) as f32 / weight + k as f32 - 1.0)   // line 38
}
```

The accumulation (lines 75-90): for each source list, walk it in *rank order* (input scores are explicitly ignored — "only the order matters"), compute `position_score(pos, k, weight)`, and **sum** scores per point id into an `AHashMap<ExtendedPointId, ScoredPoint>`. Then sort descending by accumulated score. Ties are not broken.

> **[CORRECTION 2026-06-05]** The target brief said "FusionQuery RRF k=60". That is the *textbook* Cormack 2009 constant (and Qdrant uses `k=60` only inside one unit test, `reciprocal_rank_fusion.rs:205`). The **actual production default is `DEFAULT_RRF_K = 2`** (`reciprocal_rank_fusion.rs:14`), wired in at the REST→internal conversion (`lib/shard/src/query/conversions.rs:189-205`): bare `Fusion::Rrf` → `k: DEFAULT_RRF_K`; explicit `Rrf { k, weights }` → `k.unwrap_or(DEFAULT_RRF_K)`. With weight=1 the formula reduces to `1/(position + k) = 1/(position + 2)` — i.e. the top result scores 0.5, second 0.333, etc. (verified by test `test_rrf_scoring_one`: score == 0.5).

The **weighting** is the non-obvious part: weight does not multiply the score, it *divides the position*. `position_score(pos, k, w) = 1/((pos+1)/w + k − 1)`. A 3:1 weight ratio means "for every 3 results of the first prefetch, take one of the second" — a high-weight source's rank-3 item contributes like a rank-1 item would unweighted (`test_rrf_scoring_weighted_ratio`).

#### DBSF — distribution-based score fusion (KNOWN, `lib/segment/src/common/score_fusion.rs`)

The alternative to RRF when raw scores carry signal. Each source list is normalized, weighted, summed per id, sorted. `dbsf()` config = `{ method: Sum, norm: Distr, weights: [], order: LargeBetter }`.

- **`distr_norm`** (lines ~150): Welford one-pass mean+variance, then map each score to `(score − (mean − 3σ)) / ((mean + 3σ) − (mean − 3σ))` — i.e. normalize using the ±3σ band as [0,1] extremes. Single-point lists collapse to score 0.5.
- **`min_max_norm`** (alternative): `(score − min)/(max − min)`; if `min == max`, all scores → 0.5.

So Qdrant ships **two** server-side fusers: RRF (rank-only, robust to scale mismatch between cosine and BM25) and DBSF (score-aware, Gaussian-normalized). MMR (maximal marginal relevance) is a third rescore mode (`ScoringQuery::Mmr`) for diversity.

#### MMR — diversity rescore (KNOWN, `lib/shard/src/query/mmr/mod.rs:198-257`)

The third query-tree mode, for de-duplicating near-identical memories. Greedy: pick the single most-relevant candidate first; then iteratively pick the candidate maximizing

```
mmr_score = λ · relevance(c, query) − (1 − λ) · max_similarity(c, already_selected)   // mod.rs:246-247
```

`λ` (`mmr.lambda`) is the relevance/diversity dial: `λ=1` pure relevance, `λ=0` pure diversity. `relevance_similarities` (`:142`) computes query↔candidate cosine; the candidate↔candidate similarity uses a `LazyMatrix` (computed on demand, not materialized full N²). This runs *after* fusion, on the fused shortlist — exactly Vespa's "second phase over top-N" pattern, but as a built-in operator.

### Sparse vector search — inverted index with built-in WAND pruning (KNOWN, `lib/sparse/src/`)

Qdrant's sparse leg (for SPLADE/BM25-style sparse embeddings) is a custom inverted index, *not* a generic FTS engine. Posting element (`posting_list_common.rs:28`):

```rust
pub struct PostingElementEx {
    pub record_id: PointOffsetType,   // doc/point id
    pub weight: DimWeight,            // this term's weight in this doc (f32)
    pub max_next_weight: DimWeight,   // MAX weight of ALL elements after this one in the posting list
}
```

`max_next_weight` is the WAND upper bound, maintained incrementally: on insert/delete, `propagate_max_next_weight_to_the_left` (`posting_list.rs:95`) pushes the new max leftward until it hits a larger weight. `DEFAULT_MAX_NEXT_WEIGHT = f32::NEG_INFINITY` (`posting_list_common.rs:6`).

**Search loop** (`search_context.rs:271-355`), a DAAT (doc-at-a-time) WAND:
- Process ids in batches: `ADVANCE_BATCH_SIZE = 10_000` (`:25`) — advance all posting iterators across a 10k-id window, scoring matching ids.
- **Pruning gate** (`:332`): once `top_results.len() >= top` (heap full), take the heap's min score as the threshold; `promote_longest_posting_lists_to_the_front()` (`:240`), then `prune_longest_posting_list(min_score)`: if the longest posting's current element + its `max_next_weight` can't beat the threshold AND no smaller id is pending in other lists, skip ahead — never score those docs.
- **Pruning is disabled for negative query weights** (`:78-81`): `use_pruning = reliable_max_next_weight() && all query values >= 0.0` — negative weights break the monotonic upper bound.

This is the dual-index Verso needs for hybrid memory: dense HNSW + this sparse inverted index, both feeding the prefetch tree, fused by RRF/DBSF. The `max_next_weight` trick is Qdrant's term-level analogue of Weaviate's BlockMaxWAND and Vespa's WAND.

### HNSW index params — verbatim defaults (KNOWN, `lib/segment/src/types.rs`)

```rust
pub const DEFAULT_HNSW_EF_CONSTRUCT: usize = 100;   // line 1409
pub const DEFAULT_FULL_SCAN_THRESHOLD: usize = 10_000;  // line 1872 — vectors, not KB

impl Default for HnswConfig {  // line 1411
    m: 16,
    ef_construct: 100,            // <-- NOT 64
    full_scan_threshold: 10_000,  // below this many vectors → brute-force, no graph
    max_indexing_threads: 0,      // 0 = all cores
    on_disk: Some(false),
    payload_m: None,              // separate connectivity for payload-filtered subgraphs
}
```

Graph build (`lib/segment/src/index/hnsw_index/config.rs:34-53`): `m0 = m * 2` — **level-0 gets double the connections** (32 for default m=16); `ef = ef_construct` (search beam defaults to the build beam). `payload_m` (if set) builds *additional* per-payload-tenant subgraph links, which is the basis of filtered-ANN.

> **[CORRECTION 2026-06-05]** Brief said `ef_construction=64, ef_search=40`. Source: **`ef_construct=100`**, and there is no `ef_search=40` constant — search `ef` defaults to `ef_construct` (100) and is overridable per query via `params.hnsw_ef`. The `m=16` is correct.

`full_scan_threshold = 10_000` is the key segment-routing constant: a segment with fewer than 10k indexed vectors is searched by **exact brute-force**, not the HNSW graph — small segments skip graph construction entirely. This directly informs Verso's embedded mode: below ~10k memories, skip the index.

### Storage Engine — Gridstore (four-layer mmap slab allocator)

Gridstore replaced RocksDB for payload + sparse storage. Layout (KNOWN, `lib/gridstore/src/gridstore/mod.rs:40-52` + `config.rs`):

| Layer | File(s) | Role |
|---|---|---|
| **tracker** | tracker mmap | `point_offset → ValuePointer{page_id: u32, block_offset, length: u32}` (12-byte `#[repr(C)] bytemuck::Pod`, `tracker.rs:82-93`). The point→location index. |
| **pages** | page files | The actual value blobs. Each page = 32 MB (`DEFAULT_PAGE_SIZE_BYTES`); blocks of 128 bytes (`DEFAULT_BLOCK_SIZE_BYTES`); a region = 8192 blocks (`DEFAULT_REGION_SIZE_BLOCKS`). LZ4 compression on by default. |
| **bitmask (mask)** | bitmask mmap | one bit per 128-byte block: `0 = free, 1 = used` (`mod.rs:44-46`). The allocator's free-list. |
| **gaps** | derived from bitmask, per region | `RegionGaps{max: u16, leading: u16, trailing: u16}` (`bitmask/gaps.rs:14-18`) — per-region summary of the largest contiguous run of free blocks. Lets the allocator find a fit for an N-block value in O(regions) instead of O(blocks). |

Page math (`config.rs:92-100`): `page_size` must be a multiple of `block_size × region_size` (128 × 8192 = 1 MB region; 32 MB page = 32 regions). A value of L bytes occupies `ceil(L/128)` contiguous blocks; the gaps layer is scanned to find a region whose `max` gap ≥ that many blocks.

**WAL idempotency — exactly-once writes** (KNOWN, `tracker.rs:105-139`, `PointerUpdates`): each pending write holds `{ current: Option<ValuePointer>, to_free: SmallVec<[ValuePointer;1]> }`. On `set`, the *old* pointer goes into `to_free` (its blocks get released in the bitmask on flush) and `current` becomes the new pointer. The flush is two-phase: prepare a flusher snapshotting current changes → write to disk → **drain** the persisted updates. New writes arriving between prepare and execute stay queued. Comment verbatim (`tracker.rs:117-120`): *"With this mechanism we write each update to disk exactly once."* This is the slab-allocator analogue of a WAL: mutation is recorded as (new pointer, blocks-to-free) and applied atomically at flush, so replay/crash never double-applies.

### ACORN — filtered ANN without recall collapse (KNOWN, `lib/segment/src/index/hnsw_index/hnsw/search.rs:37-83`)

The mechanism behind "filter by memory_type/agent/session without recall collapse." When a filter is present, Qdrant *estimates the filter's selectivity* and routes accordingly (`search.rs:60-83`):

```rust
selectivity = estimate_cardinality(filter) / available_vector_count   // fraction of vectors that pass
if acorn_enabled && selectivity <= ACORN_MAX_SELECTIVITY_DEFAULT (0.4) {  // types.rs:556
    algorithm = SearchAlgorithm::Acorn;   // expand traversal to 2-hop neighbors of filter-passing nodes
}
```

The intuition: in a plain HNSW, if a filter passes only a small fraction of nodes, the greedy walk keeps landing on filtered-*out* nodes and the navigable graph fragments → recall collapses. ACORN (Apolloni et al.) traverses through filtered-out nodes' edges to reach filter-passing nodes (a "predicate-agnostic" expansion), keeping the subgraph navigable. The `0.4` gate means: only pay ACORN's overhead when the filter is *selective* (≤40% pass); above that, plain HNSW is fine. This is strictly better than `payload_m` (static per-tenant links) for *dynamic, arbitrary* filters — Verso's typed-memory filters are exactly this case.

### Quantization (KNOWN, `lib/segment/src/types.rs:768-859`)

Three quantization configs, each with a `rescore` flag (re-rank top candidates on full vectors): **Scalar** (`int8`, `quantile ∈ [0.5, 1.0]` clips outliers, `always_ram`), **Product** (PQ), **Binary** (1-bit, for high-dim). The pattern matches pgvectorscale SBQ: traverse on quantized vectors (cache-resident), `rescore` exact on the shortlist. Verso's durable backend should set `quantile≈0.99` scalar quant + rescore for the memory-at-scale case.

### Segment lifecycle — Appendable → Indexed

`full_scan_threshold` (10k vectors) is the Appendable→Indexed seam *within* a segment. The optimizer (`lib/collection/src/optimizers_builder.rs`) governs segment-level transitions: `default_segment_number: 0` (auto = #CPUs), `indexing_threshold_kb` (build HNSW when a segment exceeds this many KB of vectors), `memmap_threshold_kb` (move vectors to mmap above this). A growing/appendable segment serves writes with brute-force search; once it crosses the indexing threshold the optimizer builds an HNSW graph and the segment becomes Indexed (immutable for the index, still soft-deletable via tombstone). Merge optimizer test uses `memmap_threshold_kb: 100` (`merge_optimizer.rs:86`).

### For Verso

- **Two fusers, not one.** Ship both **RRF (rank-only)** and **DBSF (score-aware, ±3σ Gaussian-normalized)** as `MemoryStore.fuse(mode=...)`. RRF when the dense and sparse legs have incomparable score scales (cosine vs BM25); DBSF when scores are calibrated. The RRF default is `k=2`, not 60 — and **weight divides position**, not score: `1/((pos+1)/w + k − 1)`. Copy this exact formula; it gives a clean "3 of leg A per 1 of leg B" knob.
- **Recursive prefetch tree.** Verso's retrieval request should be a tree: leaf legs (dense / sparse / scalar-filter) → parent fusion/rescore node. This lets an agent express "ANN over `body` ∪ BM25 over `title`, then MMR-diversify, then take top-8" in one server round-trip.
- **`full_scan_threshold = 10_000`.** Below ~10k memories, skip the ANN index and brute-force. This is the natural Verso *embedded-mode* default — no graph build cost until the store is large.
- **Gridstore is the slab-allocator memory backend.** For a Verso embedded store that mutates payloads, the four-layer design (tracker→pages, bitmask free-list, per-region gap summaries, exactly-once flush via `{current, to_free}`) is a complete, RocksDB-free blueprint. 128-byte blocks, 8192-block regions, 32 MB pages, LZ4.
- **`payload_m` filtered subgraphs.** Typed-memory filters (by `memory_type`, `agent_id`, `session`) map to Qdrant's `payload_m` — extra HNSW links per payload tenant so filtered ANN doesn't collapse recall.

---

## Chroma

### What It Is

Originally Python + SQLite + HNSW; rewritten to a ~40-crate Rust workspace (`rust/`) with PyO3 Python bindings. The same Rust `Frontend` runs **embedded** (in-process, SQLite sysdb + SQLite log + local HNSW) and **distributed** (gRPC frontend → log-service → compactor → query worker, with object-storage WAL). For Verso this is the *closest analogue to the tactical↔durable seam* — one codebase, a config switch decides embedded-vs-server. The durable side runs on **WAL3**: an object-storage log of immutable parquet-ish fragments + a CAS-guarded manifest + set-hash checksums.

### Embedded↔Distributed Seam — the PyO3 boundary (KNOWN, `rust/python_bindings/src/bindings.rs`)

The Python `Bindings` struct (`bindings.rs:38-44`) embeds the **identical** `chroma_frontend::Frontend` the distributed server uses. The constructor (`bindings.rs:79-160`) wires the *embedded* variants of every pluggable subsystem:

```rust
#[pyo3(signature = (allow_reset, sqlite_db_config, hnsw_cache_size, persist_path=None))]
// embedded config (bindings.rs:104-145):
SysDbConfig::Sqlite(...)                 // metadata in SQLite, not gRPC sysdb
LogConfig::Sqlite(SqliteLogConfig{..})   // WAL in SQLite, not WAL3/log-service
ExecutorConfig::Local(LocalExecutorConfig{})  // in-process executor, not distributed query nodes
LocalSegmentManagerConfig{ hnsw_index_pool_cache_config: Foyer(capacity: hnsw_cache_size), persist_path }
KnnIndex::Hnsw
LocalCompactionManager                   // compaction runs in-process as a System component
// then: Frontend::try_from_config(&(frontend_config, system), &registry)
```

The distributed deployment swaps these four config enums (`ExecutorConfig::Distributed`, gRPC `SysDbConfig`, WAL3 `LogConfig`, remote compactor) and reuses the same `Frontend` request handlers. **This is the seam Verso wants:** define `MemoryStore` against an abstract executor + log + sysdb; embedded mode binds SQLite implementations, durable mode binds object-storage/gRPC implementations — no API change. Note `collections_with_segments_provider.permitted_parallelism = 32`, `cache_ttl_secs = 60`, retry-to-sysdb disabled locally (`CacheInvalidationRetryConfig::new(0,0)`).

### WAL3 — object-storage log structure (KNOWN, `rust/wal3/src/`)

WAL3 is the durable write path. Writes append to **immutable Fragments** in object storage; a single **Manifest** object is the consistency root, mutated by compare-and-swap.

**Fragment** (`lib.rs:846-859`) — immutable, append-only:
```rust
pub struct Fragment {
    pub path: String,            // log/<uuidv7>  (UUIDv7 = time-sortable, aids GC)
    pub seq_no: FragmentIdentifier,
    pub start: LogPosition, pub limit: LogPosition,  // [start, limit) offset range
    pub num_bytes: u64,
    pub setsum: Setsum,          // set-hash checksum of this fragment's records
}
```

**Manifest** (`manifest.rs:251-271`) — the single mutable root:
```rust
pub struct Manifest {
    pub setsum: Setsum,          // running set-hash of the WHOLE log
    pub collected: Setsum,       // set-hash of GC'd (deleted) records
    pub acc_bytes: u64,
    pub writer: String,          // identity of the current writer (single-writer lease)
    pub snapshots: Vec<SnapshotPointer>,  // hierarchical rollups (depth-keyed)
    pub fragments: Vec<Fragment>,
    pub initial_offset, pub initial_seq_no,
}
```

**Setsum = the key invariant.** `apply_fragment` (`manifest.rs:432-436`) does `self.setsum += fragment.setsum`. Setsum is a *commutative, homomorphic set hash* — the whole-log checksum equals the sum of all fragment checksums regardless of order. So a reader can recompute Σ(fragment.setsum) and compare to manifest.setsum to detect a missing or corrupt fragment (errors `MismatchedFragmentSetsum`, `MissingFragmentBySetsumPath`, `lib.rs:315-330`). GC subtracts: `collected` accumulates deleted-record setsums so `setsum − collected` stays consistent.

**CAS via ETag** (`manifest.rs:6` verbatim: *"manifests embed the ETag for conditional writes while snapshots do not"*; `storage/src/lib.rs:534` `PutOptions::IfMatch(ETag)`, `:550` `IfNotExistsAndIfMatchEnabled`). A writer reads manifest + its ETag, appends a fragment to S3, then conditionally PUTs the new manifest *only if the ETag still matches*. A losing writer retries. This is how WAL3 gets single-writer-correct durability on plain object storage with no lock service. `can_apply_fragment` (`manifest.rs:425-429`) enforces sequentiality (`fragment.seq_no == next_seq_no` and `start.offset < limit.offset`).

**Snapshot rollover** keeps the manifest bounded: `snapshot_rollover_threshold = (1<<18)/SnapshotPointer::JSON_SIZE_ESTIMATE`, `fragment_rollover_threshold = (1<<19)/Fragment::JSON_SIZE_ESTIMATE` (256 bytes) (`lib.rs:524-531`). When fragment pointers exceed the threshold they roll up into a depth-keyed Snapshot (`generate_snapshot`, `manifest.rs:292`), so the manifest never grows unbounded — it's a B-tree-ish hierarchy of snapshot pointers.

**Throttle/batch defaults** (`lib.rs:468-498`): `batch_size_bytes = 64 MB` (2× gRPC max payload), `batch_interval_us = 100_000` (100 ms — writes coalesce for up to 100 ms before an S3 PUT), `throughput = 2000 ops/s` (~5/7 of S3's per-prefix limit), `headroom = 1500` reserved for retries. **GC grace** `uuid_grace_period_secs = 3600` (`lib.rs:615`): a fragment uploaded but not-yet-linked into the manifest looks like an orphan; UUIDv7's embedded timestamp lets GC clamp deletes to `now − 1h` so in-flight fragments survive.

**Cursors — consumer offsets** (`cursors.rs:82-100`): a `Cursor { position: LogPosition, epoch_us }` is a named, durable consumer pointer (e.g. the `"compaction"` cursor, `:11`). The compactor advances its cursor as it materializes log fragments into segments; GC can then safely delete fragments below the *minimum* cursor across all consumers. This is the mechanism that bounds the `IndexAndWal` replay range (read fragments from the compaction cursor forward) and makes GC safe (never delete un-compacted data). `CursorWitness` carries the ETag for CAS updates of the cursor — same conditional-write discipline as the manifest. **Verso parallel:** a durable memory log needs exactly this — a "compaction" cursor (how far indexed) so reads know where the un-indexed tail begins and GC knows what's safe to drop.

**Quorum writes** (`quorum_writer.rs:34` `write_quorum`): for replicated deployments, fragment writes complete when a quorum of replicas ack; the threshold is a parameter (`write_quorum(futures, min_acks, timeout)`), and *errors don't count toward the quorum* (tested at `:220`) — a down node that affirmatively fails is distinguished from a slow one.

### Read consistency — three ReadLevels (KNOWN, `rust/types/src/execution/plan.rs:550-565`)

```rust
pub enum ReadLevel {
    IndexAndWal,         // DEFAULT — full consistency: query index + replay uncompacted WAL
    IndexOnly,           // eventual: skip WAL fetch entirely (knn_filter.rs:355 → "use empty logs")
    IndexAndBoundedWal,  // bounded: index + up to N WAL entries → bounded latency, prefix consistency
}
```

A query orchestrator (`knn_filter.rs:355-365`) branches on this: `IndexOnly` skips the log-fetch stage and searches only compacted HNSW/SPANN segments (fast, may miss recent writes); `IndexAndWal` fetches the uncompacted log fragments and merges them with index results. This is exactly the **"durable by flag"** knob — a Verso agent can ask for a cheap eventually-consistent recall or a fully-consistent one per query.

### Segment types & compaction

Writes land in the log (growing). A background compactor materializes segments: **HNSW** (in-memory graph, `header.bin`/`data_level0.bin`/`link_lists.bin`), **SPANN** (clustered, billion-scale disk), **Blockfile** (Arrow `RecordBatch` columnar in the `blockstore` crate), **Sparse Index**. Metadata filtering goes through SysDB (SQLite embedded / PostgreSQL distributed). Compaction is the read↔write decoupler: writers never touch the index; readers at `IndexOnly` never touch the log.

### SPANN — the disk-scale segment (KNOWN, `rust/types/src/spann_configuration.rs:7-75`)

SPANN (the disk-resident, billion-scale alternative to in-memory HNSW) is the segment that makes Chroma's durable mode scale. It is an inverted-list/clustering index (centroids + posting lists) with an HNSW over the centroids. Verbatim defaults:

```rust
search_nprobe          = 64    // clusters probed at query
write_nprobe           = 32    // clusters a write is assigned to
nreplica_count         = 8     // each vector replicated into 8 nearest posting lists (redundancy → recall)
split_threshold        = 50    // posting list splits when it exceeds 50 entries
merge_threshold        = 25    // posting list merges below 25
num_centers_to_merge_to= 8
num_samples_kmeans     = 1000  // k-means sample size for centroid (re)computation
initial_lambda         = 100.0 // RNG-rule (relative neighborhood graph) pruning weight
reassign_neighbor_count= 64    // on split, reassign this many neighbors to keep posting lists balanced
center_drift_threshold = 0.125 // recompute a centroid when it drifts >12.5%
construction_ef_spann  = 200, search_ef_spann = 200, m_spann = 64   // HNSW over the centroids
search_rng_epsilon     = 10.0, write_rng_epsilon = 5.0             // RNG-rule slack (query vs write)
```

The interesting mechanics: `nreplica_count=8` (a vector lives in its 8 nearest clusters — trades storage for recall), `split_threshold=50`/`merge_threshold=25` (posting lists self-balance via split/merge like a B-tree), and `center_drift_threshold=0.125` (centroids are recomputed only after 12.5% drift — amortizes k-means). On split, `reassign_neighbor_count=64` neighbors are reassigned to keep the partition Voronoi-correct. This is the "compacted segment" the durable path materializes; vs HNSW it trades query latency for disk-residency at billion scale.

### For Verso

- **One Frontend, two backends.** Mirror Chroma's PyO3 seam: define `MemoryStore` against abstract `{executor, log, sysdb, segment_manager}`; embedded mode binds SQLite + local HNSW + in-process compactor, durable mode binds object-storage WAL + gRPC sysdb. The request handlers never change. This is the cleanest known template for Verso's tactical↔durable seam.
- **Set-hash checksums for log integrity.** Use a commutative set hash (setsum) so `whole_log_checksum == Σ fragment_checksums`. Detects missing/corrupt memory-log fragments without ordering assumptions, and GC stays consistent via `setsum − collected`.
- **CAS-on-object-storage durability.** A manifest object guarded by `If-Match(ETag)` gives single-writer-correct durability with *no lock service* — just S3 conditional PUT. Verso's durable memory log can be exactly this: append immutable fragments, CAS the manifest, retry on ETag mismatch.
- **Three read levels as a per-query knob.** `IndexOnly` (cheap, eventual) / `IndexAndWal` (full) / `IndexAndBoundedWal` (bounded latency). An agent doing a fast "do I roughly remember X" lookup uses `IndexOnly`; a correctness-critical recall uses `IndexAndWal`.
- **Batch to 100 ms / 64 MB before flushing.** WAL3 coalesces writes for up to 100 ms or 64 MB before an S3 PUT, capped at ~5/7 of the per-prefix throughput with 1500 ops/s reserved for retries. Copy these as the durable-write batching defaults.
- **UUIDv7 + 1h GC grace** for the orphan-fragment problem (uploaded-but-unlinked). Time-sortable IDs let GC avoid deleting in-flight writes.

---

## pgvector + pgvectorscale

### What It Is

Two PostgreSQL extensions. **pgvector** (C) adds `vector`/`halfvec`/`sparsevec` types and HNSW + IVFFlat index access methods that hook into Postgres's WAL/MVCC — so vectors live inside ACID transactions. **pgvectorscale** (Rust via PGRX) adds **StreamingDiskANN** (a disk-resident DiskANN variant), **SBQ** (Statistical Binary Quantization), and **Filtered DiskANN** (label-aware ANN). For Verso, this is the *zero-new-infrastructure* durable path: if an agent already uses Postgres for checkpoints/HITL/tool-outputs, memories live in the same DB, and hybrid search is just SQL.

### pgvector — HNSW params + Postgres integration (KNOWN, `src/hnsw.h`)

```c
#define HNSW_DEFAULT_M               16    // line 46  (min 2, max 100)
#define HNSW_DEFAULT_EF_CONSTRUCTION 64    // line 49  (min 4, max 1000)
#define HNSW_DEFAULT_EF_SEARCH       40    // line 52  (min 1, max 1000) — GUC hnsw.ef_search
#define HNSW_MAX_DIM                 2000  // line 25
#define HNSW_MAX_NNZ                 1000  // sparse non-zeros cap
#define HNSW_METAPAGE_BLKNO          0     // metapage at block 0; first element page at block 1
```

> **[CORRECTION 2026-06-05]** These three (`m=16, ef_construction=64, ef_search=40`) match the brief exactly and are the *pgvector* defaults. Note they differ from **Qdrant's** (`ef_construct=100`) — do not conflate. pgvector's are the canonical hnswlib values; Qdrant raised ef_construct to 100.

**Postgres WAL/MVCC integration** — the load-bearing reveal (KNOWN, `src/hnsw.c:266-309`, `src/hnswinsert.c`): pgvector registers a standard index access method (`hnswhandler` → `IndexAmRoutine` with `ambuild=hnswbuild`, `aminsert=hnswinsert`, `ambulkdelete=hnswbulkdelete`, `amvacuumcleanup=hnswvacuumcleanup`). Every graph mutation is wrapped in **generic WAL**: `GenericXLogStart(index)` → `GenericXLogRegisterBuffer(state, buf, GENERIC_XLOG_FULL_IMAGE)` → mutate the page image → `GenericXLogFinish(state)` (`hnswinsert.c:194,258,339`). This means HNSW pages are crash-safe, replicated to standby servers, and visible under MVCC like any heap page — the index *is* a set of regular Postgres relation pages. Deletes are handled lazily by `VACUUM` (`hnswbulkdelete`), not inline. This is why pgvector "just works" with PITR, streaming replication, and `pg_dump`.

**Two-phase HNSW build** (KNOWN, `src/hnswbuild.c:1-34` verbatim comment): **Phase 1 (in-memory)** — build the whole graph in `maintenance_work_mem`-bounded RAM. In a *parallel* build, the graph lives in one shared-memory chunk; each worker maps it at a different address, so all graph edges are stored as **relative pointers** (offset from `hnswarea`) and each element is guarded by an LWLock. When RAM is exhausted (or build completes), `FlushPages()` materializes to disk. **Phase 2 (on-disk)** — insert remaining vectors one-by-one like a live `INSERT`, *without* per-insert WAL logging, then one final scan WAL-logs all pages. If the graph fit in RAM, phase 2 is skipped entirely. Layer-0 capacity heuristic (`hnsw.c:201-202`): `layer0TuplesMax = HnswGetLayerM(m, 0) * hnsw_ef_search`. This is the same in-memory-then-spill pattern as Milvus growing→sealed, but inside one Postgres backend.

**IVFFlat** (KNOWN, `src/ivfflat.h`, `src/ivfflat.c:45`, `src/ivfkmeans.c`): `IVFFLAT_DEFAULT_LISTS = 100` (max 32768), `ivfflat.probes` GUC defaults to `IVFFLAT_DEFAULT_PROBES`, plus `ivfflat.max_probes` for iterative scans. Build = reservoir-sample rows (`ivfbuild.c:59-90`, `reservoir_get_next_S`), run **k-means++ init** (`InitCenters`, `ivfkmeans.c:19-37`) then Elkan/Lloyd to produce list centroids; query scans `probes` nearest lists. Lower build cost than HNSW, lower recall — the classic IVF tradeoff. Vector types span `vector` (float32), `halfvec` (float16, halves storage), `bit` (binary, Hamming), `sparsevec` — each with its own operator class, so the same index AM serves quantized variants.

### pgvectorscale — StreamingDiskANN params (KNOWN, `pgvectorscale/src/access_method/`)

```rust
// options.rs:23-41 (CREATE INDEX ... WITH (...))
search_list_size      = 100                        // L during build (line 39)
max_alpha             = 1.2   (DEFAULT_MAX_ALPHA)  // RobustPrune relaxation cap (line 26)
num_neighbors         = -1 sentinel → 50           // R, derived (meta_page.rs:288-289)
bq_num_bits_per_dimension = sentinel → 2 if dims<900 else 1  // (meta_page.rs:312-323)
GRAPH_SLACK_FACTOR    = 1.3                         // alloc 1.3×R neighbor slots (meta_page.rs:24,254)

// guc.rs — query-time, Userset
diskann.query_search_list_size = 100  (1..10000)   // L at query
diskann.query_rescore          = 50   (0..1000)    // exact-rescore top-N approx results (0 disables)
```

> **[CONFIRMS BRIEF]** `num_neighbors=50, search_list_size=100, max_alpha=1.2, query_rescore=50` all verified at the cited lines. SBQ `num_bits_per_dimension: 2 for dim<900, else 1` confirmed (`meta_page.rs:314-320`); >930 dims with >1 bit is a hard error ("SbqMeans must fit on a page").

**RobustPrune with α-relaxation** — the DiskANN graph-quality core (KNOWN, `graph/mod.rs:392-486`):

```
sort candidates by distance; alpha = 1.0
while alpha <= max_alpha (1.2) and results < num_neighbors:
    for each candidate i not yet occluded (max_factors[i] <= alpha):
        accept i into results
        for each farther candidate j (skip i+1..):
            factor = dist(j, point) / dist(j, neighbor_i)   # >1 means j is closer to i than to the point
            max_factors[j] = max(max_factors[j], factor)    # occlude j if it's "covered" by i
    alpha *= 1.2
```

So a node's edge list keeps the *nearest* neighbor in each direction and prunes neighbors that are "shadowed" by a closer accepted neighbor — unless relaxing α (up to 1.2) is needed to fill `num_neighbors=50` slots. This is what gives DiskANN its long-range navigability at low degree.

**"Relaxed ordering" / streaming** (KNOWN, `scan.rs:127-255`): the scan is a *streaming* greedy search (`greedy_search_streaming_init`) that yields results incrementally with a `resort_buffer: BinaryHeap` of size `resort_size = query_rescore = 50`. Unlike strict DiskANN (which fully sorts), it returns results as soon as the buffer's top is provably better than anything still unexplored — bounded memory, pipelined with the executor. The `query_rescore` step re-computes *exact* distances on the top-50 SBQ-approximate candidates and re-sorts, recovering precision lost to quantization.

### SBQ — Statistical Binary Quantization (KNOWN, `sbq/quantize.rs`)

Packs each f32 dimension into 1 or 2 bits, stored in `u64` words (`SbqVectorElement = u64`, `BITS_STORE_TYPE_SIZE = 64`). Training accumulates per-dimension `mean` and `m2` (Welford). Quantize:

- **1-bit** (`quantize.rs:57-61`): `bit_i = 1 if v_i > mean_i else 0`. Mean-thresholded, not zero-thresholded — that's the "Statistical" in SBQ.
- **2-bit** (`quantize.rs:62-90`): z-score thermometer code. `z = (v − mean)/σ`; clamp z to [−2, 2], split into `(num_bits+1)` ranges; emit `count_ones` leading 1-bits (thermometer: `100`/`110`/`111`). Multi-bit preserves magnitude ordering, not just sign.

Distance on SBQ vectors is `popcount(XOR)` (Hamming) for 1-bit — extremely cheap, SIMD-friendly — which is why pgvectorscale claims **28× lower p95 vs Pinecone at 50M vectors, 99% recall, 75% cheaper**: the graph traversal runs on 1-bit codes (small, cache-resident), then `query_rescore=50` exact re-ranks. INFERRED: "memory_optimized" (SbqCompression) = codes inline in graph nodes for cache-residency; "plain" = full vectors. The brief's "40% storage reduction" is the SBQ-vs-float footprint.

### Filtered DiskANN — label-aware ANN (KNOWN, `labels/mod.rs` + `graph/mod.rs:451-460`)

Labels are `Label = i16` (Postgres `smallint`), passed as a `smallint[]` column / query key (`Array::<i16>::from_datum`, `labels/mod.rs:192,230`). During RobustPrune, the occlusion check is gated by label intersection (`graph/mod.rs:452-460`): candidate `j` is only occluded by accepted neighbor `i` if they `contains_intersection(...)` over the query's essential labels. **Effect:** the graph retains enough edges *per label* so a filtered query (`WHERE labels && '{3,7}'`) still has a navigable subgraph and recall doesn't collapse to post-filter scanning. This is the direct mechanism for Verso typed-memory filters.

### Hybrid search — SQL-composed RRF (KNOWN pattern, pgvector docs)

No new query language. Dense + BM25 fused in a CTE with RRF:

```sql
WITH semantic AS (
  SELECT id, RANK() OVER (ORDER BY embedding <=> $query_vec) AS rank
  FROM memories ORDER BY embedding <=> $query_vec LIMIT 40),    -- <-> L2, <=> cosine, <#> neg-dot
keyword AS (
  SELECT id, RANK() OVER (ORDER BY ts_rank_cd(tsv, plainto_tsquery($q)) DESC) AS rank
  FROM memories WHERE tsv @@ plainto_tsquery($q) LIMIT 40)
SELECT COALESCE(s.id, k.id) AS id,
       COALESCE(1.0/(60 + s.rank), 0) + COALESCE(1.0/(60 + k.rank), 0) AS score  -- RRF k=60 (SQL-side choice)
FROM semantic s FULL OUTER JOIN keyword k USING (id)
ORDER BY score DESC LIMIT 10;
```

Operators: `<->` (L2), `<=>` (cosine), `<#>` (negative inner product), `<+>` (L1). The RRF `k` here is a free SQL constant (commonly 60) — unlike Qdrant where it's a compiled default of 2.

### For Verso

- **Postgres-native durable memory = zero new infra.** If a Verso deployment already runs Postgres, the durable `MemoryStore` is pgvector: memories share the DB with checkpoints/HITL/tool-outputs, get ACID + PITR + replication *for free* because the index is built on generic-WAL'd relation pages. No separate vector service to operate.
- **SBQ + rescore is the scale recipe.** Traverse the graph on 1-bit codes (Hamming popcount, cache-resident), then exact-rescore the top `query_rescore=50`. This is the lever behind the 28× p95 / 99% recall claim. Verso's durable store should adopt the same "approximate-traverse, exact-rerank-top-N" split.
- **`smallint[]` labels + intersection-gated prune = typed-memory filtering done right.** Map `memory_type`/`agent_id`/`session` to `i16` labels; build a label-aware graph so filtered recall doesn't collapse. This is strictly better than Verso post-filtering an unfiltered ANN result.
- **Index defaults are model-dependent.** pgvector HNSW = `m=16, ef_construction=64, ef_search=40`; StreamingDiskANN = `R=50, L=100, α≤1.2`. SBQ bits auto-pick `2 if dim<900 else 1`. Ship these as Verso's Postgres-backend defaults verbatim.
- **Hybrid = SQL CTE + RRF, no new engine.** Verso's hybrid memory query on the Postgres backend is a `FULL OUTER JOIN` of a `<=>` leg and a `ts_rank_cd` leg with `1/(k+rank)` RRF — composable, debuggable, no separate sparse index to operate.

---

## Weaviate

### What It Is

Vector DB in Go. HNSW for dense, an LSM-backed inverted index (BlockMaxWAND-optimized BM25F) for keyword, both living in the same shard. Two server-side hybrid fusion algorithms. For Verso the takeaways are: (1) the exact two-fusion algebra, (2) **BlockMaxWAND** — the production algorithm for fast top-k BM25 without scanning every posting, and (3) the BM25F defaults.

### Hybrid fusion — two algorithms (KNOWN, `usecases/traverser/hybrid/hybrid_fusion.go`)

`performFusion` (`searcher.go:299-310`) dispatches on `fusionAlgorithm`:

**`FusionRanked` = RRF, k=60** (`hybrid_fusion.go:22-81`):
```go
score := float32(weights[resultSetIndex] / float64(i+60))  // line 31; i = 0-based rank
// "TODO replace 60 with a class configured variable"  → 60 is hard-coded
// accumulate per-UUID across result sets; sort desc; tie-break on SecondarySortValue then ID
```
Note the constant is `i + 60` (not `i + 1 + 60`), so rank-0 contributes `weight/60`. This is the textbook Cormack k=60 — **contrast Qdrant's compiled default of 2.**

**`FusionRelativeScore`** (`hybrid_fusion.go:93-182`) — "retains more information than ranked fusion": per result-set, min-max normalize the raw scores to [0,1] (`(score − min)/(max − min)`; if all equal → just the weight), multiply by the set's weight, sum per UUID, sort. This is Weaviate's analogue to Qdrant's DBSF (score-aware) vs RRF (rank-only). The `weights` come from `alpha` — the hybrid `alpha` (dense vs sparse mix, default 0.75 favoring vector) becomes `[alpha, 1−alpha]`.

> **[CORRECTION 2026-06-05]** The brief described "Hybrid 2.0 BM25-collocated-with-HNSW + learned fusion model". In the current OSS source, the two fusion modes are the *hand-coded* `rankedFusion` (RRF k=60) and `relativeScoreFusion` (min-max), selected by `fusionType` — there is **no learned/trained fusion model in the open-source tree**; the "learned fusion" is a Weaviate Cloud / roadmap feature, not in the repo. What *is* real is BlockMaxWAND (below) and the LSM-collocated inverted index. Treat "learned fusion" as INFERRED/marketing, not KNOWN.

### BM25F + BlockMaxWAND (KNOWN, `adapters/repos/db/inverted/bm25_searcher_block.go`, `adapters/repos/db/lsmkv/segment_blockmax.go`)

BM25 defaults (`usecases/config/config_handler.go:57-58`): **`k1 = 1.2`, `b = 0.75`** — the standard Robertson values, configurable per-collection.

**BlockMaxWAND** is the top-k accelerator. The posting list is stored in blocks; each block carries a precomputed **block-max impact** (`currentBlockImpact float32`) and **max doc id** (`currentBlockMaxId uint64`) (`segment_blockmax.go:154-155`). Block entries are 20 bytes each (`DecodeBlockEntry(buf[i*20:(i+1)*20])`, `:85`). The WAND loop (`DoBlockMaxWand`, dispatched at `bm25_searcher_block.go:230`):

1. Sort active terms by current doc id; compute a **pivot** = the term where cumulative block-max impacts first exceed the current top-k heap threshold.
2. If the sum of block-max upper bounds below the pivot can't beat the heap's min score, **skip the whole block** (advance past `currentBlockMaxId`) — never decode those postings.
3. Only decode + score docs that *can* enter the top-k.

Comment verbatim (`bm25_searcher_block.go:82`): *"the goal of BlockMaxWAND is to avoid reading the full postings list into memory."* `DoBlockMaxAnd` is the AND variant (all terms must match). Per-segment internal limit configurable via `BLOCKMAX_WAND_PER_SEGMENT_LIMIT`. `blockMaxBufferSize = 4096` (`segment_blockmax.go:27`). The inverted index lives in the same `lsmkv` LSM store as object/property data — that's the "collocated" claim: one shard's LSM serves both payload rows and BM25 postings, so a hybrid query hits one storage engine, not two.

### LSM store — multiple value strategies in one engine (KNOWN, `adapters/repos/db/lsmkv/strategies.go:22-28`)

The `lsmkv` store is a strategy-per-bucket LSM: `StrategyReplace` (idempotent PUT, latest wins — for object rows), `StrategySetCollection` / `StrategyMapCollection` (multi-value), `StrategyRoaringSet` / `StrategyRoaringSetRange` (roaring-bitmap sets — for filterable/range properties), `StrategyInverted` (BM25 postings with the block-max layout). So one engine serves objects, filter bitmaps, and inverted postings by switching the value-merge strategy per bucket — the unifying substrate behind the "collocated" hybrid index. The `DeltaMerger` (`inverted/delta_merger.go:24-64`) batches additions/deletions per property before flush so a single object update touches each posting list once.

### Hybrid search flow — alpha decomposition (KNOWN, `usecases/traverser/hybrid/searcher.go:75-124`)

`Search(...)` takes a `sparseSearchFunc` and a `denseSearchFunc` closure and runs them conditionally on `alpha`:
- `if alpha < 1`: run sparse (BM25/BlockMaxWAND), append weight `1 − alpha`.
- `if alpha > 0`: run dense (HNSW), filter by `params.HybridSearch.Distance`, append weight `alpha`.
- Fuse the two weighted result sets via `performFusion` (rankedFusion / relativeScoreFusion), optional `performAutocut` (drop after a score-gap "elbow").

So `alpha` (default 0.75) is the single knob, decomposed into `[alpha, 1−alpha]` weights — skipping a leg entirely at the extremes (alpha=1 → pure vector, alpha=0 → pure keyword).

### For Verso

- **Two fusers, again — and they map 1:1 onto Qdrant's.** Weaviate `rankedFusion`(RRF k=60) ≈ Qdrant RRF; Weaviate `relativeScoreFusion`(min-max) ≈ Qdrant DBSF. The cross-system agreement (rank-only vs score-normalized) is the signal: Verso should ship exactly these two modes. Note the *k constant disagreement* (Weaviate 60, Qdrant 2) — k is a tunable, not a law; expose it.
- **`alpha → [alpha, 1−alpha]` weights** is the clean single-knob hybrid API. Default 0.75 (favor vector). Verso's `MemoryStore.search(query, alpha=0.75)` should follow this.
- **BlockMaxWAND is the BM25 algorithm to copy** if Verso runs its own sparse leg. Store postings in blocks with a precomputed per-block max-impact; skip blocks whose upper bound can't enter the top-k. This is how you get fast BM25 over millions of memories without full-scan. (Cross-ref: Turbopuffer's inverted-list BM25 in `infra-vector-memory.md` is the object-storage analogue.)
- **Collocate sparse + payload in one store.** Weaviate puts BM25 postings and object rows in the same LSM (`lsmkv`). Verso's embedded backend can do the same with SQLite — one store, no cross-index merge at the storage layer.
- **`k1=1.2, b=0.75`** — ship as Verso's BM25 defaults verbatim.

---

## Milvus + Knowhere

### What It Is

Cloud-native distributed vector DB in Go (control + stream) + C++ (Knowhere index engine). Storage/compute disaggregated: object storage (MinIO/S3) for sealed data, etcd for metadata, a message queue (Pulsar/Kafka/woodpecker) as the WAL. Milvus 2.5+ adds native BM25 full-text search by treating **BM25 as a sparse-vector metric**. For Verso the three lessons are: the **Knowhere index-type registry** (what "index routing" looks like), **BM25-as-sparse-vector** (no separate FTS engine), and the **growing→sealed** segment lifecycle (distributed analogue of Chroma's compaction).

### Knowhere — the index-type registry (KNOWN, `knowhere/`)

Knowhere is a thin C++ factory over Faiss/HNSWlib/DiskANN/RAFT-CAGRA. Every index registers a string key + a constructor (`src/index/hnsw/hnsw.cc:446`):

```cpp
KNOWHERE_REGISTER_GLOBAL(HNSW, [](const Object& o){ return Index<HnswIndexNode>::Create(o); });
```

Index-type strings (`include/knowhere/comp/index_param.h:26-43`): `FLAT`, `IVF_FLAT`, `IVF_FLAT_CC`, `IVF_PQ`, `IVF_SQ8`, `HNSW`, `DISKANN`, `GPU_FAISS_*`, `GPU_RAFT_IVF_*`, `GPU_RAFT_CAGRA`. Build/query params are *index-specific strings* in one untyped param map: HNSW = `M` / `efConstruction` / `ef` (`:76-78`); IVF = `nlist` / `nprobe` / `nbits` / `m` (`:71-75`). Metrics (`metric` namespace, `:84-92`): `IP`, `L2`, `COSINE`, `HAMMING`, `JACCARD`, `SUBSTRUCTURE`, `SUPERSTRUCTURE` — and in the Milvus-pinned Knowhere, **`BM25`** is added as a metric (referenced from Milvus C++ `knowhere::metric::BM25`, `internal/core/src/common/Types.h:700`, `Utils.h:176`). **The pattern:** index *type* (graph topology) and *metric* (distance) are orthogonal string keys; one `IndexFactory.Create(type, metric, params)` call resolves both. This is the "index menu router" Verso would want if it ever supports multiple ANN backends behind one `MemoryStore`.

### BM25-as-sparse-vector (KNOWN, `internal/util/function/bm25_function.go`)

The clean design: BM25 is *not* a separate engine — it's a sparse-vector field produced by a Function and searched with the `BM25` metric. The ingest path (`bm25_function.go:177-206`):

```go
func (v *BM25FunctionRunner) run(data []string, dst []map[uint32]float32) error {
    for each doc text:
        tokens := tokenizer.Tokenize(text)         // analyzer (tantivy-style) — stopwords, stemming
        embeddingMap := map[uint32]float32{}
        for each token:
            hash := typeutil.HashString2LessUint32(token)   // term → uint32 dimension id
            embeddingMap[hash] += 1                          // value = raw term frequency
    // → buildSparseFloatArray(embedData)                    // SparseFloatArray field
}
```

So raw text → tokenize → hash each term to a `uint32` "dimension" → accumulate term frequency → a sparse vector `{term_hash: tf}`. This sparse vector is stored in a `SPARSE_INVERTED_INDEX`. At **query** time the C++ segcore computes BM25 score as the "distance" under `metric::BM25` (k1, b, avgdl, idf applied during the sparse inner-product traversal — corpus stats maintained per segment). **Net:** dense ANN and BM25 are *the same operation* (sparse/dense vector search), just different metrics, so a hybrid query is two vector searches fused by RRF — no parallel Lucene/Elastic to run. This is the single most transferable Milvus idea for Verso.

> **[CONFIRMS BRIEF]** "tantivy tokenizer → SPARSE_INVERTED_INDEX, BM25 = inner product on sparse vectors" verified. The tokenizer is the `analyzer` package (tantivy-backed); term→dimension is `HashString2LessUint32`.

### Segment lifecycle — growing → sealed → flushed → indexed (KNOWN, `internal/datacoord/`)

Write path: streaming/proxy writes land in a **growing** segment (in-memory on the streaming node, backed by the message-queue WAL). The DataCoord seal policies (`segment_manager.go:220-227`):
- `sealL1SegmentByCapacity(SegmentSealProportion)` — seal when the segment reaches `sealProportion × maxSize`.
- `sealL1SegmentByIdleTime(SegmentMaxIdleTime, ...)` — seal idle segments past a min size.
- `sealByTotalGrowingSegmentsSize()` — backpressure cap on total growing data.

Constants (`pkg/util/paramtable/component_param.go:5204-5232`): `dataCoord.segment.maxSize = 1024 MB` (memory index) / `diskSegmentMaxSize = 2048 MB` (disk index); `sealProportion = 0.12` (seal at ~123 MB of a 1 GB target) with `sealProportionJitter = 0.1` to avoid thundering-herd seals. After sealing, a DataNode **flushes** the segment to object storage and an index build (Knowhere) materializes the ANN index → the segment becomes searchable by QueryNodes. This is the distributed twin of Chroma's WAL3 compaction: growing = uncompacted log, sealed+indexed = compacted segment, queries merge both (cf. Chroma `IndexAndWal`).

### MixCoord — unified coordinator (KNOWN, `internal/coordinator/mix_coord.go:52-103`)

Milvus 2.5+ collapses what were four separate coordinator processes into one `mixCoordImpl` (`:52`) that composes them in-process:

```go
type mixCoordImpl struct {
    rootcoordServer  *rootcoord.Core            // DDL, TSO (timestamp oracle), metadata catalog
    queryCoordServer *querycoordv2.Server       // distributes sealed-segment load across QueryNodes
    datacoordServer  *datacoord.Server          // segment allocation, seal/flush/compaction
    streamingCoord   *streamingcoord.Server     // WAL/streaming-node management (2.5 streaming arch)
}
// rootcoord.NewCore + querycoordv2.NewQueryCoord + datacoord.CreateServer, all registered at etcd
```

Each sub-coordinator still owns its domain (RootCoord = catalog + TSO, DataCoord = segment lifecycle, QueryCoord = query-node load balancing, StreamingCoord = WAL), but they share one process/etcd registration — simpler ops than four. The takeaway for Verso: a distributed memory backend's control plane can be *one* process that internally separates concerns (metadata / write-segment-lifecycle / read-load-balancing / WAL), rather than four microservices. Verso would never need this scale, but the decomposition (catalog ⊥ write-compaction ⊥ read-routing ⊥ log) is the correct mental model for sharding `MemoryStore`.

### For Verso

- **Index type ⊥ metric, both string-keyed.** If Verso ever fronts multiple ANN backends, copy Knowhere's factory: `create(index_type, metric_type, params_map)` where type and metric are orthogonal keys. Lets a `MemoryStore` swap HNSW↔DiskANN↔Flat and L2↔cosine↔BM25 without code changes.
- **BM25 = sparse-vector search with a BM25 metric — adopt this, don't run a separate FTS engine.** Tokenize → hash term to dimension → `{term: tf}` sparse vector → search with BM25 scoring. Verso's hybrid memory leg becomes "another vector search", and dense+sparse fuse with the same RRF code. Eliminates an entire Lucene/Tantivy *service* from the deployment.
- **Growing→sealed at 12% of 1 GB.** The seal-at-`0.12×maxSize` policy (with 10% jitter) is the concrete threshold for "when does an append-only memory log roll into a compacted, indexed segment." For Verso's durable mode, seal small (≈123 MB) and frequently to keep growing-segment scan costs bounded — and jitter the threshold to avoid synchronized compaction storms.

---

## Vespa

### What It Is

Java + C++ search platform (Yahoo origin). Stateful **content nodes** (C++, `searchlib` — data + index + ranking co-located) and stateless **container nodes** (Java — query parsing, cross-node merge). Its singular contribution is making **multi-phase ranking a first-class declarative primitive**, plus the original WAND operator. Verso doesn't need Vespa's infra, but its *phased ranking model* and *WAND algorithm* are reference designs for memory retrieval.

### Multi-phase ranking — three declared phases (KNOWN, `searchlib/src/vespa/searchlib/fef/ranksetup.h`, `container-search/.../GlobalPhaseRanker.java`)

A rank profile declares up to three phases, each a separate compiled rank program:

1. **first-phase** (content node, every candidate): `_first_phase_resolver` → `create_first_phase_program()` (`ranksetup.h:445`). A cheap expression (e.g. `nativeRank` or a linear combo of `closeness(vector)` + `bm25(text)`) scored over *all* matched docs. `_first_phase_rank_score_drop_limit` (`:64,313`) discards hits below a threshold *during* matching — early pruning.
2. **second-phase** (content node, top-N per node): `_second_phase_resolver` → `create_second_phase_program()` (`:448`). An expensive expression (GBDT/ONNX model, tensor ops) rescoring only the per-node top-`rerank-count`. `_second_phase_rank_score_drop_limit` (`:65,326`).
3. **global-phase** (container node, cross-node): `GlobalPhaseRanker.rerankHitsImpl` (`GlobalPhaseRanker.java:57`) re-ranks the merged top-K *after* gathering from all content nodes — the only place a model can see the global top-K (e.g. a cross-encoder over the merged shortlist). `resolveRerankCount` (`:138`) and `resolveRankScoreDropLimit` (`:150`) are per-query overridable.

So ranking is a *pipeline of progressively more expensive scorers over progressively smaller candidate sets*, declared in the schema, not hard-coded. `_numSearchPartitions` (`:55,195`) parallelizes first-phase matching.

### WAND — Weak-AND top-k (KNOWN, `searchlib/src/vespa/searchlib/queryeval/wand/`)

The production "fast BM25/dot-product top-k without full scan." Each query term has a **max-score upper bound** precomputed from its posting list (`DotProductScorer::calculateMaxScore`, `wand_parts.h:453-464`):

```cpp
// per-term upper bound = term.weight * max_weight_in_posting_list
maxWeight = dynamic_cast<MinMaxPostingInfo*>(postingInfo)->getMaxWeight();
return (score_t) term.weight * maxWeight;          // wand_parts.h:455-463
```

The WAND loop sorts terms by current doc id, finds a **pivot term** where the cumulative term upper bounds first exceed the heap threshold, and skips any doc that can't reach the threshold — only fully scoring docs that *could* enter the top-k. `GreaterThan{threshold}` (`wand_parts.h:484-487`) is the discard predicate for **parallel WAND** (`parallel_weak_and_search`), which can safely drop hits below the running heap minimum. `MaxSkipOrder` (`:164-175`) orders terms by `p_not_hit(est_hits) * max_score` so the most-skippable terms advance first. This is the same family as Weaviate's BlockMaxWAND (block-level vs term-level max bounds).

### Nearest-neighbor operator — index vs brute-force, target-hits adjustment (KNOWN, `searchlib/.../queryeval/nearest_neighbor_blueprint.h`)

The `nearest_neighbor` query operator (`nearest_neighbor_blueprint.h:60-94`) holds `_target_hits` (requested top-k), `_adjusted_target_hits` (raised to compensate for post-filter loss), `_approximate` (use HNSW vs exhaustive), `target_hits_max_adjustment_factor` (`:42`) — the cap on how far the engine over-fetches when a filter is present. With `_approximate=false` it does brute-force (the "streaming mode" for low-doc-count or strongly-filtered cases); with `=true` it traverses HNSW with `HnswParams`. **The reveal:** Vespa *automatically* switches between exact and approximate based on filter selectivity and doc count, and over-fetches (`adjusted_target_hits`) when filtering to avoid recall collapse — the engine-level version of Qdrant's `full_scan_threshold` + filtered-ANN combined into one adaptive operator.

### HNSW + BM25 co-location (KNOWN, `searchlib/src/vespa/searchlib/tensor/hnsw_index_config.h`)

Vespa's HNSW config exposes `max_links_at_level_0`, `max_links_on_inserts` (= M), `neighbors_to_explore_at_construction` (= efConstruction), `min_size_before_two_phase` (`:16-31`) — a two-phase build for large indexes. Both the HNSW tensor index and the BM25 inverted index live in the **same content node** over a shared document-id namespace: a `nearest_neighbor` operator and a `weakAnd` operator are just two query-tree leaves evaluated against the same doc store, combined by a rank expression (a tensor expression: e.g. `closeness(field, embedding) * w1 + bm25(text) * w2`). So hybrid is "two operators, one ranking formula" — not two systems merged. The formula is data, declared in the schema, so weights are tunable without redeploying.

### For Verso

- **Phased ranking as a declared pipeline, not a bolted-on reranker.** This is the headline transfer. Verso memory retrieval should be: **phase-1** cheap ANN shortlist over all memories (`closeness + bm25` linear combo, drop-limit prunes) → **phase-2** expensive rerank over top-N with the *actual task context* (cross-encoder / LLM-judge) → optional **global-phase** over the merged top-K if memory is sharded. Each phase is a named, swappable scorer with its own `rerank_count` and `score_drop_limit`. This generalizes "retrieve then rerank" into a tunable n-stage funnel.
- **`rank_score_drop_limit` per phase = built-in early pruning.** Don't carry hits that can't matter into the next, more expensive phase. Verso's funnel should drop below a per-phase score floor.
- **WAND max-score-bound skipping** (term-level) is the alternative to Weaviate's BlockMaxWAND (block-level) for Verso's sparse leg. Precompute each term's `weight × max_posting_weight`; pivot on cumulative bounds; skip docs that can't reach the heap threshold.
- **One doc store, two operators, one formula.** Co-locate the dense index and sparse postings over a shared id space (as Verso's SQLite/embedded backend naturally does), then express hybrid as a *ranking formula over two query leaves* rather than a merge of two services.

---

## sqlite-vec

### What It Is

A single-file (`sqlite-vec.c`, ~10.7k lines) zero-dependency C SQLite extension adding KNN vector search via a `vec0` **virtual table**. Brute-force by default (SIMD-accelerated), runs anywhere SQLite runs (WASM, RPi). This is the **minimum viable embedded backend** for Verso's tactical/test mode — no server, no Docker, pure Python + a loadable extension.

### Python binding — there is barely one (KNOWN, PyPI `sqlite-vec==0.1.9` wheel)

The whole "binding" (`sqlite_vec/__init__.py`) is: ship a platform `vec0.dylib`/`.so`, expose `load(conn)` = `conn.load_extension(loadable_path())`, and `serialize_float32(vec) = struct.pack("%sf" % len(vec), *vec)`. **No PyO3, no CFFI, no ctypes wrapper** — it's the native SQLite extension-loading mechanism. Contrast Chroma's heavy PyO3 `Bindings`: sqlite-vec's embedding cost is essentially zero because it lives *inside* SQLite's own plugin ABI. Vectors are passed as raw little-endian float32 blobs.

### vec0 virtual table — xBestIndex query planning (KNOWN, `sqlite-vec.c:6012-6320`)

`vec0BestIndex` inspects the query's constraints and picks one of three plans (`:4858-4860`):

```c
VEC0_QUERY_PLAN_FULLSCAN = '1'   // no MATCH, no rowid EQ → scan all chunks
VEC0_QUERY_PLAN_POINT    = '2'   // EQ on rowid → single-row fetch
VEC0_QUERY_PLAN_KNN      = '3'   // MATCH on vector col + (LIMIT or k=?) [+ optional rowid IN, partition, metadata]
```

KNN plan requires (`:6097-6106`): a `MATCH` op on a vector column, **and** either a `LIMIT` or a `k = ?` constraint (exactly one, not both — hard error otherwise), only one `MATCH`. `xBestIndex` then *encodes the plan into `idxStr`* as a tagged byte string: a plan char, then per-constraint kind tags — `KNN_MATCH`, `KNN_K`, `KNN_ROWID_IN`, `KNN_PARTITON_CONSTRAINT` (`'A'+partition_idx`, value), `METADATA_CONSTRAINT` (`'A'+metadata_idx`, op) (`:6141-6318`). `xFilter` (`vec_eachFilter`) decodes `idxStr` and runs the chosen plan. This idxStr-as-tagged-bytes is how a SQLite vtab carries structured query intent from planning to execution.

### Chunk layout — fixed-size blocks of vectors (KNOWN, `sqlite-vec.c`)

`chunk_size = 1024` default (`:5140`). A vec0 table is backed by **shadow tables**:

```sql
-- _chunks (:3411): one row per chunk
chunk_id INTEGER PK, size INTEGER, validity BLOB, rowids BLOB
--   validity = 1024/8 = 128-byte bitmap (1 bit per slot: live/deleted)  (vec0_new_chunk :4676)
--   rowids   = 1024 * 8 bytes = i64 rowid per slot                       (:4677)
-- _vector_chunksNN (:3441): the actual vectors, one blob per chunk
--   = chunk_size * vector_byte_size bytes, contiguous                    (:4725)
-- _rowids (:3419): rowid → (id, chunk_id, chunk_offset)  — locates a row's slot
-- _metadatachunksNN, _auxiliary, (+ experimental _ivf_cells / _rescore_*)
```

So a chunk = up to 1024 vectors packed contiguously in one BLOB, a 128-byte validity bitmap, and a 1024×i64 rowid array. **Deletion is a tombstone**: clear the validity bit (`bitmap`), don't compact. KNN search (`vec0Filter_knn`) iterates chunks: `sqlite3_blob_open` the vector blob, loop `i in 0..chunk_size`, skip if `!bitmap_get(validity, i)`, else compute distance, maintain a top-k via `min_idx` selection (`:6511-6589`, linear min-find over a candidate bitmap). **It is exhaustive** — every live vector is scored. (v0.1.9 adds *experimental* IVF cells, `SQLITE_VEC_EXPERIMENTAL_IVF_ENABLE`, `:3574-3582`, and optional rescore shadow tables — but the default remains brute-force.)

### Metadata filtering — columnar, chunk-aligned (KNOWN, `sqlite-vec.c:4556-4566`, `:2388-2393`)

vec0 supports inline metadata columns (`boolean`/`integer`/`float`/`text`) stored in their own per-column shadow tables, **chunk-aligned** so a metadata constraint can be evaluated as a block-wise predicate during the KNN scan (not a post-filter join). Storage per chunk (`vec0_metadata_chunk_size`):

```c
BOOLEAN → chunk_size / 8 bytes  (bitmap, 1 bit/row)
INTEGER → chunk_size * 8 bytes  (i64/row)
FLOAT   → chunk_size * 8 bytes  (double/row)
TEXT    → chunk_size * VEC0_METADATA_TEXT_VIEW_BUFFER_LENGTH  (fixed-width view + overflow)
```

The KNN `xFilter` decodes the `METADATA_CONSTRAINT` tag from `idxStr` and, for each chunk, reads the metadata column blob and prunes rows that fail the predicate *before* computing distance — so a query like `WHERE embedding MATCH ? AND k=10 AND memory_type = 2` scans vector slots only where the boolean/int filter passes. Combined with `partition key` columns (which prune whole *chunks*), this gives the embedded tier two filter granularities: partition (chunk-level) + metadata (row-level). Inserts find the next free slot via the chunk validity bitmap (`vec0Update_InsertNextAvailableStep:8692`, opens the latest chunk's `validity` blob, scans for a 0 bit); a full chunk triggers `vec0_new_chunk`.

### SIMD distance kernels (KNOWN, `sqlite-vec.c:413-789`)

Metrics: `distance_l2_sqr_float`/`_int8`, `distance_l1_f32`/`_int8`, `distance_cosine_float`/`_int8`, `distance_hamming` (NEON `:659`, AVX2 `:716`, scalar u8/u64). Element types: float32, int8, bit (binary). The hamming kernels are for binary-quantized vectors (popcount-XOR), selected at runtime by CPU feature.

### For Verso

- **This is Verso's embedded/test `MemoryStore` baseline — adopt as-is.** `pip install sqlite-vec`, `vec.load(conn)`, `CREATE VIRTUAL TABLE memories USING vec0(embedding float[768], session_id integer partition key)`, query `WHERE embedding MATCH ? AND k = ?`. Zero infra, runs in CI, in WASM, on a laptop. The graduation path is explicit: start here, move to pgvector/Qdrant for durable mode (exactly the brief's intent).
- **Brute-force below ~10k is correct** (cf. Qdrant's `full_scan_threshold = 10_000`). sqlite-vec scoring every live vector is *fine* for an agent's working memory; the absence of HNSW is a feature for the embedded tier — no index build, no graph maintenance, deletes are just a cleared bit.
- **Tombstone-bit deletes, no compaction.** For an ephemeral memory store with TTLs, clearing a validity bit is the cheapest possible delete. Verso's embedded store can mirror this and only compact chunks lazily.
- **`partition key` columns** (`session_id integer partition key`) give per-session/per-agent physical partitioning so a filtered KNN only scans the relevant chunks — the embedded-tier analogue of Qdrant `payload_m` / pgvectorscale labels. This is the typed-memory filter mechanism for the SQLite backend.
- **idxStr-as-tagged-bytes** is the pattern if Verso ever writes its own SQLite vtab: encode the query plan + constraints into the opaque `idxStr` in `xBestIndex`, decode in `xFilter`. Carries structured intent across SQLite's planner boundary.

---

## Cross-System Synthesis → Verso `MemoryStore`

### Hybrid fusion: every system ships exactly two fusers — adopt both

| System | Rank-only fuser | Score-aware fuser | k / norm |
|---|---|---|---|
| Qdrant | RRF | DBSF (±3σ Welford) | `k=2` default |
| Weaviate | rankedFusion | relativeScoreFusion (min-max) | `k=60` hard-coded |
| pgvector | RRF (SQL CTE) | — | `k=60` (SQL constant) |
| Milvus | RRF over dense+sparse | — | — |
| Turbopuffer (xref) | `rank_by Sum[Product...]` weighted | — | weighted-product |

The pattern is unanimous: **rank-only (RRF) when score scales are incomparable (cosine vs BM25), score-normalized (DBSF/relative) when scores are calibrated.** Verso ships both. The RRF `k` is a tunable, not a law — the systems disagree (2 vs 60); expose it, default to 60 (the literature value), and document Qdrant's contrarian 2.

### Storage engine: two archetypes

- **Mutable slab allocator** (Qdrant Gridstore): tracker → pages, bitmask free-list, per-region gap summaries, exactly-once flush via `{current, to_free}`. Best for in-place mutation, low metadata overhead. 128B blocks / 8192-block regions / 32MB pages / LZ4.
- **Append-only log + compaction** (Chroma WAL3, Milvus growing→sealed): immutable fragments + CAS'd manifest + set-hash checksum; background compactor materializes indexes. Best for object-storage durability and read/write decoupling. Batch 100ms/64MB; seal at ~12% of 1GB.

Verso's tactical mode → slab/SQLite (sqlite-vec); durable mode → append-only log (WAL3 pattern). The seam between them is Chroma's PyO3 `Frontend` trick: **same request handlers, swap the `{executor, log, sysdb}` config**.

### Filtered ANN: three mechanisms for typed-memory filters

`payload_m` extra subgraph links (Qdrant) / `smallint[]` labels with intersection-gated RobustPrune (pgvectorscale) / `partition key` chunk partitioning (sqlite-vec) / collocated inverted index (Weaviate). All beat "post-filter an unfiltered ANN result." Verso maps `memory_type`/`agent_id`/`session` to whichever the chosen backend supports.

### Multi-phase retrieval: Vespa's funnel is the context-engineering model

cheap ANN+BM25 shortlist (drop-limit prunes) → expensive rerank over top-N *with task context* → optional global merge. Each phase named, swappable, with its own `rerank_count` + `score_drop_limit`. This is how Verso turns "retrieve then rerank" into a tunable n-stage funnel — the highest-leverage transfer for memory retrieval quality.

### Index defaults reference (verbatim, do not conflate)

| System | M | ef_construction | ef_search | other |
|---|---|---|---|---|
| Qdrant HNSW | 16 (m0=32) | **100** | =ef_construct (100) | full_scan_threshold=10_000 |
| pgvector HNSW | 16 | **64** | **40** | max_dim=2000 |
| pgvectorscale DiskANN | R=50 | L=100 | query L=100 | α≤1.2, rescore=50, SBQ 2b<900d else 1b |
| Weaviate BM25 | — | — | — | k1=1.2, b=0.75, RRF k=60 |
| Milvus segment | — | — | — | maxSize=1024MB, seal@0.12 |
| sqlite-vec | (none) | (none) | (none) | chunk_size=1024, brute-force |

