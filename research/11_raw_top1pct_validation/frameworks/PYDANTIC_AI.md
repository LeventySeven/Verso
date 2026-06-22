# Pydantic AI — Raw Extraction (nothing-is-lost artifact)

Source teardown: `/Users/seventyleven/Desktop/researchfms/teardowns/PYDANTIC_AI.md` (789 lines), RE'd at commit `cff2825fb5534ee4f0ecea6a79ceb0a91c87160c` (HEAD of `main`, 2026-05-30). MIT. Maintained by Pydantic team (Samuel Colvin). ~14k LoC runtime in `pydantic_ai_slim/pydantic_ai/`.

Tag legend: [KNOWN] = read from source by the teardown; [INFERRED]/[DESIGNED] as the teardown marks it. Each item tagged against VERSO CURRENT STATE.

---

## 0. The core reveal (the spine)
[KNOWN] The agent run loop **IS a `pydantic_graph` state machine** — three typed `BaseNode` subclasses (`UserPromptNode → ModelRequestNode → CallToolsNode`) whose `.run()` returns *the next node or `End`*; a generic `GraphRun.next` drives it and **snapshots state between every node**. There is no `while True:` in the agent — "the loop is the graph cycle, driven externally by `GraphRun.__anext__`." The cycle `ModelRequestNode ⇄ CallToolsNode` is the agent loop; `CallToolsNode` returns `End(FinalResult)` to stop or `ModelRequestNode(...)` to continue.

- `build_agent_graph()` (`_agent_graph.py:2066-2095`) builds exactly 4 node types once per agent. `auto_instrument=False` passed (`:2083`) so graph engine opens NO Logfire spans — agent layer owns instrumentation.
- Node return-type annotation is read at runtime: `BaseNode.get_node_def()` (`basenode.py:104-136`) calls `get_type_hints(cls.run)` and walks the `-> X | Y | End[...]` union to build the adjacency list. No return hint → `GraphSetupError`. "the set of legal next-nodes is therefore *the literal type annotation*… This is the inverse of LangGraph (where edges are added imperatively with `add_edge`)."

**VERSO RELATION:** avoid-overkill. Verso's thesis is "ONE clean async ReAct loop <200 lines, no graph, we don't force the graph." The serialisable-typed-graph spine is exactly the structure Verso refuses. BUT note: pydantic-ai's durability/HITL "fall out for free" *because* every node is a persistence boundary — Verso achieves the same (checkpoint each step, resume in fresh process) WITHOUT the graph, via the tactical↔durable seam. This is the head-to-head validation point.

---

## 1. Agent() / generics / deps
[KNOWN] `Agent[DepsT, OutputT]` generic over `deps_type` and `output_type`. `from pydantic_ai import Agent, RunContext, ModelRetry`.
- **Typed dependencies**: whatever you pass to `agent.run(..., deps=X)` is delivered to every tool + system-prompt function + output validator + capability hook via `RunContext[DepsT].deps`, type-checked end to end. "There is no implicit blackboard." Coordination state = `deps` (shared, typed) + `usage` (threaded) + `message_history` (explicitly passed).
- `Agent.iter()` exposes the `GraphRun` so user code can step node-by-node, inspect/mutate the next node, resume from a snapshot. `Agent.run()` = thin `async for` over `iter`.

**VERSO RELATION:** verso-already-has. `ctx.deps` typed injection is shipped (durable seam). `RunContext`-equivalent threading exists.

## 1b. RunContext full field set (`_run_context.py:34`)
[KNOWN] The single object threaded to tools/system-prompt-fns/output-validators/capability-hooks. Fields: `deps:DepsT`, `model:Model`, `usage:RunUsage`, `prompt`, `messages:list[ModelMessage]`, `validation_context`, `tracer`/`trace_include_content`/`instrumentation_version`, `retries:dict[str,int]` (per-tool counts), `tool_name`/`tool_call_id`, `retry`/`max_retries`, `run_step:int`, `tool_call_approved:bool` (HITL), `tool_call_metadata`, `run_id`/`conversation_id` (UUID7), `metadata`, `tool_manager`, `pending_messages`, `partial_output:bool` (true during streaming arg validation).

**VERSO RELATION:** verso-already-has (ctx.deps, usage, hitl, tool identity all present). The exhaustive single-context-object pattern is neutral-context detail.

---

## 2. Tools — schema from signature
[KNOWN] `@agent.tool` (gets RunContext) vs `@agent.tool_plain` (no ctx). Tools are plain typed Python functions; **JSON schema is generated from the signature**, not declared. `function_schema()` (`_function_schema.py:103-281`):
- Uses pydantic-internal `GenerateSchema` + `signature()` + `get_type_hints(include_extras=True)`.
- **Docstrings become parameter descriptions**: `doc_descriptions` parses the docstring (Google/NumPy/Sphinx, auto-detected via `griffe`) and injects each `arg: description` into the JSON-schema property. `use_attribute_docstrings=True` picks up attribute docstrings on model fields too.
- First param annotated `RunContext[Deps]` detected by `_is_call_ctx` (`:151`) and **stripped from the JSON schema** — `def my_tool(ctx: RunContext[Deps], city: str)` exposes only `{city}` to the model.
- Validator is pydantic-core `SchemaValidator` built once; at call time `_validate_tool_args` (`tool_manager.py:215-250`) runs `validator.validate_json(raw_args or '{}', allow_partial=...)` or `validate_python`.
- **Single-arg unwrapping**: if a tool takes exactly one model-like arg, the tool's JSON schema *is* the model's schema (no wrapper envelope).
- Return schema computed eagerly via `TypeAdapter(return_type).json_schema(mode='serialization')` (for toolsets that advertise return shapes).

**VERSO RELATION:** verso-already-has for docstring→schema (Verso's `@tool` docstring→schema). **steal-additive candidate (LOW bar — likely already have):** per-PARAMETER docstring descriptions via griffe parsing (Google/NumPy/Sphinx), and single-arg model unwrapping. If Verso's `@tool` only takes the top-level docstring as the tool description but does NOT pull per-arg descriptions from the docstring body into each param's JSON-schema `description`, THAT specific behavior is additive + byte-identical-when-unused. Flagged honestly as the one place pydantic-ai may do schema better.

## 2b. Toolsets composition layer
[KNOWN] Tools live in toolsets (`AbstractToolset`); effective toolset is `CombinedToolset` wrapped by decorators: `FunctionToolset`, `CombinedToolset` (resolves name conflicts, aggregates instructions), `PreparedToolset` (prepare_tools hook filters/modifies per step), `FilteredToolset` (drop by predicate), `RenamedToolset`/`PrefixedToolset` (namespace for multi-agent), `ApprovalRequiredToolset`, `WrapperToolset`, `_DynamicToolset` (resolves tools depending on RunContext at run-step time), `ExternalToolset` (deferred out-of-process), `MCPServer`/FastMCP, `ToolSearchTool` (native tool-search when corpus large; auto-dropped when corpus empty `_agent_graph.py:514-520`).
- `for_run_step` (`tool_manager.py:120-145`) called once per model request: re-resolves dynamic toolsets, re-fetches `get_tools(ctx)`, rebuilds manager carrying over `retries`.

**VERSO RELATION:** mostly avoid-overkill (the full wrapper-toolset stack is a composition cult). `ToolSearchTool` (native tool-search when corpus large, auto-dropped when empty) is **neutral-context** — interesting for huge tool corpora but Verso has RRF retrieval over context already.

## 2c. ModelRetry / deferred / approval tools
[KNOWN]
- `ModelRetry("reason")` raised in tool body → `RetryPromptPart` → next turn (self-healing).
- `CallDeferred` raised by tool → call becomes `external` deferred; run ENDS returning `DeferredToolRequests` (if it's an output type); outside system fulfils and resumes via `agent.run(..., deferred_tool_results=...)`.
- `ApprovalRequired` → call becomes `unapproved`; resumed with `ToolApproved(override_args=...)` / `ToolDenied(message=...)`. **`ToolApproved.override_args` lets the human EDIT the args before execution** (`:1679`).
- Resume entry `_handle_deferred_tool_results` (`:355-400`): finds last `ModelResponse` with tool calls, maps results by `tool_call_id`, marks already-executed calls `'skip'`, **jumps straight to `CallToolsNode` bypassing the model** — "the human-in-the-loop loop is literally a graph edge."

**VERSO RELATION:** verso-already-has (ask_once, PermissionDecision allow/deny/ask/defer, ctx.hitl.request pause/resume idempotent, durable resume). **steal-additive candidate (genuinely additive, on-thesis):** `ToolApproved.override_args` — letting the human/approver EDIT the tool-call arguments at the approval gate before execution (not just allow/deny). Verso's PermissionDecision is 4-valued but if "ask" can't return MODIFIED args, override-args-on-approve is a small, byte-identical-when-unused HITL primitive worth considering for the safety/hooks ask path.

---

## 3. Output / structured output / validators
[KNOWN] `OutputMode = Literal['text','tool','native','prompted','tool_or_text','image','auto']` (`output.py:42`). Structured subset `StructuredOutputMode = Literal['tool','native','prompted']`.
- **`ToolOutputSchema`** (default `'tool'`): output type becomes a tool named `'final_result'` (`DEFAULT_OUTPUT_TOOL_NAME`, `_output.py:72`), description `'The final response which ends this conversation'` (`:73`). Model "returns" structured output by *calling* that tool; args validated against schema. Default for almost every model (`ModelProfile.default_structured_output_mode='tool'`).
- **`NativeOutputSchema`** (`'native'`): provider's native structured-output (OpenAI `response_format`, Gemini `responseSchema`). Response body IS the JSON.
- **`PromptedOutputSchema`** (`'prompted'`): schema injected into instructions via template, model emits raw JSON, text parsed+validated. Fallback for models with neither tool-calling nor native JSON.
- `output_type` can be: Pydantic model, dataclass, TypedDict, function, union, or wrappers `ToolOutput`/`NativeOutput`/`PromptedOutput`.
- **Output validators** (`@agent.output_validator`): run in `_output.run_output_with_hooks` after final result; may raise `ModelRetry` → consumes OUTPUT retry budget → sends `RetryPromptPart`. Output-tool success acked to model with synthetic `ToolReturnPart(content='Final result processed.')` (`:1446-1461`, also `:1523`).

[KNOWN] **Verbatim prompted-output template** (`profiles/__init__.py:97-105`):
```
Always respond with a JSON object that's compatible with this schema:

{schema}

Don't include any text or Markdown fencing before or after.
```
`{schema}` = `json.dumps(object_def.json_schema)`. Overridable per `ModelProfile.prompted_output_template`. `native_output_requires_schema_in_instructions=False` by default (native mode trusts provider, doesn't also inject template).

**VERSO RELATION:** verso-already-has. Verso ships `output_type=`, in-loop reask (append ValidationError + re-drive), output validators, Retry(feedback) self-healing. The 3-transport-mode selection (tool/native/prompted by model capability) is **neutral-context** / mild steal — Verso likely defaults to one path; pydantic-ai's capability-driven mode auto-selection is more complete but verges on over-build.

---

## 4. Model layer / providers
[KNOWN] Model classes in `models/`: `openai.py`, `anthropic.py`, `google.py`, `groq.py`, `bedrock.py`, `mistral.py`, `cohere.py`, `huggingface.py`, plus `fallback.py`, `wrapper.py`, `instrumented.py`, `test.py`, `function.py`. Each implements `Model` ABC: `request(...)`, `request_stream(...)`, `count_tokens(...)`, `prepare_messages(...)`, `prepare_request(...)`, plus a `profile` (`ModelProfile`) with capability flags.
- **`FallbackModel`** (`models/fallback.py`): tries a list of models in order; only runs `prepare_messages`/`prepare_request` on the candidate actually picked (per-profile translation stays correct).
- **`InstrumentedModel`**: wraps any model with OpenTelemetry GenAI-semconv spans.
- Framework owns typed-tool-part translation: `_narrow_tool_call_parts` (`:2098-2129`) promotes base `ToolCallPart`s to typed subclasses by `tool_kind` — adapters emit plain parts, framework keeps typed identity consistent across streaming/non-streaming.

**VERSO RELATION:** verso-already-has. Verso ships anthropic/openai/google adapters + any OpenAI-compatible via base_url, `init_model("provider:model")`, FailoverModel + RetryPolicy (typed errors, auth/content fail fast), per-call model swap + agent.override(), error taxonomy. FallbackModel == Verso FailoverModel. `prepare_messages` per-provider translation is **neutral-context**.

---

## 5. Retry & error recovery — TWO budgets
[KNOWN] Two independent retry budgets:
- **Per-tool retries**: `ToolManager.default_max_retries = 1` (`tool_manager.py:92`, i.e. 1 retry = 2 attempts), overridable per tool. `_check_max_retries` raises `UnexpectedModelBehavior(f'Tool {name!r} exceeded max retries count of {max_retries}')`. Counts carry across steps via `for_run_step`: `retries = {failed: prev+1 for failed in failed_tools}`.
- **Output-validation retries**: `GraphAgentState.output_retries_used`, `consume_output_retry(max)` raises `UnexpectedModelBehavior(f'Exceeded maximum output retries ({max})')`.

[KNOWN] **The validation-error payload IS the prompt.** `_wrap_error_as_retry` (`tool_manager.py:183-191`) converts a tool `ModelRetry` or pydantic `ValidationError` into a `RetryPromptPart(tool_name, content=error.errors(include_url=False, include_context=False) | message, tool_call_id)`. Model sees the structured pydantic validation errors and self-corrects. "the validation-error payload *is the prompt*."

[KNOWN] **`IncompleteToolCall` path** (`check_incomplete_tool_call`, `:142-156`): if last response had `finish_reason=='length'` and ended mid-tool-call (args fail to parse), raises a TARGETED error: `Model token limit (...) exceeded while generating a tool call, resulting in incomplete arguments. Increase the max_tokens model setting...` — rather than burning retries.

**VERSO RELATION:** verso-already-has for self-healing (in-loop reask, Retry(feedback), per-tool max_attempts). **steal-additive candidate:** the `IncompleteToolCall` special case — detecting `finish_reason=='length'` + unparseable tool args and emitting a "raise max_tokens" diagnostic INSTEAD of consuming a retry. This is a precise, additive, byte-identical-when-unused failure-diagnostic that prevents wasted retries on a structural (not semantic) failure. Verso's jsonish 4-stage parse waterfall handles malformed JSON, but the length-truncation-specific diagnostic is a distinct on-thesis reliability win.

---

## 6. End-strategy
[KNOWN] `EndStrategy = Literal['early','graceful','exhaustive']`, default `'early'` (`agent/__init__.py:285`).
- `early`: once any output tool yields valid FinalResult, remaining output tools skipped AND remaining function tools short-circuited with stub `Tool not executed - a final result was already processed.`
- `graceful`: remaining output tools skipped but function tools run to completion before ending.
- `exhaustive`: all output tools validated/executed (first valid = final), all function tools run.

**VERSO RELATION:** avoid-overkill / neutral-context. Verso terminates via `done()` tool + grace-call at max_steps. The 3-way end-strategy enum is a graph-execution concern (multiple final-result tool calls in one batch) Verso's simpler loop doesn't need.

---

## 7. Streaming protocol — exact event names
[KNOWN] Two layers.
Low-level `ModelResponseStreamEvent` (`messages.py`): `PartStartEvent`(`'part_start'`), `PartDeltaEvent`(`'part_delta'`), `PartEndEvent`(`'part_end'`), `FinalResultEvent`(`'final_result'`). Delta payloads: `TextPartDelta`(`'text'`), `ThinkingPartDelta`(`'thinking'`), `ToolCallPartDelta`(`'tool_call'`); each has `.apply(part)` to incrementally build. `ToolCallPartDelta` accumulates partial JSON args.
High-level `HandleResponseEvent` (fired by CallToolsNode): `FunctionToolCallEvent`(`'function_tool_call'`, `args_valid` set), `FunctionToolResultEvent`(`'function_tool_result'`), `OutputToolCallEvent`(`'output_tool_call'`), `OutputToolResultEvent`(`'output_tool_result'`), `BuiltinToolCallEvent`/`BuiltinToolResultEvent` (DEPRECATED in favor of PartStart/Delta with `NativeToolCallPart`).

[KNOWN] **Incremental structured-output validation** (the reveal): stream a Pydantic model and watch it fill field-by-field. `debounce_by: float | None = 0.1` (`result.py`) = universal 100ms temporal window via `group_by_temporal`; `None` = per-token. `stream_output(debounce_by=0.1)` validates each grouped `ModelResponse` with `allow_partial=True`. `stream_text(delta=False)` = cumulative; `delta=True` = new substring only. Partial JSON validates because pydantic-core validator uses `allow_partial='trailing-strings'` (`tool_manager.py:234`) — `{"name": "Ada", "age":` validates to `{name:'Ada'}` mid-stream. Usage limits enforced MID-stream (`UsageLimitExceeded` during, not only at end).

**VERSO RELATION:** verso-already-has typed true-delta events (message/reasoning/tool.start/tool.result/done) + SSE. **steal-additive candidate (genuinely additive, on-thesis):** (a) **incremental partial-output validation** — re-validating an accumulating structured output with `allow_partial='trailing-strings'` so a Pydantic model fills field-by-field during the stream. Verso has output_type validation but if it only validates the COMPLETE output, partial-while-streaming is additive and byte-identical-when-unused. (b) **`debounce_by=0.1` temporal coalescing** of stream deltas into 100ms windows — a small, opt-in stream ergonomic. (c) **mid-stream usage-limit enforcement** (raise during, not after).

---

## 8. State / memory / durability
[KNOWN] **Stateless between runs by design — NO built-in long-term memory store.** State lives in `GraphAgentState` (`_agent_graph.py:117-176`): `message_history`, `usage:RunUsage`, `output_retries_used`, `run_step`, `run_id`(UUID7), `conversation_id`(UUID7), `metadata`/`last_max_tokens`/`last_model_request_parameters`, `pending_messages` (priority-injected message queue). You persist `result.all_messages()` yourself and pass back as `message_history=`.
- `resolve_conversation_id` (`:90-114`): `'new'`→fresh UUID7; explicit string→as-is; else most recent non-None conversation_id in history; else fresh. `result.new_messages()` returns messages from `new_message_index` onward.

[KNOWN] **Compaction is provider-driven, not framework-driven.** `CompactionPart` (`part_kind='compaction'`, `messages.py:1716`); loop folds compaction text into response text when no other actionable text (e.g. Anthropic `pause_after_compaction=True`). `HistoryProcessor` (`_history_processor.py`) lets you register functions that rewrite the message list before each request — "the place to implement summarisation/windowing."

[KNOWN] `_clean_message_history` (`:2176-2225`): canonicalisation before each request — merges consecutive `ModelRequest`s (only when instructions match) with **tool-return parts sorted to the front** (`key = 0 if ToolReturnPart|RetryPromptPart else 1`), merges consecutive *synthetic* `ModelResponse`s (no provider id/name).

**VERSO RELATION:** Verso DIVERGES (stronger) on memory — Verso ships typed 4-tier memory (FACT/...), temporal, RRF recall, recall_as_of time-travel, reflect() consolidation. pydantic-ai explicitly has NO memory store. `HistoryProcessor` (register fns to rewrite history pre-request) is **neutral-context** — Verso's prune() masks old tool outputs (never silent-drops); HistoryProcessor is a more general but less safe hook. Verso's no-LLM-summarization-by-default is consistent with pydantic-ai NOT shipping compaction. **leanness signal: pydantic-ai (the reference target) shipping ZERO memory store strongly validates "boring core, don't over-build."**

---

## 9. Durability / checkpointing (`pydantic_graph.persistence`)
[KNOWN] Because the agent IS a graph, durability is the graph's persistence layer. `BaseStatePersistence` (`persistence/__init__.py:106`) contract: `snapshot_node(state,next_node)`, `snapshot_node_if_new(snapshot_id,...)` (idempotent dedupe on resume), `snapshot_end(state,end)`, `record_run(snapshot_id)->AsyncCM` (flip status created→running→success/error), `load_next()->NodeSnapshot|None`, `load_all()`.
- `SnapshotStatus = Literal['created','pending','running','success','error']` (`:32`).
- Implementations: `SimpleStatePersistence` (latest snapshot only, in-mem, default), `FullStatePersistence` (full list, each deep-copied), `FileStatePersistence` (JSON-file-backed, survives process restart — "the durable-execution primitive").
- `GraphAgentState` is a dataclass of pydantic-serialisable types (messages have `ModelMessagesTypeAdapter`) → whole state round-trips through JSON. Deferred tools / approval / crash-resume work by snapshotting after CallToolsNode produces DeferredToolRequests and the run ends.
- Also ships Temporal/DBOS durable-execution integration mapping the graph onto a workflow engine.

[KNOWN] `GraphRun.next` snapshots BEFORE (snapshot_node_if_new) and AFTER (snapshot_node / snapshot_end) every node run, inside a `record_run()` span. Snapshot id is per node INSTANCE (`basenode.py:67`), lazy, via `object.__setattr__` (works on frozen dataclasses); resumed runs reuse id to dedup.

**VERSO RELATION:** verso-already-has. Verso ships SqliteCheckpointStore, checkpoint each step (crash-recoverable), resume() in fresh process, history()/fork() time-travel, repair_history resume-guard. pydantic-ai's `FileStatePersistence` ≈ Verso's checkpoint store; `snapshot_node_if_new` idempotent dedup ≈ Verso's idempotent-up-to-request resume. **The key contrast:** pydantic-ai needs the GRAPH to get a persistence boundary at each node; Verso gets the same crash-resume from the tactical↔durable seam WITHOUT the graph. The `SnapshotStatus` created/pending/running/success/error lifecycle is **neutral-context**. Temporal/DBOS integration = avoid-overkill (not the model/kernel, not an orchestrator).

---

## 10. Capability (middleware) system — second hidden engine
[KNOWN] Onion-style middleware (`capabilities/`, `AbstractCapability` `:135`). 21 built-ins (web search, thinking, prepare-tools, system-prompt reinjection, deferred-tool handling, instrumentation) all are `AbstractCapability` subclasses, combined into one `CombinedCapability` (`ctx.deps.root_capability`).
- Hook quartet per stage (`before_*`/`after_*`/`wrap_*`/`on_*_error`): Run, Node, Model request, Tool validate, Tool execute, Output validate, Output process, plus `prepare_tools`/`prepare_output_tools`, `handle_deferred_tool_calls`, `for_run`.
- `wrap_model_request(ctx, request_context, handler)`: `handler()` IS the model call — classic middleware. A capability raising `SkipModelRequest(response)` short-circuits the model (canned response); `ModelRetry` from a wrap hook retries with `RetryPromptPart`.
- Ordering: `CapabilityPosition = Literal['outermost','innermost']` + `wraps`/`wrapped_by` edges, topologically sorted (`sort_capabilities`), original list order breaks ties.

**VERSO RELATION:** verso-already-has the lifecycle hooks (Hooks: pre/post_model, pre/post_tool, on_stop, ask, should_continue). The full `wrap_*`/`before_*`/`after_*`/`on_*_error` quartet ×8 stages + topological ordering + 21-built-in onion = **avoid-overkill** — "no orchestrator-as-primitive," this is complexity-for-its-own-sake relative to Verso's flat hook set. `SkipModelRequest` (canned-response short-circuit) overlaps Verso's pre_model hook returning a response. Note `reinforce_objective` (Verso) ≈ pydantic-ai's "system-prompt reinjection" capability.

---

## 11. Multi-agent
[KNOWN] [INFERRED for patterns] Does NOT ship a bespoke supervisor/swarm runtime. Composed from primitives: (1) agent-as-tool (`@agent_a.tool` body calls `await agent_b.run(prompt, deps=ctx.deps, usage=ctx.usage)`; passing `ctx.usage` threads usage so limits span both agents); (2) toolset prefixing/renaming; (3) embed an agent run as a node in a larger hand-authored `pydantic_graph`; (4) `WrapperAgent` (`agent/wrapper.py`) to intercept/augment runs.

**VERSO RELATION:** neutral-context / leanness signal. pydantic-ai (reference target) NOT shipping a supervisor runtime validates Verso's "no orchestrator-as-primitive, not a router/planner cult." Agent-as-tool with threaded `ctx.usage` is the clean composition primitive — Verso achieves multi-agent the same compositional way.

## 12. MCP as toolset
[KNOWN] `MCPServer` is an `AbstractToolset` (not special-cased) — MCP tools enter via the same `get_tools(ctx)`/`for_run_step` path. `cache_tools=True`/`cache_prompts=True`/`cache_resources=True` default-on; invalidation push-based on `notifications/tools/list_changed` or `__aexit__`. Durable-execution caveat: under Temporal/DBOS the wrapper-level cache is NOT invalidated by list_changed — set `cache_tools=False`. Sampling (`allow_sampling`+`sampling_model`: MCP server makes its own LLM calls via your model), elicitation_callback, include_instructions, include_return_schema.

**VERSO RELATION:** verso-already-has (MCP is opt-in adapter via tool_from_schema; native @tool is THE path). MCP-as-just-another-toolset matches Verso's "not MCP-first." Caching internals = neutral-context.

---

## 13. Constants table (all [KNOWN] from commit cff2825)
| Constant | Value | Source |
|---|---|---|
| `UsageLimits.request_limit` | `50` (the de-facto max iterations; no separate max_iterations) | `usage.py:272` |
| `UsageLimits.tool_calls_limit` | `None` | `usage.py:274` |
| `UsageLimits.count_tokens_before_request` | `False` | `usage.py:282` |
| `ToolManager.default_max_retries` | `1` (1 retry = 2 attempts) | `tool_manager.py:92` |
| `Agent(end_strategy=)` | `'early'` | `agent/__init__.py:285` |
| `ModelProfile.default_structured_output_mode` | `'tool'` | `profiles/__init__.py:95` |
| `native_output_requires_schema_in_instructions` | `False` | `profiles/__init__.py:107` |
| `DEFAULT_OUTPUT_TOOL_NAME` | `'final_result'` | `_output.py:72` |
| `DEFAULT_OUTPUT_TOOL_DESCRIPTION` | `'The final response which ends this conversation'` | `_output.py:73` |
| `ParallelExecutionMode` default | `'parallel'` (events as they complete) | `tool_manager.py:38,166` |
| Partial-validation mode (streaming) | `'trailing-strings'` | `tool_manager.py:234` |
| `NEW_CONVERSATION` sentinel | `'new'` | `_agent_graph.py:85` |
| `run_id`/`conversation_id` | UUID7 | `_agent_graph.py:125-126` |
| `debounce_by` (streaming) | `0.1` (100ms) | `result.py` |

**VERSO RELATION:** `request_limit=50` ≈ Verso `max_steps` cap. UUID7 time-ordered ids = neutral-context (nice for ordering checkpoints). Parallel tool exec default with deterministic `sorted(index)` history order = see §14.

---

## 14. Parallel tool execution (deterministic transcript)
[KNOWN] `get_parallel_execution_mode` (`tool_manager.py:155-168`) returns `'sequential'` if ANY called tool has `tool_def.sequential=True`, else context-var default `'parallel'`. `_call_tools` (`:1818-1921`): modes `'parallel'` (run all, emit events AS THEY COMPLETE via `asyncio.wait FIRST_COMPLETED`), `'sequential'`, `'parallel_ordered_events'` (run parallel, emit in call order). **Results appended to history in `sorted(index)` order, not completion order** (`:1916`) — parallel execution, deterministic transcript. "a single sequential tool forces the whole batch sequential."

[KNOWN] CallToolsNode bucketing (`process_tool_calls` `:1493-1816`): bucket by `tool_def.kind ∈ {output, function, external, unapproved, unknown}`; output tools first (end-strategy gate), function tools (parallel), deferred tools last. **Tool calls win over text**: "we prioritize at least executing tool calls if they are present" — when a response has both text + tool calls, executes tools and DISCARDS the text this turn; recoverable later via `_recover_text_from_message_history` if next response empty.

[KNOWN] **The "Please …" nudge** (`_agent_graph.py:1234`): if model returns neither valid output nor a tool call, synthesises `RetryPromptPart` content = `"Please " + " or ".join(alternatives) + "."` where alternatives ∈ {`return text`, `call a tool`, `include your response in a tool call`, `return an image`}.

**VERSO RELATION:** **steal-additive candidate:** **deterministic `sorted(index)` history ordering for parallel tool results** — running tools concurrently but appending results to the transcript in call-order so the recorded history is reproducible regardless of completion timing. This is directly on Verso's eval/reliability thesis (reproducible trajectories = stable regression tests; "captured failure IS a regression test"). If Verso runs tools in parallel but records them in completion order, transcript non-determinism undermines TrajectoryCheck. Additive + byte-identical-when-unused (single tool = no reordering). "Tool calls win over text" + text-recovery is a neutral-context loop-detail.

---

## 15. What pydantic-ai does BETTER than Verso (honest)
- Per-PARAMETER docstring→schema descriptions via griffe (vs tool-level docstring only) — IF Verso lacks per-arg.
- Incremental partial-output validation while streaming (`allow_partial='trailing-strings'`) — fill a model field-by-field.
- `ToolApproved.override_args` — human edits tool args at the approval gate.
- `IncompleteToolCall` diagnostic — `finish_reason=='length'` mid-tool-call → "raise max_tokens" instead of burning a retry.
- Deterministic `sorted(index)` parallel-tool history ordering.
- `debounce_by=0.1` stream coalescing; mid-stream usage-limit enforcement.

## 16. What pydantic-ai OVER-BUILDS (Verso must NOT copy)
- The entire serialisable-typed-graph spine (BaseNode/GraphRun/4-node topology) — Verso explicitly "doesn't force the graph."
- 21-capability onion middleware with 8-stage before/after/wrap/on_error quartet + topological ordering.
- 3-way `EndStrategy` enum (graph-batch concern).
- Full wrapper-toolset decorator stack (Prefixed/Renamed/Filtered/Prepared/...).
- `pydantic-graph` as a separate distribution + Temporal/DBOS workflow-engine mapping.
- 7-value `OutputMode` enum with `auto`/`tool_or_text` hybrids (capability-driven mode auto-selection borders on over-build).

## 17. Leanness signals (validate Verso's thesis)
- pydantic-ai (THE reference target) ships **ZERO long-term memory store** — stateless by design. Verso's memory is additive beyond the reference.
- **No bespoke supervisor/multi-agent runtime** — composed from agent-as-tool. Validates "no orchestrator/router cult."
- **No hidden ReAct scaffold, no "you are a helpful assistant," no CoT injection** ("the structure comes from JSON schemas, not from prose"). Validates "boring core, no prompt-magic."
- **Compaction is provider-driven, not framework-driven** — validates Verso's "no LLM-summarization-compaction-by-default."
- BUT: durability/HITL "fall out for free" ONLY because of the graph — this is the one place the source CHALLENGES Verso's "no graph": pydantic-ai got resumability by paying the graph tax up front; Verso claims the same via the tactical↔durable seam without it. Head-to-head the seam must deliver snapshot-per-step + idempotent resume that pydantic-ai gets structurally.
