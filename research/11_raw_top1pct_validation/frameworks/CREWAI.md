# CrewAI — Raw Extraction (nothing-is-lost artifact)

**Sources read (verbatim):**
- `/Users/seventyleven/Desktop/researchfms/teardowns/CREWAI.md` (2283 lines, 3 RE rounds)
- `/Users/seventyleven/Desktop/researchfms/teardowns/CREWAI_PLUS.md` (881 lines, 2 RE rounds)

**One-line (KNOWN, source):** "A role-based multi-agent framework where you declare agents (each with `role`/`goal`/`backstory`) and tasks (each with `description`/`expected_output`/assigned agent), then `crew.kickoff()` executes them in either `Process.sequential` or `Process.hierarchical` order with a ReAct-style text-parsing loop driving each agent."

The conceptual primitive (KNOWN): **the role-playing pair `(role, goal, backstory) → system_prompt`.** Everything else (memory, knowledge, flows, planning, A2A, MCP) is bolted on around that.

---

## 1. The core abstractions

### Agent (KNOWN, `agents/agent_builder/base_agent.py:228` + `agent/core.py:161`)
Pydantic model. Required text fields injected verbatim into system prompt: `role`, `goal`, `backstory`. Notable defaults:
- `max_iter: int = 25` (the loop cap)
- `allow_delegation: bool = False`
- `cache: bool = True` (tool-result cache)
- `max_retry_limit: int = 2`
- `respect_context_window: bool = True` (auto-summarize when context full)
- `guardrail_max_retries: int = 3`
- `max_execution_time: int | None = None` (wall-clock per task; ThreadPoolExecutor + `future.result(timeout=)`)
- `planning: bool = False` (plan-then-execute mode); `reasoning: bool = False` (deprecated → planning_config)
- `multimodal`, `allow_code_execution`, `code_execution_mode` all **deprecated v2.0**
- `checkpoint: CheckpointConfig | bool | None`
- `from_repository: str | None` (hub-style remote agent load)
- `executor_class: type = CrewAgentExecutor`

### Task (KNOWN, `task.py:108`)
`description`, `expected_output` (both required), `agent` (None→assigned by Crew), `context: list[Task]` (upstream task outputs injected), `tools` (task-level override), `async_execution=False`, `output_pydantic`, `human_input=False` (pause for HITL after task), `guardrail`, `guardrail_max_retries=3`, `max_retries=0`, `markdown=False`.

### Crew (KNOWN, `crew.py:158`)
`agents`, `tasks`, `process: Process = sequential`, `memory: bool|Memory = False`, four memory stores, `manager_llm`/`manager_agent`, `planning=False`, `planning_llm`, `cache=True`, `embedder`, `knowledge_sources`, callbacks.

### Process enum — ONLY two values, 3-year TODO (KNOWN, full file `process.py`, 11 lines)
```python
class Process(str, Enum):
    sequential = "sequential"
    hierarchical = "hierarchical"
    # TODO: consensual = 'consensual'
```
`kickoff` raises `NotImplementedError` for any other value (`crew.py:1011-1018`). Round 3 confirms: 3 years on, still two processes. Implementation moat for new process types is huge — `_execute_tasks` has hardcoded sequential/hierarchical paths only.

---

## 2. The agent loop (KNOWN)

`CrewAgentExecutor._invoke_loop` (`crew_agent_executor.py:292`) dispatches on capability:
```python
use_native_tools = (llm.supports_function_calling() and self.original_tools)
if use_native_tools: return self._invoke_loop_native_tools()
return self._invoke_loop_react()
```
- **ReAct path** (`:313`): regex-parse classic Thought/Action/Action Input/Observation/Final Answer text. `while not isinstance(formatted_answer, AgentFinish)`. `has_reached_max_iterations(iterations, max_iter)` → `handle_max_iterations_exceeded` force-final at 25.
- **Native-tool path** (`:449`): model returns OpenAI `tool_calls` / Anthropic `tool_use` blocks; no regex. Preferred for modern OpenAI/Anthropic.

Resume: `invoke` sets `self._resuming` and **skips** message-list rebuild — picks up at last saved iteration.

### Parser (KNOWN, `agents/parser.py`, `agents/constants.py`)
- `FINAL_ANSWER_ACTION = "Final Answer:"`, `ACTION_INPUT_REGEX = re.compile(r"Action\s*\d*\s*:\s*(.*?)\s*Action\s*\d*\s*Input\s*\d*\s*:\s*(.*)", re.DOTALL)`.
- `parse(text) -> AgentAction | AgentFinish`. `_safe_repair_json` uses `json_repair` lib (trailing commas, single quotes, missing brackets) on tool input.
- Six fallback paths; raises `OutputParserError` with format-reminder slices.

### Constants worth replicating (KNOWN)
`max_iter=25`, `max_retry_limit=2`, `guardrail_max_retries=3`, Observation prefix `"\nObservation:"`, Final answer trigger `"Final Answer:"`.

---

## 3. The prompt registry — `translations/en.json` (KNOWN, the actual moat)

**Every default prompt lives in ONE JSON file.** Localization story = "swap the file." Customization = "subclass `I18N`, override `slice(key)`." 38 distinct slices across 5 categories. Selected verbatim:

- `role_playing = "You are {role}. {backstory}\nYour personal goal is: {goal}"` — **the entire persona prompt**, three substitutions.
- `task = "...Begin! This is VERY important to you, use the tools available and give your best Final Answer, your job depends on it!\n\nThought:"`
- `force_final_answer = "Now it's time you MUST give your absolute best final answer. You'll ignore all previous instructions, stop using any tools, and just return your absolute BEST Final answer."` — the max-iter graceful exit.
- `memory` slice (counting/listing nudge): "...If the task involves counting, listing, or summing items... you MUST use the Search memory tool with several different queries... Enumerate each distinct item you find before giving a final count."
- `task_repeated_usage = "I tried reusing the same input, I must stop using this action input. I'll try something else instead."`
- `summarize_instruction` — structured 5-section conversation summary (Task Overview / Current State / Important Discoveries / Next Steps / Context to Preserve) wrapped in `<summary>` tags, used by the context-length-exceeded handler.
- `hitl_distill_system` — extract **generalizable lessons** from human feedback (reusable rules, not one-time corrections); return empty list if just approval.
- `delegate_work` / `ask_question` tool descriptions: "...they know nothing about the task, so share absolutely everything you know, don't reference things but instead explain them." (the context-blindness solution for cross-agent messages).

**Teardown's own verdict (KNOWN quote):** "The prompt engineering in `translations/en.json` is the actual moat — those prompts are battle-tested across thousands of users' production runs. The 20-line 'memory recall must enumerate distinct items' instruction is the kind of thing you only learn by watching agents fail repeatedly. That's not in the code, that's in the prompts."

---

## 4. Multi-agent / Process orchestration (the steal-vs-overkill question)

### Sequential (KNOWN, `_execute_tasks`, `crew.py:1500`)
Tasks run in **declared order**. Each task gets prior tasks' outputs as `context` (via `task_with_context` slice). No dynamic routing. `async_execution=True` tasks accumulate Futures in a ThreadPoolExecutor; **the first subsequent sync task forces a barrier** (`_process_async_tasks` joins all pending). Async parallelizes only with other async, never across a sync task. `ConditionalTask` has `condition: Callable[[TaskOutput], bool]` — skipped if False.

### Hierarchical (KNOWN, `_create_manager_agent`, `crew.py:1465`)
"Hierarchical process" = **one extra injected manager agent** whose only tools are `AgentTools(agents).tools()` = the two synthetic delegation tools ("Delegate work to coworker", "Ask question to coworker"), looped through the **same** sequential `_execute_tasks`. Manager has hardcoded "Crew Manager" persona. **Manager may NOT carry its own tools** (raises Exception). `hierarchical` ≠ recursive nesting — exactly one manager + flat worker list. No multi-level hierarchies, no swarm, no consensus.

**Key insight (KNOWN):** multi-agent coordination is implemented **entirely as tool-calling within a single ReAct loop**. The manager LLM picks a coworker via a tool-name argument; the framework dispatches; coworker runs its own `CrewAgentExecutor.invoke`; result returns as an observation.

### Honest gaps the teardown lists (KNOWN, §10)
- No native parallel agents within one task (async is a workaround).
- No state graph; routing is static task-list order + manager tool choices + `ConditionalTask`.
- Output parser is fragile (6 fallback paths + json_repair).
- **No durable interrupts**: `human_input=True` pauses in a blocking `input()` call — NOT resumable across processes.
- Limited concurrency: thread pool only, no async/await throughout; LiteLLM blocks thread on non-streaming.

---

## 5. Tool robustness layer — `ToolUsage` (KNOWN, `tool_usage.py`, 1027 LOC, Round 3)

This is CrewAI's failure-tolerance moat. Between "parsed an Action" and "ran the tool":
- **Fuzzy tool-name correction** `_select_tool`: `SequenceMatcher(None, sanitize(name), sanitize(asked)).ratio()`, returns first exact OR **`> 0.85`**. Silently fixes `web_serch` → `web_search`.
- **4-stage JSON-repair ladder** `_validate_tool_input`: `json.loads` → `ast.literal_eval` → `json5.loads` → `json_repair.repair_json`. Four parsers attack a malformed blob before failing.
- **Recursive re-parse with LLM escalation** `_tool_calling`: on parse fail, if `function_calling_llm` set, ask an LLM to re-emit valid JSON (verbatim two-key converter prompt: `tool_name: str`, `arguments: dict`); capped at `_max_parsing_attempts=3` (2 for bigger models).
- **Result cache** keyed `(sanitize(tool_name), json.dumps(arguments))`, gated by optional `cache_function`. Default `_default_cache_function` returns True (cache everything).
- **Repeated-usage guard**: identical `(tool_name, arguments)` as last call → return `task_repeated_usage` message instead of re-running (stops infinite loops).
- **Usage limit**: `max_usage_count` enforced thread-safely via `_usage_lock` (`_claim_usage`).
- **`result_as_answer=True`** short-circuits the ReAct loop — tool output becomes the agent's final answer (how delegation/HITL terminate cleanly).
- **Periodic format reminder**: every `_remember_format_after_usages=3` (4 for big models) uses, re-append full tool-list/format slice.
- `OPENAI_BIGGER_MODELS = [gpt-4, gpt-4o, o1-preview, o1-mini, o1, o3, o3-mini]` get fewer repair attempts.

**Teardown's verdict (KNOWN quote):** "CrewAI's value beyond 'ReAct + delegation' is its failure-tolerance — the fuzzy tool-name match, the 4-parser repair ladder, the LLM-assisted re-parse, the stop-word drop-retry, and the guardrail retry loop are what make it survive flaky model output. A replica that skips these will look identical on the happy path and fall apart on real traffic."

### BaseTool (KNOWN, `base_tool.py`)
Pydantic; `name`, `description`, `args_schema`, `cache_function`, `result_as_answer=False`, `max_usage_count`. **Auto-schema from `_run` signature** (`_default_args_schema`): inspect params, `create_model(f"{cls.__name__}Schema", **fields)`. `@tool` decorator wraps a function (docstring + hints → BaseTool). `_TOOL_TYPE_REGISTRY` global populated via `__init_subclass__` powers checkpoint deserialization. `crewai_tools` ships 78 prebuilt tools.

---

## 6. Memory (KNOWN, `memory/`)

Two systems. **Legacy 4-store**: `ShortTermMemory` (SQLite, recent outputs), `LongTermMemory` (cross-run, quality scores), `EntityMemory` (entities + type + description), `ExternalMemory` (mem0.ai adapter). Default off (`Crew.memory=False`).

**Unified Memory** (newer, opt-in `Memory()` instance, `unified_memory.py`): LLM-analyzed extraction. Defaults: `llm="gpt-4o-mini"`, `storage="lancedb"`, `recency_weight=0.3`, `semantic_weight=0.5`, `importance_weight=0.2`, `recency_half_life_days=30`, `consolidation_threshold=0.85`, `consolidation_limit=5`, `confidence_threshold_high=0.8`, `confidence_threshold_low=0.5`, `query_analysis_threshold=200`.

Composite score = `semantic_weight*cosine + recency_weight*exp(-elapsed_days*ln(2)/half_life) + importance_weight*importance`.

**EncodingFlow** 5-step batch pipeline (itself a CrewAI `Flow`): (1) batch embed (one call), (2) intra-batch cosine-matrix dedup (drop >0.85), (3) parallel find-similar (concurrent searches), (4) **N concurrent LLM calls** for analysis + consolidation (`keep`/`update`/`delete`/`insert_new`), (5) batch re-embed + bulk insert. Recall flow mirrors with adaptive deep-recall (`exploration_budget=1`). All LLM-analysis BaseModels use `model_config = ConfigDict(extra="forbid")` for OpenAI structured-output compatibility.

`consolidation_system` prompt is conservative: "prefer 'keep' when unsure. Only 'update' or 'delete' when there is a clear contradiction, supersession, or redundancy."

---

## 7. Other subsystems (KNOWN, briefly)

- **LLM layer** (`llm.py`, ~2469 LOC): **LiteLLM-first, native-SDK-second**. `__new__` routes to native wrapper (openai/anthropic/azure/bedrock/gemini) if model recognized, else LiteLLM (100+ providers). `_prepare_completion_params` builds the exact dict (None-key stripped). `supports_stop_words`/`supports_function_calling` capability gates. Stop-word drop-and-retry on `'stop'` errors. Streaming with `stream_options={"include_usage": True}` + index-keyed tool-arg accumulation.
- **Knowledge** (`knowledge/`): RAG document collections (PDF/text/CSV/Excel/JSON/web/GitHub), ChromaDB default. `query(results_limit=5, score_threshold=0.6)`. Auto-generates a `knowledge_search_query` via rewrite prompt, injects top-k into task prompt.
- **Planning** (`planning_handler.py`): `Crew(planning=True)` → one-shot `gpt-4o-mini` planner producing per-task plans **concatenated onto `task.description`** before normal run. Agent-level `planning=True` adds a plan-then-execute mode with per-step replanning observation (the "Devin" pattern productized). `step_executor_system_prompt`: "ACT FIRST... Do NOT spend more than 3 tool calls on exploration before attempting the primary action."
- **Guardrails** (`llm_guardrail.py`): callable `(TaskOutput)->(bool,Any)` OR a string auto-wrapped into an LLMGuardrail validator agent. `GuardrailResult` enforces result-XOR-error. Retry up to `guardrail_max_retries=3`, re-running the producing agent with feedback injected. **Callable guardrails dropped on checkpoint serialization with UserWarning; string guardrails survive.**
- **Flow API** (`flow/flow.py`, 3636 LOC): a SECOND framework in the repo. `@start`/`@listen`/`@router` decorators, Pydantic shared state, `or_`/`and_` conditions, `FlowMeta` metaclass dispatch tables. **`asyncio`-based** (Round-3 correction over Round-2's thread-pool claim). AND/OR resolved by explicit state machine: `_pending_and_listeners: dict[key, set[method]]` (seed at build, discard-on-arrive, fire-when-empty), `_fired_or_listeners: set` (multi-source OR fires once). Routers run sequentially feeding their string label as next trigger; listeners via `asyncio.gather`; racing groups (first-wins); cyclic `@start` re-entry. SQLite persistence (`~/.crewai/flow.db`); HITL via `pause_for_feedback`/`resume_with_feedback` (raises `FlowPaused`, persists snapshot). **Teardown: "CrewAI is two frameworks in one repo."**
- **Checkpoint** (`agent/internal/checkpoint.py`): persists kickoff state (completed task outputs, iteration counters, message list). On resume `_resuming=True` skips rebuild. **Much simpler than LangGraph**: per-task outputs + iteration counters; no channel versions, no time-travel between checkpoints, no parallel-fan-out replay. "A 'restart this kickoff where it crashed' feature, not a graph runtime."
- **@CrewBase** (`crew_base.py`): decorator-as-metaclass YAML loader. Loads `config/agents.yaml`/`config/tasks.yaml` relative to defining file, resolves YAML **string refs to live decorated factory methods** (`llm: my_llm` → `my_llm()`; `tools: [scrape]` → `[scrape()]`). `mcp_connect_timeout=30`. Registers `@before_llm_call`/`@after_tool_call` hooks with optional `_filter_agents`/`_filter_tools` guards.
- **Telemetry** (`telemetry.py`): OpenTelemetry singleton, OTLP to `https://telemetry.crewai.com:4319`, `SafeOTLPSpanExporter` swallows export failures. Opt-out `OTEL_SDK_DISABLED`/`CREWAI_TELEMETRY_DISABLED`. `Crew.share_crew=True` opts INTO collecting prompts+outputs (default anonymous counters). Agent fingerprint = hash of (role, goal, backstory).
- **Streaming** (no top-level `graph.stream()`): event bus `crewai_event_bus` + `step_callback`/`task_callback`. `Crew.kickoff(stream=True)` is a **re-entrant trick**: spawns a thread that flips `stream=False` and re-calls kickoff, outer call returns a `CrewStreamingOutput` iterator fed by event-bus chunks.
- **A2A / MCP**: `crewai/a2a/` (Google Agent-to-Agent over HTTP), `crewai/mcp/` `MCPToolResolver` wraps MCP server tools as BaseTools.

---

## 8. CrewAI Plus / Enterprise (KNOWN client-side; server inferred)

Hosted SaaS `https://app.crewai.com` (rebranded "CrewAI AMP"). Server closed-source — teardown built from client HTTP contract. **Same runtime, hosted**: deployed crew runs the exact same OSS code in a container. Plus primitive = "a managed crew identified by name+uuid, owned by an org, deployed from repo_clone_url with env vars, callable from outside." Identity + deployment + auth + observability.

- **Auth**: OAuth2 device flow (RFC 8628). Providers: Auth0/WorkOS/Okta/Entra ID/Keycloak. **Default migrated Auth0 → WorkOS** (live probe 2026-05-14). Tokens in OS keychain via `keyring`.
- **PlusAPI** (`crewai_core/plus_api.py`): 27 methods, 25 unique endpoints, all under `/crewai_plus/api/v1/`, Bearer auth. Resources: crews (deploy mgmt), tools (marketplace), agents (`from_repository`), tracing (8 methods incl ephemeral), integrations (MCP configs + triggers), me/organizations. `httpx.Client(trust_env=False, verify=True)` — **explicitly ignores HTTP_PROXY** (flagged unusual).
- **Tracing**: client→Plus event batches per kickoff (`TraceBatchManager`). 30s timeout. Ephemeral traces for anonymous users → `ephemeral_trace_url`.
- **Deploy validation** (`validate.py`, 9 checks): pyproject + lockfile + `src/<pkg>/{crew.py,config/agents.yaml,config/tasks.yaml}` + Flow `main.py` + hatch wheel + clean import + env-var coverage.
- **Live-probe stack (KNOWN, Round 2):** Rails monolith (`x-runtime` header), WorkOS auth, **Paragon** integration platform (corrects Round-1 "own OAuth handlers" inference — they rebrand Paragon's Connect), Cloudflare, Sentry, FullStory, Amplitude, Segment, HubSpot. **"Not a from-scratch agentic platform — a SaaS company that happens to host CrewAI deployments."**
- **Gap vs LangGraph Cloud (KNOWN):** no Plus-managed memory backend; users BYO Postgres for cross-run memory.

---

## 9. Verso relation tags (summary)

| CrewAI thing | Verso relation |
|---|---|
| ReAct loop, max_iter cap, force-final-at-max | verso-already-has (loop.py, max_steps_policy, grace-call) |
| repeated-usage / stuck guard | verso-already-has (StopReason.STUCK) |
| @tool docstring→schema, jsonish repair waterfall | verso-already-has (4-stage parse) |
| per-tool idempotent/max_attempts/timeout | verso-already-has |
| output_pydantic + in-loop reask + Retry(feedback) | verso-already-has |
| LiteLLM-first + native fallback + base_url | verso-already-has (any OpenAI-compat via base_url) |
| stop-word drop-and-retry, capability gates | verso-already-has (FailoverModel/RetryPolicy/error taxonomy) |
| typed streaming events | verso-already-has |
| OTel spans / telemetry | verso-already-has (VersoSpan + OTel) |
| typed 4-tier memory, temporal, RRF, consolidation | verso-already-has |
| checkpoint resume in fresh process | verso-already-has (durable seam) + CrewAI's is weaker |
| HITL via blocking input() | avoid-overkill (Verso's is durable/resumable — CrewAI's is NOT) |
| Process enum (sequential/hierarchical) as primitive | avoid-overkill (Verso refuses orchestrator-as-primitive) |
| Flow API (second framework) | avoid-overkill (graph-DSL = NON-GOAL) |
| LLM-analyzed memory extraction + EncodingFlow | avoid-overkill (LLM-summarization-by-default = NON-GOAL) |
| role/goal/backstory persona schema | neutral-context (prompt convention, not a primitive) |
| fuzzy tool-name match (SequenceMatcher>0.85) | steal-additive (candidate) |
| periodic format-reminder re-injection | neutral-context (ReAct-text artifact) |
| "delegate: they know nothing, share everything" prompt | neutral-context (a sub-agent briefing convention) |
| string-guardrail auto-wrapped into LLMJudge-style validator | steal-additive (candidate, overlaps Verso LLMJudge) |
