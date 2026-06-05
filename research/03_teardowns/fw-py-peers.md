# Python Framework Peers — Verso Research Note

## Cluster: fw-py-peers

### Systems: Burr (Apache) · Marvin 3.0 (PrefectHQ) · Julep · Atomic Agents · PocketFlow · Griptape

*Sources: live source reads of `apache/burr` @ HEAD (burr/core/{persistence,application,action,state}.py), `PrefectHQ/marvin` @ HEAD (src/marvin/{thread,engine,tasks,agents}.py), `julep-ai/julep` @ HEAD (src/agents-api, src/scheduler), `BrainBlend-AI/atomic-agents` @ HEAD (atomic-agents/base/base_agent.py, context_providers), `The-Pocket/PocketFlow` @ HEAD (pocketflow/__init__.py — full 100-line core), `griptape-ai/griptape` @ HEAD (griptape/memory/task, griptape/structures). Cloned 2026-06-05 into /tmp/verso-re-pyfw. Cross-ref: `fw-crewai-letta.md` (Letta paged memory), `fw-langchain-langgraph.md` (LangGraph checkpoint seam), `infra-serving.md` (streaming/cancellation patterns).*

*Labels: KNOWN = read from source at file:line. INFERRED = derived from code behavior/tests/docs. DESIGNED = Verso engineering judgment, not in the source.*

---

## Burr (apache/burr)

### What It Is

State-machine-first agent framework. An application is an explicit graph of `@action`-decorated pure functions over a typed `State`. The headline design property — the one Verso is positioned against — is that **the same graph runs in-memory or durably by adding exactly one builder call** (`.with_state_persister()`), and that persistence is not woven into the loop: it is a **lifecycle hook fired after every step**. The loop has no idea persistence exists. This is the cleanest open-source implementation of the tactical↔durable seam.

### The Persister Seam — How It Actually Works (KNOWN)

The seam is **not** a wrapper around the loop, **not** a subclass of the application, and **not** a context manager around `run()`. It is a **post-step lifecycle hook** appended to a `LifecycleAdapterSet`. Mechanism, end to end:

1. **`ApplicationBuilder.with_state_persister(persister, on_every="step")`** (`application.py:2521`) does almost nothing — it stores `self.state_persister = persister` and returns `self`. `on_every` is validated to be `"step"` (the only supported value; anything else raises). No wrapping happens here. (KNOWN `application.py:2538-2542`.)

2. The wrapping happens at **`.build()`** (sync) / **`.abuild()`** (async). `build()` (`application.py:2818`):
   ```python
   if self.state_persister:
       self._set_sync_state_persister()   # wraps persister → hook → adapter list
   if self.state_initializer:
       self._load_from_sync_persister()   # loads prior state into self.state/self.sequence_id
   return self._build_common()
   ```

3. **`_set_sync_state_persister()`** (`application.py:2565`) is the actual seam:
   ```python
   if self.state_persister.is_async():
       raise ValueError("building sync app but used async persister ... use .abuild()")
   if not isinstance(self.state_persister, persistence.BaseStateSaver):
       self.lifecycle_adapters.append(self.state_persister)        # power-user: raw LifecycleAdapter
   else:
       if not self.state_persister.is_initialized():               # table must exist
           raise RuntimeError("Uninitialized persister. Call .initialize() first.")
       self.lifecycle_adapters.append(persistence.PersisterHook(self.state_persister))
   ```
   So a `BaseStateSaver` gets wrapped in a `PersisterHook` (a `PostRunStepHook`); a raw lifecycle adapter is appended as-is. Either way it lands in `self.lifecycle_adapters`, which `_build_common` passes as `LifecycleAdapterSet(*self.lifecycle_adapters)` to the `Application` (`application.py:2761`).

4. **`PersisterHook`** (`persistence.py:214`) is dead simple — a `PostRunStepHook` whose `post_run_step` forwards to `persister.save(...)`:
   ```python
   class PersisterHook(PostRunStepHook):
       def __init__(self, persister): self.persister = persister
       def post_run_step(self, *, app_id, partition_key, sequence_id, state, action, result, exception, **kw):
           status = "completed" if exception is None else "failed"
           self.persister.save(partition_key, app_id, sequence_id, action.name, state, status)
   ```
   On exception it still saves, with `status="failed"` and the *pre-action* state (the loop's `_step` saves `new_state` on success, but on exception `new_state` is still `self._state` = the prior state — see loop below). (KNOWN `persistence.py:220-234`.)

5. The loop fires the hook with **no knowledge of persistence**. `Application._step` (`application.py:949`), inside `with self.context:`:
   - `call_all_lifecycle_hooks_sync("pre_run_step", ...)`
   - run the action (single-step → `(result, new_state)`, or two-step → `_run_function` then `_run_reducer`)
   - `finally:` `call_all_lifecycle_hooks_sync("post_run_step", app_id, partition_key, action, state=new_state, result, sequence_id, exception=exc)` (`application.py:993`).

   The `finally` is the key: the persist hook fires **even when the action raises**, so a crashed step still gets a `"failed"` row. `step()` (`application.py:916`) increments `sequence_id` *before* `_step` so replay-from-state doesn't get stuck.

**The seam in one sentence:** in-memory = empty `LifecycleAdapterSet`; durable = the same set plus one `PersisterHook`. The graph, actions, `State`, and the `while self.has_next_action()` loop are byte-identical in both modes. **This is the exact property Verso wants from "one flag."**

### Resume / Fork — `initialize_from()` (KNOWN)

The read side is symmetric. `initialize_from(initializer, resume_at_next_action, default_state, default_entrypoint, fork_from_app_id=…, fork_from_sequence_id=…, override_state_values=…)` (`application.py:2472`) stores a `BaseStateLoader` and resume flags. At `build()`, `_load_from_sync_persister()` (`application.py:2691`) calls `initializer.load(partition_key, app_id, sequence_id)` and `_init_state_from_persister` (`application.py:2635`) decides where to resume:

- `load_result is None` → use `default_state`, `sequence_id = None` (start fresh).
- loaded + `status == "completed"` + `resume_at_next_action` → `state.update(__PRIOR_STEP=last_position)` so the transition engine picks the *next* action after `last_position`.
- loaded + `status == "failed"` → `self.start = last_position; reset_to_entrypoint()` — **re-run the action that crashed** (wipe `__PRIOR_STEP`).
- **Fork:** `fork_from_app_id` set → load from *that* app's rows but write under the *new* `app_id` from `with_identifiers()`. Guard: forking to the same `app_id` raises. `override_state_values` lets you patch loaded state before resuming.

`_identify_state_to_load()` (`application.py:2615`): if forking, read `(fork_from_partition_key, fork_from_app_id, fork_from_sequence_id)`; else read `(partition_key, app_id, sequence_id)` from `with_identifiers()`. **Resume = read your own rows; fork = read someone else's rows, write to yours.**

### BaseStatePersister — Serialization Format (KNOWN)

`BaseStatePersister = BaseStateLoader + BaseStateSaver` (`persistence.py:202`). Async twin: `AsyncBaseStatePersister` (`persistence.py:208`). The save key is a **quadruple** — `(partition_key, app_id, sequence_id, position)` — `position` being the action name. The docstring explicitly says "we're over-engineering this here" by including position alongside the natural `(pk, app, seq)` triple (`persistence.py:138`).

`SQLitePersister` (`persistence.py:312`) is the reference backend. Table DDL (`persistence.py:405`, verbatim):
```sql
CREATE TABLE IF NOT EXISTS burr_state (
    partition_key TEXT DEFAULT '',
    app_id        TEXT    NOT NULL,
    sequence_id   INTEGER NOT NULL,
    position      TEXT    NOT NULL,   -- action name
    status        TEXT    NOT NULL,   -- 'completed' | 'failed'
    state         TEXT    NOT NULL,   -- JSON
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (partition_key, app_id, sequence_id, position)
);
CREATE INDEX burr_state_created_at_index ON burr_state (created_at);
```
- **Append-only, never UPDATE.** `save()` is a bare `INSERT` (`persistence.py:576`). Every step writes a new row; full history is the row set ordered by `sequence_id`. Time-travel = `load(pk, app, sequence_id=N)`.
- **State column** = `json.dumps(state.serialize(**serde_kwargs))`. `State.serialize` (`state.py:325`) walks every key; keys in `FIELD_SERIALIZATION` use a custom serde pair, everything else goes through `burr.core.serde.serialize` (pluggable by type). So the on-disk format is **flat JSON of the state dict**, with per-field serde overrides — not a pickle, not a delta log. (Burr *has* a `StateDelta` abstraction at `state.py:71` for in-memory transactions — `SetFields`/`AppendFields`/`IncrementFields` — but the persisted artifact is the materialized state, not the deltas.)
- **`load()` query modes** (`persistence.py:470`): `app_id=None` → latest row across all apps in the partition (`ORDER BY created_at DESC LIMIT 1`); `sequence_id=None` → latest for that app (`ORDER BY sequence_id DESC LIMIT 1`); both set → exact `(pk, app, seq)` row.
- **Lifecycle:** `is_initialized()` checks `sqlite_master` for the table; uninitialized table → a templated `RuntimeError` telling you to call `.initialize()`. `__getstate__`/`__setstate__` drop and re-open the sqlite connection so the persister is picklable across processes (`persistence.py:601`).
- Built-in backends mirror this schema: `b_aiosqlite`, `b_asyncpg`, `b_psycopg2`, `postgresql`, `b_redis`, `b_mongodb`, `b_pymongo` (all under `burr/integrations/persisters/`). `InMemoryPersister` (`persistence.py:612`) uses `defaultdict(lambda: defaultdict(list))` keyed `[partition_key][app_id] → list[PersistedStateData]`.

### halt_before / halt_after — The HITL Pause Protocol (KNOWN)

Burr's human-in-the-loop is **not** interrupts/exceptions (unlike LangGraph's `interrupt()` — see `fw-langchain-langgraph.md`). It is a **clean generator return**. `run(halt_before=[...], halt_after=[...], inputs=...)` (`application.py:1335`) delegates to `iterate()`, a generator (`application.py:1259`):
```python
while self.has_next_action():
    prior_action, result, state = self.step(inputs=inputs)
    yield prior_action, result, state
    if self._should_halt_iterate(halt_before, halt_after, prior_action):
        break
return self._return_value_iterate(halt_before, halt_after, prior_action, result)
```
`_should_halt_iterate` (`application.py:1213`):
```python
if self.has_next_action() and self.get_next_action().name in halt_before:  return True
elif prior_action.name in halt_after:                                       return True
return False
```
**Semantics (KNOWN, docstring `application.py:1276`):** *one step always runs before any halt is tested*; `halt_before` takes precedence over `halt_after`. The return tuple is the protocol that surfaces the pause to the caller:
- halt_before fired → `(next_action, None, state)` — note `result=None` because the next action has **not** run yet.
- halt_after fired → `(prior_action, result, state)` — the action that just ran, its result, and the new state.

The caller inspects the returned action name, collects human input, then calls `run(...)` **again** with `inputs={...}` for the action it stopped before. Because state was persisted by the post-step hook on the *last completed* step, the pause survives a process restart for free — **the HITL pause and the durability seam are the same mechanism**: persist on every step, resume from the last row. Tags work too: `halt_before=["@tag:needs_approval"]` expands via `graph.get_actions_by_tag` (`application.py:1186`). Async path: `aiterate`/`arun` are identical but can't `return` a value from an async generator, so `arun` re-derives it via `_return_value_iterate` (`application.py:1388`).

### @action Contract — reads / writes Typed State (KNOWN)

`@action(reads=[...], writes=[...], tags=[...])` (`action.py:1438`) wraps a function `(state, **inputs) → (result_dict, new_state)` into a `FunctionBasedAction` (a `SingleStepAction`). The decorator attaches the action object to the function via `setattr(fn, "action_function", FunctionBasedAction(fn, reads, writes, tags))` (`action.py:1493`) — the function stays callable; the action rides along as an attribute.

- **`reads`** are validated against the function's actual State access at decoration time. `_validate_declared_reads(fn, declared_reads)` (`action.py:55`) inspects the source for `state["x"]`/`state.get("x")` and raises if you read a key not in `reads`. This is a **static contract check**, not runtime — the framework refuses to build a graph where an action reads an undeclared key.
- **`writes`** declare which state keys the action may mutate. The transition engine uses reads/writes to validate the graph is well-formed (every read key is written by some upstream action or is in initial state).
- **Inputs** = function params not satisfiable from state; derived via `derive_inputs_from_fn` (`action.py:828`). Params with defaults → optional inputs; without → required inputs (these are what `inputs={...}` in `run()` feeds, and what HITL collects).
- **Typed state:** `@action.pydantic(reads, writes, state_input_type=MyModel, state_output_type=MyModel)` (`action.py:1440`) routes through `burr.integrations.pydantic.pydantic_action`, validating that every read/write key exists as a field on the Pydantic model. The application's `TypingSystem` (`typing.py:35`) is `DictBasedTypingSystem` by default or `PydanticTypingSystem` (the typed-state example app imports `from burr.integrations.pydantic import PydanticTypingSystem` and decorates each node with `@action.pydantic`), so `state.data` can be projected as a typed Pydantic model. State itself (`state.py:273`) is an **immutable `Mapping`** — `update`/`append`/`extend`/`increment`/`wipe`/`subset`/`merge` all return a *new* `State` via `apply_operation(StateDelta)`. Actions never mutate in place; they return a derived state, which is what makes the persisted-state-per-step model sound. The state delta classes (`SetFields`/`AppendFields`/`ExtendFields`/`IncrementFields`, `state.py`) each carry `reads()`/`writes()` and a `validate()` — the same reads/writes contract enforced at the operation level, so `increment` on a non-int or `append` on a non-list raises at apply time.

### Lifecycle Hook Dispatch — the Generalized Seam (KNOWN)

The persister is one instance of a broader pattern Verso should understand: Burr's entire extensibility surface is a **typed lifecycle-hook taxonomy** dispatched by MRO. `burr/lifecycle/base.py` defines paired sync/async ABCs for each stage: `PreRunStepHook`/`PostRunStepHook`, `PostApplicationCreateHook`, `PreStartSpanHook`/`PostEndSpanHook` (tracing), `DoLogAttributeHook` (logging), `PreStartStreamHook`/`PostStreamItemHook`/`PostEndStreamHook` (streaming), `PreApplicationExecuteCallHook`/`PostApplicationExecuteCallHook`. Each ABC defines exactly one method name; subclasses are detected by having it.

`LifecycleAdapterSet` (`lifecycle/internal.py:109`) is the dispatcher. On construction (`:132` `_get_lifecycle_hooks`), it walks `inspect.getmro(adapter.__class__)` for every adapter and indexes which hook-method names each implements into `sync_hooks: dict[hook_name → list[adapter]]` and `async_hooks` (an adapter implementing both sync+async variants lands in both). `call_all_lifecycle_hooks_sync(hook_name, **kwargs)` (`:174`) checks the name is a registered hook (`_does_hook` raises on a typo'd hook name — `REGISTERED_SYNC_HOOKS` is populated at import by a metaclass), then `for adapter in self.sync_hooks[hook_name]: getattr(adapter, hook_name)(**kwargs)`. Async dispatch (`:185`) `asyncio.gather`s all async adapters for the hook; `call_all_lifecycle_hooks_sync_and_async` (`:200`) runs sync first, then awaits async. **So `PersisterHook` is just a `PostRunStepHook` adapter; a tracker is a `PreRunStepHook`+`PostRunStepHook`+span adapter; a tracing exporter is a span-hook adapter — all the same mechanism.** Verso's takeaway: a single typed-hook taxonomy + an MRO-indexed dispatcher gives you persistence, tracing, logging, and streaming observability from one extension point, and adding a new cross-cutting concern is "implement one ABC, append to the set."

### Parallelism — Sub-Application Spawning with Persister Cascade (KNOWN)

Burr's fan-out (`core/parallelism.py`) is where the durability seam recurses. `MapStates`/`MapActions`/`MapActionsAndStates` subclass `TaskBasedParallelAction` (`:186`): a parent action yields N `SubGraphTask`s (`tasks()`, `:329`), each of which is a **full child `Application`** built from a `RunnableGraph` (`:53`). Each child is built with `.with_spawning_parent(app_id, sequence_id, partition_key)` (`:110`) — establishing the parent→child lineage in the same persistence tables (distinct from forking; cross-ref the `with_spawning_parent` builder at `application.py:2544`). The persister **cascades**: `SubGraphTask` carries an optional `state_persister`, and `MapActionsAndStates.tasks` (`:478`) resolves it — if the parent's `state_persister()` behavior is `"cascade"` and the parent persister *is* the parent initializer, the child reuses it; otherwise `_cascade_adapter(self.state_persister(), context.state_persister)` wraps both so the child writes to the parent's store under its own spawned `app_id` (`:495-514`). `reduce(state, states: Generator[State])` (`:342`) merges the child final states back into the parent state. **So a parallel branch is a durably-persisted child run, and resume works at the sub-application granularity** — a crashed fan-out resumes only the incomplete children. This is the multi-agent durability story Verso wants: a sub-agent is a child application sharing the parent's persister with its own lineage row.

### For Verso

- **Adopt the seam mechanism wholesale.** The single most important finding: Burr's durable↔tactical seam is *a post-step lifecycle hook*, not loop surgery. `with_state_persister()` only sets a field; `build()` wraps it in a `PersisterHook` and appends to an adapter set; the ReAct loop calls `call_all_lifecycle_hooks("post_run_step")` in a `finally` with zero persistence awareness. Verso's "one flag" should compile to exactly this: in-memory = no hook, durable = append-a-hook. The loop must never branch on `if persistent`.
- **Persist in `finally`, with a `completed`/`failed` status and the pre/post state distinction.** Burr writes a `"failed"` row carrying the pre-action state so resume re-runs the crashed action; a `"completed"` row carries post-action state so resume advances. Verso's event-sourced mode should encode the same success/failure semantics so replay is deterministic.
- **HITL = generator return, not exception.** `halt_before`/`halt_after` surface as `(action, result, state)` tuples from a generator that breaks the loop. This is cleaner than LangGraph's `interrupt()`/`Command(resume=...)` (cross-ref `fw-langchain-langgraph.md`) because the pause and the durability use one mechanism (persist-per-step). Verso should make its HITL pause a first-class return value of the run loop, and make "the action I stopped before" the thing the caller re-invokes with collected inputs. Note the `result=None` on halt_before vs `result=present` on halt_after — Verso's pause envelope must carry whether the boundary action has run.
- **The save key quadruple `(partition_key, app_id, sequence_id, position)` + append-only INSERT** is the minimal event-sourcing schema. `partition_key` = tenant/user; `app_id` = run; `sequence_id` = step counter; `position` = action name; full history = the rows. Time-travel/fork = read row `N`, write under a new `app_id`. Verso's durable backend should use this exact key shape — it's enough for resume, fork, audit, and replay with no extra tables.
- **Static reads/writes validation is a cheap correctness win.** Burr refuses to build a graph where an action reads an undeclared key. Verso's `@tool`/typed-IO contract could do the same: declare the state keys a tool touches and reject at registration time, not at runtime. This is the typed analog of Verso's context-scoping goal.
- **Immutable State + delta operations.** State is a `Mapping` where every mutation returns a new object. This is what makes "persist the state after every step" sound (no aliasing bugs). Verso's context object should be immutable-by-default with explicit `update`/`append`/`increment` ops.

---

## Marvin 3.0 (PrefectHQ/marvin)

### What It Is

Task-centric agent library. Marvin 3.0 fused the ControlFlow orchestration engine into Marvin's ergonomic top-level functions (`cast`, `classify`, `extract`, `generate`, `summarize`, `run`, `say`, `plan`). The agent loop is delegated to **Pydantic AI** — Marvin owns the *task / thread / orchestrator* layer; Pydantic AI owns the model call. The two primitives Verso cares about: **`Thread`** (DB-backed, ContextVar-scoped conversation memory) and **`Task[T]`** (an objective with a typed result, where the type becomes a structured-output tool). The unifying trick — and the strongest finding in this section — is that **the task result is not the LLM's text output; it is the argument to a dynamically-typed `EndTurn` tool the LLM must call to finish.**

### Thread — History Store/Retrieve (KNOWN)

`Thread` (`thread.py:107`) is a `@dataclass` with `id` (uuid str), `parent_id`, and a private `_db_thread: bool`. It is **both an object and a context manager**:
- **As context manager** (`__enter__`/`__exit__`, `thread.py:410`): sets a module-level `ContextVar _current_thread` via `token = _current_thread.set(self)`, pushes the token onto `self._tokens`, and on exit pops/resets and stashes `_last_thread = self`. This is how `get_current_thread()` works anywhere in the call stack with no plumbing — the orchestrator does `with self.thread:` (`orchestrator.py:254`) and every nested call resolves the active thread off the ContextVar. **This is exactly Verso's "context scoping" concern, implemented with `contextvars`, not parameter passing.**
- **As store:** history is **not** in memory — it's SQLAlchemy async. `add_messages_async` (`thread.py:167`) lazily ensures the thread row exists (`_ensure_thread_exists`, which calls `ensure_db_tables_exist()` on first touch), then `session.add_all([DBMessage.from_message(thread_id, m) for m in messages])` + `commit()`. Retrieval `get_messages_async` (`thread.py:258`) is `SELECT … WHERE thread_id=? ORDER BY created_at DESC [LIMIT n]`, reversed to chronological, with an `include_system_messages=False` filter that strips `system-prompt` parts. So a `limit=n` fetch returns the **most recent n** messages, which is the cheap recency window.

**Schema (KNOWN `database.py`):**
- `threads` (`database.py:143`): `id PK`, `parent_thread_id FK→threads.id` (self-referential — threads form a tree), `created_at`. Relationships to `messages` and `llm_calls`.
- `messages` (`database.py:198`): `id uuid PK`, `thread_id FK`, `message JSON` (the full Pydantic AI message blob — system/user/assistant/tool parts), `created_at`.
- `llm_calls` (`database.py:270`): `id uuid PK`, `thread_id FK`, `usage` (custom `UsageType` column — token counts), `timestamp`. One row per model invocation.
- `llm_call_messages` (`database.py:181`): the **join table** between an LLM call and its messages, with `in_initial_prompt: bool` (was this message part of the prompt vs. generated in the completion) and `order: int`. This is what lets Marvin reconstruct "exactly which messages went into call X and which came out" (`thread.py:get_messages_async` on `LLMCall`, splitting on `in_initial_prompt`). **Verso, take note: separating "the message store" from "which messages were in prompt N" is what makes per-call cost/usage attribution and context-replay possible.** Usage rolls up via `get_usage_async` (`thread.py:370`) summing `llm_call.usage` across calls.

### Task Result-Typing → LLM Output Schema (KNOWN)

`Task[T]` is `Generic[T]` (`task.py:76`) with `result_type: ResultType[T] = str` by default (`task.py:279`). The path from a Python annotation to the LLM's enforced output schema:

1. **`result_type` normalization** (`task.py:_validate_result_type`, `:337`): `result_type=["red","blue"]` → `Labels(["red","blue"])` (a classifier — the LLM returns an *integer index*, not the string); `result_type=[["a","b"]]` → `Labels(many=True)` (multi-label). Plain types (`str`, `int`, `MyPydanticModel`, `list[Foo]`) pass through.
2. **`get_result_type()`** (`task.py:411`): for classifiers returns `int`/`list[int]`; else the raw type.
3. **`get_result_type_str()`** (`task.py:420`): for the prompt, classifiers render "Provide the integer indices … {indexed labels}"; structured types render `json.dumps(TypeAdapter(type).json_schema())` — **the JSON Schema is injected into the prompt** so the LLM sees the target shape.
4. **`validate_result(raw)`** (`task.py:435`): custom `result_validator` first if present; classifier → `Labels.validate`; else `TypeAdapter(result_type).validate_python(raw)`. `TypeAdapter`s are cached in a module dict `_type_adapters` (`task.py:53`). Optional handling: `None` allowed only if `NoneType` is in the type's `get_args`.

**The result type becomes a tool, not a parse.** This is the mechanism (KNOWN, `end_turn.py:36`): `task.get_successful_tool()` calls `create_mark_task_successful(task)`, which **dynamically builds a dataclass** subclass of `EndTurn`:
```python
def create_mark_task_successful(mark_task):
    @dataclass(kw_only=True)
    class _MarkTaskSuccessful(MarkTaskSuccessful):
        result: mark_task.get_result_type()        # ← the task's T, injected as a field type
        task: ClassVar = field(default=mark_task, init=False)
        name: ClassVar[str] = f"Mark {mark_task.friendly_name()} successful"
        def __post_init__(self): mark_task.validate_result(self.result)   # validate on construction
        async def run(self, thread, actor): await mark_task.mark_successful(self.result, thread=thread)
    _MarkTaskSuccessful.__name__ = f"MarkTaskSuccessful_{mark_task.id}"
    return _MarkTaskSuccessful
```
So `MarkTaskSuccessful_<id>.result` is typed as the task's `T`. `Task.get_end_turn_tools()` (`task.py:517`) assembles the available terminators: always `create_mark_task_successful`; `+create_mark_task_failed` if `allow_fail`; `+create_mark_task_skipped` if `allow_skip`; `+create_plan_subtasks` if the task can spawn subtasks.

### The Agent Loop & EndTurn-as-Output-Type (KNOWN)

`Agent.get_agentlet()` (`agent.py:139`) constructs a fresh `pydantic_ai.Agent` per turn ("agentlet"). It splits all candidate items into plain tool callables vs. `EndTurn` subclasses (`agent.py:157`). The terminators become the agentlet's **`output_type`**:
- exactly one EndTurn def → `ToolOutput(type_=that_def, name=def.__name__, …)` (`agent.py:177`).
- zero or many → `output_type = type(None)` with a logged warning that "multi-EndTurn validation is limited" (`agent.py:186`) — an acknowledged sharp edge.

Then `pydantic_ai.Agent(model=…, model_settings=…, output_type=final_tool_output, tools=combined_tools, toolsets=mcp_servers)`. So the agent finishes a turn **only by calling the `MarkTask…` tool with a `result` that matches `T`** — Pydantic AI enforces the schema and Marvin's `__post_init__` re-validates. There is no "parse the final text into T"; the type IS the terminal tool's argument.

**Orchestrator loop** (`orchestrator.py:240`, `Orchestrator.run`):
```
with self.thread:                              # bind thread to ContextVar
  async with manage_mcp_servers(actor):
    while incomplete_tasks and turns < max_turns:   # max_turns default = settings.max_agent_turns, else math.inf
        result = await self.run_once(actor, active_mcp_servers)
        turns += 1
        if raise_on_failure: <raise if any task is_failed>
        incomplete_tasks = {t for t in self.tasks if t.is_incomplete()}
    if turns >= max_turns: raise ValueError("Max agent turns reached")
```
`run_once` (`orchestrator.py:136`): pick `ready` tasks → choose `actor` (default `tasks[0].get_actor()`) → gather only tasks assigned to that actor → assemble `tools` and `end_turn_tools` (the typed terminators) → `_check_memories` → `_get_messages` → build agentlet → `async with agentlet.iter(user_prompt, message_history=…) as run:` stream events → persist `new_messages[1:]` to the thread → `DBLLMCall.create(usage=run.usage(), prompt_messages, completion_messages)` → `end_turn(result, actor)` which, if `result.output` is an `EndTurn`, calls `result.output.run(thread, actor)` (i.e. actually marks the task successful/failed/skipped). Termination is **per-task completion**, not loop-count.

### Multi-Agent Moderation (KNOWN)

A `Team` (`team.py:21`) is an `Actor` holding `members` + a single `active_member`. It does **not** moderate by a separate LLM — moderation is **delegation via an EndTurn tool**. `Team.get_end_turn_tools()` (`team.py:102`) appends `create_delegate_to_actor(delegate)` terminators for every actor the active member may delegate to (read from `self.delegates`). When the agent calls `DelegateToActor`, its `run()` sets `team.active_member = delegate_actor` (`end_turn.py:147`) — the next turn runs the new active member. Subclasses pick the next member differently: `RoundRobinTeam.start_turn` advances `(index+1) % len` (`team.py:132`); `RandomTeam` picks `random.choice` (`team.py:142`); `Swarm` auto-wires every member to delegate to every other (`team.py:119`). **Note `Team` is deprecated as of Sep-2025 with an explicit warning that "team functionality is incomplete" (`team.py:46`)** — the maintainers' own verdict is that hand-rolled coordination of individual Agents beats the Team abstraction. `[CORRECTION 2026-06-05]` Marvin's multi-agent story is *delegation-via-tool-call* (handoff lineage, cf. OpenAI Swarm in py-frameworks "Already Covered"), not LLM-moderator selection — earlier framing of Marvin as "round-robin/moderation" overstates it; round-robin exists but moderation does not.

### High-Level Functions Are Sugar Over Task (KNOWN)

`cast(data, target)` → `Task(result_type=target, …).run()` (`fns/cast.py:95`); `extract(data, target)` → `Task(result_type=list[target], …)` (`fns/extract.py:80`). Every ergonomic function is a one-task orchestrator run. The typed-output contract is the whole library.

### Memory Module — Vector Recall, Separate from Thread (KNOWN)

`Memory` (`memory/memory.py:41`) is a `@dataclass` distinct from `Thread`: Thread is the linear conversation log; Memory is a **partitioned vector collection** for semantic recall. Fields: `key` (the partition, validated to `[a-zA-Z0-9_]` via `sanitize_memory_key`, `:74`), `instructions` (what this memory is for), `provider: MemoryProvider`, `auto_use: bool` (default `False`), `prompt` (jinja template). The `MemoryProvider` ABC (`:23`) is the swappable backend: `configure(memory_key)`, `add(key, content) → id`, `delete(key, id)`, `search(key, query, n=20) → dict[id→content]`. Concrete providers live in `memory/providers/`: `chroma`, `qdrant`, `lance`, `postgres` — each implements the 4 methods over its vector store. `__post_init__` resolves a string provider name via `get_memory_provider` and calls `provider.configure(self.key)` so the collection exists.

**`auto_use` is the recall trigger.** In the orchestrator's `_check_memories` (`orchestrator.py:316`), for every assigned task's memories (and the agent's) where `m.auto_use` is True, it builds a query from `thread.get_messages_async(limit=3)` (dumped to JSON), then `await memory.search(query=query, n=3)` and injects `{memory.friendly_name(): results}` as an **info-message** (`add_info_message_async(..., prefix="Automatically recalled memories")`). So auto-use memory = "before each turn, semantic-search the last 3 messages against the vector collection and prepend the top-3 hits as a user/info message." Non-auto memories become **tools** the agent can call deliberately (`memory.get_tools()` is folded into the task's tool set, `task.py:399`). **Two recall modes from one abstraction: ambient (auto_use, query=recent messages) and on-demand (tool call).**

### Streaming & EndTurn Detection (KNOWN)

`handle_agentlet_events` (`engine/streaming.py:44`) wraps Pydantic AI's `agentlet.iter(...)` node stream and translates each Pydantic AI event into a Marvin event. It builds `end_turn_tools_map = {tool.name: tool for tool in agentlet._marvin_end_turn_tools}` (`:89`) — the dynamically-named `MarkTaskSuccessful_<id>` terminators. As it streams `PartStartEvent`/`ToolCallPartDelta`/`FinalResultEvent`, it checks `part.tool_name in end_turn_tools_map` (`:107`) to distinguish a **terminal** tool call (one of the `MarkTask…`/`Delegate…` EndTurns) from an **ordinary** tool call — terminal calls emit `EndTurnToolCallEvent`, ordinary ones `ToolCallEvent`/`ToolCallDeltaEvent` (`:222`). The `output_type=ToolOutput(EndTurn subclass)` set in `get_agentlet` is what makes Pydantic AI surface the terminator as the run's `FinalResult`. So the streaming layer's job is purely **classification of tool calls into terminal vs. continuing**, which is exactly the information a UI needs to show "task done" vs. "agent is working." A streaming consumer can render partial structured output as the `MarkTaskSuccessful.result` field fills in.

### For Verso

- **Typed result as terminal-tool argument, not output parse.** This is the headline Marvin pattern for Verso. Instead of "run the LLM, then `TypeAdapter.validate(text)`", Marvin makes the *only* way to finish a task be calling `MarkTaskSuccessful(result: T)`, with the schema enforced by the provider and re-validated in `__post_init__`. Verso's `@tool` typed-IO contract should consider the same inversion: the agent terminates by emitting a typed object, and "done" is "a valid terminal object was produced", not "the loop hit max_iters". This makes the result type and the stop condition the same thing.
- **Dynamic dataclass per task is how you get a per-task output schema.** `create_mark_task_successful` builds a fresh `EndTurn` dataclass with `result: task.get_result_type()` and a unique `__name__`. Verso can use the same `type(...)`/dataclass-factory trick to give each task/agent its own structured terminator without a giant Union — and the `Union[all terminators]` fallback (`agent.py:137`) shows the failure mode to avoid (Marvin itself degrades to `type(None)` when there are several, losing validation).
- **ContextVar-scoped Thread is the right model for "ambient" context.** `with thread:` sets a ContextVar so any depth of nested call resolves the active conversation with zero parameter threading, and the token stack makes nesting safe. Verso's typed-context-scoping should use `contextvars` for the ambient current-run/current-thread, reserving explicit parameters for data the function genuinely transforms. (Cross-ref: Burr threads everything explicitly through `State`; Marvin makes the conversation ambient. Verso can offer both — explicit typed state for the data, ambient ContextVar for the run handle.)
- **Separate "message store" from "which messages were in call N."** The `llm_call_messages` join with `in_initial_prompt` + `order` is the schema that makes per-call usage attribution, cost tracking, and exact context replay possible. Verso's durable layer should record, per LLM call, the ordered set of prompt messages and completion messages — not just append everything to one log. This is the eval/observability substrate Verso wants and that most frameworks lack (cf. py-frameworks Note 4: "evals are an unsolved gap").
- **Recency window = `ORDER BY created_at DESC LIMIT n` reversed.** Marvin's context assembly is deliberately dumb: most-recent-n messages, system messages strippable. For semantic recall it bolts on a separate `Memory` (vector search over a query built from the last 3 messages, `orchestrator.py:325`) injected as an info-message. Verso should keep the same split: cheap recency window by default, opt-in vector recall as a tool/auto-use memory — do not conflate the two.
- **Delegation-via-tool beats moderator-LLM (and the maintainers agree).** Marvin deprecated `Team`. The surviving pattern is individual agents that hand off by calling a `DelegateToActor` terminator. Verso's multi-agent story should be handoff-as-tool-call (typed, traceable, in the same loop) rather than a separate orchestration LLM — matching OpenAI Swarm's handoff-via-return (Already Covered) and avoiding the "incomplete team" trap.

---

## PocketFlow (The-Pocket/PocketFlow)

### What It Is

A **100-line, zero-dependency** orchestration graph (the entire framework is `pocketflow/__init__.py`, lines 1–100, `import asyncio, warnings, copy, time` only). No LLM calls, no tools, no memory, no prompts — it is the irreducible skeleton of "nodes connected by labeled edges, run in a loop, sharing a dict." It is the floor against which Verso should be able to state exactly what it adds. Paper: arxiv 2504.03771 ("Agentic Coding"). The pitch: every agent framework is this graph plus integrations; ship the graph, write the integrations yourself.

### The Core, Read Line by Line (KNOWN — full source)

**`BaseNode` (`:3-20`) — the node lifecycle + edge DSL.**
- `__init__`: `self.params, self.successors = {}, {}` — params (set by the flow), successors (a `dict[action_str → node]`).
- **Three-phase lifecycle** (the whole node contract): `prep(shared)` → `exec(prep_res)` → `post(shared, prep_res, exec_res)`. `_run(shared)` (`:13`) chains them: `p = prep(shared); e = _exec(p); return post(shared, p, e)`. `prep` reads from `shared` and returns what `exec` needs; `exec` does the work (the LLM call, in user code) and is **forbidden from touching `shared`** (so it's retry-safe); `post` writes results back to `shared` and **returns an action string** that selects the next edge. This prep/exec/post split is the load-bearing design decision: it separates I/O-against-shared-state from the retryable compute.
- **Edge DSL via operator overloading:** `node_a >> node_b` (`__rshift__`, `:17`) = `node_a.next(node_b)` = register `node_b` under action `"default"`. `node_a - "approved" >> node_b` uses `__sub__` (`:18`) to return a `_ConditionalTransition(node_a, "approved")` whose own `>>` (`:24`) wires `node_b` under action `"approved"`. So **action-labeled edges are just dict keys**: `post` returns `"approved"`, the flow looks up `successors["approved"]`.
- `run(shared)` (`:14`) warns if the node has successors ("Use Flow.") and runs the single node — bare-node convenience only.

**`Node(BaseNode)` (`:26-34`) — adds retry.** `__init__(max_retries=1, wait=0)`. `_exec` (`:29`) loops `for self.cur_retry in range(max_retries)`: try `exec`; on exception, if last attempt call `exec_fallback(prep_res, exc)` (default re-raises), else `time.sleep(wait)` and retry. `cur_retry` is an attribute so user `exec` can branch on attempt number. **This is the only error handling in the framework** — no circuit breaker, no per-edge error routing.

**`BatchNode(Node)` (`:36-37`):** `_exec(items)` runs the parent `_exec` over each item — fan-out a node over a list, sequentially.

**`Flow(BaseNode)` (`:39-51`) — the orchestrator loop, and it IS a node.** `Flow` subclasses `BaseNode`, so a flow nests inside another flow as a node ("Flow as Node" — the entire multi-agent composition model). The loop `_orch` (`:46-49`):
```python
def _orch(self, shared, params=None):
    curr, p, last_action = copy.copy(self.start_node), (params or {**self.params}), None
    while curr:
        curr.set_params(p)
        last_action = curr._run(shared)
        curr = copy.copy(self.get_next_node(curr, last_action))
    return last_action
```
- `get_next_node(curr, action)` (`:42`): `curr.successors.get(action or "default")`; if no match but successors exist, warn "Flow ends" — **a missing edge silently terminates the flow** (this is how you stop: return an action with no successor).
- **`copy.copy` of each node before running** (`:47-48`): nodes are shallow-copied so a node reused in multiple flow positions doesn't share mutated `params`/`cur_retry` state. The graph definition is a template; execution copies it. (Verso note: this is a cheap immutability hack, not true isolation — a shallow copy shares nested mutable objects.)
- The loop runs **until `curr` is falsy** — no max-iteration cap, no termination guard beyond "edge not found." An infinite loop is the user's problem.
- `Flow._run` (`:50`): `prep → _orch → post`; `Flow.post` (`:51`) returns `exec_res` (the last action) so a nested flow's terminal action propagates to the parent flow's edge lookup.

**`AsyncNode(Node)` (`:59-74`):** parallel async lifecycle `prep_async`/`exec_async`/`exec_fallback_async`/`post_async`; `_exec` (`:64`) is the retry loop with `await asyncio.sleep(wait)`; `_run_async` (`:73`) chains the async trio. `_run` (`:74`) **raises** `RuntimeError("Use run_async.")` — sync entry into an async node is a hard error.

**`AsyncFlow(Flow, AsyncNode)` (`:82-88`):** `_orch_async` (`:83`) is the same loop but per node: `await curr._run_async(shared) if isinstance(curr, AsyncNode) else curr._run(shared)` — **a single flow can mix sync and async nodes**, dispatching on type at each step.

**Batch variants:** `BatchFlow` (`:53`) runs `_orch` once per param-dict from `prep` (sequential sub-flows); `AsyncParallelBatchNode` (`:79`) and `AsyncParallelBatchFlow` (`:96`) use `asyncio.gather(*...)` to run items/sub-flows concurrently. That's the entire parallelism story: `gather` over a prep-returned list.

### What It Deliberately Does NOT Do (KNOWN — by absence)

The negative space is the lesson. PocketFlow has **no**: LLM client, tool registry, system prompts, structured output, memory/persistence (the `shared` dict is in-memory and ephemeral — vanishes when the process ends), checkpointing, observability/tracing, eval, typed state (`shared` is `dict`, `params` is `dict`, both untyped), or termination guard (no max-iters). It does not even import an HTTP library. Everything an agent needs is user code inside `exec`. The framework's entire value is: **lifecycle (prep/exec/post) + labeled-edge routing + nesting + retry, in 100 lines.**

### For Verso

- **This is the minimum-viable-loop floor; Verso must say exactly what it adds.** PocketFlow proves the irreducible core is ~100 lines: a node with prep/exec/post, a dict of action→node successors, a `while curr:` loop that runs `post`'s returned action through `get_next_node`. Verso's "clean async ReAct loop as default" should be diffable against this. Everything Verso adds beyond it — typed state (vs `shared: dict`), `@tool` contract, durability seam, context engineering, evals — is a deliberate, named addition, not accidental complexity.
- **prep/exec/post is a genuinely good idea worth stealing or consciously rejecting.** The split makes `exec` (the retryable LLM/tool call) pure w.r.t. shared state — retries can't double-write. Verso's tool execution could enforce the same discipline: a read-phase (gather inputs from typed context), a compute-phase (the side-effecting call, retryable), a commit-phase (write results back, runs once). This is the node-level analog of Burr's per-step persistence boundary.
- **Action-labeled edges = `dict[str, node]` + a returned string.** Conditional branching needs no DSL engine: `post` returns `"approved"`/`"rejected"`, the loop does `successors.get(action)`. Verso's "pluggable edges" can be this cheap. The operator overloading (`>>`, `- "action" >>`) is sugar — the substance is the dict.
- **Termination by missing-edge is too implicit; Verso should make stop explicit.** PocketFlow stops when `get_next_node` returns `None` and silently warns. With no max-iteration cap, a cyclic graph loops forever. Verso must keep an explicit termination contract (max-iters + an explicit `Done`/halt action, cf. Burr's `halt_after` and Marvin's per-task completion) — this is a concrete place Verso diverges from the floor.
- **`copy.copy` per step is a warning, not a pattern.** PocketFlow shallow-copies each node before running to avoid shared mutable `params`. It's a leaky hack (nested objects still alias). Verso's answer is immutable typed state passed forward (Burr's model) rather than copying mutable node objects — cleaner and actually isolated.
- **Flow-as-Node nesting is the simplest multi-agent composition.** Because `Flow` is a `BaseNode`, a sub-agent (its own flow) drops into a parent graph as one node, its terminal action becoming the parent's edge label. Verso can offer the same: a sub-agent is just a tool/node whose output selects the next edge. No special multi-agent runtime needed for the simple case.

---

## Atomic Agents (BrainBlend-AI/atomic-agents)

### What It Is

A minimal, statically-typed agent built on **Instructor + Pydantic**. v2.0 renamed `BaseAgent` → `AtomicAgent` and made it a **PEP-695 generic** `AtomicAgent[InputSchema, OutputSchema]`. There is no graph engine, no ReAct loop, no autonomous tool-calling loop — the agent is a **single typed LLM call**: `InputSchema in → OutputSchema out`, both Pydantic models. "Tools" are just other agents you wire by hand. This is the cleanest proof of Verso's "typed I/O at every boundary" with the smallest possible runtime.

### BaseAgent.run — The "Loop" That Isn't (KNOWN)

`AtomicAgent.run(user_input: InputSchema) -> OutputSchema` (`atomic_agent.py:551`) is **one model call, no iteration**:
```python
def run(self, user_input=None) -> OutputSchema:
    assert not isinstance(self.client, AsyncInstructor)   # sync client only
    self._trim_context()                                  # token-budget trim BEFORE adding new input
    if user_input:
        self.history.initialize_turn()                    # new turn_id
        self.current_user_input = user_input
        self.history.add_message("user", user_input)
    self._prepare_messages()                              # [system msg] + history
    response = self.client.chat.completions.create(
        messages=self.messages, model=self.model,
        response_model=self.output_schema,                # ← Instructor enforces OutputSchema
        **self._get_completion_kwargs())
    self.history.add_message(self.assistant_role, response)
    self._prepare_messages()
    return response
```
There is **no `while`** — `run()` does exactly one provider round-trip and returns a validated `OutputSchema`. Multi-step behavior is the caller's job: feed one agent's output into the next agent's input. Four variants share the body: `run` (sync), `run_async` (`:630`), `run_stream` (`:585`, uses `create_partial` + the monkey-patched `model_from_chunks` for partial-validation streaming), `run_async_stream` (`:663`). Async/sync are policed by `assert isinstance(client, AsyncInstructor)` at the top of each — wrong client type is a hard assertion, not a runtime branch.

**Termination is the type, not a counter.** The agent "stops" because Instructor returned a valid `OutputSchema`. If the model's output won't validate, Instructor's own retry (configured on the client) re-prompts with the validation error; that retry loop lives in Instructor, not Atomic Agents. So the only loop in the system is Instructor's structured-output retry. (Cross-ref: Marvin also delegates the loop — to Pydantic AI; Atomic Agents delegates to Instructor. Both own only the typed-IO + context layer.)

### Instructor Wrapping (KNOWN)

The whole LLM call is `self.client.chat.completions.create(..., response_model=self.output_schema)` where `self.client` is an `instructor.Instructor` (or `AsyncInstructor`) passed in via `AgentConfig.client` (`:67`). Atomic Agents does **not** wrap or abstract Instructor — it passes the user's Instructor client straight through. Key config: `mode: Mode = Mode.TOOLS` (`:93`) selects how Instructor coerces structured output (TOOLS = function-calling schema; JSON/MD_JSON = schema in the system prompt). `_get_completion_kwargs` (`:367`) defaults `strict=None` (overriding Instructor's `strict=True`) so the OutputSchema's own Pydantic coercion applies (e.g. enum-from-string). `_build_tools_definition` (`:380`) reproduces Instructor's `generate_openai_schema(output_schema)` for accurate token counting in TOOLS mode. The hook system (`register_hook`, `:740`) forwards Instructor events (`parse:error`, `completion:kwargs`, `completion:response`, `completion:error`, `completion:last_attempt`) to user callbacks, with error-isolated dispatch (`_dispatch_hook`, `:790` — a failing hook logs a warning, never interrupts the run).

### v2 Generics — BaseAgent[In, Out] (KNOWN)

The generic-parameter capture is the most interesting code in the file because modern Python's `__orig_class__` is unreliable. `AtomicAgent[InputSchema: BaseIOSchema, OutputSchema: BaseIOSchema]` (`:105`) uses PEP-695 syntax with `BaseIOSchema` bounds. Resolving the actual types at runtime uses a **three-level fallback** (`input_schema`/`output_schema` properties, `:233`/`:255`):
1. **Subclass path** — `__init_subclass__` (`:165`) fires when you do `class MyAgent(AtomicAgent[Schema1, Schema2])`. It walks `cls.__orig_bases__`, finds the base whose `get_origin` is `AtomicAgent`, and stashes `cls._input_schema_cls, cls._output_schema_cls = get_args(base)`. This works around `__orig_class__` being unset on subclasses.
2. **Direct-instantiation path** — `AtomicAgent[Schema1, Schema2]()` sets `self.__orig_class__`; the property reads `get_args(self.__orig_class__)`.
3. **Untyped path** — falls back to `BasicChatInputSchema`/`BasicChatOutputSchema` (`:45`/`:54`, both single `chat_message: str`).

`self.output_schema` is then passed as Instructor's `response_model` — so **the generic type parameter literally becomes the LLM's enforced output schema.** This is the tightest binding of "Python type → LLM contract" in any framework here: no decorator, no registry, just a generic parameter read via introspection.

### ContextProvider Protocol — Context-by-Injection (KNOWN)

The `ContextProvider` is Atomic Agents' answer to dynamic context, and it's deliberately tiny (`system_prompt_generator.py:5`):
```python
class BaseDynamicContextProvider(ABC):
    def __init__(self, title: str): self.title = title
    @abstractmethod
    def get_info(self) -> str: ...        # the ONE method: return a string to inject
```
Providers live in a **named dict** on the `SystemPromptGenerator` (`context_providers: dict[str, BaseDynamicContextProvider]`). `generate_prompt()` (`:49`) renders fixed sections (`# IDENTITY and PURPOSE` from `background`, `# INTERNAL ASSISTANT STEPS` from `steps`, `# OUTPUT INSTRUCTIONS`), then appends `# EXTRA INFORMATION AND CONTEXT` and, **for each provider, a `## {provider.title}` subsection containing `provider.get_info()`**. Providers compose by dict ordering — multiple providers each contribute one titled markdown block. The agent can mutate them at runtime: `register_context_provider(name, provider)` / `get_context_provider(name)` / `unregister_context_provider(name)` (`:700-737`). So a RAG provider's `get_info()` runs **every time the prompt is built** (each `run()`), pulling fresh retrieved chunks into the system prompt. **This is context engineering as "a set of named string-producers folded into the system prompt at call time" — pull, not push.**

### Context Trimming (KNOWN)

`max_context_tokens` (`:95`) enables turn-preserving trim. `_trim_context` (`:293`) runs **before** adding the new user message, computes `get_context_token_count()` (system + history + tools, via LiteLLM's provider-agnostic counter), and deletes **whole turns oldest-first** (`history.delete_turn_id`) until under budget — never partial turns. If a single turn exceeds the budget it raises. Turns are tracked by `turn_id` set in `initialize_turn()`.

### BaseIOSchema — Docstring-as-LLM-Description (KNOWN)

`BaseIOSchema(BaseModel)` (`base/base_io_schema.py:6`) enforces one rule that turns every schema into self-documenting LLM contract: `__pydantic_init_subclass__` calls `_validate_description()` (`:22`) which **raises `ValueError` if the class has no non-empty docstring** ("{cls.__name__} must have a non-empty docstring to serve as its description"). `model_json_schema` (`:33`) injects that docstring as the schema `description`. So the input/output models the agent uses ALWAYS carry a description into the JSON schema the LLM sees — a missing docstring is a hard build error, not a silent gap. This is a cheap, enforced discipline Verso should copy: the type that crosses the LLM boundary must document its own purpose.

### ChatHistory — Turn-Atomic Message Log (KNOWN)

`ChatHistory` (`context/chat_history.py:31`) is the in-memory log behind the agent. A `Message` (`:16`) carries `role`, `content` (a `BaseIOSchema` or multimodal list), and a `turn_id`. `initialize_turn()` (`:53`) sets `current_turn_id = uuid4()`; `add_message` (`:59`) stamps the message with the current turn id (raising if none initialized). `get_history()` (`:90`) serializes to `[{role, content}]`, handling multimodal via `model_dump_json(exclude=...)` to strip non-serializable media fields. `delete_turn_id(turn_id)` (`:207`) removes all messages in a turn (used by `_trim_context`) and raises if the turn isn't found. `copy()` snapshots for `initial_history` (so `reset_history` restores). **A "turn" = one user input + the assistant response(s)/tool results that followed it**, which is why trimming is turn-atomic — you never strand a tool result without its triggering message.

### MCP Connector — JSON-Schema → Pydantic at Runtime (KNOWN)

`connectors/mcp/schema_transformer.py` shows how Atomic Agents folds MCP tools into its typed world. `SchemaTransformer.create_model_from_schema` (`:148`) uses Pydantic's `create_model` to build a `BaseIOSchema` subclass from an MCP tool's JSON Schema at runtime — `json_to_pydantic_field` (`:67`) maps each JSON-schema property to a typed Pydantic field, `_resolve_ref`/`_create_nested_model` handle `$ref` and nested objects. So an MCP tool becomes a Pydantic input schema just like a native one — **MCP is adapted into the typed-IO contract, not bolted on as an opaque passthrough** (matching py-frameworks Note 3: MCP as opt-in adapter, `@tool` stays primary).

### For Verso

- **Generic type parameter → `response_model` is the purest typed-IO contract.** Atomic Agents binds `AtomicAgent[In, Out]`'s `Out` directly to Instructor's `response_model` via introspection — no decorator, no registry, just `get_args`. For Verso's `@tool` typed contract, this validates that a generic/annotation can BE the schema. But note the cost: the `__init_subclass__` + `__orig_class__` + default three-level fallback (`:165`, `:244`) is ugly plumbing forced by Python's unreliable runtime generics. Verso should decide up front whether tools are typed by generics (this fallback dance) or by explicit `input_model=/output_model=` args (Marvin/Pydantic-AI style) — the explicit arg is less magic and Verso likely wants it.
- **The agent can be a single typed call; the loop is optional.** Atomic Agents proves a useful agent need not have a loop — `run()` is one round-trip, termination is "a valid `OutputSchema` came back." Verso's "clean ReAct loop as default" should still offer a loopless typed-call mode for the common cast/extract/classify case (Marvin agrees — its high-level fns are one-task runs). Don't force a loop where a typed call suffices.
- **ContextProvider = named dict of `get_info()` string-producers, folded in at call time.** This is the simplest possible "first-class context engineering": each provider contributes one titled block to the system prompt, evaluated fresh on every `run()`. Verso's context-engineering layer can adopt exactly this — a registry of named context sources, each a pure `() -> str` (or typed-object) producer, assembled deterministically into the prompt, with register/unregister at runtime. The pull model (provider runs at prompt-build time) is right for RAG: retrieval reflects the latest query/state without manual re-injection.
- **Turn-preserving trim, computed before adding new input.** `_trim_context` deletes whole turns oldest-first and runs before the new user message is added (so the new input is never trimmed). Verso's context-window management should be turn-atomic (never leave a dangling tool-result without its call) and protect the incoming message. Note Atomic Agents trims by deletion (lossy); Verso's context-by-exclusion goal (cf. Griptape below) can do better — move trimmed turns to off-prompt memory rather than dropping them.
- **Delegate the structured-output retry to the library, own only the typed boundary.** Atomic Agents has no validation-retry loop of its own; Instructor re-prompts on `parse:error`. Verso should similarly not reinvent structured-output coercion — wrap a proven structured-output engine (Instructor/Pydantic-AI/Mirascope) and keep Verso's value in the typed context + durability + eval layers.
- **Provider-role auto-detection is a real cross-provider papercut to handle.** `tool_result_role` defaults to `"user"` for Gemini (`assistant_role=="model"`) and `"system"` otherwise (`:196`), because Gemini drops mid-conversation system messages; `_prepare_messages` remaps history system→tool_result_role (`:355`). Verso's message layer must encode "this is a mid-conversation context injection" semantically and let the provider adapter choose the wire role — don't hardcode `"system"`.

---

## Griptape (griptape-ai/griptape)

### What It Is

Modular agent framework with three structure types — `Agent` (single task), `Pipeline` (sequential task chain), `Workflow` (parallel task DAG) — and one mechanism Verso specifically wants: **TaskMemory**, the most developed open-source implementation of **context-engineering-by-exclusion**. When a tool returns a large output, Griptape does NOT put it in the prompt. It stores it in a named, namespaced artifact store and injects only a one-line **reference token** into the conversation; the LLM must then explicitly call a memory-reading tool with that reference to pull the data back. The prompt stays small; the data lives off-prompt until needed.

### TaskMemory — Off-Prompt Storage (KNOWN)

`TaskMemory` (`memory/task/task_memory.py:20`, an `attrs @define`) holds:
- `artifact_storages: dict[type, BaseArtifactStorage]` — type-routed storage, default `{TextArtifact: TextArtifactStorage(), BlobArtifact: BlobArtifactStorage()}` (`:27`). A validator forbids two storages of the same type (`:41`).
- `namespace_storage: dict[str, BaseArtifactStorage]` — maps a **namespace** (the artifact id) to the storage that holds it.
- `namespace_metadata: dict[str, Any]` — per-namespace metadata (the originating subtask's actions JSON).

**The store path** (`process_output`, `:61`) is the heart of the exclusion pattern. After a tool activity runs and returns `output_artifact`:
1. `namespace = output_artifact.name` (a uuid-ish id).
2. `store_artifact(namespace, output_artifact)` (`:99`) — routes by type via `get_storage_for` (`:51`): `TextArtifact` → `TextArtifactStorage` (which **upserts into a vector store**, `text_artifact_storage.py:24`); `BlobArtifact` → `BlobArtifactStorage` (in-memory blob dict). A `ListArtifact` stores each element under the same namespace. On success `store_artifact` returns **`None`** (sentinel: "stored, not passed through").
3. `namespace_metadata[namespace] = subtask.actions_to_json()`.
4. **Render the reference token** from `templates/memory/tool.j2` (verbatim, the entire template):
   ```
   Output of "{{ tool_name }}.{{ activity_name }}" was stored in memory with memory_name "{{ memory_name }}" and artifact_namespace "{{ artifact_namespace }}"
   ```
   e.g. `Output of "WebScraper.get_content" was stored in memory with memory_name "TaskMemory" and artifact_namespace "a1b2c3..."`.
5. Return `InfoArtifact(that_string, name=namespace)` — **this short string is what goes into the prompt**, not the (possibly huge) scraped page. If `get_storage_for` returns `None` (no storage for that type, e.g. a small `InfoArtifact`), `store_artifact` returns the artifact unchanged and it goes inline — **only large/storable artifacts are excluded; small ones pass through.**

So the reference-token format is a **two-part key: `(memory_name, artifact_namespace)`**. That is the entire "pointer" the LLM sees.

### The Synthesized Memory-Access Tool (KNOWN)

The LLM reads back by calling a tool whose schema **requires the `(memory_name, artifact_namespace)` pair**. Example `QueryTool.query` (`tools/query/tool.py:44`), its `@activity` schema (verbatim structure):
```python
@activity(config={"description": "...", "schema": Schema({
    Literal("query", description="A natural language search query"): str,
    Literal("content"): Or(str, Schema({
        "memory_name": str,
        "artifact_namespace": str,    # ← the reference token, fed back in
    })),
})})
def query(self, params):
    content = params["values"]["content"]
    memory = self.find_input_memory(content["memory_name"])   # resolve the named memory
    artifacts = memory.load_artifacts(content["artifact_namespace"])  # pull from storage
    # ... then RAG/query over those artifacts
```
`find_input_memory(memory_name)` (`base_tool.py:223`) resolves the memory object from the tool's `input_memory` list by name; `memory.load_artifacts(namespace)` (`task_memory.py:124`) dispatches to the namespace's storage (vector store `load_artifacts` for text). **The tool is "synthesized" in the sense that any tool gains memory-read capability by declaring `input_memory` and accepting the `content: {memory_name, artifact_namespace}` shape** — the wiring is automatic: `BaseTool.input_memory` / `output_memory` (`base_tool.py:59-60`) are auto-set if `None`, so a tool's outputs route to memory and another tool can read them by reference. The two canonical readers are `QueryTool` (RAG over the stored artifacts using a natural-language query) and `ExtractionTool`. This is the full loop: **Tool A's big output → stored, reference token in prompt → LLM calls Tool B (Query/Extraction) with the reference → Tool B pulls from storage and returns only the relevant slice.** The big payload never enters the context window.

### Storage Backends (KNOWN)

`BaseArtifactStorage` (`base_artifact_storage.py`) is the 3-method interface: `store_artifact`, `load_artifacts`, `can_store`. `TextArtifactStorage` backs onto a `BaseVectorStoreDriver` (default from `Defaults.drivers_config.vector_store_driver`) — text artifacts are embedded and upserted; `load_artifacts(namespace)` does a namespace-scoped vector load. `BlobArtifactStorage` keeps binary blobs in memory. So **text memory is semantically searchable by default** (it's in a vector store), which is why `QueryTool` can RAG over a namespace.

### Pipeline.run() vs Workflow.run() (KNOWN)

Both are `Structure` subclasses; both `add_task` to wire parent/child by id. The difference is the execution model:
- **`Pipeline.try_run`** (`pipeline.py:52`) is strictly **sequential and recursive**: `__run_from_task(self.input_task)` (`:71`) runs a task, then `__run_from_task(next(iter(task.children), None))` — single-child chain, depth-first, stops on `ErrorArtifact` if `fail_fast`. Each task sees `parent_output` = its single parent's output (`context`, `:57`). It's a linked list of tasks.
- **`Workflow.try_run`** (`workflow.py:103`) is a **parallel DAG with a superstep loop**: `while not self.is_finished():` → `order_tasks()` (topological) → for every task where `task.can_run()` (all parents finished), `futures_executor.submit(with_contextvars(task.run))` → `futures.as_completed(...)`. Tasks run concurrently in a thread pool (`FuturesExecutorMixin`); a task sees `parent_outputs` (plural) and `parents_output_text` (`:131`). `input_tasks` = tasks with no parents, `output_tasks` = tasks with no children. So Workflow is a fan-out/fan-in DAG executed wave-by-wave until all tasks finish. **Handoff between tasks = a child reads `task.parent_outputs`** — output of upstream tasks flows into downstream task context, not via memory tokens.

### RuleSets (KNOWN)

`Ruleset` (`rules/ruleset.py`) is a named, serializable bag of `BaseRule`s loaded via a `BaseRulesetDriver` (so rules can come from code, a file, or Griptape Cloud — `__attrs_post_init__` merges driver-loaded rules with inline ones). `Rule.to_text()` (`rules/rule.py`) just returns `self.value` — a plain behavioral instruction string. `JsonSchemaRule` is the structured-output variant. Rules attach to structures/tasks via `RuleMixin` and are rendered into the system prompt. **Rulesets are prompt-injection-of-constraints, named and swappable** — the same task can be re-run under a different ruleset without changing its logic. This is lighter than CrewAI's role/goal/backstory (cross-ref `fw-crewai-letta.md`): a ruleset is just named instruction strings, not an identity model.

### The ReAct Loop That Produces the Reference Tokens (KNOWN)

The memory exclusion happens inside a ReAct loop. `PromptTask` (`tasks/prompt_task.py:46`, an `ActionsSubtaskOriginMixin`) runs up to `max_subtasks = DEFAULT_MAX_STEPS = 20` (`:48,:68`) iterations of `ActionsSubtask`. Each subtask: the LLM emits `Thought` + `Actions` (tool calls) JSON; `ActionsSubtask.run_actions` → `run_action(action)` (`actions_subtask.py:146`) calls `action.tool.run(activity, self, action)`. **`BaseTool.run` invokes the activity, then `after_run` (`base_tool.py:177`) is where exclusion fires:** if the tool has `output_memory` for that activity, it calls `memory.process_output(activity, subtask, value)` (`:189`) — which stores the artifact and **returns the `InfoArtifact` reference token** that replaces the real output. That token is what gets added to the prompt stack for the next subtask (`add_to_prompt_stack`, `actions_subtask.py:200`). The loop continues until the LLM emits a final answer (no more actions) or hits `max_subtasks`. `meta_memory` (`ActionSubtaskMetaEntry` with `thought`/`actions`/`answer`, `task_memory.py:87`) records the reasoning trace per subtask. **So the full exclusion cycle lives inside a bounded ReAct loop: Thought → Action → tool runs → large output stored, token returned → token in next prompt → LLM decides to Query the token or answer.** The prompt stack (`prompt_task.py:126`) is assembled fresh each subtask from system template + rulesets + memory + accumulated subtasks.

### Driver Abstraction (KNOWN)

20 driver categories under `griptape/drivers/` (prompt, embedding, vector, rerank, sql, web_search, web_scraper, image_generation, audio_transcription, text_to_speech, memory, ruleset, structure_run, observability, …). Every external dependency is a swappable Driver resolved from `Defaults.drivers_config` — `TaskMemory`'s `TextArtifactStorage` pulls `vector_store_driver` from defaults; `Ruleset` pulls `ruleset_driver`. **The Driver layer is what makes memory backend, embedding model, and vector store independently pluggable** without touching task/structure code.

### For Verso

- **Adopt TaskMemory's reference-token mechanism for context-by-exclusion — this is the headline Griptape finding.** The pattern: a tool's large output is stored off-prompt under `(memory_name, artifact_namespace)`; only the one-line reference token enters the context window; the LLM must call a reader tool with that pair to pull the data. Verso's context-engineering layer should make this a first-class primitive: tool outputs above a size threshold auto-store and return a typed pointer, not the payload. The exact token shape `(memory_name, artifact_namespace)` is a good template — a namespace per output, a named memory per store. This is the concrete answer to "what goes in the context window vs. what stays in memory" that py-frameworks Note 5 flags as underdeveloped everywhere else.
- **Store text in a vector store so the reader can RAG, not just fetch.** Griptape's `TextArtifactStorage` upserts into a vector store, so `QueryTool` reads back with a *natural-language query* over the namespace, returning only relevant chunks — not the whole blob. Verso should do the same: off-prompt text memory is embedded, and the reader tool takes `(pointer, query)` and returns the relevant slice. This means exclusion doesn't just defer the cost, it *reduces* it — the LLM gets the answer, never the haystack.
- **Pass-through small artifacts, exclude only storable/large ones.** `store_artifact` returns the artifact unchanged when there's no storage for its type, so small `InfoArtifact`s stay inline. Verso's exclusion gate must have the same threshold logic — don't pay the round-trip cost of a memory pointer for a 20-token result. The decision is per-output, by size/type.
- **Sequential vs parallel is two run methods over one task-graph, not two engines.** `Pipeline` (recursive single-child chain) and `Workflow` (futures-based topological superstep loop) share `Structure`/`add_task`/parent-child wiring. Verso's "pluggable edges" can be exactly this: one task graph, and the executor (sequential recursion vs. thread-pool wave-by-wave) is a strategy, not a separate framework. Note Workflow's `while not is_finished(): submit all can_run() tasks; wait as_completed` is a clean, copyable BSP-style parallel executor.
- **Task handoff via `parent_outputs`, distinct from memory tokens.** Griptape has two data paths: structured task-to-task flow (`parent_outputs` in context) and large-payload exclusion (TaskMemory reference tokens). Verso should keep these separate too — small structured results flow through typed context between steps; large opaque payloads go off-prompt with a pointer. Conflating them (everything through one messages list) is the anti-pattern most frameworks fall into.
- **RuleSets = named, swappable instruction bags loaded via a driver.** Lighter and more reusable than identity-modeling (CrewAI role/goal/backstory). Verso's behavioral-constraint layer should be named rulesets that render into the prompt and can be swapped per-run without changing task logic, loaded via a pluggable source (code/file/remote) — cheap to A/B and to govern centrally.
- **Driver abstraction = every external dep behind a `Defaults.drivers_config` lookup.** This is how Griptape keeps memory backend / embedding model / vector store independently pluggable. Verso already wants provider-agnostic inference (cf. `infra-serving.md` "one engine, N adapters"); extend the same discipline to memory storage, embeddings, and ruleset sources — a single defaults config resolving swappable drivers, so a task never names a concrete backend.

---

## Julep (julep-ai/julep)

### What It Is

A serverless platform for **durable multi-step AI workflows** backed by **Temporal**. Three primitives: `Agent` (identity + default model/tools), `Task` (a YAML/JSON-defined multi-step workflow), `Session` (a persistent conversation with configurable memory). The relevant RE target is the **task-execution engine**: how each task step maps to Temporal, and how the session memory modes work. The polyglot monorepo has a Python `agents-api` (the Temporal workflows + activities) and a `scheduler/` directory that is **just Temporal server config** (docker-compose, dynamic config, certs) — `[CORRECTION 2026-06-05]` the py-frameworks brief expected `src/scheduler/` to contain "Temporal activity per task step" code, but the activities/workflows actually live in `src/agents-api/agents_api/{workflows,activities}/`; `src/scheduler/` only deploys the Temporal cluster.

### Step-per-Workflow-Run + continue_as_new (KNOWN — the core mechanism)

`TaskExecutionWorkflow.run` (`workflows/task_execution/__init__.py:738`, decorated `@workflow.run`) executes **exactly one step, then recurses as a child workflow** — it does NOT loop over all steps in one workflow execution. The shape:
1. Build `StepContext(execution_input, current_input, cursor=start)` — `cursor` is a `TransitionTarget(workflow, step)` = the program counter.
2. If first step, `transition(type="init", next=cursor)` — durably record entry.
3. **Dispatch:** `activity = STEP_TO_ACTIVITY.get(step_type)` (`:780`). If a step maps to an activity, run it via `workflow.execute_activity(activity, context, schedule_to_close_timeout=…, retry_policy=DEFAULT_RETRY_POLICY, heartbeat_timeout=…)`. Else evaluate inline via `self.eval_step_exprs(...)`.
4. `handle_step(...)` decides the next cursor; `transition(context, state)` durably records the outcome.
5. On `finish`/`cancelled`/`error` → return. **Otherwise**, save the step output to a blob store (`save_inputs_remote`) and `continue_as_child(execution_input, start=final_state.next, current_input=final_output, …)` (`:899`) — **the next step runs as a fresh workflow execution.**

This `continue_as_new`-per-step is the durability design: Temporal's event history per workflow stays bounded (one step's worth), and every step boundary is a durable, replayable checkpoint. A crashed worker resumes the exact step from Temporal's history. **The `transition` activity (`:81`) is the event-sourcing write** — every `init`/`step`/`finish`/`error`/`cancelled` transition is persisted, so the execution is fully reconstructable.

### Step Types → Activity vs. Inline Eval (KNOWN — important nuance)

The brief expected each step type (prompt / tool_call / evaluate / wait_for_input / foreach / map_reduce / if-else) to be "a Temporal activity." **It's subtler:** `STEP_TO_ACTIVITY = {PromptStep: task_steps.prompt_step}` (`:108`) — **only `PromptStep` is dispatched as a Temporal activity** (the LLM call must be a retryable, timeout-bounded, heartbeating activity because it's the slow/flaky external call). Every other step type is handled by a `match step_type:` block (`:145`) that runs **inside the workflow** (deterministic, no activity):
- `EvaluateStep` (`:154`) — evaluate Python/jinja expressions over context (`base_evaluate`).
- `ToolCallStep` (`:171`) — `construct_tool_call` + `generate_call_id`; the actual tool execution (`execute_integration`/`execute_api_call`/`execute_system`) is a separate activity, but the step framing is in-workflow.
- `WaitForInputStep` (`:152`) — the HITL pause: transitions to a waiting state and the workflow blocks until external input resumes it (durable wait — survives restarts indefinitely, the Julep equivalent of Burr's `halt_before`).
- `ForeachStep` (`:146`) / `MapReduceStep` (`:156`) — iterate/fan-out via helpers (`execute_foreach_step`, `execute_map_reduce_step`, `execute_map_reduce_step_parallel` with `task_max_parallelism` bound); each iteration can `continue_as_child`.
- `IfElseWorkflowStep` (`:148`) / `SwitchStep` (`:162`) — branch by evaluating the condition list and routing the cursor.
- `ReturnStep` / `SetStep` / `LogStep` / `YieldStep` / `SleepStep` / `ParallelStep` — control/data steps, all in-workflow.

**Lesson: the activity boundary is drawn at non-determinism, not at "step."** Deterministic steps (branch, eval, set) run in the workflow for free replay; only non-deterministic external calls (LLM, tool I/O) become activities. This is the correct Temporal idiom and a sharper rule than "one activity per step."

### The Transition = The Event-Sourcing Write (KNOWN)

`transition(context, state, **kwargs)` (`workflows/task_execution/transition.py:22`) is the durable write that makes the whole thing event-sourced. It computes the transition `type` from `(is_last_step, cursor)` (`:30`): last step on `workflow="main"` → `"finish"`; last step on a branch → `"finish_branch"`; otherwise → `"step"`. It builds a `CreateTransitionRequest(current=cursor, next=TransitionTarget(workflow=cursor.workflow, step=cursor.step+1, scope_id=…), metadata={"step_type": type(current_step).__name__}, output=state.output, ...)` (`:38`) — **the cursor is literally a `(workflow, step_index)` program counter, and `next` is `step+1`** (or `None` at the end). Then it persists by running the `transition_step` activity (`:56`). Every state change (`init`/`init_branch`/`step`/`finish`/`finish_branch`/`error`/`cancelled`) is a row; the execution's full history = the ordered transition rows, exactly Burr's append-only model but with the action running between two transition writes and `continue_as_new` between steps.

`prompt_step` itself (`activities/task_steps/prompt_step.py:31`, `@activity.defn`) calls **LiteLLM** (`acompletion`) with the agent's model (default `"gpt-4o"`, `:52`), formatting tools via `format_tool` and running tool-augmented generation via `run_llm_with_tools` — so the one non-deterministic step is a LiteLLM call wrapped as a heartbeating Temporal activity.

`[CORRECTION 2026-06-05]` The brief (and the framework's own commented-out code) describe `DEFAULT_RETRY_POLICY = RetryPolicy(initial_interval=1s, backoff_coefficient=2, maximum_attempts=25)`, but the **live source sets `DEFAULT_RETRY_POLICY = None`** (`common/retry_policies.py:14`) with a `FIXME` noting that combining interceptors with a retry policy currently misbehaves. So in the current build, activities (including the LLM call) run with Temporal's default retry, not the documented 25-attempt exponential backoff. Worth flagging for Verso: the documented durability guarantee and the shipped one diverge here.

### Session Memory Modes (KNOWN)

A `Session` (`autogen/Sessions.py:55`) carries the memory config:
- **`context_overflow: Literal["truncate", "adaptive"] | None`** (`:80`) — the overflow strategy. `truncate` = drop oldest; `adaptive` = use `token_budget` (`:76`) as the threshold for the "adaptive context functionality" (compaction/summarization to fit the budget). Cross-ref `infra-serving.md` Together's `context_length_exceeded_behavior: "truncate"|"error"` — Julep adds an `"adaptive"` third mode (summarize rather than drop or error).
- **`recall_options: VectorDocSearch | TextOnlyDocSearch | HybridDocSearch | None`** (`:96`) — the retrieval mode for pulling from the doc store into context. So "memory modes" = the *retrieval* mode (vector / text / hybrid) plus the *overflow* mode (truncate / adaptive). This is a discriminated union — the session picks one search strategy.
- `token_budget`, `system_template` (jinja, `render_templates=True`), `auto_run_tools` (default `False` for sessions, `True` for tasks — sessions are conversational, tasks are autonomous), `forward_tool_calls`.

**Agent identity vs. Session state:** the `Agent` holds durable, cross-session knowledge (default model, tools, instructions, owned docs); the `Session` holds per-conversation state (message history, situation, the recall/overflow config, participant user/agent ids). Per-agent knowledge ends at "what this agent always knows/can do"; per-session context begins at "what's happened in this conversation + how to assemble its window." A session references one-or-many agents and users (`agent`/`agents`, `user`/`users`).

### For Verso

- **Draw the durability boundary at non-determinism, not at "step."** Julep's sharpest lesson: only `PromptStep` (the LLM call) becomes a Temporal *activity*; deterministic steps (branch, eval, set, foreach-framing) run inside the workflow for free, replayable execution. If Verso ever backs its durable mode with an external orchestrator (or its own event log), the checkpoint/activity boundary should wrap only the non-deterministic external calls (LLM, tool I/O). Wrapping every step in an activity is wasteful and Julep deliberately doesn't.
- **`continue_as_new` per step keeps event history bounded.** Each Julep step is a fresh workflow execution carrying forward only `current_input` (saved to a blob store, passed by reference). Verso's event-sourced mode should similarly bound the replay log per segment rather than accumulating an unbounded history in one execution — checkpoint, truncate history, continue. This is the durable-mode analog of context compaction.
- **`WaitForInputStep` = durable HITL that can wait indefinitely.** Unlike Burr's persist-and-re-invoke or LangGraph's interrupt, Julep's wait-for-input is a workflow that genuinely blocks (durably) until external input arrives — could be days. Verso's HITL design should distinguish "pause-and-let-the-caller-resume" (Burr-style, cheap, for in-process) from "durable indefinite wait" (Julep-style, for long-running human approval). The seam Verso wants ("one flag") should make the same `wait_for_input` step compile to a return-to-caller in tactical mode and a durable Temporal-style wait in durable mode.
- **Three context-overflow modes: truncate / adaptive / (error).** Julep's `context_overflow: "truncate"|"adaptive"` plus a `token_budget` is richer than the binary truncate/error seen in inference providers. `adaptive` = summarize-to-fit. Verso should offer all three as a per-run policy: drop-oldest, summarize-to-budget, or hard-error — and make `adaptive` (compaction) a first-class context-engineering primitive, not an afterthought.
- **Memory modes = retrieval-strategy union, separate from overflow.** Julep splits "how do I pull docs into context" (`recall_options`: vector/text/hybrid discriminated union) from "what do I do when context is full" (`context_overflow`). Verso should keep these orthogonal: a session/run declares its retrieval mode and its overflow mode independently. The hybrid search default is worth matching (cf. `infra-retrieval-tools.md` for hybrid-retrieval algebra).
- **Agent-identity vs. session-state separation is the right memory decomposition.** Durable cross-session knowledge lives on the Agent; per-conversation state (history + window-assembly config) lives on the Session. Verso's memory model should make this split explicit — an agent's "always-knows" (Letta's in-context core, cf. `fw-crewai-letta.md`) vs. a session's "this-conversation" working set — rather than one undifferentiated memory blob.

---

## Cross-Peer Synthesis → Verso

**The seam, six ways.** Each peer takes a position on the tactical↔durable seam, and the spread is the design space:
- **Burr** — durability is a *post-step lifecycle hook*; in-memory vs. durable = with/without one `PersisterHook`. The loop is persistence-agnostic. **(Closest to Verso's "one flag" — adopt this.)**
- **Marvin** — durability is *always on* (every message and LLM call hits SQLAlchemy); there is no tactical mode. Strong on typed-result-as-terminal-tool and ContextVar-scoped Thread.
- **PocketFlow** — *no* durability; `shared` dict is ephemeral. The 100-line floor Verso diffs against.
- **Atomic Agents** — *no* durability, no loop; single typed call. The purest typed-IO contract via generics.
- **Griptape** — durability is per-artifact (TaskMemory off-prompt store); the headline is context-by-exclusion via reference tokens.
- **Julep** — durability is *external* (Temporal `continue_as_new` per step); the activity boundary is drawn at non-determinism.

**What Verso should take from each:**
1. **Burr's hook-based seam** — the literal mechanism for "one flag": empty adapter set (tactical) vs. one persist hook (durable), loop unchanged. Plus the `(partition_key, app_id, sequence_id, position)` append-only schema and `halt_before`/`halt_after`-as-generator-return for HITL.
2. **Marvin's typed-terminal-tool** — the agent finishes by emitting a typed object (`MarkTaskSuccessful(result: T)`), making the result type and the stop condition the same thing. Plus the `llm_call_messages` join (per-call prompt/completion attribution) as the eval/observability substrate.
3. **PocketFlow's prep/exec/post** — node lifecycle that isolates the retryable compute from shared-state I/O; the diff-against-floor for Verso's minimal loop.
4. **Atomic Agents' ContextProvider** — context engineering as a named dict of `() -> str` producers folded into the prompt at call time (pull, not push).
5. **Griptape's TaskMemory** — context-by-exclusion: large tool outputs stored off-prompt under `(memory_name, artifact_namespace)`, only the reference token in the prompt, a reader tool RAGs it back. The single most reusable context-engineering pattern in the cluster.
6. **Julep's non-determinism boundary** — if Verso backs durable mode with an event log, wrap only the non-deterministic calls (LLM, tool I/O); deterministic steps replay for free. Plus truncate/adaptive/error as a per-run overflow policy.

**The convergent verdict (matching py-frameworks Notes):** typed output is table stakes (all six use Pydantic/dataclass schemas); the loop is increasingly delegated to a structured-output engine (Marvin→Pydantic-AI, Atomic→Instructor) while the framework owns context + durability + typing; context engineering is the real frontier and only Griptape (exclusion) and Julep (adaptive overflow) treat it architecturally. Verso's differentiation — the clean tactical↔durable seam (Burr-style hook) + first-class context engineering (Griptape exclusion + Atomic providers) + typed terminal contracts (Marvin) + a real eval substrate (Marvin's per-call message attribution) — is a coherent, defensible position none of these six occupy simultaneously.
