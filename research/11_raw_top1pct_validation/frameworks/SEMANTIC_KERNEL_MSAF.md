# Semantic Kernel + Microsoft Agent Framework — Raw Extraction

Sources (read in full):
- `/Users/seventyleven/Desktop/researchfms/teardowns/SEMANTIC_KERNEL.md` (1352 lines)
- `/Users/seventyleven/Desktop/researchfms/teardowns/MS_AGENT_FRAMEWORK.md` (357 lines)

Labels mirror the teardowns: **KNOWN** = read in source by the teardown author; **INFERRED**/**DESIGNED** = teardown's own inference. Verso-state tags are mine.

---

## PART A — SEMANTIC KERNEL (semantic-kernel, installed v1.8.0, master v1.42.0; MIT; Python >=3.10,<3.13)

### A.1 The Kernel (central primitive) — KNOWN
`Kernel` composes 4 mixins: `KernelFilterExtension + KernelFunctionExtension + KernelServicesExtension + KernelReliabilityExtension` (`kernel.py`). Holds:
- `plugins: dict[str, KernelPlugin]` — collections of named `KernelFunction`s
- `services: dict[str, AIServiceClientBase]` — LLM/embedding clients keyed by `service_id` (default `"default"`, `const.py: DEFAULT_SERVICE_NAME = "default"`)
- `ai_service_selector: AIServiceSelector`
- three filter chains: `function_invocation_filters`, `prompt_rendering_filters`, `auto_function_invocation_filters`
- `retry_mechanism` (exponential backoff for transient HTTP)
`Kernel.invoke(function|(name,plugin), arguments)` (`kernel.py:167-206`): `get_function(plugin_name, function_name)` (`:199`) then `await function.invoke(kernel=self, arguments=...)` (`:202`).

**VERSO TAG: avoid-overkill.** Verso's thesis is NO central kernel/DI registry; ContextBundle + @tool + init_model are the flat primitives. The Kernel-as-registry is exactly the "do not force the graph / no orchestrator-as-primitive" anti-pattern.

### A.2 Three-layer abstraction — KNOWN
1. `Kernel` (registry). 2. `KernelFunction` — `KernelFunctionFromMethod` (wraps `@kernel_function(name,description)` Python fn) or `KernelFunctionFromPrompt` (templated prompt). Both `invoke(kernel, arguments) → FunctionResult`. 3. `Agent` (KernelBaseModel: id/name/description/instructions/kernel/channel_type) → `ChatCompletionAgent` / `OpenAIAssistantAgent` / `AzureAIAgent` / `BedrockAgent` / `CopilotStudioAgent`.

`fully_qualified_name` = `plugin_name-function_name` (delimiter `-`). This is what the LLM sees.

### A.3 The agent loop is NOT in the agent — KNOWN
`ChatCompletionAgent.invoke` (`chat_completion_agent.py:79-130`) just injects the system prompt and calls `chat_completion_service.get_chat_message_contents(chat_history, settings, kernel=self.kernel)`. **The tool-calling loop lives in the PROVIDER CONNECTOR**, which calls back into `kernel.invoke_function_call(...)`. Each connector (`open_ai/services/open_ai_chat_completion.py` etc.) has its OWN auto-invoke loop with its own provider tool-schema translation.

Connector loop shape:
```
loop {
  response = await client.chat.completions.create(messages, tools, ...)
  if tool_calls AND function_choice_behavior.auto_invoke:
     for tc: await kernel.invoke_function_call(tc, chat_history)
     continue
  else: return
}
```
**VERSO TAG: avoid-overkill** (loop-per-connector, duplicated across providers). Verso has ONE loop in core/loop.py; adapters only translate I/O. SK's design is the thing Verso explicitly refuses.

### A.4 `kernel.invoke_function_call` — error taxonomy (KNOWN, `kernel.py:321-411`)
Validation steps, each emitting a **model-visible error string** (not an exception) into chat_history and bailing:
1. Malformed args → `"The tool call arguments are malformed. Arguments must be in JSON format. Please try again."`
2. Function not found / not in allowed list → `"The tool call with name \`{name}\` is not part of the provided tools..."`
3. Missing required params (counts `is_required` params) → error listing required args.
Tool exception inside `_inner_auto_function_invoke_handler` (`kernel.py:413-426`) → wrapped as `"An error occurred while invoking the function {fqn}: {exc}"` result string. **Pattern: tool exceptions never propagate; become recoverable model-visible strings.**

**VERSO TAG: verso-already-has** — Verso's jsonish 4-stage parse waterfall + coerce + per-tool max_attempts + tool errors fed back to model cover this.

### A.5 `context.terminate = True` — the handoff/return-direct signal (KNOWN)
`invoke_function_call` returns `invocation_context if invocation_context.terminate else None` (`kernel.py:411`). A filter sets `context.terminate=True` to break the connector loop. This is SK's `return_direct` / handoff mechanism.

**VERSO TAG: verso-already-has** — Verso has done() tool termination + StopReason. The terminate-flag-via-filter is just a different wiring of "tool ends the loop."

### A.6 Filter pipeline (THE novel SK idea) — KNOWN (`filters/filter_types.py:12-14`)
```python
class FilterTypes(str, Enum):
    FUNCTION_INVOCATION = "function_invocation"        # wraps any kernel fn call
    PROMPT_RENDERING = "prompt_rendering"              # wraps prompt template render
    AUTO_FUNCTION_INVOCATION = "auto_function_invocation"  # wraps LLM tool calls
```
Each filter `async def filter(context, next): ...await next(context)...`. Compose via `construct_call_stack(filter_type, inner_function)` — **ASP.NET-Core / express middleware onion**. Confirmed still exactly 3 types in v1.42 master (`§R2.8`); no 4th. Used for: logging, cache, retry, A/B, PII redaction, tool gating, arg mutation, loop termination (handoff).

**VERSO TAG: verso-already-has.** Verso's Hooks(pre/post_model, pre/post_tool, on_stop, ask, should_continue) ARE this middleware, with explicit named seams instead of a generic onion. The 3-type onion is more generic but Verso's typed hooks are on-thesis; do not add a generic filter-stack.

### A.7 Stepwise Planner — KNOWN (`planners/function_calling_stepwise_planner/`)
Two-stage. Stage 1 `generate_plan.yaml`: temperature 0, top_p 0, max_tokens 256 (deterministic plan gen). Stage 2 `step_prompt.txt`. Then execution loop:
```python
max_iterations = 15
min_iteration_time_ms = 100   # sleep BETWEEN steps to dodge rate limits
max_tokens_ratio = 0.1        # 10% completion / 90% prompt budget split
```
Loop sentinel: LLM calls `UserInteraction-SendFinalAnswer` to signal done. Uses `FunctionChoiceBehavior.Auto(auto_invoke=False)` so planner controls each call manually. **[CORRECTION 2026-05-30] Python SK planners are GONE** — no `semantic_kernel/planners/` in current tree; survive only under `dotnet/`. Migration path: planners → `FunctionChoiceBehavior.Auto` (native function-calling does planning). Handlebars planner = .NET-only historical.

**VERSO TAG: avoid-overkill** (the explicit plan-then-execute planner). NON-GOAL: "not a router/planner cult." BUT one durable detail worth noting: `min_iteration_time_ms = 100` sleep between iterations as a quiet rate-limit guard.

### A.8 Multi-agent — two generations (KNOWN)
**Gen 1 `AgentGroupChat`** (v1.8): strategy-pattern duo.
- Selection: `SequentialSelectionStrategy` (round-robin `(i+1)%len`), `KernelFunctionSelectionStrategy` (LLM-as-picker via template vars `DEFAULT_AGENT_VARIABLE_NAME="_agent_"`, `DEFAULT_HISTORY_VARIABLE_NAME="_history_"`).
- Termination: `DefaultTerminationStrategy(maximum_iterations=1)`, base `TerminationStrategy(maximum_iterations=99)`, `KernelFunctionTerminationStrategy` (LLM-as-judge), `AggregatorTerminationStrategy` (AND/OR combine).
- Loop default 99 iters.

**Gen 2 `orchestration/` module** (v1.42), 5 patterns on an autogen-style actor runtime:
| File | LOC | Pattern |
|---|---|---|
| concurrent.py | 247 | fan-out → collect |
| sequential.py | 205 | pipeline A→B→C |
| group_chat.py | 530 | actor-based group chat |
| handoffs.py | 530 | transfer_to_X + filter terminate |
| magentic.py | 911 | Magentic-One orchestrator+ledger+workers |

**VERSO TAG: avoid-overkill.** NON-GOAL territory (orchestrator-as-primitive, graph-DSL). Verso composes agents as plain tools/functions, no strategy-pattern coordination layer.

### A.9 HandoffOrchestration mechanism — KNOWN (`agents/orchestration/handoffs.py`)
Per-agent `agent.kernel.clone()` (line 175, so handoff plugins don't leak). For each allowed target, synthesize a `transfer_to_<name>()` `KernelFunctionFromMethod` with `parameters=[]` (zero-arg), `return_parameter type_="None"`, `plugin_name=HANDOFF_PLUGIN_NAME="Handoff"`, `method=partial(self._handoff_to_agent, name)`. Plus a `complete_task(task_summary: str)` tool on every agent. Register filter:
```python
async def _handoff_function_filter(self, context, next):
    await next(context)
    if context.function.plugin_name == HANDOFF_PLUGIN_NAME:
        context.terminate = True
```
`_handoff_to_agent` just sets `self._handoff_agent_name`. Actor then publishes `HandoffRequestMessage(agent_name=...)` to the next agent's topic. **Unique:** `human_response_function` HITL hook called after each agent response for interactive multi-turn handoff.

**VERSO TAG: avoid-overkill.** Handoff-as-synthesized-tool is a known pattern across SDKs; Verso would do this as ordinary agent-as-tool nesting, no actor pub/sub.

### A.10 Magentic-One orchestrator — KNOWN (911 LOC, 7 verbatim prompts)
Manager LLM maintains **task ledger** (facts+plan) + **progress ledger** re-evaluated each round. `MagenticContext`: `{task, chat_history, participant_descriptions, round_count, stall_count, reset_count}`. `reset()` clears chat_history + zeroes stall_count + increments reset_count, PRESERVES task/round_count/team. Config: `max_stall_count=3`, `max_reset_count=None`, `max_round_count=None`.

The signature **PROGRESS_LEDGER_PROMPT** returns strict JSON:
```json
{ "is_request_satisfied": {"reason": string, "answer": boolean},
  "is_in_loop": {"reason": string, "answer": boolean},
  "is_progress_being_made": {"reason": string, "answer": boolean},
  "next_speaker": {"reason": string, "answer": string},
  "instruction_or_question": {"reason": string, "answer": string} }
```
Every field carries `reason` (NL justification) AND `answer` (decision) — "makes debugging/auditing the orchestrator's decisions trivial — you can log the reasons." Loop: facts → plan → per-round progress-ledger → if satisfied final-answer; if in_loop OR no-progress → stall_count++; stall>=3 → reset (FACTS_UPDATE + PLAN_UPDATE prompts, reset_count++); else dispatch instruction to next_speaker.

**VERSO TAG: neutral-context** for the orchestrator (avoid-overkill: it's a heavy manager-agent). BUT the **`{reason, answer}` per-decision schema for the loop-detection / progress / done check is a genuinely durable idea** — structured self-judgment where every boolean carries an auditable reason. Verso already has stuck/doom-loop detection (StopReason.STUCK) and LLMJudge; the explicit "is_in_loop / is_progress_being_made with reasons" framing is a possible eval/judge few-shot pattern, not a new primitive.

### A.11 Processes Framework — KNOWN (`processes/`, distinct state-machine primitive)
`KernelProcessStep[TState]`, `KernelProcessStepState[TState]`, `KernelProcess`, `ProcessBuilder.add_step(...)`, `KernelProcessEvent` (Internal/Public), edges via `on_external_event("X").send_event_to(target)` / `on_event("Y").send_event_to(...)` / `.stop_process()`. Two runtimes: `local_runtime/` (in-proc), `dapr_runtime/` (distributed Dapr Actors). Declarative state-machine, separate from agents.

**VERSO TAG: avoid-overkill.** This is the explicit graph-DSL Verso's whole thesis refuses ("we don't force the graph; no 500+ nodes").

### A.12 MCP connector — KNOWN (`connectors/mcp.py`, 4 transports)
`MCPStdioPlugin`, `MCPSsePlugin`, `MCPStreamableHttpPlugin`, `MCPWebsocketPlugin` (WebSocket = 4th, more than Agents SDK/Claude SDK's 3). `await plugin.connect()` → `plugin.functions` (each MCP tool as a `KernelFunction`). `SamplingConsentCallback` gates server-initiated LLM sampling. LOG_LEVEL_MAPPING collapses MCP's 8 RFC-5424 levels → Python's 5 (notice→info, alert/emergency→critical). Content conversion Text/Image/Audio/Binary.

**VERSO TAG: verso-already-has** (MCP is opt-in adapter; NON-GOAL is MCP-first). WebSocket transport is a neutral-context detail.

### A.13 OpenAPIPlugin (signature SK pattern) — KNOWN
`OpenAPIPlugin.from_url(swagger_url)` → one `KernelFunction` per OpenAPI 3.0 operation, params from request schema, auth via middleware. Plus deprecated `OpenAIPlugin.from_url` (ChatGPT-plugin manifest).
**VERSO TAG: verso-already-has** — Verso's `tool_from_schema` (raw/MCP) covers schema→tool generation.

### A.14 Connectors / memory — KNOWN
11+ connectors (anthropic, azure_ai_inference, google, hugging_face, mistral_ai, ollama, open_ai, +bedrock/copilot_studio in master). `FunctionChoiceBehavior.Auto/Required/None_`, `filters={included/excluded plugins/functions}` to scope tools per call. `DEFAULT_MAX_AUTO_INVOKE_ATTEMPTS = 5`. Memory: `MemoryStore` ABC + 10+ vector stores (Chroma/Milvus/Pinecone/Qdrant/Redis/Weaviate/Postgres/MongoDB Atlas/AzureCognitiveSearch/Volatile). Server-side threads via `OpenAIAssistantAgent`/`AzureAIAgent`.
**VERSO TAG: verso-already-has** — adapters + per-call model swap + memory tiers + sqlite/sqlitevec.

---

## PART B — MICROSOFT AGENT FRAMEWORK (microsoft/agent-framework, main @ 2026-05-30)

> Thesis (teardown, KNOWN): **MAF merges Semantic Kernel + AutoGen into one stack.** Both are now *legacy* (ships "Migration from SK" + "Migration from AutoGen" guides, `README.md:100-101`). TWO execution primitives.

### B.1 Engine A — function-calling loop (`FunctionInvocationLayer`) — KNOWN
`_tools.py:90`:
```python
DEFAULT_MAX_ITERATIONS: Final[int] = 40                       # caps LLM round-trips
DEFAULT_MAX_CONSECUTIVE_ERRORS_PER_REQUEST: Final[int] = 3
```
`max_function_calls` caps total individual tool invocations (best-effort, checked post-batch — 20 parallel calls with limit 10 all still run). Loop `_get_response()` (`_tools.py:2376-2460`):
```python
for attempt_idx in range(max_iterations if loop_enabled else 0):  # 40
    approval = await _process_function_requests(...)    # process approvals/submit prior results
    if approval["action"]=="stop": break
    response = await super_get_response(prepped_messages, ...)   # THE MODEL CALL
    if response.conversation_id is not None: prepped_messages = []  # server holds history
    result = await _process_function_requests(response, ...)
    if result["action"]=="return": return ...           # NO function calls → DONE
    if result["action"]=="stop": mutable_options["tool_choice"]="none"  # error threshold → final turn
    elif total_function_calls >= max_function_calls: mutable_options["tool_choice"]="none"  # cap → final turn
```
Returns when model produces no function calls. **Forces a final tool-free turn (`tool_choice="none"`) after 3 consecutive errors OR hitting cap** — so pending `function_call_output` is still submitted before exit. A tool can raise a "terminate" exception carrying `term_exc.result` to stop early.

**VERSO TAG: verso-already-has.** Verso has max_steps + grace-call at max_steps (max_steps_policy) — directly analogous to MAF's forced final turn. Stuck detection covers consecutive errors. Constants differ (40 vs Verso's config) but mechanism is the same. The "force tool_choice=none for one final turn after error threshold" is a clean variant of Verso's grace-call; worth noting as confirmation, not a steal.

### B.2 Engine B — Workflow (typed Pregel/BSP graph) — KNOWN
`Runner` (`_workflows/_runner.py:30`): "run a workflow in Pregel supersteps." `run_until_convergence()` (`:78`):
```python
while self._iteration < self._max_iterations:   # default 100
    yield superstep_started
    await self._run_iteration()                 # deliver ALL queued messages
    self._state.commit()                        # COMMIT state at superstep boundary
    checkpoint()                                # checkpoint AFTER each superstep
    if not await ctx.has_messages(): break       # CONVERGENCE = no pending messages
raise WorkflowConvergenceException(...)          # if 100 iters and still messages
```
Executors (`Executor(RequestInfoMixin)`) declare typed `@handler` methods; input type → typed routing; `ctx.send_message(...)`. Edges: `SingleEdgeGroup`, `FanOutEdgeGroup`, `FanInEdgeGroup` (join), `SwitchCaseEdgeGroup` (if/elif/else by predicate), multi-selection. `WorkflowBuilder.add_edge/add_fan_out_edges/add_switch_case_edge_group/add_chain/.build()` → `graph_signature_hash`. Live-event poll 0.05s.

**VERSO TAG: avoid-overkill.** This IS LangGraph-style typed Pregel graph — exactly Verso's counter-position ("we don't force the graph; no 500+ nodes; just build agents, brutal"). The single most important "do NOT copy" item in this entire unit.

### B.3 Checkpointing + durable resume — KNOWN (`_workflows/_checkpoint.py:31-88`)
`WorkflowCheckpoint`:
```
graph_signature_hash: str            # topology hash — validates checkpoint belongs to THIS graph
checkpoint_id, previous_checkpoint_id  # chain → walk history / branch
messages: dict[str, list[WorkflowMessage]]   # superstep frontier (in-flight messages per executor)
state: dict[str, Any]                # COMMITTED state only (pending excluded)
pending_request_info_events: dict[str, WorkflowEvent]  # outstanding HITL gates → re-issued on resume
iteration_count: int
```
Checkpoint after every superstep (+superstep 0) → resume always at clean boundary, never mid-executor. `graph_signature_hash` checked on load — **cannot resume a checkpoint into a structurally different graph** (rejected). `CheckpointStorage` Protocol: `InMemoryCheckpointStorage`, `FileCheckpointStorage` (JSON envelope + base64-pickled non-JSON state → resume needs same Python classes loaded). Durable backends: `agent_framework_durabletask` / `azure-cosmos` (Azure Durable Functions + Cosmos DB).

**VERSO TAG: mostly verso-already-has** (SqliteCheckpointStore, checkpoint-each-step, resume() in fresh process, history()/fork() time-travel, repair_history resume-guard). TWO honest deltas worth noting:
- `graph_signature_hash` validation that rejects resuming into a changed topology. Verso's analog is repair_history; Verso has no graph so no topology hash needed — but the *principle* "reject a checkpoint whose code/shape changed under it" is a hardening idea (a schema/version guard on resume). **steal-additive candidate (narrow):** a checkpoint version/signature guard that refuses resume when the agent definition changed incompatibly — additive, byte-identical when unused. NOT the graph hash itself.
- `pending_request_info_events` persisted in the checkpoint so a HITL pause survives process restart. Verso's ctx.hitl.request is idempotent-up-to-request and resume() works in a fresh process — this is the same property, so verso-already-has.

### B.4 Request/response HITL ports — KNOWN (`_request_info_mixin.py:29`)
`await ctx.request_info(CustomRequest(...), ResponseType)` (`:184`) pauses, emits `request_info` WorkflowEvent (`request_id, source_executor_id, request_type, response_type`); host submits response keyed by `request_id`; delivered back as a message to a handler in the SAME executor. Typed HITL gate (distinct from agent-level tool approval).
**VERSO TAG: verso-already-has** — ctx.hitl.request pause/resume (idempotent-up-to-request).

### B.5 Tools + approval — KNOWN (`_tools.py`)
`@tool`/`tool(...)` (`:1135`) → `FunctionTool`: introspect signature + docstring (`_docstrings.py`) → JSON Schema params. `approval_mode: Literal["always_require","never_require"]` (default never). `"always_require"` → emits `function_approval_request` content the host must approve before exec. `FunctionInvocationConfiguration`: `{enabled, max_iterations, max_function_calls, max_consecutive_errors}`. Hosted tools: `get_code_interpreter_tool()`, `get_web_search_tool()`. MCP: `HostedMCPTool`.
**VERSO TAG: verso-already-has** — @tool (docstring→schema), PermissionDecision 4-valued (allow/deny/ask/defer), ask_once durable persistence, per-tool idempotent/max_attempts/timeout. MAF's binary approval_mode is LESS expressive than Verso's 4-valued PermissionDecision.

### B.6 Threads + compaction — KNOWN (`_sessions.py`, `_compaction.py`)
`AgentThread`: local `ChatMessageStore` (sentinel `LOCAL_HISTORY_CONVERSATION_ID`, `:537`, stripped before model call) OR service `conversation_id` (server holds history, send only new turn). Errors if BOTH a store AND a real conversation_id (`:658`) — one source of truth.
Compaction (`CompactionStrategy` protocol, `:51`), triggers when metric > `max_n`, trims to target:
- `SelectiveToolCallCompactionStrategy` (drop selected tool calls)
- `ToolResultCompactionStrategy` (trim/summarize old tool results)
- summarizing strategy ("summarizes oldest groups, retains newest"), tags messages `_summarized_by_summary_id`.

**VERSO TAG: mostly verso-already-has** (prune() masks old tool outputs, max_context_tokens, RRF). DELTA: MAF's `SelectiveToolCallCompactionStrategy` and `ToolResultCompactionStrategy` are distinct strategy objects. Verso's prune() masks (never silent-drops) — same spirit. NON-GOAL warning: MAF's summarizing strategy is LLM-summarization-compaction, which Verso explicitly refuses by default. So: prune/mask = verso-already-has; the LLM-summarize strategy = avoid-overkill (on the NON-GOAL list).

### B.7 Middleware — 3 layers — KNOWN (`_middleware.py`, `_agents.py:32`)
`categorize_middleware` sorts mixed list into Agent → Chat → Function (outer→inner onion). Each `async def process(context, call_next)`. `FunctionMiddleware` may return a result WITHOUT calling `call_next()` (short-circuit) — this is the approval flow mechanism. `ChatMiddleware` mutates request/response (caching, redaction). `AgentMiddleware` replaces whole `AgentRunResponse`.
**VERSO TAG: verso-already-has** — Hooks pre/post_model + pre/post_tool are exactly these seams, typed and named rather than a generic 3-layer onion.

### B.8 autogen-core actor substrate — KNOWN (under the orchestrations)
`SingleThreadedAgentRuntime`: single `asyncio.Queue` of envelopes — `SendMessageEnvelope` (point-to-point RPC w/ future), `PublishMessageEnvelope` (pub/sub by `TopicId`), `ResponseMessageEnvelope`. Agents registered as factories, lazily instantiated per `AgentId{type,key}`. `send_message(msg, recipient: AgentId)` (RPC) vs `publish_message(msg, topic_id: TopicId)` (broadcast). `TypeSubscription(topic_type, agent_type)`: `map_to_agent(topic_id) = AgentId(agent_type, key=topic_id.source)` — **the topic's `source` becomes the agent instance key → per-conversation agent instances fall out of topic addressing automatically.** `@message_handler` reads the method's message type hint → `target_types`; `RoutedAgent` = "typed switchboard." Intervention handlers = actor-level middleware. OTel `traceparent`/`tracestate` propagated in `EnvelopeMetadata`.
**VERSO TAG: avoid-overkill.** Full actor/pub-sub runtime — NON-GOAL (no orchestrator-as-primitive). Verso is a single async loop, not a message-passing actor system.

### B.9 Orchestrations package (AutoGen-Teams convergence) — KNOWN (`agent_framework_orchestrations`, 5954 L)
Every orchestration `.build()` returns a `Workflow` (Pregel engine). Files: `_magentic.py` 1801, `_handoff.py` 1126, `_group_chat.py` 1040, `_concurrent.py` 431, `_sequential.py` 269. GroupChat: `selection_func: async (GroupChatState) -> str` returns next-speaker id; `max_rounds` + `termination_condition` (unbounded if neither). Round-robin = a cycling selection_func; selector = LLM selection_func.
Magentic (`MagenticOrchestrator`, `_magentic.py:859`): same task-ledger/progress-ledger/`max_stall_count=3` machine as SK, ORIGINAL Magentic-One prompts preserved verbatim. `MagenticPlanReviewRequest`/`Response` = human-gated plan review via workflow request/response ports.
**VERSO TAG: avoid-overkill** (graph-compiled multi-agent teams).

### B.10 Streaming — KNOWN
Agent stream: `AgentRunResponseUpdate` chunks (text/function-call/function-result deltas). Workflow stream: `WorkflowEvent` factories — `superstep_started/completed`, `executor_invoked/completed/failed/bypassed`, `request_info`, `started/status/failed/warning/error/emit`. AG-UI protocol + DevUI local inspection; `_viz.py` renders Mermaid/Graphviz.
**VERSO TAG: verso-already-has** (typed true-delta events message/reasoning/tool.start/tool.result/done + SSE). The workflow-superstep events are graph-specific (avoid-overkill).

### B.11 Structured output — KNOWN
`response_format` carries Pydantic/JSON schema → native structured output (Azure/OpenAI) OR fallback forced tool. `_types.py` (3732 L) discriminated `Content` union: text/function_call/function_result/function_approval_request/data/uri/error.
**VERSO TAG: verso-already-has** — output_type= + in-loop reask + Retry(feedback) + output validators (Verso's reask is MORE than MAF's static response_format).

### B.12 Exact constants table — KNOWN
| Constant | Value | Source |
|---|---|---|
| DEFAULT_MAX_ITERATIONS (FC loop) | 40 | `_tools.py:90` |
| DEFAULT_MAX_CONSECUTIVE_ERRORS_PER_REQUEST | 3 | `_tools.py:91` |
| Workflow Runner max_iterations (supersteps) | 100 | `_runner.py:41` |
| live-event poll interval | 0.05 s | `_runner.py:110` |
| state commit / checkpoint cadence | every superstep boundary | `_runner.py:141,144` |
| checkpoint validation | graph_signature_hash match | `_checkpoint.py:48` |
| tool approval_mode | always_require/never_require (default never) | `_tools.py:93,393` |
| SK DEFAULT_MAX_AUTO_INVOKE_ATTEMPTS | 5 | `function_choice_behavior.py:18` |
| SK Stepwise max_iterations | 15 | planner options |
| SK Stepwise min_iteration_time_ms | 100 | planner options |
| SK AgentGroupChat default max iter | 99 | termination_strategy.py:22 |
| SK Magentic max_stall_count | 3 | MagenticManagerBase |

---

## SUMMARY — what is durable vs overkill

**The over-engineering (name it):** SK's Kernel-as-central-DI-registry; loop-duplicated-per-connector; the generic 3-type filter onion; the explicit Stepwise/Handlebars Planner; the Processes state-machine DSL; MAF's typed Pregel Workflow graph + supersteps + edge-group taxonomy (LangGraph clone); the autogen-core actor runtime (pub/sub topics, envelopes, subscriptions); 5-pattern orchestrations package compiling to graphs; LLM-summarization compaction. Almost the entire catalog is exactly what Verso's thesis refuses.

**Genuinely durable ideas (small):**
1. MAF forces a final `tool_choice="none"` turn after error-threshold/cap — confirms Verso's grace-call design.
2. Magentic progress-ledger `{reason, answer}` per-decision schema — auditable structured self-judgment (loop/progress/done with reasons). A judge/eval pattern, not a primitive.
3. MAF `graph_signature_hash` rejecting resume into a changed topology → the *principle* of a checkpoint version/signature guard that refuses incompatible resume (narrow steal-additive; NOT the graph).
4. SK Stepwise `min_iteration_time_ms=100` inter-step rate-limit sleep (minor production touch).
