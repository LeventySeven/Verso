# Cluster: LangChain + LangGraph
**Source teardowns:** `teardowns/LANGCHAIN.md` (1,820 lines, R1+R2), `teardowns/LANGGRAPH.md` (2,063 lines, R1+R2+R3)
**Relevance:** Highest — LangGraph is the direct peer Verso is competing with. LangChain is the integration layer everyone copies. These two together define the current state-of-the-art for Python agent frameworks.

---

## System 1: LangChain (LCEL + v0/v1 Agents)

### What it is

LangChain provides one composable primitive — the **Runnable** — and a family of concrete Runnables wrapping every external interaction (LLM call, tool call, vector lookup, output parser, prompt template). The `|` operator composes Runnables into `RunnableSequence`, dict literals into `RunnableParallel`. The actual moat is 700+ pre-built integrations (chat models, embeddings, vector stores, retrievers, document loaders, tools), all standardized to the same `invoke/stream/batch` interface.

LangChain has two parallel agent stacks:
- **v0 `AgentExecutor`** — classic `while` loop, deprecated, still widely deployed.
- **v1 `create_agent()`** — thin shim over LangGraph's Pregel runtime, with a middleware system around the model and tool nodes.

### Agent Loop

**v0 `AgentExecutor._call` (KNOWN, `agents/agent.py:1570`)**

```python
# defaults
max_iterations: int | None = 15
max_execution_time: float | None = None
early_stopping_method: str = "force"  # or "generate"
handle_parsing_errors: bool | str | Callable = False
trim_intermediate_steps: int | Callable = -1  # -1 = no trim
```

Loop structure: `while self._should_continue(iterations, time_elapsed)` → `_take_next_step` → check `AgentFinish` → extend `intermediate_steps` → check `return_direct` → `iterations += 1`.

Termination paths:
1. Model returns `AgentFinish` — normal.
2. Tool with `return_direct=True` — short-circuit, wrap observation as final output.
3. `iterations >= 15` or `time_elapsed >= max_execution_time` → `return_stopped_response("force")` → literal `"Agent stopped due to iteration limit or time limit."` (agent.py:132).
4. `early_stopping_method="generate"` — one more LLM call to synthesize closing answer from scratchpad.

**v1 `create_agent()` (KNOWN, `libs/langchain_v1/langchain/agents/factory.py`)**

The loop is no longer in this file — it lives in LangGraph's Pregel runtime. `create_agent` builds a StateGraph with `model` node and `tools` node (`ToolNode`). Termination is controlled by LangGraph's `recursion_limit` (default 25 for the agent, 10007 for the raw Pregel runtime).

Graceful shutdown when budget nearly exhausted:

```python
# _are_more_steps_needed (chat_agent_executor.py:620)
if remaining_steps < 1 and all_tools_return_direct: return True
elif remaining_steps < 2 and has_tool_calls: return True
# → emits "Sorry, need more steps to process this request."
```

### Middleware System (v1)

Ordered hooks around every loop iteration (KNOWN, `middleware/types.py`):

| Hook | Purpose |
|---|---|
| `before_agent(state, runtime)` | Runs once at start; can return state updates. |
| `before_model(state, runtime)` | Before each LLM call. Summarization, PII redaction, context trimming. |
| `wrap_model_call(request, handler)` | Surrounds the LLM call; can mutate `ModelRequest`, retry, swap model, short-circuit. |
| `after_model(state, runtime)` | After each LLM call; can set `state["jump_to"] = "tools"|"model"|"end"`. |
| `wrap_tool_call(request, handler)` | Surrounds each tool call; caching, retry, modification, suppression. |
| `after_agent(state, runtime)` | Runs once at end. |

Built-in middlewares (shipped as first-party):
- `SummarizationMiddleware` (658 lines) — when message history exceeds `max_tokens_before_summary` (default 4000), invoke a cheaper summary model, replace older messages with a `SystemMessage` summary.
- `HumanInTheLoopMiddleware` (412 lines) — interrupts before tool execution for user approval.
- `ModelCallLimitMiddleware` (267 lines), `ToolCallLimitMiddleware` (488 lines), `ModelRetryMiddleware` (312 lines), `ToolRetryMiddleware`, `ModelFallbackMiddleware` (138 lines), `PIIDetectionMiddleware` (376 lines), `ContextEditingMiddleware` (298 lines).

### Tool System

`BaseTool` (KNOWN, `tools/base.py:405`):

```python
class BaseTool(RunnableSerializable[str | dict | ToolCall, Any]):
    name: str
    description: str
    args_schema: ArgsSchema | None = None     # Pydantic v1/v2 class or raw JSON Schema dict
    return_direct: bool = False
    handle_tool_error: bool | str | Callable | None = False
    handle_validation_error: bool | str | Callable | None = False
    response_format: Literal["content", "content_and_artifact"] = "content"
```

Registration: `@tool` decorator (reads Google-style docstring, inspects type hints, builds Pydantic `args_schema`), `StructuredTool.from_function(func)`, or subclassing `BaseTool`.

Filtered args (never exposed to LLM tool schema): `InjectedToolArg`, `InjectedToolCallId`, `InjectedState`, `InjectedStore`, `RunManager`, `Callbacks` — wired in by the framework.

Tool error policy:
- `handle_tool_error=False` (default) — exception propagates, kills the loop.
- `handle_tool_error=True` — return `str(exception)` as `ToolMessage`.
- `handle_tool_error=<str>` — return that fixed string.
- `handle_tool_error=<callable>` — `f(exception) -> str`.
- Same shape for `handle_validation_error` (Pydantic ValidationError).

Tool name not found → routed to `InvalidTool` which returns `"{requested_tool_name} is not a valid tool, try one of {available_tool_names}."` as the observation.

Default tool error template: `"Error: {error}\n Please fix your mistakes."` (factory.py:109).

### ReAct Prompts (verbatim from source)

Classic ReAct (`agents/mrkl/prompt.py`, KNOWN):

```text
PREFIX = "Answer the following questions as best you can. You have access to the following tools:"

FORMAT_INSTRUCTIONS = """Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question"""

SUFFIX = """Begin!
Question: {input}
Thought:{agent_scratchpad}"""
```

Scratchpad format (`format_scratchpad/log.py`, KNOWN):

```python
def format_log_to_str(intermediate_steps, observation_prefix="Observation: ", llm_prefix="Thought: "):
    thoughts = ""
    for action, observation in intermediate_steps:
        thoughts += action.log
        thoughts += f"\n{observation_prefix}{observation}\n{llm_prefix}"
    return thoughts
```

For tool-calling agents (OpenAI/Anthropic/Mistral): the scratchpad is *messages* (not a string) — `AIMessage` with `tool_calls` + `ToolMessage` pairs. This is the only path that doesn't depend on the model emitting LangChain's prose format.

### Output Parsing

Parser per agent type (all in `agents/output_parsers/`):
- `mrkl.py` — regex: `Action: <tool>\nAction Input: <input>` and `Final Answer: <text>`.
- `structured_chat.py` — extracts ` ```json...``` ` blocks, `json.loads`.
- `openai_tools.py` — reads `AIMessage.tool_calls[*]` directly; no regex.
- `xml.py` — parses `<tool><tool_input>` XML.
- `openai_functions.py` — legacy `function_call` field.

On parse failure: raises `OutputParserException(text, observation, send_to_llm=bool)`. The `send_to_llm` flag controls whether the exception message is passed back to the model for self-correction, or replaced with `"Invalid or incomplete response"`.

### Context / Memory

**v0 memory (deprecated since 0.3.1):**
- `ConversationBufferMemory` — full history.
- `ConversationBufferWindowMemory` — last `k` turns.
- `ConversationTokenBufferMemory` — keep until `max_token_limit`, drop oldest.
- `ConversationSummaryMemory` — single rolling LLM-generated summary. Prompt (KNOWN, `memory/prompt.py`):
  ```text
  Progressively summarize the lines of conversation provided, adding onto the previous summary returning a new summary.
  Current summary: {summary}
  New lines of conversation: {new_lines}
  New summary:
  ```
- `ConversationSummaryBufferMemory` — hybrid: recent verbatim, older summarized.
- `ConversationEntityMemory` — extract proper nouns as knowledge triples. `KG_TRIPLE_DELIMITER = "<|>"`.
- `VectorStoreRetrieverMemory` — store every turn as a document, retrieve top-k by query.
- 30+ chat-history backends (Redis, Postgres, Cosmos, MongoDB, DynamoDB, Cassandra, S3).

**v1 memory (current):**
- **Short-term**: LangGraph `Checkpointer` — per-thread, survives process restarts.
- **Long-term**: `BaseStore` KV with namespaced tuples and semantic search.
- **Compaction**: `SummarizationMiddleware` — `before_model` hook. Trigger: `max_tokens_before_summary` (default 4000). Action: invoke cheaper summary model, replace with `SystemMessage` containing the summary. State preserved via `RemoveMessage(id=REMOVE_ALL_MESSAGES)` ("__remove_all__") to wipe the accumulated messages while appending the summary.

### Streaming Protocol

Three independent streaming modes:
1. **`runnable.stream(input)`** — output chunks. `BaseMessageChunk` deltas for chat models.
2. **`runnable.astream_events(input, version="v2")`** — structured events: `{"event", "name", "run_id", "parent_ids", "tags", "metadata", "data"}`. Event types: `on_chat_model_start/stream/end`, `on_tool_start/end`, `on_chain_start/stream/end`, `on_retriever_start/end`. The LangSmith trace stream. v2 is the flattened event format (recommended over v1 tree-of-runs).
3. **`runnable.astream_log(input)`** — JSONPatch-style stream of run state mutations. Used by LangServe playground.

In v1 agents, `graph.stream(stream_mode=...)` is the LangGraph stream (see System 2 §Streaming).

### LCEL Internals (R2 deep pass)

`|` operator implementation (`base.py:619`):
```python
def __or__(self, other) -> RunnableSerializable:
    return RunnableSequence(self, coerce_to_runnable(other))
```

`coerce_to_runnable` dispatches: `Runnable` → passthrough, async-generator → `RunnableGenerator`, callable → `RunnableLambda`, dict → `RunnableParallel`.

`RunnableSequence.__init__` flattens nested sequences: `(a|b)|(c|d)` → flat `[a, b, c, d]`. The first step receives all kwargs; subsequent steps do not (`**kwargs` only flows to step 0 — must pre-bind with `.bind(stop=...)`).

Config propagation: `var_child_runnable_config: ContextVar` in `runnables/config.py`. Each sequence step runs under `set_config_context(config) as context; context.run(step.invoke, input_, config)`, so inner Runnables inherit parent tags/metadata/callbacks via `ensure_config(None)` without explicit passing.

`RunnableParallel` uses `ThreadPoolExecutor` (sync) and `asyncio.gather` (async). Fan-out is real concurrency in async, GIL-bound threads in sync.

`DEFAULT_RECURSION_LIMIT = 25` (LCEL sequences, `runnables/config.py:163`).

### Error Handling

Full error policy chain:
- **LLM call fails**: if `model.with_retry(stop_after_attempt=N)` → exponential backoff + jitter via `RunnableRetry`. Default `stop_after_attempt=3`, `wait_exponential_jitter=True`, multiplier=1.0. Else exception propagates.
- **Output parsing fails**: `handle_parsing_errors` policy (False/True/str/callable). `send_to_llm=True` passes the error observation back to the model.
- **Tool validation fails**: `handle_validation_error` policy.
- **Tool execution fails**: `handle_tool_error` policy. Default=False means exception kills the loop.
- **Tool not found**: `InvalidTool` returns structured error to model.
- **Max iterations**: `return_stopped_response("force"/"generate")`.
- **v1 recursion limit**: graceful `"Sorry, need more steps to process this request."` instead of raising.

### Constants (KNOWN)

| Constant | Value | Source |
|---|---|---|
| `AgentExecutor.max_iterations` | `15` | `agent.py:1023` |
| `AgentExecutor.early_stopping_method` | `"force"` | `agent.py:1032` |
| `AgentExecutor.handle_parsing_errors` | `False` | `agent.py:1042` |
| `AgentExecutor.trim_intermediate_steps` | `-1` (no trim) | `agent.py:1053` |
| Stopped-response string | `"Agent stopped due to iteration limit or time limit."` | `agent.py:132` |
| Out-of-steps string | `"Sorry, need more steps to process this request."` | `chat_agent_executor.py:689` |
| Default tool error template | `"Error: {error}\n Please fix your mistakes."` | `factory.py:109` |
| `BaseTool.return_direct` | `False` | `tools/base.py` |
| `BaseTool.handle_tool_error` | `False` | `tools/base.py` |
| `DEFAULT_RECURSION_LIMIT` (LCEL) | `25` | `runnables/config.py:163` |
| `_RUNNABLE_SEQUENCE_MIN_STEPS` | `2` | `base.py` |
| `EnsembleRetriever.c` (RRF constant) | `60` | `retrievers/ensemble.py` |
| `OutputFixingParser.max_retries` | `1` | defaults |
| `MessagesPlaceholder.optional` | `False` | defaults |
| `KG_TRIPLE_DELIMITER` | `"<|>"` | `memory/prompt.py:112` |

### Provider Abstraction

`init_chat_model("provider:model_name")` — e.g. `"openai:gpt-4o"`, `"anthropic:claude-sonnet-4-5"`, `"groq:llama-3.3-70b"`. Supports: openai, anthropic, azure_openai, azure_ai, google_vertexai, google_genai, bedrock, bedrock_converse, cohere, fireworks, together, mistralai, huggingface, groq, ollama, deepseek, xai, perplexity, openrouter (~19 providers via `init_chat_model`; 50+ via community).

`with_structured_output(schema)` routes to: native JSON-schema mode (OpenAI), function calling (Anthropic), or Pydantic post-validation (fallback). Provider-portable.

Fallback models assumed to support structured output (KNOWN, `factory.py:150`):
```python
FALLBACK_MODELS_WITH_STRUCTURED_OUTPUT = ["grok", "gpt-5", "gpt-4.1", "gpt-4o", "gpt-oss", "o3-pro", "o3-mini"]
```

---

## System 2: LangGraph (Pregel Agent Runtime)

### What it is

LangGraph rebuilds "agent step" as a **Pregel superstep** (Bulk Synchronous Parallel model from Google's 2010 paper). Every iteration: (1) Plan — which nodes run this step. (2) Execute — run selected nodes in parallel. (3) Update — apply all channel writes atomically.

The user-facing primitive is `StateGraph`: `add_node` + `add_edge` + `add_conditional_edges` + `compile()`. Each user function is a node that reads input channels and returns partial state (dict updates). Reducers say how to merge concurrent writes.

The only abstraction LangGraph absolutely requires:
1. **State is a TypedDict or Pydantic model** with typed channels.
2. **Channels have reducers** (default `LastValue`; `add_messages` for messages; `operator.add` for accumulators). The reducer merges multiple writes in the same step.
3. **Nodes return partial state** (dict with channel updates). Reducer combines with existing channel value.

### Agent Loop (Pregel)

The scheduler (`PregelLoop.tick()`, KNOWN, `pregel/_loop.py:583`):

```python
def tick(self) -> bool:
    if self.step > self.stop:        # step budget exhausted
        self.status = "out_of_steps"
        return False
    self.tasks = prepare_next_tasks(...)    # which nodes run this step?
    if not self.tasks:
        self.status = "done"
        return False
    # ... interrupt checks, cache replay ...
    return True
```

After execution: `after_tick()` calls `apply_writes` (atomic channel update) → emits values event → `_put_checkpoint` → checks `interrupt_after`. The outer driver:

```python
# main.py:2933
with SyncPregelLoop(...) as loop:
    while loop.tick():
        for task in loop.match_cached_writes():    # cache hits — restore writes, skip execution
            loop.output_writes(task.id, task.writes, cached=True)
        for _ in runner.tick(
            [t for t in loop.tasks.values() if not t.writes],  # only non-cached tasks
            timeout=self.step_timeout,
            schedule_task=loop.accept_push,      # mid-step dynamic fan-out
        ):
            yield from _output(stream_mode, ...)    # stream as tasks finish
        loop.after_tick()
```

Key invariant: **writes are invisible until the end of the step**. A node reading `state["messages"]` sees the value as of the start of the step.

### Scheduling Algorithm

`prepare_next_tasks` (KNOWN, `_algo.py:392`):
- **PUSH tasks**: from `TASKS = "__pregel_tasks"` channel — these are `Send` objects from dynamic fan-out.
- **PULL tasks (fast path)**: if `trigger_to_nodes` index built at compile time, only check nodes subscribing to channels updated last step. O(updated_channels) not O(all_nodes × all_channels).
- Tasks sorted before processing — deterministic IDs across replays.

`apply_writes` (KNOWN, `_algo.py:232`, verbatim 6-step algorithm):
1. Update `versions_seen` per node per consumed channel.
2. Compute one `next_version` for the whole step (monotonic int, default `increment`).
3. Consume input channels (mark read; `EphemeralValue` channels clear).
4. Group writes by channel; skip reserved channels.
5. Apply via channel reducer; bump version if `channel.update(vals)` returns `True`.
6. Channels not written this step get `.update([])` called — allows `LastValueAfterFinish` state machines.
7. If no updated channels overlap `trigger_to_nodes` (tentative final step): call `.finish()` on all channels — makes `LastValueAfterFinish` values readable.

Reserved channel keys (all interned via `sys.intern`): `__input__`, `__interrupt__`, `__resume__`, `__error__`, `__error_source_node__`, `__no_writes__`, `__pregel_tasks`, `__return__`, `__previous__`. Writes to these don't trigger downstream edges.

### Task Execution

`PregelRunner.tick` (KNOWN, `_runner.py:176`):
- **Fast path**: single task → run inline on calling thread. Zero thread-pool overhead (common case: linear graph).
- **General path**: submit all tasks to `ThreadPoolExecutor` (sync) or `asyncio.create_task` (async), wait with `FIRST_COMPLETED`. `yield` after each completion — lets driver flush stream in real time.
- **Error-handler routing**: a failed task with an attached error-handler edge is not re-raised; instead a handler task is materialized and submitted.
- **Early-stop**: `_should_stop_others` — when one task fails un-handled, sibling in-flight tasks are abandoned immediately (fail-fast within a step).
- `commit(task, exc)` callback: success → push `task.writes` to `checkpoint_pending_writes`; failure → write `ERROR` control write so checkpoint records failure for later resume.

### Retry Policy

`RetryPolicy` (KNOWN, `types.py:406`):

```python
class RetryPolicy(NamedTuple):
    initial_interval: float = 0.5
    backoff_factor: float = 2.0
    max_interval: float = 128.0
    max_attempts: int = 3
    jitter: bool = True
    retry_on: type | Sequence[type] | Callable = default_retry_on
```

Backoff formula (verbatim, `_retry.py:600`):
```python
interval = min(max_interval, initial_interval * (backoff_factor ** (attempts - 1)))
sleep_time = interval + random.uniform(0, 1) if jitter else interval
```

Sleep schedule: `0.5 → 1.0 → 2.0 → … capped at 128.0s`, plus up to 1s jitter. `default_retry_on` retries transient errors (connection errors, HTTP 5xx, `openai.RateLimitError`) but NOT `ValueError`/`TypeError`/`GraphBubbleUp`.

`task.writes.clear()` before each attempt — guarantees no double-writes on retry. `CONFIG_KEY_RESUMING=True` patched on retry so subgraphs resume from checkpoint.

### Channel Types

| Channel | Semantics |
|---|---|
| `LastValue` | Default. Rejects >1 write per step with `InvalidUpdateError`. |
| `BinaryOperatorAggregate` | `op(current, new)`. `operator.add` for lists, `set.union`, etc. |
| `AnyValue` | Last write wins; allows >1 write. |
| `EphemeralValue` | Only available the step it's written; cleared after. Used for input channels. |
| `NamedBarrierValue` | Wait until N specific writers have all written, then release. Join-points. |
| `Topic` | PubSub-style accumulator; configurable `deduplicate`/`accumulate`. Used for `Send` objects (`TASKS` channel). |
| `UntrackedValue` | Like `LastValue` but never persisted in checkpoints. For ephemeral runtime objects (httpx clients). |
| `DeltaChannel` | Persists deltas instead of full snapshots; snapshot every N supersteps (default cap: `DELTA_MAX_SUPERSTEPS_SINCE_SNAPSHOT = 5000`). |

`LastValue` is the critical design choice: multi-write to the same key raises at runtime, forcing users to use `Annotated[list, operator.add]` for keys that multiple parallel nodes write. Surfaces bad patterns at definition time.

### `add_messages` Reducer

The canonical conversation state reducer (KNOWN, `graph/message.py:61`):
- Append-only, **deduplicated by message ID**.
- Missing IDs get UUIDs auto-filled.
- `RemoveMessage(id=X)` — delete a message by ID.
- `RemoveMessage(id="__remove_all__")` — wipe everything before the marker; used by summarization middleware to compact history without losing the summary.
- `format="langchain-openai"` — normalize content blocks for OpenAI shape.

`MessagesState` convenience alias:
```python
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
```

### Dynamic Routing Primitives

**`Send` — dynamic fan-out** (`types.py:654`):
```python
class Send:
    node: str
    arg: Any
    timeout: TimeoutPolicy | None
```
A conditional edge returning `[Send("worker", arg) for arg in items]` spawns N parallel instances of "worker" in the same superstep. Each becomes a separate `PregelExecutableTask`. Writes combined by the reducer. Canonical map-reduce pattern.

**`Command` — node-level routing + state update** (`types.py:749`):
```python
@dataclass
class Command:
    graph: str | None = None         # None = current; Command.PARENT = parent graph
    update: Any | None = None        # partial state update
    resume: dict | Any | None = None # resume value after interrupt
    goto: Send | Sequence | str = ()  # next node(s)
```
Used heavily in multi-agent supervisor patterns: subagent returns `Command(goto="supervisor", update={...})`. `Command.PARENT` lets a subgraph node jump out to the parent graph.

**`interrupt(value)` — durable HITL** (`types.py:801`):
- First call raises `GraphInterrupt`, halting execution.
- Checkpoint written before the exception — resume can happen hours later from another process.
- Interrupt ID: `xxh3_128_hexdigest(ns.encode())` — same node always gets same interrupt ID (idempotent across replays).
- Resume: `graph.invoke(Command(resume="approved"), config=...)` — the `interrupt(...)` call returns "approved" instead of raising.

### Memory / Checkpointing

**Checkpoint shape** (KNOWN, `checkpoint/base/__init__.py:92`):
```python
class Checkpoint(TypedDict):
    v: int                          # format version (currently 1)
    id: str                         # UUID7 or ordered string
    ts: str                         # ISO 8601
    channel_values: dict[str, Any]
    channel_versions: ChannelVersions  # monotonic version per channel
    versions_seen: dict[str, ChannelVersions]   # per-node version map
    updated_channels: list[str] | None
```

Scheduling rule: node N fires in the next step if for any input channel C, `channel_versions[C] > versions_seen[N][C]`.

**Durability modes** (KNOWN, `types.py:87`):
- `"sync"` — persist every checkpoint synchronously before next step. Slowest, safest.
- `"async"` — persist asynchronously while next step runs. Default — best throughput.
- `"exit"` — persist only at graph exit. For local debugging.

**Checkpoint savers** (each a separate PyPI package):
- `InMemorySaver` — `defaultdict[thread_id → dict[ns → dict[id → tuple(checkpoint, metadata, parent_id)]]]`. Plus a `blobs` dict content-addressed by `(thread_id, ns, channel, version)` — identical values across checkpoints share storage.
- `PostgresSaver` / `AsyncPostgresSaver` — tables `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`.
- `SqliteSaver` / `AsyncSqliteSaver`.
- `RedisSaver` (third-party).

**Serializers**: `JsonPlusSerializer` (handles BaseMessages, datetimes, UUIDs), `MsgpackSerializer` (faster), `EncryptedSerializer` (AES-256-GCM wraps any serializer).

**Resume semantics**: On restart, `tick()` calls `_reapply_writes_to_succeeded_nodes` — restores writes of tasks that already succeeded from `checkpoint_pending_writes`, so the driver filters them out of `runner.tick` (`if not t.writes`). Only failed/interrupted tasks re-run. Exactly-once-ish at superstep granularity without requiring node idempotency from the user.

### Store (Long-Term Cross-Thread Memory)

`BaseStore` (KNOWN, `store/base/__init__.py`):
```python
get(namespace: tuple[str, ...], key: str) -> Item | None
search(namespace, *, query=None, limit=10, offset=0, filter=None) -> list[SearchItem]
put(namespace, key, value, *, index=None, ttl=None) -> None
delete(namespace, key) -> None
list_namespaces(prefix=None, suffix=None) -> list[tuple[str, ...]]
```

`SearchItem.score: float | None` — similarity score from vector search. Filter operators are MongoDB-style: `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`.

`TTLConfig` (KNOWN):
```python
class TTLConfig(TypedDict, total=False):
    refresh_on_read: bool = True    # accessing an item refreshes its TTL
    default_ttl: float | None = None  # minutes; None = no expiration
    sweep_interval_minutes: int | None
```

`IndexConfig` (KNOWN):
```python
class IndexConfig(TypedDict, total=False):
    dims: int                       # 1536 for text-embedding-3-small
    embed: Embeddings | str         # "openai:text-embedding-3-small"
    fields: list[str] | None        # ["$"] = whole item, ["text","summary"] = these fields
```

`InMemoryStore` — brute-force cosine similarity. `PostgresStore` — pgvector HNSW or IVFFlat.

### `Runtime` Context Object (v0.6)

KNOWN, `runtime.py:125`:
```python
@dataclass(frozen=True, slots=True)
class Runtime(Generic[ContextT]):
    context: ContextT = None             # user-defined static context (immutable for run duration)
    store: BaseStore | None = None
    stream_writer: StreamWriter          # callable for custom stream events
    heartbeat: Callable[[], None]        # for idle_timeout refresh
    previous: Any = None                 # last return value (functional API)
    execution_info: ExecutionInfo
    server_info: ServerInfo | None
```

`ExecutionInfo` includes `checkpoint_id`, `checkpoint_ns`, `task_id`, `thread_id`, `run_id`, `node_attempt` (1-indexed), `node_first_attempt_time`.

v0.6 pattern: pass static context via `graph.invoke(input, context=MyContext(user_id="..."))` instead of stuffing into `config["configurable"]`. Typed and IDE-completable.

`runtime.heartbeat()` — the only progress signal honored under `TimeoutPolicy(refresh_on="heartbeat")`. Long-running CPU-bound nodes must call this periodically.

`runtime.stream_writer(payload)` — writes a custom event into the outer stream as `("custom", payload)`. How nodes emit application-level progress without callbacks.

### ManagedValues

Read-only state keys computed by the runtime (not stored in channels):
```python
class RemainingStepsManager(ManagedValue[int]):
    @staticmethod
    def get(scratchpad) -> int:
        return scratchpad.stop - scratchpad.step

RemainingSteps = Annotated[int, RemainingStepsManager]
```

The `create_react_agent` prebuilt puts `remaining_steps: RemainingSteps` in `AgentState`. The guard `_are_more_steps_needed` reads it and stops the agent before it dead-ends mid-tool-call.

### Node-Level Caching

`CachePolicy(key_func=default_cache_key, ttl=None)` (KNOWN, `types.py:519`). `default_cache_key` hashes node input with pickle. `ttl=None` = never expires.

Cache read happens in `tick()` before execution — `match_cached_writes()` does a batched multi-get; hits populate `task.writes`, which the driver's `if not t.writes` filter excludes from `runner.tick`. The node body never runs; prior output is replayed.

Cache write happens after task success: `self.cache.set({(ns, key): (task.writes, ttl)})` asynchronously. This is write-replay (channel writes cached), not result-memoisation — cached writes integrate seamlessly into `apply_writes`/`trigger_to_nodes`.

Backends: `InMemoryCache`, `SqliteCache` (`langgraph/cache/`). Redis cache for production.

### Streaming Protocol

```python
StreamMode = Literal[
    "values",       # full state after each step
    "updates",      # just the deltas per node per step
    "checkpoints",  # checkpoint events
    "tasks",        # task-start and task-finish events
    "debug",        # checkpoints + tasks
    "messages",     # LLM token-by-token streaming with metadata
    "custom",       # whatever node sends via runtime.stream_writer
]
```

Combinable: `stream_mode=["updates", "messages"]` yields `("updates", payload)` and `("messages", (chunk, metadata))` tuples interleaved. `subgraphs=True` includes namespaced events from subgraphs.

`"messages"` mode: `_StreamMessagesHandler` hooks into each `BaseChatModel.stream` call and forwards token chunks. Provider-side SSE preserved.

LangGraph Platform: `POST /threads/{thread_id}/runs/stream` → SSE with event types matching stream mode names.

### Multi-Agent Coordination

LangGraph provides primitives; standard patterns are:

**Supervisor pattern**: supervisor node decides which subagent runs next; subagents return `Command(goto="supervisor")`.

**Swarm pattern**: subagents hand off peer-to-peer via `Command(goto="other_agent")`; no supervisor. `langgraph-swarm` package packages this.

**Hierarchical / nested graphs**: compiled graph is a `Runnable`; add as a node into a larger graph. Subgraph has its own state schema and checkpointer namespace. `Command.PARENT` for leaf-to-root jumps.

**Send-based fan-out**: `[Send("worker", arg) for arg in items]` — map-reduce pattern. N parallel worker instances per superstep; reducer aggregates results.

**`RemoteGraph`**: client-side `Pregel`-compatible proxy to a deployed graph. `parent.add_node("subagent", RemoteGraph("my_agent", url=...))` — subagent runs over HTTP via SDK. Hybrid deployments: parent agent local, expensive vision subagent on LangGraph Cloud.

### Functional API

`@entrypoint(checkpointer=...)` + `@task(retry_policy=...)` — imperative sugar over StateGraph. Each `await task_fn(...)` becomes a checkpointed node with retry and timeout. Internally compiles to the same Pregel runtime — the functional API is a sugar layer, not a separate runtime. A crash mid-workflow resumes from the last completed `await`.

### Prebuilt Agent (v2 `create_react_agent`)

Default as of current source (`version="v2"`). Graph topology:

```
START → [pre_model_hook?] → agent(call_model) → [post_model_hook?]
     → { tools | generate_structured_response | END }
tools → agent (loop back)
tools → END (for return_direct tools)
```

- **`pre_model_hook`** — before `call_model`; returns `{"llm_input_messages": trimmed}`. Supported place for context compaction/summarization/trimming. The model sees `llm_input_messages` (windowed); `messages` history stays complete.
- **`post_model_hook`** — after `call_model`; before routing. Used for guardrails, HITL review of tool calls, response filtering.
- **`response_format`** — adds `generate_structured_response` node. Two strategies: `ToolStrategy` (structured output via synthetic tool call) and `ProviderStrategy` (native API). Optionally `(system_prompt, schema)` tuple.

Tool parallel execution (v2): `ToolNode` dispatches via `Send`, one task per tool call — better parallelism and tracing granularity than v1's internal `asyncio.gather`.

### Constants (KNOWN)

| Constant | Value | Source |
|---|---|---|
| `DEFAULT_RECURSION_LIMIT` | `10007` (env `LANGGRAPH_DEFAULT_RECURSION_LIMIT`) | `_internal/_config.py:31` |
| `recursion_limit` for `create_react_agent` | `25` (default) | `_loop.py:1676`, `main.py:2974` |
| `RetryPolicy.initial_interval` | `0.5` s | `types.py:422` |
| `RetryPolicy.backoff_factor` | `2.0` | `types.py:424` |
| `RetryPolicy.max_interval` | `128.0` s | `types.py:426` |
| `RetryPolicy.max_attempts` | `3` | `types.py:428` |
| `RetryPolicy.jitter` | `True` (`random.uniform(0,1)` s extra) | `types.py:430` |
| `Durability` default | `"async"` | `types.py` |
| `START` | `"__start__"` | `_internal/_constants.py` |
| `END` | `"__end__"` | `_internal/_constants.py` |
| `Command.PARENT` | `"__parent__"` | `types.py` |
| `REMOVE_ALL_MESSAGES` | `"__remove_all__"` | `graph/message.py:38` |
| `NS_SEP` | `"|"` | `_internal/_constants.py` |
| `NS_END` | `":"` | `_internal/_constants.py` |
| `NULL_TASK_ID` | `"00000000-0000-0000-0000-000000000000"` | `_internal/_constants.py` |
| `TAG_HIDDEN` | `"langsmith:hidden"` | `_internal/_constants.py` |
| `DELTA_MAX_SUPERSTEPS_SINCE_SNAPSHOT` | `5000` | `channels/delta.py` |
| `CachePolicy.ttl` default | `None` (never expires) | `types.py:519` |
| `TimeoutPolicy.refresh_on` default | `"auto"` | `types.py` |
| `ToolNode.name` default | `"tools"` | `tool_node.py` |
| `RemainingSteps` default (Pydantic variant) | `25` | `chat_agent_executor.py:74` |
| `MultitaskStrategy` options | `"reject"|"interrupt"|"rollback"|"enqueue"` | SDK `runs.create` |
| `IfNotExists` options | `"reject"|"create"` | SDK |
| `OnCompletionBehavior` options | `"delete"|"keep"` | SDK |
| Runner wait mode | `FIRST_COMPLETED` | `_runner.py:285` |

### Honest Gaps

- **Distributed scheduling**: Pregel runs in one process. LangGraph Platform runs each invocation on one worker — not truly distributed within a step.
- **Streaming during single LLM call across fan-out**: fan-out works at step boundaries, not mid-step. Can't `Send` and aggregate token-by-token from multiple LLMs simultaneously.
- **Cycles without a counter**: without `recursion_limit` or `remaining_steps`, loops are effectively unbounded (the 10007 default is a sentinel, not a real cap).
- **Cross-thread broadcast**: channels are per-thread; no built-in pub/sub across threads.
- **Observability**: debug events emitted, but traces require LangSmith or custom callback handlers.
- **Complexity cliff**: the `StateGraph` API is powerful but teaches engineers that "agent loop = Pregel scheduler with channels" — a non-obvious mental model that has to be sold to users.

---

## Verso Implications

### Copy from LangChain

1. **`@tool` decorator with docstring parsing** — automatically extract tool description + args schema from Python function signature and Google-style docstring. This is the ergonomic baseline users expect. ~50 lines.

2. **`InjectedToolArg` / `InjectedState` / `InjectedStore` pattern** — fields annotated as injected are filtered from the schema sent to the LLM but filled by the framework at dispatch time. Verso should support `InjectedContext` (injected from the run context) and `InjectedStore` (injected from the memory store) as first-class annotations.

3. **Tool error policy** (`handle_tool_error=True/str/callable`) — the 4-way error policy is the right shape. Verso should ship the same shape as a first-class `ToolErrorPolicy` type rather than buried kwargs.

4. **`return_direct=True` on tools** — an escape hatch for tools that are themselves final answers (file-download, structured data). Verso should support this.

5. **`remaining_steps` managed value** — expose budget to the node so agents can self-limit gracefully before the hard recursion error. The `_are_more_steps_needed` guard (`remaining_steps < 2 and has_tool_calls`) is the right pattern: stop before dead-ending mid-tool-call.

6. **Middleware/hooks around model and tool calls** — the v1 `before_model` / `wrap_model_call` / `after_model` / `wrap_tool_call` pattern is the cleanest extensibility model for an agent framework. Better than subclassing the agent or monkey-patching. Verso should ship this as `AgentMiddleware` with the same 6 lifecycle hooks.

7. **Summarization compaction** — the `SummarizationMiddleware` pattern (trigger on token threshold, invoke cheaper model, replace old messages with a `SystemMessage` summary using `RemoveMessage(id="__remove_all__")`) is the right design. Verso should ship a built-in `CompactionPolicy` that implements this.

8. **`init_model("provider:model_name")`** — the `"anthropic:claude-sonnet-4-5"` string format is ergonomic. Verso should copy this exact API for model initialization.

9. **`astream_events(version="v2")` event shape** — `{"event", "name", "run_id", "parent_ids", "tags", "metadata", "data"}` with event types `on_chat_model_start/stream/end`, `on_tool_start/end` is the established interface that downstream tooling (LangSmith, dashboards, UIs) already speaks. Verso's streaming API should be compatible with or inspired by this shape.

10. **RRF constant `c=60`** for ensemble retrieval — proven production default, copy it.

### Copy from LangGraph

11. **`add_messages` reducer semantics** — dedup by ID, `RemoveMessage(id=X)` for targeted deletion, `RemoveMessage(id="__remove_all__")` for compaction resets. This is the correct design for a conversation channel. Verso's memory module should implement this.

12. **Durability modes `"sync"|"async"|"exit"`** — these three options cover all production scenarios (slowest-safest, best-throughput, local-debug). Verso's checkpointer should expose the same enum.

13. **`ChannelWrite` with `PASSTHROUGH`/`SKIP_WRITE` sentinels** — the pattern where a node's return dict selectively updates channels, and non-updated channels don't trigger downstream nodes, is fundamental to incremental graph execution. Verso should implement the same if it offers a graph escape hatch.

14. **Per-node `RetryPolicy`** with the specific defaults (`initial=0.5`, `factor=2.0`, `max=128.0`, `attempts=3`, `jitter=True`) — proven production values. Verso should use these exact defaults for LLM-call retries.

15. **Node-level caching as write-replay** — cache the channel writes a node produced, not just its return value. This integrates naturally with the scheduling algorithm (writes-present → skip execution). Verso should think about caching at this level, not at the function-return level.

16. **`Runtime` context object** — the v0.6 typed immutable context (`context: ContextT`) passed to all nodes is better than `config["configurable"]`. Verso should ship a typed `RunContext` dataclass injected into all handlers.

17. **`runtime.stream_writer(payload)` for custom events** — application-level progress without callbacks. Verso's streaming model should include a `context.emit(payload)` that produces custom events on the outer stream.

18. **`MultitaskStrategy: "reject"|"interrupt"|"rollback"|"enqueue"`** — these four concurrent-run behaviors cover every production use case. Verso's thread/session model should support the same options.

19. **`interrupt(value)` with durable checkpoint-before-raise** — HITL via exception is the cleanest design. The checkpoint is written before the exception, so resume can happen from a different process. Verso should implement durable HITL this way, not as a flag or a polling loop.

20. **`subgraphs=True` on stream** — namespaced events from subgraphs carrying their full path tuple enables proper multi-agent observability. Verso's streaming should propagate subagent namespace in event metadata.

### Avoid from LangChain

21. **The `Runnable` / LCEL abstraction layer** — LCEL's `|` operator composition is clean in theory but adds mandatory indirection (15+ classes: `RunnableSequence`, `RunnableParallel`, `RunnableBranch`, `RunnableLambda`, `RunnableBinding`, etc.) that inflates the mental model for simple use cases. Verso should not build a universal composition abstraction. Python callables compose with Python — use them directly. The 700-integration moat is what makes LCEL worthwhile; without it, LCEL is just indirection.

22. **Pydantic v1/v2 dual-support throughout** — `tools/base.py` is riddled with `is_pydantic_v1_subclass` / `is_pydantic_v2_subclass` branch logic. This is a permanent source of subtle bugs. Verso should require Pydantic v2 only (or no Pydantic at all, accepting plain `dict`/`TypedDict`).

23. **The callback manager as the only observability mechanism** — the `BaseCallbackHandler` with 15 hook methods, wired by `run_id`/`parent_run_id` into a tree, is opaque and hard to debug. Verso should use a structured event bus (emit typed events) rather than a handler hierarchy.

24. **`**kwargs` flowing only to the first step in a sequence** — the LangChain behavior where `stop=["..."]` passed to a chain reaches only the first Runnable is a footgun. Verso should have explicit param passing, not implicit propagation.

25. **`AgentExecutor.early_stopping_method="generate"` as an option** — invoking the LLM one more time after hitting the iteration limit to generate a "closing summary" is both expensive and unpredictable in practice. Verso should always fail gracefully with a structured `StopReason.budget_exhausted` rather than an opportunistic extra LLM call.

26. **The v0 `AgentExecutor` legacy stack** — two parallel agent stacks (v0 `AgentExecutor` + v1 `create_agent`) in the same repo is a maintenance burden and a source of confusion. Verso should have one agent loop from day one and deprecate it properly if it needs to change.

27. **`ContextVar`-based implicit config propagation** — `var_child_runnable_config` propagates tags/metadata/callbacks without explicit passing. This is clever but makes it hard to reason about what config any given component is actually running with. Verso should use explicit dependency injection or a typed context object, not contextvar magic.

### Avoid from LangGraph

28. **Pregel as the default execution model** — the BSP/Pregel mental model is non-obvious. "Channels have reducers and writes are invisible until end of step" is not the intuition most developers bring. Verso's default should be a clean sequential ReAct loop; Pregel-style scheduling should be an opt-in escape hatch for legitimate fan-out use cases.

29. **`DEFAULT_RECURSION_LIMIT = 10007`** — this is misleading. Docs say 25; code says 10007; behavior confuses users. Verso should have one sensible default (25-50 for agents) and make it visible.

30. **`StateGraph.add_conditional_edges` with a `path_map` dict** — the `router_fn → path_map → node_name` indirection is extra API surface. Verso should let the router function return the node name or a `Command` directly.

31. **The `Annotated[T, reducer]` syntax for channels** — using Python type annotations as reducer declarations is clever but creates an implicit coupling between type system and runtime behavior. Verso should make channel reducers explicit (a named field or explicit argument), not implicit via `Annotated`.

32. **The 30-constant reserved-key namespace** — `__pregel_tasks`, `__pregel_send`, `__pregel_read`, `__pregel_call`, etc. These are internal plumbing that leaks into user-visible error messages. Verso should keep internal key namespaces fully hidden.

33. **Platform SDK (5 sub-clients, 30+ endpoints) as part of the core framework** — the SDK coupling (LangSmith tracing, LangGraph Platform, RemoteGraph proxy) makes it hard to use LangGraph without LangChain's cloud offerings. Verso should ship a clean framework-only surface with cloud deployment as an opt-in adapter.

### Verso Could Improve On

34. **Single-track streaming**: LangGraph has 7 stream modes (`values`, `updates`, `checkpoints`, `tasks`, `debug`, `messages`, `custom`) that can be combined. This is powerful but complex. Verso should default to one unified structured event stream (like `astream_events v2`) and expose the rest as filters rather than separate modes.

35. **Tool schema generation**: LangChain supports both `dict` (raw JSON Schema) and Pydantic (v1 and v2) for `args_schema`. This is flexible but adds combinatorial branch logic. Verso should unify: always generate from the function signature (type hints → JSON Schema automatically), accept override via a `schema=` arg if needed, no Pydantic v1.

36. **Memory architecture**: LangChain/LangGraph separate short-term (checkpointer), long-term (Store), and compaction (SummarizationMiddleware) into three different systems with different APIs. Verso should unify these under one `Memory` interface with short-term (channel state), long-term (vector + KV), and compaction (TTL-based or token-budget-based) as properties of the same object.

37. **Interrupt API ergonomics**: LangGraph's `interrupt(value)` + `Command(resume=...)` is durable and clean but requires the caller to know about `Command` to resume. Verso could expose a higher-level `await agent.hitl.request(question)` → returns answer — making the await/resume invisible to the node author while still checkpoint-backing it under the hood.

38. **Agent self-awareness of budget**: LangGraph's `remaining_steps` ManagedValue is runtime-computed and requires a specific state schema key. Verso should inject budget information through the `RunContext` object (`context.budget.remaining`, `context.budget.is_last_step`) rather than as a state channel, keeping it out of user state schemas entirely.

---

## Summary Table

| Dimension | LangChain | LangGraph | Verso recommendation |
|---|---|---|---|
| Agent loop | v0: explicit `while` with counter; v1: delegates to LangGraph Pregel | BSP superstep: plan → execute → commit atomically | Clean ReAct `while` loop as default; BSP graph as opt-in escape hatch |
| Tool registration | `@tool` + docstring + type hints → `BaseTool` | Same via `BaseTool`; `ToolNode` dispatches in parallel | Copy `@tool` decorator; first-class `InjectedContext`/`InjectedStore` |
| Tool errors | 4-way policy per tool | Same + error-handler routing at node level | Copy the 4-way policy; add structured `ToolResult.error` type |
| Loop termination | `max_iterations=15`, wall-clock, `return_direct` | `recursion_limit` step budget; `remaining_steps` managed value | `max_steps=25` default; expose `context.budget.remaining` |
| Context | LCEL: implicit `ContextVar` propagation | v0.6: typed `Runtime[ContextT]` dataclass | Typed `RunContext[ContextT]` injected into all handlers |
| Memory | v0: 7 memory classes + 30 backends (deprecated); v1: Checkpointer + Store + SummarizationMiddleware | Checkpointer (short-term) + Store with vector + TTL (long-term) | Unified `Memory` interface; `add_messages` reducer semantics |
| Streaming | 3 modes (chunks, events, JSONPatch); 7 LG modes | 7 stream modes combinable | One structured event stream; filters for granularity |
| Interrupts | HITL via HumanInTheLoopMiddleware | Durable `interrupt(value)` + `Command(resume=...)` | `await context.hitl.request(question)` → answer; checkpoint-backed |
| Retry | `RunnableRetry(stop_after_attempt=3)` | Per-node `RetryPolicy` with exact backoff defaults | Copy RetryPolicy shape and defaults verbatim |
| Multi-agent | No native support; delegates to LangGraph | Supervisor, swarm, hierarchical, `RemoteGraph` proxy | `Send`+`Command` as escape hatch; `RemoteAgent` for distributed subagents |
| Caching | `BaseChatModel._generate_with_cache` (LLM-level) | Node-level write-replay cache with TTL | Node-level write-replay cache; TTL config; `InMemoryCache` + Redis |
| DX complexity | LCEL: 15+ Runnable types; deep callback tree | `StateGraph` API + reserved-key namespace; steep mental model | Simple API first; complexity opt-in; never expose internal plumbing |
