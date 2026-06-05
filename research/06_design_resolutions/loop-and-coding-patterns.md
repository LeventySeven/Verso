# Core Loop + Coding-Agent Patterns — Verso Design Resolution

**Subsystem:** `core/loop.py` · `context/compaction.py` · `safety/inspector.py` · `tools/format.py`
**PRD sections:** §5.1 (core loop), §5.2 (context engineering), §5.3 (tools)
**Teardown source:** `coding-oss-agents.md` (opencode, Aider, Cline, Roo Code, Goose, Continue.dev, Qodo, Augment Code)
**Written:** 2026-06-05

---

## Decisions Resolved

### 1. Loop shape: part-queue dispatcher, not flat-while-branches

**Choice:** The Verso loop is a **single-message-at-a-time dispatcher over a priority queue of typed "tasks"** attached to the current turn. Compaction triggers and sub-agent dispatches are modeled as `CompactionTask` / `SubtaskTask` objects enqueued on the run context, not as `if/elif` branches inside the loop body. The main loop pops one task per iteration (LIFO) and re-enters.

**Rationale:** The flat `while True: if overflow: ... elif subtask: ... else: normal_turn` shape mixes concerns into the loop body and makes the branches compete in priority order. The LIFO-queue shape (opencode `tasks.pop()`) makes compaction and sub-task dispatch **composable with** the normal turn instead of **interrupting** it. New task types (e.g. eval-check, human approval) can be enqueued without touching the loop. The loop body stays a pure dispatcher.

**Evidence:** opencode `session/prompt.ts:1278-1295` — `tasks = MessageV2.latest(msgs).tasks`; `task = tasks.pop()` (LIFO); `BRANCH A` if `task.type==="subtask"`, `BRANCH B` if `task.type==="compaction"`, `BRANCH C` overflow check (which enqueues a new `CompactionPart` and continues), `BRANCH D` normal turn. The four branches are an ordered priority, not parallel alternatives.

**Alternatives rejected:**
- Flat `if/elif` in the while body (Cline, Roo Code): works but hardcodes priority; adding a new interrupt type requires auditing every branch.
- Event-bus model (CrewAI): adds indirection with no structural benefit for a single-process agent.

---

### 2. Termination — named `StopReason` enum + synthetic grace message

**Choice:** The loop terminates on eight named `StopReason` values (never text-sniffed strings):

```python
class StopReason(str, Enum):
    END_TURN        = "end_turn"        # model stopped with no tool calls
    MAX_STEPS       = "max_steps"       # step >= max_steps
    TOOL_RULE_STOP  = "tool_rule_stop"  # TerminalToolRule fired
    CANCELLED       = "cancelled"       # external cancel token
    BUDGET_EXHAUSTED = "budget_exhausted"  # token budget exhausted
    STUCK           = "stuck"           # doom-loop guard escalated
    ERROR           = "error"           # unrecoverable error
    COMPACTION_FAILED = "compaction_failed"  # context overflow even after compaction
```

On `MAX_STEPS`, the loop **appends a synthetic assistant message** before the final model call: `{role: "assistant", content: MAX_STEPS_TEXT}` where `MAX_STEPS_TEXT` is a short, fixed string asking the model to wrap up what it has so far. This is a nudge, not a hard kill — the model finishes gracefully.

**Rationale:** Named enum = every stop reason is a measurable, loggable, alertable event. The synthetic-message approach (opencode `session/prompt.ts:1426`, `prompt/max-steps.txt`) prevents the confusing half-finished response that a hard cut produces. The grace message is deterministic and single — it avoids LangChain's `early_stopping_method="generate"` anti-pattern (an opportunistic extra LLM call).

**Constants:**
```python
MAX_STEPS_DEFAULT = 25           # PRD §5.1; visible, not hidden like LangGraph's 10007
MAX_STEPS_TEXT = (
    "I've reached the maximum number of steps. Let me summarize what I've accomplished "
    "so far and what remains, then provide the best answer I can with the work done."
)
```

**Evidence:** opencode `prompt.ts:1240-1266` (EXIT CHECK: `finish not in {tool-calls}` + no live tool calls + `lastUser.id < lastAssistant.id`); `prompt.ts:1426` (synthetic `MAX_STEPS` assistant message injected when `step >= agent.steps`). Letta `_decide_continuation` stop reasons (`fw-crewai-letta`). Claude Code 12 `TerminalReason`s (`coding-claude-code`).

**Alternatives rejected:**
- Text-sniffing ("Final Answer:") as termination signal (MiroFish explicitly warns against this — fragile, `agents-products` §2).
- Hard kill at `max_steps` without a grace call: produces truncated, confusing responses.
- No step cap (Codex/Warp token-budget-only): acceptable for a single-user CLI; too runaway-prone in a framework where users wire arbitrary tools.

---

### 3. Overflow trigger: reactive check on prior turn's billed tokens, fixed reserve

**Choice:** Compaction fires **reactively** — checked on the **previous** assistant message's real billed token count — not on a pre-call estimate. The overflow threshold is:

```python
COMPACTION_BUFFER = 20_000   # tokens reserved for the next output

def usable_tokens(model: ModelProfile) -> int:
    reserved = min(COMPACTION_BUFFER, model.max_output_tokens)
    if model.input_limit:
        return max(0, model.input_limit - reserved)
    return max(0, model.context_window - model.max_output_tokens)

def is_overflow(last_turn_tokens: TokenUsage, model: ModelProfile) -> bool:
    total = (last_turn_tokens.input + last_turn_tokens.output
             + last_turn_tokens.cache_read + last_turn_tokens.cache_write)
    return total >= usable_tokens(model)
```

**Rationale:** Pre-call estimation is error-prone (tokenizers differ, cache read/write are not known until after the call). Using the real billed token count from the last completed turn removes the estimation error. Including cache tokens in the sum is critical — cached tokens still occupy the context window even though they cost less. The fixed `min(20k, model.max_output)` reserve is more predictable than a percentage (opencode uses this; Claude Code uses ~95% which conflates "input safety margin" with "output reserve").

**Constants:**
```python
COMPACTION_BUFFER = 20_000        # opencode overflow.ts:1
OUTPUT_TOKEN_MAX  = 32_000        # opencode transform.ts:18; global cap for any single response
COMPACTION_AUTO_ENABLED = True    # can be overridden per-session
```

**Evidence:** opencode `session/overflow.ts` (verbatim algorithm above, confirmed file:line). Note: opencode `compaction.auto === false` guard exists — Verso exposes the same escape hatch.

**Alternatives rejected:**
- Percentage threshold (Claude Code ~95%): intuitive but conflates input margin with output reserve; the absolute-reserve approach is more accurate as context windows grow.
- Pre-call estimation: too fragile (encoding differences, cache counts unknown before the call).

---

### 4. Compaction algorithm: anchored rolling Markdown summary + verbatim tail + cheap prune pass

**Choice:** Verso's default compaction is a two-pass strategy:

**Pass 1 — cheap, LLM-free `prune()`:** runs in the background after every loop exit (and opportunistically during the loop when tool output grows large). Walks messages newest→oldest, skips the most recent `PRUNE_PROTECT_TURNS=2` user turns, and marks tool output as `[elided]` for any completed tool parts beyond `PRUNE_PROTECT` cumulative tool output tokens. Only fires when total prunable output ≥ `PRUNE_MINIMUM`. Never prunes `skill` / `think` / `plan` tool outputs (those are reasoning artifacts, not transient data).

**Pass 2 — LLM summarization (on overflow or manual):** uses a small auxiliary model (not the primary model — keeps the primary's prompt cache intact). Produces a structured summary with a **fixed 8-section Markdown template**:

```
## Goal
## Constraints & Preferences
## Progress (Done / In Progress / Blocked)
## Key Decisions
## Next Steps
## Critical Context
## Relevant Files
## Failed Approaches
```

Rules baked into the compaction prompt: keep all 8 sections even when empty; terse bullets not prose; preserve exact file paths/commands/error strings/identifiers; never mention that compaction happened.

**Tail preservation:** the most recent `DEFAULT_TAIL_TURNS=2` user turns (or as many as fit in `preserve_recent_budget`) are kept verbatim after the summary:

```python
PRUNE_MINIMUM            = 20_000   # min prunable tool output before bother (tokens)
PRUNE_PROTECT            = 40_000   # keep newest N tokens of tool output untouched
TOOL_OUTPUT_MAX_CHARS    = 2_000    # truncate tool outputs fed to summarizer
DEFAULT_TAIL_TURNS       = 2
MIN_PRESERVE_RECENT_TOKENS = 2_000
MAX_PRESERVE_RECENT_TOKENS = 8_000

def preserve_recent_budget(usable: int) -> int:
    return max(MIN_PRESERVE_RECENT_TOKENS,
               min(MAX_PRESERVE_RECENT_TOKENS, usable // 4))  # 25% of usable, clamped
```

**Rolling update (not re-summarize from scratch):** if a previous summary exists, the compaction prompt switches to "update the summary below, preserve still-true details, remove stale details, merge new facts" with the old summary in `<previous-summary>` tags. A `hidden` index tracks which messages were already summarized; they are excluded from the next summarizer input (never re-summarize a summarized prefix).

**Overflow-mode replay:** if compaction was triggered by overflow (not manual), after generating the summary the algorithm re-injects the last real user message verbatim after the summary, so the model resumes mid-task without losing the pending request.

**Hard failure path:** if the summarizer call itself overflows (context too large even for the compactor), set `StopReason.COMPACTION_FAILED` and terminate — never loop.

**Evidence:** opencode `session/compaction.ts` (all constants verbatim, algorithm line-by-line confirmed). The 8-section template is at `compaction.ts:46-81`. Rolling update at `compaction.ts:127-138`. `hidden` set at `compaction.ts:392-399`. Overflow-mode replay at `compaction.ts:368-384, 480-561`. Hard failure at `compaction.ts:462-471`. `prune()` at `compaction.ts:301-345`.

**Alternatives rejected:**
- Observation-masking as the primary strategy (PRD §5.2 mentions JetBrains NeurIPS 2025 +52% cheaper, +2.6% solve-rate): this is a **complementary** mechanism that applies to `prune()` for routine tool-output masking (keep reasoning, mask data), not a replacement for full summarization when the window overflows. Adopt both: `prune()` as the cheap pass, LLM summary only on overflow.
- Warp-style deterministic truncation (Cline sliding window) as the sole strategy: works but loses too much context on tasks with long tool-output chains. Use as a **fallback** when the LLM summarizer fails.

---

### 5. Cheap truncation fallback (no-LLM path)

**Choice:** Before triggering LLM summarization, attempt a deterministic file-read deduplication pass; if still over budget, apply a sliding-window truncation. Expose as `TruncationFallback` that the compaction layer calls before escalating to an LLM summarizer.

```python
TRUNCATION_THRESHOLD_PCT = 0.90   # fire when billed_tokens / usable >= 0.90
# Half vs. quarter decision:
# if billed_tokens / 2 > usable → remove 3/4 of the middle (model switched to smaller context)
# else → remove 1/2
# Always keep: first user-assistant pair + alternation invariant (drop even numbers of messages)
# Cumulative deleted range persisted to disk; never shrinks across turns
```

**Evidence:** Cline `context/context-management/ContextManager.ts:150-339` — `shouldCompactContextWindow`, `getNextTruncationRange(messages, currentDeletedRange, keep)`, half/quarter adaptive logic at line 249-252, file-read dedup optimization at lines 254-259. The alternation invariant (ensure last removed message is an assistant message) is at lines 320-321 — critical for Anthropic which requires strict user→assistant alternation.

**Alternatives rejected:**
- LLM summarization as the only compaction path: expensive and slow for small overflows; the cheap truncation handles the "model switched from 200k to 64k context" case without a model call.

---

### 6. Doom-loop guard: two-threshold inspector pipeline

**Choice:** Stuck-detection runs as a **`ToolInspector`** — a composable inspector in a pluggable pipeline, not hardcoded in the loop body. Two thresholds:

1. **Soft threshold (3 identical calls):** inject a self-correction message into the next user message: `"[Warning: The last 3 calls to '{tool_name}' had identical arguments. If you're stuck, try a different approach or use a different tool.]"`. Continue the loop.
2. **Hard threshold (5 identical calls):** set `StopReason.STUCK`, emit to HITL queue if in durable mode, terminate in tactical mode.

"Identical" means **canonical JSON equality** (`json.dumps(args, sort_keys=True)`) after **stripping metadata-only params** that legitimately change each turn (configurable `IGNORED_PARAMS` set; default includes `task_progress`, `step_number`, `timestamp`).

```python
LOOP_DETECTION_SOFT_THRESHOLD = 3   # Cline loop-detection.ts
LOOP_DETECTION_HARD_THRESHOLD = 5   # Cline loop-detection.ts
DOOM_LOOP_THRESHOLD_OPENCODE   = 3   # opencode processor.ts:36 (maps to our hard threshold in tactical mode)
IGNORED_PARAMS = frozenset({"task_progress", "step_number", "timestamp", "attempt"})
```

**Inspector pipeline:** The `ToolInspector` protocol returns `InspectionResult(action: Literal["allow","warn","deny"], reason: str, finding_id: str)`. The loop calls `inspect_pipeline.check(tool_name, args)` before executing any tool call. Results from multiple inspectors merge: any `deny` wins; `warn` injects message. The pipeline is ordered and short-circuits on `deny`. Built-in inspectors: `RepetitionInspector` (above), `PermissionInspector` (§5.3 tool policy), `BudgetInspector` (cost guard). Third-party inspectors register via `agent.add_inspector(...)`.

**Evidence:** opencode `session/processor.ts:36,526-549` (3-identical-call doom-loop, `JSON.stringify` equality, `permission.ask` on trip). Cline `task/loop-detection.ts` (two thresholds, `IGNORED_PARAMS`, `toolCallSignature` canonical-JSON, soft=3/hard=5, `consecutiveMistakeCount` on hard). Goose `tool_monitor.rs` (`RepetitionInspector` as a `ToolInspector` trait object in a pluggable pipeline with `Allow/Deny/Ask` + confidence — the architectural pattern).

**Alternatives rejected:**
- Single threshold without a warning: no self-correction opportunity; the model often fixes itself on the soft nudge.
- Doom-loop check hardcoded in the loop's `while` body: couples the detection logic to the loop; can't be composed with other inspectors or tested in isolation.
- Levenshtein fuzzy-match on tool inputs (Aider's disabled dead code path, `editblock_coder.py:183`): over-fires on legitimately similar-but-different calls; exact canonical-JSON + metadata stripping is the right signal.

---

### 7. Plan/Act HITL seam: persisted mode with per-mode {prompt, tools, model}

**Choice:** Verso's `mode` is a **persisted run-level state** (not a per-turn flag), stored in the `RunContext`. Two built-in values: `"plan"` and `"act"`. Toggling mode with a pending user message carries the draft across (`ctx.toggle_mode(new_mode, carry_draft=True)`).

Per-mode config (a `ModeConfig` dataclass):

```python
@dataclass
class ModeConfig:
    slug: str                        # "plan" | "act" | custom slug
    role_definition: str             # prepended to system prompt
    when_to_use: str | None = None   # routing hint for orchestrator
    custom_instructions: str | None = None
    tool_groups: list[str | tuple[str, ToolGroupOptions]] = field(default_factory=list)
    model: str | None = None         # override model for this mode

@dataclass
class ToolGroupOptions:
    file_regex: str | None = None    # Roo Code: restrict edit tools to matching paths
    description: str | None = None
```

The tool subset in `"plan"` mode: `["read", "search", "think"]` — no edit, no exec. In `"act"` mode: `["read", "edit", "exec", "search", "think", "done"]`. The `task_boundary` tool (opt-in) can enforce the mode transition architecturally — model cannot call edit tools in `"plan"` mode even if it tries.

**The HITL seam:** `"plan"` mode = the durable/checkpoint side (reason, propose, no side effects). `"act"` mode = the tactical side. `ctx.hitl.request("Approve this plan?")` is the transition mechanism in durable mode. In tactical mode, `mode="plan"` simply restricts the tool surface with no HITL overhead.

**Evidence:** Cline `controller/state/togglePlanActModeProto.ts` (mode as persisted global state, per-mode system prompt fragment, per-mode tool surface, per-mode model, `chatContent` carry-across). Roo Code `packages/types/src/mode.ts` (full `modeConfigSchema` Zod shape, `groups` as `ToolGroup | [ToolGroup, {fileRegex, description}]` tuples, `DEFAULT_MODES` instantiation). PRD §5.1 `mode` knob; §4.1 tactical↔durable seam.

**Alternatives rejected:**
- Per-turn `mode=` arg (not persisted): creates state-management burden on the caller; the model's tool surface would flicker unpredictably mid-task.
- Separate `PlanningAgent` and `ActingAgent` classes: forces the rewrite that the seam is supposed to eliminate.
- Mode enforced only by prompt instruction: not architectural — model can ignore it; the `task_boundary` tool + filtered tool list makes it structural.

---

### 8. Architect/editor split (code-edit context isolation)

**Choice:** For coding tasks, Verso provides an **opt-in two-pass tool execution pattern** accessible as `@tool(mode="architect")` + `@tool(mode="editor")` or via `agent.run(task, split="architect_editor")`. The planner pass emits prose instructions; the editor pass receives only those instructions in a **fresh context** (empty history, no repo map).

Concrete mechanics:
1. `ArchitectPass`: runs with the full context + repo-map (if available). System prompt: describe the change needed; do NOT produce any edit format — output prose instructions only. Tool set: read-only.
2. `EditorPass`: receives only the architect's output as the user message. History: empty (`[]`). Repo-map budget: `0`. Tool set: edit tools only. Returns a diff/patch/whole-file output.
3. After: collapse the editor's turn back into the architect's transcript as `"[Editor applied changes: <summary>]"`.

**Edit format selection (static per-model table):**

```python
EDIT_FORMAT_TABLE: dict[str, EditFormat] = {
    # strong models → search-replace (lowest token overhead, highest compliance)
    "claude": EditFormat.SEARCH_REPLACE,
    "gpt-4": EditFormat.SEARCH_REPLACE,
    "gemini": EditFormat.SEARCH_REPLACE_FENCED,  # filename inside the fence
    "gpt-4-turbo": EditFormat.UDIFF,             # prevents lazy full-file rewrites
    # weak/small models → whole file (highest compliance, highest tokens)
    "default": EditFormat.WHOLE,
}
```

**Search/Replace parser (tolerant regexes + 4-stage match cascade):**

```python
HEAD_RE    = re.compile(r"^<{5,9} SEARCH>?\s*$", re.MULTILINE)
DIV_RE     = re.compile(r"^={5,9}\s*$",          re.MULTILINE)
UPDATED_RE = re.compile(r"^>{5,9} REPLACE\s*$",  re.MULTILINE)

def apply_edit(whole: str, search: str, replace: str) -> str:
    # Stage 1: exact match
    # Stage 2: whitespace-flexible (dedent search and replace by common leading whitespace)
    # Stage 3: elision via "..." lines (split on ^\s*\.\.\.\n, match/replace each chunk)
    # Stage 4 (disabled, dead code in Aider): Levenshtein fuzzy — do NOT implement
    # On failure: return structured error message back to model:
    #   "SearchReplaceNoExactMatch: SEARCH block did not match. The block must match exactly
    #    including all whitespace. [If REPLACE content is already present: are you sure
    #    this edit is needed?]"
```

The structured error message **is** the self-correction loop — feed it back to the model as a tool result and let it retry.

**Evidence:** Aider `aider/coders/architect_coder.py:11` (fresh editor coder, `cur_messages=[]`, `map_tokens=0`, collapse back). `aider/models.py:131,439-596` (format table). `aider/coders/editblock_coder.py:85-120,157-203` (tolerant regexes, 4-stage cascade, structured error). `aider/repomap.py` (the `map_tokens=0` for the editor is explicit in `architect_coder.py`).

**Alternatives rejected:**
- Universal SEARCH/REPLACE for all models: weak models produce too many no-match failures; whole-file for strong models wastes tokens.
- Levenshtein fuzzy match as Stage 4 (Aider has this as dead code, disabled with a bare `return` at line 183): over-fires on adjacent similar blocks; the structured-error-back-to-model approach is more reliable.

---

### 9. Budget-aware repo-map context (tree-sitter + PageRank + binary search)

**Choice:** Verso's context assembly layer provides an opt-in `RepoMap` object for coding agents. When active, it produces a token-budgeted symbol index of the repo and injects it as a `retrieved` section of the `ContextBundle`.

**Algorithm (Aider's, translated to Python):**

1. **Tag extraction:** tree-sitter extracts `def` (definitions) and `ref` (references) per file. Cache: SQLite `diskcache` at `.verso/tags.cache.v1`, keyed by `(path, mtime)`.
2. **Graph construction:** `networkx.MultiDiGraph`. For each `(referencer_file, defined_name, definer_file)`: add edge `referencer → definer` with weight `use_mul * sqrt(num_refs)` where `use_mul` applies these multipliers in order:
   ```python
   CHAT_FILE_REFERENCER_MUL = 50.0   # edge from a file the user is working on
   MENTIONED_IDENT_MUL      = 10.0   # identifier mentioned in the chat message
   LONG_MULTICASE_MUL       = 10.0   # len >= 8 AND (snake_case OR camelCase OR PascalCase)
   PRIVATE_IDENT_MUL        =  0.1   # starts with "_"
   COMMON_IDENT_MUL         =  0.1   # defined in > 5 files
   SQRT_REFS_DAMPING         = True   # sqrt(num_refs) — damps high-freq refs
   SELF_EDGE_WEIGHT         =  0.1   # lone definitions with no refs
   ```
3. **Personalization:** `base = 100 / len(fnames)`. Chat files `+= base`; mentioned files `= max(current, base)`; files with a path component matching a mentioned ident `+= base`.
4. **PageRank:** `nx.pagerank(G, weight="weight", personalization=..., dangling=...)`. Each node's rank distributed across out-edges proportional to weight → `ranked_definitions[(dst, ident)]`. Sort descending; exclude chat files (model already has full text).
5. **Token-budget binary search to within 15%:**
   ```python
   SEED_TOKENS_PER_TAG = 25   # initial guess
   MAP_BUDGET_DEFAULT  = 1024  # tokens
   MAP_PCT_ERR_TOLERANCE = 0.15
   MAP_MUL_NO_FILES    = 8     # multiply budget by 8 when no files added yet (capped at ctx window)
   MAP_AUTO_RECOMPUTE_THRESHOLD = 1.0  # seconds: recompute only if last pass was slow
   ```
6. **`token_count()` sampling:** for texts > 200 chars, sample every Nth line to estimate cheaply.

**Evidence:** Aider `repomap.py:365-574` (graph construction), `repomap.py:374-445` (personalization), `repomap.py:519-574` (PageRank + distribution), `repomap.py:666-704` (binary search), `repomap.py:35-43,585-624` (cache + refresh policy), `repomap.py:56,124-132` (`map_mul_no_files=8`), `repomap.py:89-101` (token_count sampling). Edge multipliers at `repomap.py:487-514`.

**Alternatives rejected:**
- BM25/grep-based symbol search: no relationship awareness; doesn't prioritize chat-adjacent symbols.
- Fixed-window symbol inclusion: either too small (misses distant but relevant defs) or too large (floods context).
- Always-full repo dump: infeasible for any repo > ~20 files.

---

### 10. MCP-as-extension cost — why Verso demotes it

**Choice confirmed:** MCP remains a **demoted, opt-in adapter** for external servers only. First-party tools are direct Python function calls.

**The cost (empirically confirmed from Goose):** Even Goose's *builtin* extensions (`developer`, `computercontroller`, `memory`) pay the full `rmcp::ServerHandler` + stdio transport tax — schema serialization, stdio framing, lifecycle management — because Goose's `BuiltinExtension` system routes all builtins through the same `ServerHandler` interface as external subprocess extensions (`crates/goose-mcp/builtin_extension.rs` + `mcp_server_runner.rs`). This is the uniformity benefit: one extension model regardless of source. The cost: even a first-party tool that could be a 10-line Python function requires a `ServerHandler` impl, transport setup, and schema round-trip.

For Verso: the benefit (uniformity) is real only when interoperating with the MCP ecosystem. For first-party tools, the zero-overhead Python `@tool` path gives the same capability at zero schema-bloat and zero lifecycle complexity. MCP is the right choice for: (a) connecting to external servers that are already MCP-native, (b) sandboxed tool servers that should run in a separate process, (c) the `openapi` adapter that auto-converts a spec.

**Evidence:** Goose `crates/goose-mcp/builtin_extension.rs` + `mcp_server_runner.rs` — every builtin extension spawns via `rmcp::transport::stdio` just like external extensions. PRD §2 "MCP-first is not Verso's identity"; §5.3 "MCP demoted to optional adapter." Perplexity/Yarats MCP-schema-context-flooding concern (`research-perplexity`).

---

### 11. Headless / CI run contract

**Choice:** Verso exposes a `run_headless(prompt, allow_tools=[...], timeout_s=360, output="text|json")` function (or CLI flag `--print`) that runs print-mode: **one-shot, no interactive approval loop, hard timeout, typed failure fallbacks**.

```python
# Headless contract (Continue.dev + Augment Code pattern)
async def run_headless(
    agent: Agent,
    prompt: str | Path,              # str or @file path
    allow_tools: list[str] = (),     # fixed allow-list; no runtime approval prompts
    timeout_s: int = 360,
    output_format: Literal["text", "json"] = "text",
    max_turns: int = 10,
) -> HeadlessResult:
    ...

@dataclass
class HeadlessResult:
    output: str
    stop_reason: StopReason
    usage: UsageStats
    failure_mode: Literal["ok","empty_output","timeout","auth_error","config_error","generic"] | None
```

Each `failure_mode` maps to a templated fallback message (never a silent empty result). Output is captured, ANSI-stripped, and returned.

**Evidence:** Continue.dev `actions/general-review/action.yml` + `scripts/buildPrompt.js` (headless contract: `--print`, `--allow Bash`, `timeout 360`, typed failure fallbacks, ANSI strip). Augment Code `auggie` CLI (`--print`, `--quiet`, `--output-format json`, `--max-turns`, `--wait-for-indexing`, `--permission launch-process:allow`).

---

### 12. Eval-driven termination as a first-class stop strategy

**Choice:** Alongside `end_turn` and `max_steps`, Verso supports **metric-terminated** agent loops via `agent.run(task, exit_when=Callable[[RunContext], bool])`. The callable receives the run context (including the last tool result) and returns `True` to terminate. A convenience preset:

```python
agent.run(
    "write and run tests for module X",
    exit_when=lambda ctx: ctx.last_tool_result.get("all_passed") is True,
    max_steps=50,    # safety net; eval-driven agents still need a cap
)
```

For the common case of test-coverage loops, a built-in `ExitWhen.tests_pass(test_runner="pytest")` preset emits `StopReason.END_TURN` when the test runner reports zero failures.

**Evidence:** Qodo `onboarding/agents/cover.toml` — `cover` agent loop: ANALYSIS → PLANNING → IMPLEMENTATION → EXECUTION (run→fail→fix→re-run) → REPORT; termination condition verbatim: "Finish once all tests of all the key components are passing and the code is stable." This is a metric-terminated loop, not human-terminated.

**Alternatives rejected:**
- Human-terminated only: insufficient for CI/eval agents that should run unattended.
- Convergence-based termination ("until agents agree"): explicitly rejected by Verso design (PRD §6.2, `_SYNTHESIS.md` Avoid #13 — Grok has no convergence metric; it's `turns ∧ time ∧ tokens` only).

---

## Component Spec

### `core/loop.py` — public interface

```python
@dataclass
class AgentResult:
    output: str | dict | None
    stop_reason: StopReason
    usage: UsageStats        # {input, output, cache_read, cache_write, total}
    cost_usd: float
    trace_id: str
    steps_taken: int

@dataclass
class UsageStats:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int

    @property
    def total(self) -> int:
        return (self.input_tokens + self.output_tokens
                + self.cache_read_tokens + self.cache_write_tokens)

class StopReason(str, Enum):
    END_TURN          = "end_turn"
    MAX_STEPS         = "max_steps"
    TOOL_RULE_STOP    = "tool_rule_stop"
    CANCELLED         = "cancelled"
    BUDGET_EXHAUSTED  = "budget_exhausted"
    STUCK             = "stuck"
    ERROR             = "error"
    COMPACTION_FAILED = "compaction_failed"
    EVAL_EXIT         = "eval_exit"     # exit_when() returned True

# Internal task queue types (enqueued on RunContext, LIFO)
@dataclass
class CompactionTask:
    auto: bool          # True = overflow-triggered; False = manual
    overflow: bool      # True = the triggering turn itself overflowed before output

@dataclass
class SubtaskTask:
    mode: str
    message: str
    todos: list[str] | None

async def run_loop(
    ctx: RunContext,
    task_queue: deque[CompactionTask | SubtaskTask],
    max_steps: int = MAX_STEPS_DEFAULT,
    exit_when: Callable[[RunContext], bool] | None = None,
    inspector_pipeline: InspectorPipeline | None = None,
) -> AgentResult: ...
```

### `context/compaction.py` — constants and interfaces

```python
# Overflow constants (from opencode overflow.ts)
COMPACTION_BUFFER             = 20_000
OUTPUT_TOKEN_MAX              = 32_000

# Compaction summary constants (from opencode compaction.ts)
PRUNE_MINIMUM                 = 20_000
PRUNE_PROTECT                 = 40_000
TOOL_OUTPUT_MAX_CHARS         = 2_000
DEFAULT_TAIL_TURNS            = 2
MIN_PRESERVE_RECENT_TOKENS    = 2_000
MAX_PRESERVE_RECENT_TOKENS    = 8_000
PRUNE_PROTECTED_TOOL_NAMES    = frozenset({"think", "plan", "skill"})

COMPACTION_SUMMARY_SECTIONS = [
    "Goal", "Constraints & Preferences", "Progress",
    "Key Decisions", "Next Steps", "Critical Context",
    "Relevant Files", "Failed Approaches",
]

class CompactionResult(TypedDict):
    summary: str
    tail_messages: list[Message]
    hidden_indices: frozenset[int]
    stop: bool   # True = compaction itself failed (hard stop)

def is_overflow(last_turn_tokens: UsageStats, model: ModelProfile) -> bool: ...
def usable_tokens(model: ModelProfile) -> int: ...
def preserve_recent_budget(usable: int) -> int: ...
async def compact(
    messages: list[Message],
    model: ModelProfile,
    aux_model: ModelProfile,            # small cheap model for summarization
    previous_summary: str | None,
    hidden: frozenset[int],
    tail_turns: int = DEFAULT_TAIL_TURNS,
    overflow_mode: bool = False,
) -> CompactionResult: ...
def prune(messages: list[Message]) -> list[Message]: ...
```

### `context/truncation.py` — deterministic fallback

```python
TRUNCATION_THRESHOLD_PCT    = 0.90
TRUNCATION_KEEP_FIRST_N     = 2     # always keep first N messages (first user+assistant pair)

def should_truncate(billed_tokens: int, usable: int) -> bool:
    return billed_tokens / usable >= TRUNCATION_THRESHOLD_PCT

def truncation_keep_fraction(billed_tokens: int, usable: int) -> Literal["half", "quarter"]:
    return "quarter" if billed_tokens / 2 > usable else "half"

def truncate(
    messages: list[Message],
    deleted_range: tuple[int, int] | None,   # cumulative, only grows
    keep: Literal["half", "quarter"],
) -> tuple[list[Message], tuple[int, int]]: ...   # (truncated, new_deleted_range)

def dedupe_file_reads(messages: list[Message]) -> tuple[list[Message], bool]: ...
# Returns (updated_messages, freed_any)
```

### `safety/inspector.py` — ToolInspector pipeline

```python
@dataclass
class InspectionResult:
    action: Literal["allow", "warn", "deny"]
    reason: str
    finding_id: str
    inject_message: str | None = None  # text to inject into next user turn on "warn"

class ToolInspector(Protocol):
    def inspect(self, tool_name: str, args: dict) -> InspectionResult: ...

class RepetitionInspector:
    SOFT_THRESHOLD: ClassVar[int] = 3
    HARD_THRESHOLD: ClassVar[int] = 5
    IGNORED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "task_progress", "step_number", "timestamp", "attempt",
    })
    def canonical_sig(self, tool_name: str, args: dict) -> str: ...
    def inspect(self, tool_name: str, args: dict) -> InspectionResult: ...

class InspectorPipeline:
    inspectors: list[ToolInspector]
    def check(self, tool_name: str, args: dict) -> InspectionResult: ...
    # Merge rule: any "deny" wins; "warn" collects inject_messages; "allow" passes
```

### `tools/edit_format.py` — file-edit format taxonomy

```python
class EditFormat(str, Enum):
    WHOLE             = "whole"             # return entire file in fenced block
    SEARCH_REPLACE    = "search_replace"    # <<<SEARCH ... === ... >>>REPLACE
    SEARCH_REPLACE_FENCED = "search_replace_fenced"  # filename inside fence (Gemini)
    UDIFF             = "udiff"             # unified diff with @@ hunks

EDIT_FORMAT_TABLE: dict[str, EditFormat] = {
    "claude":            EditFormat.SEARCH_REPLACE,
    "gpt-4":             EditFormat.SEARCH_REPLACE,
    "gpt-4o":            EditFormat.SEARCH_REPLACE,
    "gemini":            EditFormat.SEARCH_REPLACE_FENCED,
    "gpt-4-turbo":       EditFormat.UDIFF,
    "default":           EditFormat.WHOLE,  # weak/small/unknown models
}

# Tolerant marker regexes (Aider editblock_coder.py)
HEAD_RE    = re.compile(r"^<{5,9} SEARCH>?\s*$",  re.MULTILINE)
DIVIDER_RE = re.compile(r"^={5,9}\s*$",            re.MULTILINE)
UPDATED_RE = re.compile(r"^>{5,9} REPLACE\s*$",    re.MULTILINE)

def apply_search_replace(whole: str, search: str, replace: str) -> str | ApplyError:
    """4-stage cascade: exact → whitespace-flex → dotdotdots → error."""

@dataclass
class ApplyError:
    search_block: str
    already_present: bool   # REPLACE content already in file?
    error_message: str      # model-legible, fed back as tool result
```

### `context/repomap.py` — budget-aware symbol context

```python
MAP_BUDGET_DEFAULT          = 1_024   # tokens; override per-session
MAP_PCT_ERR_TOLERANCE       = 0.15
MAP_MUL_NO_FILES            = 8       # multiply budget when no chat files set
SEED_TOKENS_PER_TAG         = 25
MAP_AUTO_RECOMPUTE_THRESHOLD = 1.0    # seconds

CHAT_FILE_REFERENCER_MUL    = 50.0
MENTIONED_IDENT_MUL         = 10.0
LONG_MULTICASE_NAME_MUL     = 10.0   # len >= 8 AND multi-case
PRIVATE_IDENT_MUL           =  0.1   # starts with "_"
COMMON_IDENT_MUL            =  0.1   # defined in > 5 files
SELF_EDGE_WEIGHT            =  0.1

class RepoMap:
    def get_map(
        self,
        chat_files: list[Path],
        mentioned_idents: set[str],
        max_tokens: int = MAP_BUDGET_DEFAULT,
    ) -> str: ...   # formatted symbol tree, token-budgeted to ±15%
```

### `runtime/mode.py` — plan/act persisted mode

```python
@dataclass
class ToolGroupOptions:
    file_regex: str | None = None
    description: str | None = None

ToolGroupEntry = str | tuple[str, ToolGroupOptions]

@dataclass
class ModeConfig:
    slug: str
    role_definition: str
    when_to_use: str | None = None
    custom_instructions: str | None = None
    tool_groups: list[ToolGroupEntry] = field(default_factory=list)
    model: str | None = None         # None = inherit from agent

BUILT_IN_MODES: dict[str, ModeConfig] = {
    "plan": ModeConfig(
        slug="plan",
        role_definition="You are in PLANNING mode. Reason, propose, and outline changes. "
                        "Do NOT make any edits or run any commands.",
        tool_groups=["read", "search", "think"],
    ),
    "act": ModeConfig(
        slug="act",
        role_definition="You are in EXECUTION mode. Implement the plan.",
        tool_groups=["read", "edit", "exec", "search", "think", "done"],
    ),
}
```

### `core/retry.py` — retry/backoff constants

```python
# Adapted from opencode session/retry.ts
RETRY_INITIAL_DELAY_MS        = 2_000
RETRY_BACKOFF_FACTOR          = 2
RETRY_MAX_DELAY_NO_HEADERS_MS = 30_000    # cap when server gives no retry hint
RETRY_MAX_ATTEMPTS            = 6         # PRD §6.4 default

# PRD §6.4: "initial=4s, max=240s" for Verso — slightly more conservative than opencode
RETRY_INITIAL_DELAY_VERSO_MS  = 4_000
RETRY_MAX_DELAY_VERSO_MS      = 240_000

# Never retry on context overflow — compaction must happen first (opencode retry.ts)
NEVER_RETRY_REASONS = frozenset({StopReason.COMPACTION_FAILED, StopReason.BUDGET_EXHAUSTED})
```

---

## Open Unknowns

1. **Auxiliary compaction model selection.** The compaction pass should use a small cheap model to avoid burning the primary model's token budget and disrupting prompt-cache warmth. Which model is the default auxiliary? Options: `haiku-3-5`, `gpt-4.1-mini`, same model as primary (Warp's approach — higher fidelity but costs more). Need to dogfood: does a cheap auxiliary produce summaries good enough to resume mid-task without confusion? Warp's deterministic TODO-preservation is a promising hybrid (cheap model + structured payload for must-keep items).

2. **RepoMap in non-coding agents.** Tree-sitter + PageRank is clearly right for coding agents. For research or general-purpose agents with large document corpora, the right analogue is unclear — a sentence-transformer embedding index with MMR selection is the obvious candidate but hasn't been validated as "budget-aware" in the same binary-search sense. Prototype needed.

3. **`task_boundary` tool adoption rate.** The Antigravity `PLANNING → EXECUTION → VERIFICATION` mode gate (PRD §5.1) is described as "the single most impactful reliability pattern" but it adds friction for trivial tasks. The "skip mode for simple work meta-selector" needs to be defined concretely: who decides "simple"? Model self-assessment? A fast classifier? A heuristic on task description length? Needs dogfooding on real tasks before hardcoding.

4. **Compaction summary quality vs. pure observation masking.** The PRD cites JetBrains NeurIPS 2025 observation-masking at +52% cheaper, +2.6% solve-rate. Opencode's anchored-summary approach preserves more semantic continuity. Both are adopted (prune = masking, compact = summary) but the trigger threshold for when to invoke summarization vs. relying on masking alone needs calibration on real long-running tasks.

5. **Shadow-git checkpoint for the Python equivalent.** Cline's `core.worktree` shadow-git approach requires the checkpoint repo to be initialized in a controlled directory. In Verso's durable runtime, the checkpoint is an event log (PRD §6.1). For per-file undo in coding agents specifically, the shadow-git approach is the best OSS primitive — but the interaction with the durable event log (two checkpointing systems: file state + agent state) needs a clean design. Do they share a commit boundary? Are they independent? This is Phase 2/3 work but the design decision should be made before implementing durable runtime.

6. **Boomerang disk-freeze vs. in-memory parent freeze.** Roo Code freezes the parent to disk before launching a child (guaranteeing isolation). Verso's durable runtime naturally provides this (all state is persisted). But in tactical (in-memory) mode, a sub-agent call means the parent's context is still in memory — is that acceptable, or should tactical sub-agent calls always be forced to durable mode? The PRD says "depth cap default = 1" which limits the problem, but the isolation semantics need to be explicit.
