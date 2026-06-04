# Agentic Architectures

Source file: `core/06_AGENTIC_ARCHITECTURES.md` (2,874 lines)
Covers: Claude Code, Cursor, Devin, Windsurf/Cascade, Manus, Bolt.new, v0, Codex CLI, OpenCode, Google Antigravity, Amp, Amazon Q, xAI Grok 4.20 — sourced from leaked system prompts, open-source Rust/TypeScript code, engineering blogs, and research papers.

---

## core/06_AGENTIC_ARCHITECTURES.md

### Agent Loop Shape

- **Universal primitive** — every production agent is a while-loop:
  ```python
  messages = [system_prompt, user_message]
  while True:
      response = llm.generate(messages, tools=tool_defs)
      if response.has_tool_calls:
          for call in response.tool_calls:
              messages.append(tool_result(execute(call)))
      else:
          return response.text
  ```
  Differences between products are entirely in what surrounds this loop, not the loop itself.

- **Claude Code** (`nO` function, Rust rewrite `claw-code` ~88 lines in `conversation.rs`): single-threaded while-loop; entire state = message array; `AgentRuntime` holds `{session, api_client, tool_executor, permission_policy, system_prompt, max_iterations, usage_tracker}`.

- **Codex CLI** (`codex-rs/core/src/agent_loop.rs`): `AgentLoop.run()` — parses streaming events from OpenAI Responses API, detects tool calls, dispatches to handlers, feeds results back.

- **Manus** (exception): strictly ONE tool call per iteration; must await results before proceeding; ~50 tool calls per typical task.

- **Cursor 2.0**: structured `<flow>` baked into system prompt:
  ```
  1. UNDERSTAND → 2. INVESTIGATE → 3. PLAN → 4. IMPLEMENT → 5. VERIFY → 6. REPORT
  ```
  With `<non_compliance>` self-correction block: "If you find yourself not following these rules, STOP immediately. Re-read the rules. Start over."

- **Devin**: two-mode split — Planning Mode (read-only exploration, `suggest_plan`) → Standard Mode (execution). `<think>` tag provides explicit scratchpad.

- **Manus event-stream** (verbatim): `Events: Message | Action | Observation | Plan | Knowledge | Datasource`. Chronological append-only log; agent reads full stream each iteration.

- **Claude Code `queryLoop()` internal state** (from 512K-line source leak):
  ```typescript
  type State = {
    messages, toolUseContext, autoCompactTracking,
    maxOutputTokensRecoveryCount, hasAttemptedReactiveCompact,
    maxOutputTokensOverride, pendingToolUseSummary,
    stopHookActive, turnCount,
    transition: Continue | undefined   // records WHY the loop continued
  }
  ```
  Seven continue transitions: `max_output_tokens_escalate` (8K→64K retry), `max_output_tokens_recovery` (max 3x), `reactive_compact_retry` (413 error), `collapse_drain_retry`, `stop_hook_blocking`, `token_budget_continuation`, implicit tool-use continuation.

- **Token budget constants**: `COMPLETION_THRESHOLD = 0.9` (90% usage = done), `DIMINISHING_THRESHOLD = 500` (< 500 new tokens = no progress). Early stop if continuation count ≥ 3 AND delta < 500 AND prior delta < 500.

- **Transcript-first reliability**: user message written to disk BEFORE calling API; sessions resumable if process terminates mid-response.

---

### Models (name + provider + role)

| Product | Model(s) | Role |
|---------|----------|------|
| Claude Code | claude-sonnet-4-5 (daily), claude-opus-4-6 (ULTRAPLAN) | Primary agent; Opus for heavy planning |
| Cursor tab | Custom MoE (retrained every 90 min) | Autocomplete; RL from accept/reject |
| Cursor Composer 2 | Kimi K2.5 base (1T params / 32B active) + RL | Main coding agent |
| Cursor apply model | Fine-tuned Llama-3-70B | Applies sketch edits at 1,000 tok/s |
| Devin | Claude Sonnet 4.5 + SWE-1.5 (Cognition custom) | Main + specialized coding |
| Windsurf SWE-1 | Custom from scratch ("Claude 3.5 Sonnet-equivalent but cheaper to serve") | Coding harness |
| Windsurf SWE-1.5 | Open-source base + end-to-end RL, GB200 NVL72 chips, Cerebras inference 950 tok/s | Upgraded coding |
| Manus | Claude Sonnet (primary) + Qwen (routing) | Agent |
| Codex CLI memory Phase 1 | gpt-5.4-mini (reasoning: Low) | Memory extraction, 8 parallel jobs |
| Codex CLI memory Phase 2 | gpt-5.3-codex (reasoning: Medium) | Consolidation |
| Codex CLI guardian | gpt-5.4, 90-second timeout | Security reviewer |
| Codex CLI orchestrator | GPT-5.x family | Main loop |
| Amp main | Claude Opus 4.6 (smart mode) | Only agent that modifies files; 300K input budget |
| Amp Oracle | GPT-5.4 (reasoning: high) | Deep analysis, debugging, code review |
| Google Antigravity | Gemini 3.1 Pro (High/Low), Claude Sonnet 4.6, Claude Opus 4.6, GPT-OSS 120B | Multi-model |
| Antigravity config | Temperature 0.4, TopP 1, MaxTokens 16384, thinking budget 1024 | — |
| Anthropic research system | Opus 4 (orchestrator) + Sonnet (workers 3-5 parallel) | Orchestrator-Workers |
| xAI Grok 4.20 | ~3T MoE backbone; 4 LoRA adapters (~0.3% of params each) | Shared backbone multi-agent debate |

---

### Full Tool Registry

**Claude Code (40+ tools):**
```
File: Read, Edit, MultiEdit, Write, Glob, LS
Search: Grep (ripgrep-based, NOT vector embeddings)
Execution: Bash, BashOutput, KillBash
Web: WebFetch, WebSearch
Notebooks: NotebookEdit
Orchestration: Agent (subagent_type: general-purpose | Explore | Plan), TodoWrite
Mode: ExitPlanMode
MCP: MCPTool, ListMcpResourcesTool, ReadMcpResourceTool
```
KAIROS exclusive tools: `SendUserFile`, `PushNotification`, `SubscribePR`
Hook system: 25+ events (SessionStart, PreToolUse, PostToolUse, Stop, …). Hooks can block, modify `updatedInput`, replace MCP tool output, inject context into subagents.

**Cursor v1.2 (13 tools):**
`codebase_search`, `read_file` (line-range), `run_terminal_cmd` (`require_user_approval` flag), `edit_file` (sketch+apply), `grep_search`, `file_search` (fuzzy), `delete_file`, `list_dir`, `web_search`, `fetch_pull_request`, `create_diagram` (Mermaid), `todo_write` (dependency tracking), `reapply` (escalate failed apply)

**Cursor `edit_file` schema:**
```json
{
  "name": "edit_file",
  "parameters": {
    "target_file": "MUST be generated first before other args",
    "instructions": "Single sentence for the apply model",
    "code_edit": "Code with // ... existing code ... markers"
  }
}
```

**Devin unique tools:**
`<think>` (scratchpad, written to context not executed), `<find_and_edit>` (regex + separate LLM per match), LSP: `go_to_definition`, `go_to_references`, `hover_symbol`, `<deploy_frontend>`, `<deploy_backend>`, `<expose_port>`, Browser (Playwright with `devinid` identifiers)

**Devin `find_and_edit` schema:**
```xml
<find_and_edit dir="." regex="def old_func\(" exclude_file_glob="**/*.test.py"
               file_extension_glob="*.py">
  Instructions. A separate LLM instance evaluates each match independently.
</find_and_edit>
```

**Windsurf (20 tools):**
`replace_file_content` (ReplacementChunks), `trajectory_search` (cross-session), `create_memory`, `deploy_web_app` (Netlify), `browser_preview`, `capture_browser_screenshot`, `capture_browser_console_logs`, `read_browser_page`, `codebase_search`, `grep_search`, `find_by_name` (fd-based), `view_code_item`, `view_file`, `write_to_file`, `run_command` (+ SafeToAutoRun), `command_status`, `search_web`

**Windsurf `replace_file_content` schema:**
```json
{
  "TargetFile": "MUST be generated first",
  "CodeContent": "complete new content",
  "ReplacementChunks": [
    { "TargetContent": "exact text", "ReplacementContent": "replacement", "AllowMultiple": false }
  ]
}
```

**Manus (29 tools):**
```
COMMUNICATION: message_notify_user, message_ask_user
FILE (5): file_read (line ranges), file_write, file_str_replace,
          file_find_in_content (regex), file_find_by_name (glob)
SHELL (5): shell_exec, shell_view, shell_wait,
           shell_write_to_process, shell_kill_process
BROWSER (12): browser_view, browser_navigate, browser_restart,
              browser_click, browser_input, browser_move_mouse,
              browser_press_key, browser_select_option,
              browser_scroll_up, browser_scroll_down,
              browser_console_exec, browser_console_view
WEB (1): info_search_web (date range filters)
DEPLOY (3): deploy_expose_port, deploy_apply_deployment, make_manus_page
CONTROL (1): idle (enters standby = task complete)
```
Key constraint: ONE tool call per iteration.

**Codex CLI tool registry (from `build_specs_with_discoverable_tools()`):**
```
ShellHandler, ShellCommandHandler (Classic or ZshFork),
UnifiedExecHandler (interactive PTY), ApplyPatchHandler,
PlanHandler, McpHandler, McpResourceHandler,
ViewImageHandler, ListDirHandler,
JsReplHandler / JsReplResetHandler (V8 REPL),
ToolSearchHandler / ToolSuggestHandler,
RequestPermissionsHandler / RequestUserInputHandler,
SpawnAgentHandler / WaitAgentHandler / CloseAgentHandler,
BatchJobHandler, DynamicToolHandler,
CodeModeExecuteHandler / CodeModeWaitHandler
```

**Codex CLI multi-agent v2 (6 tools):**
`spawn_agent` (fork_turns: none|all|last-N, agent_type, model, reasoning_effort),
`send_message` (queue-only, no wake), `followup_task` (trigger-turn, wakes target),
`wait_agent` (blocks on `watch::Receiver<u64>` with timeout), `list_agents`, `close_agent`

**OpenCode built-in tools:**
`bash`, `edit` (9 fuzzy strategies), `read` (50KB cap, images/PDFs as base64), `lsp` (real diagnostics), `task` (subagent), `skill` (on-demand SKILL.md load), `apply_patch` (GPT-specific), `batch` (25 parallel executions), `multiedit`, `glob`, `grep`, `ls`, `websearch`, `webfetch`, `codesearch`, `todo`, `question`, `plan`

**v0 (Vercel) tools:**
`Write`, `Read`, `Glob`, `Grep`, `WebSearch`, `WebFetch`, `TodoManager`, `GenerateImage`, `GenerateDesignInspiration` (sub-agent for creative), `GetOrRequestIntegration`, `EnterPlanMode`

**Xai Grok 4.20 inter-agent tools:**
`chatroom_send` (to agent name | array | "All") + `wait` (max 120s/call, 200s global)

---

### Context Assembly / Compaction / Budgets

**Claude Code — three-tier compaction:**
1. **MicroCompact** (zero API calls): surgically truncates high-token tool outputs; preserves cache boundaries; stores oversized outputs externally as stubs.
2. **AutoCompact** (1 API call): triggers at `ContextWindow - 13,000` tokens (~95% capacity); generates ~20K token summary; circuit breaker after 3 consecutive failures (`MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3`) — stopped burning ~250K API calls/day (1,279 sessions, worst session: 3,272 retries).
3. **Full Compact**: compresses everything including older summaries; re-injects recently accessed files (capped 5K tokens each), active plans/TODOs, skill schemas; "summary of summaries" pattern.

Five named strategies in priority order (from source):
`applyToolResultBudget` → `snipCompact (HISTORY_SNIP)` → `microcompact` → `contextCollapse` → `autoCompact`

**Claude Code system prompt assembly** (not monolithic — 110+ conditional strings):
- Split at `SYSTEM_PROMPT_DYNAMIC_BOUNDARY`; static prefix maximizes prompt cache hits; dynamic suffix changes per session.
- 14 cache-break vectors tracked (`promptCacheBreakDetection.ts`): system prompt hash, tool schemas, model selection, beta headers, messages prefix, cache control markers, dynamic tool descriptions, skill changes, memory ranking, file diffs, diagnostics, attachment ordering. Sticky latches prevent mode-toggle false negatives.
- Known bug (`cch=` bug): CLI does global find-and-replace of billing hash across ALL message content before each API call → permanently breaks cache on 50K-context sessions.

**Manus KV-cache architecture (their stated #1 metric, 100:1 input-to-output ratio):**
- Static system prompt prefix (no timestamps)
- Append-only conversation (previous actions/observations NEVER modified)
- Deterministic JSON serialization (sorted keys — must be enforced explicitly; many languages don't guarantee stable ordering)
- Tool masking via **logit manipulation at decoding time** instead of removing tools from the prompt (removal breaks KV-cache prefix). Three modes: Auto, Required, Specified. Tool names use consistent prefixes (`browser_*`, `shell_*`) enabling group-level masking.
- Session affinity routing: session IDs → consistent vLLM workers → warm KV-cache
- Cost: Claude Sonnet cached $0.30/MTok vs uncached $3.00/MTok = **10x savings**

**`todo.md` recitation pattern (Manus):** Agent creates and updates `todo.md` step-by-step; "recites objectives into the end of context" to push goals into recent attention; avoids lost-in-the-middle on multi-step tasks.

**Observation masking (JetBrains NeurIPS 2025, arxiv:2508.21433):**
- Keep ALL action/reasoning history; mask observations outside rolling window (N=10 turns optimal for SWE-agent)
- Result: **52% cost savings + 2.6% solve-rate improvement** over baseline
- Beats LLM summarization in 4 of 5 settings (no API overhead; summarization causes 13-15% longer trajectories)

**Priompt — JSX priority-scored context (Cursor, open-sourced at github.com/anysphere/priompt):**
- Every prompt element has numeric priority; binary search finds minimum priority cutoff to stay within token budget
- `<isolate tokenLimit={N}>`: sub-budget that renders identically regardless of surrounding context → byte-identical API prefixes → cache hits
- Reasonable up to ~10,000 scopes; token counting is bottleneck
- Design caveat: "Adding priorities to everything is sort of an anti-pattern" — best for structured line-by-line file inclusion

**Anthropic API context primitives:**
1. **`compact_20260112`**: triggers at 50K tokens minimum; generates `<summary>` block; all prior messages dropped. Multiple compactions = "summary of summaries." Default prompt: "Write a summary of the transcript… provide continuity so you can continue to make progress in a future context."
2. **`clear_tool_uses_20250919`** (zero inference cost): replaces old `tool_result` content with `"[cleared to save context]"`; keeps `tool_use` record; exempt tools via `exclude_tools: ["memory"]`. Benchmark: 335K peak → 173K peak with 7 clearing events (96.3% of tokens were file-read results).
3. **`memory_20250818`**: six operations: view, create, str_replace, insert, delete, rename.

**Programmatic tool calling (`code_execution_20250825`):** Claude writes Python that calls tools; only `print()` output enters context; tool outputs from programmatic calls NOT added to context. Token reduction: 37% on complex tasks (43,588 → 27,297 avg). Eliminates 19+ inference passes for 20+ tool call sequences.

**Deferred tool loading (`tool_search_tool_regex`):** Mark tools `defer_loading: true`; only names loaded initially; schemas loaded on-demand. Context overhead: 77K → 8.7K tokens (95% reduction). Opus 4 accuracy: 49% → 74%. Opus 4.5: 79.5% → 88.1%.

**Amp "No Compaction" bet:** Instead of compressing (losing nuance), Amp uses thread handoff — new context with pointer to old thread preserving full decision history. Architectural bet: rather start new context than compress.

---

### Memory

**Claude Code four-layer architecture:**
| Layer | Stores | Persistence | Writer |
|-------|--------|-------------|--------|
| CLAUDE.md | Project instructions, conventions | Permanent (version controlled) | Human |
| Auto Memory | Per-session observations, corrections | Survives sessions | Claude (automatic) |
| Session Memory | Conversation continuity | Single session | System |
| autoDream | Consolidated, deduplicated, pruned | Permanent | Claude (background subagent) |

**autoDream — four-phase consolidation (three-gate trigger, cheapest first):**
- Gate 1: 24+ hours since last dream
- Gate 2: 5+ sessions since last dream
- Gate 3: file-based advisory consolidation lock
- Phase 1 Orient → Phase 2 Gather Signal (grep JSONL transcripts) → Phase 3 Consolidate (merge, convert relative dates to absolute, delete contradictions) → Phase 4 Prune (keep MEMORY.md under 200 lines, ~25KB)
- Dream subagent: read-only bash, runs as separate process
- Perf: 913 sessions consolidated in ~9 minutes (observed)
- Theoretical basis: UC Berkeley "Sleep-Time Compute" (arXiv:2504.13171) — pre-processing during idle reduces test-time compute 5x

**Codex CLI memory pipeline:**
- Phase 1: `gpt-5.4-mini` (reasoning: Low), 8 parallel jobs, scans up to 5,000 threads, truncates rollouts to 70% of context window; 570-line extraction prompt; no-op gate: "Will a future agent plausibly act better because of what I write here?"
- Raw memory YAML frontmatter: `{description, task, task_group, task_outcome: success|partial|fail|uncertain, cwd, keywords[]}`
- Phase 2: `gpt-5.3-codex` (reasoning: Medium); produces: `memory_summary.md` (always in system prompt), `MEMORY.md` (keyword-searchable handbook), `skills/<name>/SKILL.md`, `rollout_summaries/<slug>.md`; two modes: INIT and INCREMENTAL UPDATE

**Windsurf `trajectory_search`:** searches across previous conversation sessions (not just current). Limitation: workspace-scoped — doesn't transfer between workspaces.

**Cursor memories (v1.2+):** Persistent key-value store with citations `[[memory:MEMORY_ID]]`; create/update/delete; survives across sessions.

---

### System Prompts (verbatim / near-verbatim)

**Claude Code core instructions (verbatim):**
```
You are an interactive agent that helps users with software engineering tasks.
...
# Doing tasks
- Do not create files unless they're absolutely necessary for achieving your goal.
- Don't add features, refactor code, or make "improvements" beyond what was asked.
- Don't add error handling, fallbacks, or validation for scenarios that can't happen.
- Don't create helpers, utilities, or abstractions for one-time operations.

# Output efficiency
Go straight to the point. Try the simplest approach first without going in circles.
Keep your text output brief and direct. Lead with the answer or action, not the reasoning.
```

**Claude Code Git Safety Protocol (verbatim):**
```
- NEVER run destructive git commands unless user explicitly requests
- CRITICAL: Always create NEW commits rather than amending
- Prefer adding specific files by name rather than "git add -A"
```

**Cursor `<flow>` (verbatim):**
```xml
1. UNDERSTAND → 2. INVESTIGATE (codebase_search, grep, read — NEVER guess)
→ 3. PLAN (create/update TODOs) → 4. IMPLEMENT (run linter, max 3 fix iterations)
→ 5. VERIFY (read modified files) → 6. REPORT

CRITICAL: You MUST reconcile TODOs before making any edits.
```

**Cursor `<maximize_parallel_tool_calls>` (verbatim):**
```xml
When you need to perform multiple INDEPENDENT operations, you MUST call them in parallel.
This is 3-5x faster than sequential calls.
```

**Devin planning/standard split (verbatim):**
```xml
<planning_mode>
AVAILABLE TOOLS: read-only tools only
When ready, call <suggest_plan/> with numbered file list and change order.
IMPORTANT: Do not make any code changes in Planning Mode.
</planning_mode>
```

**Manus event stream (verbatim):**
```
<agent_loop>
5. IMPORTANT: You must issue exactly ONE tool call per iteration of the loop
</agent_loop>
```

**Windsurf SafeToAutoRun (verbatim):**
```
A command is unsafe if it may have some destructive side-effects.
You must NEVER NEVER run a command automatically if it could be unsafe.
You cannot allow the USER to override your judgement on this.
```

**Codex CLI orchestrator prompt (verbatim, 43 lines core):**
```
Prefer multiple sub-agents to parallelize your work. Time is a constraint. When you have a
plan with multiple steps, process them in parallel by spawning one agent per step. Your only
role becomes to coordinate them. Do not perform the actual work while they are working.
```

**Antigravity `// turbo` annotation:** marks a workflow command as auto-run without approval; `// turbo-all` auto-runs every command in the workflow.

---

### Error Handling

**Claude Code `withRetry()` — smart exponential backoff:**
```typescript
const baseDelay = Math.min(BASE_DELAY_MS * Math.pow(2, attempt - 1), maxDelayMs)
const jitter = Math.random() * 0.25 * baseDelay
```
- 529 (overloaded): foreground retries only; background bails immediately
- Opus fallback: after 3 consecutive 529s on non-custom Opus → switch model
- OAuth 401 → force token refresh
- Context overflow 400 → parse token counts from error message, compute new `maxTokensOverride`
- Persistent mode (`UNATTENDED_RETRY`): indefinite retries, 30-min backoff cap, heartbeat every 30s
- ECONRESET/EPIPE (stale keep-alive) → `disableKeepAlive()` before retry

**Reactive compact:** on real 413 error, engine withholds error during streaming, attempts one compaction; if fails, surfaces error and skips stop hooks (prevents death spiral).

**Stop hooks entirely skipped when last assistant message is an API error** (rate limit, prompt-too-long) → prevents death spirals.

**Codex CLI guardian (security reviewer):**
- Model: `gpt-5.4`, 90-second timeout
- Transcript budget: 10K tokens messages, 10K tools, max 40 recent entries
- Structured JSON output: `{risk_level, user_authorization, outcome: allow|deny, rationale}`
- **Fails closed**: timeout/failure/malformed = deny
- Delta mode: sends only new transcript entries on retry (cursor-based)

**Devin CI failure rule:** "If CI fails 3 times, ask the user for help."

**Codex CLI depth limiting:** `config.agent_max_depth` — when exceeded: "Agent depth limit reached. Solve the task yourself."

---

### Exact Constants

| System | Constant | Value |
|--------|----------|-------|
| Claude Code AutoCompact trigger | `ContextWindow - N` | N = 13,000 tokens |
| Claude Code AutoCompact output | ~20K token summary | — |
| Claude Code circuit breaker | `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES` | 3 |
| Claude Code Full Compact file cap | per recently-accessed file | 5K tokens |
| Claude Code COMPLETION_THRESHOLD | 90% context usage = done | 0.9 |
| Claude Code DIMINISHING_THRESHOLD | < N new tokens = no progress | 500 tokens |
| Claude Code early stop | continuation_count ≥ 3 AND delta < 500 AND prior delta < 500 | — |
| Claude Code max_output_tokens escalation | 8K cap → retry at | 64K |
| Claude Code max_output_tokens recovery | max retries | 3 |
| Claude Code UNATTENDED_RETRY backoff cap | — | 30 minutes |
| Claude Code h2A queue throughput | >10,000 messages/second | — |
| Claude Code bash security checks | sequential pre-shell validators | 23 |
| Claude Code blocked Zsh builtins | — | 18 |
| Claude Code KV-cache break vectors | — | 14 |
| Claude Code autoDream memory limit | MEMORY.md | 200 lines / ~25KB |
| Claude Code autoDream gates | time + session + lock | 24h + 5 sessions |
| Claude Code autoDream perf | 913 sessions consolidated | ~9 minutes |
| Claude Code feature flags | compile-time via Bun `feature()` | 44 flags |
| Claude Code tool results retained in context | 5 most recent, older removed | — |
| Codex CLI memory Phase 1 | parallel jobs | 8 |
| Codex CLI memory Phase 1 | max threads scanned | 5,000 |
| Codex CLI memory Phase 1 | rollout truncation | 70% of context window |
| Codex CLI memory Phase 1 extraction prompt | — | 570 lines |
| Codex CLI memory Phase 2 consolidation prompt | — | 698 lines |
| Codex CLI guardian timeout | — | 90 seconds |
| Codex CLI guardian transcript budget | messages / tools | 10K / 10K tokens, max 40 entries |
| Codex CLI apply_patch context lines | above/below change | 3 lines |
| Codex CLI BNF grammar | — | 76 lines |
| Codex CLI agent names | hardcoded `agent_names.txt` | recycled when exhausted |
| Manus input:output ratio | — | 100:1 |
| Manus KV-cache savings | cached vs uncached Sonnet | $0.30 vs $3.00/MTok (10x) |
| Manus sandbox session persistence | — | up to 14 days |
| Manus Firecracker boot time | — | ~150ms |
| Anthropic `clear_tool_uses` keep | most recent tool uses | 4 |
| Anthropic tool-result clearing baseline | 335K → 173K peak tokens | 7 clearing events |
| Anthropic programmatic tool calling | token reduction | 37% |
| Anthropic deferred loading impact | context overhead | 77K → 8.7K tokens (95% reduction) |
| Anthropic Opus 4 accuracy (deferred tools) | 49% → 74% | — |
| Cursor apply model speed | — | ~1,000 tok/s |
| Cursor speculative edits speedup | vs vanilla Llama-3-70B | 13x |
| Cursor Composer 2 RL volume | vs base training | 4x |
| Cursor Tab RL cycle | — | every 90 minutes |
| Cursor Tab RL reward | accepted / rejected / silence | +0.75 / -0.25 / 0 |
| Cursor Tab RL results | fewer suggestions / higher acceptance | 21% / 28% |
| Cursor Tab RL deploy cycle | — | 1.5-2 hours |
| Cursor Tab daily requests | — | 400M+ |
| Cursor agent sandboxing impact | reduced interruptions | 40% |
| Cursor Bugbot parallel passes | — | 8 |
| Cursor Bugbot resolution rate | original → agentic | 52% → 70%+ |
| Cursor Bugbot PRs reviewed | monthly | 2M+ |
| Devin blockdiff snapshot | 20GB in | ~200ms |
| Devin total snapshot+transfer | — | ~6.5 seconds |
| Devin VM startup vs EC2 | — | 10x faster |
| Devin concurrent VMs | — | tens of thousands |
| Devin planning RFT back-and-forths | baseline → after RFT | ~8 → ~4 (2x speedup) |
| Devin RFT rollouts per sample | burst size | ~32 per sample, ~500 simultaneous |
| Devin SWE-1.5 inference speed | via Cerebras | up to 950 tok/s |
| Devin SWE-1.5 harness overhead | per step | up to 2s |
| Manus typical tool calls per task | — | ~50 |
| Amazon Q success rate | multi-agent vs single | 85% higher |
| Amazon Q SWE-bench | — | 66% |
| Anthropic multi-agent research | improvement over single-agent Opus 4 | 90.2% |
| Anthropic multi-agent tokens | vs chat / vs single-agent | ~15x / ~4x |
| Anthropic tool-test agent improvement | rewriting tool descriptions | 40% decrease in completion time |
| Anthropic 3-factor model | explains variance | 95% (token usage 80%, tool calls, model) |
| Observation masking (JetBrains) | cost reduction + solve rate | 52% cheaper, +2.6% improvement |
| Observation masking window | optimal for SWE-agent | N=10 turns |
| SWE-bench top score | Claude Mythos Preview | 93.9% |
| SWE-bench novel issues | best agents | ~18-20% |
| OpenCode batch tool | parallel executions | 25 |
| Xai Grok 4.20 hallucination reduction | MARL debate | ~12% → ~4.2% (65% reduction) |
| Xai Grok 4.20 cost | vs single pass | 1.5-2.5x (NOT 4x — shared KV cache) |
| Xai Grok 4.20 agents | standard / heavy mode | 4 / 16 |
| Xai Grok 4.20 wait tool | per-call / global timeout | 120s / 200s |

---

### Multi-Agent Coordination

**Anthropic Orchestrator-Workers pattern (90.2% improvement on research eval):**
```
LeadResearcher (Opus 4)
  → spawns 3-5 parallel Subagents (Sonnet)
    each makes 3+ parallel tool calls
  → LeadResearcher merges outputs
  → CitationAgent post-processes
```
- Subagents store work in external systems, pass lightweight references → prevents info loss on context truncation
- Lead uses extended thinking for planning; subagents use interleaved thinking post-tool-execution
- A tool-testing agent rewrites tool descriptions → 40% decrease in task completion time

**Claude Code Coordinator Mode — four-phase:**
1. Research — workers investigate codebase in parallel
2. Synthesis — coordinator reads findings, crafts "Synthesized Spec" with file paths + line numbers
3. Implementation — workers execute targeted changes per spec
4. Verification — workers test via VERDICT system (adversarial proof, not existence checking)
Key: when coordinator mode active, main session's tool pool REDUCED to coordinator-only tools (NO Bash, FileRead, FileEdit, Grep, Glob, WebSearch — purely management layer).

**Claude Code KAIROS (autonomous daemon, 150+ references in source):**
- Receives `<tick>` prompts on intervals; 15-second blocking budget per decision cycle
- Append-only daily logs; GitHub webhook subscriptions; 5-minute cron refresh cycles
- Exclusive tools: `SendUserFile`, `PushNotification`, `SubscribePR`
- Integration with Claude Dispatch mobile app; persists across session restarts

**Claude Code Agent Teams (experimental):**
- Team lead spawns teammates (separate Claude Code instances with own contexts)
- Shared task list with dependency tracking + file-locking for race-free claiming
- Peer-to-peer mailbox messaging
- Display: in-process (Shift+Down to cycle) or split panes

**Codex CLI subagent forking:**
- `SpawnAgentForkMode::FullHistory` — child gets complete conversation
- `SpawnAgentForkMode::LastNTurns(usize)` — truncated fork
- Filter `keep_forked_rollout_item()`: strips tool calls/outputs; keeps only system/developer/user messages + assistant final answers
- Three built-in roles: `default`, `explorer` (read-only, fast), `worker` (execution, warned about concurrent edits)
- Sub-agents inherit parent's full conversation history and system prompt for 90% KV-cache discount on shared context

**Amp multi-agent (50 tools, three-tier permission):**
- Main Agent (Opus 4.6) only agent that can modify files; 300K input budget
- Oracle (GPT-5.4) separate context for deep analysis
- Librarian (unspecified) searches GitHub public + private repos
- Task Subagents: isolated, cannot communicate with each other; main agent receives only final summaries; handoff via `@T-[thread-id]` mentions

**Amazon Q — Critic with rollback:**
- Debugger AI: multi-agent with intelligent backtracking, recognizes dead-end paths
- Memory Management Agent: appends relevant portions to inter-iteration memory
- Critic Agent: detects dead ends, triggers rollback to known-good previous state
- 85% higher success rate vs single-agent

**CodeTree (NAACL 2025, Salesforce Research):**
- Four agents: Thinker (strategies) + Solver (implementations) + Debugger (refinement) + Critic (Refine|Abort|Accept)
- `Score(node) = Score(execution_feedback) + Score(critic_feedback)`
- Dynamic tree expansion — low-scoring branches pruned
- GPT-4o 20-sample budget: HumanEval 95.1%, MBPP 98.7%, CodeContests 43.0%

**xAI Grok 4.20 — Native multi-agent debate:**
- ~3T MoE backbone; 4 agents are LoRA adapters (~0.3% params) on SAME backbone
- Cross-attention debate (NOT message-passing) — agents exchange critique embeddings
- Trained end-to-end with PPO-style MARL
- 4 agents: Grok (Captain/coordinator), Harper (Research, X firehose), Benjamin (Logic, math/proofs), Lucas (Contrarian, bias detection)
- `chatroom_send` + `wait` tools baked into model's tool system
- Heavy mode: 16 agents (domain specialists), triggered by `reasoning_effort="high"/"xhigh"` or `agent_count=16`

**Cognition anti-pattern ("Don't Build Multi-Agents"):**
- "Actions carry implicit decisions, and conflicting decisions carry bad results."
- Recommended: single-threaded linear agent with compression layer for context overflow
- Caveat: Anthropic's 90.2% improvement comes from ~15x more tokens, not architecture; 80% of variance = token usage

---

### Streaming Protocol

- **Claude Code**: SSE with streaming tool call chunks; `h2A` dual-buffer async queue (>10,000 msg/s); `kq5` streaming function for mid-stream user injection; `text_delta` and `tool_use` blocks streamed separately.
- **Codex CLI**: parses streaming events from OpenAI Responses API (`content_block_start`, `content_block_delta`, `message_stop`).
- **OpenCode**: client-server SSE over Bun+Hono HTTP server; sessions survive terminal disconnects/SSH drops/machine sleep; TUI frontend is Zig core + SolidJS reconciler.
- **Antigravity**: Gemini 3.1 Pro streaming; `webp` video recording for browser subagent.
- **Xai Grok 4.20**: gRPC (xai-proto confirmed); `chatroom_send` tool for inter-agent messaging.

---

### Edit Format Taxonomy

| Format | Product | Mechanism | Speed | Token cost |
|--------|---------|-----------|-------|-----------|
| Exact string replace (`old_str`→`new_str`) | Claude Code | Must be unique in file | Fastest | Low |
| Sketch + apply model | Cursor | Smart model sketches with `// ... existing code ...`; Llama-3-70B applies | ~1,000 tok/s (13x speedup) | 2-model cost |
| `find_and_edit` regex + per-match LLM | Devin | Main agent regex; separate LLM per match | Parallelized | High |
| ReplacementChunks array | Windsurf | Batch non-adjacent edits; `AllowMultiple` flag | Single call | Medium |
| V4A Unified Diff | Codex CLI | `*** Begin Patch`, 3-line context, `@@` class names, 4-pass fuzzy match | Standard | Low |
| Full file (no diffs) | Bolt.new | Complete file content always | Simple | High (large files) |
| Hashline content-hash anchors | OpenCode (alt) | Lines tagged with short hash; agent edits by anchor not text | No reproduction errors | Medium |
| 9-strategy fuzzy fallback | OpenCode | Exact→whitespace-normalized→indentation→trimmed→Levenshtein | Progressive | Medium |
| Provider-adaptive | OpenCode | GPT→apply_patch; Claude/other→edit+write | Auto-switched | — |
| `diff` / `udiff` / `whole` | Aider | 5 formats matched to model; unified diff reduced GPT-4 Turbo "lazy coding" 3x | Varies | Varies |

**V4A BNF grammar (Codex CLI):**
```
Patch := Begin { FileOp } End
FileOp := AddFile | DeleteFile | UpdateFile
UpdateFile := "*** Update File: " path NEWLINE [MoveTo] { Hunk }
Hunk := "@@" [" " header] NEWLINE { (" "|"-"|"+") text NEWLINE } [EndOfFile]
```

**Codex CLI four-pass fuzzy matching (apply_patch):**
1. Exact match
2. Trim trailing whitespace (rstrip)
3. Trim both sides
4. Unicode normalization (typographic dashes→ASCII, smart quotes→plain, NBSP→regular)

**Key finding from hashline benchmark:** Fuzzy matching triggered ZERO times across 134 edits. LLMs either reproduce source text exactly or hallucinate completely — the near-miss case fuzzy matching targets does not occur in practice.

---

### Sandbox as Architecture

| Approach | Product | Boot time | Key mechanism |
|----------|---------|-----------|---------------|
| macOS Seatbelt (SBPL) | Codex CLI, Cursor | Negligible | `sandbox-exec`, deny-by-default, dynamic policy assembly |
| Linux Landlock + seccomp-BPF | Codex CLI, Cursor | Negligible | Capability-based filesystem; blocks `connect`/`bind`/`listen`/`accept`; applied before `execvp()` |
| Custom VM hypervisor (otterlink) | Devin | 10x faster than EC2 | blockdiff: XFS CoW + FIEMAP metadata-only diff; 200ms 20GB snapshot |
| Firecracker microVMs | Manus (E2B), Cursor cloud | ≤125ms | True hardware isolation per VM; `<5 MiB` overhead; up to 150 VMs/sec/host |
| Bash input validation | Claude Code | None (pre-shell) | 23 sequential regex/AST checks BEFORE command reaches shell; catches parser differentials sandbox misses |

**Claude Code 23 bash security checks (complete list):**
`INCOMPLETE_COMMANDS`, `JQ_SYSTEM_FUNCTION`, `JQ_FILE_ARGUMENTS`, `OBFUSCATED_FLAGS`, `SHELL_METACHARACTERS`, `DANGEROUS_VARIABLES`, `NEWLINES`, `COMMAND_SUBSTITUTION`, `INPUT_REDIRECTION`, `OUTPUT_REDIRECTION`, `IFS_INJECTION`, `GIT_COMMIT_SUBSTITUTION`, `PROC_ENVIRON_ACCESS`, `MALFORMED_TOKEN_INJECTION`, `BACKSLASH_ESCAPED_WHITESPACE`, `BRACE_EXPANSION`, `CONTROL_CHARACTERS`, `UNICODE_WHITESPACE` (13 non-ASCII spaces U+00A0→U+FEFF), `MID_WORD_HASH`, `ZSH_DANGEROUS_COMMANDS` (18 blocked builtins), `BACKSLASH_ESCAPED_OPERATORS`, `COMMENT_QUOTE_DESYNC`, `QUOTED_NEWLINE`

Tree-sitter WASM integration: when AST is available, it is authoritative → entire classes of parser differential attacks impossible.

**Anti-debug hardening (Codex CLI):** `ptrace(PT_DENY_ATTACH)` macOS, `prctl(PR_SET_DUMPABLE, 0)` Linux, core dump prevention, `DYLD_*`/`LD_*` env sanitization — all via `#[ctor::ctor]` (pre-main execution).

---

### RL-Trained Subagents

**Cursor Tab (continuous RL):** custom MoE retrained every 90 min from accept/reject (+0.75/-0.25/0); 400M+ daily requests; deploy-data-retrain cycle 1.5-2 hours; result: 21% fewer suggestions, 28% higher acceptance.

**Cursor Composer 2 training pipeline:**
- Base: Kimi K2.5 (1T params / 32B active MoE)
- Continued pretraining: code-dominated, 32K → 256K context via RoPE scaling
- RL occurs in realistic Cursor sessions (Anyrun Firecracker VMs, 500+ pods/second)
- RL volume = 4x base training
- Router replay: during inference, engine returns selected expert indices per token per MoE layer; training overrides router to match → prevents numerical divergence
- Self-summarization via RL: model learns when/how to summarize as natural consequence of long-horizon reward
- Algorithm: GRPO variant; removed length standardization term (length bias); skipped advantage normalization by std dev (over-amplifies noise when all rollouts equal)
- Infrastructure: Ray + PyTorch + ThunderKittens; tens of thousands H100s (Azure) + B300s

**Devin Planning RFT:** restricted to `read_file` + `shell`; ~32 rollouts/sample, ~500 simultaneous in fresh otterlink VMs; reward = file prediction F1 score; emergent: model learned parallel tool calls and branching exploration without explicit teaching; 100 training samples outperformed base GPT-5.

**SWE-grep (Cognition):** RL for parallel code retrieval; 8 parallel tool calls/turn max, 4 turns max; reward `R = A × P` (accuracy × parallelism factor); F1 with beta=0.5 (precision > recall — context pollution more harmful than omission); SWE-grep-mini: 2,800+ tok/s; full SWE-grep: 650+ tok/s; in real-world vibe-coding, search = 56.6% of tokens (vs 12% on SWE-bench).

**Relace FAS:** dedicated subagent (own context window) with 5 tools (`view_file`, `view_directory`, `grep_search`, `bash`, `report_back`); 20 turns → 5 turns (4x latency reduction); 12-24s → 1-2s per turn.

---

### Permission / Safety Models

| Product | Model |
|---------|-------|
| Claude Code Auto mode | Two-layer classifier: Stage 1 single-token yes/no (8.5% FPR); Stage 2 CoT only if flagged (reduces to 0.4% FPR, 17% FNR). Classifier sees only user messages + tool payloads (assistant messages stripped). |
| Codex CLI | 3×3 matrix: sandbox mode (read-only / workspace-write / danger) × approval policy (untrusted / on-request / never). Session-scoped approval caching reduces fatigue. |
| Windsurf | `SafeToAutoRun` boolean per command; user cannot override |
| Devin | Never force push; never `git add .`; ask user after 3 CI failures |
| Claude Code 4-tier | Default / AcceptEdits / Plan / Auto |

**Claude Code anti-distillation (three layers):**
1. Fake tool injection (`ANTI_DISTILLATION_CC` flag + GrowthBook flag) — decoy definitions poison competitors' training data
2. Connector-text summarization with cryptographic signatures — compressed reasoning returned to API traffic
3. Client attestation header (`x-anthropic-billing-header`) computed below JS runtime in Bun's Zig HTTP stack

**Xai Grok 4.20 security incident:** PromptArmor demonstrated hidden 1px text on webpage could make Gemini exfiltrate `.gitignore`-protected files to webhook.site. Google classified as "intended behavior." Called "Lethal Trifecta": untrusted input + private data + external communication channels all open simultaneously.

---

## → Verso Implications

- **The loop is the spec.** Every production agent, from Claude Code to Codex CLI to Manus, uses the same 8-line while-loop. Verso's core loop must be exposed as a first-class API — not hidden inside framework abstractions. Users should be able to read `verso run()` and see: build messages → call model → if tool_calls execute tools → loop; if done return. This is the correct complexity level for the durable layer.

- **One tool call per iteration (Manus) is a valid architectural choice for reliability.** Verso should support both: multi-tool parallel (default, Cursor/Claude Code style) AND single-tool sequential mode as an opt-in flag. Single-tool mode simplifies debugging and prevents "running ahead of reality."

- **Parallel tool calls must be first-class, not bolted on.** Cursor mandates `<maximize_parallel_tool_calls>` as "3-5x faster." OpenCode supports 25 parallel executions in a batch tool. Verso's tool executor must resolve all tool calls in a response concurrently (async gather), not sequentially.

- **The `<flow>` pattern (Cursor 2.0) is a system-prompt primitive worth adopting.** Verso should ship a default agent flow: UNDERSTAND → INVESTIGATE → PLAN → IMPLEMENT → VERIFY → REPORT. This is not framework logic — it lives in the system prompt, which means users can override it. Baking it as a default removes a class of reliability failures.

- **Context compaction is not optional — it is a production necessity.** Claude Code built a circuit breaker because 1,279 sessions hit 50+ consecutive failures, burning 250K API calls/day. Verso must ship compaction as a standard feature with the same circuit-breaker pattern (fail after N consecutive failures, not infinitely). Target trigger: 80-95% of context window. Default: keep 5 most recent tool results, drop older ones (Claude Code constant).

- **KV-cache hygiene must be a first-class design constraint.** Manus achieved 10x cost reduction purely from architectural decisions: static prompt prefix, append-only context, deterministic JSON serialization, tool masking via logits instead of tool removal. Verso's loop must never modify previous messages — append only. System prompt construction must separate a stable prefix from a dynamic suffix. Verso docs must call out "adding timestamps to your system prompt breaks cache on every call."

- **Tool masking via logit manipulation > tool removal for state machines.** When a tool is unavailable in a given state, Verso should mask it at the logit level (if provider supports it) rather than removing it from the tool list. Removing changes the prompt → breaks KV-cache. This is the Manus pattern. For providers that don't support logit masking, the alternative is keeping tools but using the `disable_parallel_tool_use` constraint with explicit state machine routing in the system prompt.

- **Observation masking beats LLM summarization as a context reduction strategy.** JetBrains NeurIPS 2025: 52% cost savings + 2.6% solve-rate improvement with zero API overhead. Verso should implement this as the DEFAULT context management strategy: keep all action/reasoning history; replace old tool outputs (beyond a rolling window of N=10 turns by default) with `"[observation cleared]"` placeholders. Reserve LLM compaction as a fallback for when observation masking alone is insufficient.

- **Deferred tool loading (tool search) should be Verso's default for large tool sets.** Anthropic's implementation dropped context overhead from 77K to 8.7K tokens (95% reduction) and improved Opus 4 accuracy from 49% to 74%. Verso should load tool schemas on-demand when the agent requests them — not upfront. MCP tools especially should be deferred by default.

- **Programmatic tool calling is the highest-leverage context optimization.** 37% token reduction by letting the model write code that calls tools and only receiving stdout. Verso should expose `code_execution` as a first-class tool type that grants the model this capability, with `allowed_callers` on subordinate tools.

- **Memory must be multi-layer.** A single key-value store is insufficient. Verso must support: (1) project-level static instructions (CLAUDE.md/AGENTS.md pattern), (2) per-session in-memory state, (3) cross-session persistent key-value, (4) an optional consolidation pass (autoDream pattern) triggered by time+session gates. Implement the "Will a future agent plausibly act better?" no-op gate for memory writes.

- **The edit format is a product decision, not a formatting preference.** Verso should ship with opinionated defaults: exact string replace for Claude-family models; apply_patch for OpenAI-family models (OpenCode's provider-adaptive pattern). Make the format pluggable but provide sensible defaults that match model training data.

- **Agent roles are useful and should be built-in.** Codex CLI ships `default`, `explorer` (read-only, fast), `worker` (execution, explicit ownership) as named role presets. Verso should ship these as first-class role types that configure: tool access, model, reasoning effort, context scope. Don't force users to re-invent roles via system prompt.

- **Plan mode (read-only phase before execution) should be an opt-in first-class mode.** Devin and Codex CLI both implement this. Plan mode: read-only tool access only; outputs a structured plan; transitions to execute mode explicitly. Verso should support `mode: "plan" | "execute" | "auto"` as a session parameter.

- **The stop hook lifecycle is critical for production use.** Claude Code fires: standard stop hooks → TaskCompleted hooks → fire-and-forget background tasks (memory extraction, autoDream). Verso must provide a hook system with at minimum: `pre_tool_call` (can block/modify), `post_tool_call`, `on_stop` (after model finishes), `on_error`. Stop hooks must be skipped when the last message is an API error (prevents death spirals — Claude Code's hard-learned lesson).

- **Sandboxing should be opt-in but ready.** Verso doesn't need to ship its own hypervisor (that's Devin/E2B territory), but it should provide first-class integration points for: Firecracker/E2B cloud sandboxes, OS-native sandboxing (Seatbelt/Landlock) for local execution, and Docker for middle ground. The sandbox should be a parameter on tool execution, not a separate system.

- **Bash input validation is complementary to sandboxing, not a substitute.** Claude Code's 23 checks catch attacks sandboxes miss (parser differentials, IFS injection, Unicode whitespace). Verso should provide a `shell_safety_checks` middleware that runs before any bash execution, with the tree-sitter AST path as the gold standard and regex fallback.

- **Multi-agent should be simple to compose but not the default.** Cognition's finding is correct: dispersed decision-making produces incompatible outputs. Verso's answer is the Anthropic orchestrator-worker pattern: one orchestrator (big model) decomposes; N workers (smaller models) execute in parallel; orchestrator synthesizes. The key implementation constraint: each worker must have a clear objective, output format spec, and explicit task boundaries. Verso should enforce this structurally when spawning subagents.

- **Sub-agent context fork modes matter.** Codex CLI's `FullHistory` vs `LastNTurns(n)` vs filtered fork (strips tool calls, keeps reasoning) covers the real use cases. Verso should implement all three: full clone for deep context inheritance, N-turn slice for lightweight subagents, reasoning-only fork (strips tool outputs) for orchestration chains.

- **The `todo.md` recitation pattern is worth adopting as a first-class memory primitive.** Manus: pushing current goals into the end of context avoids the lost-in-the-middle problem. Verso should support a `todo` tool with auto-injection of current TODO state into every request's context (near the end, not the beginning).

- **Transcript-first reliability (Claude Code): write user message to disk before calling API.** Verso should persist each turn before making the API call, enabling session resumability even if the process terminates mid-response. This is a one-liner that eliminates an entire class of lost-work failures.

- **Tool descriptions are the highest-ROI prompt engineering surface.** Anthropic found a tool-testing agent that rewrites tool descriptions reduced task completion time by 40%. Verso should make tool descriptions easily updatable/overridable, and should ship a tool description testing harness.

- **The "3 factors explain 95% of performance variance" finding shapes Verso's roadmap.** Token usage (80%), tool call count, model choice. This means: Verso's most impactful features are context management (maximize effective tokens), parallel tool execution (maximize tool throughput), and model routing (use the right model per subtask). Graph complexity, custom workflows, and middleware chains account for < 5% of variance — do not over-invest there.

- **xAI Grok 4.20 proves that multi-agent debate works when agents share context.** Cognition's critique of multi-agent is about dispersed context; Grok solves it by putting all agents on the same backbone. For Verso's multi-agent mode: prefer shared-context patterns (subagents with full conversation fork, or shared external state) over isolated-context patterns (message-passing only). If agents share a context, they can debate productively; if they communicate only via messages, Cognition is right.

- **The escape hatch for graph cases (Verso's founding thesis) is validated.** Only specific cases genuinely need graph structure: durable execution with checkpoint-resume (otterlink blockdiff pattern), explicit backtracking / critic-with-rollback (Amazon Q, CodeTree), and HITL with approval gates (Devin planning→standard, Codex `GuardianApproval`). Everything else is better served by a clean ReAct loop with good tooling. Verso should provide graph primitives as an opt-in escape hatch, not as the primary abstraction.
