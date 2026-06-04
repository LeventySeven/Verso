# Cluster: fw-composio-browseruse
## Composio (Tool Platform) + Browser Use (Browser Agent)
*Extracted for Verso framework design — June 2026*

---

## System 1: Composio

### What Composio is

Composio is a hosted tool-execution platform: 10,000+ API tools (GitHub, Slack, Gmail, Linear, etc.) exposed through a unified interface, with OAuth vault, per-user session scoping, and an MCP server. The v0.7 SDK had ~200 tools visible to the LLM as individual schemas; the v0.12 architecture collapsed that into **6 meta-tools** the LLM ever sees, with all tool routing server-side. This is the key architectural bet: reduce LLM prompt token cost from "1000+ tool schemas" to ~6, saving 50K+ tokens per request.

---

### Agent Loop Shape

Composio is NOT itself an agent framework — it is the tool layer beneath an agent. The loop lives in the client (OpenAI, CrewAI, LangChain) and Composio's meta-tools intercept individual tool calls. Key meta-tool: `COMPOSIO_MULTI_EXECUTE_TOOL` — the LLM emits one call with an array of N concrete tool invocations; the SDK partitions into local (in-process custom tools) and remote (server-side), runs remote in a single batched backend call, runs local via `ThreadPoolExecutor(max_workers=5)`, and merges in original order.

```python
# The entire LLM-facing surface (v0.12, from tool_router_session.py):
COMPOSIO_SEARCH_TOOLS           # BM25 + LLM re-rank tool search
COMPOSIO_MANAGE_CONNECTIONS     # OAuth connection flow
COMPOSIO_MULTI_EXECUTE_TOOL     # batched parallel execution (max_workers=5)
COMPOSIO_REMOTE_WORKBENCH       # code sandbox
COMPOSIO_REMOTE_BASH_TOOL       # remote shell
COMPOSIO_FETCH_TOOL             # raw HTTP proxy
# v3.1 additions:
COMPOSIO_UPSERT_RECIPE          # store multi-step plan in cache
COMPOSIO_GET_RECIPE             # replay cached plan (BM25 plan cache)
COMPOSIO_GET_TOOL_SCHEMAS       # lazy-load full tool schemas
```

**Termination/iteration:** No agent loop — tool calls are one-shot via session execute. Session state (toolkits, permissions, sandbox files) persists across multiple LLM turns within a session.

---

### Models

| Role | Model | Notes |
|---|---|---|
| Tool search/planning | gpt-4o (default, client-supplied hint) | `model` hint in SEARCH request; server can substitute. BM25 first, then LLM re-rank |
| Parameter inference (`/tools/execute/{slug}/input`) | Server-side unknown; likely gpt-4o-mini | Called with tool's JSON-Schema + NL text → fills args |
| Planner/Rube assistive prompt | Server-side LLM, not disclosed | Generates `assistive_prompt` at session creation |
| Workbench code execution | Sandbox (E2B or Fly.io, black box) | Python execution in remote container |

**Model routing signal:** the `provider=` field (e.g. `"openai"`, `"crewai"`) is sent to the API on every request so the server can optionally tailor responses per framework. Actual schema shaping is 100% client-side (see Provider Transform below).

---

### Full Tool Registry

The LLM sees only the 6 (or 9) meta-tools above. Behind them, the tool catalog is:

- ~10,000+ tools across 250+ toolkits stored as data (Postgres): `{slug, description, http_method, http_path, parameters: JSON-Schema, tags, version}`
- Tool tags: `readOnlyHint`, `idempotentHint`, `destructiveHint` — matching MCP spec, usable as allow/deny filters in session config
- Session filtering: per-toolkit `{enable: [...], disable: [...], tags: [...]}` allowlists/denylists
- `preload="all"` exposes every tool directly (capped at 1000; emits `PRELOAD_TOOLS_HIGH_CONTEXT_USAGE` warning)
- Tag-based filter at session level: `tags=["readOnlyHint"]` = read-only sandbox

**Custom tool registration:** in-process via `composio.experimental` decorators; auto-routed to the local-execution path without hitting the API.

---

### Context Assembly / Token Budget

Key insight: the meta-tool architecture is a context budget optimization.

- **v0.7 approach:** emit all tool schemas → LLM context. 200+ schemas = 50K+ tokens burned per request.
- **v0.12 approach:** emit 6 meta-tool schemas. LLM uses `COMPOSIO_SEARCH_TOOLS` to discover the tools it needs (BM25 + LLM re-rank), then calls `COMPOSIO_MULTI_EXECUTE_TOOL`. Full schemas only fetched on demand via `COMPOSIO_GET_TOOL_SCHEMAS` (lazy load with `hasFullSchema=false` + `schemaRef` in search results).
- **Plan cache:** search response returns `plan_id + recommended_plan_steps + reference_workbench_snippets` on cache hit → LLM skips the SEARCH call and replays steps directly. Cache key = normalized `use_case` string (exact mechanism server-side black box).
- **`known_fields` pre-seeding:** search request accepts `known_fields: "channel_name:eng, user_email:john@example.com"` to pre-fill slot values before the planner runs. Reduces parameter inference calls.

---

### Memory

- **Session-bound:** `ToolRouter.session.create(user_id=..., toolkits=[...])` → server returns a session with a per-session sandbox (`/mnt/files`) and an `assistive_prompt`. Session config is mutable via PATCH.
- **Per-app memory (cross-session):** search response returns `memory: Dict[app_slug → string[]]` on cache miss — discovered entity IDs / relationships the planner learned from prior runs. Stored server-side per `(user_id, app)`.
- **Recipe/plan cache (long-term):** `COMPOSIO_UPSERT_RECIPE` stores `{plan_steps, tool_slugs, pitfalls, reference_code}`; subsequent searches with similar `use_case` hit the plan cache and skip LLM planning. This is the "skills" product layer.
- **Trigger state:** Pusher WebSocket subscription (`new-trigger`, `chunked-trigger_to_client` events). Client-side chunk reassembly: `{id, index, chunk, final}` → sorted join. Filtered by 6-tuple: `{trigger_slug, trigger_id, toolkit, user_id, auth_config_id, connected_account_id}`.
- **Connected account polling:** 60s wall clock, 1s interval, terminal states = `{FAILED, EXPIRED, REVOKED}`.

---

### System Prompt Fragments

**Assistive prompt (server-generated, black box):** composed dynamically per session from:
1. Meta-tools present (sections toggled based on workbench/permissions config)
2. `user_timezone` (IANA tz injected at session create)
3. `time_info.message` in search responses (date/timezone reasoning instructions)

The assistive prompt teaches the LLM the `SEARCH → MULTI_EXECUTE → WORKBENCH` workflow. Text is NOT in any public mega-repo (x1xhlol, jujumilk3 both return zero hits for "composio" or "rube").

**Permissions layer (elicitation):**
```python
experimental.permissions = {
  "default": "allow_all" | "ask_every_call" | "ask_once_per_session",
  "overrides": {
    "GITHUB_DELETE_REPO:ca_x": "always_deny",
    "*:ca_x": "ask_always",           # account-wide wildcard
  }
}
```
Exact-tool overrides beat account-wide overrides, which beat `default`. This is the MCP elicitation spec realized as a session-level guardrail.

---

### Error Handling / Retry

**Proxy execute retry policy (KNOWN, from Stainless base client):**
```python
DEFAULT_TIMEOUT         = httpx.Timeout(timeout=60, connect=5.0)
DEFAULT_MAX_RETRIES     = 2                         # not 3
INITIAL_RETRY_DELAY     = 0.5s
MAX_RETRY_DELAY         = 8.0s                      # cap
```
Retry predicate:
- `x-should-retry: true/false` header overrides everything (server-controlled per-response retry toggle)
- HTTP 408, 409 (lock timeout — not a hard conflict), 429, 5xx → retry
- Everything else → no retry

Note: 409 is retried (treated as lock contention). The server can force a retry via non-standard `x-should-retry` header on any response.

**Execution envelope:** `{data, error, successful}` — always; a tool failure returns this envelope rather than raising, so the agent loop receives a result it can inspect.

---

### Exact Constants

| Constant | Value | Source |
|---|---|---|
| `MAX_PARALLEL_WORKERS` | 5 | `tool_router_session.py:49` |
| `DEFAULT_TIMEOUT` | 60s total, 5s connect | `_constants.py` |
| `DEFAULT_MAX_RETRIES` | 2 | `_constants.py` |
| `INITIAL_RETRY_DELAY` | 0.5s | `_constants.py` |
| `MAX_RETRY_DELAY` | 8.0s | `_constants.py` |
| Connected-account poll interval | 1s | `connected_accounts.py:92` |
| `DEFAULT_WAIT_TIMEOUT` (OAuth poll) | 60.0s | `connected_accounts.py:46` |
| Trigger subscribe default timeout | 15.0s | `triggers.py:872` |
| File upload default dir | `~/.composio/temp` | `sdk.py:117` |
| `preload="all"` cap | 1000 tools | `session_create_params.py` |
| Backoff Retry-After honor cap | ≤60s | `_base_client.py:779` |
| Tool search ranking | BM25 + LLM (2-bucket primary/related) | `session_search_response.py` |

---

### Multi-Agent Coordination

**Framework adapter tiers:**
- `NonAgenticProvider` (OpenAI, Anthropic, Gemini): Composio runs the tool execution. `wrap_tool` is a 5-line key rename (`slug→name`, `input_parameters→parameters key`). Composio calls the upstream API after tool_use/function_call response.
- `AgenticProvider` (CrewAI, LangChain, LangGraph, LlamaIndex, AutoGen): the framework runs its own agent loop. `wrap_tool` synthesizes a live executable object in the framework's class system (a `BaseTool` for CrewAI, a `StructuredTool` for LangChain with a manufactured function signature). The `execute_tool(slug, args)` callback is injected as a closure. `pydantic.ValidationError` is normalized to `{successful:False, error, data:None}` so a bad-args call returns a tool-result, never crashing the framework's loop.
- Shared schema compiler: `json_schema_to_model` / `get_signature_format_from_schema_params` in `composio/utils/shared.py` — the JSON-Schema → native-schema compiler every agentic provider uses.

**Modifier engine (3-point, KNOWN):**
```python
@schema_modifier(tools=["GITHUB_CREATE_ISSUE"])  # rewrite schema before LLM sees it
@before_execute(toolkits=["github"])              # rewrite args before execution
@after_execute                                    # rewrite result after execution
```
Matching rule: `(modifier_type, tools=[], toolkits=[])` where empty filter = apply to ALL. Applied at: (1) schema fetch, (2) argument serialization, (3) result return. This is the extensibility layer that lets users inject default `repo` args, strip noisy fields, hide params from the LLM — without forking Composio.

---

### Streaming Protocol

- Tool execution: synchronous JSON over HTTPS (`{data, error, successful}`)
- Sandbox (Workbench): SSE over `POST /tool_router/session/{id}/execute_meta` — event types: `browser_created`, `instance_created`, `instance_ready`, `log`, `result`, `error`, `stream_complete`
- Triggers: Pusher WebSocket (`pusher:connection_established`, `new-trigger`, `chunked-trigger_to_client`)
- MCP transport: Streamable HTTP (per MCP spec) — `tools/list` and `tools/call`

---

### Auth/OAuth Architecture

Three-entity model (KNOWN from SDK source):
- `AuthConfig` — OAuth app/credentials definition. Per-toolkit, scoped to `is_enabled_for_tool_router`, allows per-config `tool_access_config` (allow/deny list)
- `ConnectedAccount` — a user's live link (nanoid + status). Polled to ACTIVE, terminal = `{FAILED, EXPIRED, REVOKED}`
- `user_id` — the end-user identity, keyed to connected accounts

11 auth schemes: `OAUTH1`, `OAUTH2`, `COMPOSIO_LINK`, `API_KEY`, `BASIC`, `BEARER_TOKEN`, `NO_AUTH`, `SNOWFLAKE`, `GOOGLE_SERVICE_ACCOUNT`, `CALENDLY_API_KEY`, `BILL_COM`. Token-import → `ACTIVE` immediately; redirect OAuth → `INITIALIZING` until user completes flow.

---

### Verso Lesson: Composio

**COPY:**
1. **Meta-tool architecture over schema flooding.** Exposing 6 meta-tools (search, multi-execute, workbench, fetch, manage-connections, recipe) instead of N tool schemas is the right abstraction for a Verso tool layer. Verso should ship a `VersoToolSearch` and `VersoMultiExecute` built-in, letting agents discover tools dynamically rather than front-loading the context with every schema.
2. **Batched parallel tool execution in a single LLM emission.** `COMPOSIO_MULTI_EXECUTE_TOOL` with `ThreadPoolExecutor(max_workers=5)` + single backend call for all remote tools. Verso's tool dispatch should natively batch a list of `{tool_slug, arguments}` in one call and fan out with bounded parallelism.
3. **Tag-based tool filtering.** `readOnlyHint`, `idempotentHint`, `destructiveHint` at the tool level — built-in, matching MCP spec. Verso should ship these tags and let agents declare "read-only mode" at session init.
4. **Modifier engine (3-point: schema/before/after).** Scoped by `(tool, toolkit)` with empty-filter = all. This is the cleanest middleware pattern seen in any tool system. Verso's tool invocation pipeline should have these three hooks.
5. **Execution envelope `{data, error, successful}` — always.** A tool failure is data, not an exception. The agent loop sees results and adapts. Verso should standardize this envelope across all tool types.
6. **Server-controlled retry via `x-should-retry` header.** Lets the backend decide retry behavior per-response without changing the client. Verso remote tool calls should honor this pattern.
7. **Per-session permission model.** `default: allow_all|ask_every_call|ask_once_per_session` + per-tool overrides. Verso should ship this as first-class: dangerous tools require explicit session-level approval.
8. **Plan cache (recipe layer).** BM25 `use_case` → plan hit → replay stored steps without re-planning. Verso could ship a `PlanCache` abstraction: on a cache miss the agent plans and `upsert_plan(use_case, steps)`; on a hit the plan is replayed cheaply.

**AVOID:**
1. **Hiding the schema compiler complexity.** Composio's `json_schema_to_model` is shared critical infrastructure, but it lives in `utils/shared.py` — undiscoverable. Verso's schema-to-framework adapters should be a first-class public API.
2. **Provider-name-to-API coupling.** Sending `provider=` on every API request means the server can silently alter behavior per framework. Verso should keep tool execution behavior identical regardless of which LLM is upstream — no provider leakage into the tool layer.
3. **Session-scoped assistive prompts (black-box server generation).** Composio generates the system prompt server-side per session. This makes the agent's behavior opaque to the developer. Verso should generate system prompts client-side with explicit, inspectable templates.

---

## System 2: Browser Use

### What Browser Use is

Browser-Use is a step-loop browser-automation agent framework. The novel primitive: **indexed-DOM-as-action-target** — every interactive element gets a stable integer index, the LLM picks actions by index (`click(3)`, `input(5, "hello")`). Eliminates CSS-selector hallucination (the dominant failure mode of LLM-driven browser agents). The LLM cannot make up a non-existent index.

---

### Agent Loop Shape

Single-agent, 4-phase step loop (`agent/service.py:1023`):

```python
# Phase 0: captcha wait
captcha_wait = await self.browser_session.wait_if_captcha_solving()

# Phase 1: Prepare context (DOM + screenshot + history)
browser_state_summary = await self._prepare_context(step_info)

# Phase 2: LLM call + action execution
await self._get_next_action(browser_state_summary)
await self._execute_actions()

# Phase 3: Post-processing (downloads, loop detection, failure tracking)
await self._post_process()
```

**Termination conditions:**
- `done` action called (mandatory pre-done verification: 6-step checklist in system prompt)
- `max_steps` reached → force-done injected into last step message
- Failure budget exhausted: `max_failures=5` consecutive errors → one final recovery attempt, then terminal

**Iteration caps (KNOWN from `views.py`):**
- `max_steps`: configurable (default used: 30-100 per task)
- `max_actions_per_step = 5` — up to 5 actions emitted per LLM turn
- `max_failures = 5` — consecutive, not total; resets on success
- Budget warning at 75% of max_steps (injected as message)

**LLM output format (required per step):**
```json
{
  "thinking": "...",
  "evaluation_previous_goal": "...",
  "memory": "...",
  "next_goal": "...",
  "current_plan_item": 0,
  "plan_update": ["item1", "item2"],
  "action": [{"navigate": {"url": "..."}}, ...]
}
```
Flash mode strips `thinking`, `evaluation_previous_goal`, `next_goal`, `current_plan_item`, `plan_update` — only `memory` + `action` remain. Much cheaper per step.

---

### Models

| Slot | Default | Fallback | Purpose |
|---|---|---|---|
| `llm` | Any (user-supplied) | `fallback_llm` | Main reasoning/action selection; called every step |
| `page_extraction_llm` | = main llm | — | Structured extraction from page markdown; 120s timeout |
| `judge_llm` | = main llm (or gpt-4o) | ChatBrowserUse(request_type='judge') | Post-hoc trace evaluation |
| `compaction_llm` | = page_extraction_llm | — | Message compaction summaries |
| `fallback_llm` | None | — | Used when main llm raises |

**LLM timeout auto-detection (KNOWN, `service.py:266-282`):**
```
"gemini"          → 75s
"gemini-3-pro"    → 90s
"groq"            → 30s
"o3/claude/sonnet/deepseek" → 90s
default           → 75s
step_timeout      → 180s
```

**Proprietary fine-tuned models:**
- `bu-2-0`, `bu-1-0` — closed-source cloud models, endpoint `https://llm.api.browser-use.com/v1/chat/completions`
- `bu-30b-a3b-preview` — open-weights; architecture: Qwen3-VL-30B-A3B-Instruct MoE (30B total, 3B active at inference, 65536-token context, BF16)
- Fine-tuned specifically on browser-use trajectory data to reliably output the `AgentOutput` JSON schema

---

### Full Tool Registry (~30 actions)

Actions registered via `@self.registry.action(description, param_model=...)` in `tools/service.py`. Every action returns `ActionResult(error=msg)` on failure — never raises.

**Navigation:**
- `search(query, engine="duckduckgo")` — default duckduckgo ("less captchas" per comment); `terminates_sequence=True`
- `navigate(url, new_tab=False)` — with empty-DOM retry: wait 3s → reload + wait 5s → error
- `go_back()`, `wait(seconds=3, cap=30)`

**Element interaction:**
- `click(index, coordinate_x?, coordinate_y?)` — two variants; coordinate variant auto-enabled for Claude Sonnet 4.5+
- `input(index, text, clear=True)` — autocomplete detection (0.4s delay for combobox), sensitive-data redaction, value-mismatch detection
- `upload_file(index, path)` — path must be in `available_file_paths` allowlist
- `send_keys(key)` — Escape, Enter, PageDown, Control+o, etc.

**Content extraction:**
- `extract(query, output_schema?)` — separate `page_extraction_llm` call, 120s timeout; output < 10K chars → `long_term_memory`; else → filesystem
- `search_page(query, regex=False, css_scope?)` — **zero LLM cost**, pure JS grep via `Runtime.evaluate`
- `find_elements(query, css_scope?)` — zero LLM cost
- `screenshot()`, `save_as_pdf()`

**Tab management:** `switch(tab_id)`, `close(tab_id)`, `open_tab(url)`, `list_tabs()`

**File system:** `write_file(file_name, content)`, `read_file(file_name)`, `replace_file(file_name, old, new)`

**JS execution:** `evaluate(code)` — CDP `Runtime.evaluate` with `returnByValue=True, awaitPromise=True`

**Done:** `done(text, success)` — triggers 6-step pre-done verification in system prompt

**Plan (not a tool):** `plan_update` in the output JSON — maintained in `<plan>` section of the user message

**MCP integration (bidirectional):**
- Browser-Use consumes MCP tools via `MCPToolWrapper` → every MCP tool becomes a registered action with auto-generated Pydantic schema
- Browser-Use exposes 15 tools as an MCP server (see MCP section below)

---

### Context Assembly

Per-step message structure (rebuilt fresh each step — NOT appended, cache-friendly):

```
<agent_history>
  {compacted_memory if present}
  <step_1>
    Evaluation of Previous Step: ...
    Memory: ...
    Next Goal: ...
    Action Results: ...
  </step_1>
  ...
</agent_history>

<agent_state>
  <user_request>{task}</user_request>
  <file_system>{file_system.describe()}</file_system>
  <todo_contents>{todo.md content}</todo_contents>
  <plan>{plan_description}</plan>
  <sensitive_data>{summary}</sensitive_data>
  <step_info>Step{N} maximum:{max}  Today:{YYYY-MM-DD}</step_info>
  <available_file_paths>{paths}</available_file_paths>
</agent_state>

<browser_state>
  <page_stats>{stats}</page_stats>
  Current tab: {id_last4}
  Available tabs: ...
  Interactive elements: [1]<button>Click me</button> ...
</browser_state>

<read_state>
  <read_state_0>{once-only extracted content}</read_state_0>
</read_state>

<page_specific_actions>{filtered actions for this URL}</page_specific_actions>

[screenshots as multipart content]
```

**Key design decisions:**
- Single user message rebuilt each step (not a growing conversation). Provider-level caching hits the system message every time.
- `read_state` is a one-shot channel: extracted content appears ONCE in next message, then discarded. Used for `extract`, `read_file`, dropdown options.
- `<page_specific_actions>` — per-URL action filtering reduces distraction
- `sensitive_data` is passed separately so it's available to actions but redacted in logs

---

### Memory

**In-session (non-persistent):**
- `MessageManager` maintains `agent_history_items: list[HistoryItem]`
- `compacted_memory: str | None` — rolling summary of older history
- `ActionLoopDetector` — last 20 action hashes + 5 page fingerprints (behavioral memory)

**Message compaction (KNOWN, `MessageCompactionSettings`):**
```python
compact_every_n_steps = 25
trigger_char_count    = 40000   # ~10k tokens
keep_last_items       = 6       # keep first + last 6 items after compaction
summary_max_chars     = 6000
chars_per_token       = 4.0
```
Compaction system prompt (verbatim):
```
You are summarizing an agent run for prompt compaction.
Capture task requirements, key facts, decisions, partial progress, errors, and next steps.
Preserve important entities, values, URLs, and file paths.
CRITICAL: Only mark a step as completed if you see explicit success confirmation in the history.
If a step was started but not explicitly confirmed complete, mark it as "IN-PROGRESS".
Never infer completion from context — only report what was confirmed.
Return plain text only. Do not include tool calls or JSON.
Keep under 6000 characters if possible.
```

**Persistent (per-session FileSystem):**
- Default file: `todo.md` (auto-created)
- `MAX_MEMORY_SIZE = 1000` chars per file in long-term memory slot; full content via `read_file`
- System prompt instruction: "DO NOT use the file system if the task is less than 10 steps!"

**Cross-session:** NOT supported natively. The agent has no cross-session memory; the user must bootstrap from an external store.

---

### System Prompts (verbatim fragments)

8 variants compiled at init time. Selection logic:
```
if is_browser_use_model:
  flash_mode → system_prompt_browser_use_flash.md (15 lines)
  use_thinking → system_prompt_browser_use.md (18 lines — minimal; model is fine-tuned)
  else → system_prompt_browser_use_no_thinking.md
elif is_anthropic_4_5 and flash_mode: system_prompt_anthropic_flash.md (240 lines — inflated for cache threshold)
elif flash_mode and is_anthropic: system_prompt_flash_anthropic.md (31 lines)
elif flash_mode: system_prompt_flash.md (16 lines)
elif use_thinking: system_prompt.md (269 lines — default)
else: system_prompt_no_thinking.md (245 lines)
```

**Anthropic 4.5 cache optimization:** prompt inflated to ≥4096 tokens specifically to cross the Anthropic prompt-cache threshold. Every call with the same system prompt gets a cache hit.

Key sections in default prompt (`system_prompt.md:269 lines`):
- `<browser_rules>` — 24 rules: elements, captchas, popups, autocomplete, login, PDF, 403/bot detection, loops
- `<planning>` — task-complexity-driven plan generation rules
- `<pre_done_verification>` — 6-step mandatory check before calling done
- `<efficiency_guidelines>` — action categories: page-changing (always last), potentially page-changing, safe-to-chain
- `<reasoning_rules>` — 15 reasoning guidelines
- `<critical_reminders>` — 12 reminders
- `<error_recovery>` — 8 strategies

Budget nudge (verbatim from `system_prompt.md:133-137`):
> "When you reach 75% of your step budget, critically evaluate whether you can complete the full task in the remaining steps."

---

### Error Handling / Resilience

```
Error type              → Handling
InterruptedError        → User interruption; not logged as error
CDP/WebSocket error     → Reconnect wait (RECONNECT_WAIT_TIMEOUT); if root is None → terminal
RateLimitError          → "Rate limit reached. Waiting before retry."
ValidationError         → "Invalid model output format. Please follow the correct schema."
Missing required fields → Stripped stacktrace; "Please stick to the required output format."
All others              → Format error, return as ActionResult.error
```

**Replan nudge:** 3 consecutive failures → inject "Consider revising your plan or trying a different approach."
**Exploration nudge:** no plan after 5 steps on a complex task → nudge to generate one.
**Force-done:** last step reached without `done` call → inject forcing message.

**Loop detection (escalating):**
- 5+ repetitions: soft nudge ("If this is intentional, carry on")
- 8+ repetitions: stronger nudge
- 12+ repetitions: strongest nudge
- 5+ consecutive stagnant pages: "page content has not changed"
Nudges are injected into the user message as context — the agent is informed, never hard-blocked.

---

### Exact Constants

| Constant | Value | Source |
|---|---|---|
| `max_failures` | 5 | `views.py:66` |
| `max_actions_per_step` | 5 | `views.py:71` |
| `compact_every_n_steps` | 25 | `views.py:39` |
| `trigger_char_count` | 40000 (~10k tokens) | `views.py:55` |
| `keep_last_items` | 6 | `views.py:43` |
| `summary_max_chars` | 6000 | `views.py:44` |
| `max_clickable_elements_length` | 40000 chars | `views.py:92` |
| `MAX_CHAR_LIMIT` (extract) | 100000 | `tools/service.py:1050` |
| `MAX_MEMORY_LENGTH` (extract) | 10000 | `tools/service.py:1213` |
| `MAX_CONTENT_SIZE` (read_state) | 60000 | `message_manager/service.py:354` |
| `MAX_MEMORY_SIZE` (read_file) | 1000 | `tools/service.py:1773` |
| `llm_timeout` default | 60s (auto-set per model) | `views.py:85` |
| `step_timeout` | 180s | `views.py:86` |
| `extract llm timeout` | 120s | `tools/service.py:1163, 1243` |
| `loop_detection_window` | 20 | `views.py:90` |
| `planning_replan_on_stall` | 3 | `views.py:79` |
| `planning_exploration_limit` | 5 | `views.py:80` |
| `wait action cap` | 0-30s | `tools/service.py:580` |
| `autocomplete dropdown delay` | 0.4s | `tools/service.py:818` |
| `empty DOM retry wait 1` | 3s | `tools/service.py:524` |
| `empty DOM retry wait 2` | 5s | `tools/service.py:535` |
| `Anthropic 4.5 cache threshold` | 4096 tokens | `prompts.py:17-24` |
| `ChatBrowserUse retries` | max=5, base=1.0s, max=60s, 10% jitter | `chat.py:28,67-69` |
| Loop nudge thresholds | 5/8/12 | `views.py:215-244` |
| Page stagnation threshold | 5 consecutive | `views.py:239` |
| MCP session timeout | 10 minutes | `mcp/server.py:190` |
| Sandbox SSE endpoint | `https://sandbox.api.browser-use.com/sandbox-stream` | `sandbox.py:366` |
| Sandbox HTTP timeout | 1800s (30 min) | `sandbox.py:379` |
| Cloud LLM endpoint | `https://llm.api.browser-use.com/v1/chat/completions` | `chat.py:85,256` |
| Download file-size min | > 4 bytes | `downloads_watchdog.py:353` |
| Popup dialog timeout | 0.5s per approach (2 approaches) | `popups_watchdog.py:96,116` |
| Search engine default | duckduckgo | `tools/views.py:52` |
| Google search URL anti-AI-overview param | `&udm=14` | `tools/service.py:454` |

---

### Multi-Agent Coordination

Browser-Use is **single-agent with opt-in composition**:

1. **Shared BrowserSession parallelism:** multiple `Agent` instances share one `BrowserSession`, each runs in its own tab via `asyncio.gather`. No coordination protocol — race conditions possible if agents manipulate the same tab.
2. **Specialized sub-LLMs per role:** one agent, 4 LLM slots (main, extract, judge, compact). The pattern matches OpenAI Operator's planner+executor split.
3. **Post-hoc judge:** `judge_llm` evaluates entire trace after completion. Returns `{success, score, reasoning, failure_mode}`. Opt-in, NOT used to gate or retry execution.
4. **Cloud Skills:** named pre-built workflows fetched at init. Skills inject as native actions. The local agent calls a skill; the cloud runs another agent to execute it. Multi-agent through composition.
5. **MCP Server:** 15 tools exposed, making the entire Agent a tool for upstream LLMs (Claude Desktop, Cursor, OpenAI Operator). Includes `retry_with_browser_use_agent` — when direct tools fail, the MCP host's LLM can hand off the full task to browser-use's internal agent as a sub-agent.

---

### Streaming Protocol

- **LLM calls:** `asyncio.wait_for(get_model_output_with_retry, timeout=llm_timeout)` — waits for complete JSON, no token-level streaming back to user
- **Sandbox cloud:** SSE over HTTP POST (`sandbox.api.browser-use.com/sandbox-stream`) — event types: `browser_created` (with `live_url`), `instance_created`, `instance_ready`, `log`, `result`, `error`, `stream_complete`
- **Cloud LLM:** `sticky routing via session_id` header — same session always hits same backend container (LLM context cache reuse)
- **Cancellation:** `pause()`, `resume()`, `stop()` on the Agent; state is a Pydantic model, checkpointable

---

### Provider-Specific Structured Output

| Provider | Mechanism | Notes |
|---|---|---|
| OpenAI | `response_format: ResponseFormatJSONSchema` with `strict=True` | Rejects schemas with `oneOf`; requires `additionalProperties: false` |
| Anthropic | Single tool + `tool_choice=ToolChoiceToolParam(type='tool', name=X)` | `cache_control='ephemeral'` on every call (prompt caching on by default) |
| Google/Gemini | `response_mime_type='application/json'` + `response_schema` | Constrained decoding; `pattern`/`format` not enforced |
| browser-use cloud | `payload['output_format'] = model_json_schema()` | Server-side enforcement (presumably constrained decoder) |

**Anthropic double-serialization fix (KNOWN, `chat.py:225-244`):**
When Claude emits `{"actions": "[{...}]"}` (string instead of array), browser-use intercepts validation failure, attempts `json.loads` on any field value starting with `[` or `{`, retries validation. This production workaround is battle-tested.

**Anthropic prompt caching default:** `cache_control='ephemeral'` on every call. At ~5KB system prompt, saves ~$0.30 per 100 steps on cache hits.

---

### Watchdog Architecture

15 watchdogs, total ~9,500 lines (2x the BrowserSession class). Each inherits `BaseWatchdog(pydantic.BaseModel)` with `LISTENS_TO` and `EMITS` declarations. Communication via event bus; cross-watchdog synchronization via **direct callbacks** (bypassing the bus for synchronous coordination).

Key watchdogs:
- `DefaultActionWatchdog` (3,702 lines) — the one doing actual browser work: click, type, scroll, get_state, extract_content
- `DownloadsWatchdog` (1,411 lines) — PDF auto-download detection, filesystem diff fallback for missing CDP `filePath`, direct-callback bypass for click→download sync
- `CaptchaWatchdog` (207 lines) — blocks agent step loop at `wait_if_captcha_solving()`; only tracks one captcha at a time
- `SecurityWatchdog` (296 lines) — `allowed_domains` enforcement via `Network.continueInterceptedRequest` → cloud-safety boundary for runaway agents
- `CrashWatchdog` (336 lines) — `Inspector.targetCrashed` / `Target.targetCrashed`; optional auto-recovery (re-create tab or restart local browser)
- `PopupsWatchdog` (145 lines) — dialog policy: `alert/confirm/beforeunload` → accept; `prompt` → cancel

**Dual-path pattern (event bus + direct callbacks):** events go through the async queue; direct callbacks are out-of-band for the originator. Used when an action handler (e.g., DefaultActionWatchdog.click) needs to synchronously wait for a downstream result (e.g., DownloadsWatchdog download completion) without going through the full async dispatch.

---

### MCP Server (bidirectional)

**Exposed tools (15, from `mcp/server.py:228+`):**
`browser_navigate`, `browser_click`, `browser_type`, `browser_get_state`, `browser_get_html`, `browser_screenshot`, `browser_extract_content`, `browser_scroll`, `browser_go_back`, `browser_list_tabs`, `browser_switch_tab`, `browser_close_tab`, `retry_with_browser_use_agent`, `browser_list_sessions`, `browser_close_session`, `browser_close_all`

**Key design:** `retry_with_browser_use_agent` is the escape hatch — when the MCP host's LLM fails repeatedly with direct tools, it can invoke the full browser-use Agent as a sub-agent. This makes Browser-Use simultaneously an MCP server AND an MCP-tool-using agent.

**Session model:** `session_timeout_minutes=10` default; auto-cleanup task polls for stale entries.

---

### Verso Lesson: Browser Use

**COPY:**
1. **4-phase step loop with explicit phases.** The clean separation of (0) pre-check, (1) context preparation, (2) LLM+execute, (3) post-process is the right architecture for any Verso agent loop. Each phase has a clear contract.
2. **Failure budget that resets on success.** `max_failures=5` consecutive, not total. A hard cumulative cap would kill agents that hit a temporary error and recover. Reset on success preserves progress.
3. **Message compaction with anti-hallucination instruction.** "Never infer completion from context — only report what was confirmed." The `IN-PROGRESS` vs `confirmed complete` distinction is critical for long-running agents. Verso should ship this as the default compaction prompt.
4. **One-shot `read_state` channel.** Extracted content appears once in the next message then is discarded. Prevents "I already know that" context bloat. Verso should ship this pattern for any "fetch and process" tool result.
5. **Escalating loop nudges (soft, not hard).** 5/8/12 repetition thresholds with escalating message injection. Never hard-block the agent — inform it. Verso's loop detector should be a soft conscience.
6. **Budget warning at 75%.** Inject a budget-awareness message when the agent is ¾ through its step budget. Verso should have this built into the loop, not left to the user.
7. **Post-hoc judge as first-class.** `judge_llm` evaluates traces with `{success, score, reasoning, failure_mode}`. The judge is opt-in and does NOT gate execution. Verso should ship this as the built-in eval harness — separate from the agent loop, hooked into the return value.
8. **Provider-native structured output per LLM.** Browser-Use's `SchemaOptimizer` and per-provider serializer are the right answer to "make the LLM emit valid JSON." Verso should have a per-provider output schema adapter that handles OpenAI strict mode, Anthropic tool_use, Gemini response_schema, and the double-serialization bug fix.
9. **Flash mode (strip thinking/planning fields).** For cost optimization on cheap models, emit only `memory + action`. Verso agents should have a `flash_mode` flag that strips non-essential output fields.
10. **`done` as a tool with mandatory pre-verification.** The 6-step pre-done checklist prevents the agent from declaring success prematurely. Verso should enforce a `done` tool with a configurable verification checklist.
11. **Anthropic prompt caching on by default.** At ~5KB system prompts, the Anthropic ephemeral cache saves ~$0.30/100 steps. Verso agents using Anthropic should set `cache_control='ephemeral'` on system messages automatically.

**AVOID:**
1. **70-argument constructors.** Browser-Use's `Agent.__init__` accepts ~70 kwargs. Composability is good; surface area is too wide. Verso should group related settings into nested config objects (e.g., `CompactionSettings`, `LoopSettings`, `ModelSlots`).
2. **Provider-specific system prompt variants.** Maintaining 8 prompt files for 8 provider/mode combinations is a maintenance burden. Verso should have one canonical prompt template with feature flags (thinking, flash, cache-padding) handled by the template engine, not separate files.
3. **Cross-session memory gap.** Browser-Use has no cross-session memory. Verso should ship a pluggable `MemoryBackend` (default: in-process; opt-in: Redis/Postgres/vector store) as a first-class primitive.
4. **The `retry_with_browser_use_agent` escape hatch in the MCP server.** Having the MCP server spawn a full Agent as a fallback creates unpredictable behavior — the MCP client doesn't know whether it's getting a deterministic tool call or an autonomous sub-agent. Verso's MCP exposure should be transparent about what it invokes.
5. **Direct-callback bypass of the event bus.** The DownloadsWatchdog's out-of-band callback is a design smell — when the bus is too slow for synchronous coordination, that's a signal the bus architecture needs a synchronous lane, not a bypass. Verso's event/tool system should have explicit synchronous and async dispatch modes.

---

## Composio + Browser Use: Cross-System Patterns

### Pattern 1: Tools as Data, Not Code

Composio: `{slug, description, http_method, http_path, parameters: JSON-Schema}` stored in Postgres. The 250+ tools are data rows, not code. The proxy executor reads the tool descriptor and forwards the HTTP request.

Browser-Use: action descriptions are docstrings on Python functions. The DOM provides the action space — elements are the parameters.

**Verso implication:** Verso's built-in tool registry should be data-driven. Tool definitions should be storable, serializable, and inspectable without running code.

### Pattern 2: Bidirectional MCP (Server AND Client)

Both systems are simultaneously MCP servers and MCP clients:
- Composio exposes its tool catalog as an MCP server, while consuming MCP tools from external servers
- Browser-Use exposes browser actions as an MCP server (`mcp/server.py`), while consuming MCP tools as actions via `MCPToolWrapper`

**Verso implication:** Verso should ship with bidirectional MCP as a first-class concern, not a plugin. An agent built on Verso should be usable as a tool by other agents without any additional configuration.

### Pattern 3: The Judge / Evaluator as Separate LLM

Both systems have explicit post-hoc evaluators:
- Composio: SEARCH returns `difficulty` assessment + `execution_guidance`
- Browser-Use: `judge_llm` evaluates complete traces with `{success, score, failure_mode}`

The judge is NEVER in the hot path. It does not gate execution or trigger retries.

**Verso implication:** Verso's eval harness should be a separate component (not part of the loop), hooked into `agent.run()` return value. The judge LLM should be configurable independently of the main LLM.

### Pattern 4: Graceful Degradation on Structured Output Failure

Both systems handle LLM structured output failures gracefully:
- Composio: `{successful: false, error: ..., data: null}` envelope; agent sees error and adapts
- Browser-Use: Anthropic double-serialization fix; fallback to JSON extraction from markdown fences; increment failure budget and continue

**Verso implication:** Verso's action/tool invocation pipeline must never propagate unhandled exceptions to the agent loop. Every tool failure is data. The framework handles output format errors with provider-specific fixups before surfacing to the loop.

### Pattern 5: Bounded Parallelism (Not Unlimited Fan-out)

- Composio: `MAX_PARALLEL_WORKERS=5` in MULTI_EXECUTE
- Browser-Use: `max_actions_per_step=5`

**Verso implication:** Verso's parallel tool dispatch should have a configurable but bounded worker limit. The default should be small (5) to avoid OAuth rate limits and resource exhaustion.

---

## Verso Implications Summary

1. **First-class meta-tool layer.** Build `VersoSearch`, `VersoMultiExecute` as built-in meta-tools that reduce tool-schema token cost from O(N) to O(1). Agents discover tools dynamically.
2. **Modifier engine (schema/before/after) is the right middleware abstraction.** Three apply points, scoped by `(tool, toolkit)`, empty = all. Ship this in Verso's tool invocation pipeline.
3. **Execution envelope `{data, error, successful}` — always, never raise.** Every tool failure is data the agent can reason about.
4. **4-phase step loop with failure budget that resets on success.** Clean phase boundaries, `max_failures=5` consecutive reset, budget warning at 75%.
5. **Compaction with anti-hallucination instruction.** Never infer completion from context. `IN-PROGRESS` vs confirmed-complete.
6. **One-shot read_state channel.** Extracted content lives in the next message only.
7. **Escalating soft nudges for loop detection.** 5/8/12 thresholds, never hard-block.
8. **Post-hoc judge LLM returning `{success, score, failure_mode}`.** Not in the hot path.
9. **Provider-native structured output with per-provider fixups.** Ship `SchemaOptimizer` equivalent.
10. **Flash mode (strip planning fields).** For cheap, fast steps.
11. **Done as a tool with verifiable checklist.** Prevent premature success declarations.
12. **Bidirectional MCP as first-class.** Every Verso agent is both an MCP server and an MCP client.
13. **Session-level permission model.** `allow_all|ask_every_call|ask_once_per_session` + per-tool overrides.
14. **Plan cache (recipe layer).** BM25 use_case → cached plan replay without re-planning.
15. **Tag-based tool filtering (`readOnlyHint`, `destructiveHint`).** MCP-spec tags, first-class in session config.
16. **Anthropic prompt caching automatic.** Set `cache_control='ephemeral'` on system messages by default.
17. **Pluggable cross-session MemoryBackend.** In-process default; Redis/Postgres opt-in.
18. **Tools as data rows, not code.** Verso tool registry should be serializable and storable.
