# Verso Design Brief — Synthesis of 23 Teardowns

**Date:** 2026-06-04
**Inputs:** all 23 notes in `research/03_teardowns/` (frameworks, coding agents, research agents, multi-agent ensembles, product agents, model-routing / retrieval / vector-memory / serving infra).
**Thesis under test:** Verso is a *keep-it-simple* agent framework — one clean async ReAct loop as the default, MCP-first tools, typed memory, named stop reasons, and evals as a first-class citizen. The escape hatch for graphs/multi-agent exists but is never the default.

This brief is opinionated. Each claim cites the source note (filename without `.md`). When two notes disagree, both are named and the call is made explicitly.

---

## 0. The one-paragraph conclusion

Across every teardown the production winners converge on the *same boring core*: a single async ReAct loop, tool failures as data (never exceptions), structured stop reasons, prompt-cache-preserving context assembly, and a separate cheap model for the side jobs (compaction, classification, judging). The interesting differentiation is almost never in the loop — it's in (a) the **tool dispatch layer** (meta-tools, deferred loading, fuzzy repair, parallel-with-order-preservation), (b) **context engineering** (distilled reflections, cache-aware truncation, memory-freeze invariant), (c) **memory tiers** (scratchpad/episodic/fact/procedural + temporal versioning), and (d) **provider routing** (cross-model failover, per-role models, `require_parameters`). LangGraph/CrewAI/Letta over-build the loop; Claude Agent SDK hides it in a binary; Warp/Codex/Cursor/Devin keep it dumb and invest everything in tooling + failover + context. **Verso's wedge is to ship the boring core as a clean, small, typed, async surface — and ship the four differentiators as first-class primitives that the big frameworks bury in 3,000-line files.**

---

## 1. How the leading FRAMEWORKS actually differ — and the gap Verso fills

The six framework families (`fw-langchain-langgraph`, `fw-crewai-letta`, `fw-claude-sdk-platforms`, `fw-composio-browseruse`) are not interchangeable. They make fundamentally different bets on *where the loop lives* and *what the core primitive is*.

| Framework | Core primitive | Loop location | Tool model | Memory model | Provider abstraction | The trap |
|---|---|---|---|---|---|---|
| **LangChain** (`fw-langchain-langgraph`) | `Runnable` (universal `invoke/stream/batch`) | v0: explicit `while` (`max_iterations=15`); v1: delegates to LangGraph | `@tool` + docstring → Pydantic `args_schema`; 4-way error policy | 7 deprecated memory classes + 30 backends → v1 Checkpointer+Store | `init_chat_model("provider:model")`, ~19 providers | LCEL: 15+ `Runnable` classes of mandatory indirection; Pydantic v1/v2 dual-support branch hell |
| **LangGraph** (`fw-langchain-langgraph`) | **Pregel superstep** (BSP: plan→execute→commit atomically) | BSP scheduler with channels + reducers | `ToolNode` dispatches via `Send`; per-node `RetryPolicy` | Checkpointer (short) + `BaseStore` (vector+TTL long) | inherits LangChain | "agent = Pregel scheduler with channels" is a non-obvious mental model that must be *sold*; `DEFAULT_RECURSION_LIMIT=10007` ≠ docs' 25 |
| **CrewAI** (`fw-crewai-letta`) | Role-play agent (`role`/`goal`/`backstory` → system prompt) | dual loop: native-tools vs ReAct-text, `max_iter=25` | `BaseTool` Pydantic; `ToolUsage` 4-stage input-repair ladder + fuzzy name fix (0.85) | 4 legacy stores + Unified Memory (LanceDB) with `0.5/0.3/0.2` recall weights | LiteLLM (100+ providers) | two execution models in one repo (`Crew` + `Flow`); streaming = run-in-thread + tail-event-bus (not real); `raise Exception("Manager should not have tools")` |
| **Letta** (`fw-crewai-letta`) | **Virtual context** (LLM edits its own memory via tools; core/recall/archival tiers) | `LettaAgentV3` continuation state machine, `DEFAULT_MAX_STEPS=50` | memory tools are first-class; V3 `memory` omni-tool; tool-rule constraint solver | core blocks (DB rows, shareable across agents) + recall (hybrid) + archival (pgvector 1024-dim) | 17 providers, auto-mode content+availability routing | `letta_agent_v3.py` = 2,134 lines; Postgres+pgvector mandatory; V2→V3 silent heartbeat semantics break |
| **Claude Agent SDK** (`fw-claude-sdk-platforms`) | **Subprocess-delegated loop** (SDK is a protocol bridge; loop runs in the `claude` binary) | inside the binary (opaque); SDK demuxes one JSONL stream | in-process SDK-MCP via `mcp_message` control req; 5 transports | binary-owned JSONL transcript; pluggable `SessionStore` via `transcript_mirror` side-channel | **Anthropic-only** (7 API providers but one vendor) | you can't inspect or extend the loop; Anthropic-locked — fatal for a general framework |
| **Composio** (`fw-composio-browseruse`) | **Meta-tool layer** (6 tools the LLM sees; 10K+ tools server-side) | NOT a framework — tool layer beneath an agent | `COMPOSIO_MULTI_EXECUTE_TOOL` batches N calls (`max_workers=5`); 3-point modifier engine | session sandbox + per-app cross-session memory + recipe/plan cache | sends `provider=` per request (leakage) | hides the schema compiler in `utils/shared.py`; provider-name→behavior coupling |

**The gap Verso fills (the synthesis verdict):**

1. **No framework ships a clean, small, async-native ReAct loop as the default.** LangGraph forces Pregel; CrewAI ships two execution models; Claude SDK hides the loop in a binary; Letta's loop is a 2,134-line monolith. Verso's loop body should be **<200 lines** — all retry/failover delegates to an error classifier, all tool exec to a dispatcher, all prompt building to a builder (`hermes-agent-core` §1 lesson: Hermes' 3,600-line loop is the anti-pattern to avoid).

2. **Memory is fragmented into 3 different systems with 3 different APIs everywhere.** LangChain/LangGraph: Checkpointer (short) + Store (long) + SummarizationMiddleware (compaction). Letta: core/recall/archival. Verso should **unify these under one `Memory` interface** (`fw-langchain-langgraph` Verso-Could-Improve #36) with short-term (channel state), long-term (vector+KV), and compaction (TTL/token-budget) as properties of the same object, and the four-tier taxonomy (`scratchpad/episodic/fact/procedural`) from `research-nia-societies-mindtrip` as the type system.

3. **Tool-schema flooding is universal and unsolved at the framework layer.** Composio reduced 1000+ schemas to 6 meta-tools (50K+ token saving). Claude Code, Codex, Cursor, Claude Research, OpenAI DR all independently shipped *deferred tool loading* (`ToolSearch` / `tool_search` / `defer_loading`). Verso must ship **deferred MCP tool loading** as a first-class default (`coding-claude-code` Copy #2, `research-deepresearch` §5).

4. **Provider abstraction is either too thin (Claude SDK = one vendor) or too fat (LiteLLM = 592K LOC monolith).** The right shape is the 4-method `Config`/`ProviderProfile` pattern (`infra-model-routing` LiteLLM lesson + `hermes-surfaces` §1) with cross-model failover (`coding-devin-warp` Warp). Verso sits *above* a thin provider layer, never re-implements it, and exposes routing as **per-node config, not a global setting**.

5. **MCP is bolted on everywhere; nobody treats it as the primary tool protocol.** CrewAI uses an adapter; LlamaIndex passes MCP via `tools=[...]`; Letta has a separate `mcp_client/`. Verso should make **MCP the primary tool registration mechanism**, bidirectional by default (every Verso agent is both an MCP server and a client — `fw-composio-browseruse` Pattern 2, `coding-codex` MCP section).

6. **Evals are an afterthought in every framework and a first-class product surface in every winning *product*.** Mindtrip (`generate_from_session`, `build_from_description`, `run_ephemeral`), Character.AI (JudgeJudy 3-judge panel), Together (managed evals API), Pleep (RAGAS loop), Aemon (eval IS the entry point), Anthropic Research (`define_outcome` grade→revise loop). **No framework ships this.** Verso's differentiator is evals-in-the-loop (`research-nia-societies-mindtrip` §5, `agents-abridge-pleep-misc` Copy #3, `agents-products` §15-17).

---

## 2. Best agent-LOOP + TOOL + CONTEXT + MEMORY mechanisms (each tied to its source)

### 2A. Agent LOOP mechanisms

**Default loop shape: clean async ReAct, no max-iterations religion, context-budget as the real safety net.**
- The overwhelming consensus is **single-agent tool-use loop, no plan/execute split at the loop level** — Cursor, Zed, Codex, Claude Code, Stardrift all converge here (`coding-cursor-zed` Copy #1: "the model plans internally; don't build a separate planning agent — it adds latency without improving quality"). Codex runs with **no max_iterations at all** — only token-budget + cancellation token (`coding-codex` Agent Loop; auto-compact at 95%). Warp's loop predicate is the cleanest: **continue iff `!is_cancelled()`** — a *failed* tool result continues the loop (model self-corrects); only explicit cancellation stops it (`coding-devin-warp` Warp continuation rule).
- **But always expose budget to the model.** LangGraph's `remaining_steps` ManagedValue + the `_are_more_steps_needed` guard (`remaining_steps < 2 and has_tool_calls` → stop before dead-ending mid-tool-call) is the right pattern (`fw-langchain-langgraph` Copy #5). Verso should inject budget via `context.budget.remaining` / `context.budget.is_last_step`, **not** as a state-schema channel (`fw-langchain-langgraph` Improve #38).
- **Grace call on budget exhaustion** — Hermes fires one final call so the model can summarize rather than hard-cutting mid-task (`hermes-agent-core` §1). Without it, hitting the cap produces a truncated, confusing response. LangChain ships the same idea but the opportunistic `early_stopping_method="generate"` extra-LLM-call is an anti-pattern to *avoid* (`fw-langchain-langgraph` Avoid #25) — the grace call should be deterministic, single, and final.

**Named stop reasons (not "done").**
- Letta's `_decide_continuation` state machine returns named reasons: `end_turn | max_steps | max_tokens_exceeded | tool_rule_stop | cancelled | error` (`fw-crewai-letta` Letta Copy #3). Claude Code has **12 `TerminalReason` values** (`coding-claude-code`). Exa has `schema_satisfied | budget_reached | error | cancelled` (`research-deepresearch` Exa). **Verso must return `AgentResult(output, stop_reason: StopReason, usage: UsageStats)` always** (`fw-crewai-letta` Improve #3). Each stop reason maps to a different downstream metric/log/error path.

**The 4-way error switch keeps the loop tiny.**
- Hermes' `error_classifier.py` (22-reason `FailoverReason` enum, self-contained, stdlib-only, built from hundreds of production incidents) pre-computes `{retryable, should_compress, should_rotate_credential, should_fallback}` so the retry loop is a **4-way switch, not a re-classification at each branch** (`hermes-agent-core` §8 — "port this entire module verbatim"). Critical ordering rule: *server-disconnect-on-large-session must classify as context_overflow BEFORE generic transport error* — otherwise the agent retries without compressing and hits the same wall.

**Cross-model failover, not same-model retry (the single hardest-won finding).**
- Warp: "We originally attempted to retry with the same model, and found that this often produced repeat failures." → switch to **heterogeneous failover chain** (Sonnet → Gemini Pro → GPT-4.1) on outage/rate-limit/malformed-tool-call/invalid-response (`coding-devin-warp` Warp — "this is a framework-level responsibility, not application-level"). LiteLLM ships **error-typed fallback chains** — three separate lists: `context_window_fallbacks`, `content_policy_fallbacks`, general `fallbacks` (`infra-model-routing` LiteLLM). Verso copies both: heterogeneous chain + error-typed routing.

**Tool-rule constraint solver (declaratively constrained FSM agents).**
- Letta's per-step intersection-of-allowed-tools: `InitToolRule` (must call X first), `TerminalToolRule` (calling X ends loop), `ContinueToolRule`, `ChildToolRule`/`ParentToolRule`, `MaxCountPerStepToolRule`, `RequiresApprovalToolRule`. When exactly one tool is allowed, `should_force_tool_call()` fires. This turns free-form ReAct into a declarative FSM without hardcoding workflows (`fw-crewai-letta` Letta Copy #2 — "copy the solver exactly"). Expose as optional `tool_rules: list[ToolRule]`.

**Mode-gate FSM as an opt-in reliability primitive.**
- Antigravity's `PLANNING → EXECUTION → VERIFICATION` enforced by a dedicated `task_boundary` tool — *the model cannot edit code while in PLANNING mode; the constraint is architectural, not advisory* (`coding-gemini-antigravity` Copy #1, "the single most impactful agent-reliability pattern in this teardown"). Devin's two-mode gate (planning gate before edits, user-controlled transition) is the simplest reliable version (`coding-devin-warp` Devin). Crucially, both pair it with a **"skip task mode for simple work" meta-selector** — don't pay FSM overhead on trivial tasks. Verso ships this as opt-in `mode` on a turn, not the default.

**Two-stage synthesis (loop-LLM → synthesis-LLM with a context boundary).**
- NIA's Oracle: the loop accumulates `tool_calls + summaries`, then a *separate* synthesis LLM renders the final report — and **the synthesis LLM never sees the system prompt** (security + cheaper-aggregation/premium-render tiering) (`research-nia-societies-mindtrip` §6, NIA). Perplexity forces `ToolChoice.NONE` on the final step to force synthesis (`research-perplexity` System 1). Verso: `on_finish(tool_calls, summaries) → synthesis_call` as a first-class hook with optional context isolation.

**The `think`/scratchpad sentinel makes reasoning observable.**
- NIA's `think({reflection})` is a structured no-op that forces CoT into the wire's `reason` field without leaking to the response (`research-nia-societies-mindtrip` §1, NIA). Devin's `<think>` has **13 enumerated mandatory/should-use triggers** (before git decisions, before edits, before reporting done) — the strongest "force reflection" mechanism in any deployed agent (`coding-devin-warp` Devin Copy). Ship a built-in `think` tool with documented trigger conditions.

### 2B. TOOL mechanisms

**Tool failures are data, never exceptions — the universal invariant.**
- Composio's execution envelope `{data, error, successful}` — *always* (`fw-composio-browseruse` Composio Copy #5). LangChain's 4-way `handle_tool_error` policy (`fw-langchain-langgraph` Tool error policy). LlamaIndex catches exceptions → `ToolOutput(is_error=True, content=str(e))`, model can recover (`infra-retrieval-tools` LlamaIndex). Hermes' universal `dispatch()` *always* returns `{"error": "msg"}`, never raises (`hermes-agent-core` §3). **Verso's tool invocation pipeline must never propagate an unhandled exception to the loop.**

**The 4-stage input-repair ladder + fuzzy name correction.**
- CrewAI's `_validate_tool_input`: `json.loads → ast.literal_eval → json5.loads → repair_json` before giving up; `SequenceMatcher > 0.85` silently fixes `web_serch → web_search`; repeated-`(tool, args)` short-circuit returns cached result to stop identical infinite loops (`fw-crewai-letta` CrewAI Copy #3,#4,#9). Browser-Use's Anthropic double-serialization fix (`{"actions": "[...]"}` string instead of array → `json.loads` any field starting with `[`/`{`) is the battle-tested production workaround (`fw-composio-browseruse` Browser-Use Provider-Specific Output).

**Meta-tools + deferred loading (O(N) schemas → O(1)).**
- Composio: 6 meta-tools instead of 1000 (`COMPOSIO_SEARCH_TOOLS`, `COMPOSIO_MULTI_EXECUTE_TOOL`, ...) (`fw-composio-browseruse` Composio Copy #1). Claude Code: MCP tools NOT inlined; discovered via `ToolSearch`, only `alwaysLoad:true` inlined (`coding-claude-code` Copy #2). Codex: `ToolSearchHandler` + Code Mode V8 isolate with `ALL_TOOLS` introspection (`coding-codex` Code Mode). Cursor: MCP Tool Search cut **77K → 8.7K tokens (85%)** (`coding-cursor-zed` §4). Exa consolidated **11 tools → 2**, pushing complexity into query strings (`infra-retrieval-tools` Exa: "prefer richer query strings over more tools").

**Batched parallel tool execution with bounded workers + order preservation.**
- Composio `MULTI_EXECUTE` with `ThreadPoolExecutor(max_workers=5)` + single backend call (`fw-composio-browseruse` Composio Copy #2). Hermes: multiple tools → `ThreadPoolExecutor(max_workers=4)`, results appended in **original tool-call order regardless of completion order** + FIFO ID queue so two concurrent `read_file` calls match completions to starts (`hermes-agent-core` §3,§10). Codex: `RwLock` read-lock for parallel-safe, write-lock for exclusive (`coding-codex` Parallel tool calls). Antigravity: per-tool `waitForPreviousTools: bool` — surgical DAG-level parallelism, finer than OpenAI's per-request `parallel_tool_calls` (`coding-gemini-antigravity` Copy #2). **Bounded default = 5** (`fw-composio-browseruse` Pattern 5).

**Tool annotation bits drive permission routing for free.**
- `readOnlyHint / destructiveHint / idempotentHint / openWorldHint` (MCP spec) → `readOnlyHint:true` auto-runs, `destructiveHint:true` routes to approval gate. Used by Composio, Conductor, Grok, Turbopuffer (`multiagent-grok-heavy` Copy #5, `coding-conductor` Copy #3, `infra-vector-memory` Turbopuffer). Zero engineering cost; adopt as standard tool metadata.

**`return_direct` + the `done` tool with verification.**
- LangChain/LlamaIndex `return_direct=True` (tool output IS the final answer, no extra LLM call) — with the `handoff` exception (return_direct but doesn't terminate) showing the flag needs a `bypass_termination` sibling (`fw-langchain-langgraph` Copy #4, `infra-retrieval-tools` LlamaIndex). Browser-Use's `done(text, success)` enforces a **6-step pre-done verification checklist** to prevent premature success (`fw-composio-browseruse` Browser-Use Copy #10). MiroFish warns: **don't terminate on a sentinel string** (`"Final Answer:"` is fragile) — use a structured `done(result)` tool (`agents-products` §2).

**JSON-action ReAct as the loop contract (provider-portable + observable).**
- NIA emits `{action, args, reason}` and parses it itself with `--no-builtin-tools` — provider-agnostic (no Anthropic/OpenAI native `tool_use` blocks required), observable (`reason` on every wire event), interruptible (`research-nia-societies-mindtrip` §1, NIA + cross-cutting). CrewAI's dual-path loop auto-detects `supports_function_calling()` and falls back to ReAct-text for models without native tool calling (`fw-crewai-letta` CrewAI Copy #2) — the text path is the forever-fallback. Letta ships **GBNF grammars** for local models without native tool-calling (works on Llama 3 8B) (`fw-crewai-letta` Letta Copy #13).

### 2C. CONTEXT mechanisms

**Static/dynamic split for prompt caching (the single biggest free cost win).**
- Claude Code: system prompt split by `__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__` sentinel; static prefix gets **1h ephemeral cache**, dynamic suffix **5m** → 80-95% cost reduction on the static portion (`coding-claude-code` Copy #1). Hermes: 10-layer cached system prompt with a **memory-freeze invariant** — mid-session memory writes go to disk immediately but the model's view stays frozen so the prompt hash is stable for all N turns (`hermes-agent-core` §4 Copy #4). Browser-Use *inflates* the Anthropic-4.5 prompt to ≥4096 tokens to cross the cache threshold (`fw-composio-browseruse` Browser-Use system prompts). Codex composes the prompt from per-fragment `.md` files at turn-start (`coding-codex` Copy #1).

**Cache-aware truncation (round to a step boundary, never to the exact limit).**
- Character.AI's Prompt Poet (`pip install prompt-poet`, used verbatim in prod): truncate to the *next multiple of `truncation_step`* so the prefix stays byte-identical across turns → KV cache hits; `truncation_priority` integers (0 = never truncated) (`agents-character-deep` Copy #1,#2,#14 — "set `truncation_step` to 5-10% of token limit"). Warp's compaction replaces earlier turns *in-place* (window freed, not expanded), seeds the most-recent turn verbatim, preserves TODO+rules deterministically via a structured payload (not LLM discretion) (`coding-devin-warp` Warp compaction).

**Distilled-reflection context (O(n·m²) → O(n·m)) — the most important research-agent decision.**
- Tavily and Firecrawl independently converged: **never accumulate raw tool outputs in the iterative window; compress each iteration into short notes; reintroduce raw sources only at final synthesis** → Tavily reports **66% token reduction vs Open Deep Research at SOTA** (`infra-retrieval-tools` §1 cross-system; Tavily research agent). Firecrawl caps findings at a **50-item rolling window** (`agents-abridge-pleep-misc` Aemon/Firecrawl note; `infra-retrieval-tools` Firecrawl). Ship as a built-in `ResearchMemory(cap=50, add_finding, get_findings(max_tokens), get_sources)`.

**One-shot `read_state` channel.**
- Browser-Use: extracted content appears **once** in the next message, then is discarded — prevents "I already know that" context bloat (`fw-composio-browseruse` Browser-Use Copy #4). NIA truncates `tool_complete.result_summary` to ~250 chars on the wire while the agent gets the full result (`research-nia-societies-mindtrip` NIA context). Same pattern in Warp (`RETRIEVE_FRAGMENT_CONTEXT_LENGTH = 0` — deliberately zero context lines on retrieved fragments).

**Compaction with an anti-hallucination instruction.**
- Browser-Use compaction prompt (verbatim): *"Only mark a step as completed if you see explicit success confirmation... If started but not confirmed, mark IN-PROGRESS... Never infer completion from context."* (`fw-composio-browseruse` Browser-Use Copy #3). Conductor's verbatim 27-line compaction prompt (Task Overview / Current State / Discoveries / Next Steps / Context to Preserve) + the trick of **stripping trailing `tool_use`-only blocks before compacting** so the compactor doesn't try to "answer" the tool call (`coding-conductor` Copy #6). Compaction at **100K tokens counting input+cache_creation+cache_read+output** (cached tokens still occupy the window) (`coding-conductor` Copy #9).

**Mixin-based prompt assembly with budget-conditional fallback.**
- Antigravity: the prompt is a topologically-ordered set of mixins each with `ShouldInclude(ctx)`, `Content()`, `DynamicContent(budget_constrained)`, `TokenType()` — falls back to the compressed `DynamicContent` when over-budget instead of hard-failing (`coding-gemini-antigravity` Copy #4). Cursor/Zed both independently ship **Handlebars-conditional prompts** gated on active tools (`{{#if (contains available_tools 'spawn_agent')}}`) — the model sees only instructions for tools it actually has (`coding-cursor-zed` Copy #2). Warp assembles the prompt from a **capability bitmap**, not a hardcoded string, which is what lets feature-flagged tools appear without prompt rewrites (`coding-devin-warp` Warp Copy).

**Project-context file hierarchy (AGENTS.md walk).**
- Codex/Warp/Hermes/Cursor all walk up from cwd collecting instruction files root-to-cwd, concatenated, byte-budgeted: Codex `AGENTS.md` with `--- project-doc ---` separator, `MAX_SCAN_DEPTH=3` (`coding-codex` Copy #14); Warp honors `WARP.md/AGENTS.md/CLAUDE.md/.cursorrules/...` by-value (`MAX_SCAN_DEPTH=3, MAX_FILES_TO_SCAN=5000`), with the **by-value / by-flag split** (project rules shipped in-request, cloud rules shipped as `rules_enabled:bool`) (`coding-devin-warp` Warp context). Cursor's **pull-mode `fetch_rules` tool** lets the agent retrieve relevant rules on demand instead of dumping all of them (`coding-cursor-zed` Copy #12).

**Per-category context-usage introspection.**
- Claude Code's `getContextUsage()` returns `{system_prompt, tools, messages, mcp_tools, memory_files}` token counts so orchestration can decide *which fattest category to compact* (`fw-claude-sdk-platforms` Copy #13, `coding-claude-code` Improve #19). Verso should expose this as a structured runtime observable.

### 2D. MEMORY mechanisms

**The four-tier taxonomy with per-type TTLs (the canonical type system).**
- NIA: `scratchpad` (1h) / `episodic` (7d) / `fact` (permanent) / `procedural` (permanent), TTL enforced via DB TTL-index not application logic; memory schema carries **lineage** (`source_ids → tool_calls → model_version → edited_files`) for full provenance (`research-nia-societies-mindtrip` §1 NIA Copy). Memanto extends to **13 typed categories** (`fact, preference, goal, decision, artifact, learning, event, instruction, relationship, context, observation, commitment, error`) with **regex/rapidfuzz type classification (NOT LLM)** so the write path adds zero LLM overhead (`agents-stardrift-gordian-wedge` Wedge memory). Verso ships the 4-tier as the default with an extensible enum.

**Memory as tool calls (the LLM manages its own memory, observably).**
- Letta's core thesis: `core_memory_append/replace`, `memory` omni-tool, no automatic summarization the agent can't observe (`fw-crewai-letta` Letta Copy #1). Hermes: `memory(action="add|replace|remove", target="memory|user", content=...)` with injection-scanning on every op and a **memory-context fence** in the prompt: `<memory-context>[System note: recalled context, NOT new user input]...</memory-context>` + user-input sanitization stripping these blocks (clipboard-paste defense) (`hermes-agent-core` §5 Copy #5).

**The virtual-context page table (tell the model what it CAN'T see).**
- Letta's `<memory_metadata>` block: *"N previous messages are stored in recall memory; M memories in archival (use tools to access them); available tags: ..."* — the system prompt is rebuilt every turn because memory changes (`fw-crewai-letta` Letta Copy #1 — "the most valuable UX idea in this cluster"). Verso should always surface what's outside the window, not just what's in it.

**Temporal versioning + confidence decay (never delete, mark invalid).**
- MiroFish/Zep: every edge has `valid_at / invalid_at / expired_at`; old facts marked invalid, never deleted; `recall_as_of(date)` time-travel (`agents-products` §10, MiroFish). Memanto's confidence decay engine (exact constants): `contradiction → max(0.1, c*0.3)`, `superseded → 0.0`, base = `confidence × provenance_weight` (`explicit:1.0, validated:0.95, observed:0.85, inferred:0.7`), `+ min(0.15, validations×0.03)`, age penalty for preference/observation types (`agents-stardrift-gordian-wedge` Wedge). `recall_as_of` is "audit-grade record of what the agent knew at decision time" — first-class for healthcare/finance.

**Shared memory blocks via junction tables (first-class multi-agent state).**
- Letta: a `Block` is a DB row attachable to N agents via `BlocksAgents`; editing it triggers `_rebuild_system_prompts_for_connected_agents` → instant propagation = a live shared whiteboard (`fw-crewai-letta` Letta Copy #12). This beats copying memory into each agent's context.

**Sleep-time / background consolidation agents.**
- Letta's `SleeptimeMultiAgentV4` fires after each main run, reads recent messages, rewrites core memory, archives older content — active curation not passive accumulation, gated by trigger-steps/probability for cost (`fw-crewai-letta` Letta Copy #6). Claude Code's `autoDream` (≥24h AND ≥5 sessions AND lock): Orient→Curate→Consolidate→Prune/Index (`coding-claude-code` KAIROS). Antigravity's **KNOWLEDGE SUBAGENT** fires on `stop_hook`, distills conversations into KI files with a restricted toolset (read-everywhere, write-only-in-allowlist) (`coding-gemini-antigravity` Copy #7). Hermes' **two-tier self-improvement** (per-session review every N turns + 7-day library curator) is the deepest version — "class-first generalization" prompt, "archive never delete" invariant, idle gate (`hermes-agent-core` §7). Verso ships hooks (`on_turn_complete`, `on_idle`) that *let* users build this, plus a built-in consolidation primitive.

**Bounded memory creates quality.**
- Cross-cutting finding (`fw-claude-sdk-platforms` Pattern 1): Hermes hard-caps MEMORY.md=2200 / USER.md=1375 chars forcing consolidation; Dust uses `cat` with `offset/limit/grep`; Claude SDK gates on `getContextUsage`. *"Unconstrained context is noise. Bounded + curated memory is signal."* Verso's memory module should not ship without a configurable budget policy.

**Typed-entity RAG beats raw chunking.**
- Pleep: docs → typed entities in 6 categories (Products/Q&A/Procedures/Contacts/Context/Other), category-filtered retrieval *before* similarity search → 99.87% factual accuracy vs ~91.8% raw-chunk (`agents-products` §4 Pleep, `agents-abridge-pleep-misc` Copy #4). Mid-conversation re-retrieval as a callable tool (single-pass RAG is the baseline not the goal). Verso memory: `TypedKnowledgeBase` with category indexes + a `retrieve(query, context)` tool callable at any point.

**Pin/memo (always-include) items survive truncation.**
- Character.AI's `is_pinned` turns surface on every generation regardless of dialog length; `TooManyPins` quota (`agents-character-deep` Layer 3, `agents-products` §11). Verso memory entries get an `always_include: bool` with an optional quota.

---

## 3. Model-ROUTING + retrieval + vector-memory infra lessons for Verso's provider/memory layers

### 3A. Provider / routing layer

**Sit above a thin provider abstraction; never re-implement it.** (`infra-model-routing` Verso implications #1)
- The correct shape is the 4-method `Config` pattern: `get_supported_openai_params` + `map_openai_params` + `transform_request` + `transform_response`, **OpenAI shape as canonical, every other provider a translation** (`infra-model-routing` LiteLLM). Hermes proves the declarative version: a single `ProviderProfile` dataclass with 5 polymorphic hooks (`get_hostname`, `prepare_messages`, `build_extra_body`, `build_api_kwargs_extras`, `fetch_models`) + the `OMIT_TEMPERATURE = object()` three-state sentinel (use-default / strip-field / override) — replaces a forest of `if provider == 'kimi'` branches (`hermes-surfaces` §1 Copy). **Plugin discovery with zero-touch override** (`~/.verso/plugins/model-providers/<name>/__init__.py` last-writer-wins, failure-isolated) is the right extensibility model.

**Routing is per-node config, not a global setting.** (`infra-model-routing` #2)
- OpenRouter's `ProviderPreferences` is the control surface to copy: `require_parameters:true` (CRITICAL for agents — a fallback provider silently dropping `tools` returns text instead of a tool call, breaking the loop with no error), `data_collection:"deny"`, `max_price` (hard limit, 503 if unmet) vs `preferred_max_latency` (soft), `sort: price|throughput|latency`, `allow_fallbacks:false` for critics (cross-family evaluation is uncalibrated) (`infra-model-routing` OpenRouter Copy). Per-role configs: Orchestrator pins Anthropic for cache-warm + `data_collection:deny`; Tool-Executor uses throughput-sort + hard price cap; Critic uses `allow_fallbacks:false`.

**Cheap-primary → expensive-retry + role-tiered models (universal across research agents).**
- Firecrawl: gpt-4o-mini first, gpt-4.1 on failure; **o3-mini ONLY for final synthesis**; planner (Gemini 2.5 Pro, `toolChoice:required`) + executor (Gemini 2.0 Flash, 10× cheaper) (`infra-retrieval-tools` Firecrawl Copy). The cross-system taxonomy (`infra-retrieval-tools` §4): `loop_model` (cheap, iterative) + `retry_model` (mid) + `synthesis_model` (reasoning, final only) — **never default to the reasoning tier for all steps**. Anthropic Research: Opus lead (standard speed) + Sonnet workers (fast speed) — "concentrate intelligence where coordination happens, distribute compute where search happens" (`research-deepresearch` §10,§11). Hermes' first-class **`AuxiliaryClient`** for compression/curation/review keeps the primary's prompt cache intact (`hermes-agent-core` §2 Copy).

**Reasoning-effort dial as a first-class knob, with multi-turn continuity.**
- Effort→token mapping is the right abstraction (Claude Code `low/medium/high/xhigh/max`, OpenRouter `xhigh:95% / high:80% / medium:50% / low:20%`) — "effort levels are meaningful to users; raw token counts are not" (`coding-claude-code` Improve #21, `infra-model-routing` OpenRouter). **Pass `reasoning_details` back across turns** — reasoning models lose coherence otherwise; auto-drop `thinking` blocks when the previous assistant turn has none (Anthropic rejects the mismatch) (`infra-model-routing` LiteLLM Copy, #10). Grok/LlamaIndex/Hermes all stream `reasoning_content` as a **separate channel** from `content` (`multiagent-grok-heavy` Copy #8, `infra-retrieval-tools` LlamaIndex, `hermes-surfaces` §1.5).

**Cache-sticky routing overrides the load balancer.** (`infra-model-routing` #11)
- Once a provider warms the cache for a conversation, pin subsequent turns to it — explicit exception to cost/throughput optimization. Character.AI's L4 sticky-session-per-`chat_id` is the prerequisite for any KV-prefix-cache strategy (`agents-character-deep` Copy #8).

**Mid-stream errors are invisible to HTTP status — parse the chunk.** (`infra-serving` shared, `infra-model-routing` #8)
- All serving systems send HTTP 200 before the first token; mid-stream errors arrive as a chunk with `finish_reason:"error"` + `error` object. vLLM pairs this with an out-of-band watchdog. Verso's streaming consumer must classify errors chunk-by-chunk, never on status. OpenRouter's **Zero Completion Insurance** (0 completion tokens + blank finish_reason → retry immediately, transient) is a real failure mode to handle.

**Tool-name sanitization with forward/reverse maps.** (`infra-model-routing` LiteLLM Copy)
- Anthropic rejects `/` and `.` in tool names; sanitize to `_` before sending and reverse-map on response so names round-trip. Verso's tool executor must do this transparently.

**`max_iterations_limiter` per session is the non-negotiable safety rail.** (`infra-model-routing` LiteLLM Copy)
- LiteLLM caps total LLM calls per `metadata.session_id`; `dynamic_rate_limiter` self-tunes the RPM cap when it sees 429s. Verso exposes `max_llm_calls` per run, enforced in the durable execution layer.

### 3B. Retrieval layer

**RRF (k=60) as the default hybrid reranker — everywhere.**
- LanceDB ships RRF (k=60) as its *only* built-in reranker (scale-invariant, no training, near-optimal per the 2009 paper) (`infra-vector-memory` LanceDB Copy #8). LangChain `EnsembleRetriever.c=60` (`fw-langchain-langgraph` Copy #10). Exa, Perplexity, Grok `collections_search`, OpenAI DR `file_search` all use RRF fusion (`research-deepresearch`, `multiagent-grok-heavy`, `research-perplexity`). Default it; allow pluggable `Reranker`.

**Unified single-query hybrid (rank_by algebra) over two-pass merge.**
- Turbopuffer runs BM25 + ANN inside the *same* vectorized MAXSCORE engine with `rank_by: ['Sum', [['Product', 0.7, ANN], ['Product', 0.3, BM25]]]` — one query, no round-trip — vs LanceDB's two-pass FTS+vector then RRF (`infra-vector-memory` Cross-system, Avoid #3). Prefer the unified approach when both are needed. Verso could ship a `HybridSearch` tool type with a declarative `rank_by` DSL and pluggable backends (`infra-vector-memory` Improve #4).

**Asymmetric embedding (source ≠ query).** (`infra-vector-memory` LanceDB Copy #7)
- LanceDB separates `compute_source_embeddings` from `compute_query_embeddings` (E5/BGE prefixes differ). Collapsing them silently degrades retrieval for asymmetric models. Verso memory must preserve the distinction.

**Tunable per-corpus BM25.** (`infra-vector-memory` Avoid #2)
- Turbopuffer exposes `k1/b` per-namespace; LanceDB hardcodes `K1=1.2, B=0.75`. Different corpora (code/prose/logs) have different optima — make them tunable per collection.

**Two-tool MCP retrieval shape + stateless sandbox.** (`infra-vector-memory` Turbopuffer Copy #1,#2)
- Turbopuffer's MCP server exposes exactly two tools: `execute` (mutating) + `search_docs` (`readOnlyHint:true`). "Variables do not persist between calls" — tools are stateless; cross-call state flows through Verso's memory layer, never tool-side globals.

**Highlights / query-biased passage extraction is the token-efficiency moat.** (`research-deepresearch` Exa, `infra-retrieval-tools` Exa)
- Exa: "500 chars of highlights match the accuracy of the first 8000 chars of page, 16× fewer tokens." This is what makes agentic search economically viable. Web-fetch should return query-biased highlights, not full pages.

**The URL gate (web_fetch only fetches seen URLs) — safety AND correctness.** (`research-deepresearch` §12)
- Anthropic enforces at API + prompt layer: `web_fetch` can ONLY fetch URLs returned by prior search/fetch results → structural SSRF/hallucination defense. Surface `paywall | unsafe | error` as typed result statuses (Gemini DR) the agent routes on.

### 3C. Vector-memory / serving infra

**OCC retry loop with adaptive slot-backoff for concurrent memory writes.** (`infra-vector-memory` LanceDB Copy #5)
- Lance's `execute_with_retry`: execute *separately* from commit, retry on conflict by *re-executing against latest state* (not just re-committing); `SlotBackoff` unit adapts to actual operation duration (`unit = first_attempt_elapsed × 1.1`, slots = `2^(N+2)`) so retriers are statistically uncorrelated. `max_retries=10, retry_timeout=30s`. Use for concurrent agent writes to shared memory.

**Three-level prefixed cache hierarchy + e_tag invalidation.** (`infra-vector-memory` LanceDB Copy #6)
- Lance's `Global → Dataset → File` prefix chain maps to Verso's `Global → Session → Task`. Two agents sharing a `Session` share cache; e_tag invalidation prevents stale state. `DualCache` (in-memory short TTL + Redis long TTL) is the right primitive (`infra-model-routing` LiteLLM Copy), with **model-group cache key collapse** so deployments behind one logical model share hits.

**Pluggable memory backend, no hard DB pin.** (`fw-crewai-letta` Letta Avoid #2, `agents-products` §5 MiroFish GraphStorage)
- Letta's mandatory Postgres+pgvector is the anti-pattern. SQLite+sqlite-vec for dev, Postgres+pgvector for prod, mem0/Zep/Memanto adapters. MiroFish's `GraphStorage` abstract interface (Zep Cloud → Neo4j → anything) is the right layering. Lance's `ManifestNamespace` (catalog-as-table, no external catalog service) shows session/memory metadata can be self-contained in the same store (`infra-vector-memory` LanceDB Copy #11).

**Serving lessons (only if Verso runs a gateway).** (`infra-serving` §→Verso)
- One engine + N protocol adapters (OpenAI Chat / Anthropic Messages / custom) — never duplicate the engine per dialect. `@with_cancellation` two-task race (`asyncio.wait(FIRST_COMPLETED)` vs disconnect listener) — `request.is_disconnected()` is broken under ASGI middleware. Out-of-band watchdog (≥5s) for dead-engine detection. Pure-ASGI middleware for auth (constant-time SHA-256) + request-id — `BaseHTTPMiddleware` buffers streams and breaks SSE (confirmed by Letta's `RequestIdMiddleware` finding too, `fw-crewai-letta` Letta Copy #10). `gc.freeze()` before serving. Budget enforcement per scheduler step, not just at admission. Three-state health: `ready | busy | unavailable`.

---

## 4. Concrete anti-patterns to avoid (each tied to its source)

1. **A universal composition abstraction (LCEL).** 15+ `Runnable` classes of mandatory indirection inflate the mental model; the 700-integration moat is what justifies it — without that, it's pure indirection. *Python callables compose with Python.* (`fw-langchain-langgraph` Avoid #21)

2. **Pregel/BSP as the default execution model.** "Channels have reducers and writes are invisible until end of step" is not the intuition developers bring. Clean ReAct default; Pregel-style scheduling only as an opt-in escape hatch for legitimate fan-out. (`fw-langchain-langgraph` Avoid #28)

3. **Misleading constants.** LangGraph's `DEFAULT_RECURSION_LIMIT=10007` while docs say 25. Pick one sensible default (25-50) and make it visible. Codex's implicit max-iterations of zero can runaway on broken tool calls — have an explicit `max_iterations` that defaults to `None` but is trivial to set. (`fw-langchain-langgraph` Avoid #29, `coding-codex` Avoid #4)

4. **Two execution models / two agent stacks in one repo.** LangChain v0 `AgentExecutor` + v1 `create_agent`; CrewAI `Crew` + `Flow`; Claude Code subagents + experimental teams. One agent loop from day one; multi-agent is configuration of the same loop, not a parallel system. (`fw-langchain-langgraph` Avoid #26, `fw-crewai-letta` CrewAI Avoid #1, `coding-claude-code` Avoid #17)

5. **Streaming = run-in-thread + tail-event-bus.** CrewAI spawns a thread that flips `self.stream=False` and tails the event bus — not real streaming. The loop must be async-native and emit SSE directly. (`fw-crewai-letta` CrewAI Avoid #2)

6. **Hard runtime exceptions for config errors.** CrewAI's `raise Exception("Manager agent should not have tools")`. Validate at construction time with a typed error. (`fw-crewai-letta` CrewAI Avoid #3)

7. **Blocking HITL via `input()` / non-durable interrupts.** CrewAI's `human_input=True` blocks on `input()`, not resumable across processes. Use durable interrupt-via-exception with checkpoint-before-raise (LangGraph `interrupt()`), or higher-level `await context.hitl.request(question)`. (`fw-crewai-letta` CrewAI Avoid #4, `fw-langchain-langgraph` Copy #19/Improve #37)

8. **Monolith agent class.** Letta's `letta_agent_v3.py` = 2,134 lines; Hermes' loop body = 3,600 lines; agent_manager.py = 3,599 lines. Decompose: loop / dispatcher / prompt-builder / error-classifier as separate <300-line components. (`fw-crewai-letta` Letta Avoid #1, `hermes-agent-core` §1 Improve)

9. **Anthropic-only (or any single-vendor) model routing.** The Claude Agent SDK's biggest limitation. Abstract over providers from day one. (`fw-claude-sdk-platforms` Avoid #2)

10. **Subprocess-delegated loop for a general framework.** Works for Anthropic (owns SDK + binary); fatal for a framework whose users must inspect and extend the loop. (`fw-claude-sdk-platforms` Avoid #1)

11. **MCP for *internal* tool orchestration at scale.** Denis Yarats (Perplexity): "MCP tool definitions consume context window tokens — every schema eats working memory." MCP for *external* connectors; direct registry+name reference for internal built-ins. (`research-perplexity` §5, AVOID)

12. **Inverting streaming delta semantics across endpoints.** Perplexity's fatal DX bug: `/v1/responses` is true-delta, `/v1/chat/completions` is cumulative — opposite of OpenAI. Pick ONE convention globally, document it loudly. (True-delta is the right choice: consumers can buffer, senders can't un-accumulate.) (`research-perplexity` §10)

13. **Convergence-based termination for multi-agent.** Grok explicitly has NO convergence metric — termination is `turns ∧ time ∧ tokens`, purely resource-bound. "Loop until agents agree" never converges on hard problems and is impossible to tune. (`multiagent-grok-heavy` Avoid #1)

14. **A separate orchestrator + judge as extra model calls.** Grok's leader IS one of the N agents and IS the synthesizer — no extra aggregation model. (`multiagent-grok-heavy` Avoid #2)

15. **Nested orchestrators / unbounded subagent nesting.** Claude Code hard-bans nesting; Anthropic Research depth-limit=1; Codex `max_depth=1`. Exponential token cost. Verso: configurable depth, conservative default (1). (`fw-claude-sdk-platforms` Avoid #5, `research-deepresearch` Avoid, `coding-claude-code` Avoid #14)

16. **Unbounded grader/eval loops.** The cookbook evaluator-optimizer's `while True` is a production bug. Anthropic's `define_outcome` is bounded default-3/max-20. Verso's grader MUST require `max_iterations`. (`research-deepresearch` §7)

17. **Building a source-quality scoring tool.** Anthropic shipped `evaluate_source_quality`, it broke in production, they patched it out at the *prompt* layer mid-flight (sessions in progress). Bake source heuristics into the prompt instead. (`research-deepresearch` Claude Research Avoid)

18. **Letting subagents write the final report.** Hard architectural boundary: orchestrator synthesizes, workers research. (`research-deepresearch` Avoid)

19. **Terminating on a sentinel string.** MiroFish's `"Final Answer:" in response` breaks on rephrasing. Use a structured `done(result)` tool. (`agents-products` §2)

20. **Filesystem JSON polling as IPC.** MiroFish's `commands/`/`responses/` dirs break under concurrency. Use Redis Streams / asyncio / NATS with structured schemas. (`agents-products` §20)

21. **Hiding the system prompt / promptless black box.** Pleep generates prompts the user never sees; Composio generates assistive prompts server-side. Advanced users always want to inspect/override. Expose `agent.instructions` as readable/editable. (`agents-products` Pleep Avoid, `fw-composio-browseruse` Composio Avoid #3)

22. **70-argument constructors / 60-param agents / 64-method APIs grown organically.** Browser-Use's ~70-kwarg `Agent.__init__`; Hermes' 60-param constructor; Hermes TUI's 64 overlapping methods. Use typed nested config objects (`CompactionSettings`, `ModelSlots`, `DelegationPolicy`); define a minimal 15-20 method API upfront. (`fw-composio-browseruse` Browser-Use Avoid #1, `hermes-agent-core` Avoid #1, `hermes-surfaces` §C Avoid)

23. **The dead-zone confidence bug.** Wedge's `[0.70, 0.85)`-clean band is neither applied, reviewed, nor logged — silently dropped. Any confidence router must cover the full `[0,1]` range with no gaps. (`agents-stardrift-gordian-wedge` §4)

24. **Vendor count > 12 in the critical path.** 11x stacked 30+ vendors → `0.999^12 ≈ 98.8%` per run, >30%/month failure probability. MCP standardization is exactly the swap-any-tool abstraction that fixes this; ship a "complexity budget" concept. (`agents-products` 11x, §18)

25. **`request.is_disconnected()` / `BaseHTTPMiddleware` in streaming paths.** Both broken under ASGI middleware (vLLM + Letta both hit this). Use the two-task cancellation race + pure-ASGI middleware. (`infra-serving` vLLM Avoid, `fw-crewai-letta` Letta §streaming)

26. **15-model-type proliferation.** Character.AI's 15 internal routing slots → maintenance burden + "the model used may vary" confusion. Route by capability class (fast/balanced/smart) + one `dynamic` auto-route. (`agents-character-deep` Avoid #9)

27. **ContextVar-based implicit config propagation; callback-manager-as-only-observability.** LangChain's `var_child_runnable_config` and 15-method `BaseCallbackHandler` tree are opaque and hard to debug. Use explicit typed `RunContext` injection + a structured event bus. (`fw-langchain-langgraph` Avoid #23,#27)

---

## 5. First-cut Verso architecture sketch (modules + public API surface)

The synthesis implies a small set of composable modules. Everything below is **synthesized from the teardowns** — each module names the notes that shaped it.

### 5.1 Module map

```
verso/
├── core/
│   ├── loop.py          # <200-line async ReAct loop. continue iff !cancelled.
│   │                    #   named StopReason. grace call on budget. mode-gate opt-in.
│   │                    #   (coding-devin-warp, coding-codex, fw-langchain-langgraph,
│   │                    #    coding-gemini-antigravity, hermes-agent-core §1)
│   ├── context.py       # RunContext[ContextT]: typed, injected into every handler.
│   │                    #   context.budget.{remaining,is_last_step}, context.emit(event),
│   │                    #   context.hitl.request(q), context.usage_by_category()
│   │                    #   (fw-langchain-langgraph #16,#17,#38; fw-claude-sdk #13)
│   └── result.py        # AgentResult(output, stop_reason: StopReason, usage: UsageStats,
│                        #   cost_usd, trace_id)  (fw-crewai-letta #3, multiagent-grok #9)
│
├── model/
│   ├── profile.py       # ProviderProfile dataclass + 5 hooks + OMIT sentinel.
│   │                    #   plugin discovery, zero-touch override.  (hermes-surfaces §1)
│   ├── router.py        # per-node ModelPolicy: {provider_order, require_parameters,
│   │                    #   data_collection, max_price, sort, quantizations}.
│   │                    #   heterogeneous + error-typed failover chain.
│   │                    #   reasoning effort dial. cache-sticky override.
│   │                    #   (infra-model-routing OpenRouter+LiteLLM, coding-devin-warp)
│   ├── adapter.py       # 1 internal request shape → N dialect adapters (OpenAI canonical).
│   │                    #   reasoning_content as a first-class field. tool-name sanitize.
│   │                    #   (infra-serving, infra-model-routing, hermes-surfaces §1.3)
│   └── auxiliary.py     # AuxiliaryClient(role=compression|review|classify|judge) —
│                        #   cheap side-model, never touches primary prompt cache.
│                        #   (hermes-agent-core §2)
│
├── tools/
│   ├── registry.py      # import-time self-register w/ check_fn gate + max_result_chars
│   │                    #   + kind taxonomy + annotation bits (readOnly/destructive/...).
│   │                    #   (hermes-agent-core §3, multiagent-grok #5, agents-character-deep)
│   ├── dispatch.py      # universal dispatch: coerce args, ALWAYS {data,error,successful},
│   │                    #   4-stage input-repair ladder, fuzzy-name (0.85), repeated-call
│   │                    #   short-circuit, truncate, bounded-parallel (5) w/ order preserve
│   │                    #   + FIFO id queue.  (fw-crewai-letta, fw-composio, hermes §3,§10)
│   ├── mcp.py           # MCP client (stdio+HTTP) + server (every Verso agent is both).
│   │                    #   deferred loading via tool_search. sampling callback.
│   │                    #   (coding-codex, fw-composio Pattern 2, coding-claude-code #2)
│   ├── meta.py          # VersoSearch + VersoMultiExecute built-ins (O(N)→O(1) schemas).
│   │                    #   (fw-composio Composio Copy #1,#2)
│   ├── rules.py         # optional ToolRule solver (Init/Terminal/Continue/Child/Approval).
│   │                    #   (fw-crewai-letta Letta Copy #2)
│   └── builtins.py      # think (no-op CoT sentinel), done (with verification checklist).
│                        #   ZERO opinionated domain tools.  (research-nia §1, fw-composio #10,
│                        #    hermes-agent-core Avoid #5: "ship 0 built-in tools")
│
├── memory/
│   ├── store.py         # unified Memory: short(channel) + long(vector+KV) + compaction.
│   │                    #   4-tier type enum (scratchpad/episodic/fact/procedural, extensible
│   │                    #   to 13). per-type TTL via DB index. memory-freeze invariant.
│   │                    #   (research-nia §1, fw-langchain #36, hermes-agent-core §4,§5)
│   ├── temporal.py      # valid_at/invalid_at/expired_at, never-delete, confidence decay,
│   │                    #   recall_as_of(date).  (agents-products §10, agents-stardrift Wedge)
│   ├── backend.py       # pluggable: sqlite-vec (dev) / pgvector (prod) / Zep/Mem0/Memanto.
│   │                    #   GraphStorage-style abstract iface.  (agents-products §5, infra-vector)
│   ├── retrieval.py     # RRF k=60 default + pluggable Reranker. asymmetric embed.
│   │                    #   typed-entity category-filtered RAG. unified rank_by DSL.
│   │                    #   (infra-vector-memory, agents-products §4)
│   ├── compaction.py    # CompactionPolicy presets (conservative/aggressive/custom).
│   │                    #   protect-first-N/last-N, tool-pair integrity, anti-hallucination
│   │                    #   prompt, strip-trailing-tool_use, cache-aware truncation_step.
│   │                    #   (hermes §4, coding-conductor #6, agents-character-deep #1)
│   └── research.py      # ResearchMemory(cap=50): distilled-reflection rolling buffer.
│                        #   (infra-retrieval-tools §1, infra-retrieval Firecrawl/Tavily)
│
├── stream/
│   ├── events.py        # ONE structured event stream (astream_events-v2 shape):
│   │                    #   {event,name,run_id,parent_ids,tags,metadata,data}. filters not
│   │                    #   separate modes. reasoning_content as separate channel. goal field.
│   │                    #   (fw-langchain #9,#34, multiagent-grok #8, research-deepresearch §4)
│   ├── transport.py     # resumable: seq_id per frame, Redis-stream cursor replay,
│   │                    #   reconnect endpoint w/ starting_after, decoupled worker.
│   │                    #   belt-and-suspenders [DONE]. status_snapshot for long reconnect.
│   │                    #   (fw-crewai-letta Letta, agents-stardrift Stardrift, research-nia Mindtrip)
│   └── runs.py          # background job control plane: POST→{id,queued}; GET/{id};
│                        #   GET/{id}/stream?starting_after=N; webhook terminal; DELETE cancel.
│                        #   (research-deepresearch §3, multiagent-grok DeferredCompletion)
│
├── orchestrate/         # OPT-IN. default is single agent.
│   ├── delegate.py      # spawn subagent: leaf|orchestrator role, depth cap (default 1),
│   │                    #   DELEGATE_BLOCKED_TOOLS, child isolation (no parent history),
│   │                    #   async-mailbox (send_message→reactive wakeup, NOT poll).
│   │                    #   (hermes-agent-core §9, coding-gemini-antigravity #3, research-deepresearch §1)
│   ├── patterns.py      # depth-loop (single, long-ctx) | orchestration-loop (lead+workers,
│   │                    #   parallel, leader-only render, continuous-injection merge) |
│   │                    #   plan-execute (explicit task list + parallel workers).
│   │                    #   (research-deepresearch §1, multiagent-grok #2,#3, research-perplexity Computer)
│   └── graph.py         # escape hatch: Send-fan-out + Command-routing for legit map-reduce.
│                        #   (fw-langchain-langgraph dynamic routing)
│
├── evals/               # FIRST-CLASS, not an add-on.
│   ├── judge.py         # 3-judge panel default (Sonnet 0.4 / GPT 0.4 / Gemini 0.2,
│   │                    #   pointwise, 1-5, 0.7 threshold). post-hoc, NEVER in hot path.
│   │                    #   (agents-character-deep #4, fw-composio Browser-Use #7)
│   ├── outcome.py       # define_outcome(rubric, max_iterations REQUIRED) generate→grade→
│   │                    #   revise loop. advisor (inline mini-judge). bBoN (best-of-N).
│   │                    #   (research-deepresearch §7, fw-claude-sdk Agent-S3)
│   ├── feedback.py      # FeedbackToEval: feedback→checklist→dedup(0.85)→enforceability(0.70)
│   │                    #   →coverage-diversity(α=0.5,λ=0.0005). generate_from_session.
│   │                    #   (agents-abridge-pleep-misc Abridge, research-nia Mindtrip §5)
│   └── verify.py        # verify_grounding flag: claims grounded in retrieved content +
│                        #   provenance trail (source span per claim).  (agents-products §16,
│                        #    agents-abridge-pleep-misc Copy #12)
│
├── hooks/               # 5-stage lifecycle, declarative + callable.
│   │                    # pre_model/post_model/wrap_model_call/pre_tool/post_tool/wrap_tool_call
│   │                    # /on_turn_complete/on_idle/stop. updatedInput + updatedToolOutput.
│   │                    # 4-value permission decision allow|deny|ask|defer. async hooks.
│   │                    # (fw-langchain middleware, fw-claude-sdk hooks, coding-gemini #5)
│
├── safety/
│   ├── permissions.py   # composable policy layers (tool_call,ctx)→allow|deny|ask|defer,
│   │                    #   priority-ordered, provenance-tracked. session-level
│   │                    #   allow_all|ask_every_call|ask_once_per_session + per-tool override.
│   │                    #   (coding-claude-code #7, fw-composio Composio #7, fw-claude-sdk Pattern 4)
│   ├── confidence.py    # ConfidenceRouter(high=0.85,review=0.70,discard=0.40) — full [0,1]
│   │                    #   coverage (no dead zone). review queue w/ approve/reject/correct.
│   │                    #   append-only audit log.  (agents-stardrift Wedge §4)
│   └── tool_middleware.py # async post-tool scanner (BrowseSafe pattern): runs concurrent
│                          #   w/ LLM planning, REPLACES (not flags) injected content.
│                          #   (research-perplexity BrowseSafe)
│
└── persist/
    ├── session.py       # session run-generation counter (drop stale callbacks), agent cache
    │                    #   keyed by config signature (preserve prompt cache), resumable.
    │                    #   (hermes-agent-core §13)
    └── checkpoint.py    # durability sync|async|exit. git-worktree isolation for parallel
                         #   agents. checkpoint-bracket every turn. S3-snapshot pause/resume.
                         #   (fw-langchain #12, coding-conductor #10,#11, research-perplexity §12)
```

### 5.2 Public API surface (the shape users actually touch)

```python
# --- the 90% path: one agent, a few tools, async ---
from verso import Agent, tool, init_model

@tool  # docstring + type hints → schema; InjectedContext/InjectedStore filtered from LLM
async def get_weather(city: str, ctx: InjectedContext) -> dict:
    ...  # raise freely — framework wraps to {data,error,successful}

agent = Agent(
    model=init_model("anthropic:claude-sonnet-4-6"),  # "provider:model" (fw-langchain #8)
    tools=[get_weather],                               # or mcp_servers=[...]
    instructions="You are ...",                        # readable/editable, never hidden
    memory=Memory.default(),                           # 4-tier, sqlite-vec dev backend
    max_steps=25,                                      # visible default, not 10007
    model_policy=ModelPolicy(require_parameters=True,  # CRITICAL for tool agents
                             fallback=["openai:gpt-5.1", "google:gemini-3-pro"]),
)

result = await agent.run("weather in Paris?")
# result.output, result.stop_reason (StopReason enum), result.usage, result.cost_usd

async for ev in agent.stream("..."):     # one structured event stream
    ...  # ev.type in {message.delta, reasoning.delta, tool.start, tool.result, ...}

# --- resumable / long-running ---
handle = await agent.submit("deep task", background=True)   # → {id, status:queued}
async for ev in agent.attach(handle.id, starting_after=last_seq):  # reconnect-safe
    ...

# --- effort / verbosity / mode knobs ---
await agent.run("...", effort="high", verbosity="quick", mode="plan")

# --- memory as tool-callable + typed ---
await agent.memory.remember(type="fact", content="...", confidence=0.9)
await agent.memory.recall(query="...", types=["fact","preference"], scope="user")
await agent.memory.recall_as_of(query="...", date=...)   # audit-grade

# --- evals first-class ---
suite = Evals.from_sessions(agent, last_n=50)            # generate_from_session
await agent.run("...", judge=JudgePanel.default())        # post-hoc, not gating
agent.define_outcome(rubric="...", max_iterations=3)      # generate→grade→revise (bounded)

# --- HITL, durable, invisible to node author ---
answer = await ctx.hitl.request("Approve sending this email?")  # checkpoint-backed pause

# --- opt-in multi-agent (NOT the default) ---
team = Orchestration(lead=agent, workers=[a, b, c],
                     pattern="orchestration",           # leader-only render
                     merge="continuous_injection")       # not collect-and-reduce

# --- hooks (declarative or callable) ---
@agent.hook("pre_tool")
async def gate(req, ctx): return PermissionResult.ask if req.tool.destructive else ...

# --- config-file path for simple stateless agents ---
agent = Agent.from_yaml("agent.yaml")   # name, model, prompt, tool decls (Retell pattern)

# --- every Verso agent is an MCP server with one tool, automatically ---
mcp_app = agent.as_mcp_server()          # composable into any MCP ecosystem
```

**Design invariants baked into the surface:**
- `result.stop_reason` is *always* a named enum; "done" is never a bare string.
- Tool functions raise freely; the framework never lets an exception reach the loop.
- One model-id string format (`provider:model`); one streaming-delta convention (true-delta) globally.
- Memory is one object with typed entries; routing is per-node config; MCP is the primary tool path.
- Single agent is the default; orchestration is an explicit, separate import.
- Evals, resumable streaming, durable HITL, and confidence-gating are *in the box*, not bolted on.

---

## 6. Open decisions for the brainstorm

These are the genuine forks where the teardowns give evidence on both sides. Each needs a Verso call.

1. **Loop default: max_steps cap or pure budget?**
   Codex/Warp run with no iteration cap (only token budget + cancel). MiroFish/LlamaIndex/Perplexity hard-cap. *Tension:* unbounded is "let the model decide" but runaway-prone on broken tool calls (`coding-codex` Avoid #4). **Proposal:** ship `max_steps=25` visible default + token-budget as the real safety net + grace call. Brainstorm whether the default should be `None`.

2. **Pydantic dependency: require v2, or accept plain dict/TypedDict?**
   LangChain's v1/v2 dual-support is "a permanent source of subtle bugs" (`fw-langchain-langgraph` Avoid #22). Pydantic v2-only is ergonomic but a heavy dep. Plain-dict/TypedDict is lighter but loses validation. **Decide the schema substrate.**

3. **Streaming-delta convention: true-delta vs cumulative.**
   Character.AI ships full-snapshot (simpler client); Perplexity/most ship true-delta (efficient). The *only* hard rule is "pick one and never invert" (`research-perplexity` §10, `agents-character-deep` Copy #7). **Proposal:** true-delta globally — but confirm given Character.AI's "snapshot is dramatically simpler at low per-token cost" argument.

4. **Multi-agent default topology: orchestrator-worker vs symmetric-peer-ensemble vs single-only?**
   Anthropic Research: hierarchical (orchestrator + specialized workers, +90.2%, 15× tokens). Grok: symmetric peers, leader-only render, continuous injection. Agent-S3 *removed* the manager-worker hierarchy and *gained* 13% (`fw-claude-sdk-platforms` Avoid #5). Warp/Devin: single-agent wins on interactive latency. **The evidence genuinely conflicts.** Proposal: single-agent default, both orchestration patterns as opt-in, instrument before recommending either (`coding-devin-warp` §14: "evaluate on real benchmarks before claiming architecture wins").

5. **Memory type taxonomy depth: NIA's 4 or Memanto's 13?**
   4 (`scratchpad/episodic/fact/procedural`) is clean and covers most domains; 13 adds `decision/commitment/error/relationship/...` granularity that helps compliance domains. **Decide the default enum and whether it's extensible vs fixed.**

6. **Compaction model: same-model (Warp) or cheap-aux (Hermes/LangChain)?**
   Warp uses the conversation's *own* model for summarization (no separate summarizer, deterministic rule/TODO preservation). Hermes/LangChain route to a cheap `AuxiliaryClient`. *Tension:* same-model = higher fidelity + no aux-context-window-feasibility problem; cheap-aux = lower cost but Hermes had to add a startup feasibility check (`coding-devin-warp` Warp compaction vs `hermes-agent-core` §4). **Decide the default; possibly expose both.**

7. **Tool-list strategy: meta-tools (Composio) vs deferred-loading (Claude/Codex) vs both?**
   Both solve O(N)-schema-flooding. Meta-tools (`VersoSearch`+`VersoMultiExecute`) put a discovery layer in front of the LLM; deferred loading keeps schemas out of context until `tool_search`. They compose but add surface. **Decide whether Verso ships one, the other, or both as the default tool-surface model.**

8. **Durable execution substrate: bare async, or Inngest/Temporal-style step isolation?**
   11x's Inngest durable steps (each step replays independently on crash) are required for agents touching external state (`agents-products` §4); but it's heavy infra. Bare async is simple but loses crash-resilience for side-effecting tools. **Decide whether durable step isolation is core, an adapter, or out of scope for v1.**

9. **Code-execution escape hatch: ship a sandboxed JS/Python `exec` tool (Codex Code Mode)?**
   Code Mode (V8 isolate, `exec`+`wait`) collapses N sequential tool round-trips into one JS program with real `Promise.all` parallelism — "the single most impactful addition for high-tool-count tasks" (`coding-codex` Code Mode). But it's a large surface and a security boundary (needs E2B/Modal/V8 sandbox). **Decide if this is v1 or later, and which sandbox.**

10. **HITL ergonomics: expose `Command(resume=...)` (LangGraph) or hide it behind `await ctx.hitl.request()`?**
    LangGraph's durable `interrupt()` + `Command(resume=...)` is checkpoint-backed but forces the caller to know about `Command`. The higher-level `await ctx.hitl.request(question) → answer` hides the await/resume from the node author (`fw-langchain-langgraph` Improve #37). **Decide the HITL surface; the higher-level one is more Verso-thesis-aligned but harder to make durable.**

11. **Provider profile granularity: how much provider-specific quirk handling is "core" vs plugin?**
    Hermes' `anthropic_adapter.py` = 2,273 lines of accumulated quirks (thinking-signature policies, orphan-tool-pair stripping, screenshot eviction, double-serialization). Pushing ALL of it into per-provider plugins keeps the core thin but front-loads work (`hermes-surfaces` §1 Avoid). **Decide the line: which quirks ship in core adapters vs which are plugin-only.**

12. **Self-improvement: ship Hermes' two-tier curator, or just the `on_turn_complete`/`on_idle` hooks?**
    Hermes' session-review + library-curator is the deepest self-improving loop in any teardown but is a large opinionated subsystem. The minimalist position: ship the two hooks and let users build it (`hermes-agent-core` §7 — "Verso doesn't need to ship skill management; provide the hooks that enable it"). **Decide whether memory consolidation is a built-in primitive or purely hook-enabled.**

13. **Eval judge default model set: hardcode the JudgeJudy panel, or leave fully pluggable?**
    Character.AI's production-validated panel (Sonnet 0.4 / GPT-4o 0.4 / Gemini 0.2, 0.7 threshold) is a strong default (`agents-character-deep` Copy #4), but hardcoding three vendors as a default conflicts with anti-pattern #9 (no single-vendor lock). **Decide whether to ship a default panel config or require explicit judge configuration.**

---

*Synthesis written 2026-06-04 from all 23 notes under `research/03_teardowns/`. Every numbered claim cites the source note (filename minus `.md`). Where notes conflicted (multi-agent topology, compaction model, streaming-delta convention) the conflict is surfaced in §6 rather than resolved silently.*
