# LANGGRAPH — Raw Extraction (frameworks track)

Source: `/Users/seventyleven/Desktop/researchfms/teardowns/LANGGRAPH.md` (2063 lines, 123KB). Repo: `langchain-ai/langgraph @ 076e2a3`. All "KNOWN" tags are the teardown author's claim of source-verified facts; "INFERRED" are my judgments for Verso.

LangGraph is THE counter-position for Verso's "we don't force the graph." This note separates: (A) what the graph GENUINELY buys that Verso must MATCH without a graph, vs (B) pure overkill Verso must REFUSE.

---

## 1. The core thesis of LangGraph (verbatim framing)

> "A graph-based agent orchestration runtime where nodes are functions that read and write **channels** (typed state), and the scheduler runs **supersteps** (Pregel/BSP-style) — every iteration is checkpointed, every node is retryable, every channel update is durable." (one-line summary, line 3)

> "The 'moat' is not the runtime — it's the **mental model**. Convincing engineers that 'agent loop' should be 'Pregel scheduler with channels' is the harder half." (line 934)

User-facing primitive: **StateGraph** — `graph.add_node(name, fn)` + `graph.add_edge("a","b")` + `graph.add_conditional_edges("a", router_fn)` + `graph.compile()` → `CompiledStateGraph` (internally a `Pregel`). (line 35)

**This is exactly Verso's counter-position.** Verso's thesis: ONE clean async ReAct loop, no graph, no 500+ nodes. LangGraph forces the BSP scheduler + channels mental model on every user. The teardown ITSELF admits the runtime is not the moat — the mental-model tax is.

---

## 2. StateGraph builder API (KNOWN, state.py:130)

```python
class StateGraph(Generic[StateT, ContextT, InputT, OutputT]):
    def __init__(self, state_schema, *, context_schema=None, input_schema=None,
                 output_schema=None, node_defaults=None): ...
    def add_node(self, node_or_name, action=None, *, metadata=None, input_schema=None,
                 retry_policy=None, cache_policy=None, defer=False, timeout=None): ...
    def add_edge(self, start_key: str | list[str], end_key: str): ...
    def add_conditional_edges(self, source, path: Callable, path_map=None): ...
    def add_sequence(self, nodes): ...
    def set_entry_point(self, key); def set_finish_point(self, key): ...
    def compile(self, *, checkpointer=None, store=None, cache=None,
                interrupt_before=None, interrupt_after=None, debug=False,
                name=None, durability=None, transformers=None) -> CompiledStateGraph: ...
```

- `START = "__start__"`, `END = "__end__"` sentinels.
- `add_edge([a,b,c], "d")` = a JOIN: `d` runs only after all three complete (`waiting_edges`, line 966).
- Multi-edges from same source ONLY allowed if state key is `Annotated` (forces explicit reducer choice). Else `ValueError("Already found path for node 'X'.")` (line 190).
- Conditional edge `path_map={"yes":"tools","no":END}`: router returns the dict KEY.

**OVERKILL for Verso:** the whole `add_node/add_edge/add_conditional_edges/compile` ceremony is the "force the graph" tax. A linear ReAct loop is `model→tools→model`; encoding it as nodes+edges+a router function + a compile step is exactly the "500+ nodes" complexity Verso refuses.

---

## 3. Pregel runtime / superstep scheduler (KNOWN)

`Pregel` class (main.py:4314 lines) is the scheduler. `PregelLoop` (`_loop.py:155`) holds runtime state. Core: `tick()` (plan which nodes run) → runner executes in parallel via executor/`asyncio.gather` → `after_tick()` applies writes atomically + checkpoints.

Driver pattern (KNOWN, simplified `Pregel.stream`):
```python
async with PregelLoop(...) as loop:
    while loop.tick():
        await runner.atick(loop.tasks, timeout=…, retry_policy=…)
        loop.after_tick()
        if loop.status == "out_of_steps":
            raise GraphRecursionError(...)
```

**Key invariant (line 687):** "writes are invisible until the end of the step. A node reading `state['messages']` sees the value as of the start of the step, never what other nodes wrote during the step. This deterministic semantics is what makes the model checkpointable and replayable."

Default recursion limit (KNOWN, `_config.py:31`): `DEFAULT_RECURSION_LIMIT = int(getenv("LANGGRAPH_DEFAULT_RECURSION_LIMIT", "10007"))` — "effectively unbounded by default." Older docs cited 25. The prebuilt `create_react_agent` uses `state["remaining_steps"]` for self-limit instead.

**Honest gap from LangGraph itself (line 906-908):**
- "Distributed scheduling. Pregel runs in one process."
- "Cycles without a counter — without `recursion_limit` or `remaining_steps`, infinite loops are unbounded by default."

**VERSO RELATION:** Verso's loop already has StopReason.STUCK / doom-loop detection + max_steps_policy grace-call — which is STRICTLY BETTER than LangGraph's 10007 sentinel "effectively unbounded." The BSP superstep machinery (fan-out, atomic step boundary, deterministic replay) is what the graph buys for PARALLEL multi-node fan-out — Verso doesn't need it for a single ReAct loop.

---

## 4. Channels + reducers (the state-integrity story) — KNOWN

Channels are typed state. Reducers say how to merge multiple writes in one step:
- `LastValue` (default) — REJECTS concurrent writes (raises at runtime if two nodes write same channel same step). "what forces users to use `Annotated[list[str], add_messages]` or `Annotated[list, operator.add]`" (line 94).
- `LastValueAfterFinish` — value invisible to readers until `finish()` called (output channels in subgraphs).
- `BinaryOperatorAggregate(op)` — stores `op(current, new)`; `operator.add`, `set.union`, anything associative.
- `Topic` — accumulator/pubsub; the internal `TASKS` channel is `Topic(Send, accumulate=False)`, cleared each step.

### 4.1 `add_messages` reducer (KNOWN, message.py:61) — THE conversation-state primitive

Behaviors (this is the state-integrity / orphan-repair-adjacent logic):
- Append-only, **deduplicated by message ID** (`merged_by_id`).
- Missing IDs get UUIDs filled in (`if m.id is None: m.id = str(uuid.uuid4())`).
- `RemoveMessage(id=X)` deletes a message by ID.
- `RemoveMessage(id=REMOVE_ALL_MESSAGES)` (`"__remove_all__"`) wipes everything before the marker, keeps what's after — "used by summarization middleware."
- Deleting an ID that doesn't exist → `raise ValueError("Attempting to delete a message with an ID that doesn't exist")`.
- `format="langchain-openai"` normalizes content blocks to OpenAI shape.

```python
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
```

**VERSO RELATION:** Verso's history is the ContextBundle + prune()-masks-old-tool-outputs (never silent-drop) + repair_history resume-guard (orphan tool-call/result repair). LangGraph's `add_messages` is ID-dedup + RemoveMessage. The orphan-tool-call problem LangGraph solves implicitly (dedup by ID, explicit delete) Verso solves explicitly with repair_history. **Verso already covers the genuine need.** The `LastValue` reject-on-concurrent-write is a GRAPH artifact: it only exists because parallel nodes can write the same channel — a single ReAct loop never has that race, so Verso doesn't need reducers at all. This is pure graph-induced complexity.

---

## 5. interrupt() — durable HITL (KNOWN, types.py:801) — WHAT THE GRAPH GENUINELY BUYS

```python
def interrupt(value: Any) -> Any:
    """The first invocation raises a `GraphInterrupt` exception, halting execution.
    The provided value is included with the exception and sent to the client.
    A client resuming the graph must use the `Command` primitive to specify a
    value for the interrupt and continue execution."""
```

- "**durable**: the checkpoint is written before the exception is raised, so the resume can happen hours later from another process." (line 426)
- Interrupt id = `xxh3_128_hexdigest(ns.encode())` so "the same node always gets the same interrupt ID (**idempotent across replays**)." (line 426)
- Use case: tool calls `interrupt({"question":"approve?","tool_call":...})` → graph pauses → client reads, asks user → `graph.invoke(Command(resume="approved"), config=...)` → execution resumes with `interrupt(...)` now returning "approved" instead of raising. (line 428)
- `interrupt_before` / `interrupt_after` on compile() or per static-node-list; `should_interrupt` gate uses a synthetic `INTERRUPT="__interrupt__"` node in `versions_seen` so "consecutive interrupts on the same checkpoint don't fire twice."

**VERSO RELATION (the head-to-head):** This is precisely Verso's durable seam — `ctx.hitl.request` pause/resume (idempotent-up-to-request), SqliteCheckpointStore checkpoint-each-step, resume() in a FRESH process. Verso ships ALL FOUR of LangGraph's "what's novel" durable HITL guarantees (durable checkpoint-before-pause, resume from another process hours later, idempotent ID across replays, resume-value injection) **WITHOUT requiring a graph** — it's the one-flag tactical→durable promotion. LangGraph requires you to build the StateGraph first; Verso flips a flag on an existing ephemeral agent. Verso WINS the seam comparison.

---

## 6. Send (dynamic fan-out) + Command (node routing) — KNOWN

```python
class Send:  # types.py:654
    node: str; arg: Any; timeout: TimeoutPolicy | None

@dataclass
class Command(Generic[N], ToolOutputMixin):  # types.py:749
    graph: str | None = None        # None=current; Command.PARENT="__parent__"
    update: Any | None = None       # partial state update
    resume: dict | Any | None = None
    goto: Send | Sequence[Send | N] | N = ()
    PARENT: ClassVar[Literal["__parent__"]] = "__parent__"
```

- Conditional edge returning `[Send("worker", arg) for arg in items]` fans out to N parallel `worker` instances in one superstep (map-reduce). Writes combined by destination channel's reducer.
- `Command(update={...}, goto="next_node")` both updates state AND forces next node — "bypassing the static edges." Used by supervisor multi-agent: each subagent returns `Command(goto="supervisor", update={...})`.
- `Command.PARENT` lets a subgraph leaf jump to parent graph's node.

**VERSO RELATION:** `Send` map-reduce fan-out is a genuine capability the graph buys — but it's on Verso's NON-GOAL list (no orchestrator-as-primitive, no graph-DSL). For Verso, parallel sub-work is "dispatch parallel agents" when genuinely file-disjoint, not a Send primitive. `Command(goto=...)` is graph routing — Verso uses tool-return + the loop, not node-jumps. **avoid-overkill.**

---

## 7. Durability modes (KNOWN, types.py:87)

```python
Durability = Literal["sync", "async", "exit"]
```
- `"sync"`: persist every checkpoint synchronously before next step. Slowest/safest.
- `"async"`: persist asynchronously while next step runs. DEFAULT, best throughput.
- `"exit"`: persist only at graph exit. Local debugging.
- `_delta_write_futs` machinery: even under async, "a checkpoint never becomes durable before the writes that produced it."

**VERSO RELATION:** Verso's SqliteCheckpointStore checkpoints each step (crash-recoverable). The sync/async/exit knob is a reasonable durability-vs-throughput tradeoff. **steal-additive (small):** a per-store durability mode ("checkpoint sync vs async-after-step vs only-on-exit") is additive and byte-identical when unused — if Verso's checkpoint is always-sync today, an async/exit option is a pure throughput add for prod. Worth a look, NOT the graph.

---

## 8. Retry policy (KNOWN, types.py:406)

```python
class RetryPolicy(NamedTuple):
    initial_interval: float = 0.5
    backoff_factor: float = 2.0
    max_interval: float = 128.0
    max_attempts: int = 3
    jitter: bool = True
    retry_on: ... = default_retry_on   # connection errors, httpx 5xx, openai.RateLimitError
```
Per-node: `add_node("model", fn, retry_policy=RetryPolicy(max_attempts=5))`. "The runner re-executes the node from scratch on retry — writes from the failed attempt are discarded." (line 353)

**VERSO RELATION:** Verso ships RetryPolicy + FailoverModel + typed error taxonomy (auth/content fail fast). **verso-already-has.** The "re-execute from scratch, discard failed-attempt writes" is the same idempotency posture as Verso's per-tool idempotent/max_attempts.

---

## 9. ToolNode + create_react_agent prebuilt (KNOWN)

`ToolNode` (tool_node.py:2030 lines): tools stored by name; parallel exec via `executor.map`/`asyncio.gather`; default error policy catches **invocation errors** (bad args from model) but lets **execution errors** (tool `_run` raises) propagate.

`tools_condition` router (line 1582):
```python
def tools_condition(state, messages_key="messages"):
    ai_message = state[messages_key][-1]
    if not isinstance(ai_message, AIMessage): return END
    if ai_message.tool_calls: return "tools"
    return END
```

`create_react_agent` graph: `START → pre_model_hook → agent → post_model_hook → tools|generate_structured_response|END`, `tools → agent` loop. v1: tool node runs all calls in parallel internally; v2: dispatches via Send, one task per call.

Self-limit (line 620) emits literal: `"Sorry, need more steps to process this request."` instead of raising `GraphRecursionError`. (line 577 — "graceful-shutdown behavior")

**VERSO RELATION:** This IS Verso's loop, expressed as a 5-node graph. Verso's @tool (docstring→schema), per-tool parallel exec, invocation-vs-execution error split (jsonish parse waterfall + coerce), pre/post_model & pre/post_tool Hooks, output_type structured response, and the grace-call-at-max_steps (vs LangGraph's literal "Sorry, need more steps") are ALL shipped. **verso-already-has** — and Verso's version is the loop itself, not a graph compiled to mimic a loop. The "Sorry, need more steps" graceful shutdown == Verso max_steps_policy grace-call.

---

## 10. Functional API @entrypoint / @task (KNOWN, func/__init__.py)

```python
@entrypoint(checkpointer=InMemorySaver())
def workflow(input_data: str) -> str:
    result1 = await classify_input(input_data)
    return await summarize(result1)

@task(retry_policy=RetryPolicy(max_attempts=5))
async def classify_input(text): ...
```
"Compiles to the same Pregel runtime — sugar over StateGraph, not a separate runtime. Each `await task_fn(...)` becomes a synthetic node... a crash mid-workflow resumes from the last completed `await`." (line 615)

**VERSO RELATION:** This is LangGraph's tacit admission that the graph is too heavy — they built an imperative escape hatch that hides the graph. Verso's whole thesis is "imperative loop is the default, no graph to escape." `@task`'s "resume from last completed await" == Verso checkpoint-each-step resume(). **verso-already-has** (the seam IS the default, not a sugar layer). Confirms Verso's leanness thesis: even LangGraph users want to NOT see the graph.

---

## 11. Checkpoint shape + saver protocol (KNOWN)

```python
class Checkpoint(TypedDict):  # checkpoint/base:92
    v: int; id: str; ts: str
    channel_values: dict[str, Any]
    channel_versions: ChannelVersions          # monotonic version per channel
    versions_seen: dict[str, ChannelVersions]   # per-node version map
    updated_channels: list[str] | None

class CheckpointMetadata(TypedDict, total=False):
    source: Literal["input", "loop", "update", "fork"]
    step: int; parents: dict[str,str]; run_id: str
```
"`versions_seen` is critical: node N runs next step if for some input channel C, `channel_versions[C] > versions_seen[N][C]`." (line 727)

```python
class BaseCheckpointSaver(Generic[V]):  # checkpoint/base:176
    def get_tuple(self, config) -> CheckpointTuple | None: ...
    def list(self, config, *, filter=None, before=None, limit=None): ...
    def put(self, config, checkpoint, metadata, new_versions): ...
    def put_writes(self, config, writes, task_id, task_path=""): ...
    def delete_thread(self, thread_id): ...
    # async: aget_tuple, alist, aput, aput_writes, adelete_thread
```

Savers (each separate PyPI pkg): `InMemorySaver`, `PostgresSaver`/`AsyncPostgresSaver`, `SqliteSaver`/`AsyncSqliteSaver`, `RedisSaver` (3rd-party). Serializers: `JsonPlusSerializer` (messages/datetime/UUID), `MsgpackSerializer` (faster), `EncryptedSerializer` (AES-256-GCM wrapping any serializer).

Content-addressing: blobs keyed by `(thread_id, ns, channel, version)` — "identical values across checkpoints share storage." Resuming an old checkpoint "walks the version chain to find the right blob for each channel." (line 774)

**VERSO RELATION:** Verso ships SqliteCheckpointStore + checkpoint-each-step + resume + history()/fork() time-travel. The `source: input|loop|update|fork` metadata and content-addressed blob dedup are nice mechanics. **steal-additive candidates (small, additive, byte-identical-when-unused):** (a) `EncryptedSerializer` (AES-256-GCM) as an opt-in checkpoint-store wrapper for prod compliance; (b) content-addressed blob dedup so forking a long thread doesn't copy the whole history. Both are pure storage-layer adds that don't touch the loop and don't require a graph. The Postgres saver itself is on-thesis only if Verso wants a prod backend beyond sqlite — currently a NON-GOAL to over-build.

---

## 12. apply_writes — atomic update / state-integrity algorithm (KNOWN, _algo.py:232-345)

The 7 load-bearing steps (verbatim from teardown §R2.2):
1. **Tasks sorted by path** (`task_path_str(t.path[:3])`) → deterministic update order even when parallel.
2. **Single `next_version` computed once per step**, applied to all updated channels (so the scheduler can compare `channel_versions` vs `versions_seen`).
3. Consume input channels (`channels[chan].consume()`); default `get_next_version` is `increment` (monotonic ints from 1).
4. Group writes by channel, **skip reserved channels** (`NO_WRITES, PUSH, RESUME, INTERRUPT, RETURN, ERROR, ERROR_SOURCE_NODE`). Write to unknown channel → `logger.warning(...ignoring it)`.
5. Apply via reducer; bump version IFF `channel.update()` returns True.
6. `bump_step` → unwritten-but-available channels get `.update([])` (mostly no-op; `LastValueAfterFinish` flips `finished`).
7. **Finalization:** if `updated_channels.isdisjoint(trigger_to_nodes)` (nothing would trigger another node → tentative final step), call every channel's `.finish()` — `LastValueAfterFinish.finish()` flips visibility. "what makes 'the graph runs to fixpoint, then output channels become readable' work." (line 1102)

`prepare_next_tasks` fast path: compile builds `trigger_to_nodes: dict[chan, list[node]]` → "only checks nodes that subscribe to channels updated last step. Otherwise scans every node — O(N²) per step." (line 1181)

**VERSO RELATION:** This entire algorithm exists ONLY because the graph has parallel nodes writing shared channels with versions and fixpoint detection. A single ReAct loop has none of this — there is no "which node fires next" scheduling problem, no concurrent-write merge, no fixpoint. **avoid-overkill — this is the single clearest example of "complexity-for-the-graph's-sake" that Verso's thesis exists to refuse.** ~1,460 lines of `_algo.py` that Verso replaces with "append the tool result, loop."

---

## 13. Postgres saver schema (KNOWN, verbatim DDL, base.py:43-91)

4 tables: `checkpoint_migrations(v)`, `checkpoints(thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, type, checkpoint JSONB, metadata JSONB)`, `checkpoint_blobs(thread_id, ns, channel, version, type, blob BYTEA nullable)`, `checkpoint_writes(thread_id, ns, checkpoint_id, task_id, idx, channel, type, blob, task_path)`. Indexes created CONCURRENTLY (no lock). 9 migrations (v0-v9); v9 added `task_path` "for deterministic write ordering in apply_writes." Blob upserts are `ON CONFLICT DO NOTHING` — "blobs are immutable: once written, never overwritten." Checkpoint loaded in ONE trip via subquery joining `channel_versions` against `checkpoint_blobs`.

**VERSO RELATION:** Production-grade checkpoint backend with content-addressed immutable blobs + concurrent index creation. **neutral-context / minor steal-additive:** the "immutable blob, ON CONFLICT DO NOTHING, content-addressed by version" pattern is a clean prod checkpoint-store design if Verso ever adds a Postgres backend — but a Postgres saver is not on-thesis today (sqlite is the shipped path). Don't build the platform.

---

## 14. Time-travel / get_state / update_state (KNOWN, SDK ThreadsClient)

- `get_state(thread_id, *, checkpoint=None, subgraphs=False)` → current state
- `update_state(thread_id, values, *, as_node=None)` → write to state WITHOUT running
- `get_history(thread_id, *, limit=10, before=None, metadata=None)` → list of checkpoints
- `CheckpointMetadata.source` includes `"fork"`; time-travel = "passing a specific checkpoint ID." (line 37)
- `runs.cancel(..., action="interrupt"|"rollback")`; `MultitaskStrategy: "reject"|"interrupt"|"rollback"|"enqueue"`.

**VERSO RELATION:** Verso ships history()/fork() time-travel + recall_as_of (memory time-travel). `update_state(as_node=...)` (inject state as if a node produced it) is graph-specific. The `MultitaskStrategy` (reject/interrupt/rollback/enqueue when a run is already active on a thread) is a genuine **concurrency-at-the-seam** concern. **steal-additive (small):** a documented policy for "resume() called while a run is already active on the same checkpoint thread" (reject vs enqueue) is an additive durable-seam hardening, byte-identical when unused — relevant to Verso's reliability-at-the-seam story. Verso already has idempotent-up-to-request; an explicit multitask policy is the next notch.

---

## 15. LangGraph Platform / RemoteGraph / Cloud (KNOWN) — pure platform, NON-GOAL for Verso

- LangGraph Platform: hosted runtime wrapping a compiled graph, REST+SSE API, managed Postgres threads, "Studio" UI for observability + time-travel.
- `RemoteGraph("my_agent", url=..., api_key=...)` (remote.py:1191 lines): client-side Pregel-compatible proxy; can be `add_node`-ed into a parent graph so an expensive subagent runs on Cloud while parent runs local.
- SDK: 5 sub-clients (`.assistants/.threads/.runs/.crons/.store`), ~30 endpoints. `runs.create` has ~22 params (webhook, multitask_strategy, after_seconds delay, if_not_exists, on_completion, langsmith_tracing, durability...).

**VERSO RELATION:** Verso is explicitly "not an SDK, not the platform." **avoid-overkill** — RemoteGraph (~1,200 lines) + the SDK (~2,000 lines sync+async) + Cloud are the distributed-platform layer that explains why the repo is 72,573 lines vs the ~3,200-line core. This is exactly the "platform creep" Verso refuses.

---

## 16. Size accounting (KNOWN, from teardown)

- Core runtime clone estimate: ~3,200 lines (channels + checkpoint format + InMemorySaver + serializer + StateGraph builder + Pregel loop + Send/Command + streaming + interrupt + ToolNode).
- Actual repo: **72,573 lines** — the delta is 5 backend savers, functional API, RemoteGraph, store+semantic-search, cache backends, CLI, SDK (Py+JS), tracing, tests, "1,800+ lines of public types with backwards-compatibility shims."
- `_algo.py` alone (scheduler) = 1,460 lines; `main.py` = 4,314; `tool_node.py` = 2,030; `state.py` = 1,964.

**VERSO RELATION:** Verso's core loop is <200 lines. The teardown's own numbers are the leanness argument: the genuine durable+HITL+time-travel value lives in maybe ~2,500 lines of checkpoint/interrupt machinery; the other ~70,000 lines are graph-scheduler + platform + SDK that Verso correctly refuses. **This is the headline finding for the "we don't force the graph" thesis.**

---

## 17. What the graph GENUINELY buys (must MATCH without a graph) vs OVERKILL

GENUINELY BUYS (Verso must match — and DOES, via the one-flag seam):
- Durable checkpoint-each-step + resume in a fresh process hours later → Verso: SqliteCheckpointStore, resume().
- Idempotent-across-replay HITL pause/resume with resume-value injection → Verso: ctx.hitl.request (idempotent-up-to-request).
- Time-travel / fork from a past checkpoint → Verso: history()/fork().
- Per-step retry with discard-failed-writes idempotency → Verso: per-tool idempotent/max_attempts + RetryPolicy.
- State-integrity (orphan tool-call/result repair, message dedup) → Verso: repair_history + prune-never-silent-drop.

PURE OVERKILL (Verso must REFUSE):
- StateGraph/nodes/edges/conditional-edges ceremony for what is a linear loop.
- Channels + reducers + LastValue-reject-concurrent-write (only needed because parallel nodes share state).
- BSP superstep scheduler + `apply_writes` 7-step fixpoint algorithm + `versions_seen`/`trigger_to_nodes` (~1,460 lines).
- Send/Command node-routing primitives (orchestrator-as-primitive = NON-GOAL).
- RemoteGraph + Platform + SDK + Studio (not-an-SDK, not-a-platform = NON-GOAL).
- 10007 "effectively unbounded" default recursion limit (Verso's STUCK/doom-loop detection is strictly better).

**Verdict on the seam head-to-head:** LangGraph forces you to author the graph FIRST, then get durable/HITL/time-travel as graph properties. Verso's tactical→durable seam grants the SAME four guarantees by flipping ONE flag on an already-written ephemeral agent — additive, byte-identical when unused, no rewrite, no graph. Verso wins the comparison the teardown's own "what's novel" list (#1 Pregel, #4 durable interrupts) sets up.
