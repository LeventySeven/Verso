# RE Targets: Retrieval + Vector/Memory Stores (Not Yet Covered)

Category key: `retrieval-vector-missing`
Produced: 2026-06-05

Verso relevance lens: Verso needs a **memory backend edge** — a pluggable interface where agents
persist and retrieve semantic memories. The choice of storage primitive (embedded vs. server,
dense-only vs. hybrid, SQL-integrated vs. standalone, synchronous vs. async-compacting) directly
shapes the Verso `MemoryStore` abstraction. This file asks: which vector/retrieval stores teach
Verso something non-obvious about that abstraction design?

---

## Already Covered

- **LanceDB** — `teardowns/LANCEDB.md` (31,400 lines). Full RE: Lance columnar format, multimodal
  index, Python-native embedded+server modes. Covers hybrid search, multi-index, FTS.
- **Turbopuffer** — `teardowns/TURBOPUFFER.md` (11,736 lines). Full RE: serverless ANN-over-object-
  storage, sparse vector support (SPLADE/uniCOIL via inverted-list), six-index-per-attribute schema,
  BM25F comparison.
- **R2R** — `teardowns/R2R.md` (758 lines). Covered as RAG pipeline, not a vector store itself.

None of the seed targets (Chroma, Weaviate, Qdrant, pgvector/pgvectorscale, Vespa, txtai, Milvus,
sqlite-vec) have dedicated teardown files.

---

## RE Targets

### Qdrant

**What it is:** Production-grade vector database written in Rust; HNSW for dense, inverted index for
sparse, Gridstore custom key-value for payload+sparse storage; native hybrid search via Query API
with server-side RRF fusion.

**Why for Verso:** Qdrant's Query API is the clearest published model of "one request, multiple
retrieval legs merged server-side." The prefetch→fuse→rerank pipeline is directly transferable to
Verso's memory retrieval path. Gridstore (O(1) reads/writes, 6 KB metadata per GB) is the answer to
"what does an agent-memory store's storage engine look like at low overhead." Sparse inverted index
(lib/sparse/) alongside dense HNSW shows the dual-index layout Verso would need for hybrid memory
search. ACORN index (filtered ANN without post-filtering recall collapse) is directly relevant to
Verso's typed-memory filtering (filter by memory type, agent id, session).

**What to RE:**
1. `lib/segment/` — segment lifecycle (Appendable → Indexed transition thresholds, SegmentHolder
   merge logic, optimizer config)
2. `lib/sparse/src/index/inverted_index/` — sparse inverted index structure (posting lists,
   compression, search path)
3. Gridstore four-layer design (data/mask/gaps/tracker), block size, WAL idempotency
4. Query API pipeline: how `prefetch` + `FusionQuery` (RRF with `k=60` constant) routes to
   segment-level search and merges results
5. ACORN index (post-v1.12) — how it avoids recall collapse under metadata filters

**Source pointer:** `github.com/qdrant/qdrant` (Rust, 87% of codebase); docs at
`qdrant.tech/documentation/`; engineering blog has Gridstore article and 1.13 release notes.

**Priority:** P0 — Qdrant's Query API prefetch/fuse/rerank model and Gridstore O(1) storage are
directly load-bearing for Verso's memory backend interface design.

---

### Chroma

**What it is:** Open-source "search infrastructure for AI" — originally Python+SQLite+HNSW; fully
rewritten to a multi-crate Rust workspace (68% of codebase) with PyO3 Python bindings, log-
structured storage on S3, and a distributed microservices topology.

**Why for Verso:** Chroma solves exactly the "same library runs embedded in tests AND as a
distributed server in prod" problem — which is Verso's tactical↔durable seam applied to storage.
The WAL3 log-structured design (writes append to immutable S3 parquet fragments; background
compaction materializes HNSW/SPANN segments; reads combine INDEX_ONLY or INDEX_AND_WAL consistency
modes) is a direct blueprint for how Verso could make its memory backend "durable by flag." The
PyO3 boundary (RustBindingsAPI for embedded vs. HTTP client for distributed) is the exact seam
Verso needs to define for its MemoryStore edge.

**What to RE:**
1. `rust/frontend`, `rust/worker`, `rust/log-service` — service topology and gRPC contracts
2. WAL3 structure: S3-backed parquet fragments + setsum checksum + manifest; how reads merge
   compacted segments with uncompacted log entries
3. Segment types: HNSW (header.bin, data_level0.bin, link_lists.bin), SPANN (clustered, billion-
   scale), Blockfile (Arrow RecordBatch columnar), Sparse Index
4. `rust/python_bindings/src/bindings.rs` — PyO3 FFI boundary; how the same Rust core serves
   embedded and remote modes
5. Metadata filtering path through SysDB (SQLite→PostgreSQL) and how it interacts with HNSW scan

**Source pointer:** `github.com/chroma-core/chroma`; deepwiki at `deepwiki.com/chroma-core/chroma`;
architecture overview at `docs.trychroma.com/docs/overview/architecture`; WAL3 engineering post at
`trychroma.com/engineering/wal3`.

**Priority:** P0 — the embedded↔distributed same-codebase pattern is the closest analogy to
Verso's tactical↔durable seam; WAL3 and compaction are directly applicable to durable memory design.

---

### Weaviate

**What it is:** Open-source vector database in Go; HNSW for dense vectors, LSM-based inverted index
(BlockMaxWAND-optimized BM25F) for keyword; Hybrid Search 2.0 collocates BM25 data with HNSW nodes
in a unified index; learned fusion model eliminates manual alpha tuning.

**Why for Verso:** Weaviate's Hybrid Search 2.0 unified index (BM25 data collocated with HNSW nodes,
not separate indexes merged at query time) achieves 40% storage reduction and eliminates merge
overhead — this is the architecture Verso's memory backend would want if it needs hybrid retrieval
without running two separate stores. The BlockMaxWAND optimization for BM25 top-k is a specific
algorithm Verso should know about for efficient sparse leg execution. The learned fusion model
(trained on query patterns, replaces manual alpha=0.75 default) is relevant to Verso's evals/
reliability pillar — retrieval quality should be measurable and improvable.

**What to RE:**
1. `adapters/repos/db/inverted/` — BM25 inverted index: posting lists, delta_merger.go, document
   length normalization; BlockMaxWAND top-k algorithm
2. Hybrid Search 2.0 unified index: how BM25 data is stored alongside HNSW graph nodes (co-location
   in shard), what the learned fusion model looks like (training data, feature set, output weight)
3. `adapters/repos/db/lsmkv/` — LSM key-value store: segment format, compaction triggers, how it
   serves both payload and inverted index
4. `adapters/repos/db/shard.go` — shard lifecycle: how a Weaviate "class" maps to one or more shards
5. RRF implementation and relative-score fusion: the two fusion algorithms exposed as `fusionType`

**Source pointer:** `github.com/weaviate/weaviate` (Go); deepwiki at
`deepwiki.com/weaviate/weaviate`; Hybrid Search 2.0 announcement at
`app.ailog.fr/en/blog/news/weaviate-hybrid-search-2`.

**Priority:** P1 — unified hybrid index architecture and learned fusion are strong reference
patterns; less directly applicable than Qdrant/Chroma because Verso is Python, not Go.

---

### pgvector + pgvectorscale

**What it is:** Two PostgreSQL extensions — pgvector (C, HNSW + IVFFlat vector operators inside
Postgres ACID transaction layer) and pgvectorscale (Rust/PGRX, StreamingDiskANN + Statistical
Binary Quantization + Filtered DiskANN for label-based filtering).

**Why for Verso:** For Verso agents that already use Postgres for durable state (the durable half of
the tactical↔durable seam), pgvector means zero new infrastructure: memories live in the same DB as
checkpoints, tool outputs, and HITL approvals. pgvectorscale's StreamingDiskANN is the right answer
when the Postgres memory store grows to tens of millions of rows (28x lower p95 latency vs Pinecone
at 50M vectors, 99% recall). The SBQ quantization (num_bits_per_dimension: 2 for dim<900, else 1)
and Filtered DiskANN (label smallint arrays with `&&` overlap) show the exact SQL-level API Verso
would expose for typed-memory filtering. Hybrid search is SQL-composed: BM25 via `plainto_tsquery`
+ pgvector ANN merged with RRF in a SQL CTE — no new query language.

**What to RE:**
1. pgvector `src/` — HNSW C implementation: m=16, ef_construction=64, ef_search=40 defaults; how
   the index access method hooks into Postgres WAL/MVCC; IVFFlat k-means phase
2. pgvectorscale `pgvectorscale/` — StreamingDiskANN: num_neighbors=50, search_list_size=100,
   max_alpha=1.2, query_rescore=50; how "relaxed ordering" differs from strict DiskANN
3. SBQ compression: num_bits_per_dimension logic, memory_optimized vs plain layout
4. Filtered DiskANN: how Microsoft's filtered-ANN research maps to `smallint[]` label arrays in SQL
5. Hybrid search SQL pattern: combining `<->` operator with `ts_rank_cd` in a single query via CTE
   and RRF re-ranking

**Source pointer:** `github.com/pgvector/pgvector` (C); `github.com/timescale/pgvectorscale`
(Rust/PGRX); pgvector docs at `pgvector.github.io`; pgvectorscale README has benchmark numbers.

**Priority:** P1 — directly relevant for Verso's "durable mode uses Postgres" deployment path;
pgvector+pgvectorscale is the zero-new-infrastructure memory backend for Postgres users.

---

### Milvus

**What it is:** Cloud-native distributed vector database in Go+C++ (Knowhere index library);
storage/compute disaggregated (MinIO/S3 + etcd + Pulsar/Kafka); MixCoord coordinator pattern
(RootCoord/DataCoord/QueryCoord/StreamingCoord unified); Milvus 2.5 adds native BM25 full-text
search via tantivy tokenizer → SPARSE_INVERTED_INDEX, enabling true dense+sparse hybrid queries.

**Why for Verso:** Milvus is the reference architecture for "vector database at microservices scale"
— the pattern Verso would follow if the memory backend needs to scale beyond a single node without
changing the API. The Knowhere library (wraps HNSW, IVF, DiskANN, SCANN, GPU-CAGRA) is the most
complete index menu in the open-source space and teaches Verso what index-type routing decisions
look like. The BM25-via-sparse-vector approach (tantivy tokenizer + inner product on sparse vectors
= BM25 scoring) is a clean design pattern: no separate FTS engine, BM25 is just a special case of
sparse ANN. The growing→sealed segment lifecycle with message-queue-driven compaction is the
distributed equivalent of Chroma's WAL3 compaction — relevant for Verso's durable memory path.

**What to RE:**
1. Knowhere library (`github.com/milvus-io/knowhere`) — index type registry, how HNSW/IVF/DiskANN/
   SCANN/CAGRA are wrapped, build-time vs query-time params for each
2. BM25 implementation: tantivy integration, how raw text → sparse vector → SPARSE_INVERTED_INDEX;
   k₁ and b parameters; how term stats are maintained across growing/sealed segments
3. Hybrid query execution: how dense ANN + sparse BM25 results are merged (RRF); the
   `multi-vector-search` API surface
4. Growing vs sealed segment lifecycle: write path (Pulsar WAL → growing segment), flush trigger
   (size threshold), seal→compact→index cycle on DataNode
5. MixCoord unified coordinator: what each sub-coordinator owns, how QueryCoord distributes sealed
   segment load across QueryNodes

**Source pointer:** `github.com/milvus-io/milvus` (Go main); `github.com/milvus-io/knowhere` (C++
index library); deepwiki at `deepwiki.com/milvus-io/milvus`; BM25 internals blog at
`milvus.io/blog/full-text-search-in-milvus-what-is-under-the-hood.md`.

**Priority:** P1 — Knowhere index menu and BM25-as-sparse-vector pattern are strong reference;
microservices complexity makes it P1 not P0 (Verso is Python-native, not Go+C++).

---

### Vespa

**What it is:** Full-stack Java+C++ search platform (Yahoo origin); content nodes (C++, stateful,
data+index+ranking co-located) + container nodes (Java, stateless, query processing) + config nodes;
multi-phase ranking (first-phase cheap expr on all candidates → second-phase expensive on top-k →
global-phase for cross-node merge); HNSW + BM25 + WAND + OR operators + tensor ranking expressions
all in one engine.

**Why for Verso:** Vespa is the only system that makes multi-phase ranking a first-class primitive —
not "apply a reranker after retrieval" but a declared ranking profile with phases. This maps
directly onto Verso's context engineering: if memory retrieval is multi-phase (fast ANN shortlist →
expensive rerank with the actual task context), Vespa's YQL ranking profile syntax is the reference
design. The WAND (Weak AND) operator for efficient top-k over sparse BM25 candidates is the
production algorithm behind "fast BM25 without scanning all docs." The tensor expression language
for ranking shows how to express hybrid scoring as a formula without hard-coding weights.

**What to RE:**
1. Content node C++ ranking architecture: first-phase vs second-phase expressions, how they're
   evaluated, what "phased ranking" looks like in `searchlib/` source
2. WAND operator: implementation in `searchlib/src/vespa/searchlib/queryeval/wand/`; how it achieves
   efficient top-k for BM25 without full scan
3. HNSW + BM25 co-location in content node: are they in the same storage layer or separate
   components sharing a document ID namespace?
4. YQL ranking profile syntax → how Verso could model a configurable hybrid-score formula
5. Nearest-neighbor search operator in streaming mode vs index mode: when to use which

**Source pointer:** `github.com/vespa-engine/vespa` (Java+C++); architecture at `vespa.ai/
architecture/`; multi-stage ranking blog at `pradeepbhandari.com/blog/vespa-multi-stage-ranking-
merging-bm25-and-vector-search`; WAND in `searchlib/src/vespa/searchlib/queryeval/wand/`.

**Priority:** P1 — multi-phase ranking profile is directly relevant to Verso's memory retrieval
design; closed-in practice (Yahoo-scale infra, hard to run locally), so RE focus is source code +
blog, not server probing.

---

### sqlite-vec

**What it is:** Pure-C SQLite extension (no dependencies) adding KNN vector search via a `vec0`
virtual table; brute-force by default, SIMD-accelerated; runs anywhere SQLite runs including WASM
and Raspberry Pi; Mozilla Builders project, sponsored by Fly.io/Turso/SQLite Cloud.

**Why for Verso:** sqlite-vec is the minimum viable memory backend for Verso's tactical (in-memory /
test) mode — zero server, zero Docker, pure Python + ctypes. The `vec0_vtab` virtual table module
is the exact design pattern for "vector search as a SQL virtual table" that Verso would replicate
if it ships an embedded SQLite memory backend. The chunk-based storage (vectors stored in fixed-size
blocks grouped by partition key) teaches the tradeoff between brute-force simplicity and the
overhead of managing an HNSW index. Its limits (no HNSW, no hybrid search, brute-force only) are
also instructive: Verso's embedded mode can start here and graduate to Qdrant/pgvector for durable
mode.

**What to RE:**
1. `vec0_vtab` virtual table module — C source at `github.com/asg017/sqlite-vec/src/sqlite-vec.c`;
   how the virtual table implements KNN via `xBestIndex` + `xFilter` SQLite hooks
2. Chunk layout: how vectors are packed into fixed-size blocks, partition key storage, deletion flags
3. SIMD acceleration: which intrinsics are used, how they're selected at runtime, distance metrics
   supported (L2, cosine, dot)
4. Python binding: how `sqlite-vec` is exposed via the `sqlite-vec` PyPI package; the ctypes/CFFI
   interface
5. Absence of HNSW: is there any approximate index, or is it always exhaustive? What's the design
   choice reasoning?

**Source pointer:** `github.com/asg017/sqlite-vec` (C); PyPI package `sqlite-vec`; Mozilla Builders
project page.

**Priority:** P2 — directly useful as Verso's zero-dependency embedded test backend; low RE
complexity (single C file), high practical value for the tactical mode use case.

---

### txtai

**What it is:** Pure-Python AI framework where the `Embeddings` class is a union of three stores:
dense ANN index (default all-MiniLM-L6-v2 via sentence-transformers), sparse BM25 index, and a
graph network (entity/relationship extraction on ingest); SQL query layer across all three; agent
integration via smolagents.

**Why for Verso:** txtai ships a ready-made "embeddings database" that is architecturally very
close to what Verso's typed memory backend would be — one Python class that exposes dense search,
sparse BM25, graph queries, and SQL in a unified API. Reading its `Embeddings` class implementation
answers: how do you merge dense+sparse+graph scores in Python without native code? The graph layer
(entities/relationships extracted on ingest, stored as NetworkX or separate graph backend) is
relevant to Verso's typed memory — does Verso want a graph layer over memories? The smolagents
integration shows the minimal API contract between an agent loop and a memory store.

**What to RE:**
1. `src/python/txtai/embeddings/` — the `Embeddings` class: index types, backend selection
   (Faiss/Annoy/Hnswlib for ANN, BM25-via-rank_bm25 for sparse), how hybrid scoring merges results
2. `src/python/txtai/embeddings/search/base.py` — search pipeline: dense path, sparse path,
   combined path
3. Graph layer: what entity extraction is used, graph backend (NetworkX default), how graph
   search integrates with ANN results
4. SQL layer: how SQL queries are routed to the correct underlying store; the relational metadata
   schema
5. smolagents integration: the tool definitions Verso could adopt for memory read/write

**Source pointer:** `github.com/neuml/txtai` (Python); PyPI `txtai`; hybrid search example at
`github.com/neuml/txtai/blob/master/examples/48_Benefits_of_hybrid_search.ipynb`.

**Priority:** P2 — pure Python makes it easy to read; closest existing Python implementation of
"typed memory as unified dense+sparse+graph store"; lower novelty than Qdrant/Chroma because it
uses off-the-shelf ANN libraries, but the API design is directly useful as a reference.

---

## Notes

**What's deliberately excluded:**

- **Pinecone** — closed, serverless-only, no source to read; architecture is well-described by
  Turbopuffer (which the team explicitly positioned against Pinecone) and Qdrant. Skip.
- **Faiss** (Meta) — covered implicitly via Milvus/txtai; it's a library, not a store; no agent-
  memory-backend relevance beyond being an ANN primitive.
- **ElasticSearch/OpenSearch** — covered at the "hybrid search exists" level in the ecosystem;
  Java, not Python; Verso is not building a search engine, it's building a memory backend. Skip.
- **Redis (vector search)** — RediSearch/redis-stack adds vector search on top of Redis; the
  interesting part for Verso is the in-memory key-expiry model for ephemeral memory TTLs, but
  this is covered by Redis generally; not enough novel RE surface.
- **Zep / Mem0 / Cognee** — agent memory *layers* not vector stores; they sit on top of stores
  like Qdrant/pgvector. The memory-layer category is separate from this vector-store category.
  They may warrant their own RE file if Verso needs to understand the memory orchestration layer.

**Priority rationale:**

- P0 (must RE before shipping memory backend interface): Qdrant (Query API / Gridstore), Chroma
  (WAL3 + embedded↔distributed seam). These two define the design space.
- P1 (strong reference, shapes specific decisions): Weaviate (unified hybrid index), pgvector+
  pgvectorscale (Postgres-native path), Milvus (microservices scale + BM25-as-sparse-vector),
  Vespa (multi-phase ranking profile).
- P2 (useful but lower urgency): sqlite-vec (zero-dep embedded baseline), txtai (Python reference
  for unified dense+sparse+graph API).

**Cross-reference:** Verso memory backend interface should also read:
- `teardowns/LANCEDB.md` — Lance columnar format, multimodal, embedded+server
- `teardowns/TURBOPUFFER.md` — serverless ANN-over-object-storage, sparse BM25, six-index schema
- `teardowns/SUPERMEMORY.md` — agent memory orchestration layer (if it exists)
