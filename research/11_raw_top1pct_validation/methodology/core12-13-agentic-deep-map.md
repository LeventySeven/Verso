# RAW EXTRACTION — core12-13-agentic-deep-map (methodology)

Source files (READ, bounded):
- `/Users/seventyleven/Desktop/researchfms/core/12_AGENTIC_AI_DEEP.md` (124KB, 2602 lines) — "The Definitive Guide to Frontier Agentic AI Systems (2026)"
- `/Users/seventyleven/Desktop/researchfms/core/13_AGENTIC_AI_ARCHITECTURE_MAP.md` (42KB, 1102 lines) — "Agentic AI Architecture Map: From Screenshot Concepts to Production Systems"

Tags: KNOWN = verbatim/specific from source. INFERRED = my mapping/judgment.
Verso-state tags applied per finding in the structured object.

---

## A. THE UNIVERSAL AGENT LOOP (file 12 §1, file 13 §1) — KNOWN

File 12 §1, verbatim code comment: `# This is the entire agent loop. Everything else is engineering around it.`

```python
messages = [system_prompt] + [user_message]
while True:
    response = llm.generate(messages, tools=tool_definitions)
    if response.has_tool_calls:
        for tool_call in response.tool_calls:
            result = execute_tool(tool_call)
            messages.append(tool_result(result))
    else:
        return response.text  # done
```

> "The insight that matters: The loop itself is trivial (5-10 lines). The 10,000+ lines of engineering in production systems are all in: (1) context management to fit useful information in the window, (2) tool design ..., (3) security ..., (4) error recovery when things go wrong."

Claude Code Rust rewrite loop = **~88 lines** (claw-code/runtime/conversation.rs). Key principle quoted: **"Messages are the only state."** Single append-only message array. "No state machine, no workflow graph."

Three production variants (§1 table):
- **Single-threaded while-loop** (Claude Code, Codex CLI): messages are the only state, all complexity pushed to context/security/tool-specificity.
- **Event stream + one-tool-per-turn** (Manus): strictly ONE tool call per iteration, must await results, ~50 tool calls/task, "prevents model from running ahead of reality."
- **Multi-agent debate** (Grok 4.20): NOT a loop — 4 agents analyze concurrently, debate via cross-attention.

File 13 §1 expands the harness checklist OUTSIDE the loop: compile context within budget; route each call to right model; validate every tool call against schema+permissions; **run read-only tools in parallel, mutating tools sequentially**; **persist state after each step so the task can resume**; compact/clear old tool outputs; trace everything; stop when goal done / budget exhausted / context overflows / policy blocks.

File 13 §1 ADK commit-boundary (INFERRED-useful): Runner appends user event -> calls agent -> **agent yields Event** -> Runner commits actions through SessionService/ArtifactService/MemoryService -> resumes after commit. "Event as commit boundary" — "better than a naive while-loop when state consistency matters."

File 13 minimal skeleton: `AgentRuntime(model_router, tool_registry, session_store, policy, tracer)`; `_execute_tools` does `readonly, mutating = partition_by_readonly(calls)`; gather readonly in parallel, loop mutating sequentially. `session_store.commit(session)` after EVERY append (user / assistant / tool_results).

VERSO MAP: Verso already ships the <200-line async ReAct loop, done() termination, "messages are the only state" philosophy, and the durable seam (commit-each-step, resume in fresh process). The parallel-readonly/sequential-mutating partition is a concrete pattern worth checking against Verso's tool execution.

---

## B. CLAUDE CODE REFERENCE (file 12 §2) — KNOWN

- Six-layer arch: UI / Query Engine (~46K lines) / Tool System (40+ tools, permission gates) / Context Mgmt (5 compaction strategies, 14 cache-break vectors) / Permission-Security (23 bash checks, 2-layer classifier, hook system) / Agent Orchestration (fork, teammate, worktree).
- **System prompt assembly NOT monolithic:** 110+ prompt strings, conditionally included. Split at `SYSTEM_PROMPT_DYNAMIC_BOUNDARY`: static prefix (max cache hits) then dynamic suffix (env tools, MCP defs, CLAUDE.md, memory index, active plan/TODOs, skill schemas). "Single character difference in the static prefix breaks the entire prompt cache." Tracks **14 cache-break vectors** with "sticky latches."
- **Edit format:** exact string replacement (`old_string` -> `new_string`), must be unique in file, no diffs/line-numbers. "Simplicity is intentional — fewer failure modes than diff-based formats." [Verso parallel: Edit tool already uses this exact shape.]
- **Deferred tool loading:** MCP tools `defer_loading: true`, only names consume context, full schemas loaded on-demand via tool search. **85% context reduction (72K -> 8.7K tokens for 50+ MCP tools).**
- **Context compaction (three-tier):**
  - Tier 1 MicroCompact: zero API calls, surgically truncates high-token tool outputs, preserves cache boundaries.
  - Tier 2 AutoCompact: ONE API call, triggers at `ContextWindow - 13,000` tokens (~95%), generates ~20K structured summary. **Circuit breaker after 3 consecutive failures** — added because "1,279 sessions hit 50+ consecutive failures, wasting ~250K API calls/day globally."
  - Tier 3 Full Compact: compresses everything, re-injects recently accessed files (capped 5K tokens each), active plans/TODOs, skill schemas.
- **Permission model two-layer classifier:** Stage 1 fast single-token yes/no (8.5% FPR raw); Stage 2 chain-of-thought only if Stage 1 flags (-> 0.4% FPR). Classifier sees ONLY user messages + tool-call payloads — assistant messages & tool outputs **stripped** ("prevents model from talking classifier into bad calls"). Production: **0.4% FPR, 17% FNR**.
- Bash security: 23 sequential checks/command, 18 blocked Zsh builtins, zero-width Unicode injection prevention, IFS null-byte blocking.
- **Hook system: 25+ events** (SessionStart, PreToolUse, PostToolUse, Stop, etc.). Hooks can block, modify tool input, replace MCP tool output, inject context into subagents.
- Sub-agents via `Agent` tool `subagent_type`: general-purpose / Explore (read-only) / Plan (no writes). Each gets own context window. Foreground (blocking) or background (async). Isolated git worktrees.
- Agent Teams (Feb 2026, experimental, env `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`): Team Lead + teammates each with own instance/context. Shared Task List (pending/in_progress/completed/blocked + dependency tracking + auto-unblock), Peer-to-Peer Mailbox, File Locking. Rec 3-5 teammates, 5-6 tasks each. Hooks `TeammateIdle/TaskCreated/TaskCompleted` (exit code 2 rejects + sends feedback).
- §2.9 unreleased (KAIROS daemon, autoDream memory consolidation idle, ULTRAPLAN cloud planning, anti-distillation decoy tools) — interesting context, mostly OVERKILL for Verso.
- Managed Agents API (Apr 8 2026): hosted, agents run hours, sessions persist through network disconnects, `$0.08/session-hour`.

---

## C. CODEX CLI (file 12 §3, §20.9) — KNOWN

- `AgentControl` orchestrator. Submission/event queue: `Op` messages (UserTurn, InterAgentCommunication, ExecApproval, Compact, Interrupt, ~20 more) -> `EventMsg` stream. Dedicated Tokio task dispatches sequentially.
- V4A unified diff edit (`*** Begin Patch`, `@@ function descriptors`), **four-pass fuzzy matching**: exact -> rstrip -> both-trim -> Unicode normalization (typographic dashes->ASCII, smart quotes->plain).
- Sandbox: macOS Seatbelt (.sbpl, `(deny default)` + selective allows), Linux Bubblewrap+seccomp (blocks connect/accept/bind/listen/ptrace/io_uring), anti-debug (ptrace PT_DENY_ATTACH, prctl PR_SET_DUMPABLE 0). Exact Rust enum:
```rust
enum SandboxPolicy {
    DangerFullAccess,
    ReadOnly { access, network_access: bool },
    ExternalSandbox { network_access },
    WorkspaceWrite { writable_roots, network_access, exclude_tmpdir_env_var, exclude_slash_tmp },
}
```
- **Guardian (AI security reviewer):** model gpt-5.4, 90s timeout, budget 10K msg + 10K tools, max 40 entries, risk taxonomy low/medium/high/critical. **"Fails closed": timeout/failure/malformed = deny.** Delta mode (only new entries on retry).
- Memory two-phase: extraction (gpt-5.4-mini, 8 parallel jobs, no-op gate prompt **"Will a future agent plausibly act better because of what I write here?"**); consolidation produces memory_summary.md / MEMORY.md / SKILL.md / rollout_summaries.
- §3.5 multi-agent v2: six tools (`spawn_agent` with fork_turns none/all/last-N; `send_message` queue-only; `followup_task` wakes target; `wait_agent` blocks; `list_agents`; `close_agent`). Roles default/explorer(read-only)/worker. **Max depth 1, max 6 parallel threads.** Orchestrator prompt: "Prefer multiple sub-agents. Do not perform actual work while they are working."
- §20.9 `InterAgentCommunication` **first-class protocol primitive** with `author/recipient/other_recipients(broadcast)/content/trigger_turn:bool`. `AgentPath` hierarchical unix-style addressing (`/root`, `/root/researcher`, `/root/researcher/worker`). "fundamentally more capable than Claude Code's one-way result-only return."
- Git ghost commits: `create_ghost_commit()` snapshots working tree as unreferenced commit (no branch pollution), `restore_ghost_commit()` rolls back. Used for undo during agent work.

---

## D. OTHER SYSTEMS — KNOWN highlights

- **Cursor Apply Model:** decouples "knowing what to change" from "performing the file edit." Smart model emits sketch with `// ... existing code ...` markers; fine-tuned apply model (Llama-3-70B) performs edit; **speculative edits treat existing file as draft -> ~1,000 tok/s (13x).** Failure -> reapply (escalate to smarter model).
- **Cursor loop (leaked):** UNDERSTAND->INVESTIGATE->PLAN->IMPLEMENT(always run linter, max 3 fix iterations)->VERIFY(read modified files)->REPORT. `<non_compliance>`: "If you find yourself not following these rules, STOP. Re-read the rules. Start over from the last correct step." `<maximize_parallel_tool_calls>`: "Multiple INDEPENDENT operations MUST be parallel. 3-5x faster."
- **Cursor Bugbot:** 8 parallel passes with randomized diff ordering -> bucket -> majority voting -> validator model (false-positive reducer) -> dedupe. 52%->70%+ resolution.
- **Grok 4.20:** shared ~3T MoE backbone + 4 LoRA persona adapters (~0.3% params), shared KV cache, cross-attention debate (2-4 rounds, <=180 tokens, exchange "critique embeddings"). Cost 1.5-2.5x NOT Nx. `chatroom_send(to=..., message=...)` + `wait(timeout)`. Heavy mode 16 agents -> hallucination 12%->4.2%.
- **Devin:** Planner/Coder/Critic compound. `<find_and_edit>` = regex + **separate LLM instance per match location** (parallelizes multi-site refactors). RFT planning subagent: file-prediction F1 reward, ~8-10 back-and-forths -> ~4 (2x).
- **Devin "Don't Build Multi-Agents" thesis (June 2025):** parallel multi-agent fragile due to context isolation; alternative = single-threaded linear agent + compression layer. Counter-evidence (Anthropic, 24h): 90.2% improvement multi-agent. **Resolution: naive multi-agent fails; production w/ shared state works.**
- **Windsurf SafeToAutoRun:** every terminal command classified safe/unsafe. "NEVER run unsafe commands automatically even if user asks." Hardcoded, cannot be overridden by user. `trajectory_search` (cross-session memory), `create_memory`, `EPHEMERAL_MESSAGE` (transient context, doesn't persist).
- **Manus:** event stream (Message|Action|Observation|Plan|Knowledge|Datasource), INPUT:OUTPUT=100:1 so cache 100x > output. Rules: static prefix (no timestamps), append-only, deterministic JSON (sorted keys), session->consistent vLLM worker, **logit masking instead of tool removal** (tool list constant, mask unavailable). Cached $0.30/MTok vs uncached $3.00 = 10x. **todo.md pattern:** "recites objectives into the end of context" to mitigate lost-in-the-middle.
- **Amazon Q:** **Critic with Rollback** — critic detects dead end -> rolls back to previous state. "Most other agents lack explicit rollback."
- **Sierra Constellation:** 15+ models routed per task type (retrieval/classification/tool-calling/policies/tone) on latency/precision/context/tone. Built-in redundancy + automated failover to healthier equivalent models + supervisor enforcement. Experience Manager: every annotated conversation becomes a conversation test, thousands run in parallel before every release.
- **Augment Code (#1 SWE-bench Pro 51.8%):** Context Engine = proprietary semantic dependency analysis (NOT text search). Coordinator/specialist/verifier + quality gates.
- **GitHub Rubber Duck (cross-model review):** pair models from different families as reviewer (Claude + GPT-5.4). +4.8% on hardest; "add one reviewer, close 74.7% of the performance gap." "The cheapest multi-agent pattern."

---

## E. CONTEXT ENGINEERING — THE NEW DISCIPLINE (file 12 §15, file 13 §4) — KNOWN

> "Context engineering replaces prompt engineering. The question shifts from 'what words do I use?' to 'what configuration of context produces the desired behavior?'"

**Three Anthropic API primitives:**
1. Compaction (`compact-2026-01-12`): trigger at threshold (min 50K), summary preserves decisions/bugs/next-steps, prior messages dropped, "summary of summaries" over time.
2. Tool-Result Clearing (`clear_tool_uses_20250919`): zero inference cost, replaces old tool_result with `"[cleared to save context]"`, **KEEPS tool_use record (model knows what happened, not raw output)**. Benchmark 335K peak -> 173K peak (7 clearing events).
3. Memory Tool (`memory_20250818`): client-side persistent, six ops: view/create/str_replace/insert/delete/rename.
Combined: clear at 50K (keep 6 recent), compact at 180K.

**Observation Masking (file 12 §15.4, "Best Academic Finding"; file 13 §4 JetBrains):** keep full action+reasoning history, mask older OBSERVATIONS with placeholders, retain recent 10 turns full observations. **Result: 52% cost savings WITH 2.6% solve-rate IMPROVEMENT.** Why: "old tool outputs rarely re-read, but old reasoning informs current decisions."

**KV-cache hierarchy (§15.3):** static prefix (10x), append-only (preserves all KV), deterministic JSON (byte-identical prefixes), session routing to consistent workers (warm cache), logit masking (constant tool list), cache-boundary tracking (14 vectors), deferred tool loading (85%), MicroCompact (zero API calls), DYNAMIC_BOUNDARY split.

**Multi-agent context math (§15.6, Phase Transition paper Jan 2026):** Star topologies saturate at `N ~ W/m` (W=window, m=per-agent message size). Hierarchical trees bypass. "Compaction at each level isn't optional — it's a mathematical requirement for scaling."

**File 13 §4 five useful techniques:** static prompt prefix, append-only history, tool-result clearing, observation masking, deferred tool loading.

**file 13 compile_context pattern:** at 0.85*budget -> `clear_old_tool_results(keep_recent=6)`; at 0.95*budget -> `compact(history)`.

**Google ADK state split (file 12 §15.5, file 13 §4):** Session (conversation + KV scratchpad + Events) / Memory (long-lived searchable, `add_session_to_memory`+`search_memory`) / Artifacts (binary/large, name+version, lazy-loaded). "Named, ordered processors compile working context per-invocation."

---

## F. EVALS / OBSERVABILITY (file 13 §8) — KNOWN

**Minimum trace schema — OpenTelemetry GenAI semantic conventions as baseline:**
- `gen_ai.operation.name`: chat / generate_content / embeddings / retrieval / execute_tool / invoke_agent.
- Tool span name `execute_tool {gen_ai.tool.name}`; attrs: tool call id, name, description, type, arguments, result.
- Low-cardinality `error.type`.
- **Content capture opt-in; store content externally, put references on spans** (privacy/volume).

**What to log for calibration:** exact model/provider/version, prompt hash + components, tool schema hash, args + normalized result refs, token counts + cache hit/miss, latency per stage, retry count + error class, final answer + citations, human/eval score.

**Eval loops by architecture:** Coding agent -> patch applies / tests pass / no unrelated edits / tool budget / review findings. Research agent -> source coverage / contradiction handling / citation precision / synthesis quality. (RAG -> recall@k/citation support/hallucination rate.)

**Sierra Experience Manager:** "Every annotated conversation becomes a conversation test. Thousands run in parallel during development and before every release." [= Verso "captured failure IS a regression test."]

---

## G. SAFETY / SECURITY (file 13 §9) — KNOWN

Risk -> Control table:
- Prompt injection from retrieved pages -> classifier/regex scan, isolate untrusted text, cite-only synthesis, NEVER execute instructions from sources.
- Dangerous shell/browser -> permission classifier, allow/deny policies, dry-run mode, command parser, sandbox.
- Tool exfiltration -> per-tool scopes, user consent, no secrets in context, outbound network policy.
- SSRF/file abuse -> URL allowlists, scheme checks, internal IP blocks, file ref validation.
- Memory poisoning -> memory write policy, provenance, confidence, TTL, **human approval for permanent memory**.
- Multi-agent race -> file locks, worktrees, ownership assignment, task state machine.

**Policy gate (file 13 §12) explicit code:**
```python
def authorize(user, tool, args, session):
    if not user.has_scopes(tool.scopes): raise PolicyDenied("missing_scope")
    if tool.risk == "high" and not session.has_user_approval(tool.name, args): raise PolicyNeedsApproval
    if tool.name in {"fetch_url","browser_open"}: validate_no_ssrf(args.get("url"))
    if tool.name == "shell": validate_command(args["cmd"])
```
**ToolSpec descriptor:** name, description, input_schema, output_schema, read_only:bool, timeout_s:float, scopes:list, risk:Literal["low","medium","high"].

---

## H. MULTI-AGENT PATTERNS (file 12 §14, §19.3; file 13 §6) — KNOWN

Three production patterns that WORK:
1. **Orchestrator-Workers w/ external shared state:** lead (expensive) spawns N workers (cheap), workers store output in EXTERNAL systems (files/artifacts), pass lightweight REFERENCES back. Con: lead can't steer mid-execution. (Anthropic 90.2%, Codex subagents, Copilot /fleet.)
2. **Shared-backbone w/ persona adapters** (Grok only): 1.5-2.5x not Nx.
3. **Peer-to-peer w/ shared task list** (Agent Teams): no bottleneck, file locking.

Decision tree (§19.3): not decomposable -> single agent w/ tool parallelization (Devin). Decomposable + heavy shared context -> shared backbone or shared filesystem. Decomposable + no shared -> orchestrator-workers. Need cross-model checking -> add Rubber Duck reviewer.

"Three focused agents consistently outperform one generalist agent working three times as long" (Osmani, O'Reilly).

---

## I. SEVEN CROSS-CUTTING PRINCIPLES (file 12 §19.1) — KNOWN, verbatim

1. **Messages are the only state.** No state machines/workflow graphs. Single append-only array. Sessions persistable/replayable/compressible.
2. **Invest complexity in the harness, not the loop.** Loop 5-10 lines; 10,000+ lines in context/security/tools/error-recovery.
3. **Scaffolding > model quality.** Same model, different harness = 5+ point gap.
4. **Cache hit rate is the #1 cost metric.** 100:1 input:output.
5. **Three focused agents > one generalist working 3x as long.**
6. **Token usage explains 80% of performance variance.** Multi-agent 15x tokens vs chat, 4x vs single. "The tokens ARE the performance."
7. **Cross-model review is the cheapest multi-agent pattern.**

**§14.4 THE CRITICAL FINDING:** "Agent architecture matters more than model quality. On SWE-bench Pro, the same model (Opus 4.5) scored 50.2-55.4% depending on the harness. The 5-point spread comes entirely from context management and tool orchestration. This is the single most important insight in agentic AI."

**§19.4 — What every >50% SWE-bench Pro system shares:**
1. Typed tool system w/ specific tools (NOT bash-for-everything)
2. Context compaction/clearing strategy
3. **Linter-in-the-loop (run after every edit, fix up to N times)**
4. File reading before editing (never guess)
5. Plan/TODO tracking for long-session coherence
6. Parallel tool calls where independence allows
7. **Error as feedback** (failed tool calls inform next action, not crash)

---

## J. WHAT IS HYPE / WHAT IS REAL (file 13 §13) — KNOWN, anti-overkill signal

- "Agentic AI is just ChatGPT plus tools." -> FALSE. "Tool use is only the inner loop. The product is state, context, routing, policies, sandboxes, protocols, evals, and calibration."
- "Multi-agent is always better." -> FALSE. Helps when context partitions; hurts when agents duplicate work or need tight shared state.
- "Prompt engineering is the moat." -> Usually FALSE. "Context engineering and eval-driven iteration are the moat."
- "Frameworks solve agents." -> FALSE. "Frameworks provide loop/state abstractions. The product-specific tool schemas, data plane, and evals still decide quality."
- "More model is better." -> FALSE. Route small/fast/cheap for classify/apply/extract, reserve frontier for reasoning/synthesis.

---

## K. PROTOCOLS (file 12 §16) — KNOWN, mostly NON-GOAL context for Verso

- MCP (agent-to-tool, Anthropic->Linux Foundation, dominant). A2A (agent-to-agent, Google->LF, JSON-over-HTTP peer-to-peer). ACP (REST-first, JetBrains+Zed). Agent Skills open standard (agentskills.io, Dec 2025). Verso treats MCP as opt-in adapter (native @tool is the path) — aligned.

---

## L. FRAMEWORK COMPARISON (file 12 §17) — KNOWN, competitive context

LangGraph = "best state management, checkpointing, debuggability" for complex Python production. CrewAI = fastest role-based prototyping. PydanticAI v1 = type-safe Python + Temporal integration. (Verso counter-positions exactly against the LangGraph "force the graph / checkpointing" framing while still owning the durable seam without a graph.)

File 13 §1 best-examples table cites LangGraph "State graph with checkpoints / Use checkpoints for time travel, human approval, retry from super-step, and failed-node recovery." — Verso's durable seam (history()/fork() time-travel, HITL, resume) delivers these WITHOUT the graph.
