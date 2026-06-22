# Memory-Reality — Raw Extraction (Mem0 + Graphiti)

Track: production. Unit: memory-reality.
Sources READ line-by-line:
- `/Users/seventyleven/Desktop/researchfms/teardowns/MEM0.md` (Mem0 `mem0ai/mem0`, HEAD `3ac1c94`, arXiv 2504.19413)
- `/Users/seventyleven/Desktop/researchfms/teardowns/GRAPHITI.md` (`getzep/graphiti` v0.29.2, HEAD `4a742cf`, arXiv 2501.13956)

Label key from sources: KNOWN = read from clone (`file:line`). INFERRED-paper = from arXiv. DESIGNED = teardown author's port engineering (treat as INFERRED for our purposes).

Verso memory baseline (for tagging): typed 4-tier (FACT/...), temporal, RRF recall, `recall_as_of` time-travel, `reflect()` consolidation, ADD-only with supersede-invalidates, bounded, sqlite/sqlitevec/inmem. Verso DEFERS the graph backend by design.

---

## PART A — MEM0

### A0. The headline finding (KNOWN, MEM0.md:14-27)
There are TWO Mem0 architectures and the gap is the central finding:
- **Paper/"classic" Mem0** (arXiv Apr 2025): TWO LLM calls — (1) extract facts, (2) **LLM-arbitrated ADD/UPDATE/DELETE/NOOP** over top-10 similar memories. Conflict resolution: LLM rewrites/deletes stale memories in-loop. Model GPT-4o-mini.
- **HEAD `3ac1c94` (2026-06)**: **ONE LLM call**, ADD-only "V3 phased batch pipeline" (`main.py:725`). **No conflict resolution in the add path.** Dedup = md5 hash check + prompt's own skip logic. UPDATE/DELETE only via explicit public API. Model `gpt-5-mini` default.

> CORRECTION (MEM0.md:25): The signature mechanism everyone cites — the LLM tool-call returning `[{id, text, event: ADD|UPDATE|DELETE|NOOP}]` over top-k retrieved memories — **is dead code at HEAD.** `get_update_memory_messages` and `DEFAULT_UPDATE_MEMORY_PROMPT` still exist in `prompts.py:176/:406` but `grep` returns ZERO call sites outside `prompts.py`. Live `_add_to_vector_store` (`main.py:688`) emits only `event:"ADD"` (`:875,987`). UPDATE/DELETE fire only via manual `update(memory_id,data)` / `delete(memory_id)` (`main.py:1555,1578`).

### A1. `Memory.add()` V3 phased pipeline (KNOWN, MEM0.md:31-76, `main.py:599`+)
8 phases inside `_add_to_vector_store` when `infer=True` (`main.py:725`):
- **Phase 0:** `session_scope = _build_session_scope(filters)` (sorted "user_id=..&run_id=.."); `last_messages = db.get_last_messages(scope, limit=10)` (SQLite recent buffer); `parse_messages` → "user: ..\nassistant: ..".
- **Phase 1:** `query_embedding = embed(parsed, "search")`; `existing = vector_store.search(..., top_k=10, search_filters)` (`:735`). Anti-hallucination id-map: existing[idx] → {"id": str(idx), "text": payload["data"]} (`:743-747`).
- **Phase 2:** `system_prompt = ADDITIVE_EXTRACTION_PROMPT`; `llm.generate_response([sys,user], response_format={"type":"json_object"})` (`:765`); parse `remove_code_blocks → json.loads(...).get("memory", [])` + `extract_json` fallback.
- **Phase 3:** `mem_embeddings = embed_batch([m["text"]...], "add")`.
- **Phase 4/5 per memory:** `mem_hash = md5(text)`; **skip if hash ∈ existing_hashes or ∈ batch seen** (`:826-829`); `text_lemmatized = lemmatize_for_bm25(text)` (spaCy); build payload {data, text_lemmatized, hash, created_at, updated_at, attributed_to}.
- **Phase 6:** `vector_store.insert(...)` batch (fallback 1-by-1); `db.batch_add_history([{event:"ADD",...}])`.
- **Phase 7 entity linking:** `extract_entities_batch → dedup globally → embed_batch → entity_store.search_batch(top_k=1)`; score≥0.95 → merge memory_id into existing entity.linked_memory_ids; else insert new entity row {data, entity_type, linked_memory_ids, *filters}.
- **Phase 8:** `db.save_messages(...)` (keeps last 10 per scope); return `[{"id":uuid,"memory":text,"event":"ADD"}]`.
- Returns `{"results":[...]}`. Async twin (`main.py:2066/2133`) is byte-identical with `asyncio.to_thread`.
- Requires ≥1 of user_id/agent_id/run_id else `Mem0ValidationError VALIDATION_001` (`:318`).
- `infer=False` (`:689`): no LLM, raw transcript storage, embed+`_create_memory` per message verbatim.

### A2. Extraction call — models & params (KNOWN, MEM0.md:82-95)
| Role | Default | Source |
|---|---|---|
| LLM | `gpt-5-mini` | `llms/openai.py:39` |
| LLM params | temp=0.1, max_tokens=2000, top_p=0.1, top_k=1 | `configs/llms/base.py:19-23` |
| Reasoning guard | drops temp/max_tokens for o1/o3/gpt-5; `gpt-5-mini` treated as reasoning; `reasoning_effort` honored | `llms/base.py:43-114` |
| Embedder | `text-embedding-3-small` @ 1536 dims | `embeddings/openai.py:15-19` |
| Vector store | qdrant lib default; pgvector default 1536, HNSW on | `vector_stores/configs.py:9` |
| Anthropic default | `claude-3-5-sonnet-20240620` | `llms/anthropic.py:38` |

`embed()` takes `memory_action ∈ {add,search,update}` (`embeddings/openai.py:37`) — supports **asymmetric embeddings** (query-vs-doc encoders) but OpenAI ignores it.

### A3. `ADDITIVE_EXTRACTION_PROMPT` (KNOWN VERBATIM head, MEM0.md:97-112, `prompts.py:468`, ~470 lines)
- Role: "You are a Memory Extractor … Your sole operation is ADD." Extracts from BOTH user and assistant messages.
- User-prompt inputs (`generate_additive_extraction_prompt`, `prompts.py:1016`): `## Summary`, `## Last k Messages` (truncated to **300 chars** each — `PAST_MESSAGE_TRUNCATION_LIMIT`), `## Recently Extracted Memories` (up to 20), `## Existing Memories` (`[{"id":"uuid","text":..}]` — **used only for dedup + linking, never as extraction source**), `## New Messages`, `## Observation Date`, `## Current Date`.
- **Temporal grounding rule (the non-obvious bit, `prompts.py:528-540`):** resolve "yesterday/last week/recently" against **Observation Date, NOT Current Date** — "User went to Paris last week" → "the week of May 15, 2023" so it stays meaningful forever.
- Dedup delegated to model (`prompts.py:511`): "If new information … is semantically equivalent to an Existing Memory with no meaningful new context, skip it" — the ONLY semantic dedup in V3 beyond md5.
- Linking: emit existing UUID in `linked_memory_ids` on same-entity/updated-preference/continuation/contradiction (`prompts.py:513,694-701`).
- **Output contract** (`prompts.py:918-942`): `{"memory":[{"id":"0","text":"…","attributed_to":"user","linked_memory_ids":["uuid…"]}]}`. `id`=sequential string; `attributed_to ∈ {user,assistant}`.
- **Quality clauses worth stealing:** "Contextually Rich, Not Atomic" (capture transitions: *"switched from almond to oat milk after an almond sensitivity"* not *"prefers oat milk"*, `prompts.py:606-621`); "Preserve Specific Details — Never Generalize" (proper nouns/quantities verbatim, `:640-666`); "No Echo Extraction" (don't re-extract assistant restating user, `:682`); 11 worked examples.

### A4. The dead UPDATE arbitration prompt (KNOWN, MEM0.md:120-159, `prompts.py:176`)
Reproduced because it IS the conflict-resolution logic for volatile facts. Four ops:
- **ADD:** new info not in memory → new ID.
- **UPDATE:** info present but "totally different" → keep same ID, change value. "If the retrieved fact conveys the same thing … keep the fact which has the most information." Merges "cheese pizza" + "chicken pizza" → "cheese and chicken pizza".
- **DELETE:** retrieved facts CONTRADICT memory → delete. ("Loves cheese pizza" + "Dislikes cheese pizza" → DELETE.)
- **NONE:** already present.
Wrapper `get_update_memory_messages` (`prompts.py:406`) demands: `{"memory":[{"id","text","event":"ADD|UPDATE|DELETE|NONE","old_memory":"<only if UPDATE>"}]}`.

> **The id-mapping anti-hallucination trick (BOTH designs, MEM0.md:159):** existing memories presented with integer-string ids "0","1",… mapped from real UUIDs (`main.py:743-747`). The LLM can only echo integer ids; caller translates int→UUID before touching the store. Classic path enforces via "Return IDs from the input IDs only; do not generate any new ID." Stops the LLM inventing a UUID and corrupting an unrelated row.

### A5. Event-apply primitives (KNOWN, MEM0.md:163-184)
- **`_create_memory`** (`main.py:1640`): embed (action="add"), uuid4, payload {data, hash=md5, created_at/updated_at, text_lemmatized}; insert; `add_history(id, None, data, "ADD", ...)`.
- **`_update_memory`** (`main.py:1711`): overwrite-in-place. `prev_value`; new payload **`created_at` preserved, `updated_at=now`**; re-embed (action="update"); `vector_store.update` overwrites both vector+JSON; `add_history(id, prev, data, "UPDATE")`; entity-store reconcile (strip old, relink new). **Destroys the prior value in the vector store** — only SQLite history survives.
- **`_delete_memory`** (`main.py:1776`): `vector_store.delete(id)` (row gone); `add_history(id, prev, None, "DELETE", is_deleted=1)` — **audit row is the only trace left**. Soft-delete is HISTORICAL not RETRIEVABLE.

### A6. Hybrid retrieval (KNOWN, MEM0.md:188-205, `main.py:1152/1373`)
`search(query, top_k=20, filters, threshold=0.1, rerank=False, explain=False)`. Operator grammar: `eq/ne/gt/gte/lt/lte/in/nin/contains/icontains` + `AND/OR/NOT`.
1. lemmatize query + extract query entities.
2. `embed(query,"search")`.
3. **over-fetch** `internal_limit = max(limit*4, 60)`; semantic vector search.
4. `keyword_search` BM25/FTS (None if store lacks it).
5. **BM25 sigmoid normalization** by lemma count: ≤3→(mid5.0,steep0.7), ≤6→(7.0,0.6), ≤9→(9.0,0.5), ≤15→(10.0,0.5), else (12.0,0.5); `norm = 1/(1+e^(-steep·(raw-mid)))`.
6. **entity boost** (`main.py:1473`): dedup query entities (max 8), search entity store (top_k=500, 4 threads); match sim≥0.5 boosts its `linked_memory_ids`. `boost = sim · ENTITY_BOOST_WEIGHT(0.5) · memory_count_weight`, where `memory_count_weight = 1/(1+0.001·(num_linked−1)²)` — entity linked to MANY memories is a WEAKER signal. Per memory, MAX boost across entities kept.
7. **score_and_rank:** threshold gates the **semantic score BEFORE combining** (BM25/entity can't rescue a below-threshold candidate, `scoring.py:111`). `combined = min((semantic + bm25 + entity_boost)/max_possible, 1.0)`, `max_possible = 1.0 (+1.0 if any bm25) (+0.5 if any entity)`.
8. Optional `rerank=True` → `reranker.rerank(...)` (default `reranker=None`).
- `explain=True` returns `score_details` {semantic_score, bm25_score, entity_boost, raw_score, max_possible_score, final_score, threshold} — a free calibration probe.
- `get_all(filters, top_k=20)`: pure filtered list, no scoring.

### A7. History/audit DB (KNOWN, MEM0.md:209-225, `storage.py`)
**Local SQLite** (`~/.mem0/history.db`), global `threading.Lock`, `check_same_thread=False`. Two tables:
- **`history`**: `(id PK, memory_id, old_memory, new_memory, event[ADD|UPDATE|DELETE], created_at, updated_at, is_deleted, actor_id, role)`. Every `_create/_update/_delete` writes exactly one row. `get_history(memory_id)` orders `created_at ASC, updated_at ASC` — **that ordered list IS the per-memory version timeline.**
- **`messages`**: recent-conversation buffer per scope; `save_messages` evicts beyond most-recent **10** per `session_scope`. Mem0's short-term working memory feeding `## Last k Messages`.
- Teardown note: audit lives in SQLite next to app, NOT in Postgres even when vectors are in pgvector.

### A8. pgvector backend (KNOWN, MEM0.md:229-246)
`collection_name="mem0"`, dims 1536, hnsw=True. Schema: `id UUID PK, vector vector(1536), payload JSONB`. ANN: `hnsw (vector vector_cosine_ops)` default; DiskANN if dims<2000+vectorscale. Keyword: `gin(to_tsvector('simple', payload->>'text_lemmatized'))`. Semantic: `vector <=> %s` cosine, score = `max(0.0, 1.0 - distance)` (so threshold 0.1 is on 1-cos_dist). Keyword: `ts_rank_cd(...)`. All filtering is JSONB-path predicates on the single payload column — no dedicated entity columns. Second entity-store = same pgvector class with `collection_name="{collection}_entities"`, payload {data, entity_type, linked_memory_ids:[uuid]}.

### A9. Constants (KNOWN, MEM0.md:266-289)
Add-time existing retrieval top_k=**10**; search over-fetch `max(limit*4,60)`; default search/get_all top_k=20; semantic threshold **0.1**; entity link sim **≥0.95**; entity boost min sim **≥0.5**; ENTITY_BOOST_WEIGHT **0.5**; entity-store boost top_k=500; max query entities 8; recent buffer/last-k=10; last-k truncation 300 chars; dedup md5 exact; api_version v1.1.

### A10. Paper benchmarks (INFERRED-paper, MEM0.md:290)
LOCOMO LLM-as-Judge: Mem0 **66.88±0.15%**, Mem0g **68.44±0.17%**, +26% rel over OpenAI memory. Search p50 **0.148s**/p95 **0.200s**; total p50 **0.708s**/p95 **1.440s**; **~7k tokens/conversation** (Mem0g ~14k); **91% lower p95 latency** and **>90% token cost** vs full-context. Classic: extraction context = summary + m=10 prev messages; update retrieval s=10 similar; ops ADD/UPDATE/DELETE/NOOP via function-calling.

---

## PART B — GRAPHITI

### B0. The one thing: bi-temporal `EntityEdge` (KNOWN, GRAPHITI.md:12-41, `edges.py:263-285`)
Graphiti = **one data structure + one resolution algorithm.** Structure = `EntityEdge`: triple (source_node, relation_name, target_node) + NL `fact` + `fact_embedding` + **FOUR timestamps forming TWO independent timelines.** Algorithm = `resolve_extracted_edge`: on each new fact, hybrid-search existing facts, ask LLM which are duplicates vs contradictions, then write `invalid_at`/`expired_at` so old facts are **superseded, not overwritten.**

| Field | Timeline | Meaning |
|---|---|---|
| `uuid`, `group_id` (graph partition / multi-tenant), `source/target_node_uuid` | — | identity |
| `name` | — | relation name, SCREAMING_SNAKE_CASE |
| `fact` | — | NL sentence |
| `fact_embedding` | — | embedding of fact |
| `episodes` | — | list of episode ids (**provenance**) |
| `created_at` | **T′ system** | when written to system (= t'_created) |
| `expired_at` | **T′ system** | system-time tombstone (= t'_expired) |
| `valid_at` | **T event** | "when the fact became true" (= t_valid) |
| `invalid_at` | **T event** | "when the fact stopped being true" (= t_invalid) |
| `reference_time` | **T event** | episode reference timestamp |
| `attributes` | — | typed custom-edge attributes (Pydantic) |

- **T (event time)** = valid_at…invalid_at ("temporal range during which facts held true").
- **T′ (transaction/system time)** = created_at…expired_at ("when facts are created/invalidated in the system").
- A fact is **currently believed AND currently true** iff `expired_at IS NULL AND invalid_at IS NULL`. The single query the brain reads.
- **Nothing is ever deleted on supersession** — old edge keeps its row, gets invalid_at/expired_at stamped, stays queryable as history. "That is the entire pitch over last-write-wins."
- Stored per-backend: Neo4j relationship vector property; FalkorDB `vecf32`; **Kuzu reified `RelatesToNode_` node** (can't put vectors on relationships). Kuzu proves the plain node/edge-table model — why the Postgres port is clean.

### B1. `add_episode` pipeline (KNOWN, GRAPHITI.md:44-93, `graphiti.py:980-1228`)
One episode in → nodes + bi-temporal edges out. 9 steps:
1. Retrieve previous episodes (`retrieve_episodes`, last_n=RELEVANT_SCHEMA_LIMIT=10).
2. Build/get episode node (valid_at=reference_time).
3. **Extract nodes** (one LLM call, prompt by source: message/text/json) → ExtractedEntity{name, entity_type_id, episode_indices}; in-batch exact-dup collapse.
4. **Resolve nodes** (cosine candidate search → deterministic exact+MinHash/LSH → LLM dedupe residue).
5. **Extract + resolve edges** (5a extract_edges max_tokens 16384; 5b resolve_extracted_edge = invalidation core) → (resolved, invalidated, new).
6. `entity_edges = resolved + invalidated`.
7. Hydrate node attributes/summaries (only new_edges, to avoid re-summarizing).
8. Persist (episode, MENTIONS edges, nodes, edges incl. invalidated).
9. (optional) update_communities (off by default).
- **Concurrency:** `semaphore_gather` with `SEMAPHORE_LIMIT=20` everywhere — the throughput knob.

### B2. Entity extraction (KNOWN, GRAPHITI.md:97-107)
One LLM call. Entity types passed as **integer-indexed list** (type 0 = generic `Entity`, custom types 1..n with docstring as description). Prompt aggressively anti-noise: "NEVER extract abstract concepts, feelings, or generic words"; bans pronouns/generic nouns/bare kinship ("Nisha's dad" not "dad"); demands **most specific form** ("wool coat" not "coat", "Gamecube" not "console"). Speaker always extracted first. **No reflexion/missed-entity retry in v0.29.2** (single-shot; older versions had it).

### B3. Entity resolution — cheapest-first (KNOWN, GRAPHITI.md:111-126)
- **Stage A semantic candidates:** embed name, search NODE_DEDUP_CANDIDATE_LIMIT=15, NODE_DEDUP_COSINE_MIN_SCORE=0.6, no rerank.
- **Stage B deterministic:** (1) exact normalized-name (lowercase+collapse ws); 1 hit→resolved no LLM, >1→escalate. (2) **Entropy gate:** names <_MIN_NAME_LENGTH=6 with <_MIN_TOKEN_COUNT=2 tokens, or Shannon char-entropy <_NAME_ENTROPY_THRESHOLD=1.5 → escalate. (3) **MinHash/LSH fuzzy:** 3-gram shingles, _MINHASH_PERMUTATIONS=32 blake2b, _MINHASH_BAND_SIZE=4 LSH bands; accept if Jaccard ≥ _FUZZY_JACCARD_THRESHOLD=0.9.
- **Stage C LLM fallback:** only residue → `dedupe_nodes.nodes`; returns NodeResolutions, `duplicate_candidate_id=-1` = no dup. Defensive id guardrails.
- `_promote_resolved_node`: generic canonical absorbing a typed duplicate is upgraded to that label (type flows upward on merge).

### B4. Edge/fact extraction (KNOWN+VERBATIM, GRAPHITI.md:130-146, `edge_operations.py:117`)
One LLM call max_tokens=16384. Response: Edge{source_entity_name, target_entity_name, relation_type, fact, valid_at, invalid_at, episode_indices}. Reference time = latest episode's valid_at.
- **Name-based binding:** LLM returns entity NAMES; each validated against ENTITIES list (`name_to_node`); names not in list → edge **rejected**; self-edges dropped. (Keeps LLM from inventing endpoints — analogous to Mem0's int-id trick.)
- valid_at/invalid_at parse failures logged+skipped, never fatal.
- System prompt VERBATIM: *"You are an expert fact extractor that extracts fact triples from text. ... Use each episode's timestamp to resolve temporal references ... REFERENCE_TIME is a fallback ..."*
- Rule 5 fidelity (VERBATIM): *"The `fact` MUST preserve all specific details ... NEVER generalize 'Gamecube' to 'gaming console'..."*
- DATETIME RULES VERBATIM: ISO-8601 Z/UTC; ongoing/present → valid_at=episode ts; change/termination → invalid_at; both null if unstated; date-only→00:00:00; year-only→Jan 1 00:00:00.

### B5. Temporal extraction fallback (KNOWN+VERBATIM, GRAPHITI.md:150-154)
When valid_at/invalid_at come back null, `_extract_edge_timestamps` runs a **separate lightweight LLM call (ModelSize.small)** against `extract_edges.extract_timestamps` — only if still None AND episode has valid_at. Two-path design: most facts timestamped in main call, gaps cost one cheap call. Prompt: *"You extract temporal bounds from facts. NEVER hallucinate dates."* "Do NOT hallucinate or infer dates from unrelated events." Response model EdgeTimestamps{valid_at, invalid_at}.

### B6. Edge resolution / invalidation — THE CORE (KNOWN, GRAPHITI.md:158-223, `edge_operations.py:325-847`)
**Candidate sets (`resolve_extracted_edges`):**
1. In-batch exact dedup: key `(source_uuid, target_uuid, normalize(fact))`.
2. Embed all extracted facts.
3. **Duplicate candidates** = `get_between_nodes(source,target)` (same endpoints) UNION hybrid `EDGE_HYBRID_SEARCH_RRF` filtered to those same-endpoint uuids.
4. **Invalidation candidates** = SEPARATE `EDGE_HYBRID_SEARCH_RRF` over fact text with **NO endpoint filter** (semantically related anywhere); minus anything already in duplicate-candidates.

**The LLM contradiction call (`resolve_extracted_edge`):** fast path first — if related edge has identical endpoints AND normalize(fact) matches verbatim, reuse it (append episode id), no LLM. Otherwise **continuous-indexed** context: existing=dup candidates 0..k-1, invalidation candidates k.. ; one call to `dedupe_edges.resolve_edge` (ModelSize.small) → `EdgeDuplicate{duplicate_facts:list[int], contradicted_facts:list[int]}`.
- Prompt VERBATIM: *"You are a fact deduplication assistant. NEVER mark facts with key differences as duplicates."* "duplicate_facts: ONLY idx from EXISTING FACTS. contradicted_facts: idx from EITHER list." "A fact can be both a duplicate AND contradicted (semantically same but new fact updates/supersedes it)."
- Worked example: "Alice works at Acme as a software engineer" vs "...senior engineer" → duplicate_facts=[], contradicted_facts=[1] (updated title = contradiction NOT duplicate). "Bob ran 5 miles Tuesday" vs "Bob ran 3 miles Wednesday" → neither.

**idx → action:** duplicate → resolved_edge becomes the EXISTING edge (first dup), new episode id appended to its `episodes` — duplicate does NOT create new edge, just gains provenance. contradicted → split by offset into invalidation_candidates.

**THE BI-TEMPORAL ALGEBRA (KNOWN, get-verbatim-right, `edge_operations.py:538-573,826-839`):**
- (a) New edge invalidated by a more-recent contradicting fact: if a candidate has `valid_at > resolved_edge.valid_at` → `resolved_edge.invalid_at = candidate.valid_at; resolved_edge.expired_at = now` (new edge born already-invalidated).
- (b) Old edges contradicted by new: `resolve_edge_contradictions` — skip if ranges don't overlap-conflict; elif `edge.valid_at < resolved_edge.valid_at` → **`edge.invalid_at = resolved_edge.valid_at; edge.expired_at = now`**.
- **The rule plainly:** `old.invalid_at = new.valid_at; old.expired_at = now()`. Event-time end of old fact glued to event-time start of new fact; system-time tombstone = now. **Temporally-disjoint facts COEXIST** (invalidation only fires on range-conflict) — it's a HISTORY, not a latest-value cache. Paper confirms: "invalidates the affected edges by setting their t_invalid to the t_valid of the invalidating edge."

### B7. Embeddings (KNOWN, GRAPHITI.md:227-232)
Default dim **1024** (`EMBEDDING_DIM` env, frozen). Truncated to embedding_dim at client. OpenAI default `text-embedding-3-small`; Voyage default `voyage-3`. **Two embedders' worth per graph:** name-vectors on nodes, fact-vectors on edges. Node search uses name vectors; edge/fact search uses fact vectors.

### B8. Search / hybrid retrieval (KNOWN, GRAPHITI.md:236-255)
- Methods: cosine_similarity, bm25, bfs (breadth-first graph). Rerankers: rrf, mmr, node_distance, episode_mentions, cross_encoder.
- Defaults: DEFAULT_SEARCH_LIMIT=10, RELEVANT_SCHEMA_LIMIT=10, DEFAULT_MIN_SCORE=0.6, DEFAULT_MMR_LAMBDA=0.5, MAX_SEARCH_DEPTH=3, MAX_QUERY_LENGTH=128.
- **RRF:** `score[uuid] += 1/(i + rank_const)`, rank_const=1.
- **MMR:** `mmr = λ·dot(query,cand) + (λ-1)·max_sim_to_selected`, λ=0.5 (COMBINED recipe overrides λ=1).
- **node_distance:** rerank by graph hop-distance from center, score=1/distance, center pinned 0.1.
- **episode_mentions:** RRF then re-sort by count(MENTIONS).
- **cross_encoder default = boolean-classifier-with-logprobs trick:** model gpt-4.1-nano, prompt "Respond with 'True' if PASSAGE is relevant ... else 'False'", temp=0, max_tokens=1, logit_bias on True/False token ids, logprobs=True; score = exp(logprob) of True token. Alternatives: BGE, Gemini.
- Recipes: COMBINED_HYBRID_SEARCH_RRF, COMBINED_HYBRID_SEARCH_CROSS_ENCODER (slowest/highest quality, +bfs), **EDGE_HYBRID_SEARCH_RRF (the recipe used internally by resolve_extracted_edges for dup+invalidation candidate search — ingestion and retrieval share retrieval code).**

### B9. Models / structured output / retries (KNOWN, GRAPHITI.md:259-275)
LLM base temp=0 (config default is 1; abstract client uses 0); max_tokens=16384; OpenAI default `gpt-5.5`, small `gpt-4.1-nano`; OpenAI MAX_RETRIES=2; Anthropic default `claude-haiku-4-5-latest`; tenacity `wait_random_exponential` retry on server/empty-response; optional file LLM cache keyed by hash(messages+model); two model sizes (small for dedup/timestamps/attributes, medium for extraction).
- **Structured output:** OpenAI native response_format/parse; **Anthropic forced tool-use** — `_create_tool` from `response_model.model_json_schema()`, `tool_choice={'type':'tool','name':...}`, JSON-from-text fallback.

### B10. Bulk path (KNOWN, GRAPHITI.md:279-281)
`add_episode_bulk`: union-find with path compression across batch, CHUNK_SIZE=10, edge dedup min_score=0.6. **Edge invalidation + date extraction run in bulk too** — same `extract_edges→resolve_extracted_edges`. Bulk is NOT a skip-invalidation fast path; same semantics batched.

### B11. Storage / index DDL (KNOWN, GRAPHITI.md:285-296)
Node labels: Entity, Episodic, Community, Saga. Edges: RELATES_TO, MENTIONS, HAS_MEMBER, HAS_EPISODE/NEXT_EPISODE. Neo4j range indices: `[:RELATES_TO] ON (uuid, group_id, name, created_at, expired_at, valid_at, invalid_at)` — **all four bi-temporal fields indexed on the fact edge.** Full-text: node_name_and_summary, edge_name_and_fact.

### B12. Node summary + attribute hydration (KNOWN+VERBATIM, GRAPHITI.md:436-457)
Step 7 of add_episode: two LLM passes per node both ModelSize.small, parallel under SEMAPHORE_LIMIT=20.
- **Pass A typed-attribute:** short-circuit — if entity type has zero declared Pydantic fields → returns {}, NO LLM call. Generic Entity skips entirely; only custom-typed entities pay. `apply_capped_attributes` merges (capped to avoid unbounded growth).
- **Pass B summary:** `should_summarize_node` callback can skip (host cost-control hook). **Fact-append shortcut:** if node has short summary, append edge facts `'\n'.join(edge.fact...)`; if `len(summary_with_edges) <= MAX_SUMMARY_CHARS*2` (≤2000 chars) use concatenation WITHOUT LLM. Only on overflow call LLM. Result truncated at sentence boundary to MAX_SUMMARY_CHARS=1000.
- `summarize_context` VERBATIM: "...only use information from the provided MESSAGES... If the value... cannot be found... set the value of the property to the Python value None."
- **`summary_instructions` VERBATIM (10 rules, the quality bar):** "1. Output only factual content. Never explain what you're doing... 3. ...STATE FACTS DIRECTLY IN UNDER 1000 CHARACTERS. 8. Never use filler verbs like 'mentioned', 'described', 'stated', 'reported', 'noted', 'discussed', 'referenced', or 'indicated' unless the communication act itself is the fact. 10. Begin with the entity name or a direct fact, not with 'A', 'An', 'The', or 'This is'..." BAD/GOOD worked example.
- `summarize_pair`: when two nodes merge, fuse summaries "into a single information-dense summary" — dedup non-lossy at summary level.

### B13. dedupe_nodes prompt (KNOWN+VERBATIM, GRAPHITI.md:459-464)
System: "You are an entity deduplication assistant. NEVER fabricate entity names or mark distinct entities as duplicates." **Count guardrail (load-bearing):** "ENTITIES contains N entities with IDs 0 through N-1. Your response MUST include EXACTLY N resolutions with IDs 0 through N-1." — why host code can zip resolutions back; missing/extra defensively ignored. Examples: NYC→New York City IS dup; Java language vs Java island NOT dup.

### B14. Async-ingest worker + failure paths (KNOWN, GRAPHITI.md:466-489)
Production FastAPI ingest = **single-consumer asyncio queue**. `POST /messages` does NOT process inline — wraps `add_episode` in partial, `queue.put`, returns 202. **Queue serialized (one episode at a time)**; intra-episode concurrency from SEMAPHORE_LIMIT=20 inside add_episode. **This ordering guarantee matters for invalidation correctness** — parallel contradicting episodes could race the supersession algebra. Failure paths: bad timestamps → field left None, never fatal; LLM transient → tenacity retry MAX_RETRIES=2; malformed dedup ids → defensively dropped → "no duplicate"; **worker cancellation is the only clean exit — any other exception kills the consumer (known fragility, no per-job try/except).**

### B15. Benchmarks (INFERRED-paper, GRAPHITI.md:428)
DMR 94.8%/98.2%, LME +18.5%, ~90% latency cut. (Paper used gpt-4-turbo/gpt-4o-mini, differ from OSS defaults — not reproducible from code.)

---

## PART C — JUDGMENT vs VERSO MEMORY

Verso already ships: typed 4-tier, temporal, RRF recall, recall_as_of (time-travel), reflect() consolidation, ADD-only with supersede-invalidates, bounded, multiple backends. Verso DEFERS the graph backend by design.

### verso-already-has
- **ADD-only with supersede-invalidates** = Mem0 V3's exact posture (ADD-only, never silent-overwrite) AND Graphiti's invalidation posture. Verso's "supersede invalidates" matches Graphiti "nothing deleted on supersession" without the graph.
- **Temporal + recall_as_of (time-travel)** = Graphiti's bi-temporal "what was true on date D" query and Mem0's per-memory version timeline.
- **RRF recall** = both Mem0's hybrid score blend and Graphiti's RRF reranker (`1/(i+rank_const)`).
- **reflect() consolidation** = Graphiti's node-summary hydration / Mem0's procedural-memory summarization.
- **Bounded memory** = Mem0's recent-message-buffer eviction (keep last 10) / Graphiti's capped attributes + MAX_SUMMARY_CHARS.
- **Audit/version timeline** = Mem0's history table ordered ASC.

### steal-additive (HIGH BAR; additive + byte-identical-when-unused + not a NON-GOAL)
- **Extraction-prompt quality clauses as optional helpers** (NOT a pipeline): "Contextually Rich, Not Atomic" (capture transitions, not atomized prefs), "Preserve Specific Details — Never Generalize" (Gamecube not console), "No Echo Extraction", and Graphiti's anti-filler-verb `summary_instructions` (ban "mentioned/stated/noted unless the act IS the fact"; begin with entity name; state facts directly under N chars). These are prompt-string assets for `reflect()`/memory-write — pure additions, zero cost when unused.
- **Temporal grounding against Observation-Date-not-Current-Date** (Mem0 `prompts.py:528-540`): rewrite "last week"→"week of May 15 2023" at write time so the stored fact stays meaningful forever. A write-time normalization helper; additive, on-thesis for a temporal memory.
- **The integer-id / name-binding anti-hallucination rail** (Mem0 int-id map; Graphiti name-in-ENTITIES validation): when a memory-mutation tool lets the model reference existing rows, present synthetic indices and reject real ids — stops the model corrupting an unrelated row. A bounded safety helper for any "edit existing memory" tool path.
- **`explain=True` score_details** (Mem0): return per-result {semantic, bm25, entity_boost, raw, max_possible, final, threshold} as an optional debug field on recall — a free calibration probe that pairs with Verso's evals/calibrate. Additive, off by default.
- **Serialize-per-scope ingest ordering** (Graphiti): the explicit insight that contradicting writes within one scope MUST be serialized or supersession races. Relevant to the durable seam's concurrency story; a documented invariant, not new machinery.

### avoid-overkill (real but complexity Verso should refuse)
- **Graphiti's full bi-temporal 4-timestamp edge + LLM contradiction-resolution + node/edge graph backend** — this is the graph Verso explicitly defers. Two timelines, `resolve_extracted_edge`, per-backend vector storage (Neo4j/FalkorDB/Kuzu), communities, sagas, BFS recursive CTE. Powerful but it IS "force the graph." Verso's recall_as_of + supersede gets the 80% answer without it.
- **Mem0's entity-store + entity-boost re-ranking** (second vector table, spaCy NER, memory_count_weight math) — a +0.5 nice-to-have boost signal, heavy dep, ~1% lift territory.
- **Two-model split + per-task ModelSize routing** — a cost knob, not correctness; Verso's per-call model swap already covers the need without a routing cult.
- **spaCy lemmatization/NER for BM25** — heavy Python dep; Verso's RRF doesn't need a lemmatizer sidecar.
- **Mem0g / Neo4j/Memgraph/Kuzu/AGE graph providers; Graphiti community detection (label propagation), sagas** — explicitly out of scope; graph-DSL territory.
- **Mem0's split SQLite-history-beside-pgvector** — a deployment wart the teardown itself says NOT to port (fold into one store). Verso's single event-sourced store is already better.

### Leanness signal
Both sources strongly SUPPORT the lean thesis from opposite directions: Mem0's own HEAD **collapsed from two LLM calls to ONE and made the famous arbitration prompt dead code** (less machinery won in production), while Graphiti's value is admittedly "one struct + one algorithm, everything else is plumbing" — and the teardown's own port advice repeatedly says skip communities, skip sagas, skip the two-model split, skip the entity boost as ~1% extras. The graph IS powerful for "as-of-when" history, but it's exactly the complexity Verso deliberately defers; the prompt-quality clauses and write-time temporal grounding are the only genuinely additive, byte-identical-when-unused steals.
