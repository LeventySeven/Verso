# Memory Systems — Verso Research Note
## Cluster: memory-systems
### Systems: Mem0 · Graphiti (Zep) · Hindsight (vectorize.io) · Honcho (Plastic Labs) · Cognee · Memobase · MemOS (MemTensor) · txtai (neuml)

*Sources: cloned repos (`git clone --depth=1`, read 2026-06-05) — `mem0ai/mem0`, `getzep/graphiti`, `vectorize-io/hindsight`, `plastic-labs/honcho`, `topoteretes/cognee`, `memodb-io/memobase`, `MemTensor/MemOS`, `neuml/txtai`. Papers: Mem0 arXiv:2504.19413, Graphiti arXiv:2501.13956, Hindsight arXiv:2512.12818, MemOS arXiv:2505.22101 / 2507.03724.*

> Scope: extract the **write loop** (extract → consolidate), the **retrieval fusion math**, the **temporal/invalidation model**, the **scoping model**, and the **DB schema** at reimplementable depth. Companion file `infra-vector-memory.md` (Turbopuffer + LanceDB) covers the *storage primitive* (ANN index, BM25 backend, object-store tiering) — this file covers the *memory cognition layer* that sits on top of it. Already-covered systems (Supermemory, Letta/MemGPT, HydraDB) live in `teardowns/` in the main `researchfms` repo and are referenced where relevant.

Labels: **KNOWN** = read from source at `file:line`. **INFERRED** = derived from code behaviour or paper. **DESIGNED** = our engineering call for a gap.

---

## Mem0

### What It Is

Universal memory layer for agents (~48K stars), OSS + managed cloud, multi-store (vector + entity + KV). The classic Mem0 design is a two-phase write: **extract facts** from the turn, then run an **ADD / UPDATE / DELETE / NONE** LLM pass that reconciles each new fact against the top-k semantically-similar existing memories. The repo head read on 2026-06-05 has **moved past that** to a "V3 phased batch pipeline" that is the default `add()` path — and it is a materially different (and better) design.

`[CORRECTION 2026-06-05]` The RE-target doc and the HydraDB teardown describe Mem0's write loop as a per-fact A.U.D.N. (Add/Update/Delete/No-op) reconcile that causes false-positive deletions at scale. **That is the legacy path. The current default `add()` is ADD-only.** The `DEFAULT_UPDATE_MEMORY_PROMPT` (the AUDN prompt) still ships (`mem0/configs/prompts.py:176-324`) and is used by `_create_procedural_memory` and custom flows, but `_add_to_vector_store` no longer calls it for normal memory writes. Both designs are documented below because the AUDN→additive shift is itself the load-bearing finding for Verso's write-policy decision.

### Write Loop — the V3 phased batch pipeline (current default)

**KNOWN** `mem0/memory/main.py:662-971` (`_add_to_vector_store`). When `infer=True` (default), the pipeline is **8 phases, exactly one LLM call**:

```
Phase 0  context     get_last_messages(session_scope, limit=10)  +  parse_messages(messages)
Phase 1  retrieve    embed(parsed_messages,"search") → vector_store.search(top_k=10, filters=user/agent/run)
                      → map each existing mem to an INTEGER index "0".."9"  (uuid_mapping)  ← anti-hallucination
Phase 2  EXTRACT     ONE LLM call. system = ADDITIVE_EXTRACTION_PROMPT (+ AGENT_CONTEXT_SUFFIX if agent-scoped)
                      response_format={"type":"json_object"} → {"memory":[{text, linked_memory_ids?, attributed_to?}]}
Phase 3  embed       embed_batch(all extracted texts, "add")           ← single batch call
Phase 4/5 dedup      md5(text) hash; skip if hash ∈ existing_hashes ∪ seen_hashes (intra-batch + vs retrieved)
Phase 6  persist     vector_store.insert(vectors, ids=uuid4(), payloads)   ← single batch insert
Phase 7  entities    extract_entities_batch(texts) → global dedup → embed_batch → entity_store.search_batch
                      → if match.score ≥ 0.95 UPDATE linked_memory_ids else INSERT new entity row
Phase 8  history     batch_add_history(event="ADD") ; db.save_messages(messages, session_scope)
```

The key architectural decision: **the default write is monotonic ADD-only.** There is no UPDATE and no DELETE in the hot path. Dedup is done by (a) exact md5 hash match and (b) the extraction prompt being told to skip semantically-equivalent facts. Conflicting/superseding facts are NOT deleted — they are added as new memories, and the *linking* (`linked_memory_ids`) carries the relationship. This is the same conclusion HydraDB's paper §4.1 reaches (iterative resolve-on-write is O(N) and causes false deletes) — Mem0 quietly adopted it.

**The anti-hallucination index map** (`main.py:716-721`): existing memories are presented to the LLM as `{"id":"0","text":...}` with a side `uuid_mapping["0"]→real_uuid`. The LLM only ever sees and emits small integer ids; the system maps back to UUIDs. This prevents the model from inventing or corrupting UUIDs — a pattern Verso should copy verbatim for any LLM-in-the-loop store mutation.

### Write Loop — legacy AUDN (still shipped, used for procedural + custom)

**KNOWN** `mem0/configs/prompts.py:176-324` `DEFAULT_UPDATE_MEMORY_PROMPT`. Two-phase:
1. **Extract** with `FACT_RETRIEVAL_PROMPT` (`prompts.py:15-60`) → `{"facts":[...]}`. Few-shot: "Hi." → `[]`; "my name is John. I am a software engineer." → `["Name is John","Is a Software engineer"]`. Rules: extract from user+assistant only (never system), detect language and record facts in the same language, "Today's date is {date}".
2. **Reconcile** — the LLM is given old memory as `[{id, text}]` + retrieved facts, and must emit per-element `event ∈ {ADD, UPDATE, DELETE, NONE}`. UPDATE keeps the same id and adds `old_memory`; DELETE fires when a new fact *contradicts* an existing one ("Loves cheese pizza" + new "Dislikes cheese pizza" → DELETE id 1). **This contradiction→DELETE rule is exactly the false-positive-deletion failure mode** that the V3 additive path was built to eliminate.

### Retrieval Fusion Math — the actual formula

**KNOWN** `mem0/memory/main.py:1343-1438` (`_search_vector_store`) + `mem0/utils/scoring.py:60-121` (`score_and_rank`). Three signals fused additively (NOT RRF):

```
internal_limit = max(top_k * 4, 60)          # over-fetch pool for re-scoring
semantic  = vector_store.search(query_vec, top_k=internal_limit)          → per-mem cosine in [0,1]
bm25_raw  = vector_store.keyword_search(lemmatize_for_bm25(query))        → raw BM25
entity    = _compute_entity_boosts(extract_entities(query))              → per-mem boost in [0, 0.5]

# BM25 → [0,1] via QUERY-LENGTH-ADAPTIVE logistic sigmoid (utils/scoring.py:16-54):
#   num_terms ≤3 → (midpoint 5.0, steepness 0.7);  ≤6 → (7.0,0.6);  ≤9 → (9.0,0.5)
#   ≤15 → (10.0,0.5);  else → (12.0,0.5)
#   bm25_norm = 1 / (1 + exp(-steepness*(raw - midpoint)))

# FUSION (score_and_rank):
#   gate FIRST on semantic: if semantic < threshold (default 0.1): DROP the candidate
#   raw_combined = semantic + bm25_norm + entity_boost
#   max_possible = 1.0  (+1.0 if any bm25)  (+0.5 if any entity)     ← ADAPTIVE divisor
#   combined = min(raw_combined / max_possible, 1.0)
#   sort desc, take top_k
```

The adaptive divisor is the clever bit: if a query produced no BM25 hits and no entities, the divisor stays 1.0 so a pure-semantic result isn't artificially deflated. `ENTITY_BOOST_WEIGHT = 0.5` (`scoring.py:57`) caps entity contribution at one third of the max-3-signal score.

**Entity boost** (`main.py:1440-1499`, `_compute_entity_boosts`): query NER (max 8 deduped entities) → for each, embed and search the **entity_store** (a separate vector collection of entity rows) `top_k=500`; keep matches with cosine ≥ 0.5; each matched entity carries `linked_memory_ids`, and each linked memory gets a boost:

```
num_linked = max(len(linked_memory_ids), 1)
memory_count_weight = 1.0 / (1.0 + 0.001 * (num_linked - 1)**2)     # spread attenuation
boost = similarity * 0.5 * memory_count_weight                       # ENTITY_BOOST_WEIGHT=0.5
# a memory keeps the MAX boost across all query entities
```

Spread attenuation means a popular entity ("User") that links to hundreds of memories contributes almost nothing per-memory (quadratic decay), while a rare entity ("Osteria Francescana" linking to 2 memories) gives near-full 0.5 boost. This is a genuinely smart cheap-IDF substitute that needs no corpus statistics.

### Entity store (replaces the old Neo4j graph in the default build)

**KNOWN** `main.py:413-535`, `:865-955`. The current OSS default has **no Neo4j**. Instead, entities are stored as their own vector rows (`entity_store`, a second collection) with payload `{data, entity_type, linked_memory_ids[], user_id/agent_id/run_id}`. NER is **spaCy** `get_nlp_full()` (`utils/entity_extraction.py:137-144`), producing 4 entity types: `PROPER, QUOTED, COMPOUND, NOUN`. Entity merge dedup is cosine ≥ **0.95** (`main.py:918`). This is a vector-only "poor man's knowledge graph" — adjacency lives in the `linked_memory_ids` array, not in graph edges. (Neo4j `mem0g` graph memory still exists in the platform/managed product and older OSS tags; the head OSS build folds it into vectors.)

### Scoping model — how user_id/agent_id/run_id compose

**KNOWN** `main.py:231-314` (`_build_filters_and_metadata`). At least one of `user_id`, `agent_id`, `run_id` is **required** (raises `VALIDATION_001` otherwise). Whichever are present are written into BOTH the storage metadata AND the query filter (AND-composed). `actor_id` is a **query-only** filter (precedence: explicit arg → `filters["actor_id"]`) — it narrows *who said it* within a session but is derived from message content at write time, not from the scope args. `_build_session_scope` (`:317-324`) builds a deterministic key by sorting `[agent_id, run_id, user_id]` and joining `key=val&...` — this is the buffer/last-messages partition key. `app_id` is a managed-cloud concept, not in OSS scope args.

There is no hierarchy/inheritance: scopes are flat AND-ed filter tags, not a tree. Agent-scoped writes (`agent_id` set, `user_id` absent) flip the extraction system prompt to `ADDITIVE_EXTRACTION_PROMPT + AGENT_CONTEXT_SUFFIX` (`main.py:724-727`) so facts are attributed to the assistant persona rather than the user.

### Constants (KNOWN)

| Constant | Value | Source |
|---|---|---|
| existing-memory retrieval top_k (write) | 10 | `main.py:712` |
| last-messages context | 10 | `main.py:703` |
| search over-fetch | `max(top_k*4, 60)` | `main.py:1356` |
| semantic gate threshold (default) | 0.1 | `main.py:1343` |
| `ENTITY_BOOST_WEIGHT` | 0.5 | `scoring.py:57` |
| entity-match dedup cosine | 0.95 | `main.py:918` |
| entity-boost min cosine | 0.5 | `main.py:1478` |
| entity-store search top_k (boost) | 500 | `main.py:1473` |
| query entities considered | first 8 | `main.py:1454` |
| dedup hash | md5(text) | `main.py:799` |
| spread-attenuation coeff | 0.001 (quadratic) | `main.py:1488` |
| NER | spaCy, types {PROPER,QUOTED,COMPOUND,NOUN} | `entity_extraction.py:134` |
| BM25 sigmoid (≤3 terms) | midpoint 5.0, steepness 0.7 | `scoring.py:31` |

### Agent-scoped extraction + AsyncMemory (KNOWN)

**KNOWN** `mem0/configs/prompts.py:947` (`AGENT_CONTEXT_SUFFIX`) + `mem0/memory/main.py:1795+` (`AsyncMemory`). When a write is agent-scoped (`agent_id` set, `user_id` absent), the extraction system prompt gets `AGENT_CONTEXT_SUFFIX` appended (verbatim): "The primary entity is an AI agent. Frame memories from the agent's perspective: user-stated facts → 'Agent was informed that [fact]'; agent actions → 'Agent recommended [X]'; configuration → 'Agent is configured to [behavior]'. The `attributed_to` field should still reflect the original source." So the SAME pipeline produces user-memory or agent-memory depending only on the scope args + this suffix — a clean way to give an agent its own self-model. The V3 prompt builder (`prompts.py:965+`) truncates each past message to `PAST_MESSAGE_TRUNCATION_LIMIT = 300` chars when assembling the extraction context (bounds prompt size). `AsyncMemory` mirrors `Memory` but wraps every blocking store/embed call in `asyncio.to_thread(...)` (`main.py:1859-1948`) so the whole add/search/entity-link pipeline is non-blocking — the design Verso needs for an async agent loop (don't block the event loop on a sync vector-store call).

### Procedural memory — run-trace summarization (KNOWN, directly relevant to Verso's durable-seam)

**KNOWN** `mem0/configs/prompts.py:326-408` (`PROCEDURAL_MEMORY_SYSTEM_PROMPT`), invoked by `_create_procedural_memory` (`main.py:1618`) when `memory_type="procedural_memory"` and `agent_id` is set. This is a *separate* write path from fact extraction: instead of extracting atomic facts, it summarizes an agent's last-N execution steps into a structured run trace. The prompt mandates (verbatim structure):
```
## Summary of the agent's execution history
**Task Objective**: <overall goal>
**Progress Status**: <% complete, milestones>
N. **Agent Action**: <precise action + all params/targets/methods>
   **Action Result (Mandatory, Unmodified)**: <exact unaltered output — JSON/HTML/errors verbatim>
   **Key Findings** / **Navigation History** / **Errors & Challenges** / **Current Context**
```
Hard rules: "**Every output produced by the agent must be recorded verbatim**"; "Do not paraphrase or summarize the output"; preserve exact URLs, element indexes, error messages, numeric counts ("3 out of 5 items processed"), and stack traces. This is precisely Verso's L1 run-trace requirement — it produces a single resumable procedural memory per run, where the unmodified action results are what let a checkpoint-resumed agent continue without re-executing. Verso should copy this prompt almost verbatim for its run-trace memory type.

### Proxy middleware — how memory hooks into the agent loop (KNOWN)

**KNOWN** `mem0/proxy/main.py:28-189`. The `Mem0`/`Chat`/`Completions` proxy wraps `litellm.completion` as a drop-in OpenAI-compatible client that transparently injects memory. On every `create()` whose last message is from `user` (`:106-110`):
1. **`_async_add_to_memory`** (`:154-166`) — fires `mem0_client.add(...)` on a **daemon thread** (fire-and-forget, non-blocking) so the write never delays the response.
2. **`_fetch_relevant_memories`** (`:168-179`) — searches with the **last 6 messages** joined as the query (`top_k` default 10), to bound query length.
3. **`_format_query_with_memories`** (`:181+`) — injects retrieved memories (and graph `relations` if present) into the last user message, prepending `MEMORY_ANSWER_PROMPT` as system if absent (`:149-152`).
This is the canonical "memory as a transparent LLM-proxy middleware" pattern: read-before, write-after-async, all inside one `completion()` call. Verso's agent loop should wire memory exactly here — search to assemble context pre-call, enqueue the write post-call on a background worker (never block the turn). Note `litellm.supports_function_calling(model)` is asserted (`:100`) since the underlying `add()` historically needed function calling.

### Metadata-filter query language (KNOWN)

**KNOWN** `mem0/memory/main.py:1239-1342` (`_process_metadata_filters`, `_has_advanced_operators`). Beyond the scope-id AND filters, `search()` accepts a structured operator language on arbitrary metadata, mapped to a universal form each vector store translates: `eq, ne, gt, gte, lt, lte, in, nin, contains, icontains` (`:24-28`). An unsupported operator raises `ValueError`. `_has_advanced_operators` detects whether a filter dict uses these (vs flat equality) to choose the query path. This is the data-model query surface — Verso's `recall()` should expose the same operator set so callers can filter memories by typed metadata (e.g. `{"confidence": {"gte": 0.8}, "tags": {"contains": "project-x"}}`) without dropping to raw SQL/Cypher.

### Storage + history schema (KNOWN)

**KNOWN** `mem0/memory/storage.py`. SQLite (default) `history` table is the append-only audit log:
```sql
CREATE TABLE history (id TEXT, memory_id TEXT, old_memory TEXT, new_memory TEXT,
                      event TEXT, created_at DATETIME, updated_at DATETIME, is_deleted INTEGER, ...)
```
Every `add`/`update`/`delete` writes a history row (`event ∈ {ADD,UPDATE,DELETE}`) — so even the additive V3 path keeps a full change log (`batch_add_history`, `main.py:856`). A `messages` table stores raw turns keyed by `session_scope` (`save_messages`, `get_last_messages`). The vector payload itself carries `{data, hash, text_lemmatized, created_at, updated_at, user_id/agent_id/run_id, actor_id, role, attributed_to}` (`main.py:808-816, 1408`). `search()` (public, `main.py:1126`) defaults `top_k=20`, `threshold=0.1`, requires ≥1 scope id, and composes scope ids as AND filters identical to the write path.

### Paper benchmarks (arXiv:2504.19413)

Mem0 paper reports **26% relative improvement over OpenAI memory on LOCOMO** (LLM-as-judge), with ~91% lower p95 latency and ~90% token savings vs full-context. The RE-target doc's 94.8% LongMemEval / 91.6% LoCoMo are the managed-cloud numbers; OSS-vector-only is far lower (the doc cites 29.07% LongMemEval-s under a Gemini-3 judge) — the gap is the entity-boost + additive pipeline + reranking that the cloud runs. The OSS head read here closes much of that gap (hybrid fusion + entity boost are now in OSS).

**For Verso:** Mem0's V3 pipeline is the single most directly copyable write loop for Verso.
1. **Adopt ADD-only as the default write policy.** Conflicting facts become new linked memories, never deletions. This is provably safer at scale (HydraDB §4.1) and Mem0 has now converged on it.
2. **Copy the integer-index anti-hallucination map** for any LLM-mutates-store operation — never let the model see or emit real UUIDs.
3. **Copy the additive fusion with adaptive divisor** (`semantic + bm25_norm + entity_boost`, divisor grows only with active signals) — it is simpler than RRF and avoids deflating pure-semantic hits. Gate on semantic *before* fusing.
4. **Copy the spread-attenuated entity boost** as a corpus-statistic-free IDF substitute: `1/(1+0.001*(n-1)²)`.
5. **Copy the query-length-adaptive BM25 sigmoid** rather than min-max normalizing BM25 against a moving corpus.
6. The vector-only entity store (`linked_memory_ids` arrays instead of graph edges) is the right default for Verso's "single pluggable backend" goal — it gives 80% of graph-memory value with zero Neo4j operational cost. Reserve a real graph backend (see Graphiti) for the temporal-reasoning tier.
7. **Copy the procedural-memory prompt almost verbatim for run-trace memory.** It is the closest existing artifact to Verso's L1 checkpoint requirement: structured numbered steps, action + *unmodified verbatim result*, progress %, errors, current context. The "never paraphrase the output" rule is what makes a trace resumable.
8. **Wire memory into the agent loop the way the proxy does:** search the last ~6 messages to assemble context *before* the LLM call, and enqueue the `add()` write on a background worker *after* — never block the turn on consolidation. Prepend a memory-answer system prompt, inject retrieved memories into the last user message.
9. **Keep a full append-only `history` log even under an additive policy.** Mem0 logs every event (ADD/UPDATE/DELETE) to a `history` table regardless of the write policy — Verso gets audit + time-travel for free without bi-temporal complexity.

---

## Graphiti (Zep)

### What It Is

Open-source temporal knowledge-graph engine that powers Zep's memory service. Every fact is an **edge** in a Neo4j/FalkorDB/Kuzu/Neptune graph, and every edge carries a **bi-temporal** model: when the fact was *recorded* (transaction time) and when it was *true in the world* (valid time). New facts never destroy old ones — a contradicting fact *invalidates* the prior edge by stamping its `invalid_at`/`expired_at`, leaving the history queryable. This is the reference implementation for "what was true, when did it change, why."

### Bi-temporal edge model (the durable-seam primitive)

**KNOWN** `graphiti_core/edges.py:263-285` (`EntityEdge`). Four timestamps per edge — this is the whole game:

```python
created_at:   datetime          # TRANSACTION time: when the system recorded this edge
expired_at:   datetime | None   # TRANSACTION time: when the system marked it invalidated
valid_at:     datetime | None   # VALID (event) time: when the fact became true in the world
invalid_at:   datetime | None   # VALID (event) time: when the fact stopped being true
reference_time: datetime | None # the source episode's timestamp that produced this edge
# plus: name (relation, SCREAMING_SNAKE_CASE), fact (NL sentence), fact_embedding, episodes[] (source episode uuids)
```

Two independent axes: `(created_at, expired_at)` is *system* knowledge ("when did WE learn / un-learn this"); `(valid_at, invalid_at)` is *world* knowledge ("when was it actually true"). A checkpoint-resume agent reconstructs state at past time `T` by querying edges where `valid_at ≤ T AND (invalid_at IS NULL OR invalid_at > T) AND created_at ≤ T_record`. The `EpisodicNode` (`nodes.py:318-348`) is the raw source unit; the `EntityNode` (`nodes.py:499-559`) holds `name_embedding` + `summary` ("regional summary of surrounding edges").

`[CORRECTION 2026-06-05]` The RE-target doc states "BGE-m3 embeddings at 1024-dim" and "last n=4 messages for NER context". Verified against current source: (a) the **OSS default embedder is OpenAI `text-embedding-3-small`** (`embedder/openai.py:24`), not BGE-m3 — BGE-m3 is one configurable option and the paper's reference config; `EMBEDDING_DIM` defaults to **1024** via env (`embedder/client.py:23`). (b) The NER/dedup context window is **`EPISODE_WINDOW_LEN = 3`** (`utils/maintenance/graph_data_operations.py:29`), not 4. (c) The BGE-m3 cross-encoder *reranker* is real: `BAAI/bge-reranker-v2-m3` (`cross_encoder/bge_reranker_client.py:36`).

### Write Loop — `add_episode()` pipeline

**KNOWN** `graphiti_core/graphiti.py:980-1223`. Per episode (one chat turn or JSON blob):

```
1. retrieve_episodes(reference_time, last_n=RELEVANT_SCHEMA_LIMIT=10)   # recent context (or explicit previous_episode_uuids)
2. extract_nodes(episode, previous_episodes, entity_types)             # LLM: NER → EntityNodes
3. resolve_extracted_nodes(...)                                        # LLM dedupe_nodes.nodes → uuid_map (merge into canonical entities)
4. _extract_and_resolve_edges(...):
     a. extract_edges  → EntityEdges (relation NER, SCREAMING_SNAKE relation_type, valid_at/invalid_at via DATETIME RULES)
     b. exact-dedup within batch on (src_uuid, tgt_uuid, normalize(fact))
     c. for each edge: search EXISTING (between same nodes) + INVALIDATION candidates (EDGE_HYBRID_SEARCH_RRF)
     d. resolve_extracted_edge → LLM returns {duplicate_facts:[idx], contradicted_facts:[idx]}
     e. resolve_edge_contradictions → set invalid_at/expired_at on contradicted edges by TEMPORAL ORDERING
5. extract_attributes_from_nodes(...)                                  # LLM: hydrate node summary + custom typed attributes
6. _process_episode_data(...)                                          # save EpisodicEdges (MENTIONS), entity edges, episode
7. (optional) update_community(...)                                    # incremental community/summary rollup
```

The whole thing is `async` with `semaphore_gather(max_coroutines=...)` — node-resolve, edge-resolve, and attribute extraction run concurrently. Bulk variant `add_episode_bulk` (`:1230+`) batches NER across episodes then dedupes globally.

### Conflict resolution — verbatim prompt + temporal arithmetic

This is the load-bearing mechanism. The LLM does **classification only** (which existing facts are duplicates, which are contradicted); the actual invalidation timestamps are computed in Python by comparing valid/invalid intervals — the LLM never gets to set `expired_at`.

**KNOWN — `resolve_edge` prompt, verbatim** (`prompts/dedupe_edges.py:43-99`):

```
SYSTEM: You are a fact deduplication assistant. NEVER mark facts with key differences as duplicates.
USER:
  NEVER mark facts as duplicates if they have key differences, particularly around numeric values, dates, or key qualifiers.
  IMPORTANT constraints:
  - duplicate_facts: ONLY idx values from EXISTING FACTS (NEVER include FACT INVALIDATION CANDIDATES)
  - contradicted_facts: idx values from EITHER list
  - idx values are continuous across both lists (INVALIDATION CANDIDATES start where EXISTING FACTS end)
  <EXISTING FACTS>{related_edges as [{idx, fact}]}</EXISTING FACTS>
  <FACT INVALIDATION CANDIDATES>{existing_edges as [{idx, fact}]}</...>
  <NEW FACT>{extracted_edge.fact}</NEW FACT>
  1. DUPLICATE DETECTION: identical factual information → return idx in duplicate_facts
  2. CONTRADICTION DETECTION: a fact can be BOTH duplicate AND contradicted (same relationship but updated/supersedes)
  EXAMPLE:
    idx=1 "Alice works at Acme Corp as a software engineer" / NEW "...as a senior engineer"
      → duplicate_facts=[], contradicted_facts=[1]   (same relationship, updated title — contradiction NOT duplicate)
    idx=2 "Bob ran 5 miles on Tuesday" / NEW "Bob ran 3 miles on Wednesday"
      → [],[]   (different events on different days — neither)
```

Response schema `EdgeDuplicate` (`dedupe_edges.py:24-32`): `{duplicate_facts: list[int], contradicted_facts: list[int]}`. The candidates are presented with **continuous integer indexing** across two lists with a computed offset (`invalidation_idx_offset = len(related_edges)`, `edge_operations.py:703`) — same anti-hallucination integer-index trick as Mem0.

**KNOWN — temporal invalidation arithmetic** (`resolve_edge_contradictions`, `edge_operations.py:538-573`). For each contradicted candidate edge:
```python
# SKIP (intervals don't overlap, no real conflict):
if (edge.invalid_at <= resolved.valid_at) or (resolved.invalid_at <= edge.valid_at): continue
# INVALIDATE the older edge:
elif edge.valid_at < resolved.valid_at:
    edge.invalid_at = resolved.valid_at                       # world-time: old fact stopped being true when new one started
    edge.expired_at = edge.expired_at or utc_now()            # system-time: we learned of expiry now
```
So a contradiction only invalidates the *prior* edge (older `valid_at`), and it sets the old edge's `invalid_at` to the new edge's `valid_at` — the timeline is stitched, not overwritten. The new edge is kept; the old edge remains in the graph, queryable, just bounded.

**KNOWN — edge date extraction prompt** (`prompts/extract_edges.py:168-175`, DATETIME RULES): ISO-8601 with `Z`; ongoing/present-tense → `valid_at = episode timestamp (or REFERENCE_TIME)`; change/termination expressed → set `invalid_at`; both `null` if no resolvable time; date-only → assume `00:00:00`; year-only → Jan 1 `00:00:00`. Crucially: "Do NOT hallucinate or infer temporal bounds from unrelated events."

### Retrieval — hybrid search + RRF fusion + pluggable rerankers

**KNOWN** `graphiti_core/search/`. Three parallel retrieval methods over edges, nodes, episodes, communities: (1) **cosine** vector similarity on `fact_embedding`/`name_embedding` (`min_score DEFAULT_MIN_SCORE = 0.6`, `search_utils.py:65`), (2) **full-text/BM25** (Neo4j Lucene), (3) **BFS graph traversal** from seed nodes. Results fused, then reranked.

**RRF (KNOWN, `search_utils.py:1780-1796`)** — note the unusual constant:
```python
def rrf(results: list[list[str]], rank_const=1, min_score=0):
    for result in results:
        for i, uuid in enumerate(result):
            scores[uuid] += 1 / (i + rank_const)        # rank_const = 1, NOT the canonical 60
```
Graphiti uses **k=1** in RRF (`1/(rank+1)`), which weights the top results far more aggressively than the textbook k=60. This is a deliberate small-candidate-set choice (search returns ~10–20 per method, not thousands).

**Reranker menu (KNOWN, `search_config.py:53-77` enums + recipes)** — five rerankers, selected per search config:
- `rrf` (default for every node/edge/episode/community search)
- `node_distance` — rerank by graph hops from a `center_node_uuid`; score = `1/shortest_path_len`, center gets 0.1 (`search_utils.py:1798-1857`)
- `episode_mentions` — rerank by `count(MENTIONS)` edges (popularity)
- `mmr` — maximal marginal relevance, `mmr_lambda = DEFAULT_MMR_LAMBDA = 0.5` (`search_utils.py:1901+`). Exact formula (`:1926-1930`): `mmr(d) = λ·cos(q,d) + (λ-1)·max_{d'≠d} cos(d,d')` over L2-normalized vectors — note `(λ-1)` is negative, so the second term is a *diversity penalty* (subtract the max similarity to any already-considered candidate). `min_score` default −2.0 for MMR (scores can go negative).
- `cross_encoder` — `BAAI/bge-reranker-v2-m3` (local) or OpenAI/Gemini LLM-as-reranker (`cross_encoder/`)

Pre-baked recipes: `COMBINED_HYBRID_SEARCH_RRF` / `_MMR` / `_CROSS_ENCODER` (`search_config_recipes.py:34,56,81`) search all four entity types at once. The edge-resolution write path itself uses `EDGE_HYBRID_SEARCH_RRF` (`edge_operations.py:398`) to find dedup + invalidation candidates — so retrieval fusion is reused inside the write loop.

**The invalidation persist (KNOWN, the actual Cypher).** When `resolve_edge_contradictions` stamps an old edge's `invalid_at`/`expired_at`, the change is written via the entity-edge save query (`models/edges/edge_db_queries.py:90-99`): a single `MERGE (n)-[e:RELATES_TO]->(m)` upsert that `SET`s `e.expired_at`, `e.valid_at`, `e.invalid_at`, `e.reference_time` alongside `fact`/`fact_embedding`/`episodes`. So invalidation is an in-place property update on the existing edge — the edge is NEVER deleted, only its temporal bounds are tightened. Cross-provider variants exist for Kuzu (relation-as-node), Neptune (string-encoded embeddings). This confirms the bi-temporal model is implemented as property mutation, not edge deletion + recreation — cheap, and the edge UUID is stable across invalidation (so `episodes[]` provenance survives).

### Node extraction (NER) + dedup prompts (KNOWN, verbatim)

**KNOWN — `extract_message` NER prompt** (`prompts/extract_nodes.py`). The entity extractor is aggressively constrained to avoid graph pollution. System: "You are an entity extraction specialist… NEVER extract abstract concepts, feelings, or generic words." The `NEVER extract` list (verbatim, abbreviated) bans: pronouns; abstract feelings (joy, balance, growth, resilience); generic common nouns (day, life, stuff, things, tickets, supplies); generic media nouns (photo, video, post) unless uniquely named; broad institutional nouns (government, school, company) unless named; sentence fragments; adjectives; **bare kinship/pet terms** — "extract 'Nisha's dad' not 'dad', 'Jordan's dog' not 'dog'". Pronouns must be disambiguated to the referenced entity's name. Output `ExtractedEntities{[{name, entity_type_id, episode_indices}]}` where `entity_type_id` is the integer index of a provided custom type. This possessor-qualification rule ("Nisha's dad") is the single biggest lever against a graph that fills with useless generic nodes — Verso must copy it.

**KNOWN — `dedupe_nodes` prompt** (`prompts/dedupe_nodes.py:25-101`). Entity resolution is integer-indexed (same anti-hallucination pattern): NEW ENTITY vs `[{candidate_id, name, entity_types, summary}]` → `NodeDuplicate{duplicate_candidate_id: int}` (`-1` if no match / unsure). System: "NEVER fabricate entity names or mark distinct entities as duplicates." Rules (verbatim examples): "NYC" + "New York City" → match (abbreviation); "Java"(language) + "Java"(Indonesian island) → -1 (same name, distinct things); "Marco's car" + "Marco's vehicle" → match (synonym, same possessor). The `resolve_extracted_nodes` step (`node_operations.py:627`) batches all new entities into `NodeResolutions{entity_resolutions:[...]}` and builds a `uuid_map` merging duplicates into the canonical node. `[CORRECTION 2026-06-05]` Earlier Graphiti had a "reflexion" missed-entity loop; the current head has **no reflexion** — extraction is single-pass, dedup is the only resolution step.

### Edge (fact) extraction prompt (KNOWN, verbatim core)

**KNOWN** `prompts/extract_edges.py:94-176` (`edge`). System: "You are an expert fact extractor that extracts fact triples from text. 1. Extracted fact triples should also be extracted with relevant date information. 2. The CURRENT_MESSAGE may contain multiple episodes, each with its own timestamp. Use each episode's timestamp to resolve temporal references within that episode. REFERENCE_TIME is a fallback." Input wraps `<PREVIOUS_MESSAGES>` (the last-3 episode window) + `<CURRENT_MESSAGE>` + optional `<FACT_TYPES>` (custom edge schemas). The EXTRACTION RULES (`:144-161`, verbatim-abridged) enforce: facts must connect two ENTITIES already extracted ("Nate plays games on a Gamecube" only if Gamecube ∈ ENTITIES); single-entity vague states are BAD ("Alice feels happy" → need "Alice feels happy about Bob's promotion"); no semantically-redundant facts across episodes, BUT a more-detailed later fact IS a new fact ("plays video games" → "plays games on a Gamecube" = extract the second); the `fact` MUST preserve every proper noun, brand, model number, quantity, color ("NEVER generalize 'Gamecube' to 'gaming console'"); `relation_type` is a matched FACT_TYPE or a derived `SCREAMING_SNAKE_CASE` predicate. This anti-generalization rule (shared with Mem0's additive prompt and Graphiti's NER) is the cluster-wide consensus: specificity is the highest-value property of an extracted memory.

### Community building — label propagation + summary rollup (KNOWN)

**KNOWN** `utils/maintenance/community_operations.py`. When `update_communities=True`, Graphiti clusters entities into `CommunityNode`s via **label propagation** (`label_propagation`, `:93-100`): every node starts as its own community, then iteratively adopts the plurality community of its neighbors, ties broken toward the largest community. Each community gets an LLM-generated `summary` (rolled up from member node summaries) and a `name_embedding`, so community-level search is possible. `MAX_COMMUNITY_BUILD_CONCURRENCY = 10`. This is Graphiti's GraphRAG-style hierarchical summarization layer — optional, built incrementally on `add_episode` rather than as a batch post-process. Verso's graph tier should treat community rollup as an opt-in async step, not a write-path cost.

### Scoping model

**KNOWN.** Graphiti partitions by **`group_id`** (a graph namespace string) on every node and edge; all search calls take `group_ids: list[str]`. There is no built-in user/agent/run taxonomy — `group_id` is the single tenancy axis (a Zep "user" maps to a `group_id`). This is coarser than Mem0's composable user/agent/run but maps cleanly onto Neo4j label-scoped indexes.

### Episode types + custom typed attributes (KNOWN)

**KNOWN** `graphiti.py:980+`, `nodes.py`. Input is a `RawEpisode` (the API ingestion unit) → persisted `EpisodicNode` with `source ∈ {message, text, json}` — so the SAME graph absorbs unstructured chat AND structured JSON through one pipeline (the `extract_json` vs `extract_message` vs `extract_text` prompt variants, `extract_nodes.py:62-67`). Custom entity/edge **types are Pydantic models** passed as `entity_types: dict[str, type[BaseModel]]` / `edge_types`; after dedup, `extract_attributes` (a `ModelSize.small` LLM call) fills the typed fields, and `apply_capped_attributes` (`edge_operations.py:669`) merges them with `merge_mode='replace'`. The `edge_type_map: dict[(src_label, tgt_label), [type_names]]` constrains which relation types are legal for which node-type pairs — a typed schema over the graph. Verso's typed-memory API can adopt this exactly: user supplies Pydantic schemas, the framework extracts into them with a cheap model.

### Constants (KNOWN)

| Constant | Value | Source |
|---|---|---|
| `EPISODE_WINDOW_LEN` (NER context) | 3 | `graph_data_operations.py:29` |
| `RELEVANT_SCHEMA_LIMIT` | 10 | `search_utils.py:64` |
| `DEFAULT_SEARCH_LIMIT` | 10 | `search_config.py:29` |
| `DEFAULT_MIN_SCORE` (cosine gate) | 0.6 | `search_utils.py:65` |
| `DEFAULT_MMR_LAMBDA` | 0.5 | `search_utils.py:66` |
| RRF `rank_const` (k) | **1** | `search_utils.py:1780` |
| `EMBEDDING_DIM` | 1024 (env) | `embedder/client.py:23` |
| default embedder | OpenAI `text-embedding-3-small` | `embedder/openai.py:24` |
| cross-encoder reranker | `BAAI/bge-reranker-v2-m3` | `bge_reranker_client.py:36` |
| edge-resolve LLM model_size | small | `edge_operations.py:729` |

### Paper (arXiv:2501.13956)

Zep/Graphiti reports SOTA on the Deep Memory Retrieval (DMR) benchmark (94.8% vs MemGPT 93.4%) and large latency reductions vs full-context. The temporal model is the contribution: bi-temporal edges + LLM-driven invalidation that preserves history. (Note the RE-target doc's Zep LongMemEval-s 71.2% is a judge-confounded number; the paper's DMR result is the apples-to-apples claim.)

**For Verso:** Graphiti is the reference for Verso's *durable-seam temporal tier*.
1. **Adopt the four-timestamp bi-temporal edge** (`created_at, expired_at, valid_at, invalid_at`) as the schema for any fact Verso must time-travel. This is exactly what checkpoint-resume needs: reconstruct state at past `T` with one interval query, no event replay.
2. **Separate LLM classification from timestamp arithmetic.** The LLM only labels `duplicate`/`contradicted` by integer index; Python computes the invalidation timestamps from interval ordering. Never let the model write `expired_at` — it will hallucinate dates.
3. **Invalidation, not deletion.** A contradiction stamps the old edge's `invalid_at = new.valid_at` and keeps it. This is the audit-grade version of Mem0's ADD-only policy — Verso's compliance/healthcare tier needs this, the chat tier can use Mem0's lighter version.
4. **Copy the continuous-integer-index candidate presentation** (offset between two lists) — identical to Mem0's anti-hallucination map.
5. **RRF with k=1 for small candidate sets.** Verso's graph retrieval returns tens, not thousands, of candidates — the textbook k=60 over-flattens. Use k=1.
6. **Pluggable reranker as a config enum** (rrf / node_distance / episode_mentions / mmr / cross_encoder) is the right shape for Verso's `recall(rerank=...)` knob. `node_distance` (rerank by hops from a focus entity) is unique to graph memory and worth exposing.
7. `group_id` single-axis tenancy is too coarse for Verso — prefer Mem0's composable user/agent/run, but borrow Graphiti's "namespace string is also the index partition key" implementation detail.

---

## Hindsight (vectorize.io)

### What It Is

Agent memory system whose defining choice is **a single PostgreSQL instance for ALL memory operations** — vectors in pgvector, BM25 in pgroonga/tsvector, graph as adjacency rows, temporal as date columns. No Milvus, no Neo4j, no Redis on the hot path. It proves a single-DB stack reaches near-SOTA (91.4% LongMemEval with a large backbone, arXiv:2512.12818). The retrieval is **TEMPR**: four parallel arms (semantic + BM25 + graph + temporal) fused via RRF, then cross-encoder reranked with multiplicative recency/temporal/proof boosts.

### Epistemic taxonomy + `memory_units` schema (KNOWN)

**KNOWN** `alembic/versions/5a366d414dce_initial_schema.py:265-305`. The whole memory is one table:

```sql
CREATE TABLE memory_units (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bank_id TEXT NOT NULL,                    -- tenancy axis (one "bank" = one user/agent isolation unit)
  document_id TEXT,                         -- FK → documents(id, bank_id) ON DELETE CASCADE
  text TEXT NOT NULL,
  embedding Vector(384),                    -- pgvector; default dim 384 (small ST model)
  context TEXT,
  event_date TIMESTAMPTZ NOT NULL,          -- primary temporal anchor
  occurred_start TIMESTAMPTZ,               -- event validity window start
  occurred_end TIMESTAMPTZ,                 -- event validity window end
  mentioned_at TIMESTAMPTZ,                 -- when the fact was learned/said (transaction-ish time)
  fact_type TEXT NOT NULL DEFAULT 'world',  -- CHECK IN ('world','bank','opinion','observation')
  confidence_score FLOAT,                   -- REQUIRED for opinion, NULL for world/bank
  access_count INTEGER NOT NULL DEFAULT 0,  -- frequency signal for boosting
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ
);
-- CHECK: fact_type IN ('world','bank','opinion','observation')
-- CHECK: opinion ⟹ confidence_score NOT NULL ; world/bank ⟹ confidence_score NULL
```

The four **fact_type**s are the epistemic taxonomy (paper's "world facts / experiences / entity summaries / evolving beliefs" map onto these): `world` = objective external facts, `bank`/`experience` = first-person agent actions, `opinion` = belief with required `confidence_score ∈ [0,1]`, `observation` = consolidated/synthesized knowledge with a `proof_count`. The triple temporal columns (`occurred_start/end` for world-validity, `mentioned_at` for learned-time, `event_date` anchor) are a lighter bi-temporal model than Graphiti's four-timestamp edges.

**ANN index is pluggable in-SQL** (`:87-94`): `diskann (num_neighbors=50)` / `vchordrq` / `scann (mode=AUTO)` / `hnsw` — chosen by which pgvector extension is installed. BM25 is `tsvector` by default, swapped to **pgroonga** at startup (`ensure_text_search_extension()` drops the tsvector column and builds a pgroonga index). This is the entire "polyglot stack in one Postgres" thesis made concrete.

### Write Loop — `retain()` (KNOWN)

**KNOWN** `engine/retain/orchestrator.py` + `fact_extraction.py`. Pipeline:
```
chunk → LLM fact extraction (5W schema) → entity resolution → embed → store memory_units → create graph links
```
The **fact extraction schema is 5W** (`fact_extraction.py:177-200`, `ExtractedFact`): `what` (1-2 sentence core fact), `when`, `where`, `who` (people + relationships), `why` (significance), plus `fact_type ∈ {world, assistant}`, `fact_kind ∈ {event, conversation}`, `occurred_start/end`, `entities[]`, and `causal_relations[]` (links to a previous fact by `target_index < this index` — intra-batch causal DAG). `build_fact_text()` (`:215`) concatenates `what | Involving: who | why` into the embedded text. Multiple verbosity modes exist (`ExtractedFactVerbose` instructs "Include EVERYTHING: feelings, preferences, motivations…"). Like Mem0, the write is **additive** — no destructive update in the retain hot path; consolidation/dedup is deferred to async graph maintenance (`graph_maintenance.py`) and `reflect()`.

### Retrieval — TEMPR fusion math (KNOWN, the headline finding)

**Stage 1 — four parallel arms** (`engine/search/retrieval.py:40-48`, `ParallelRetrievalResult`): `semantic`, `bm25`, `graph` (link-expansion BFS over `memory_links`), `temporal` (date-window from extracted query temporal constraint). Semantic over-fetches **5× (min 100)** because HNSW is approximate, then trims in Python (`retrieval.py:117`). Each arm is `cap_per_source`-capped before fusion so one over-expanding arm can't crowd out others (`fusion.py:10-28`).

**Stage 2 — RRF fusion** (`fusion.py:31-98`), canonical k=60:
```
rrf_score(d) = Σ_arms  1 / (60 + rank_arm(d))        # arms: [semantic, bm25, graph, temporal]
```
An alternative **interleave_fusion** (`fusion.py:101-158`) exists specifically for the consolidation-dedup path: RRF averages down a doc that is #1 in one arm but absent elsewhere (the "twin to merge into" failure), so interleave round-robins each arm's #1, then #2, … guaranteeing every arm's top hit a slot. This is a genuinely sharp insight worth stealing.

**Stage 3 — per-strategy recall boost** (`recall_boost.py:69-71`), applied in TWO places:
```
LEVELS = { low:  BoostWeights(rrf=1.0, additive=0.05),
           medium:BoostWeights(rrf=3.0, additive=0.2),
           high: BoostWeights(rrf=6.0, additive=0.5) }
# (a) before reranker cap: boosted_rrf = rrf_score + level.rrf * 1/(60+rank)   ← rank-aware, protects top of a prioritized arm
# (b) after reranker:      weight += level.additive                            ← flat bump in [0,1] post-CE space
```
This lets a caller say "prioritize graph results" and have it survive both the candidate-pool cutoff AND the final cross-encoder ordering.

**Stage 4 — cross-encoder rerank + multiplicative boosts** (`reranking.py:12-130`, `apply_combined_scoring`). Default CE model **`cross-encoder/ms-marco-MiniLM-L-6-v2`** (`reranking.py:138`; alternatives via env: FlashRank/ONNX, Cohere, Google, LiteLLM, jina-reranker-v3-mlx on Apple Silicon). Final score:
```
recency      = clamp(1 - days_ago/365, 0.1, 1.0)        # linear decay over a year, neutral 0.5 if no date
temporal     = retrieval.temporal_proximity or 0.5      # only set by the temporal arm
proof_norm   = clamp(0.5 + log(proof_count)/10, 0, 1)   # observation evidence strength, neutral 0.5
recency_boost     = 1 + 0.2 * (recency    - 0.5)        # _RECENCY_ALPHA   = 0.2  → ±10%
temporal_boost    = 1 + 0.2 * (temporal   - 0.5)        # _TEMPORAL_ALPHA  = 0.2  → ±10%
proof_count_boost = 1 + 0.1 * (proof_norm - 0.5)        # _PROOF_COUNT_ALPHA = 0.1 → ±5%
combined_score    = CE_normalized * recency_boost * temporal_boost * proof_count_boost
```
The CE score is the **primary relevance signal**; recency/temporal/proof are bounded *multiplicative* nudges (max ±10/±10/±5%) — they re-rank within a relevance band, never override it. Edge case (`reranking.py:71-98`): if every CE score is identical (degenerate/slim deployment), CE is reseeded from RRF rank mapped to `[0.1, 1.0]` so the result isn't a pure recency sort.

### Tag-match modes (KNOWN)

**KNOWN** `engine/search/tags.py:6-46`. Hindsight's tag filter has four modes with explicit untagged-handling semantics: `any` (OR, includes untagged — default), `all` (AND, includes untagged), `any_strict` (OR, excludes untagged), `all_strict` (AND, excludes untagged). `_parse_tags_match` resolves `(operator, include_untagged)`; `build_tags_where_clause` emits the SQL. The untagged-inclusion flag is the subtle bit: by default an untagged memory still matches any tag query (so tagging is additive-precision, not a hard gate), but `_strict` modes exclude untagged memories entirely. Verso's tag filter should expose this same any/all × strict/non-strict matrix — the "does an untagged item match a tag query" decision is a real product choice most systems get implicitly wrong.

### `reflect()` — belief synthesis as an agentic loop (KNOWN)

**KNOWN** `engine/reflect/agent.py` + `tools_schema.py` + `prompts.py`. Reflect is NOT a single LLM call — it's an agentic ReAct loop (`DEFAULT_MAX_ITERATIONS = 10`, `agent.py:49`) with native tool calling and a **hierarchical retrieval contract**: tools `search_mental_models` (consolidated beliefs), `search_observations` ("consolidated knowledge with freshness"), `recall` (raw facts), `expand` (graph neighborhood), `done`. The system prompt (`prompts.py:96+`) forces `search_mental_models` FIRST, then `search_observations`, then raw `recall` only if needed — beliefs before evidence ("if a relevant mental model exists and is FRESH, it may fully answer the question"). The `done` tool can carry a directive-compliance field. `_FINAL_PROMPT_CONTEXT_FRACTION = 0.8` budgets context for the final synthesis. Output is written back as `observation`/`mental_model` rows, which then score in future recalls via the `proof_count` boost. This is exactly Verso's "memory improves between runs" durable-seam loop.

### Read-time conflict resolution — the temporal rule (KNOWN, the standout finding)

**KNOWN** `engine/reflect/prompts.py:170-206`. Because Hindsight's write loop is **additive** (no write-time invalidation, unlike Graphiti), conflicts are resolved at **read time** by the reflect prompt — a remarkably detailed, auditable procedure injected into the synthesis LLM:
```
## Temporal Reasoning (verbatim, abridged)
Every memory carries: mentioned_at (when retained, always set), occurred_start/occurred_end (when the event happened).
When facts about the SAME facet conflict (counts, statuses, ownership, location...):
  the fact with the LATEST mentioned_at is AUTHORITATIVE. Later statements SUPERSEDE earlier ones.
  Do NOT average, sum, or favor an explicitly-dated fact over a more recent one.
Example: "2 engineers"(T1) / "now 1 engineer"(T2) / "5 engineers"(T3), T1<T2<T3 → current = 5, not 1.
For a TIMELINE, order by occurred_start/end (when things happened), NOT mentioned_at (when retained).

## Showing Your Reasoning (forced chain-of-thought for any conflict resolution)
1. List relevant facts in mentioned_at order (oldest→newest) with asserted value.
2. Identify the authoritative fact (latest mentioned_at). Write its date.
3. List candidate events to apply on top (each with its date).
4. For EVERY event: "<event>(<date>) vs authoritative(<date>) → BEFORE/AFTER → KEEP/DROP".
   If event ≤ authoritative date, DROP it — it's already reflected; re-applying = double-counting.
   "This is the single most common mistake — do not skip this step."
5. Show arithmetic using only KEEP events: "auth count = 5 (2025-02-12); kept: Shadow died (2025-03-12, AFTER); 5−1=4".
6. If no clean winner → STOP, surface as UNRESOLVABLE ambiguity (name conflicting facts, give a range, never fabricate).
```
This is the most sophisticated conflict-resolution logic in the whole cluster, and it lives entirely in the *read* path. The contrast is sharp: **Graphiti resolves conflicts at write time (invalidate the edge); Hindsight defers to read time (latest `mentioned_at` wins, with a double-counting guard).** Verso should understand this as the fundamental fork — write-time invalidation (audit-clean store, expensive writes) vs read-time resolution (cheap additive writes, expensive reads + a strict prompt). For Verso's checkpoint-resume, write-time (Graphiti) is better for reconstructing past state; for high-write chat, read-time (Hindsight) is cheaper. The "double-counting guard" (step 4) is copyable verbatim into any read-time-resolution prompt.

### The "graph" arm — three link types in `memory_links` (KNOWN, this is how a single Postgres does graph memory)

**KNOWN** `engine/search/link_expansion_retrieval.py:4-22` + `engine/retain/link_creation.py`. There is no graph DB — the graph is a `memory_links` table plus a `unit_entities` join, expanded at query time from semantic/temporal seeds through **three first-class signals**:
```
1. Entity links  : query-time self-join through unit_entities. score = COUNT(DISTINCT shared entity_id)
                   between seed set and candidate. LATERAL per-entity cap graph_per_entity_limit=200
                   to stop high-fanout entities ("User") from exploding the join.
2. Semantic links: precomputed kNN graph — at INSERT each new fact is linked to its top-5 most-similar
                   existing facts with similarity >= 0.7 (asymmetric, checked both directions). score = weight.
3. Causal links  : explicit chains (causes / caused_by / enables / prevents) from the 5W extraction's
                   causal_relations. score = weight + 1.0  (boosted as highest-quality signal).
```
For non-observation fact types all three expansions run as **one CTE query** (one roundtrip) with a `source` discriminator column. A `graph_expansion_timeout` fallback drops entity expansion if over budget. This is the concrete proof that "graph memory" needs no Neo4j: precompute a kNN edge at insert, store causal edges from extraction, and self-join entities at query time. Verso's no-graph-DB tier should copy this exactly — it is cheaper to operate than Graphiti's Neo4j and covers entity/semantic/causal adjacency.

### Entity resolution + write phases (KNOWN)

**KNOWN** `engine/retain/entity_processing.py:52-90`, `orchestrator.py`. `retain` is phased: Phase 1 **`resolve_entities`** (read-heavy) maps extracted entity names to canonical entity IDs (the `entities` table, with a case-insensitive trigram index — `2eee35aa3cfc_case_insensitive_entities_trgm_index`), building `entity_to_unit` / `unit_to_entity_ids` maps; Phase 2 stores facts; Phase 3 batch-creates the temporal/semantic/causal links. Entity canonicalization via pg_trgm similarity (not embeddings) is a cheap dedup that avoids an LLM call per entity — contrast Mem0's 0.95-cosine entity merge and Graphiti's LLM dedup. For high-volume Verso writes, trigram entity resolution is the cheapest tier.

### Mental models — consolidated beliefs as `memory_units` rows (KNOWN)

**KNOWN** `alembic/versions/p1k2l3m4n5o6_new_knowledge_architecture.py:12-17, 103-106`. The architecture collapsed separate `learnings`/`mental_models` tables into `memory_units` with `fact_type='mental_model'` plus three columns: **`proof_count`** (how many observations support this belief → drives the proof_count_boost in reranking), **`source_memory_ids UUID[]`** (provenance — which raw memories consolidated into this belief; GIN-indexed for expansion), and **`history`** (prior versions). `reflections` (renamed from `pinned_reflections`) are user-curated belief documents. So a belief is just a typed memory_unit that points back at its evidence — the same table, queried by `fact_type`. This unifies raw facts and synthesized beliefs in one store, scored together, which is cleaner than MemOS's separate tiers for the single-DB case.

### Scoping model

**KNOWN.** Single axis: **`bank_id`** (TEXT) on every row — `documents`, `memory_units`, `entities`, `memory_links` all carry it; the per-bank vector index is built **per `bank_id`** (`bank_utils.py:48`, `create_bank_vector_indexes` — each bank gets its own ANN index, bank_id SQL-escaped). A bank = one isolation unit (user or agent). Coarser than Mem0's composable triple, but the FK cascades (`memory_units.document_id → documents` ON DELETE CASCADE) give clean per-bank teardown, and per-bank indexes mean one tenant's growth never degrades another's recall.

### Constants (KNOWN)

| Constant | Value | Source |
|---|---|---|
| embedding dim | 384 | `5a366d414dce:271` |
| RRF k | 60 | `fusion.py:31` |
| semantic over-fetch | 5× (min 100) | `retrieval.py:117` |
| `_RECENCY_ALPHA` | 0.2 (±10%) | `reranking.py:15` |
| `_TEMPORAL_ALPHA` | 0.2 (±10%) | `reranking.py:16` |
| `_PROOF_COUNT_ALPHA` | 0.1 (±5%) | `reranking.py:17` |
| recency decay window | 365 days → [0.1,1.0] | `reranking.py:108` |
| boost levels (rrf/additive) | low 1.0/0.05, med 3.0/0.2, high 6.0/0.5 | `recall_boost.py:69-71` |
| reflect max iterations | 10 | `agent.py:49` |
| default cross-encoder | `cross-encoder/ms-marco-MiniLM-L-6-v2` | `reranking.py:138` |
| diskann num_neighbors | 50 | `5a366d414dce:87` |
| `graph_per_entity_limit` (LATERAL cap) | 200 | `link_expansion_retrieval.py:14` |
| semantic-link kNN | top-5, sim ≥ 0.7 (at insert) | `link_expansion_retrieval.py` |
| causal-link score boost | weight + 1.0 | `link_expansion_retrieval.py` |
| entity canonicalization | pg_trgm (case-insensitive) | `entities trgm index` |
| mental-model columns | proof_count, source_memory_ids[], history | `p1k2l3m4n5o6:103` |

**For Verso:** Hindsight is the single most important reference for Verso's **pluggable-single-backend** decision.
1. **A single Postgres can be the entire memory backend.** pgvector (diskann/hnsw/vchordrq/scann) + pgroonga BM25 + adjacency-row graph + date-column temporal. Near-SOTA without a polyglot ops burden. This is the right default for Verso's pluggable backend — reserve Neo4j (Graphiti) only for the temporal-reasoning tier.
2. **Adopt the four-arm TEMPR retrieval** (semantic / bm25 / graph / temporal) with **canonical RRF k=60** for large candidate pools (contrast Graphiti's k=1 for small pools — pick k by pool size).
3. **Steal `interleave_fusion` for the dedup/consolidation path.** RRF systematically drops the near-duplicate twin you most need to see during merge; round-robin guarantees each arm's #1 a slot.
4. **Adopt multiplicative bounded boosts** (CE relevance × recency × temporal × proof, each ±5–10%) rather than additive weighted sums — boosts re-rank within a relevance band and can never let a stale-but-recent fact outrank a strong match. Copy the degenerate-CE-reseed guard.
5. **Adopt the epistemic `fact_type` taxonomy** (`world / experience / opinion+confidence / observation+proof_count`) as Verso's typed-memory enum — it's cleaner than a flat fact list and the `confidence`/`proof_count` columns drive scoring for free.
6. **`reflect()` as a hierarchical-retrieval agentic loop** (beliefs → observations → raw facts, max 10 iters, write synthesized beliefs back) is the template for Verso's between-run consolidation.

---

## Honcho (Plastic Labs)

### What It Is

FastAPI + Postgres/pgvector memory service whose two distinguishing ideas are (1) a **peer-symmetric identity model** — both humans and AIs are "peers," and memory is keyed by *who observes whom* — and (2) a **two-stage async cognition pipeline**: a fast synchronous-ish *deriver* extracts atomic observations off the request path, and a slow background *dreamer* consolidates them into higher-level structure using geometric **surprisal** sampling. 90.4% LongMem.

### Peer-symmetric scoping — the `(observer, observed)` key (KNOWN)

**KNOWN** `src/models.py:130-441`. Hierarchy: `Workspace → Peer / Session → Message`. Memory itself lives in `Collection` and `Document` rows that are **not** keyed by a single `user_id` — they are keyed by a pair:
```python
class Collection / Document:
    observer: str   # the peer doing the observing  (could be an AI peer)
    observed: str   # the peer being observed        (could be a human peer)
    workspace_name: str
    # composite FKs to peers(name, workspace_name) for BOTH observer and observed
```
So "what Agent-A believes about User-B" and "what User-B believes about Agent-A" are distinct, symmetric memory partitions. There is no privileged "user" — a `Peer` is just an identity, and any peer can observe any other. This is strictly more expressive than Mem0's `user_id`/`agent_id` flat tags (which can't represent agent-observes-agent or multi-party theory-of-mind) and is the model Verso should study for multi-agent sessions.

### Deriver — fast observation extraction (KNOWN)

**KNOWN** `src/deriver/`. A background worker (`consumer.py` polls a queue; `POLLING_SLEEP_INTERVAL` with exponential backoff toward a max, snapping back when work appears) pulls message batches and runs ONE LLM call per batch (`deriver.py:37-296`). It produces a `Representation` with two observation classes (`deriver.py:233`): **`explicit`** (facts derivable directly from the peer's messages) and **`deductive`** (inferred via general knowledge). The minimal extraction prompt (`prompts.py:39-82`, verbatim core):
```
Analyze messages from {peer_id} to extract **explicit atomic facts** about them.
[EXPLICIT] DEFINITION: Facts derivable directly from their messages.
  - Transform statements into one or multiple conclusions; each self-contained with context
  - Use absolute dates/times ("June 26, 2025" not "yesterday")
RULES:
  - Attribute to the correct subject (about {peer_id}? or {peer_id} referencing someone else?)
  - Contextualize sufficiently: "Ann is nervous about the job interview at the pharmacy" not "Ann is nervous"
EXAMPLES:
  "I just had my 25th birthday last Saturday" → "{peer_id} is 25 years old", "{peer_id}'s birthday is June 21st"
  "I took my dog for a walk in NYC"            → "{peer_id} has a dog", "{peer_id} lives in NYC"
```
Observations are saved as `Document` rows (embedded, dim 1536 — `surprisal.py:362`) via `RepresentationManager.save_representation` scoped to `(observer, observed)`. This runs **off the request path** — the agent responds immediately; consolidation lags. That async-decouple is the pattern Verso's durable-seam needs: respond now, consolidate before next run.

### Dreamer — surprisal-driven consolidation (KNOWN, the novel piece)

**KNOWN** `src/dreamer/`. The "dreaming" loop is a *deferred* background consolidation triggered by accumulation, not by every turn:
- **Trigger** (`config.py:1168-1170`): `DOCUMENT_THRESHOLD = 50` new observations since last dream, AND `MIN_HOURS_BETWEEN_DREAMS = 8`. `DreamScheduler.schedule_dream` (`dream_scheduler.py:54`) debounces with a delay and cancels stale scheduled dreams when new observations for the same `(observer, observed)` arrive.
- **Surprisal sampling** (`surprisal.py:46-170`): instead of consolidating everything, it picks the *novel* observations. Steps: fetch observations with embeddings → `_build_tree(embeddings)` (a `SurprisalTree` — cover tree / RP tree / LSH / sklearn KNN, `trees/`) → `tree.surprisal(embedding)` = geometric novelty (distance to existing neighbors) → normalize to [0,1] → sort desc → keep `TOP_PERCENT_SURPRISAL = 0.10` (top 10%). Min observations gate before computing. Hybrid mode: `MIN_HIGH_SURPRISAL_FOR_REPLACE = 10` high-surprisal obs replace standard reflection questions.
- **Specialists** (`specialists.py`): agentic consolidators (`BaseSpecialist` with tools, model config) that turn the surprising observations into higher-level structure.

The insight: an agent's most valuable memories to consolidate are the *surprising* ones (far from the existing cluster manifold), not the redundant ones. Spending LLM budget on the top-10%-novel observations is a principled cost control — and a directly transferable idea for Verso's between-run consolidation budget.

### Observation taxonomy — four reasoning types with provenance (KNOWN)

**KNOWN** `src/utils/representation.py:59-111`. A `Representation` (the deriver's output) carries four observation classes, each with `source_ids` (document IDs of supporting observations, enabling **tree traversal** back to evidence):
```
ExplicitObservation     : {content}                                  — derivable directly from messages
DeductiveObservation    : {premises[], source_ids[], conclusion}     — logical inference from explicit facts
InductiveObservation    : {sources[], source_ids[], pattern_type, conclusion, confidence}
                            pattern_type ∈ {preference, behavior, personality, tendency, correlation}
                            confidence   ∈ {high, medium, low}
ContradictionObservation: {source_ids[], ...}                        — conflicting statements flagged, not deleted
```
This is a richer epistemic model than Hindsight's flat `fact_type`: it separates *what was said* (explicit) from *what was reasoned* (deductive/inductive) and records the premise chain (`source_ids`) so a belief can be traced to its evidence — and a **contradiction is a first-class observation**, not a deletion. Verso's typed memory should adopt this: explicit/deductive/inductive with a premise-chain field, plus an explicit contradiction type that surfaces conflicts to the agent rather than silently resolving them.

### Async pipeline — queue, task types, schedulers (KNOWN)

**KNOWN** `src/deriver/consumer.py`, `queue_manager.py`. A single `QueueItem(task_type, payload, workspace_name)` queue multiplexes task types: `representation` (deriver extraction batch), `dream` (consolidation), `reconciler` (cleanup/merge), `webhook`, `summary`. The consumer polls with exponential backoff (`POLLING_SLEEP_INTERVAL` → `POLLING_SLEEP_MAX` × `POLLING_BACKOFF_MULTIPLIER`, snap-back on work; `POLLING_STARTUP_JITTER` to desynchronize workers). The `DreamScheduler` and `ReconcilerScheduler` are process-singletons that debounce/cancel scheduled work. So Honcho's whole cognition layer is one prioritized work queue feeding three async stages (derive → reconcile → dream) — the clean async-worker topology Verso's durable-seam needs (respond now; derive/reconcile/dream off the request path).

### Retrieval — the dialectic path (two query modes)

**KNOWN** `src/dialectic/prompts.py:6-236`. Recall isn't a raw vector query — the "dialectic" endpoint takes a natural-language question about a peer and synthesizes an answer via an **agentic loop with search tools** over the `(observer→observed)` observations. Two modes (`agent_system_prompt`): **directional** ("`{observer}` wants to know about `{observed}`" — theory-of-mind, what one peer knows about another) and **global** (omniscient view of the peer). The prompt mandates: analyze what the query demands → do MULTIPLE searches with different terms for coverage → stop calling tools once an explicit answer is found → synthesize (no tool-usage explanation in the output). **Peer cards** are constructed summaries synthesized from the same observation store (not a separate source). So recall = "ask a question about a peer," answered by an agent that searches the observation store — closer to Hindsight's `reflect()` than Mem0's `search()`. Verso should offer this directional-vs-global distinction for multi-agent theory-of-mind queries.

### Pluggable vector store + reconciler (KNOWN, cross-links `infra-vector-memory.md`)

**KNOWN** `src/vector_store/`. Honcho abstracts vector storage behind a `VectorStore` ABC (`__init__.py:53`) with two concrete backends: **`lancedb.py`** and **`turbopuffer.py`** — exactly the two stores reverse-engineered in the companion `infra-vector-memory.md`. So Honcho is a live example of the cognition layer (deriver/dreamer) sitting on top of an interchangeable storage primitive. `VectorRecord`/`VectorQueryResult{score}` ("lower = more similar for cosine distance"); namespaces are content-hashed (`_hash_namespace_components`) from the `(observer, observed, ...)` scope. The **reconciler** (`src/reconciler/scheduler.py`) runs a `reconciler:sync_vectors` work unit that keeps the relational `Document` rows and the vector-store namespace in sync — the relational DB is source of truth, the vector store is a derived index that can be rebuilt. Verso should adopt this same split: Postgres rows are authoritative, the ANN index (LanceDB/Turbopuffer/pgvector) is a reconcilable derived view, and a background reconciler heals drift.

### Constants (KNOWN)

| Constant | Value | Source |
|---|---|---|
| observation embedding dim | 1536 | `surprisal.py:362` |
| `DREAM.DOCUMENT_THRESHOLD` | 50 | `config.py:1168` |
| `DREAM.MIN_HOURS_BETWEEN_DREAMS` | 8 | `config.py:1170` |
| `SURPRISAL.TOP_PERCENT_SURPRISAL` | 0.10 | `config.py:1152` |
| `SURPRISAL.MIN_HIGH_SURPRISAL_FOR_REPLACE` | 10 | `config.py:1156` |
| deriver queue flush threshold | 50 | `config.py:1094` |
| deriver poll backoff | exponential, snap-back on work | `config.py:749-754` |
| scoping key | `(observer, observed, workspace)` | `models.py:339-372` |

**For Verso:**
1. **Adopt the peer-symmetric `(observer, observed)` scoping** for multi-agent memory. It is the only model here that represents "what agent A believes about agent B" without a privileged user role — essential for Verso's multi-agent coordination story. Mem0's flat tags are a degenerate special case (observer = system).
2. **Two-stage async cognition: fast deriver (off request path) + slow dreamer (accumulation-triggered).** Verso's durable-seam should respond immediately, enqueue observation extraction, and run consolidation only when `N` observations accumulate AND a min interval has passed — never block the agent on consolidation.
3. **Surprisal-gated consolidation is the budget-control idea worth copying.** Build a tree over observation embeddings, consolidate only the top-10% most novel (highest distance-to-neighbors). This is principled spend control for the consolidation LLM, far better than "consolidate everything every N turns."
4. **Recall as a synthesized answer (dialectic), not raw top-k** — matches Hindsight's `reflect()`; Verso should offer both a cheap `search()` and an expensive `ask-about-peer` mode.

---

## Cognee

### What It Is

A memory "control plane" whose value to Verso is two things: a **pluggable-backend abstraction** (graph engine = NetworkX / Neo4j / Kuzu / Memgraph / Neptune / Postgres; vector = LanceDB / pgvector / Chroma; all behind one interface) and a **retrieval-mode taxonomy** of ~18 search types. Memory is built by a clean staged `cognify` pipeline and queried as a knowledge graph with **triplet-importance scoring**.

### The `cognify` pipeline (KNOWN)

**KNOWN** `cognee/api/v1/cognify/cognify.py:281-344` (`get_default_tasks`). The default pipeline is an ordered list of `Task`s (the 6-stage pipeline the RE-target doc describes — slightly compressed in current head):
```
1. classify_documents              # EXTRACT: raw Data items → typed Document objects
2. extract_chunks_from_documents   # CHUNK: max_chunk_size = get_max_chunk_tokens(), chunker=TextChunker
3. extract_graph_and_summarize     # COGNIFY: ONE task that BOTH LLM-extracts entities+relations into a
                                    #   KnowledgeGraph (graph_model=KnowledgeGraph, ontology_resolver) AND
                                    #   summarizes each chunk for retrieval; custom_prompt overridable
4. add_data_points                 # LOAD: persist nodes/edges + embeddings; embed_triplets toggle
5. extract_dlt_fk_edges            # LOAD: derive FK edges from ingested relational data
```
`chunks_per_batch` defaults to **100** (`:313`). The permission/ownership step the RE-target doc lists as stage 2 is enforced upstream at the dataset/`User` boundary (each task carries `user`), not as an inline task. A separate `get_temporal_tasks` variant swaps stages 3-4 for `extract_events_and_timestamps → extract_knowledge_graph_from_events` (a temporal-graph build). Pluggable graph_model lets users inject domain ontologies (`KnowledgeGraph` is the default Pydantic schema).

### Pluggable backend abstraction (KNOWN — the headline for Verso)

**KNOWN** `cognee/infrastructure/databases/`. Three storage planes, each behind a factory + interface:
- **graph** (`graph/get_graph_engine.py:110`): provider chosen by `GRAPH_DATABASE_PROVIDER` env → adapters for `neo4j_driver`, `kuzu`, `ladybug`, `neptune_driver`, `postgres`, plus a `USE_UNIFIED_PROVIDER=pghybrid` mode that collapses graph+vector into one Postgres. All implement `GraphDBInterface`.
- **vector** (`vector/create_vector_engine.py`): `lancedb`, `pgvector`, `chromadb`, with an `embeddings/` adapter layer.
- **relational** + **hybrid** + **unified** planes.

The lesson: a memory framework can present ONE `add()`/`search()` API and let the operator pick NetworkX (in-process, zero-ops) for dev, Kuzu (embedded) for single-node, Neo4j for scale, or `pghybrid` (single Postgres) — exactly Verso's pluggable-backend goal. The cheapest default is the **NetworkX in-process graph** (no external service), which Cognee scores against during search with the triplet math below.

### Retrieval modes (KNOWN)

**KNOWN** `cognee/modules/search/types/SearchType.py:4-20` — the `recall(mode=...)` taxonomy Verso wants. 18 modes:
```
SUMMARIES, CHUNKS, CHUNKS_LEXICAL (BM25), RAG_COMPLETION (classic vector RAG),
TRIPLET_COMPLETION, GRAPH_COMPLETION (graph-triplet RAG), GRAPH_COMPLETION_COT (chain-of-thought
multi-round graph traversal), GRAPH_COMPLETION_DECOMPOSITION (query decomposition),
GRAPH_COMPLETION_CONTEXT_EXTENSION, GRAPH_SUMMARY_COMPLETION, CYPHER (raw graph query),
NATURAL_LANGUAGE (NL→Cypher), TEMPORAL (time-aware), FEELING_LUCKY (auto-pick mode),
AGENTIC_COMPLETION, CODING_RULES
```
The retrievers are registered (`register_retriever.py`), so modes are pluggable too. `FEELING_LUCKY` auto-routes to a mode — the "let the system pick the retrieval strategy for this query" pattern that the RE-target doc flags as the adaptive-retrieval research direction.

### Triplet-importance scoring (KNOWN — the graph-search math)

**KNOWN** `cognee/modules/graph/cognee_graph/CogneeGraph.py:504-540` (`score`). For `GRAPH_COMPLETION`, candidate triplets (node1 → edge → node2) are scored and the **smallest-distance** k kept:
```python
# per triplet, sum the distance contributions of its 3 elements (both nodes + the edge):
for element in (node1, node2, edge):
    distance = vector_distance[query_index]              # cosine distance to query (lower = closer)
    importance_weight = element.importance_weight or 0.5 # per-element salience prior
    distance = (2 - importance_weight) * distance        # high-importance element → distance shrinks → ranks better
    # optional feedback blend: normalized_d = d/2; blended = (1-fi)*nd + fi*feedback ; back to distance scale
triplet_score = sum(importances)                         # lower is better
return heapq.nsmallest(k, edges, key=score)              # missing distance defaults to penalty 6.5
```
Constants from `GraphCompletionRetriever.__init__` (`graph_completion_retriever.py:47-78`): `top_k=5`, `wide_search_top_k=100`, `triplet_distance_penalty=6.5`, `neighborhood_seed_top_k=10`, `neighborhood_depth`, `global_context_index_top_k=3`. The `(2 - importance_weight)` factor is a clean salience prior: an entity flagged important (weight→1) gets its distance multiplied by 1.0, an unimportant one (weight→0) by 2.0 — doubling its penalty. The `GraphCompletionCotRetriever` (`graph_completion_cot_retriever.py:36`) extends this with a `max_iter` reasoning loop that generates follow-up queries each round and re-fetches triplets — the chain-of-thought graph traversal.

### KnowledgeGraph schema + cascade extraction (KNOWN)

**KNOWN** `cognee/shared/data_models.py:20-44`. The default `graph_model` is a Pydantic `KnowledgeGraph{summary, description, nodes:[Node], edges:[Edge]}` where `Node{id, name, type, description, label}` and `Edge{source_node_id, target_node_id, relationship_name, description}` — and crucially the edge `description` is "a concrete one-sentence fact expressed by this edge, using endpoint names" (same fact-as-edge-sentence design as Graphiti). Users inject domain schemas by passing a different `graph_model`. The newer **cascade extraction** (`tasks/graph/cascade_extract/`) splits extraction into THREE LLM passes instead of one: (1) `extract_graph_nodes` ("be exhaustive… capture all entities, names, nouns, noun-parts, implied mentions… also extract potential entity *type* nodes… avoid duplicates and overly generic terms"), (2) `extract_graph_relationship_names` (name the relations between found nodes), (3) `extract_graph_edge_triplets` (bind nodes + relations into triplets). This node→relation→triplet decomposition trades more LLM calls for higher recall and cleaner typing than the single-shot `extract_graph_and_summarize`.

### Ontology injection — RDF/OWL with fuzzy matching (KNOWN)

**KNOWN** `cognee/modules/ontology/`. The default resolver is `RDFLibOntologyResolver(ontology_file=None, matching_strategy=FuzzyMatchingStrategy())` (`get_default_ontology_resolver.py:7`). Users supply an `.owl`/RDF ontology file + a matching strategy (`rdflib` + `fuzzy`) via env (`get_ontology_resolver_from_env`), and during `extract_graph_and_summarize` extracted entities are matched/typed against the ontology (subclass hierarchy aware). This is the domain-type-injection point the RE-target doc flags — a formal ontology constrains and types the extracted graph, which fuzzy-matches surface mentions to canonical ontology classes. For Verso, this is the mechanism to let users declare domain entity types (a Pydantic graph_model OR an RDF ontology) and have extraction conform to them.

### `memify` — agent-trace memory (KNOWN, directly relevant to Verso)

**KNOWN** `cognee/tasks/memify/`. Beyond `cognify` (document → graph), Cognee has a `memify` pipeline that ingests **agent execution traces** as memory: `extract_agent_trace_feedbacks` (`extract_agent_trace_feedbacks.py:28`) retrieves stored `session_feedback` or raw `method_return_value` step-level trace content per user/session and feeds it into the graph; `extract_agent_trace_feedbacks` / `extract_subgraph` / `sync_graph_to_session` / `cognify_agent_trace_feedback` build session-scoped subgraphs from agent runs. This is exactly Verso's "run trace → durable memory" path implemented as a pipeline variant — the agent's own execution history becomes queryable graph memory, with feedback signals attached. Verso should treat run-trace ingestion as a `memify`-style pipeline variant alongside document ingestion.

### Constants (KNOWN)

| Constant | Value | Source |
|---|---|---|
| `chunks_per_batch` | 100 | `cognify.py:313` |
| graph retriever `top_k` | 5 | `graph_completion_retriever.py:47` |
| `wide_search_top_k` | 100 | `:51` |
| `triplet_distance_penalty` | 6.5 | `:52` |
| `neighborhood_seed_top_k` | 10 | `:57` |
| `global_context_index_top_k` | 3 | `:59` |
| importance salience factor | `(2 - importance_weight)` | `CogneeGraph.py:534` |
| default importance_weight | 0.5 | `CogneeGraph.py:516` |
| search modes | 18 | `SearchType.py` |

**For Verso:**
1. **Adopt the three-plane pluggable-backend factory** (graph / vector / relational, each behind an interface, provider chosen by config). Ship NetworkX in-process as the zero-ops dev default, Kuzu/pgvector as embedded prod, Neo4j/Postgres-hybrid for scale. This is the cleanest reference for Verso's "pluggable backend" requirement — cleaner than building it bespoke.
2. **Adopt the `recall(mode=...)` taxonomy.** Verso doesn't need all 18, but the spine — `chunks` / `rag` / `graph` / `graph_cot` / `cypher` / `temporal` / `feeling_lucky` — is the right API. Register retrievers as plugins so new modes don't touch the core.
3. **Steal the triplet-importance salience math:** `score = Σ_{node1,node2,edge} (2 - importance_weight) * cosine_distance`, `heapq.nsmallest(k)`, missing→penalty. It's a one-line way to bias graph retrieval toward salient entities without a learned reranker.
4. `FEELING_LUCKY` (auto-route to a mode) is the seed of the adaptive-retrieval direction — Verso's evals layer could learn the mode→task-type mapping.
5. The single `extract_graph_and_summarize` task (graph + summary in one LLM call) is a cost optimization Verso should copy — don't make two passes over each chunk.

---

## Memobase

### What It Is

A memory system that stores a **structured, evolving user profile** instead of a flat fact list, and writes via **buffer batching** rather than per-message. Messages accumulate in a buffer; when the buffer crosses a token threshold it flushes with a small fixed number of LLM calls (extract → merge → event-tag) that see the full batch at once. FastAPI + Postgres + Redis, MIT. The design contrast with Mem0 is the whole point: profile-vs-facts, buffered-vs-per-turn.

### Profile taxonomy — the two-level ontology (KNOWN)

**KNOWN** `prompts/user_profile_topics.py:11-77`. The default profile is a fixed `topic → sub_topic` tree (extensible per project):
```
basic_info   → Age, name, gender, language, ...
contact_info → ...
education    → school, degree, major, ...
demographics → ...
work         → working_industry, position, work_skills
interest     → movie, music, book, sports, food, ... (+ movie_director etc. emergent)
psychological→ personality, values, beliefs, motivations, goals
life_event   → marriage, relocation, retirement
```
`max_profile_subtopics = 15` (`env.py:88`) caps fan-out per topic. This two-level taxonomy is how Memobase gets typed memory **without a graph DB** — a profile entry is `(topic, sub_topic, memo)` and the memo is free text. The LLM may "create your own topics/sub_topics if necessary" unless `profile_strict_mode` (`env.py:117`, default False).

### Write Loop — buffer batching (KNOWN)

**KNOWN** `controllers/buffer.py`. Messages ("blobs") land in a `buffer_zones` table with a per-blob `token_size`. `detect_buffer_full_or_not` (`:66-90`) sums buffered tokens and flushes when `buffer_token_size > CONFIG.max_chat_blob_buffer_token_size` (**default 1024 tokens**, `env.py:86`). On flush (`flush_buffer_by_ids`), the *entire* batch is processed together — this is the key efficiency claim (the RE-target doc's "3 LLM calls max / 40-50% cost reduction"). The flush pipeline runs a small fixed set of LLM calls over the whole batch, not per message:
```
flush(batch):
  1. summary_entry_chats  → condense the chat batch into a Markdown "memo" of user info/events/prefs
  2. extract_profile      → memo → AIUserProfiles{facts:[{topic, sub_topic, memo}]}   (see prompt below)
  3. merge_profile        → per (topic,sub_topic): reconcile new memo vs existing profile entry → APPEND/UPDATE/ABORT
  4. event_summary + event_tagging → timeline event with tags
```
Because step 2 sees the whole buffered batch with full context, it dedups and contextualizes far better than Mem0's per-message extraction — at the cost of latency (memory lags until flush).

### Extract prompt (KNOWN, verbatim core)

**KNOWN** `prompts/extract_profile.py`. System: "You are a professional psychologist… extract the important profiles of user in structured format… not only extract explicitly stated, but also infer what's implied." Output schema `AIUserProfiles{facts:[{topic, sub_topic, memo}]}`. Few-shot (verbatim):
```
"User's favorite movies are Inception and Interstellar [mention 2025/01/01]
 User's favorite movie is Tenet [mention 2025/01/02]"
→ facts:[
    {topic:"interest", sub_topic:"movie",
     memo:"Inception, Interstellar[mention 2025/01/01]; favorite movie is Tenet [mention 2025/01/02]"},
    {topic:"interest", sub_topic:"movie_director", memo:"user seems to be a big fan of director Christopher Nolan"}]
```
Note the `[mention YYYY/MM/DD]` inline timestamping preserved inside the memo text — a lightweight temporal anchor without a temporal schema. The prompt is told NOT to create profile entries about *other* people ("if the memo mentions the position of another person, don't generate a work/position topic").

### Merge logic — APPEND / UPDATE / ABORT (KNOWN, verbatim)

**KNOWN** `prompts/merge_profile.py:9-63`. This is the conflict-resolution policy — three actions, per `(topic, sub_topic)`:
```
MERGE_FACTS_PROMPT: "determine how new supplementary information should be merged with the current memo"
- APPEND  →  new info brings new content (or current memo empty) → output literal "APPEND" (server appends new memo)
- UPDATE  →  [UPDATED_MEMO]  →  new info conflicts/refines → LLM REWRITES the full merged memo
- ABORT   →  new info is worthless / already covered → discard
Output: THOUGHT --- ACTION   (chain-of-thought before the action)
Example: midterm-exam memo + new "preparing for final exams" → UPDATE (rewrite, drop the obsolete midterm line)
```
Unlike Mem0's legacy AUDN (which can DELETE a whole memory on contradiction), Memobase's UPDATE **rewrites the memo string in place** — the profile entry is a living document, not a list. There is no DELETE; the closest is UPDATE rewriting away stale content. A `merge_profile_yolo` variant does the merge in one shot for lower cost.

### Schema (KNOWN)

**KNOWN** `models/database.py`. `user_profiles` table:
```sql
user_profiles(id UUID, user_id, project_id,
              content TEXT NOT NULL,            -- the memo string (the living document)
              attributes JSONB,                 -- {topic, sub_topic} + metadata
              ...)
INDEX idx_user_profiles_user_id_project_id (user_id, project_id)
buffer_zones(id, user_id, project_id, blob_type, token_size, ...)  -- the pending-message buffer
general_blobs(blob_data JSONB, ...)                                -- raw messages
```
Scoping is `(user_id, project_id)` — flatter than Mem0's triple. Retrieval is **SQL on the structured profile** (no vector search on the hot path), which is how Memobase hits sub-100ms recall: the profile is small and indexed, so "get the user's profile" is a keyed lookup, not an ANN search.

### Event timeline + tagging (KNOWN)

**KNOWN** `prompts/event_tagging.py`, `controllers/modal/chat/event_summary.py`. Parallel to the profile, each flush also produces a **timeline event**: `event_summary` condenses the batch into an episodic event, then `event_tagging` classifies it against a configurable tag vocabulary (`<event_tags>`). So Memobase stores TWO memory shapes per user: a structured **profile** (stable attributes, `topic/sub_topic/memo`) AND a **timeline of tagged events** (episodic, time-ordered). This profile-vs-events split is cleaner than a single fact list: durable traits live in the profile, time-bound happenings live in the event timeline. Verso should adopt the same dual shape — stable typed profile + episodic event log — rather than forcing both into one store.

### Recall — `pick_related_profiles` (KNOWN)

**KNOWN** `prompts/pick_related_profiles.py:54`. When a query needs profile context, the recall path is an LLM **selection** over the profile, not vector search: system "You are a professional journalist… select all possible user's memos to enrich the conversation," given the conversation + the candidate `topic_lists`, capped at `max_num`. The `chat_context_pack` prompt (`chat_context_pack.py:6`) then packs the selected `profile_section` + `event_section` into context with the instruction "Unless the user has relevant queries, do not actively mention those memories." So recall = LLM picks relevant profile entries + recent events → packed into the prompt. For a small structured profile this LLM-select is cheap and more precise than ANN; for Verso it's the right recall mode for the profile tier (reserve ANN for the large fact/event store).

### Constants (KNOWN)

| Constant | Value | Source |
|---|---|---|
| `max_chat_blob_buffer_token_size` (flush trigger) | 1024 tokens | `env.py:86` |
| `max_profile_subtopics` | 15 | `env.py:88` |
| `profile_strict_mode` | False | `env.py:117` |
| profile taxonomy depth | 2 (topic → sub_topic) | `user_profile_topics.py` |
| merge actions | APPEND / UPDATE / ABORT | `merge_profile.py:34-46` |
| LLM calls per flush | ~4 (summary, extract, merge, event-tag) | `controllers/modal/chat/` |
| scoping | `(user_id, project_id)` | `database.py:447` |

**For Verso:**
1. **Buffer-batched async write is the right default for high-volume chat.** Accumulate to a token threshold (Memobase: 1024), then extract once over the full batch. Far cheaper and higher-quality dedup than Mem0's per-message extraction — but Verso must expose a `flush()` so latency-sensitive callers can force-consolidate before a checkpoint.
2. **The profile-vs-facts axis is a real design fork.** For long-lived single-user relationships (companion, assistant), the evolving structured profile (`topic/sub_topic/memo`) is more coherent than a growing fact list. Verso should support BOTH: a Mem0-style fact store AND a Memobase-style profile, selectable per memory type.
3. **The two-level `topic → sub_topic` taxonomy gives typed memory with zero graph infra** — a `(topic, sub_topic, memo)` row in Postgres, SQL-indexed, sub-100ms recall. This is the cheapest viable typed-memory backend and should be Verso's default tier (graph reserved for relational reasoning).
4. **UPDATE-rewrites-the-document, never DELETE.** Memobase's merge keeps a living memo and rewrites it; combined with `[mention DATE]` inline anchors it preserves history cheaply. Safer than AUDN deletes.
5. **APPEND/UPDATE/ABORT with chain-of-thought** is a cleaner 3-action merge than AUDN's 4-action — no separate ADD (it's APPEND) and no destructive DELETE. Worth copying for Verso's profile-merge policy.

---

## MemOS (MemTensor)

### What It Is

A research-grade "Memory OS" whose contribution to Verso is the **MemCube** — a typed, versioned, provenance-tracked memory container with explicit lifecycle types — and the **WorkingMemory → LongTermMemory/UserMemory promotion hierarchy** (the published L1→L2→L3→Skill model, made concrete). Three memory planes per cube: textual / activation (KV-cache) / parametric (LoRA-style). Papers arXiv:2505.22101 + 2507.03724.

### MemCube schema — provenance + lifecycle (KNOWN)

**KNOWN** `src/memos/memories/textual/item.py:94-188`. A `TextualMemoryItem` has rich provenance metadata — this is the typed/versioned container the RE-target doc calls MemCube:
```python
TextualMemoryMetadata:
  user_id, session_id
  status: "activated" | "resolving" | "archived" | "deleted"   # "resolving" = mid-conflict-merge
  version: int = 1                       # incremented on update
  history: list[ArchivedTextualMemory]   # archived prior versions (core info only)
  evolve_to: list[str]                   # ids of new nodes this one "evolves" to after LLM extraction
  covered_history: Any                   # ids covered by an update
  is_fast: bool                          # raw, not-yet-LLM-edited ("fast mode")
  working_binding: str                   # links a fast memory to its working-memory node
  confidence: float [0,100]
  source: "conversation"|"retrieved"|"web"|"file"|"system"
  visibility: "private"|"public"|"session"
  tags: list[str]; updated_at: ISO8601
TreeNodeTextualMemoryMetadata(extends):
  memory_type: WorkingMemory | LongTermMemory | UserMemory | OuterMemory |
               ToolSchemaMemory | ToolTrajectoryMemory | RawFileMemory |
               SkillMemory | PreferenceMemory | Context        # ← the lifecycle + skill tiers
  sources: list[SourceMessage]; background: str; embedding
```
The `version + history + evolve_to + covered_history + status` quintet is exactly the "provenance/versioning that can be migrated and fused" the RE-target doc wants — every memory knows its prior versions, what it evolved from, and what it covers. The `SkillMemory` / `ToolSchemaMemory` / `ToolTrajectoryMemory` types ARE the skill-crystallization tier (experience trajectories → reusable tool schemas/skills).

### L1→L2→L3 promotion — the capacity-gated hierarchy (KNOWN)

**KNOWN** `src/memos/memories/textual/tree.py:81-86` + `tree_text_memory/organize/manager.py`. The lifecycle types have hard capacities:
```python
memory_size = {"WorkingMemory": 20, "LongTermMemory": 1500, "UserMemory": 480}
```
Flow (`manager.py:30-285`): `mem_reader` extracts raw turns → **WorkingMemory** nodes (L1, transient run traces, cap 20). The manager then produces **LongTermMemory** (L2, durable extracted knowledge, cap 1500) and **UserMemory** (L3, stable user model, cap 480) from them. WorkingMemory is **FIFO-evicted** to stay within cap: `remove_oldest_memory(memory_type="WorkingMemory", keep_latest=20)` (`:255-257, 283-285`). This is the concrete L1→L2→L3 crystallization: ephemeral working set bounded at 20, promoted into bounded long-term/user tiers. `is_reorganize` triggers conflict-merge (status flips to `resolving`, old version pushed to `history`, `covered_history` records what was superseded — versioned, not deleted).

### Retrieval — graph + vector + FTS hybrid (KNOWN)

**KNOWN** `tree_text_memory/retrieve/searcher.py` + `graph_dbs/neo4j.py`. The tree memory is backed by a **graph DB** (Neo4j / Neo4j-community / PolarDB) for structure + **Milvus** for vectors; the searcher does scope-filtered retrieval (`["All","WorkingMemory","LongTermMemory","UserMemory"]`) combining graph traversal, vector similarity, and full-text. A `reranker/` plane reranks (`reranker/factory.py:40`): backends `http_bge`/`bge` (default model **`bge-reranker-v2-m3`**), `http_bge_strategy` (strategy variants: single_turn, dialogue_common, concat_background, singleturn_outmem — context-shaping for the rerank pairs), `cosine_local`, `noop`. The RE-target doc's "FTS5+vector" is the lightweight local variant; the production path is Neo4j-FTS + Milvus + BGE rerank.

### MemScheduler — the OS-level memory controller (KNOWN)

**KNOWN** `src/memos/mem_scheduler/`. This is the "OS" in MemOS: an async scheduler (`GeneralScheduler` → `OptimizedScheduler`) that owns three responsibilities. (1) **WorkingMemory reorder/replace** (`optimized_scheduler.py:285`, `replace_working_memory`): on each query it re-orders the WorkingMemory set and applies "combined unrelated and redundant memory filtering" — pruning the working set to the most relevant items before the LLM sees it (with a keep-memories fallback on failure). (2) **Activation-memory update** (`update_activation_memory_periodically`): periodically promotes hot textual memories into the **activation plane** (precomputed KV-cache) so frequently-hit memories skip recomputation — this is the 35% token-savings mechanism. (3) **mix_search with priority** (`mix_search_memories`, `:117-162`): blends fresh retrieval with a Redis-cached working set under a `search_priority`, writing results back to Redis (`update_search_memories_to_redis`). So MemOS treats the working set like an OS page cache: schedule what's hot into fast tiers, evict the cold. Verso's context-assembly step should adopt this "reorder + filter working set per query, cache hot items" pattern rather than re-retrieving from scratch every turn.

### Dream — heuristic + semantic enrichment (KNOWN)

**KNOWN** `src/memos/dream/`. Separate from the scheduler, MemOS also has a `dream/` subsystem (`enrichment.py`, `contextualization.py`, `maintenance.py`) that binds context to memories. `DreamHeuristicEnricher` (`enrichment.py:58`) does cheap rule-based enrichment (in `extract_mode="fine"`) writing into each item's `metadata.internal_info["dream"]` — "cheap signals that help a later semantic enricher or Dream binding stage." This two-phase (cheap heuristic → expensive semantic) enrichment mirrors Honcho's deriver→dreamer split and is the same async-consolidation pattern recurring across the cluster.

### Constants (KNOWN)

| Constant | Value | Source |
|---|---|---|
| WorkingMemory capacity (L1) | 20 | `tree.py:83` |
| LongTermMemory capacity (L2) | 1500 | `tree.py:84` |
| UserMemory capacity (L3) | 480 | `tree.py:85` |
| WorkingMemory eviction | FIFO (`remove_oldest`) | `manager.py:255` |
| status enum | activated/resolving/archived/deleted | `item.py:109` |
| version default | 1 (incremented on update) | `item.py:121` |
| confidence range | [0, 100] | `item.py:135` |
| memory_type lifecycle tiers | 10 (incl. SkillMemory) | `item.py:178-188` |

Paper claims (2505.22101): MemCube as a standardized container; ~35% token savings vs full-context via the tiered promotion. The 2507.03724 paper adds the OS-level scheduling.

**For Verso:** MemOS is the reference for Verso's **durable-seam crystallization tier**.
1. **Adopt the MemCube metadata quintet** (`version + history + evolve_to + covered_history + status`) for any memory that must be auditable and time-travelable. It's a lighter-weight versioning than Graphiti's bi-temporal edges and works for non-graph stores. `status="resolving"` as an explicit mid-merge state is a nice touch for concurrent writes.
2. **Adopt capacity-gated lifecycle tiers** (WorkingMemory cap 20 → LongTermMemory 1500 → UserMemory 480, FIFO eviction at L1). This is exactly Verso's "in-memory run traces (L1) → extracted durable patterns (L2) → agent world model (L3)" mapping. The hard caps + FIFO are the cheap mechanism that prevents unbounded growth.
3. **`SkillMemory` / `ToolTrajectoryMemory` as first-class memory types** is the "memory as capability" pattern — a successful tool trajectory crystallizes into a reusable skill schema. Verso's agent-specialization story needs exactly this typed promotion path.
4. The three-plane MemCube (textual / activation-KV / parametric-LoRA) is more than Verso needs day one, but the *textual* plane's typed-versioned-item design is directly adoptable; reserve activation/parametric for a later tier.

---

## txtai (neuml)

### What It Is

The most mature **unified-store** implementation: one Python-native `Embeddings` object runs dense vector ANN, sparse BM25, a graph network, and a relational DB through a single API, with no external services required. Its value to Verso is API design — what a clean "memory backend = embeddings + graph + KV in one handle" interface looks like — plus three auto-selected hybrid-fusion strategies in one tidy module.

### The unified `Embeddings` API (KNOWN)

**KNOWN** `src/python/txtai/embeddings/base.py`. One object, one surface:
```python
index(documents, reindex=False, checkpoint=None)              # build dense+sparse(+graph) indexes
upsert(documents)                                             # incremental add
search(query, limit, weights=None, index=None, graph=False)   # hybrid; graph=True returns graph results
batchsearch(queries, ...)                                     # batched
similarity / batchsimilarity(query, data)                     # pairwise
explain / batchexplain(query, texts, limit)                   # per-token attribution
terms / batchterms(queries)                                   # term-weight introspection
```
The single `search()` transparently runs keyword (sparse only), ANN (dense only), or hybrid (both present) depending on which indexes the embeddings was configured with (`base.py:87-88`). The same call with `graph=True` projects results onto the graph. This "one method, behavior depends on configured components" is the clean unified surface Verso should emulate — no separate `vector_search()` / `keyword_search()` / `graph_search()` methods.

### Hybrid fusion — three auto-selected strategies (KNOWN)

**KNOWN** `src/python/txtai/embeddings/search/hybrid.py:8-46`. The fusion method is chosen by the scoring backend's normalization, not hard-coded:
```python
if scoring is BB25/Bayesian-normalized → logodds   (log-odds conjunction)
elif scoring isnormalized()            → convex     (weighted convex combination)
else (unnormalized)                    → rrf        (reciprocal rank fusion)
```
Default `weights = 0.5` → `[dense_weight, sparse_weight] = [0.5, 0.5]` (`search/base.py:64,114`). Over-fetch `limit * 10` per arm when hybrid (`base.py:108-109`).
```python
# convex (normalized scores):  uids[uid] += score * weights[v]              # v=0 dense, v=1 sparse
# rrf    (unnormalized):        uids[uid] += (1.0/(r+1)) * weights[v]        # RRF k=1, weighted
# logodds(BB25):               LogOdds() — per-query dynamic sigmoid calibration then log-odds sum
```
Two notable details: (1) **RRF here uses k=1** (`1/(rank+1)`), same aggressive small-pool choice as Graphiti, distinct from Hindsight's k=60. (2) the fusion is **weighted RRF** (`* weights[v]`) — most RRF implementations are unweighted. (3) the strategy auto-switches on score normalization — a principled way to avoid the "you can't add cosine to BM25" problem (normalize first, then choose the matching fusion).

### Sparse-scoring backends + BB25 normalization (KNOWN)

**KNOWN** `src/python/txtai/scoring/`. The sparse (keyword) arm is itself pluggable via `ScoringFactory` (`factory.py:40`): `bm25` (default), `tfidf`, `sif` (smooth inverse frequency), `sparse` (learned sparse vectors / SPLADE-style), `pgtext` (Postgres full-text). BM25 idf is the textbook `log(1+(N-f+0.5)/(f+0.5))` (`bm25.py:27`). The interesting piece is `normalize.py` — a **Bayesian "BB25" normalization** (`isbayes`) that calibrates raw scores into a probability-like range with `alpha` (default 1.0, scaled by per-query std for score-range invariance) and `beta` (per-query median): `logits = clip(alpha*(candidates - beta), -500, 500)`. This is what lets the hybrid fusion *auto-select* log-odds vs convex (the normalized scores feed `logodds`; unnormalized feed `rrf`). The lesson for Verso: making the sparse scorer's normalization explicit is what enables principled fusion-strategy selection — don't bolt BM25 on as raw scores.

### Graph component (KNOWN)

**KNOWN** `src/python/txtai/graph/`. Backend is pluggable (`factory.py:30`): **`networkx`** (in-process, default) or **`rdbms`** (SQLAlchemy-backed, SQL-projectable for persistence). The NetworkX graph (`networkx.py`) supports community detection (louvain, greedy modularity, async LPA) and topic modeling (`topics.py`) — so "graph memory" here is a real network with community rollups, but with zero external service. The RDBMS backend (`rdbms.py:22`) *subclasses NetworkX* and mirrors the in-memory graph into SQL `nodes`/`edges` tables (configurable table names) for persistence — `create()` clears the tables, `scan()` iterates with attribute filters, and `self.graph.nx` is returned so the rest of the code sees a NetworkX-compatible handle. So persistence is "same NetworkX API, SQL underneath" — the cleanest possible pluggable-graph design. Graph + vector results are fused by projecting ANN hits onto graph nodes and traversing (`graphsearch`). This is the simplest viable graph-memory implementation: `pip install networkx`, done; add a DSN for persistence.

### Agent memory integration (KNOWN)

**KNOWN** `src/python/txtai/agent/base.py:24-75` (built on smolagents `CodeAgent`/`ToolCallingAgent`). Memory here is deliberately minimal: `memory=N` keeps the last N agent outputs in a `self.memory` dict keyed by `session`, injected into the prompt via a Jinja `{{ memory }}` placeholder ("Use the following conversation history… If the history is irrelevant, forget it"). This is conversation-window memory, NOT the Embeddings store — the long-term memory is a separately-instantiated `Embeddings` the agent calls as a tool. The lesson: txtai keeps short-term (prompt window) and long-term (embeddings store) memory cleanly separate, connected only by the agent loop. Verso should keep the same separation.

### Constants (KNOWN)

| Constant | Value | Source |
|---|---|---|
| default hybrid weight | 0.5 (→[0.5,0.5]) | `search/base.py:64` |
| hybrid over-fetch | `limit * 10` per arm | `search/base.py:108` |
| RRF k | 1 (`1/(rank+1)`, weighted) | `hybrid.py` rrf |
| fusion auto-select | logodds / convex / rrf by normalization | `hybrid.py:26-33` |
| graph backend default | networkx (or rdbms) | `graph/factory.py:30` |
| agent memory | last-N outputs, Jinja `{{memory}}` | `agent/base.py` |
| BM25 idf | `log(1+(N-f+0.5)/(f+0.5))` | `scoring/bm25.py:27` |

**For Verso:**
1. **Adopt the single-method unified surface:** one `search()` whose behavior (keyword / ANN / hybrid / graph) depends on which components are configured — not four separate methods. This is the cleanest API shape in the whole cluster and the direct reference for Verso's `memory.recall()`.
2. **Auto-select the fusion strategy by score normalization** (normalized→convex, BB25→logodds, raw→RRF). It dodges the "can't compare cosine and BM25" trap and means Verso never has to hard-pick a fusion. Combined with the cluster's other data points, the rule is: **RRF k=1 for small graph pools (txtai, Graphiti), k=60 for large ANN pools (Hindsight), convex when both scores are normalized.**
3. **NetworkX as the zero-ops graph-memory default** (with louvain community rollups, RDBMS projection for persistence) is the right baseline for Verso — matches Cognee's recommendation. Reserve Neo4j/Milvus for scale.
4. **Keep short-term (prompt-window) and long-term (embeddings) memory architecturally separate**, connected only through the agent loop / tool calls. Don't conflate the two as some systems do.

---

## Cross-System Synthesis → Verso

### The write-loop spectrum (extract → consolidate)

| System | Trigger | LLM calls | Consolidation policy | History |
|---|---|---|---|---|
| **Mem0** (V3) | per turn | 1 (extract, ADD-only) | additive + entity-link; dedup by md5 + prompt | none (additive) |
| **Mem0** (legacy) | per turn | 1 extract + 1 AUDN | ADD/UPDATE/**DELETE**/NONE | lost on DELETE |
| **Graphiti** | per episode | extract + resolve (small model) | invalidate (bi-temporal), never delete | full (valid/invalid intervals) |
| **Hindsight** | per `retain` | 1 (5W extract) | additive; async graph-maint + reflect() | versioned |
| **Honcho** | async deriver | 1/batch | surprisal-gated dreaming (top-10% novel) | observation rows |
| **Memobase** | buffer flush (1024 tok) | ~4/batch | profile APPEND/UPDATE/ABORT (rewrite memo) | `[mention DATE]` inline |
| **MemOS** | per turn → tiers | reader + reorganize | capacity-gated promotion (20→1500→480), version+history | full (version chain) |

**Convergent verdict for Verso:** the ecosystem has moved AWAY from destructive update (legacy Mem0 AUDN-DELETE) toward **additive + invalidate/version**. Verso's default write should be: extract → ADD with linking; conflicts produce a new linked memory + (optional) an invalidation stamp on the prior; never hard-delete. Buffer-batch for high volume (Memobase), gate consolidation by novelty (Honcho surprisal) and capacity (MemOS tiers).

### Embedding model / dim / NER per system (KNOWN, RE'd)

| System | Embedding (default) | Dim | NER / entity method | Cross-encoder rerank |
|---|---|---|---|---|
| Mem0 | configurable (OpenAI default) | model-dep | **spaCy** (PROPER/QUOTED/COMPOUND/NOUN) | none (entity-boost instead) |
| Graphiti | OpenAI `text-embedding-3-small` | 1024 (env) | **LLM** (`extract_message`, integer-typed) | `BAAI/bge-reranker-v2-m3` (optional) |
| Hindsight | local ST | **384** | **LLM** (5W) + **pg_trgm** canonicalize | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Honcho | OpenAI | **1536** | LLM (explicit/deductive/inductive) | none (surprisal tree) |
| Cognee | configurable | model-dep | **LLM cascade** (node→rel→triplet) + RDF ontology | none (triplet salience) |
| Memobase | none on hot path (SQL recall) | — | LLM into topic/sub_topic | none (LLM pick) |
| MemOS | configurable | model-dep | LLM (mem_reader) | `bge-reranker-v2-m3` |
| txtai | configurable ST | model-dep | n/a (general framework) | n/a |

Takeaways: dims range 384→1536; **NER is split between cheap-spaCy/pg_trgm (Mem0, Hindsight) and expensive-LLM (Graphiti, Cognee, Honcho)** — Verso should offer both, default cheap. The two BGE-reranker users (Graphiti, MemOS) and the MiniLM user (Hindsight) bound the cross-encoder choice; Verso defaults to `bge-reranker-v2-m3` for quality, `ms-marco-MiniLM-L-6-v2` for speed.

### Recurring pattern — the async two-stage cognition split

Every system that handles real volume converges on the SAME topology: **a fast extraction stage off the request path + a slow consolidation stage triggered by accumulation.** Honcho: deriver (fast) → dreamer (surprisal, threshold 50/8h). MemOS: mem_reader → scheduler reorder + dream enrichment (heuristic→semantic). Hindsight: retain (additive) → async graph-maint + reflect(). Memobase: buffer (1024 tok) → flush. Mem0 proxy: daemon-thread add(). The lesson is unambiguous for Verso's durable-seam: **never consolidate on the request path.** Respond → enqueue extraction → consolidate when (N accumulated AND interval elapsed AND/OR novelty high). The cheap-heuristic-then-expensive-semantic two-phase (MemOS dream, Honcho surprisal-gate) is the budget-control mechanism.

### The retrieval-fusion spectrum

- **Additive normalized** (Mem0): `semantic + bm25_sigmoid + entity_boost`, adaptive divisor, gate on semantic first. Simplest; no rank info needed.
- **RRF** (Graphiti k=1, Hindsight k=60, txtai k=1 weighted): rank-based, robust to score-scale mismatch. **Pick k by pool size** (k≈1 for tens of candidates, k≈60 for hundreds+).
- **Convex / log-odds / RRF auto-select by normalization** (txtai): the most principled — normalize, then choose.
- **Multiplicative bounded boosts** (Hindsight): CE relevance × recency × temporal × proof, each ±5–10%. Re-ranks within a relevance band; recency can never beat relevance.
- **Triplet salience** (Cognee): `Σ (2-importance_weight)*distance`, nsmallest. For graph retrieval.

**Verso fusion recommendation:** default to **RRF with pool-size-adaptive k**; offer the Mem0 additive path for the no-graph tier; layer Hindsight's multiplicative recency/temporal/proof boosts as a post-rerank stage; use a cross-encoder (`bge-reranker-v2-m3` like Graphiti, or `ms-marco-MiniLM` like Hindsight) only on the final candidate budget.

### Scoping models, ranked by expressiveness

1. **Honcho `(observer, observed)` peer-symmetric** — most expressive; represents agent-observes-agent and theory-of-mind. Verso should adopt this for multi-agent.
2. **Mem0 composable `user_id ∧ agent_id ∧ run_id` (+actor_id query filter)** — flat but composable; good default.
3. **Memobase `(user_id, project_id)`**, **Hindsight `bank_id`**, **Graphiti/cognee `group_id`** — single-axis namespace = index partition key. Simplest, coarsest.

Verso should implement Mem0's composable tags as the default and Honcho's `(observer, observed)` as the multi-agent extension, with the namespace doubling as the backend index partition key (Graphiti/Hindsight implementation detail).

### Backend decision (cross-link `infra-vector-memory.md`)

Hindsight (single Postgres: pgvector + pgroonga + adjacency rows) and txtai/Cognee (NetworkX in-process + pluggable) both prove Verso does **not** need a polyglot Milvus+Neo4j+Redis stack for near-SOTA. Recommended Verso backend tiers:
- **dev / zero-ops:** txtai-style in-process (NetworkX graph + in-memory ANN).
- **single-node prod:** single Postgres (Hindsight model) — pgvector (hnsw/diskann) + pgroonga BM25 + adjacency + date columns.
- **temporal-reasoning / audit tier:** Graphiti bi-temporal edges on Neo4j.
- **scale:** the storage primitives in `infra-vector-memory.md` (Turbopuffer object-store tiering, LanceDB) sit *under* this cognition layer — Verso's memory backend interface (Cognee-style three-plane factory) selects among them. This file (cognition: write loop + fusion + temporal model) and `infra-vector-memory.md` (storage: ANN index + tiering) compose: the memory framework owns extract/consolidate/fuse; the vector store owns persist/index/scan.

### → Verso memory architecture (DESIGNED, synthesized from the above)

The extracted mechanisms compose into a concrete Verso spec. **DESIGNED** = our engineering call; every choice traces to a KNOWN mechanism above.

**Typed memory model (from Hindsight fact_type + Honcho observation taxonomy + MemOS lifecycle):**
```
MemoryItem {
  id, scope{user_id?, agent_id?, run_id?, observer?, observed?},   # Mem0 composable + Honcho symmetric
  type: explicit | deductive | inductive | belief | procedural | skill | contradiction,
  text, embedding,
  # provenance (MemOS quintet): version, history[], evolve_to[], source_ids[], status,
  # temporal (Graphiti-lite + Hindsight): mentioned_at, occurred_start, occurred_end, valid_at?, invalid_at?,
  confidence?, proof_count?, tags[], linked_ids[]                  # Mem0 linked_memory_ids
}
```

**Write loop (DESIGNED — Mem0 V3 additive + Memobase buffering + Honcho async):**
1. Per turn: enqueue raw turn to a buffer (Memobase pattern), respond immediately (Mem0 proxy daemon-thread).
2. On buffer flush (token threshold ~1024) OR explicit `flush()` before a checkpoint: ONE extraction LLM call over the batch, system prompt = additive (Mem0 `ADDITIVE_EXTRACTION_PROMPT`) + agent-context suffix when agent-scoped, with the anti-generalization rules (cluster consensus) and integer-index anti-hallucination map (Mem0/Graphiti).
3. ADD-only persist; dedup by md5 hash + prompt-level skip; entity-link via `linked_ids`.
4. Run-trace path: separate procedural-memory prompt (Mem0 verbatim) producing one resumable trace per run, action+verbatim-result.
5. Conflict policy is TIER-SELECTED: chat tier = read-time resolution (Hindsight "latest mentioned_at wins" + double-counting guard prompt); audit/checkpoint tier = write-time invalidation (Graphiti `invalid_at = new.valid_at`, LLM classifies + Python computes timestamps).

**Consolidation (DESIGNED — Honcho surprisal + MemOS tiers + Hindsight reflect):**
- Triggered by accumulation (N=50 new items AND ≥8h since last, Honcho constants) — never on request path.
- Cheap heuristic enrich first (MemOS), then surprisal-gate to top-10% novel (Honcho tree), then an agentic `reflect()` loop (max 10 iters, hierarchical: beliefs→observations→raw, Hindsight) that writes back `belief`/`inductive` items with `proof_count` + `source_ids` provenance.
- Capacity-gated tiers (MemOS): working set bounded (~20, FIFO), durable tier large (~1500), user-model tier (~480).

**Recall fusion (DESIGNED — txtai auto-select + Hindsight boosts + pool-adaptive RRF):**
```
arms = [semantic, bm25, graph(entity+semantic+causal links, Hindsight), temporal]
fuse  = auto-select by normalization (txtai): convex if normalized, RRF else
        RRF k = pool-size-adaptive (1 for tens, 60 for hundreds)
rerank= cross-encoder (bge-reranker-v2-m3) on final budget only
boost = × recency(±10%) × temporal(±10%) × proof_count(±5%)   [Hindsight, multiplicative, bounded]
gate  = drop below semantic threshold BEFORE fusing (Mem0)
modes = recall(mode=) taxonomy (Cognee): chunks/rag/graph/graph_cot/temporal/feeling_lucky
```

**Backend (DESIGNED — Cognee 3-plane factory over the tiers, cross-link `infra-vector-memory.md`):** one `MemoryBackend` interface, provider-selected: dev = txtai-style in-process (NetworkX + in-mem ANN); single-node = single Postgres (Hindsight: pgvector + pgroonga + `memory_links` adjacency + date cols); audit/temporal = Graphiti bi-temporal on Neo4j; scale = primitives in `infra-vector-memory.md` (Turbopuffer/LanceDB) under the same interface. Graph adjacency uses Hindsight's three-signal `memory_links` (entity self-join + kNN-at-insert + causal) before reaching for a graph DB.

**API surface (DESIGNED — unified like txtai):** one `recall()` whose behavior depends on configured components; `remember()`/`flush()` for the buffered write; `reflect()`/`consolidate()` for the async durable-seam; `mode=` selects retrieval strategy. Short-term (prompt window) and long-term (store) kept architecturally separate (txtai), connected only through the agent loop (Mem0 proxy injection: search-before, write-after-async).

This is the spec the per-target "For Verso" notes above feed into. The single highest-leverage decisions: (1) ADD-only writes with tier-selected conflict resolution, (2) async accumulation-triggered consolidation with surprisal gating, (3) pool-adaptive RRF + bounded multiplicative boosts for fusion, (4) a single-Postgres default backend behind a pluggable interface.
