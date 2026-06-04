# fw-claude-sdk-platforms — Claude Agent SDK + Agent Platforms
<!-- cluster research note for Verso framework design -->
<!-- sources: teardowns/CLAUDE_AGENT_SDK.md (R1–R3 + Coverage Expansion), teardowns/AGENT_PLATFORMS.md -->

---

## 1. Claude Agent SDK

### What It Is

Anthropic's official agent harness (`claude-agent-sdk` PyPI / `@anthropic-ai/claude-agent-sdk` npm).
**Decisive architectural fact:** it does NOT implement an agent loop in user code. It spawns the `claude` CLI binary as a subprocess and speaks a JSONL bidirectional control protocol over stdin/stdout. The loop — tool execution, planning, sub-agents, context compaction, permission gating — runs inside the Bun-compiled TypeScript CLI. The Python/TS SDK is a process orchestrator + protocol bridge only.

- Python LOC: ~10,561 across `src/claude_agent_sdk/`
- Bundled CLI version: `2.1.158`; minimum supported: `2.0.0` (`MINIMUM_CLAUDE_CODE_VERSION`)
- Runtime deps: `anyio`, `mcp`, `typing_extensions`

### Agent Loop Shape

The loop is subprocess-owned. The SDK's contribution is the message-dispatch loop `Query._read_messages` (`query.py:247`), which demuxes one stdout stream into:

```
control_response        → wake pending RPC waiter (anyio.Event.set)
control_request         → spawn inbound-callback handler task
control_cancel_request  → cancel in-flight handler by request_id
transcript_mirror       → hand to TranscriptMirrorBatcher (NOT yielded to user)
result                  → flush batcher; set _first_result_event; capture error text
(everything else)       → forward to user's async iterator
```

Three subtle mechanics worth copying in Verso:

1. `transcript_mirror` frames are peeled off and never surfaced. Persistence is a side-channel; it must not pollute the message stream.
2. Opaque `ProcessError(exit_code=1)` is swapped for the CLI's structured last-error text so the raised exception is actionable.
3. A shielded `{"type":"end"}` sentinel is emitted on `finally` via `send_nowait`, so a blocked `receive_messages()` caller always unblocks on stream end, even under `CancelledError`.

**Termination / iteration caps:**
- `max_turns: int` → `--max-turns N` CLI flag
- `max_budget_usd: float` → `--max-budget-usd N`
- `task_budget: {total: int}` → `--task-budget N` (beta: `task-budgets-2026-03-13`)
- Sub-agent cap: `AgentDefinition.maxTurns`

### Models / Routing

Anthropic-only. No provider abstraction in the SDK; the CLI calls `/v1/messages` directly.

- `ClaudeAgentOptions.model` — exact model name or alias (`sonnet`, `opus`, `haiku`)
- `ClaudeAgentOptions.fallback_model` — backup if primary fails
- `AgentDefinition.model: "sonnet" | "opus" | "haiku" | "inherit"` — per-sub-agent override
- `effort: "low" | "medium" | "high" | "xhigh" | "max" | int` — 5 named levels; `xhigh` is Opus 4.7-only; `max` requires 4.6+ family; default is `"high"`
- `betas: SdkBeta[]` — currently one named beta: `"context-1m-2025-08-07"` (1M context, Sonnet 4/4.5 only)
- `thinking: {type: "adaptive" | "enabled" | "disabled", budget_tokens?, display?}` — three-mode thinking config; `display: "omitted"` is Opus 4.7+ default

**7 API providers** (from `AccountInfo.apiProvider` in `sdk.d.ts:23-34`):
`firstParty | bedrock | vertex | foundry | anthropicAws | mantle | gateway`

### Tool System

Three tool sources, all configured via CLI flags:

**1. Built-in tools (~25, live inside the CLI binary):**
`Bash`, `Read`, `Write`, `Edit`, `MultiEdit`, `Glob`, `Grep`, `Task` (sub-agent spawn), `WebFetch`, `WebSearch`, `NotebookRead`, `NotebookEdit`, `TodoRead`, `TodoWrite`, `Skill`, ...

Selected via `options.tools = ["Bash", "Read", ...]` or preset; empty list `[]` → `--tools ""` disables all.

**2. External MCP servers** — 5 transport types (from `sdk.d.ts:945-1029`):
- `stdio` — subprocess over stdin/stdout
- `sse` — HTTP+SSE
- `http` — streamable HTTP (newer)
- `sdk` — in-process (zero IPC; tool call routed via `mcp_message` control request)
- `claudeai-proxy` — Anthropic's hosted MCP proxy at `https://mcp-proxy.anthropic.com` (OAuth aggregator model)

`strict_mcp_config=True` ignores all MCP sources except `options.mcp_servers`.

**3. In-process SDK MCP servers** (the novel feature):

```python
@tool("greet", "Greet a user", {"name": str})
async def greet(args):
    return {"content": [{"type": "text", "text": f"Hello, {args['name']}!"}]}

server = create_sdk_mcp_server(name="my_server", version="1.0.0", tools=[greet])
options = ClaudeAgentOptions(mcp_servers={"my_server": server}, allowed_tools=["greet"])
```

Mechanics: the `instance` field is stripped before the config JSON is sent to the CLI (`subprocess_cli.py:312-317`). When the CLI calls a tool on `my_server`, it emits an `mcp_message` control_request. The SDK's manual JSONRPC router (`query.py:548`) handles 4 methods: `initialize`, `tools/list`, `tools/call`, `notifications/initialized`. Per-call MCP protocol version hardcoded: `"2024-11-05"`, tools-only capabilities (no `listChanged`).

**Content-block type conversions** for `tools/call` responses: `text` → text block; `image` → image block; `resource_link` → synthetic text (name + uri + description joined with newlines); `resource` with embedded text → text block; binary resource → **silently dropped with warning**.

**Per-tool permission policy** (`sdk.d.ts:1034`): `always_allow | always_ask | always_deny`.

**Tool schema generation** (`__init__.py:234-303`): custom `_python_type_to_json_schema` handles `Annotated[type, "description"]`, `NotRequired`/`Optional`/`Union`/`list[T]`/TypedDict. Falls back to `"string"` for unknown types.

### Control Protocol (13 subtypes)

Synchronous RPC over the async JSONL stream. Wire format:

```jsonc
// SDK → CLI
{"type": "control_request", "request_id": "req_42_a1b2c3d4",
 "request": {"subtype": "initialize", "hooks": {...}, "agents": {...}}}

// CLI → SDK (success)
{"type": "control_response", "response": {"subtype": "success",
 "request_id": "req_42_a1b2c3d4", "response": {...}}}

// CLI → SDK (error)
{"type": "control_response", "response": {"subtype": "error",
 "request_id": "req_42_a1b2c3d4", "error": "Tool permission denied"}}

// CLI → SDK (cancel in-flight)
{"type": "control_cancel_request", "request_id": "req_42_a1b2c3d4"}
```

`request_id` format: `f"req_{counter}_{os.urandom(4).hex()}"` (`query.py:515`). Pending requests: two parallel dicts (`pending_control_responses: {id: anyio.Event}`, `pending_control_results: {id: dict|Exception}`).

**SDK → CLI (10 outbound):** `initialize`, `interrupt`, `set_permission_mode`, `set_model`, `mcp_status`, `get_context_usage`, `rewind_files`, `mcp_reconnect`, `mcp_toggle`, `stop_task`

**CLI → SDK (3 inbound callbacks):** `can_use_tool`, `hook_callback`, `mcp_message`

**Default timeout:** 60.0 s per request (`query.py:502`); `initialize_timeout` default also 60.0 s (`query.py:83`). Timeout → `Exception("Control request timeout: {subtype}")`.

**Cancellation:** `control_cancel_request` → `_inflight_requests.pop(request_id).cancel()`. The handler re-raises `CancelledError` **without writing a response** — writing a stale response would cause a "stale response" error on the CLI side.

### Context Assembly / Compaction / Budget

Managed entirely by the CLI binary (opaque). The SDK exposes:

- `getContextUsage()` → per-category token counts: `system_prompt`, `tools`, `messages`, `mcp_tools`, `memory_files`, and more
- `excludeDynamicSections: bool` → sent in `initialize` to enable fleet-wide caching (strips sections that change per request)
- `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` sentinel — marks where static/cacheable content ends
- `seedReadState(path, mtime)` — primes the CLI's read-file-state cache when a Read was snipped from context, preventing false "file not read yet" errors on subsequent Edits
- `rewindFiles(user_message_id)` — reverts tracked files to their state at a given message (requires `enable_file_checkpointing=True`)

### Memory

**In-session:** managed by the CLI (JSONL transcript at `~/.claude/projects/<hash>/<session-id>.jsonl`).

**Persistence / resume options:**
- `continue_conversation=True` → `--continue`
- `resume=session_id` → `--resume <id>`
- `fork_session=True` → new session ID, history copied

**Pluggable SessionStore** (S3, Redis, Postgres, custom):
- `--session-mirror` flag turns every CLI disk-write into a `transcript_mirror` stdout frame
- SDK's `TranscriptMirrorBatcher` coalesces them and calls `store.append()`
- Constants: `MAX_PENDING_ENTRIES = 500`, `MAX_PENDING_BYTES = 1 MiB`, 3 retries with backoff `(0.2s, 0.8s)`, `SEND_TIMEOUT_SECONDS = 60.0` (`transcript_mirror_batcher.py:28-29`)
- Coalescing strategy: one `store.append` per file_path per flush (not one per frame)
- Close flush is shielded (`anyio.CancelScope(shield=True)`) — survives Ctrl+C
- Errors surfaced asynchronously via `on_error` callback AFTER lock release; at-most-once delivery

**Session fork** (`session_mutations.py:240-430`): pure local JSONL UUID-remap — copy linear main-chain transcript up to message N, mint fresh uuid for every entry, rewrite all `parentUuid` fields through the old→new map. Sidechains (sub-agent runs) excluded. Progress frames mapped (for chain-walk) but not written. Not a server operation.

**Sub-agent memory scopes** (`AgentDefinition.memory`): `"user"` → `~/.claude/agent-memory/<type>/`, `"project"` → `.claude/agent-memory/<type>/`, `"local"` → `.claude/agent-memory-local/<type>/`.

**Skills** — filesystem-resident `SKILL.md` files; `options.skills = ["search"]` adds `Skill(search)` to `allowed_tools`.

### Hook System

**29 hook events** (TypeScript SDK; Python SDK has 10 — `SessionStart` not in Python `HookEvent` literal):

Python (10): `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `PreCompact`, `Notification`, `SubagentStart`, `PermissionRequest`

Hook registration is ID-based: each callback function gets `hook_{N}` assigned at `initialize`; only the IDs are sent on the wire; functions stay in-process. When the CLI fires a hook, it sends `hook_callback` control_request with `callback_id`; the SDK looks up the function and invokes it.

**Hook output fields (critical ones):**
```python
# PreToolUse hookSpecificOutput:
{
    "permissionDecision": "allow" | "deny" | "ask" | "defer",  # 4-value; deny>ask>allow>defer precedence
    "updatedInput": dict,          # rewrite tool args before execution
    "additionalContext": str,      # inject text into the model's next turn
}
# PostToolUse hookSpecificOutput:
{
    "updatedToolOutput": Any,      # rewrite tool result BEFORE model sees it
    # (must match tool's exact output schema for built-in tools)
}
# Common:
{
    "continue_": bool,             # False = stop the loop (→ "continue" on wire)
    "async_": True,                # defer execution (→ "async" on wire); CLI doesn't wait
    "asyncTimeout": int,           # ms
}
```

Field-name rewriting: `async_` → `async`, `continue_` → `continue` (`_convert_hook_output_for_cli`). Only these two keys.

**Async hooks** (`{async_: True}`) let slow side-effects (remote logging, alerts) run without blocking the conversation turn.

### Permission System

**6 modes** (`types.py:24-26`):
`default | acceptEdits | plan | bypassPermissions | dontAsk | auto`

- `auto` — a classifier model on the CLI side decides per call
- `plan` — model can reason but cannot execute tools
- `bypassPermissions` — allow everything

**`can_use_tool` callback**: receives `ToolPermissionContext` (tool_name, input, tool_use_id, agent_id, blocked_path, decision_reason, suggestions list). Returning `PermissionResultAllow(updated_input=...)` rewrites the tool args before execution. Returning `PermissionResultDeny(interrupt=True)` aborts the whole turn.

**`PermissionResultAllow` wire encoding:** `{"behavior":"allow", "updatedInput": updated_input or original_input}`. The CLI always expects `updatedInput` — SDK echoes original if not overridden.

**5 permission update destinations**: `userSettings`, `projectSettings`, `localSettings`, `session`, `cliArg`.

**7 policy settings origins**: `helper` (admin subprocess), `remote` (cached), `plist` (macOS MDM), `hklm` (Windows registry), `file` (managed-settings.json), `parent` (embedding app), `hkcu` (Windows user registry).

**Managed settings restrictive-only filter**: embedding apps can strengthen admin policies via `managedSettings` but cannot weaken them — permissive arrays (`allow`, `additionalDirectories`) are silently dropped.

### Multi-Agent / Handoffs

**No explicit "handoff" mechanism.** Multi-agent means sub-agents via the `Task` built-in tool. Defined in `options.agents = {name: AgentDefinition}`, sent in `initialize` payload (NOT a CLI flag). The CLI spawns sub-agents in-process (not a new subprocess) with own context, model, tools, MCP servers, permission mode.

`AgentDefinition` schema:
```python
description: str
prompt: str
tools: list[str] | None
disallowedTools: list[str] | None
model: str | None           # "sonnet" | "opus" | "haiku" | "inherit"
skills: list[str] | None
memory: "user" | "project" | "local" | None
mcpServers: list[str | dict] | None
initialPrompt: str | None
maxTurns: int | None
background: bool | None
effort: EffortLevel | int | None
permissionMode: PermissionMode | None
```

**Sub-agent attribution**: `_SubagentContextMixin` carries `agent_id` + `agent_type` on every hook event. When parallel sub-agents run, their tool-lifecycle hooks interleave over the same control channel; `agent_id` is the only reliable disambiguator.

**`backgroundTasks(toolUseId?)`** — background a running Bash command or sub-agent, returns "running in background" result immediately, task emits `task_notification` when it settles. Equivalent to Ctrl+B.

**`stop_task(task_id)`** — stop a sub-agent task; CLI emits `task_notification` with `status:'stopped'` asynchronously.

### Streaming Protocol

**JSONL over stdin/stdout only.** No SSE, no WebSocket at the SDK boundary.

CLI internally uses SSE to talk to Anthropic's API, but the SDK never sees raw API responses.

`include_partial_messages=True` → CLI emits `StreamEvent` with token-by-token deltas.
`include_hook_events=True` → CLI emits `HookEventMessage` objects alongside regular messages.

**User message wire frame** (`client.py:261-266`):
```json
{"type": "user", "message": {"role": "user", "content": "..."},
 "parent_tool_use_id": null, "session_id": "default"}
```

**Speculative JSON parsing** (`subprocess_cli.py:640`): `TextReceiveStream` can truncate long lines; buffer accumulates across reads until `json.loads` succeeds, bounded by `_DEFAULT_MAX_BUFFER_SIZE = 1024 * 1024` (1 MB). Non-`{` lines skipped when idle; appended mid-parse (could corrupt buffer — the `not json_buffer` guard prevents this for debug noise). On buffer overflow: raise `SDKJSONDecodeError`, buffer discarded (no partial-message recovery).

### Error / Retry Paths

- Non-zero subprocess exit → `ProcessError(exit_code)`, swapped for CLI's structured error text when available
- Control request timeout (60s) → `Exception("Control request timeout: {subtype}")`
- `CLINotFoundError` — binary not found in 8 search paths
- `SDKJSONDecodeError` — JSONL buffer overflow (>1 MB message)
- `MirrorErrorMessage` — SessionStore write failure (surfaced as a system message, not an exception)
- Hook callback exceptions → wrapped in `control_response` error subtype and re-raised in the CLI's context

### Exact Constants

| Constant | Value | Source |
|---|---|---|
| `MINIMUM_CLAUDE_CODE_VERSION` | `"2.0.0"` | `subprocess_cli.py:31` |
| Bundled CLI version | `2.1.158` | `_cli_version.py` |
| `_DEFAULT_MAX_BUFFER_SIZE` | `1024 * 1024` (1 MB) | `subprocess_cli.py:30` |
| Control-request timeout | 60.0 s | `query.py:502` |
| `initialize_timeout` | 60.0 s | `query.py:83` |
| version-check timeout | 2 s | `subprocess_cli.py:723` |
| `request_id` format | `"req_{counter}_{os.urandom(4).hex()}"` | `query.py:515` |
| `hook_callback_id` format | `"hook_{N}"` | `query.py:190` |
| In-process MCP `protocolVersion` | `"2024-11-05"` | `query.py:591-593` |
| `MAX_PENDING_ENTRIES` (batcher) | 500 | `transcript_mirror_batcher.py:28` |
| `MAX_PENDING_BYTES` (batcher) | 1 MiB | `transcript_mirror_batcher.py:29` |
| `SEND_TIMEOUT_SECONDS` (batcher) | 60.0 | `transcript_mirror_batcher.py` |
| `MIRROR_APPEND_MAX_ATTEMPTS` | 3 | `transcript_mirror_batcher.py` |
| `MIRROR_APPEND_BACKOFF_S` | `(0.2, 0.8)` | `transcript_mirror_batcher.py` |
| Subprocess grace (stdin EOF) | 5 s | `subprocess_cli.py:545-601` |
| Subprocess SIGTERM grace | 5 s | `subprocess_cli.py:545-601` |
| `EXIT_REASONS` | 6: `clear`, `resume`, `logout`, `prompt_input_exit`, `other`, `bypass_permissions_disabled` | `sdk.d.ts:555-557` |

### Subprocess Lifecycle

```
1. _find_cli: check _bundled/claude → PATH → 6 well-known paths → CLINotFoundError
2. atexit.register(_kill_active_children) — SIGTERM all live subprocesses on Python exit
3. connect(): build argv → anyio.open_process(piped stdio) → inject OTEL context
4. Query.start() → spawn _read_messages reader task
5. Query.initialize() → handshake (hooks/agents/skills, 60s timeout)
6. Write user message frame to stdin
7. [steady state: demux loop]
8. close():
   - cancel stderr reader
   - async with write_lock: _ready=False; stdin.aclose()  ← TOCTOU guard
   - stdin EOF → wait 5s for graceful exit (CLI flushes session file, issue #625)
   - timeout → SIGTERM → wait 5s → SIGKILL
   - discard from _ACTIVE_CHILDREN
```

OTEL: `propagate.inject(carrier)` + scrub stale inherited TRACEPARENT before writing active span's values. User `options.env` overrides everything.

### SDK API Surface (TypeScript canonical)

Two top-level entry points:
- `query(prompt, options, transport)` — fire-and-forget `AsyncIterator<Message>`. One-shot.
- `ClaudeSDKClient(options).connect()` — interactive bidirectional client

`ClaudeSDKClient` is **always streaming mode**. Per-turn boundary: `receive_response()` yields messages and `return`s after the first `ResultMessage` (inclusive).

**23-method Query interface** (key subset):
- `interrupt()`, `setPermissionMode()`, `setModel()`
- `getContextUsage()` → per-category token breakdown
- `rewindFiles(user_message_id)` → file-state rollback
- `seedReadState(path, mtime)` → prime read cache
- `backgroundTasks(toolUseId?)` → background foreground tasks
- `stopTask(task_id)`
- `forkSession(sessionId, options?)` → `{newSessionId}`
- `applyFlagSettings(settings)` → mid-session settings merge (flag layer sits above user/project/local, below managed policy; successive calls shallow-merge top-level keys)
- `reconnectMcpServer()`, `toggleMcpServer()`, `setMcpServers()`

**Settings cascade (5 tiers, lowest to highest):**
`localSettings` < `projectSettings` < `userSettings` < `flagSettings` (mid-session `applyFlagSettings`) < `managedSettings` (enterprise policy, restrictive-only)

### What's Novel / Verso Relevance

1. **Subprocess-delegated loop.** The SDK owns zero loop logic. All ReAct, compaction, sub-agent scheduling live in the binary. The SDK is a protocol bridge. This means loop improvements ship in the binary without SDK updates.

2. **In-process MCP routing via control protocol.** Tools can be pure async functions in user code, invoked over a single bidirectional JSONL channel with no subprocess per tool. Zero-IPC custom tools.

3. **`transcript_mirror` as a side-channel.** Session persistence piggybacks on the same stdout stream as messages; the SDK filters it out. Clean separation of concerns.

4. **Hook system = pre/post intercept for every layer.** `PreToolUse` can rewrite args before execution. `PostToolUse` can rewrite results before the model sees them. `UserPromptSubmit` can inject additional context. All without touching the model API.

5. **Async hooks.** Returning `{async_: True}` from a hook lets slow side-effects run without blocking the turn.

6. **Shielded final flush.** `anyio.CancelScope(shield=True)` in the batcher's `close()` ensures the last turn's writes land even under Ctrl+C.

---

## 2. Browserbase / Stagehand

### Agent Loop Shape

Stagehand's agent uses **Vercel AI SDK** (`generateText`) with tool calling — not a hand-rolled loop:

```
prepareAgent() → buildAgentSystemPrompt() → createAgentTools()
→ llmClient.generateText(temperature=1, toolChoice="auto",
    stopWhen: stepCountIs(maxSteps) || done tool called)
→ [each step: processMessages() → captcha check → tool execution]
→ ensureDone() forces done tool if agent didn't call it
```

**Default max steps: 20**
**Temperature: 1 (always)**
**`done` tool is auto-injected**, not user-created.

**Two modes:**
- `dom` (default): uses accessibility tree first (`ariaTree`), screenshot secondary
- `hybrid`: screenshot primary, ariaTree secondary; coordinate tools available

### Tool Registry (17 + 1 injected)

```
act, ariaTree, click (hybrid), clickAndHold (hybrid), dragAndDrop (hybrid),
extract, fillForm (dom), fillFormVision (hybrid), goto, keys, navback,
screenshot, scroll, type (hybrid), think, wait, search (optional, Exa/Brave),
done (auto-injected)
```

**Timeout handling:** All I/O tools (except `think` and `wait`) wrapped with configurable timeout. On timeout: returns `{success: false, error: "TimeoutError: ..."}` to the LLM instead of throwing. Each tool has a timeout hint telling the model what to try instead.

### Context Assembly (AXTree-to-Token Pipeline)

The core data pipeline (`capture.ts`):

1. **Scoped fast-path** — If `focusSelector` provided, resolve across iframe hops and build data for only the owning frame (early return)
2. **Build session DOM indexes** — `DOM.getDocument` once per unique CDP session; hydrate `SessionDomIndex` with absolute-XPath-by-backendNodeId, tag, scrollability maps
3. **Collect per-frame maps** — For each frame: slice shared session index, build `EncodedId` (`frameOrdinal-backendNodeId`), fetch AXTree to produce outline and URL map
4. **Compute frame prefixes** — BFS walk; each child frame's prefix = absolute XPath of its iframe host element in parent; OOPIFs inherit parent prefix
5. **Merge** — prefix all per-frame XPaths, stitch outlines via `injectSubtrees()`

Result: `{combinedTree: string, combinedXpathMap, combinedUrlMap, perFrame}`. AXTree typically reduces data 80-90% vs raw DOM.

**EncodedId** (`frameOrdinal-backendNodeId`) solves CDP's non-global `backendNodeId` across iframes.

### Caching

**Cache key**: SHA-256 of `JSON.stringify({instruction, url, variableKeys})`. Variable values excluded from key — same instruction with different variable values hits same cache entry. Cache replay: replay each cached action; auto-refreshes if selectors shift.

`observe()` returns deterministic `Action` objects. Subsequent `act(action)` executes with zero LLM calls. Server-side cache hits (Browserbase only) return `cacheStatus: "HIT"` and consume zero tokens.

### System Prompt (verbatim XML structure)

```xml
<system>
  <identity>You are a web automation assistant...</identity>
  <customInstructions><![CDATA[{userInstructions}]]></customInstructions>
  <task>
    <goal><![CDATA[{executionInstruction}]]></goal>
    <date display="local" iso="{isoDate}">{localeDate}</date>
  </task>
  <page><startingUrl>{url}</startingUrl></page>
  <mindset>
    <note>Be very intentional about your action...</note>
    <importantNote>If something fails to meet a single condition, move on...</importantNote>
  </mindset>
  <page_understanding_protocol><!-- mode-specific: dom vs hybrid --></page_understanding_protocol>
  <tools><!-- all mode-appropriate tools described --></tools>
  <strategy>
    <item>CRITICAL: Use extract ONLY when task explicitly requires structured data output</item>
    <item>Keep actions atomic and verify outcomes before proceeding</item>
  </strategy>
  <variables>
    <note>Use %variableName% syntax to substitute variable values</note>
  </variables>
  <completion><note>When complete, explain relevant information found</note></completion>
</system>
```

Variables use `%name%` syntax and are **never shared with LLM providers** — sensitive data separation by design.

### Self-Healing

1. Action throws error
2. Take fresh hybrid snapshot
3. Re-run LLM inference with same instruction
4. Get new selector from LLM
5. Retry action with new selector, original method/args

Fallback for total failure: full agent that reviews what happened and reassesses goal.

---

## 3. Dust

### The Primitive: Synthetic Filesystem

Five Unix commands over enterprise data: `list` (ls), `find`, `cat` (with `offset`, `limit`, `grep`), `search` (semantic), `locate_in_tree`. Maps Slack channels → directories/files, Notion workspaces → root folders, GitHub repos → natural directory structure, spreadsheets → folder of table files.

**Dual-nature nodes**: Notion pages are both readable (`cat`) and have children (`list`). Resolved via metadata flag.

**Why not just RAG**: navigation reveals structure + adjacent relationships; search finds specific content within structure. Both together.

### Multi-Agent Orchestration (Deep Dive)

Three-agent hierarchy:
- `@deep-dive` (Coordinator): classifies complexity, decomposes, orchestrates up to **6 concurrent sub-agents** via parallel tool calling
- `@dust-planning` (Strategic Reviewer): validates approach WITHOUT data access, maximum reasoning effort
- `@dust-task` (Worker, up to 6 concurrent): each gets focused self-contained prompt, own fresh context window, full data tool access; produces information-dense reports

Duration: 10-30+ minutes, hundreds of tool calls.

**Max steps per turn: 10** (default). `DEFAULT_MCP_REQUEST_TIMEOUT_MS = 180,000` (agent tools: 300,000 ms). Max 128 output items per action. Batch fetching in groups of 32.

### MCP Tool System

- 60+ internal tools (stable IDs, auto-enabled or manual)
- 30+ remote MCP servers (HTTP/SSE, OAuth + bearer auth)
- Client-side MCP (browser extension, Redis transport)

**Tool approval (argument-level)**: low-stake → auto; medium-stake → block on user approval for specific args; high-stake → explicit approval; never-ask → system-internal.

**Tool name conflict prevention**: `tryListMCPTools()` prepends space names to tool names.

### Temporal Infrastructure

10M+ Activities/day on Temporal Cloud. Each incoming event (Slack message, Notion edit, PR) triggers a Temporal Workflow. `continueAsNew` for long-running operations. Horizontal scaling = more Workers.

---

## 4. OpenClaw

### The Primitive: Agent Gateway

Single `Gateway` process (`src/gateway/server.ts`), Node.js 22+, WebSocket at `ws://127.0.0.1:18789`.

### 7-Stage ReAct Loop

```
Phase 1 — Ingestion:       platform adapter parses text/media/metadata
Phase 2 — Access Control:  allowlist/pairing checks (<10ms)
Phase 3 — Context Assembly: session load, system prompt build, memory search (<100ms)
Phase 4 — Model Invocation: stream to LLM (first token: 200-500ms)
Phase 5 — Tool Execution:   intercept + execute (bash 100ms, browser 1-3s)
Phase 6 — Response Delivery: format per platform, send via adapter
Phase 7 — Persistence:     save session state to disk
```

22+ channel adapters: WhatsApp, Telegram, Discord, Slack, iMessage, Signal, Matrix, etc.

### System Prompt Architecture

Composable from layers:
- Workspace config files: `AGENTS.md` (core), `SOUL.md` (personality), `TOOLS.md` (conventions)
- Dynamic per-turn: session history, skill content (`SKILL.md`), memory search results
- Auto-generated: built-in tools, plugin tools via `api.registerTool()`

Behavior changes through file edits, no code changes needed.

### Memory

SQLite with FTS5 + vector embeddings at `~/.openclaw/memory/<agentId>.sqlite`. Hybrid search: vector similarity + BM25 keyword matching. Auto-reindexing via file watcher with **1.5s debounce**. Embedding selection: local > OpenAI > Gemini (automatic).

**No hard size limit** — agent manages memory explicitly, auditable.

**`MEMORY.md`** for curated facts (main sessions only). Daily notes at `memory/YYYY-MM-DD.md`.

### Session Management

Append-only event logs supporting branching. **Compaction:** automatic summarization of older turns + optional "memory flush" before compaction promotes durable info to memory files.

**Session types** as security boundaries:
- Direct messages → `main` session (full host access)
- DM sessions → sandboxed by default
- Group sessions → sandboxed by default

### Multi-Agent / ACP Protocol

ACP enables OpenClaw to orchestrate external coding harnesses (Claude Code, Codex, Cursor, Copilot, Gemini CLI, etc.).

Session ID: `agent:<agentId>:acp:<uuid>`.

Permission model for non-interactive ACP sessions: `permissionMode`: `approve-all | approve-reads | deny-all`. `nonInteractivePermissions`: `fail` (default, aborts) | `deny` (silently denies).

**Federation** with Hermes Agent via Open Gateway Protocol (OGP) — cryptographically-verified messages across framework boundaries.

**Tool policy precedence** (7 layers):
`Tool Profile → Provider Profile → Global Policy → Provider Policy → Agent Policy → Group Policy → Sandbox Policy`

---

## 5. Hermes Agent

### The Primitive: Bounded Memory + Closed Learning Loop

**Four-layer memory:**
1. **Prompt Memory** (`MEMORY.md` + `USER.md`): always-on; **hard limit 3,575 chars total** (agent: 2,200, user: 2,575 — correction: 2,200 + 1,375 = 3,575). Tight constraint creates selective pressure.
2. **Session Search**: SQLite FTS5 + WAL mode; uses **Gemini Flash** to summarize relevant past sessions before injecting
3. **Skills** (procedural memory): `~/.hermes/skills/` as `agentskills.io` standard Markdown. Progressive disclosure: only names+summaries loaded by default; full content appears on demand. 48 built-in tools across 40 toolsets.
4. **Honcho** (optional): passive user modeling across 12 identity layers.

**Skill creation triggers**: 5+ tool calls in a workflow; recovery from error; user correction; non-obvious workflow that worked.

**Skill self-improvement**: `skill_manage` tool with `patch | edit | delete` actions; default is `patch` (targeted, more reliable than full rewrites).

**Compression as Consolidation**: when approaching context limits, auxiliary model extracts retention-worthy content into 3,575-char window, summarizing middle turns. "Lineage" reference chain connects summarized turns to original SQLite records.

**Memory nudge**: every ~15 turns, agent receives internal system prompt asking it to assess and consolidate recent activity.

### Agent Loop Turn Lifecycle

1. Generate task ID per message
2. Load system prompt from memory + skill index + context files
3. **Preflight compression check** — validate history against context limits BEFORE API call
4. Model execution + tool call interception
5. Synchronous tool execution loop
6. SQLite persistence
7. Response routing through gateway

### RL Training Pipeline

Three components:
- **Atropos** (trajectory API, port 8000): rollout groups, advantage values
- **Tinker** (training service, port 8001): LoRA adapter training, Adam lr=4e-5, beta1=0.9, beta2=0.95; LoRA rank=32
- **Environments**: Python `BaseEnv` subclasses, 11 tool-call parsers

Constants: tokenizer `Qwen/Qwen3-8B`, max token length 8192, total training steps 2500, group_size=16, batch_size=128, max parallel workers 2048. Process stagger: API +5s, trainer +30s, env +120s.

---

## 6. Decagon

### The Primitive: AOPs (Executable Procedures)

AOPs combine NL instructions with code-based logic. Compile into "structured logic" for execution. CX teams write NL; engineers control underlying systems. Data requirements, decision points, success criteria, escalation triggers all explicit.

### Multi-Model Constellation (8 specialized models)

| Role | Function |
|---|---|
| Intent Interpreter | Classify intent, select AOP |
| Workflow Executor | Execute AOP step-by-step |
| Hallucination Detector | Evaluate response accuracy in context |
| Escalation Router | Decide human handoff |
| Bad Actor Detector | Adversarial/manipulation detection |
| Brand Voice Guardian | Tone and style enforcement |
| Response Supervisor | Final review: accurate + brand-safe |
| Watchtower Monitor | Post-conversation full arc review |

Fine-tuning: SFT first (behavioral foundation) → RL on top (GRPO/GSPO/DPO, sharpen decision boundaries). Result: smaller fine-tuned models outperform larger general-purpose on specific tasks.

### Three-Phase Guardrails

- **Pre-deployment**: regression testing, historical replay, unit tests for tone, integration tests
- **During conversation**: real-time fine-tuned models (bad actor, escalation, brand voice, response supervision)
- **Post-conversation (Watchtower)**: reviews EVERY conversation against custom criteria; analyzes arc, not keywords

**Qualitative guardrails** for sensitive actions: "user appears very angry," "has asked for refund three times" — fuzzy conditions alongside explicit ones.

---

## 7. Simular / Agent-S

### The Primitive: Modular Agent-Computer Interface

**Agent S2 key decisions:**
- Proactive Hierarchical Planning (PHP): updates plan after EACH subtask, not just after errors
- Mixture of Grounding (MoG): routes to visual grounding expert (button UIs), textual grounding expert (text content), structural grounding expert (spreadsheets)
- Operates solely on raw screenshots — no accessibility tree dependency
- Foundation models for high-level planning; specialist modules for precise execution

**Agent S3:**
- Removed manager-worker hierarchy → +13% single-agent performance
- Behavior Best-of-N (bBoN): generate N parallel rollouts → judge selects best
  - Stage 1: convert runs to fact statements (noise reduction)
  - Stage 2: concatenate into behavior narratives
  - Stage 3: comparator evaluates; judge alignment 92.8%
- Native coding agent: GUI workflow → Python/shell deterministic code
- OSWorld benchmark: 69.9% (bBoN) vs 72% human baseline

---

## 8. Cross-Cutting Patterns Across All Systems

### Pattern 1: Memory Constraints Create Quality

| System | Memory Constraint | Mechanism |
|---|---|---|
| Hermes | Hard 3,575-char cap | Forced consolidation via periodic nudge |
| Claude Agent SDK | `getContextUsage()` per-category | SDK can gate on token budget |
| Dust | `cat` with `offset/limit/grep` params | Deliberate chunk-by-chunk access |
| OpenClaw | No hard limit | Agent curates explicitly, auditable |
| Decagon | Historical replay as training | Constraint is what fits in fine-tuning batch |

Unconstrained context is noise. Bounded + curated memory is signal.

### Pattern 2: Every Production Agent Has a Pre-Flight Compression Check

Both Hermes (explicit preflight before API call) and Claude Agent SDK (`excludeDynamicSections` + `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` for fleet-wide caching) validate context budget before sending. Verso needs this as a first-class primitive.

### Pattern 3: Bidirectional Control Over a Single Channel

Claude Agent SDK routes 13 RPC subtypes (hooks, permissions, MCP, session control) over the same JSONL stream as messages. OpenClaw routes tool execution, access control, session state over the same WebSocket gateway. The single channel simplifies multiplexing: one reader demuxes everything.

### Pattern 4: Tool Permission Is a First-Class Policy Layer, Not an Afterthought

Claude SDK: 6 permission modes + `can_use_tool` callback + 7-tier policy origins + 5 update destinations + per-tool `always_allow|ask|deny`. Dust: 4-tier approval (auto → user approval → explicit → never). OpenClaw: 7-layer tool policy stack. The pattern: permissions compose through ordered layers with known precedence.

### Pattern 5: MCP Is Winning as the Tool Protocol

Claude Agent SDK has 5 MCP transports including a centralized Anthropic-hosted proxy. Dust has 90+ MCP tools across 3 server types. OpenClaw has a full MCP server exposed to ACP agents. This is not a "nice to have" — it's the connective tissue.

### Pattern 6: Compute Scaling Beats Model Scaling

| System | Strategy | Result |
|---|---|---|
| Agent S3 (bBoN) | N parallel rollouts + judge | 62.6% → 69.9% on OSWorld |
| Dust Deep Dive | 6 concurrent sub-agents | 10-30 min investigations |
| Decagon | 8 specialized small models | Lower latency than 1 large model |
| Stagehand | observe-then-act caching | Zero LLM calls on cache hit |

### Pattern 7: Typed Error Systems, Not Generic Exceptions

Stagehand defines 13 typed error classes (`StagehandElementNotFoundError`, `LLMResponseError`, etc.). Hermes and OpenClaw use typed tool result shapes. Claude SDK has `CLINotFoundError`, `SDKJSONDecodeError`, `ProcessError`. Verso should define a typed error hierarchy per subsystem.

### Pattern 8: Session Fork / Branch Is Increasingly Expected

Claude Agent SDK has `forkSession()` (UUID-remap + parent-chain rewrite), Hermes has append-only event logs supporting branching, OpenClaw has append-only session logs. The pattern: sessions are immutable-append; fork = fresh ID + remapped parent chain.

---

## Verso Implications

### Copy

1. **Control protocol pattern**: bidirectional RPC over a single stream (JSONL or similar), request/response correlated by `request_id`, with explicit cancellation semantics (`cancel_request` type, re-raise without responding). Simple, composable, no extra sockets.

2. **In-process tool routing via the same channel**: tools defined as async functions in user code, invoked by the framework over the control channel. No subprocess per tool. Zero-IPC custom tools. The `mcp_message` pattern is the implementation recipe.

3. **Hook system with `updatedInput`/`updatedToolOutput`**: pre-tool hooks that can rewrite args AND post-tool hooks that can rewrite results before the model sees them. This is the correct interception model. Four-value permission decision: `allow | deny | ask | defer` (defer = pass-through to next hook; deny > ask > allow > defer precedence).

4. **Async hooks**: a hook can return `{async: true}` to run its side-effect without blocking the turn. Verso needs this for non-blocking observability (logging, metrics, alerts).

5. **5+5+kill subprocess shutdown with session-flush grace**: if Verso ever manages sub-processes, `stdin.close() → wait 5s → SIGTERM → wait 5s → SIGKILL`. The 5s grace is for the subprocess to flush its session file. Dropping this causes intermittent last-message loss (issue #625 was a real production bug).

6. **Shielded final flush**: `CancelScope(shield=True)` for any batcher's `close()` — ensures last batch reaches the store under Ctrl+C. Copy this pattern for Verso's session persistence.

7. **Write-lock for TOCTOU around channel close**: acquire the same lock for both `write()` and `close()`. Set `_ready=False` inside the lock, not before acquiring it.

8. **`transcript_mirror` side-channel for pluggable session stores**: persistence should not pollute the message stream. Peel persistence frames off before forwarding to user code.

9. **3,575-char bounded memory with forced consolidation (Hermes)**: Verso's memory subsystem should support a configurable hard cap that triggers automated consolidation, not just soft warnings.

10. **AXTree-over-raw-DOM (Stagehand)**: if Verso needs web context, the AXTree pipeline is the right approach (80-90% token reduction, semantic stability).

11. **Behavior Best-of-N (Agent S3)**: Verso's eval harness should support parallel rollout generation + judge selection as a first-class workflow.

12. **`excludeDynamicSections` / `SYSTEM_PROMPT_DYNAMIC_BOUNDARY`**: mark the boundary between static (cacheable) and dynamic (per-request) system prompt content. Verso's prompt assembly should support this split explicitly.

13. **Per-category context usage introspection**: `getContextUsage()` returning `{system_prompt, tools, messages, mcp_tools, memory_files}` token counts. Verso should expose this so orchestration code can make informed compaction decisions.

14. **Settings cascade with provenance**: 5+ tiers (local < project < user < session < policy), each key traceable to its origin. `applyFlagSettings()` for mid-session overrides without restart.

### Avoid

1. **Subprocess-delegated loop for a general framework**: Anthropic's design works because they own both the SDK and the CLI binary. Verso is a general framework — the loop must run in framework code, not inside a binary that users can't inspect or extend.

2. **Anthropic-only model routing**: the Claude SDK's biggest limitation. Verso must abstract over providers from day one. The 7 API provider types in `AccountInfo` show what's actually needed: first-party, Bedrock, Vertex, Azure Foundry, custom gateway.

3. **Implicit async tool execution without timeout hints**: Stagehand's per-tool timeout hints to the model ("the page may be too large") are valuable. Don't just timeout silently — tell the model what to do differently.

4. **Manual JSONRPC routing for in-process MCP** (Python SDK's `_handle_sdk_mcp_request`): this exists only because the Python MCP SDK lacks a Transport abstraction. Verso should implement the Transport abstraction correctly from the start, so in-process and out-of-process MCP servers are plugged in identically.

5. **Manager-worker hierarchy for general agent orchestration (Agent S3's lesson)**: Agent S3 removed the hierarchical manager-worker structure and gained 13% performance. Flat multi-agent with good coordination beats nested hierarchies for most tasks.

6. **Unconstrained memory**: every production system with good memory has a constraint (Hermes: 3,575 chars, Dust: `cat` pagination, Claude SDK: `getContextUsage` + budget). Verso should not ship a memory module without a configurable budget policy.

7. **Single monolithic model for all agent roles (Decagon's lesson)**: specialized fine-tuned small models outperform one large general model on specific tasks. Verso's model routing should support per-task model dispatch.

### Verso Could Improve By

1. **First-class eval loop integrated with session fork**: `forkSession(at_message_N)` + `bBoN(N=10)` as a built-in workflow. Verso has thesis alignment here — evals as first-class citizens.

2. **Transparent context budget dashboard**: expose `getContextUsage()` equivalent as a real-time annotation on every turn, not just on explicit query. Budget consumed by category → framework can auto-compact the fattest category.

3. **Skill system as first-class primitive**: Hermes + OpenClaw both converge on `agentskills.io` Markdown skill files. Verso should adopt this as the skill interchange format, enabling cross-framework portability.

4. **Unified permission layer with policy provenance**: Claude SDK's 7-origin policy stack is sophisticated but Anthropic-specific. Verso could generalize it: a composable policy middleware where each layer is a function `(tool_call, context) → allow|deny|ask|defer`, chained in priority order, with provenance tracking.

5. **Workflow-to-deterministic-code flywheel (Agent S3 pattern)**: when Verso completes a successful multi-step agentic task, offer to emit the workflow as deterministic code. AI exploration → deterministic automation. This is the product flywheel Verso's thesis describes.
