# CLAUDE AGENT SDK — Raw Extraction (Verso validation)

Source read: `/Users/seventyleven/Desktop/researchfms/teardowns/CLAUDE_AGENT_SDK.md` (2465 lines, 154 KB).
Package: `@anthropic-ai/claude-agent-sdk` (npm), `claude-agent-sdk` (PyPI). SDK v0.1.81; bundled CLI v2.1.141–2.1.158; min CLI `MINIMUM_CLAUDE_CODE_VERSION = "2.0.0"`.

This is Anthropic's OWN agent harness. The single most authoritative "how Anthropic says to build agents" — but with a TWIST that reframes the whole comparison to Verso (see §0).

---

## §0 The defining architecture — the loop is NOT in the SDK (KNOWN)

> "Unlike every other SDK in this batch, the Claude Agent SDK does not implement an agent loop in user code." (teardown summary, line 3)

The SDK is a thin client (~10.5k Python LOC) that **spawns the `claude` CLI binary as a subprocess** and speaks a JSONL **control protocol** over stdin/stdout. The actual ReAct loop — tool calling, planning, sub-agents, compaction, permission gating — runs **inside the CLI** (a Bun-bundled TypeScript daemon, ~50 MB minified). The CLI is invoked:

```
claude --output-format stream-json --verbose --input-format stream-json \
  --system-prompt ... --tools ... --mcp-config ... --max-turns N ...
```

> "the SDK gets free updates to context management, planning, sub-agents, compaction without releasing a new package." (line 547)

**Verso relevance:** This is the OPPOSITE of Verso's thesis. Verso's wedge is owning the <200-line loop in-process so it is inspectable/eval-able/forkable. Anthropic's SDK deliberately makes the loop a BLACK BOX (the teardown: "Roughly 80% of the agent behavior lives inside the Bun-compiled `claude` binary"). Verso is the LEANER and more transparent design for anyone who wants to own/eval the loop. The Claude SDK is leaner only in the sense of "don't reimplement what Anthropic already built." These are different products; the validation value is in the PRIMITIVE shapes Anthropic chose, not the delegation architecture.

---

## §1 Permission system (KNOWN) — strongest Verso validation

**4-valued permission decision — IDENTICAL to Verso's PermissionDecision:**
`PreToolUse` hooks return `permissionDecision: "allow" | "deny" | "ask" | "defer"` plus `permissionDecisionReason` (line 246, §R2.5 line 779, §C21). Verso ships exactly this 4-valued enum (allow/deny/ask/defer). **This is direct independent corroboration of Verso's permission model by Anthropic.**

**`can_use_tool` callback** (CLI → SDK), signature:
```python
CanUseTool = Callable[[str, dict[str, Any], ToolPermissionContext],
                      Awaitable[PermissionResult]]  # Allow | Deny
```
Returning `PermissionResultAllow(updated_input=...)` lets the callback **rewrite the tool args before execution** (line 275). Verso has this via Hooks(pre_tool) + PermissionDecision + arg rewrite path.

**Six permission MODES** (`types.py:24-26`): `default | acceptEdits | plan | bypassPermissions | dontAsk | auto`.
- `default` — prompt per non-allowlisted call.
- `plan` — model reasons but cannot execute tools.
- `bypassPermissions` — allow everything (requires `allowDangerouslySkipPermissions`).
- `dontAsk` — deny anything not pre-approved by allowlist/rules.
- `auto` — **a classifier MODEL on the CLI side decides per call** ("A model classifier approves or denies each tool call", `query.py:60-61`).

**Per-tool MCP policy** (§C16): `'always_allow' | 'always_ask' | 'always_deny'`. Default `always_ask` for unknown tools; `always_allow` for read-only built-ins (ls/cat/head/tail).

**5 permission-update destinations / settings tiers** (§C8): session / user / project / local / managed(admin). Ephemeral grant pattern: `await query.applyFlagSettings({permissions: {allow: [...]}})` (session tier).

**Managed-settings restrictive-only filter** (§C9): admin `managedSettings` can only NARROW, never widen, runtime rules — "defense in depth at the API level. Embedding apps cannot bypass enterprise lockdowns by passing wider rules."

---

## §2 Hook system (KNOWN) — Verso has the model; Anthropic has far more event types

**Hook output shape** (`types.py:493-559`) — maps closely to Verso's Hooks:
- `PreToolUse` → `permissionDecision` (4-valued) + `permissionDecisionReason` + `updatedInput` (rewrite args) + `additionalContext` (inject text into model).
- `PostToolUse` → `updatedToolOutput` to **rewrite the tool's response before the model sees it**. CRITICAL constraint: for built-in tools the rewritten output "must match the tool's exact output schema (e.g. `{stdout, stderr, interrupted}` for Bash); a mismatched shape is rejected and the original output is kept" (line 796-799).
- `UserPromptSubmit / SessionStart / Notification / SubagentStart` → `additionalContext` to inject text (custom prompt enrichment).
- Common control fields: `continue_` (False = stop loop), `suppressOutput`, `stopReason`, `decision:"block"`, `systemMessage`, `reason` (feedback to Claude).

**Async hooks** (`AsyncHookJSONOutput`, line 816): `{async_: True, asyncTimeout: int(ms)}` — "the CLI does NOT wait for the hook's result before proceeding. Useful for slow side-effects like sending alerts or persisting to remote logs without blocking the conversation." Verso does NOT have a fire-and-forget async-hook variant.

**Hook event count grew across versions:** Python SDK = **10 events**; TS SDK (canonical) = **29 events** (`HOOK_EVENTS` const, `sdk.d.ts:738`):
`PreToolUse, PostToolUse, PostToolUseFailure, PostToolBatch, Notification, UserPromptSubmit, UserPromptExpansion, SessionStart, SessionEnd, Stop, StopFailure, SubagentStart, SubagentStop, PreCompact, PostCompact, PermissionRequest, PermissionDenied, Setup, TeammateIdle, TaskCreated, TaskCompleted, Elicitation, ElicitationResult, ConfigChange, WorktreeCreate, WorktreeRemove, InstructionsLoaded, CwdChanged, FileChanged`.

Verso's hook surface (pre/post_model, pre/post_tool, on_stop, ask, should_continue) covers the load-bearing subset. The 29-event catalog is product-surface for an IDE/CLI product (worktrees, teammates, elicitation, config-change) — NOT lean core. AVOID copying wholesale.

**`PreCompact`/`PostCompact` hooks** — fire around context compaction. Verso deliberately does NOT do LLM-summarization-compaction-by-default (NON-GOAL), so these have no analogue. A `PreCompact` hook is a leak point that exists only because the CLI compacts.

---

## §3 Sub-agents (Task tool) (KNOWN) — design Verso can validate against, NOT a graph

`AgentDefinition` dataclass (`types.py:81-100`):
```python
@dataclass
class AgentDefinition:
    description: str
    prompt: str
    tools: list[str] | None = None
    disallowedTools: list[str] | None = None
    model: str | None = None       # "sonnet"|"opus"|"haiku"|"inherit"
    skills: list[str] | None = None
    memory: Literal["user","project","local"] | None = None
    mcpServers: list[str | dict] | None = None
    initialPrompt: str | None = None
    maxTurns: int | None = None
    background: bool | None = None
    effort: Literal["low","medium","high","xhigh","max"] | int | None = None
    permissionMode: PermissionMode | None = None
```

**Mechanism:** sub-agents are NOT invoked directly. Passed in `options.agents = {name: AgentDefinition}`, registered via `initialize`, and **the main Claude invokes them by calling the `Task` built-in tool with the sub-agent's name** (line 352). The CLI spawns the sub-agent **in-process (not a new subprocess)** with its own context window, model, tools, MCP servers, permission mode. **Sub-agents always return to the parent — "There is no explicit 'agent A hands control to agent B' mechanism"** (line 473). NO handoff in the Swarm/OpenAI sense.

> Validation for Verso's "no graph" thesis: even Anthropic's OWN multi-agent is just "a tool that spawns a bounded child agent and returns" — NOT a node graph, NOT an orchestrator primitive. A sub-agent is "agent-as-tool with its own context." This strongly supports Verso's counter-position to LangGraph/CrewAI.

**Sub-agent attribution through hooks** (`_SubagentContextMixin`, lines 288-304): tool-lifecycle hooks carry `agent_id` + `agent_type`. Comment (line 294): "When multiple sub-agents run in parallel their tool-lifecycle hooks interleave over the same control channel — this is the only reliable way to attribute each one to the correct sub-agent." If 3 parallel Task agents all call Bash you see 3 interleaved PreToolUse events; `agent_id` is the disambiguator.

**Subagent memory scopes** (§C18): `memory: 'user'|'project'|'local'` → `~/.claude/agent-memory/<agentType>/`, `.claude/agent-memory/<agentType>/`, `.claude/agent-memory-local/<agentType>/`.

---

## §4 Tools (KNOWN)

Three tool sources (all configured via CLI flags):
1. **~25 built-in tools** (live in CLI): `Bash, Read, Write, Edit, MultiEdit, Glob, Grep, Task, WebFetch, WebSearch, NotebookRead, NotebookEdit, TodoRead, TodoWrite, Skill, ...`. Selected via `options.tools = [...]` or `{type:"preset", preset:"claude_code"}` (everything); empty list disables all.
2. **External MCP servers** (stdio/sse/http) via `--mcp-config <json>`.
3. **SDK MCP servers (in-process)** — the novel bit. `@tool` decorator:
```python
@tool("greet", "Greet a user", {"name": str})
async def greet(args):
    return {"content": [{"type":"text","text": f"Hello, {args['name']}!"}]}
server = create_sdk_mcp_server(name="my_server", version="1.0.0", tools=[greet])
```
The in-process server is wrapped in a real `mcp.server.Server`; when the CLI calls a tool it emits an `mcp_message` control_request the SDK routes to `Server.handle_jsonrpc()` — **zero IPC, runs in the same event loop** (§R2.3, §R3.3).

**Tool schema generation** (`__init__.py:234-303`): custom `_python_type_to_json_schema` handles `Annotated[type, "description"]`, `NotRequired`/`Required`/`ReadOnly`, `Optional`, `Union`, `list[T]`, `dict`, TypedDict; falls back to `"string"` for unknown. "more sophisticated than Swarm's mapping but less so than Agents SDK's full Pydantic schema" (line 460). Verso's `@tool` (docstring→schema) is the same idea — note Anthropic's SDK requires you to pass a schema dict, Verso derives it from the docstring (Verso leaner).

**`anthropic/maxResultSizeChars`** `_meta` key (line 462) — the CLI's tool-result spill threshold for layer-2 storage (`toolResultStorage.ts maybePersistLargeToolResult`). Large tool results are persisted out-of-band rather than dumped into context. Verso prune() masks old tool outputs; this is a related but different mechanism (spill at write-time vs. mask-at-prune-time).

---

## §5 Control protocol — the SDK's central abstraction (KNOWN)

Synchronous RPC over an async JSONL stream. `request_id = f"req_{counter}_{os.urandom(4).hex()}"` (per-Query counter + 4 random bytes to survive reconnects). Default timeout 60s; `initialize` uses `max(CLAUDE_CODE_STREAM_CLOSE_TIMEOUT/1000, 60.0)`.

**13 subtypes** (Round 1 undercounted as 6). SDK→CLI: `initialize, interrupt, set_permission_mode, set_model, mcp_status, get_context_usage, rewind_files, mcp_reconnect, mcp_toggle, stop_task`. CLI→SDK: `can_use_tool, hook_callback, mcp_message`.

**Cancellation** (`control_cancel_request`): on cancel, the handler re-raises the cancelled exc **WITHOUT writing a response** — "if you write a response after cancellation, the CLI's correlation map has already dropped the request_id, and you'd get a stale-response error" (line 688). Good idempotency/concurrency detail.

**Field-name rewriting** (`_convert_hook_output_for_cli`): only `async_`→`async`, `continue_`→`continue` (Python keywords → JS-conventional wire names). One-directional Python→CLI.

Verso has no control protocol because it owns the loop in-process — this whole abstraction is a CONSEQUENCE of the subprocess-delegation choice, not a primitive Verso lacks.

---

## §6 Session / durable / fork / checkpoint (KNOWN) — overlaps Verso's durable seam

CLI persists every session as JSONL at `~/.claude/projects/<sanitized-cwd-hash>/<session-id>.jsonl`.

**Resume:** `options.resume=session_id` → `--resume <id>`. **Fork:** `options.fork_session=True` → new session ID, history copied (`--fork-session`). §C19 `forkSession(sessionId)` → `{newSessionId}` for what-if exploration / A/B / pre-destructive-command recovery. **Verso already has history()/fork() time-travel.** Independent validation that fork-by-copy-with-new-id is the right shape.

**Session fork mechanic** (§R3.11): read source JSONL, **remap every UUID** (new session id + new message UUIDs preserving parent links), write `{forked_session_id}.jsonl` (compact JSON, no trailing newline per line). Implementation detail worth noting if Verso ever needs JSONL-transcript fork.

**Pluggable SessionStore** (`session_store.py`, 1900+ LOC): abstract base with `append(key,entries)`, `load(key)`, `list_sessions(project_key)`, `delete(key)`, `rename`, `tag`. `--session-mirror` flag makes the CLI emit `transcript_mirror` stdout frames containing every JSONL entry it would write; SDK forwards to S3/Redis/Postgres. On resume, `materialize_resume_session()` reads from store → temp `CLAUDE_CONFIG_DIR` → CLI resumes from there. **Conformance test harness** `testing/session_store_conformance.py` (327 lines) — a single suite all SessionStore impls must pass. Verso ships SqliteCheckpointStore; the **conformance-suite-as-contract** idea is a nice pattern (but Verso has one store; not needed yet).

**File checkpointing** (`enable_file_checkpointing=True` → `CLAUDE_CODE_ENABLE_SDK_FILE_CHECKPOINTING=true`): `rewind_files(user_message_id)` rewinds tracked FILES on disk to their state at a specific user message. Verso's checkpoint resumes the AGENT; this rewinds the FILESYSTEM. Different scope — likely overkill for Verso core (a coding-product feature, not an agent-loop primitive).

**6 EXIT_REASONS** (`sdk.d.ts:555`): `clear, resume, logout, prompt_input_exit, other, bypass_permissions_disabled`. The last forcibly ends a session if an admin disables bypass mode mid-session. Product/policy surface, not core.

---

## §7 Streaming (KNOWN)

Wire = JSONL over stdin/stdout (`stream-json`). NO SSE/WebSocket at the SDK boundary (CLI talks SSE to Anthropic API internally, invisible to SDK). User-facing: `async for message in query(...)`, each a parsed dataclass. Message types: `AssistantMessage, UserMessage, SystemMessage, ResultMessage, TaskStartedMessage, TaskProgressMessage, TaskNotificationMessage, HookEventMessage, MirrorErrorMessage, StreamEvent`.

`include_partial_messages=True` → `StreamEvent` token-by-token deltas (reconstruct stream client-side). `include_hook_events=True` → observe every hook event in the stream without a callback. Verso already ships typed true-delta streaming events (message/reasoning/tool.start/tool.result/done) + SSE — Verso's streaming is at least as good and SSE-native.

---

## §8 Context usage accounting (KNOWN) — candidate steal

`get_context_usage()` / `getContextUsage()` (§C20, `sdk.d.ts:2146`):
> "Get a breakdown of current context window usage by category (system prompt, tools, messages, MCP tools, memory files, etc.). @returns Context usage breakdown including token counts per category and total usage"

Per-category token accounting: `system_prompt`, `tools` (schema overhead), `messages` (turn history), `mcp_tools`, plus memory files. Verso has `inspect()` (byte-for-byte) and `max_context_tokens`; a **per-category token breakdown** (how many tokens are spent on tool schemas vs history vs instructions) is a small, additive, byte-identical-when-unused diagnostic Verso could expose on ContextBundle.inspect(). On-thesis (context-engineering is first-class). See structured `steal`.

---

## §9 Models / providers (KNOWN)

**Anthropic-only.** No provider abstraction in the SDK. `model`, `fallback_model`, `betas: ["context-1m-2025-08-07"]` (1M context, Sonnet 4/4.5). Account `apiProvider` (§C17, 7 values): `firstParty, bedrock, vertex, foundry, anthropicAws, mantle, gateway`. **Verso is MORE flexible here** — anthropic/openai/google + ANY OpenAI-compatible endpoint via base_url, plus FailoverModel/RetryPolicy. Verso wins on provider breadth; this is a non-goal-aligned divergence.

`fallback_model` ≈ Verso's FailoverModel. `effort: low/medium/high/xhigh/max` thinking-effort knob (§C11). Verso has per-call model swap + override; effort tiers are a thin add-on (model-specific).

---

## §10 Subprocess lifecycle (KNOWN) — only relevant if delegating

5+5+kill shutdown: close stdin → wait 5s graceful → SIGTERM → wait 5s → SIGKILL. The 5s grace is empirical: "the subprocess needs time to flush its session file after receiving EOF on stdin... SIGTERM-ing too early (issue #625) truncates that write" — you lose the last assistant message otherwise. Module-level `atexit` + signal handler tracks `_ACTIVE_CHILDREN` to avoid zombies. Speculative JSON parse: accumulate JSONL chunks until `json.loads` succeeds, 1 MB buffer cap (`_DEFAULT_MAX_BUFFER_SIZE`), drop non-`{`-prefixed log lines only when buffer empty (#347 fix). All of this is subprocess-bridge plumbing irrelevant to Verso's in-process loop.

---

## §11 MCP posture (KNOWN)

First-class, 5 transports: stdio, sse, http, **sdk (in-process)**, **claudeai-proxy** (Anthropic's hosted MCP proxy at `https://mcp-proxy.anthropic.com` — Anthropic as OAuth aggregator for Linear/Notion/GitHub). `strict_mcp_config=True` ignores all MCP sources except `options.mcp_servers`. Verso is deliberately NOT MCP-first (native @tool is THE path; MCP is opt-in adapter) — a NON-GOAL. Anthropic being MCP-first is a product-positioning choice (marketplace play), not a leanness argument.

---

## §12 Bottom line for Verso

WHERE THEY AGREE (strongest validation):
- **4-valued permission decision allow/deny/ask/defer** — byte-identical to Verso's PermissionDecision.
- **Permission callback can rewrite tool args** before execution.
- **Hooks: pre/post tool + injection + output-rewrite + stop control** — same surface as Verso's Hooks.
- **Sub-agent = a tool that spawns a bounded child with its own context and RETURNS** — NO handoff, NO graph. Anthropic's own multi-agent validates "we don't force the graph."
- **fork session by copy-with-new-id; resume in a fresh process; pluggable durable store** — Verso's durable seam shape confirmed by Anthropic.

WHERE VERSO IS LEANER:
- Verso owns the <200-line loop in-process (inspectable/eval-able); Anthropic delegates the loop to an opaque 50 MB CLI black box.
- Verso multi-provider + base_url; Anthropic Anthropic-only.
- Verso derives tool schema from docstrings; Anthropic requires explicit schema dicts.
- Verso's 7-event hook surface vs Anthropic's 29 product-surface events (worktrees/teammates/elicitation) — Verso refuses the bloat.

WHERE ANTHROPIC IS RICHER (but mostly product surface, not lean core):
- 29 hook events, file checkpointing/rewind, MCP proxy marketplace, 6 permission modes incl. `auto` classifier-model, per-category context-usage breakdown, effort tiers, async fire-and-forget hooks.
