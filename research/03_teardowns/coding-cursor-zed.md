# Teardown Cluster: Cursor + Zed
> Cluster key: `coding-cursor-zed`
> Source files: `teardowns/CURSOR.md` (4,659 lines) · `teardowns/ZED.md` (13,898 lines)
> Distilled for Verso — an AI agent framework (peer to LangGraph/CrewAI/Pydantic-AI)

Both systems are production coding agents with open-sourceable reference implementations. Cursor is the largest deployed coding agent (closed-source, ~$400M ARR as of 2026); Zed is the highest-quality open-source agent + editor combination. Both converged on the same core loop but diverged sharply on tooling surface area, multi-agent coordination, and extensibility model.

---

## 1. Cursor — Agent Loop

### Loop shape

Standard tool-use loop — no plan/execute separation at the loop level. Planning is internal to the model's reasoning, not an explicit framework phase.

```
1. Receive user input + injected context (open files, cursor pos, linter errors, edit history)
2. Model produces assistant message with 0-N tool calls
3. Execute all tool calls (parallel where no dependencies)
4. Hooks fire (postToolUse, afterShellExecution)
5. Append tool results → loop back to step 2
6. When model produces 0 tool calls → turn ends
7. `stop` hook fires → if hook returns followup_message → inject as new user message → loop continues
```

From the leaked v1.2 system prompt (x1xhlol, KNOWN):
> "You are an agent — please keep going until the user's query is completely resolved, before ending your turn."
> "If you make a plan, immediately follow it, do not wait for the user to confirm."

### Termination / iteration caps

- No hardcoded max-turn limit in the loop itself.
- The `stop` hook has a `loop_limit` parameter (default: **5**) — the hook can re-inject a follow-up at most 5 times.
- Linter error fix loop: **3 iterations** hardcoded in system prompt ("DO NOT loop more than 3 times on fixing linter errors on the same file").
- Context overflow: `preCompact` hook fires at `context_usage_percent: 85`, triggers compaction, loop continues.
- User abort: `sessionEnd` hook fires with `reason: "user_close"`.

### Parallel tool calls

Cursor 1.0 changelog confirms parallel tool execution. The v1.2 tools list includes `multi_tool_use` — a framework-injected wrapper that batches tool calls into a single response. Non-mutating tools run fully concurrently; mutating tools serialize.

---

## 2. Cursor — Models

| Role | Model | Provider | Notes |
|------|-------|----------|-------|
| Planning / reasoning | Composer 2 (fast + standard), Claude Sonnet 4.6, Claude Opus 4, GPT-5, Gemini 2.5 Flash | User-selectable | Model is **below all harness layers** — swapping it changes nothing in the harness |
| Apply (Fast Apply) | Llama-3-70B fine-tune (`llama-70b-ft-spec`) | Fireworks AI | Speculative decoding; ~1,000 tokens/sec (~13x speedup over vanilla Llama-3-70B) |
| Explore subagents | Faster/cheaper model | KNOWN from docs | "using faster models for parallel searches" |
| Shadow workspace lint | None (LSP-based) | IDE-local | Not a model call — pure static analysis |
| Composer 2 (proprietary) | Kimi K2.5 base (1.04T params, 32B active MoE) | Fireworks AI (inference) | Cursor's own RL-trained model; see §8 of CURSOR.md |

### Model routing

- Per-mode routing: Ask → `StreamChat` (no tools); Manual → `StreamUnifiedChat` (propose_edit only); Agent → `StreamUnifiedChatWithToolsIdempotent` (full 80-tool registry).
- Plan-then-execute routing: explicit UI support for two-model pipelines ("Create plan with one model, build with another").
- `/best-of-n` racing: same task dispatched to N models simultaneously in isolated worktrees; user picks best diff.

---

## 3. Cursor — Tool Registry (Complete, KNOWN from bundle)

Round 1 had 12 tools; Round 2 extracts the full v3 registry: **~80 tools** grouped as follows.

### File Operations (15)
`read_file`, `read_chunk`, `read_with_linter`, `read_lints`, `read_project`, `read_semsearch_files`, `edit_file` (routes through FastApply), `new_edit`, `new_file`, `save_file`, `delete_file`, `create_rm_files`, `undo_edit`, `reapply`, `apply_agent_diff`

### Search and Navigation (10)
`grep_result`, `ripgrep_search`, `ripgrep_raw_search`, `glob_file_search`, `file_search`, `search_symbols`, `get_symbols`, `gotodef`, `semantic_search`, `semantic_search_full`, `deep_search` (multi-hop subagent)

### Terminal / Shell (8)
`run_terminal_commands`, `force_background_shell_result`, `background_shell_spawn_result`, `write_shell_stdin`, `shell_result`, `record_screen`, `setup_vm_environment`, `replace_env_result`

### Git / GitHub (10)
`commit`, `commit_and_push`, `push`, `create_branch_and_commit`, `create_branch_commit_and_push`, `create_pr`, `create_pr_with_changes`, `fetch_pull_request`, `pr_management_result`, `babysit_pr_in_cloud`

### Agent Coordination (10)
`task` (spawn subagent), `subagent_result`, `subagent_await_result`, `await_task`, `force_background_subagent_result`, `async_task_result`, `completed_task_result`, `heal_stale_composer`, `switch_mode` (Ask/Manual/Agent mid-conversation), `mark_completed_task_result`

### Planning and Knowledge (10)
`create_plan`, `todo_read`, `todo_write`, `update_project`, `get_project_structure`, `knowledge_base`, `fetch_rules`, `ask_question` (suspends agent, waits for user), `create_diagram`

### Tests, Lint, Bug Fixes (8)
`add_test`, `delete_test`, `run_test`, `get_tests`, `fix_lints`, `report_bugfix_results`, `diagnostics_result`, `report_bug_tool_call`

### MCP and External (8)
`call_mcp_tool`, `mcp_auth` (OAuth), `get_mcp_tools`, `list_mcp_resources`, `read_mcp_resource`, `web_search`, `web_fetch`, `generate_image`

### Computer Use and UI (5)
`computer_use` (Anthropic-style mouse/keyboard), `record_screen`, `add_ui_step`, `active_editor_result`, `get_blob_result` / `set_blob_result`

### Specialized (5)
`redacted_read_result`, `bugbot_response`, `cmd_k_response`, `null_result`, `final_result` / `final_tool_result`

Key architectural observation: most agentic tools have 5-15 tools; Cursor 3 has 80. The combinatorial expressiveness of the full registry is what enables complete-task execution (commit → PR → review → land) within a single agent turn.

---

## 4. Cursor — MCP Integration

MCP config: `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global).

Transports: `stdio` (local), `SSE`, `Streamable HTTP`, OAuth remote.

Config interpolation: `${env:NAME}`, `${userHome}`, `${workspaceFolder}`, `${workspaceFolderBasename}`, `${pathSeparator}`.

Supported protocol features: Tools, Prompts, Resources, Roots, Elicitation, Apps.

Tool approval: default asks; "Enable auto-run" bypasses. January 2026: MCP Tool Search (Anthropic feature) loads tool definitions on-demand — cuts token overhead from **~77K to ~8.7K tokens** (85% reduction) when many servers are connected.

Cursor acts as **MCP client only** — no mechanism to expose itself as an MCP server to external orchestrators (contrast Codex CLI, which has `codex mcp-server`).

---

## 5. Cursor — Context Assembly

Injected per turn (KNOWN from v1.2 system prompt):
- Open files and cursor position
- Recently viewed files
- Edit history in current session
- Linter errors (live from shadow workspace)
- `.cursor/rules/*.mdc` always-on rules
- Relevant `SKILL.md` files (dynamically loaded by agent)
- Memories (from `update_memory` tool, persistent across sessions)

### Rules system (two modes)

**Push mode** — `alwaysApply: true` rules injected into every system context.

**Pull mode** — agent calls `fetch_rules` tool to load rules matching its current task. This is a critical design: rules are not statically dumped into the system prompt; the agent retrieves them on demand. A repo can have unlimited rules files; only relevant ones cost tokens.

.mdc frontmatter schema:
```yaml
---
description: <string — LLM uses this to decide injection relevance>
globs: <string|string[] — glob patterns for file-type matching>
alwaysApply: <bool>
---
<markdown body>
```

Priority hierarchy:
1. User Rules (global, from Settings)
2. Repo Rules (`alwaysApply: true`)
3. Repo Rules matched by glob
4. Repo Rules selected by `fetch_rules` tool (per-turn-as-needed)
5. `.cursorrules` legacy file

### Context sharing between parallel agents

Contexts are "summarized and reduced" before sharing (KNOWN from docs). No public detail on token budgets, summarization model, or uncommitted-change visibility. Recommended budgets (Addy Osmani analysis): frontend agent 180k tokens, backend agent 280k tokens; auto-pause at 85% utilization; kill-and-reassign agents stuck 3+ iterations on identical errors.

---

## 6. Cursor — Memory

**Cursor Memories** (Cursor 1.0 beta, KNOWN):
- Stored per-project at individual user level.
- Created/updated/deleted by `update_memory` tool during agent turns.
- Cited in responses as `[[memory:MEMORY_ID]]`.
- Persistent across conversations.
- Not shared between users on the same team.
- Scope: per-project, per-user (no cross-project, no team-shared).

---

## 7. Cursor — System Prompt (Verbatim, v1.2, KNOWN from x1xhlol)

Key behavioral sections:

```
<tool_calling>
1. ALWAYS follow the tool call schema exactly...
3. NEVER refer to tool names when speaking to the USER. Instead, just say what the tool is doing.
4. If you need additional information that you can get via tool calls, prefer that over asking the user.
5. If you make a plan, immediately follow it...
6. Only use the standard tool call format...
7. Do NOT guess or make up an answer.
8. You can autonomously read as many files as you need...
</tool_calling>

<making_code_changes>
DO NOT loop more than 3 times on fixing linter errors on the same file. On the third time, stop and ask.
</making_code_changes>

<memories>
MUST update/delete memory immediately using the update_memory tool when user corrects something or you encounter contradicting information.
<memory_citation>ALWAYS cite a memory when you use it: [[memory:MEMORY_ID]]</memory_citation>
</memories>
```

**Key design constants from this prompt:**
- Linter fix loop cap: **3**
- Rule about tool name disclosure: never expose tool names in user-facing messages
- Preference ordering: tools > guessing; PRs > manual git history inspection

---

## 8. Cursor — Error Handling and Retry

- **Linter errors**: up to 3 fix attempts; then surface to user.
- **Failed `edit_file`**: `reapply` tool calls the "smarter model" (Apply model) with the last edit to try again.
- **Stuck agents** (`heal_stale_composer` tool): explicit recovery mechanism for hung Composer sessions.
- **Context overflow**: `preCompact` hook (fire-and-forget) + compaction + loop continues (no restart).
- **Idempotent RPCs**: `StreamUnifiedChatWithToolsIdempotent` carries idempotency key so retries on connection drop don't double-execute side-effecting tools (write_file, run_command).
- **Session resume**: `AttachBackgroundComposerRequest` + `AttachBackgroundComposerLogsResponse` — server-side resume semantics. User can close laptop and re-attach hours later; cloud agent never stops.

---

## 9. Cursor — Multi-Agent Architecture

### Local parallel agents (Cursor 3, KNOWN)

Up to 8 agents simultaneously. Mechanism: `git worktree add` per agent (UI wrapper in Cursor 3). Each agent gets own filesystem view; edits in worktree A do not affect worktree B. File-based coordination only — no native agent-to-agent messaging protocol.

Community-developed coordination pattern (forum.cursor.com/t/140218): filesystem-lock + JSON claim file protocol where each of 8 agents atomically self-assigns a task number (1–8) via `mkdir $LOCK_DIR` race.

### Cloud parallel agents (KNOWN)

- Isolated Ubuntu VMs on AWS; codebase cloned fresh per VM.
- Up to 10-20 agents in cloud; VMs ephemeral (destroyed after task).
- Agents produce draft PRs with video/screenshot/log artifacts attached.
- Pre-warm optimization: `PreWarmPodRequest` — client calls pre-warm when user opens repo in cloud UI; by the time user submits task, VM is already booted, deps installed, LSP warm. Latency: 30s+ → milliseconds.
- GitHub OAuth refresh inside pod: `RefreshGithubAccessTokenInBackgroundComposerRequest` handles 8-hour token TTL for long-running agents.
- Network egress policy per-user: `BackgroundComposerUserEgressPolicy` (values: `"all"` / `"github_only"` / `"none"`) — enterprise exfiltration prevention.

### Subagent types (Cursor 2.4+, KNOWN)

| Type | Model | Purpose |
|------|-------|---------|
| `task` | Configurable | General-purpose work |
| `explore` | Fast model | Navigate large repos, build context |
| `bash` | Fast model | Shell command sequences |
| `browser` | Fast model | MCP-based browser control; filters DOM noise |

Config: `.cursor/agents/` or `.claude/agents/` (cross-tool compat) or `.codex/agents/`.

Each subagent has its own isolated context window — parallel subagents don't contaminate each other's or the parent's context.

### Deep Search subagent (KNOWN from bundle)

`DeepSearchSubagentParams` + `DeepSearchSubagentReturnValue` — deep retrieval is a sub-agent, not a single retrieval call. Flow:
1. Composer asks "search for X"
2. Spawns Deep Search subagent with `{query, max_iterations, scope}`
3. Subagent runs own ReAct loop: search → read → search-again → read-again → synthesize
4. Returns `{summary, cited_files, raw_chunks}`
Progress streamed via `DeepSearchStream`. This is why `@codebase` queries take 10+ seconds.

---

## 10. Cursor — Streaming Protocol

Three-tier streaming RPC family (KNOWN from bundle):
- `StreamChatRequest` / `StreamChatContextRequest` / `StreamChatDeepContextRequest` — legacy Chat plane
- `StreamUnifiedChatRequest` — new unified plane (Cursor 3.x)
- `StreamUnifiedChatRequestWithTools` — with tool calling
- `StreamUnifiedChatRequestWithToolsIdempotent` — crash-resilient variant (idempotency key prevents double-execution on reconnect)

Cursor 3 is mid-migration: new clients hit Unified, old Cursor 2.x clients hit legacy Chat. Server routes both.

"Enhancer" sub-protocol (`ComposerEnhancerClientMessage` / `*ServerMessage` / `*ToolCall` / `*ToolResult`): a side-channel parallel to the main chat stream, used for async context fetches arriving after main response started, and inline lint-warning streams while the model writes code.

---

## 11. Cursor — RL Training (Composer 2, KNOWN from arXiv:2603.24477)

Base: Kimi K2.5 (1.04T params, 32B active, MoE). Training on NVIDIA B300 GPUs.

**Key RL innovations:**
1. **KL divergence: k₁ = −log r** instead of k₃ — avoids variance blow-up when distributions diverge; enables larger policy steps.
2. **Self-summarization**: chains multiple generations with summaries between them; final reward propagates back through all. Model learns to summarize on hard examples, conserve tokens on easy ones.
3. **Non-linear length penalty**: `C_length = [(1+kx)^(1-q) − 1] / [k(1−q)]` — weak penalty for hard tasks (extended reasoning allowed), strong for easy (concise solutions enforced).
4. **Router Replay (MoE stability)**: expert indices captured at inference; replayed during training forward pass to ensure numerical consistency.
5. **Asynchronous 4-service architecture**: training / environments / inference / evaluations — independently scalable, independently restartable.

**Emergent behaviors during RL (and mitigations):**
- Excessive chain-of-thought in code comments → auxiliary reward for coding style
- Over-reliance on terminal tools → auxiliary reward for proper tool usage
- Poor communication quality → auxiliary reward for communication quality

Finding: "RL improves both average performance AND best-of-K simultaneously" — contradicts trade-off assumption from literature.

---

## 12. Zed — Agent Loop

### Loop shape

`crates/agent/src/agent.rs:5,356 lines`. Identical pattern to Claude Code / Cline / opencode:

```
loop {
    1. Send messages + tool definitions to LLM.
    2. Stream response chunks; if tool_use detected, materialize the tool call.
    3. For each tool call:
       a. Check if it needs permission (tool_permissions.rs).
       b. If permission needed, pause and wait for user response.
       c. Otherwise, run the tool.
       d. Append tool_result to messages.
    4. If LLM indicates "done" (no further tool calls), exit loop.
    5. Otherwise, loop back to step 1 with updated messages.
}
```

No explicit max-iteration cap in the loop. Termination: model stops calling tools. Explicit sub-agent spawning via `spawn_agent` tool.

### Thread data model

`crates/agent/src/thread.rs:5,055 lines`. A `Thread` is: system prompt + user messages + assistant messages + tool calls + tool results + active model + active tools + pending tool calls (awaiting permission) + streamed output buffer + token usage counters.

Thread is a `gpui::Entity` — Zed's reference-counted observable type. Updates trigger UI re-renders.

### Streaming dispatch

SSE chunks arrive via background executor → posted to foreground executor → `thread.update(cx, |thread, cx| { thread.append_chunk(chunk); cx.notify(); })`. Chunk arrival (network time) decoupled from rendering (frame time, 60–120Hz). Multiple chunks batch between frames if arrival is fast.

---

## 13. Zed — Models

Zed is provider-agnostic at every layer. Per-provider crates:
- `crates/anthropic/` — Anthropic (Claude)
- `crates/cloud_llm_client/` — Zed's own hosted LLM (proxy)
- `crates/copilot/` + `crates/copilot_chat/` — GitHub Copilot
- `crates/bedrock/` — AWS Bedrock
- `crates/codestral/` — Mistral's code model
- Plus: OpenAI, Google Gemini, Ollama (local), OpenRouter

Edit prediction (Zeta) is also provider-agnostic at the integration layer — same trigger dispatches to Ollama / OpenAI-compatible / Zed cloud / Zeta.

---

## 14. Zed — Tool Registry (KNOWN from crates/agent/src/tools/)

25+ tools, each in its own file:

| Tool | File:lines | Purpose |
|------|-----------|---------|
| `grep` | `grep_tool.rs:1,210` | Regex search, paginated (20 per page) |
| `read_file` | `read_file_tool.rs:2,037` | Read with line ranges |
| `edit_file` | `edit_file_tool.rs:2,818` | Modify file (largest tool) |
| `write_file` | `write_file_tool.rs` | Create or overwrite |
| `terminal` | `terminal_tool.rs:1,431` | Shell command in Zed's terminal |
| `find_path` | `find_path_tool.rs:271` | Glob file finder |
| `find_references` | `find_references_tool.rs:102` | LSP find-references |
| `go_to_definition` | `go_to_definition_tool.rs:111` | LSP go-to-definition |
| `diagnostics` | `diagnostics_tool.rs:258` | LSP diagnostics |
| `get_code_actions` | `get_code_actions_tool.rs:116` | LSP code actions |
| `apply_code_action` | `apply_code_action_tool.rs:145` | Apply a code action |
| `rename` | `rename_tool.rs:125` | LSP rename symbol |
| `web_search` | `web_search_tool.rs` | Web search |
| `fetch` | `fetch_tool.rs:180` | Fetch URL |
| `list_directory` | `list_directory_tool.rs:1,247` | Directory listing, paginated |
| `create_directory` | `create_directory_tool.rs:447` | mkdir |
| `delete_path` | `delete_path_tool.rs:519` | rm |
| `copy_path` | `copy_path_tool.rs:462` | cp |
| `move_path` | `move_path_tool.rs:472` | mv |
| `spawn_agent` | `spawn_agent_tool.rs:256` | Sub-agent (separate Thread) |
| `update_plan` | `update_plan_tool.rs:221` | Update visible plan/todo |
| `skill` | `skill_tool.rs:785` | Invoke user-defined skill |
| `edit_session` | `edit_session.rs:1,132` | Multi-step edit session |

### Grep pagination constants (grep_tool.rs, KNOWN)

```rust
const RESULTS_PER_PAGE: u32 = 20;
const CONTEXT_LINES: u32 = 2;
const MAX_ANCESTOR_LINES: u32 = 10;
```

Tool description explicitly tells the model to paginate via `offset:` parameter for subsequent pages.

---

## 15. Zed — Tool Permissions

`crates/agent/src/tool_permissions.rs:2,409 lines`. Permission categories:
- **Read** — no permission needed: `read_file`, `grep`, `find_path`, `diagnostics`, `list_directory`, `find_references`, `go_to_definition`
- **Local mutation** — requires confirmation: `edit_file`, `write_file`, `delete_path`, `move_path`, `copy_path`
- **Network** — requires confirmation: `fetch`, `web_search`
- **Shell** — requires confirmation: `terminal`

User can pre-approve patterns: "always allow edit_file in `src/**/*.rs`", "never allow terminal commands containing `rm -rf`". Pending requests stack up in a panel.

---

## 16. Zed — System Prompt (Verbatim, KNOWN from crates/agent/src/templates/system_prompt.hbs)

```
You are the Zed coding agent running inside the Zed editor. You help users complete 
software engineering tasks by understanding their codebase, making careful changes, 
and explaining your work clearly.

## Tool Use
- Follow the available tool schemas exactly and provide every required argument.
- Use only the tools that are currently available. Do not call a tool just because 
  it appeared earlier in the conversation; the user may have disabled it.
- Prefer the most direct tool for the job.
- Before acting, gather enough context to avoid guessing.
- You can call multiple tools in a single response. If you intend to call multiple 
  tools and there are no dependencies between them, make all independent tool calls 
  in parallel.
- When running commands that may run indefinitely, specify timeout_ms.
- Do not waste tokens by re-reading files after calling write_file or edit_file.
```

**Handlebars-conditional structure** (`system_prompt.hbs`): large prompt sections are gated on `{{#if (contains available_tools 'update_plan')}}`. If `update_plan` is disabled, planning instructions vanish from the prompt. The model sees only what's relevant to its current tool set.

Other templates in the same directory:
- `experimental_system_prompt.hbs` — A/B test variant
- `edit_file_prompt_diff_fenced.hbs` — edit_file with diff-fence format
- `edit_file_prompt_xml.hbs` — edit_file with XML format
- `create_file_prompt.hbs` — for write_file
- `diff_judge.hbs` — verifier that the edit-file diff matches model intent

---

## 17. Zed — MCP Integration

`crates/context_server/`. Client side of MCP (Anthropic's Model Context Protocol). Config in `settings.json`:

```json
"context_servers": {
  "filesystem": {
    "command": "npx",
    "args": ["@modelcontextprotocol/server-filesystem", "/home/user/repos"]
  }
}
```

Zed spawns the server as a subprocess, communicates over stdio JSON-RPC, lists the server's tools, exposes them to the agent as additional callable functions.

**ACP (Agent Client Protocol)**: `crates/acp_thread/`, `crates/acp_tools/`, `crates/agent_servers/`. Zed's own protocol for letting external agent processes (Claude Code, opencode) plug into Zed's UI. Claude Code's chat can appear inside Zed's agent panel. Zed is positioning as the **agent host UI** that hosts any agent via ACP.

---

## 18. Zed — Sub-agents

`spawn_agent_tool.rs:256 lines`. Each sub-agent is a separate `Thread` with its own model + tools + conversation. Parent waits for sub-agent to return (or times out). Pattern identical to Claude Code's Task tool / opencode's Tracer / NIA's Oracle.

---

## 19. Zed — Zeta (Edit Prediction Model)

`crates/edit_prediction/src/zeta.rs:795 lines` + `crates/zeta_prompt/src/zeta_prompt.rs:5,988 lines`.

Custom-trained open-weight model (fine-tune of Qwen2.5-Coder or similar) for next-edit prediction. Open-sourced at `https://huggingface.co/zed-industries/zeta`.

Input struct:
```rust
pub struct ZetaPromptInput {
    pub cursor_path: Arc<Path>,
    pub cursor_excerpt: Arc<str>,
    pub cursor_offset_in_excerpt: usize,
    pub events: Vec<Arc<Event>>,           // recent edit events
    pub related_files: Option<Vec<RelatedFile>>,
    pub active_buffer_diagnostics: Vec<ActiveBufferDiagnostic>,
    pub excerpt_ranges: ExcerptRanges,
    pub syntax_ranges: Option<Vec<Range<usize>>>,
    ...
}
```

Constants (zeta_prompt.rs:17-31):
```rust
pub const CURSOR_MARKER: &str = "<|user_cursor|>";  // inserted at cursor position
pub const PREFILL_RATIO: f64 = 0.1;                 // max 10% prefill of editable region
fn estimate_tokens(bytes: usize) -> usize { bytes / 3 }  // ~3 bytes/token for code
fn apply_prompt_budget_margin(max_tokens: usize) -> usize { (max_tokens as f64 * 0.9) as usize }
```

Current default format: `V0131GitMergeMarkersPrefix` — uses `<<<<<<<`/`=======`/`>>>>>>>` markers (git merge conflict syntax) to delimit edit regions. Multiple trained format versions (`V0112`, `V0113`, `V0114`, `V0120`, `V0131`).

Integration: provider-agnostic at the integration layer — same trigger dispatches to Zeta, Ollama, or any OpenAI-compatible endpoint.

---

## 20. Zed — Constants Catalogue (KNOWN)

| Constant | Value | Source |
|----------|-------|--------|
| Grep `RESULTS_PER_PAGE` | 20 | `grep_tool.rs:67` |
| Grep `CONTEXT_LINES` | 2 | `grep_tool.rs:121` |
| Grep `MAX_ANCESTOR_LINES` | 10 | `grep_tool.rs:122` |
| Zeta `CURSOR_MARKER` | `<|user_cursor|>` | `zeta_prompt.rs:17` |
| Zeta `PREFILL_RATIO` | 0.1 (10%) | `zeta_prompt.rs:22` |
| Zeta token estimate | `bytes / 3` | `zeta_prompt.rs:24` |
| Zeta prompt budget margin | 0.9× | `zeta_prompt.rs:29` |

---

## 21. Architectural Comparison

| Dimension | Cursor | Zed |
|-----------|--------|-----|
| Loop type | Tool-use (no explicit plan phase) | Tool-use (identical) |
| Max agents | 8 local / 10-20 cloud | 1 + spawn_agent sub-agents (no hard cap) |
| Agent isolation | Git worktrees (local) / Ubuntu VMs (cloud) | Separate Thread objects (in-process) |
| Tool count | ~80 | ~25 |
| MCP role | Client only | Client (+ ACP as agent host) |
| System prompt | Handlebars-conditional (per active tools) | Handlebars-conditional (identical pattern) |
| Memory | Persistent cross-session (update_memory tool) | None built-in (ephemeral Thread) |
| Rules system | Push (always) + Pull (fetch_rules tool) | None (static context injection) |
| Streaming | SSE (Unified/Idempotent variants) | SSE (background → foreground executor pattern) |
| Session resume | Server-side (BackgroundComposer) | None (Thread dies with process) |
| Open source | No | Yes (Apache 2.0 + GPL-3.0 server) |

Both systems **independently converged** on Handlebars-conditional system prompts, identical tool-use loop shape, 20-result pagination for search tools, and sub-agent spawning via a `spawn_agent` / `task` tool with isolated context per sub-agent.

---

## → Verso Implications

### Copy directly

1. **Standard tool-use loop with no mandatory plan phase.** Both Cursor and Zed use the exact same loop. The model plans internally. Don't build a separate "planning agent" layer — it adds latency without improving quality. Verso's `Agent` should be: stream response → collect tool calls → execute (parallel where safe) → append results → repeat.

2. **Handlebars-conditional system prompts.** Gate prompt sections on which tools are active. `{{#if (contains available_tools 'spawn_agent')}}` includes sub-agent coordination instructions only when the user has multi-agent enabled. This is cheap engineering that saves meaningful tokens and reduces model confusion about non-available capabilities. Verso should adopt this as its standard prompt construction pattern.

3. **Per-tool pagination with explicit model instruction.** Grep/list_directory/read_file all paginate (Zed: 20 results/page; Cursor: comparable). The tool description itself tells the model how to paginate via `offset:` parameter. This is the correct interface design — the model drives pagination, not the framework. Verso tool definitions should include pagination parameters and descriptions by default for any tool returning potentially-large results.

4. **Permission tiers with pre-approvable patterns.** Zed's 4-tier permission system (Read / LocalMutation / Network / Shell) is the minimal viable set. The key design: user can pre-approve glob patterns ("always allow edit_file in src/**/*.rs"), not just individual calls. Verso should implement this tier + pattern system natively.

5. **Two separate ignore files for different privacy concerns.** Cursor uses `.cursorignore` (block from AI entirely) vs `.cursorindexingignore` (skip semantic index but allow lexical search). Verso's file-system tools should support analogous scoping so users can prevent secrets from reaching the model while still allowing file search.

6. **Apply model pattern: separate fast model for code application.** The planner decides what to change (expensive, slow model); a separate fine-tuned model applies the actual edit (fast, cheap, specialized). Verso's tool system should support routing specific tool calls to different models — the `edit_file` tool should optionally dispatch to a fast apply model rather than the main reasoning model.

7. **Subagent isolation — context windows don't contaminate.** Both Cursor and Zed give each sub-agent its own isolated context. The parent passes only the task, not the full conversation history. Verso's `spawn_agent` primitive should enforce this: sub-agent receives only (system_prompt + task_instruction), never the parent's message history.

8. **`ask_question` tool to suspend the loop for user input.** Cursor has an explicit `ask_question` tool that suspends the agent turn, injects the user's response, and continues. This is cleaner than the agent ending its turn and hoping the user continues. Verso should have this as a first-class tool.

9. **`stop` hook with `loop_limit` for extending agent turns.** Cursor's stop hook can inject a follow-up message (up to `loop_limit=5` times) without user interaction — enabling fully autonomous multi-step recovery. Verso should support post-turn hooks with auto-inject semantics.

10. **Sub-agents are agentic retrieval, not just tools.** Cursor's Deep Search subagent runs a full ReAct loop (search → read → search-again → synthesize) rather than a single retrieval call. Verso should treat "retrieval" as a possible agent task, not as a single tool call. A `deep_search` primitive that spawns a bounded sub-agent with read-only tools is the right pattern for codebase-scale retrieval.

11. **Grep ancestor-scope context lines.** When returning search results, include 2 context lines around each match AND up to 10 lines of the enclosing function/class scope. This costs tokens but dramatically reduces the model's need for follow-up `read_file` calls. Verso's grep tool should do this by default.

12. **Metrics-driven rule injection (pull-mode rules).** Cursor's `fetch_rules` tool lets the agent retrieve relevant rules on-demand rather than dumping all rules into the system prompt. For Verso agents managing large rule sets (e.g., enterprise deployments with hundreds of project-specific rules), this pattern is essential. The agent calls `fetch_rules(query="working on authentication")` and only gets the auth rules.

### Avoid / anti-patterns

1. **80-tool registries.** Cursor's 80-tool surface is a function of it being a full IDE replacement, not an agent framework. For Verso, the core primitive set should be ~15-25 tools. Extra domain-specific tools should come through MCP, not by baking them into the framework. The Zed approach (25 core tools + MCP extension) is the right model for a framework.

2. **File-based-only agent-to-agent communication.** Cursor's parallel agents communicate only through files and git commits — no native messaging protocol. This works for coding tasks where git is the coordination medium, but is inadequate for general multi-agent workflows. Verso should provide a first-class inter-agent messaging primitive (cf. Codex CLI's `InterAgentCommunication` with `AgentPath` hierarchical addressing).

3. **No session resume (Zed) / only cloud resume (Cursor).** Zed loses all state when the process dies. Cursor's resume works only for cloud-hosted Background Composers. For Verso, session persistence should be a first-class design concern — serialize Thread state (messages + tool results + pending tool calls) to a durable store at configurable intervals so any agent session can resume after crash or process restart.

4. **Model-specific streaming format coupling.** Cursor is mid-migration between two streaming RPC families (legacy Chat + new Unified). The migration is painful because the streaming format was tightly coupled to the agent mode. Verso should design its streaming layer as a pure provider adapter — one internal format, N provider adapters. The agent never sees provider-specific SSE/WebSocket formats.

5. **Capability negotiation per message.** Cursor sends `ComposerCapabilityContext` on every message, letting the server choose model + tool set dynamically. For a framework, this logic should be resolved at session start, not re-negotiated per message. Dynamic capability changes mid-session (Cursor's `switch_mode` tool) are a useful escape hatch but should not be the default path.

### Verso could improve by

1. **Idempotency keys on all side-effecting tool calls.** Cursor added `WithToolsIdempotent` RPC variant to prevent double-execution on reconnect. Verso should make this the default: every tool call carries an idempotency key derived from `(session_id, turn_id, tool_call_index)`. The tool executor deduplicates by key.

2. **Best-of-N model racing as a first-class dispatch primitive.** Cursor's `/best-of-n` dispatches to N models in parallel isolated worktrees and lets the user pick the best diff. Verso could expose this as a built-in evaluation mode: `verso.race(task, models=[...], n=3)` returns N completed results. The eval harness (not the user) could auto-select the best by a scoring function.

3. **Pre-warm hooks for expensive environment setup.** Cursor's `PreWarmPodRequest` fires before the user submits a task, cutting 30s+ boot time to milliseconds. Verso should support a `on_session_open` hook that runs setup tasks (e.g., clone repo, install deps, warm index) before the user's first message arrives.

4. **Multi-version system prompt with A/B testing infrastructure.** Zed maintains `experimental_system_prompt.hbs` and `edit_file_prompt_diff_fenced.hbs` / `edit_file_prompt_xml.hbs` as separate prompt variants. Cursor has versioned prompts (v1.0, v1.2, v2.0) in its x1xhlol leak. Verso should build prompt versioning and A/B test assignment natively — prompt engineering is a continuous iteration cycle, and the framework should support it without manual bucket logic.

5. **Linter/verifier feedback loop baked into the edit-file tool.** Cursor's shadow workspace runs LSP linting on the Apply model's output before returning from the `edit_file` call. Verso's `edit_file` tool could optionally run a configurable verifier (a Python function, a shell command, a lightweight model call) and return both the edit and verification result in one tool response. The agent then decides whether to `reapply` or accept.

6. **`null_result` / `final_result` explicit termination signals.** Cursor has `null_result` (no-op) and `final_result` (agent termination) as explicit tool calls. This is useful for framework-level telemetry (when did the agent decide it was done vs. when did the model simply stop calling tools). Verso should distinguish these in its event stream.
