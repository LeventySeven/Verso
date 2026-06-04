# Top Agentic Startups RE

Source file: `/Users/seventyleven/Desktop/researchfms/core/15_TOP_AGENTIC_STARTUPS_RE.md`
Freshness: 2026-04-26. Evidence depth: very high for Browserbase/Stagehand, Firecrawl, Dust, E2B, Composio (cloned source). Medium-high for Tavily, AgentQL, Nia (local teardowns). Medium/INFERRED for Sierra, Harvey, Factory, Decagon, Cognition (official posts only, no source).

---

## `15_TOP_AGENTIC_STARTUPS_RE.md`

### Agent Loop Shape

**Browserbase / Stagehand (KNOWN from source `packages/core/lib/v3/handlers/v3AgentHandler.ts`):**
- ReAct-style loop: `for step in range(maxSteps)` → generate(system, tools, temp=1) → execute tool calls → check for `done` tool → refresh page URL.
- `maxSteps = options.maxSteps || 20` (default 20 for normal agent; default 10 for CUA handler).
- Loop terminates when model calls the `done` tool; if it exits without calling it, `ensureDone()` forces extraction.
- `toolChoice: "auto"`. `temperature: 1` for both generation modes (streamText/generateText).
- Two handlers: `V3AgentHandler` (DOM/hybrid tools + MCP), `V3CuaAgentHandler` (screenshot-action loop for Google/OpenAI CUA).
- Anthropic system prompt gets `cacheControl: { type: "ephemeral" }` via provider metadata.
- `FlowLogger.createLlmLoggingMiddleware(baseModel.modelId)` wraps every model call; records usage metrics after CUA execute.

**Firecrawl interact browser agent (KNOWN from `apps/api/src/lib/scrape-interact/browser-agent.ts`):**
- Simple step-capped loop: `MAX_STEPS = 25`, `SNAPSHOT_TIMEOUT = 15`, `SNAPSHOT_MAX_CHARS = 40000`.
- Single tool exposed: `browser` (CLI command surface).
- Temperature: `0` (not 1 — explicit anti-hallucination choice for browser automation).
- Stop condition: `stepCountIs(MAX_STEPS)`.

**Dust (KNOWN from monorepo `agentLoopWorkflow`):**
- Temporal-backed durable loop: `for (let i = startStep; i < MAX_STEPS_USE_PER_RUN_LIMIT + 1; i++)`.
- `MAX_STEPS_USE_PER_RUN_LIMIT = 64`.
- Loop can PAUSE for human approval and RESUME from `startStep` without losing state.
- Graceful stop: lets current step finish, exits at next step boundary. Hard cancel via `CancellationScope`.
- If no tool calls on a step → break (unless resume with null runId, then continue).
- Tool calls execute concurrently (`Promise.all`). Deferred events published after all tools complete.
- Model activity: start-to-close 10 min, heartbeat 60s. Tool activity: heartbeat 60s, timeout = max(10min, 3min MCP) + 60s.
- `RUN_MODEL_MAX_RETRIES = 5`, backoff coefficient 1. Non-idempotent tools: `maximumAttempts: 1`. Retryable tool: `RETRY_ON_INTERRUPT_MAX_ATTEMPTS = 15`.
- Queue: `agent-loop-queue-v2`.

**Aemon evolutionary agent (KNOWN from local bundle/source RE):**
- NOT a ReAct loop — MAP-Elites evolutionary search: CONCEPTUALIZE(20%) → EVOLVE(45%) → IMPROVE(70%) → STEER(reset to 0%) → SOLUTION(100%).
- User steering = full reset to 0% + constraint update, not a chat reply appended to context.
- Archive of diverse candidates (MAP-Elites), not just best-so-far.
- Mutation via SEARCH/REPLACE style edit operations.
- Eval cascade: syntax check first, then sandbox (cheap before expensive).

---

### Models (Exact Names + Roles)

| Company | Model | Role | Source |
|---------|-------|------|--------|
| Stagehand | Any provider (AI SDK `generateText`/`streamText`) | Agent generation | KNOWN |
| Stagehand FARA | `Qwen2.5-VL-7B` (SFT, not RL) + `fara-7b` string | Browser action model; 145,603 trajectories, 70,117 domains, ~1.8M samples, 64 H100s ~2.5 days | KNOWN local teardown |
| Stagehand hybrid mode warn | Warns unless model id contains `gemini-3-flash` or `claude` | Hybrid mode guard | KNOWN |
| Firecrawl SmartScrape planner | `gemini-2.5-pro` (Vertex) | Planning/tool-choice | KNOWN |
| Firecrawl SmartScrape executor | `gemini-2.0-flash` (Google) | Tool execution | KNOWN |
| Firecrawl interact | `gemini-2.5-flash` (Google) | Browser interact loop | KNOWN |
| Firecrawl deep research final | `o3-mini` | Final synthesis | KNOWN |
| Aemon primary | Gemini Flash | Main mutations | KNOWN local |
| Aemon secondary | Claude Sonnet (15% of time) | Diversity sampling | KNOWN local |
| Tavily retrieval | Cohere `embed-english-v3.0` (1024d) | Embedding | KNOWN |
| Tavily local crawl2rag | `gpt-4.1-nano` + `text-embedding-3-large` | Crawl pipeline | KNOWN local |
| Nia oracle (live probe) | `claude-opus-4-7` | Main reasoning/search | KNOWN live API probe |
| Nia embed | `zembed-1` (Qwen3-4B fine-tune, 4.02B params, 32K ctx, 2560-dim) | Code/doc embedding | KNOWN |
| Nia rerank | `zerank-2` (4B Qwen3 cross-encoder, +8.7pp NDCG@10 vs Cohere rerank-3.5) | Reranking | KNOWN |

---

### Tool Registry (Full Schemas / Names)

**Stagehand DOM mode tools (KNOWN from `agentSystemPrompt.ts`):**
- `screenshot`, `ariaTree`, `act`, `keys`, `fillForm`, `think`, `extract`, `goto`, `wait`, `navback`, `scroll`
- + `search` (requires `useSearch` flag + `BROWSERBASE_API_KEY`, or `BRAVE_API_KEY`)
- Variables addressed as `%variableName%`

**Stagehand hybrid mode tools (KNOWN):**
- All DOM tools + `click`, `type`, `dragAndDrop`, `clickAndHold`, `fillFormVision` (direct coordinate tools)
- Hybrid falls back DOM→a11y→act in that priority order

**Stagehand CUA tools (KNOWN from `v3CuaAgentHandler.ts`):**
- Screenshot → computer-use action → screenshot response cycle
- Default viewport: `{ width: 1288, height: 711 }` (smart resize: patch factor 28, 1288x711→1288x700)
- Inter-action delay: 500ms around typing, otherwise 200ms
- Pre-action delay: 300ms

**Stagehand MCP (KNOWN from `mcp/connection.ts`, `mcp/utils.ts`):**
- Transports: stdio + Streamable HTTP
- Client identity: `{ name: "Stagehand", version: "1.0.0" }`
- Connect → ping; failure raises `MCPConnectionError`
- Tool resolution paginates `listTools(cursor)`, converts JSON Schema → Zod, wraps `client.callTool`
- MCP tools OVERWRITE native tools on name conflict (current behavior; `{ ...tools, ...this.mcpTools }`)

**Firecrawl `/v2/agent` actions schema (KNOWN from `types.ts`):**
- `ACTIONS_MAX_WAIT_TIME = 60` (seconds total wait)
- `MAX_ACTIONS = 50`
- Action union: wait, click, screenshot, write, press, scroll, scrape, executeJavascript, pdf
- Model enum: `["spark-1-pro", "spark-1-mini"]`, default `spark-1-pro`
- Webhook events: `started`, `action`, `completed`, `failed`, `cancelled`
- Prompt max length: 10,000

**Firecrawl interact browser agent commands (KNOWN from system prompt):**
- snapshot, click, fill, type, select, check, press, keyboard type, hover, scroll, get text/title/url, wait, find text/role/placeholder, frame, eval, back
- Workflow: initial snapshot → interact with `@refs` → snapshot after changes → repeat

**Dust tool resolution (KNOWN from monorepo):**
- Resolver gathers: JIT servers + client-side MCP configs + enabled/system/equipped skills + skill servers + MCP tools
- `ask_user_question` filtered out for non-web/slack/extension/agent_sidekick origins
- On last step, available actions set to empty (forces final text generation)
- Duplicate tool/spec names → user-facing `duplicate_specification_name` error
- Missing tool called → `missing_action_catcher` internal MCP server (if available)

**Composio tool router session (KNOWN from Python SDK):**
- Session exposes: `tools`, `authorize`, `toolkits`, `search`, `execute`, `files`
- Meta multi-execute slug: `COMPOSIO_MULTI_EXECUTE_TOOL`
- `MAX_PARALLEL_WORKERS = 5` (ThreadPoolExecutor)
- Routing: local custom tools run in-process; remote tools forwarded to backend
- If all remote → entire payload to backend. If mixed → local submitted individually, remote batched into one backend call
- Remote results merged first; local results appended
- Single local tool + no remote → result returned unwrapped
- `proxy_execute`: proxies arbitrary API call through Composio auth layer (toolkit/endpoint/method/body/params)
- MCP server type: `streamable_http`; generated per user/session with toolkits + allowed_tools + `manually_manage_connections`

**Tavily MCP (KNOWN from local teardown):**
- 5 MCP tools
- Crawl tool: `chunks_per_source = 3` hardcoded
- HybridRAG: `numCandidates = max_local + 3`, cosine enforced at init
- Vector search: k=20, then k=10 after `thread_id`
- Research internal tool name: `WebSearch`
- Citation format enum: numbered, mla, apa, chicago
- OAuth discovery at `mcp.tavily.com/.well-known`

**Nia MCP (KNOWN from local teardown):**
- MCP v1.1.2: 16 tools + 4 filesystem write tools
- Universal search: `alpha=0.7`, `top_k=20`, `repo_boost=1.2`
- Accuracy mode: `["fast", "slow"]` → ZeroEntropy latency modes `["low", "high"]`
- `citation_boost=0.15`, `statute_boost=0.10`, `max_hops=3`, `top_n=50`
- NIATokenVerifier: 120s cache using `sha256(token)[:16]`
- Connector types: imessage, whatsapp, contacts, telegram, database
- Company data graph tools: list, locate_in_tree, find, search, cat (never cat without limit; max 10,000 chars per Dust Deep Dive policy)

---

### Context Assembly / Compaction / Budgets

**Dust (KNOWN):**
- Allowed tokens = `model.contextSize - model.generationTokensCount`
- Pruning order: previous interaction tool results (all) → current interaction tool results (oldest-to-newest)
- Pruned placeholder (previous): `<dust_system>This function result is no longer available.</dust_system>`
- Pruned placeholder (current): includes context-overflow warning
- Pruned token estimates: previous = 20 tokens/result, current = 40 tokens/result
- Pruned context emits `agent_context_pruned` once; updates DB/memory

**Dust output offload thresholds (KNOWN):**
- Text blocks > 20KB → offload to file
- Image blocks > 2MB → offload
- Resource blocks > 20MB → offload
- Remote tool hard limits: 2MB text, 2MB image, 20MB resource, 50MB total result array rejection
- Snippet length fed back to model: 8,000 chars
- Tool output processing concurrency: 10
- Offloaded text files skip data-source indexing (model reads by `cat` instead of semantic search)

**Dust streaming/coalescing (KNOWN):**
- Generation tokens batched with default flush interval: 100ms
- Max buffer age: 60s
- Cleanup interval: 5 min
- Delimiter events bypass batching → flush immediately
- Classification changes → flush existing token buffer

**Stagehand deterministic act cache (KNOWN from `ActCache.ts`):**
- Cache key: `sha256(JSON.stringify({ instruction, url, variableKeys }))`
- Stored: instruction, url, variableKeys, actions, actionDescription, message; version = 1
- Hit path: `waitForCachedSelector` → `takeDeterministicAction`
- No TTL visible in source

**Firecrawl deep research state (KNOWN from `research-manager.ts`):**
- `ResearchStateManager` tracks: findings, summaries, nextSearchTopic, urlToSearch, currentDepth, failedAttempts, seenUrls, sources
- `maxFailedAttempts = 3`
- `totalExpectedSteps = maxDepth * 5`
- `addFindings` keeps most recent 50 findings
- Prompt trim target: 100,000 tokens

---

### Memory (Persistence, TTLs, Backends)

**Dust (KNOWN):**
- Memory injected per agent via `AgentMemoryResource.findByAgentConfigurationIdAndUser`
- Toolsets context lists MCP server views in global space (excludes `auto_hidden_builder`)
- Memory/context APIs are first-class — contexts are addressable

**Nia/ZeroEntropy (KNOWN from local teardown):**
- Memory types have TTLs (exact TTL values not in this file; confirmed in local teardown `teardowns/NIA.md`)
- Retrieval backends: repos, docs, packages + connectors (imessage, whatsapp, contacts, telegram, database)

**Dust Deep Dive sub-agents (KNOWN):**
- Sub-agents do NOT get prior context — self-contained task scoping is enforced
- If sandbox available, sub-agents lack sandbox access; sandbox work must stay in primary agent

---

### System Prompts (Verbatim/Near-verbatim)

**Stagehand agent system prompt (KNOWN from `agentSystemPrompt.ts`):**
- Injects current date via `new Date()`
- System prompt cache via Anthropic provider metadata: `cacheControl: { type: "ephemeral" }`
- Injected as first user message for CUA/Google: `System prompt: ...` then user instruction

**Firecrawl interact system prompt (KNOWN from source):**
- Defines "browser automation agent" with CLI-style command surface
- Workflow instruction: use initial snapshot, interact with @refs, snapshot after changes, repeat

**Dust Deep Dive global agent prompt (KNOWN from monorepo):**
- Complex request must start with a plan → planning agent reviews it
- Complex = decompose into small sub-tasks; use sub-agents for heavy browsing/data warehouse queries
- Sub-agent tasks must be: atomic, outcome-scoped, self-contained
- Max 6 concurrent sub-agent tasks
- Cat tool: never use without limit; maximum 10,000 chars

---

### Error Handling Paths

**Dust (KNOWN):**
- `runModelAndCreateActionsActivity` has `RUN_MODEL_MAX_RETRIES = 5`
- Tool activities with `maximumAttempts: 1` (non-idempotent — no auto-retry)
- Retryable tool: `RETRY_ON_INTERRUPT_MAX_ATTEMPTS = 15`
- Cancellation: `CancellationScope` cancels in-flight activities
- Finalization always runs in non-cancellable scope
- Duplicate tool names → `duplicate_specification_name` user-facing agent error
- Missing action called → `missing_action_catcher` MCP server (soft fallback)

**Stagehand (KNOWN):**
- No done tool called before `maxSteps` → `ensureDone()` forces extraction
- CUA if page is blank → navigate to `https://www.google.com`
- MCP connect failure → `MCPConnectionError`
- CUA retry policy: `maxRetries = 5`, `baseDelayS = 1`, exponential backoff `baseDelayS * 2^attempt`
- Captcha solver blocks pre-step while solving
- Coordinates above 999 sanitized to 999; images compressed to max 2 recent

**Firecrawl (KNOWN from `nuq.sql`):**
- Lock reaper every 15s; locks older than 1min requeued if `stalls < 9`, failed if `stalls >= 9`
- Completed cleanup every 5min for rows > 1hr old with null group
- Failed cleanup every 5min for rows > 6hr old
- Backlog reaper every 1min; orphan null-timeout rows > 25hr handled
- Daily reindex at 09:00

**Aemon (KNOWN from local RE):**
- Eval cascade: syntax check → sandbox eval (cheap-before-expensive)
- User STEER → full reset to 0% (constraint update, not incremental chat)

---

### Exact Constants

| System | Constant | Value | Source |
|--------|----------|-------|--------|
| Stagehand | maxSteps (agent) | 20 | KNOWN |
| Stagehand | maxSteps (CUA) | 10 | KNOWN |
| Stagehand | temperature | 1 | KNOWN |
| Stagehand | CUA inter-action delay | 500ms (typing), 200ms (other) | KNOWN |
| Stagehand | CUA pre-action delay | 300ms | KNOWN |
| Stagehand | CUA viewport | 1288×711 | KNOWN |
| Stagehand | CUA config: topP, topK, maxOutputTokens | 0.95, 40, 8192 | KNOWN |
| Stagehand | FARA context length | 128k | KNOWN |
| Stagehand | FARA action space | 11 actions | KNOWN |
| Stagehand | Smart resize patch factor | 28 | KNOWN |
| Firecrawl | MAX_STEPS (interact) | 25 | KNOWN |
| Firecrawl | SNAPSHOT_TIMEOUT | 15s | KNOWN |
| Firecrawl | SNAPSHOT_MAX_CHARS | 40,000 | KNOWN |
| Firecrawl | temperature (interact) | 0 | KNOWN |
| Firecrawl | ACTIONS_MAX_WAIT_TIME | 60s | KNOWN |
| Firecrawl | MAX_ACTIONS | 50 | KNOWN |
| Firecrawl | maxFailedAttempts (deep research) | 3 | KNOWN |
| Firecrawl | findingsCapacity | 50 | KNOWN |
| Firecrawl | promptTrimTarget | 100,000 | KNOWN |
| Firecrawl | SmartScrape input cost | 1.3 | KNOWN |
| Firecrawl | SmartScrape output cost | 5 | KNOWN |
| Firecrawl | lock reaper interval | 15s | KNOWN |
| Firecrawl | stall limit before fail | 9 | KNOWN |
| Firecrawl | lock TTL before requeue | 1min | KNOWN |
| Dust | MAX_STEPS | 64 | KNOWN |
| Dust | model activity timeout | 10min | KNOWN |
| Dust | heartbeat timeout | 60s | KNOWN |
| Dust | DEFAULT_MCP_REQUEST_TIMEOUT_MS | 3min (180,000ms) | KNOWN |
| Dust | RUN_AGENT_CALL_TOOL_TIMEOUT_MS | 10min (600,000ms) | KNOWN |
| Dust | RUN_MODEL_MAX_RETRIES | 5 | KNOWN |
| Dust | RETRY_ON_INTERRUPT_MAX_ATTEMPTS | 15 | KNOWN |
| Dust | Deep Dive max concurrent sub-agents | 6 | KNOWN |
| Dust | token batch flush interval | 100ms | KNOWN |
| Dust | max buffer age | 60s | KNOWN |
| Dust | cleanup interval | 5min | KNOWN |
| Dust | offload text threshold | 20KB | KNOWN |
| Dust | offload image threshold | 2MB | KNOWN |
| Dust | offload resource threshold | 20MB | KNOWN |
| Dust | remote result array hard limit | 50MB | KNOWN |
| Dust | snippet length fed to model | 8,000 chars | KNOWN |
| Dust | tool output concurrency | 10 | KNOWN |
| Dust | pruned result token est. (previous) | 20 | KNOWN |
| Dust | pruned result token est. (current) | 40 | KNOWN |
| Dust | MCP JS SDK heartbeat | 5min | KNOWN |
| Dust | MCP CLI heartbeat | 15min | KNOWN |
| Dust | MCP reconnect delay | 5s | KNOWN |
| E2B | NBD pool default | 64 | KNOWN |
| E2B | envd port | 49983 | KNOWN |
| Composio | MAX_PARALLEL_WORKERS | 5 | KNOWN |
| Tavily | crawl chunks_per_source | 3 | KNOWN |
| Tavily | HybridRAG numCandidates | max_local + 3 | KNOWN |
| Tavily | vector search k | 20 (then 10 after thread_id) | KNOWN |
| Tavily | research polling start | 2s (×1.5, cap 10s) | KNOWN |
| Tavily | research timeout (mini) | 5min | KNOWN |
| Tavily | research timeout (pro/auto) | 15min | KNOWN |
| Tavily | SimpleQA target | 93.3% | KNOWN |
| Nia | universal search alpha | 0.7 | KNOWN |
| Nia | universal search top_k | 20 | KNOWN |
| Nia | repo_boost | 1.2 | KNOWN |
| Nia | citation_boost | 0.15 | KNOWN |
| Nia | statute_boost | 0.10 | KNOWN |
| Nia | max_hops | 3 | KNOWN |
| Nia | top_n | 50 | KNOWN |
| Nia | token verifier cache TTL | 120s | KNOWN |
| Nia | cat tool max chars | 10,000 | KNOWN |
| AgentQL | run timeout | 600,000ms (10min) | KNOWN |
| AgentQL | retry timing | 0.5s, max 8s, 2 retries | KNOWN |

---

### Multi-Agent Coordination

**Dust Deep Dive (KNOWN from monorepo + official blog):**
- Primary agent classifies: simple vs complex request
- Complex: primary agent generates plan → planning agent reviews → primary decomposes into atomic sub-tasks
- Sub-agents receive self-contained tasks (no prior context inheritance by default)
- Max 6 concurrent sub-agent tasks
- Sub-agents handle: heavy browsing, company data queries, data warehouse queries
- Sandbox work stays in primary agent (sub-agents cannot access it)
- Parent owns: plan, synthesis, final answer

**Sierra (INFERRED from official platform):**
- Supervisor/router separation: routing, task execution, safety, and final answer are different models
- Multiple models behind one Agent OS; routed by task/risk/cost
- Long-term customer memory + policy/procedure memory

**Firecrawl Spark `/v2/agent` (INFERRED):**
- Forwarded to closed internal service at `EXTRACT_V3_BETA_URL`
- Auth: `Bearer AGENT_INTEROP_SECRET`
- Response immediate: `{ success: true, id }` — async result via webhook events

---

### Streaming Protocol

**Dust (KNOWN):**
- MCP SDK transport: SSE to receive requests, HTTP POST to send results back
- SSE events carry `eventId` and `data`; `lastEventId` stored for reconnect
- Generation tokens batched 100ms before flush; delimiter events bypass buffer

**Firecrawl (KNOWN):**
- Webhook events: `started`, `action`, `completed`, `failed`, `cancelled`
- Deep research: async polling start 2s, backoff ×1.5, cap 10s

**AgentQL / TinyFish Mino (KNOWN from local teardown):**
- SSE streaming events: STARTED, STREAMING_URL, PROGRESS, HEARTBEAT, COMPLETE

---

### Infrastructure + Persistence Primitives

**E2B sandbox (KNOWN from `e2b-dev/infra` source):**
- Firecracker microVMs (not Docker) for hostile code execution
- In-VM daemon `envd` exposes process API + filesystem API via Connect RPC; port 49983
- API: Go/Gin REST; auth JWT via Supabase
- Persistence: PostgreSQL (primary), ClickHouse (analytics), Redis (cache/state)
- IaC: Terraform + Nomad
- Client proxy: Consul service discovery + Redis-backed state
- Sandbox states: running, paused
- Network config per sandbox: allowPublicTraffic, allowOut, denyOut, maskRequestHost
- Lifecycle timeout actions: kill or pause; auto-resume config
- Template/snapshot: IDs are product-level concepts; peer chunk proto allows local cache bypass vs GCS hot path
- NBD pool default 64; snapshot cache fast path for already-cached byte ranges
- MCP config can attach to sandbox

**Firecrawl NUQ queue (KNOWN from `nuq-postgres/nuq.sql`):**
- `queue_scrape` table: id UUID, status enum default `queued`, data JSONB, priority default 0, lock UUID, locked_at, stalls, finished_at, listen_channel_id, returnvalue, failedreason, owner_id, group_id
- Autovacuum tuned: scale factor 0.01, cost limit 10,000, delay 0
- Optimal index: `(priority ASC, created_at ASC, id) WHERE status='queued'`
- Daily reindex: 09:00

**Composite recommended service map (KNOWN from synthesis section):**
- `api`: auth, run creation, SSE, approval endpoints (FastAPI/Next)
- `orchestrator`: Temporal worker or durable queue loop
- `model-gateway`: provider routing, tracing, retries, structured output
- `tool-router`: MCP/Composio-compatible session tool layer
- `browser-service`: Stagehand/Playwright/Understudy adapter
- `sandbox-service`: E2B-compatible microVM adapter
- `retrieval-service`: Tavily/Nia-inspired search/memory
- `eval-service`: trace evaluator
- `postgres`: run/event/action/state tables
- `redis`: stream fanout, locks, short-lived caches
- `object-store`: offloaded tool outputs, screenshots, traces

**Minimal agent event schema (synthesized from Dust/Firecrawl/Browserbase, shown verbatim):**
```sql
agent_runs(id uuid, user_id, agent_id, status, created_at, updated_at)
agent_events(id bigserial, run_id uuid, step int, type text, payload jsonb, created_at)
agent_actions(id uuid, run_id uuid, step int, tool_name text, input jsonb, status text,
              output jsonb, needs_approval boolean default false, created_at)
```

---

### Evaluation / Governance

**Decagon (INFERRED from official AOP, Watchtower, Duet posts):**
- Agent Operating Procedures (AOP) = versioned DSL/markdown procedure artifacts
- `procedure_steps` with required tools, constraints, escalation triggers
- Watchtower QA agent inspects BOTH final answer AND process trace (event log)
- Duet self-improvement: proposes procedure diffs requiring human approval before applying
- Self-improvement updates procedures/evals — NOT silent prompt mutation

**Harvey (INFERRED from official posts):**
- Custom embedding: `voyage-law-2-harvey` (Harvey + Voyage partnership)
- Data Factory: eval tests for citations, hallucination, jurisdiction, privilege, source freshness
- Eval is more important than the prompt

**Factory AI (INFERRED from Code Droid technical report + local teardown):**
- HyperCode: multi-resolution codebase graph (beats flat embeddings for code agents)
- ByteRank: code relevance ranking
- MCTS/LATS-style search over candidate patches
- DroidShield: safety/eval gate for destructive commands and repo mutations
- SWE-bench Lite: ~31.67%
- Eval cascade: terminal/test feedback is the reward signal

**Aemon (KNOWN from local product code):**
- Eval cascade: syntax check → sandbox eval
- Eval results feed MAP-Elites archive scoring

---

### Cross-System Patterns (Architecture Primitives)

**Pattern 1 — Event Log IS the Agent State:**
- Never let LLM conversation string be the only source of truth
- Dust: model calls, tool params, tool results, approvals, finalization are ALL persisted rows
- Firecrawl queue: status, locks, returnvalue, failedReason in DB
- Stagehand: FlowLogger wraps every LLM + action execution

**Pattern 2 — Tool Calls Need Policy, Not Just Schemas:**
- Every tool needs: risk level, retry policy, timeout, output limit, approval behavior
- Dust: stake levels high/medium/low/never_ask; approval gate in loop
- Composio: session auth + connected accounts
- Decagon: AOP procedure gate
- Stagehand: captcha + safety confirmation handlers
- `ToolConfig` schema: `{ name, namespace, inputSchema, timeoutMs, retryPolicy, stake, outputLimits }`

**Pattern 3 — Browser Agents Need Three Perception Channels:**
- DOM/a11y: stable selectors, semantic labels
- Screenshot/vision: visual grounding
- CUA/coordinate: sites that defeat DOM automation
- Rule: do NOT pick one; route per action

**Pattern 4 — Output Offload is Mandatory:**
- Dust: >20KB text → file; snippet (8K chars) + URI fed to model
- Firecrawl: GCS offload paths in product code
- Nia: contexts make retrieved state addressable
- Model reads more via `cat`/read with offset/limit

**Pattern 5 — Sub-Agents Need Isolation + Bounded Concurrency:**
- Dust: max 6 concurrent, self-contained, no prior context by default
- Sub-agents own task execution; parent owns plan/synthesis/final answer

**Pattern 6 — Search/Retrieval Is a Product, Not a Library Call:**
- Full stack: source ingestion, chunking, embedding, reranking, source governance, citation, caching, freshness
- Tavily: proprietary TavilyBot index (not Bing/Exa/Brave wrapper)
- Nia: zembed + zerank + contexts + memory + TTLs
- Harvey: domain-specific embeddings are a real moat

**Pattern 7 — Sandbox is Security Boundary AND Product Surface:**
- Sandbox config part of agent state: template, env vars, network, files, lifecycle, logs
- E2B: Firecracker not Docker; pause/auto-resume as lifecycle states

**Pattern 8 — Evaluation Is The Real Moat:**
- Add evals before scaling tool count
- Log traces so evals can inspect PROCESS, not only final answer
- Decagon, Harvey, Factory, Aemon all invest heavily here

---

## → Verso Implications

**Loop Architecture:**
- Verso's core loop MUST persist every event (model calls, tool params, tool results, approval decisions) as structured rows — conversation string is NOT state. Copy Dust's `agentLoopWorkflow` pattern, not a simple in-memory chain.
- Verso must support PAUSE + RESUME without state loss. This is a hard requirement for HITL and production agents. Temporal or a durable-queue equivalent (Postgres-backed) is the right substrate.
- `MAX_STEPS` should be configurable per agent config but MUST have a hard default (Dust: 64, Stagehand: 20). Never let a loop run unbounded in production.
- On last step, force final generation by setting available actions to empty — don't let the loop exit silently. This is the Dust pattern; Stagehand uses `ensureDone()` as backup.
- Termination should be explicit: `done` TOOL (Stagehand), no actions returned (Dust), max-step fail path (both). Pick one convention and enforce it — text-based "I'm done" detection is fragile.

**Tool System:**
- Tool configs in Verso MUST include: `timeoutMs`, `retryPolicy` (`no_retry | retry_on_interrupt`), `stake` level (`high/medium/low/never_ask`), and `outputLimits`. Schemas alone are insufficient — this is the lesson from every production system here.
- Non-idempotent tools MUST have `maximumAttempts: 1`. Auto-retrying state-changing actions (email sends, DB writes, PR opens) is a correctness bug, not a config choice.
- MCP tools should be first-class citizens but MUST NOT silently overwrite native tool names — Stagehand's current `{ ...tools, ...this.mcpTools }` pattern is a footgun. Verso should make conflicts explicit (warn or error).
- Build a meta-tool layer (Composio pattern): do not expose hundreds of raw tools to the LLM. Expose `search_tools`, `execute_tool`, `authorize_tool`, `list_files` as the 4-5 meta-tools, with routing behind them.
- Tool session = atomic unit: (user_id, toolkits, auth_configs, connected_accounts, files, custom_tools). Per-session scoping prevents cross-user contamination and enables MCP server per session.

**Context Management:**
- Verso MUST implement output offload: large tool results (>20KB text / >2MB image) become file references; model sees snippet + URI. Dust's 8,000-char snippet is the right default.
- Pruning must use PLACEHOLDER strings, not silent deletion. Dust's `<dust_system>...</dust_system>` approach preserves the agent's awareness that a result existed and was dropped — silent deletion causes hallucination.
- Token budget = `contextSize - generationTokensCount`. Compute this explicitly at context assembly time; don't let context overflow crash the loop.
- Streaming tokens should be batched before pubsub writes (Dust: 100ms default flush). Delimiter events (chain-of-thought boundaries) should bypass the buffer.

**Multi-Agent:**
- Sub-agents in Verso should receive self-contained task specs — no automatic prior context inheritance. Parent owns plan + synthesis + final answer.
- Concurrency limit is mandatory: Dust's 6 concurrent sub-agents is a reasonable default. Unbounded fan-out crushes providers and is unpredictable.
- Sub-agents should be defined by policy (what they can access), not just prompt. Dust's "sub-agents cannot use sandbox" rule is a policy, not a prompt instruction.

**Temperature / Generation Defaults:**
- Browser automation loops: `temperature = 0` (Firecrawl interact). Creativity hurts determinism for click/fill/navigate.
- Agent reasoning loops (plan, decide, synthesize): `temperature = 1` (Stagehand, SmartScrape planner). Let the model explore.
- Verso should expose temperature per tool-calling step vs text-generation step — these are different tasks requiring different defaults.
- Split planner vs executor models (Firecrawl SmartScrape: gemini-2.5-pro planner + gemini-2.0-flash executor). Verso's model gateway should support model-per-role routing natively.

**Durable Execution (Verso's opt-in escape hatch for graph cases):**
- The legitimate graph use case is: durable execution, HITL checkpoints, approval gates, and pause/resume. This is exactly what Temporal solves for Dust.
- Verso's "simple ReAct loop" should be the default; durable orchestration should be an opt-in adapter (Temporal worker or Postgres-backed durable queue).
- Cancellation must be first-class: Dust's graceful stop (finish current step, exit at boundary) vs hard cancel (`CancellationScope`) distinction is correct and necessary.

**Retrieval Integration:**
- Research loops need explicit state management, not just "call search in a loop": Firecrawl's `ResearchStateManager` (seenUrls, failedAttempts cap=3, findingsCap=50, depthProgress) is the right pattern.
- Retrieval in Verso should be a service boundary, not a library call. Parameters that matter: alpha (hybrid weight, Nia=0.7), top_k (Nia=20), rerank (separate from embed), accuracy mode (fast/slow).
- Citations and source provenance should be first-class in the retrieval response schema. Citation format enum (numbered/mla/apa/chicago) belongs at the API layer, not post-processing.

**Evals (Non-Negotiable for Production Verso):**
- Add evals before scaling tool count. The moat is eval infra (Decagon, Harvey, Factory all confirm this).
- Evaluation agents must inspect the EVENT TRACE (process), not only the final answer. This requires the event log to be readable by an eval agent.
- Procedures/policies should be versioned artifacts with diffs requiring human approval — NOT silent prompt mutation. This is the Decagon/Duet lesson.
- Test-driven agent development: define eval scenarios before deploying new tool integrations.

**Browser Adapter:**
- Three perception channels are non-negotiable for a serious browser adapter: DOM/a11y (stable selectors), screenshot/vision (visual grounding), CUA/coordinates (defeat-DOM fallback). Route per action, not per session.
- Deterministic action cache (Stagehand: sha256(instruction+url+variableKeys) → replay) is a legitimate performance primitive for repetitive browser workflows.
- Browser profiles should be an abstraction layer (AgentQL's BrowserProfileType including `tf-browser`) to support remote browser providers without coupling the agent loop to Playwright directly.

**Sandbox Adapter:**
- Verso's sandbox interface should expose: create(template, env, network, lifecycle), runProcess, readFile, writeFile, pause, resume(snapshot). These are the minimal operations code agents need.
- Network egress policy per sandbox (E2B's allowOut/denyOut/maskRequestHost) is a security primitive, not optional config.
- Pause/auto-resume lifecycle states enable long-running agent tasks to checkpoint between steps without paying cold-start cost.

**Framework-level "what to avoid":**
- Do NOT make a single model handle routing + task execution + safety + final answer (Sierra's lesson). Role separation is architectural, not a prompt-engineering choice.
- Do NOT silently mutate prompts when agents fail — update versioned procedures with human approval (Decagon/Duet).
- Do NOT let tool count grow unbounded without a meta-tool router — the LLM degrades past ~20 exposed tools.
- Do NOT use Docker for hostile code execution — Firecracker microVMs (E2B lesson).
- Do NOT treat "multi-agent" as a vague concept — it has a specific contract: isolated tasks, concurrency limit, no context leakage, parent synthesis.
