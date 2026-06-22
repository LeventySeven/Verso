# AGNO — Raw Extraction Note (Verso top-1% validation)

**Source read:** `/Users/seventyleven/Desktop/researchfms/teardowns/AGNO.md` (852 lines, RE teardown of `agno==2.6.9`, repo `github.com/agno-agi/agno` @ `1444c9b`, 2026-05).
**Labels:** the teardown self-labels every claim KNOWN (`file:line`) / INFERRED / DESIGNED. I carry those labels through.

---

## 0. Core primitive (KNOWN)

> "Agno's core primitive is 'the agent is a thin dataclass; the loop lives in the Model.'" (teardown §0)

- `Agent` is `@dataclass(init=False)` with a hand-written `__init__` (`agent/agent.py:376`) that does **pure attribute assignment** (~300 fields) — no DB connect, no tool resolution, no model warmup. That is the literal mechanism behind the "≈3 µs to instantiate, ≈6.5 KiB memory" marketing claim.
- The ReAct loop lives **down in the Model base class**: `models/base.py:697` `while True:` inside `Model.response()`. `Agent.run()` calls it once. Providers subclass `Model` and inherit the loop.
- Contrast: OpenAI Agents SDK `Runner` owns the loop and calls stateless `Model.get_response()` once per turn; Agno inverts — `Model.response()` owns the whole multi-turn tool loop.

## 1. THE LOOP (KNOWN, `models/base.py:697-858`)

Two nested control structures:
- **Outer retry loop** — `agent/_run.py:395` `for attempt in range(num_attempts)`, `num_attempts = agent.retries + 1`. Re-runs whole pipeline on exception.
- **Inner ReAct loop** — `models/base.py:697` `while True:`. Real "call model → run tools → call model again."

Per-iteration: (a) mid-loop compression if token threshold crossed (`should_compress`/`compress`, `:699`); (b) one model call (`_process_model_response`); (c) if `assistant_message.tool_calls`, run them via `run_function_calls`, append `role=tool` msgs, then check break conditions.

**Termination conditions (exhaustive, from source):**
1. Model returns no tool calls → `break` (`:858`) — normal exit (final answer).
2. Tool flagged `stop_after_tool_call` → `break` (`:832`).
3. HITL pause — `requires_confirmation` (`:836`), `external_execution_required` (`:840`), `requires_user_input` (`:844`) → `break`, paused state returned.
4. Member-agent HITL propagation — `run_response.requirements` unresolved (`:850`) → `break`.
5. Tool-call limit hit — does **NOT** break; `run_function_calls` (`:2322-2328`) appends a synthetic `create_tool_call_limit_error_result(fc)` and skips real execution; model still sees an "over limit" result.

**CRITICAL (KNOWN):** "there is NO `max_turns`/`max_iterations` on the inner loop." Only hard cap is `tool_call_limit` (default `None` = unlimited, `agent/agent.py:169`). Contrast OpenAI Agents SDK `max_turns=10` default. The teardown flags this as a DESIGNED gap: "an unlimited `while True:` driven only by a tool cap can loop forever … add a turn ceiling."

`tool_call_limit` is **cumulative across loop iterations** (count passed back in each turn), so it caps total tool invocations across the whole run, not per turn (`:2310-2328`, `:810`).

Four copies of the loop kept in lockstep by hand: `response()` / `response_stream()` (`:1408`) / `aresponse()` (`:919`) / `aresponse_stream()` (`:1687`).

## 2. Tools / function-calling (KNOWN)

- Tool inputs normalized to `Function` (`tools/function.py`). Accepts: bare `Callable`, `Function`, `Toolkit`, raw `dict` (pre-formed provider schema), or a **callable factory** `tools: Callable[..., List]` returning tools at runtime.
- Schema extraction `Function.from_callable` (`tools/function.py:278-311`): docstring→description, type hints→JSON Schema. **Reserved/injected params** (`agent`, `team`, `run_context`, `images`, `videos`, `audios`, `files`) are STRIPPED from the schema the model sees, then injected at call time. So `def my_tool(query: str, agent: Agent)` shows the model only `{query}`.
- `strict` → OpenAI strict-mode JSON schema (all props required, `additionalProperties:false`).
- `@tool(...)` decorator (`tools/decorator.py`) carries HITL/control flags: `requires_confirmation`, `requires_user_input`, `external_execution`, `stop_after_tool_call`, plus `tool_hooks` (middleware). These are exactly the break conditions at `models/base.py:832-845`.
- `tool_hooks: List[Callable]` (`agent/agent.py:179`) wrap every tool call (logging/auth/caching/retries) — chain-of-responsibility middleware inside `run_function_calls`.
- Built-in HITL tools `get_user_input` / `ask_user` (`tools/user_control_flow.py`) special-cased to build `user_input_schema` and pause.
- **`Toolkit`** (`tools/toolkit.py:12`): groups Functions in `OrderedDict`. `auto_register=True` (`:33`) auto-wraps every public method; `include_tools`/`exclude_tools` allow/deny filter; `requires_confirmation_tools: list[str]` stamps HITL at bundle level; `cache_results=True` (default False) memoizes results; `add_instructions` injects usage instructions into system prompt.

## 3. Model layer + structured output (KNOWN)

- `Model` base; providers subclass and implement `invoke()`/`ainvoke()`/`invoke_stream()` + `parse_provider_response()`. **Extensibility seam:** "adding a model provider = implement invoke + parse_provider_response; you inherit the entire loop, retry, fallback, caching, and compression machinery."
- **Fallback models** (`agent/agent.py:73-76`, `models/fallback.py`): `fallback_models: List[Model|str]` + `fallback_config: FallbackConfig` (error-specific routing). `call_model_with_fallback` tries primary, walks fallbacks on failure. Wraps the whole inner loop per model.
- **Response caching** (`models/base.py:672-681`): model-level cache keyed by `_get_model_cache_key(messages, stream, response_format, tools)` when `model.cache_response`.
- **Three retry layers stacked** (`:228`): provider-invoke retry ⊂ fallback-model walk ⊂ agent-run retry.
- **Model-level retry + retry-with-guidance** (`models/base.py:228-275`): `_invoke_with_retry`, `retries=0` default (no retry unless configured). On `ModelProviderError`: `classify_error`→typed subclass, `_is_retryable_error` decides. Delay = `delay_between_retries * 2**attempt` if `exponential_backoff` else flat `1`s. **Retry-with-guidance (`:258-272`):** on `RetryableModelProviderError`, appends a corrective `Message(role="user", content=e.retry_guidance_message, temporary=True)` (`:270`) then re-invokes — self-correction injecting a corrective user turn telling the model what went wrong, capped `retry_with_guidance_limit=1`. `temporary=True` strips it from persisted history.

**Structured output — three mechanisms (KNOWN):**
1. `output_schema: Type[BaseModel]` → `response_format` to provider, native structured outputs. Parsed post-loop via `convert_response_to_structured_format`.
2. `use_json_mode=True` → prompt-engineered JSON (`get_json_output_prompt`).
3. `parser_model` / `output_model` → a SECOND model call to re-structure free text or generate final answer ("decouple thinking model from formatting model").

**Structured-output decision cascade** `get_response_format` (`agent/_response.py:876`): selects wire format per provider capability — native Pydantic class (OpenAI strict / Anthropic) / `{"type":"json_schema",...}` dict / `{"type":"json_object"}` last-resort prompt-engineered. Same `output_schema=MyModel` yields different wire formats per provider. "A replica must replicate this cascade or it will send invalid response_format to providers that don't support native structured outputs."

## 4. Context assembly (KNOWN, `agent/_messages.py::get_run_messages`)

System message built in fixed order: `description` → role/goal → `instructions` → `<additional_information>` → expected output / `markdown` flag → tool-usage instructions → `<context>` (dependencies) → `<session_state>` → memories block → session summary → `<references>` (knowledge/RAG, `references_format` json|yaml). Then **history**: last `num_history_runs` runs OR `num_history_messages` msgs, historical tool calls capped at `max_tool_calls_from_history` (`agent/agent.py:140`). Then user message + media. `SafeFormatter` does tolerant `{var}` interpolation (missing keys don't crash). "Imperative in one function rather than a processor chain."

## 5. Memory v2 — agentic, a SECOND LLM (KNOWN, `memory/manager.py`)

- "Agno's 'user memory' is **agentic**: a `MemoryManager` (its own `Model`) decides what to remember." Verbatim "You are a Memory Manager…" system prompt (`memory/manager.py:991-1034`) with `<memories_to_capture>` + `<existing_memories>`, plus tools `add_memory`/`update_memory`/`delete_memory`/`clear_memory`. Then `model.response(...)` — the model CALLS those tools to mutate the store.
- **Runs on a background `ThreadPoolExecutor(max_workers=3)`** ("agno-bg", `agent/agent.py:716-718`) CONCURRENTLY with the main model call, joined at step 14. Submitted at `_run.py:492`.
- **Agentic search** (`:665 _search_user_memories_agentic`): a second LLM call, prompt "Your task is to search through user memories and return the IDs of the memories that are related to the query." + `<user_memories>`, output-schema `MemorySearchResponse`. Plus non-agentic recency search `_get_last_n_memories` / `_get_first_n_memories`.
- Storage: `UserMemory` rows in configured `db`. **17 DB backends:** sqlite, postgres, async_postgres, mysql, mongo, redis, dynamo, firestore, singlestore, surrealdb, gcs_json, json, in_memory.
- **Session summaries** (`session/summary.py`): post-run `SessionSummaryManager` condenses session into `SessionSummary`, optionally re-injected next run.
- **Compression manager** (`compression/manager.py`, called `models/base.py:699`): `compress_tool_results=True` → consulted INSIDE the loop; `should_compress(...)` checks token threshold; if crossed, `compress(...)` rewrites/summarizes prior tool-result messages in place. Mid-conversation compaction, distinct from session summaries.
- **Background managers** (`agent/_managers.py`): THREE concurrent side-effect pipelines on the 3-worker pool: `start_memory_future`, `start_learning_future` (`LearningMachine` extracts "learnings"), `start_cultural_knowledge_future` (`CultureManager` extracts "cultural knowledge"). Each takes `existing_future` so retries reuse in-flight future. `wait_for_open_threads` joins them (also on HITL-pause early-return so background work isn't orphaned).

## 6. Knowledge / RAG (KNOWN)

- `AgentKnowledge` + vector DB (pgvector, Qdrant, LanceDB, Chroma). `add_knowledge_to_context` retrieves + folds references (`references_format` json|yaml). Agentic RAG = `search_knowledge` tool (default-on when knowledge set); `knowledge_filters` / `enable_agentic_knowledge_filters`; custom `knowledge_retriever` callable can replace default.
- **10 chunking strategies** (`knowledge/chunking/`): fixed, recursive, semantic, agentic, document, markdown, code, row. Constants: fixed/recursive/semantic/agentic `chunk_size=5000`; semantic `similarity_threshold=0.5` (split where adjacent-sentence cosine < 0.5); **agentic chunking = an LLM asked iteratively for the integer char offset to cut at** (one model call per chunk boundary — "novel and expensive").
- **Hybrid-search algebra** (`vectordb/pgvector/pgvector.py:1067-1219`): `max_results` default `10`. Two component scores blended in SQL: text `ts_rank_cd` squashed `x/(x+0.1)`; vector per metric (cosine `1-dist` clamped 0 / l2 `1/(1+d)` / inner-product `(ip+1)/2`); `hybrid_score = vector_score_weight*vector + (1-w)*text`, **`vector_score_weight` default `0.5`** (`:62`). Empty tsquery → text_rank=0, vector drives. IVFFlat/HNSW index hints as session-locals.
- **Rerank pass** (`knowledge/reranker/`) after retrieval in all three search types, best-effort (returns original list on any error): CohereReranker (`rerank-multilingual-v3.0`), SentenceTransformerReranker (`BAAI/bge-reranker-v2-m3` CrossEncoder), aws_bedrock, infinity.

## 7. Streaming protocol + EXACT event names (KNOWN, `run/agent.py:146-191`)

Typed `RunOutputEvent` objects (SSE/WebSocket is transport detail). Full enum (constant→wire):
- Lifecycle: `RunStarted`, `RunContent`, `RunContentCompleted`, `RunIntermediateContent`, `RunCompleted`, `RunError`, `RunCancelled`, `RunPaused`.
- Hooks: `pre_hook_started/completed`, `post_hook_started/completed`.
- Tools: `ToolCallStarted`, `ToolCallCompleted`, `ToolCallError`.
- Reasoning: `reasoning_started`, `ReasoningStep`, `ReasoningContentDelta`, `reasoning_completed`.
- Memory: `memory_update_started/completed`. Session summary: `session_summary_started/completed`.
- Parser/output model: `parser_model_response_started/completed`, `output_model_response_started/completed`.
- Model request: `model_request_started/completed`. Compression: `compression_started/completed`. Followups: `followups_started/completed`.
- `RunPaused` is the HITL-exit event matching loop breaks. Content deltas carry `content_type` (default `"str"`).

## 8. State + durability + HITL resume (KNOWN)

- Persistence via `db`: `AgentSession` rows (history + session_state), `UserMemory`, `SessionSummary`. `session_state` dict merged across runs (`overwrite_db_session_state=True` replaces). `enable_agentic_state=True` gives model tools to mutate `session_state` mid-run. `cache_session=True` keeps session in `_cached_session` to skip DB read.
- **Cooperative cancellation** (HEAD commit): `register_run(run_id)` + `raise_if_cancelled(run_id)` checkpoints (`:430,:515,:521,:540`); `_handle_run_cancellation` persists `RunCancelled`. "Cooperative cancellation, not preemption."
- **Session read-or-create** (`agent/_storage.py:288-345`): cache check → DB read (only if `db AND team_id is None AND workflow_id is None` — sub-agents don't own sessions) → create fresh `AgentSession` with **deepcopy** of session_state → introduction seeding → cache write.
- **HITL resumption `continue_run`** (`agent/agent.py:1498-1560`): loop breaks → paused `RunOutput` whose `requirements`/`tools` carry pending `ToolExecution`s. Caller flips `confirmed=True` / fills `result` / sets input, re-enters via `continue_run(updated_tools=...)` which splices resolved results back into history and **re-enters the SAME `Model.response()` loop**. `run_id` preserved — same state machine re-entered, not a new run. Async `acontinue_run`. Team propagates member pauses up via `run_response.requirements`.
- **Storage schema** (`db/postgres/schemas.py`): JSONB-heavy, BigInteger epoch timestamps. **KEY FACT:** "runs are stored inline on the session as a JSONB array" (`runs` column) — no separate runs table, no join; loading a session loads its entire run history in one read (why `cache_session` is cheap, why long sessions inflate the row). Sibling tables: EVAL, KNOWLEDGE (status/access_count/external_id), METRICS (daily aggregation, token_metrics/model_metrics JSONB, uq_metrics_date_period), CULTURAL_KNOWLEDGE, VERSIONS (per-table schema versioning), TRACE/span (OTel-style, ISO-8601, duration_ms).

## 9. Multi-agent — the Team (KNOWN, `team/`) — [overkill-flag candidate]

- `Team` = leader agent + member agents (`Agent` or nested `Team`). **Same loop-in-Model architecture** — `team/_run.py:1198` also calls `call_model_with_fallback`, leader runs the identical `models/base.py:697` loop.
- Coordination = a **delegation tool**: `delegate_task_to_member(member_id: str, task: str)` (`team/_default_tools.py:594`) runs the member and feeds its `RunOutput` back as the tool result. `get_member_information` exposes the roster. `respond_directly` short-circuits (route).
- "Multi-agent in Agno = the leader's tool loop, where one tool is 'run another agent'." Same primitive as OpenAI agent-as-tool.
- **FOUR modes** (correction; `team/mode.py:12-23`):
  - `coordinate` (default): "supervisor pattern. Leader picks members, crafts tasks, synthesizes responses."
  - `route`: "router pattern. Leader routes to a specialist and returns the member's response directly."
  - `broadcast`: "delegates the same task to all members simultaneously."
  - `tasks`: "autonomous task-based execution. Leader decomposes goals into a shared task list, delegates tasks, loops until all work complete." — architecturally distinct: does NOT register delegation tool, loads `_get_task_management_tools` over a persisted task list.
- Mode→behavior is implemented by THREE orthogonal flags, not a `match`: `respond_directly`=route (also pushes team `output_schema` onto member), `delegate_to_all_members`=broadcast (tool name → plural `delegate_task_to_members`), `determine_input_for_members` (raw input vs leader-crafted task).
- Member streams events upward (sets `parent_run_id`) but swallows terminal RunOutput; `child_run_id` stitched into leader's tool-call record so trace tree links leader→member. Broadcast fan-in via `asyncio.Queue`, pauses propagated sequentially after all complete.

## 10. Workflow engine — third execution primitive (KNOWN, `workflow/`) — [overkill-flag: graph-DSL]

"Agno has THREE top-level execution objects: `Agent`, `Team`, and `Workflow`." A Workflow is a **deterministic step graph** ("the antithesis of the model-driven `while True`") — control-flow primitives execute steps, not an LLM. Five primitives:
- `Step` (`workflow/step.py:103`): executor is `Union[Agent, Team, Callable, Function]` — a step can BE an agent/team/function.
- `Steps` (sequential chain), `Parallel` (fan-out, collect StepOutputs), `Condition` (predicate callable OR CEL string), `Loop` (repeat until `end_condition` or `max_iterations: int = 3` default — bounded, unlike agent loop), `Router` (dynamic dispatch via selector callable / CEL / HITL).
- **CEL (Common Expression Language)** embedded so branching is data-driven and **serialized** (workflows are JSON-round-trippable; agents/teams with code aren't). e.g. `'input.contains("video") ? "video_step" : "image_step"'`.
- "Agno gives you BOTH paradigms under one roof … the LangGraph-style graph that the base Agent deliberately lacks."

## 11. Reasoning (KNOWN)

- `reasoning=True` runs a separate reasoning agent before main call (`_run.py:518`). Default reasoning agent (`reasoning/default.py:27`) = full `Agent` with `output_schema=ReasoningSteps`, 6-step structured prompt. `ReasoningStep.next_action ∈ {continue, validate, final_answer}` + `confidence: float` 0.0–1.0. Bounds `reasoning_min_steps=1` / `reasoning_max_steps=10`.
- **Two control-flow paths** (`reasoning/manager.py:1012`): native-reasoner detection (deepseek/anthropic-thinking/openai-o-series/etc., priority cascade) → pull model's own trace into one `ReasoningStep`, no loop. Else **manual CoT** (`run_default_reasoning`, `:790`): bounded re-invocation `while next_action==CONTINUE and step_count<max_steps` — each iteration a complete reasoning-agent run emitting `ReasoningSteps`. `NextAction` 4-value enum `CONTINUE|VALIDATE|FINAL_ANSWER|RESET`; `get_next_action` defensively coerces unknown → `FINAL_ANSWER`. Accumulated CoT spliced into main context.
- **`ReasoningTools`** (`tools/reasoning.py:10`, a Toolkit): in-band reasoning via tool calls (no separate agent). `think(title, thought, action, confidence=0.8)` = scratchpad ("never revealed to the user"), appends to `session_state["reasoning_steps"][run_id]`, returns the FULL accumulated step list each call. `analyze(title, result, analysis, next_action, confidence=0.8)`. "Cheaper alternative — one agent, the normal tool loop, reasoning is just two tools writing into session state."

## 12. Guardrails (KNOWN, `guardrails/`)

`BaseGuardrail.check(run_input)` run as a **pre-hook**; raising `InputCheckError` aborts before model call. Four built-ins:
- `PromptInjectionGuardrail`: substring match against verbatim list ("ignore previous instructions", "jailbreak", "system prompt", …). "Naive `any(keyword in input.lower())` — easily bypassed; a replica should upgrade to a classifier."
- `PIIDetectionGuardrail`: regex (SSN `\b\d{3}-\d{2}-\d{4}\b`, credit card, email, phone), `mask_pii=True` masks instead of raising, `custom_patterns` extends.
- `OpenAIModerationGuardrail`: calls OpenAI moderation endpoint.

## 13. AgentOS (KNOWN, `os/app.py`)

`AgentOS` = FastAPI app wrapping agents/teams/workflows into a deployable server. Composed lifespans: `db_lifespan`, `scheduler_lifespan`, MCP lifespan. Routers: base/info/**websocket** (runs stream over WebSocket). `run_hooks_in_background=True` → hooks as FastAPI background tasks. Auth, middleware, config. "The deploy half — same engine, exposed as HTTP+WS."

## 14. Eval framework (KNOWN, `eval/`)

`BaseEval` importable into pre_hooks/post_hooks. THREE eval types: **accuracy** (LLM-as-judge vs reference), **performance** (latency/cost — powers the instantiation benchmark), **reliability** (did the agent call expected tools / produce valid output). "Because evals can be attached as post-hooks, an agent can self-score every production run." The performance eval "literally times `Agent(...)` construction" — the harness behind "~3 µs instantiate / ~6.5 KiB."

## 15. Performance claims (KNOWN — the headline)

- "agents instantiate in ~3 µs and use ~6.5 KiB."
- Mechanism (entirely in the constructor): `@dataclass(init=False)`, hand-written `__init__` = pure attribute assignment (~300 fields) + one `_init.get_models(self)` that only normalizes string→Model (no network/warmup). NO DB connection, NO tool resolution, NO MCP connect, NO toolkit expansion, NO factory invocation at construction. Lazy `@property` for `background_executor` and `learning_machine`.
- "'instantiation' measures only Python attribute writes on a dataclass — everything expensive is deferred to the first `run()`. This is the entire trick: the constructor is a no-op; the cost moves to run-time." Teardown caveat: "fair benchmark for `Agent(...)` but the first `run()` pays the deferred cost."

## 16. Full per-run call budget (KNOWN, §E18)

One `Agent.run()` at max config: (1) optional reasoning-agent run (≤10 steps); (2) N main-loop turns (bounded only by model stopping or tool_call_limit, mid-loop compression); (3) optional parser_model + output_model + followups calls; (4) 3 concurrent background runs (memory/learning/culture). "Potentially 6+ distinct model invocations for one user turn." All wrapped in invoke-retry ⊂ fallback-walk ⊂ run-retry.

## Constants table (KNOWN)

| Constant | Value | Source |
|---|---|---|
| Inner agent loop cap | none (`while True`) | `models/base.py:697` |
| `tool_call_limit` default | `None` (unlimited) | `agent/agent.py:169` |
| Retry attempts | `retries+1` | `_run.py:394` |
| `reasoning_min/max_steps` | `1`/`10` | `agent/agent.py:194-195` |
| Background executor workers | `3` | `agent/agent.py:718` |
| Model `retries` | `0` | `models/base.py:172` |
| `retry_with_guidance_limit` | `1` | `models/base.py:181` |
| Workflow `Loop.max_iterations` | `3` | `workflow/loop.py:75` |
| Chunk size | `5000` | chunking |
| Semantic `similarity_threshold` | `0.5` | `chunking/semantic.py:74` |
| RAG `max_results` | `10` | `knowledge/knowledge.py:49` |
| Hybrid `vector_score_weight` | `0.5` | `pgvector.py:62` |
| DB backends | 17 | `db/` |

---

## Verso relation summary
- Verso ALREADY has: ReAct-loop-as-core, @tool docstring→schema, injected/stripped params, structured output + reask, per-tool timeout/max_attempts, HITL pause/resume (idempotent), durable checkpoint/resume in fresh process, typed streaming events, evals-as-first-class (unit/judge + OTel spans), typed memory + temporal recall + reflect consolidation, RRF retrieval, hooks (pre/post model+tool), failover+retry-policy, OpenAI-compatible base_url, MCP-as-opt-in-adapter.
- Verso must REFUSE: Team multi-agent modes (orchestrator-as-primitive), Workflow/CEL graph-DSL (NON-GOAL: "we don't force the graph"), background learning/culture managers (~1% complexity), unbounded `while True` (Verso already bounds via max_steps).
- Genuinely missing & possibly additive: retry-with-guidance (corrective `temporary=True` user turn on retryable provider error), and possibly the *labeling* of compression as an in-loop opt-in (Verso has prune()/max_context_tokens; the "should_compress token-threshold mid-loop" hook is a near-cousin but LLM-summarization-compaction-by-default is a NON-GOAL).
