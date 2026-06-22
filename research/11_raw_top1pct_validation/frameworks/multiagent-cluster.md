# Multi-Agent / Role Framework Cluster — Raw Extraction

Sources (all KNOWN-from-source, read 2026-06-23):
- `/Users/seventyleven/Desktop/researchfms/teardowns/METAGPT.md`
- `/Users/seventyleven/Desktop/researchfms/teardowns/AGENCY_SWARM.md`
- `/Users/seventyleven/Desktop/researchfms/teardowns/CAMEL_AI.md`
- `/Users/seventyleven/Desktop/researchfms/teardowns/TASKWEAVER.md`
- `/Users/seventyleven/Desktop/researchfms/teardowns/MICROCHAIN.md`
- `/Users/seventyleven/Desktop/researchfms/teardowns/OPENAGENTS.md`

Verso thesis check: Verso's stated stance is **"no forced multi-agent / we don't force the graph."** Every framework here EXCEPT microchain is a multi-agent coordination layer. So the default expectation — most of this is overkill Verso must refuse — holds. The job is to find the 1-2 coordination primitives genuinely worth stealing as additive, byte-identical-when-unused options.

---

## 1. METAGPT — pub/sub message bus + document-as-protocol (KNOWN)

Primitive (verbatim teardown): *"a `Team` of typed `Role`s with private message inboxes, communicating over a shared `Environment` message bus, following a Standard Operating Procedure (SOP) where every role's output is a structured artifact (PRD, Class Design, Task List, Code Files) — not free text."*

API shapes:
- `Message(content, role, cause_by, sent_from, send_to: set[str])` — `cause_by` = FQN of the Action class that produced it; `send_to` defaults to `{MESSAGE_ROUTE_TO_ALL}` (`"<all>"`). Routes by subscription (`cause_by ∈ watch`) OR explicit `send_to` name.
- `MessageQueue` — each role's private `asyncio.Queue` inbox with non-blocking `pop_all()`.
- `Role._observe()`: drains buffer, filters `news = [n for n in news if (n.cause_by in watch or self.name in n.send_to) and n not in memory]`. This IS the subscription filter.
- `Environment.publish_message(msg)`: iterates roles, `is_send_to(msg, addrs)` → delivers to inbox. `Environment.run(k=1)` = `asyncio.gather` over `role.run()` for every non-idle role per tick. "Send-now, process-next-tick" semantics avoid reentrancy.
- `Team.invest($3)` → `cost_manager.max_budget`; raises `NoMoneyException` when LLM cost exceeds budget. **Cost-cap-as-termination.**
- Three react modes on one base via `RoleReactMode` enum: `REACT` (default, `max_react_loop=1` — one think/act), `BY_ORDER` (fixed playbook), `PLAN_AND_ACT` (planner-driven).

Key contrast quote: *"MetaGPT roles don't know each other's names — they just watch for the artifacts they care about."* (vs LangGraph's explicit `add_edge(from,to)`). Mental model: *"closer to Erlang/Akka actors than to LangChain."*

WriteCodeReview: 6-item checklist → `LGTM`/`LBTM` (Looks Bad To Me) verdict; on LBTM auto-rewrite, `code_validate_k_times` rounds.

TeamLeader (`MGXEnv`, newer path): `publish_team_message(content, send_to)` is the dispatch tool; after dispatch it calls `_set_state(-1)` to idle itself and waits; guards `if send_to == self.name: return` (no send-to-self). T-shirt sizing prompt (XS/S/M...) decides whether to skip the full SOP.

Verso relation: pub/sub bus, persistent role actors, SOP, budget-as-termination = **avoid-overkill** (this IS the forced-multi-agent graph Verso refuses). Cost-cap termination is mildly interesting but Verso already has `max_context_tokens` and stuck/max_steps policies; a hard USD budget cap is **neutral-context**.

---

## 2. AGENCY_SWARM — SendMessage-as-a-tool (KNOWN) ← best idea in cluster

Primitive: inter-agent communication is **a normal tool call, not a message bus.** *"When Agent A 'talks to' Agent B, Agent A's LLM emits a `send_message` tool call with `recipient_agent='B'`. The tool's `on_invoke_tool` runs a complete recursive agent loop on B (`B.get_response(message)`) and returns B's final answer as the tool's string output. From A's perspective, B is a tool that returns text."*

Consequence (verbatim): *"agent communication uses the same retry/streaming/guardrails machinery as user-to-agent communication, with no additional async runtime."* Chains `A→B→C→D` are just nested tool calls; D returns to C returns to B returns to A.

API shapes:
- `SendMessage` = a `FunctionTool` with fixed schema `{recipient_agent, message, additional_instructions}`. `recipient_agent` is an **enum constrained to allowed recipients** — "the LLM literally cannot address an agent it isn't allowed to."
- `Agency(*entry_points, communication_flows=[(a,b),...])` — static DAG of who-can-talk-to-whom. Operator DSL: `a > b > c` via `AgentFlow.__gt__` (and `__lt__` reverse), compose unions with `+`. (The `>` returns an AgentFlow object recording all edges.)
- Subclass `SendMessage` to add typed extra params (nested `ExtraParams(BaseModel)`, `extra_params_model`, or inline fields) — schema-merged into the tool params.
- **Per-thread pending-call guard:** prevents "LLM calls send_message twice before getting a reply" deadlock with a friendly error the LLM can react to.
- **Handoff variant** (`SendMessage.create_handoff`): transfers the conversation entirely (recipient takes over user session) rather than reply-then-return. `add_reminder=True` installs an `input_filter` that injects a system message tagged `"message_origin": "handoff_reminder"` so downstream filters can distinguish framework-inserted text from model output.
- Conversation-starter cache: first-message replies precomputed; cache fingerprint includes the instructions hash → invalidates when the agent changes.

Verso relation: The CORE insight — "a sub-agent is just a tool that returns a string; recursion reuses the entire existing single-agent loop, retry, streaming, guardrails; no new runtime" — is fully **on Verso's thesis** ("just build agents, no graph, no orchestrator-as-primitive"). Verso already has `@tool`, structured tool schemas, and a clean ReAct loop; an agent can ALREADY be wrapped as a `@tool` that calls another agent's loop. So Verso effectively already supports this pattern with zero new primitive — it's **verso-already-has** at the mechanism level. The only genuinely-additive, byte-identical-when-unused sliver is the **pending-call re-entrancy guard** (return a friendly typed error if the same in-flight sub-call is invoked twice before resolving) — see steal list, but it's tiny/optional. The `communication_flows` DAG + operator DSL = **avoid-overkill** (forces a graph/topology Verso explicitly rejects).

---

## 3. CAMEL — inception prompting + Workforce HITL (KNOWN)

Inception prompting (`AISocietyPromptTemplateDict`): two LLMs locked into producer/consumer via prompt. Verbatim load-bearing lines:
- `"Never forget you are a {assistant_role} and I am a {user_role}. Never flip roles! Never instruct me!"`
- `"Never flip roles!"` — *"Necessary because LLMs default to being helpful, which means switching to whichever role would be most helpful next."*
- Fixed `Solution: <YOUR_SOLUTION>` / `Instruction: <YOUR_INSTRUCTION>` envelope — machine-readable without a parser model.
- `"Always end <YOUR_SOLUTION> with: Next request."` — explicit turn-handover token.
- `<CAMEL_TASK_DONE>` sentinel — user agent ends via substring search (cheap). Without the role anchor, *"the LLMs role-flip after ~5–10 turns."*
- Bootstrapped the AI Society dataset (45k+ instruction examples).

Workforce (`societies/workforce/workforce.py`, 6239 L): coordinator decomposes → best-fit worker by description embedding → workers run in parallel via `task_channel` (asyncio.Queue) → `_apply_recovery_strategy` (decompose-further / replace-worker / pause-and-ask-human). `WorkforceState` FSM: IDLE/RUNNING/PAUSED/STOPPED/SNAPSHOTTING.

Workforce HITL surface (the richest in the cluster): `save_snapshot(desc)→WorkforceSnapshot`, `list_snapshots`, `restore_from_snapshot`, `pause/resume` (sets `pause_event`, agents check between steps), `stop_gracefully`/`stop_immediately`/`skip_gracefully`, `modify_task_content(task_id, new)`, `reorder_tasks`, `add_subtask`, `remove_task`, `resume_from_task(task_id)`, `continue_from_pause`. Pipeline mode: explicit DAG builder with `add_task/fork/join/build/depends_on`. Shared memory: `_collect_shared_memory`/`_share_memory_with_agents`/`_sync_shared_memory` broadcast worker chat histories.

Agent pool (`single_agent_worker.py:54`): pre-cloned agent pool for parallel exec, metrics `_total_borrows`/`_total_clones_created`/`_pool_hits`.

Verso relation: Inception prompting = a prompt pattern, not a framework primitive — **neutral-context** (Verso ships ContextBundle/instructions; users can author such a prompt). Workforce coordinator/DAG/pipeline/agent-pool = **avoid-overkill** (forced hierarchy + DAG). Workforce's snapshot/pause/resume/`modify_task_content`/`reorder` HITL — Verso already ships the durable seam: `SqliteCheckpointStore`, `resume()` in fresh process, `ctx.hitl.request` pause/resume, `history()`/`fork()` time-travel. So **verso-already-has** at the seam level. The one thing Verso's durable seam may NOT expose is *editing a queued/pending task's content mid-pause* (`modify_task_content`) — but that's a multi-agent task-queue concept Verso doesn't have a queue for; **avoid-overkill**.

---

## 4. TASKWEAVER — Planner↔CodeInterpreter, code-as-action, scoped shared memory (KNOWN)

Primitive: `Planner ↔ CodeInterpreter` pair; action space is Python in a **stateful Jupyter kernel**; "plugins" are pre-loaded Python functions the generated code can call.

- Session loop: `User → Planner → Worker → … → User`; each hop is one LLM call; hard cap `max_internal_chat_round_num=10`.
- Planner output is strict JSON: `plan_reasoning, init_plan, plan, current_plan_step, stop, send_to, message`. `send_to` constrained to worker enum; all fields required → "Planner cannot ever produce malformed orchestration messages."
- No-Planner mode: `roles=["code_interpreter"]` → user talks directly to the worker (worker reply wraps to a synthetic Planner reply). I.e. **the orchestrator is optional/removable.**
- Code verification: AST-walk before exec; reject imports outside `allowed_modules` + calls to `blocked_functions`. `local` vs `container` (Docker) execution as a config flag.
- Self-correction: verifier emits error strings w/ line numbers → `format_code_correction_message()` → `revise_message` attachment → loops CodeInterpreter→CodeInterpreter; after `max_retry_count=3` → back to Planner with failure summary.
- `Post(id, send_from, send_to, message, attachment_list)`; `Attachment(type, content, extra)`; ~15-type `AttachmentType` enum (plan, init_plan, thought, reply_content, verification, code_error, execution_status, execution_result, artifact_paths, revise_message, shared_memory_entry, stop, send_to...). Render strips metadata to prose for the LLM but stores all for debugging.
- **`SharedMemoryEntry {type, scope, content}`, `scope ∈ {round, session, global}`** — Planner posts plan as `scope="round"` readable by all workers in that round; `session` persists across rounds; `global` across sessions.
- Experience replay: past successful runs summarized as "lessons," retrieved for similar future tasks.

Verso relation: Planner↔Worker orchestration + Post/attachment message envelope = **avoid-overkill** (forced two-role graph). Code-as-action + stateful kernel = **neutral-context** (a tool design choice, not a Verso gap; Verso's `@tool` can wrap a kernel). The strict-JSON-orchestration-message and AST code verification map to things Verso already has (structured `output_type` + in-loop reask; tool trust-tier/quarantine). The **scoped shared-memory** idea (`round`/`session`/`global`) is interesting but Verso's typed 4-tier memory + temporal recall already covers session/global persistence; "round" scope only exists because there are multiple roles per round — **verso-already-has**. Self-correction loop = Verso's `Retry(feedback)` + validators.

---

## 5. MICROCHAIN — the minimal single-agent loop (KNOWN) — NOT multi-agent

Tagline: *"function calling-based LLM agents. Just that, no bloat."* ~1100 LOC total, ~580 LOC core.

- Loop: `while True`: LLM emits one Python call expr as plain text → `ast.parse` (NOT JSON, NOT function-calling API) → dispatch → `str(result)` appended as a `user` message → loop until iteration cap or a `Stop()` function calls `engine.stop()`.
- `Function` base: subclass's `__call__` type annotations ARE the schema; `help` built from `inspect.signature` + `description` + `example_args`. No JSON schema, no decorator metadata.
- `safe_call`: `TypeError/SyntaxError` → short "wrong format" retry message; any other exception → full stack trace returned as user message ("let the LLM read the trace and adapt").
- **Reasoning-as-tool**: no-op `Reasoning(reasoning: str)` — CoT is structurally a tool call (same parse/record path, no `Thought:` prefix parsing). **Stop-as-tool**: termination is a `Stop()` call (no is_done prediction, no special token).
- **Bootstrap-as-real-execution**: few-shot examples are a list of command strings *actually executed by the engine* before the loop, so the LLM sees grounded `assistant: CALL / user: REAL_RESULT` pairs from its own engine.
- `transient_history`: per-call ephemeral context, prepended for the LLM call but never committed.
- `clean_reply`: `reply[:reply.rfind(")")+1]` — truncate trailing chatter after the last `)`.
- Callbacks: `on_iteration_start/step/end(agent)` — wire external state without subclassing. `Engine(state=...)` binds one shared dict to every function.
- Explicit gaps: "No multi-agent / orchestration", no async, no streaming, no persistence, no timeout.

Verso relation: This is Verso's own thesis ("the boring core done right, <200 lines, just build agents") in miniature — mostly **verso-already-has** (Verso's loop, `done()` tool, `@tool` docstring→schema, jsonish parse waterfall, stuck detection all subsume this). Two small grounding ideas worth noting: **bootstrap-as-real-execution** (few-shot examples that are actually run so results are real, not faked) and **Reasoning/Stop as plain tools** — see steal list. Verso already has `done()` (Stop-as-tool ✓). The AST-Python-as-tool-call protocol is **neutral-context** (Verso deliberately uses jsonish; not a gap).

---

## 6. OPENAGENTS — LangChain-wrapper platform + infra (KNOWN) — not a coordination primitive

*"Three production-quality language agents behind one chat-server, each built on LangChain primitives."* The agent loops are LangChain ReAct; "the surrounding infrastructure is the lesson."

Infra worth noting (NOT coordination primitives):
- **Embedding tool-selector** over 229 ChatGPT-format plugins: top-K cosine sim via `hkunlp/instructor-large`, cached on disk per-plugin.
- **Kernel publisher** (Redis pubsub admission queue): max 300 concurrent kernels; channels `job_submitted`/`job_started`/`job_completed`; `kernel_pending_queue` (FIFO) + `kernel_running_queue`. *"a global admission queue keyed on chat_id... Simple, effective, no consensus needed."* Per-user kernel reuse with LRU-evict.
- **Dual-view DataModel**: every tool output has `get_llm_side_data()` (text, sized to context) and `get_human_side_data()` (full structured for frontend); scratchpad uses LLM-side only; only the **last** observation wrapped with the CoT scaffold text.
- Per-turn truncation: hard `max_tokens=8000`, `max_gen_tokens=1000`; truncate chat history to `8000 - system_prompt_tokens - 1000` every iteration (their own `# FIXME`).
- Message branching via `parent_message_id` (ChatGPT edit-and-regenerate, leaf→root walk).
- Anthropic continue-model fixup (`NEED_CONTINUE_MODEL`): canned fake `Human:` message injected after every tool response because *"models like anthropic claude can only return valid completion with human message as the last message."*

Verso relation: Tool-selector over a large registry = retrieval (Verso has RRF retrieval) — **verso-already-has**. Redis admission queue/300-kernel cap = production infra, not a Verso primitive — **avoid-overkill** (Python-only, no orchestrator/queue as primitive). Dual-view (LLM-side vs human-side tool output) is a real idea — see steal list; relates to but extends Verso's `prune()` (which masks, doesn't keep a parallel rich view). Truncation-by-token-budget = Verso's `max_context_tokens` + `prune()`. Anthropic last-message-must-be-human is a model-adapter quirk Verso's adapters should already handle — **neutral-context** (worth a sanity check in the anthropic adapter, but not a coordination primitive).

---

## Cross-cluster synthesis

The single recurring GOOD idea, stated three different ways:
- AGENCY_SWARM: a sub-agent is **just a tool that returns a string**; recursion reuses the whole existing loop/retry/streaming — "no additional async runtime."
- TASKWEAVER: the orchestrator (Planner) is **optional/removable** (`roles=["code_interpreter"]`); single-worker degrades gracefully.
- MICROCHAIN: multi-agent is explicitly a NON-feature; one clean loop is enough.

This trio strongly VALIDATES Verso's "no forced multi-agent / we don't force the graph" thesis: the most coherent design in the cluster (Agency Swarm) achieves multi-agent by making the OTHER agent a tool — i.e. with no graph runtime at all. Verso already supports exactly this (wrap an agent loop in `@tool`). The frameworks that DO force a graph (MetaGPT bus, CAMEL Workforce DAG, TaskWeaver Planner) carry 6000+ LOC each of coordination machinery — the overkill Verso is right to refuse.

Genuinely-additive micro-candidates (all byte-identical-when-unused, all tiny):
1. **Pending-call re-entrancy guard** (Agency Swarm) — if an agent-as-tool is re-invoked while an identical call is still in-flight, return a typed friendly error the LLM can recover from. Prevents the double-dispatch deadlock. Opt-in only when one agent calls another.
2. **Bootstrap-as-real-execution** (microchain) — few-shot examples that are actually executed against the real tool registry so the demonstrated tool results are real, not hand-faked. Optional helper on top of ContextBundle.
3. **Dual-view tool output** (OpenAgents) — a tool can return a compact `llm_side` view (for context) plus a rich `human_side` view (for trace/UI) without bloating the model's context. Generalizes `prune()` from "mask" to "downscale-but-keep-rich-elsewhere." Only materializes when a tool opts in.

None of these require a graph, an orchestrator, or a second runtime, and all are no-ops when unused.
