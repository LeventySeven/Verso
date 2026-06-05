# Durable Execution — Verso Research Note
## Cluster: infra-durable-execution
### Systems: Temporal · DBOS · LangGraph Checkpointing · Restate · Hatchet · Inngest · Resonate · Trigger.dev v3 · Windmill · Cloudflare Workflows · LittleHorse · AWS Step Functions

*Sources (all read at `--depth=1` HEAD, 2026-06-05): temporalio/sdk-python `temporalio/worker/_workflow_instance.py` (3836 lines), `worker/workflow_sandbox/_importer.py` (578), `_restrictions.py` (1196), `_runner.py` (230); dbos-inc/dbos-transact-py `dbos/_workflow.py`, `_core.py`, `_sys_db.py`, `_schemas/system_database.py`, `_dbos.py`; langchain-ai/langgraph `libs/checkpoint/.../base/__init__.py`, `libs/checkpoint-postgres/.../postgres/{base,__init__,aio}.py`, `libs/langgraph/.../pregel/`; restatedev/sdk-python `restate/context.py`, `_internal/*`, `restate/serde.py`; inngest/inngest-py `inngest/_internal/{step_lib,execution_lib,server_lib}/`; resonatehq durable-promise-specification + resonate-sdk-py (web). P2/closed targets (Trigger.dev CRIU, Windmill, Cloudflare Workflows, LittleHorse, AWS SFN) from blog/docs as marked.*

*Cross-ref: `researchfms/teardowns/PREFECT.md` covers the Prefect FastAPI server layer ONLY — the orchestration engine/scheduler is NOT covered there, and is out of scope here too (Prefect is DAG-first, not ReAct-first). `infra-serving.md` (this folder) covers the streaming/cancellation contract that the durable layer sits behind.*

The four subsystems Verso must extract from this cluster, used as the lens for every target:
1. **Journal / checkpoint store** — the append-only log or KV store that persists step results.
2. **Replay / determinism mechanism** — how the runtime re-executes code without re-firing side effects.
3. **HITL pause protocol** — how the agent suspends mid-loop and resumes on external input.
4. **The seam** — the decorator/context-manager that makes `durable=False` and `durable=True` share one code path.

---

## Temporal (Python SDK + Rust core) — P0

### What It Is

The gold-standard event-history-replay durable engine. The Python SDK is a three-layer stack: a Rust core (`sdk-core`, compiled via PyO3 into `temporalio.bridge.temporal_sdk_bridge`) owns the connection to the Temporal server and the event-history state machine; a **custom deterministic asyncio event loop** (`_WorkflowInstanceImpl`, which subclasses `asyncio.AbstractEventLoop`) drives the user's `async def` workflow; and an **import sandbox** re-imports the workflow module fresh per worker to prevent global-state leakage. The workflow code never touches the network — it emits **Commands**, the server records **Events**, and replay re-runs the code to regenerate the same Commands. This is the canonical "determinism required, no side effects in workflow body" model.

### The Replay Engine — Commands vs Events, driven by `seq`

The replay contract is `seq`-based, not order-based. Every durable operation (timer, activity, child workflow, signal-external, etc.) gets a **monotonic per-type sequence number** (KNOWN, `_workflow_instance.py:2422`):

```python
def _next_seq(self, type: str) -> int:        # type ∈ {"timer","activity","child_workflow","external_signal",...}
    seq = self._curr_seqs.get(type, 0) + 1     # independent counter PER TYPE
    self._curr_seqs[type] = seq
    return seq
```

The pending-operation maps are all keyed by this seq (`:281`): `_pending_timers: dict[int, _TimerHandle]`, `_pending_activities: dict[int, _ActivityHandle]`, `_pending_child_workflows`, `_pending_external_signals: dict[int, tuple[asyncio.Future, str]]`. When the server sends back a resolution job, the SDK pops by seq and resolves the matching future (KNOWN, `:808`):

```python
def _apply_resolve_activity(self, job):
    handle = self._pending_activities.pop(job.seq, None)
    if not handle:
        raise RuntimeError(f"Failed finding activity handle for sequence {job.seq}")  # non-determinism detector
    ...
    handle._resolve_success(ret)   # or _resolve_failure / _resolve_backoff
```

That `RuntimeError` IS the non-determinism guard: if a replay generates Commands in a different order/count than the recorded Events, a resolution job arrives with a seq that has no pending handle → the workflow task fails (not the workflow). The handle objects subclass asyncio primitives and emit their commands directly: `_TimerHandle(asyncio.TimerHandle)` (`:3055`) has `_apply_start_command(command, delay)` setting `command.start_timer.seq = self._seq` and `start_to_fire_timeout.FromNanoseconds(int(delay*1e9))`, and `_apply_cancel_command` setting `command.cancel_timer.seq`. So an `await asyncio.sleep(5)` in workflow code becomes: `call_later` → `_timer_impl` → `_next_seq("timer")` → a `start_timer` command with that seq → on replay, a `fire_timer` job with the same seq pops the pending handle and resumes the coroutine. The asyncio API is fully reimplemented over the command/event substrate. Scheduling a timer emits the command immediately at schedule time (`:2756`):

```python
def _timer_impl(self, delay, options, callback, *args, context=None):
    seq = self._next_seq("timer")
    handle = _TimerHandle(seq, self.time() + delay, options, callback, args, self, context)
    handle._apply_start_command(self._add_command(), delay)   # Command emitted NOW
    self._pending_timers[seq] = handle
    return handle
```

### The Activation Loop — the actual `activate()` algorithm

A "workflow task" from the server is a `WorkflowActivation` containing N jobs. `activate()` (KNOWN, `:414`) does NOT process jobs in arrival order — it **sorts jobs into 4 ordered sets** to guarantee deterministic ordering:

```python
job_sets = [[], [], [], []]
for job in act.jobs:
    if job.HasField("notify_has_patch"):                              job_sets[0]   # patches FIRST
    elif job.HasField("signal_workflow") or job.HasField("do_update"): job_sets[1]   # signals + updates
    elif not job.HasField("query_workflow"):                          job_sets[2]   # everything non-query (incl. timer/activity resolutions, init)
    else:                                                             job_sets[3]   # queries LAST
for index, job_set in enumerate(job_sets):
    for job in job_set: self._apply(job)
    self._run_once(check_conditions = index == 1 or index == 2)   # conditions checked ONLY after signals (1) and main (2)
```

Key invariant: `wait_condition` predicates are re-evaluated only after signal/update jobs and after the main job set — never after patch jobs or query jobs. This is why a query cannot unblock a `wait_condition` (queries are read-only, run last, no condition check).

`_run_once` (KNOWN, `:2520`) is the deterministic event-loop tick. It sets itself as the running loop (`asyncio._set_running_loop(self)`), drains the `_ready` deque of `asyncio.Handle`s, then re-checks conditions, looping until quiescent:

```python
while self._ready:
    while self._ready:
        handle = self._ready.popleft(); handle._run()
        if self._current_activation_error and not self._deleting: raise self._current_activation_error
    if check_conditions:
        self._conditions[:] = [t for t in self._conditions
                               if not t[1].done() and not self._check_condition(*t)]   # (predicate, future) pairs
```

`call_soon` just appends to `self._ready` (`:2791`). `time()` returns `self._time_ns / 1e9` where `_time_ns` is set from `act.timestamp` per activation (`:433`, `:2833`) — **workflow time is server-stamped, never wall-clock**. `call_later` routes through `_timer_impl` so `asyncio.sleep` becomes a durable Temporal timer command.

### Determinism guards (the seam's hard boundary)

- **Randomness**: `self._random = random.Random(det.randomness_seed)` (`:296`), reseeded by `_apply_update_random_seed` (`:1103`). `workflow.random()` returns this seeded RNG; `random.random()` from the sandbox is *blocked*.
- **`is_replaying`** flag (`:434`) gates side-effect-once logic. `workflow_patch(id)` (`:1355`) is the versioning primitive: memoizes per id; on replay returns `id in self._patches_notified`; on first run emits a `set_patch_marker` command — this is how you safely change workflow code in flight (the `[CORRECTION]`-safe alternative to seq-order brittleness).
- **`_assert_not_read_only`** wraps every state-mutating call (schedule timer, random, create task, set query handler) — during query/read-only contexts these raise, enforcing that queries cannot mutate workflow state.

### HITL trio: signal / query / update + wait_condition

The canonical pause-resume model. Handlers are pre-registered on the instance (`:314`): `_signals = dict(self._defn.signals)`, `_queries`, `_updates`. Three built-in queries are auto-registered: `__stack_trace`, `__enhanced_stack_trace`, `__temporal_workflow_metadata` (`:331-347`).

- **Signal** (`@workflow.signal`, async, no return): `_apply_signal_workflow` (`:1055`) looks up `_signals.get(name) or _signals.get(None)` (None = dynamic catch-all); if no handler, **buffers** into `_buffered_signals[name]` (delivered when a handler later registers — solves the signal-before-handler race). Delivered signals spawn a top-level task tracked in `_in_progress_signals` (`:2482`).
- **Update** (`@workflow.update`, can have a `@x.validator`, returns a value): `_apply_do_update` (`:607`) runs the validator synchronously (rejection = no history mutation), then runs the handler tracked in `_in_progress_updates: dict[str, HandlerExecution]` keyed by `job.id` (`:630`).
- **Query** (`@workflow.query`, sync, read-only): `_apply_query_workflow` (`:734`) runs in a read-only context, no condition checks, no commands.
- **`workflow.wait_condition(fn, timeout)`** (`:1787`) is the suspend primitive: appends `(fn, future)` to `self._conditions` and `await asyncio.wait_for(fut, timeout)`. The future is resolved by `_check_condition` re-evaluating `fn()` after each signal/main job set. Pattern: `await workflow.wait_condition(lambda: self._approved is not None)` — the agent blocks until a signal sets `self._approved`. With a timeout (`:1810` `await asyncio.wait_for(fut, timeout)`), the condition future races a durable timer; if the timer fires first, `wait_for` raises `TimeoutError` and `_run_once` (`:2546`) prunes the now-cancelled condition from `self._conditions` (the `not t[1].done()` filter). This is the exact "wait for human-approval signal OR timeout, whichever first" primitive — the same shape as Hatchet's `OrGroup` and SFN's `HeartbeatSeconds`, here expressed as a condition-future racing a durable timer.
- **`workflow_all_handlers_finished`** (`:1140`): `not self._in_progress_updates and not self._in_progress_signals` — the SDK warns (`_warn_if_unfinished_handlers`, `:547`) if the workflow completes while handlers are still running.

### Failure classification — fail-the-task vs fail-the-workflow

KNOWN, `_run_top_level_workflow_function` (`:2556`). The single most important error-handling distinction in durable execution: when the workflow coroutine raises, the SDK classifies it three ways: (1) `_ContinueAsNewError` → apply the continue-as-new command (not a failure); (2) if a cancel was requested and `is_cancelled_exception(err)` → emit `cancel_workflow_execution`; (3) if `workflow_is_failure_exception(err)` (a configured "failure" type, e.g. `ApplicationError`) → `_set_workflow_failure(err)` — **the workflow ends as FAILED, history records the failure, no retry of the workflow task**; (4) **any other exception** → `self._current_activation_error = err` — this **fails the workflow TASK, not the workflow**: the task is retried (with the same history) indefinitely until the bug is fixed or the error becomes deterministic. This is the crucial safety property: a transient bug (network blip, OOM) fails the task and retries; only an explicit application failure ends the workflow. **Verso must replicate this two-tier classification**: a transient step error retries the step/run; only an explicit terminal failure (or `MAX_RECOVERY_ATTEMPTS`) ends the agent as failed. Conflating them means a transient blip permanently kills an agent run.

### The activation completion protocol

KNOWN, `activate()` epilogue (`:536`). After running all job sets, the SDK builds a `WorkflowActivationCompletion`: either `.successful` (carrying the list of generated `WorkflowCommand`s) or `.failed` (carrying a converted `Failure`). `is_completion` (`:536`) scans the commands for `complete_workflow_execution` / `continue_as_new_workflow_execution` / `fail_workflow_execution` / `cancel_workflow_execution` — if any present, the workflow is done and `_warn_if_unfinished_handlers` checks for orphaned signal/update handlers. The completion is what crosses the FFI boundary back to the Rust core, which sends the commands to the server. The protocol is: server sends Activation (jobs) → SDK applies jobs + runs the loop → SDK returns Completion (commands or failure). One activation = one workflow task = one atomic unit of progress. Verso's equivalent atomic unit: one durable executor tick that consumes pending external inputs, runs the loop forward, and emits the set of new step-writes + any terminal command.

### The Sandbox — per-replay reimport + passthrough

To stop two workflow runs from sharing mutable module globals, `SandboxedWorkflowRunner` (`_runner.py:62`) re-imports the workflow module inside a restricted `Importer` **for each instance** (`runner_class` docstring: "re-imported and instantiated for *each* workflow run"). The `Importer` swaps `sys.modules` to a thread-local `new_modules` dict (`_importer.py:143`) and proxies non-deterministic stdlib through `RestrictedModule`.

**Passthrough tiers** (modules imported from outside the sandbox, NOT re-imported — for performance and C-extension safety):
- `passthrough_modules_minimum` (`_restrictions.py:465`): `grpc, pathlib, importlib, importlib_metadata, platform, zipfile, typing, typing_extensions, google.protobuf, temporalio.api, temporalio.bridge.proto, temporalio.bridge.temporal_sdk_bridge` (the PyO3 bridge MUST pass through — PyO3 disallows re-init since 0.17).
- `passthrough_modules_with_temporal` (`:499`): adds `asyncio, abc, nexusrpc, temporalio, pkg_resources, pydantic`.

**Restricted stdlib members** (`invalid_module_members_default`, `:551`) — these raise `RestrictedWorkflowAccessError` at runtime inside a workflow: `datetime.datetime.{now,today,utcnow}`, all of `os`, `random.*`, `secrets.*`, `time.*`, `threading.*` (all_uses_runtime), `uuid.{uuid1,uuid4}` (only_runtime). The matcher distinguishes `only_runtime` (allowed at import, blocked at execution) from import-time blocks.

### Constants

| Constant | Value | Source |
|---|---|---|
| `max_cached_workflows` | 1000 | `_worker.py:114` (sticky cache; 0 disables stickiness) |
| `nonsticky_to_sticky_poll_ratio` | 0.2 | `_worker.py:121` |
| `sticky_queue_schedule_to_start_timeout` | 10s | `_worker.py:124` |
| seq counters | per-type, monotonic from 1 | `_workflow_instance.py:2422` |
| `call_at` time rounding | nearest ms (`round(..., 3)`) | `:2829` (float ns precision workaround) |
| job-set ordering | patches→signals/updates→main→queries | `:442` |

### Activity scheduling & retry (the side-effect boundary)

KNOWN, `workflow_start_activity` (`:1450`). The workflow body never does I/O directly — it schedules an **activity** (the side-effectful unit) with a full option set: `schedule_to_close_timeout`, `start_to_close_timeout`, `retry_policy: RetryPolicy`, `cancellation_type: ActivityCancellationType`. The activity runs on a separate worker pool (or the same worker, different executor), and its result/failure crosses back as a `ResolveActivity` job matched by seq. The `RetryPolicy` (initial_interval, backoff_coefficient, max_interval, max_attempts, non_retryable_error_types) is enforced server-side — the workflow just `await`s the handle; retries are invisible to the workflow body and don't consume workflow-task time. This is the hard determinism boundary: **`@workflow.run` = deterministic orchestration; `@activity.defn` = arbitrary side-effects with server-managed retry.** Verso's equivalent is "the LLM call / tool call is the activity (retryable, side-effectful); the loop logic that decides what to call is the workflow (must be replayable)."

### Continue-as-new (unbounded loops without unbounded history)

KNOWN, `workflow_continue_as_new` (`:1143`). Event history grows with every command; a long-running loop would grow it without bound and slow replay. `continue_as_new(...)` atomically completes the current run and starts a fresh run with new input, carrying `task_queue`, `run_timeout`, `memo`, `search_attributes`, `versioning_behavior` — **history resets to zero**. `_continue_as_new_suggested` (`:429`) is a server hint (set when history crosses a size/length threshold) telling the workflow it's time. **This is the critical pattern for a long-running Verso agent**: an agent that runs for days/thousands of turns cannot keep an unbounded journal — it must periodically snapshot its essential state and "continue as new" with a fresh, small journal. Any memoization-based Verso durable mode has the same problem (the `step_outputs` table grows per turn) and needs the same escape hatch: compact + restart with carried-over state.

### Eviction & GC safety

KNOWN, `_apply_remove_from_cache` (`:797`). When the worker evicts a workflow from its sticky cache, it sets `self._deleting = True`, `self._is_replaying = True` (so replay-skipping code like logging stays quiet), and **cancels every pending task** (`task.cancel()`). The `activate()` epilogue (`:504`) then asserts `not self._tasks` after eviction — if tasks remain, a `GeneratorExit` could fire a coroutine on the wrong thread/event-loop, corrupting state, so it raises rather than risk it. The non-weak `_tasks` set (`:2511`, with `_log_destroy_pending=False`) exists precisely so Python's GC doesn't collect a coroutine too early and trigger that cross-thread wakeup. Lesson for Verso: when evicting/suspending an in-flight agent, cancel all its outstanding async tasks deterministically before releasing — don't let GC do it lazily.

### `Replayer` — workflow-compatibility testing

KNOWN, `worker/_replayer.py` (441 lines). The `Replayer` re-runs a recorded event history against current workflow code with no server — if the new code generates different commands than the recorded events, replay fails. This is the regression-test harness for "did my code change break in-flight workflows?" Verso's equivalent: a test that replays a recorded agent run's `step_outputs` against the current agent code and asserts the same step sequence/hashes.

### Child workflows & cross-workflow signals (multi-agent coordination)

KNOWN, `workflow_start_child_workflow` (`:1507`) + `_ExternalWorkflowHandle` (`:3396`). A workflow spawns a child via `StartChildWorkflowInput` (seq-tracked in `_pending_child_workflows`) with a `parent_close_policy: ParentClosePolicy` (TERMINATE / ABANDON / REQUEST_CANCEL — what happens to the child when the parent closes). The start resolves in two phases: `_apply_resolve_child_workflow_execution_start` (child started, returns its run id) then `_apply_resolve_child_workflow_execution` (child completed). A workflow can also get a handle to *any other* workflow via `workflow_get_external_workflow_handle(id)` (`:1220`) and `await handle.signal(name, arg)` (`:3416`) — a cross-workflow signal, seq-tracked in `_pending_external_signals` and resolved by `_apply_resolve_signal_external_workflow` (`:1031`). **This is Temporal's multi-agent coordination substrate**: a parent agent spawns durable child agents (each with its own journal), awaits their results, and agents signal each other by id. Verso's multi-agent durable mode needs the same: a durable `run_child_agent` that returns a handle, and a `signal_agent(id, msg)` for sibling coordination — all journaled so the coordination survives crashes.

### Payload converters & codec (the serialization + encryption boundary)

KNOWN, `temporalio/converter/`. Every value crossing the FFI boundary (workflow input/output, activity args, signal payloads, memo) is a protobuf `Payload` produced by a `CompositePayloadConverter` — an ordered chain of `EncodingPayloadConverter`s (binary/null → protobuf JSON → `JSONPlainPayloadConverter` Pydantic-aware default). An optional `PayloadCodec` (`_payload_codec.py`) wraps the converter to encrypt/compress payloads at rest (the codec runs *outside* the sandbox, on the way to/from the server). The `ActivitySerializationContext` (`:814`) gives the converter per-activity context (namespace, workflow_id, activity_type) so encryption keys can be scoped. Lesson for Verso: the checkpoint serializer must be a pluggable chain (JSON default, Pydantic-aware, with an optional encryption codec layer) — an agent's durable state often contains sensitive data (API keys in context, PII in tool results) that must be encrypted at rest in the checkpoint store.

**For Verso:** Temporal's three-layer split is the most complete existence proof of the seam, but the full event-history replay + sandbox is *heavier than Verso needs* for a dynamic ReAct loop (replay requires the workflow body be fully deterministic; the sandbox reimport is expensive). Steal: (1) the **per-type monotonic `seq`** as the step-identity primitive and the "resolution job with unknown seq → fail the task" non-determinism detector; (2) the **4-set job ordering** so signals are always applied before condition checks (Verso's HITL `wait_condition` equivalent must re-check predicates only after delivering external input, never on a read-only query); (3) `wait_condition(fn, timeout)` as the literal shape of Verso's pause primitive — a `(predicate, future)` list drained each tick; (4) server-stamped `time()` and a seeded RNG as the determinism-safe replacements. Skip the sandbox reimport — Verso's memoization model (see Inngest/DBOS below) doesn't replay the whole body, so it doesn't need global-state isolation.

---

## DBOS (dbos-transact-py) — P0

### What It Is

The cleanest "one decorator, no rewrite, Postgres is the whole backend" model. There is no orchestration server — you annotate `@DBOS.workflow()` / `@DBOS.step()` / `@DBOS.transaction()` and a Postgres (or SQLite) schema named `dbos` becomes the checkpoint store. Recovery happens in a background thread at process startup. The headline trick: `@DBOS.transaction()` writes the step's checkpoint **inside the same Postgres transaction** as the user's SQL, giving exactly-once semantics at zero extra round-trip.

### Step identity: a per-workflow monotonic `function_id`

Unlike Temporal's per-type seq or Inngest's content hash, DBOS uses a **single monotonic counter per workflow context**, incremented on every durable operation (KNOWN, `_context.py:169`):

```python
self.function_id += 1
rv.function_id = self.function_id     # snapshot into the child step context
if reserve_sleep_id:
    self.function_id += 1             # sleep reserves TWO ids (the sleep + its wakeup record)
```

This means **step identity = call order within the workflow**. The determinism requirement is therefore "call your steps in the same order on replay" — exactly like Windmill, and weaker than Temporal (the workflow body can contain arbitrary non-determinism *between* steps, only the step *sequence* must be stable). The replay key is the composite primary key `(workflow_uuid, function_id)` on `operation_outputs`.

### The checkpoint store — exact Postgres schema (`dbos` schema)

KNOWN, verbatim from `_schemas/system_database.py`. The two load-bearing tables:

```
dbos.workflow_status   PK(workflow_uuid)
  status TEXT           ∈ {PENDING, ENQUEUED, SUCCESS, ERROR, CANCELLED, MAX_RECOVERY_ATTEMPTS_EXCEEDED, DELAYED}
  name, class_name, config_name, inputs TEXT, output TEXT, error TEXT
  executor_id TEXT      -- which worker owns it (recovery filters on this)
  recovery_attempts BIGINT
  application_version TEXT  -- in-flight version pinning
  queue_name, deduplication_id, priority INT, workflow_timeout_ms, workflow_deadline_epoch_ms
  forked_from, was_forked_from BOOL, parent_workflow_id
  partial indexes: idx_workflow_status_pending (WHERE status='PENDING'), _delayed, _failed, _in_flight (queue_name,status,priority,created_at WHERE status IN ('ENQUEUED','PENDING'))

dbos.operation_outputs   PK(workflow_uuid, function_id)   -- the step journal
  function_id INT, function_name TEXT
  output TEXT, error TEXT, serialization TEXT
  child_workflow_id TEXT   -- if this step started a child workflow
  started_at_epoch_ms, completed_at_epoch_ms BIGINT
```

HITL tables: `dbos.notifications` (PK `message_uuid`, FK→workflow_status; cols `destination_uuid, topic, message, consumed BOOL`; index `idx_workflow_topic (destination_uuid, topic)`) backs `recv`/`send`. `dbos.workflow_events` (PK `(workflow_uuid, key)`) backs `set_event`/`get_event`. `dbos.streams` (PK `(workflow_uuid, key, offset)`) backs durable streaming. `dbos.queues` holds queue config (concurrency, `worker_concurrency`, `rate_limit_max`, `rate_limit_period_sec`, `priority_enabled`, `polling_interval_sec` default `1.0`).

### The three-write cost model & memoization

Every step is wrapped by `invoke_step` (`_core.py`). Before running, `check_existing_result()` (`:1703`) reads `operation_outputs` by `(workflow_id, function_id)`:

```python
recorded_output = dbos._sys_db.check_operation_execution(ctx.workflow_id, ctx.function_id, step_name)
if recorded_output:
    if recorded_output["error"] is not None: raise deserialize_exception(...)   # replay the error too
    elif recorded_output["output"] is not None: return deserialize_value(...)    # cache hit → instant
    # → "Running step, id: {function_id}" on miss
```

On miss it runs the function then `record_operation_result(step_output)` (one INSERT). Plus the workflow itself does one INSERT on start (status=PENDING) and one UPDATE on finish (status=SUCCESS + output) → the **three-write baseline**: 1 per step + 2 per workflow.

### Transaction piggybacking (the zero-overhead exactly-once trick)

`@DBOS.transaction()` (`_core.py:1374`) opens `session.begin()`, sets `isolation_level`, checks `ApplicationDatabase.check_transaction_execution` for OAOO, runs the user's SQL, then writes the checkpoint **as the last statement of the SAME transaction** (KNOWN, `:1448`):

```python
with session.begin():
    session.connection(execution_options={"isolation_level": isolation_level})
    recorded_output = ApplicationDatabase.check_transaction_execution(session, ctx.workflow_id, ctx.function_id, transaction_name)
    if recorded_output: return ...        # replay
    ... run user SQL ...
    dbos._app_db.record_transaction_output(ctx.sql_session, txn_output)   # SAME txn → commits atomically with user writes
    break
```

The checkpoint row lives in `transaction_outputs` in the *application* DB (not the system DB) precisely so it shares the user's transaction. Schema (`_schemas/application_database.py:18`): `transaction_outputs(workflow_uuid, function_id, output, error, txn_id, txn_snapshot, executor_id, function_name, created_at)` — note `txn_id` (the Postgres transaction id) and `txn_snapshot` (the MVCC snapshot string) are recorded, enabling point-in-time consistency checks and the OAOO (once-and-only-once) guarantee: `check_transaction_execution` reads this row by `(workflow_uuid, function_id)` *inside the same transaction* before running, so a replay of a committed transaction returns the recorded output without re-executing the SQL. Because the checkpoint and the user's writes commit atomically, there is **zero window** where the DB mutation happened but the checkpoint didn't (or vice versa) — the defining property of the piggyback. Serialization-error retry loop: `retry_wait_seconds=0.001`, `backoff_factor=1.5`, `max_retry_wait_seconds=2.0` (`:1371`). **This is the single highest-value pattern for Verso's DB-touching tool steps**: if a Verso tool writes to the same Postgres as the checkpoint store, write the checkpoint in that tool's transaction → exactly-once with no extra round-trip and no dual-write inconsistency.

### HITL: recv / send (Postgres pub/sub, not a signal channel)

`DBOS.recv(topic, timeout=60)` is a two-phase durable receive. `recv_setup` (`_sys_db.py:2570`): first checks `operation_outputs` for a replayed result; if fresh, registers a `threading.Event` in an in-process `notifications_map` keyed `f"{workflow_uuid}::{topic}"`, calls `recv_check` (is a message already in `notifications`?), and records a **durable sleep** for the timeout (`record_sleep`, which is why `function_id` increments by 2 for waits). `recv_consume` (`:2629`) transactionally `UPDATE notifications SET consumed=TRUE` on the **oldest unconsumed** message (`ORDER BY created_at_epoch_ms ASC LIMIT 1` scalar subquery) and records the operation result in the same `engine.begin()` transaction. The Event is signaled by a Postgres `LISTEN/NOTIFY` listener thread, with a **60s fallback poll** (`_notification_fallback_polling_interval = 60.0`, `:2720`) to catch dropped notifications. This is a durable named-channel mailbox, distinct from Temporal's in-memory signal buffer.

### Recovery algorithm (startup, no server)

`startup_recovery_thread` (`_recovery.py:26`) runs in the background at boot; `recover_pending_workflows(dbos, executor_ids=["local"])` (`:52`) queries `workflow_status WHERE status='PENDING' AND executor_id=<id> AND application_version=<current>` and re-enqueues each. Crucially, the `recovery_attempts` counter is incremented on each PENDING-insert attempt; when `recovery_attempts > max_recovery_attempts + 1` the workflow is flipped to `MAX_RECOVERY_ATTEMPTS_EXCEEDED` (a poison-pill guard, `_sys_db.py:731`). `DEFAULT_MAX_RECOVERY_ATTEMPTS = 100` (`_registrations.py:10`). The exact recovery driver (`_recovery.py:16`): `_recover_workflow` checks `if workflow.queue_name: clear_queue_assignment(id)` — a queued workflow that was mid-dispatch is returned to the queue (`retrieve_workflow`), not re-executed directly; otherwise `execute_workflow_by_id(dbos, id, True, False)` re-runs it. The startup loop (`:32`) retries each pending workflow, tolerating `DBOSWorkflowFunctionNotFoundError` (the code for that workflow isn't deployed on this executor — sleep 1s, leave it for another executor) but dropping a workflow on any other exception. The `executor_id` filter is the multi-worker partition: each worker only recovers its own pending workflows (or, for queued ones, returns them to the shared queue). `SetWorkflowID(key)` is the idempotency context manager (workflow_uuid = key → duplicate start is a no-op replay). `fork_workflow(id, start_step)` copies `operation_outputs` rows with `function_id < start_step` into a new workflow_uuid (`was_forked_from=true`), the operator restart-from-step escape hatch.

| Constant | Value | Source |
|---|---|---|
| `DEFAULT_MAX_RECOVERY_ATTEMPTS` | 100 | `_registrations.py:10` |
| notification fallback poll | 60.0s | `_sys_db.py:2720` |
| queue default `polling_interval_sec` | 1.0 | schema |
| txn retry: start / factor / max | 0.001s / 1.5× / 2.0s | `_core.py:1371` |
| step journal PK | `(workflow_uuid, function_id)` | schema |
| sleep id reservation | +2 function_ids | `_context.py:171` |
| recv default timeout | 60s | `_sys_db.py:2576` |

### Events: set_event / get_event (workflow-as-key-value-publisher)

KNOWN, `_core.py:1986`, `_dbos.py:1692`. Distinct from recv/send (a mailbox), `set_event(key, value)` publishes a value on the workflow's own id, readable by anyone via `get_event(workflow_id, key, timeout=60)`. Inside a workflow it's recorded as a step (`EnterDBOSStepCtx`) so it's idempotent on replay; the value lands in `workflow_events` PK `(workflow_uuid, key)` (and the immutable `workflow_events_history` keyed `(workflow_uuid, key, function_id)`). Use case: a long-running agent publishes progress/intermediate results that an external dashboard polls — without interrupting the agent. `get_event` blocks up to the timeout using the same LISTEN/NOTIFY + 60s fallback poll as recv.

### Durable sleep

KNOWN, `_dbos.py:1586`, `record_sleep` (`_core.py:2034`). `DBOS.sleep(seconds)` records the wakeup deadline as an operation result keyed by `function_id`; on replay it reads the recorded deadline and computes remaining time — so a workflow that slept 24h and crashed at hour 23 resumes and sleeps only the remaining hour, not a fresh 24h. This is why `function_id` increments by 2 for a sleep (`_context.py:171`): one id for the sleep operation, one reserved for its recorded wakeup. Survives process restart because the deadline is in Postgres, not an in-process timer.

### Queues & concurrency control

KNOWN, `_queue.py:57`. A `Queue(name, concurrency=, worker_concurrency=, priority_enabled=, rate_limit=...)` is a durable work queue backed by the `queues` table (schema above) + `workflow_status.queue_name`. `concurrency` = global cap across all workers; `worker_concurrency` = per-worker cap (must be `≤ concurrency`, enforced `:121`). Enqueue via `queue.enqueue(fn, *args)` → inserts a `workflow_status` row with `status='ENQUEUED'`; the partial index `idx_workflow_status_in_flight (queue_name, status, priority, created_at WHERE status IN ('ENQUEUED','PENDING'))` is what makes dequeue-by-priority cheap. Rate limiting via `rate_limit_max` + `rate_limit_period_sec` (the `idx_workflow_status_rate_limited` partial index). This is Verso's concurrency-control substrate: cap how many durable agents run concurrently globally and per-worker, with priority and rate limits, all in Postgres.

### DBOSClient — programmatic control plane

KNOWN, `_client.py:147`. The out-of-process control API (no decorators needed): `list_workflows(...)` (filter by status/name/time/queue), `retrieve_workflow(id)` → handle, `fork_workflow(id, start_step)` (restart from step N — copies `operation_outputs` rows with `function_id < start_step`, sets `was_forked_from=true`), `send(destination, message, topic)`, `get_event(workflow_id, key, timeout=60)`, plus cancel/resume. This is the operator escape hatch Verso needs: inspect stuck agent runs, restart from a specific step after a bug fix, inject a message, read a published event — all from outside the agent process.

### Step retry — the `Outcome` monad

KNOWN, `_outcome.py:155`, used by `invoke_step` (`_core.py:1751`). A `@DBOS.step(retries_allowed=True, max_attempts=N, interval_seconds=, backoff_rate=)` wraps the step body in an `Outcome` (an `Immediate[T]` for sync, `Pending[T]` for async) and calls `.retry(attempts, on_exception, exceeded_retries, should_retry)`. `on_exception(attempt, err) -> float` returns the next sleep before retry (so backoff is a callback, default exponential via `interval_seconds * backoff_rate**attempt`); `exceeded_retries(attempt, errors) -> Exception` builds the terminal error after the last attempt; `should_retry(err) -> bool` lets the step opt out of retrying specific exceptions. The retry composes via `.then(...)` chaining, and only after exhaustion does `record_operation_result` persist the terminal error to `operation_outputs`. Important: retries happen *in-process within one step execution* (the workflow doesn't re-enter); only the final outcome is checkpointed. This is the clean separation Verso wants: transient step retry is in-memory + fast; durable checkpoint is only the settled result. For async steps the `Pending` outcome (`_outcome.py:176`) runs the body via `dbos._configure_asyncio_thread_pool()` + `asyncio.to_thread` for the before/after checkpoint hooks (`_wrap`, `:187`) so a sync checkpoint write doesn't block the event loop, and it carefully rebinds the caught exception to a local (`:203`) to dodge the Python 3.12+ "cannot access free variable" bug when a lambda closes over an `except ... as exp` variable on the thread pool — a real reimplementation gotcha for any framework running checkpoint hooks across a thread boundary.

### Scheduled (cron) workflows

KNOWN, `_scheduler_decorator.py:67`. `@DBOS.scheduled(cron)` validates the crontab with `croniter` (`:72`, `second_at_beginning=True`) and runs a dedicated thread (`_scheduler.py:25`) that, each fire, starts the workflow with `SetWorkflowID` keyed on the scheduled time — so two workers racing the same cron tick produce one idempotent run (the duplicate is deduped by workflow_uuid). State lives in `workflow_schedules` (schema above: `schedule_id`, `cron_timezone`, `last_fired_at`, `automatic_backfill`). Verso's "run this agent every N minutes" needs exactly this: a cron thread + time-keyed idempotent workflow id so cron fires are exactly-once across a worker fleet.

**For Verso:** DBOS is the closest blueprint for Verso's *default* durable backend. Steal directly: (1) the **two-table schema** — `workflow_status` (one row per agent run with status enum + inputs/output/error/executor_id/recovery_attempts) plus `operation_outputs` keyed `(workflow_uuid, function_id)` as the step journal — this is a near-drop-in for Verso's Postgres checkpoint store; (2) the **transaction-piggyback** pattern for any step that touches a DB (write the checkpoint in the user's transaction → exactly-once for free); (3) the **monotonic `function_id` = call order** step identity, accepting the "same step order on replay" determinism contract (correct for a ReAct loop where you don't replay the whole body); (4) the **startup recovery thread** filtering `status='PENDING' AND executor_id AND version` with a `MAX_RECOVERY_ATTEMPTS_EXCEEDED` poison-pill. Note the recv/send Postgres-mailbox HITL is more operationally complex than Resonate's promise — Verso should prefer the promise model (below) but can reuse DBOS's `notifications` table shape if it wants topic-based fan-in.

---

## LangGraph Checkpointing — P0

### What It Is

LangGraph executes a graph as a **Pregel/BSP (Bulk Synchronous Parallel) superstep loop**: each superstep is one "tick" in which all scheduled nodes run in parallel against a set of named **channels**, and a checkpoint is saved atomically after each superstep. Durability is a swap of one argument at `graph.compile(checkpointer=...)`: `InMemorySaver` → `PostgresSaver`. The interface contract that makes that swap seamless is `BaseCheckpointSaver`. This is the dominant existing implementation of Verso's exact `durable=False`→`durable=True` toggle for an agent loop, so the interface is the prize.

### The seam interface: `BaseCheckpointSaver`

KNOWN, `libs/checkpoint/.../base/__init__.py:176`. The contract a backend must satisfy is exactly five methods (sync + async variants):

```python
class BaseCheckpointSaver(Generic[V]):
    serde: SerializerProtocol = JsonPlusSerializer()
    def get_tuple(self, config) -> CheckpointTuple | None     # :239  read latest/specific checkpoint
    def list(self, config, *, filter, before, limit) -> Iterator[CheckpointTuple]  # :253  time-travel
    def put(self, config, checkpoint, metadata, new_versions) -> RunnableConfig    # :277  save a superstep
    def put_writes(self, config, writes, task_id, task_path="") -> None            # :300  per-task pending writes
    def get_next_version(self, current, channel) -> V                              # :692  monotonic version: int+1 default
```

`get_next_version` default is `current + 1` (int) or `1` if None — but a backend may return `str`/`float` as long as it's monotonically increasing. This is the channel-version generator.

### The checkpoint payload — `Checkpoint` + `CheckpointMetadata`

KNOWN, `:92` and `:38`. This is the exact shape Verso should adapt:

```python
Checkpoint = {
  "v": 1,                      # format version
  "id": str,                   # MONOTONIC + unique (sortable first→last)
  "ts": str,                   # ISO 8601
  "channel_values": {name: value},
  "channel_versions": {name: "version-str"},      # per-channel monotonic versions
  "versions_seen": {node_id: {channel: version}}, # what each node has consumed → determines next nodes
  "updated_channels": [str] | None,
}
CheckpointMetadata = {
  "source": "input" | "loop" | "update" | "fork",
  "step": int,                 # -1 first input ckpt, 0 first loop ckpt, n after
  "parents": {ckpt_ns: ckpt_id},
  "run_id": str,
}
CheckpointTuple = (config, checkpoint, metadata, parent_config, pending_writes)
```

`versions_seen` is the BSP scheduling engine: a node is scheduled in the next superstep iff a channel it subscribes to has a `channel_versions[ch]` greater than the node's `versions_seen[node][ch]`. The config key is always `{thread_id, checkpoint_ns, checkpoint_id}` — `thread_id` is the durable identity (Verso's agent-run id).

### Postgres schema — channel-versioned blob storage (the write-amplification win)

KNOWN, verbatim `MIGRATIONS` in `checkpoint-postgres/.../postgres/base.py:43`. Four tables:

```sql
checkpoints       PK(thread_id, checkpoint_ns, checkpoint_id)
  parent_checkpoint_id TEXT, type TEXT, checkpoint JSONB, metadata JSONB
checkpoint_blobs  PK(thread_id, checkpoint_ns, channel, version)   -- ONE ROW PER (channel,version)
  type TEXT, blob BYTEA
checkpoint_writes PK(thread_id, checkpoint_ns, checkpoint_id, task_id, idx)   -- per-task pending writes
  channel TEXT, type TEXT, blob BYTEA NOT NULL, task_path TEXT DEFAULT ''
checkpoint_migrations PK(v)
```

The optimization: the `checkpoints` row stores only `channel_versions` (a JSONB map name→version), NOT the channel *values*. The values live in `checkpoint_blobs` keyed by `(channel, version)`, written with `ON CONFLICT (...channel, version) DO NOTHING` (`UPSERT_CHECKPOINT_BLOBS_SQL:131`). So **a new checkpoint only inserts blobs for channels whose version changed** — unchanged channels reuse the prior blob row. Reads reassemble via a correlated subquery joining `jsonb_each_text(checkpoint->'channel_versions')` against `checkpoint_blobs` on `channel AND version` (`SELECT_SQL:93`). This is the write-amplification-minimizing design Verso should copy if it stores large per-channel state.

`put_writes` (`checkpoint_writes`) saves each task's pending writes *within* a superstep, keyed by `task_id`. On crash-resume, tasks that already wrote their results are skipped (their writes replay from this table) so successful siblings don't re-run — the per-task granularity that makes a partially-failed superstep recoverable without full re-execution. `UPSERT_CHECKPOINT_WRITES_SQL` uses `ON CONFLICT DO UPDATE` for normal writes; `INSERT_CHECKPOINT_WRITES_SQL` uses `DO NOTHING` for idempotent ones.

### The `put` write path — primitive inlining + pipelined upserts

KNOWN, `postgres/__init__.py:263`. The actual `put` is sharper than "store versions, store blobs": it **inlines primitive channel values** (`None | str | int | float | bool`) directly into the `checkpoints.checkpoint` JSONB and only sends *complex* values (lists, dicts, objects) to `checkpoint_blobs` (`:312-319`). `_DeltaSnapshot` channels store `True` inline as a marker and the snapshot in blobs. Then, only for channels in `new_versions` that are *also* blob values, it `executemany(UPSERT_CHECKPOINT_BLOBS_SQL, ...)` and `execute(UPSERT_CHECKPOINTS_SQL, ...)` — **inside a `_cursor(pipeline=True)`** (`:321`), so the blob upserts and the checkpoint upsert are one pipelined Postgres round-trip, not N. `get_tuple` (`:192`) runs the correlated `SELECT_SQL` (joining `channel_versions` JSONB against `checkpoint_blobs`), then `_load_checkpoint_tuple` reassembles `channel_values` by merging inlined primitives with deserialized blobs. The two optimizations together — inline small/primitive values, blob only large values, pipeline the writes — are why LangGraph's per-superstep write cost stays low even with many channels. Verso should inline small step outputs in the run/step row and blob only large outputs (tool results, retrieved docs).

### Durability modes (latency vs durability axis)

KNOWN, `types.py:87`: `Durability = Literal["sync", "async", "exit"]`. `"sync"` = persist before next superstep starts (max durability); `"async"` = persist concurrently with next superstep (the default tradeoff); `"exit"` = persist only when the graph exits (fastest, least durable — and `_loop.py:459` skips `put_writes` entirely when `durability=="exit"`).

### HITL: `interrupt()` — counter-indexed resume

KNOWN, `types.py:811`. The modern primitive (replaces static `interrupt_before/after` compile flags). Inside a node, `interrupt(value)`:

```python
scratchpad = conf[CONFIG_KEY_SCRATCHPAD]
idx = scratchpad.interrupt_counter()          # per-task, per-node call counter
if scratchpad.resume and idx < len(scratchpad.resume):
    return scratchpad.resume[idx]             # already have a resume value for THIS interrupt
v = scratchpad.get_null_resume(True)
if v is not MISSING:
    scratchpad.resume.append(v); return v
raise GraphInterrupt(Interrupt(value=value, ns=conf[CONFIG_KEY_CHECKPOINT_NS], ...))   # first time → halt
```

Critical semantic: on resume, **the entire node re-executes from the top**; multiple `interrupt()` calls in one node are matched to resume values **by call-order index** into `scratchpad.resume[]`. Client resumes with `Command(resume=value)`. The `GraphInterrupt` propagates up, the loop checkpoints state, and the run returns the surfaced value. (Re-execution means everything before the `interrupt()` in that node must be idempotent — the same determinism caveat as Temporal's wait_condition, scoped to the node.)

| Constant | Value | Source |
|---|---|---|
| checkpoint format `v` | 1 | `base/__init__.py:95` |
| default version step | `current + 1` (int) | `:692` |
| `step` first input / first loop | -1 / 0 | metadata `:49` |
| durability default | `"async"` | (compile default) |
| delta-channel max supersteps before forced snapshot | 5000 | metadata `:79` (`LANGGRAPH_DELTA_MAX_SUPERSTEPS_SINCE_SNAPSHOT`) |
| blob upsert | `ON CONFLICT (channel,version) DO NOTHING` | `:131` |

### The Pregel tick — how `versions_seen` schedules the next superstep

KNOWN, `pregel/_algo.py:232` (`apply_writes`) + `_loop.py`. The executor's core algorithm. After a superstep's tasks run, `apply_writes` does three things: (1) sorts tasks by `task_path[:3]` for deterministic update order; (2) for each task, updates `versions_seen[task.name][chan] = channel_versions[chan]` for every channel the task was triggered by — recording "this node has now consumed this channel at this version"; (3) bumps `channel_versions[chan]` to a new version for every channel written this step (via `get_next_version`, default `current+1`). The next superstep's task selection (`prepare_next_tasks`) then schedules node N iff some channel it subscribes to has `channel_versions[chan] > versions_seen[N][chan]` — i.e. a channel it cares about was written since it last ran. **This is the entire BSP scheduling logic, and it's what makes resume work**: on crash-recovery you reload `channel_versions` and `versions_seen` from the checkpoint, and the exact same set of nodes is scheduled as would have been — no node re-runs unless its input channel genuinely advanced.

### The pending-writes resume algorithm (partial-superstep recovery)

KNOWN, `_loop.py:417`. When a superstep is interrupted mid-flight (some parallel nodes succeeded, some didn't), the loop reloads `checkpoint_pending_writes` (from `checkpoint_writes`) and, per task, separates "writes already recorded for this task_id" from the rest (`:423-428`):

```python
self.checkpoint_pending_writes = [w for w in self.checkpoint_pending_writes ...]   # keep only un-replayed
# writes for an already-completed task_id are applied from the table, NOT re-run
self.checkpoint_pending_writes.extend((task_id, c, v) for c, v in writes)   # accumulate as tasks complete
if self.durability != "exit" and self.checkpointer_put_writes is not None:
    # persist each task's writes immediately (write-before-advance at TASK granularity)
    self.checkpointer.put_writes(config, writes, task_id, task_path)
```

So a superstep with 5 parallel nodes where node 3 crashed: on resume, nodes 1/2/4/5 replay their writes from `checkpoint_writes` (instant), only node 3 re-runs. This per-task write persistence (vs per-superstep) is the difference between "re-run the whole superstep" and "re-run only the failed task." Verso needs this if it ever runs tool calls in parallel within one durable step.

### Static interrupts (the older HITL primitive, still supported)

KNOWN. Pre-`interrupt()`, HITL was compile-time: `graph.compile(interrupt_before=["tools"], interrupt_after=["agent"])` — the loop halts before/after the named node, checkpoints, and returns; the client resumes by re-invoking with `None` (continue) or `Command(update=...)` (modify state then continue). `should_interrupt` (`_algo.py:163`) checks `version > versions_seen[INTERRUPT].get(chan, null_version)` — i.e. interrupt fires only on channels updated since the last interrupt. The evolution to dynamic `interrupt()` (mid-node, counter-indexed) is the lesson: Verso should support both a *static* "pause before tool execution" gate (cheap, declarative) and a *dynamic* "pause right here for this specific input" call.

### Serialization & encryption (`JsonPlusSerializer` + `EncryptedSerializer`)

KNOWN, `serde/jsonplus.py`, `serde/encrypted.py`. The default `serde` is `JsonPlusSerializer` — `dumps_typed(obj) -> (type_str, bytes)` / `loads_typed` over **ormsgpack** with custom extension types for LangChain objects, datetimes, enums, etc. (pre-msgpack JSON checkpoints stay resumable, `:64`). Crucially, channel values are stored as typed `(type, blob)` pairs in `checkpoint_blobs` — the `type` column is this `type_str`, so a blob's decoder is self-describing. For encryption, `EncryptedSerializer` wraps any serde: `dumps_typed` encrypts to `("aes", nonce + tag + ciphertext)` (`:69`, `from_pycryptodome_aes`), `loads_typed` asserts `ciphername == "aes"` and decrypts. **This is the model for Verso's encrypted-at-rest checkpoints**: a serializer-wrapper that AES-encrypts each blob with a nonce, transparently to the storage layer — agent state (which may hold secrets) is never plaintext in Postgres. The msgpack extension-type registry (`jsonplus.py:295`) is the concrete "serialize arbitrary Python objects" answer: ext codes `EXT_CONSTRUCTOR_SINGLE_ARG=0`, `EXT_CONSTRUCTOR_POS_ARGS=1`, `EXT_CONSTRUCTOR_KW_ARGS=2`, `EXT_METHOD_SINGLE_ARG=3`, `EXT_PYDANTIC_V1=4`, `EXT_PYDANTIC_V2=5`, `EXT_NUMPY_ARRAY=6` — each object is encoded as `(ext_code, module, name, payload)` so it reconstructs by calling the right constructor/method on deserialize, with a security allowlist (`:87`) of permitted `(module, name, method)` triples to prevent arbitrary-code-execution on load. Verso's checkpoint serializer needs exactly this: Pydantic-model-aware (agent state and tool I/O are usually Pydantic), with a construction allowlist so a malicious checkpoint can't RCE on resume.

### Cache, thread/run deletion (lifecycle)

KNOWN, `cache/base/__init__.py:15`, `base/__init__.py:320`. A separate `BaseCache` layer (`get(keys) -> {FullKey: value}`, `set(pairs: {key: (value, ttl_or_None)})`) memoizes node results across runs with a TTL — distinct from the checkpointer (which persists run state). `delete_thread(thread_id)` (`:320`) and `delete_for_runs(run_ids)` (`:331`) are the GC API — delete all checkpoints + writes for a thread/run. Verso needs both: a TTL'd result cache (don't re-run an expensive deterministic tool whose inputs repeat) layered above the durable checkpoint store, plus explicit `delete_run(run_id)` for retention/GDPR.

**For Verso:** This is the single most important interface to internalize because LangGraph already won the "one flag" argument. Steal: (1) the **`BaseCheckpointSaver` 5-method contract** (`get_tuple`/`list`/`put`/`put_writes`/`get_next_version`) as the literal shape of Verso's pluggable checkpoint backend — InMemory for `durable=False`, Postgres for `durable=True`, identical code path above; (2) the **`Checkpoint` payload shape** (`id`, `channel_versions`, `versions_seen`) — `versions_seen` is how you decide what runs next on resume without re-running everything; (3) the **channel-versioned blob storage** (store versions in the checkpoint row, values in a `(channel,version)`-keyed side table with `ON CONFLICT DO NOTHING`) to kill write amplification; (4) the **three durability modes** as Verso's latency knob; (5) `interrupt()`'s **counter-indexed resume** — but note the "re-execute the whole node" cost; Verso's per-step memoization (DBOS/Inngest model) avoids that by replaying only completed steps, which is strictly better for an LLM ReAct loop where re-calling the model is expensive.

---

## Restate — P0

### What It Is

A Rust durable-execution engine with a **journal-per-invocation** model and no Commands/Events split. The server is a single binary; the actual state machine lives in a Rust `shared-core` VM that is compiled into every SDK (the Python SDK loads it as a PyO3 extension, `restate.vm`). The SDK code is thin: every durable operation calls a `sys_*` method that appends a **journal entry** in the VM and returns an integer **handle**; a `do_progress` driver loop either resolves the handle from the replayed journal or suspends the invocation. On the server side the journal is persisted to the **Bifrost** segmented log (replicated WAL → tiered object storage); RocksDB state is derived from the log and is fully recoverable.

### The journal-handle model (the replay substrate)

KNOWN, `vm.py` + `server_context.py`. There is no per-type seq and no content hash — **journal position is the step identity**. The VM is the single source of truth; the SDK never decides what to replay. Every durable call returns a handle int:

```python
# vm.py — the durable-operation surface, all return an int handle into the journal
def sys_run(self, name: str) -> int                      # :398  a side-effecting step
def sys_sleep(self, millis, name=None) -> int            # :363  durable timer
def sys_get_state(self, name) -> int / sys_set_state     # :321  K/V state (atomic w/ journal)
def sys_awakeable(self) -> tuple[str, int]               # :404  (id, handle) — external resolvable
def sys_get_promise(self, name) -> int                   # :429  named durable promise (workflow)
def sys_complete_promise_success(self, name, value)      # :437
def sys_call / sys_send                                  # :367  child invocation (req-resp / fire-forget)
def propose_run_completion_success(self, handle, output) # :423  record a run's result into the journal
```

`run_typed(name, action, options)` (`server_context.py:762`) does: `handle = self.vm.sys_run(name)` → stash the coroutine in `self.run_coros_to_execute[handle]` → return a future bound to that handle. The action does NOT run immediately. It runs only when the driver decides it must (next).

### `do_progress` — the driver loop (replay vs execute vs suspend)

KNOWN, `server_context.py:531`. This is the heart. Awaiting any durable future enters `create_poll_or_cancel_coroutine`, which loops calling `vm.do_progress(...)`. The VM returns one of four verdicts:

```python
do_progress_response = self.vm.do_progress(unresolved_future)
if DoProgressAnyCompleted:        return                      # journal already has the result → replay, no execution
if DoProgressExecuteRun:          # this run handle has NO journal entry yet → actually execute the user fn now
    fn = self.run_coros_to_execute[resp.handle]; asyncio.create_task(wrapper(fn))   # then it calls propose_run_completion_*
if DoProgressWaitExternalProgress: chunk = await self.receive()  # block on HTTP body frames (server pushes completions)
    self.vm.notify_input(body)                                   # feed completions back into the VM
if DoProgressCancelSignalReceived: raise TerminalError("cancelled", 409)
if Suspended:                     raise SuspendedException()   # nothing to do, no input → suspend invocation, free the worker
```

So replay is implicit: on a re-invocation the server replays the journal into the VM up front; every `sys_run` handle that already has a recorded completion returns `DoProgressAnyCompleted` (the user fn is never re-entered); the first handle WITHOUT a completion returns `DoProgressExecuteRun`. **This is the "checkpoint as a side-effect of execution" pattern** — `propose_run_completion_success(handle, output)` writes the result into the journal atomically; K/V `sys_set_state` writes are part of the same journaled progress, so state and execution-progress commit together.

### `is_replaying` & suspension

`update_restate_context_is_replaying(self.vm)` is called after *every* `sys_*` op (e.g. `:783`, `:802`) — the VM tells the SDK whether it's still draining the journal or has caught up to live execution, which gates side-effect logging. The defining property vs Temporal: when there is nothing to do and no input pending, the invocation **suspends** (`SuspendedException`) and the HTTP request returns — the worker is freed, and the server re-invokes later with the journal replayed. There is no resident worker holding the workflow in memory (unlike Temporal's sticky cache).

### HITL: Durable Promises + Awakeables

Two primitives, both first-class external-resolvable futures:
- **Awakeable** (`ctx.awakeable()` → `(id, future)`): `sys_awakeable` returns an id string the handler passes to an external system; the external system resolves via `resolve_awakeable(id, value)` / `reject_awakeable(id, msg, code=500)`. Transport-agnostic — the resolver just needs the id.
- **Durable Promise** (workflow-scoped, `ctx.promise(name)`, `WorkflowContext` only): `sys_get_promise(name)` → handle; resolved by `sys_complete_promise_success(name, value)` (`:437`) or `..._failure(name, Failure)` (`:441`). Named (not id-based), so any handler/external caller that knows the workflow key + promise name can resolve it. `ServerDurablePromise.resolve/reject` (`:226-247`) is the in-VM path. This is the cleaner model for "agent yields, human approves later" — exactly Resonate's design (Restate and Resonate share this lineage).

### Protocol & discovery

Service-protocol is content-negotiated: discovery returns `application/vnd.restate.endpointmanifest.v{2,3,4}+json` (`server.py:69`); the SDK advertises `min/maxProtocolVersion` (`discovery.py:157`). The wire between SDK and server is the journal-entry protobuf stream over a single HTTP request (bidirectional via chunked body frames — the `DoProgressWaitExternalProgress` path reads `chunk["body"]` and feeds `vm.notify_input`).

### The bidirectional ASGI frame protocol (the streaming wire)

KNOWN, `server_context.py:390-460`. The SDK↔server contract over a single HTTP request is a bidirectional stream of body frames. Outbound: `take_and_send_output()` drains `self.vm.take_output()` (journal entries the VM wants to emit) and `await self.send({"type": "http.response.body", "body": chunk, "more_body": True})` — streaming journal updates to the server as they're produced. Inbound: the `DoProgressWaitExternalProgress` path does `chunk = await self.receive()`, extracts `chunk["body"]`, and `self.vm.notify_input(body)` to feed server-sent completions back into the VM; `more_body=False` → `notify_input_closed()`. On terminal: `sys_write_output_success/failure(out)` + `sys_end()` then drain remaining output. This is exactly the vLLM/llama.cpp streaming concern from `infra-serving.md` (cross-ref) but for journal frames not tokens: a long-poll-style bidirectional body stream where the SDK pushes journal entries and the server pushes completions, all within one HTTP request that stays open until the invocation suspends or completes. Verso's durable-step streaming (if it streams intermediate journal state to a coordinator) needs the same frame-multiplex-over-one-connection pattern.

**INFERRED (blog "building a modern durable execution engine from first principles"):** 3ms median step latency, ~10ms under load, 94K actions/sec; Bifrost = Delos/LogDevice-style segmented log with embedded replicated log tier → object-storage tier; RocksDB state is ephemeral/derived.

| Fact | Value | Source |
|---|---|---|
| step identity | journal position (VM handle) | `vm.py` |
| replay verdicts | AnyCompleted / ExecuteRun / WaitExternalProgress / CancelSignal | `server_context.py:541` |
| awakeable reject default code | 500 | `context.py:557` |
| promise reject default code | 500 | `context.py:635` |
| discovery manifest versions | v2/v3/v4 | `server.py:72` |
| median step latency / throughput | 3ms / 94K ops/s | blog (INFERRED) |

### K/V state — atomic with execution progress

KNOWN, `vm.py:321`, `server_context.py:617`. Restate's `ObjectContext`/`WorkflowContext` expose durable key-value state: `ctx.get(name)` → `sys_get_state(name)` (a journaled read — returns a handle, the value replays on re-invocation), `ctx.set(name, value)` → `sys_set_state(name, bytes)`, `ctx.clear(name)` / `clear_all`. The defining property: a `set_state` is journaled in the **same progress step** as the execution that produced it, so state and execution-position commit atomically — there's no window where the agent advanced but its state write was lost. `update_restate_context_is_replaying(self.vm)` after each (`:618`, `:633`) keeps the SDK's replay flag synced. This is the K/V-as-side-effect-of-execution model: Verso's agent scratchpad (accumulated context, tool-result cache) can be durable state that commits with each step, not a separate save.

### Run retry with backoff override

KNOWN, `create_run_coroutine` (`server_context.py:664`). When a `ctx.run`/`run_typed` action raises: a `TerminalError` → `propose_run_completion_failure` (permanent, no retry); a `RetryableError` → `propose_run_completion_transient_with_delay_override(handle, failure, ...)` carrying `max_attempts`, `max_duration`, `initial_retry_interval`, `max_retry_interval`, `retry_interval_factor` and the measured `attempt_duration` (`:696`). The VM (server-side) computes the next retry delay from this policy — so retry of a side-effecting step is server-managed and journaled, like Temporal's activity retry but expressed per-`run` call. Sync actions run in `loop.run_in_executor` (`:684`) so a blocking step doesn't stall the event loop.

### Service calls vs sends + awakeable resolution

KNOWN, `vm.py:367`, `server_context.py:872`. Two child-invocation shapes, both journaled: `ctx.service_call(handler, arg)` → `sys_call(service, handler, parameter, key, idempotency_key, headers)` (request-response — await the result); `ctx.service_send(handler, arg, delay)` → `sys_send(..., delay, idempotency_key, ...)` (fire-and-forget, optionally delayed). The `idempotency_key` on both means a retried invocation doesn't double-execute the target. `workflow_call`/`generic_call` (`:930`/`:953`) target a specific workflow key. Awakeable resolution from elsewhere: `ctx.resolve_awakeable(id, value)` → `sys_resolve_awakeable(id, bytes)` (`:1015`), `reject_awakeable(id, msg, code=500)` — the same id-based external-resolve as a Durable Promise but ephemeral (per-invocation, not workflow-scoped). The split — awakeable (transient, id-based) vs promise (workflow-scoped, name-based) — is worth Verso copying: a short-lived "wait for this one callback" (awakeable) vs a durable named approval gate (promise).

### Virtual Objects — keyed single-writer concurrency

KNOWN, `object.py:38`, `workflow.py:43`. The three context types map to three concurrency models: `ServiceContext` (stateless, fully concurrent), `ObjectContext`/`VirtualObject` (keyed — one logical object per `ctx.key()`, with `kind="exclusive"` handlers **serialized per key** by the server and `kind="shared"` handlers allowed concurrent read-only access), `WorkflowContext`/`Workflow` (one execution per key, `kind="workflow"` is the main handler + `kind="shared"` signal handlers). The exclusive-per-key guarantee means **all mutations to one object's durable K/V state are serialized server-side — no locks in user code, no races**. This is the actor model (like a Cloudflare Durable Object) baked into the durable runtime: a per-key single-writer. For Verso, the lesson is that durable agent state should be keyed and single-writer per agent run — two concurrent activations of the same run id must be serialized (DBOS does this via `owner_xid`/`SELECT FOR UPDATE`; Restate does it by routing all invocations for a key through one ordered processor). Verso must pick one (Postgres row-lock per run id is the simplest) to prevent two workers double-driving one agent.

**For Verso:** Restate is the architecturally cleanest model for Verso and the one to imitate if Verso wants suspend-and-free-the-worker semantics. Steal: (1) the **journal-position-as-step-identity** + a single **driver loop** that, per await, asks the journal "do I have this result already (replay), or must I execute, or must I suspend?" — this is simpler than Temporal's seq-matching and DBOS's function_id, and it naturally handles a dynamic ReAct loop because the journal grows as the loop runs; (2) **checkpoint-as-side-effect**: `propose_run_completion` writes the step result and any K/V state in one journaled step — no separate "save checkpoint" call; (3) the **four-verdict `do_progress`** as the literal control-flow of Verso's durable executor (`AnyCompleted`→continue, `ExecuteRun`→run the LLM/tool now, `WaitExternalProgress`→block for HITL input, `Suspended`→persist & release); (4) the **named Durable Promise / Awakeable** HITL primitive — pick this over DBOS recv/send. The cost: the journal/VM is the hard part to build (Restate ships it as compiled Rust). Verso's pure-Python equivalent is the DBOS function_id journal + an explicit "is this handle resolved?" check, accepting that it won't suspend-and-free the worker as cheaply.

---

## Inngest — P1

### What It Is

A serverless durable-workflow platform whose SDK protocol is one of the most precisely specified in the space. The execution model is **stateless request/response with memoization**: the Inngest server invokes your HTTP function on every step; the SDK runs the function from the top each time, but **memoizes already-completed steps** so they return instantly, and the function runs forward until it hits the first *new* step — which it executes (or emits as an opcode) and returns to the server via HTTP 206. There are no resident processes; durability comes from the server persisting each step result and re-driving the function.

### Step identity: SHA-1 of the human-readable id + `:n` loop counter

KNOWN. Step IDs are content-addressed by name, not position. `hash_step_id` (`transforms.py:30`):

```python
def hash_step_id(step_id: str) -> str:
    return hashlib.sha1(step_id.encode("utf-8")).hexdigest()
```

Reused ids (e.g. a loop calling `step.run("fetch", ...)` repeatedly) are disambiguated by a per-id counter BEFORE hashing (`base.py:111`):

```python
def _parse_step_id(self, step_id: str) -> ParsedStepID:
    pre_hashed = step_id
    id_count = self._step_id_counter.increment(step_id)   # thread-safe dict, mutex
    if id_count > 1:
        pre_hashed = f"{step_id}:{id_count - 1}"            # "fetch", "fetch:1", "fetch:2", ...
    return ParsedStepID(hashed=transforms.hash_step_id(pre_hashed), user_facing=step_id, index=...)
```

So identity = `sha1(name)` for the first use, `sha1(f"{name}:{n}")` for the nth (n≥1). This is **the most portable step-identity scheme in the cluster** — refactor-tolerant (renaming reorders nothing as long as the name string is stable) and loop-safe.

### Memoization-via-Call-Request (the server-side half of the contract)

KNOWN. Every invocation the server POSTs a `ServerRequest` (`execution_request.py:8`):

```python
class ServerRequest:        ctx: ServerRequestCtx;  event/events;  steps: dict[str, object]   # ← the memo map: {hashed_id: output}
class ServerRequestCtx:      attempt: int;  disable_immediate_execution: bool;  max_attempts: int | None
```

`steps` is the memoized-output map keyed by hashed step id. The SDK loads it into a `StepMemos` (`base.py:41`) — a dict it **pops from** as it replays. `report_step` (`execution_lib/v0.py:56`) is the per-step gate:

```python
memo = self._memos.pop(step.info.id)            # pop by hashed id
if self._memos.size == 0: await before_execution()   # all remaining code is "new"
if not EmptySentinel(memo):                     # CACHE HIT
    if memo.error: step.error = StepError(...)
    elif memo.data: step.output = memo.data
    return step                                 # → step.run() returns cached output instantly, no execution
...                                             # CACHE MISS → fall through to execute / emit opcode
if step_info.op == STEP_RUN: return step        # run the handler
raise ResponseInterrupt(StepResponse(step=step_info))   # non-run opcodes (sleep, wait) emit immediately
```

On a cache miss in `step.run`, the handler executes, then **`raise ResponseInterrupt(StepResponse(output, step_info))`** (`step_async.py:205`) — a `BaseException` (so user `except Exception` can't swallow it) that unwinds to the SDK boundary, which serializes it as the step result and returns it. The HTTP response is **206 Partial Content** (`comm_lib/models.py:184`, `http.HTTPStatus.PARTIAL_CONTENT`) carrying the step's output; the server persists it, adds it to the `steps` memo map, and re-POSTs to advance to the next step. A 200 means the function fully completed; 500 + `NO_RETRY` header gates retry.

### Opcode taxonomy

KNOWN, `server_lib/consts.py:77`. The complete durable-action vocabulary:

```python
class Opcode(enum.Enum):
    STEP_RUN = "StepRun"           # a memoized sync side-effect
    SLEEP = "Sleep"                # duration string ("10s") or ISO date (sleep_until)
    WAIT_FOR_EVENT = "WaitForEvent"# {if: CEL filter, timeout: str} — HITL/event join
    INVOKE = "InvokeFunction"      # call another durable function, await result
    AI_GATEWAY = "AIGateway"       # step.ai.infer — proxied LLM call as a durable step
    PLANNED = "StepPlanned"        # parallel-mode: declare a step without running it (server schedules)
    STEP_ERROR = "StepError"       # retryable step failure
    STEP_FAILED = "StepFailed"     # terminal (attempt+1 >= max_attempts)
```

`WaitForEvent` opts (`base.py:207`): `{if: CEL filter expression, timeout: duration str}`. Parallel handling: when `step.parallel([...])` is active, a `STEP_RUN` is rewritten to `PLANNED` and emitted without running, so the server can fan-out (`v0.py:86`). `max_attempts` retry decision is made SDK-side: `STEP_FAILED` when `attempt + 1 >= max_attempts`, else `STEP_ERROR` (`step_async.py:217`).

| Fact | Value | Source |
|---|---|---|
| step hash | `sha1(name).hexdigest()` (hex) | `transforms.py:30` |
| loop disambiguation | `f"{name}:{n-1}"` before hash | `base.py:120` |
| step-result HTTP status | 206 Partial Content | `comm_lib/models.py:184` |
| done / fatal status | 200 / 500 (+`NO_RETRY`) | `comm_lib/models.py` |
| memo map field | `steps: dict[hashed_id, output]` | `execution_request.py:12` |
| `ResponseInterrupt` base | `BaseException` (un-swallowable) | `base.py:161` |

### The non-run opcodes — exact signatures

KNOWN, `step_async.py`. Unlike `step.run` (which executes the handler in-SDK then returns the result via 206), the async opcodes are emitted to the server which performs the wait/call and re-invokes with the result:
- `wait_for_event(step_id, *, event, if_exp=None, timeout)` (`:366`) → `WAIT_FOR_EVENT` opcode with `opts={if: CEL expr, timeout: duration_str}`. Returns the matched `Event | None` (None = timed out). The HITL/event-join primitive.
- `sleep(step_id, duration)` / `sleep_until(step_id, datetime)` (`:310`) → `SLEEP` opcode, duration as a string (`"10s"`) or ISO date. The SDK returns nothing; the server schedules the wakeup and re-invokes after.
- `invoke(step_id, *, function, data, timeout)` (`:45`) → `INVOKE` opcode — call another durable function and await its result.
- `ai.infer(...)` → `AI_GATEWAY` opcode (`:465`) with `{auth_key, body, format, headers, url, type:"step.ai.infer"}` — a durable, memoized LLM call proxied through Inngest's AI gateway. **This is the directly-Verso-relevant opcode**: the LLM call is a first-class durable step type, not a generic `step.run`.

### `ReportedStep` — the async-context-manager gate + nested-step prevention

KNOWN, `execution_lib/models.py:127`. Each step runs inside `async with await self._execution.report_step(step_info) as step:`. `ReportedStep.__aenter__` (`:142`) checks the `_in_step` contextvar — **if already inside a step, it raises `NestedStepInterrupt`** (`step.run` inside another `step.run` is forbidden, because nested memoization would corrupt step ordering). `release()` (`:155`) resolves the `_release_signal` future — the synchronization point that lets the execution coordinator order concurrent `step()` calls deterministically (it sets the result then awaits it, yielding control). `on_done` registers a callback for when the step's body finishes. This context-manager-per-step pattern (enter → check-not-nested → release-for-ordering → run body → exit) is the clean structural primitive Verso should adopt for its step boundary: a contextmanager that prevents accidental step nesting and provides the ordering sync point for parallel steps.

### Parallel steps → PLANNED, and disable_immediate_execution

KNOWN, `execution_lib/v0.py:86`. When steps run in parallel (`step.parallel([...])`, tracked via the `in_parallel` contextvar), `report_step` rewrites a `STEP_RUN` opcode to `PLANNED` and **raises `ResponseInterrupt` without running the handler** — declaring the step to the server, which then fans out and schedules each planned step as a separate invocation. The `disable_immediate_execution` flag in the request ctx (`:95`) forces a single new `step.run` after parallel steps to also be PLANNED first (so the server can persist the parallel results before the next sequential step runs). The `ParallelMode.RACE` opt (`base.py:232`) makes a parallel group resolve on the first completion rather than all. This planned/fan-out mechanism is how a stateless serverless SDK does parallelism deterministically — Verso's parallel tool-call execution needs the equivalent "declare all, then resolve" two-phase model.

### Function config — the flow-control vocabulary

KNOWN, `server_lib/registration.py:95`. A function's `FunctionConfig` declares (sent to the server at registration): `concurrency: list[Concurrency]` (multiple keyed concurrency limits, e.g. per-user), `throttle` (smooth rate), `rate_limit` (hard cap), `debounce` (collapse rapid triggers), `batch_events: Batch` (batch N events into one run), `idempotency: str` (CEL expr → dedupe key), `priority: Priority` (CEL expr → run priority), `retries: Retries`, `triggers: [TriggerEvent(event, expression=CEL) | TriggerCron(cron)]`. This is a richer flow-control surface than DBOS's queue (which has concurrency + rate limit but not debounce/throttle/batch/CEL-idempotency). For a Verso agent triggered by events (e.g. "run the triage agent on every `ticket.created`"), this is the exact control vocabulary: dedupe duplicate triggers, batch bursts, cap concurrency per tenant, prioritize by a CEL expression on the event.

### Connect mode — the persistent-worker alternative to serverless re-POST

KNOWN, `connect/_internal/execution_handler.py`. Beyond the stateless HTTP re-POST model, Inngest supports **connect** — a persistent WebSocket from worker to gateway. The worker leases work and must **renew the lease periodically** (`_lease_extender` task, `:128`; `_handle_lease_extend_ack`, `:380`) — a dead worker's lease expires and the run is redispatched. This is the resident-worker model (like DBOS/Restate) layered on the same step protocol, avoiding the per-step HTTP round-trip for long-running functions. Lesson: Verso should support both a stateless mode (re-invoke per step, serverless-friendly) and a leased resident mode (persistent worker with lease-renewal heartbeat for crash detection) over one step-memoization protocol.

**For Verso:** Inngest's step-identity scheme is the one Verso should adopt for its durable event log: **`sha1(human_name)` + `:n` loop counter**, content-addressed, refactor-tolerant — strictly better than DBOS's order-based `function_id` or Temporal's order-sensitive seq for a ReAct loop where the user names steps. Steal: (1) the **`steps: dict[hashed_id, output]` memo map** as the wire contract — Verso's durable backend returns this map, the executor pops from it on replay, runs forward to the first miss; (2) the **`ResponseInterrupt(BaseException)`** pattern to unwind a completed step result to the framework boundary without user code swallowing it; (3) the **opcode taxonomy** as Verso's durable-action enum — note `AI_GATEWAY` is exactly a durable LLM call, which is Verso's single most important step type, and `WAIT_FOR_EVENT` with a CEL filter + timeout is the HITL primitive. The one caveat: the stateless re-POST model means the *whole function re-runs from the top each step* (memoized steps are fast but the orchestration code between them re-executes) — fine for serverless, but for a long-running in-process Verso agent, prefer keeping the function resident (DBOS/Restate style) and only re-run on actual crash recovery.

---

## Hatchet — P1

### What It Is

A Go/PostgreSQL orchestration engine (MIT) with the clearest Python API for the four durable primitives Verso needs. Durable tasks build their shape at runtime (vs DAGs which predeclare it statically), backed by a Postgres **durable event log** with explicit replay branching. The four primitives — `aio_sleep_for`, `aio_wait_for`/`aio_wait_for_event`, `memo`, `run_child` — each append a node to that log.

### Step identity: a monotonic `_wait_index` → idempotency key

KNOWN, `context.py:744`. `DurableContext` keeps `self._wait_index = 0`, incremented per durable op (`:809`). `aio_sleep_for` builds a signal key from the index (`:891`):

```python
wait_index = self._increment_wait_index()
res = await self.aio_wait_for(
    f"sleep:{timedelta_to_expr(duration)}-{wait_index}",   # signal_key = "sleep:10s-0", "sleep:5m-1", ...
    SleepCondition(duration=duration), label=label)
```

The signal_key is the per-task durable identity. The engine independently computes an **`idempotency_key BYTEA`** server-side from "type of event + wait-for conditions or trigger payload + options" (schema comment, `v1-core.sql:2353`) — this is the non-determinism detector: on replay, if the SDK emits a different wait condition at the same node, the idempotency key mismatches → non-determinism error.

### The durable event log (the journal)

KNOWN, `sql/schema/v1-core.sql:2301`. Two tables form the journal:

```sql
v1_durable_event_log_file   PK(durable_task_id, durable_task_inserted_at)   -- one row per task; the sequence counter
  latest_invocation_count INT
  latest_node_id BIGINT       -- monotonic, starts at 0, +1 per entry; "writers must LOCK this row to increment"
  latest_branch_id BIGINT     -- branches = different execution paths on replay

v1_durable_event_log_entry  PK(durable_task_id, durable_task_inserted_at, branch_id, node_id)
  kind ENUM('RUN','WAIT_FOR','MEMO')     -- the three durable op kinds
  node_id BIGINT              -- the sequence position (= step identity in the log)
  branch_id BIGINT            -- which replay path this node belongs to
  idempotency_key BYTEA       -- non-determinism guard (see above)
  is_satisfied BOOL, satisfied_at TIMESTAMPTZ   -- for WAIT_FOR: has the condition fired?
  child_task_external_id UUID -- RUN entries: the spawned child
  wait_data JSONB, result_payload_external_id UUID
```

Replay reads `WHERE durable_task_id=? AND node_id=?` for each node as the task re-emits ops; the `branch_id` mechanism lets a single durable task have *multiple* execution paths recorded (a branch point is created when replay diverges, table `v1_durable_event_log_branch_point`). The `kind` enum maps 1:1 to the API: `RUN`=`run_child`, `WAIT_FOR`=`aio_wait_for`/sleep/event, `MEMO`=`memo`.

### HITL & "or groups": wait for sleep OR event

KNOWN. `aio_wait_for(signal_key, *conditions, label)` (`:817`) takes a varargs of `SleepCondition | UserEventCondition | OrGroup`. Conditions are flattened (`flatten_conditions`) and sent as a proto to the engine via the **durable event listener** (a gRPC stream): `listener.send_event(durable_task_external_id=self.step_run_id, invocation_count=self.invocation_count, event=WaitForEvent(wait_for_conditions=..., label=...))`. The SDK then `await listener.wait_for_callback(...)` — which blocks the coroutine until the engine resolves the match server-side. Crucially this is wrapped in `aio_durable_eviction_wait(...)`: while waiting, the worker slot is **released** (durable eviction), so a long wait holds zero compute. An `OrGroup` lets the task wait for "sleep 5m OR event X" — whichever match fires first satisfies the node. `aio_wait_for_event(key, expression, payload_validator, scope, lookback_window)` is the typed event-wait with a **CEL filter** (`expression`) and a `lookback_window` (match events that arrived before the wait started).

| Fact | Value | Source |
|---|---|---|
| step identity | `_wait_index` monotonic, signal_key `"sleep:<expr>-<idx>"` | `context.py:891` |
| node_id | monotonic from 0, +1/entry, row-locked | `v1-core.sql:2315` |
| log kinds | RUN / WAIT_FOR / MEMO | `v1-core.sql:2324` |
| non-determinism guard | `idempotency_key BYTEA` (type+conditions+options) | `v1-core.sql:2353` |
| worker behavior on wait | slot released (durable eviction) | `context.py:861` |
| event filter | CEL expression + lookback_window | `context.py:938` |

### The durable-event listener — bidirectional gRPC stream + eviction tiers

KNOWN, `clients/listeners/durable_event_listener.py:148`. The wait machinery is a long-lived bidirectional gRPC stream `StreamStreamCall[DurableTaskRequest, DurableTaskResponse]` (`:163`) to the engine's `V1Dispatcher`. `send_event(durable_task_external_id, invocation_count, event)` pushes a `WaitForEvent` (or sleep) onto the stream; a background reader (`:319` `async for response in self._stream`) demuxes incoming `DurableTaskResponse`s by `(external_id, node_id, branch_id, invocation_count)` and resolves the matching waiter; a `ConnectionResetError` on stream disconnect (`:327`) triggers reconnect-and-replay. Two implementations gate on engine version (`context.py:798` `_supports_durable_eviction`): the modern `DurableEventListener` (worker slot released during the wait — durable eviction) vs the legacy `aio_wait_for_pre_eviction` (`pre_eviction.py:26`) which `register_durable_event(request)` then `await result(task_id, signal_key)` while *holding* the slot. The `invocation_count` is the replay generation — it increments each time the durable task is re-invoked, so a stale response from a prior invocation is ignored. Verso's HITL-over-a-stream needs this: a reconnectable bidirectional channel keyed by (run, node, invocation) so a resume delivered during a reconnect isn't lost or double-applied.

### DAG mode vs durable-task mode (the dual executor)

KNOWN, `runnables/workflow.py:1337` (`@task`) vs `:1442` (`@durable_task`). Two ways to define work, on one engine/log:
- **`@workflow.task(name, parents=[...], wait_for=[Condition|OrGroup], skip_if=[...], cancel_if=[...], retries=0, execution_timeout=60s, schedule_timeout=5m, concurrency=[ConcurrencyExpression])`** — a **DAG node**. Shape is declared statically: `parents=[task_a, task_b]` makes this task run after them; `wait_for`/`skip_if`/`cancel_if` are CEL conditions evaluated against parent outputs. The engine knows the whole graph up front → cheaper, deterministic-by-construction, no replay needed.
- **`@workflow.durable_task(...)`** — appended to `self._durable_tasks` (`:1553`); receives a `DurableContext` and builds shape at runtime via `aio_sleep_for`/`aio_wait_for`/`run_child` — dynamic, the durable event log records each node as it's emitted. Suited to a ReAct loop where the next action depends on LLM output.

The workflow registers `tasks = self._default_tasks + self._durable_tasks` (`:356`) and triggers via `on_events=[...]` (CEL-filtered event subscriptions) or `on_crons=[...]`. Verso needs exactly this duality: a static plan-DAG mode for known-shape pipelines (cheaper) and a dynamic durable-task mode for the open-ended agent loop, both persisting to one journal.

**For Verso:** Hatchet teaches Verso the **dual-mode model** (static DAG vs dynamic durable task on one log) and the cleanest **"or group" HITL**. Steal: (1) the **`kind ∈ {RUN, WAIT_FOR, MEMO}` durable-log shape** with a monotonic `node_id` + `branch_id` for replay paths — the branch_id idea (record divergent replay paths instead of failing) is more forgiving than Temporal's hard non-determinism error and worth considering for a ReAct loop whose shape legitimately changes between runs; (2) the **server-computed `idempotency_key`** (hash of op-type + conditions + options) as the non-determinism detector — content-based, like Inngest; (3) **`aio_wait_for(...conditions, OrGroup)`** as the literal shape of Verso's HITL-with-timeout: wait for "human-approval event OR 24h-timeout sleep", whichever fires; (4) **release the worker slot during the wait** (durable eviction) so a pending HITL holds no compute — essential for an agent that may pause for hours.

---

## Resonate (+ Durable Promise Specification) — P1 / P2

### What It Is

"Distributed Async Await" — durable execution expressed as **Python generators** where every `yield` is a checkpoint, with **Durable Promises** (named, externally-resolvable futures) as the universal primitive. The single-binary server stores promises; the SDK is a generator scheduler. The whole model is the closest to Verso's desired developer experience: `durable=True` is a per-call option, not a per-agent rewrite, and HITL is just a named promise someone else resolves over HTTP.

### The generator/yield checkpoint model

KNOWN, `resonate.py:750`. A durable function is a generator taking `ctx: Context`. Inside it, the yieldables are:

```python
ctx.run(func, *args)    -> LFC[R]   # local effectively-once call, await result (alias lfc)  :821
ctx.begin_run(func)     -> LFI[R]   # local invoke, returns a promise to await later (alias lfi) :846
ctx.rfi(func) / rfc(func)           # REMOTE invoke / call — run on another process            :995/:1018
ctx.detached(func)                  # fire-and-forget remote                                    :1041
ctx.sleep(secs)         -> RFC[None]                                                            :1095
ctx.promise(id=, timeout=, idempotency_key=, data=, tags=) -> RFI    # named durable promise    :1119
```

You write `result = yield ctx.run(fn, arg)` — the generator suspends at the yield; the scheduler runs `fn` (checkpointing the invocation and the result), resumes the generator with the value. Each `yield ctx.run(...)` is therefore one checkpoint. No custom event loop, no sandbox — Python generator suspension *is* the suspension mechanism. `@resonate.register` marks a generator durable. The `durable=True/False` flag lives on `Options` (`options.py:18`, default `True`) and is applied per-call via `.options(durable=False)`.

### Step identity: hierarchical path `parent_id.counter`

KNOWN, `resonate.py:1184`:

```python
def _next(self) -> str:
    self._counter += 1
    return f"{self._id}.{self._counter}"     # e.g. "root.1", "root.2", "root.2.1" for a child
```

Identity is a **path through the call tree**, monotonic per context. This is deterministic by call order (like DBOS) but hierarchically namespaced (so a child execution's steps are `<child>.{n}`), which makes promise ids globally meaningful — an external resolver addresses a promise by this id.

### Determinism guards

`ctx.random` and `ctx.time` (`:780`, `:785`) are deterministic replacements — but note they're implemented as **`lfc` calls** (`Time.time()` = `self._ctx.lfc(lambda _: ...time.time())`, `:1196`): the wall-clock read is itself a checkpointed local call, so its result is journaled and replays identically. This is cleverer than Temporal's seeded RNG — *any* non-deterministic call becomes deterministic by wrapping it in a checkpointed `lfc`.

### HITL: the Durable Promise

KNOWN, `:1119`. `promise = yield ctx.promise(id="approval-42")` creates a named promise (default timeout `31536000`s = 1 year, `:1177`; `idempotency_key` defaults to the id). The generator yields and suspends. An external system resolves it via the server's HTTP API: `resonate.promises.resolve(id="approval-42", data=...)`. No signal channel, no query, no polling — a named future anyone can complete. This is the cleanest async-approval model in the cluster.

### The Durable Promise HTTP API (the open spec, as implemented)

KNOWN from `stores/remote.py` (the spec README `durable-promise-specification` is a 50-line pointer; the concrete contract is the SDK's HTTP client). The minimal interface a Verso backend must implement to be Resonate-compatible:

```
POST   /promises                         create  {id, param:{headers,data}, timeout, tags}   ; headers: idempotency-key, strict
POST   /promises/task                    create + claim a task {promise:{...}, task:{processId, ttl}}
GET    /promises/{id}                     read
PATCH  /promises/{id}  {state:"RESOLVED",         value:{headers,data}, ikey}     resolve   :232
PATCH  /promises/{id}  {state:"REJECTED",         value:..., ikey}                reject    :260
PATCH  /promises/{id}  {state:"REJECTED_CANCELED", value:..., ikey}               cancel    :291
POST   /promises/callback/{promise_id}    register a resume callback (engine wakes the waiter)
POST   /promises/subscribe/{promise_id}   subscribe to completion
```

State machine: `PENDING → {RESOLVED | REJECTED | REJECTED_CANCELED | REJECTED_TIMEDOUT}` (terminal). Idempotency-key on create + complete makes every operation safely retriable. `strict` mode rejects a complete if the promise is already in a conflicting terminal state.

| Fact | Value | Source |
|---|---|---|
| step identity | `f"{parent_id}.{counter}"` (path) | `resonate.py:1185` |
| `durable` default | `True` (per-call `Options`) | `options.py:18` |
| default promise timeout | 31536000s (1 year) | `resonate.py:1177` |
| idempotency_key default | = promise id | `resonate.py:1178` |
| determinism wrap | `ctx.time`/`ctx.random` are `lfc` checkpointed calls | `:1196` |
| promise states | PENDING / RESOLVED / REJECTED / REJECTED_CANCELED / REJECTED_TIMEDOUT | `stores/remote.py:235-291` |
| HITL resolve | `PATCH /promises/{id} {state:RESOLVED, value}` | `stores/remote.py:232` |

### The scheduler — a deterministic state-machine graph

KNOWN, `scheduler.py:52`. The generator scheduler is a pure state machine over a `Graph[State]` of execution nodes, each in one of: `Enabled[Running[...]]` / `Enabled[Suspended[Init|Rfnc|Coro]]` / `Enabled[Completed[...]]` / `Blocked[...]` (`:135`). `step(cmd, future) -> More | Done` (`:76`) advances the graph one transition; `eval()` (`:674`) drives nodes until all are suspended or done, returning `More(reqs)` (requests the bridge must fulfill against the store — create promise, invoke remote) or `Done(reqs)`. A yielded `LFI` (local invoke) transitions a node to a child Coro; an `RFI` (remote invoke) transitions to `Suspended(Rfnc)` with a `suspends` set — the node blocks until the remote promise resolves. This pure-state-machine design (no threads, no locks in the core) is what makes Resonate deterministically simulable (it ships a `simulator.py` for DST — deterministic simulation testing). Lesson: Verso's durable executor as a pure state machine (input: event/completion, output: requests to fulfill) is testable without real I/O.

### Local (LFI/LFC) vs Remote (RFI/RFC) + the Bridge

KNOWN, `bridge.py:54`. `lfi/lfc` run in-process (the scheduler runs the child generator locally, checkpointing invocation + result). `rfi/rfc` (`resonate.py:995`) create a remote durable promise and dispatch the invocation to *another process* via the **Async RPC protocol** (transport-agnostic — HTTP today, the bridge `:208` handles `More(reqs)`/`Done(reqs)` by routing each request to the store/network). `detached` is fire-and-forget remote. This local/remote split on the same `yield` surface means a Verso step can run in-process or be dispatched to a worker pool with zero call-site change — the same `durable=True` ergonomic extended to distribution.

### Promise store internals & the timeout control loop

KNOWN, `stores/local.py:30`. The `LocalStore` (in-memory/SQLite, for single-process or testing; `RemoteStore` is the HTTP client to the server) runs a **control loop** (`:117`) that wakes on a `Condition` whose timeout is `min(all pending promise timeouts, all task expiries, next schedule run time)` (`:145-158`). On wake it: creates scheduled promises (`:168`), and **transitions any `PENDING` promise whose `timeout` has passed to `REJECTED_TIMEDOUT`** (`:188`) via `promises.transition(id, to)` — the state-machine enforcer. This is the server-side timeout mechanism every Durable Promise system needs: a single loop computing the next deadline across all pending promises rather than a timer per promise. The **Task** model (`models/task.py`): a task is a claimable unit (`processId`, `ttl`) that wakes a process to resume a suspended generator — `create_with_task` (`remote.py:169`) atomically creates a promise + a task to drive it. Verso's equivalent: a single timeout-scanner loop over the `step_outputs`/promise table that fires timeouts and re-dispatches resumable runs, not N in-process timers.

### Convention — promise-id / idempotency generation

KNOWN, `models/convention.py:9`. A `Convention` protocol defines how a yieldable maps to a durable-promise record: `id() -> str`, `idempotency_key() -> str | None`, `data() -> Any`, `timeout() -> float` (relative seconds), `tags() -> dict | None`. The `Base` convention (used by `ctx.promise`, `resonate.py:1174`) defaults `idempotency_key = id` and `timeout = 31536000` (1yr). This indirection means the id/idempotency/tag scheme is pluggable per invocation type (a local call, a remote call, an explicit promise each have a convention) — the single point that decides "what is this step's durable identity and how is it deduped." Verso should centralize step-id + idempotency-key derivation in one `Convention`-like object rather than scattering `sha1(name)` calls, so the identity scheme is swappable (content-hash vs path vs ordinal) without touching call sites.

**For Verso:** Resonate is the model whose *developer experience* Verso should target most closely. Steal: (1) the **generator-yield-as-checkpoint** model — if Verso's ReAct loop is written as a generator, each `yield ctx.step(...)` is a natural checkpoint with zero sandbox/replay machinery; (2) the **`durable=True` per-call option** (default-on, overridable via `.options(durable=False)`) — exactly Verso's seam, applied at the call granularity rather than the agent granularity; (3) the **wrap-any-nondeterminism-in-a-checkpointed-call** trick (`ctx.time`/`ctx.random` as journaled `lfc`) — more general than Temporal's seeded RNG and lets Verso allow arbitrary side-effects in steps as long as they're wrapped; (4) **adopt the Durable Promise HTTP spec verbatim** as Verso's pluggable HITL backend interface — `POST /promises`, `PATCH /promises/{id} {state}`, `POST /promises/callback/{id}` — implementing it makes Verso interop with any Resonate SDK, and it IS the minimal "named external future" Verso's HITL needs. The one gap the spec doesn't cover (note for Verso): parent-child promise ancestry / step lineage — Verso must add that on top if it wants the call-tree path identity Resonate's own SDK layers on (`parent.counter`).

### The Durable Promise Specification — full data model & state machine (P2 target in its own right)

KNOWN (canonical spec at distributed-async-await.io, fetched). This is the minimal interface Verso's pluggable HITL/checkpoint backend must implement to be Resonate-compatible. The **data model** of a promise record (every field):

```
id: string                          # unique identifier
state: PENDING | RESOLVED | REJECTED | REJECTED_CANCELED | REJECTED_TIMEDOUT
timeout: int64                      # expiration (epoch); auto-transitions to REJECTED_TIMEDOUT
param:  { headers: object, data: string }    # creation payload
value:  { headers: object, data: string }    # result/error payload (set on completion)
tags:   object                      # custom k/v metadata (used for routing/search)
idempotencyKeyForCreate:   string (read-only)
idempotencyKeyForComplete: string (read-only)
createdOn:   int64
completedOn: int64
```

**State machine:** `PENDING → {RESOLVED | REJECTED | REJECTED_CANCELED | REJECTED_TIMEDOUT}`; all non-PENDING states are terminal (no further transitions). The timeout fires the `REJECTED_TIMEDOUT` transition automatically server-side.

**HTTP API (the complete contract):**
```
POST  /promises          create    headers: request-id, idempotency-key, strict   body: {id, timeout, param?, tags?}
GET   /promises/:id       read      headers: request-id
GET   /promises           search    query: id, state, tags, limit, cursor
PATCH /promises/:id       complete  headers: request-id, idempotency-key, strict   body: {state: RESOLVED|REJECTED|REJECTED_CANCELED, value?}
```

**Idempotency semantics (the correctness core):** a create or complete with a matching idempotency key returns OK + "Deduplicated" when the existing state matches; a mismatched key or a state conflict returns KO. `strict` mode makes a complete fail if the promise is already terminal in a conflicting state (vs lenient: idempotent no-op). The two separate idempotency keys (create vs complete) mean the *creation* of a HITL promise and its *resolution* are independently deduplicated — a retried agent re-creating the same promise is a no-op, and a double-fired external resolve is a no-op.

**For Verso:** implement this 4-endpoint contract as the HITL backend interface and Verso interoperates with every Resonate SDK for free. The two-idempotency-key design is the detail to copy: dedupe promise creation (retried agent) separately from promise completion (double callback). The `tags` field is Verso's routing hook — tag a promise with the agent id / approval type so external systems can `GET /promises?tags=...` to find pending approvals. The gap to fill (same as noted above): the spec has no parent/child promise lineage, so Verso adds step-ancestry on top.

---

## Windmill (Workflow as Code) — P1

### What It Is

An open (AGPLv3) Rust-backend script/workflow platform. The "workflow-as-code v2" Python layer is the most accessible Python-native suspend-replay model in the cluster: the workflow function runs to a `@task` call; if that step isn't cached, the function **throws a suspend exception that exits the worker**, persisting completed-step results to a Postgres JSONB column and re-queuing; on resume the cached steps return instantly and the function runs forward to the next uncached step.

### Step identity: name-based ordinal `_alloc_key`

KNOWN, `client.py:2437`. A per-name counter, deterministic by call order:

```python
def _alloc_key(self, name="step") -> str:
    n = self._counters.get(name, 0) + 1
    self._counters[name] = n
    return name if n == 1 else f"{name}_{n}"     # "double", "double_2", "double_3"
```

So identity is `name` (first) / `name_n` (nth) — like Inngest's `:n` but unhashed, and like DBOS's order-dependence. The determinism contract is explicit in the SDK docstring (`:2805`): "the workflow function must call tasks in the same order on replay; non-deterministic values (timestamps, random) must be wrapped in `step()` for stability."

### Suspend-replay via `_StepSuspend` (the core algorithm)

KNOWN, `client.py:2443`. `WorkflowCtx` holds `_completed: dict` (the checkpoint, loaded from `workflow_as_code_status`), `_counters`, `_pending: list`, and `_executing_key`. `_next_step` is the gate:

```python
def _next_step(self, name, script, func=None, dispatch_type="inline", ...):
    key = self._alloc_key(name or script or "step")
    if key in self._completed:                         # CACHE HIT
        val = self._completed[key]
        if val.get("__wmill_error"): raise TaskError(...)
        return self._resolved(val)                     # instant
    if self._executing_key is not None:                # this re-invocation is to RUN one specific step
        if key == self._executing_key: return self._execute_directly(func, **kwargs)
        else: return self._never_resolve()             # await asyncio.Future() forever — not our turn
    self._pending.append(info)                         # CACHE MISS, no target → record pending step
    return self._suspend()                             # raise _StepSuspend({mode, steps:[pending]})
```

`_suspend` (`:2485`) raises `_StepSuspend({"mode": "parallel" if len>1 else "sequential", "steps": [pending]})` — this **exits the workflow function entirely**; the worker catches it, persists `_completed` to Postgres, dispatches the pending step(s) as child jobs, and frees the slot. When children finish, the workflow is re-invoked with the updated checkpoint, the now-cached steps replay instantly, and execution proceeds to the next miss. Two execution modes: `@task` (full suspend → child job → replay) and `step(name, fn)` (`:2533`) — an **inline fast path** that runs `fn()` in the parent process and POSTs the result to `/jobs/wac/inline_checkpoint/{job_id}` (`:2593`) with `{"key", "result"}`, persisting without spawning a child job (~15ms saved per step by reusing one `httpx.AsyncClient`; serialized by `_inline_lock` to close the `SELECT FOR UPDATE` first-write race on the `v2_job_status` row).

### Checkpoint storage & HITL

KNOWN. Checkpoint = JSONB column `workflow_as_code_status` on table `v2_job_status` (`migrations/20250201124743_v2_job_queue_sync.up.sql:177` UPSERTs it; synced to `__flow_status` via trigger `:20250201124805`). It stores the whole serialized `_checkpoint` object including `completed_steps`. HITL: `_wait_for_approval(timeout=1800, form, self_approval)` (`:2495`) raises `_StepSuspend({"mode": "approval", "key", "timeout", "form", "self_approval_disabled"})` — the worker suspends, surfaces a resume URL/form in the UI; on human action it returns `{approved, approver, value}`. `_sleep(seconds)` (`:2516`) raises `_StepSuspend({"mode": "sleep", "key", "seconds": max(1, int)})`.

| Fact | Value | Source |
|---|---|---|
| step identity | `name` / `name_n` ordinal | `client.py:2441` |
| checkpoint store | JSONB `v2_job_status.workflow_as_code_status` | migration `20250201124743` |
| suspend mechanism | `_StepSuspend` exception exits worker | `client.py:2488` |
| inline fast-path | `POST /jobs/wac/inline_checkpoint/{job_id}` | `client.py:2593` |
| approval default timeout | 1800s | `client.py:2496` |
| min sleep | `max(1, int(seconds))` | `client.py:2529` |
| concurrency safety | `_inline_lock` + `SELECT FOR UPDATE` on status row | `client.py:2429` |

### Server side — the Rust worker's checkpoint cycle

KNOWN, `backend/windmill-worker/src/wac_executor.rs`. The Python `_StepSuspend` payload is consumed by the Rust worker as a `WacResult` enum (`:22`): `Dispatch{mode, steps}` (spawn child jobs), `inline_checkpoint` (persist a step result computed in-parent, no child), `approval{key, timeout, form, self_approval_disabled}` (suspend for human input, no child), `sleep` (server-side suspend for a duration without holding a worker). The checkpoint type is `WacCheckpoint{completed_steps, pending_steps}` persisted via `save_checkpoint`/`load_checkpoint` to `v2_job_status.workflow_as_code_status` (JSONB). The resume path `prepare_checkpoint_for_resume` (`:131`) is the load-bearing detail: when the workflow re-runs after an approval/sleep resolves, it **injects the resume result into `completed_steps[key]` before re-execution** — so the suspended `_wait_for_approval`/`_sleep` step finds its result in the cache and returns `{approved, approver, value}` instead of suspending again. `all_parallel_steps_complete` (`:123`) checks every pending parallel key is in `completed_steps` before resuming. `persist_inline_checkpoint_delta` writes just the one new step (the fast-path delta), avoiding a full-checkpoint rewrite under the `SELECT FOR UPDATE` lock. This is the exact server↔SDK protocol Verso must implement: SDK raises a typed suspend with pending work; server persists completed steps + dispatches/suspends; on resume, server pre-injects resolved waits into the cache, re-invokes, SDK replays.

### The job queue substrate (the Postgres queue the WAC layer sits on)

KNOWN, `migrations/20220123221903_first.up.sql:120+`. The whole platform is a Postgres job `queue` table: `scheduled_for TIMESTAMPTZ` (the durable-sleep / delayed-execution mechanism — a slept workflow sets `scheduled_for` to wake time, the worker polls `WHERE scheduled_for <= now() AND running=false`), `running BOOLEAN`, `flow_status JSONB` (flow execution state), with `CREATE INDEX index_queue_on_scheduled_for` making the "what's ready to run" scan cheap. On completion a job moves from `queue` to `completed_job`. The Rust worker pulls jobs with `SELECT ... FOR UPDATE SKIP LOCKED` (the standard Postgres-queue dequeue), executes the script in an **nsjail sandbox** (process isolation, not language-level like Temporal). This is the simplest possible durable backend: a single Postgres queue table with `scheduled_for` for timers and a JSONB status column — no separate scheduler, no event bus. Verso's minimal durable backend can be exactly this: a `verso_runs` table doubling as the work queue (`scheduled_for` for durable sleeps/HITL-timeouts, `FOR UPDATE SKIP LOCKED` dequeue), no extra infrastructure.

**For Verso:** Windmill is the most direct "pure-Python suspend-replay" reference. Steal: (1) the **`_StepSuspend`-exception-exits-the-worker** pattern — on a cache miss, raise an exception that unwinds out of the agent function, persist completed steps, free the worker, re-invoke later — this is exactly how Verso can implement `durable=True` without a sandbox or a separate VM; (2) the **two-tier step API** — heavyweight `@task` (suspend + child job, for steps that should run on a different worker / be retried independently) vs lightweight `step(name, fn)` (inline checkpoint in-process, for cheap steps like an LLM call you want journaled but not dispatched) — Verso wants both; (3) the **single JSONB checkpoint column** (`completed_steps` map) as a dead-simple checkpoint store for small state — simpler than LangGraph's blob-versioning, appropriate when per-step outputs are small; (4) the **`_inline_lock` + `SELECT FOR UPDATE`** detail — concurrent in-process steps writing one JSONB checkpoint row will clobber each other unless serialized; Verso must guard the checkpoint write under parallel tool calls.

---

## Trigger.dev v3 — P1

### What It Is

The only system here using **OS-level container checkpointing (CRIU — Checkpoint/Restore In Userspace)** instead of application-level event sourcing. At every `wait.*` / `triggerAndWait` call, the running Node container is frozen to disk and restored on a machine when the wait resolves. Fundamentally different tradeoffs: **no determinism requirement** (arbitrary code, including the whole task body, runs once and is frozen mid-execution), but checkpoint artifacts are large and restore adds latency.

### The waitpoint + suspendable mechanism (the CRIU hook)

KNOWN, `packages/core/src/v3/runtime/sharedRuntimeManager.ts`. Every wait goes through `suspendable(promise)` (`:276`):

```typescript
private setSuspendable(suspendable: boolean): void {
    this.ipc.send("SET_SUSPENDABLE", { suspendable });   // tell the supervisor: safe to checkpoint now
}
private async suspendable<T>(promise: Promise<T>): Promise<T> {
    this.setSuspendable(true);                 // CRIU may freeze the container while this promise is pending
    const [error, result] = await tryCatch(promise);
    this.setSuspendable(false);                // back to non-checkpointable (actively executing)
    if (error) throw error;
    return result;
}
```

This is the entire CRIU integration contract from the SDK side: `SET_SUSPENDABLE true` over IPC tells the supervisor process "the task is now blocked on a waitpoint — you may CRIU-freeze this container." The supervisor checkpoints the container image; when the waitpoint resolves (external event, duration elapsed, child task done), the supervisor restores the image on a (possibly different) machine, the pending `Promise` resolves with the waitpoint's output, and execution continues exactly where it froze. No memoization, no replay — the *process memory itself* is the checkpoint.

Waitpoint resolution is push-based: the supervisor injects the `CompletedWaitpoint` into `resolversById` (`:55`, a map of waitpoint friendly-id → promise resolver); `resolvePendingWaitpoints()` handles waitpoints that arrived before the resolver was registered (the resume-before-wait race). `_preventMultipleWaits` enforces one outstanding wait at a time (a single CRIU freeze point).

### Waitpoint taxonomy

KNOWN, `schemas/api.ts`. The complete HITL pause set:
- `wait.for(duration)` / `wait.until(date)` → `waitForWaitpoint({finishDate})` — duration waitpoint
- `wait.forToken(...)` / `waitForWaitpoint({waitpointFriendlyId})` — a **manual token** waitpoint (the HITL primitive); status enum `WaitpointTokenStatus = ["WAITING", "COMPLETED", "TIMED_OUT"]` (`:1511`); resolved externally by API call carrying the token's friendly id + output
- `task.triggerAndWait(taskRef)` → `waitForTask({id})` — wait for one child run
- `task.batchTriggerAndWait([...])` → `waitForBatch({id, runCount})` — N child runs, resolvers keyed `${id}_${index}` (`:90`)
- `event.waitForEvent(matcher)` — event-match waitpoint

The token model: an external system holds the waitpoint friendly id; it `POST`s completion with `{output}`; the supervisor resolves the frozen run. Status is `WAITING → COMPLETED | TIMED_OUT`.

### Versioning & rollback (INFERRED, blog/docs)

Immutable deployment versions: each deploy is a version snapshot; running tasks **lock to their deploy version** (a frozen container is bound to the image it was checkpointed from), so a new deploy never disturbs in-flight runs. Rollback functions: explicit undo blocks for non-idempotent mutations — a complement to retry-based recovery (since CRIU re-runs nothing, a partial side-effect before a crash needs an explicit compensator).

| Fact | Value | Source |
|---|---|---|
| checkpoint mechanism | CRIU container freeze/restore | runtime manager + blog |
| SDK→supervisor signal | IPC `SET_SUSPENDABLE {true/false}` | `sharedRuntimeManager.ts:273` |
| determinism requirement | NONE (process memory is the checkpoint) | — |
| token waitpoint states | WAITING / COMPLETED / TIMED_OUT | `api.ts:1511` |
| batch resolver keys | `${id}_${index}` | `:90` |
| concurrency guard | `_preventMultipleWaits` (one freeze point) | `:54` |

### Trigger options & version-locking

KNOWN, `schemas/api.ts:205`. A trigger carries: `concurrencyKey` (string, keyed concurrency — e.g. per-user serial execution), `idempotencyKey` (≤2048 chars) + `idempotencyKeyTTL` (string) + `idempotencyKeyOptions` (dedupe a trigger for a window), `machine: MachinePresetName` (the compute size — small/medium/large, since a CRIU image is bound to a machine shape), `maxDuration` (number, seconds — hard wall-clock cap). The `machine` preset is CRIU-specific: because the checkpoint is a process image, restore must target a compatible machine, so the machine size is part of the trigger contract. Version-locking (INFERRED): a run's CRIU image is bound to the deploy version it was captured from, so an in-flight frozen run restores onto its original code, never a new deploy — this is the immutable-deployment-version guarantee. Verso's memoization model gets the same in-flight-upgrade safety more cheaply (record the agent code version in the run row, like DBOS `application_version` / LittleHorse `old_wf_spec_versions[]`, and refuse to resume a run on an incompatible version) without binding to a machine image.

**For Verso:** Trigger.dev is the architectural *foil* — it shows the alternative to event sourcing, and why Verso probably should NOT take it. CRIU's appeal is zero determinism constraint (the agent body can do anything), but it requires container-level infra (a supervisor that can CRIU-freeze and restore process images), large checkpoint artifacts, and version-locking of in-flight runs — wrong for a pip-installable Python framework. What Verso SHOULD steal: (1) the **`SET_SUSPENDABLE` boundary concept** — even in a memoization model, Verso benefits from explicitly marking "the agent is now blocked on a HITL waitpoint, it is safe to persist+evict" vs "actively executing, do not checkpoint mid-step"; (2) the **token waitpoint** (`WAITING → COMPLETED | TIMED_OUT`, resolved by external id) — identical to Resonate's promise and AWS's task token, confirming this is THE convergent HITL shape; (3) the **rollback/compensator** primitive for non-idempotent steps — any durable model that re-runs (or, here, freezes) needs an explicit undo for side-effects that already partially happened; (4) **batch-wait with per-index resolvers** for parallel child agents. Avoid CRIU itself: Verso's `durable=True` must work without container orchestration.

---

## LittleHorse — P2

### What It Is

A gRPC-first orchestration engine with a **Kafka-as-WAL** durability model — the closest open analog to Temporal but with Kafka + Kafka Streams (RocksDB state stores) instead of Temporal's proprietary store. The headline split: **WfSpec** (compiled workflow definition, like bytecode) vs **WfRun** (an execution instance). Java kernel; Python/Go/Java SDKs build the WfSpec via a fluent builder.

### Kafka as the durable WAL (the durability substrate)

KNOWN (README:31) + INFERRED (architecture docs). Every state mutation is a `Command` protobuf appended to a Kafka **command topic**; the LH kernel is a Kafka Streams topology that consumes commands, mutates RocksDB-backed state stores, and emits changelog records (Kafka replicates the changelog → recovery re-applies the log). `command.proto:20`:

```protobuf
message Command {
  oneof command {
    TaskClaimEventPb task_claim_event = 5;   // a worker claimed/completed a task
    RunWfRequest run_wf = 6;                  // start a WfRun
    PutExternalEventRequest put_external_event = 7;   // HITL / external signal
    ...
  }
}
```

So recovery is event-sourcing over Kafka: the command log is the source of truth, RocksDB is a materialized view that Kafka Streams rebuilds from the changelog topic on failover. This is the high-throughput alternative to Postgres-as-checkpoint-store: append to Kafka (sequential, partitioned by WfRun id for ordering) rather than UPDATE a row.

### WfRun / ThreadRun / NodeRun model

KNOWN, `wf_run.proto:16`. The execution-instance hierarchy:

```protobuf
WfRun { id; wf_spec_id; old_wf_spec_versions[];   // version migration audit trail
        status (LHStatus); thread_runs[ThreadRun]; parent_trigger; ... }
ThreadRun { number; status; ... }                  // a concurrent thread within a WfRun
// each Node in the WfSpec produces a NodeRun (a durable, independently-retryable record)
```

A `WfSpec` `Node` (`wf_spec.proto:385`) is a tagged union: `TaskNode` (dispatch to a task worker), `ExternalEventNode` (the HITL pause), `StartThreadNode` / `WaitForThreadsNode` (fork/join concurrency), `SleepNode`, `RunChildWfNode`. The compile-then-run split means a WfRun records `old_wf_spec_versions[]` so an in-flight run can be migrated across spec versions with a full audit trail — the version-safety mechanism.

### HITL: ExternalEvent + correlation

KNOWN, `wf_spec.proto:325` + `service.proto:551`. An `ExternalEventNode` "causes the WfRun to stop and wait for an ExternalEvent." External systems resolve it via the gRPC `PutExternalEvent(PutExternalEventRequest)` (`service.proto:179`) — the request can carry a correlation guid so the right ExternalEventNode in the right WfRun is matched. This is the same task-token/named-promise pattern: the WfRun idles (no compute), an external caller pushes an event with a correlation key, the kernel resolves the waiting NodeRun. Task dispatch to workers is via **bidirectional gRPC streaming** (no polling — the kernel pushes `TaskClaimEvent`s to connected workers).

| Fact | Value | Source |
|---|---|---|
| WAL | Kafka command topic (partitioned by WfRun id) | README + `command.proto:20` |
| state store | RocksDB via Kafka Streams, rebuilt from changelog | INFERRED (arch docs) |
| compile/run split | WfSpec (definition) / WfRun (instance) | `wf_run.proto:16` |
| durable unit | NodeRun (independently retryable) | `wf_spec.proto:385` |
| HITL | ExternalEventNode + `PutExternalEvent(correlation guid)` | `service.proto:179` |
| task dispatch | bidirectional gRPC stream (push, no poll) | `service.proto` |
| version migration | `WfRun.old_wf_spec_versions[]` audit trail | `wf_run.proto:25` |

### UserTask — a first-class human-task primitive

KNOWN, `common_wfspec.proto:252`. Beyond raw ExternalEvent, LittleHorse has a dedicated `UserTaskRun` (a human task with `user_id`/`user_group` assignment) and **scheduled hooks** (`UserTaskAction`): on creation or after `delay_seconds`, fire a hook that can `CANCEL` the task, `REASSIGN` it to a different user/group, or `schedule a TaskRun` (escalation). This is HITL with built-in SLA/escalation — a human approval that auto-escalates or reassigns if not actioned in time. Most systems here give you a raw token/promise and leave assignment+escalation to the app; LittleHorse bakes it in. For a Verso agent that pauses for human review, the UserTask model (assignee + timeout-escalation hook) is the richer HITL target if Verso wants managed approvals rather than just a bare promise. Failure handling: `WfRun.pending_failures[PendingFailureHandler]` and `pending_interrupts[PendingInterrupt]` (`wf_run.proto:48-54`) — thread-scoped failure handlers and interrupts that fire once the relevant ThreadRun halts (try/catch + interrupt semantics at the workflow level).

**For Verso:** LittleHorse is the reference for the **Kafka-WAL durability option** Verso should offer for high-throughput deployments (alongside the Postgres default from DBOS). Steal: (1) the **command-log-as-WAL** model — every state transition is an event appended to a partitioned log (partition key = run id for per-run ordering), state is a materialized view rebuilt from the log — this is the right backend when Verso needs >40K steps/sec and Postgres row-updates become the bottleneck; (2) the **WfSpec/WfRun compile-then-run split** with `old_wf_spec_versions[]` — Verso could compile an agent definition to a versioned spec and let in-flight runs record which version they started under (cleaner in-flight-upgrade story than Trigger.dev's version-locking); (3) the **ExternalEventNode + correlation-guid** HITL — same convergent pattern, but note LH's bidirectional gRPC task-push (no polling) is worth copying for Verso's worker dispatch. Caveat: LH's SDK is lower-level (you build a WfSpec graph), less natural for a dynamic ReAct loop than the generator/decorator models above — study it for the *backend* (Kafka WAL), not the developer surface.

---

## Cloudflare Workflows (+ Durable Objects) — P1 (closed infra; blog + workerd)

### What It Is

JS/TS-only durable runtime built on **Durable Objects** with per-instance **SQLite** state. Each workflow instance is its own DO; the DO's SQLite is the checkpoint store. Despite being closed and JS-only, it documents the **simplest possible replay algorithm** in the cluster — the "game loop" — and the cleanest storage design. (No source to clone for the Workflows layer; `cloudflare/workerd` is open for the DO/storage/alarm primitives the blog references.)

### The game-loop executor (the replay algorithm)

KNOWN (blog, verbatim pseudocode):

```
while (last step not completed)
    iterate every step
       use memoized cache as response if the step has run already
       continue running step or timer if it hasn't finished yet
end while
```

This is memoization-replay reduced to its essence: re-run the whole workflow function from the top each tick; for each `step.do`, check storage for a memoized result and return it instantly if present; only the first not-yet-completed step actually executes. The per-step gate (blog, verbatim):

```javascript
async do<T>(name: string, callback: () => Promise<T>): Promise<T> {
    const maybeResult = await this.#state.storage.get(name);   // memoized by step NAME
    if (maybeValue) { return maybeValue; }                     // cache hit → skip execution
    return doWrapper(callback);                                // cache miss → run, then persist
}
```

Step identity = the **step name** (string key into DO storage). Steps must be "stateful and idempotent — produce the same result no matter how many times we run them," same determinism contract as Inngest/Windmill.

### Write-before-advance & storage

KNOWN (blog). The step result is written to SQLite via **`transactionSync()`** (the DO SQLite backend's atomic write) *before* the workflow advances. If the DO is evicted after the write but before the next step, replay reads the memoized result and skips re-execution — the write-before-advance invariant that makes eviction safe. Relational state via `this.ctx.storage.sql.exec()` inside the transaction.

### Sleep & long waits: scheduler.wait + DO alarms

KNOWN (blog). Two-tier waiting: `scheduler.wait()` (WICG Scheduling API) for short in-process waits; **Durable Object alarms** for long sleeps — a DO alarm is a persistent cron-like callback that wakes the (possibly-evicted) DO at a future time, rehydrating the cached state. The alarm-as-resume-trigger is transport-agnostic and the key reusable idea. API:

```javascript
await step.do('name', { retries: {limit:5, delay:'5 seconds', backoff:'exponential'}, timeout:'15 minutes' }, async () => {...});
await step.sleep("wait for three days", "3 days");
// step.waitForEvent(matcher) — event-match resume (signature not in blog)
```

**INFERRED:** V2 (May 2026) scales to 50K concurrent instances; each instance is a separate DO+SQLite; the control-plane refactor lifted the concurrency ceiling.

| Fact | Value | Source |
|---|---|---|
| replay algorithm | game loop (re-run, memoize by name) | blog (verbatim) |
| step identity | step name (DO storage key) | blog |
| write ordering | `transactionSync()` write-before-advance | blog |
| short wait / long wait | `scheduler.wait()` / DO alarm | blog |
| retry default shape | `{limit:5, delay, backoff:'exponential'}` (example) | blog |
| V2 concurrency ceiling | 50K instances | blog (INFERRED) |

### V2 architecture & the Durable Object storage primitive (workerd)

KNOWN (V2 blog) + workerd (open). V2 (May 2026): **up to 50,000 concurrent instances and 300 new instances/sec per account**, "redesigned for the agentic era"; Dynamic Worker boots in single-digit ms. Each workflow instance is a separate Durable Object; the DO's SQLite is its private checkpoint store. The DO primitive itself (open in `cloudflare/workerd`): a Durable Object is a single-threaded, globally-addressable actor with `ctx.storage` (a transactional KV + SQLite API: `storage.get/put`, `storage.transactionSync()`, `storage.sql.exec()`) and `ctx.storage.setAlarm(time)` — the alarm wakes an evicted DO at a future timestamp by re-instantiating it and calling `alarm()`. This actor-per-instance model is why CF needs no cross-instance coordination for the game loop: each workflow's entire state is one DO's serialized SQLite, and concurrency is just "how many DOs are live." The agentic-era reframing (50K concurrent) is precisely the "many long-lived paused agents" workload Verso targets. Verso's non-CF equivalent: one logical actor (checkpoint namespace) per agent run, but multiplexed over a shared Postgres + a job scheduler for alarms, rather than a dedicated DO process per run (Verso can't assume an actor runtime).

**For Verso:** Cloudflare gives Verso the **minimal mental model** for its durable executor: the game loop is exactly what Verso's `durable=True` Python executor should be — re-enter the agent function, memoize each step by a stable key, run only the first uncached step. Steal: (1) the **game-loop algorithm verbatim** as Verso's executor skeleton; (2) **write-before-advance** with an atomic transaction — persist the step result before the loop advances, so eviction/crash between steps is always safe (this is the single most important invariant across every memoization-based system here — DBOS, Inngest, Windmill, CF all enforce it); (3) the **two-tier wait** (in-process timer for short sleeps, a persistent scheduler/alarm for long ones that survives eviction) — Verso should back long `wait.for` on any external job scheduler (the alarm pattern is backend-agnostic), not an in-process `asyncio.sleep`. The per-instance-SQLite model is CF-specific; Verso's equivalent is one checkpoint namespace per agent run in shared Postgres.

---

## AWS Step Functions — P2 (closed; ASL docs)

### What It Is

Managed serverless workflow engine; workflows are **ASL (Amazon States Language)** JSON state machines (not code). The reason it's in scope: the **task token** `.waitForTaskToken` pattern is the canonical, production-proven HITL abstraction — "pause a workflow and wait for an external human/system to call back" — used at scale. The ASL DSL is exactly what Verso *avoids*, but the token semantics are the reference.

### The three integration patterns

KNOWN (docs). Controlled by the `Resource` ARN suffix:
- **Request Response** (no suffix): call the service, advance immediately on HTTP response.
- **Run a Job (`.sync`)**: call the service, **pause until the job completes** (Step Functions polls `DescribeExecution`-style APIs + consumes EventBridge events to detect completion).
- **Wait for Callback (`.waitForTaskToken`)**: call the service with a task token, pause until the token is returned via API. **This is the HITL primitive.**

### The task token mechanism (the convergent HITL pattern)

KNOWN (docs). When a Task's `Resource` ends in `.waitForTaskToken`, a unique opaque token is generated and exposed in the state via the **Context object**: `"TaskToken.$": "$$.Task.Token"` (the `$$.` prefix accesses the Context object, `$$.Task.Token` is the JSONPath to the token). The token is passed to the external system (embedded in an SQS message, Lambda payload, etc.). The workflow **idles** until the external system calls:

```
SendTaskSuccess(taskToken, output)    → resolve, continue with `output`
SendTaskFailure(taskToken, error)     → fail the task
SendTaskHeartbeat(taskToken)          → keep-alive (resets the heartbeat timer)
```

The workflow needs **zero knowledge of the approval system** — it only knows the token. Timeout semantics: a waiting task can pause up to the **1-year** service quota; `HeartbeatSeconds: N` (e.g. 600 = 10 min) sets a heartbeat deadline — if no `SendTaskSuccess/Failure/Heartbeat` arrives within `N` seconds, the task fails with `States.Timeout`. On task timeout/retry, **a new random token is generated** (the old token becomes invalid — prevents stale callbacks resolving a retried task). Production HITL choreography: token stored in DynamoDB by the initiating Lambda → EventBridge rule fires on the external completion event → a resolver Lambda looks up the token and calls `SendTaskSuccess`.

| Fact | Value | Source |
|---|---|---|
| token JSONPath | `$$.Task.Token` (Context object) | docs |
| resolve / fail / keepalive | `SendTaskSuccess` / `SendTaskFailure` / `SendTaskHeartbeat` | docs |
| max wait | 1 year (service quota) | docs |
| heartbeat field | `HeartbeatSeconds: N` → `States.Timeout` on miss | docs |
| token on retry | new random token generated (old invalidated) | docs |
| patterns | Request-Response / `.sync` / `.waitForTaskToken` | docs |

**For Verso:** SFN confirms the **task-token HITL pattern is the industry-standard convergent design** — Resonate's named promise, Trigger.dev's token waitpoint, Restate's awakeable, LittleHorse's ExternalEvent correlation guid, and AWS's task token are all the same primitive: *an opaque external identifier the workflow yields on, that any out-of-band system resolves with a payload, with no coupling to the approval mechanism*. Verso must offer exactly this as its first-class HITL primitive. Steal the SFN refinements specifically: (1) the **`SendTaskHeartbeat` keep-alive** + `HeartbeatSeconds` deadline → `States.Timeout` — for long human approvals, a heartbeat prevents a dead approval system from holding a run forever; (2) **generate a new token on retry and invalidate the old** — critical correctness detail: a retried Verso step must not be resolvable by a stale callback from the prior attempt; (3) the **three-pattern taxonomy** (fire-and-continue / wait-for-job-completion / wait-for-callback) as the shape of Verso's tool-call durability options. Avoid the ASL JSON DSL entirely — Verso's whole thesis is "Python code, not a JSON state machine."

---

## Cross-System Patterns

### Master comparison matrix

The full design space, one row per system, the four subsystems as columns. This is the decision table for Verso's architecture.

| System | Family | Step identity | Checkpoint store | Replay/resume mechanism | HITL primitive | Worker freed on wait? | Determinism contract |
|---|---|---|---|---|---|---|---|
| **Temporal** | Event-source | per-type monotonic `seq` (order) | server event history | Commands↔Events match by seq; sandbox + custom asyncio loop | signal / query / update + `wait_condition`; cross-wf signal | yes (sticky cache evict) | strict (sandbox-enforced; body fully deterministic) |
| **DBOS** | Memoize | `function_id` (call order) | Postgres `operation_outputs(wf_uuid, function_id)` | check_operation_execution by (wf,fid); run forward | `recv`/`send` topic mailbox; `set_event` | yes (no resident proc) | "same step order on replay" |
| **LangGraph** | Memoize | superstep + channel version | Postgres channel-versioned blobs + `versions_seen` | `versions_seen` schedules next nodes; `pending_writes` per-task replay | `interrupt()` (counter-indexed) / static `interrupt_before` | yes (checkpoint+return) | node body idempotent (re-runs on resume) |
| **Restate** | Event-source (journal) | journal position (VM handle) | Bifrost log → object store; RocksDB derived | `do_progress`: AnyCompleted/ExecuteRun/Wait/Suspend | Durable Promise (named) + Awakeable (id) | yes (Suspended → HTTP returns) | journal replay (run results memoized) |
| **Inngest** | Memoize | `sha1(name[:n])` (content) | server State Store; `steps:{hash:out}` map | re-POST; pop memo by hash; run to first miss; 206 | `wait_for_event` (CEL+timeout) | yes (stateless) | step name stable (content-addressed) |
| **Hatchet** | Memoize (durable log) | `_wait_index` → signal_key; server idempotency_key | Postgres `v1_durable_event_log_entry` (node_id, branch_id) | replay by node_id; branch_id for divergent paths | `aio_wait_for(...OrGroup)` (sleep OR event) | yes (durable eviction) | server idempotency_key (content) |
| **Resonate** | Memoize (generator) | `parent.counter` (path) | promise store (local/remote) | generator yields = checkpoints; state-machine graph | Durable Promise (named, HTTP-resolved) | yes | wrap nondeterminism in `lfc` |
| **Windmill** | Memoize | `name`/`name_n` (ordinal) | Postgres `v2_job_status.workflow_as_code_status` JSONB | `_StepSuspend` exits worker; replay `completed_steps` | `waitForApproval` (form+timeout) | yes (`_StepSuspend`) | "same task order on replay" |
| **CF Workflows** | Memoize | step name | DO SQLite (per-instance) | game loop: re-run, memoize by name, write-before-advance | `step.waitForEvent` + DO alarm | yes (DO evict, alarm wakes) | step idempotent |
| **Trigger.dev** | CRIU (process image) | n/a (frozen memory) | container checkpoint image | CRIU freeze/restore at `wait.*` | token waitpoint (WAITING→COMPLETED/TIMED_OUT) | yes (CRIU freeze) | NONE |
| **LittleHorse** | Event-source (Kafka) | NodeRun in WfRun | Kafka command log; RocksDB view | re-apply command log | ExternalEvent (correlation guid) + UserTask | yes (WfRun idles) | WfSpec compiled (deterministic by construction) |
| **AWS SFN** | Managed state machine | ASL state name | managed (opaque) | managed | task token (`.waitForTaskToken`) + heartbeat | yes | ASL DSL (not code) |

The pattern jumps out: **memoization + Postgres + named-promise HITL + worker-freed-on-wait** is the modal column choice, and it's exactly the Verso target.

### The two durability families — and which Verso should pick

Every target falls into one of two families. Verso's headline decision is which to build.

**Family A — Event-sourced replay (re-run the whole body, match against a log):**
- Temporal: replay the workflow against event history; per-type `seq` matched against recorded events; sandbox + custom event loop to keep the body deterministic.
- Restate: journal-per-invocation; the Rust VM replays the journal; `do_progress` decides replay-vs-execute-vs-suspend per await.
- LittleHorse: Kafka command log re-applied; RocksDB is a materialized view.
- Trigger.dev: degenerate case — the "log" is the frozen process image (CRIU); no replay, restore.

**Family B — Memoization (re-enter the function, skip already-done steps by key, run forward to first miss):**
- DBOS: `operation_outputs(workflow_uuid, function_id)` — step id = call-order `function_id`.
- Inngest: `steps: {sha1(name[:n]): output}` — step id = content hash, refactor-tolerant.
- Windmill: `completed_steps` JSONB — step id = `name`/`name_n` ordinal.
- LangGraph: per-channel versioned blobs; step = superstep; resume via `versions_seen`.
- Cloudflare: game loop, memoize by step name in DO SQLite.
- Resonate: generator yields; each `ctx.run` checkpoints; step id = `parent.counter` path.

**The verdict for Verso (informed by the input's own analysis + the source reads):** a ReAct loop is inherently dynamic — the next action depends on LLM output — so full event-sourced replay (Family A) is the wrong fit: it requires the body be deterministic, which an LLM-driven loop is not, and forces a sandbox (Temporal) or a compiled VM (Restate) to enforce that. **Family B memoization is the correct base model.** Within B, the cleanest realization for Verso is the **Cloudflare game loop** (re-enter, memoize by key, run to first miss) using the **Inngest content-addressed step id** (`sha1(name[:n])`, not order-based), persisted via the **DBOS two-table Postgres schema** with **write-before-advance**, exposed through the **Resonate per-call `durable=True`** seam, with the **LangGraph `BaseCheckpointSaver` 5-method interface** as the pluggable-backend boundary (InMemory ↔ Postgres). That single sentence is the synthesized Verso durable architecture.

### Convergent invariant 1 — write-before-advance

DBOS (record_operation_result before return), Inngest (206 persists before re-POST), Windmill (`_StepSuspend` persists `completed_steps` before dispatch), Cloudflare (`transactionSync()` before loop advance), LangGraph (`put`/`put_writes` after each superstep before next). **Every memoization system persists the step result before allowing the loop to advance.** This is non-negotiable for crash-safety: a crash in the gap between "step ran" and "result persisted" must replay the step, never skip it. Verso MUST persist atomically before advancing.

### Convergent invariant 2 — step identity is the whole ballgame

Three schemes, ranked for Verso:
1. **Content hash of a human name + loop counter** (Inngest `sha1(name[:n])`) — refactor-tolerant, loop-safe, portable. **Best for Verso.**
2. **Hierarchical path** (Resonate `parent.counter`) — globally addressable, good for child-agent lineage; order-dependent.
3. **Call-order ordinal** (DBOS `function_id`, Windmill `name_n`, Temporal `seq`) — simplest, but brittle to refactors and reordering.

The order-based schemes (3) impose "call steps in the same order on replay." The content-hash scheme (1) only requires the *name string* be stable. For an agent loop a developer edits often, (1) is strictly safer.

### Convergent invariant 3 — the HITL token is universal

Resonate Durable Promise, Restate Awakeable, Trigger.dev token waitpoint, AWS task token, LittleHorse ExternalEvent guid, Hatchet `wait_for` signal_key, DBOS recv topic — **all the same primitive**: an opaque external identifier the run yields on; any out-of-band system resolves it with a payload; the run has zero coupling to the resolver. The only design variation is naming (named vs generated id) and channel (HTTP PATCH vs gRPC vs SQS). Temporal's signal/query/update trio and LangGraph's `interrupt()` are the *outliers* (in-process, framework-coupled) and are worse for async human approval. **Verso's HITL = a named durable promise resolved over HTTP** (adopt the Resonate Durable Promise spec), with the SFN heartbeat/timeout and new-token-on-retry refinements.

### Convergent invariant 4 — release the worker during a wait

Temporal (sticky cache eviction), Restate (`Suspended` → HTTP returns, worker freed), Hatchet (durable eviction during `wait_for`), Windmill (`_StepSuspend` frees slot), Trigger.dev (CRIU freeze), Inngest (stateless, no resident process), CF (DO evicted, alarm rehydrates). **No system holds a worker thread blocked during a long HITL wait.** A Verso agent paused for human approval for hours must hold zero compute — the checkpoint is persisted, the worker is released, and an external resolve (or scheduler alarm) re-drives the run.

---

## → Verso Implications

1. **Build Family B (memoization), not Family A (replay).** A ReAct loop is non-deterministic by nature; do not impose a sandbox or a deterministic-body contract. Re-enter the agent function, memoize completed steps, run forward to the first uncached step. (CF game loop + DBOS storage.)

2. **Step id = `sha1(step_name)` + `:n` loop counter** (Inngest scheme). Content-addressed, refactor-tolerant. Reject order-based ids (DBOS/Temporal) — they break when a developer reorders the loop.

3. **Two-table Postgres checkpoint store** (DBOS): `agent_runs(run_id PK, status, input, output, error, executor_id, recovery_attempts, version)` + `step_outputs(run_id, step_hash, output, error, started_at, completed_at PK(run_id, step_hash))`. Status enum `{PENDING, SUSPENDED, SUCCESS, ERROR, CANCELLED, MAX_RECOVERY_EXCEEDED}`. Postgres-only default (no Redis/Kafka), per DBOS's >40K-steps/sec proof.

4. **Write-before-advance, atomically.** Persist the step result (and any state mutation, in the same transaction — DBOS piggyback) before the loop advances. A crash in the gap re-runs the step; it never skips it.

5. **`BaseCheckpointSaver`-style 5-method backend interface** (LangGraph): `get_run`/`list`/`put_step`/`put_run`/`next_step_version`. InMemory impl for `durable=False`, Postgres for `durable=True`, identical executor above. The backend is pluggable (Postgres default, Kafka-WAL à la LittleHorse for high throughput, Resonate-promise-spec for HITL).

6. **Per-call `durable=True`** (Resonate), default-on, overridable to `False`. Applied at the step granularity (`yield ctx.step(...).options(durable=False)`), not the agent granularity. This is the literal seam.

7. **HITL = named Durable Promise over HTTP.** Implement the Resonate Durable Promise spec (`POST /promises`, `PATCH /promises/{id} {state:RESOLVED, value}`, callback registration). Add the SFN refinements: `SendTaskHeartbeat`-style keep-alive with a timeout → `States.Timeout`, and **a fresh promise id on step retry** so a stale callback can't resolve a retried step.

8. **Release the worker on wait.** A `durable=True` agent that hits a HITL promise persists its checkpoint and returns; the worker is freed. An external resolve or a scheduler alarm (CF pattern — back long waits on any job scheduler, not `asyncio.sleep`) re-drives the run.

9. **`SET_SUSPENDABLE` boundary marker** (Trigger.dev): even in memoization, explicitly mark "blocked on a waitpoint, safe to persist+evict" vs "executing a step, do not checkpoint mid-step" — clean lifecycle for the executor.

10. **Wrap nondeterminism in a checkpointed call** (Resonate): rather than forbidding `time()`/`random()` (Temporal's sandbox approach), let any side-effect be a journaled step — its result is persisted and replays identically. More permissive and more natural for agent code.

11. **`MAX_RECOVERY_ATTEMPTS` poison-pill** (DBOS, default 100): a step that crashes the process on every recovery must eventually be flipped to a terminal failed state, not retried forever.

12. **Three durability modes** (LangGraph `sync`/`async`/`exit`): expose the latency-vs-durability knob. `sync` (persist before next step) for critical agents, `async` (persist concurrently) as default, `exit` (persist only on completion) for cheap throwaway runs. Plus a per-step `memo`-vs-`task` weight (Windmill): inline-checkpoint cheap steps in-process, dispatch heavy steps as child jobs.

---

## Synthesized Verso Durable Substrate (DESIGNED — composed from the reads above)

This is the concrete architecture the twelve teardowns point to. Every element is attributed to its source system; this is DESIGNED (Verso's gap-fill), assembling KNOWN mechanisms.

### Schema (Postgres default backend) — DBOS shape + Inngest step id + LangGraph versioning

```sql
-- one row per agent run (DBOS workflow_status shape)
CREATE TABLE verso_runs (
  run_id        TEXT PRIMARY KEY,         -- = SetWorkflowID idempotency key (DBOS)
  agent_name    TEXT NOT NULL,
  status        TEXT NOT NULL,            -- PENDING|SUSPENDED|SUCCESS|ERROR|CANCELLED|MAX_RECOVERY_EXCEEDED (DBOS enum)
  input         JSONB, output JSONB, error JSONB,
  executor_id   TEXT,                     -- which worker owns it (DBOS recovery filter)
  recovery_attempts INT DEFAULT 0,        -- DBOS poison-pill (cap 100)
  agent_version TEXT,                     -- in-flight upgrade guard (DBOS application_version / LH old_wf_spec_versions)
  created_at BIGINT, completed_at BIGINT,
  durability    TEXT DEFAULT 'async'      -- sync|async|exit (LangGraph)
);
CREATE INDEX verso_runs_pending ON verso_runs(created_at) WHERE status='PENDING';  -- DBOS partial index

-- the step journal (DBOS operation_outputs + Inngest content-addressed key)
CREATE TABLE verso_steps (
  run_id     TEXT NOT NULL REFERENCES verso_runs(run_id) ON DELETE CASCADE,
  step_hash  TEXT NOT NULL,               -- sha1(step_name) or sha1(f"{name}:{n}") for loop iter (Inngest)
  step_name  TEXT NOT NULL,               -- human-readable, for debugging
  kind       TEXT NOT NULL,               -- RUN|LLM|TOOL|SLEEP|WAIT (Hatchet kind + Inngest AI_GATEWAY)
  output     JSONB, error JSONB,
  started_at BIGINT, completed_at BIGINT,
  PRIMARY KEY (run_id, step_hash)         -- DBOS composite PK
);

-- HITL durable promises (Resonate Durable Promise spec, verbatim)
CREATE TABLE verso_promises (
  id TEXT PRIMARY KEY, state TEXT NOT NULL,         -- PENDING|RESOLVED|REJECTED|REJECTED_CANCELED|REJECTED_TIMEDOUT
  timeout BIGINT, param JSONB, value JSONB, tags JSONB,
  ikey_create TEXT, ikey_complete TEXT,              -- two-key idempotency (Resonate)
  run_id TEXT, step_hash TEXT,                       -- lineage the spec lacks (Verso addition)
  created_on BIGINT, completed_on BIGINT
);
```

### Executor (the CF game loop + Windmill suspend + write-before-advance)

```python
def run_durable(agent_fn, run_id, backend):
    run = backend.get_or_create_run(run_id)          # DBOS SetWorkflowID idempotency
    completed = backend.load_steps(run_id)            # {step_hash: output}  (Inngest memo map)
    ctx = DurableCtx(run_id, completed, backend)
    try:
        result = agent_fn(ctx)                         # CF game loop: re-enter, run forward to first miss
        backend.finish(run_id, SUCCESS, result)        # write-before-advance: terminal state persisted
    except StepSuspend as s:                           # Windmill _StepSuspend: cache miss on a wait
        backend.persist(run_id, completed, pending=s)  # persist completed steps, mark SUSPENDED, FREE WORKER
        # external resolve or scheduler alarm re-invokes run_durable later

class DurableCtx:
    def step(self, name, fn, *, durable=True):         # Resonate per-call durable flag
        h = sha1(self._key(name))                      # Inngest content-addressed id (+ :n loop counter)
        if h in self.completed: return self.completed[h]   # memoized → instant (every Family-B system)
        if not durable: return fn()                    # transient
        out = fn()                                     # run the LLM/tool (the "activity" — Temporal boundary)
        self.backend.put_step(self.run_id, h, name, out)   # WRITE-BEFORE-ADVANCE (DBOS/Inngest/CF/Windmill)
        self.completed[h] = out; return out
    def promise(self, id, timeout):                    # Resonate/SFN named-promise HITL
        h = sha1(self._key(f"promise:{id}"))
        if h in self.completed: return self.completed[h]
        self.backend.create_promise(id, timeout, run_id=self.run_id, step_hash=h)  # Resonate spec
        raise StepSuspend(waiting_on=id)               # suspend, free worker (universal invariant 4)
```

### HITL resolve (Resonate spec + SFN refinements)

External system: `PATCH /promises/{id} {state:RESOLVED, value, idempotency-key}` (Resonate). Verso's backend: validate `state` transition (PENDING→terminal only), write `value` into `verso_steps[run_id, step_hash]` so the resumed game loop finds it memoized, flip promise to RESOLVED, re-dispatch the run. SFN refinements applied: a `heartbeat` deadline → auto-`REJECTED_TIMEDOUT` if no resolve/heartbeat in N seconds; **a fresh promise id (and step_hash) generated on step retry** so a stale callback from a prior attempt can't resolve the retried step.

### What is NOT in this sketch (deliberately, per the reads)

- No sandbox / module-reimport (Temporal) — memoization doesn't replay the body, so global-state isolation is unneeded.
- No CRIU / container freeze (Trigger.dev) — Verso is pip-installable, can't assume container orchestration.
- No Kafka (LittleHorse) by default — Postgres handles >40K steps/sec (DBOS proof); Kafka-WAL is an optional high-throughput backend behind the same `BaseCheckpointSaver` interface.
- No ASL/JSON DSL (SFN) — Verso's thesis is Python code.

This sketch IS the answer to "can a senior engineer build the durable substrate from this teardown?" — schema, executor loop, step-id scheme, write ordering, and HITL flow, each traced to the system that proved it.

---

## Freshness & Confidence

**Durable (architecture, low churn — safe to design against):** the four-subsystem decomposition; the two durability families (event-source vs memoize); write-before-advance; the convergent HITL token/promise; worker-freed-on-wait; the DBOS two-table Postgres shape; the LangGraph `BaseCheckpointSaver` contract; the Inngest content-addressed step id; the Resonate Durable Promise spec data model + state machine; the Restate journal/`do_progress` model; Temporal's Commands-vs-Events + seq matching. These are years-stable design primitives.

**Semi-fresh (APIs, may drift — re-verify before copying verbatim):** exact method signatures and constants (DBOS `MAX_RECOVERY_ATTEMPTS=100`, recv 60s fallback, LangGraph delta-channel 5000-superstep bound, Inngest 206/`NO_RETRY` header shape, Restate discovery v2/v3/v4, Trigger.dev `idempotencyKey` 2048-char cap, SFN 1-year wait quota). Pinned to HEAD as of 2026-06-05; SDK APIs evolve.

**Inferred (not from source — flagged inline):** Restate's 3ms/94K-ops perf numbers + Bifrost internals (blog, not the cloned SDK — the SDK only shows the VM boundary, the Rust server `restate` repo was not cloned this pass); Cloudflare V2's 50K-concurrent ceiling and DO-per-instance mapping (blog, closed infra); Trigger.dev's CRIU freeze/restore + version-locking (blog rationale — the SDK shows the `SET_SUSPENDABLE` IPC boundary but the supervisor/CRIU layer is closed); LittleHorse's RocksDB-from-changelog recovery (architecture docs, not traced in the proto/SDK read).

**Not covered (out of scope / would need more cloning):** the Restate Rust server (`restatedev/restate`) Bifrost log crate and service-protocol crate — only the Python SDK + VM boundary were read; the Temporal Rust `sdk-core` state machines (only the Python side + bridge boundary); the Hatchet/LittleHorse/Windmill server engines beyond the schemas and Python SDKs; `cloudflare/workerd` was referenced for the DO primitive but not cloned. If Verso commits to the Restate journal model or the Kafka-WAL model, those server repos are the next read.

**Cross-references:** `infra-serving.md` (this folder) — the streaming/cancellation/watchdog contract the durable layer sits behind (Restate's bidirectional ASGI frame protocol is the durable-journal analog of the SSE token streaming there). `researchfms/teardowns/PREFECT.md` — Prefect's FastAPI server layer only; its orchestration engine is uncovered and out of scope (DAG-first, not ReAct-first). When Verso's durable substrate is built, it pairs with the serving layer: durable steps wrap LLM/tool calls that themselves stream via the `infra-serving` contract.

---

## Coverage Expansion (2026-06-05) — Rust Server Internals (Restate Bifrost + Temporal sdk-core)

*The first pass read the Python SDKs + the cross-FFI VM/bridge boundary but explicitly did NOT read the Rust server crates (see "Not covered" note above). This pass closes that gap by reading the actual Rust. Sources (all `git clone --depth=1` HEAD, 2026-06-05): `restatedev/restate` — `crates/bifrost/src/{loglet,types,record,bifrost,loglet_wrapper}.rs`, `crates/bifrost/src/providers/{local_loglet,replicated_loglet}/*`, `crates/types/src/logs/metadata.rs`, `crates/service-protocol/src/message/header.rs`, `service-protocol/dev/restate/service/protocol.proto`, `crates/worker/src/partition/mod.rs`; `temporalio/sdk-core` — `ARCHITECTURE.md`, `crates/sdk-core/src/worker/workflow/machines/{mod,timer_state_machine,workflow_machines}.rs`; `temporalio/sdk-python` — `temporalio/bridge/src/worker.rs`. This SUPERSEDES the prior "Inferred (blog)" Bifrost claims and the "Not covered" note — those are now KNOWN from source.*

### Restate — Bifrost log + service-protocol wire format

**The two-coordinate addressing scheme (the core abstraction).** KNOWN, `crates/types/src/logs/metadata.rs` + `crates/bifrost/src/types.rs`. A Restate *log* is NOT a single physical file — it is a **chain of segments**, each segment a separate *loglet* instance (possibly a different provider). Two distinct sequence-number spaces:
- **`Lsn`** (`u64`) — the **virtual** log-sequence-number, monotonic across the *entire* log, never resets across segments. This is what the partition processor reads against.
- **`LogletOffset`** (`u32`) — the **physical** offset *within one loglet/segment*; `OLDEST = 1`, `INVALID = 0` (`loglet.rs:66-67`). Each new segment restarts its offset at `OLDEST`.

The bridge between them is `LsnExt` (`types.rs:20-70`), a sealed trait impl'd only for `Lsn`. `base_lsn.offset_by(offset)` = `base_lsn + (offset - OLDEST)` → virtual Lsn; `lsn.into_offset(base_lsn)` is the inverse, with `#[track_caller]` panics on overflow / `base_lsn == INVALID` / `base_lsn > lsn` (`types.rs:29-69`). So every read against a virtual Lsn first finds the segment, subtracts that segment's `base_lsn`, and reads the loglet at the physical offset. **For Verso: a durable journal should separate "global position" from "physical storage position" so the storage tier can be swapped/segmented under a stable virtual address.** (KNOWN)

**The chain / segment layout.** KNOWN, `metadata.rs:505-545`. `struct Chain { chain: BTreeMap<Lsn, LogletConfig> }` — a `BTreeMap` keyed by each segment's `base_lsn`. A `Segment<'a>` is a *view*: `{ base_lsn: Lsn, tail_lsn: Option<Lsn>, config: &LogletConfig }` where `tail_lsn = None` means "this is the open/writeable tail segment" (`metadata.rs:517-519`). `LogletConfig { kind: InternalKind, params: LogletParams(ByteString), index: SegmentIndex(u32), created_at }` — `(log_id, SegmentIndex)` is the globally-unique collision-free loglet identity (`:534-535`). `InternalKind ∈ {Local, InMemory, Replicated, Sealed}` (`:598-609`); `Sealed` is a zero-record seal-marker segment appended to mark a chain immutable (`is_seal_marker()`, `:612`). `find_segment_for_lsn(lsn)` (`:928-961`) does a **linear backward search** (`chain.iter().rfind(|(base,_)| lsn >= base)`) — returns `MaybeSegment::Some(Segment)` or `MaybeSegment::Trim { next_base_lsn }` if the Lsn fell below the oldest segment (i.e. trimmed away) (`:800-806`). The deliberate `range(Bound::Excluded(base)..)` re-walk to find `tail_lsn` (`:948-954`) carries an in-source comment that BTreeMap range iterators don't advance after returning `None` — a real footgun they document inline. `LogletWrapper` (`loglet_wrapper.rs:41-54`) is the runtime object that pairs a `base_lsn`/`tail_lsn`/`SegmentIndex` with the `Arc<dyn Loglet>` and does the LSN↔offset translation on `create_read_stream` (`:101-114`: `start_lsn.into_offset(base_lsn)`, and `to = tail_lsn.prev().into_offset(base_lsn)` because `tail_lsn` is exclusive but the loglet `to` is inclusive). (KNOWN)

**The `Loglet` trait (the storage-substrate abstraction).** KNOWN, `loglet.rs:70-153`. `trait Loglet: Send + Sync` — the seam every provider implements: `enqueue_batch(payloads: Arc<[Record]>) -> LogletCommit` (append, returns a future resolving to the **last offset** in the batch), `create_read_stream(filter, from, to) -> SendableLogletReadStream`, `watch_tail() -> BoxStream<TailState<LogletOffset>>`, `find_tail(FindTailOptions) -> TailState<LogletOffset>`, `get_trim_point() -> Option<LogletOffset>`, `trim(trim_point)`, `seal()`. The offset semantics are spelled out as ASCII art (`:45-53`): `[ trim_point .. last_committed(released) .. tail ]` where **tail = first unwritten position** and "released = can be delivered to readers". `FindTailOptions ∈ {ConsistentRead (default, accurate), Fast (cheap, possibly stale, falls back to ConsistentRead)}` (`:155-164`). `LogletCommit` is a `oneshot`-backed future (`:195-238`) with constructors `sealed()` / `reconfiguration_needed(reason)` / `resolved(offset)` / `deferred() -> (LogletCommit, LogletCommitResolver)` for pipelined background commits. Seal contract (`:148-152`): appends MUST NOT succeed after the first `TailState::Sealed()` is observed — this is the linearizability hinge for reconfiguration. (KNOWN)

**`Record` / `LogEntry` — the on-log payload.** KNOWN, `record.rs`. A read yields `LogEntry<S=Lsn> { offset: S, record: MaybeRecord<S> }` where `MaybeRecord ∈ {Data(Record), TrimGap(Gap), Filtered(Gap), DataLoss(Gap)}` (`:191-198`) — i.e. a read stream interleaves real records with **gap markers**: `TrimGap` (records below this were trimmed), `Filtered` (records skipped by a `KeyFilter` — the reader advances past them), `DataLoss` (irrecoverable hole, surfaced as an error upstream). `RecordKind ∈ {Data, TrimGap, DataLoss, Filtered}` (`:23-29`). `Gap<S> { to: S }` is inclusive (`:200-204`). `LogEntry::with_base_lsn` (`:42-60`) is where a per-loglet `LogEntry<LogletOffset>` is re-stamped into a global `LogEntry<Lsn>` on the way out. `InputRecord<T>` carries `{ created_at: NanosSinceEpoch, keys: Keys, body: PolyBytes }` — `PolyBytes ∈ {Typed(Arc<T>), Bytes(Bytes)}` is a zero-cost type-erasure (`:206-247`, `from_bytes_unchecked` is `unsafe` requiring the caller to guarantee a valid storage-encoding). `Keys` are the routing/partition keys carried *in the record* so the partition processor can filter (`KeyFilter`). (KNOWN)

**The local-loglet — RocksDB as a segmented WAL.** KNOWN, `providers/local_loglet/`. Two column families: `DATA_CF = "logstore_data"`, `METADATA_CF = "logstore_metadata"` (`log_store.rs:29-30`), with `DATA_CF_BUDGET_RATIO = 0.85` of the memory budget (`:32`, `const_assert!(< 1.0)`). **Key encoding** (`keys.rs`): a data key is `b'd' || loglet_id:u64(BE) || offset:u64(BE)` (`:46-53` — offset is logically `u32` but stored as `u64` BE "for backward compatibility and future-proofing", asserted to fit `u32` on read `:60-61`); a metadata key is `b'm' || loglet_id:u64 || kind:u8` where `MetadataKind ∈ {Unknown=0, LogState=1}` (`:69-73`, `:102-107`). The big-endian offset means **RocksDB's lexicographic key order == log order**, so a prefix-seek over `b'd'||loglet_id` is a sequential scan of the loglet (`DATA_KEY_PREFIX_LENGTH = 1+8 = 9`, `:17`, used as the RocksDB prefix-extractor). **`LogState`** (`log_state.rs:139-148`) is the per-loglet manifest: `{ release_pointer: u32, trim_point: u32, sealed: bool }`. It is updated via **RocksDB merge operators**, not read-modify-write: `log_state_full_merge` / `log_state_partial_merge` (`:178-270`) fold a stream of `LogStateUpdate ∈ {ReleasePointer(u32), TrimPoint(u32), Seal}` where release-pointer and trim-point use `.max()` (**monotonic, can only move forward** — `:216`, `:220`) and `Seal` sets the flag — so concurrent appenders/trimmers never lose an update and never need a lock for the manifest. **Append path** (`mod.rs:150-206`): holds an async `next_write_offset` mutex *only* to assign the contiguous offset and enqueue in order (so an ack of offset N implies all `< N` are durable, `:168-171`), bounded `assert!(payloads.len() <= u16::MAX)` (65535 records/batch, `:163`), then `last_committed_offset.fetch_max(offset, AcqRel)` publishes the release pointer and `notify_readers(is_sealed, release_pointer)` wakes tailing streams. **`find_tail`** (`:208-221`) returns `TailState::{Open|Sealed}(last_committed.next())` — tail = last committed + 1. **`trim`** (`:235-`) clamps `new_trim_point.min(last_committed)`, takes a `trim_point_lock` to serialize, and no-ops if already trimmed past. (KNOWN — this REPLACES the prior INFERRED "RocksDB state is ephemeral/derived" blog claim with the actual storage layout.)

**The replicated-loglet — Restate's native replication.** KNOWN, `providers/replicated_loglet/sequencer.rs`. The `Replicated` provider is a **single-writer sequencer + a NodeSet of log-servers**. `struct Sequencer` (`:104-121`) holds `next_write_offset: CachePadded<AtomicU32>`, a `record_permits: Arc<Semaphore>` (bounds in-flight records for backpressure), a `SpreadSelector` (`SelectorStrategy`, `:62`) that picks which log-servers in the `NodeSet` get each record according to a `ReplicationProperty` (the replication factor / f-majority), and a `known_global_tail: TailOffsetWatch` (`:60`) — the global commit point, advanced once an f-majority of log-servers ack. "Only one leader sequencer is alive per loglet-id, tied to the generation of this node-id" (`:101-103`) — generational fencing prevents split-brain writers, exactly the `LeaderEpoch` fencing the partition processor uses. `MAX_OFFSET_SOFT = i32::MAX` (`:46`) is the soft per-loglet record ceiling. `RecordCache` (`:118`) keeps recently-appended records hot for re-delivery to lagging readers without a log-server round-trip. The seal flow: `mark_as_maybe_sealed()` → `known_global_tail.is_sealed()` short-circuits new appends (`:205`). The reconfiguration story (vs `ErrorRecoveryStrategy` in `bifrost.rs:48-58`: `Wait` / `ExtendChainAllowed` (default) / `ExtendChainPreferred`): on a stuck write, Bifrost **seals the current loglet and appends a new segment to the chain** (a new `LogletConfig` at a higher `base_lsn`) rather than blocking — the virtual `Lsn` stays continuous while the physical loglet underneath changed. **For Verso: replication = single-writer-sequencer + NodeSet + f-majority-ack + generational-fencing; reconfiguration = seal-and-extend-chain, NOT in-place mutation.** (KNOWN — confirms & details the prior INFERRED "Delos/LogDevice-style segmented log" claim.)

**Object-storage tiering — via partition-store snapshots, NOT the log itself.** KNOWN, `crates/partition-store/src/snapshots/`. The prior pass's INFERRED claim of a "tiered object-storage tier" for Bifrost is **partly imprecise** — the *log* tiers via the loglet provider (local RocksDB or replicated log-servers), while *durable long-term state* tiers to object storage as **RocksDB SST snapshots** of the partition store (`snapshots/snapshot_task.rs`, `snapshots/metadata.rs`). The trim point of the log can advance once a snapshot covering that Lsn range is durable in object storage — so the log is a bounded recent window and the object store holds the compacted materialized state. [CORRECTION 2026-06-05] The prior file's line ("Bifrost = ... embedded replicated log tier → object-storage tier; RocksDB state is ephemeral/derived") conflated two mechanisms: Bifrost (the log) tiers across loglet providers; the *partition store* (RocksDB) is what snapshots to object storage. RocksDB is "derived" in that it's rebuilt by replaying the log, but it is itself the thing that persists to object store, not Bifrost. (KNOWN)

**The service-protocol wire format — the journal-entry-over-HTTP framing.** KNOWN, `service-protocol/dev/restate/service/protocol.proto` + `crates/service-protocol/src/message/header.rs`. Every frame on the SDK↔server bidirectional HTTP stream is `[ 8-byte big-endian header ][ protobuf body ]`. The **64-bit header** packs (`header.rs:351-391`): `ty_code:u16 << 48 | flags | length:u32` where `length` = body byte-length (low 32 bits), and two flag bits — `COMPLETED_MASK = 0x0001_0000_0000` (bit 32, only on completable entries) and `REQUIRES_ACK_MASK = 0x8000_0000_0000` (bit 47). The **type-code taxonomy** is a `0xKK00 + n` scheme grouping by `MessageKind` (`:117-142`):
| Range | `MessageKind` | Members (type-code) |
|---|---|---|
| `0x0000+n` | **Core** | Start `0x0000`, Completion `0x0001`, Suspension `0x0002`, Error `0x0003`, EntryAck `0x0004`, End `0x0005` |
| `0x0400+n` | **IO** | InputEntry `0x0400`, OutputEntry `0x0401` |
| `0x0800+n` | **State** | GetState `0x0800`, SetState `0x0801`, ClearState `0x0802`, ClearAllState `0x0803`, GetStateKeys `0x0804`, GetPromise `0x0808`, PeekPromise `0x0809`, CompletePromise `0x080A` |
| `0x0C00+n` | **Syscall** | Sleep `0x0C00`, Invoke(Call) `0x0C01`, BackgroundInvoke(OneWayCall) `0x0C02`, Awakeable `0x0C03`, CompleteAwakeable `0x0C04`, SideEffect(Run) `0x0C05`, CancelInvocation `0x0C06`, GetCallInvocationId `0x0C07`, AttachInvocation `0x0C08`, GetInvocationOutput `0x0C09` |
| `& 0xFC00 != 0` | **CustomEntry** | any high-range code → user-defined entry (`:213`) |

`has_completed_flag()` (`:92-107`) is true only for the **completable** entries (GetState/GetStateKeys/Sleep/Invoke/Awakeable/{Get,Peek,Complete}Promise/GetCallInvocationId/AttachInvocation/GetInvocationOutput) — these emit a command *then later* a completion notification; non-completable entries (SetState, Output, etc.) are fire-once. (KNOWN)

**The Commands-vs-Notifications journal model (protocol V7).** KNOWN, `protocol.proto`. The modern journal (the proto's "Immutable journal", V5+) splits every durable op into a **Command** (`0x0400`-range message, the operation) and zero-or-more **Notifications** (`0x8000`-range, the results). A command declares its `result_completion_id: u32` and the matching notification carries the same `completion_id` (`NotificationTemplate`, `:262-280`: id is a `oneof {completion_id | signal_id | signal_name}`, result is a `oneof {Void | Value | Failure | invocation_id | state_keys}`). **This is Restate's analog of Temporal's Command↔Event seq-matching** — but keyed by an explicit `completion_id` carried in the proto, not a positional seq. Notable taxonomy details: `CallCommandMessage` (`:513-539`) produces **two** notifications — first a `CallInvocationIdCompletionNotificationMessage` (the child's invocation id, `invocation_id_notification_idx`) then a `CallCompletionNotificationMessage` (the actual result). `SleepCommandMessage` (`:491-498`) carries `wake_up_time: u64` (absolute, ms since epoch — durable timers are absolute deadlines, not relative). `RunCommandMessage` (`:627-630`) is the side-effect step but the **result is proposed out-of-band** via `ProposeRunCompletionMessage` (`0x0005`, `:205-211`) which "won't be written to the journal immediately, but will appear later as a new notification" — the runtime acks with `ProposeRunCompletionAckMessage` (`0x0007`, `:246-248`) whose ordering is "relative to the ordering of notifications" so on replay the `RunCompletionMessage` appears in the same relative position (`:232-242`, a worked example is in the proto comments). This is exactly the journal-position-as-identity model from the first-pass `do_progress` analysis — now confirmed at the wire level. (KNOWN)

**Suspension & the future-combinator tree.** KNOWN, `protocol.proto:109-156`. When an invocation has nothing to do and is awaiting external input, the SDK sends a `SuspensionMessage` (`0x0002`) carrying a `Future` — a *recursive combinator tree* describing the await point: `Future { waiting_completions: [u32], waiting_signals: [u32], waiting_named_signals: [string], nested_futures: [Future], combinator_type }` where `CombinatorType ∈ {FIRST_COMPLETED (Promise.race), ALL_COMPLETED (allSettled), FIRST_SUCCEEDED_OR_ALL_FAILED (any), ALL_SUCCEEDED_OR_FIRST_FAILED (all)}` (`:110-147`). So `Promise.all([completion_3, Promise.race([signal_1, signal_2])])` serializes to a two-level `Future` tree (the proto gives this exact example, `:129-140`). The runtime knows precisely which completions/signals must arrive to wake the invocation — this is how Restate suspends-and-frees the worker (vs Temporal's resident sticky cache) while still resuming on the *right* event. `ErrorMessage` (`:159-185`) defines `JOURNAL_MISMATCH=570` (replay divergence — the non-determinism detector) and `PROTOCOL_VIOLATION=571`, plus `next_retry_delay: u64` and `should_pause: bool` (the per-entry retry/pause override the first pass saw from the Python side). `BuiltInSignal::CANCEL=1` (`:796-800`) is the reserved cancellation signal. (KNOWN)

**The Partition Processor — the state machine fed by the log.** KNOWN, `crates/worker/src/partition/mod.rs`. This is the "RocksDB as ephemeral materialized view" mechanism the first pass inferred. The processor `run()` loop (`:623-790`) is a `tokio::select!` whose main arm reads a **batch** of records from a Bifrost read stream (`read_entries(..., max_command_batch_size, ...)` — default **32**, `crates/types/src/config/worker.rs:183`) into a `command_buffer`, opens **one `PartitionStoreTransaction`** (`:621`), and for each entry: `maybe_advance` (`:993-1054`) decodes the `LogEntry` — a `TrimGap` is a fatal `TrimGapEncountered` error (must restore from snapshot), a `DataLoss` gap is fatal, a `Filtered` gap just advances `applied_lsn`, a `Data` record proceeds — then writes `transaction.put_applied_lsn(lsn)` so the **applied-Lsn watermark is committed in the same transaction as the state mutations** (atomic state+position, exactly Restate's whole-system invariant). `apply_record` (`:1058-1148`) checks `is_targeted_to_me(keys)` (partition-key routing), **deduplicates** via `DedupInformation { producer_id, sequence_number }` (`:1079-1096` — `is_outdated_or_duplicate` + `put_dedup_seq_number`, the idempotency layer), then dispatches by `CommandKind`: `AnnounceLeader`/`UpdatePartitionDurability` are handled inline (leader fencing via `LeaderEpoch`, trim-queue advance), everything else goes to `state_machine.apply(envelope, created_at, lsn, txn, action_collector, vqueues, is_leader)` (`:1133-1143`). The state machine is **deterministic**: same log → same RocksDB state on every replica; only the **leader** flushes the `ActionCollector` (side effects: invoke SDKs, send timers) to the actuators (`:778-784`), followers apply the same state but suppress actions. `decode_record` (`:462-477`) transparently upgrades v1→v2 `Envelope` formats. **For Verso: the partition store is a pure function of the log prefix — recovery = replay-from-snapshot-Lsn; the leader/follower split (all apply, only leader acts) is how you run hot standbys of a durable agent without double-executing side effects.** (KNOWN — confirms the first-pass INFERRED "RocksDB state is derived from the log" with the actual apply loop.)

**For Verso:** the storage-substrate lesson is the **two-coordinate journal + pluggable loglet trait**: address durable steps by a *virtual* monotonic position (`Lsn`) that is stable across storage reconfiguration, while the *physical* substrate (`LogletOffset` within a segment) is swappable — local RocksDB for single-node, replicated NodeSet for HA, all behind one `Loglet` trait (`enqueue_batch`/`find_tail`/`trim`/`seal`). Steal four concrete mechanics: (1) **monotonic manifest via merge operators** — track `release_pointer`/`trim_point` with `max()`-fold merges so concurrent writers never need a lock; (2) **seal-and-extend-chain reconfiguration** — never mutate a sealed segment in place, append a new one and keep the virtual address continuous; (3) **state = pure fold of the log prefix** — the materialized store (RocksDB / Postgres / whatever) commits the applied-position watermark in the *same* transaction as the state mutation, so recovery is unambiguous replay from the last snapshot Lsn; (4) **leader-applies-and-acts / follower-applies-only** — run hot standbys that stay warm by applying the log but suppress side effects until they win the generational-fenced leadership. The wire-format lesson: frame every journal entry as `[type-code:u16 | flags | len:u32][protobuf]` with an explicit `completion_id` linking command→completion, and serialize the await point as a combinator tree so you can suspend-and-free the worker yet resume on exactly the right signal set.

### Temporal — sdk-core state machines + PyO3 bridge

**The three-layer split and where determinism actually lives.** KNOWN, `sdk-core/ARCHITECTURE.md`. The first pass attributed determinism to the Python `_WorkflowInstanceImpl` event loop. That is the *user-code driver*; the **replay/non-determinism engine lives in the Rust core**, language-agnostic, shared by every SDK (Python/TypeScript/Go/.NET/Ruby via FFI; Java/Go-classic have their own). The vocabulary (`ARCHITECTURE.md:36-61`): `HistoryEvent` (server's recorded history) → fed into → `StateMachine`s (one per durable op) → which emit `Command`s (proto commands sent back to server on WFT completion) and `MachineResponse`s (internal — push `WorkflowActivationJob`s to lang). The lang side only ever sees `WorkflowActivation` (jobs to run) in and `WorkflowActivationCompletion` (commands) out — it never touches `HistoryEvent`s. **All interactions pass through the `TemporalStateMachine` trait** (`machines/mod.rs:91-109`): `handle_command(CommandType)`, `handle_event(HistEventData)`, `is_final_state()`, `name()`. (KNOWN)

**The `fsm!` macro — declarative transition tables.** KNOWN, `machines/timer_state_machine.rs:22-46`. Each machine is generated by a `fsm!` macro (from the `rustfsm` crate) that takes a literal **transition table**: `State --(Event[, handler]) --> NextState`. The canonical timer machine's full table:
| From state | Event | Handler | To state |
|---|---|---|---|
| `Created` | `Schedule` | `on_schedule` | `StartCommandCreated` |
| `StartCommandCreated` | `CommandStartTimer` | — | `StartCommandCreated` (self) |
| `StartCommandCreated` | `TimerStarted(HistoryEventId)` | `on_timer_started` | `StartCommandRecorded` |
| `StartCommandCreated` | `Cancel` | `on_cancel` | `Canceled` |
| `StartCommandRecorded` | `TimerFired(TimerFiredEventAttributes)` | `on_timer_fired` | `Fired` |
| `StartCommandRecorded` | `Cancel` | `on_cancel` | `CancelTimerCommandCreated` |
| `CancelTimerCommandCreated` | `CommandCancelTimer` | `on_command_cancel_timer` | `CancelTimerCommandSent` |
| `CancelTimerCommandSent` | `TimerCanceled` | — | `Canceled` |
| `Canceled` | `Cancel` | — | `Canceled` (absorb spurious) |
| `Fired` | `Cancel` | — | `Fired` (absorb spurious) |

The state-progression encodes the durable lifecycle: the machine is `Created` when user code schedules a timer → `StartCommandCreated` once the `StartTimer` command is queued → `StartCommandRecorded` once the *server* echoes back a `TimerStarted` history event (`on_timer_started` stores the `HistoryEventId` so later `TimerFired` can be matched) → `Fired`. Two `TryFrom<HistEventData>` (`:109-133`) and `TryFrom<CommandType>` (`:135-145`) impls map server events/commands into the machine's event enum; an unmatched `HistEventData` returns `nondeterminism!("Timer machine does not handle this event")` (`:127`). The full machine set (`machines/*.rs`): activity, local_activity, timer, child_workflow, signal_external, cancel_external, cancel_workflow, complete_workflow, fail_workflow, continue_as_new_workflow, patch, update, upsert_search_attributes, modify_workflow_properties, nexus_operation, cancel_nexus_op, workflow_task. (KNOWN)

**Non-determinism detection — the two-tier error split, at the core.** KNOWN, `machines/mod.rs:120-184`. This is where the first pass's Python-level `RuntimeError` guard actually originates. The generic `TemporalStateMachine` impl over any `SM: StateMachine` distinguishes by *which direction* the invalid transition came from:
- **`handle_command`** (lang produced a command): `command_type.try_into()` the machine's event; on `MachineError::InvalidTransition` → `nondeterminism!("Unexpected command producing an invalid transition {cmd} in state {state}")` (`:133-137`); a command the machine can't even convert → `nondeterminism!("Unexpected command ... generated by a {machine} machine")` (`:141`).
- **`handle_event`** (server's history): on `MachineError::InvalidTransition` → **`fatal!`** ("transition is invalid during event", `:167-172`) — because the *server's recorded history* can't be wrong; an invalid transition while applying history means the SDK's machine is buggy, not that the user changed code.

So **`nondeterminism!` = the user's workflow code diverged from recorded history (the recoverable "fail the WFT, retry" path); `fatal!` = the SDK/history is internally inconsistent (unrecoverable).** (KNOWN — this is the Rust-side origin of the Python `RuntimeError` non-determinism guard documented in the first pass.)

**The WFT processing loop — events→machines→commands, matched by event-id.** KNOWN, `machines/workflow_machines.rs`. `WorkflowMachines` owns `all_machines: SlotMap<MachineKey, Machines>` (`:139`) and three indices: `machines_by_event_id: HashMap<i64, MachineKey>` (`:145`), `machines_by_protocol_instance_id` (for updates, `:148`), `id_to_machine: HashMap<CommandID, MachineKey>` (`:150`). `current_started_event_id: i64` (`:94`) is the replay cursor. The event-application split (`handle_event`, `:856-926`):
- **Command events** (events generated by a prior command, e.g. `ActivityTaskScheduledEvent` ← `ScheduleActivityTaskCommand`) route to `handle_command_event` (`:937-1000`): it pops the **front of the `commands` queue** (FIFO of commands the lang side emitted) and asserts the event matches — if the queue is empty, `nondeterminism!("No command scheduled for event {event}")` (`:980`). This is the positional command↔event matching: commands must be echoed back by the server in the exact order the workflow emitted them.
- **Events with an `initial_command_event_id`** (a result for an earlier command, e.g. `TimerFired` referencing the `TimerStarted` id) look up `machines_by_event_id.get(&initial_cmd_id)` (`:910-919`) → `nondeterminism!("this event had an initial command ID but we could not find a matching command")` if missing → `submachine_handle_event(mkey, event)`.
- **Non-stateful events** (`WorkflowExecutionStarted`, `WorkflowTaskScheduled`, `WorkflowExecutionSignaled`) go to `handle_non_stateful_event` (`:1002-`): `WorkflowExecutionStarted` calls `drive_me.start(workflow_id, str_to_randomness_seed(&original_execution_run_id), event_time, attrs)` (`:1020-1023`) — **the deterministic RNG seed is derived from the original run-id**, which is exactly the `randomness_seed` the first pass saw arrive at the Python `_WorkflowInstanceImpl`. Time is server-stamped: `set_current_time(event.event_time)` (`:1011-1017`) — the source of the Python layer's `_time_ns`.

`iterate_machines` (`:544-555`) is the driver tick: pull the lang side's iteration output (`fetch_workflow_iteration_output`), `handle_driven_results`, then `prepare_commands` (`:1125`) to collect the commands the machines produced for the WFT completion. `ready_to_apply_next_wft` / `can_take_next_wft_sequence(current_started_event_id)` (`:557-560`) gate whether a full next-WFT worth of events is buffered before activating lang. (KNOWN)

**The PyO3 bridge — protobuf bytes across the FFI, nothing else.** KNOWN, `sdk-python/temporalio/bridge/src/worker.rs`. The first pass noted the bridge must pass-through the sandbox; here is what actually crosses. The bridge is a thin `#[pymethods]` wrapper over `sdk-core`'s `Worker`. **The entire FFI contract is serialized protobuf `bytes` in both directions — no structured Python objects cross the boundary.** Poll methods (`:567-604`) return encoded bytes: `worker.poll_workflow_activation().await.encode_to_vec()` → `Ok(bytes)` (the Python side decodes into a `WorkflowActivation` proto); same shape for `poll_activity_task` / `poll_nexus_task`. Complete methods (`:606-655`) take `proto: &Bound<'_, PyBytes>` and `WorkflowActivationCompletion::decode(proto.as_bytes())` (prost decode) → `worker.complete_workflow_activation(completion).await`; decode failure → `PyValueError::new_err("Invalid proto")`; same for `complete_activity_task` / `complete_nexus_task`. `record_activity_heartbeat` (`:657-`) decodes an `ActivityHeartbeat` proto synchronously (no future). Async is bridged via `pyo3_async_runtimes::future_into_py` (`:570`) — a Rust future becomes a Python awaitable on the Python event loop captured in `event_loop_task_locals: Arc<OnceLock<TaskLocals>>` (`:38-39`). `assert_same_process("use worker")` (`:568`) guards against fork. **Replay** uses `HistoryPusher` (`:919-970`): `push_history(workflow_id, history_proto: &PyBytes)` does `History::decode(...)` and sends `HistoryForReplay` over a `tokio::mpsc::channel(1)` to the replay worker's stream — so the `Replayer` the first pass documented at the Python layer is backed by this single-slot channel feeding the same core machines. The `Payload` type the first pass mentioned crossing the FFI is just a field *inside* these protos — it never crosses as a distinct typed object; the whole activation (jobs, each carrying `Payload`s) is one prost-encoded blob. (KNOWN — this is the concrete FFI surface behind the first-pass `temporalio.bridge.temporal_sdk_bridge` passthrough note.)

**For Verso:** the FFI-boundary lesson is **serialize-everything-as-protobuf-bytes across the language seam** — the Rust core never exposes typed structs to Python, only `poll() -> bytes` / `complete(bytes)`; this makes the seam trivially stable, language-agnostic, and versionable (proto evolution = wire compat), and is why one Rust core serves every Temporal SDK. The state-machine lesson: model each durable op as an explicit FSM with a *declarative transition table* (the `fsm!` macro) rather than imperative if-ladders — this makes the legal state space auditable (the table IS the spec, and `transition_coverage.rs` tracks which transitions tests exercised) and localizes non-determinism detection to one place: an event that can't drive a legal transition is, by construction, a divergence. Crucially, **detect non-determinism in the core, not the language layer** — split it two ways: a divergence found while applying the *user's* commands is recoverable (`nondeterminism!` → fail-and-retry the task), while a divergence found while applying the *server's* history is a fatal internal bug (`fatal!`). If Verso ever wants multi-language agents over one durable engine, this Rust-core + protobuf-FFI + declarative-FSM shape is the proven blueprint; if Verso stays single-language Python, the lesson is narrower — keep the determinism engine (the command↔event matcher + the per-op FSMs) as one isolated, table-driven module, not scattered through the agent loop.
