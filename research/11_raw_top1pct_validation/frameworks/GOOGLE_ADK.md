# GOOGLE ADK — Raw Extraction (frameworks track)

**Source read:** `/Users/seventyleven/Desktop/researchfms/teardowns/GOOGLE_ADK.md` (648 lines, full read).
**ADK versions in source:** `google-adk==1.33.0` (Python, 2026-05-08, commit `bd062ec9`); Round-2/3 re-clone at HEAD `4006fe4` = `google-adk==2.0.0`; Java `com.google.adk:google-adk:1.3.0`; A2A `v1.0.0` GA.
Labels below: KNOWN (file:line cited in source) vs INFERRED.

---

## 1. Agent / loop primitive (KNOWN)

- ADK = **tree of agents executed by a shared async-generator event stream**. Every agent is `async def run_async(ctx) -> AsyncGenerator[Event]`. "No graph engine, no scheduler, no message bus — just nested `async for` over generators sharing one `InvocationContext`." Java mirror = RxJava `Flowable<Event>`.
- The loop is `base_llm_flow.py:851` — `while True:` (`:855`); each iteration = `_run_one_step_async` = ONE LLM call (`:866`/`:870`). Terminate when `last_event.is_final_response() or last_event.partial` (`:861`).
- `is_final_response()` (`event.py:268-272`): final iff `actions.skip_summarization or long_running_tool_ids` set, OR event has **no function calls and no function responses**. = same ReAct termination as everyone, expressed through Event stream.
- **No tool-iteration cap.** Hard ceiling `max_llm_calls=500` (`agents/run_config.py:314`). Loop continues purely because function-response events are not `is_final_response()`.
- SingleFlow vs AutoFlow: the SINGLE most-cited architectural fact — single-agent vs multi-agent app differ by **exactly one appended request processor** (`agent_transfer`).

## 2. Request-processor pipeline (KNOWN, exact) — the ADK primitive

`single_flow.py:36-69` — ordered list mutating a shared `LlmRequest`:
1. `basic` — model + generate_content_config
2. `auth_preprocessor` — inject auth/credentials
3. `instructions` — agent.instruction + global_instruction → system
4. `identity` — agent name/description → system (`identity.py:37`: `You are an agent. Your internal name is "{name}".`)
5. `contents` — assemble history (after compaction)
6. `_nl_planning` — PlanReActPlanner scaffold (after contents)
7. `_code_execution` — code executor (after contents, mutates data files)

`AutoFlow = SingleFlow + [agent_transfer.request_processor]` (`auto_flow.py:44`) — the ONLY difference. Flow selection (`llm_agent.py:801-809`): SingleFlow iff `disallow_transfer_to_parent and disallow_transfer_to_peers and not sub_agents`, else AutoFlow.

## 3. Tool system (KNOWN)

- **Default schema path is a MANUAL type parser** `_function_parameter_parse_util._parse_schema_from_parameter`, NOT pydantic `model_json_schema()` (the pydantic path is gated by `FeatureName.JSON_SCHEMA_FOR_FUNC_DECL`, default_on=False).
- `FunctionTool` (`function_tool.py`): docstring via `inspect.cleandoc(func.__doc__)` (`:76`); context param detected by **type annotation first, then literal name `'tool_context'`** (`:88`); `_ignore_params=['tool_context','input_stream']` stripped from model-visible schema; re-injected at call time `args_to_call[ctx_param]=tool_context` (`:223`).
- **Parallel tool dispatch by default**: `tasks=[__call_tool_async(...) for fc in filtered_calls]` (`functions.py:442`), `await asyncio.gather(*tasks)` (`:447`), `merge_parallel_function_response_events` (`:463`). Sync tool run in new loop via `asyncio.run` (`:210-215`).
- **6-step callback pipeline per tool** (`functions.py:550-620`): plugin-before → canonical-before (list, first-truthy wins) → call → on_tool_error → plugin-after → canonical-after. Non-None return short-circuits.
- `LongRunningFunctionTool` = `FunctionTool` with `is_long_running=True` (`long_running_tool.py:45`) → keeps call open across turns (resumability/HITL).
- `OpenAPIToolset`: REST spec → N callable `RestApiTool`s, schema auto-derived per operation (`operation_parser.get_json_schema()`), executed over `httpx.AsyncClient.request`.
- `AgentTool`: wraps agent as tool → spins **brand-new isolated Runner + fresh InMemorySessionService**, returns final text. (vs `transfer_to_agent` = same session, no return.)
- Built-in tools: `google_search`, `built_in_code_execution`, `vertex_ai_search_tool`, `load_memory`/`preload_memory`, `load_artifacts`, `get_user_choice`, `transfer_to_agent`, `exit_loop`.
- MCP: ADK is primarily an MCP **consumer** (stdio/SSE/Streamable HTTP); `adk_to_mcp_tool_type` is the only ADK→MCP-server bridge.

## 4. Session / state / runner (KNOWN)

- **Runner is the SOLE persister** (`runners.py:834-966`): persists ONLY non-partial events (`:954`), applies `EventActions.state_delta` at append time. Agents never touch storage.
- State prefixes (`sessions/state.py:64-66`): `app:` (cross-session per app), `user:` (cross-session per user), `temp:` (single invocation, NEVER persisted), bare = session-scoped. `extract_state_delta` (`_session_util.py:37-49`) partitions one flat delta into 3 stores by prefix; `temp:` keys SILENTLY DROPPED (fall through both branches). Re-prefixed back to flat dict on read (`_merge_state`).
- SessionService backends: `InMemorySessionService`, `DatabaseSessionService`, `SqliteSessionService` (new v2), `VertexAiSessionService` (managed). SQL V1 schema = 4 tables (sessions/events/app_states/user_states), composite PKs, FK CASCADE, optimistic-concurrency `_storage_update_marker` + per-session `asyncio.Lock`.
- **Resumability (v2)**: pause/resume of long-running-tool + HITL flows via `InvocationContext.is_resumable` + per-agent `agent_state` checkpoints. HITL via `requested_tool_confirmations` → synthetic `adk_request_confirmation` (`functions.py:59`); auth via `requested_auth_configs` → `adk_request_credential`. Run suspends, caller resolves, `Runner.run` resumes from checkpoint.

## 5. EventActions side-channel (KNOWN, `event_actions.py:52-120`)

One event stream + one actions bag: `skip_summarization`, `state_delta`, `artifact_delta`, `transfer_to_agent`, `escalate` (stop LoopAgent), `requested_auth_configs`, `requested_tool_confirmations`, `compaction`, `end_of_agent`/`agent_state` (v2 resume checkpoints), `rewind_before_invocation_id` (v2 rewind/replay), `route`/`render_ui_widgets`/`set_model_response` (v2).

## 6. Workflow agents (KNOWN) — deterministic orchestration

- `SequentialAgent` (`sequential_agent.py:69-89`): for-loop over `sub_agents[start_index:]`, resumable via `SequentialAgentState`.
- `ParallelAgent` (`parallel_agent.py:177-221`): concurrent + **branch isolation** (each sub-agent own `branch`, histories don't bleed) but share `session.state` (shallow model_copy → concurrent same-key writes RACE).
- `LoopAgent` (`loop_agent.py:83-137`): `while times_looped < max_iterations and not escalate/pause`. Terminate via (1) `max_iterations` (`None`=unbounded default `:75`), (2) sub-agent `actions.escalate=True`, (3) pause. `exit_loop` tool sets escalate.

## 7. Models (KNOWN)

- `LLMRegistry` regex→class, `@lru_cache(maxsize=32)`. Default model `gemini-2.5-flash` (`google_llm.py:115`).
- Resolution (`registry.py:130-158`): (1) explicit `prefix:model` override (`_match_prefix` strips trailing "llm", lowercase) bypasses regex; (2) `re.compile(regex).fullmatch`; lazy `importlib.import_module` + memoize.
- Native vs LiteLlm fork is a pure regex decision: `gemini-*`→native `Gemini`; `gpt-*`/`o1-*`/`o3-*`→ADK labs `OpenAILlm`; `openai/*`,`azure/*`,`anthropic/*`,`bedrock/*`,`groq/*`,`mistral/*`,`deepseek/*`,…→`LiteLlm` (~2,503-line translation wrapper, the largest file); `claude-3-*`/`claude-*-4*`→`Claude` (`anthropic_llm.py`).
- `model` field accepts a string OR a `BaseLlm` instance.

## 8. Callbacks (KNOWN) — six points

{before, after} × {agent, model, tool}. Each = single callable or list (`canonical_*_callbacks`). Order = **plugin → agent-callbacks (list, first-wins) → real work**. Rule: non-None return short-circuits/overrides. `before_model_callback` truthy ⇒ skip model call entirely (`:225-226`).

## 9. Planners (KNOWN)

- `BuiltInPlanner` (`built_in_planner.py`): native-thinking models; only sets `llm_request.config.thinking_config`. No prompt scaffold, no parsing.
- `PlanReActPlanner` (`plan_re_act_planner.py`): model-AGNOSTIC. 5 tags `/*PLANNING*/ /*REPLANNING*/ /*REASONING*/ /*ACTION*/ /*FINAL_ANSWER*/`. Re-planning is prompt-driven (model emits `/*REPLANNING*/` on failure), not a Python loop. Tag parser splits on last `/*FINAL_ANSWER*/`.

---

## 10. ★ EVAL SURFACE (KNOWN — §2.13 / `05` §3) — the comparison target

ADK ships an eval framework as its "training analogue" (ADK doesn't train models). From the source:

- **Eval set format**: `.evalset.json` / `.test.json` — pydantic models `EvalSet` / `EvalCase` / `Invocation` / `IntermediateData`.
- **12 metrics total.** Named key metrics:
  - **`tool_trajectory_avg_score`** — trajectory match, with **EXACT / IN_ORDER / ANY_ORDER** algorithms.
  - **`response_match_score`** — **ROUGE-1** (lexical overlap of final response vs reference).
  - **`final_response_match_v2`** — (newer final-response match).
  - **`rubric_based_final_response_quality_v1`** — rubric-scored final-response quality (LLM-as-judge).
  - **hallucination segmenter/validator** — LLM-as-judge; **judge prompts reproduced verbatim in `05` §3** (the raw notes, not in this teardown body).
- **Runners**: `pytest` integration + `adk eval` CLI + **eval UI inside `adk web`**.

### Verso comparison (eval wedge)

Verso eval primitives present: `Eval.unit/judge/pass_k/best_of_n/calibrate/predicts/bucket/lift/from_trace`; `TrajectoryCheck (exact/in-order/any-order)`; `LLMJudge(examples=)` few-shot; `Assertion`; `VersoSpan+OTel`; "prod==eval, captured failure IS a regression test."

| ADK eval primitive | Verso equivalent | Verdict |
|---|---|---|
| `tool_trajectory_avg_score` (EXACT/IN_ORDER/ANY_ORDER) | `TrajectoryCheck(exact/in-order/any-order)` | Verso already has — same three algorithms. |
| `response_match_score` (ROUGE-1) | Verso has judge/unit/Assertion but **no named lexical ROUGE-1 metric** | Minor; ROUGE-1 is a cheap deterministic string metric. Additive-but-low-value. |
| `rubric_based_final_response_quality_v1` (rubric judge) | `LLMJudge` | Verso has LLM-judge; rubric is a judge-prompt convention. |
| hallucination segmenter/validator (verbatim judge prompts) | `LLMJudge(examples=)` | Verso has few-shot judge; ADK ships specific hallucination judge prompts. Content, not primitive. |
| `.evalset.json` / `EvalCase`/`Invocation`/`IntermediateData` schema | `Eval.from_trace`, captured-failure-as-regression | Verso captures from trace; ADK has a file format. Equivalent goal. |
| eval UI in `adk web` | (Verso has no GUI; non-goal — not an SDK/product surface) | Avoid-overkill / out of scope. |
| 12-metric registry | Verso's composable Eval/Assertion/judge | ADK pre-packs a fixed catalog; Verso composes. Neutral. |

**Net: ADK has NO eval primitive Verso structurally lacks.** Trajectory (3 algos), LLM-judge, rubric, captured-trace-as-test — all present in Verso. ADK's edges are (a) ROUGE-1 as a named lexical metric, (b) a shipped hallucination-judge prompt pack, (c) a GUI eval surface (out of scope / non-goal). None clears the steal-additive bar except possibly a tiny deterministic ROUGE-1 metric, which is low value.

---

## 11. A2A / deployment (KNOWN, neutral context)

- A2A v1.0.0 GA (Linux Foundation, proto `lf.a2a.v1`): 11 RPC methods × 3 bindings (JSON-RPC/gRPC/REST); 9 `TaskState` values; `.well-known/agent-card.json` discovery. ADK implements both sides (server `A2aAgentExecutor`, client `RemoteA2aAgent`). A2A = agent↔agent; MCP = agent↔tool. (Verso non-goals: not an SDK, not graph-DSL, not MCP-first; A2A multi-agent-protocol is out of Verso scope.)
- Deploy: `adk deploy cloud_run` (Dockerfile + FastAPI), Vertex AI Agent Engine (source-based, NOT pickle), Agentspace/"Gemini Enterprise" consumption surface.
- `adk api_server` FastAPI: `/run`, `/run_sse` (SSE `data: {json Event}\n\n`), `/run_live` (websocket BIDI), session CRUD.

## 12. Exact constants (KNOWN)

`max_llm_calls=500`; default model `gemini-2.5-flash`; live reconnect ≤5; MCP connect 5.0s / sse_read 300s; OpenAPI tool-name cap 60 chars; plugin-close 5.0s; toolset-close 10.0s; LLMRegistry `lru_cache(32)`; streaming modes NONE/SSE/BIDI (default NONE); `ADK_ENABLE_PROGRESSIVE_SSE_STREAMING` default ON.
