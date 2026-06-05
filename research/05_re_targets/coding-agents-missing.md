# RE Targets: Coding Agents Not Yet in Teardowns

**Category:** Coding agents — loop/diff/context/permission patterns not yet covered  
**Date:** 2026-06-05  
**Verso relevance:** async ReAct loop design, tactical↔durable seam, context engineering, typed memory, permission/approval UX, diff application, multi-agent sub-task dispatch, evals.

---

## Already Covered

The following coding agents have teardowns in `teardowns/` and are NOT re-targeted here:

| File | Agent | Depth | Key covered patterns |
|------|-------|-------|----------------------|
| `CLAUDE_CODE.md` | Claude Code | 5,140 lines | Multi-agent Task dispatch, permission modes, subagent context isolation, background agents, file locking for parallel work |
| `CODEX.md` | OpenAI Codex CLI | 5,367 lines | Sampling loop (not ReAct), parallel tool calls, streaming, Agents SDK + MCP wrapping, multi-model diff comparison |
| `CURSOR.md` | Cursor | 4,659 lines | Shadow workspace, speculative edits, background agents, diff rendering |
| `OPENHANDS.md` | OpenHands (All Hands) | 1,404 lines | Event-stream loop, LLMSummarizingCondenser (max_size=80, keep_first=4), ApplyPatchTool (unified diff), ConversationExecutionStatus 8-state machine, Docker sandbox, FIFOLock state manager |
| `SOURCEGRAPH_AMP.md` | Amp (Sourcegraph) | 963 lines | Provider-multiplexed loop, Task sub-agent (1 tier, no recursion), Oracle=o3 reasoning escape hatch, `@pierre/diffs` WASM diff renderer, AGENTS.md self-extension |
| `DEVIN.md` | Devin | 2,485 lines | Long-horizon planning, browser+shell+IDE in sandbox |
| `REPLIT_AGENT.md` | Replit Agent | 831 lines | In-browser execution loop |
| `BOLT_NEW.md` | Bolt.new | 805 lines | WebContainer, in-browser full-stack |
| `JULES.md` | Jules (Google) | 880 lines | Async background agent, PR-first dispatch |
| `JUNIE.md` | Junie (JetBrains) | 824 lines | IDE-native loop, JetBrains PSI integration |
| `FACTORY_AI.md` | Factory AI | 827 lines | Droids architecture, long-horizon task graphs |
| `ANTIGRAVITY.md` | Antigravity (ex-Gemini CLI) | 2,089 lines | PLANNING→EXECUTION→VERIFICATION state machine, per-edit Complexity 1-10 rating, SafeToAutoRun, task_boundary tool, Trajectories replay artifact, brain/ persistent context dir |

---

## RE Targets

### Aider

**What it is:** CLI pair-programmer that edits files via typed diff formats and commits changes to git after each step; architect/editor two-model pipeline is the main architectural differentiator.

**Why for Verso:** Aider's five edit formats (`whole`, `diff`, `diff-fenced`, `udiff`, `editor-diff`, `editor-whole`) are the most studied diff-application taxonomy in open-source coding agents — each format makes a different tradeoff between token cost and LLM compliance. The architect/editor split (one model plans in prose, a cheaper model converts prose to edits) is a concrete implementation of Verso's "tactical loop" idea: the planning pass is model-agnostic and the editing pass is a deterministic transform. The RepoMap (tree-sitter PageRank graph with personalization weights: chat_fnames=100/n, mentioned_fnames=100/n, self-loop=0.1, edge=1.0) is the best open-source implementation of budget-aware context selection. These three patterns — format taxonomy, two-model split, RepoMap — directly inform Verso's context engineering and tool-output surface area.

**What to RE:** (1) `aider/coders/*.py` — each Coder subclass maps to one edit format; extract the exact prompts and search/replace parsing logic. (2) `aider/repomap.py` — `get_ranked_tags_map()` lines 365-485, `rank_tags()` lines 487-577; extract all edge weights, token budget algorithm, cache schema. (3) `aider/models.py` — how default edit format is assigned per model. (4) Architect→editor message passing: what exact prompt the architect produces that the editor consumes.

**Source pointer:** `github.com/Aider-AI/aider` — fully open source (Apache 2.0). Primary files: `aider/coders/`, `aider/repomap.py`, `aider/models.py`, `aider/website/docs/more/edit-formats.md`.

**Priority:** P0 — the diff format taxonomy and RepoMap algorithm are directly load-bearing for Verso's tool output surface and context selection design.

---

### Cline

**What it is:** Apache 2.0 VS Code extension (5M+ installs, 61k stars) — the most widely deployed open-source coding agent; plan/act split with per-step approval; 30+ provider support.

**Why for Verso:** Cline's plan/act split is the most production-tested implementation of the "human in the loop" toggle that maps directly onto Verso's tactical↔durable seam: Plan mode = read+reason without executing (same as Verso's HITL checkpoint mode), Act mode = execute with configurable approval granularity. The approval model is the richest in the open-source space: per-tool allow rules, auto-approve toggle, `.clinerules` per-repo overrides. The checkpoint system (git snapshot before each step, undo via restore) is the closest open-source analog to Verso's checkpoint-resume primitive. As the common ancestor of Roo Code and Kilo Code, understanding Cline's core architecture illuminates the whole family.

**What to RE:** (1) `src/core/Cline.ts` — the main agent loop; extract the plan/act state machine, tool dispatch, approval gate logic, and `DOOM_LOOP` guard. (2) `src/core/tools/` — the full tool registry with schemas. (3) Checkpoint/undo implementation — how git snapshots are taken and restored. (4) Context window management — truncation strategy and what gets dropped first. (5) `.clinerules` loading and merging logic.

**Source pointer:** `github.com/cline/cline` — Apache 2.0. Key dirs: `src/core/`, `apps/cli/`, `sdk/`.

**Priority:** P0 — plan/act split + approval granularity + checkpoint-undo is the reference implementation for Verso's HITL seam.

---

### opencode (SST)

**What it is:** TypeScript/Bun terminal coding agent with client-server architecture; TUI + VS Code extension + web all connect to a local `opencode serve` process; 150k GitHub stars in ~11 months; Kilo Code replatformed on its server in April 2026.

**Why for Verso:** opencode is architecturally the most Verso-like of the open-source agents: the `SessionPrompt.loop()` state machine in `packages/opencode/src/session/prompt.ts` explicitly handles `SubtaskPart` (sub-agent dispatch), `CompactionPart` (context maintenance), and `StructuredOutput` injection — three concerns Verso addresses at the framework level. The client-server split (agent runs as a local process, multiple UIs connect via HTTP+SSE) is the cleanest implementation of "agent as a service" in this space. Session persistence via SQLite/Drizzle with WAL mode + 5s busy timeout + cursor-based message pagination is a concrete durable-state implementation. The `DOOM_LOOP_THRESHOLD=3` guard and `SessionRetry.retryable()` + exponential backoff with `retry-after` header respect are production-tested reliability patterns. `ProviderTransform` middleware (Claude tool ID regex normalization, Anthropic empty-part filtering, `promptCacheKey` injection, surrogate sanitization) is the cleanest provider-normalization layer in the space.

**What to RE:** (1) `packages/opencode/src/session/prompt.ts` — `SessionPrompt.loop()` in full; all state transitions, `isOverflow()` trigger, compaction algorithm. (2) `packages/opencode/src/session/message-v2.ts` + `packages/opencode/src/session/llm/request.ts` — how messages are assembled and tools filtered by `Permission.Ruleset`. (3) `packages/opencode/src/provider/transform.ts` — `ProviderTransform` middleware; every normalization step per provider. (4) Session schema in Drizzle — exact fields, indexes, foreign keys. (5) ACP (Agent Client Protocol) — the JSON-RPC protocol that Zed and other editors use to connect to the agent server.

**Source pointer:** `github.com/sst/opencode` — MIT. Also: `deepwiki.com/sst/opencode` has well-mapped architecture docs covering session lifecycle, prompt pipeline, compaction, and ACP.

**Priority:** P0 — the TypeScript analog of what Verso wants to be in Python; the session loop, compaction trigger, and provider normalization are directly design-informing.

---

### Goose (Block / AAIF)

**What it is:** Rust-core open-source agent (Apache 2.0) donated to the Agentic AI Foundation at the Linux Foundation; CLI + Electron desktop; MCP-first extension system; 15+ providers; Recipe system for declarative workflows.

**Why for Verso:** Goose is the primary Rust-implemented reference for MCP-as-extension-system — the exact architecture Verso is explicitly NOT copying (MCP demoted to adapter). Reading Goose's `goose-mcp` crate reveals what MCP buys you at the implementation level and what it costs (lifecycle complexity, transport multiplexing, schema repetition). The builtin extensions implemented as Rust structs that implement the MCP client trait synchronously show the lowest-friction MCP embedding. The Recipe system (declarative YAML workflows with `minijinja` templating) is the closest open-source analog to Verso's "durable workflow" concern — declarative task graphs without a graph DSL. The provider abstraction (canonical model registry of ~1,700 models, tool shim for non-native-tool models) is the most comprehensive in open source.

**What to RE:** (1) `crates/goose/src/` — the core agent loop; how conversation turns are managed, tool invocation sequenced, context compacted. (2) `crates/goose-mcp/` — builtin extension implementations; what the MCP client trait looks like in Rust, how builtin vs external extensions differ. (3) Recipe system — `minijinja` template evaluation, how recipes compose tool calls. (4) Provider trait — how the ~1,700 model registry maps to capability detection and tool shimming for non-native models. (5) SQLite session persistence via `sqlx` — schema and query patterns.

**Source pointer:** `github.com/block/goose` (mirrors at `github.com/aaif-goose/goose`) — Apache 2.0. Cargo workspace; key crates: `goose`, `goose-cli`, `goose-server`, `goose-mcp`.

**Priority:** P1 — Rust architecture so not directly portable, but the MCP-as-extension tradeoff analysis and Recipe/durable-workflow design are high Verso relevance.

---

### Roo Code

**What it is:** Apache 2.0 VS Code fork of Cline with orchestrator mode (Boomerang Tasks), custom modes, cloud agents, SOC 2 Type II; 1.5M+ users before Kilo Code fork; now pivoting to Roo Code Cloud.

**Why for Verso:** Roo Code invented the Boomerang Tasks pattern — the only open-source implementation of structured multi-agent orchestration where the parent agent pauses, the subtask runs in a fresh context with a different mode, returns only a summary, and the parent resumes. This is the concrete implementation of Verso's "sub-agent dispatch returns summary to parent" pattern. The mode system (Orchestrator, Architect, Code, Debug, Ask, custom) maps each mode to a different system prompt + tool set + context policy — a typed agent variant system Verso needs to understand. The separation of "orchestrator sees summary only" (not the subtask's full context) is the key context-isolation decision.

**What to RE:** (1) `src/core/` — how Boomerang task launch works: what state the parent freezes, how the subtask's context is isolated, what summary format the subtask returns. (2) Mode definition schema — how custom modes specify their tool subsets and system prompt fragments. (3) Diff between Cline base and Roo additions — `git log --oneline` from fork point to identify architectural additions vs UI changes. (4) Cloud agent integration — how `.continue/checks/`-style async agents are dispatched.

**Source pointer:** `github.com/RooCodeInc/Roo-Code` — Apache 2.0. Docs: `docs.roocode.com/features/boomerang-tasks`.

**Priority:** P1 — Boomerang Tasks is the most studied open-source implementation of the "sub-task with context isolation and summary return" pattern Verso needs in its multi-agent story.

---

### Augment Code

**What it is:** Closed-source enterprise coding agent; its architectural differentiator is the Context Engine — a proprietary semantic indexer for 400k+ file codebases, now exposed as an MCP server (local CLI or hosted at `api.augmentcode.com/mcp`). SWE-bench Pro: 51.80% (top score April 2026, ahead of Cursor, Claude Code, Codex).

**Why for Verso:** Augment's core claim — "a weaker model with great context beats a stronger model with poor context" — is the empirical validation of Verso's context engineering pillar. The Context Engine MCP exposes the semantic search as a standalone service any agent can call, which means: (a) the tool schema is inspectable, (b) the performance delta (30-80% improvement across different agents) is measured, (c) the architecture is decoupled enough to RE via the MCP interface. The question for Verso is: what does the Context Engine MCP tool schema look like, and what retrieval algorithm produces 70%+ gains?

**What to RE:** (1) Probe `api.augmentcode.com/mcp` — list tools, get schemas via MCP `tools/list`. The MCP protocol means the tool schemas are inspectable without source access. (2) Run `auggie` CLI locally as MCP server and capture the tool call/response pairs for representative queries. (3) Read the engineering blog post referenced in SWE-bench Pro analysis for indexing algorithm details. (4) DNS/TXT records for `augmentcode.com` to map the backend stack. (5) Check `docs.augmentcode.com/context-services/mcp/overview` for tool schema documentation.

**Source pointer:** Closed — probe via: MCP `tools/list` at `api.augmentcode.com/mcp`; `auggie` CLI binary (`npm install -g @augment/cli`); `docs.augmentcode.com/context-services/`. VS Code extension ID: `augment.vscode-augment`.

**Priority:** P1 — the only closed target here, but the context-first performance evidence directly validates Verso's design thesis, and the MCP interface makes it partially RE-able without source.

---

### Continue.dev (post-pivot)

**What it is:** Pivoted from IDE extension to open-source CLI for async PR agents; agents are markdown files in `.continue/checks/`; runs in GitHub Actions; no hosted code processing. Apache 2.0.

**Why for Verso:** Continue's post-pivot architecture is the simplest open-source implementation of the "async agent triggered by CI event" pattern — exactly the durable/event-sourced side of Verso's tactical↔durable seam in the context of code review. Each check is a markdown prompt file; the agent runs headlessly against the PR diff; results post as GitHub status checks. The architectural question for Verso: how is the agent loop structured when there's no interactive user — what are the termination conditions, how is the context assembled from the PR diff, and how is the result serialized back to GitHub? The "zero hosted service reads your code" design is also a useful trust/permission model reference.

**What to RE:** (1) `github.com/continuedev/continue` — the CLI's agent loop for headless PR review mode; how `checks/*.md` files are parsed and executed. (2) The GitHub Actions integration — what event payload is passed to the agent. (3) Context assembly from PR diff — how the agent sees the diff vs the full file vs the repo. (4) Output serialization — how the agent's response becomes a GitHub status check + diff suggestion.

**Source pointer:** `github.com/continuedev/continue` — Apache 2.0. Docs: `docs.continue.dev/agents/overview`, `docs.continue.dev/guides/github-pr-review-bot`.

**Priority:** P2 — the async/CI side of the agent spectrum; useful for Verso's durable seam design but lower priority than the core loop references above.

---

### Qodo (Qodo Gen CLI)

**What it is:** Formerly CodiumAI; multi-agent test generation + code review platform; Qodo 2.0 (Feb 2026) introduced 4 parallel specialist agents (bug, quality, security, test coverage); F1=60.1% on bug benchmarks; Qodo Gen CLI lets users define custom agents.

**Why for Verso:** Qodo is the only coding agent that runs N specialist agents in parallel on the same diff and merges results — a pattern Verso's multi-agent story could adopt for evals/review. The "Qodo Cover CLI" agent loop (iterate until test coverage target met) is the cleanest example of an eval-driven agent loop: the termination condition is a metric, not a human decision. The custom agent framework (Qodo Gen CLI) exposes how they parameterize agent behavior via config — directly relevant to Verso's typed memory + evals design.

**What to RE:** (1) Qodo Cover CLI binary — extract the test-generation loop: how many iterations, what coverage metric drives termination, what tools are available. (2) The 4-parallel-agent review architecture in Qodo 2.0 — how results are merged, how conflicts between agents are resolved. (3) Qodo Gen CLI agent definition schema — what fields define a custom agent. (4) npm/PyPI packages: `@qodo/gen`, `qodo-cover` — read every source file.

**Source pointer:** Partially open — `github.com/Codium-ai` org; `npm pack @qodo/gen` and `pip install qodo-cover` for source. Docs: `qodo.ai/docs`. VS Code extension: `Codium.codium`.

**Priority:** P2 — the eval-driven termination and parallel-specialist merge pattern is useful for Verso's evals pillar, but the core loop patterns are less novel.

---

## Notes

**What's already well-covered for Verso's purposes:**

- The standard ReAct sampling loop (Codex teardown covers this exhaustively).
- Sub-agent dispatch with context isolation (Claude Code teardown: Task tool + FIFOLock; Amp teardown: Task + Oracle).
- Event-stream state machines (OpenHands teardown: 8-state ConversationExecutionStatus, FIFOLock, condenser).
- PLANNING→EXECUTION→VERIFICATION explicit state machine with user-approval gates (Antigravity teardown).
- Multi-provider proxy with uniform agent (Amp teardown: 9 providers, same loop/tools/prompt across all).

**Patterns not yet covered that Verso most needs:**

1. **Diff format taxonomy** (Aider) — Verso needs to decide what its tool-call output surface looks like for file edits; Aider's 5-format taxonomy is the reference.
2. **Approval granularity + HITL toggle** (Cline) — The production-tested implementation of "same agent, in-memory vs checkpoint" via plan/act + auto-approve + .clinerules.
3. **Session-as-service with typed compaction** (opencode) — The cleanest TypeScript implementation of the loop concerns Verso wants in Python: `isOverflow()`, `SubtaskPart`, `CompactionPart`, `DOOM_LOOP_THRESHOLD`.
4. **Context-first semantic retrieval** (Augment) — Empirical validation that context quality > model size; the MCP tool schema is RE-able.
5. **Boomerang sub-task with context isolation** (Roo Code) — The only open-source implementation of "parent pauses, subtask runs in fresh context, returns summary only."

**Kilo Code note:** Kilo Code forked both Cline and Roo Code and replatformed on opencode's server (GA April 2, 2026). It adds Orchestrator mode (same as Roo's Boomerang), inline autocomplete, and Memory Bank. Its architecture is a superset of Cline + Roo + opencode server — reading those three sources covers Kilo Code's architecture without a separate teardown. Not added as a standalone target.

**Goose note:** Moved from `block/goose` to the Agentic AI Foundation (`aaif-goose/goose`). The Rust implementation means no code is directly portable to Verso, but the MCP-as-extension system and Recipe/durable-workflow design are the highest-value architecture references for what Verso explicitly demotes (MCP) or builds (durable workflows without graph DSL).
