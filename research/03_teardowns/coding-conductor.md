# Conductor — Verso Teardown Note

**Source file:** `teardowns/CONDUCTOR.md` (35,690 lines, 6 rounds of RE)
**Product:** Conductor.build — macOS multi-agent coding orchestrator; spawns Claude Code + OpenAI Codex CLIs in parallel git worktrees
**RE depth:** Tier-1A — Bun bundle decompiled, Rust binary symbol-extracted, Anthropic SDK vendored source read, Zod schemas verbatim

---

## Agent Loop Shape

Conductor does NOT implement a ReAct loop itself. It delegates all loop logic to the LLM CLIs it manages.

**Inner loop (Anthropic SDK, vendored at SDK version 0.93.0, KNOWN L 55540–55600):**
```
while (true):
    tw++                                   # iteration counter
    if max_iterations && tw >= max_iterations: break
    call messages.stream() or messages.create()
    if compaction triggered (100,000 token threshold): replace history → continue
    push assistant message
    if tool_use blocks present:
        run tools → push tool_result → back to top
    else:
        break  (final answer, no more tool calls)
```
Compaction threshold: **100,000 tokens** (`Dn0 = 1e5`, KNOWN L 39354). At that threshold, the compaction prompt (Ln0, verbatim 27 lines) is injected to produce a continuation summary; the summary replaces all history as turn-0 user message.

**Outer driver (Conductor's `runUserMessage`, KNOWN L 67937–68010):**
- One generator per session; reused across turns.
- One-turn-at-a-time enforced: `if (v.resolveTurn !== undefined) throw Error("A turn is already in progress for session ${c}")`.
- Hot-swap of `model` and `permissionMode` between turns without restarting the child process (via SDK `queryResult.setModel()` / `setPermissionMode()`).
- Restart triggers: `fastMode`, `chromeEnabled`, `thinkingLevel` changes → kill + restart with `resume:`.

**Iteration cap:**
- `maxTurns: 1000` (KNOWN L 68309 — Conductor's per-session ceiling; SDK default is much lower).
- `max_iterations` param on the SDK loop is separate; it applies within a single messages stream.

**Termination signals (cancellation ladder, KNOWN L 57842–57867):**
1. Close stdin (EOF — agent exits gracefully).
2. After `Y_0` ms delay: SIGTERM.
3. After 5,000 ms more: SIGKILL.
4. AbortController.signal wired: fires SIGTERM immediately on abort.

---

## Models — Names, Routing, Effort Levels

**Claude model slugs (verbatim Zod union, KNOWN L 884–888):**
```ts
"opus-1m" | "opus" | "opus-4-6-1m" | "sonnet" | "haiku"
```
Model aliasing: `"opus-1m" → "opus[1m]"`, `"opus-4-6-1m" → "claude-opus-4-6[1m]"` (the `[1m]` flag signals 1M-token context).

**Codex model slugs (verbatim, KNOWN L 891–895):**
```ts
"gpt-5.5" | "gpt-5.4" | "gpt-5.3-codex-spark" | "gpt-5.3-codex" | "gpt-5.2-codex"
```
Default: `"gpt-5.3-codex"` (KNOWN L 898).

**Internal pre-release codename** (KNOWN L 901): `"claude-mythos-preview"` = pre-release ID for Opus 4.7. `"claude-opus-4-6"` is the stable Opus 4.6 ID.

**Effort levels (KNOWN L 912–916):**
- Claude: `low | medium | high | xhigh | max`
- Codex: `none | low | medium | high | xhigh` (no "max" tier)

**Thinking mode (KNOWN L 1056–1059):** `thinking.type=adaptive` (deprecated `enabled` form). Conductor passes this for all supported models.

**Per-session config knob `thinkingLevel` (KNOWN L 1096–1102):**
```ts
"none" | "low" | "medium" | "high" | "xhigh" | "max"
```

**Model routing:** No AI-driven routing. The user picks the model; Conductor just passes it to the appropriate CLI. Provider routing via env vars: 8 provider paths including LocalClaude, OpenRouter, AWS Bedrock, Google Vertex, Vercel AI Gateway, Anthropic API, GLM, Azure AI Foundry.

**Hot-swap:** Model can change between turns without restarting the process (SDK supports `setModel()` call over running stdin).

---

## Tool Registry

### Conductor's MCP Server (4 Conductor-specific tools, KNOWN L 67463–67608)

**Tool 1: `AskUserQuestion`**
- Purpose: route agent questions to the Conductor UI question panel (NOT to stdout/TTY).
- Annotations: `{ readOnly: false }`. Schema `hG` (Zod).
- Key: Conductor's native `AskUserQuestion` tool is DISABLED (`disallowedTools: ["AskUserQuestion"]`, L 68309), and this MCP version replaces it — same name, different impl. Tool override via MCP.

**Tool 2: `GetWorkspaceDiff`**
- Purpose: retrieve the current diff for the agent's worktree.
- Annotations: read-only. Schema `yG` = `{ file?: string, stat?: boolean }`.

**Tool 3: `DiffComment`**
- Purpose: leave inline comments on the diff during code review.
- Annotations: `{ readOnly: false, destructive: false, idempotent: false, openWorld: false }`. Schema `GG`.
- Post-result message: `"Posted ${b.comments.length} comment(s) on the diff."` or `"Failed to post comments."` (L 67555–67557).

**Tool 4: `GetTerminalOutput`**
- Purpose: read terminal output (run script, dev server, build logs) from the workspace.
- Annotations: read-only. Schema `mG` = `{ source: "spotlight"|"run_script"|"terminal"|"auto", maxLines?: number }`.
- Output prefixed: `[Spotlight - running/stopped]` / `[Run script - ...]` / `[Terminal - ...]`.

### MCP Transport Types (8 supported, KNOWN L 1319–1328)
```ts
"stdio"          // local subprocess, JSON-RPC over stdin/stdout
"sse"            // Server-Sent Events
"sse-ide"        // SSE with IDE-name metadata (VS Code MCP discovery)
"http"           // streamable-HTTP
"ws"             // WebSocket
"sdk"            // in-process SDK MCP server
"ws-ide"         // WebSocket + IDE-name
"claudeai-proxy" // proxy through https://mcp-proxy.anthropic.com/v1/mcp/{server_id}
```
The `claudeai-proxy` type lets users add Anthropic-hosted MCP servers without local install.

### Tool Annotations (3 bits, KNOWN L 1334–1344)
```ts
readOnly:    boolean  // no state change → auto-approve safe
destructive: boolean  // deletes/overrides → always-ask
openWorld:   boolean  // talks to internet → policy decision
```
These drive Conductor's per-tool permission policy.

### Tool Call Types (3, KNOWN L 1348–1350)
```ts
"tool_use"        // built-in Claude tools
"server_tool_use" // Anthropic server-tools (e.g., web search)
"mcp_tool_use"    // user-configured MCP servers
```

### Disallowed Tools (KNOWN L 68309/68518)
```ts
disallowedTools: ["AskUserQuestion"]
```
Claude's native `AskUserQuestion` writes to TTY, which doesn't exist in Conductor's UI. Conductor replaces it with its MCP version (see above).

---

## Context Management

**Compaction threshold:** 100,000 tokens (`Dn0 = 1e5`, KNOWN L 39354). Computed from: `input_tokens + cache_creation_input_tokens + cache_read_input_tokens + output_tokens`.

**Compaction prompt (verbatim, KNOWN L 39355–39381, 27 lines):**
```
You have been working on the task described above but have not yet completed it.
Write a continuation summary that will allow you (or another instance of yourself)
to resume work efficiently in a future context window where the conversation history
will be replaced with this summary. Your summary should be structured, concise, and
actionable. Include:
1. Task Overview [user's core request, success criteria, constraints]
2. Current State [what's been completed, files modified, key outputs]
3. Important Discoveries [technical constraints, decisions, errors, what didn't work]
4. Next Steps [specific actions needed, blockers, priority order]
5. Context to Preserve [user preferences, domain-specific details, promises made]
Be concise but complete—err on the side of including information that would prevent
duplicate work or repeated mistakes. Write in a way that enables immediate resumption.
Wrap your summary in <summary></summary> tags.
```
After compaction: history replaced with `[{role:"user", content: O.content}]` — summary is turn-0.

**Special handling before compaction (KNOWN L 55502–55510):** if the last assistant message is a `tool_use`-only block, it is STRIPPED before compaction to prevent the compactor model from trying to "answer" the tool call.

**Compaction override:** `contextTokenThreshold` param accepts custom value; Conductor never overrides it (uses SDK default of 100,000).

**Context token display:** `RT0` schema (KNOWN L 1251–1263) — surfaced to UI for "85% used" indicators:
```ts
{ totalTokens, inputTokens, cachedInputTokens, outputTokens,
  reasoningOutputTokens, modelContextWindow?, percentUsed?, rateLimits? }
```

**Context sources / `settingSources` (KNOWN L 68639):**
```ts
settingSources: ["user", "project", "local"]
```
All three CLAUDE.md / settings layers loaded. No custom Conductor system prompt injected at API level. Customization happens entirely via AGENTS.md / CLAUDE.md file reads.

**Conductor system prompt (KNOWN L 68515):**
```ts
systemPrompt: { type: "preset", preset: "claude_code" }
```
Uses Claude Code's built-in default preset. Zero verbatim "You are…" prompts in the bundle (KNOWN-by-negation from grep, §BUN1.3.8).

---

## Memory

**Memory subsystem:** Conductor inherits Claude Code's memory verbatim — no custom memory implementation:
- `autoMemoryEnabled` — boolean toggle (KNOWN L 37603).
- `autoMemoryDirectory` — defaults to `~/.claude/projects/<sanitized-cwd>/memory/` (KNOWN L 37604–37608).
- `autoDreamEnabled` — background memory consolidation ("dream cycle") — Claude Code's own feature.
- `claudeMd` — org-managed CLAUDE.md injection (only honored from managed/policy settings, KNOWN L 9963).

**Persistence layer (KNOWN — SQLite schema §A.6):** Local SQLite at `~/Library/Application Support/com.conductor.app/conductor.db`. 10 tables + 7 indexes + 27 schema migrations (versions 81–107 visible). Key tables:
- `workspaces` — per-agent-run record: `id, name, repo_id, branch, cwd, status, created_at, worktree_path, session_id, setup_script, run_script, run_script_mode, files_to_copy, spotlight_enabled, symlink_dirs, context_token_count, context_used_percent, vm_id`
- `sessions` — chat thread state: `id, workspace_id, last_user_message_at, context_used_percent, context_token_count, last_assistant_message_id`
- `session_messages` — per-turn record: `session_id, sdk_message_id, full_message, sender_id, sent_at, created_at, model, turn_id, queue_order`

**Dropped columns (KNOWN from migration history):** `creator_user_id`, `sender_id`, `sandbox_provider`, `hosting_server_url` — evidence of a walked-back multi-user/remote-VM feature.

---

## Streaming Protocol

**Inner stream (Claude):** NDJSON over stdio. `--output-format stream-json --verbose --input-format stream-json` argv. Each line is one JSON event. Conductor writes to claude's stdin:
```json
{"type":"user","session_id":"","message":{"role":"user","content":[{"type":"text","text":"..."}]},"parent_tool_use_id":null}
```

**Conductor's outer stream (WebSocket to `api.conductor.build`):** Typed JSON messages. Monotonically indexed `notificationIndex` for resumable-at-index reconnect (at-least-once with dedup semantics, KNOWN L 1248).

**27 SSE event types (KNOWN L 10148–10166)** in 5 namespaces:
1. Anthropic primitives: `message_start`, `message_delta`, `message_stop`, `content_block_start`, `content_block_delta`, `content_block_stop` + `message`
2. User events: `user.message`, `user.interrupt`, `user.tool_confirmation`, `user.custom_tool_result`
3. Agent events: `agent.message`, `agent.thinking`, `agent.tool_use`, `agent.tool_result`, `agent.mcp_tool_use`, `agent.mcp_tool_result`, `agent.custom_tool_use`, `agent.thread_context_compacted`
4. Session events: `session.status_running`, `session.status_idle`, `session.status_rescheduled`, `session.status_terminated`, `session.error`, `session.deleted`
5. Span events: `span.model_request_start`, `span.model_request_end`

Note: `agent.*` namespace is a Conductor invention layered over the Claude SSE stream. The model produces `content_block_*` events; Conductor translates those into `agent.*` for the UI.

**Codex stream:** JSON-RPC notifications over persistent stdio (`codex app-server --listen stdio://`). 25 notification methods including `model/rerouted` (OpenAI backend can swap models mid-stream) and `thread/compacted` (server-side compaction).

**Event wrapping pattern:** Agent events from claude/codex are wrapped as `{type:"agent", rawPayload: <native event>}` in Conductor's outer protocol. UI re-parses `rawPayload`. Two protocols kept separate — Conductor can distinguish its own events from pass-through agent events without parsing the inner content.

---

## Permission / Tool Approval System

**5-tier decision system (KNOWN L 1209–1214):**
```ts
"allow"                    // one-time
"allow_edits_for_session"  // session-scoped allow-all-edits
"allow_with_permissions"   // allow + record suggested permission rules (extra vs vanilla Claude Code)
"always_allow"             // persist permanent allow
"deny"
```
The extra `allow_with_permissions` tier lets the UI surface permission-rule suggestions inline with the approval prompt. This is one tier richer than vanilla Claude Code (which has 4).

**Tool approval RPC (KNOWN L 1190–1214):** Runtime sends `frontendRpcRequest` of kind `toolApproval` carrying: `toolUseId`, `toolName`, `toolInput`, `decisionReason?`, `blockedPath?`, `suggestions[]`. UI responds with `resolveFrontendRpcRequest` carrying the 5-tier decision.

**Permission bypass mode (KNOWN L 68314):**
```ts
permissionMode: "bypassPermissions"
```
Conductor always sets bypass mode at the Claude SDK level. Actual approval UX lives in Conductor's Tauri UI via the `canUseTool` callback — not in Claude's TTY prompt. Result: users get Conductor's approval UI, not Claude's.

---

## Session Protocol / API Shape

**Session config schema `rn` (KNOWN L 1091–1107):**
```ts
{
  collaborationMode: "default" | "plan",
  model: DG,                       // Claude or Codex model union
  thinkingLevel: "none"|"low"|"medium"|"high"|"xhigh"|"max",
  personality: "none"|"friendly"|"pragmatic" | null,
  fastMode?: boolean,
  requiresToolApprovals?: boolean,
  additionalDirectories?: string[],
  chromeEnabled?: boolean
}
```

**Request types (KNOWN §A.2.8):**
- `initializeSessionRequest` — {sessionId, agentType, config}
- `sendUserMessageRequest` — {sessionId, agentMessage, turnId?, displayMessage?, resume?, deliveryMode?: "default"|"steering"}
- `rollbackSessionRequest` — {sessionId, numTurns, resumeSessionAt?, threadId?}
- `getContextUsageRequest` — {sessionId, agentType?, externalSessionId?, model?}
- `spotlightSyncRequest` — {checkpointId}
- `respondToPlanRequest` — {sessionId, approved, feedback?, planFilePath?}
- `answerQuestionRequest` — {sessionId, answers: (string|string[])[]}
- `resolveFrontendRpcRequest` — {sessionId, requestId, response}

**Collaboration modes (KNOWN §BUN1.3.3):**
- `"plan"` → `permissionMode: "plan"` on Claude argv (read-only, propose plan, await approval).
- `"default"` → normal interactive mode.
- `"steering"` → mid-turn intervention; user sends message that pre-empts current step.

**Session lifecycle (KNOWN §A.2.14):**
1. authenticate → `{accountType, email, planType, authMode, modelProvider}`
2. initializeSession → backend preps git worktree
3. sendUserMessage → async; results stream as `sessionNotification` with `newEvents`
4. frontend RPCs in-flight → toolApproval / getDiff / diffComment / getTerminalOutput
5. stop / rollback / destroy
6. disconnect → `connectionClosed` reason `idle|max_lifetime` → reconnect with last `notificationIndex`

---

## Parallel Agent / Multi-Agent Isolation

**The core primitive: one git worktree per agent run (KNOWN §A.8.2).**
```
User's main repo:  ~/projects/myapp/
git worktree add → ~/projects/myapp/.conductor/worktrees/<workspace-id>/
                                                          ↑ agent runs here
```
Agents on the same repo share `.git` but operate in isolated worktrees. No HEAD conflicts, no branch fights.

**Checkpoint system (`checkpointer.sh`, KNOWN §A.3.1):**
Every turn is bracketed by `checkpointCreated {type:"start"}` and `checkpointCreated {type:"end"}`.
Each checkpoint = a git commit under `refs/conductor-checkpoints/<id>`:
- Commit TREE = the full working tree snapshot (tracked + untracked files).
- Commit MESSAGE = parseable key/value: `head <oid>`, `index-tree <sha>`, `worktree-tree <sha>`, `created <ISO>`.
- HEAD is NOT moved. Working tree is NOT changed. Entirely non-destructive.

Restore: `git reset --hard <head_oid>` + `git read-tree --reset -u <worktree_tree>` + `git clean -fd` + `git read-tree --reset <index_tree>`.

**Rewind/rollback:** `rollbackSessionRequest {numTurns}` → pick the `checkpointId` from N turns back → restore.

**Bidirectional sync (`spotlighter.sh`, KNOWN §A.3.3):**
`watchexec --watch <agent_worktree>` → on every file change → `checkpointer save` + `checkpointer restore $CONDUCTOR_ROOT_PATH`. The user sees the agent's changes live in their main repo without losing their own HEAD state.

Sync exclusions: `*.tmp.*`, `.context/**`, `**/*/.git`, `**/*/.conductor`, `**/*/.github/**`, `$HOME/.claude/*`.

**Workspace atom (KNOWN §D.5):** `(branch, working_tree, CONDUCTOR_PORT, .context/, setup_script, run_script)`. One branch per workspace at a time. NOT a security boundary — agents run with full user permissions.

**Naming:** 295 city names (random, collision-avoided). Each workspace path: `<repo>/<city>-vN/`. N agents = N cities = N parallel processes.

---

## Error Handling

**Agent crash / sidecar death (KNOWN §R6.8.6):**
1. `SidecarProcessState::is_sidecar_alive` returns false.
2. Rust host catches WS close, returns error to in-flight Tauri command.
3. React shows "Connection lost, retrying..."
4. `ensure_sidecar_started` re-invokes.
5. Sessions resume from `resume_session_at` (migration v76 added this column).

**Anthropic 5xx during streaming:**
- Bun sidecar surfaces as JSON-RPC error → Rust host forwards → React shows in thread.
- User hits "retry" → re-sends last user message.

**Rust panic (KNOWN §R6.1.7):**
- `setup_panic_hook` fires.
- Panic message + file + line + user context POSTed to PostHog as `$exception` event.
- Previous hook (stderr print) runs.
- Process aborts (Tauri default).

**Checkpoint save skip (exit codes, KNOWN §A.3.1):**
- `101` — merge/rebase in progress (not error, just skip this cycle).
- `102` — index has unresolved conflicts.
`spotlighter.sh` handles both: silently skip sync, wait for next file change.

**HTTP download retry (KNOWN §A.5):**
- HTTP 416 Range Not Satisfiable → drop partial file → restart full download.
- Failed downloads use scheduled retry: `next_attempt_unix_ms + backoff(attempt)`, persisted across app restarts.

**Sidecar boot timeout (KNOWN §R6.2.3):**
`Duration::from_secs(120)` — `"Failed to start Claude Code within 2 minutes"`.

**Anthropic SDK retry (KNOWN L 28558):** `maxRetries: 2` default. `DEFAULT_TIMEOUT: 600000ms` (10 minutes).

**Codex `model/rerouted` event (KNOWN L 70748–70751):** OpenAI backend can silently swap models mid-stream; Conductor detects and updates `currentSdkModel`.

---

## Key Constants

| Constant | Value | Source |
|---|---|---|
| Compaction token threshold | 100,000 | `Dn0 = 1e5`, L 39354 |
| maxTurns | 1,000 | L 68309 |
| maxRetries | 2 | L 28558 |
| DEFAULT_TIMEOUT | 600,000 ms (10 min) | L 56778 |
| Sidecar boot timeout | 120,000 ms (2 min) | `Duration::from_secs(120)` |
| SIGKILL grace after SIGTERM | 5,000 ms | L 57629 |
| Anthropic SDK version | 0.93.0 | L 38733 |
| `anthropic-version` header | `"2023-06-01"` | L 29060 |
| City names pool | 295 | docs |
| Default Codex model | `"gpt-5.3-codex"` | L 898 |
| Default personality | `"pragmatic"` | L 70011 |
| Agent binary cache path | `~/Library/Application Support/com.conductor.app/agent-binaries/` | INFERRED |
| SQLite DB path | `~/Library/Application Support/com.conductor.app/conductor.db` | INFERRED |
| MCP proxy URL (prod) | `https://mcp-proxy.anthropic.com/v1/mcp/{server_id}` | verbatim |

---

## Anthropic Managed Agents API Schema (extracted via Pydantic typo-hint probing, KNOWN §R6.5)

```python
# POST /v1/agents
class CreateAgentRequest(BaseModel):
    name: str
    description: str
    model: str
    tools: list[Tool]

class Tool(BaseModel):
    type: Literal["custom"]   # ONLY "custom" valid — no "bash", "computer", "text_editor"
    name: str
    description: str
    input_schema: dict        # JSON Schema object

# POST /v1/sessions
class CreateSessionRequest(BaseModel):
    agent: str           # agent ID
    environment_id: str  # execution environment ID
```

**Key finding:** `system_prompt`, `instructions`, `memory_store_id`, `messages`, `stream` are ALL rejected at agent-creation time. System prompt is not bound at agent level. Memory store is a separate top-level resource (`/v1/memory_stores`).

Resource model:
```
/v1/agents        — capability profile (name + model + custom tools)
/v1/environments  — execution sandbox config
/v1/memory_stores — persistent context / RAG store
/v1/sessions      — runtime binding of (agent, environment)
```

---

## DX / API Shape Observations

**Agent as a typed discriminated union.** Conductor's agent config is a Zod tagged union:
```ts
agentType: "claude" | "codex"
```
Each type has its own config schema with only valid fields for that backend. No stringly-typed "provider" fields.

**Session config is flat and hot-patchable.** `updateSessionConfigRequest {sessionId, config: partial(rn)}` can change model, thinkingLevel, personality, requiresToolApprovals, chromeEnabled mid-session. Most changes apply without restarting the child process (except `fastMode`, `chromeEnabled`, `thinkingLevel` which require restart + resume).

**Delivery mode as a message property.** Each `sendUserMessageRequest` carries `deliveryMode?: "default"|"steering"`. Steering = mid-turn interrupt; doesn't start a new turn, it pre-empts the current one. This is a per-message flag, not a session-level flag.

**Collaboration mode as a first-class session param.** `plan` mode is wired to `permissionMode: "plan"` on the Claude SDK — native concept, not a Conductor invention. Clean.

**Tool replacement via MCP.** Conductor disables a built-in tool (`AskUserQuestion`) and re-provides it via MCP with a custom implementation that routes to the UI. This pattern is elegant: the LLM never knows the tool changed; the behavior changes without touching the system prompt.

**Resumable event streams.** `notificationIndex` monotonically increments; client sends last-seen index on reconnect; server replays. Trivially at-least-once.

**Plan/approve flow via `respondToPlanRequest`.** Clean: agent proposes plan, Conductor buffers it in `proposedPlan: string | null` on the status object, user approves/rejects via a dedicated request.

---

## → Verso Implications

1. **COPY: Agent-type-as-discriminated-union for config.** Verso should model agent configs as tagged unions keyed on provider/backend type. `{type: "claude", model: "sonnet", effortLevel: "high"}` vs `{type: "openai", model: "gpt-5.3", reasoningEffort: "high"}`. Different providers have different valid params; Zod/Pydantic discrimination enforces this at parse time, not runtime.

2. **COPY: Per-message delivery mode (default vs steering).** Verso's turn API should carry a `delivery_mode` field. `"steering"` = interrupt running turn, inject message; `"default"` = queue for next turn. This enables mid-turn intervention without building a separate control channel.

3. **COPY: Tool-annotation bits (readOnly / destructive / openWorld).** These three bits are from the MCP spec but Conductor proves they're useful as a permission-policy driver. Verso should adopt them as standard tool metadata; they power auto-approve-safe vs always-ask behavior without any prompt engineering.

4. **COPY: Resumable event stream via monotonic index.** `notificationIndex` + replay-from-index is a trivial, zero-dependency approach to reliable streaming. Verso's event stream should be indexed and replayable from any offset.

5. **COPY: The AskUserQuestion override pattern.** Verso should support tool-replacement at the framework layer: disable a built-in tool by name and re-register a custom implementation under the same name. The LLM's behavior is unchanged; the host execution changes. No system-prompt surgery needed.

6. **COPY: Compaction at 100K tokens with structured prompt.** The verbatim compaction prompt is production-proven. Verso should ship this as the default compaction strategy, configurable via `contextTokenThreshold` param. Crucially: strip trailing `tool_use`-only blocks before compacting to avoid model confusion.

7. **COPY: 5-tier permission system.** One-time / session-scoped / allow-with-rules / always-allow / deny is the right granularity. Vanilla Claude Code's 4 tiers miss the `allow_with_permissions` case where the framework surfaces suggested permission rules alongside the approval UI.

8. **COPY: Bypass-permissions at SDK level + custom approval UX.** Verso should set `permissionMode: bypassPermissions` at the SDK level and handle all approval UX in the framework's own UI layer. This separates "what the model can call" (SDK-level) from "what the user sees" (framework UX) cleanly.

9. **COPY: Structured compaction trigger with explicit token accounting.** Count `input_tokens + cache_creation_input_tokens + cache_read_input_tokens + output_tokens` (not just `input_tokens`) as the compaction signal. Cached tokens still contribute to the context window.

10. **COPY: Git-worktree isolation for parallel agents.** Verso's parallel agent primitive should use git worktrees: cheap (share `.git`), diff-ready, restore-ready, no CRDT needed. `refs/verso-checkpoints/<id>` as the private ref namespace. Checkpoint = commit where tree is full worktree snapshot; message encodes HEAD OID + index tree as parseable key-value.

11. **COPY: Checkpoint bracketing every turn.** Every agent turn should emit `checkpoint_start` and `checkpoint_end` events. This makes rewind a first-class operation (pick a checkpoint ID, restore) rather than an afterthought.

12. **AVOID: Bundling the LLM CLI inside the framework binary.** Conductor bundles Claude Code 2.1.139 inside the Bun binary for the "no install" guarantee, but this creates a permanent version-lag: the bundled Claude Code ages out while users expect latest behavior. Verso should treat LLM clients as dependencies, not bundled assets.

13. **AVOID: Disabling `AskUserQuestion` without providing a replacement.** Conductor's approach works because it provides `mcp__conductor__AskUserQuestion` as a replacement. If Verso disallows the native tool without a replacement, agents silently lose the ability to ask clarifying questions — bad default. Either provide a framework-level replacement or don't disable it.

14. **AVOID: Shell-stripping of user API keys.** Conductor strips `ANTHROPIC_API_KEY` from the shell env before spawning Claude (to force OAuth). This surprises developers who have the env var set. Verso should prefer explicit auth resolution order (env var > config file > OAuth) with a clear precedence visible in the developer docs, not silent stripping.

15. **AVOID: No system prompt at all.** Conductor's `developer_instructions: null` means Codex agents get zero custom context from the framework. For a framework, this is a missed opportunity: Verso should inject a thin, configurable system-prompt layer (the AGENTS.md pattern is good, but it requires the user to author files — Verso should support a `system_prompt` field on the session config that flows cleanly without CLAUDE.md/AGENTS.md ceremony).

16. **VERSO COULD IMPROVE: Plan mode as a first-class turn type.** Conductor's `collaborationMode: "plan"` is elegant but binary. Verso could generalize: any turn can carry `mode: "plan" | "execute" | "review"` and the framework routes to the appropriate `permissionMode` + prompt override accordingly. Plan → read-only. Execute → bypass. Review → read-only + diff annotations enabled.

17. **VERSO COULD IMPROVE: Model hot-swap between turns without restart.** Conductor supports `setModel()` mid-session for Claude. Verso should expose this as a first-class API: `session.update({model: "haiku"})` takes effect on the next turn without dropping session history.

18. **VERSO COULD IMPROVE: Structured event taxonomy.** Conductor's 27-event taxonomy (5 namespaces) is clean. Verso should adopt a similar namespace structure: `message.*`, `tool.*`, `session.*`, `memory.*`, `span.*`. The `span.*` events (request_start / request_end) enable latency tracing without external instrumentation.

19. **VERSO COULD IMPROVE: Managed Agents resource model.** Anthropic's Managed Agents API separates `Agent` (capability profile) from `Environment` (sandbox config) from `Session` (runtime binding). Verso's object model should mirror this: define agents (tools + model + description) separately from the session that executes them. Session = agent + context.

20. **VERSO COULD IMPROVE: Streaming compaction event.** `agent.thread_context_compacted` is emitted when compaction runs. Verso should surface this as a first-class event in the stream — clients can display a "context trimmed" marker in the UI without polling.
