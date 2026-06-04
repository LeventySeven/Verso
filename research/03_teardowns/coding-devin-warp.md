# coding-devin-warp — Verso Research Note

**Cluster:** Coding agents — Devin (Cognition AI) + Warp (warp.dev)
**Sources:** `teardowns/DEVIN.md` (2,485 lines, Tier-1A — leaked system prompt + JS bundle + GitHub) and `teardowns/WARP.md` (14,830 lines, Tier-1A — AGPL Rust source + leaked system prompt + blog)
**Date:** 2026-06-04

---

## System 1 — Devin (Cognition AI)

### Agent Loop Shape & Termination

Devin runs a **two-mode state machine**: `planning` and `standard`. Mode is set by the **user**, not the agent. In `planning` mode the agent reads, searches, runs LSP queries, browses — but cannot edit code. Once the agent calls `<suggest_plan/>` (a self-closing signal; plan content already conveyed via prior `<message_user>` calls), the user approves and toggles to `standard` mode. This is the first deployed implementation of "gate edits behind user-approved plan."

Loop structure (KNOWN, verbatim `Prompt.txt`):
- Agent emits **multiple tool calls per turn** (sequential, fail-fast: if action N fails, N+1..N+k are not executed).
- No published iteration cap in the leaked prompt. KNOWN failure sentinel: `max_iterations_reached` event type in the session event stream (visible in the dashboard JS bundle).
- Termination: agent decides completion itself — no explicit `done()` tool. Mandatory `<think>` before reporting completion (situation #3 of 13) ensures self-review before the final `<message_user>`.
- 3-CI-failure escape hatch: "When iterating on getting CI to pass, ask the user for help if CI does not pass after the third attempt." Prevents infinite retry loops on broken CI.

The **6-state session lifecycle** (`qa-devin/devin_api_client.py`, KNOWN verbatim):
```
working → blocked → finished (terminal)
         ↓
   suspend_requested → resume_requested → resumed → working
```
`blocked` = agent waiting on user (e.g. `<wait on="user"/>` or `request_auth=true`). `suspend_requested` / `resume_requested` = VM snapshot/restore via blockdiff. Sessions survive browser close, re-attach on wake.

### Models

| Role | Model | Source |
|---|---|---|
| Main agent loop | Opus 4.6 (default); Opus 4.7 / GPT-5.5 (enterprise preview flags `opus47PreviewEnabled` / `newModelApril23Enabled`) | bundle `/tmp/devin-index.js` |
| Side conversation / `find_and_edit` sub-LLM | Opus 4.6 Fast (first entry in `ksi` array, `Asi=admin-side-conversation-model`) | bundle |
| Devin Lite / free tier | SWE-1.6 served via Fireworks (200 tok/s) or Cerebras (950 tok/s paid) | blog |
| DeepWiki Q&A | Opus-tier (200k budget aligns with Anthropic context window) | `DeepWiki Prompt.txt:63` |

Multi-model routing is **enterprise-flag-gated**: org admin enables `['opus-4-7', 'gpt-5-5']` preview flags; individual sessions select from the active set. The leaked prompt was authored for **Claude 3.7 Sonnet** (based on dating markers: `<find_and_edit>` existence = post-Devin-2.0, `devinid` with coordinate fallback = transition to devinid).

### Tool Registry (KNOWN, verbatim `Prompt.txt`)

Full count: **32 tools** (31 non-think + 1 think). Grouped:

**Reasoning (1):**
- `<think>freeform</think>` — private scratchpad, user-invisible. 3 mandatory + 10 "should use" enumerated situations.

**Shell (4):**
- `<shell id exec_dir>cmd</shell>` — named session, long output truncated+saved to file, long-running returns snapshot.
- `<view_shell id/>` — poll running shell output.
- `<write_to_shell_process id press_enter>input</write>` — stdin injection (Ctrl+C/D, arrow keys via ANSI).
- `<kill_shell_process id/>` — SIGKILL.

**Editor (6):**
- `<open_file path start_line end_line sudo/>` — returns content + LSP outline + LSP diagnostics + diff-since-first-open (tracks file state across the task).
- `<str_replace path sudo many><old_str><new_str>` — exact-match find/replace.
- `<create_file path sudo>contents</create_file>`.
- `<undo_edit path sudo/>` — revert last edit.
- `<insert path sudo insert_line><content>` — line insertion.
- `<remove_str path sudo many>str` — exact-match deletion.
- **`<find_and_edit dir regex exclude file_extension>instruction`** — dispatches a **separate sub-LLM call per regex match** (parallel fan-out), each independently decides edit/skip. This is the unique multi-agent refactoring primitive.

**Search (3):**
- `<find_filecontent path regex/>` — ripgrep equivalent.
- `<find_filename path glob/>` — find -name equivalent.
- `<semantic_search query/>` — cross-repo vector retrieval with LLM-generated explanation notes.

**LSP (3):**
- `<go_to_definition path line symbol/>` — textDocument/definition.
- `<go_to_references path line symbol/>` — textDocument/references (use before refactoring).
- `<hover_symbol path line symbol/>` — type info, docstring.

**Browser (8):** navigate, view, click, type, restart (with extensions), move mouse, press key, browser_console (view output or run JS). All use `devinid` attribute as primary selector, XY coordinates as fallback. Chrome via Playwright.

**Deployment (3):**
- `<deploy_frontend dir/>` — deploy build folder, returns public URL.
- `<deploy_backend dir logs/>` — **FastAPI + Poetry projects only**, deploys to **Fly.io**.
- `<expose_port local_port/>` — public tunnel for user testing.

**User interaction (4):** wait, message_user (the ONLY user-visible channel), list_secrets, report_environment_issue.

**Git (2):** git_view_pr (better than `gh pr view`, shows comments+CI), gh_pr_checklist (tracks done/outdated per PR comment).

**Plan (1):** `<suggest_plan/>` — signal mode transition.

**Key tool constraints (KNOWN verbatim):**
- `grep`/`find` via shell are **forbidden** — must use built-in search tools.
- `cat`/file reading via shell is **forbidden** — must use `open_file`.
- The agent **may not** edit files via shell — must use editor tools.
- `<message_user>` is the **only** user-visible output channel. Everything else (thoughts, actions, tool results) is invisible unless explicitly messaged.

### The `find_and_edit` Multi-Agent Dispatch (KNOWN + INFERRED)

```
1. Agent emits <find_and_edit dir regex ...>edit instruction</find_and_edit>
2. Orchestrator: find all regex matches → collect (file_path, line, match, context) tuples
3. For each tuple (fan-out factor ~8-32, parallel):
   Sub-LLM system prompt: "You are a code editor. Decide whether to edit this location.
     If edit: emit <str_replace><old_str>...</old_str><new_str>...</new_str></str_replace>
     If skip: emit <no_edit reason='...'/>"
   Sub-LLM user: instruction + file_path + ~50 lines context around match
4. Apply all str_replace edits sequentially per file (avoid line-offset shifts)
5. Return to main agent: multi_edit_result event — "Edited 7/12 matches. Files: a.py, b.py"
```

Sub-LLM model: Opus 4.6 Fast (INFERRED from `ksi` array default for side conversations). The prompt's explicit "no big deal to have false positive matches" confirms the sub-LLM's primary job is false-positive filtering before making the edit.

### Context Assembly & Memory

**Per-task context:**
- Full conversation history (compacted when context approaches model limit — INFERRED).
- Approved plan (the content of the user's `suggest_plan` approval).
- VM filesystem (blockdiff-snapshotted, persists across sessions).
- Secrets store (per-task + per-org, accessed via `<list_secrets/>`).

**Cross-task memory (Knowledge/Playbooks/Notes, KNOWN):**
- Knowledge notes: short factual statements ("we use pytest-cov", "main branch is `main`"). Auto-indexed per repo, regenerated when stale. Agent can autonomously propose changes (user reviews via Suggestions queue).
- Playbooks: reusable task templates with outcome/steps/postconditions/forbidden-actions.
- AGENTS.md: file-based knowledge inside the repo.
- Index refresh: ~2 hours (per Cognition blog wording).
- Storage: INFERRED Postgres with vector search (semantic retrieval over notes).

**The `devinid` browser injection (INFERRED — high confidence):**
Cognition injects `devinid` attributes via Playwright `page.addInitScript()`. The script walks every interactive DOM element (`A`, `BUTTON`, `INPUT`, `SELECT`, `TEXTAREA` + ARIA roles + tabindex) and assigns a monotonic integer ID. MutationObserver keeps IDs fresh on SPA route changes. Orchestrator maps `devinid="N"` → `page.locator('[devinid="N"]').click()`. Fallback: XY coordinates for canvas/cross-origin-iframe elements.

### System Prompt (KNOWN verbatim, key fragments)

Identity: `"You are Devin, a software engineer using a real computer operating system."`

Planning mode (verbatim): `"While you are in mode 'planning', your job is to gather all the information you need to fulfill the task and make the user happy. [...] Once you have a plan that you are confident in, call the <suggest_plan ... /> command."`

Think tool mandatory situations (verbatim — 3 mandatory):
1. Before critical git/GitHub decisions (branch, PR creation).
2. When transitioning from exploring code to making code changes.
3. Before reporting completion — critically examine whether the request was fully fulfilled.

Approach to work: "When facing environment issues, report them to the user using `<report_environment_issue>` command. Then, find a way to continue your work without fixing the environment issues." Do not try to fix broken environments.

Never modify tests: "When struggling to pass tests, never modify the tests themselves, unless your task explicitly asks you."

Pop quizzes: `STARTING POP QUIZ` keyword suspends normal tool-using behavior. Quiz instructions take precedence over the system prompt. Agent cannot exit quiz on its own. This is Cognition's **production-time evaluation channel** — injectable eval that overrides the system prompt.

### Error Paths & Constants

| Constant | Value | Source |
|---|---|---|
| CI retry limit | 3 attempts before asking user | `Prompt.txt:403` |
| Git identity | `Devin AI <devin-ai-integration[bot]@users.noreply.github.com>` | `Prompt.txt:399` |
| Branch format | `devin/{unix_timestamp}-{feature-name}` | `Prompt.txt:400` |
| Edit truncation | ~500 lines per open_file | `Prompt.txt:114` |
| DeepWiki token budget | 200,000 | `DeepWiki Prompt.txt:63` |
| Deploy target | Fly.io | `Prompt.txt:327` |
| Deploy constraint | FastAPI + Poetry only | `Prompt.txt:327` |
| find_and_edit parallelism | ~8-32 sub-LLM calls (INFERRED) | orchestrator design |
| Sub-LLM context window | ~4-8K tokens per match | INFERRED |
| max_iterations_reached | session event type confirming a hard cap exists | bundle |

### Multi-Agent Coordination

**Concurrent Devins (KNOWN from blog):** Each Devin is a separate VM. No shared filesystem. Coordination via GitHub PR comments, Slack threads, Linear tickets — the same channels human engineers use. Parent Devin can spawn children via `devin_session_create` (MCP tool), monitor via `devin_session_interact`, consume their event streams via `devin_session_events`. Multi-agent orchestration as JSON-RPC MCP, not in-process Python.

**DeepWiki** is a read-only sibling product (same agent identity, different prompt, no tools that write). Hotkey Cmd+Enter upgrades a Q&A answer to a full Devin task.

**Devin Review** = sub-agent that reviews PRs. Triggered by replacing `github.com` with `devinreview.com` in any PR URL, or by auto-review config on PR open/commit push.

### Streaming

INFERRED: SSE from `api.devin.ai/tasks/{id}/stream`. Session UI is event-stream driven — 327+ unique `type:` discriminators in the bundle. Key event types: `tool_call`, `tool_group` (parallel batch), `multi_edit_result`, `plan`, `plan_accepted`, `set_mode`, `devin_thoughts` (collapsed-by-default `<think>` blocks), `max_iterations_reached`, `progress_update`.

### Verso Lesson — Devin

**Copy:**
- Two explicit operating modes (planning gate before edits) with user-controlled transition. The simplest and most reliable way to prevent an agent from making edits before it has enough context.
- Mandatory `<think>` with 13 enumerated trigger conditions. Force reflection at specific decision points (before git decisions, before edits, before reporting done). Verso should copy this pattern as structured per-tool scratchpad.
- `find_and_edit` as a first-class multi-agent fan-out primitive baked into a single tool call. Verso's tool system should expose this as a built-in capability rather than requiring the developer to implement fan-out manually.
- LSP tools as first-class tools (go_to_definition, go_to_references, hover_symbol). Corso's tool registry should include LSP by default for coding contexts.
- `devinid` browser addressing — inject stable IDs via page.addInitScript(), never rely on CSS selectors or coordinates as primary.
- 3-attempt hard limit for CI retries before escalating to user. All agent loops need bounded retry with a user-escalation path.
- `<message_user>` as the single user channel + `<think>` as the invisible scratchpad. Clean separation between agent reasoning (private) and agent communication (explicit). Verso should enforce this split at the framework level.
- The 6-state session lifecycle (working/blocked/finished + suspend/resume/resumed). Verso should support VM-snapshotted session persistence.
- Multi-agent-as-MCP: spawn child agents via JSON-RPC tools, not in-process orchestration. The protocol is the interface, not the runtime.
- Pop quiz / superuser eval channel: a mechanism to inject evaluation prompts that override the system prompt is an essential production telemetry primitive.

**Avoid:**
- Undifferentiated "call GPT with a plan" — Devin's value is in the planning-mode gate, mandatory think, LSP tooling, and find_and_edit parallelism. Copy the engineering, not the marketing.
- Forcing a single deployment target (Fly.io + FastAPI + Poetry) without escape hatches.

---

## System 2 — Warp (warp.dev)

### Agent Loop Shape & Termination

Warp's loop is **client-driven, server-orchestrated**. The Rust desktop client assembles a protobuf request, ships it to Warp's backend over SSE; the backend resolves the model + builds the system prompt + streams back text and tool calls; the client executes tools **locally**; the client **auto-re-sends** tool results as the next request.

**The continuation rule (KNOWN verbatim, `controller.rs:461-537`):**
```rust
// should_trigger_request_upon_completion() = !self.is_cancelled()
```
Any non-cancelled tool result (including a *failed* one) automatically triggers the next model request. **There is no max-iteration count on the client.** The loop terminates only when:
1. The server stream finishes with no pending tool calls (clean completion), or
2. Every result in the batch is cancelled.

Three modifiers on continuation:
- `is_passive_code_diff` — a slash-command diff (not an agentic turn) does not trigger a follow-up.
- `is_lrc_command_completed` — completion of a long-running command routes the next turn to the server CLI subagent, not a new orchestrator turn.
- `has_manual_follow_up` — user-queued follow-up forces continuation regardless.

**Single in-flight stream invariant (KNOWN, `controller.rs:2244-2267`):** before sending, the controller `safe_assert!`s there is no in-flight stream for the conversation. One conversation = at most one live stream, strictly enforced.

**Single-agent thesis (KNOWN verbatim, SWE-bench blog):** Warp explicitly tried and rejected dedicated testing/reasoning agents, planner/executor splits, and best@k voting for the primary coding loop. Conclusion: "the most consistent, reliable architecture remained our single primary agent." The reason is **latency**: "the additional latency of multi-attempt approaches may be untenable" for a real-time terminal. For SWE-bench 75.8% they added a "light best@k wrapper" framed strictly as "non-determinism smoothing, not a capability change."

For long-running commands: "this does not use a separate agent — we've found that using the **same agent with a restricted tool set is more reliable due to context window preservation**." Same conversation, same context window, different advertised tools.

### Models

**Four-slot `ModelConfig` (KNOWN verbatim, `llms.rs:412-423`):**
```rust
pub struct ModelsByFeature {
    pub agent_mode:   AvailableLLMs,           // base — the orchestrator model
    pub coding:       AvailableLLMs,           // coding — server-resolved, unused client-side
    pub cli_agent:    Option<AvailableLLMs>,   // cli_agent — long-running command model
    pub computer_use: Option<AvailableLLMs>,   // computer_use_agent — vision subagent
}
```
All slots default to `"auto"` — an opaque string the server resolves to a concrete provider+model. The client never names a provider model. This is how Warp swaps the default model without a client release.

**Model string format (`crates/ai/src/llm_id.rs:3-35`):** `LLMId` is a transparent `#[serde(transparent)]` newtype over `String`. Concrete model strings are fetched from the server and cached in user prefs. The crate carries only the opaque string.

**The `auto*` router family (KNOWN from docs snapshot):**
- `auto` — highest-quality fastest available.
- `auto-efficient` — lower credit consumption.
- `auto-genius` — adapts to task complexity, picks most capable when warranted.
- `auto-open` — routes between open-source models (GLM, Kimi, Minimax, Qwen).

**Current model menu (KNOWN, freshness-sensitive):** OpenAI GPT-5.2/5.3/5.4/5.5 (low|medium|high|xhigh reasoning); Anthropic Claude Opus 4.7/4.6/4.5 + Sonnet 4.5/4.6 + Haiku 4.5; Google Gemini 3.1 Pro; Fireworks-hosted open models.

**Cross-model FAILOVER CHAINS (KNOWN verbatim — single most important routing fact):**

The stated reason (verbatim): "We originally attempted to retry with the same model, and found that this often produced repeat failures." Switch to cross-model fallback.

Triggers: outage, rate-limit, malformed tool call, invalid response.

SWE-bench 71% chain:
```
1. Anthropic Claude 4 Sonnet
   ↓ (outage/rate-limit/malformed)
2. Anthropic Claude 3.7 Sonnet
   ↓
3. Google Gemini 2.5 Pro
   ↓
4. OpenAI GPT-4.1
```

Terminal-Bench 52% chain: Plan = Claude Opus 4, Execute = Claude Sonnet 4, Fallback = Gemini 2.5 Pro or GPT-4.1 (~2% of runs).

Current (post-Sep 2025): primary = GPT-5.x, same chain mechanism.

**`LLMInfo` per-model metadata (KNOWN verbatim, `llms.rs:156-171`):**
```rust
pub struct LLMInfo {
    pub reasoning_level: Option<String>,       // "high", "max", "xhigh" — free-form string
    pub spec: Option<LLMSpec>,                 // { cost: f32, quality: f32, speed: f32 }
    pub host_configs: HashMap<LLMModelHost, RoutingHostConfig>,  // DirectApi|AwsBedrock|CustomEndpoint
    pub context_window: LLMContextWindow,      // { is_configurable, min, max, default_max }
    pub disable_reason: Option<DisableReason>, // AdminDisabled|OutOfRequests|ProviderOutage|RequiresUpgrade
    ...
}
```
`DisableReason::should_clear_preference`: `ProviderOutage` → **keep** the user's preference (transient, will restore). This is the client-side half of failover/restore.

### Tool Registry (29 Variants, KNOWN verbatim `action/mod.rs:32-177`)

The registry has three views at three granularities — they are the same registry, not contradictions:
- **29-variant `AIAgentActionType`** — full client capability.
- **Wire `ToolType` advertisement** — dynamic per-request subset (feature-flag gated).
- **7-tool leaked prompt** — the model-facing coding subset the server narrates in prose.

**Always-on base tools (every request):** `Grep`, `FileGlob`, `FileGlobV2`, `ReadMcpResource`, `CallMcpTool`, `InitProject`, `OpenCodeReview`, `RunShellCommand`, `SuggestNewConversation`, `Subagent`, `WriteToLongRunningShellCommand`, `ReadShellCommandOutput`, `ReadDocuments`, `CreateDocuments`, `EditDocuments`, `SuggestPrompt`.

**Conditionally added (feature-flag or session):** `ReadFiles`/`ApplyFileDiffs`/`SearchCodebase` (local only), `UseComputer`/`RequestComputerUse` (FF `AgentModeComputerUse`), `RunAgents` (FF `RunAgentsTool` + `OrchestrationV2`), `ReadSkill` (FF `ListSkills`), `AskUserQuestion` (FF), `InsertCodeReviewComments` (FF), `UploadArtifact` (FF), `FetchConversation` (FF).

**Key tool variant details:**

`RequestCommandOutput` — the shell primitive. Model tags each command with:
- `is_read_only: Option<bool>` — LLM's judgment of side-effect-free.
- `is_risky: Option<bool>` — requires user confirmation.
- `wait_until_completion: bool` — if false + long-running: returns a PTY snapshot instead of blocking (this is the LRC mechanism).
- `uses_pager: Option<bool>`.

`WriteToLongRunningShellCommand { block_id, input: Bytes, mode: Raw|Line|Block }` — inject bytes into a running PTY (drive REPLs, vim).

`RequestFileEdits { file_edits: Vec<FileEdit>, title }` — `FileEdit::Edit(ParsedDiff) | Create{file,content} | Delete{file}`. The fuzzy-match diff applier (4-tier ladder, see Error Handling).

`RunAgents(RunAgentsRequest)` — batch multi-agent fan-out:
```rust
pub struct RunAgentsRequest {
    pub base_prompt: String,          // shared instruction for all children
    pub skills: Vec<SkillReference>,
    pub model_id: String,
    pub harness_type: String,         // "oz"|"claude"|"opencode"|"gemini"|"codex"
    pub execution_mode: RunAgentsExecutionMode,  // Local | Remote{environment_id, worker_host}
    pub agent_run_configs: Vec<RunAgentsAgentRunConfig>,  // per-child name/prompt/title
    pub plan_id: String,
}
// per-child prompt: base_prompt + "\n\n" + agent_run_configs[i].prompt
```

`StartAgent { name, prompt, execution_mode, lifecycle_subscription }` — spawn one child.

`SendMessageToAgent { addresses, subject, message }` — point-to-point mailbox (128 KB body cap, `POST /agent/messages`).

`AskUserQuestion { questions: Vec<AskUserQuestionItem> }` — `AskUserQuestionType::MultipleChoice { is_multiselect, options, supports_other }`. Structured clarifying questions.

`TransferShellCommandControlToUser { reason }` — hand PTY back to user.

**Dual-agent tool partition (KNOWN verbatim, `impl.rs:256-284`):**
During a long-running command, the CLI subagent takes over with a restricted set:
```
CLI subagent: WriteToLongRunningShellCommand, ReadShellCommandOutput, Grep, FileGlob, FileGlobV2
           + TransferShellCommandControlToUser (FF)
           + ReadFiles, SearchCodebase (local)
```
Same conversation, same context window — the partition is enforced by swapping `get_supported_tools()` for `get_supported_cli_agent_tools()` in the request `Settings`. The agent cannot start a second shell command or a file edit while one is in flight.

**5 Harnesses for `RunAgents`/`StartAgent` (KNOWN verbatim):**
```rust
"oz"          → Harness::Oz        (Warp-native agent, model via Warp catalog)
"claude"      → Harness::ClaudeCode (Claude Code CLI subprocess)
"opencode"    → Harness::OpenCode  (OpenCode CLI)
"gemini"      → Harness::Gemini    (Gemini CLI)
"codex"       → Harness::Codex     (OpenAI Codex CLI)
```

Per-harness model delivery (KNOWN verbatim, critical for replication):
- Claude Code → `ANTHROPIC_MODEL` env var (beats `--model` flag, avoids settings.json conflicts).
- Codex (Cloud) → rewrite `~/.codex/config.toml` key `model` via `toml_edit` (preserves other user keys).
- Codex (Local) → no override (shared global config, races with parallel agents).
- Oz → model id rides the proto request to Warp's backend.

### System Prompt (KNOWN verbatim — two independent leaks, textually identical)

Identity: `"You are Agent Mode, an AI agent running within Warp, the AI terminal."`

The prompt text lives **entirely server-side**. The client's contribution is a structured `Settings` capability bitmap + tool advertisement + rules + skills. Warp's `ResolvePromptHandler` (Go, `warp-server/.../logic/ai/prompt/tools/suggest_diff.yaml`) templates the final prompt from it.

Key verbatim rules:
- "Before responding, think about whether the query is a question or a task." (Question → give instructions only, ask if they want you to perform it. Task → execute directly.)
- For `run_command`: "NEVER use interactive or fullscreen shell Commands." "Try to maintain your current working directory throughout the session by using absolute paths and avoiding usage of `cd`."
- For `read_files`: "This can only respond with 5,000 lines of the file." "When processing large files, always request exactly 5,000 line chunks."
- For `edit_files`: "Never abridge or truncate code in either the 'search' or 'replace' section." "DO NOT USE COMMENTS LIKE `// ... existing code...` OR THE OPERATION WILL FAIL."
- "IMPORTANT: Do not use terminal commands (`cat`, `head`, `tail`, etc.) to read files. Instead, use the `read_files` tool."
- "IMPORTANT: NEVER edit files with terminal commands."
- Task completion: "Do exactly what was requested by the user, no more and no less! [...] don't automatically commit and push the changes without confirmation."
- "Bias toward action to address the user's query. If the user asks you to do something, just do it, and don't ask for confirmation first."
- Secret handling: "For any terminal commands you provide, NEVER reveal or consume secrets in plain-text. Instead, compute the secret in a prior step using a command and store it as an environment variable."
- Citations: "If you use external context OR any of the user's rules to produce your text response, you MUST include them after a `<citations>` tag." (Format: `<document><document_type>...</document_type><document_id>...</document_id></document>`)

### Context Assembly

**Three rule sources, two transport mechanisms (KNOWN, `specs/APP-3893`, `project_context/model.rs`):**

1. **Project rules** — `WARP.md` / `AGENTS.md` files, walked up from CWD. Shipped **by value** (full file contents) in every request. Also honors: `CLAUDE.md`, `.cursorrules`, `AGENT.md`, `GEMINI.md`, `.clinerules`, `.windsurfrules`, `.github/copilot-instructions.md`. Constants: `MAX_SCAN_DEPTH = 3`, `MAX_FILES_TO_SCAN = 5000`.
2. **Cloud `AIFact`s** — created in-app, server-held. Client ships only the `rules_enabled: bool` bit. Server applies them. Key asymmetry: **project/global rules by value; cloud rules by flag only.**
3. **Global rules** — `~/.agents/AGENTS.md`. Shipped by value. Watched by `HomeDirectoryWatcher` with ~500ms debounce.

Rule precedence: `global > project WARP.md > project AGENTS.md`.

**Codebase context (KNOWN, `chunker.rs:14-21`):**
- Client builds SHA-256 Merkle tree of code fragments, syncs to server (server embeds).
- Chunking: `LINES_PER_CHUNK = 200`, `MAX_BYTES_PER_CHUNK = 12000`.
- `RETRIEVE_FRAGMENT_CONTEXT_LENGTH = 0` — deliberately zero context lines attached to retrieved fragments ("does not improve quality and causes token-efficiency issues").
- Semantic search returns fragments + LLM-generated explanation notes.

**Skills — progressive disclosure (KNOWN, `parse_skill.rs:12`):**
- Skill descriptor (≤512 chars, `MAX_SKILL_DESCRIPTION_CHARS = 512`) advertised every request.
- Full skill content fetched only on `ReadSkill` tool call.
- 10-provider precedence: `Agents > Warp > Claude > Codex > Cursor > Gemini > Copilot > Droid > Github > OpenCode`.

**@-mentions (KNOWN):** Files, folders, code symbols (with line number), terminal blocks, Warp Drive objects, prior conversations. All by value as citable `<document>`s. URL content is **pre-fetched by the Warp client** — the agent has no browser.

### Memory & Self-Improving Loop

Three layers:

1. **Transient:** SQLite-backed `AgentConversationData` JSON blob. Enables session restore across restarts. `was_summarized` monotonic bool (false→true only — a conversation never un-summarizes).

2. **Durable cloud `AIFact`s:** server-held, applied via `rules_enabled` flag.

3. **Self-improving loop (KNOWN verbatim, `block.rs:2137-2189`):**
After every agent response, `AIBlock::handle_complete_output` inspects output for suggested rules. Creates an inline "save this as a rule" chip. User one-click saves → persisted as cloud `AIFact` → applies server-side on all future requests. The loop is: agent observes interaction → proposes rule → user approves → rule shapes every future prompt (no developer intervention).

Fallback: when no rule suggestions, the same chokepoint emits **agent-mode workflow suggestion chips** instead.

### Context-Window Compaction (KNOWN verbatim)

`SummarizeConversation` is a first-class `AIAgentInput` variant processed through the same driver path as a user turn:
```rust
SummarizeConversation {
    prompt: Option<String>,          // None = server-templated
    context: Arc<[AIAgentContext]>,  // carries rules + TODO blocks
}
```

Design choices (KNOWN, verbatim from blog + source):
- Summary produced by **the same model** as the conversation — no separate summarizer.
- **TODO state + rules are deterministically preserved** via the structured `context` payload — not left to LLM discretion.
- Earlier turns are **replaced in-place** by the summary (not appended) — the window is freed, not expanded.
- The most-recent turn is seeded verbatim (un-lossy immediate context).
- File-edit token reduction: return only the modified section ± surrounding lines, never the whole file.

Fresh-conversation auto-segmentation triggers:
- Shell command then AI query → new conversation.
- 3 hours idle → new conversation.
- Topic shift → *suggest* new conversation (`SuggestNewConversation` tool, not forced).

Manual slash commands: `/compact`, `/fork`, `/fork-and-compact`, `/compact-and`.

Context usage indicator: hidden below 20%, red near full.

### Error Handling (KNOWN verbatim)

**Three distinct recovery layers:**

1. **Client whole-stream retry (KNOWN, `response_stream.rs:263-339`):**
```rust
const MAX_RETRIES: usize = 3;
let should_retry = !self.has_received_client_actions   // no partial work done yet
    && is_retryable
    && self.retry_count < MAX_RETRIES
    && is_online;
```
If `ClientActions` were already received (partial work done) → schedule **conversation resume** instead of blind retry. `AUTO_RESUME_TIMEOUT = 120s`.

2. **Server per-tool-call retry** — server retries individual failed tool calls (stated in blog, exact mechanism server-side).

3. **Server cross-model failover chain** — NOT same-model retry. The key finding: "retry with the same model often produced repeat failures."

**Tool failure continuation (KNOWN):** `is_failed()` is not `is_cancelled()`. A failed tool result still triggers the next request (the model sees the failure and self-corrects). Loop only stops on *cancelled* or clean completion.

**Edit-match failure — 4-tier fuzzy ladder (KNOWN, `diff_validation/mod.rs`):**
1. Exact match (`SECTION_MATCH_THRESHOLD = 0.9`, binary 1.0 exact).
2. Indentation-agnostic match @ 0.9.
3. Prefix-tail rescue @ 1.0 (only with line-number hint).
4. Jaro-Winkler (`strsim::jaro_winkler`) @ 0.9.
- Localization radius: ±2 lines.
- On ladder exhaustion → `DiffApplicationFailed` result → fed back to model for correction.
- Noop guard: if `stripped_search == replace` → skip (no diff emitted).

**Harness runtime-failure detection (KNOWN, `specs/REMOTE-1385`):**
- Scan schedule: `[(5s delay, 30s window), (15s delay, 60s window)]` (~90s total).
- Confirm stall: two consecutive byte-identical plaintext snapshots + pattern still present (prevents false positives from transient API retries).
- Failure excerpt capped to ~240 chars, secrets obfuscated.
- Stall poll interval: 10s. Confirmation budget: 60s.
- A detected failure always **drops resume state** — a failed run must not be silently resumable.

**NL vs. shell input classifier (KNOWN, `input_classifier`):**
Heuristic gauntlet (word lists, token ratio) → BERT-tiny ONNX model (17.6 MB, 128-token fixed input, softmax `[0]=p_ai [1]=p_shell`, tie→AI).
- `AGENT_FOLLOW_UP_INPUTS = {yes, continue, "do it", approve}` — these stay in the agent, not classified as shell.
- `OnnxClassifier` falls back permanently to `HeuristicClassifier` if inference panics.

### Constants Table

| Constant | Value | Source |
|---|---|---|
| `MAX_RETRIES` | 3 | `response_stream.rs:274` |
| `AUTO_RESUME_TIMEOUT` | 120s | `driver.rs:132` |
| `SETUP_FAILED_IDLE_TIMEOUT` | 120s | `driver.rs:128` |
| `HARNESS_SAVE_INTERVAL` | 30s | `driver.rs:124` |
| Harness scan schedule | [(5s,30s),(15s,60s)] | `specs/REMOTE-1385` |
| Stall poll interval | 10s | `specs/REMOTE-1385` |
| Stall confirmation budget | 60s | `specs/REMOTE-1385` |
| Harness failure excerpt cap | ~240 chars | `specs/REMOTE-1385` |
| `SECTION_MATCH_THRESHOLD` | 0.9 | `diff_validation/mod.rs:933` |
| Edit localization radius | ±2 lines | `diff_validation/mod.rs:1010-1011` |
| Ctrl-C exit code sentinel | 130 | `action_result/mod.rs:194-195` |
| `read_files` window | 5,000 lines/file/response | leaked prompt |
| Codebase file limit | ≥5,000 files (plan-tiered) | docs |
| `LINES_PER_CHUNK` | 200 | `chunker.rs:14-21` |
| `MAX_BYTES_PER_CHUNK` | 12,000 | `chunker.rs:14-21,97-106` |
| `RETRIEVE_FRAGMENT_CONTEXT_LENGTH` | 0 | `codebase_index.rs:81` |
| `REPO_SNAPSHOT_SHELF_LIFE_DAYS` | 30 | `snapshot.rs:27` |
| `MAX_SKILL_DESCRIPTION_CHARS` | 512 | `parse_skill.rs:12` |
| Skill providers | 10 (Agents > Warp > Claude > ...) | `skill_provider.rs:104-158` |
| `MAX_ATTACHMENT_SIZE_BYTES` | 10 MiB | `attachment_utils.rs:7` |
| `MAX_ATTACHMENT_COUNT_FOR_CLOUD_QUERY` | 25 | `driver/attachments.rs:23` |
| Context indicator hidden | <20% window used | docs |
| Fresh conversation: idle | 3 hours | docs |
| `RULES_FILE_PATTERN` | `["WARP.md","AGENTS.md"]` (case-insensitive) | `model.rs:20` |
| `MAX_SCAN_DEPTH` (rules) | 3 | `model.rs:21` |
| `MAX_FILES_TO_SCAN` (rules) | 5,000 | `model.rs:22` |
| Rule precedence | global > WARP.md > AGENTS.md | `model.rs:39-43` |
| `EVENT_POLL_BATCH_LIMIT` | 100 | `orchestration_event_streamer.rs` |
| OZ_PARENT_MAX_CONTEXT_CHARS | 6,000 | `harness/mod.rs:42-43` |
| Agent inbox message body cap | 128 KB | `/agent/messages` OpenAPI |

### Multi-Agent Orchestration

**Single-agent by default.** Multi-agent only when the user explicitly invokes `RunAgents` (FF-gated). The system is designed to make single-agent the natural path; multi-agent requires deliberate intent.

**`RunAgents` confirmation gate (KNOWN verbatim, `orchestration_config.rs:64-96`):** A `RunAgents` tool call does NOT automatically spawn children — it renders a confirmation card first. It skips the card only if the request matches the user-approved `OrchestrationConfig` for that plan (matching on `model_id`, `harness_type`, `execution_mode` only — per-child prompts are explicitly excluded from the match because they don't change the trust boundary).

**`OrchestrationConfig` persistence:** append-only protobuf snapshots per `plan_id`. Most-recent snapshot per plan_id wins (backward scan). Config edits sync as "dirty events" piggybacked on the next outbound request.

**Orchestration event bus (parent ↔ child):**
- Dual cursor persistence: `cursor = max(SQLite cursor, server cursor)`. Never deliver the same event twice across a restart.
- Same monotonic `int64` sequence regardless of transport (SSE push or cursor long-poll).
- Parent watches child `run_id`s via `watched_run_ids: HashSet<String>`.
- Agent inbox: `POST /agent/messages` (point-to-point, 128 KB body, per-recipient delivery state).

**Two-level run model:** stable `ai_task` (run) → many `ai_run_executions` (attempts). A follow-up is a new execution under the same run, not a new conversation.

### Streaming Protocol (Three Mechanisms)

1. **GraphQL + WebSocket subscription** — config/control plane. `POST https://app.warp.dev/graphql/v2` for queries/mutations. `wss://rtc.app.warp.dev/graphql/v2` with `graphql-transport-ws` sub-protocol for Warp Drive change-feed subscriptions. Firebase ID token auth. Introspection disabled.

2. **SSE + base64-protobuf** — agent token stream. `POST {server_root}/ai/multi-agent`. Request body = protobuf `api::Request`, `Content-Type: proto`. Response = SSE frames, each `Event::Message.data` = base64-url-safe-encoded `ResponseEvent` protobuf. Three stream event types: `Init(StreamInit)`, `ClientActions(...)`, `Finished(StreamFinished)`. Wake-lock held for stream duration.

3. **Cursor long-poll** — cloud-agent events. `GET /agent/events?run_ids=...&since=<int64>`. Monotonic sequence cursor. No SSE, no WebSocket. Transcripts: `GET /agent/runs/{runId}/transcript` → 302 redirect to signed GCS URL.

4. **Computer-use action wire** — model-agnostic atomic primitives: `MouseDown/Up`, `MouseMove`, `MouseWheel`, `KeyDown/Up`, `TypeText`, `Wait`. Provider-specific actions (Anthropic `left_click`, etc.) translated server-side. Client is thin (zero per-provider code). Cloud sandbox uses Xvfb headless X11.

### Verso Lesson — Warp

**Copy:**
- **Cross-model failover chain, not same-model retry.** Warp's hardest-won finding: "retry with the same model often produced repeat failures." Verso's error layer should implement a heterogeneous failover chain (Sonnet → Gemini Pro → GPT-4.1) triggered on outage/rate-limit/malformed-tool-call/invalid-response. This is a framework-level responsibility, not application-level.
- **Client-side continuation rule as `!is_cancelled()`** — elegant. Failed tool results continue the loop (model self-corrects). Only user cancellation stops the loop. Simple, composable, correct.
- **Single in-flight stream per conversation** enforced by `safe_assert!`. Prevents duplicate/racing requests. Verso should make this a hard invariant at the runtime level.
- **4-tier fuzzy edit-match ladder** before declaring failure. Exact → indentation-agnostic → prefix-tail → Jaro-Winkler at 0.9, ±2 line radius. Verso's edit tools should implement this as a built-in capability.
- **Same-model compaction** — summarize with the conversation's own model, not a cheap side-model. Carry rules/TODO in a structured context payload (deterministic preservation), not in free-text history.
- **Dual cursor persistence for agent event bus** — `max(local_cursor, server_cursor)` on restore. Never deliver the same event twice, never skip events across restart. Essential for reliable multi-agent orchestration.
- **RunAgents confirmation gate** — require user approval before spawning N credit-consuming child agents. The match only covers model+harness+local/remote (trust boundary), not per-child prompts (which can vary freely).
- **`SkippedByAutoApprove` is not `Cancelled`** — an auto-approve skip continues the loop. Verso should model permission outcomes as `Executed | Approved | Skipped | Cancelled`, where only `Cancelled` stops the loop.
- **Dynamic tool advertisement per request** — the server only narrates the tools the client said it supports. Verso's system prompt should be assembled from a capability bitmap, not hardcoded. This is what allows feature-flag-gated tool introduction without prompt rewrites.
- **Request-level capability bitmap** (`supports_parallel_tool_calls: true`, `use_anthropic_text_editor_tools: false`, `autonomy_level: Supervised|Unsupervised`) as first-class request fields, not prompt hacks.
- **Skill progressive disclosure** — advertise ≤512-char descriptors every request; fetch full content only on demand. Keeps context lean for the common case.
- **Three-tier rule hierarchy** (global > project > local) with the by-value/server-held asymmetry for cloud memory. Verso's rule system should mirror this exact precedence and transport split.
- **Two distinct "5000" constants** must not be conflated: read window (5,000 lines per response) vs. codebase index size (≥5,000 files). Different mechanisms, same number.
- **LRC (long-running command) tool-set swap** — during a blocking command, swap full tool set for shell-IO + read/search only. Same conversation, same context, swapped capability. This is context window preservation by constraint, not by sub-agent isolation.
- **BERT-tiny ONNX input classifier** for NL vs. shell disambiguation before the agent ever sees input. Ship a small local classifier for intent routing, not a model call.
- **Task lists +2% SWE-bench** (verbatim attribution). Dynamic per-step TODO as a first-class context item is measurable improvement.

**Avoid:**
- The complexity of Warp's client/server split where the system prompt lives entirely on the server. For Verso, keeping the prompt template client-side (or at the framework layer) is simpler and more inspectable.
- Growing the tool registry to 29 variants without strong feature-flag discipline. Warp has 29 variants but only ~16 are advertised by default; the rest are FF-gated. Always-on tool count should be minimal.
- `"auto"` model strings whose resolution is a complete server black box. Verso should have an explicit model routing layer with observable failover chain state.
- Separate model slots for `agent_mode` / `coding` / `cli_agent` / `computer_use` — this is over-designed for most use cases. Start with one slot + override mechanism.
- LangGraph/CrewAI-style mandatory multi-agent fan-out. Warp's empirical result: single-agent is more reliable for coding tasks at interactive latency. Multi-agent should be opt-in escape hatch, not the default.

---

## Cross-System Findings

### Loop Architecture

| Dimension | Devin | Warp |
|---|---|---|
| Loop driver | Server-side orchestrator | Client-driven auto-re-send |
| Iteration cap | `max_iterations_reached` event (cap exists, value not leaked) | **None on client** (continuation = `!is_cancelled()`) |
| Mode gating | Two explicit modes, user-controlled transition | No explicit modes; Question-vs-Task routing in prompt |
| Think tool | Mandatory XML scratchpad, 13 trigger conditions | Not present; thinking via `reasoning_level` model flag |
| Tool dispatch | Multiple per turn, sequential fail-fast | Parallel tool calls (`supports_parallel_tool_calls: true`) |
| Retry on failure | Ask user after 3 CI failures | Continue loop (model self-corrects), client retry ≤3, cross-model fallover |

### Context Management

| Dimension | Devin | Warp |
|---|---|---|
| Rules format | AGENTS.md + playbooks + knowledge notes (RAG-indexed) | WARP.md/AGENTS.md by value + cloud AIFacts by flag |
| Rule transport | Not specified (INFERRED server-side injection) | Project/global by value in request; cloud flag-only |
| Compaction | INFERRED summarization when context approaches limit | Explicit SummarizeConversation with same-model, deterministic TODO preservation |
| Memory self-improvement | Agent autonomously proposes knowledge note changes → user reviews | Agent proposes rules via suggestion chips → user one-click approves |
| File reading | `open_file` with LSP diagnostics + diff-since-first-open | `read_files` (5,000 line chunks) + `search_codebase` (vector) |

### Tool System Design

| Dimension | Devin | Warp |
|---|---|---|
| Tool protocol | XML DSL in assistant message | Protobuf `AIAgentActionType` enum, server narrates in prose |
| Diff application | `str_replace` (exact match required) | 4-tier fuzzy ladder (Jaro-Winkler fallback) |
| Multi-file refactor | `find_and_edit` (sub-LLM per match, server fan-out) | `RequestFileEdits` (single diff application, no fan-out) |
| LSP tools | First-class: go_to_definition, go_to_references, hover_symbol | Not in tool registry (search/read only) |
| Browser | Playwright + devinid injection | No browser (`curl` via shell for URL fetch) |
| LRC/PTY | Long-running shells via shell sessions | `WriteToLongRunningShellCommand` + tool-set swap |

### Multi-Agent

| Dimension | Devin | Warp |
|---|---|---|
| Default architecture | Single main agent + sub-LLMs via `find_and_edit` | Single agent (explicitly chosen over fan-out) |
| Fan-out mechanism | `find_and_edit` (server-side); `devin_session_create` (MCP) | `RunAgents` (FF-gated, confirmation card) |
| Fan-out confirmation | No explicit gate for `find_and_edit`; MCP tool for session spawn | `OrchestrationConfig` approval required |
| Child-parent communication | MCP: `devin_session_interact`, `devin_session_events` | `SendMessageToAgent` (inbox API, 128 KB), event bus cursor |
| Agent harnesses | Devin VM only | 5 harnesses: oz, claude-code, opencode, gemini, codex |
| Benchmark stance | Concurrent Devins for throughput (not latency) | Single-agent wins on latency; best@k only for variance reduction |

---

## → Verso Implications

1. **Default to single-agent with a clean escape hatch.** Both systems independently arrived at single-agent as the correct primary architecture for interactive use. Verso's default should be one ReAct loop. Fan-out should require explicit developer opt-in with a confirmation step for blast-radius actions.

2. **Implement cross-model failover at the framework level, not the application level.** Warp's empirical finding is clear: same-model retry fails. Verso should ship a heterogeneous failover chain (configurable: primary → fallback-1 → fallback-2) triggered on outage/rate-limit/malformed-tool-call. This is a framework primitive, not a user concern.

3. **Loop continuation = `!is_cancelled()`.** Simple, correct, composable. A failed tool result continues the loop. A skipped-by-auto-approve result continues the loop. Only explicit cancellation stops it. Implement this as the default loop predicate.

4. **Force explicit scratchpad with enumerated trigger conditions.** Devin's `<think>` with 13 mandatory/should-use triggers is the strongest "force reflection" mechanism seen in any deployed agent. Verso should expose a `scratchpad` tool with framework-documented trigger conditions (before edits, before done, before risky decisions). Frameworks that leave this to the developer get agents that skip thinking.

5. **Implement a planning-mode gate.** Devin's two-mode state machine (explore vs. edit) prevents premature code changes. Verso should expose `planning_mode: bool` as a first-class session parameter. In planning mode, write tools should return `PlanningModeError` (not silently execute).

6. **Fuzzy edit matching is load-bearing infrastructure.** Both Devin (`undo_edit` + diff-since-first-open) and Warp (4-tier Jaro-Winkler ladder) invest heavily in edit reliability. Verso's `edit_files` tool must implement at minimum: exact match → indentation-agnostic match → Jaro-Winkler @ 0.9, ±2 line radius. Return `DiffApplicationFailed` on ladder exhaustion so the model can self-correct.

7. **Same-model compaction with deterministic rule/TODO preservation.** Do not use a cheap side-model for summarization. Carry structured context (rules, active tasks) as a typed payload through the summarization turn so the model doesn't decide whether to preserve them.

8. **Skill progressive disclosure.** Advertise ≤512-char descriptors in every prompt; fetch full content on demand via `read_skill` tool. This is the right architecture for any large knowledge base attached to an agent: cheap metadata always present, expensive content only when needed.

9. **Three-tier rule hierarchy with by-value/server-held split.** Local file-based rules ship in the request body (inspectable, reproducible). Cloud/user-level memory is flag-gated and server-held (privacy, cross-device). Verso should enforce this split: `VERSO.md` / `AGENTS.md` by value, cloud memory as flag.

10. **Dual-cursor event bus for multi-agent.** For any parent-child agent coordination, persist the event cursor in two places (local + server) and take `max()` on restore. This is the correctness invariant for at-least-once delivery without duplicates across restarts.

11. **MCP as the multi-agent protocol.** Devin's "multi-agent as MCP" (child agents spawned via JSON-RPC tools, monitored via MCP) is the cleanest multi-agent pattern across all teardowns. Protocol = interface. Verso should expose child-agent spawn/monitor as first-class MCP tools rather than in-process Python APIs.

12. **Tool advertisement is a capability bitmap, not a hardcoded prompt.** Warp's `Settings.supported_tools` bitmap (assembled per-request from feature flags + session state) that the server uses to template the system prompt is the correct architecture. Verso's prompt should be assembled from what tools are actually registered and live in this session, not hardcoded. Feature-flagged tools simply aren't advertised.

13. **LRC (long-running command) tool-set swap.** When a blocking operation is in flight, swap to a restricted tool set (read/search + shell-IO only). Same context window, different capability. This prevents the agent from starting a second shell command while one is running — a common failure mode in coding agents. Implement as a context-aware `get_supported_tools()` that checks in-flight state.

14. **Evaluate on real benchmarks before claiming architecture wins.** Warp's decision to abandon multi-agent fan-out was empirical (SWE-bench data, Terminal-Bench data). Verso should instrument the agent loop with enough telemetry to run similar ablations: measure single-agent vs. fan-out on the actual use case before committing to the architecture.
