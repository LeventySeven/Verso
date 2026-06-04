# Teardown Cluster: Gemini Spark + Antigravity
**Cluster key:** `coding-gemini-antigravity`
**Sources:** `teardowns/ANTIGRAVITY.md` (Tier-1A, 2090 L, two verbatim leaked system prompts + AppImage binary RE), `teardowns/GEMINI_SPARK.md` (Tier-1A, 3800+ L, Spark is a strict runtime subset of Antigravity with feature-flag gating)
**Evidence tier:** Both are Tier-1A. The Antigravity binary (`language_server_linux_x64`, 134 MB stripped Go binary, SHA-256 `4b23f0a2949f032c47365a3f9a8c4aaf62daf46995c49071a488b6c35fde0354`) is byte-identical between Antigravity-desktop and the harness Spark loads server-side. All binary claims use `strings-min100.txt`, `tool-arg-descriptions.txt`, `cortex-steps.txt`, `rpc-clean.txt` as cite format.

---

## System 1 — Antigravity (Google DeepMind coding agent harness)

Antigravity is Google's internal coding-agent platform, built on the `gemini_coder` / `jetski/cortex` framework stack (originally acquired as Codeium). It is NOT a multi-agent debate system; it is a **single-orchestrator + on-demand-subagent** architecture — the same topology as Claude Code's Task tool.

### Agent Loop Shape

Three-mode state machine enforced via a dedicated tool (`task_boundary`). Modes are `PLANNING → EXECUTION → VERIFICATION` with explicit rules on which transitions are permitted:

```
null        → PLANNING   (always start here on a new user request)
PLANNING    → PLANNING   (user requests plan changes — update implementation_plan.md in place)
PLANNING    → EXECUTION  (ONLY after user explicitly approves implementation_plan.md)
EXECUTION   → PLANNING   (unexpected complexity discovered mid-task)
EXECUTION   → VERIFICATION (implementation done)
VERIFICATION → EXECUTION (minor bugs, same TaskName)
VERIFICATION → PLANNING  (fundamental design flaw — new TaskName)
```

Source: `planning-mode.txt:21-23`, verbatim.

**Two meta-level modes** (the mode-selector layer above the three-mode FSM):
1. **Agentic task mode** — complex work; use `task_boundary` + `notify_user`; produce artifacts.
2. **Simple chat mode** — quick questions, single-file edits; bypass the full plan/execute/verify workflow.

Criterion for skipping task mode (verbatim from `planning-mode.txt:16`): "For simple work (answering questions, quick refactors, single-file edits that don't affect many lines etc.), skip task boundaries and artifacts."

**Termination condition:** main agent issues a final `notify_user` WITHOUT `BlockedOnUser: true`. There is NO explicit iteration cap visible in the binary; the runtime has soft and strict reminder thresholds (`no_active_task_soft_reminder_tool_threshold` ~8 turns, `no_active_task_strict_reminder_tool_threshold` ~16 turns) that inject warnings, not hard stops.

**Loop implementation** is the `gemini_coder` 8-component framework:

| Component | Role |
|---|---|
| `framework/agent` | Core abstract Agent type — the loop primitive |
| `framework/executor` + `agentexecutor` | Drives the loop, dispatches tool calls, handles streaming |
| `framework/generator` | LLM-call wrapper — request formatting, streaming response, retries |
| `framework/handlers/{applyedit, checkpoint, handlers}` | Per-step handlers |
| `framework/registry` | Tool/handler/converter registry (dependency injection) |
| `framework/stepmanager` | Per-CortexStep state machine |
| `framework/stringconverters` | markdown ↔ HTML ↔ trajectory-step format |
| `framework/task` | Top-level task lifecycle |
| `framework/toolconverters` | Schema-format converters: Gemini ↔ OpenAI ↔ MCP ↔ Antigravity-internal |

The `cortex/executors/{posthooks, prehooks, stophooks}` packages implement the **5-stage hooks ABI**:

| Hook stage | When it fires |
|---|---|
| `pre_invocation_hooks` | Before each LLM invocation |
| `post_invocation_hooks` | After each LLM invocation completes |
| `pre_tool_hooks` | Before each tool call dispatches |
| `post_tool_hooks` | After each tool call returns |
| `stop_hooks` | When the agent decides to stop / finish |

Hooks are **declarative JSON configs** (`cortex/customization/hooks/jsonhook` package), not Go callbacks — user can ship them via `~/.gemini/antigravity/hooks.json`. The `stop_hooks` trigger the KI-distillation background job.

### Models

3-tier model selector per subagent (`InvokeSubagentToolConfig.Model` enum, verbatim from `tool-arg-descriptions.txt`):

| Tier | Value | INFERRED mapping | Use case |
|---|---|---|---|
| `inherit` | default | Parent's model (Gemini 3 Pro typically) | Continuity |
| `fast` | explicit | Gemini 3 Flash | Simple lookups, file reads, binary classifiers, KI extraction |
| `heavy` | explicit | Gemini 3 Ultra (thinking-enabled) | Deep refactors, multi-step planning, complex reasoning |

Spark surface: primary model `gemini-3.5-flash`; escalation model `gemini-3.5-pro`; image `gemini-3-flash-image` (Nano Banana 2); video Veo; music Lyria 3.

**11 distinct LLM call-site prompts** in the binary (not one monolithic system prompt):

1. Main Antigravity identity (`strings-min100.txt:49039`) — "You are Antigravity, a powerful agentic AI coding assistant…"
2. Subagent caller (`strings-min100.txt:49023`) — "You are running as a subagent, invoked by a caller agent (name: %[1]q, id: %[2]q). You MUST use send_message…"
3. Code-editor / FastApply (`strings-min100.txt:49017`) — "You are a helpful assistant whose purpose is to help a user edit a code document…"
4. NEXT_STEPS extractor (`strings-min100.txt:49072`) — "Your goal is to articulate the OVERALL_GOAL of the USER, and any potential NEXT_STEP…"
5. Background-KI-extractor (`strings-min100.txt:49091`) — "You are operating as a background agent that runs automatically after conversations to extract and preserve knowledge…"
6. Persistent-memory preamble (`strings-min100.txt:49209`) — injected when memory is available
7. Planning-mode preamble (`strings-min100.txt:49271`) — "You are in Planning Mode. Exercise judgement on whether a user's request warrants a plan…"
8. Generic XML tool-calling boilerplate (`strings-min100.txt:49364`) — used inside subagents without the full Antigravity prompt
9. Cider/Critique agent (Google-internal path only)
10. Stdin-classifier (`strings-min100.txt:49136`) — yes/no binary classifier: "You are a classifier that determines if a terminal command is actively waiting for the user to type something into stdin…"
11. Search-engine bot (`strings-min100.txt:48953`) — "You are a search engine bot. You will be given a query from a user… You MUST perform a web search."

Plus a commit-message generator (`strings-min100.txt:49047`).

The **FastApply architecture** (Prompt #3) is a separate LLM call dispatched by `replace_file_content`/`multi_replace_file_content` to a smaller "apply" model that takes diff intent + file and emits the patched file. Cursor calls this "FastApply"; Google ships the same pattern in `cortex/fastapply`.

### Full Tool Registry (47 ToolConfigs, verbatim from binary)

Round-1 leaked-prompt inferred 19 tools; binary reveals 47. All 19 confirmed + 28 net new:

**File ops:** `view_file`, `view_code_item`, `list_dir`, `find`, `grep_search`, `codebase_search` (semantic, vector index over code chunks), `cluster_query` (multi-repo), `internal_search` (Google-internal `google3`), `replace_file_content` (single-chunk), `multi_replace_file_content` (multi-chunk).

**Multi-chunk edit metadata** (per chunk):
- `importance`: `high | medium | low` — drives IDE diff prominence
- `lint_ids`: IDs of lint errors this edit fixes (correlates with LSP diagnostic stream)
- `explanation`: user-facing rationale (non-obvious design decisions)
- `StartLine`, `EndLine`, `TargetContent`, `ReplacementContent`

**Shell / command:**
- `run_command` (`SafeToAutoRun: boolean` — see safety rule below)
- `command_status` (check background command status)
- `manage_task` (verbs: `list | kill | status | send_input`)
- `is_command_waiting_for_stdin` (YES/NO classifier subagent for long-running commands)
- `send_command_input` (stdin write XOR Terminate — exactly one required)

**Browser (CDP, not Playwright):**
- `browser_subagent` (spawn focused browser session; parent does NOT see intermediate steps)
- `capture_browser_screenshot`
- `click_browser_pixel` (1000×1000 normalised coords; de-normalised at execution time)
- `execute_browser_javascript`
- `browser_get_network_request`, `browser_list_network_requests`
- All coords: "X coordinate of the pixel to click (0-999). Coordinates are scaled to a 1000x1000 grid and mapped to screen dimensions when executing." (`tool-arg-descriptions.txt`)

**Knowledge base / memory:**
- `knowledge_base_search` (semantic over KIs)
- `read_knowledge_base_item`
- `memory` (read/write `CortexMemory`)
- `indexed_memory` (vector-backed retrieval — separate from KI; two-layer memory system)

**Communication / boundary:**
- `notify_user` (the ONLY user-visible channel during task mode)
  - Args: `Summary`, `Mode (PLANNING|EXECUTION|VERIFICATION)`, `BlockedOnUser: bool`, `PathsToReview: str[]`, `ConfidenceScore` (numeric), `ConfidenceJustification` (free text)
- `ask_question` (multi-choice blocking prompt — consent flow)
- `send_message` (subagent→parent mailbox — the async return protocol)
- `manage_message` (verbs: `list | read`)
- `task_boundary` (start/update task — THE state-machine transition primitive)
- `schedule_task` (5-field cron + one-shot timer, see below)
- `intent` (high-level intent declaration; primes planner before tool dispatch)
- `finish` (terminate task)

**Subagent invocation (`invoke_subagent` full 8-arg ABI):**

| Arg | Purpose |
|---|---|
| `Name` | Display name |
| `TaskDescription` | Clear, actionable task description |
| `Role` | 2-5 word job title (e.g. "Codebase Researcher") |
| `Model` | `inherit` / `fast` / `heavy` |
| `Tools` | Tool allowlist (empty = inherit defaults) |
| `CustomPromptSections` | Array of `{title, content}` pairs injected into subagent's system prompt |
| `WorkspaceMode` | `inherit` (shares parent workspace) / `branch` (CitC clone or git worktree) |
| `ResumeFromSubagentId` | Checkpoint resume — continue from a cancelled subagent |

**Web / external:** `search_web`, `read_url_content`, `generate_image`

**Notebook:** `notebook_edit` (6 verbs: `list | get | add | update | delete | create`; `cell_type`: `code | markdown | raw`)

**Workspace:** `workspace_api` (generic authenticated REST proxy to Google Workspace APIs — `batchUpdate` is the formatting primitive)

**MCP:** `mcp:call` (per-server dispatch); `list_resources`; `read_resource`

**Deployment (Enterprise+dev):** Cloud SQL, Firebase, web-app deploy, dev-server restart, applet compile/lint

**Safety rule on every destructive tool** (verbatim from `tool-arg-descriptions.txt`):
```
"Set to true if you believe that this command is safe to run WITHOUT user
approval. A command is unsafe if it may have some destructive side-effects.
Example unsafe side-effects include: deleting files, mutating state,
installing system dependencies, making external requests, etc. Set to true
only if you are extremely confident it is safe. If you feel the command
could be unsafe, never set this to true, EVEN if the USER asks you to. It
is imperative that you never auto-run a potentially unsafe command."
```

**Per-tool parallelism gate** (`waitForPreviousTools?: boolean` on every tool):
- `false` or omitted = run immediately in parallel with other tools in the same turn
- `true` = wait for all prior tool calls in this turn to complete first

This is per-tool surgical parallelism control — more granular than OpenAI's per-request `parallel_tool_calls`.

### Context Assembly / Prompt Architecture

The system prompt is **not a static string** — it is dynamically assembled from a **topologically-ordered set of mixins**, each implementing a 5-method Go interface:

```go
type Mixin interface {
    GetJudgeCriteria() *JudgeCriteria  // criteria for whether to include this turn
    ShouldInclude(ctx) bool            // gate
    Content() string                   // static full-budget text
    DynamicContent(ctx) string         // budget-conditional compressed variant
    TokenType() TokenBucket            // which budget pool this spends from
    GetName() string                   // logical section name
}
```

Assembly order:
1. Identity prompt (static)
2. All active mixins (gated by `ShouldInclude`; falls back to `DynamicContent` when over budget)
3. User-rules mixin with precedence statement (user rules outrank everything that follows)
4. Per-turn dynamic context (open files, cursor position, recent diffs)

User-rules precedence statement (verbatim, `strings-min100.txt:48890`):
```
The following are user-defined rules that you MUST ALWAYS FOLLOW WITHOUT ANY
EXCEPTION. These rules take precedence over any following instructions.
```

Source files for user rules: `AGENTS.md` and `GEMINI.md` at workspace root; `Manager.readGlobalRules` also reads a global-rules path outside the workspace. Conditional memories carry trigger predicates (only render when predicate fires); unconditional memories always render.

**Critical instructions prepended to every thought block** (`strings-min100.txt:49074`):
- NEVER use `cat`/`grep`/`ls`/`sed` as shell commands when specialised tools exist
- Before making tool calls, explicitly list related tools; only execute if all others are more generic
- The format MUST start: `'...94>thought\nCRITICAL INSTRUCTION 1: ...\nCRITICAL INSTRUCTION 2: ...'`

### Memory

Two-layer memory system (both confirmed by binary):

**Layer 1 — Knowledge Items (KI):**
- Per-KI: `metadata.json` + `artifacts/` directory at `$HOME/.gemini/antigravity/knowledge/<ki-id>/`
- KI shape: `{title, summary, references: [{type ∈ {file, conversation_id, url}, value}]}`
- Produced by a **separate KNOWLEDGE SUBAGENT** (Prompt #5) that runs after conversations on `stop_hooks`
- KNOWLEDGE SUBAGENT has restricted toolset: read-everywhere, write-only-in-allowlist
- Injected as summaries at conversation start; "MANDATORY FIRST STEP: Check KI Summaries Before Any Research"

**Layer 2 — CortexMemory:**
- `MemoryToolConfig` (read/write `CortexMemory`) — per-session/per-conversation structured key-value
- `IndexedMemoryToolConfig` — vector-backed retrieval over the CortexMemory store

**Conversation logs:**
```
$HOME/.gemini/antigravity/brain/<conversation-uuid>/
├── .system_generated/logs/
│   ├── overview.txt           # auto-generated TL;DR
│   └── <task-files>.txt       # per-task turn-by-turn logs
├── task.md
├── implementation_plan.md
└── walkthrough.md
```

### System Prompt Fragments (verbatim)

Main identity (`strings-min100.txt:49039`):
```
You are Antigravity, a powerful agentic AI coding assistant designed by the
Google Deepmind team working on Advanced Agentic Coding.
You are pair programming with a USER to solve their coding task. The task
may require creating a new codebase, modifying or debugging an existing
codebase, or simply answering a question.
The USER will send you requests, which you must always prioritize
addressing. Along with each USER request, we will attach additional
metadata about their current state, such as what files they have open and
where their cursor is.
You are in NON-INTERACTIVE mode. The user will not respond to questions or
requests for approval. Work autonomously.
```
(NON-INTERACTIVE paragraph injected only when running headless via `agentapi run`)

Subagent return-value protocol (`strings-min100.txt:49023`):
```
You are running as a subagent, invoked by a caller agent (name: %[1]q, id: %[2]q).
You MUST use send_message to communicate all results, reports, and updates back
to the caller. Your response is NOT automatically relayed. If you do not call
send_message, the caller will only know that you have gone idle. Always use the
caller's id as the Recipient and %[1]q as the RecipientName.
Text you generate outside of send_message will NOT be seen by the caller, so
keep them brief. Put all important information into your send_message calls
instead. You can also share files by including their absolute paths in your
message; the caller can then read them directly.
```

Planning-mode preamble (`strings-min100.txt:49271`):
```
You are in Planning Mode. Exercise judgement on whether a user's request
warrants a plan before taking action.
```

Proactiveness rule (`Fast Prompt.txt:302-307`):
```
As an agent, you are allowed to be proactive, but only in the course of
completing the user's task. For example, if the user asks you to add a new
component, you can edit the code, verify build and test statuses, and take
any other obvious follow‑up actions, such as performing additional research.
However, avoid surprising the user. For example, if the user asks HOW to
approach something, you should answer their question and instead of jumping
into editing a file.
```

### Three Durable Artifacts

Every task produces three structured markdown files in the brain dir:

**`task.md`** — mutable checklist with three-state checkboxes: `[ ]` (pending), `[/]` (in-progress), `[x]` (done). Updated throughout execution.

**`implementation_plan.md`** — created in PLANNING, requires user approval before EXECUTION can start. Format:
- Goal description + background context
- User-review-required items (using GitHub-style `[!IMPORTANT]` / `[!WARNING]` alerts)
- Grouped changes (component-by-component, dependencies-first) with `file:///` clickable links
- Verification plan: automated tests + manual verification

**`walkthrough.md`** — created in VERIFICATION. Proof-of-work artifact with embedded screenshots/videos. Uses `render_diffs(file:///...)` shorthand that the IDE renders as inline diff blocks. The "Trajectories" product feature.

### Schedule Tool (verbatim from `strings-min30.txt:121882`)

```
Schedule a one-shot timer or a recurring cron job that sends notifications
in the background.

NOTE: This tool call returns immediately and does not pause execution.
To wait for the timer to fire, you must stop calling tools to end your turn.

1. One-shot timer: ...DurationSeconds=60, Prompt="Check if the build has completed"
2. Recurring cron: Set CronExpression to a standard 5-field cron expression
   (e.g., '*/5 * * * *' for every 5 minutes)...
   CronExpression="0 * * * *", MaxIterations=3, Prompt="Run the health check script"

You must specify exactly one of DurationSeconds or CronExpression.
Never run a background 'sleep' command to set a timer, use this tool instead.
```

Cron format: `minute hour day-of-month month day-of-week` (5-field, no seconds). Timer returns `task_id` for cancellation via `manage_task(action='kill')`. Tool does NOT block — model must end its turn for the timer to drive a wake-up.

### Multi-Agent Topology

```
Main Agent (Gemini 3 Pro / 3.5 Flash)
├── browser_subagent (separate Gemini instance, Playwright/CDP, WebP recording)
│   └── returns DOM snapshot / screenshot to parent
├── KNOWLEDGE SUBAGENT (background batch, runs on stop_hook)
│   └── reads conversation logs → distills into KI files
└── on-demand subagents (via invoke_subagent / define_subagent)
    ├── Model: inherit | fast | heavy
    ├── WorkspaceMode: inherit | branch (git worktree)
    └── ResumeFromSubagentId: checkpoint resume
```

Subagent→parent communication is **async mailbox** (NOT synchronous return):
- Subagent must call `send_message(Recipient=caller_id)` to return results
- Parent does NOT poll; system reactively wakes it when message arrives
- Anti-poll rule (verbatim): "After launching a subagent, you do NOT need to poll or check your inbox in a loop. The system will automatically notify you when the subagent sends a message."

### Streaming Protocol

IDE ↔ harness: **gRPC localhost socket** over `exa.language_server_pb.LanguageServerService` (472 unique gRPC method paths in binary). `StreamCascadePanelReactiveUpdates` is the server-streaming method for the chat UI's live update channel. The shell is a thin VS Code fork client; harness owns all agent state.

Trajectory step events streamed to the frontend:
```json
{"step_index": int, "source": "USER_EXPLICIT|MODEL|SYSTEM",
 "type": "USER_INPUT|PLANNER_RESPONSE|VIEW_FILE|...",
 "status": "DONE|ERROR", "content": str, "tool_calls": [...]}
```

258 distinct `CortexStep*` types in the trajectory data model (not ~30 as the leaked prompt suggested).

### MCP Config Schema (verbatim from `extensions/antigravity/schemas/mcp_config.schema.json`)

```json
{
  "mcpServers": {
    "<server_name>": {
      "command": "string",        // local stdio mode
      "args": ["string"],
      "env": {"<key>": "string"},
      "serverUrl": "string",      // remote HTTP mode (Spark uses only this)
      "disabled": "boolean",
      "disabledTools": ["string"],
      "cwd": "string",
      "headers": {"<key>": "string"},
      "authProviderType": "google_credentials",
      "oauth": {"clientId": "string", "clientSecret": "string"},
      "tools": {"<tool_name>": {"background": "off|always"}}
    }
  }
}
```

`background: "always"` — tools can run without blocking the agent turn. This is the mechanism behind Spark's "keeps working in the background even when you close your laptop" claim. MCP spec version: **2022-draft** (binary built before 2025-06-18 stable).

### DLP Architecture (4-checkpoint, verbatim from binary)

`RedactionOptions` proto (11 fields): `omit_entirely`, `max_string_length`, `max_repeated_values`, `match_regex`, `min/max_integer_value`, `audit_instructions`, `timestamp_precision`, `min/max_double_value`, `field_reference`.

Four enforcement checkpoints (none is the LLM itself):
1. Pre-LLM input filter — strips PII from user message before it hits the model
2. Per-tool argument validator — scans model's function call args before execution
3. Post-tool-result filter — classifies tool responses before injecting into model context (attacker-controlled surface when using third-party MCPs)
4. MCP-credential vault — OAuth tokens NEVER on the model's path; loaded at tool-invocation time from KMS-backed store

`thinking_redacted` boolean gates whether chain-of-thought is stripped from trajectory logs. `debug_redact` proto-option annotates every field for PII-status at log emission.

### Exact Constants

| Constant | Value | Source |
|---|---|---|
| Three-mode state machine modes | PLANNING, EXECUTION, VERIFICATION | `planning-mode.txt:21` |
| Brain dir | `$HOME/.gemini/antigravity/brain/<convo-id>/` | `planning-mode.txt:28` |
| KI dir | `$HOME/.gemini/antigravity/knowledge/<ki-id>/` | `Fast Prompt.txt:204` |
| Soft no-active-task reminder threshold | ~8 turns (INFERRED) | `cortex_go_proto.TaskBoundaryToolConfig` field 3 |
| Strict no-active-task reminder threshold | ~16 turns (INFERRED) | field 4 |
| max_subagent_snapshots | server-pushed (field 18) | `strings-min30.txt:191601` |
| runningTaskLimit per user | ~10 INFERRED | server-side opaque |
| Browser coordinate grid | 1000×1000 | `tool-arg-descriptions.txt` |
| Cron format | 5-field (minute hour dom month dow) | `strings-min30.txt:121882` |
| find_by_name result cap | 50 matches | tool schema description |
| Task checkbox states | `[ ]` / `[/]` / `[x]` | `planning-mode.txt` |
| notify_user confidence fields | `ConfidenceScore` (numeric), `ConfidenceJustification` (free text), `BlockedOnUser` (bool) | `notify_user` spec |
| Default agentic temperature | 0.1 (INFERRED) | Dev.to article + industry standard |
| Max output tokens per turn | 8192 (INFERRED) | Vertex default for Flash class |
| Antigravity desktop version | 1.23.2 (lang-server) / 2.0.1 (shell) | binary mtime + auto-updater |
| Model-selection enum | `inherit` / `fast` / `heavy` | `InvokeSubagentToolConfig.Model` |
| Workspace-branch enum | `inherit` / `branch` | `InvokeSubagentToolConfig.WorkspaceMode` |
| MCP spec version | 2022-draft | `cortex/utils/mcp/schema_meta_2022` package name |

### Workflows / User-Defined Patterns

`.agent/workflows/<name>.md` in the repo root. Activated by `/slash-command` typing or agent inference. Two turbo annotations:
- `// turbo` (above one step): auto-execute just that step's `run_command` with `SafeToAutoRun=true`
- `// turbo-all` (anywhere in the file): auto-execute ALL `run_command` steps in the workflow

Edit tool `Complexity` parameter: 1-10 rating of "how important it is for the user to review this change". Drives IDE diff-review UX — high-complexity edits get prominent diff cards; low-complexity edits are auto-accepted.

---

## System 2 — Gemini Spark (consumer personal-agent)

Spark is Antigravity with the IDE-specific tools feature-flagged off, the Workspace tools feature-flagged on, and a consumer-facing identity. The binary is **byte-identical** (`language_server_linux_x64`, same SHA-256). No Spark-specific code exists.

### What Spark Drops vs Antigravity Desktop

Disabled for Spark (IDE-only or internal-only):
- File ops: `find`, `grep_search`, `list_dir`, `view_file`, `view_code_item`, `replace_file_content`, `multi_replace_file_content`, `codebase_search`, `cluster_query`
- Browser introspection: `browser_get_network_request`, `browser_list_network_requests`
- Google-internal: `mquery`, `rel`, `internal_search`, `inspect_cluster`
- IDE-only code: `compile`, `compile_tool`, `apply_edit_via_propose_code`

Both have (Spark inherits unchanged):
- All communication / boundary tools (`notify_user`, `ask_question`, `send_message`, `manage_message`, `task_boundary`, `schedule_task`, `intent`, `finish`)
- All browser tools that operate on the agent-controlled browser
- All web/search/external tools, all MCP tools, all memory/KI tools
- `workspace_api`, notebook editing, `manage_task`, `command_status`, `run_command` (sandboxed-only)

### Novel Primitive

The **persistent personal-agent VM** — a long-lived Cloud Run sandbox per paying Ultra user with their encrypted workspace credentials, a schedule/trigger system, a tool registry of MCP servers, and the Antigravity harness running on top. The product is the VM, not the chat UI.

- Every task = fresh ephemeral Cloud Run instance spun off the user's persistent sandbox
- "Data never overlaps between sessions" (Google Cloud blog, verbatim)
- Agent Gateway (stateless proxy) owns ALL OAuth tokens; the LLM never sees credentials
- DLP policies applied at the gateway to all traffic in and out

### Workspace Integration

`workspace_api` is a **single generic authenticated REST proxy** (not 4 separate tools):
- Args: `Full API URL`, `HTTP method`, `Request body JSON`, `Human-readable description`
- `batchUpdate` is the formatting primitive for Docs/Sheets/Slides
- Read-only enforcement mode exists (`workspace_api tool is in read-only mode, only GET requests are allowed, got %s`)
- The harness explicitly prefers API calls over URL shortcuts (`docs.new`, `sheets.new`)

Internal tool name: `gemkick_corpus` (the agent is explicitly told not to reveal this name to users). Actual Google Workspace APIs used: `gmail.readonly`, `gmail.modify`, `gmail.send`, `drive.readonly`, `drive.file`, `calendar.events`, `chat.messages`, `meet.readonly`.

### MCP Partner Architecture

At Spark launch: Canva, OpenTable, Instacart. The `mcp_config.json` `background: "always"` tool flag enables non-blocking execution. Third-party MCP servers hold the user's OAuth/API-key; Spark talks to the MCP server, never to the third party directly.

### Model Routing (Spark)

| Task type | Model |
|---|---|
| Short conversational reply | Gemini 3.5 Flash |
| Tool-using turn (common case) | Gemini 3.5 Flash |
| Long-horizon reasoning | Gemini 3.5 Flash (thinking-budget param raised) |
| Difficult reasoning escalation | Gemini 3.5 Pro (INFERRED) |
| Image generation | Gemini 3 Flash Image (Nano Banana 2) |
| Video generation | Veo |
| Music generation | Lyria 3 |
| Browser session | browser_subagent (Gemini 3.5 Flash) |

Benchmarks: Terminal-Bench 2.1 = 76.2%, GDPval-AA = 1656 Elo, MCP Atlas = 83.6% (+9.7pp vs 3.1 Pro).

### Streaming (Spark)

- Chat responses: HTTPS POST to `geminiweb-pa.clients6.google.com`; SSE-style chunked response
- Voice/camera: WSS to Gemini Live cluster
- Long-running task progress: push notifications via FCM/APNs/web-push — each `notify_user` call becomes one push notification
- Android APK (`com.google.android.apps.bard`) has ZERO networking permissions — all Spark capabilities delivered through AGSA (`com.google.android.googlequicksearchbox`); the Gemini APK is a forwarding stub

### Single-Orchestrator Design Rationale

Google deliberately chose single-orchestrator + on-demand subagents (not fixed-role CrewAI-style multi-agent) because:
1. Personalisation MASTER RULE needs a single enforcement chokepoint
2. DLP gateway is simpler with one orchestrator
3. `notify_user` is the single user-facing channel — multi-agent debate would need filtering anyway
4. User-perceived latency proportional to critical path — single fast orchestrator + parallel on-demand subagents minimises it

---

## Key Findings

- **The agent loop has explicit state machine enforcement** — a dedicated `task_boundary` tool enforces mode transitions. The model CANNOT edit code while in PLANNING mode; the constraint is architectural, not advisory.
- **11 distinct LLM call-sites, not one monolithic prompt** — FastApply, KI-extractor, stdin-classifier, search-engine bot, NEXT_STEPS predictor, subagent identity, and 4 mode-specific preambles are separate model invocations with separate smaller/faster models.
- **Per-tool parallelism control via `waitForPreviousTools` boolean** — more granular than OpenAI's per-request `parallel_tool_calls`.
- **Two-layer memory system** — `CortexMemory` (read/write key-value, per-session) + `IndexedMemory` (vector-backed retrieval) + `KnowledgeItems` (cross-session KI files distilled by a background KNOWLEDGE SUBAGENT).
- **Mixin-based prompt assembly with budget-conditional fallback** — the system prompt is not a static string; it is a topologically-ordered set of mixins, each with a `DynamicContent` compressed variant for budget overflows.
- **5-stage hooks ABI** — `pre_invocation / post_invocation / pre_tool / post_tool / stop` — user-extensible via declarative JSON config, not code callbacks.
- **3-tier subagent model routing** (`inherit / fast / heavy`) with workspace branching (`inherit / branch` for git worktrees) and checkpoint resume (`ResumeFromSubagentId`).
- **47 ToolConfigs** in the binary (not 19 from the leaked prompt), including schedule/cron, multi-chunk edits with lint attribution, notebook editing, deployment (Firebase+Cloud SQL), enterprise tools.
- **Async mailbox subagent protocol** — subagents return via `send_message`, not synchronous return; parent is reactively woken up (no polling).
- **DLP at 4 checkpoints** (pre-LLM input, per-tool arg, post-tool result, MCP-credential vault) — none of the checkpoints is inside the LLM.
- **Spark = strict feature-flag subset of Antigravity-desktop** — no Spark-specific code exists in the binary.

---

## → Verso Implications

1. **COPY the three-mode state machine as a first-class primitive.** Antigravity's PLANNING → EXECUTION → VERIFICATION FSM enforced via a dedicated state-transition tool is the single most impactful agent-reliability pattern in this teardown. Verso should offer this as a built-in mode system, not just a ReAct loop. The mode-transition tool should be the ONLY way to change mode — making mode transitions explicit and auditable in the trajectory. The "skip task mode for simple work" meta-selector is equally important for avoiding overhead on trivial tasks.

2. **COPY per-tool parallelism gating (`waitForPreviousTools`).** OpenAI's binary `parallel_tool_calls` is too coarse. Antigravity's per-tool `waitForPreviousTools: boolean` lets the agent emit a set of tool calls with explicit dependency edges. Verso should implement this: tool calls in one turn form a DAG; tools without the flag run in parallel by default; tools with the flag wait for all prior calls in the turn. This is directly copyable with no proprietary dependency.

3. **COPY the async-mailbox subagent protocol.** When Verso spawns a subagent, do NOT make it synchronous (block parent until subagent returns). Use the `send_message` → reactive-wakeup pattern: subagent pushes results into parent's inbox; parent is event-driven. This scales to parallel subagents without polling loops. Pair with one-shot timer (`schedule_task` with `DurationSeconds`) as a liveness guarantee: "if no message in 60s, wake me up to check."

4. **COPY the mixin-based prompt assembler with budget-conditional fallback.** Do not build Verso with a static system prompt template. Implement the 5-method Mixin interface: `ShouldInclude(ctx)`, `Content()`, `DynamicContent(budget_constrained=true)`, `TokenType()`, `GetName()`. Topologically order mixins; fall back to DynamicContent when over-budget. This is what makes the harness gracefully degrade under context pressure instead of hard-failing.

5. **COPY the 5-stage hooks ABI (`pre_invocation / post_invocation / pre_tool / post_tool / stop`) with declarative JSON config.** This is the right extensibility model: users ship hooks as JSON config files, not code callbacks. Verso's hook system should implement all 5 stages. The `stop_hook` stage is where KI distillation, evals, and post-task logging belong. The `pre_tool` stage is where DLP/safety checks belong. The `post_tool` stage is where prompt-injection detection on tool results belongs.

6. **COPY the three durable artifacts pattern (task + plan + walkthrough).** Every non-trivial Verso task should produce `task.md` (mutable three-state checklist `[ ] / [/] / [x]`), `implementation_plan.md` (user-approved before execution), and `walkthrough.md` (proof-of-work after verification). These artifacts are the agent's output contract — not chat messages. Make them first-class objects in Verso's trajectory store.

7. **COPY the KNOWLEDGE SUBAGENT pattern for cross-session memory.** A background LLM job that fires on `stop_hook`, reads completed conversation logs, and distills them into structured KI files is the correct architecture for persistent agent memory. Key constraints Verso should inherit: restricted toolset (read-everywhere, write-only-in-allowed-paths), triggered on conversation completion rather than inline, completely separate from the main agent's context.

8. **COPY per-edit `Complexity: 1-10` for user-review prioritization.** The agent rates its own edits; the UI renders accordingly — low-complexity edits auto-accepted, high-complexity edits require explicit user review. This is a unique Antigravity feature that no other deployed agent has. Verso's tool schemas for any write/edit/execute action should include an agent-rated importance/complexity field. This is the mechanism that prevents "I asked it a question and it rewrote my whole codebase" — the user spends review time proportional to the risk of each change.

9. **COPY the 3-tier model routing (`inherit / fast / heavy`) per subagent.** Verso should NOT dispatch all subagents on the same model. The `inherit` default is conservative and correct. `fast` for binary classifiers, quick lookups, stdin detection. `heavy` for deep planning passes. This reduces cost without sacrificing quality on reasoning-heavy tasks.

10. **COPY the `WorkspaceMode: branch` pattern for speculative subagents.** When a subagent might make edits that could conflict with the parent workspace, give it a git worktree (`WorkspaceMode: branch`). This is Git-native isolation: branch per subagent, merge when done. No custom filesystem virtualization needed.

11. **COPY the `ResumeFromSubagentId` checkpoint mechanism.** Subagents can be cancelled and resumed. Verso should expose this as a first-class concept: every subagent invocation returns an ID; a future invocation can pass that ID to inherit the prior subagent's context. This is the correct design for long-running agents that may be interrupted.

12. **COPY the schedule-task tool as a first-class primitive.** `schedule_task` is one of the most directly-copyable subsystems from the teardown. Two modes: one-shot timer (`DurationSeconds`) and recurring cron (`CronExpression`, 5-field). The timer is auto-cancelled if any message arrives first. Implementable in <200 LOC with any cron library. This is what makes agents "work while you sleep" — not a separate scheduling service, but a tool the agent itself can invoke.

13. **COPY the `SafeToAutoRun` safety classifier pattern on destructive tools.** Every shell-execute / browser-execute / send-email tool should have an agent-facing `SafeToAutoRun: boolean` parameter with this exact schema description: "never set this to true, EVEN if the USER asks you to. It is imperative that you never auto-run a potentially unsafe command." This overrides user instruction at the tool-schema level — the model's own judgment is the gate, not the user's stated intent.

14. **COPY the MCP gateway architecture** (`mcp_config.json` + `background: off|always` per tool + `disabledTools` kill-switch). The gateway pattern is the right design: credential vault separate from the model's context, per-tool enable/disable, per-tool background mode. Verso's MCP integration should be a stateless proxy, not inline in the agent loop.

15. **AVOID building a static system prompt.** Antigravity's mixin assembler with `ShouldInclude` gating and `DynamicContent` budget fallback is the correct architecture. Static prompts fail under context pressure and require code changes to adapt to new deployments. Verso should resist the temptation to build a flat string template.

16. **AVOID fixed-role multi-agent topology for the core loop.** Antigravity's design is definitively single-orchestrator + on-demand subagents. The reasons are sound: DLP enforcement, user-facing notification channel, latency minimization. Verso should offer the on-demand subagent pattern (via `invoke_subagent` equivalent) as the default; fixed-role graphs should be an opt-in escape hatch.

17. **AVOID polling loops while waiting for subagents.** The reactive-wakeup mailbox (with a timeout schedule_task as liveness guarantee) is the correct architecture. Verso should expose an event queue for subagent results, not a polling API.

18. **VERSO COULD IMPROVE** on Antigravity's DLP placement by making the 4-checkpoint architecture explicit in the framework's middleware stack, so framework users can plug in their own redaction functions at each stage. Antigravity's DLP is Google-proprietary (`RedactionOptions` proto); Verso could provide a pluggable per-checkpoint interface that accepts regex patterns, named-entity functions, and custom classifiers.

19. **VERSO COULD IMPROVE** on the `Complexity` rating by making it bidirectional: the agent rates the complexity outbound; the user's actual review behavior (time spent, edits made to the diff) feeds back into a calibration loop that adjusts the agent's future complexity ratings. Antigravity has the rating but not the feedback loop.

20. **VERSO COULD IMPROVE** on the mixin assembler by making the token-budget accounting explicit and user-observable — expose a per-turn "prompt budget breakdown" showing which mixins consumed how many tokens and which fell back to `DynamicContent`. This makes context pressure visible and debuggable.
