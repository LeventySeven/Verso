# Agentic AI Deep

Source file: `core/12_AGENTIC_AI_DEEP.md` (2602 lines, last updated 2026-04-13)

---

## core/12_AGENTIC_AI_DEEP.md

### Universal Agent Loop

- The entire loop is 5–10 lines: `messages = [system_prompt] + [user_message]` → `while True` → `llm.generate(messages, tools=...)` → if tool calls: execute + append results, else return.
- **All complexity lives outside the loop**: context management, tool design, security, error recovery. The loop itself is not where systems differentiate.
- Three production variants: (1) single-threaded while-loop (Claude Code, Codex CLI) — messages are the only state, no state machine; (2) event stream with one-tool-per-turn (Manus) — strictly ONE call per iteration, forces grounded sequential execution; (3) multi-agent debate (Grok 4.20) — not a loop, 4 agents share KV cache and cross-attend during inference.

---

### Claude Code — Reference Implementation

**Architecture — Six Layers:**
1. Terminal UI (React/Ink)
2. Query Engine (~46K lines)
3. Tool System (40+ tools, permission gates)
4. Context Management (5 compaction strategies, 14 cache-break vectors)
5. Permission/Security (23 bash checks, 2-layer classifier, hook system)
6. Agent Orchestration (fork, teammate, worktree execution models)

**Agent Loop (Rust rewrite, claw-code/runtime/conversation.rs):**
- `while True` → `api_client.create_message(system_prompt, messages, tool_definitions)` → push assistant message → if no tool calls: break → for each tool call: `tool_executor.execute(tool_call, permission_policy)` → push tool result → `iterations += 1` → check `max_iterations`.
- "Messages are the only state." Single append-only message array. Sessions persistable, replayable, compressible.

**System Prompt Assembly (NOT monolithic):**
- Dynamically assembles 110+ prompt strings conditionally based on environment.
- Hard boundary: `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` separates static prefix (cached) from dynamic suffix (env tools, MCP server definitions, CLAUDE.md, memory index, active plans, skill schemas).
- Single character difference in static prefix breaks the **entire** prompt cache.
- Tracks **14 cache-break vectors** with sticky latches preventing mode toggles from invalidating cache.

**Tool System (40+ tools):**
| Category | Tools |
|----------|-------|
| File Ops | Read, Edit, MultiEdit, Write, Glob, LS |
| Search | Grep (ripgrep-based, NOT vector embeddings) |
| Execution | Bash, BashOutput, KillBash |
| Web | WebFetch, WebSearch |
| Notebooks | NotebookEdit |
| Orchestration | Agent (general-purpose/Explore/Plan), TodoWrite |
| Mode | ExitPlanMode |
| MCP | MCPTool, ListMcpResourcesTool, ReadMcpResourceTool |

- **Edit format:** Exact string replacement (`old_string` → `new_string`). Must be unique in file. No diffs, no line numbers. Intentionally simple — fewer failure modes.
- **Deferred tool loading:** MCP tools marked `defer_loading: true`; only names consume context; full schemas loaded on-demand. **85% context reduction** (72K → 8.7K tokens for 50+ tools).

**Context Compaction (Three-Tier):**
- **Tier 1 MicroCompact** (zero API calls): surgically truncates high-token tool outputs, preserves cache boundaries.
- **Tier 2 AutoCompact** (one API call): triggers at `ContextWindow - 13,000` tokens (~95% capacity), generates ~20K token structured summary. Circuit breaker after 3 consecutive failures (1,279 sessions hit 50+ consecutive failures → ~250K wasted API calls/day globally before fix).
- **Tier 3 Full Compact**: re-injects recently accessed files (capped 5K tokens each), active plans/TODOs, skill schemas.
- **API-level compaction (beta):** `betas=["compact-2026-01-12"]`, `compaction_config={"trigger_token_count": 50000}`.
- **Tool-Result Clearing** `clear_tool_uses_20250919`: zero inference cost, replaces old tool_result content with `"[cleared to save context]"`, keeps tool_use record. Benchmark: 335K peak → 173K peak (7 clearing events).
- **Combined deployment:** clear at 50K tokens (keep 6 most recent), compact at 180K tokens.

**Permission Model (Auto Mode):**
- Two-layer classifier: Stage 1 fast single-token yes/no (8.5% FPR on raw traffic); Stage 2 chain-of-thought only if Stage 1 flags (reduces FPR to **0.4%**).
- Classifier sees only user messages + tool call payloads; assistant messages and tool outputs **stripped** (prevents model from talking classifier into bad calls).
- Final rates: **0.4% FPR, 17% FNR** on production traffic.
- Bash security: 23 sequential checks per shell command, 18 blocked Zsh builtins, zero-width Unicode injection prevention, IFS null-byte blocking.
- **Hook system:** 25 events (`PreToolUse`, `PostToolUse`, `PostToolUseError`, `SessionStart`, `SessionStop`, `ConversationStart`, `ConversationStop`, `SubagentStart`, `SubagentStop`, `SubagentError`, `TeammateIdle`, `TaskCreated`, `TaskCompleted`, `TaskFailed`, `WorktreeCreate`, `WorktreeDestroy`, `PermissionDenied`, `PermissionGranted`, `Compact`, `PostCompact`, `MemoryRead`, `MemoryWrite`, `Elicitation`, `ElicitationResult`, `Stop`). Hooks can block, modify tool input, replace MCP tool output, inject context into subagents.
- Hook handler types: `command` (shell script, stdin=JSON), `http` (POST), `prompt` (fast single-turn LLM, no tools), `agent` (full subagent with tools).
- `PreToolUse` with `"defer"` action (v2.1.89+): returns `stop_reason: "tool_deferred"` + `deferred_tool_use` block; resume by passing result in next `query()`.

**Sub-Agents:**
- Spawned via `Agent` tool with `subagent_type` parameter: `general-purpose` (full tool access), `Explore` (fast, read-only), `Plan` (architecture planning, no writes).
- Each gets own context window. Foreground (blocking) or background (async notification). Can run in isolated **git worktrees**.
- **The only channel parent → subagent is the `Agent` tool's prompt string.** Pass file paths, error messages, decisions explicitly.
- Return path: only the subagent's **final message** (verbatim) returns as tool result. All intermediate tool calls and outputs are isolated and discarded.
- Transcripts: `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl`. Retention: 30 days (`cleanupPeriodDays`).
- Background subagent permissions: pre-approved = inherited; anything not pre-approved = auto-denied; `AskUserQuestion` fails silently.

**Subagent File Format (all frontmatter fields):**
```yaml
name: researcher          # REQUIRED
description: >            # REQUIRED — routing mechanism
tools: [Read, Glob, Grep] # allowlist; omit = inherits all
disallowedTools: [Bash]   # denylist
model: sonnet             # sonnet|opus|haiku|inherit|full model ID
permissionMode: default   # default|acceptEdits|auto|dontAsk|bypassPermissions|plan
maxTurns: 30
skills: [nia]
mcpServers: [...]
hooks: {...}
memory: project           # user|project|local
background: false
effort: medium            # low|medium|high|xhigh|max
isolation: worktree       # worktree = temporary git worktree
color: blue
initialPrompt: >          # auto-submitted first user turn
```

**Model resolution order:** (1) `CLAUDE_CODE_SUBAGENT_MODEL` env var → (2) per-invocation `model` param in Agent tool call → (3) subagent `model` frontmatter → (4) main session's model.

**Agent Teams (Experimental, shipped Feb 2026):**
- Enable: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (v2.1.32+).
- Architecture: Team Lead + N teammates, each teammate gets own Claude Code instance + fresh context.
- Coordination: Shared Task List (pending → in_progress → completed | blocked) with dependency tracking + file-locked claiming; Peer-to-Peer Mailbox (any→any, or broadcast, no routing through lead); shared filesystem.
- Team tools: `SendMessage`, `TeamCreate`, `TeamDelete`, `TaskCreate`, `TaskGet`, `TaskList`, `TaskUpdate`, `TaskStop`.
- Recommended: 3–5 teammates, 5–6 tasks per teammate.
- Quality hooks: `TeammateIdle` (exit 2 = keep working), `TaskCreated` (exit 2 = prevent creation), `TaskCompleted` (exit 2 = prevent mark-complete).
- Hard limits: one team per session, no nested teams, no session resumption for in-process teammates, task status can lag (eventual consistency).
- **Why P2P matters:** peer-to-peer messaging prevents lead from becoming bottleneck — solves Anthropic's own orchestrator-worker limitation where lead can't steer subagents mid-run.

**Parallel tool execution within a single turn:**
- Read-only tools (Read, Glob, Grep, read-only MCP tools): concurrent.
- State-modifying tools (Edit, Write, Bash): sequential.
- Custom SDK tools: sequential by default; set `readOnly: true` (TS) or `readOnlyHint: True` (Python) to enable concurrency.

**Git Worktree Isolation:**
- `isolation: worktree` per-subagent → each invocation gets temporary git worktree, auto-cleaned if no changes.
- Session-level: `claude --worktree <name>` creates worktree at `<repo>/.claude/worktrees/<name>/`, branch `worktree-<name>` from `origin/HEAD`.
- `.worktreeinclude` file copies gitignored files (`.env`, secrets) to new worktrees.
- `WorktreeCreate` hook **replaces** `git worktree add` entirely; hook must print worktree path on stdout.

**Python SDK — `AgentDefinition` dataclass:**
```python
@dataclass
class AgentDefinition:
    description: str           # REQUIRED
    prompt: str                # REQUIRED
    tools: list[str] | None = None
    model: Literal["sonnet","opus","haiku","inherit"] | None = None
    skills: list[str] | None = None
    memory: Literal["user","project","local"] | None = None
    mcpServers: list[str | dict] | None = None
```

**`ClaudeAgentOptions` — multi-agent fields:**
```python
allowed_tools: list[str]                 # must include "Agent" to spawn subagents
agents: dict[str, AgentDefinition]
max_turns: int | None
max_budget_usd: float | None             # hard stop at USD spend
hooks: dict[HookEvent, list[HookMatcher]]
resume: str | None                       # resume by session ID
effort: Literal["low","medium","high","xhigh","max"] | None
```

**`ResultMessage` subtypes:** `success`, `error_max_turns`, `error_max_budget_usd`, `error_during_execution`, `error_max_structured_output_retries`.

**`stop_reason` values (2026):** `end_turn`, `tool_use`, `max_tokens`, `tool_deferred` (v2.1.89+), `tool_deferred_unavailable`.

**Package:** `@anthropic-ai/claude-agent-sdk@0.2.114` (renamed from `@anthropic-ai/claude-code-sdk`). Requires `@anthropic-ai/sdk@^0.81.0`, `@modelcontextprotocol/sdk@^1.29.0`, peer: `zod@^4.0.0`.

**Unreleased internal systems (from npm source map leak, 512K lines TS):**
- **KAIROS** (150+ references): always-on autonomous daemon. systemd-style service, periodic `<tick>` prompts, 15s blocking budget per decision cycle (`ASSISTANT_BLOCKING_BUDGET_MS = 15_000`), tools: `SendUserFile`, `PushNotification`, `SubscribePR`. Append-only daily logs: `logs/YYYY/MM/YYYY-MM-DD.md`. Note: sleeping >5min causes prompt cache to expire.
- **autoDream**: memory consolidation during idle. Three gates (all required): ≥24h since last consolidation, ≥5 sessions since last, consolidation lock acquired. Four phases: Orient → Curate → Consolidate → Prune+Index.
- **Three-Layer Memory Architecture:**
  - Layer 1: `MEMORY.md` index (~150 chars/pointer, always loaded, truncated at line 200).
  - Layer 2: topic files (`memory/*.md`), loaded on-demand; frontmatter: name, description, type, tags.
  - Layer 3: daily transcript logs (`logs/YYYY/MM/YYYY-MM-DD.md`), append-only, never loaded, grep-only (source for autoDream Curate phase).
- **ULTRAPLAN**: offloads complex planning to cloud containers running Opus 4.6, 30-minute thinking windows.
- **Anti-distillation**: Layer 1 injects fake/decoy tool definitions; Layer 2 buffers assistant text between tool calls, returns only cryptographically signed summaries.
- **44 feature flags:** KAIROS, BUDDY (Tamagotchi), COORDINATOR_MODE, VOICE_MODE, WORKFLOW_SCRIPTS, BRIDGE_MODE, ANTI_DISTILLATION_CC, NATIVE_CLIENT_ATTESTATION.
- Cache boundary constant: `SYSTEM_PROMPT_DYNAMIC_BOUNDARY = "<!-- DYNAMIC -->"`. Anti-distillation DRM marker: `cch=ed1b0`.

**Anthropic Managed Agents API (April 8, 2026):**
- Hosted infrastructure for autonomous agents: sandboxing, permissions, state persistence, error recovery.
- Agents run for hours; sessions persist through network disconnections.
- Pricing: standard token rates + $0.08/session-hour. Access via `managed-agents-2026-04-01` header.

---

### OpenAI Codex CLI — Rust Runtime

**Stack:** Apache 2.0, 94.9% Rust, ~90 crates. Source: `github.com/openai/codex`.

**Architecture:**
- Execution modes: TUI (`codex`), Exec (`codex exec`), App Server (`codex app-server`), MCP Server (`codex mcp-server`).
- `Codex` struct manages sessions via Submission Queue (`Op` messages: UserTurn, InterAgentCommunication, ExecApproval, Compact, Interrupt, ~20 more) and Event Stream results (`EventMsg`). Dedicated Tokio task dispatches operations sequentially.
- `AgentControl` is central orchestrator.

**Agent Loop (`codex-rs/core/src/session/turn.rs` — `run_turn`):**
- Type: **streaming sampling loop** (not ReAct, not plan-execute).
- Steps: (1) pre-sampling compact if near limit; (2) drain pending `Op::UserTurn` messages; (3) build `Prompt { history, tools, parallel_tool_calls, base_instructions }`; (4) `client_session.stream(prompt)` → async event stream; (5) for each `OutputItemDone(tool_call)` → `ToolOrchestrator` → `FuturesOrdered in_flight`; (6) when `Completed` event arrives → drain all in_flight; (7) mid-turn compact if `token_limit_reached && needs_follow_up`; (8) `SamplingRequestResult { needs_follow_up: bool }` — true: continue, false: run stop hooks, return.
- No hardcoded `max_iterations`; loop runs until model stops returning tool calls, context overflow (triggers auto-compact), or cancellation.

**Error paths:**
- `NetworkError` → retry with exponential backoff (max 3).
- `ContextOverflow` → return error to orchestrator.
- `CancellationToken` → clean shutdown, ghost commit if configured.

**Edit Format — V4A Unified Diff:**
```
*** Begin Patch
*** Update File: src/main.ts
@@ function startApp
 import { loadConfig } from './config';
+import { initialize } from './new_module';
 export function startApp() { ... }
*** End Patch
```
3 lines context, `@@` uses function/class names for disambiguation. **Four-pass fuzzy matching**: exact → rstrip → both-trim → Unicode normalization (typographic dashes → ASCII, smart quotes → plain).

**Sandbox (per-platform):**
- **macOS Seatbelt:** Three `.sbpl` policies assembled dynamically. `(deny default)` then selective allows. Chrome-inspired.
- **Linux Bubblewrap + seccomp:** `--new-session --die-with-parent --unshare-user/pid/net --ro-bind / /`. seccomp blocks: `connect`, `accept`, `bind`, `listen`, `ptrace`, `io_uring_*`. Only `AF_UNIX` sockets allowed.
- Anti-debug: `ptrace(PT_DENY_ATTACH)` on macOS, `prctl(PR_SET_DUMPABLE, 0)` on Linux. All via `#[ctor::ctor]` (pre-main).
- **`SandboxPolicy` enum (exact Rust):** `DangerFullAccess`, `ReadOnly { network_access: bool }`, `ExternalSandbox { network_access }`, `WorkspaceWrite { writable_roots, network_access, exclude_tmpdir_env_var, exclude_slash_tmp }`.
- For autonomous parallel work: `approval_policy = "never"` + `sandbox = "workspace-write"`.

**Multi-Agent System (v2, full source):**

Config limits:
```toml
[agents]
max_threads = 6
max_depth = 1
```

**Six v2 tools:**
| Tool | Semantics |
|------|-----------|
| `spawn_agent` | `fork_turns` (none/all/last-N), agent_type, model, reasoning_effort |
| `send_message` | Queue-only delivery — does NOT wake sleeping agent |
| `followup_task` | Trigger-turn delivery — wakes target, interrupts current turn |
| `wait_agent` | Blocks on `watch::Receiver<u64>` with timeout |
| `list_agents` | All live agents with status |
| `close_agent` | Terminates sub-agent |

**Three built-in roles:**
```
"explorer": read-only, fast/authoritative, separate config block with different model
"worker": execution, explicit ownership, warned about concurrent edits at spawn
"default": no config overlay
```

**Inter-Agent Communication Protocol — first-class primitive (`codex-rs/core/src/protocol.rs`):**
```rust
pub struct InterAgentCommunication {
    pub author: AgentPath,
    pub recipient: AgentPath,
    pub other_recipients: Vec<AgentPath>,  // broadcast
    pub content: String,
    pub trigger_turn: bool,                // wakes sleeping agent
}
```
`AgentPath` — Unix-style hierarchical addressing: `/root` (orchestrator), `/root/researcher`, `/root/researcher/worker`. Format: lowercase + digits + underscores only. True async P2P without routing through root.

**`SpawnAgentForkMode` enum:** `None` (empty history), `FullHistory` (complete parent conv), `LastNTurns(usize)`.
Stripped at fork: tool calls, tool outputs, reasoning/thinking tokens, ghost commit snapshots.
Kept: user messages, developer messages, system messages, final-answer assistant messages.

**`ThreadManager` (`thread_manager.rs`):**
```rust
const THREAD_CREATED_CHANNEL_CAPACITY: usize = 1024;
pub struct ThreadManager {
    threads: Arc<RwLock<HashMap<ThreadId, Arc<CodexThread>>>>,
}
```
`FuturesUnordered` drives concurrent shutdown.

**`Mailbox`:**
```rust
pub struct Mailbox {
    sender: tokio::sync::mpsc::UnboundedSender<InterAgentCommunication>,
    trigger_watch: tokio::sync::watch::Sender<u64>,  // monotonic sequence number
}
```
`trigger_turn: false` → `QueueOnly`, recipient wakes on own schedule.
`trigger_turn: true` → `TriggerTurn`, increments watch, recipient wakes immediately.

**`AgentRegistry` — CAS Loop + Nickname Pool:**
- `try_increment_spawned()` = compare-and-swap to atomically claim spawn slot, returns `SpawnReservation` RAII guard.
- Nickname pool: "Alice", "Bob", "Charlie"... When pool exhausted: "Alice the 2nd". Metric on rollover: `codex.multi_agent.nickname_pool_reset`.

**Complete 9-step spawn_agent → running thread dispatch flow:**
1. Model returns `FunctionCall(name="spawn_agent", args={...})`
2. `ToolOrchestrator` → `MultiAgentV2::SpawnAgent` handler
3. `AgentRegistry.try_increment_spawned()` — CAS loop claims slot → `SpawnReservation` acquired
4. `fork_history(mode)` — filters parent history per `SpawnAgentForkMode`
5. New `ThreadId` generated; `CodexThread` constructed with forked history, `developer_instructions` (16 rules), role config, own `Mailbox`, `SubAgentSource` lineage
6. `ThreadManager` inserts `CodexThread` into `RwLock<HashMap>`
7. Tokio task spawned: `CodexThread.run_submission_loop()`
8. Parent receives `SpawnAgentResult { thread_id, nickname, agent_path }`
9. Parent can: `send_message`, `followup_task`, `wait_agent`, `list_agents`, `close_agent`

**`SPAWN_AGENT_DEVELOPER_INSTRUCTIONS` — 16 verbatim rules auto-injected at spawn:**
1. You are a sub-agent spawned by an orchestrating agent.
2. Complete the task and report back.
3. Do not ask for clarification unless truly ambiguous.
4. Be concise in final response — orchestrator reads it programmatically.
5. Sub-agents are limited to depth 1.
6. Prefer multiple sub-agents for parallelizable work.
7. Do not perform actual work while waiting for sub-agents — use wait_agent.
8. Use send_message for non-urgent coordination; followup_task to interrupt.
9. Call list_agents before spawning.
10. Close agents with close_agent when work complete.
11. Read freely from shared workspace; take care with concurrent writes.
12. If two agents must write to the same file, coordinate via send_message first.
13. Emit a concise summary as final message.
14. Do not exceed configured max depth.
15. Ghost-commit your work before signalling completion if long-running.
16. Report tool failures explicitly — do not silently retry more than twice.

**Ghost Commits (`codex-rs/utils/git/src/ghost_commits.rs`):**
```rust
const DEFAULT_COMMIT_MESSAGE: &str = "codex snapshot";
const DEFAULT_IGNORE_LARGE_UNTRACKED_DIRS: usize = 200;      // skip dirs > 200 files
const DEFAULT_IGNORE_LARGE_UNTRACKED_FILES: u64 = 10 * 1024 * 1024;  // skip > 10MB
// Ignored dirs: .git, node_modules, target, .venv, __pycache__, dist, build, .next, .nuxt, vendor
```
`create_ghost_commit()`: uses `GIT_INDEX_FILE` env var → temp index file → stages without touching `.git/index` → creates unreferenced commit (no branch update) → returns SHA.
`restore_ghost_commit(sha)`: `git restore --source <sha> --worktree -- .`

**Parallel Tool Calls within a turn (`codex-rs/core/src/tools/parallel.rs`):**
```rust
let _guard = if supports_parallel {
    Either::Left(lock.read().await)    // concurrent read lock
} else {
    Either::Right(lock.write().await)  // exclusive write lock
};
```
MCP servers opt-in per-server: `supports_parallel_tool_calls = true`.

**Codex as MCP Server:** `codex mcp-server` exposes `codex` tool (prompt, model, profile, cwd, approval-policy, sandbox, config, base_instructions, developer_instructions, compact_prompt) and `codex-reply` tool (thread_id, prompt). Returns `{ structuredContent: { thread_id, transcript } }`.

**Guardian System:**
- Model: `gpt-5.4`, 90-second timeout.
- Transcript budget: 10K tokens messages + 10K tools, max 40 recent entries.
- Risk taxonomy: low/medium/high/critical.
- **Fails closed:** timeout/failure/malformed = deny. Delta mode: only sends new transcript entries on retry.

**Memory System (Two-Phase Background Pipeline):**
- **Phase 1 Extraction:** `gpt-5.4-mini` (reasoning: Low), 8 parallel jobs, scans up to 5,000 threads. 570-line prompt. No-op gate: "Will a future agent plausibly act better because of what I write here?"
- **Phase 2 Consolidation:** `gpt-5.3-codex` (reasoning: Medium). Produces: `memory_summary.md` (always in system prompt), `MEMORY.md` (searchable handbook), `skills/<name>/SKILL.md` (reusable procedures), `rollout_summaries/`.

**Prompt Composition (Multi-Template stack):**
```
base_instructions/default.md          (276 lines)
  + model-specific prompt              (81–332 lines per GPT version)
    + personality template             (18–20 lines)
      + collaboration mode             (8–129 lines)
        + sandbox/approval policy      (1–58 lines)
          + memory read_path.md        (130 lines)
            + apply_patch BNF grammar  (76 lines)
              + AGENTS.md              (user-provided, 32KB cap)
```
Model differentiation: GPT-5.1 gets stronger autonomy rules; GPT-5.2 gets parallelism instructions; Codex models get anti-slop guidance.

**Codex Cloud / Symphony:**
- Runs in isolated Linux microVMs preloaded with GitHub repo. Container caches state 12 hours. Internet disabled by default during execution.
- **Symphony Framework (March 2026):** Elixir-based orchestration on BEAM VM. Polls Linear board → creates isolated workspaces → dispatches Codex agents → delivers PRs.

**Model options for multi-agent work:**
- `gpt-5.4` — primary orchestrator, frontier coding + reasoning + computer use.
- `gpt-5.4-mini` — parallel subagents, fast/cheap for read-heavy exploration.
- `gpt-5.3-codex-spark` — near-instant text-only (research preview, Pro only).
- Any OpenAI-compatible via `model_providers.<custom>` config (Azure, Ollama, etc.).
- Reasoning effort levels: `minimal` / `low` / `medium` / `high` / `xhigh`.

---

### Cursor — RL-Trained Coding Agent

**Models:**
- **Composer 2:** base Kimi K2.5 (1.04T total, 32B active, MoE + MLA) + continued pretraining on code + large-scale RL (4× base training volume). RL algorithm: policy gradient, single-epoch regime. KL estimator: `k₁ = −log r` (NOT k₃). Length penalty: `C_length{k,q}(x) = [(1+kx)^(1-q) − 1] / [k(1−q)]` (non-linear). Self-summarization via RL reward (model learns WHEN to summarize, not hardcoded). Router replay for MoE training stability. Hardware: NVIDIA B300, MXFP8/NVFP4, AdamW.
- **Tab Model:** custom MoE retrained every **90 minutes** from accept/reject signals. Deployed multiple times daily across **400M+ daily requests**. Fastest RL training loop in production AI.
- **SWE-1 (Windsurf):** trained on shared timeline data model from actual user sessions. SWE-1.5 uses end-to-end RL on thousands of GB200 NVL72 chips, inference via Cerebras at 950 tok/s with speculative decoding.

**Apply Model (key innovation):**
- Smart model (GPT-5/Claude) generates "sketch" with `// ... existing code ...` markers.
- Apply model (fine-tuned Llama-3-70B) interprets sketch → performs file edit.
- **Speculative edits:** existing source code IS the draft token sequence. Server validates longest matching prefix between speculation and actual generation. Result: **~1,000 tok/s** (13× speedup over vanilla Llama-3-70B).
- Decouples "knowing what to change" from "performing the file edit."
- On failure: reapply tool escalates to smarter frontier model.
- **Stateless parallel Apply:** 8 parallel agents → each makes independent Fireworks AI Apply call, no shared state. Throughput: ~8,000 tok/s across 8 simultaneous instances.

**Agent Loop (from leaked Cursor 2.0 system prompt):**
```xml
<flow>
1. UNDERSTAND: Read user's request carefully
2. INVESTIGATE: codebase_search, grep_search, read_file
3. PLAN: Create/update TODOs
4. IMPLEMENT: edit_file or search_replace
   - ALWAYS update TODOs as you complete steps
   - ALWAYS run linter after edits (max 3 fix iterations)
5. VERIFY: Read modified files
6. REPORT: Summarize
</flow>
<non_compliance>
If you find yourself not following these rules, STOP.
Re-read the rules. Start over from the last correct step.
</non_compliance>
<maximize_parallel_tool_calls>
Multiple INDEPENDENT operations MUST be parallel.
This is 3-5x faster than sequential calls.
</maximize_parallel_tool_calls>
```
Hardcoded limit: **max 3 debugging iterations** before seeking user input.

**Background Agents — Five-Layer Harness:**
```
Layer 1: Interface   — Slack, GitHub, Linear, cursor.com/agents, mobile, IDE
Layer 2: Orchestration — task planning, model routing, parallel dispatch
Layer 3: Execution   — VM infrastructure + trust boundaries
Layer 4: Verification — computer use, video capture, screenshots, log aggregation
Layer 5: Output      — PRs with multimedia artifacts (video proof-of-work)
Model sits BELOW all five layers. Swapping GPT-5/Claude/Gemini/Composer 2 changes nothing above.
```

**Parallel execution limits:**
- Local (Cursor 3): up to **8 agents** in parallel across isolated git worktrees.
- Cloud: up to **10–20 parallel agents** per user, each in own Ubuntu VM on AWS. Results appear as draft PRs with video proof-of-work.
- **Isolation gap:** parallel agents in isolated branches do NOT see each other's in-progress work. Two agents building against same interface will diverge on field names until merge time.

**Model Racing (`/best-of-n`):**
- Same task dispatched to multiple models simultaneously (GPT-5, Claude, Gemini, Composer 2). Harness picks best result. Available as `/best-of-n` command in Cursor 3 UI. Unique to Cursor — no other coding agent has this pattern built in.

**Anyrun Platform:**
- >500 pods/second per cluster (Firecracker VM launch rate).
- Live migration, filesystem-level forking (copy-on-write snapshot), memory-level snapshotting.
- Per-VM: full Ubuntu + Chromium, terminal + browser + full desktop, git worktree branch pre-loaded.
- **Anygress:** injected root CA in every VM, per-request policies at TCP layer, drops sensitive headers before forwarding.

**`worktrees.json` — Atomic coordination protocol:**
```json
{ "tasks": [{ "id": "task-1", "assignedTo": null, "status": "pending" }],
  "worktreeCleanupIntervalHours": 6,
  "worktreeMaxCount": 20,
  "coordinationDir": ".coord-<SESSION>" }
```
Atomic mkdir locking: each agent atomically attempts `mkdir .coord-<SESSION>/task-N.json/` — exactly one wins per task (POSIX atomicity).

**StopHook schema (`.cursor/hooks.json`):**
```typescript
interface StopHookInput {
  conversation_id: string;
  status: "completed" | "aborted" | "error";
  loop_count: number;
}
```

**Bugbot (Code Review Agent — 8-pass pipeline):**
1. Run 8 parallel passes with randomized diff ordering.
2. Combine similar bugs into buckets.
3. Majority voting — multi-pass flags strengthen signal.
4. Merge each bucket into clear description.
5. Categorical filtering.
6. Validator model — dedicated false-positive reducer.
7. Deduplication against previous runs.
Resolution rate: 52% → 70%+. Processes 2M+ PRs/month.

**Weight sync — geo-distributed inference:**
Training completes (H100/B300 US) → delta compression → sharded upload → US Fireworks AI cluster + EU Fireworks AI cluster (both reconstruct independently).

**Cursor MCP: client only.** Cannot be orchestrated by external agents via MCP.

---

### Grok 4.20 — Native Multi-Agent Inference

**Architecture (novel — not prompt engineering):**
- Not separate model instances. Not MoE. A new inference-time computation primitive.
- 4 persona adapters (~0.3% params each) on a shared ~3T MoE backbone with shared KV cache.
- **Agents:** Grok (Captain, coordinator + synthesis), Harper (research + fact-checking, X firehose 68M tweets/day + web search), Benjamin (math/code/logic), Lucas (creative/contrarian, bias detection).
- Flow: complexity router → Captain decomposes → 4 agents analyze concurrently → **cross-attention debate** (2–4 rounds, ≤180 tokens) exchanging "critique embeddings" → Captain synthesizes final response.
- Cost: **1.5–2.5× single agent**, not N×. Sub-agent state encrypted.

**Inter-agent protocol (from leaked prompt):**
```
chatroom_send(to="Harper", message="Verify the claim that...")
chatroom_send(to="All", message="Summary of findings so far...")
wait(timeout=30)  // max 120s/call, 200s global
```
11 tools for all agents: `code_execution` (Python 3.12.3), `browse_page`, `view_image`, `web_search`, `x_keyword_search`, `x_semantic_search` (min_score_threshold=0.18), `x_user_search`, `x_thread_fetch`, `search_images`, `chatroom_send`, `wait`.

**Training (MARL):**
- PPO-style Multi-Agent RL: reward = answer quality + debate efficiency (jointly optimized). Penalties: premature consensus, factual drift, redundant computation.
- Adapters trained end-to-end with debate protocol.
- RLHF at pre-training scale (~6× efficiency, xAI's key differentiator).
- Continuous RL from production ("improvements every week").

**Heavy Mode:** Victor as orchestrator + 12 domain specialists = 16 agents total. Triggered by `reasoning_effort="high"/"xhigh"` or `agent_count=16`. Hallucination drops ~12% → ~4.2% (65% reduction).

**Infrastructure:** API server Rust + axum (confirmed via serde error format), inference SGLang (RadixAttention, FP8 quantization), training JAX + Rust + Kubernetes on Colossus (555K GPUs, 2GW), internal domain `mouseion.dev` (GCP staging).

**vs alternatives:**
- vs AutoGen/CrewAI: those create separate instances with different system prompts; Grok shares weights + KV cache.
- vs MoE: MoE routes tokens at FFN level; Grok's agents are persona-level routing at output/adapter level.
- vs self-consistency/voting: those sample independently; Grok's agents exchange critique embeddings during debate.

---

### Devin — Full VM Computer-Use Agent

**Architecture (Devin 2.0):**
- Compound AI system: **Planner** (high-reasoning model, task decomposition), **Coder** (specialized, trained on trillions of code tokens), **Critic** (adversarial security/logic review with rollback capability).

**Unique tools:**
- `<think>` — explicit scratchpad (written to context, not executed).
- `<find_and_edit>` — regex + **separate LLM instance per match location**. Main agent specifies regex + edit instructions; secondary LLM invoked independently for each match. Parallelizes multi-site refactors.
- LSP: `go_to_definition`, `go_to_references`, `hover_symbol`.
- `<deploy_frontend>`, `<deploy_backend>`, `<expose_port>`.
- Browser: Playwright-based with `devinid` element identifiers.

**VM Hypervisor (otterlink):**
- Custom-built by Cognition. VMs over containers (dev environments often need Docker).
- **blockdiff** (open-sourced): XFS copy-on-write + Linux FIEMAP for metadata-only diffing. 20GB snapshot in ~200ms. Written in a few hundred lines of Rust.
- Scale: tens of thousands of concurrent VMs. 10× faster than EC2 startup.

**Planning Subagent (RFT-Trained):**
- Reinforcement Fine-Tuning with file prediction F1 score as reward.
- ~32 rollouts/sample, ~500 simultaneous in fresh otterlink VMs.
- Emergent: model learned parallel tool calls and branching exploration without being taught.
- Baseline ~8–10 back-and-forths → after RFT: ~4 (2× speedup).

**"Don't Build Multi-Agents" Thesis (Cognition, June 2025):**
- Parallel multi-agent = fragile due to context isolation. Alternative: single-threaded linear agent + compression layer for overflow.
- Counter-evidence (within 24h): Anthropic multi-agent research system showed 90.2% improvement.
- **Resolution (2026 consensus):** naive multi-agent (separate instances, no shared state) = fragile. Production multi-agent WITH shared context primitives (shared KV cache, task lists, external artifacts, file locking) = works.

---

### Windsurf/Cascade — Flow-Aware Coding

**SafeToAutoRun:** every terminal command classified as safe/unsafe. "NEVER run unsafe commands automatically even if user asks." Hardcoded policy, cannot be overridden by user.

**Unique tools:**
- `trajectory_search` — searches across **previous conversation sessions** (cross-session memory).
- `create_memory` — persistent memory database.
- `EPHEMERAL_MESSAGE` — injects transient context that doesn't persist in history.
- `deploy_web_app` — Netlify deployment built-in.
- Browser: `browser_preview`, `capture_browser_screenshot`, `read_browser_page`.

---

### Manus — Event Stream + KV-Cache Mastery

**Event Stream Architecture:**
- Event types: Message | Action | Observation | Plan | Knowledge | Datasource.
- Chronological log; agent reads full stream each iteration.
- Planner module generates numbered pseudocode plans injected as events.
- Knowledge module injects task-relevant best practices.

**KV-Cache Optimization (their #1 metric):**
```
INPUT:OUTPUT RATIO = 100:1
→ Cache optimization matters 100x more than output optimization

RULES:
1. System prompt prefix is STATIC (no timestamps) → maximum cache prefix hits
2. Conversation is APPEND-ONLY (never modify previous actions) → all prior KV-cache reused
3. JSON serialization is DETERMINISTIC (sorted keys) → byte-identical prefixes
4. Session IDs → consistent vLLM workers → warm KV-cache reuse
5. LOGIT MASKING instead of tool removal → tool list constant; mask unavailable during decoding

COST: Claude Sonnet cached $0.30/MTok vs uncached $3.00/MTok = 10x savings
```

**One tool per turn (strict):** 29 tools, ONE call per iteration. Must await result before next action. ~50 tool calls per typical task. Prevents model from "running ahead" of reality.

**todo.md Pattern:** agent creates and updates `todo.md` step-by-step — "recites objectives into the end of context" to keep plan in recent attention. Mitigates lost-in-the-middle problem.

**Sandbox:** Firecracker microVMs via E2B (self-hosted). Ubuntu 22.04, ~150ms boot, sessions persist up to **14 days**.

---

### GitHub Copilot — Fleet + Rubber Duck

**Coding Agent:** runs inside GitHub Actions runner. Creates `copilot/issue-{number}` branch. Reads AGENTS.md. Iterative loop: write → test → diagnose → revise. Mandatory three-layer security scan (CodeQL, secret scanning, dependency review) before PR.

**`/fleet` (Parallel Multi-Agent, April 2026):**
- Orchestrator decomposes tasks into work items with dependencies.
- Dispatches independent items as background sub-agents simultaneously.
- Each sub-agent gets own context window but shares filesystem.
- **Critical limitation:** if two agents write to same file, last one wins silently.

**Rubber Duck (Cross-Model Review, April 2026):**
- Second model from **different AI family** as independent reviewer. Claude orchestrator → GPT-5.4 reviewer (and vice versa).
- Activates at three checkpoints: post-planning, post-implementation, pre-test execution. Also triggers reactively when agent gets stuck.
- Performance: Claude Sonnet 4.6 + Rubber Duck closes **74.7%** of the gap between Sonnet and Opus. **+4.8%** on hardest problems.
- Proves pairing models from different families catches errors neither catches alone.

---

### Google ADK — Context Engineering Formalized

**Context as "compiled view over tiered stateful systems":**
```
Session/State ← conversation container + key-value scratchpad + Events
    │
Memory ← long-lived, searchable knowledge (MemoryService)
    │
Artifacts ← binary/textual data, name+version addressed, lazy-loaded
    │
Named, ordered processors compile Working Context per-invocation:
  system instructions + agent identity + selected history +
  tool outputs + memory results + artifact references
    │
Auto-filters irrelevant events, summarizes older turns, tracks tokens
```
Two agent categories: `LlmAgent` and Workflow Agents (Sequential, Parallel, Loop). Multi-agent via Agent-as-Tool pattern and LLM-driven transfer.

**Project Mariner (Browser Agent):** Chrome extension, Gemini 2.0 (2M context). Observe-Plan-Act loop: captures browser state (pixels + web elements), formulates action sequence, executes. Cloud VM isolation. 83.5% on WebVoyager.

---

### Amazon Q — Critic + Rollback

**Unique architecture:** Critic agent analyzes progress + provides information to debugger agent. If dead end detected → **rolls back to previous state**. Most other agents lack explicit rollback.
Multi-file solutions. Explores codebase rather than single-file fixes.
Code transformation pipeline: source → verify build/test → apply deterministic changes → build/test in target.

---

### Sierra — Constellation Multi-Model Routing

**Constellation:** 15+ models (frontier, open-weight, proprietary from OpenAI, Anthropic, Meta). Tasks modularly abstracted into: retrieval, classification, tool-calling, policies, tone. Each routed to best-suited model based on latency, precision, context length, tone sensitivity.
**Reliability:** built-in redundancy, continuous monitoring, automated failover, multi-model cross-checking, supervisor enforcement.
**Experience Manager:** every annotated conversation becomes a conversation test. Thousands run in parallel during development and before every release.

---

### Multi-Agent Orchestration Patterns

**Three production patterns:**

**Pattern 1 — Orchestrator-Workers with External Shared State:**
- Lead (expensive model) → spawns N workers (cheap model) → workers store output in EXTERNAL systems (files, artifacts) → workers pass lightweight REFERENCES back to lead → lead synthesizes.
- Examples: Anthropic research system (90.2% improvement), Codex CLI subagents, Copilot `/fleet`.
- Pro: clean separation, model tiering for cost. Con: lead can't steer workers mid-execution.

**Pattern 2 — Shared-Backbone with Persona Adapters:**
- Single ~3T MoE backbone → 4 LoRA persona adapters (~0.3% params), shared KV cache → cross-attention debate → coordinator synthesizes.
- Example: Grok 4.20 (ONLY one doing this).
- Pro: 1.5–2.5× cost (not N×), shared context solves isolation. Con: requires same backbone.

**Pattern 3 — Peer-to-Peer with Shared Task List:**
- Team Lead → N teammates (each own context) + Shared Task List + P2P Mailbox + File Locking.
- Example: Claude Code Agent Teams.
- Pro: no bottleneck at lead, true parallel execution. Con: coordination overhead.

**Decision tree:**
```
Is task decomposable into truly independent subtasks?
├── No → single agent with tool parallelization (Devin approach)
└── Yes
    ├── Do subtasks need to share context heavily?
    │   ├── Yes → Shared backbone (Grok 4.20) or shared filesystem (Agent Teams)
    │   └── No → Orchestrator-Workers (Anthropic pattern, Codex subagents)
    └── Do you need cross-model error checking?
        └── Yes → Add Rubber Duck reviewer (cheapest multi-agent pattern)
```

**Critical finding:** "Agent architecture matters more than model quality." Same model (Opus 4.5) scored **50.2–55.4%** on SWE-bench Pro depending on harness. 5-point spread = context management + tool orchestration entirely.

---

### Context Engineering

**Paradigm shift:** "what configuration of context produces the desired behavior?" replaces "what words do I use?"

**Observation Masking (best academic finding):**
Keep full action + reasoning history. **Mask older observations** with placeholders. Retain recent 10 turns of full observations. Result: **52% cost savings with 2.6% solve-rate IMPROVEMENT.** Why: old tool outputs rarely re-read, but old reasoning informs current decisions.

**Multi-Agent Context Math (Phase Transition paper, January 2026):**
Star topologies saturate at approximately `N ~ W/m` agents (W = window size, m = per-agent message size). Hierarchical trees bypass this. **Compaction at each level isn't optional — it's a mathematical requirement for scaling.**

**KV-Cache Optimization Hierarchy:**
| Technique | Who | Impact |
|-----------|-----|--------|
| Static prompt prefix (no dynamic content) | Manus | 10× cost reduction |
| Append-only context (never modify history) | Manus | Preserves all KV-cache |
| Deterministic JSON serialization | Manus | Byte-identical prefixes |
| Session routing to consistent workers | Manus | Warm KV-cache reuse |
| Logit masking (not tool removal) | Manus | Constant tool list |
| Prompt cache boundary tracking (14 vectors) | Claude Code | Prevent accidental invalidation |
| Deferred tool loading (names only) | Claude Code | 85% context reduction |
| MicroCompact (surgical tool output trim) | Claude Code | Zero API calls |
| `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` split | Claude Code | Static prefix cached |

**Token usage:** multi-agent uses 15× more tokens than chat, 4× more than single agent. "The tokens ARE the performance." Context engineering = which tokens.

---

### Agent Communication Protocols

- **MCP (Model Context Protocol):** Anthropic → Linux Foundation. Client-server. Standard for tool connectivity. Dominant — Claude, Codex, Cursor, Gemini CLI, Windsurf all adopted.
- **A2A (Agent-to-Agent Protocol):** originally Google → Linux Foundation. Peer-to-peer. JSON-over-HTTP, task lifecycle, SSE/webhooks. Complementary to MCP.
- **ACP (Agent Communication Protocol):** JetBrains + Zed. REST-first, HTTP-native, agent registries, client-server (vs A2A's P2P). Compatible: Kimi CLI, goose, Augment Code, Gemini CLI.
- **Agent Skills (Open Standard, Dec 2025):** agentskills.io. Adopted by Microsoft, OpenAI, Atlassian, Figma, Cursor, GitHub. Skills = domain-specific workflows; MCP = connections to services. Complementary.
- W3C AI Agent Protocol Community Group working toward official web standards (expected 2026–2027).

---

### Cross-Cutting Principles from Production

**Seven principles:**

1. **Messages are the only state.** (Claude Code, Codex CLI) No state machines, no workflow graphs. Single append-only message array. All complexity in context management, not control flow.

2. **Invest complexity in the harness, not the loop.** (Claude Code) The agent loop is 5–10 lines. The 10,000+ lines are in context management, security, tool design, error recovery.

3. **Scaffolding > model quality.** Same model, different harness = 5+ point gap on SWE-bench Pro. Change scaffolding, not model, for maximum improvement.

4. **Cache hit rate is the #1 cost metric.** (Manus) Input:output = 100:1. Cache optimization matters 100× more than output optimization.

5. **Three focused agents > one generalist working 3× as long.** Gains are multiplicative: parallelism (3× throughput) × specialization (focused context) × isolation (git worktrees prevent conflicts).

6. **Token usage explains 80% of performance variance.** Multi-agent uses 15× more tokens than chat.

7. **Cross-model review is the cheapest multi-agent pattern.** One reviewer from different model family → closes 74.7% of performance gap. +4.8% on hardest problems.

**What every >50% SWE-bench Pro system has in common:**
1. Typed tool system with specific tools (not bash-for-everything)
2. Context compaction/clearing strategy
3. Linter-in-the-loop (run after every edit, fix up to N times)
4. File reading before editing (never guess about existing code)
5. Plan/TODO tracking to maintain coherence over long sessions
6. Parallel tool calls where independence allows
7. Error as feedback (failed tool calls inform next action, not crash)

**Edit Format Comparison:**
| System | Format | Unique Property |
|--------|--------|-----------------|
| Claude Code | Exact string replacement | Must be unique in file. Simplest format. |
| Codex CLI | V4A Unified Diff | 4-pass fuzzy matching, Unicode normalization |
| Cursor | Sketch + Apply Model | Separate model interprets sketch. 1,000 tok/s via speculative edits |
| Devin | `<find_and_edit>` (regex + per-match LLM) | Parallelizes multi-site refactors |
| Windsurf | `ReplacementChunks` array | Multiple non-adjacent edits in single tool call |
| Bolt.new | Full file content always | Simplest possible — works in WebContainer |
| Manus | `file_str_replace` (single string match) | One tool call per turn |

---

### Parallel-Agent Substrate Analysis (§20.21–20.23)

**The primitive boundary:** "Does the worker have separate goal/context/memory and produce an output that must be merged? Yes → parallel agent. No → parallel execution (inference slots or tool phase)."

**Six substrates classified:**
- **Ollama / llama.cpp:** inference/router substrate. Tool execution is caller-owned. Not multi-agent runtimes; build orchestrator above.
- **OpenRouter agent (`@openrouter/agent@0.4.0`):** single-agent state machine. `Promise.allSettled` over tool calls within a turn. Max tool steps = 5 (default). `nextTurnParams` lets tools modify next turn's model/temperature/instructions. Not a native multi-agent orchestrator.
- **LM Studio `.act()`:** local single-agent tool loop. Serial by default; `allowParallelToolExecution: true` enables parallel phase. `maxPredictionRounds` disables tools on last round. `guardToolCall` can allow/override/deny. Best local single-agent primitive.
- **OASIS/MiroFish:** true multi-persona simulation. `asyncio.Semaphore(128)`, `asyncio.gather`. MiroFish: four nested concurrency layers (profile generation ThreadPoolExecutor(5), OASIS semaphore(30) per platform, dual-world gather, post-run IPC). OASIS token baseline: 100 agents, 1 timestep → 335,600 input / 16,750 output tokens (QWEN_TURBO).
- **Artificial Societies:** closed-source, 300–5,000+ personas per society, 2.5M+ real-world profiles, 95% opinion distribution accuracy, 90% persona internal coherence across hundreds of survey questions.

**Five implementation distinctions:**
1. Inference slots ≠ independent goals.
2. Parallel tool calls (all rejoin one context barrier before next model step) ≠ parallel agents.
3. True parallel agents = separate contexts + action choices + merge semantics.
4. Router/process parallelism ≠ multi-agent planner.
5. Approval state persistence (OpenRouter: `pendingToolCalls`, `unsentToolResults`; LM Studio: `guardToolCall` + plugin `requestConfirmToolCall`) varies widely.

**Streaming traces differ:** Ollama uses `response.reasoning_summary_text.delta`; llama.cpp uses `response.reasoning_text.delta`. The discrepancy is a known compatibility hazard for multi-model orchestrators.

**Replica layering guidance:**
1. model executor: Ollama or llama.cpp
2. provider/router substrate: OpenRouter or llama.cpp router
3. single-agent tool loop: OpenRouter `callModel()` or LM Studio `.act()` semantics
4. multi-agent scheduler: application-owned queue/state/worktree/persona environment
5. merge/evaluation: parent synthesizer, society metrics, or report writer

"Putting layer 4 into layer 1 is the common architecture mistake."

---

### Benchmarks (April 2026)

**SWE-bench Pro (trust — contamination-resistant):**
| System | Score |
|--------|-------|
| Claude Mythos Preview | 77.8% |
| GPT-5.3 Codex | 56.8% |
| Augment Code | 51.8% |
| Cursor Composer 2 | 50.2% |
| Claude Code | 49.8% |
| Codex CLI | 46.5% |

**SWE-bench Verified:** CONTAMINATED. OpenAI's audit found every frontier model could reproduce verbatim gold patches. Do not report these scores.

**Terminal-Bench 2.0:** Claude Mythos Preview 82.0%, GPT-5.3 Codex 77.3%.

---

## → Verso Implications

- **The agent loop is not where Verso competes.** The loop is 5–10 lines; every system agrees on it. Verso's differentiation is entirely in what surrounds it: context management, tool system design, security/permission model, and multi-agent coordination. Invest complexity in the harness, not the loop (Principle 2 above).

- **Adopt append-only message state as the foundational invariant.** Never mutate prior messages. Never use a state machine or workflow graph as the primary execution primitive. "Messages are the only state" (Claude Code, Codex CLI) is the proven production pattern. This also makes sessions persistable, replayable, and compressible for free.

- **Static prompt prefix + `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` is table stakes.** Any provider-level prompt caching (Anthropic `cache_control`, OpenAI prompt caching) requires the static prefix to be byte-identical across requests. Verso must enforce this boundary in the framework API — the user should not be able to accidentally break it. Track cache-break vectors explicitly (Claude Code tracks 14).

- **Deferred tool loading should be a first-class primitive.** Claude Code and Cursor both achieve 85% context reduction (72K → 8.7K tokens) by loading only tool names until a tool is needed. Verso's tool registry should load schemas on-demand by default for any MCP-connected tool, not upfront.

- **Observation masking over full-context dumps.** The academic result (52% cost savings, 2.6% solve-rate improvement) directly translates: when Verso compacts context, keep the full action + reasoning history but replace older tool outputs with placeholders. Do NOT compact reasoning alongside tool outputs — old reasoning informs current decisions even when old outputs are stale.

- **Two-layer permission classifier is the right model for auto-mode safety.** Stage 1: fast single-token gate (accepts most traffic cheaply). Stage 2: chain-of-thought reasoning only for flagged cases. Strip assistant messages and tool outputs from classifier input (prevents the model from talking the classifier into bad calls). Target: ~0.4% FPR.

- **The hook system is how Verso gets extensibility without complexity in the core.** Claude Code's 25-hook architecture (PreToolUse, PostToolUse, WorktreeCreate, TeammateIdle, TaskCompleted, etc.) with 4 handler types (command/http/prompt/agent) is the right model. Hooks let users inject quality gates, custom approval flows, and cross-cutting concerns without touching the agent loop.

- **Ship two distinct multi-agent primitives, not one.** The Claude Code lesson is critical: `Subagents` (one-way, model-invoked, fresh context, isolation by default) and `Teams` (peer-to-peer mailbox, shared task list, file locking) solve different problems. Conflating them produces a bad API. Verso should ship the simple subagent primitive first; P2P teams as the optional escape hatch.

- **Codex CLI's `InterAgentCommunication` + `AgentPath` is the right design for P2P agent messaging.** Unix-style hierarchical addressing (`/root/researcher/worker`), monotonic sequence numbers, `trigger_turn: bool` for wake semantics. Verso's advanced multi-agent tier should copy this protocol.

- **Ghost commits are the right undo primitive for agent work.** Unreferenced commits (no branch pollution), snapshot the working tree before any multi-agent write, roll back via `git restore --source <sha>`. The Codex ghost commit constants are the starting defaults: skip dirs > 200 files, skip files > 10MB, ignore `.git`, `node_modules`, `target`, `.venv`, etc.

- **`SpawnAgentForkMode` (none/full/last-N) is the right API for history inheritance.** Subagents need precise control over what parent context they receive. "Last-N turns" is the most common production need. Codex's filtering rule (strip tool calls/outputs/reasoning at fork, keep user/system/final-answer messages) prevents the subagent from being confused by the parent's tool results.

- **Build the 16 Codex `SPAWN_AGENT_DEVELOPER_INSTRUCTIONS` verbatim into Verso's subagent injection.** Rules 7 (don't work while waiting — use wait), 12 (coordinate on file writes via messaging first), 15 (ghost-commit before signaling completion), and 16 (report failures explicitly, no silent retries >2) are especially important for correctness in parallel agent scenarios.

- **Rubber Duck cross-model review should be a first-class Verso pattern.** +4.8% on hardest problems, closes 74.7% of Sonnet-to-Opus gap at minimal cost. Verso should expose a `reviewer` hook slot where a second model from a different family reviews at post-planning, post-implementation, and pre-test-execution checkpoints.

- **Model racing (`/best-of-n`) is architecturally unique and worth prototyping.** Cursor is the only system that dispatches the same task to 4 models simultaneously and picks the best. If Verso has a multi-provider router, this becomes a natural escape hatch for high-stakes tasks where cost is less important than quality.

- **Do NOT use Ollama, llama.cpp, or OpenRouter as multi-agent runtimes.** All three are single-agent-with-parallel-tool-phase systems. The multi-agent scheduler must live at the application layer above them. Verso's local deployment story should be: llama.cpp/Ollama as model executor, Verso as multi-agent scheduler above.

- **Manus's logit masking trick is worth implementing in Verso's tool system.** Instead of removing tools from the tool list when unavailable (which breaks the KV-cache prefix), mask the tool's tokens during decoding. This keeps the tool list schema constant → byte-identical system prompt prefix → maximum cache hit rate across requests in the same session.

- **The Anyrun-style platform architecture (model below all infrastructure layers) is the right framing for Verso's cloud execution.** Layer 1: interface (API, Slack, CLI). Layer 2: orchestration (task planning, routing, parallel dispatch). Layer 3: execution (sandbox, worktrees). Layer 4: verification (linting, testing, review). Layer 5: output (PRs, artifacts). Model is swappable below all five. This means Verso's API contracts should never assume a specific model provider.

- **Implement `max_budget_usd` as a hard stop from day one.** Claude Code SDK exposes this. It's the only production-grade cost guardrail for long-running autonomous agents. Without it, a runaway agent loop can run up unbounded API bills. Set a default (e.g., $5/session) with opt-out, not opt-in.

- **The `todo.md` / plan-tracking pattern (Manus, Cursor) prevents lost-in-the-middle failures.** Verso should inject a step requiring the agent to maintain and update a TODO list in the system prompt or as a persistent artifact. This keeps the plan in recent attention across long sessions.

- **Three-tier memory (index + topic files + transcript logs) is the right memory architecture.** Claude Code's autoDream design: Layer 1 (always-loaded pointer index, ~150 chars/pointer, capped at line 200), Layer 2 (on-demand topic files), Layer 3 (append-only transcript logs, grep-only). Verso should implement this exact structure with the same gates for consolidation (24h + N sessions + lock).

- **The `WorktreeCreate` hook override pattern is essential for enterprise Verso deployments.** Customers need to control how git worktrees are provisioned (different branch naming conventions, external CI setup, etc.). Hook with stdout protocol for path return is the right API.

- **Augment Code's context engine insight: semantic dependency analysis, NOT text search.** The highest SWE-bench Pro score outside frontier models (51.80%) uses proprietary semantic dependency analysis to maintain live understanding of the entire codebase. Verso's code-context integration should aim for structural understanding, not grep-based retrieval.
