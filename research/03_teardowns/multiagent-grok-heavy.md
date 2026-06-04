# Cluster: Grok Heavy + Grok 4.20 — Multi-Agent Test-Time Compute

> Sources: `teardowns/GROK_HEAVY.md` (R1–R4, CE, 2026-05-26) + `teardowns/GROK_420.md`.
> All KNOWN/INFERRED/DESIGNED labels preserved from source teardowns.

---

## System A — Grok 4 Heavy / `grok-4.20-multi-agent`

### What it is

The first commercial product to make **parallel-instance debate ensemble** the central architectural primitive for test-time compute. Instead of one model thinking longer (OpenAI's reasoning-effort dial), xAI spawns N identical full-model instances on the same query, lets each independently reason + call tools, then merges via a leader-writes-final rule. This is the "symmetric N-agent ensemble" pattern — every agent is a peer, no specialist sub-agents, no orchestrator separate from the team.

As of May 2026 the product is a single model ID (`grok-4.20-multi-agent`) with one integer differentiating "Deep Research" from "Heavy": `agent_count ∈ {4, 16}` (proto-confirmed `AgentCount = Literal[4, 16]`). The perceived product bifurcation ("deep research" vs "Heavy") is entirely a marketing layer over the same runtime.

---

### Agent Loop Shape

```
User query + agent_count=4|16
   │
   ▼
N agents instantiated (all receive identical system prompt + tools)
   │
   ├── Agent #1 = Grok (LEADER — has render components)
   ├── Agent #2 = Harper
   ├── Agent #3 = Benjamin
   └── Agent #4 = Lucas   (for N=16, agents 5-16 names not yet leaked)

Each agent independently:
  while turns < max_turns and not final_answer and elapsed < 200s:
    reason()                   # one model generation pass
    tool_calls(parallel=True)  # multiple tool calls per turn allowed
    if peer_message_arrived:
        inject_as_function_turn()   # continuous merge, not final reduce

Leader's final turn: render_only (no tool calls, only <grok:render> components)
```

**Termination** (4-way conjunction, all must hold — KNOWN, confirmed from proto + leaked prompt):
1. `final_answer_emitted` — model stop (no tool calls in last generation)
2. `max_turns_hit` — defaults to server-side max (not exposed in API)
3. `200s wait-budget exhausted` — cumulative `wait` tool calls, hard wall-clock ceiling
4. `max_tokens / 1M context hit` — leader must synthesize when context fills

**Critical correction vs. naive assumption:** There is NO convergence/agreement metric anywhere — not in the proto, not in the leader prompt, not in the bundle. The teardown explicitly corrects R1's "75% convergence" hypothesis. Termination is purely time+count-bounded.

**Two levels of parallelism:**
- Within each agent: multiple tool calls per turn (parallel fan-out per turn)
- Across agents: all N agents run simultaneously

---

### Models

| Role | Model ID | Notes |
|---|---|---|
| All agents (leader + sub) | `grok-4.20-multi-agent` (alias → `grok-4.20-multi-agent-0309`) | Same base model for all N — no separate planner/reader/judge model |
| Single-agent / web search | `grok-4.3` | Used for non-multi-agent calls; same price ($1.25/$2.50 per 1M) |
| Coding | `grok-build-0.1` | 256K context; $1.00/$2.00 per 1M |

**Agent differentiation is role, not model.** The leader and sub-agents run the same model — they differ only in:
- Which system prompt they receive (leader gets `grok-expert.md`; sub-agents get `grok-4.2.md`)
- Whether they have render components (leader only)
- Whether they have `view_x_video` and `conversation_search` (leader only)

**No separate orchestrator/judge call.** R1 hypothesised a "separate judge." The real architecture: the leader IS the synthesizer. There is no extra model call for aggregation.

---

### Tool Registry (Complete)

**14-tool registry in multi-agent mode** (merged leader + sub-agent; asymmetries noted).

**Server-side tools (autonomous execution, model decides when to call):**

| Tool | Leader | Sub-agent | Key schema constants |
|---|---|---|---|
| `code_execution` | yes | yes | Python 3.12.3 REPL; internet **disabled except Polygon.io** (live financial data via preconfigured API key); no pip install; `code_execution_training_parity` name confirms inference sandbox = RL training sandbox |
| `browse_page` | yes | yes | `{url, instructions}` — instructions param routes to a **summarizer LLM**, not raw page text; JS/no-JS variants in consumer |
| `web_search` | yes | yes | `{query, num_results 1-30, default 10}`; server-side routes to Google and/or Bing; max_search_results default **15** |
| `web_search_with_snippets` | yes | yes | `{query}` — returns longer per-result snippets; useful for fact-checking without full browse |
| `x_keyword_search` | yes | yes | Full X advanced operator grammar (`from:`, `since:`, `filter:has_engagement`, `min_faves:N`, etc.); **limit default 3, max 10** (not 10 default — important correction) |
| `x_semantic_search` | yes | yes | `{query, limit default 3 max 10, from_date, to_date, exclude_usernames, usernames, min_score_threshold=0.18}` |
| `x_user_search` | yes | yes | `{query, count default 3}` |
| `x_thread_fetch` | yes | yes | `{post_id: string}` — recursive parent+replies fetch |
| `view_image` | yes | yes | `{image_url}` |
| `view_x_video` | **leader only** | NO | `{video_url}` — only leader can analyze X-hosted video |
| `search_images` | yes | yes | `{image_description, number_of_images 1-10}` |
| `collections_search` | yes | yes | RRF hybrid (`k`, `embedding_weight`, `text_weight`, named reranker); RAG over uploaded docs |
| `attachment_search` | yes | yes | `{limit}` only — server-injected |
| `mcp` | yes | yes | Remote MCP proxy `{server_url, server_label, allowed_tools, authorization, headers}` |

**Multi-agent runtime tools (not callable by API users — internal to the agent loop):**

| Tool | Schema | Notes |
|---|---|---|
| `chatroom_send` | `{message: str, to: enum{"Benjamin","Harper","Lucas","All"}}` | Leader addresses sub-agents by hardcoded name; sub-agents can also address leader ("Grok") |
| `wait` | `{timeout: 1-120, default 10}` | Synchronization barrier; 120s per call, 200s cumulative global cap |
| `conversation_search` | `{query, limit max 50 default 10}` | **Leader only** — cross-conversation semantic memory retrieval → returns `{conversationId, summary}` refs |

**Three architecturally separate X-search surfaces** (the teardown's central R3.0 finding — a replica that conflates them gets the wrong data model):

- **Surface A (Live-Search `x_source`):** Request-time RAG config on normal chat; model does NOT call it — the caller configures it; returns bare URL citations in `response.citations[]`
- **Surface B (Agentic `x_search`):** Server-side tool the *model* invokes mid-loop; the umbrella tool exposed to API callers
- **Surface C (4 fine-grained X functions):** The model's internal view behind surface B — `x_keyword_search`, `x_semantic_search`, `x_user_search`, `x_thread_fetch` as separate functions in the system prompt. **These are internal decompositions of the single `x_search` API tool — never separately exposed in the API.**

**Consumer-only X tools** (not in public API; server-injected behind X-OAuth `allowXPersonalization` flag):
`get_x_user_timeline`, `get_x_bookmarks`, `get_x_liked_posts`, `get_x_user_handle`, `get_x_user_profile_pic_description`, `get_top_us_news_from_x_trends`, `x_post_lookup`

**Coding agent tool family** (Grok Build / coding-agent mode — same `toolUsageCard` schema, different tool-set):
`bash{command, timeout}`, `readFile{filePath, offset, limit}`, `writeFile`, `editFile{filePath, oldString, newString, replaceAll}`, `browserTab{url, tabId, jsCode}`, `openPage{url, startLine, pattern}`

**Permission loop on destructive tools:** `bash`, `editFile`, and destructive MCP calls require `toolPermission` gate before execution; read-only tools auto-run. The gate carries `bashContext{fullCommand}` or `editContext{filePaths,kind}` so the user can allow-once, allow-pattern, or allow-domain.

---

### Context Assembly and Management

- Context window: **1M tokens** (grok-4.x family, as of May 2026; the 256K in R1/model card is the July-2025 launch figure, superseded)
- All N agents share the **same input context** (identical system prompt + user query + conversation history) — each agent's persona adapter modifies processing but attention over shared context happens once
- Debate-phase context: leader receives peer findings as **asynchronous function-turn injections** (not a final reduce step) — sub-agent findings arrive mid-generation and get spliced into the leader's running context the moment they arrive
- No shared scratchpad during independent execution phase
- Prefix caching (`RadixAttention`): the shared ~600-line `grok-expert.md` system prompt is cached and read (not recomputed) per agent — `DebugOutput.cache_read_input_bytes` confirms this; at N=16, the shared prompt prefix is a cache hit 15/16 times
- Multi-turn continuity: `previous_response_id` (server-side chaining) or `use_encrypted_content=True` (passes encrypted sub-agent state blob forward)

---

### Memory

**Three memory systems at different TTLs:**

| System | Mechanism | TTL | Backend |
|---|---|---|---|
| Session | `previous_response_id` chaining; server stores responses | 30 days | xAI server-side |
| Persistent ("memory v2") | `editMemory({memory})` tool write → ADD/EDIT/DELETE substring-diff + `expiresAtTimestamp`; `conversationSearch(query)` retrieval → `{conversationId, summary}` | Per-entry configurable TTL | Server-side black box (MongoDB likely from DNS TXT) |
| Collections (RAG) | Upload docs → HNSW vector index (`cosine/euclidean/inner_product`) → `collections_search` hybrid RRF retrieval | Persistent until deleted | `management-api.x.ai` |

**Memory write schema** (KNOWN, bundle `0fp4_ms8-g1zv.js:2062`):
```js
memoryV2UpdateResult: { oldMemorySubstring, newMemorySubstring, operationType, expiresAtTimestamp }
// operationType ∈ { MEMORY_V2_OPERATION_TYPE_ADD | _EDIT | _DELETE }
```
Edits are **surgical substring replacements**, not full rewrites. Memory partitioned by `companionId` (per-persona).

**Memory retrieval** streamed as `memoryReferences={references:[{conversationId, summary}]}` events — rendered as "Based on our previous chats" citation chips in the UI, each linking to the source conversation. Gated by `enableMemory` user setting (default true) and `DISABLE_CONVERSATION_SEARCH` feature flag.

---

### System Prompts (Verbatim Fragments)

**Leader prompt (`grok-expert.md`, 598 lines, commit `2251a8f`, asgeirtj capture 2026-05-11):**

```
You are Grok and you are collaborating with Harper, Benjamin, Lucas.
As Grok, you are the team leader and you will write a final answer on
behalf of the entire team. You have tools that allow you to communicate
with your team: your job is to collaborate with your team so that you
can submit the best possible answer. The other agents know your name,
know that you are the team leader, and are given the same prompt and
tools as you are, except only you have render components.
[...]
You use tools via function calls to help you solve questions.
You can use multiple tools in parallel by calling them together.
```

**Final-answer rule** (verbatim, `GROK-4.20.mkd:84`):
> "Interweave render components within your final response where appropriate… In the final response, you must never use a function call, and may only use render components."

**`chatroom_send` merge mechanism** (verbatim):
> "If another agent sends you a message while you are thinking, it will be directly inserted into your context as a function turn. If another agent sends you a message while you are making a function call, the message will be appended to the function response of the tool call that you make."

**`wait` synchronization** (verbatim):
> "Wait for a teammate's message or an async tool to return. There is a global timeout of 200.0s across all requests to this tool and a hard limit of 120.0s for each request to this tool."

**Citation rule** (verbatim, `grok-expert.md:614-622`):
> "Display an inline citation as part of your final response. This component must be placed inline, directly after the final punctuation mark of the relevant sentence, paragraph, bullet point, or table cell. Do not cite sources any other way; always use this component to render citation. You should only render citation from web search, browse page, X search, or document search results, not other sources. Finance API, sports API, and other structured data tools do NOT require citations."

**Jinja2 template variables** (from `grok4_system_turn_prompt_v8.j2`, `xai-org/grok-prompts`):
`is_mobile`, `is_subjective`, `chart_tool_enabled`, `custom_personality`, `enable_memory`, `has_memory_management`, `is_vlm`, `dynamic_prompt`, `max_turns`

---

### Error Handling and Retry

- **API retry:** UNAVAILABLE status only; max 5 attempts; 0.1s→1s exponential backoff (2x multiplier, max 1.0s)
- **gRPC timeout:** 1620s (27 min) default; SDK default 900s; recommended 3600s for reasoning models
- **Multi-agent agent timeout:** `wait` max 120s per call → proceed with available data (no crash)
- **Consensus failure (Grok 4.20 MARL framing):** If consensus_score < threshold after max debate rounds → Grok (Captain) makes final call unilaterally
- **Tool failure:** Individual tool failures don't crash session; agent proceeds with other available information
- **`wait`-budget exhaustion:** When 200s cumulative is hit, leader synthesizes from what it has
- **DeferredCompletion pattern:** `StartDeferredCompletion` → poll `GetDeferredCompletion` — allows async workflows without long-held HTTP connections (important for heavy runs)

---

### Exact Constants Table

| Constant | Value | Source |
|---|---|---|
| `agent_count` options | `4` or `16` (only two values) | CONFIRMED (SDK `Literal[4,16]`) |
| `reasoning_effort` options | `none/low/medium/high` (NO `xhigh`) | CONFIRMED (`types/chat.py:18`) |
| Default `reasoning_effort` | `medium` | CONFIRMED (`chat.py:140`) |
| `wait` max per call | 120s | CONFIRMED (leaked prompt) |
| `wait` global max | 200s | CONFIRMED (leaked prompt) |
| `max_search_results` default | 15 | CONFIRMED (`search.py:37`) |
| `x_keyword_search` limit default | 3 (max 10) | CONFIRMED (`GROK-4.20.mkd:33`) |
| `x_semantic_search` min_score | 0.18 | CONFIRMED (leaked prompt) |
| `x_user_search` count default | 3 | CONFIRMED (`GROK-4.20.mkd:37`) |
| Context window (grok-4.x) | 1,000,000 tokens | CONFIRMED (docs probe, May 2026) |
| Code sandbox internet | Disabled **except Polygon.io** | CONFIRMED (`GROK-4.20.mkd:25`) |
| Knowledge cutoff | November 2024 | CONFIRMED (docs) |
| Cached prefix price | $0.20/M tokens (10× cheaper) | CONFIRMED (docs) |
| `cost_in_usd_ticks` unit | 1 tick = 1e-10 USD | CONFIRMED (`xai_sdk/cost.py:8`) |
| Debate overhead (MARL framing) | ≤180 tokens total | INFERRED (multiple sources) |
| Debate rounds (MARL framing) | 2-4 | INFERRED |
| Stored response TTL | 30 days | CONFIRMED (docs) |
| gRPC max message | 20 MiB | CONFIRMED (SDK) |
| gRPC keepalive | 30s ping | CONFIRMED (SDK) |
| Max tools per request | 200 | CONFIRMED (docs) |
| Max functions per request | 128 | CONFIRMED (proto) |
| Retry max attempts | 5 | CONFIRMED (SDK) |
| Retry initial backoff | 0.1s | CONFIRMED (SDK) |
| Retry backoff multiplier | 2× | CONFIRMED (SDK) |
| Retry max backoff | 1.0s | CONFIRMED (SDK) |

---

### Multi-Agent Coordination Protocol

The inter-agent communication is a **continuous injection model**, not a collect-and-reduce model. The key distinction:

```
# NOT a final-reduce pattern:
results = await gather(agent1, agent2, agent3)
leader.synthesize(results)                    # ← wrong model

# ACTUAL: continuous injection
# Sub-agent sends message mid-run:
chatroom_send(to="Grok", message="Harper: Found contradicting claim in source X")
# → Injected into leader's context as function turn immediately
# → Leader can update its reasoning in-flight
# No synchronization barrier — findings flow in continuously
```

The `wait(timeout=10)` call is the only explicit barrier — the leader uses it to pause and check for peer responses before finalizing a section. The 200s global cap is the sum of all `wait` calls, not an overall run timeout.

**Only the leader renders.** Sub-agents can call all tools (search, code, browse, MCP) but cannot emit `render_inline_citation`, `render_searched_image`, `render_generated_image`, `render_edited_image`, `render_file`. This is enforced by the system prompt (sub-agents do not have these functions listed in their tool registry), not by an access-control layer.

**Named roster (N=4, KNOWN):**
- Grok (leader, `grok-expert.md`) — `chatroom_send.to` is enum-restricted to `{"Benjamin","Harper","Lucas","All"}`
- Harper, Benjamin, Lucas (sub-agents, `grok-4.2.md`) — share same prompt, same tools minus video/memory-search

**Named roster (N=16, INFERRED):** The teardown confirms `agent_count=16` exists but the names of agents 5-16 are not in any leaked prompt. Likely 1 leader + 15 named sub-agents (not 4 teams of 4).

---

### Streaming Protocol

**gRPC server-streaming** (`GetChatCompletionChunk`); OpenAI-compat REST layer wraps each chunk as SSE `data:` line.

**6-channel `Delta` struct** (the key architectural wire fact — `chat_pb2.pyi:283`):
```protobuf
message Delta {
  string content            = 1;  // visible answer text delta
  string reasoning_content  = 2;  // thinking-trace delta — streamed SEPARATELY from content
  MessageRole role          = 3;  // ROLE_ASSISTANT vs ROLE_TOOL distinguishes answer vs tool output
  repeated ToolCall tool_calls = 4;
  string encrypted_content  = 5;  // opaque encrypted reasoning blob (for multi-turn hydration)
  repeated InlineCitation citations = 6;  // opt-in, when include=[inline_citations]
}
```

**Thinking trace** is the `reasoning_content` buffer — streamed as a separate channel, not interleaved with answer text. Consumer segments it into `thinkingTrace: string[]` array with step types `"summary" | "header" | "action"`. The full raw CoT is in `encrypted_content` (field 5, never displayed; re-sent on next turn for multi-turn continuity).

**Tool-call render protocol:** `ToolCall` arrives with `status=IN_PROGRESS` (spinner) → same `id` arrives with `status=COMPLETED` (checkmark) or `FAILED(error_message)`. The `IN_PROGRESS→COMPLETED/FAILED` transition stream is what drives the consumer activity feed.

**`verbose_streaming`** include flag: enables intermediate sub-agent activity — extra `ROLE_TOOL` outputs appear in the chunk's `outputs[]` with their own `index`. Default (without the flag): only leader tool calls + leader final response visible.

**Multi-agent progress categories** (KNOWN, `GrokApiProgressReportCategory` enum, bundle):
```
PROGRESS_REPORT_CATEGORY_ATTACHMENTS_PREPROCESSING   // pre-generation ingestion
PROGRESS_REPORT_CATEGORY_WEBPAGE_ATTACHMENTS_PREPROCESSING
TOOL_PROCESSING                                       // mid-run tool calls
HEAVY_ROLLOUT                                         // multi-agent fan-out phase — distinct category
```
The term `HEAVY_ROLLOUT` is xAI's internal name for the parallel-agent fan-out (matching RL "rollout" — each agent is a sampled trajectory).

**DeferredCompletion for heavy runs:**
- `StartDeferredCompletion` → returns request ID immediately
- `GetDeferredCompletion` → polls for result
- Required for N=16 runs where HTTP connection would time out before completion

---

### MCP Integration

First-party connector toolsets (consumer, implemented as MCP servers):
- `slack-ro` (Slack read-only), `gmail-ro`, `gcal-ro` (Google Calendar), `notion-ro`, `x-ro`, `browse-ro`
- Each connector = `{connectorId, connectorName, serverUrl}` — server-side MCP client holds OAuth token
- Per-call card carries the 4 MCP `ToolAnnotations` hint fields: `{readOnlyHint, destructiveHint, idempotentHint, openWorldHint}`
- `readOnlyHint:true` → auto-run; `destructiveHint:true` → routes through permission gate
- `authNotification.mcpConnectors[]` streamed when user must authorize (OAuth trigger)
- Tiered by feature flags: `ENABLE_CONSUMER_MCP_CONNECTORS` / `ENABLE_BUSINESS_MCP_CONNECTORS` / `ENABLE_ORG_SCOPE_CONNECTORS`

---

## System B — Grok 4.20 Model-Level Architecture (from `GROK_420.md`)

This is the separate teardown's framing of the same underlying system. Key additional facts not covered above:

### Architecture Framing (INFERRED — convergent estimates)

The `GROK_420.md` teardown frames the multi-agent system differently: it argues the 4 agents are **lightweight persona adapters (~0.3% of parameters, LoRA-style) on a shared ~3T MoE backbone**, sharing the same KV cache — meaning N=4 costs only **1.5-2.5× single-pass**, not 4×. The debate adds ≤180 tokens of overhead via a cross-attention block added exclusively in 4.20.

This framing (INFERRED, never confirmed by xAI) explains the cost economics in a way the API-only framing (`GROK_HEAVY.md`) does not. The `GROK_HEAVY.md` teardown treats each agent as a full separate API call; `GROK_420.md` argues they are subsumed on one model pass. **Both framings are consistent with the wire protocol** — the API surface does not reveal whether agents are separate inference calls or persona adapters on one inference pass.

**The implication for replicas:** A prompt-engineering replica (separate API calls per agent) will cost more than xAI's native implementation. The real system likely achieves sub-linear cost via architecture, not just prompt caching.

### MARL Training (KNOWN-reported, from model card)

- RL = ~50% of Grok 4's total training budget (vs RL as a thin post-training layer in prior gens)
- **Trained on tool-use trajectories via RL** — the `code_execution_training_parity` tool name is the confirming detail: inference sandbox kept identical to RL training sandbox to prevent distribution shift
- Reward criteria: final answer quality + debate efficiency (jointly optimized); penalties for premature consensus, factual drift, redundant computation
- **RL-trained tool-use = the deepest quality gap for replicas.** A prompt-only replica cannot match Grok's multi-step research quality because the model has RL-trained beliefs about *when* to search, *what* queries to issue, *how* to chain browses. Closing this requires fine-tuning on tool-use traces (DESIGNED gap, not closeable by prompting alone).

### Per-Agent Specialization (CONFIRMED from leaked prompts)

| Agent | Role per leaked prompt | Key specialization |
|---|---|---|
| Grok (Captain) | Coordinator, task decomposition, final synthesis | Global state, conflict resolution |
| Harper | Research | Real-time X firehose + web search, fact-checking |
| Benjamin | Logic | Mathematical reasoning, formal proofs, code verification |
| Lucas | Creative/Contrarian | Divergent thinking, bias detection, alternative angles |

The personas are NOT different models — same base model, different system-prompt-level role assignments. In a prompt-engineering replica, these are literal different system prompt instructions.

### Inference Infrastructure

- **SGLang** (open-source, co-founded by ex-xAI researchers): radix tree KV cache reuse (`RadixAttention`) — up to 6× throughput for shared-prefix workloads. The N-agent shared system prompt is the canonical shared-prefix that RadixAttention was designed for.
- **API server:** Rust + axum (CONFIRMED via validation error format `Failed to deserialize the JSON body into the target type` = serde through axum)
- **Error envelope:** `[WKE=category:subcode]` internal error framework
- **`DeferredCompletion`:** `StartDeferredCompletion` / `GetDeferredCompletion` pattern for long-running runs (key for N=16 async workflows)

---

## Key Architectural Reveals (Cross-System Synthesis)

1. **The "parallel debate ensemble" is architecturally distinguished from "hierarchical orchestrator+workers"** (Anthropic's pattern). Grok's bet: symmetric peers with identical tools, no specialization, debate via continuous injection. Anthropic's bet: specialized workers delegated slices, orchestrator aggregates. Different cost/quality tradeoffs. Grok's costs more per query but avoids orchestrator-bottleneck risks.

2. **"Only the leader renders" is the cleanest production answer to "who emits the final UI" in a multi-agent system.** Without this rule, competing sub-agents would emit inconsistent citations, duplicate UI components, and conflicting rendered outputs. Enforced at the system-prompt level (sub-agents literally do not have render components in their tool registry).

3. **Turn-bounded termination, not convergence-bounded.** The obvious intuition ("loop until agents agree") is wrong. Real termination: `turns ∧ time ∧ tokens` — purely resource-bound, no quality threshold. This is architecturally simpler and avoids infinite loops on hard problems where agents never converge.

4. **Continuous injection merge, not final reduce.** Sub-agent findings arrive as `function_turn` injections into the leader's running context — not collected at the end and reduced. The leader's synthesis incorporates findings as they arrive. This eliminates the N-agent-all-done synchronization barrier as a latency bottleneck.

5. **The 4/16 hard cap is a deliberate product simplification.** xAI could expose continuous N but chose exactly two values. This makes: (a) pricing predictable ($0.19 vs $0.94 per query), (b) product positioning clean (Deep Research vs Heavy), (c) the cost math auditable via `cost_in_usd_ticks`. The consumer sees two buttons; internally it's one integer.

6. **Agent tool asymmetry by role, not model.** The leader has 2 extra tools (`view_x_video`, `conversation_search`) that sub-agents don't. This is the minimum asymmetry needed to make the leader the final author — only the leader can view video (research gate) and only the leader has memory access (continuity gate).

7. **The thinking trace is a first-class streaming channel** (`Delta.reasoning_content` = field 2, separate from `content` = field 1). Not interleaved text. The encrypted full CoT (`Delta.encrypted_content` = field 5) is the multi-turn continuity mechanism — never displayed but re-sent on follow-up turns. This is the industry-standard answer to CoT exposure pressure: visible summary + encrypted full trace.

8. **RL-trained tool use is the quality moat.** The inference sandbox is kept identical to the RL training sandbox (`code_execution_training_parity` tool name is the evidence). Grok's multi-step research quality comes from RL-trained beliefs about search/browse chains, not just prompt engineering. Any prompt-only replica has a calibrated quality gap on multi-step research tasks.

9. **The DeferredCompletion pattern solves long-running agent HTTP timeouts.** For N=16 runs (60-180s wall-clock), keeping an HTTP connection open for the full duration is impractical. `StartDeferredCompletion` → poll `GetDeferredCompletion` is the standard pattern. Verso needs this for any run expected to exceed ~30s.

---

## → Verso Implications

### Copy

**1. Turn-bounded loop termination** (`max_turns ∧ time_budget ∧ token_budget`). Verso's agent loop should terminate on the conjunction of these three resource bounds — no convergence metric, no agreement threshold. Simpler, provably terminates, easier to explain to users. The pseudo-code:
```python
while turns < max_turns and not final_answer and elapsed < time_budget:
    step()
```

**2. Leader-only rendering / output gating.** In any Verso multi-agent workflow, designate one agent as the sole output emitter. Sub-agents communicate findings to the leader; only the leader writes the final response. This prevents duplicate citations, conflicting UI, and inconsistent answers. Enforce at the tool-registry level: sub-agents literally do not have "emit response" in their tool set.

**3. Continuous injection merge over final reduce.** When designing multi-agent coordination in Verso, prefer the `chatroom_send`/`wait` continuous-injection pattern over collect-all-then-synthesize. Sub-agent findings arrive as function turns in the leader's context as they complete — no synchronization barrier, leader can update reasoning in-flight.

**4. Explicit `wait` synchronization barrier as a first-class primitive.** `wait(timeout=N)` is how the leader pauses to receive peer findings. Verso should offer this as a first-class primitive in its multi-agent API. It is simpler than streaming event buses and maps naturally to async/await in the host language.

**5. MCP tool annotation hints (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) as the permission routing gate.** Verso should read these four MCP hints and auto-route: `readOnlyHint:true` → auto-run; `destructiveHint:true` → require explicit user approval. This is the standard MCP `ToolAnnotations` spec — implementing it costs nothing and enables safe delegation.

**6. Symmetric `agent_count` tiers instead of continuous N.** Offer 2-3 fixed presets (e.g., 1 / 4 / 16) with named pricing rather than an open N dial. Simpler cost model, clearer user expectations, easier to capacity-plan.

**7. DeferredCompletion / async polling pattern for long-running runs.** Any Verso run expected to exceed ~30s should support `start_run() → poll_result()` to avoid HTTP connection timeouts. Essential for heavy multi-agent workflows.

**8. Thinking trace as a first-class output channel separate from content.** Verso's streaming protocol should emit `reasoning_content` and `content` as separate channels in the Delta, not interleaved. Clients that want to show thinking can render the reasoning channel; clients that don't simply ignore it.

**9. `cost_in_usd_ticks` — per-request cost in the response.** Return the actual cost of each request to the caller directly. For multi-agent runs where cost scales with N, this is essential for budget observability. Verso should compute and return actual run cost in every response envelope.

### Avoid

**1. Convergence-based termination.** Do not build a "loop until agents agree" exit condition. The obvious design choice is wrong — hard problems may never converge, cost grows unboundedly, and the condition is hard to tune. Pure resource-bounded termination is simpler and predictable.

**2. Separate orchestrator + judge as additional model calls.** Grok's R1 hypothesis (separate orchestrator that selects N, separate judge that aggregates) was wrong. The real architecture is one of the N agents acting as leader. Adding a dedicated orchestrator/judge model call adds latency and cost without a clear quality benefit. Verso should use the leader-in-team pattern.

**3. Fixed specialized agent roles without evidence they help.** Grok assigns roles (Research/Logic/Contrarian/Coordinator) to its agents. Whether this specialization actually helps vs. N copies of the same prompt is unclear — xAI has not published ablations. Verso should not hardcode domain specializations; instead offer role assignment as user config, defaulting to identical peers.

**4. Exposing raw sub-agent output by default.** The default should be leader-only output (clean response). Sub-agent state, intermediate reasoning, and tool-call traces should be opt-in (equivalent to `verbose_streaming` or `use_encrypted_content`). Raw intermediate output overwhelms users on simple tasks.

**5. Making the agent count a continuous parameter.** Continuous N complicates pricing, capacity planning, and user communication. Two or three fixed tiers is the right default; expose `agent_count` as a power-user escape hatch if needed.

### Verso Could Improve By

**1. Exposing convergence monitoring as an observable metric without making it a termination condition.** xAI explicitly has no convergence metric in the termination logic — but tracking agreement across agents would be valuable telemetry for evals. Verso could stream a `consensus_score` field in the Delta without using it to terminate the loop.

**2. Making the agent roster user-configurable at the system-prompt level.** Grok hardcodes Harper/Benjamin/Lucas. Verso could let the user specify N agent roles via config at framework level, defaulting to N identical peers. This is a pure framework design win with no training cost.

**3. Budget-aware synthesis trigger.** Grok's 200s wall-clock ceiling is a hard wall. Verso could add a softer trigger: when `elapsed > budget * 0.8`, have the leader begin synthesizing from what it has (warning the user that synthesis may be incomplete). Smoother UX than a hard timeout.

**4. Explicit tool-call parallelism control.** Grok allows multiple tool calls per turn natively. Verso's framework should expose a `parallel_tools: bool` flag and make the two levels explicit in the API: (a) within-turn parallelism (fan-out multiple tools in one generation pass) and (b) cross-agent parallelism (N agents run simultaneously). Users can then reason about cost and latency separately.

**5. Cost telemetry as a first-class framework concern.** `cost_in_usd_ticks` returned per chunk is Grok's mechanism. Verso's core loop should accumulate token + tool-call costs and emit a live `cost_so_far` event to the caller throughout the run, not just in the final response. This is especially important for multi-agent runs where cost scales non-linearly.

**6. Sandbox parity as a documented property.** xAI's `code_execution_training_parity` makes the RL-training vs. inference sandbox identity a named, documented property. Verso should document which sandbox a tool runs in and whether it matches any fine-tuning environment. This is table-stakes hygiene for RL-trained agents.

---

*Note path: `/Users/seventyleven/Desktop/Verso/research/03_teardowns/multiagent-grok-heavy.md`*
*Sources: `teardowns/GROK_HEAVY.md` (Rounds 1–4 + CE, 2026-05-26 state) + `teardowns/GROK_420.md`*
