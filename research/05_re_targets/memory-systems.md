# RE Targets — Agent Memory Systems

**Category:** Agent memory systems (Verso primitive — HIGH)
**Date:** 2026-06-05
**Purpose:** Identify which memory frameworks Verso must RE to make informed decisions about extraction/write policy, retrieval scoring, temporal/invalidation model, scoping, and backend design. Verso's memory is a first-class primitive (typed, scoped, pluggable backend), not a bolt-on.

---

## Already Covered

The following are fully reverse-engineered in `teardowns/`:

- **Supermemory** (`teardowns/SUPERMEMORY.md`, ~1,600 lines) — versioned memory entry as primitive, three-embedding-slots-per-record (raw/sparse/latent), memory forgetting via version chain, PostgreSQL + Cloudflare stack, LongMemEval-s 85.2%, ASMR agentic pipeline, full SDK source (supermemory@4.21.1). Verso-relevant: versioned fact model, multi-slot embedding design.
- **Letta / MemGPT** (`teardowns/LETTA.md`, very deep) — self-editing core memory blocks via tool calls, virtual context (core/recall/archival layers), `request_heartbeat` control, `DEFAULT_EMBEDDING_DIM=1024`, 9 system prompt variants, agent-as-memory-OS design. Verso-relevant: the agent-as-memory-OS pattern, the in-loop vs. external memory tradeoff.
- **HydraDB** (`teardowns/HYDRADB.md`, ~2,800+ lines) — Sliding Window Inference Pipeline, latent semantic bridging, git-style append-only temporal multigraph, recall equations 7–16 from paper, Milvus triple-vector per record, bio-mimetic decay, explicit comparison table vs. Mem0/Zep/Supermemory. Verso-relevant: most technically complete memory teardown in the repo; explicit rejection of iterative-resolve-on-write (Mem0/Zep pattern) with O(N) argument.

---

## RE Targets

### Mem0

**What it is:** Universal memory layer for AI agents (~48K GitHub stars); open-source OSS tier + managed cloud; Python/JS SDK; multi-store (vector + graph + KV); 91.6% LoCoMo, 94.8% LongMemEval.

**Why for Verso:** Mem0 is the current default memory layer — Verso will be compared against it by every user. Its write policy is the most-copied pattern in the ecosystem: a two-phase Extract → A.U.D.N. (Add/Update/Delete/No-op) consolidation loop using LLM function calling (GPT-4o-mini). Understanding exactly what that loop does — how extraction prompts work, how the update/delete cycle causes false positive deletions at scale (the failure mode HydraDB paper §4.1 attacks), how graph memory (mem0g) differs from flat vector memory — is prerequisite for Verso's memory write-policy design. The OSS code is fully readable.

**What to RE:** `mem0/memory/main.py` — the `add()` method, the two-phase extraction+consolidation pipeline, the exact LLM prompts for extraction and AUDN classification. `mem0/memory/graph_memory.py` — Neo4j graph memory, entity extraction, edge invalidation. `mem0/utils.py` — scoring/ranking fusion (semantic + BM25 + entity search). The scoping model: `user_id`, `agent_id`, `run_id`, `app_id` tagging and how they compose at retrieval. Memory decay/LRU cleanup logic. Also: `mem0/proxy/` — the OpenAI-proxy memory middleware pattern (relevant to how Verso hooks memory into the agent loop).

**Source pointer:** `github.com/mem0ai/mem0` (fully open source, Python); paper `arxiv.org/abs/2504.19413`; benchmark suite `github.com/mem0ai/memory-benchmarks`.

**Priority:** P0

---

### Graphiti (Zep)

**What it is:** Open-source temporal knowledge graph engine powering the Zep memory service; Python; bi-temporal model with validity intervals on every edge; paper arXiv:2501.13956; used in production CRM/compliance/healthcare agents.

**Why for Verso:** Graphiti is the most rigorous open-source implementation of temporal memory — every edge carries `(t_valid, t_invalid)` intervals, conflict resolution preserves history rather than deleting it, and the system handles both unstructured chat and structured JSON in the same graph. This is the reference implementation for the temporal/invalidation model that Verso's durable-seam memory must support: "what was true, when did it change, why." The bi-temporal model directly answers the question of how Verso's checkpoint-resume agents reconstruct valid memory state at an arbitrary past point. Full Neo4j-backed, Cypher-query based, entity resolution with gpt-4o-mini. The paper gives exact constants: last n=4 messages for NER context, BGE-m3 embeddings at 1024-dim cosine.

**What to RE:** `graphiti_core/` — `graphiti.py` (the main add_episode() pipeline), `nodes.py` + `edges.py` (data model, bi-temporal fields), `search/search.py` (hybrid search combining semantic + keyword + graph traversal), `llm_client/` (extraction prompt templates for entity/relation NER, reflexion step, conflict resolution decision). The specific Cypher queries for temporal edge invalidation. Episode types: `RawEpisode` vs. `EpisodicNode`. The community/summary rollup logic. Constants: embedding dim, context window for NER, similarity thresholds.

**Source pointer:** `github.com/getzep/graphiti` (open source, Python); paper `arxiv.org/abs/2501.13956`; Zep service at `getzep.com` (closed backend, but graphiti is the engine).

**Priority:** P0

---

### Hindsight

**What it is:** Agent memory system by vectorize.io; open-source Python; PostgreSQL-only stack (no separate vector DB, no separate graph store); four epistemic memory types (world facts, experiences, entity summaries, evolving beliefs); multi-strategy TEMPR retrieval (semantic + keyword + graph + temporal) fused via RRF then cross-encoder reranked; paper arXiv:2512.12818; 91.4% LongMemEval with large backbone.

**Why for Verso:** Hindsight makes the specific design choice Verso should study most carefully: a single embedded PostgreSQL instance for ALL memory operations (vectors stored in pgvector, BM25 via pg_search/ParadeDB, graph via adjacency rows) rather than a polyglot stack. This directly addresses Verso's "pluggable backend" question — Hindsight proves a single-DB approach is viable at near-SOTA accuracy, avoiding the operational complexity of Milvus+Neo4j+Redis. The four-type epistemic model (world/experience/entity/belief) is a cleaner taxonomy than most systems. The `reflect()` operation — synthesizing beliefs from accumulated experiences — is the pattern Verso's durable-seam agents need for checkpointed belief state. The open-source code is readable and the CLAUDE.md in the repo means they wrote it to be agentic-tool-friendly.

**What to RE:** `hindsight-api/` — `memory/retain.py` (write pipeline: fact extraction → entity resolution → storage), `memory/recall.py` (TEMPR multi-strategy retrieval + RRF fusion + cross-encoder), `memory/reflect.py` (belief synthesis from experiences), the schema (`alembic/versions/`) for the `memory_units` table with `fact_type` column. LLM prompts for extraction and reflection. The `bankGranularity` per-user isolation model. ParadeDB pg_search BM25 integration (v0.7.1+). Constants: retrieval k per strategy, RRF weights, cross-encoder model choice.

**Source pointer:** `github.com/vectorize-io/hindsight` (open source, Python, AGPL); paper `arxiv.org/abs/2512.12818`.

**Priority:** P0

---

### Honcho (Plastic Labs)

**What it is:** Open-source memory library by Plastic Labs; FastAPI + PostgreSQL/pgvector + Redis; peer-centric model (both users and AI agents are "peers"); asynchronous background reasoning to derive psychological facts; 90.4% LongMem; AGPL-3.0; managed service at `api.honcho.dev`.

**Why for Verso:** Honcho's peer-centric identity model is novel and directly relevant to Verso's scoping design. Instead of tagging memory with `user_id` and `agent_id` as flat identifiers (Mem0's model), Honcho treats both as full entities with their own representation, enabling multi-participant sessions where AIs and humans are symmetric. The async background reasoning pipeline — where Honcho infers user psychology asynchronously without blocking the main request path — is a pattern Verso's durable-seam would use: the agent continues while memory consolidation runs in the background, with checkpoint state updated before the next run. The `dreaming` continual-learning loop (background belief refinement over stored sessions) is Verso's answer to "how does memory improve between runs." Fully open-source Python.

**What to RE:** `src/honcho/` — the async background worker pipeline (what triggers it, what LLM prompts it uses to derive psychological facts, how results are stored back), the `Peer` data model (the schema for representing users and agents symmetrically), the collections model (reserved internal collections vs. application collections), the `dreaming` loop implementation, the retrieval scoring (how peer-derived facts score against query relevance). The Redis coordination layer for async workers. The session/message hierarchy and how it maps to memory scopes.

**Source pointer:** `github.com/plastic-labs/honcho` (open source, Python, AGPL-3.0); `honcho.dev`.

**Priority:** P1

---

### Cognee

**What it is:** Open-source Python memory control plane; $7.5M seed; 12K+ GitHub stars; 6-stage pipeline (classify → permissions → chunk → LLM entity+relation extraction → summarize → embed+graph commit); 14 retrieval modes including chain-of-thought graph traversal; pluggable graph backends (NetworkX, Neo4j, Memgraph); 500x pipeline volume growth in 2025.

**Why for Verso:** Cognee's value to Verso is its pluggable backend design and its multi-modal retrieval taxonomy. The 14 retrieval modes — from classic vector RAG to graph traversal with reasoning steps — is the reference for Verso's `memory.recall(mode=...)` API design. The permission/ownership model (step 2 of the pipeline) is the reference for multi-tenant memory scoping. The adaptive retrieval trace (moving from fixed traversal to learned task-dependent policies) is where Verso's evals/reliability concern meets memory: which retrieval mode works for which task type. The 6-stage pipeline is clean enough to read and copy the structure. The in-memory Python graph abstraction (triplet importance scoring + vector distance during search) is simpler to embed than Neo4j.

**What to RE:** `cognee/tasks/` — the 6-stage pipeline implementation, specifically `extract_chunks_from_documents.py`, the entity/relation extraction task, the graph commitment logic. `cognee/infrastructure/databases/` — the pluggable backend adapters (how Vector, Graph, and Relational storage are abstracted). `cognee/api/v1/cognify/` — the retrieval dispatch for the 14 modes. The ontology/custom-type injection point (how users define domain-specific entity types). `cognee/modules/graph/` — the in-memory graph representation and triplet scoring.

**Source pointer:** `github.com/topoteretes/cognee` (open source, Python, Apache-2.0); `cognee.ai`.

**Priority:** P1

---

### Memobase

**What it is:** Open-source Python+server memory system by memodb-io; user profile-based (not fact-list based); structured profiles with topics/subtopics (e.g., `basic_info/name`, `interests/movies`); buffer-based batching (3 LLM calls max per flush, 40-50% cost reduction vs. naive); FastAPI + Postgres + Redis; LOCOMO benchmark top-tier; MIT license.

**Why for Verso:** Memobase makes a specific and defensible design choice: store a structured evolving user profile rather than a flat list of extracted facts. The buffer-based batching — accumulate N messages, then flush with one LLM extraction call seeing full context — is the opposite of Mem0's per-message extraction. This directly informs Verso's write policy: synchronous-per-turn vs. buffered-async. The topic/subtopic taxonomy (a two-level ontology) is how Verso's typed memory could be organized without requiring a full graph DB. The sub-100ms retrieval via SQL (no vector search on hot path) is the latency target to beat. The 3-LLM-calls-max constraint is a useful engineering constraint to evaluate.

**What to RE:** `src/server/` — the buffer flush pipeline, the extraction LLM prompt (what exactly the structured profile extraction asks the model), the topic/subtopic taxonomy definition, the Postgres schema for user profiles. `src/client/` — the Python SDK API contract (how `flush()` and `search()` work). Redis usage for buffer coordination. The update policy: how existing profile entries are merged vs. replaced when new facts conflict.

**Source pointer:** `github.com/memodb-io/memobase` (open source, Python, MIT); `memobase.io`; PyPI `memobase`.

**Priority:** P1

---

### MemOS (MemTensor)

**What it is:** Research-grade open-source "Memory OS" from MemTensor; Python; paper arXiv:2505.22101 + arXiv:2507.03724; MemCube abstraction (standardized memory container with provenance/versioning); four-tier hierarchy (L1 traces → L2 policies → L3 world models → crystallized Skills); hybrid FTS5+vector retrieval; cross-task skill reuse; 35.24% token savings claimed; local-first plugin variant.

**Why for Verso:** MemOS is primarily relevant to Verso's durable-seam design: the L1→L2→L3→Skill crystallization hierarchy is the clearest published model of how an agent's episodic experience becomes reusable structured knowledge. For Verso, this maps to: L1 = in-memory run traces, L2 = extracted patterns from multiple runs (durable), L3 = agent's world model (long-lived), Skills = callable capabilities derived from memory. The MemCube abstraction — a typed, versioned, provenance-tracked memory container that can be migrated and fused — is a potential design for Verso's typed memory API. The cross-task skill reuse is the "memory as capability" pattern relevant to Verso's agent specialization story.

**What to RE:** `memos/` in `github.com/MemTensor/MemOS` — the MemCube schema (how provenance/versioning is tracked), the L1 trace capture mechanism (what fields are recorded per step: action + observation + reflection + value), the L2 policy induction from L1 traces (the abstraction step, including the LLM prompt), the MemOS scheduler for deciding when to promote L1→L2→L3. The FTS5+vector hybrid retrieval implementation. The skill crystallization: how a pattern becomes a callable skill. Paper §3-5 for the formal architecture.

**Source pointer:** `github.com/MemTensor/MemOS` (open source, Python); papers `arxiv.org/abs/2505.22101` + `arxiv.org/abs/2507.03724`.

**Priority:** P2

---

### txtai (neuml)

**What it is:** All-in-one Python AI framework; embeddings DB = union of vector indexes (dense + sparse) + graph network + relational DB; agent capabilities (skills, memory) added in 2024; built on smolagents; active since 2020; 14K+ stars; Apache-2.0.

**Why for Verso:** txtai is the most mature unified-store implementation: it runs vector search, BM25, and graph queries against a single Python-native index without external services. The Embeddings class is the reference design for Verso's "memory backend = embeddings + graph + KV in one API." The smolagents integration shows how a memory store connects to an agent tool loop. The graph component (built on networkx, projectable to SQL) is the simplest graph memory implementation available. The primary value is reading the embeddings API to understand what a clean unified-store Python API looks like before designing Verso's.

**What to RE:** `txtai/embeddings/` — the Embeddings class (index() / search() / graph() methods, the unified API surface), the graph projection (how vector + graph results are fused), `txtai/graph/` — the networkx-backed graph implementation and its query API. `txtai/agent/` — the memory integration with smolagents (how `memory=` parameter is passed). The SQL backend option for embeddings persistence. The approximate vs. exact search tradeoff and the index types supported.

**Source pointer:** `github.com/neuml/txtai` (open source, Python, Apache-2.0); `neuml.github.io/txtai`.

**Priority:** P2

---

## Notes

**Coverage gaps after this list:** No target covers streaming/real-time memory update (Graphiti partially does via incremental graph update). No target covers multimodal memory (image/audio as memory facts) — MemOS has this in `apps/memos-local-plugin` but it's nascent. No target covers adversarial memory (prompt injection into memory stores, memory poisoning) — relevant for Verso's security model but not prioritized here.

**Benchmarks to track:** LongMemEval-s (Xiaowu0162/LongMemEval on GitHub), LoCoMo, LOCOMO, DMR. HydraDB teardown already has LongMemEval-s scores for the main players (Table in §18). Key numbers as of mid-2026:
- HydraDB: 90.79% (LongMemEval-s, Gemini 3.0 Pro judge)
- Honcho: 90.4% (LongMem)
- Hindsight: 91.4% (LongMemEval, large backbone)
- Mem0: 94.8% (LongMemEval), 91.6% (LoCoMo)
- Supermemory: 85.2% (LongMemEval-s)
- Zep: 71.2% (LongMemEval-s, GPT-4o judge — judge-confounded vs. HydraDB/Supermemory)
- Mem0-oss: 29.07% (LongMemEval-s, Gemini 3.0 Pro judge — baseline OSS vector-only)

**Cross-reference:** `teardowns/HYDRADB.md §R2.5` already contains a side-by-side comparison table of Mem0/Zep/Supermemory/GraphRAG architecture choices — read before RE-ing Mem0 or Graphiti to avoid duplicating that analysis.

**Memary status:** Abandoned/inactive (github.com/kingjulio8238/Memary). Not worth RE-ing; no architectural novelty vs. active systems.

**txtai vs. Hindsight priority note:** txtai teaches API design (what a clean unified-store Python interface looks like); Hindsight teaches implementation (how to build it inside PostgreSQL). If resource-constrained, RE Hindsight first.
