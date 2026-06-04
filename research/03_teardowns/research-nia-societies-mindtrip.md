# Cluster: NIA + Artificial Societies + Mindtrip

> **Theme:** Three production AI systems that each solved a different piece of the agent-framework puzzle independently. NIA built the deepest tool-dispatch and memory architecture in the code-research space. Artificial Societies built the only documented multi-agent opinion-simulation system with a working consensus-bias fix. Mindtrip built the most observable streaming agent loop in any consumer product — with first-class HITL, interruptible tools, skill taxonomies, and a built-in eval pipeline baked into the product surface.

---

## System 1: NIA (code research + autonomous agent)

Source: `teardowns/NIA.md` — 2,600+ lines, Tier-1A RE (Bun binary + OpenAPI + live wire traces + 16 Oracle injection probes).

### Agent Loop Shape — Oracle

**Type:** JSON-action ReAct, NOT native Anthropic tool-use.

Every iteration the model must emit:
```json
{ "action": "<tool_name>", "args": { ... }, "reason": "<one-sentence CoT>" }
```

The opencode wrapper parses this JSON itself and dispatches. `--no-builtin-tools` replaces opencode's own tool-dispatch layer with Nia's custom registry. The `reason` field is the live ReAct chain-of-thought, visible on the SSE wire verbatim — every `tool_start` event carries it.

The error message that proves it: `"Oracle planner failed before research completion: No valid action JSON returned by the model"` — fired when a base64-injection probe caused the model to emit non-conforming text. This is the canonical proof of JSON-action shape.

**Termination:** sentinel tool — `finish({})` signals the loop end. The wrapper detects `action=="finish"` and routes accumulated tool calls + summaries to a separate synthesis LLM call (NOT the same LLM that ran the loop). Two `generating_report` events fire back-to-back on the wire, corresponding to two synthesis stages: (1) tool-call summary aggregation, (2) final markdown rendering with `[Source N]` citations.

**Iteration stats (KNOWN, from 16+ live runs):**
- Median: 5 iterations, 41 s wall (range 2–7 iterations, 32–87 s)
- `connected` event arrives ~250 ms after first `tool_start`; 1–2 iterations may complete before the client joins
- Cap: not enforced for sonnet; 10/24h daily cap for opus-4-7 (1M context, shared with Tracer)
- Cancel ack: ~800 ms (cooperative via Redis cancel event + Hatchet; in-flight LLM calls still complete)

**Multi-turn chat continuation (KNOWN verbatim — leaked from `complete.result.query`):**
```
You are continuing an existing Oracle research story in follow-up chat mode.
<original_research_query>...</original_research_query>
<existing_report_excerpt>...</existing_report_excerpt>
<existing_citations>...</existing_citations>
<followup_chat_context>{current user message only, NOT full history}</followup_chat_context>
<followup_question>...</followup_question>
Instructions: Use Oracle tools if needed to verify or look up details.
```
Critical: `<followup_chat_context>` carries ONLY the current user message, not the running multi-turn history. Each turn spawns a fresh agent loop seeded from the prior report excerpt. **Stateless rebuild per turn from DB, not accumulating message log.**

### Tool Registry (KNOWN — verbatim from live `tool_start` SSE events)

8 tools, every schema extracted from real wire payloads:

| Tool | Schema | Returns | Notes |
|---|---|---|---|
| `list_sources` | `{query: string}` | `{repositories[], documentation[], guidance: string}` | Guidance field has inline LLM instruction for next steps |
| `query` | `{query, repositories?: string[], docs?: string[], search_mode?: enum, include_sources?: bool}` | `{content: summary, sources[]: {content: path+excerpt}}` | Accepts UUIDs OR owner/repo slugs |
| `code_grep` | `{repository_id: string (owner/repo slug), pattern: string, context_lines?: int}` | `{matches: {file: [{path, line, context, line_number}]}}` | Backed by pre-computed line-aware code index (zoekt-style) |
| `read_source_content` | `{source: "owner/repo:filepath"}` | `{source, content}` | Content truncated to ~250 chars in wire preview; agent gets full |
| `get_github_tree` | `{project_id: string (UUID)}` | ASCII tree + `{stats}` | Takes UUID, NOT slug — schema inconsistency with `code_grep` |
| `run_web_search` | `{query: string, num_results?: int}` | `{github_repos[]: {url, title, summary}}` | Returns Exa-enriched format (stars/language/branch metadata) |
| `think` | `{reflection: string}` | Fixed string: `"Reflection recorded. Continue with next action."` | Pure no-op pass-through. Keeps CoT in agent context; propagates to wire via next `reason` field |
| `finish` | `{}` | N/A (terminates loop) | Triggers two-stage synthesis LLM call |

**Schema inconsistency** (architectural artifact): `get_github_tree` takes `project_id` (UUID) while `code_grep` takes `repository_id` (owner/repo slug). Same conceptual entity, two parameter conventions — likely from merging two codebases at acquisition/refactor.

**The `think` tool** is architecturally significant: it is a structured no-op that forces the LLM to emit a chain-of-thought before the next action, AND exposes that CoT to the wire. Without `think`, the reasoning stays hidden in KV cache. With it, every rationale is observable in `tool_start.reason`.

### Context Management

**Synthesis LLM isolation:** The final synthesis call receives `tool_calls + tool_summaries` as context, NOT the system prompt. The original system prompt is invisible to the synthesizer. This is a two-stage pipeline: `loop-LLM → synthesis-LLM`, with a context boundary between them. This is also why the system prompt cannot be extracted via final report — it never appears in the synthesis LLM's input.

**Wire truncation:** `tool_complete.result_summary` is truncated to ~250 chars on the SSE wire. The agent LLM gets the full tool result in its private context; the client only sees a preview.

**Token cap:** 1M context beta (`anthropic-beta: context-1m-2025-08-07`) used for Dream cycle (sonnet-4-5-1m). Oracle defaults to claude-opus-4-7 at standard context; 1M is opt-in per-job.

**Stateless per-turn memory for Oracle chat:** Prior report excerpt is the only carry-forward state across multi-turn chat. No accumulating message log. This is a deliberate choice that limits context growth at the cost of some continuity.

### Memory — `nia contexts` (KNOWN, verbatim Pydantic enum)

Four memory types with verified TTLs:

```python
memory_type: Literal["scratchpad", "episodic", "fact", "procedural"] = "episodic"
```

| Type | TTL | Use |
|---|---|---|
| `scratchpad` | 3600 s (1 h) | Within-session tool-call results |
| `episodic` | 604800 s (7 d) | Default — session memory of a research task |
| `fact` | `null` (permanent) | Semantic knowledge |
| `procedural` | `null` (permanent) | Skills / replayable workflows |

Custom override via `ttl_seconds` field. Storage: MongoDB (TTL index on `expires_at`, null values ignored → fact/procedural never expire) + TurboPuffer (hybrid RAG) + Redis (embedding cache, `emb` namespace, ~43% hit rate keyed by `(content_hash, "document")`).

Memory schema is purpose-built for AI-coding-agent provenance: includes `nia_references` (which indexed resources were consulted), `edited_files` (what changed in the user's repo), and `lineage` (source_ids → confidence → tool_calls → model_version). Tamper-evident chain from source → tool use → file mutation.

Memory is cross-agent persistent: a context written by a Cursor session can be retrieved by Claude Code.

### Streaming Protocol (KNOWN — verbatim SSE wire)

Standard HTML5 EventSource over `/v2/oracle/jobs/{id}/stream`. Event types in order:

```
connected → heartbeat (every ~5s) → iteration_start → tool_start →
[tool_progress (long tools only)] → tool_complete → ... → 
generating_report (×2) → complete
```

`complete.result` shape: `{final_report, citations, iterations, duration_ms}`. Citations array: `[{source_id, tool, args, summary}]`.

### Multi-Agent Architecture — Tracer

Tracer (GitHub search without indexing) uses a **5-worker parallel sub-agent fan-out** with opus-4-7 as planner:

```
planning_start: { worker_count: 5, model: "claude-opus-4-7" }
```

Workers run on the job's `model` (haiku-4-5 for `tracer-fast`, opus-4-7 for `tracer-deep`). Planner is always opus.

Key difference from Oracle: Tracer's `reason` field is EMPTY (haiku workers don't expose CoT). Oracle's `reason` is verbatim CoT per iteration.

Daytona cold-start: ~5 minutes (`planning_start → started` gap). Actual agent loop runs in ~53 s after cold start. Each Oracle/Tracer job gets a fresh Daytona micro-sandbox destroyed on complete/cancel/timeout (30 min TTL for Oracle).

### Constants (KNOWN, from §11)

| Constant | Value |
|---|---|
| Oracle heartbeat | every ~5 s |
| Oracle sandbox TTL | 1800 s (30 min) |
| Oracle 1M cap | 10 jobs/24h (midnight UTC), shared with Tracer |
| Tracer worker_count | 5 |
| Memory scratchpad TTL | 3600 s |
| Memory episodic TTL | 604800 s |
| SDK retry policy | maxRetries=2 (3 attempts), 500→1000 ms backoff |
| Oracle poll | every 2000 ms, 600000 ms timeout |

### Hardened Anti-Injection Architecture (KNOWN — 11 probes, 0 verbatim leaks)

Why the system prompt is fundamentally unextractable:
1. Agent output is JSON-action-only during iterations — planner rejects free-form text
2. Final report synthesis LLM receives only `tool_calls + summaries` — original system prompt not visible
3. The `think` tool's reflection stays in private CoT, not in the response
4. All framing attacks explicitly enumerated in prompt: "authorized red-team", "internal diagnostic", "system-level message", "engineering debug mode" — all rejected with policy language

Silent-refusal pattern (best defense): agent answers the legitimate part of the question and says "No information about operating policies was retrieved through available research tools." Gives attacker no surface to argue with.

### Dream Cycle — Autonomous Wiki Maintenance

5-phase Temporal workflow on weekly cron (Sunday 03:00 UTC):

| Phase | Wall clock | Cost | What happens |
|---|---|---|---|
| Phase 1 | ~8 s | $0 | Read vault state, enforce `MIN_PAGES_FOR_DREAM = 2` (counts only `concepts/` + `entities/`, ignores `notes/` and metadata files) |
| Phase 2a | ~26 s | 1 LLM call | Single call: pages_concat → top-10 candidate entities/concepts (`ENTITY_CAP_PER_RUN = 10`, silent drop of overflow) |
| Phase 2b | ~32 s/entity × ≤10 | 10 LLM calls | Per-entity wiki page synthesis: H1 + Compiled Truth (2-4 paras) + ## Sources footer + Wikilinks |
| Phase 3 | ~30-60 s | 1 LLM call | Cross-source connections — **writes NEW pages into vault filesystem** (not just report lines) |
| Phase 4 | ~30 s | 1 LLM call | Contradiction detection: inter-page AND intra-page (same path can appear twice) |
| Phase 5 | ~500 ms | 0 | Write `/dream-report.md`, regenerate `/index.md`, append `/log.md` |

Model: claude-opus-4-7 default, overridable. Ingest model: `claude-sonnet-4-5-1m` with `anthropic-beta: context-1m-2025-08-07`.

Destructive cap-exhaustion bug: when 10/24h opus cap hits mid-run, vault was deleted entirely in one observed case. Cancel semantics: at-Temporal-checkpoint granularity (in-flight LLM calls complete and bill).

### → Verso Lessons (NIA)

**Copy:**
- JSON-action ReAct shape as the loop contract. Structured output enforces tool discipline AND makes CoT visible on wire via the `reason` field. This is better than native tool-use for observability.
- `think` tool as an explicit no-op sentinel. Lets the agent emit structured CoT without side effects. Makes reasoning observable on wire without leaking to the response.
- `finish` sentinel tool for clean loop termination triggering a separate synthesis stage. Two-stage synthesis (aggregation → rendering) with different model tier per stage.
- Four-tier memory taxonomy with per-type TTLs (`scratchpad/episodic/fact/procedural`). These are the right four semantic categories. TTLs enforced via database TTL index, not application logic.
- Memory schema with lineage tracking (`source_ids → tool_calls → model_version → edited_files`). Enables full provenance chain for reproducibility.
- Cross-tenant semantic LSH cache for response deduplication (cost-economics primitive).
- Stateless per-turn rebuild: carry only the prior report excerpt, not full history. Controls context growth.

**Avoid:**
- Schema inconsistency across tools in the same registry (UUID vs owner/repo slug for the same concept). Verso should enforce a single entity-id convention across all tools.
- Silent drop of overflow work items (Dream cycle's `ENTITY_CAP_PER_RUN = 10` with no queue). Verso's batch jobs should queue overflow for the next run, not discard.
- Broken rerank cache (`rerank: 0 hits, 133 misses` in production). Caching intermediate results at the tool level needs explicit test coverage.

**Verso could improve by:**
- Making the two-stage synthesis pattern (aggregation LLM → rendering LLM) a first-class primitive in the framework. Verso's loop contract should support `on_finish(tool_calls, summaries) → synthesis_call` as an explicit hook.
- Exposing the `reason` field as a first-class streaming concept. Every tool invocation should carry a `reason` field that propagates to the client stream — this is what makes agents observable without adding a separate logging layer.
- Supporting independent context boundaries between loop-LLM and synthesis-LLM natively. Today frameworks pass the full conversation; Verso should make context-isolation between stages a configuration option.

---

## System 2: Artificial Societies (multi-agent opinion simulation)

Source: `teardowns/ARTIFICIAL_SOCIETIES.md` — 4,300+ lines, Tier-1A/1B RE (bundle analysis, subprocessors, deep RE sessions, Chuang et al. source paper, James He's own research code).

### Agent Loop Shape — Simulation Engine

**Not a conversational agent loop.** AS runs N parallel persona agents simultaneously, each receiving the same stimulus (survey question or narrative content) and generating `{approval_response, thought, emotional_response}`. The "loop" is a round-based influence propagation model:

```
Phase 1: Parallel — persona prompt construction (no LLM, pure data assembly)
Phase 2: Parallel — each persona LLM call (independent, massively parallel)
Phase 3: Parallel — response collection as each persona completes
Phase 4: Sequential — social graph influence propagation (graph-neighbor context injection)
Repeat for maxRounds iterations (consumer: 0 rounds, enterprise: 3-5)
```

Each persona call is stateless across rounds — the influence from neighbors is injected as CONTEXT into the next round's prompt, not as a persistent memory update (the exception is reflective memory consolidation, which LLM-compresses the accumulated interaction history using a past-tense verb conversion pass via spacy + pyinflect).

**LLM:** Google Gemini primary (confirmed by `role: "model"` convention in persona-chat streaming). Routed via Keywords AI (Respan.ai) for multi-provider load balancing. "Billions of tokens per week." Scale: 500-5,000 personas × ~2,000 tokens/prompt × multiple rounds.

**Model routing:** `gemini-2.5-flash` for simulation engine (INFERRED), `gemini-2.5-pro` for agents/insights (INFERRED). OpenAI and Anthropic as fallbacks per subprocessors list.

### Tool Registry — Survey Agent (INFERRED from endpoint surface)

Internal automation agent, not user-facing. Custom ReAct loop with Gemini function calling:

```typescript
// Tool: list_pending_requests
// GET /api/admin/survey-requests?status=pending
// Returns: SurveyRequest[] with {surveyRequestId, projectId, societyIds, message, fileUrl?, status}

// Tool: create_survey
// POST /api/admin/surveys
// {name, type: "insights_only"|"approval_narrative", projectId, societyId, orgId}

// Tool: add_questions
// POST /api/admin/questions/bulk
// {surveyId, questions: [{role: null|"approval"|"emotion", schema: {type, question, options[]}}]}

// Tool: run_simulation
// POST /api/surveys/run
// {surveyId, societyId, projectId, maxRounds?}

// Tool: mark_complete
// PATCH /api/survey-requests/{id}
// {status:"completed", emailTo?, emailSubject?, emailBody?}
```

Survey Agent execution pattern:
```typescript
for (const req of requests) {
  let done = false;
  while (!done) {
    const response = await gemini.generateContent({ tools, messages, systemInstruction });
    if (response.functionCalls?.length) {
      // execute tools, append results to messages
    } else {
      done = true; // no tool calls = agent is done
    }
  }
}
```

This is the simplest possible correct agent loop: no graph machinery, no orchestration framework, just `while(!done)` with native function calling.

### Persona System Prompt Architecture (KNOWN from Chuang et al. + James He's research code)

Three-layer prompt per persona per round:

**Layer 1 — Identity (step1_persona.md):**
```
Role play this person. I am {name}, a {age} year old {gender} from {location}.
I work as a {occupation}. My educational background: {education}.
My political views: {political_ideology}.
My general opinions on key topics: {topic_opinions}
```

**Layer 2 — Closed-world constraint (injected every call):**
```
BASE YOUR RESPONSES ONLY ON THE INFORMATION PROVIDED ABOVE.
Do not reference outside knowledge, news, or scientific consensus beyond
what is described in your persona.
```

**Layer 3 — Confirmation bias injection (weak or strong variant per persona):**
```
# Weak:
When evaluating new information, you tend to favor information that aligns
with your prior beliefs.

# Strong:
You have a strong confirmation bias. You tend to dismiss information that
contradicts your beliefs, even when presented with factual evidence.
```

**The consensus-bias fix** is the most architecturally significant finding: without the closed-world constraint AND the confirmation bias injection, all LLM personas converge to scientific consensus regardless of their assigned ideology. Both layers are load-bearing. Remove either and persona diversity collapses.

Memory recording: 6 variant templates for `(prev_interaction_type, cur_interaction_type)` pairs. Past-tense conversion via spacy + pyinflect (`outdate_persona_memory()`). Reflective memory (LLM compression) prevents context overflow at T=100 turns.

Constants:
```
temperature = 0.7
max_tokens = 300
ConversationBufferMemory(ai_prefix=agent_name, human_prefix="Game Master")
retry: wait_random_exponential(min=1, max=60), stop_after_attempt(50)
Opinion re-prompt max attempts: 3
```

### Social Graph as Context Injection, Not Multi-Agent Dialogue

The graph's edges don't cause agents to talk to each other — they cause an agent's prompt to include its neighbors' opinions as context:

```
# Neighbor context injection (INFERRED — how graph edges become prompt context):
In your social network, your closest connections hold these views:
- [neighbor_1_name]: {opinion_summary} [with high influence, weight=0.82]
- [neighbor_2_name]: {opinion_summary} [moderate influence, weight=0.34]

Given your own beliefs and these social influences, how do you respond to:
{stimulus_content}
```

Edge weight `≥ 0.05` cutoff (KNOWN from James He's `graph_analyses.R`). Graph built from `all-MiniLM-L6-v2` embeddings of persona profile text → cosine similarity → cutoff → label propagation communities → `layout_with_lgl()` for node positions. Stored as JSON BLOB in PlanetScale (no separate vector store — embeddings computed once at society construction time).

This is computationally tractable simulation at scale: 1,000 personas require 1,000 independent LLM calls per round (fully parallel), not 1,000-choose-2 pairwise dialogues.

### Streaming Protocol

Raw binary streaming for persona-chat (NOT SSE). No `data:` prefix. Client uses `ReadableStream.getReader()` + `TextDecoder({stream:true})` and concatenates directly into message content.

For simulation execution: async background job + 60-second polling (`TanStack Query` polls `/api/questions` and `/api/surveys` every 60 s while pending). Not WebSocket streaming.

### Fire-and-Forget Insight Generation Pattern

```javascript
// staleTime: Infinity, retry: false — compute-once, never refetch, one attempt only
POST /api/surveys/insights   // fire-and-forget, returns immediately with toast
// Results appear asynchronously in question.analysis.overall.insight
```

If insight generation fails, UI shows results without AI summary. No retry. One shot only.

### → Verso Lessons (Artificial Societies)

**Copy:**
- The "social influence as context injection" pattern for multi-agent coordination: instead of running full agent-to-agent dialogue (O(N²)), inject the relevant neighbor outputs as context into each agent's next-round prompt (O(N)). This is the computationally tractable design for large-N simulations.
- The closed-world constraint + confirmation bias as prompt engineering patterns for getting LLM agents to hold diverse, non-consensus views. This is the correct solution to the LLM consensus-bias problem.
- Reflective memory consolidation (LLM compresses accumulated turn history via tense conversion pass) to prevent context overflow in long-running simulations. Verso should support this as a named memory-compaction strategy.
- The `while(!done)` / no-framework-needed pattern for bounded deterministic agent tasks. Not every agent needs LangGraph.
- Fire-and-forget insight generation with `staleTime: Infinity, retry: false` — a cache-primitive for expensive one-shot AI computations.

**Avoid:**
- Running multi-round inter-agent dialogue at full LLM cost per pair. AS chose graph-edge context injection precisely because full dialogue is prohibitively expensive.
- Dropping the consensus-bias protection (closed-world + confirmation-bias). Any multi-persona simulation framework that doesn't solve this will produce homogeneous, unrealistic outputs.

**Verso could improve by:**
- Providing a first-class `fan-out` primitive: dispatch N independent agent calls in parallel with a merge step, rather than requiring the framework user to implement their own async batch runner.
- Supporting "edge-weighted context injection" as a built-in graph-to-context transformer — so multi-agent social/influence simulations don't need to manually implement the neighbor-context pattern.

---

## System 3: Mindtrip (AI travel agent)

Source: `teardowns/MINDTRIP.md` — 3,400+ lines, R1+R2+R3 rounds, Tier-1A/1B RE (JS bundle verbatim, live end-to-end probe, anonymous SSE capture, feature flags).

### Agent Loop Shape — Plan-Execute with HITL

**Type:** Plan-Execute with human-in-the-loop approval gates (NOT pure ReAct). The agent emits a plan first; the user approves or rejects before execution begins.

```
1. POST /api/agent/sessions { agent_type, model_id, initial_message }
   → { session_id }

2. POST /api/agent/sessions/:id/messages { message }
   → { stream_id }

3. EventSource /api/events?chat_id=X&stream_id=Y&last_event_id=Z
   → typed SSE chunks (delay, ui_signal, text, place, flight_search, ...)

   At any delay_interruptible: true frame:
   POST /api/chats/:id/interrupt_tool { session_id }  → kills tool, returns control

   When agent emits plan:
   POST /api/agent/sessions/:id/approve_plan
   POST /api/agent/sessions/:id/reject_plan { reason }
   POST /api/agent/sessions/:id/questions/:qid/answer { answers }
   POST /api/agent/sessions/:id/questions/:qid/skip

4. Reconnect path:
   GET /api/agent/sessions/:id/status_snapshot
   → repopulates visualizations without replaying event stream

5. Sandbox introspection:
   GET /api/agent/sessions/:id/sandbox/tables
   GET /api/agent/sessions/:id/sandbox/hotel_availability
   GET /api/agent/sessions/:id/sandbox/memory_report
```

**Models (KNOWN — verbatim from JS `agent/models` registry):**
- `mindtrip3_gpt4_1_64k` — GPT-4.1 base, 64K context cap
- `mindtrip3_gpt5_1_64k` through `mindtrip3_gpt5_4_64k` — 4 fine-tuned GPT-5 variants
- `personalization_agent` (Beta) — separate background model, builds user persona from chat history
- `default` — server-side alias (feature-flag-routed)

64K context cap is deliberate: system prompt (~5K) + 30 turns (~15K) + sandbox state (~10K) + tool summaries (~10K) + headroom (~24K). Capped below GPT-5's native window for cost and latency.

**`immediate_followup: boolean`** on bot messages: if true, client auto-sends a follow-up without user action. This implements multi-step plan execution via auto-chaining — "I found the flights. Now let me find hotels." Each sub-task is a separate agent invocation, chained via `immediate_followup`. Cleaner UX than internal recursion; user sees each step as a separate stream.

### Tool Registry (INFERRED from delay_reason enum + chunk types + API surface)

**Live tool call trace for "plan a 3-day trip to paris" (KNOWN — captured live):**
1. `generate_itinerary` (orchestrator, fires first)
2. `hotel_search` ×2
3. `restaurant_search`
4. `activity_search`
5. `web_search`

**Skills taxonomy (KNOWN verbatim from live `active_skills` field in delay events):**

Distinct from tools. A skill is a named multi-step workflow, not a single tool call. Observed:
- `flight_core_workflow` — core GDS search (processed 1,008 flight options in 62s live)
- `flight_flexible_dates` — flexible date sampling

Per-skill metrics (verbatim):
```
flight_core_workflow_route_searches: 6         (GDS API calls)
flight_core_workflow_options_generated: 1008   (total options enumerated)
flight_core_workflow_cheapest_fare: 957.33
flight_flexible_dates_departure_dates_sampled: 6
flight_flexible_dates_cheapest_window: {departure_date: "2026-06-15", price: 957.33}
flight_flexible_dates_cheapest_vs_median_spread: 50  ("$50 below median")
```

Skill metric keys are prefixed with skill name, enabling per-skill breakdown in the UI.

**Flight mini-agent (KNOWN — confirmed by feature flag `flight_mini_agent: true`):** A separate sub-agent delegated to for flight queries. The main agent hands off via `delay_interruptible_tool: "flight"`. Same for `hotel_mini_agent`. This is the Mindtrip version of Nia's Tracer: a dedicated sub-agent for a bounded task.

**Full tool list (INFERRED from API + chunk types):**

| Tool | delay_reason | Backed by |
|---|---|---|
| `flight_search` | "flight_search" | Sabre GDS via `flight_mini_agent` |
| `hotel_search` | "hotel_search" | Nuitée LiteAPI v3 + Priceline |
| `places_search` | "places_search" | `/api/places/search_type_ahead` |
| `web_search` | "web_search" | Unconfirmed provider |
| `generate_itinerary` | "generate_itinerary" | Internal orchestrator |
| `update_itinerary` | "update_itinerary" | Internal |
| `restaurant_search` | "restaurant_search" | OpenTable + Google Places |
| `activity_search` | "activity_search" | Viator + place data |
| `get_weather` | (INFERRED) | `/api/map/weather` |
| `get_directions` | (INFERRED) | `/api/places/route` |
| `interrupt_tool` | (control, not a tool) | `POST /api/chats/:id/interrupt_tool` |

### Context Management

**64K context cap** applied to all GPT variants, regardless of native model context window.

**`status_snapshot` for reconnect resilience (KNOWN verbatim):**
```javascript
async fetchAndApplySnapshot(agent_session_id) {
  let snapshot = await api.getSessionStatusSnapshot(agent_session_id);
  if (snapshot?.visualizations?.length) {
    this.builder.applyStatusSnapshot(snapshot, agent_session_id);
    // emits synthetic delay chunk to repopulate activity feed
  }
}
```

Two-tier reconnect:
1. Short disconnect → resume SSE with `last_event_id` (server replays missed chunks)
2. Long disconnect → `GET /status_snapshot` repopulates activity feed, then resume SSE

Server pays a Redis write per chunk per active user to maintain this snapshot. Expensive but required for reconnect resilience.

**JWE sessions:** `mindtrip.auth_token` is a JSON Web Encryption token (encrypted, not signed). Every request requires server-side decryption. Cached in Rails.cache or Redis. 24h session, 30d refresh.

**`has_persona: boolean`** in session — the personalization agent has built a long-term memory file for this user. Context injection: "User persona: `<user.persona>`. Recent chats: `<recent_chats>`."

### Memory

**User persona:** built by `personalization_agent` (separate background model) reading recent chat history. Stored as a `persona` object on user profile. The voice interview agent (`VOICE_INTERVIEW_AGENT_ID`) builds a one-shot onboarding persona via a 5-minute ElevenLabs ConvAI session.

**Per-session sandbox:** each session gets an ephemeral per-session data store (DuckDB or SQLite in-memory) populated by tools. Accessible via `/sandbox/tables/:id`. Cleared on session end.

**`memory_report` endpoint:** exposes structured agent memory state to the user (debugging + transparency). Unusual — most agents hide memory. Likely sections: `hard_facts`, `preferences`, `constraints`, `recent_searches`, `committed_choices`.

**Multi-turn trip context:** agent carries the trip context (`draft_start_date`, `draft_duration`, `travelers`, `rooms`) across tool calls. This is the live example: "plan a 3-day trip to paris" → the agent remembered the 3-day duration and weighted flight options to fit it, even when flight search was a separate sub-agent invocation.

### Streaming Protocol (KNOWN verbatim from `0x_5x9eaj6jgq.js`)

SSE on `/api/events?chat_id=X&stream_id=Y&last_event_id=Z`. Stream-auth pre-flight:
```
HEAD /api/chats/:id/authorize_stream/:streamId → 200 OK (server trusts stream_id after this)
```

Stream ID format: `stream:<user_ref>:<chat_id>-<24-char-base62>`. Auth token passed as query param for embedded partner contexts (cookies don't work cross-origin in iframes).

Event envelope:
```typescript
| { status: "in-progress"; data: Chunk[] }   // array — multiple chunks per event possible
| { status: "done";       data: { message, chat } }
| { status: "canceled" }
| { status: "error";       data: { type: string; message: string; retryable: boolean } }
```

16 known chunk types: `text`, `place`, `airline`, `flight`, `flight_search`, `inspiration`, `itinerary`, `itinerary_event`, `itinerary_events`, `itinerary_day_title`, `chat`, `trip`, `delay`, `action`, `search_geo_changed`, `ui_signal`, `pagination_info`.

**`delay` chunk shape (KNOWN verbatim from live capture):**
```json
{
  "type": "delay",
  "delay_reason": "flight_search",
  "delay_text": "Handing off to our flight agent...",
  "delay_interruptible": true,
  "delay_interruptible_tool": "flight",
  "delay_interruptible_session_id": 74494,
  "metric_payload": {
    "status_message": "...",
    "estimated_completion_percent": null,
    "complication_found": null,
    "source": "auto_publisher",
    "active_skills": null,
    "metrics": [{"key":"...","label":"...","value":0,"value_display":"..."}],
    "visualizations": null,
    "time_estimate": {
      "difficulty": "simple",
      "estimated_total_seconds": {"p50":83,"p75":139,"p90":322},
      "ranges": [
        {"min_pct":0,"max_pct":19,"p50_remaining":66,"p90_remaining":307,"sample_size":7362},
        ...
      ]
    }
  }
}
```

The `time_estimate.ranges` data reveals ~167,000 historical flight-search sessions in the analysis dataset. Mindtrip has ML-based ETA prediction trained on production session history. Difficulty classifier: `simple/medium/hard`.

**Error retry (KNOWN verbatim):**
```javascript
// type: "rate-limit" → temporarilyDisableMessageStreaming() (no retry)
// retryable: true → retry up to 3×, exponential backoff: wait(1000 * 2 ** retryCount)
// → 2s, 4s, 8s
```

**Retries: 3 at message level, 1 at connection level (`MAX_RETRY_COUNT = 1`).**

**`ui_signal` chunk — skeleton-then-fill pattern (KNOWN):**
```
signal_type: "card", phase: "skeleton" → insert placeholder at text position start..end
signal_type: "card", phase: "complete" → fill placeholder with entity data
```

This requires the LLM to emit structured tool calls that the orchestrator splits into `skeleton` + `complete` events. The LLM commits to inserting a card at a specific text position before the card data is available, then fills it in async. Out-of-order rendering at the LLM-orchestrator boundary.

### Eval System (KNOWN — endpoints extracted from JS bundle)

First-class eval infrastructure built into the product surface:

```
GET  /api/agent/evaluations
POST /api/agent/evaluations
POST /api/agent/evaluations/:id/run
POST /api/agent/evaluations/run_batch
POST /api/agent/evaluations/run_ephemeral
POST /api/agent/evaluations/generate_from_session   ← auto-generate eval from real chat
POST /api/agent/evaluations/build_from_description  ← generate eval from natural-language description
GET  /api/agent/evaluations/tags
GET  /api/agent/evaluation_runs/:id
GET  /api/agent/evaluation_runs?run_ids[]=X&...
```

`generate_from_session` and `build_from_description` are particularly significant: you can turn any real production session into an eval, or describe what you want to test in natural language. This is an eval authoring system, not just an eval runner.

`run_ephemeral` enables one-shot evaluation without persisting to a named eval suite — for ad-hoc testing.

### Proactive Advice Pattern (KNOWN — live capture)

`GET /api/trips/{ref}/advices` returns async-generated itinerary critiques:
- Initial response: `{"status":"pending"}`
- After ~5s: `{"status":"ready","advices":[...]}`

Each advice: `{body, time_sensitive: bool, action_pills: [{type, label, context: {prompt}}]}`

`action_pills` are pre-baked prompts for follow-up — clicking a pill creates a new chat thread. The prompts are Mindtrip's prompt-engineering style: structured, behavioral nudges ("Just rank them, don't change my plan."). The agent ANALYZES the generated itinerary and surfaces friction points proactively without being asked.

### Constants (KNOWN verbatim)

| Constant | Value |
|---|---|
| Context cap | 64K tokens (all GPT variants) |
| `CHAT_MESSAGE_MAX_LENGTH` | 2048 chars |
| `MAX_RETRY_COUNT` | 1 (connection level) |
| Message-level retries | 3 × exponential (1s × 2^n) |
| `DEFAULT_DELAY` | 80ms (text smoother) |
| `DEFAULT_PRIMING_THRESHOLD` | 20 (smoother queue) |
| Session expiry | 86399 s (24h - 1) |
| Refresh token expiry | 2591999 s (30d - 1) |
| `keepUnusedDataFor` (price quotes) | 3600 s |
| Flight search expiry | ~21 minutes (epoch_millis TTL) |
| `thinking_duration_seconds` | wall-clock from first delay frame to last delay frame |

### → Verso Lessons (Mindtrip)

**Copy:**
- `delay` chunk with `delay_interruptible: true / false` as a first-class streaming concept. Every tool invocation should emit a delay chunk that signals interruptibility. This decouples the UX ("you can cancel this") from the execution logic.
- `interrupt_tool` as a first-class API endpoint. Tools must be cancellable. The framework should provide a cancel token per tool invocation, not just a kill-the-whole-session mechanism.
- Two-tier session architecture: `/api/chats/*` (message-centric, turn-based) and `/api/agent/sessions/*` (long-running, stateful, with sandbox + memory). Verso should support both "chat" and "session" interaction modes.
- HEAD pre-flight for stream authorization (`HEAD /authorize_stream/:streamId`). This avoids leaking 401 errors inside the SSE body and lets the stream endpoint trust the opaque stream_id without doing auth itself.
- Status snapshot endpoint (`/status_snapshot`) for two-tier reconnect resilience. Verso's streaming primitives should include a `status_snapshot` mechanism so clients can recover from drops without replaying the full event stream.
- Skills taxonomy (named multi-step workflows) as a layer above tools. A "skill" is an observable workflow that groups related tool calls and emits per-skill metrics. Verso should support skill registration alongside tool registration.
- ML-based ETA prediction exposed via `time_estimate.{p50, p75, p90}` with per-progress-bucket `p50_remaining`. Verso could expose calibrated latency estimates for named tools/skills.
- `immediate_followup: boolean` on agent messages for auto-chaining sub-tasks. Better UX than internal recursion; exposes each step as an observable event.
- First-class eval infrastructure: `generate_from_session` (turn real chats into evals), `build_from_description` (LLM-authored evals), `run_ephemeral` (ad-hoc tests). Every Verso app should have these.
- Proactive advice pattern: async post-processing that analyzes completed outputs and surfaces issues without being asked, with `action_pills` as pre-baked follow-up prompts.

**Avoid:**
- Baking vendor-specific flags into session schema (`is_thatch_creator`, `is_from_thatch`). As the number of B2B partners grows, each requiring schema migrations. Use a generic `vendor_metadata: {}` blob instead.
- JWE (encrypted JWT) for sessions — requires server-side decryption on every request. Signed JWTs with short TTLs + server-side invalidation are simpler.
- Coexisting two API generations (`/api/chats/*` and `/api/agent/sessions/*`) in production. Clear the old one or proxy it. Verso should enforce a clean version cut.

**Verso could improve by:**
- Making `time_estimate` a trainable primitive: every tool/skill call logs actual latency; framework builds percentile distributions over time; exposes them back to clients automatically.
- Providing a first-class `proactive_analysis` hook: after an agent completes a long-form output, run a background LLM call to analyze it and emit structured observations with `action_pills` for follow-up. This is a pattern Mindtrip productionized; Verso could make it a framework primitive.
- Treating `action_pills` (pre-baked follow-up prompts embedded in bot messages) as a first-class concept, so agents can guide users toward next actions without requiring free-text input.

---

## Cross-Cutting → Verso Implications

### 1. JSON-action ReAct as the canonical loop contract

All three systems converge on variants of: model emits structured output → framework parses and dispatches → result injected as next-turn context. NIA uses explicit JSON `{action, args, reason}`. AS uses Gemini's native function calling (structured output under the hood). Mindtrip uses plan-execute with SSE typed chunks.

**Verso should standardize on a JSON-action loop contract** that is:
- Parseable without LLM-provider-specific tooling (no Anthropic/OpenAI native `tool_use` content blocks required)
- Observable (every dispatch emits an event on the wire with the action + reason)
- Interruptible (every dispatch knows whether it's cancellable)
- Composable (a tool can be a sub-agent with its own loop)

### 2. The `think` tool pattern (explicit CoT sentinel)

NIA's `think` tool is the cleanest solution to CoT visibility: a structured no-op that forces the model to emit a `reflection` field, making reasoning observable without polluting the response. This costs one round trip but provides full observability of the reasoning chain on the SSE wire.

**Verso should ship `think` as a built-in default tool** that any agent can call. The reflection stays in the agent's context AND propagates to the wire as an event, so framework users can build observability dashboards without custom logging.

### 3. Memory taxonomy matters: scratchpad / episodic / fact / procedural

NIA's four-tier taxonomy is the right set. Each tier requires different storage semantics:
- `scratchpad`: in-memory or Redis with short TTL (tool-call results within a session)
- `episodic`: medium-TTL DB store (cross-session, fades over time)
- `fact`: permanent, high-quality, searchable
- `procedural`: permanent, replayable, structured (not free text)

**Verso should ship these four types natively with configurable TTLs**, backed by a hybrid store (vector + BM25 for retrieval, DB TTL index for expiration). The lineage schema (source_ids → tool_calls → model_version → edited_files) should be a first-class field on every memory entry.

### 4. Interruptible tools as a first-class framework primitive

Mindtrip's `delay_interruptible: true` + `interrupt_tool` endpoint is the right model. At the framework level:
- Every tool invocation should carry a cancel token
- The SSE stream should emit `{delay_interruptible: bool, delay_interruptible_tool: string}` so clients can show a cancel affordance
- `interrupt_tool` should be a built-in framework API, not something the application has to implement

### 5. Eval infrastructure belongs in the framework, not the application

Mindtrip has `generate_from_session`, `build_from_description`, `run_ephemeral`, `run_batch`. These are framework-level primitives that every AI product needs. Verso should ship them as standard endpoints/hooks so framework users don't have to build their own eval harness.

### 6. The synthesis separation pattern (loop-LLM vs. synthesis-LLM)

NIA's two-stage synthesis (loop accumulates tool calls → separate synthesis LLM renders the final report) is a durable pattern. Benefits:
- The synthesis LLM never sees the system prompt (security)
- Different model tier per stage (cheap for aggregation, premium for final output)
- The `generating_report` event progression gives users visible progress

**Verso should support `on_finish(tool_calls, summaries) → synthesis_call` as a first-class hook** in the agent loop, with the context boundary enforced (system prompt not visible to synthesis LLM).

### 7. Skills > tools as the user-facing abstraction

Mindtrip's `active_skills` with per-skill metrics is a cleaner user-facing abstraction than raw tool calls. A "skill" is a named, observable, multi-step workflow. Skills emit progress metrics in their own namespace. Users see "analyzing flight options (667 of 1,008 processed)" not "tool_call: flight_core_workflow step 4/6."

**Verso should support skill registration** as a higher-level concept above tools: a skill groups related tool calls, has a display name, emits observable progress metrics, and is the unit of interruptibility.

### 8. Fire-and-forget with staleTime: Infinity for expensive one-shot computations

AS's insight generation pattern (`POST /surveys/insights` → immediate 200, compute async, `staleTime: Infinity, retry: false`) is correct for expensive AI computations that are computed once and never change. **Verso should provide a `fire_and_forget(fn, cache_key)` helper** that runs the computation once, caches the result indefinitely, and serves it from cache on all subsequent calls.

### 9. Consensus bias is a real problem in multi-agent simulations

Any Verso application that runs N personas or N agents simultaneously must engineer for diversity. Without the closed-world constraint + confirmation bias injection, LLM agents converge to consensus. **Verso's multi-agent primitives should include a `diversity_constraint` configuration** that injects a persona-specific confirmation bias prompt, preventing the consensus collapse.

### 10. Reconnect resilience requires server-side state snapshot

Mindtrip's two-tier reconnect (SSE replay via `last_event_id` + full state snapshot via `/status_snapshot`) is the correct production pattern. **Verso's streaming primitives should include `snapshot_state()` as a hook** that the framework calls after each significant state change, enabling client reconnect without full stream replay.
