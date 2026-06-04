# Coding Cluster: OpenAI Codex CLI

Source file: `teardowns/CODEX.md` (5,367 lines, 3 rounds of deep RE)
Codebase: `github.com/openai/codex` — Rust cargo workspace, 70+ crates as of Round-3 (2026-05-20).
Distribution: single musl-static Rust binary per platform, shipped via npm `@openai/codex`.

---

## Agent Loop Shape

**Type: Classic ReAct / streaming sampling loop — NOT plan-execute.**
Source: `codex-rs/core/src/session/turn.rs` (2,274 lines), `tasks/regular.rs:40-87`.

The loop is a `loop { ... }` block inside `run_turn`. Continuation driven by a `needs_follow_up: bool` returned from `run_sampling_request`. `needs_follow_up = true` when the model emitted tool calls; `false` when it emitted only text. No hardcoded `max_iterations` — the loop runs as long as the model keeps calling tools.

**Outer `RegularTask::run` loop (continuation loop):** calls `run_turn` in a loop while `sess.has_pending_input()`. This handles mid-turn user input — a user can submit a follow-up message while the model is mid-tool-call; the outer loop picks it up.

**Phase structure per `run_turn` call:**

1. **Pre-turn setup (lines 146–373):** auto-compact pre-check, plugin resolution, MCP tool listing (`list_all_tools()`), connector merge, skill resolution (`SkillInjections` built from `@skill` mentions), session-start hooks, `UserPromptSubmit` hooks, `TurnDiffTracker` init (git-diff tracker rooted at repo).
2. **ReAct loop (line 383+, `loop {}`):** drain pending input, filter history to model modalities, sample, handle `SamplingRequestResult`.
3. **Auto-compact mid-turn (line 475–512):** if `total_usage_tokens >= auto_compact_limit && needs_follow_up`, run `run_auto_compact(CompactionReason::ContextLimit, CompactionPhase::MidTurn)`. Then `continue` — loop resumes with compacted context.
4. **End-of-turn (line 514):** stop hooks, `HookEvent::AfterAgent`, `break`.
5. **Error handling:** `TurnAborted` → silent break; `InvalidImageRequest` → replace invalid images in last turn with `"Invalid image"` placeholder then `continue` (sanitize-and-retry); all other errors → emit `EventMsg::Error`, break.

**Termination conditions:**
- `!needs_follow_up` AND no pending input AND stop hook approves → `break`
- Token limit without `needs_follow_up` → break
- `Op::Interrupt` cancels `CancellationToken` → break
- Hook returns `should_stop` → break
- Error path → break

**No max-iterations constant.** The only safety nets are context-token budgets and the cancellation token.

**4 distinct SessionTask types:**
- `RegularTask` — normal user turn
- `CompactTask` — `Op::Compact` summarization
- `UserShellTask` — `!cmd` execution
- `ReviewTask` — `/review` mode (code review)

Each has `kind()`, `span_name()` (OTEL trace span), `records_turn_token_usage_on_span()`.

---

## Models

**Context window:** 272,000 tokens default (`context_window: Option<i64>`). `max_context_window: Option<i64>` also 272,000.

**Auto-compact trigger:** `effective_context_window_percent: u32 = 95` — auto-compact fires at 95% full, giving a 5% overflow safety margin.

**Per-model system prompts (6 distinct files):**

| File | Target |
|---|---|
| `core/gpt-5.2-codex_prompt.md` (80 lines) | `gpt-5.2-codex` (current) |
| `core/gpt-5.1-codex-max_prompt.md` (80 lines) | `gpt-5.1-codex-max` |
| `core/gpt_5_codex_prompt.md` (68 lines) | `gpt-5-codex` (predecessor) |
| `core/gpt_5_2_prompt.md` | `gpt-5.2` (non-codex) |
| `core/gpt_5_1_prompt.md` | `gpt-5.1` |
| `core/prompt_with_apply_patch_instructions.md` (351 lines) | gpt-4.1 (legacy, includes apply_patch teaching) |
| `protocol/src/prompts/base_instructions/default.md` (275 lines) | fallback / any unknown model |

**ModelInfo fields (model_info.rs:66+):**
- `shell_type: ConfigShellToolType` — which shell tool to expose (`Default` vs `container.exec` for codex models)
- `apply_patch_tool_type: Option<...>` — `Function` (newer) vs `FreeForm` (older models)
- `truncation_policy: TruncationPolicyConfig` — default `Bytes(10_000)` for tool output truncation
- `supports_parallel_tool_calls: bool`
- `auto_compact_token_limit: Option<i64>` — `None` means never compact
- `default_reasoning_level` / `supported_reasoning_levels` — per-model reasoning effort
- `model_messages: Option<ModelMessages>` — templated personality substitution at runtime

**Reasoning effort:** `ReasoningEffortConfig` — `Minimal | Low | Medium | High` per turn via `Op::UserTurn { effort, ... }`. Only takes effect on reasoning-capable models.

**Service tier routing:** `Op::UserTurn { service_tier: Option<Option<String>>, ... }` — double-Option: `Some(Some("priority"))` sets, `Some(None)` clears, `None` keeps. Values: `flex`, `priority`, `default`, `scale`.

**Model rerouting:** `EventMsg::ModelReroute(ModelRerouteEvent)` — when backend swaps model (e.g., quota exhaustion fallback), emits notification; turn continues with new model.

**Personality system:** `{DEFAULT_PERSONALITY_HEADER}\n\n{PERSONALITY_PLACEHOLDER}\n\n{BASE_INSTRUCTIONS}`. `PERSONALITY_PLACEHOLDER` is Mustache `{{ personality }}` substituted at runtime. Three values: empty (default), `"You optimize for team morale..."` (friendly), `"You are a deeply pragmatic, effective software engineer."` (pragmatic). User selects via `Op::UserTurn { personality: Option<Personality>, ... }`.

**Local model providers:** `lmstudio/` and `ollama/` crates — point to `http://localhost:1234` or `http://localhost:11434`. AWS Bedrock via `aws-auth/`. Azure via provider-info config.

---

## Tool Registry

**Trait:** `ToolHandler` in `tools/registry.rs:44-95`.

```rust
pub trait ToolHandler: Send + Sync {
    fn tool_name(&self) -> ToolName;
    fn kind(&self) -> ToolKind;  // Function | Mcp
    fn is_mutating(&self, invocation) -> Future<Output = bool>;  // defensive: return true if any doubt
    fn pre_tool_use_payload / post_tool_use_payload  // hook integration
    fn create_diff_consumer() -> Option<Box<dyn ToolArgumentDiffConsumer>>;  // streaming patch render
    fn handle(&self, invocation) -> Future<Output = Result<Output, FunctionCallError>>;
}
```

`ToolName = { name: String, namespace: Option<String> }` — MCP tools render as `mcp__github__create_issue`.

**Complete builtin tool inventory (~25-30 surfaces):**

| Handler | Purpose |
|---|---|
| `ApplyPatchHandler` | Structured diff format (see below) |
| `DynamicToolHandler` | Runtime-registered tools (skills, plugins) |
| `CreateGoalHandler`, `GetGoalHandler`, `UpdateGoalHandler` | Long-running thread goals |
| `McpHandler` | Generic MCP tool invocation |
| `ListMcpResourcesHandler`, `ReadMcpResourceHandler` | MCP resource access |
| `PlanHandler` | Structured plan tool — emits `update_plan` events |
| `RequestPermissionsHandler` | Granular per-action permission elevation |
| `RequestPluginInstallHandler` | Install missing plugins mid-turn |
| `RequestUserInputHandler` | Structured question with form fields |
| `ShellHandler`, `ShellCommandHandler`, `LocalShellHandler`, `ContainerExecHandler` | Shell exec (4 variants) |
| `ToolSearchHandler` | Search/load deferred tool schemas (same concept as Claude Code's `ToolSearch`) |
| `UnavailableToolHandler` | Stub for tools the model called that aren't registered |
| `ExecCommandHandler`, `WriteStdinHandler` | Long-lived exec sessions with stdin/stdout streaming |
| `ViewImageHandler` | Attach a local image as model input |
| `CodeModeExecuteHandler`, `CodeModeWaitHandler` | V8 isolate JS-orchestrator tools (Round-3) |
| Multi-agent v1/v2 handlers | Agent spawn/control |
| `TestSyncHandler` | Test-only sync barrier |

**Parallel tool calls:** `tools/parallel.rs`. Concurrency controlled by `RwLock`:
- `supports_parallel = true` → acquire **read lock** (concurrent with other parallel-safe tools)
- `supports_parallel = false` → acquire **write lock** (exclusive)
Multiple parallel tool futures queued in `FuturesOrdered`.

```rust
let _guard = if supports_parallel {
    Either::Left(lock.read().await)
} else {
    Either::Right(lock.write().await)
};
```

**Tool routing:** `tools/router.rs` (334 lines) + `tools/orchestrator.rs` (482 lines) — maps `ToolPayload` → handler via `matches_kind`, runs pre/post hooks, applies sandbox policy transforms, records `ToolDispatchTrace`.

**Streaming diff consumer:** `create_diff_consumer()` emits `PatchApplyUpdated` events as the model streams the patch JSON → typewriter-effect patch display in TUI.

---

## The `apply_patch` Format

Codex's flagship contribution to coding agents. Crate `codex-rs/apply-patch/` (4,384 lines, 7 files).

**Grammar (14-line Lark BNF, `apply_patch.lark`):**
- `*** Begin Patch` / `*** End Patch` — outer envelope
- `*** Add File: <path>` / `*** Delete File: <path>` / `*** Update File: <path>` — file operations
- `*** Move to: <path>` — rename within Update hunk
- `*** End of File` — anchors hunk at end of file
- `@@ <anchor>` inside change chunks — function/class signature as seek anchor
- `+`/`-`/` ` lines — add/remove/context

**Five-tier fuzzy seek algorithm (`seek_sequence.rs:12-110`):**
1. Exact match
2. `rstrip()` match
3. `trim()` match
4. Unicode normalization (smart quotes → ASCII quotes, em-dashes → hyphens, NBSP → space)
5. End-of-file anchor

Tier 4 (Unicode normalization) is the key insight: models emit Unicode that visually looks like ASCII but isn't. Production scar. This is mature anti-fragility — models trained on web text will emit smart quotes and em-dashes.

**Strict vs Lenient mode (`parser.rs:44-50`):** lenient mode tolerates malformed markers; strict mode rejects. Model-facing instruction: `apply_patch` only, never `applypatch` or `apply-patch` (anti-typo training in system prompt).

**Token format:** the shell tool is invoked as `{"command":["apply_patch","*** Begin Patch\n..."]}` — `apply_patch` is a shell command, not a separate tool call. On gpt-4.1 the full instruction set (351 lines) is injected into the system prompt to teach the format.

---

## Code Mode (V8 Isolate, Round-3, MAJOR)

Source: `code-mode/` crate, 2,696 LOC.

Two tools exposed: `exec` and `wait`.

**`exec`:** runs arbitrary async JavaScript in a fresh V8 isolate. Every registered tool is available as `await tools.<normalized_name>(args)`. No Node APIs, no fs, no network, no console. Hard isolation.

**Constants (`code-mode/src/runtime/mod.rs:23-25`):**
```rust
pub const DEFAULT_EXEC_YIELD_TIME_MS: u64 = 10_000;
pub const DEFAULT_WAIT_YIELD_TIME_MS: u64 = 10_000;
pub const DEFAULT_MAX_OUTPUT_TOKENS_PER_EXEC_CALL: usize = 10_000;
```

**Global helpers injected into every isolate:** `text()`, `image()`, `store()`, `load()`, `notify()`, `setTimeout()`, `clearTimeout()`, `yield_control()`, `exit()`, `ALL_TOOLS` (metadata list for all available tools).

**Deferred tool discovery:** tools not inlined in the description are still available via `tools.*`; model introspects via `ALL_TOOLS`. Same problem space as Claude Code's `ToolSearch` and Cursor's filesystem descriptor approach — three different solutions to tool-list inflation.

**MCP TypeScript preamble (75 lines, `description.rs:44-119`):** type aliases for `Role`, `TextContent`, `ImageContent`, `CallToolResult`, etc. — embedded directly so the model can type-check MCP tool returns inside the JS script.

**V8 sandbox (`v8-poc/src/lib.rs:17-19`):** `v8__V8__IsSandboxEnabled()` returns true. V8's own memory-tagging defence (1 TiB virtual-address sandbox). A malicious model output that escapes JS semantics cannot trash Codex's Rust heap.

**`wait` tool:** resumes a paused `exec` cell identified by `cell_id`. Used for long-running scripts that yield early via `yield_time_ms`. Returns only new output since last yield.

**Why this matters for Verso:** Code Mode is the answer to N-sequential-tool-call roundtrip latency. One JS program orchestrates multiple tool calls inline with real parallelism (JS `Promise.all`). The model pays one sampling round-trip cost instead of N. This is the most architecturally novel addition in Round-3.

---

## Multi-Agent Coordination

Three concurrency layers:

**Layer 1 — ThreadManager (`thread_manager.rs`):**
```rust
pub struct ThreadManager {
    state: Arc<ThreadManagerState>,
    // threads: RwLock<HashMap<ThreadId, Arc<CodexThread>>>
}
```
Multiple agent threads can run simultaneously. `FuturesUnordered` drives concurrent shutdown.

**Layer 2 — Subagent (user-triggered):**
- `agents.max_threads` = 6 (default) — max concurrent agent threads
- `agents.max_depth` = 1 (default) — nesting depth limit for spawned agents
- `agents.job_max_runtime_seconds` — per-worker timeout for CSV-based jobs
Subagents only activate via explicit user instruction. Model does NOT auto-spawn based on task structure.

**Layer 3 — Parallel tool calls within a single agent turn:** `parallel_tool_calls` set per-turn based on `model_info.supports_parallel_tool_calls`.

**AgentControl + AgentRegistry + Mailbox (Parts 5.3–5.5, floor file):**
- `AgentRegistry` — concurrency limit enforcement across all threads
- `Mailbox` — inter-agent async messaging (`mpsc::UnboundedSender` per agent)
- `AgentControl` — the multi-agent control plane (commands, state machine)

**Agent roles:** multiple built-in role definitions (planner, worker, reviewer, etc.) — model assigned at spawn time.

**Agent graph store (Round-3):** `agent-graph-store/` crate (454 LOC). Persists agent spawn DAG to local disk — survives restarts. Public trait is generic so cloud-backed stores (Postgres, Redis) can be plugged in.

**Op/Event wire protocol:** strongly-typed `Op` enum (28 variants) and `EventMsg` enum (~70 variants) over JSON. `CodexThread::submit(op) -> CodexResult<String>` is the public API. Events go out a `broadcast::Sender<Event>` so multiple subscribers (TUI + telemetry + rollout recorder) can read simultaneously.

---

## Context Assembly

**System prompt composition order (9.5, runtime `developer/system` message):**
1. Personality header (model-specific)
2. `{{ personality }}` substitution (default/friendly/pragmatic)
3. Base instructions (model-specific `.md` or `default.md`)
4. Approval policy fragment (`.md` from `prompts/permissions/approval_policy/`)
5. Sandbox mode fragment (`.md` from `prompts/permissions/sandbox_mode/`)
6. AGENTS.md hierarchy (root → CWD → intermediate, concatenated root-first)
7. Skill instructions for any `@skill` mentions (`SkillInjections`)
8. Plugin instructions for any `@plugin` mentions
9. Permission instructions (current granular state)
10. User instructions (`~/.codex/config.toml [profile.user_instructions]`)
11. Environment context (cwd, OS, shell, git status, network state, sandbox tag)

Each fragment is a separate `.md` file in `core/src/context/prompts/` — composable at runtime. Easy to A/B-test individual fragments.

**AGENTS.md hierarchy (`core/src/agents_md.rs`):**
- Walk upward from cwd to project root (determined by `project_root_markers`, default `[".git"]`)
- Collect every `AGENTS.md` from root DOWN to cwd (inclusive), concatenate root-first
- Deeper files come later → higher recency in prompt
- `AGENTS.override.md` in `~/.codex/` for personal overrides without touching repo-committed `AGENTS.md`
- Byte budget: `project_doc_max_bytes` (configurable). Exceeding truncates at file boundary with `tracing::warn!`. Partial inclusion at the boundary file.
- Separator string: `"\n\n--- project-doc ---\n\n"` — visible to the model
- `Feature::ChildAgentsMd` flag enables `HIERARCHICAL_AGENTS_MESSAGE` stanza explaining nested precedence

**Skill context budget (`core-skills/src/render.rs:17-20`):**
```rust
const DEFAULT_SKILL_METADATA_CHAR_BUDGET: usize = 8_000;
const SKILL_METADATA_CONTEXT_WINDOW_PERCENT: usize = 2;
const APPROX_BYTES_PER_TOKEN: usize = 4;
```
2% of model context window allocated to skill descriptions, floor 8,000 chars.

**Per-turn context (`Op::UserTurn` is stateless):** each turn ships its own cwd, approval, sandbox, model, effort, summary, service_tier, collaboration_mode, personality, environments. Critical for multi-tenant app-server and reproducible replay.

**History assembly:** `sess.clone_history().for_prompt(&model_info.input_modalities)` — full history filtered to modalities the model accepts (images dropped if text-only model). This happens once per loop iteration.

**Token accounting:** `total_usage_tokens` tracked per loop. `auto_compact_token_limit` = `model_info.auto_compact_token_limit()` — when `None`, auto-compact never fires.

---

## Memory / Session Persistence

**Rollout format:** JSONL files at `~/.codex/sessions/YYYY/MM/DD/rollout-YYYY-MM-DDThh-mm-ss-<uuid>.jsonl`. Year/Month/Day hierarchy prevents flat-directory degradation at scale.

**`RolloutItem` enum (protocol.rs:2769):**
```rust
pub enum RolloutItem {
    SessionMeta(SessionMetaLine),
    ResponseItem(ResponseItem),
    Compacted(CompactedItem),
    TurnContext(TurnContextItem),
    EventMsg(EventMsg),
}
```

**`TurnContextItem`** — complete settings snapshot per turn: cwd, approval_policy, sandbox_policy, model, personality, reasoning effort, user_instructions, developer_instructions, `final_output_json_schema`, truncation_policy. Enables exact policy state reconstruction on `--resume`.

**`CompactedItem`:**
```rust
pub struct CompactedItem {
    pub message: String,                          // summarization output
    pub replacement_history: Option<Vec<ResponseItem>>,  // replaces old history
}
```
Auto-compact: calls model with `templates/compact/prompt.md` + existing history → summary → `replacement_history` → replaces in-memory history → writes `RolloutItem::Compacted` to JSONL.

**SQLite index (`rollout/src/state_db.rs`, 668 lines):** session_id → file path, timestamp, cwd, model, last_active, branch, summary. Powers `/resume` browser and fast session lookup.

**Rollout truncation (`thread_rollout_truncation.rs`):** mechanical pruning for very long sessions — drops the middle while preserving SessionMeta + early context + recent turns. Different from `Compact` (model summarizes) — no model call, just truncation.

**Resume/Fork:** `/resume` replays JSONL line-by-line restoring session state. `/fork` creates new rollout file with `forked_from_id = original.id`, new UUID, new date directory. Fork point state copied from source.

**`SessionMetaLine`** records git state at session start: `commit_hash`, `branch`, `repository_url`. So every rollout is tied to a specific git commit.

**`memory_mode: Option<String>`** — `Enabled`/`Disabled` per session.

---

## System Prompt Fragments (Verbatim)

### Default base instructions opening (default.md:1-15)
```
You are a coding agent running in the Codex CLI, a terminal-based coding
assistant. Codex CLI is an open source project led by OpenAI. You are expected
to be precise, safe, and helpful.

Your capabilities:
- Receive user prompts and other context provided by the harness, such as files in the workspace.
- Communicate with the user by streaming thinking & responses, and by making & updating plans.
- Emit function calls to run terminal commands and apply patches. Depending on
  how this specific run is configured, you can request that these function
  calls be escalated to the user for approval before running.
```

### GPT-5 Codex prompt 2026-03-25 (jujumilk3 capture) — key fragments

**Identity and values:**
```
You are Codex, a coding agent based on GPT-5. You and the user share the same workspace and collaborate to achieve the user's goals.

[Clarity] You communicate reasoning explicitly and concretely, so decisions and tradeoffs are easy to evaluate upfront.
[Pragmatism] You keep the end goal and momentum in mind, focusing on what will actually work.
[Rigor] You expect technical arguments to be coherent and defensible, and you surface gaps or weak assumptions politely.
```

**Anti-cheerleading (verbatim):**
```
You avoid cheerleading, motivational language, or artificial reassurance, or any kind of fluff.
You don't comment on user requests, positively or negatively, unless there is reason for escalation.
```

**Autonomy and persistence (verbatim):**
```
Persist until the task is fully handled end-to-end within the current turn whenever feasible:
do not stop at analysis or partial fixes; carry changes through implementation, verification,
and a clear explanation of outcomes unless the user explicitly pauses or redirects you.

Unless the user explicitly asks for a plan [...], assume the user wants you to make code changes
or run tools to solve the user's problem. In these cases, it's bad to output your proposed solution
in a message, you should go ahead and actually implement the change.
```

**Two-channel communication:**
```
You have 2 ways of communicating with the users:
- Share intermediary updates in `commentary` channel.
- After you have completed all your work, send a message to the `final` channel.
```

**Key editing constraints (verbatim):**
- "Always use apply_patch for manual code edits. Do not use cat or any other commands when creating or editing files."
- "Default to ASCII when editing or creating files."
- "You struggle using the git interactive console. ALWAYS prefer using non-interactive git commands." — explicit weakness disclosure to steer behavior.
- "NEVER use destructive commands like `git reset --hard` or `git checkout --` unless specifically requested."
- "Do not waste tokens by re-reading files after calling `apply_patch` on them."
- "NEVER output inline citations like `【F:README.md†L5-L14】` in your outputs."
- "Do not use one-letter variable names unless explicitly requested."
- "NEVER add copyright or license headers unless specifically requested."

**Coding guidelines key rules:**
- Fix root cause, not surface. Do NOT fix unrelated bugs. Keep changes minimal and focused.
- `git log` and `git blame` for codebase history context.
- 3 formatting iterations max, then present a correct-but-unformatted solution and call it out.
- Do NOT add tests to codebases with no tests. Do NOT add a formatter if none exists.

**Ambition vs precision:**
```
For tasks with no prior context: feel free to be ambitious and creative.
If operating in an existing codebase: surgical precision. Treat the surrounding codebase with respect.
Don't gold-plate.
```

**Plan tool guidance (update_plan):**
- Skip plans for the easiest ~25% of tasks (single-step).
- Do not make single-step plans.
- Update plan after completing each sub-task.
- Do NOT repeat plan contents after `update_plan` — harness renders it.
- Anti-incapability: don't plan steps you can't execute.
- 4-6 distinct, sequenced steps in a good plan. Vague 2-3 step "Create X / Add Y / Convert Z" plans are bad.

**Preamble messages (before tool calls):** 1-2 sentences, 8-12 words. 8 verbatim examples:
```
"I've explored the repo; now checking the API route definitions."
"Ok cool, so I've wrapped my head around the repo. Now digging into the API routes."
"Spotted a clever caching util; now hunting where it gets used."
```

**Formatting rules (2026-03-25, key rules):**
- No emojis, no em dashes unless explicitly instructed.
- No nested bullets — flat lists only.
- File paths as markdown links (`[app.ts](/abs/path/app.ts)`) not inline code.
- Headers: 1-3 words, `**Title Case**`, no blank line before first bullet.
- Simple tasks: 1-2 short paragraphs in prose; do NOT default to bullets.
- Large tasks: 2-3 high-level sections max, prefer grouping by change area not by file.
- If answer is turning into a changelog, compress it.

**Parallel tool call mandate (verbatim):**
```
Parallelize tool calls whenever possible - especially file reads, such as `cat`, `rg`, `sed`, `ls`, `git show`.
Use `multi_tool_use.parallel` to parallelize tool calls and only this.
Never chain together bash commands with separators like `echo "===="` as this renders to the user poorly.
```

---

## Error Handling

**`FunctionCallError::RespondToModel`** — wraps JSON parse failures in tool arguments; send error back to model as tool output, let model retry.

**`CodexErr::InvalidImageRequest`** — sanitize-and-retry: replace invalid image in last turn's tool output with `"Invalid image"` string, then `continue` the loop. The model sees a corrected tool output and can proceed.

**`CodexErr::TurnAborted`** — silent break. The abort event was already emitted via a different channel.

**Tool `UnavailableToolHandler`** — stub registered for any tool the model calls that isn't in the live registry. Returns an error message to the model without crashing.

**Process lifecycle:** on Linux, `prctl(PR_SET_PDEATHSIG, SIGTERM)` ensures child process dies when Codex dies (even on SIGKILL). `kill_on_drop(true)` on `tokio::process::Command`. Shell tools: `stdin = Stdio::null()` to prevent ripgrep-style stdin hangs.

**`EventMsg::ModelReroute`** — backend-initiated model swap (e.g., quota exhaustion) emits this; turn continues transparently.

**Stop hooks blocking:** if a stop hook says `should_block` and has a continuation prompt, that prompt is injected and the loop `continue`s with `stop_hook_active = true`. If `should_stop`, break. Prevents premature termination.

---

## Exact Constants

| Constant | Value | Source |
|---|---|---|
| `agents.max_threads` | 6 | `config.toml` default |
| `agents.max_depth` | 1 | `config.toml` default |
| `effective_context_window_percent` | 95 | `model_info.rs` — compact at 95% |
| Default context window | 272,000 tokens | `protocol/src/openai_models.rs` |
| Tool output truncation | 10,000 bytes | `truncation_policy: TruncationPolicyConfig` default |
| Formatting iteration cap | 3 | system prompt `§RN.24` |
| `DEFAULT_EXEC_YIELD_TIME_MS` | 10,000 ms | `code-mode/src/runtime/mod.rs:23` |
| `DEFAULT_WAIT_YIELD_TIME_MS` | 10,000 ms | `code-mode/src/runtime/mod.rs:24` |
| `DEFAULT_MAX_OUTPUT_TOKENS_PER_EXEC_CALL` | 10,000 tokens | `code-mode/src/runtime/mod.rs:25` |
| `MAX_JS_SAFE_INTEGER` | 2^53 − 1 | `code-mode/src/description.rs:9` |
| `SESSION_IMPORT_MAX_COUNT` | 50 | `external-agent-sessions/src/detect.rs:10` |
| `SESSION_IMPORT_MAX_AGE` | 30 days | `external-agent-sessions/src/detect.rs:11` |
| `SESSION_TITLE_MAX_LEN` | 120 chars | `external-agent-sessions/src/lib.rs:21` |
| `DEFAULT_SKILL_METADATA_CHAR_BUDGET` | 8,000 chars | `core-skills/src/render.rs:17` |
| `SKILL_METADATA_CONTEXT_WINDOW_PERCENT` | 2% | `core-skills/src/render.rs:18` |
| `APPROX_BYTES_PER_TOKEN` | 4 bytes | `core-skills/src/render.rs:20` |
| `MAX_SCAN_DEPTH` (skills) | 6 | `core-skills/src/loader.rs:122` |
| `MAX_SKILLS_DIRS_PER_ROOT` | 2,000 | `core-skills/src/loader.rs:123` |
| `MAX_NAME_LEN` (skill) | 64 chars | `core-skills/src/loader.rs:111` |
| `MAX_DESCRIPTION_LEN` (skill) | 1,024 chars | `core-skills/src/loader.rs:112` |
| `project_doc_max_bytes` | configurable | `config_types.rs` |
| AGENTS.md separator | `"\n\n--- project-doc ---\n\n"` | `agents_md.rs:41` |
| Preamble message length | 1-2 sentences, 8-12 words | system prompt |

---

## Streaming Protocol

**Internal event bus:** `broadcast::Sender<Event>` per CodexThread. Multiple subscribers (TUI, telemetry, rollout recorder) receive all events.

**`EventMsg` enum (~70 variants):** `TurnStarted`, `TurnEnded`, `AgentMessageContentDelta` (streaming tokens), `PatchApplyUpdated` (streaming patch lines), `TokenCount`, `PlanUpdate`, `PlanDelta`, `ContextCompacted`, `ModelReroute`, `ElicitationRequest`, `HookStarted`, `TurnDiff`, `Error`, etc.

**`Op` enum (28 variants):** `UserTurn`, `Interrupt`, `Compact`, `ReloadUserConfig`, `ResolveElicitation`, `ThreadGoalUpdated`, etc. `Op::UserTurn` carries all per-turn context (model, sandbox, approval, effort, personality, etc.).

**Rollout persistence:** curated subset of the wire stream. `is_persisted_rollout_item` filters out streaming deltas (`AgentMessageContentDelta`) — those go to telemetry only. `should_persist_response_item` and `should_persist_event_msg(ev, mode)` control what is durable.

**Two output channels (system prompt):** `commentary` channel for intermediary updates (progress, status), `final` channel for completed response. CLI multiplexes them for different rendering.

**TUI streaming render:** patches display line-by-line via `create_diff_consumer()` on `ApplyPatchHandler`. Tokens stream token-by-token via `AgentMessageContentDelta`.

---

## MCP Integration (Both Directions)

**Codex IS BOTH an MCP server AND client — uniquely bidirectional.**

**As MCP server (`mcp-server/`):** exposes ONE tool called `codex`. Calling it runs a full Codex turn.

```rust
pub struct CodexToolCallParam {
    pub prompt: String,
    pub model: Option<String>,
    pub profile: Option<String>,
    pub cwd: Option<String>,
    pub approval_policy: Option<CodexToolCallApprovalPolicy>,  // untrusted|on-failure|on-request|never
    pub sandbox: Option<CodexToolCallSandboxMode>,              // read-only|workspace-write|danger-full-access
    pub config: Option<HashMap<String, serde_json::Value>>,
    pub base_instructions: Option<String>,
    pub developer_instructions: Option<String>,
    pub compact_prompt: Option<String>,
}
```

Any agent (e.g. Claude Code) can call `mcp__codex__codex { prompt, cwd, approval_policy: "never", sandbox: "workspace-write" }` and get back the result. This makes Codex a drop-in coding delegate for other agents.

**Approval bridging:** when Codex (as MCP server) needs user approval, it sends an MCP `elicitation` request to the calling client. When Codex (as MCP client) receives an elicitation from an external server, it routes it to the user via `EventMsg::ElicitationRequest`. Symmetric.

**As MCP client (`rmcp-client/`):** three transports: stdio (standard), HTTP (with optional SSE), in-process (for builtin MCPs). OAuth support via `oauth.rs` + `perform_oauth_login.rs` — browser-based OAuth, localhost callback, keyring storage.

**Builtin MCPs (`builtin-mcps/`):** bundled servers that run in-process (git, github, possibly search).

**Tool inflation solution:** `ToolSearchHandler` — same concept as Claude Code's `ToolSearch`. Deferred tool schemas not loaded by default; model calls `tool_search` to fetch them. MCP tools merged into the live registry at turn-start via `mcp_connection_manager.list_all_tools()`.

---

## Sandbox Architecture

**Three platform backends:**
1. **macOS Seatbelt** — `.sbpl` files, borrows Chrome renderer policy. `seatbelt_base_policy.sbpl` (123 lines), network policy (35 lines), read-only filesystem defaults (200 lines).
2. **Linux bubblewrap** — Codex ships its own `bwrap` binary (`bundled_bwrap.rs`), no system install required.
3. **Linux seccomp + landlock** (`linux-sandbox/src/landlock.rs:168-267`) — denies `io_uring` deliberately (bypasses normal syscall hooks), allows `recvfrom` deliberately (cargo clippy needs it).
4. **Windows AppContainer** (`windows-sandbox-rs/`) — active development as of Round-3 (commit `2b4898c`).

**Three network modes (seccomp):**
- `restricted` — AF_UNIX only
- `proxy-routed` — AF_INET/INET6 only, **AF_UNIX blocked** (prevents agent from bypassing via Unix domain sockets to a local proxy)
- `full` — no filter

**Four sandbox modes (model-visible):** `read-only` (default), `workspace-write`, `danger-full-access`. Disclosed to model in system prompt.

**Four approval modes (model-visible):** `untrusted`, `on-failure`, `on-request`, `never`. In `never` mode the model is explicitly authorized to add scratch tests that it removes before yielding.

**Default safety posture** (disclosed in system prompt): `workspace-write` + network restricted + `on-failure`. Conservative by default.

**`CODEX_SANDBOX`** env var set in child processes. Value: `"seatbelt"` on macOS. `CODEX_SANDBOX_NETWORK_DISABLED` set to `"1"` when network is restricted. Children can detect their own sandbox state.

**`is_mutating()` rule:** defensive — return `true` if there is any doubt. This drives sandbox selection. A tool that might write must use the write-capable sandbox.

---

## Skill System (`core-skills/`, Round-3)

**Directory layout (`loader.rs:106-111`):**
```rust
const SKILLS_FILENAME: &str = "SKILL.md";
const AGENTS_DIR_NAME: &str = ".agents";
const SKILLS_METADATA_FILENAME: &str = "openai.yaml";
const SKILLS_DIR_NAME: &str = "skills";
const MAX_SCAN_DEPTH: usize = 6;
const MAX_SKILLS_DIRS_PER_ROOT: usize = 2000;
```

**SKILL.md frontmatter:** `name`, `description`, sidecar `agents/openai.yaml` with interface (display_name, icon, brand_color, default_prompt), dependencies.tools[], and policy (allow_implicit_invocation, products[]).

**Trigger rules in system prompt:** model uses a skill if user names it with `$SkillName` OR task clearly matches description. Progressive disclosure: open `SKILL.md` and read only what's needed; load `references/` files only when needed; run `scripts/` over retyping large code blocks.

**OTEL metrics emitted:** `THREAD_SKILLS_ENABLED_TOTAL_METRIC`, `THREAD_SKILLS_KEPT_TOTAL_METRIC`, `THREAD_SKILLS_TRUNCATED_METRIC`, `THREAD_SKILLS_DESCRIPTION_TRUNCATED_CHARS_METRIC`.

---

## Claude Code Migration Feature (`external-agent-migration/`, Round-3)

```rust
const SOURCE_EXTERNAL_AGENT_NAME: &str = "claude";  // lib.rs:15
```

Imports from Claude Code: MCP config (`.mcp.json`), hooks (translates Claude hook names via `codex_hooks::HOOK_EVENT_NAMES`), subagents (`.agents/` → Codex agent TOML), commands (Claude `/command` → Codex `SKILL.md` with `"source-command"` prefix).

Session import (`external-agent-sessions/`): max 50 sessions, max age 30 days, filtered by `cwd` still existing on disk, ledger-tracked to prevent duplicate imports.

This is a **first-party defection feature** — Claude Code has no equivalent Codex importer.

---

## API/DX Shape

**Config:** `~/.codex/config.toml` (780-line `config_types.rs`). Profile-based: `[profiles.<name>]` with full overrides. Dynamic reload via `Op::ReloadUserConfig` (no restart required).

**Config layering (`config_lock.rs`):** multiple layers merged. Project-layer excluded when determining `project_root_markers` (chicken-and-egg: the markers define the project, so they can't come from inside the project).

**49 slash commands** (TUI). Order in source = popup display order. Notable: `/resume`, `/fork`, `/side` (ephemeral fork), `/compact`, `/plan`, `/agent`, `/skills`, `/hooks`, `/mcp`. `/debug-config` shows all config layers and requirement sources.

**Hook system:** 8 trigger points (vs Claude Code's 5) — `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `StopHook` (blocks turn continuation), `AfterAgent`, `preview_stop`, etc. Hook has `trust_status`, scope, source enum.

**MCP per-server config (`[mcp_servers.<name>]`):** `parallel_tool_calls: bool` — mark individual MCP servers as parallel-safe.

**Shell environment policy (`[shell_environment_policy]`):** inherit `core`/`all`/`none`, wildmatch exclude patterns, explicit `set` overrides, `include_only` whitelist. Default passes SECRET/TOKEN/KEY through (so `gh`, `aws` etc. work without explicit allowlisting).

**Notifications (`[notify]`):** `command = [...]` spawned with JSON event payload on stdin when approval needed or long task completes. `sound = true` for audio.

**`$SkillName` prefix** for skill invocation (vs Claude Code `/<skill-name>`, vs Cursor no prefix).

**`AGENTS.md`** is becoming the cross-tool standard (Codex, Cursor, others). `CLAUDE.md` is Claude-specific.

---

## Verso Implications

### Copy

1. **Composable system prompt fragments.** Codex's per-model + per-approval-policy + per-sandbox-mode `.md` files composed at runtime is cleaner than a single string with conditionals. Verso should compose `system_prompt = [base, approval_fragment, sandbox_fragment, context_fragment, skill_fragment, user_instructions]` at turn-start, not bake one string.

2. **Stateless per-turn context (`Op::UserTurn` carries everything).** Each turn is self-describing: cwd, model, approval, sandbox, effort, personality. This enables reproducible replay, multi-tenant servers, and fork/resume. Verso's `Turn` type should carry its full execution context, not rely on ambient session state.

3. **ReAct loop without max_iterations + context-budget auto-compact as the only safety net.** Codex runs until the model stops calling tools. The only hard stop is token budget + cancellation token. Verso should do the same — no artificial iteration caps, let the model decide when it's done. Add auto-compact at 95% context.

4. **`apply_patch` 5-tier fuzzy seek (especially Unicode normalization).** Models emit smart quotes, em-dashes, NBSP. Any Verso coding tool that does text-level file editing needs Unicode normalization as a fallback tier. Copy the `seek_sequence.rs` algorithm.

5. **RwLock-based parallel tool concurrency.** Tools declare `supports_parallel: bool`. Read-lock for parallel-safe, write-lock for exclusive. This is the right primitive — simple, correct, avoids a separate scheduler. Verso should adopt this pattern for its tool executor.

6. **JSONL rollout with `TurnContextItem` snapshot.** Full settings snapshot per turn stored durably. Resume/fork become trivial. Verso's persistence layer should store a full `TurnContext` snapshot with every turn, not just the message history.

7. **Commentary/final channel split.** Intermediary updates (`commentary`) vs completed response (`final`) as distinct output streams. The framework should expose both; the host UI routes them differently. Verso could make this the standard agent output protocol.

8. **Explicit "you struggle with interactive git" weakness disclosure.** Telling the model about a known tool limitation is better than letting it discover it at runtime. Verso's tool descriptions should include failure-mode warnings where applicable.

9. **`update_plan` tool with `explanation` param on change.** Plan changes require a rationale. High-quality plan = 4-6 sequenced steps with specific actions/libraries. Verso's built-in plan tool should copy this exactly, including the anti-padding and anti-incapability rules.

10. **Preamble messages (1-2 sentences before tool-call groups).** Model trained to emit brief status updates before action groups. This is UX state management — the user knows what's happening. Verso's system prompt should include this convention with similar exemplars.

11. **3-iteration formatting cap.** Convergent with Cursor. Verso should include this in the default system prompt — try formatting up to 3 times, then present correct-but-unformatted and note it.

12. **Ambition vs precision mode detection.** New-project: ambitious. Existing-codebase: surgical precision, no gold-plating. Simple context detection, large behavioral difference. Include in Verso's default system prompt.

13. **`ToolSearch` / deferred tool loading.** Don't inline all tool schemas in the prompt. Register deferred tools, let the model call `tool_search` when it needs one. Reduces prompt bloat proportionally to tool count. Verso should ship this as a first-class pattern.

14. **AGENTS.md / VERSO.md hierarchy.** Walk upward to project root, collect all instruction files root-to-cwd, concatenate, apply byte budget. Verso should adopt this as the project-context injection pattern. `VERSO.md` or `AGENTS.md` (use the standard) at multiple levels.

15. **Code Mode (V8/JS-orchestrator as `exec` + `wait` tools).** This is the single most impactful architectural innovation for high-tool-count tasks. One JS program that orchestrates N tool calls in parallel costs one model round-trip vs N. Verso should provide an `exec` tool backed by a sandboxed JS runtime (rusty_v8, QuickJS, or a Python equivalent) as an opt-in escape hatch. The `store()`/`load()` cross-call persistence is also valuable.

16. **Agent graph store — generic trait, filesystem-backed default, cloud-backend pluggable.** Verso's multi-agent coordination should be persistence-agnostic from day one. Local FS default, Postgres/Redis plug-in.

### Avoid

1. **Monolithic codebase complexity.** 70+ crates is artifact of a production Rust workspace evolved over time. Verso should stay at a few well-defined modules until the surface area justifies splitting.

2. **Model-specific prompt file proliferation.** 6+ distinct prompt files with subtle per-model differences creates maintenance debt. Verso should parametrize the base prompt with clear variables rather than forking files per model.

3. **`max_depth = 1` for subagents by default.** This is too conservative for many legitimate use cases. Verso should make nesting depth configurable from the start and document the tradeoffs.

4. **Implicit max-iterations of zero.** No cap is right in theory but can produce runaway loops on broken tool calls. Verso should have an explicit `max_iterations` option that defaults to `None` (unlimited) but is easy to set per-run.

5. **Storing secrets in shell environment by default (passing SECRET/KEY/TOKEN through).** Codex's default is pragmatic but a security risk. Verso should default to explicit allowlisting of env vars passed to tools.

### Verso Could Improve By

1. **First-class bidirectional MCP.** Codex's symmetric MCP role (both server and client) means it can be embedded in any agent pipeline. Verso should expose itself as an MCP server (with a single `run_agent` tool) out of the box, making it composable with the broader MCP ecosystem.

2. **Context budget as a first-class configurable.** Codex hardcodes 95% and 2% for skills. Verso should expose `context_budget_policy` with per-section allocations (skill context, AGENTS.md, tool schemas) that sum to a percentage of the model window.

3. **`commentary` / `final` as a protocol-level streaming type.** Elevate this from a convention to a first-class `AgentOutputStream { kind: Commentary | Final | Approval, content }` type. Hosts always know how to route output without ad-hoc parsing.

4. **OTEL-native observability from day one.** Codex emits metrics for skill truncation, token usage, model reroutes. Verso should ship with OTEL traces and counters as a peer concern, not an afterthought.

5. **Personality as a first-class config.** The `default/friendly/pragmatic` personality system is underrated — different use cases need different communication styles. Verso should expose `personality: Personality` at the agent level with user-overridable values, not bake tone into the base prompt.
