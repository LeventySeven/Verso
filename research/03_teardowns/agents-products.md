# agents-products — Agent Products Teardown
## Cluster: 11x / Character.AI / Aemon / Pleep / MiroFish

> Distilled for **Verso** — the simple ReAct + first-class MCP + memory + evals agent framework.
> Every section ends with a Verso lesson.

---

## 1. 11x (Alice / Julian) — AI SDR workers on LangGraph + Inngest + MCP fleet

### Agent loop shape

11x's "AI worker" is NOT a tight real-time ReAct loop. It is a **durable-workflow-orchestrated pipeline** where the "agent" runs as a LangGraph `StateGraph` hosted on LangGraph Cloud, triggered and retried by **self-hosted Inngest** (Temporal-style durable workflows). The two registered LangGraph workflows extracted verbatim from the `alice.11x.ai` bundle:

- `workflowKey: "list-builder"` (Alice) — prospect list building with human-in-loop interrupts
- `workflowKey: "campaign-builder"` — orchestrates list-builder as a subagent, then drafts and schedules the email sequence

The execution path: `CreateWorkflowSession(workflowKey, configurable)` → LangGraph thread spawned on `production-frontend-v1-d2be287fb433522cbe5a83921d1ed800.us.langgraph.app` → client subscribes to **Inngest Realtime** channel for streamed events → user sends messages via `SendWorkflowSessionMessage` → agent raises interrupts via `ResolveWorkflowSessionInterrupt({resolved, newRunId})`.

**Human-in-loop interrupt commands** (verbatim from bundle):
- `list-builder.add-column` — agent proposes a new column, frontend renders approval card
- `list-builder.add-qualification-column` — agent proposes a yes/no qualifier with payload `{label, criteria}`, user must confirm before column is added
- `list-builder.signals-review` — agent surfaces research signals for review

Termination: LangGraph handles it; no explicit max-iteration constant visible client-side.

### Tool system (fleet-MCP)

`fleet-mcp.11x.ai` resolves to AWS eu-central-1 (port-filtered, internal ALB). This is **a dedicated fleet of MCP servers** the LangGraph agents call as tools. Inferred MCP server inventory (INFERRED from bundle + docs):

| MCP Server | Wraps | Key operations |
|---|---|---|
| `apollo-mcp` | Apollo.io API | `people_search`, `person_enrich`, `organization_enrich` |
| `pdl-mcp` | People Data Labs | `person_enrichment`, `bulk_search` |
| `linkedin-mcp` | LinkedIn (stored `li_at` cookie) | `profile_view`, `connection_request`, `message_send` |
| `web-search-mcp` | Tavily/Serper/Brave | `websearch.query` |
| `web-fetch-mcp` | URL fetch + Readability/Trafilatura parse | `webfetch.url` |
| `pdf-parse-mcp` | PDF text extraction | — |
| `crm-mcp` | Ampersand (SF/HubSpot/Zoho) | `contact_get`, `contact_update`, `task_create` |
| `cal-mcp` | Cal.com | `event_types_list`, `booking_create` |
| `knowledge-base-mcp` | RAG over customer docs (pgvector) | `kb.search`, `kb.get_chunk` |
| `g2-mcp` | G2 buyer-intent signals | — |
| `reply-classifier-mcp` | Fine-tuned Mistral 7B / DistilBERT | 8-class reply intent classification |
| `personalization-mcp` | GPT-4o / Claude Sonnet | Email body generation with system prompt + few-shot |

Each MCP server is a separate container (ECS Fargate or EKS). The MCP fleet runs autoscaled per workload — I/O-bound tools (search, Apollo) scale wide; LLM-backed tools (personalization) scale tall.

### Models (INFERRED, post-fingerprinting)

| Workload | Model |
|---|---|
| Email personalization | GPT-4o (`gpt-4o-2024-08-06` or `gpt-4.1`) |
| Reply classification | GPT-4o-mini or Claude Haiku |
| Prospect research (tool-calling loop) | GPT-4o with tool use |
| Voice (Julian browser) | GPT-4o-realtime-preview or Claude via Sindarin/Vapi |
| KB RAG | GPT-4o-mini + `text-embedding-3-large` |
| Scale reply classification | DistilBERT or Llama 3 8B fine-tuned (self-hosted AWS) |

Feature-flag-driven model routing: PostHog `getFeatureFlag` pattern suggests a flag like `personalization_model` with payload `{provider, model, temperature}`.

### Durable workflow layer (Inngest)

Self-hosted on AWS eu-central-1 (3-IP cluster). Key inferred Inngest functions:

```
campaign.daily_send_loop   cron every 15m → fans out prospect.send_email
prospect.enrich            Apollo → PDL → Cognism → FullEnrich cascade
prospect.research          LangGraph "research_prospect" workflow (fleet-mcp tools)
prospect.send_email        personalization-mcp → Gmail/MS Graph → send receipt
reply.classify_and_route   8-class classifier → update campaign state → optional HIL interrupt
knowledge_base.embed       chunk → text-embedding-3-large → pgvector
billing.meter_org_usage    hourly → Stigg entitlements engine
```

Each Inngest function has step-level isolation: if step 3/5 crashes, replays from step 4 with same step IDs (idempotent).

### Context/memory

Context is stateless per LangGraph run; state is persisted in Hasura (GraphQL gateway on Fly.io Frankfurt, behind Cloudflare → AWS ALB → Envoy → Express middleware). No explicit cross-session memory — context is assembled fresh from Hasura on each run.

### System prompt

Partial client-templating: Sindarin Persona Client takes a `details` object with Mustache-style `{{details.firstName}}` placeholders. The agent's prompt is partially assembled client-side at session-start with arbitrary key-value maps.

### Error paths

- HIL interrupt: `ResolveWorkflowSessionInterrupt({resolved: false, newRunId})` cancels the run
- `CancelWorkflowSession` terminates a stuck run
- Inngest step-isolation: each durable step retried independently; re-sending = real damage so idempotency keys are critical

### Constants

- Inngest cron: `every '15 minutes'` for daily send loop
- GraphQL: `GetWorkflowSessionEvents`, `ListWorkflowSessions`, `SendWorkflowSessionMessage`, `SubmitWorkflowSessionCommand`, `ResolveWorkflowSessionInterrupt`
- LangGraph Cloud: `production-frontend-v1-d2be287fb433522cbe5a83921d1ed800.us.langgraph.app`
- Heartbeat: 900,000 ms (15 min)

### Architecture lesson (the anti-pattern)

11x stacked 30+ vendors in the critical path. At 99.9% per-vendor uptime, `0.999^12 ≈ 98.8%` per campaign run — compounding to >30% probability of some failure per month. The integration moat is also the reliability burden. **Every vendor is also a failure mode.**

### Verso lessons

- **Copy:** MCP fleet pattern — each tool as an independently deployable, autoscaling MCP server behind an internal ALB. LangGraph's human-in-loop interrupt pattern (`commandType`, `approvalRenderers` map) is clean; Verso should expose this as a first-class primitive.
- **Copy:** Inngest's durable step isolation as the execution substrate for long-running multi-step agent tasks. Verso's "tactical layer" = a durable Inngest/Temporal-style step runner, not a bare ReAct loop.
- **Avoid:** 30-vendor stack without a reliability budget. Verso should make it trivially easy to swap any single tool without cascading breakage. MCP standardization is exactly the right abstraction for this.
- **Verso could improve:** First-class interrupt/approval flow that doesn't require LangGraph Cloud. The HIL pattern (raise interrupt → frontend renders approval card → resume or cancel) is too useful to gate behind LangGraph licensing.

---

## 2. Character.AI — Persona chat, multi-character Rooms, custom inference

### Agent loop shape

Character.AI's core is **not agentic** — it is single-shot: one user message → one model response over a WebSocket. The only structurally agentic part is **Rooms** (`smart_reply_v2`): a server-side speaker-selection LLM picks which character responds next, then generates that character's turn. Two-LLM-call pattern: classify speaker → generate response. `smart_reply_v2` likely collapses these into one call.

Room turn-taking modes (verbatim from bundle `chunks/_app-7becf23e83ddd0c6.js`):
- Explicit: user clicks character avatar → `generate_turn` command with `character_id`
- Smart-reply: `create_and_generate_turn` with `smart_reply: true` → server picks next speaker
- Continue: `generate_turn` with `smart_reply: smart_reply` → same character continues

Termination: `abort_generation` command; `is_final: true` on the final `update_turn` event.

### Wire protocol

Single long-lived WebSocket per session. 1:1 chat → raw WS to `wss://neo.character.ai/ws/`. Rooms → Centrifuge (open-source pub/sub) to `/connection/websocket` with SSE + long-poll fallback. Centrifuge required for rooms because it supports presence tracking and channel fan-out to N participants.

Wire envelope (every message in both directions):
```json
{
  "command": "<enum>",
  "request_id": "<uuid v4>",
  "origin_id": "<uuid v4 issued at connect>",
  "payload": { ... },
  "error_code": null,
  "sub_code": null,
  "retry_after_seconds": null
}
```

Outbound commands (15): `create_chat`, `create_and_generate_turn`, `smart_reply_v2`, `generate_turn_candidate`, `set_turn_pin`, `abort_generation`, `update_primary_candidate`, etc.

Inbound events (15): `add_turn`, `update_turn`, `neo_error`, `filter_user_input`, `filter_user_input_self_harm`, `mu_state_update`, etc.

HTTP and WS errors share the same envelope shape — the Neo gateway translates HTTP errors into the same protobuf-shaped command stream.

### Streaming

Streaming is **full-message snapshot** (NOT incremental delta): each `update_turn` event contains the entire text-so-far as `raw_content`. Client replaces displayed message on each update, stops on `is_final: true`. Cheaper to implement than delta encoding; more bandwidth, irrelevant at their per-token cost.

Retry backoff on WS reconnect: `500 * 2**retryAttempts` (exponential), max 5 retries. Heartbeat ping every 900,000 ms (15 min).

### Models and routing

15 model variants exposed via `MODEL_TYPE_*` enum (verbatim):
```javascript
MODEL_TYPE_FAST       // "Speed"  → c1.fast (small, low-latency)
MODEL_TYPE_BALANCED   // "Mix"    → c1.balanced (default)
MODEL_TYPE_DEEP_SYNTH // "Deep"   → internal codename "RatGPT"
MODEL_TYPE_DEEP_SYNTH_LITE // "Deep Lite" → codename "Clawd"
MODEL_TYPE_DYNAMIC    // "Auto"   → server-side routing, picks best per query
MODEL_TYPE_MEMORY_OPTIMIZED  // → longer context variant
```

Server may silently downgrade routing under load (confirmed by i18n string `"tooltip-model-availability":"The actual model used may vary based on system load and availability"`). All are Character.AI's own c1.x model family (NOT frontier API calls).

Custom inference stack key numbers (from June 2024 engineering blog, KNOWN):
- 20,000 QPS steady-state (~20% of Google Search QPS)
- < $0.01 per conversation-hour (33× cost reduction vs 2022 baseline, 13.5× cheaper than frontier APIs)
- 95% cross-turn KV cache hit rate
- KV cache reduced >20× vs GQA baseline via: MQA (÷8), hybrid local/global attention 1-in-6 ratio with 1024-token local window (÷5.2 at 32k context), cross-layer KV sharing (÷2-3)
- Native int8 training (weights + activations + KV cache); custom CUDA kernels for matmul and attention
- RadixAttention-style stateful host-RAM KV cache with rolling-hash prefix keys and LRU tree eviction
- Sticky-session routing per `chat_id` for KV cache reuse

### Memory architecture (three layers)

**Short-term:** WebSocket-buffered turn list. Each turn = `{turn_key, author, candidates[], primary_candidate_id, state, is_pinned}`. Multiple candidates per turn power swipe-to-regenerate.

**Mid-term (cross-turn KV cache):** Host RAM, keyed by rolling hash of prefix tokens, tree-indexed (RadixAttention-style), LRU eviction. 95% hit rate. Sticky sessions route `chat_id` to same inference server. Each server caches thousands of dialogues (~30-40 MB/dialogue, ~175 GB host RAM per inference server inferred). Popular character persona KV essentially never evicted (always a warm child branch).

**Long-term (Memos / pinned turns):** `set_turn_pin` command toggles pin state. Pinned turns surface to the model on every subsequent generation. `TooManyPins` error (errorCode 429, subCode 16) caps per-chat pins. Cap likely 3 for free users; purchasable in packs of 100/200/300 as Charm SKUs.

### Context assembly (Prompt Poet — open source, MIT)

`character-ai/prompt-poet` (pip-installable) is the production prompt construction library. Key abstractions:
- `PromptPart`: `{name, content, role, truncation_priority, tokens, sections}`
- `PromptSection`: `{name, content, tokens, truncation_priority}`
- Truncation blocks: sorted by `truncation_priority`, dropped oldest-first to fit token limit
- Template: Jinja2 + YAML → rendered → YAML list of parts → tokenized → truncated

Verbatim from `prompt_poet/prompt.py:190-236`:
```python
def truncate(self, token_limit=None, truncation_step=None):
    num_tokens_to_truncate = self._calculate_num_tokens_to_truncate(token_limit, truncation_step)
    truncation_blocks = self._build_truncation_blocks()
    self._truncate(truncation_blocks=truncation_blocks, num_tokens_to_truncate=num_tokens_to_truncate, ...)
```

Truncation strategy: priority-based (lower priority = truncated first). The key innovation is that truncation decisions are **cache-aware**: the ordering preserves the longest common prefix to maximize KV cache hits.

### Persona / system prompt format (DESIGNED, our best guess)

```
<system>
You are {{char_name}}: {{char_description}}
Definition: {{char_definition}}
{{#if lorebook_entries}}
Relevant lore (keyword-triggered retrieval):
{{#each lorebook_entries}}
- {{this.keys}}: {{this.content}}
{{/each}}
{{/if}}
{{#if pinned_memos}}
Persistent memories:
{{#each pinned_memos}} - {{this.content}} {{/each}}
{{/if}}
User persona: {{user_persona.name}} — {{user_persona.description}}
</system>
<dialogue>
{{char_name}}: {{first_message}}
...history...
{{user_name}}: {{new_message}}
{{char_name}}:
```

Lorebook = keyword-match RAG: each entry has `keys: string[]`, server intersects entry keys with recent message before injection. Model fine-tuned to never break character (always continue the `{{char_name}}:` token).

### Multi-agent orchestration (Rooms)

Server-side speaker-selection LLM picks next speaker from the participating character list given chat history. Likely a fast small classifier. `INVOKED_COOLDOWN_MS: 3000` between explicit invocations. Max 10 characters + 10 humans per room. All participants share one Centrifuge channel; presence (who is typing/generating) broadcast via `mu_state_update` events.

### Safety (filter events)

Two interrupt events: `filter_user_input`, `filter_user_input_self_harm`. Self-harm filter A/B-tested via Statsig variant (`self_harm_coping_tools_variant`).

### Constants

```
MAX_CHARACTERS_LEN: 10       (per room)
MAX_USERS_LEN: 10            (per room)
INVOKED_COOLDOWN_MS: 3000    (room speaker invoke cooldown)
MIN_VOICE_CLIP_DURATION_MS: 3000
MAX_VOICE_CLIP_DURATION_MS: 60000
VOICE_INACTIVITY_TIMEOUT_MS: 180000   (3 min auto-disconnect)
LIVEKIT_URL: "wss://caimm-7f849j8w.livekit.cloud"
WS heartbeat: 900,000 ms (15 min)
WS retry: 500 * 2^attempts, max 5 retries
KV cache hit rate: 95% production
```

### Verso lessons

- **Copy:** Centrifuge (or equivalent pub/sub with presence) for any multi-participant streaming scenario. Raw WS is insufficient for rooms/multi-agent because it lacks server-side channel fan-out and presence.
- **Copy:** Full-snapshot streaming (not delta) is dramatically simpler to implement. Only add delta encoding when bandwidth cost is a real constraint.
- **Copy:** Cache-aware truncation (Prompt Poet's `truncation_priority`) — order context sections to maximize KV cache reuse. Verso's context assembly layer should expose `cache_control: ephemeral|breakpoint|persistent` on every context block.
- **Copy:** Memo/pin pattern — user-pinned turns that persist regardless of context window truncation. Verso memory module should have an `always_include: bool` flag on memory entries.
- **Copy:** Sticky-session routing per thread ID is the prerequisite for any prefix KV cache strategy. Verso's deployment layer should document this requirement explicitly.
- **Avoid:** Multi-turn KV caching at host-RAM depth is only practical with a custom inference stack. Verso should document that this optimization is off-limits unless you control the serving layer.
- **Verso could improve:** Speaker-selection for multi-agent is currently a bespoke LLM call. Verso could generalize this as a configurable `next_speaker` policy (enum: `explicit | round_robin | llm_select | random`) on a multi-agent session object.

---

## 3. Aemon — Evolutionary R&D agent (AlphaEvolve + research paper RAG)

### Agent loop shape

Not a conversational loop. Aemon implements an **evolutionary coding agent** pattern (AlphaEvolve/FunSearch lineage) with 5 stages:

```
Conceptualize → Build → Run → Analyze → Improve (repeat)
```

Visible from JS bundle demo data (verbatim extracted):
1. **Conceptualize** — literature survey: 3 papers retrieved and cited (FIRST 2024, LEXA graph contrastive learning, "Retrieve Summarize Plan" Jiang 2024)
2. **Build** — LLM generates/mutates code variants (SEARCH/REPLACE diff format)
3. **Run** — evaluation against user-supplied eval set (E2B sandbox likely)
4. **Analyze** — score candidate; update MAP-Elites program database
5. **Improve** — next-generation prompt assembled from: best parent + inspiration programs + research summaries + evaluation results

**No fixed iteration cap visible.** Demo shows 23 experiments / 5 generations progressing from Recall@10: 0.612 → 0.671 → 0.734 → 0.834 → 0.912. Human steering mid-run (natural language constraint injection) triggers full re-evolution at generation 0.

### LLM ensemble

From AlphaEvolve pattern + OpenEvolve community finding: best results with two-provider ensemble:
- **Flash model** (high throughput, broad exploration) — likely Gemini Flash or equivalent
- **Pro model** (high quality, breakthrough mutations) — likely Gemini Pro, Claude Sonnet, or GPT-4o

Mutation prompt structure (composite from FunSearch / AlphaEvolve / OpenEvolve — KNOWN from open-source):
```
[System] You are an expert programmer. Improve the EVOLVE-BLOCK sections. Output SEARCH/REPLACE blocks.
[User]
# Problem Description
{problem_statement}
# Current best program (score: {fitness_score})
{parent_code_with_EVOLVE_BLOCK_markers}
# Inspiring programs
## Program A (score: {score_a}) {inspiration_1}
## Program B (score: {score_b}) {inspiration_2}
# Previous evaluation results
{error_traces, metric_values}
# Relevant research findings   ← AEMON'S DIFFERENTIATOR
{paper_summaries}
# Evolution history
{what_tried, what_worked}
# Instructions: Generate SEARCH/REPLACE improvements.
```

### Research paper RAG layer (key differentiator)

Aemon's founders (Ray Xu — FIRST paper EMNLP 2024, CoRNStack ICLR 2025) built SOTA retrieval. The RAG pipeline at each generation:

1. **Retrieval** — CoRNStack-style contrastive embedding (CodeRankEmbed, 137M params, Arctic-Embed-M base), consistency filtering, hard negative mining. Beats CodeSage-Large (1.3B) on code retrieval.
2. **Reranking** — FIRST single-token listwise reranking (Qwen-2.5-Coder-7B). 50% latency reduction vs standard reranking. Outputs a single token per candidate (rank token), not a full score sequence.
3. **Synthesis** — same LLM reads top-k ranked papers, extracts techniques relevant to the current problem.
4. **Injection** — paper summaries injected into the mutation prompt as `# Relevant research findings`.

Live paper corpus: arXiv API (evidence: LEXA v3 updated March 2026 cited in demo — live, not curated static corpus).

### Program database (MAP-Elites + Islands)

Population: programs mapped to multi-dimensional feature grid; highest-fitness individual retained per cell. Island model (5 islands, ~500 programs, from OpenEvolve defaults). Ring-topology migration between islands. Programs use `# EVOLVE-BLOCK-START` / `# EVOLVE-BLOCK-END` markers.

Selection: double selection — high-fitness parent for quality + diverse inspiration programs for cross-pollination. No tournament selection; fitness-proportional or rank-based.

### Evaluation

Cascade: simpler checks first (syntax, tests), full benchmark only for promising candidates. Multi-metric optimization. Sandbox: likely E2B (hosted sandbox, consistent with Cloudflare Workers infrastructure).

### Infrastructure

Cloudflare Workers (OpenNext + Cloudflare), NOT Vercel. Zero public API, no self-serve. Forward-deployed model — customer-specific eval sets feed customer-specific tuning that open-source replication cannot match.

### Verso lessons

- **Copy:** The EVOLVE-BLOCK annotation pattern for agentic code evolution — markers that constrain what the LLM is allowed to change, leaving "fixed code" outside the evolve window. This is a clean interface between human-authored scaffold and LLM-generated mutations. Verso's code-execution tool could expose this as a first-class parameter.
- **Copy:** MAP-Elites as the program database — keeps the solution space diverse across multiple dimensions simultaneously, not just a single best-of-N. When Verso runs multi-step optimization loops, the archive should track diversity, not just quality.
- **Copy:** Research augmentation at each iteration: plan-search-synthesize-inject before generating the next mutation. Verso's tool registry should include a `literature_search(query)` tool that the agent calls at the start of each iteration.
- **Avoid:** Running evolutionary loops without sandbox isolation. E2B or equivalent is mandatory when arbitrary code is generated and executed.
- **Verso could improve:** Human steering mid-run (constraint injection → full re-evolution) is currently bespoke. Verso could generalize this as a `steer(constraint: string)` method on any running agent that injects a new constraint and resumes the loop with updated context.

---

## 4. Pleep — AI sales agent builder (WhatsApp/Telegram/Instagram)

### Agent loop shape

Three-phase inference pipeline (CONFIRMED from changelog Feb 16, 2026 status indicators):

```
THINKING → GENERATING → VERIFYING
```

- **THINKING:** Load thread history + KB retrieval (embedding search, category-filtered) + CRM data injection + extension configs loaded + tool definitions loaded
- **GENERATING:** System prompt + history + retrieved KB + CRM data → LLM inference → tool calls if needed (REST API tools or MCP servers) → raw response
- **VERIFYING:** Anti-hallucination check — does response reference only KB content? Are prices within guardrails? Scope control. If fails: retry, modify, or escalate to human operator. Pleep claims 99.87% factual accuracy (RAGAS eval, 1,000 samples, LLM-as-a-judge, Q1 2026).

No max-iteration constant visible. Single-turn response generation per incoming message; not a multi-step planning loop.

### Tool system (MCP — April 7, 2026)

From changelog (CONFIRMED existence; implementation details INFERRED):
- REST API tools: agent calls arbitrary external REST endpoints mid-conversation; results injected back as tool call observations
- MCP servers: backend connects to user-configured MCP servers (stdio or SSE transport likely), discovers tools via MCP protocol, exposes as LLM function-calling schemas
- NestJS backend already routes to Claude (Anthropic `tool_use`) and GPT-4o (OpenAI `tools` array); unified tool abstraction maps to provider-appropriate format
- CRM integrations (amoCRM, Bitrix24, MoySklad, Altegio, Google Calendar) are real-time data injected at THINKING phase, NOT via tool calling

### Models

Per-agent provider selection (user-configurable via wizard):
- Anthropic: Claude 3 Sonnet or Claude 3.5 Sonnet
- OpenAI: GPT-4o (inferred from marketing)
- Google: Gemini 2.0 Flash (`gemini-2.0-flash-001` found as default state in bundle)

KB processing (CONFIRMED):
- File uploads: Claude 3.5 Sonnet
- Manual entry / Q&A: Claude 3 Sonnet

Improvement system: "Pleep has its own LM model fine-tuned for prompt-engineering" (from llms.txt). Separate from the agent inference LLM.

### System prompt construction pipeline (verbatim data model)

Four-phase wizard pipeline (all server actions, NOT client-side):

**Phase 1: Data extraction**
`fetchAgentDataAction(url, useCase, locale)` → structured extraction `{agent_name, company_name, company_activity_description, primary_conversion_goal, key_benefits, formality_address_ru, letter_case_style, timezone, currency}` + `scrapedContent` + `branding`

**Phase 2: Sales script generation (sales only)**
`generateSalesScript({companyName, companyActivityDescription, primaryConversionGoal, keyBenefits, scrapedContent, locale})` → `{steps: [{step_number, instruction, id}], reasoning}`. User edits steps in drag-and-drop editor (react-beautiful-dnd). Steps serialized as: `e.steps.map((e,t) => \`${t+1}. ${e.instruction}\`).join("\n")` → `assistantDialogFlow` string.

**Phase 3: System prompt generation**
`generateInstructions({assistantName, companyName, ..., assistantDialogFlow, salesCycleDays, communicationStyle})` → `{prompt: string, description: string}`. Server-only; template logic opaque. LLM-generated, user never sees raw prompt.

**Phase 4: Agent creation**
`createAssistant({name, instructions: prompt, applicationId, model, provider})` → `createAnthropic/createOpenAI` → file uploads → `deleteAssistantCache(assistantId)` (force fresh config read).

### Memory / context

All context assembled fresh per request:
- Full thread message history (array of `{id, role, text, created_at}`)
- KB retrieval result (category-filtered embedding search)
- CRM data snapshot (amoCRM / Bitrix24 / MoySklad / etc.)
- Thread state: `{thread_id, phone, message_handler: "AI"|"OPERATOR", messages[]}`

No persistent cross-session memory beyond thread history. Cross-channel continuity: `unknownUserId` in localStorage for web widget; phone number is the permanent identifier for WhatsApp/Telegram/Instagram.

### Knowledge base (structured entity RAG — NOT naive chunking)

Documents → Claude 3.5 Sonnet → typed entity extraction into 6 categories: **Products, Q&A, Procedures, Contacts, Context, Other**. Each entity individually addressable and editable. Retrieval is category-filtered before similarity search:

```
User message → category classification → targeted retrieval against relevant category index
  Product question → Products index
  Process question → Procedures index
  Contact request  → Contacts index
  General          → Context index
→ injected into LLM context with category label
→ VERIFYING step: checks response references only KB content
```

Mid-conversation re-retrieval (Feb 12, 2026): agent can trigger additional KB searches during generation when it needs more info. Vector store: `vector.pleep.app` (self-hosted, Qdrant likely). Embedding: `embed.pleep.app` (OpenAI `text-embedding-3-small` likely). KB is NOT chunks — it is typed entities; changes are live immediately, no re-indexing.

### Improvement loop (CONFIRMED — system prompt mutation, NOT fine-tuning)

1. User describes problem: "My agent gives wrong prices"
2. System validates specificity (rejects "make it better")
3. Analysis: examines current agent settings and instructions, identifies which sections need modification
4. Generation: fine-tuned prompt-engineering LLM rewrites relevant sections, preserves unmodified settings
5. Application: immediate, no retraining; full revision history maintained; `deleteAssistantCache` called

Like/dislike buttons on every AI response → dislike captures `{problem_description, correct_answer, context}` → pattern detection on repeated identical errors → triggers "deeper correction."

### Conversation state management

Human operator handoff:
- Auto-handoff: keyword detection (`"позовите менеджера"`, `"хочу поговорить с человеком"`, custom keywords) + external channel detection + working hours check
- Manual: operator clicks mode toggle
- Auto-return: configurable timer after operator's last message

Optimistic UI: client adds message with `isOptimistic: true`, removes flag on `user.message.saved` Socket.IO confirmation.

### Constants

```
salesCycleDays default: 3 (sales), 0 (support)
KB website scrape limit: 100 pages
KB Instagram scrape limit: last 120 posts from public profiles
Message delay simulation: 1-3 seconds recommended
RAGAS accuracy benchmark: 99.87% factual accuracy (Q1 2026)
```

### Verso lessons

- **Copy:** Three-phase pipeline (THINKING → GENERATING → VERIFYING) exposed as named states with observable status — users trust the system more when they can see which phase is running. Verso agents should emit observable status events, not just final outputs.
- **Copy:** Category-typed RAG — entity extraction into typed categories before embedding is dramatically more accurate than chunking raw text. Verso's memory/KB module should support typed entity storage with category-filtered retrieval.
- **Copy:** The improvement loop (natural language → system prompt mutation) using a separate fine-tuned prompt-engineering LLM is the right separation of concerns. Verso should have a first-class `agent.improve(feedback: string)` method.
- **Copy:** The verification step — a post-generation check that the response is grounded in retrieved content. Verso could expose this as a configurable `verify_grounding: bool` flag on any RAG-backed agent.
- **Avoid:** Hiding system prompt from the user (the "promptless" pattern). Advanced users will always want to inspect and override. Verso agents should expose `agent.instructions` as a readable/editable field, not an internal black box.
- **Verso could improve:** MCP server discovery + unified tool abstraction (maps MCP tools to the right provider-native format: Claude `tool_use` vs OpenAI `tools` array) is exactly what Verso should build as a first-class runtime capability. Pleep built this ad-hoc inside NestJS; Verso can offer it generically.

---

## 5. MiroFish — Multi-agent social simulation + LangChain ReACT report agent

### Agent loop shapes (two distinct loops)

**Loop 1 — SocialAgent (simulation agents, OASIS engine):**
Single-step tool-call loop per simulation round. Per `env.step()` call:

```python
async def perform_action_by_llm(self):
    env_prompt = await self.env.to_text_prompt()   # refresh + serialize platform state as JSON
    user_msg = f"Please perform social media actions... Here is your environment: {env_prompt}"
    response = await self.astep(user_msg)   # CAMEL ChatAgent: tool calls auto-executed inside astep()
```

Max concurrency: `asyncio.Semaphore(128)` across all agents. Max iterations per step: 1 LLM call per agent per round. All 29 ActionTypes auto-registered as OpenAI function-calling tools (`FunctionTool`). Tool results written to agent memory as system messages.

**Loop 2 — ReportAgent (LangChain ReACT, report generation):**
Multi-step ReACT loop per report section:

```python
while tool_call_count < MAX_TOOL_CALLS_PER_SECTION:   # MAX = 5
    response = llm.call(system=section_system_prompt, messages=history)
    if "<tool_call>" in response:
        tool_name, params = parse_tool_call(response)   # parses <tool_call>{...}</tool_call> XML
        result = execute_tool(tool_name, params)
        history.append({"role": "assistant", "content": response})
        history.append({"role": "user", "content": f"Observation: {result}"})
        tool_call_count += 1
    elif "Final Answer:" in response:
        section_content = response.split("Final Answer:")[1].strip()
        break
    else:
        break   # force output if neither pattern found
```

Three-phase report loop: Planning (2-5 section outline, JSON output) → Section Generation (min 3 tool calls required, max 5) → Reflection (validates citations + grounding, `MAX_REFLECTION_ROUNDS = 2`).

### Report tool registry (4 tools, verbatim from `zep_tools.py`)

**`insight_forge`** — deep semantic search:
```
1. LLM decomposes query into sub-problems: _generate_sub_queries(query, max_queries=5)
2. For each sub_query: graph.search(graph_id, sub_query, limit=10, scope="edges")
3. For top entities: get_node_detail() + get_node_edges() → relationship chains
Returns: InsightForgeResult(semantic_facts, entity_insights, relationship_chains)
```

**`panorama_search`** — full graph scan including historical facts:
```
1. get_all_nodes(graph_id) → paginate (max 2000)
2. get_all_edges(graph_id, include_temporal=True)
3. Classify: expired_at IS NOT NULL OR invalid_at IS NOT NULL → historical_facts; else → active_facts
Returns: PanoramaResult(active_facts, historical_facts, all_nodes)
```

**`quick_search`** — lightweight BM25/semantic hybrid:
```
graph.search(graph_id, query, limit=10, scope="edges", reranker="cross_encoder")
```

**`interview_agents`** — query live simulation agents:
```
1. Read persona files from simulation dir
2. LLM selects relevant agent IDs from persona list based on query
3. POST /api/simulation/interview/batch with selected agents + prompt
4. Returns multi-perspective responses
```

### Models

Primary: `qwen-plus` on `dashscope.aliyuncs.com/compatible-mode/v1` (Alibaba Cloud). Fallback: `gpt-4o-mini`. Boost LLM (optional, for report agent + ontology generation): separate `LLM_BOOST_*` env vars. OASIS paper backbone: `Llama-3-8B-Instruct` via vLLM. Group polarization evaluator: `GPT-4o-mini`.

### Memory (Zep Cloud graph memory)

MiroFish uses Zep Cloud as the persistent memory layer for simulation state. Key API (KNOWN):

```python
# Ingestion (async, returns immediately):
graph.add(data=str, type="text"|"json"|"message"|"fact_triple", graph_id=..., metadata=...) → Episode

# Hybrid retrieval:
graph.search(query=str, scope="edges"|"nodes"|"episodes"|"communities"|"sagas"|"themes"|"auto",
             limit=10, reranker="rrf"|"cross_encoder", mmr_lambda=...) → GraphSearchResults
```

Temporal fact model: every edge has `valid_at`, `invalid_at`, `expired_at`. Old facts are marked invalid (never deleted). History preserved. `panorama_search` queries both active and historical facts to show simulation evolution.

Graph Memory Updater runs every K rounds: reads actions from JSONL log, formats as `"Agent {id} performed {action} at round {n}: {result}"`, calls `graph.add()` for each batch.

OASIS simulation agents use **CAMEL's sliding-window conversation context** (no Zep) — only the report agent uses Zep for cross-simulation memory.

### Simulation state machine

```
CREATED → PREPARING → READY → RUNNING → PAUSED → STOPPED → COMPLETED / FAILED
```

Persisted to filesystem: `backend/uploads/simulations/{sim_id}/state.json`.
`sim_id` format: `sim_{uuid.uuid4().hex[:12]}` (e.g., `sim_a3f2c91b4d7e`).
`TaskManager` cleans up completed/failed tasks older than 24h.

### IPC protocol (simulation ↔ runner)

Filesystem JSON polling. `commands/` dir for inbound, `responses/` dir for outbound. Command types: `INTERVIEW`, `BATCH_INTERVIEW`, `CLOSE_ENV`. Interview prompt prefix (verbatim, Chinese, with English translation):
```
"You are being interviewed. Based on your persona, all past memories and actions, answer in plain text.
Requirements: 1. Natural language only, no tool calls. 2. No JSON. 3. No Markdown headers.
4. Answer question-by-question, prefix each with 「问题X：」. 5. Blank line between answers. 6. 2-3 sentences minimum."
```

### Constants

```python
# Report agent
MAX_TOOL_CALLS_PER_SECTION = 5
MAX_REFLECTION_ROUNDS = 2
REPORT_AGENT_TEMPERATURE = 0.5
MAX_TOOL_CALLS_PER_CHAT = 2   (interactive Q&A mode)

# Zep paging
ZEP_PAGE_SIZE = 100
ZEP_MAX_NODES = 2000

# Retry
RETRY_MAX = 3
RETRY_INITIAL_DELAY = 1.0
RETRY_MAX_DELAY = 30.0
RETRY_BACKOFF_FACTOR = 2.0

# OASIS concurrency
llm_semaphore = 128   (max concurrent LLM calls)

# Embedding cache (offline fork)
max_entries = 2000; evict oldest 10% on overflow; batch_size = 32

# Hybrid search (offline fork, Neo4j)
VECTOR_WEIGHT = 0.7  (vs BM25)
```

### Offline fork architecture (MiroFish-Offline — Neo4j + Ollama)

Replaces Zep Cloud with Neo4j 5.18 Community. Abstract `GraphStorage` interface (11 methods). Entity UPSERT:
```cypher
MERGE (n:Entity {graph_id: $gid, name_lower: $name_lower})
ON CREATE SET n.uuid = $uuid, n.name = $name, n.summary = $summary,
              n.attributes_json = $attrs, n.embedding = $emb, n.created_at = $ts
ON MATCH SET n.summary = $summary, n.attributes_json = $attrs, n.embedding = $emb
```
Embedding: `nomic-embed-text` (768 dims, batch 32, in-memory cache 2000 entries). Hybrid search: VECTOR_WEIGHT 0.7 vs BM25 0.3.

### Verso lessons

- **Copy:** The `MAX_TOOL_CALLS_PER_SECTION` hard cap with `Final Answer:` termination sentinel is a clean, explicit ReACT loop contract. Verso should expose this as `max_steps: int` on every agent, with a configurable termination token.
- **Copy:** Three-phase report structure (Planning → Section generation → Reflection) as a reusable pattern for any long-form synthesis task. This is a generalization of "plan-execute-verify" that Verso should support as a built-in task pattern.
- **Copy:** `interview_agents` tool — the ability to query running simulation agents mid-execution as a tool in the report agent's arsenal. This is cross-agent querying as a first-class tool. Verso multi-agent sessions should support agent-to-agent queries as a built-in tool type.
- **Copy:** Zep's temporal fact model (valid_at / invalid_at / expired_at, never delete) is the right approach for agent memory that changes over time. Verso's memory module should track fact validity timestamps, not just upsert.
- **Copy:** The `GraphStorage` abstract interface (offline fork) is the right layering — memory backend is swappable (Zep Cloud → Neo4j → anything). Verso should define a `MemoryBackend` protocol that any implementation can satisfy.
- **Copy:** OASIS `Channel` (asyncio Queue) between agents and platform — message-passing rather than shared state. Verso multi-agent sessions should use a message bus, not a shared mutable object.
- **Avoid:** Filesystem JSON polling as IPC between the Flask API and the simulation subprocess. This is fragile at scale. Replace with Redis pub/sub or an in-process asyncio queue. MiroFish pays for this complexity because OASIS runs as a subprocess; Verso should run agents in-process.
- **Verso could improve:** The `interview_agents` pattern (inject a question into running agents at any point and get back their current perspective) is powerful for evals. Verso could expose `session.probe(agent_ids, question)` as a first-class eval primitive.

---

## → Verso Implications

### Agent loop

1. **Explicit `max_steps` cap is non-negotiable.** All 5 systems enforce it: MiroFish `MAX_TOOL_CALLS_PER_SECTION = 5`, Character.AI `max 5 WS retries`, Aemon generation count. Verso default: `max_steps = 10`, configurable per agent.

2. **ReACT termination by sentinel string is fragile.** MiroFish's `elif "Final Answer:" in response: break` is easily broken by models that phrase differently. Verso should use structured output (tool call that signals completion) rather than string matching. Ship with a `done(result: str)` tool as part of every default tool set.

3. **Three-phase pipeline (think → act → verify) is the production pattern.** Pleep proved it with observable status states. Verso agents should emit `{phase: "thinking"|"acting"|"verifying", ...}` status events on a subscribable stream, not just final outputs.

4. **Durable step isolation is required for any agent that touches external state.** 11x's Inngest pattern: each step gets a unique ID; failed steps replay from that step without re-executing prior steps. Verso's task execution layer should be Inngest/Temporal-compatible, not bare async/await.

### Tools and MCP

5. **MCP fleet is the right deployment pattern.** 11x's `fleet-mcp.11x.ai` — each tool as an independently deployable, autoscaling MCP server. Verso should generate MCP server stubs from tool definitions and document how to deploy them to ECS/EKS.

6. **Unified tool abstraction across providers is table stakes.** Pleep built it ad-hoc: Claude `tool_use` vs OpenAI `tools` array vs Google function declarations. Verso must normalize this at the framework level; users should define tools once and Verso maps them to the right wire format per provider.

7. **Tool call routing via feature flag is the right pattern for A/B testing models.** 11x's `personalization_model` feature flag pattern: flag payload = `{provider, model, temperature}`. Verso should support `routing_policy: FeatureFlag | Static | ABTest` on any agent.

### Context and memory

8. **Cache-aware context ordering is a free performance win.** Character.AI's Prompt Poet: sections ordered by `truncation_priority` to maximize KV cache prefix reuse. Verso context assembly should expose `cache_priority: permanent|important|ephemeral` on every context block, and document the sticky-session requirement.

9. **Typed entity RAG dramatically outperforms raw chunking.** Pleep's category-typed KB (Products / Q&A / Procedures / Contacts) with category-filtered retrieval achieves 99.87% factual accuracy. Verso memory module should support entity types with type-specific indexes.

10. **Temporal memory (valid_at / invalid_at) is correct for long-running agents.** MiroFish/Zep never deletes facts; marks them invalid. Verso memory entries should have `valid_at: datetime | None` and `invalid_at: datetime | None` fields. The default behavior: facts expire but history is preserved.

11. **Memo/pin pattern (always-include memory items) is essential for long conversations.** Character.AI's `is_pinned` + `TooManyPins` cap. Verso memory: `always_include: bool` flag on any memory item, with an optional quota (`max_pinned: int = 10`).

### Multi-agent

12. **Centrifuge (or equivalent pub/sub with presence) is required for multi-participant streaming.** Raw WebSocket is insufficient for multi-agent rooms because it lacks server-side channel fan-out and presence tracking. Verso multi-agent sessions should use a proper pub/sub layer (Centrifuge, NATS, Redis Pub/Sub, Ably).

13. **Speaker selection is a first-class policy.** Character.AI's `smart_reply_v2` (LLM-picks-next-speaker) vs explicit selection. Verso: `next_speaker: "explicit" | "round_robin" | "llm_select" | "random"` on multi-agent session config.

14. **Cross-agent querying as a tool.** MiroFish's `interview_agents` — query running agents mid-simulation as a tool callable from another agent. Verso should support `query_agent(agent_id, question) → response` as a built-in tool in multi-agent sessions.

### Evals and improvement

15. **The improvement loop (feedback → system prompt mutation) is more valuable than fine-tuning.** Pleep's system: natural language → separate fine-tuned prompt-engineering LLM → rewrites relevant prompt sections → immediate re-deployment. Verso should expose `agent.improve(feedback: str)` as a first-class method and provide a default prompt-engineering model (Claude Sonnet or GPT-4o-mini fine-tuned for instruction rewriting).

16. **Verification step (grounding check) should be opt-in, not manual.** Pleep's VERIFYING phase: checks that response references only KB content + price guardrails + scope. Verso: `verify_grounding: bool` flag on RAG-backed agents; when `True`, a second LLM call validates the response before delivery.

17. **Probing running agents as an eval primitive.** MiroFish's `interview_agents` pattern is also the right model for evals: inject a known-answer question into a running agent and compare the response to the expected answer. Verso should expose `session.probe(question, expected_answer) → EvalResult` for integration testing.

### Architecture anti-patterns to avoid

18. **Vendor count > 12 in the critical path guarantees > 1 failure per month.** 11x's 30-vendor architecture explains its 70-80% churn rate. Verso should ship with a "complexity budget" concept: document the expected number of external service calls per agent request, and flag agents that exceed a configurable threshold.

19. **Partial client-templating of system prompts (Mustache in the browser) is a security smell.** 11x's Sindarin `{{details.firstName}}` pattern exposes part of the system prompt contract to the client. Verso system prompts are server-side only; variable substitution happens server-side before the LLM call.

20. **Filesystem JSON polling as IPC is not production-grade.** MiroFish's `commands/` / `responses/` dir pattern breaks under concurrent load and is not observable. Verso inter-process communication uses a proper queue (Redis Streams, asyncio, or NATS) with structured message schemas.
