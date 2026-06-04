# Missing Top Agentic Startups RE

Source file: `core/16_MISSING_TOP_AGENTIC_STARTUPS_RE.md`
Commits studied: `bd9d27ff` (Mem0), `70515e33` (Arcade), `fe36f41d` (Exa JS SDK), `9d9479e8` (Sema4.ai Actions), `af61c229` (Relevance AI)

---

## core/16_MISSING_TOP_AGENTIC_STARTUPS_RE.md

### Architecture Family Map

Five distinct agent families extracted from this pass:

| Family | Canonical example | Verso relevance |
|---|---|---|
| Memory as product primitive | Mem0 | Memory layer spec for Verso |
| Tool auth as product primitive | Arcade.dev | Tool runtime spec for Verso |
| Research as evented plan/task graph | Exa Research | Async job + event log model |
| Enterprise action server as trust boundary | Sema4.ai Actions | Action packaging + MCP bridge |
| Enterprise graph agents | Glean / Writer | Permission-aware context assembly |

---

### Mem0 — Agent Memory Substrate (KNOWN-CODE)

**Loop shape:** not a ReAct loop; a pipelined write/read service consumed by agents.

**Models:**
- Default extraction/reranking LLM: `gpt-4o-mini` (OpenMemory self-hosted) / `gpt-5-mini` (README default, time-sensitive)
- Default embedder: `text-embedding-3-small` (OpenAI)
- Extraction temperature: `0`
- Reranker temperature: `0.0`, max tokens `100`
- Reranker default model: `gpt-4o-mini`

**Tool registry (MCP, KNOWN-CODE from `openmemory/api/app/mcp_server.py`):**
- `add_memories(text: str, infer: bool = True)` — always call when user says anything relevant; `infer=False` bypasses LLM extraction
- `search_memory(query: str)` — always call on every user message

**Context assembly / write path (KNOWN-CODE from `Memory.add()`):**
1. Require at least one of `user_id`, `agent_id`, `run_id` (scope key)
2. String message → `[{"role": "user", "content": "..."}]`
3. If `infer=False`: skip LLM, embed non-system messages directly with `embed(content, "add")`
4. V3 additive path: load `last_messages(limit=10)` from SQLite; vector search existing memories `top_k=10`; map UUIDs to integer IDs (anti-hallucination tactic before showing to LLM)
5. System prompt: `ADDITIVE_EXTRACTION_PROMPT` (ADD-only; no UPDATE/DELETE from LLM); if agent-scoped, append `AGENT_CONTEXT_SUFFIX`
6. LLM call: `response_format={"type": "json_object"}`, parse key `"memory"` (list); fallback `extract_json`
7. Batch embed with `embed_batch(..., "add")`; per-text fallback if batch fails
8. Dedup hash: `hashlib.md5(text.encode()).hexdigest()`
9. Metadata payload: `text_lemmatized`, `data`, `hash`, `created_at`, `updated_at`, `attributed_to`
10. Vector insert batched; per-item fallback if batch fails
11. Entity extraction: `extract_entities_batch`; globally dedup; embed in batch; entity store search `top_k=1`
12. Entity link threshold: `score >= 0.95`
13. Return: `{"id": ..., "memory": ..., "event": "ADD"}`

**Context assembly / read path (KNOWN-CODE from `Memory.search()`):**
- Default `top_k=20`, default `threshold=0.1`
- `rerank=False` by default
- Hybrid search algorithm:
  1. Lemmatize query (`lemmatize_for_bm25`)
  2. Extract entities from query
  3. Embed query with `embed(query, "search")`
  4. `internal_limit = max(limit * 4, 60)`
  5. Semantic vector search `top_k=internal_limit`
  6. Keyword/BM25 search over lemmatized text `top_k=internal_limit` (if vector store supports it)
  7. BM25 normalization by query length (sigmoid; midpoints: `<=3 terms → 5.0`, `<=6 → 7.0`, `<=9 → 9.0`, `<=15 → 10.0`, else `12.0`; steepnesses `0.7/0.6/0.5/0.5/0.5`)
  8. Entity boost: up to first 8 entities; entity store `top_k=500`; entity match threshold `0.5`
  9. `ENTITY_BOOST_WEIGHT = 0.5`; memory count weight = `1 / (1 + 0.001 * ((num_linked - 1) ** 2))`
  10. Combined score: `min((semantic + bm25 + entity_boost) / max_possible, 1.0)` where max possible = `1 + 1 + 0.5` when all three present
  11. Gate by threshold before fusion (semantic must pass `threshold` before combination)
  12. Sort descending; return `top_k`

**Memory (KNOWN-CODE):**
- SQLite at `~/.mem0/history.db` (local) / Postgres for server replicas (DESIGNED)
- Vector store: Qdrant default; 24 alternatives supported including pgvector, Pinecone, Chroma, Weaviate, Redis
- Procedural memory: records complete agent execution history over last N steps verbatim (program/behavior memory, not preference memory)
- Memory version field: `MemoryConfig.version = "v1.1"`
- History DB path: `MemoryConfig.history_db_path = "~/.mem0/history.db"`

**Exact constants:**
- Entity link threshold: `0.95`
- Entity match threshold: `0.5`
- Entity boost weight: `0.5`
- Entity store search top_k: `500`
- Memory count weight formula: `1 / (1 + 0.001 * ((num_linked - 1) ** 2))`
- Default search top_k: `20`; default threshold: `0.1`
- Write path vector search top_k: `10`; last messages limit: `10`
- Internal search limit: `max(limit * 4, 60)`
- Reranker: enable only when candidate count > 30 or semantic scores are close (DESIGNED recommendation)
- LLM reranker fallback score: `0.5`

**System prompts (KNOWN-CODE from `mem0/configs/prompts.py`):**
Named templates: `ADDITIVE_EXTRACTION_PROMPT` (primary), `FACT_RETRIEVAL_PROMPT`, `USER_MEMORY_EXTRACTION_PROMPT`, `AGENT_MEMORY_EXTRACTION_PROMPT`, `DEFAULT_UPDATE_MEMORY_PROMPT`, `PROCEDURAL_MEMORY_SYSTEM_PROMPT`

Key semantics of `ADDITIVE_EXTRACTION_PROMPT`:
- Extract from BOTH user and assistant messages
- New extractions must come exclusively from New Messages; Existing Memories only for dedup/linking
- ADD-only; LLM never generates UPDATE/DELETE
- Context-rich memories required (not atomized facts without subject)
- Dates resolved against Observation Date / Current Date
- Incidental user facts and shared content descriptions included
- Output: JSON with memory list

**Error handling:** batch embed fallback → per-text; batch insert fallback → per-item; LLM parse fallback via `extract_json`; if no memories extracted, raw messages still saved to SQLite history

**Multi-agent:** `agent_id` scope key isolates per-agent memory; procedural memory type only available when `agent_id` is set

**Streaming:** not applicable (service layer, not response streaming)

---

### Arcade.dev — Agent Tool/Auth/MCP Runtime (KNOWN-CODE)

**Core insight:** tool calling is an auth, schema, transport, and runtime error problem — not just a JSON schema problem.

**Tool schema (KNOWN-CODE from `arcade_core/schema.py`):**
- Separator: `ARCADE_TOOL_NAME_SEPARATOR` env; default `"."`
- Fully qualified name: `{toolkit_name}{sep}{name}`, case-insensitive, version-aware
- `equals_ignoring_version` exists for compatibility
- `ValueSchema` types: `string`, `integer`, `number`, `boolean`, `json`, `array`
- `ValueSchema` carries: inner types, enum, properties, inner properties, descriptions, required keys, nullable
- `InputParameter`: `name`, `required`, `description`, `value_schema`, `inferrable=True`
- `ToolOutput.available_modes` defaults: `["value", "error", "null"]`
- Tool requirements: authorization, secrets, metadata
- `ToolDefinition` fields: `name`, `fully_qualified_name`, `description`, `toolkit`, `input`, `output`, `requirements`, `deprecation_message`, `metadata`
- `ToolContext` carries: auth token/user info, secrets list, metadata list, user id; accessors `get_auth_token_or_empty`, `get_secret`, `get_metadata`

**Auth providers (KNOWN-CODE):** 21 OAuth providers built in: Asana, Atlassian, Attio, ClickUp, Discord, Dropbox, Figma, GitHub, Google, Hubspot, Linear, LinkedIn, Microsoft, Notion, PagerDuty, Reddit, Slack, Spotify, Twitch, X, Zoom

**Tool decorator / adapter chain (KNOWN-CODE from `arcade_tdk/tool.py`):**
- `@tool` accepts: `desc`, `name`, `requires_auth`, `requires_secrets`, `requires_metadata`, `adapters`, `metadata`
- Builds adapter chain: user adapters + auth adapter + GraphQL adapter + HTTP adapter fallback; deduped by type
- Arbitrary exceptions → `FatalToolError`; raw `str(exception)` explicitly NOT put in agent-facing message
- Agent-facing: stable, terse, safe error; developer logs: full fidelity

**Catalog (KNOWN-CODE from `arcade_core/catalog.py`):**
- Loads toolkits from directory/pyproject or installed packages via entrypoints group `arcade_toolkits`
- Package discovery by `arcade_` prefix
- Disable controls: `ARCADE_DISABLED_TOOLS`, `ARCADE_DISABLED_TOOLKITS`
- `add_tool` creates Pydantic input/output models + `MaterializedTool` (definition + callable + metadata + input model + output model)

**Executor pipeline (KNOWN-CODE from `arcade_core/executor.py`):**
1. Validate raw input with Pydantic input model
2. Detect if function expects `ToolContext`; inject if needed
3. Async functions: execute directly; sync functions: `asyncio.to_thread`
4. Validate output with output model
5. Return `output_factory.success` on success
6. Pydantic input errors: report only field path + reason + error type; no offending values in message
7. Runtime errors: `ToolRuntimeError` with `message`, `developer_message`, `stacktrace`, `additional_prompt_content`, `retry_delay`, `kind`, `can_retry`, `status_code`, `extra_data`

**Worker server (KNOWN-CODE from `arcade_serve`):**
- Base path: `/worker`
- Default components: `Catalog`, `CallTool`, `HealthCheck`
- Auth secret from `ARCADE_WORKER_SECRET`; no secret → startup raises
- Routes: `GET /worker/tools`, `POST /worker/tools/invoke`, `GET /worker/health` (no auth)
- Execution: logs `execution_id`; creates OpenTelemetry span `RunTool`
- Response includes: `duration_ms`, `finished_at`, `success`, `output`
- Client disconnect during body read → HTTP 499

**MCP server (KNOWN-CODE from `arcade_mcp_server`):**
- Server name validation: alphanumeric/underscore, no leading underscore, no consecutive underscores, end alphanumeric
- Version normalized as semver
- Transport: `stdio` and `http`; default host `127.0.0.1`, port `8000`
- Tool name conversion: `.` → `_` in fully qualified names
- `_meta.arcade.requirements` carries auth/metadata requirements
- Input schema: `additionalProperties: false`
- Primitive/list outputs wrapped as `{result: ...}`
- HTTP transport: JSON-RPC over HTTP with SSE; headers: `Mcp-Session-Id`, `MCP-Protocol-Version`, `Last-Event-ID`; content types: `application/json`, `text/event-stream`
- Optional `EventStore` for resumability

**Error handling:** two-level — agent-facing `ToolRuntimeError` (safe, stable) vs. developer `FatalToolError` (full exception). `can_retry` + `retry_delay` fields enable framework-level retry policy.

**Streaming:** HTTP MCP transport uses SSE with `Last-Event-ID` for resumability; `EventStore` optional

---

### Exa — Agentic Search, Research, And Websets (KNOWN-CODE)

**Loop shape:** evented plan/task graph — not a turn-based ReAct loop. Research is a persistent async job with SSE event stream.

**Models (KNOWN-CODE from `exa-js/src/research/openapi.ts`):**
- SDK default: `exa-research-fast`
- OpenAPI enum: `exa-research-fast`, `exa-research`, `exa-research-pro`
- `exa-research`: faster and cheaper; `exa-research-pro`: more thorough, stronger reasoning

**Base search constants (KNOWN-CODE from `exa-js/src/index.ts`):**
- Base URL: `https://api.exa.ai`
- Auth header: `x-api-key`
- User-Agent: `exa-node ${version}`
- `DEFAULT_MAX_CHARACTERS = 10_000`
- If no contents specified: search returns text with `maxCharacters: 10000`
- Deep search additional queries: max 5 (code comment)
- Search types: `keyword`, `neural`, `auto`, `hybrid`, `fast`, `instant`
- Deep search types: `deep-lite`, `deep`, `deep-reasoning`
- Streaming via `streamSearch()` → SSE chunks (OpenAI-style)

**Research API (KNOWN-CODE from `exa-js/src/research/client.ts`):**
- `ResearchClient.create` → `POST /research/v1`
- `get(id, {stream: true})` → SSE
- Poll defaults: interval `1000 ms`, timeout `600_000 ms` (10 min), max consecutive failures `5`

**Research event type architecture (KNOWN-CODE — these ARE the pipeline):**
- `research-definition` — top-level job descriptor
- `plan-definition` — planner emits plan
- `plan-operation` — type = `think` | `search` | `crawl`
  - `think`: reasoning content
  - `search`: goal, pageTokens, query, result URLs, searchType
  - `crawl`: goal, pageTokens, result URL
- `plan-output` — type = `tasks` (reasoning + `tasksInstructions[]`) | `stop` (reasoning)
- `task-definition` — per-task descriptor
- `task-operation` — same types as plan-operation
- `task-output` — task result
- `research-output` — final output + cost accounting: pages, searches, reasoning tokens, total cost dollars

**Websets (KNOWN-CODE from `exa-js/src/websets/`):**
- `POST /v0/websets` — create
- `POST /v0/websets/preview` — preview decomposition (with `search=true` for items)
- `GET /v0/websets/{id}/searches`, `/enrichments`, `/items`
- Monitors: cron + timezone for refresh scheduling
- Priority header: `x-exa-websets-priority` = `low` | `medium` | `high`
- INFERRED pipeline: NL query → decomposition → search ops → crawl/extract → filter → items → enrichment columns → monitor refresh

**Context assembly:** output schema validation; output can be constrained with `outputSchema`; `systemPrompt` field on search

**Cost accounting:** explicit per-operation counters in `research-output` (pages, searches, reasoning tokens, total dollars)

**Error handling:** poll timeout after 10 min, max 5 consecutive poll failures before giving up

**Streaming:** SSE for research job events; OpenAI-style chunks for `streamSearch`

---

### Sema4.ai Actions — Enterprise Action Runtime (KNOWN-CODE)

**Core primitive:** Python function + type hints + docstring → typed action exposed to agents via MCP, OpenAPI, custom GPT, and LangChain surfaces.

**Action decorators (KNOWN-CODE):**
- `@action` and `@tool` are interoperable
- `@action(is_consequential=False)` — skip user confirmation for GPT actions
- `@query` — read-only actions
- MCP-specific: `@resource`, `@prompt`

**Server surface (KNOWN-CODE from README):**
- `action-server start` → UI at `http://localhost:8080`, MCP at `http://localhost:8080/mcp`
- `--auto-reload` for development
- `--expose` → creates public URL with bearer auth (persisted in `expose_session.json`)
- Production: user-managed reverse proxy with SSL/auth
- Bearer API key auth supported

**Public tunnel (KNOWN-CODE from `_server_expose.py`):**
- Session payload: `sessionId` + `sessionSecret`; encoded as ASCII hex of `"sessionId:sessionSecret"`
- Public URL: `https://{sessionId}.{expose_url}`
- Headers: `x-session-id`, `x-session-secret`
- Client: `wss://client.{expose_url}` WebSocket
- Ping interval: `4` seconds
- Forwarded request: `requestId`, `path`, `method`, `body`, `headers`
- Response retry: up to `30` seconds before giving up
- Expose session persisted: `expose_session.json` under datadir

**Agent interaction clues (KNOWN-CODE from tests):**
- Prompt generation endpoint: `/api/v2/prompts/generate`
- Test traces include: `thread_id`, `agent_id`, `platform_config_raw`
- Test prompt content includes `tool_use` and `tool_result`
- OAuth2, websocket server, encryption, run errors, and CLI modules present

**Key design rule:** action package is independent from agent runtime; runtime discovers packages and generates API surface dynamically from type hints and docstrings.

---

### Relevance AI — Multi-Agent Workforce Builder (KNOWN-CODE SDK; server black box)

**Core primitive:** orchestrated multi-agent workforce with agents, child agents, tools, knowledge, approvals, triggers, task state machine, and parallel tool calls.

**Task state machine (KNOWN-CODE from `types/task.py`):**
States: `idle`, `starting-up`, `running`, `pending-approval`, `waiting-for-capacity`, `cancelled`, `timed-out`, `escalated`, `unrecoverable`, `paused`, `completed`, `errored-pending-approval`

Unrecoverable error type: `max-tool-retries`

Critical field: `ignore_state_at` — prevents conversations from being permanently locked if agent job stalls (explicit deadlock prevention)

Conversation metadata: `tags`, `user_id`, `agent_id`, `agent_region`, `agent_project`, `bookmark`, `title`, `params_from_previous_trigger`, `caller_agent`, `debug`, `is_debug_mode_task`, `debug_mode_config_id`, `custom_params`, `enable_custom_params`, `state_metadata`

**Message/event roles (KNOWN-CODE):**
- `tool-run`
- `action-confirm`
- `action-confirm-mock-tool-output`
- `agent-error`
- `terminate-conversation`

**Multi-agent coordination (KNOWN-CODE from `types/agent.py`):**
- `Multiagent` has `child_agents`
- `parallel_tool_calls: Optional[bool]` on agent config
- Child agent delegation via `caller_agent` field
- `agent_decide_prompt` guides action approval/decision behavior

**Knowledge schema (KNOWN-CODE):**
- Chunking: `SplitMethod.type = num_tokens`; `split_chunk` = `token` | `sentence` (default `sentence`)
- Vectorizing states: `unvectorized`, `vectorizing`, `vectorized`, `failed`
- `TableMetadata.tool_columns`: maps UUID → chain metadata + param mapping + output mapping
- Tool columns can infer params from table fields or accept manual values; can overwrite existing columns

**API surface (KNOWN-CODE):**
- Base URL: `https://api-{region}.stack.tryrelevance.com/latest`
- Auth: `{project}:{api_key}` in Authorization header
- Client managers: `agents`, `knowledge`, `tools`, `tasks`, `oauth`

**Memory type:** `short-term-memory` (field on agent config)

---

### Glean — Enterprise Graph-Grounded Agents (KNOWN-DOC only)

**Architecture (INFERRED):** enterprise graph (content + people + activity) as permission-aware retrieval backbone, not vector DB.

- 100+ connectors; crawler extracts titles, body, comments, media, creator, creation time, update history, file type, folder structure, permissions
- Crawl config: inclusion/exclusion by asset id/container, crawl frequency, blackout periods
- Knowledge graph includes people: identities, roles, teams, org relationships; activity: interactions, document history, engagement
- LLM hosting: Bedrock, Azure OpenAI, Vertex AI, OpenAI (Glean is model-agnostic)
- Agent primitive: "agents reason over company knowledge graph, not just prompt window"
- ACLs stored as first-class filters, never as prompt text

**Key rule (INFERRED):** permission trim must run before LLM context assembly. If ACL layer is wrong, agent is wrong regardless of model strength.

---

### Writer — Enterprise AI Studio + Palmyra + Knowledge Graph (KNOWN-DOC)

**Models:** Palmyra X5 (confirmed), Palmyra X4 (minimum for KG chat tool), external via AWS Bedrock

**Knowledge Graph tool calling (KNOWN-DOC from `dev.writer.com/api-guides/kg-chat`):**
```json
{
  "model": "palmyra-x5",
  "messages": [{"role": "user", "content": "question"}],
  "tool_choice": "auto",
  "tools": [{
    "type": "graph",
    "function": {
      "description": "...",
      "graph_ids": ["<GRAPH_ID>"],
      "subqueries": true
    }
  }],
  "stream": true
}
```
- Endpoint: `https://api.writer.com/v1/chat`
- Only one prebuilt graph tool at a time
- Tool type `"graph"` with fields: `graph_ids`, `description`, `subqueries`, `query_config`
- Streaming: `"stream": true` → SSE

**Graph construction (INFERRED):** specialized LLM processes data at scale and builds semantic relationships; graph-based RAG supports source citations, broad-question decomposition, subquestions

**Observability:** OpenLLMetry for telemetry export; usage/cost tracking; session logs; individual agent performance

---

### Relevance AI / Lindy / Clay / Genspark / Hebbia — Inferred Architectures

**Lindy (INFERRED):** workflow as DAG; node types: trigger, LLM action, integration action, condition, loop, approval, wait/schedule; parallel branches with join; idempotency keys on external actions; human approval gate; run logs; model router: cheap for classification, stronger for planning/writing

**Clay (INFERRED):** table-first agent pattern; rows = leads/accounts; columns = enrichment outputs; waterfall = ordered providers with stop-condition fallback ending in Claygent (GPT-4-based browser/research agent); each cell stores provenance + source URL; enrichment column config: ordered providers, stop condition, input/output mapping, cost cap, cache TTL

**Genspark (INFERRED):** super-agent planner → model/tool router → tool packs (browser, terminal, artifacts, data, voice); every action writes artifact tree; final response links artifact ids; production feedback loop: tool selection + model routing examples → training/eval data for future routing

**Hebbia Matrix (INFERRED):** rows = documents/entities/questions; columns = extraction questions; cells = agent runs; decomposition improves over time without retraining; model routing: o3-mini/o1/GPT-4o depending on step; OCR + table extraction + chart captioning; citations per cell; row/column dependencies form DAG

---

### Composite Stack (What To Build First — KNOWN-DOC/DESIGNED)

Priority build order from §13:

1. Mem0-style memory service (additive extraction, entity boost, hybrid search, MCP tools)
2. Arcade-style tool runtime (schema/auth/error/worker/MCP)
3. Exa-style research trace API (evented planner/search/crawl with persistent Websets)
4. Sema4-style action server (Python packages → OpenAPI/MCP)
5. Relevance-style workforce runner (task state machine, approvals, child agents, task steps, short-term memory)

```
USER/TASK
  └── Relevance-style workflow runner
        ├── Mem0-style long-term memory (↔ feedback)
        ├── Exa-style research/search
        ├── Arcade-style tool/auth runtime
        │     └── Sema4-style Python action server
        └── event log + task steps
```

---

## → Verso Implications

- **Memory is a first-class primitive, not an afterthought.** Mem0's architecture reveals that write-path quality determines recall quality. Verso should ship a memory service interface where write = additive extraction (ADD-only LLM, no UPDATE/DELETE from model), read = hybrid (semantic + BM25 + entity boost), and the framework never silently overwrites. The entity link threshold (`0.95`) and boost weight (`0.5`) are reasonable starting defaults for Verso's memory module.

- **Scope keys are mandatory.** Every memory operation in Mem0 requires at least one of `user_id`, `agent_id`, `run_id`. Verso agents should carry a scope tuple at construction time; the framework should inject it into every memory read/write automatically, never requiring the developer to pass it manually per call.

- **Tool calling has two error channels.** Arcade's executor pattern — agent-facing `ToolRuntimeError` (stable, terse, safe) vs. developer-facing `FatalToolError` (full exception + stacktrace) — must be replicated in Verso. The framework should never forward raw Python exceptions to the model context; it should always convert to a structured, model-stable error envelope with `can_retry` and `retry_delay` fields so the agent loop can act on them.

- **Tool auth is a first-class framework concern, not a user problem.** Arcade encodes 21 OAuth providers as tool metadata. Verso should ship an `AuthRequirement` type on tool definitions; when an agent tries to call a tool with unsatisfied auth, the framework returns a structured `NeedsAuth` event rather than a tool error, allowing the orchestrator to pause and request credentials without crashing the loop.

- **The MCP bridge must carry auth metadata.** Arcade uses `_meta.arcade.requirements` in MCP tool definitions. Verso's MCP bridge should propagate auth and approval requirements as metadata fields, so any MCP-compatible client can surface them appropriately.

- **Research is a persistent async job, not a synchronous tool call.** Exa's Research API reveals that multi-step search/crawl/synthesis should be modelled as a job with an event log (`plan-definition`, `plan-operation`, `task-definition`, `task-output`, `research-output`) not as a single blocking LLM call. Verso should provide a `ResearchJob` primitive: create job → persist event log → SSE stream → final output with cost accounting.

- **Event log is the agent's durable trace.** Exa's event types (`think`, `search`, `crawl`) per operation and per task are the trace record. Verso should mandate that every agent loop step emits a typed event to a persistent event log, not just to stdout. This enables replay, debugging, billing, and UI streaming simultaneously.

- **Cost accounting belongs in the framework.** Exa's `research-output` includes pages, searches, reasoning tokens, and total cost dollars. Verso's agent executor should maintain per-run cost counters (input tokens, output tokens, tool calls, external API calls) and expose them in the run result envelope.

- **Task state machine should include deadlock prevention.** Relevance AI's `ignore_state_at` field is a deadlock escape hatch for stalled agent jobs. Verso should implement a configurable max-staleness timeout per task state: if an agent stays in `running` for longer than `T`, the framework automatically transitions to `timed-out` and triggers error recovery rather than hanging indefinitely.

- **Approval gates belong in the task state machine.** Relevance AI has `pending-approval` and `errored-pending-approval` as first-class task states, plus `action-confirm` as a message role. Verso should provide an opt-in approval gate at the tool-call boundary: before executing a consequential tool, the framework emits an `ApprovalRequest` event and suspends; on approval/rejection, the loop resumes or cancels. This maps directly to Sema4.ai's `is_consequential` decorator.

- **Parallel tool calls must be explicit and opt-in.** Relevance AI exposes `parallel_tool_calls: Optional[bool]` on agent config. Verso should not silently parallelize tool calls; parallelism should be declared per-agent or per-tool-group, and the framework should handle join semantics (wait-all vs. first-success vs. first-non-null).

- **Child agent delegation requires a `caller_agent` field in task records.** Relevance AI's `caller_agent` field and `Multiagent.child_agents` reveal that multi-agent systems require explicit parent-child linkage in the task store. Verso should record `parent_task_id` and `spawned_by_agent_id` on every task, enabling full trace attribution and preventing orphaned subtasks.

- **Action packaging should be independent of agent runtime.** Sema4.ai's core rule: keep action packages independent from the agent runner. In Verso, tools/actions should be deployable as standalone action servers with their own OpenAPI and MCP surfaces, then registered with the agent runtime. The runtime discovers tools dynamically; tools do not depend on the runtime.

- **Enterprise context assembly is permission-first, not prompt-first.** Both Glean and Writer confirm: in enterprise settings, ACL/permission trim must execute before LLM context assembly. Verso's context assembler should accept a permission scope at call time and apply it as a hard filter before ranking or selecting context chunks — never encode permissions in the prompt.

- **Graph retrieval is a named tool type.** Writer's `type: "graph"` tool in the chat API, with explicit `subqueries: true` and `graph_ids`, shows that graph-based RAG should be exposed as a first-class tool type in Verso's tool registry — not wired as a special code path in the agent loop. Verso should treat RAG (vector), Graph RAG, BM25, and web search as interchangeable named retrieval tools.

- **Waterfall enrichment is a reusable agent primitive.** Clay's enrichment column pattern (ordered providers, stop-on-found, cost cap, cache TTL, provenance) is broadly applicable beyond GTM. Verso should offer a `Waterfall` step type in workflow DAGs: try providers in order, stop on success, track provenance, respect cost caps, cache results.

- **Model routing should be logged for eval feedback.** Genspark's production feedback loop — accumulating successful tool selection and model routing examples from production into training/eval data — is the right design. Verso should log every routing decision (task classification → model chosen → outcome) so the routing policy can be evaluated and improved without retraining the main model.

- **Every agent action should produce an artifact with an ID.** Genspark's artifact tree model (every action writes to artifact tree; final response links artifact IDs; artifacts are editable/re-runnable) is the correct mental model for agentic workspaces. Verso should define an `Artifact` type in its data model and require action results to declare their artifact type, enabling downstream composition and re-use.

- **Hebbia's "improve decomposition over time without retraining" is achievable with a plan cache.** The pattern: store successful decompositions keyed by task type/domain; on similar future tasks, retrieve and adapt prior decompositions as few-shot examples to the planner. Verso should support a pluggable `PlanCache` that agents can consult before generating a fresh plan.

- **Chunk-before-embed with `text_lemmatized` metadata is correct.** Mem0 stores `text_lemmatized` as a dedicated metadata field alongside raw text, enabling BM25 search over lemmatized form while preserving original text for display. Verso's memory module should maintain both forms; do not lemmatize at query time without a lemmatized index to match against.

- **MCP session IDs must be visible ASCII; enforce at the framework boundary.** Arcade's validation rule (`Mcp-Session-Id` must be visible ASCII) is a real interoperability constraint. Verso's MCP server module should validate session ID format at ingress and reject non-conforming clients with a clear error before they reach agent logic.

- **Poll timeout and consecutive failure limits are infrastructure constants, not magic numbers.** Exa's research poll defaults (interval `1000 ms`, timeout `600_000 ms`, max failures `5`) should be configurable per-task in Verso's async job runner. Expose them as first-class task config fields, not buried in HTTP client retry logic.
