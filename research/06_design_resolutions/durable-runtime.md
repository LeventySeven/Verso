# Durable Runtime (the Seam) — Verso Design Resolution

**Date:** 2026-06-05
**Subsystem:** `runtime/durable` — the tactical↔durable seam (PRD §6.1 + §10.8)
**Evidence base:** `03_teardowns/infra-durable-execution.md` (Temporal, DBOS, LangGraph, Restate, Inngest, Hatchet, Resonate, Windmill) + `03_teardowns/discovery-wildcard.md` (Anthropic Managed Agents, Google AX, Centaur, CF Project Think, Salus) + PRD v1.

---

## Decisions Resolved

### D1 — Build vs. Delegate the Durable Engine

**Choice:** BUILD in-house (pure Python + Postgres). Do NOT delegate to Temporal, Trigger.dev, or Restate for v1.

**Rationale:**
Temporal requires a running server (not self-contained), a full Rust-core FFI, and the sandbox/determinism model that is deliberately heavier than Verso needs. Restate ships a compiled Rust VM. Trigger.dev imposes CRIU and container infrastructure. All three bring operational complexity that contradicts the "dogfood-first, personal infra" framing. The PRD seam test is: flip `durable=True`, zero loop-code changes — that test is trivially satisfied by an in-house step-memoization engine and impossible to satisfy cleanly with Temporal's activity/workflow split (it requires the author to split `@workflow.run` from `@activity.defn`). Inngest, Centaur, Windmill, and DBOS all independently prove that a pure-Python + Postgres step-memoization engine achieves the same crash-resume + HITL guarantees Temporal provides, with far less ceremony, and all run with no orchestration server. Verso's design requirement is "durable=True is one flag on the same loop", not "the loop must be deterministically replayable."

The **clean seam** (PRD §6.1 final bullet) is kept by designing `CheckpointBackend` as an interface: the default backend is the in-house Postgres implementation; a Temporal or Trigger.dev adapter can slot in later by implementing the same interface. Build for the seam, not for the vendor.

**Evidence:**
- Centaur `workflow_engine.py:338-435` — a 200-line pure-Python step-memoization engine (`ctx.step(name, fn)` → checkpoint PK `(run_id, name)` → skip if present, else run + persist) runs in production at Paradigm with no orchestration server. `[KNOWN]`
- DBOS `_core.py` + schema `dbos.workflow_status` + `dbos.operation_outputs` — the entire durable engine is Python + Postgres, startup recovery runs in a background thread, no server needed. `DEFAULT_MAX_RECOVERY_ATTEMPTS=100` (`_registrations.py:10`). `[KNOWN]`
- LangGraph `BaseCheckpointSaver` 5-method interface — the `InMemorySaver`→`PostgresSaver` swap demonstrates an in-house interface can back both tactical and durable runtimes with zero loop changes. `[KNOWN]`
- Anthropic Managed Agents blog — "nothing in the harness survives a crash" is the design invariant that makes any-harness-resumes-any-session work; that invariant is satisfied by pure event-log replay, not by delegating to Temporal. `[INFERRED, blog verbatim]`
- AX `controller.go:88-159` `tryResuming` — the full crash-resume algorithm for an append-only event log is 70 lines of Go; the Python equivalent is <100 lines. `[KNOWN]`

**Alternatives rejected:**
- **Temporal** — operational server required; sandbox/determinism model forces author to split workflow from activity; heavier than needed; keep as optional adapter target once the interface is defined.
- **Restate** — compiled Rust VM; no pure-Python path; suspend-and-free-the-worker semantics are architecturally superior but the operational cost is too high for v1 (single-developer dogfood phase).
- **Inngest** — excellent step-identity scheme and opcode taxonomy (adopt both as design references); but the stateless-re-POST model means the *whole function re-runs from the top each step*, fine for serverless but undesirable for an in-process Verso agent that should stay resident.

---

### D2 — Which Durability Model (Temporal Replay vs. DBOS Postgres-rows vs. Restate Journal vs. AX Record-Outputs)

**Choice:** DBOS-style step-memoization (re-execute top-to-bottom, skip checkpointed steps) with Inngest's step-identity scheme and AX's two-log separation.

**Rationale:**
Five production systems converge on the same answer for Python agent loops: step-memoization (re-execute + skip-completed) beats Temporal's full-history-replay because (a) it does not require the loop body to be deterministic — the LLM call IS non-deterministic, and that is correct, (b) it does not require a sandbox, (c) the "step" granularity matches the ReAct loop's natural unit (one LLM call + one tool call = one step), and (d) completed steps are never re-run, so the expensive LLM call is not repeated on resume. The three choices this resolves:

1. **Step identity: Inngest SHA-1 name scheme, NOT DBOS ordinal.** DBOS `function_id` is a monotonic ordinal — call steps in the same order on replay or it breaks. Inngest `sha1(name)` + `:n` loop counter is refactor-tolerant (renaming the step key is the only breaking change, not reordering) and loop-safe (the `:n` suffix disambiguates repeated calls). For a ReAct loop that may legitimately change the tool call order based on LLM output across two runs, content-based identity is strictly safer. Adopt verbatim: `step_key = sha1(name.encode()).hexdigest()` for first use, `sha1(f"{name}:{n}".encode()).hexdigest()` for the nth (n≥1).

2. **Event-log model: AX's two-log separation.** AX separates `ConversationEvent` (user-visible, seq-ordered, client-polled) from `ExecutionEvent` (internal replay, tool plumbing, `internal_only` steps). Verso adopts this: `verso_run_events` (the user-visible stream, seq-keyed, is what `agent.attach()` polls) and `verso_step_outputs` (the step-memoization journal, `(run_id, step_key)` PK, is what crash-resume reads). They are logically separate though can share one Postgres instance.

3. **Resume algorithm: AX `tryResuming` + DBOS `startup_recovery_thread`.** On `agent.run(durable=True)` or `agent.submit()`: check `verso_runs` for a PENDING run with this `run_id` → load all step outputs (the `verso_step_outputs` memo map) → re-enter the loop with the memo map pre-loaded → each `ctx.step()` call pops from the memo (instant on hit) or executes (on miss). At process startup, a recovery thread reschedules PENDING runs assigned to this executor (same as DBOS `recover_pending_workflows`).

**Evidence:**
- Inngest `transforms.py:30` — `sha1(step_id.encode("utf-8")).hexdigest()`, `base.py:111` loop counter `f"{step_id}:{id_count - 1}"`. `[KNOWN]`
- Centaur `workflow_engine.py:266-270` `_resolve_name` — `name`, `name#2`, `name#3` auto-dedup. Same idea. `[KNOWN]`
- AX `ax.proto:54-86` — `ConversationEvent{conversation_id, seq, exec_id, messages, state}` + `ExecutionEvent{exec_id, inputs, outputs, state}`, `internal_only` bit. `[KNOWN]`
- AX `controller.go:88-159` `tryResuming` — load all events, find pending exec id, replay; `executor.go:78` short-circuit on COMPLETED. `[KNOWN]`
- DBOS `_recovery.py:26-52` — `recover_pending_workflows`, filters by `status='PENDING' AND executor_id AND application_version`. `[KNOWN]`
- Centaur `discovery-wildcard.md:364-416` — entire Python workflow engine confirmed in production. `[KNOWN]`

**Alternatives rejected:**
- **Temporal full-history-replay** — requires deterministic body, sandbox reimport, seq-matching; wrong for a dynamic ReAct loop where the step sequence legitimately varies by run.
- **Restate journal-position identity** — clean concept, but the journal-position-as-identity model (no name, just position) breaks if the function produces a different number of steps on replay before the crash point; name-based identity is more robust.
- **AX record-outputs-only (re-prompt from history, never skip)** — correct for the "any-harness" autoscale story, but means re-calling the LLM on resume even for a step that already completed; more expensive. Verso's step-memoization model avoids re-calling the LLM.
- **DBOS ordinal function_id** — fragile under loop refactors; content-addressed names win.

---

### D3 — Default Backend

**Choice:** Postgres is the default durable backend. SQLite (in-process) is the dev/test backend. `durable=False` uses an in-memory no-op backend.

**Rationale:**
DBOS proves Postgres is sufficient with zero external infrastructure: a schema named `verso` (two load-bearing tables), a `psycopg`/`asyncpg` connection pool, and a startup recovery thread. LangGraph's `PostgresSaver` proves the same. Centaur's workflow engine proves it in Python. SQLite for dev (same schema, `aiosqlite`) avoids the "install Postgres first" friction on the zero-infra dev path — LangGraph's `InMemorySaver` / AX's `sqlite.go` / Windmill's JSONB-on-SQLite are three independent precedents. The in-memory backend (`durable=False`) is the tactical runtime from PRD §4.1: events in a Python list, no persistence, same interface.

The **pluggable `CheckpointBackend` interface** (5 methods, see Component Spec) is the seam: swap `InMemoryBackend()` for `PostgresBackend(dsn=...)` to cross from tactical to durable. `durable=True` defaults to `PostgresBackend`; explicit `backend=` overrides.

**Evidence:**
- DBOS schema `_schemas/system_database.py` — `workflow_status` + `operation_outputs`, plain Postgres, no extensions required. `[KNOWN]`
- LangGraph `postgres/base.py:43` migrations — 4-table schema, plain `psql` migrations, no extension (except optionally `vector`). `[KNOWN]`
- AX `executor/sqlite.go:51-76` — SQLite `modernc.org/sqlite` (pure-Go, CGo-free) for dev; same 2-table schema as Postgres analog. 10 s busy timeout. `[KNOWN]`
- Windmill `client.py:2485-2593` — JSONB checkpoint in one `v2_job_status` column, inline checkpoint in-process via `POST /jobs/wac/inline_checkpoint`. `[KNOWN]`

---

### D4 — Checkpoint / Event Schema

**Choice:** Two tables in a `verso` schema; schema below is the load-bearing spec.

**Rationale:**
DBOS's two-table model (`workflow_status` + `operation_outputs`) is the simplest proven schema that handles status, version pinning, executor ownership, recovery, HITL, and step journaling. Centaur's schema (`workflow_runs` + `workflow_checkpoints`) is richer (step_kind enum, execution_id for exactly-once agent turns, child_run_id for sub-agents, unique partial index for idempotency). LangGraph adds `checkpoint_writes` for per-task pending writes within a superstep — Verso does not need that complexity yet (a ReAct loop has sequential steps, not parallel supersteps). AX adds the `ConversationEvent` log for the client-polled stream. Verso blends: two tables from DBOS for the journal, plus a third `verso_run_events` for the user-facing stream (AX's conversation log).

**Schema (authoritative, attributed):**

```sql
-- Migrated at startup; schema name: verso

CREATE TABLE verso_runs (
  -- Identity (from DBOS workflow_status + Centaur workflow_runs)
  run_id          TEXT        PRIMARY KEY,          -- uuid4, Verso's workflow_uuid
  agent_id        TEXT        NOT NULL,             -- which agent class / yaml
  agent_version   TEXT        NOT NULL,             -- hash of agent config at submit time

  -- Status machine (DBOS statuses + Centaur additions)
  status          TEXT        NOT NULL              -- see RunStatus enum below
                  CHECK (status IN (
                    'queued',       -- submitted, not yet claimed
                    'running',      -- claimed by a worker
                    'sleeping',     -- durable sleep, available_at set
                    'waiting',      -- HITL: blocked on a promise
                    'completed',
                    'failed',
                    'cancelled',
                    'max_recovery_exceeded'          -- DBOS DEFAULT_MAX_RECOVERY_ATTEMPTS=100
                  )),
  available_at    TIMESTAMPTZ DEFAULT NOW(),        -- for sleeping runs: when to re-claim

  -- Payload
  input_json      JSONB       NOT NULL,             -- serialized initial input
  output_json     JSONB,                            -- set on completion
  error_json      JSONB,                            -- set on failure

  -- Worker ownership (DBOS executor_id + Centaur worker_id/lease)
  worker_id       TEXT,                             -- null = unclaimed
  worker_lease_expires_at TIMESTAMPTZ,              -- heartbeat at lease/3 (Centaur: 30s lease)

  -- Recovery (DBOS recovery_attempts)
  recovery_attempts INT NOT NULL DEFAULT 0,
  max_recovery_attempts INT NOT NULL DEFAULT 100,   -- DBOS DEFAULT_MAX_RECOVERY_ATTEMPTS

  -- Lineage (AX sub-exec parent, Centaur parent_run_id)
  parent_run_id   TEXT REFERENCES verso_runs(run_id),
  root_run_id     TEXT,                             -- top of the call tree

  -- Deduplication (DBOS deduplication_id + Inngest idempotency)
  idempotency_key TEXT UNIQUE,                      -- null = no dedup

  -- Timestamps
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Claim index (DBOS idx_workflow_status_in_flight pattern)
CREATE INDEX verso_runs_claimable ON verso_runs
  (status, available_at, worker_lease_expires_at)
  WHERE status IN ('queued', 'sleeping');

-- Recovery index
CREATE INDEX verso_runs_recovery ON verso_runs
  (worker_id, status)
  WHERE status = 'running';

--------------------------------------------------------------------------------

CREATE TABLE verso_step_outputs (
  -- Step journal (DBOS operation_outputs + Centaur workflow_checkpoints)
  run_id          TEXT        NOT NULL REFERENCES verso_runs(run_id) ON DELETE CASCADE,
  step_key        TEXT        NOT NULL,             -- sha1(name) or sha1(f"{name}:{n}")
                                                    -- (Inngest transforms.py:30)
  step_name       TEXT        NOT NULL,             -- human-readable, for debugging

  -- Payload (DBOS output/error TEXT + Centaur state JSONB)
  output_json     JSONB,                            -- null until completed
  error_json      JSONB,                            -- set on step failure
  step_kind       TEXT        NOT NULL              -- maps to Centaur step_kind
                  CHECK (step_kind IN (
                    'llm_call',
                    'tool_call',
                    'hitl_request',               -- Resonate: durable promise
                    'sleep',
                    'child_run',
                    'event_wait'
                  )),

  -- Sub-agent reference (AX sub-exec child run id)
  child_run_id    TEXT REFERENCES verso_runs(run_id),

  -- Timing
  started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at    TIMESTAMPTZ,

  PRIMARY KEY (run_id, step_key)
  -- Centaur: unique partial index on execution_id for exactly-once agent turns
  -- Verso equivalent: the PK itself is the idempotency guard (ON CONFLICT DO NOTHING on insert)
);

--------------------------------------------------------------------------------

CREATE TABLE verso_run_events (
  -- User-facing event stream (AX conversation_log)
  run_id          TEXT        NOT NULL REFERENCES verso_runs(run_id) ON DELETE CASCADE,
  seq             INT         NOT NULL,             -- monotonic per run; AX sqlite.go:82-90
  event_type      TEXT        NOT NULL,             -- see RunEventType enum
  payload         JSONB       NOT NULL,
  internal_only   BOOLEAN     NOT NULL DEFAULT FALSE, -- AX: persist but never emit to client
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (run_id, seq)
);

CREATE INDEX verso_run_events_poll ON verso_run_events (run_id, seq);

--------------------------------------------------------------------------------

CREATE TABLE verso_hitl_promises (
  -- Named durable promises for HITL (Resonate durable-promise-specification)
  promise_id      TEXT        PRIMARY KEY,          -- globally unique; from ctx.hitl.request()
  run_id          TEXT        NOT NULL REFERENCES verso_runs(run_id),
  step_key        TEXT        NOT NULL,             -- which step is suspended

  -- State machine (Resonate: PENDING → {RESOLVED|REJECTED|REJECTED_TIMEDOUT|REJECTED_CANCELED})
  state           TEXT        NOT NULL DEFAULT 'PENDING'
                  CHECK (state IN ('PENDING','RESOLVED','REJECTED','REJECTED_TIMEDOUT','REJECTED_CANCELED')),

  -- Payload
  question        TEXT        NOT NULL,             -- shown to the human approver
  param_json      JSONB,                            -- creation payload
  value_json      JSONB,                            -- resolution value (set by human)
  tags            JSONB,                            -- routing metadata

  -- Idempotency (Resonate two-key design: create and complete are independently deduped)
  create_ikey     TEXT,
  complete_ikey   TEXT,

  -- Timeout (Resonate default 31536000s = 1yr; Verso: configurable, default 24h)
  timeout_at      TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),

  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at    TIMESTAMPTZ
);

CREATE INDEX verso_hitl_promises_pending ON verso_hitl_promises
  (run_id, state) WHERE state = 'PENDING';
```

**RunStatus enum (Python):**
```python
class RunStatus(str, Enum):
    QUEUED             = "queued"
    RUNNING            = "running"
    SLEEPING           = "sleeping"
    WAITING            = "waiting"       # HITL
    COMPLETED          = "completed"
    FAILED             = "failed"
    CANCELLED          = "cancelled"
    MAX_RECOVERY_EXCEEDED = "max_recovery_exceeded"
```

**step_kind enum:**
```python
class StepKind(str, Enum):
    LLM_CALL     = "llm_call"
    TOOL_CALL    = "tool_call"
    HITL_REQUEST = "hitl_request"
    SLEEP        = "sleep"
    CHILD_RUN    = "child_run"
    EVENT_WAIT   = "event_wait"
```

**RunEventType enum (user-visible stream):**
```python
class RunEventType(str, Enum):
    USER_INPUT        = "user_input"
    ASSISTANT_DELTA   = "assistant_delta"
    TOOL_USE          = "tool_use"
    TOOL_RESULT       = "tool_result"
    HITL_REQUESTED    = "hitl_requested"
    HITL_RESOLVED     = "hitl_resolved"
    STATUS_CHANGE     = "status_change"
    ERROR             = "error"
    COMPLETED         = "completed"
```

---

### D5 — Durability Modes

**Choice:** Three modes, matching LangGraph exactly: `sync | async | exit`. Default is `async`.

**Rationale:**
LangGraph `types.py:87` proves three modes is the right granularity: `sync` (persist before next step starts, max durability), `async` (persist concurrently with next step, default tradeoff), `exit` (persist only on completion, fastest, least durable). These map cleanly onto Verso's use cases: `sync` for HITL gates and financial tool calls; `async` for normal agent loops; `exit` for short throwaway runs you want some durability on. The LangGraph source shows `exit` skips `put_writes` entirely (`_loop.py:459`) — Verso's equivalent: `exit` mode skips writing `verso_step_outputs` after each step, writes once at terminal. Inngest's `disable_immediate_execution` and `PLANNED` opcode capture the same tradeoff (declare vs execute) but are serverless-specific.

**Evidence:** LangGraph `types.py:87` `Durability = Literal["sync", "async", "exit"]`; `_loop.py:459` `if self.durability != "exit"`. `[KNOWN]`

```python
class DurabilityMode(str, Enum):
    SYNC  = "sync"    # checkpoint before advancing; max durability; HITL/financial default
    ASYNC = "async"   # checkpoint concurrently with next step; DEFAULT
    EXIT  = "exit"    # checkpoint only at terminal; fastest
```

---

### D6 — How `agent.run(durable=True)` and `agent.submit()` Work

**Choice:** `durable=True` executes synchronously in the caller's event loop using the durable runtime; `agent.submit()` enqueues asynchronously and returns a handle immediately. Both use the same `DurableExecutor`.

**Rationale:**
The seam is architectural, not syntactic. The distinguishing property is that the `DurableExecutor`:
1. Persists a `verso_runs` row with status=`running` on entry and transitions to `completed`/`failed` on exit.
2. Wraps each step in `ctx.step()` which checks `verso_step_outputs` before executing.
3. On crash-resume (process restart), the startup recovery thread finds PENDING rows and re-enters the loop.

`agent.submit()` writes a `verso_runs` row with status=`queued` and returns `{run_id, status}` immediately. A background worker (same process or out-of-process, configurable) claims queued rows and drives them. `agent.attach(run_id, starting_after=N)` streams `verso_run_events` with `seq > N` (AX's `last_seq` replay-since-N protocol).

The `durable=True` synchronous path is Resonate's `durable=True` per-call option semantics: the same function, same event loop, same async signature — but every `ctx.step()` call is now journaled.

**Evidence:**
- Resonate `options.py:18` `durable: bool = True` per-call option. `[KNOWN]`
- AX `executor.go:51-82` `Exec` + `tryResuming` — synchronous path re-enters the loop from the recovered state. `[KNOWN]`
- DBOS `_dbos.py` `submit` → enqueue → recovery thread dequeues — the `submit` path. `[KNOWN]`
- PRD §7 `handle = await agent.submit("deep task")` / `async for ev in agent.attach(handle.id, starting_after=last_seq)`. `[PRD verbatim]`

**Public API (from PRD §7, now specified):**

```python
# Tactical path (unchanged, in-memory)
result: AgentResult = await agent.run(task)

# Durable synchronous path (same loop, journaled)
result: AgentResult = await agent.run(task, durable=True)
                                              # ^ optionally: durability="sync"|"async"|"exit"
                                              #   backend=PostgresBackend(dsn=...)

# Async submit / background
handle: RunHandle = await agent.submit(task)
# handle.run_id: str; handle.status: RunStatus

# Attach / reconnect (AX last_seq replay)
async for event in agent.attach(handle.run_id, starting_after=last_seq):
    ...   # event.seq, event.event_type, event.payload

# Cancel
await agent.cancel(handle.run_id)
```

The `RunHandle` and `attach()` together implement the "resumable transport" from PRD §5.6 for the durable runtime: the seq-cursor protocol ensures a reconnecting client gets exactly the events it missed.

---

### D7 — HITL Surface (`await ctx.hitl.request()` over what primitive)

**Choice:** Resonate-style named Durable Promise over a Postgres table (`verso_hitl_promises`), accessed through `await ctx.hitl.request(question, timeout=86400)`. The low-level `interrupt()`/`Command(resume=)` stays internal.

**Rationale:**
Five systems provide HITL primitives; they differ on the underlying primitive:
- **Temporal**: signal + `wait_condition(lambda: approved)` — in-memory condition racing a durable timer. Clean, but requires the server and in-memory handler registration; signals can arrive before the handler is registered (buffered, but ordering is complex).
- **LangGraph** `interrupt(value)` — counter-indexed resume, whole node re-executes on resume. The "re-execute the whole node" cost is acceptable for a graph node but expensive for a full LLM call inside a ReAct loop.
- **AX**: "log ends on an unanswered confirmation" — resume is the next turn's inputs carrying `ApprovalDecision`. Elegant but couples HITL to the turn boundary; can't pause mid-step.
- **Centaur** `ctx.wait_for_event` + `workflow_events` table — suspend workflow by exception, re-claim when the event row arrives. Correct but requires a separate reconciler poll.
- **Resonate** `ctx.promise(id)` — named durable future, externally resolved via `PATCH /promises/{id}`. The cleanest model: a suspend point in the log (`hitl_request` step_kind, status=`waiting`), a named promise anyone can resolve over HTTP, two independent idempotency keys (create vs complete). Does not require re-executing the node; the promise result is stored in `verso_hitl_promises.value_json` and replayed as a cached step output on resume.

Resonate's model wins because: (a) it is the only one that does NOT require re-executing the LLM call on resume (the promise result is the step's memoized output), (b) named promises are addressable from outside the agent process without a callback registry, (c) the two-idempotency-key design handles double-callbacks and retried agents cleanly, (d) it maps directly onto the `verso_hitl_promises` table already in the schema.

The `ctx.hitl.request()` user API (from PRD §7) hides the promise mechanics. Under the hood:
1. Compute `promise_id = sha1(f"{run_id}:{step_key}".encode()).hexdigest()`.
2. INSERT into `verso_hitl_promises` (idempotent via `ON CONFLICT DO NOTHING`).
3. Emit a `HITL_REQUESTED` event to `verso_run_events`.
4. Transition `verso_runs.status` → `waiting`.
5. Raise `SuspendRun(promise_id=...)` — the executor catches it, persists the promise row, and returns `RunHandle(status=waiting)` to the caller.
6. An external call to `POST /verso/hitl/{promise_id}/resolve` or the SDK's `await agent.resume_hitl(promise_id, value)` sets `verso_hitl_promises.state=RESOLVED` + `value_json`, transitions the run back to `queued`, and the recovery/worker loop re-claims it.
7. On resume, `ctx.step()` finds `verso_step_outputs[step_key]` cached (the promise resolution was written there by the resolve handler); the awaiting coroutine receives the value.

Timeout: a scanner task polls `verso_hitl_promises WHERE state='PENDING' AND timeout_at <= NOW()` and transitions them to `REJECTED_TIMEDOUT`, writing a `StepError` to `verso_step_outputs` and transitioning the run to `failed` (or to a configurable `on_hitl_timeout` hook). Default timeout: `86400s (24h)` for Verso (vs Resonate's 1yr default — more opinionated).

**Evidence:**
- Resonate `resonate.py:1119` `promise = yield ctx.promise(id="approval-42")`, `stores/remote.py:232` `PATCH /promises/{id} {state:RESOLVED, value}`. `[KNOWN]`
- Resonate `options.py:18` — `idempotency_key = id` default. `[KNOWN]`
- Resonate spec: two idempotency keys (create vs complete), `strict` mode for conflicting terminal states. `[KNOWN]`
- Centaur `workflow_engine.py:338-435` `wait_for_event` + `workflow_events` table — the Postgres-mailbox HITL model Verso adapts. `[KNOWN]`
- LangGraph `types.py:811` `interrupt(value)` counter-indexed resume — the "re-execute the whole node" cost. `[KNOWN]`
- PRD §6.1 `answer = await ctx.hitl.request("Approve sending this email?")` — verbatim surface. `[PRD]`

**Alternatives rejected:**
- **LangGraph `interrupt()` + `Command(resume=)`** — whole node re-executes on resume; expensive for a node that starts with an LLM call. Keep as the *internal* mechanism name only (PRD says "Command(resume=) stays internal").
- **Temporal `wait_condition` + signal** — requires the Temporal server; signal-before-handler buffering is complex. Keep as a reference design for the Temporal adapter.
- **AX turn-boundary HITL** — can only pause at turn boundaries, not mid-step; too coarse for "approve this specific tool call."

---

### D8 — The `CheckpointBackend` Interface (the seam contract)

**Choice:** A 6-method async ABC modeled on LangGraph's `BaseCheckpointSaver`, adapted for Verso's flat step-journal model (not BSP channels).

**Rationale:**
LangGraph's `BaseCheckpointSaver` (5 methods: `get_tuple`/`list`/`put`/`put_writes`/`get_next_version`) is the proven interface that lets `InMemorySaver` and `PostgresSaver` share one code path above. Verso needs a slightly different shape (no BSP channels; the unit is a run+step, not a thread+checkpoint) but the principle is identical: a small, stable interface that the tactical runtime implements as a no-op (in-memory Python dict) and the durable runtime implements against Postgres.

```python
class CheckpointBackend(ABC):

    @abstractmethod
    async def create_run(self, run: RunRow) -> None:
        """Insert a new run row (status=queued or running). Idempotent: ON CONFLICT DO NOTHING."""

    @abstractmethod
    async def update_run(self, run_id: str, **fields) -> None:
        """Update status, output, error, worker_id, lease, recovery_attempts, etc."""

    @abstractmethod
    async def get_run(self, run_id: str) -> RunRow | None:
        """Read the current run row."""

    @abstractmethod
    async def get_step_output(self, run_id: str, step_key: str) -> StepOutput | None:
        """Memo map read: None = cache miss (execute the step). (DBOS check_operation_execution)"""

    @abstractmethod
    async def put_step_output(self, run_id: str, step_key: str, kind: StepKind,
                              name: str, output: Any | None, error: Any | None,
                              child_run_id: str | None = None) -> None:
        """Memo map write (DBOS record_operation_result). INSERT ... ON CONFLICT DO NOTHING."""

    @abstractmethod
    async def append_event(self, run_id: str, event_type: RunEventType,
                           payload: dict, internal_only: bool = False) -> int:
        """Append to verso_run_events; returns the new seq. (AX EventLog.Append)"""

    @abstractmethod
    async def get_events(self, run_id: str, since_seq: int = 0) -> list[RunEvent]:
        """Range-read run events (AX tryResuming + last_seq replay)."""

    @abstractmethod
    async def claim_pending_runs(self, worker_id: str, limit: int = 10) -> list[RunRow]:
        """SELECT ... FOR UPDATE SKIP LOCKED WHERE status IN ('queued','sleeping')
           AND available_at <= NOW(). Sets worker_id + lease. (Centaur lease claim)"""

    @abstractmethod
    async def extend_lease(self, run_id: str, worker_id: str,
                            lease_seconds: float = 30.0) -> None:
        """Heartbeat: UPDATE worker_lease_expires_at = NOW() + lease_seconds
           WHERE run_id=? AND worker_id=? (fencing guard). (Centaur workflow_engine.py:1108)"""

    @abstractmethod
    async def recover_expired_runs(self, worker_id: str) -> int:
        """Flip lease-expired running rows back to queued. Returns count.
           (Centaur _requeue_expired_running_runs)"""

    @abstractmethod
    async def delete_run(self, run_id: str) -> None:
        """Hard-delete run + cascade. For retention / GDPR. (LangGraph delete_thread)"""
```

`InMemoryBackend` (tactical runtime) implements every method against Python dicts / asyncio.Queue with no I/O. `PostgresBackend` maps each method to the SQL in D4's schema.

---

### D9 — The `ctx.step()` Call Contract (the seam-visible primitive)

**Choice:** An `async with` context manager that wraps any coroutine, memoizing the result by `step_key`.

**Rationale:**
Centaur `workflow_engine.py:338-435` provides the reference Python implementation. The key design points:
1. Compute `step_key = _hash_step_id(name)` using the Inngest scheme.
2. Check backend `get_step_output(run_id, step_key)` — cache hit → return immediately, do NOT call `fn`.
3. Cache miss → run `fn()` with `RetryPolicy` (configurable per-step, defaulting to `max_attempts=3, backoff="exponential"`).
4. On success: `put_step_output(run_id, step_key, kind, name, output=result, error=None)`.
5. On terminal failure: `put_step_output(run_id, step_key, kind, name, output=None, error=serialized_exc)` then re-raise as `StepError`.
6. Fencing on the write: in `SYNC` durability mode, the write must commit before `fn`'s result is returned to the caller (no window where the step ran but wasn't checkpointed). In `ASYNC` mode, the write is dispatched concurrently.

The Centaur `_persist_checkpoint` fencing detail (Centaur `workflow_engine.py:272-326`): the write does `SELECT status, worker_id FROM verso_runs WHERE run_id=? FOR UPDATE` — if `worker_id != self._worker_id` the run was stolen; raise `StaleWorkerError` (not a `StepError`). This prevents a zombie worker from writing a stale checkpoint after losing its lease.

```python
@asynccontextmanager
async def step(
    self,                          # RunContext
    name: str,
    *,
    kind: StepKind = StepKind.TOOL_CALL,
    retry_policy: RetryPolicy | None = None,
):
    step_key = _hash_step_id(name, self._step_counter)
    self._step_counter.increment(name)   # Inngest loop counter

    cached = await self.backend.get_step_output(self.run_id, step_key)
    if cached is not None:
        if cached.error:
            raise StepError(cached.error)    # replay the error too (DBOS)
        yield _CachedResult(cached.output)   # instant, no fn call
        return

    # Cache miss: caller's body runs inside the `async with` block
    try:
        yield _StepWriter(step_key)          # caller assigns: async with ctx.step("x") as s: s.result = await fn()
    except Exception as exc:
        await self._persist_step(step_key, name, kind, output=None, error=exc)
        raise StepError(exc) from exc
    else:
        await self._persist_step(step_key, name, kind, output=s.result, error=None)
```

The LLM call is always wrapped in `ctx.step("llm_call_{n}", kind=StepKind.LLM_CALL)` so a crash mid-inference does not re-call the model on resume. Tool calls are wrapped in `ctx.step(f"tool_{tool_name}_{n}", kind=StepKind.TOOL_CALL)`.

---

### D10 — Worker Model: Resident vs. Stateless

**Choice:** Resident worker (process-local async task), lease-renewed, with a configurable out-of-process worker pool for `agent.submit()`.

**Rationale:**
For `agent.run(durable=True)` (synchronous path), the agent stays resident in the caller's event loop — no re-invoke per step. This is the DBOS/Centaur/Restate model (resident worker) rather than Inngest's stateless-re-POST model. The re-POST model is correct for serverless but adds latency and complexity for an in-process Verso agent. The resident model means the `step_key` cache is also held in-process as a dict (avoiding a DB round-trip on cache-hit replay in the common case after a crash-resume initial load).

For `agent.submit()` (async path), a separate worker loop runs as a background asyncio task (same process) or as a separate process. Either way it uses the `claim_pending_runs` / `extend_lease` / `recover_expired_runs` cycle from D8. Lease = 30s, heartbeat at 10s (lease/3, Centaur constant `workflow_engine.py:167`).

The Windmill insight applies: a `SELECT ... FOR UPDATE SKIP LOCKED` dequeue (Windmill migration `20220123221903.sql:120`) is the correct Postgres-queue dequeue — multiple workers compete for unclaimed runs without locking each other. Verso's `claim_pending_runs` uses this exactly.

**Constants:**
```python
WORKER_LEASE_SECONDS       = 30       # Centaur workflow_engine.py:167
WORKER_HEARTBEAT_SECONDS   = 10       # lease / 3
WORKER_CONCURRENCY         = 2        # Centaur WORKFLOW_WORKER_CONCURRENCY
WORKER_RECONCILE_INTERVAL  = 0.5      # Centaur WORKFLOW_RECONCILE_INTERVAL_S
MAX_RECOVERY_ATTEMPTS      = 100      # DBOS _registrations.py:10
HITL_DEFAULT_TIMEOUT_S     = 86400    # 24 hours (vs Resonate's 31536000 = 1yr)
SLEEP_STEP_ID_RESERVE      = 2        # DBOS: sleep reserves 2 function_ids (sleep + wakeup)
DURABILITY_DEFAULT         = DurabilityMode.ASYNC
```

---

## Component Spec

### Interfaces

```python
# verso/runtime/durable/backend.py

from abc import ABC, abstractmethod
from typing import Any
from verso.runtime.durable.schema import RunRow, RunEvent, StepOutput, StepKind, RunEventType

class CheckpointBackend(ABC):
    """The seam. InMemoryBackend = tactical. PostgresBackend = durable."""

    @abstractmethod
    async def create_run(self, run: RunRow) -> None: ...

    @abstractmethod
    async def update_run(self, run_id: str, **fields) -> None: ...

    @abstractmethod
    async def get_run(self, run_id: str) -> RunRow | None: ...

    @abstractmethod
    async def get_step_output(self, run_id: str, step_key: str) -> StepOutput | None: ...

    @abstractmethod
    async def put_step_output(
        self, run_id: str, step_key: str, kind: StepKind,
        name: str, output: Any | None, error: Any | None,
        child_run_id: str | None = None,
    ) -> None: ...

    @abstractmethod
    async def append_event(
        self, run_id: str, event_type: RunEventType,
        payload: dict, internal_only: bool = False,
    ) -> int: ...  # returns seq

    @abstractmethod
    async def get_events(self, run_id: str, since_seq: int = 0) -> list[RunEvent]: ...

    @abstractmethod
    async def claim_pending_runs(self, worker_id: str, limit: int = 10) -> list[RunRow]: ...

    @abstractmethod
    async def extend_lease(self, run_id: str, worker_id: str,
                            lease_seconds: float = 30.0) -> None: ...

    @abstractmethod
    async def recover_expired_runs(self, worker_id: str) -> int: ...

    @abstractmethod
    async def delete_run(self, run_id: str) -> None: ...
```

```python
# verso/runtime/durable/hitl.py

class HITLManager:
    """User-facing HITL surface. Backed by verso_hitl_promises."""

    async def request(
        self,
        question: str,
        *,
        timeout: float = 86400.0,      # HITL_DEFAULT_TIMEOUT_S
        tags: dict | None = None,
        promise_id: str | None = None,  # override for idempotent re-entry
    ) -> Any:
        """
        Checkpoint-before-pause, then suspend.
        Returns the human-provided value on resume.
        Raises HITLTimeout if timeout_at elapses.
        Raises HITLRejected if explicitly rejected.

        Low-level: writes verso_hitl_promises + step_kind=HITL_REQUEST +
        raises SuspendRun(promise_id). On resume, step cache hit returns value.
        """
        ...

    async def resolve(self, promise_id: str, value: Any, *,
                      idempotency_key: str | None = None) -> None:
        """External: set promise RESOLVED + write step output + re-queue run."""
        ...

    async def reject(self, promise_id: str, reason: str, *,
                     idempotency_key: str | None = None) -> None:
        """External: set promise REJECTED + write StepError + fail run (or hook)."""
        ...
```

```python
# verso/runtime/durable/executor.py

class DurableExecutor:
    """
    Wraps the core loop (imported unchanged) in the durable runtime.
    Replaces RunContext.backend with a CheckpointBackend.
    All durability is in this class; the loop never knows.
    """

    def __init__(
        self,
        backend: CheckpointBackend,
        durability: DurabilityMode = DurabilityMode.ASYNC,
        worker_id: str | None = None,   # auto-generated if None
        lease_seconds: float = WORKER_LEASE_SECONDS,
    ): ...

    async def run(
        self,
        agent: Agent,
        task: str,
        run_id: str | None = None,      # auto-generated if None
        idempotency_key: str | None = None,
    ) -> AgentResult:
        """
        Synchronous durable path.
        1. Upsert verso_runs row (idempotent).
        2. Load all step_outputs into an in-process memo dict.
        3. Run the agent loop with a DurableRunContext.
        4. On SuspendRun: persist promise, return RunHandle(status=waiting).
        5. On completion: update verso_runs status + output.
        6. On exception: update status=failed + error.
        """
        ...

    async def submit(self, agent: Agent, task: str,
                     idempotency_key: str | None = None) -> RunHandle:
        """Insert verso_runs with status=queued; return immediately."""
        ...

    async def attach(self, run_id: str, starting_after: int = 0) -> AsyncIterator[RunEvent]:
        """Stream verso_run_events WHERE seq > starting_after. (AX last_seq replay)"""
        ...

    async def _worker_loop(self) -> None:
        """
        Background task for submit() path.
        claim_pending_runs → extend_lease (heartbeat at lease/3) → run loop →
        recover_expired_runs on startup.
        """
        ...
```

```python
# verso/runtime/durable/step.py

import hashlib
from collections import defaultdict

class StepIDCounter:
    """Inngest-style per-name loop counter."""
    def __init__(self): self._counts: dict[str, int] = defaultdict(int)
    def increment(self, name: str) -> int:
        self._counts[name] += 1
        return self._counts[name]

def hash_step_id(name: str, counter: StepIDCounter) -> str:
    """
    Inngest transforms.py:30 + base.py:111.
    First use: sha1(name). Nth use (n>=2): sha1(f"{name}:{n-1}").
    """
    n = counter.increment(name)
    pre_hashed = name if n == 1 else f"{name}:{n - 1}"
    return hashlib.sha1(pre_hashed.encode()).hexdigest()

class RetryPolicy:
    max_attempts: int = 3              # DBOS: DEFAULT_MAX_RECOVERY_ATTEMPTS=100 is for runs; steps default 3
    initial_delay: float = 1.0
    backoff: Literal["exponential", "fixed"] = "exponential"
    max_delay: float = 60.0
    non_retryable: tuple[type[Exception], ...] = ()
```

### Data Schema (load-bearing types)

```python
# verso/runtime/durable/schema.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class RunRow:
    run_id: str
    agent_id: str
    agent_version: str
    status: RunStatus
    input_json: dict
    output_json: dict | None = None
    error_json: dict | None = None
    worker_id: str | None = None
    worker_lease_expires_at: datetime | None = None
    recovery_attempts: int = 0
    max_recovery_attempts: int = MAX_RECOVERY_ATTEMPTS   # 100
    parent_run_id: str | None = None
    root_run_id: str | None = None
    idempotency_key: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    available_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class StepOutput:
    run_id: str
    step_key: str
    step_name: str
    step_kind: StepKind
    output_json: Any | None           # deserialized
    error_json: dict | None           # serialized exception; replayed on resume
    child_run_id: str | None = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

@dataclass
class RunEvent:
    run_id: str
    seq: int
    event_type: RunEventType
    payload: dict
    internal_only: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class RunHandle:
    run_id: str
    status: RunStatus
```

### Serialization

Adopt LangGraph's `JsonPlusSerializer` approach (KNOWN, `serde/jsonplus.py`): default serialization is `msgpack` (via `ormsgpack`) with Pydantic v2 extension type codes (`EXT_PYDANTIC_V2=5`) and a construction allowlist to prevent RCE on load. For v1 dogfood: `json.dumps` with a Pydantic v2 model encoder is sufficient; swap to msgpack when the schema stabilizes.

Encryption: wrap the serializer in an `EncryptedSerializer(key: bytes)` that AES-GCM-encrypts each blob (nonce + tag + ciphertext), transparent to the storage layer. Agent state often contains sensitive data; Postgres-at-rest encryption is insufficient when the Postgres host may be shared. See LangGraph `serde/encrypted.py` (KNOWN) for the reference implementation.

### Checkpoint Write Path (SYNC vs ASYNC)

In `SYNC` mode:
```
step fn runs → await backend.put_step_output(...) → step result returned to loop
```
In `ASYNC` mode (default):
```
step fn runs → asyncio.create_task(backend.put_step_output(...)) → step result returned IMMEDIATELY
              (the write completes concurrently with the next loop iteration)
```
In `EXIT` mode:
```
step fn runs → result held in in-process memo dict only → batch write on loop exit
```

The `ASYNC` mode risk: if the process crashes between the step completing and the background write committing, the step re-runs on resume. This is acceptable for LLM calls (idempotent-in-practice) and read-only tool calls; for destructive / non-idempotent tool calls, the tool's `StepKind.TOOL_CALL` entry should use `SYNC` mode (override per-step: `ctx.step(..., durability=DurabilityMode.SYNC)`).

### Topology: Anthropic Managed Agents as the Reference Architecture

Verso's durable runtime maps onto the Anthropic Managed Agents three-entity contract (KNOWN, blog) as follows:

| Anthropic | Verso |
|---|---|
| Session (`emitEvent`/`getEvents`) | `verso_run_events` table + `append_event`/`get_events` |
| Harness (stateless, any-instance resumes) | `DurableExecutor` + `CheckpointBackend`; holds **no** durable state |
| Sandbox (lazy, provisioned on first tool call) | `@tool` execution environment; `durable=False` for pure-text agents |
| `wake(sessionId)` | `DurableExecutor.run(run_id=existing_id)` → loads memo + re-enters loop |
| `emitEvent(id, event)` | `backend.append_event(run_id, event_type, payload)` |
| "nothing in the harness survives a crash" | `DurableExecutor` holds only the in-process memo cache, never canonical state; the DB is canonical |
| Container death = tool-call error | `SandboxDead` → `StepError` → loop continues (NOT `RunStatus.FAILED`) |

The design test (from the blog, verbatim): **"If any Verso loop state can't be reconstructed by replaying the run events + step_outputs, that state is a bug."** Every decision-relevant fact must be an emitted event or a persisted step output. If it isn't, the harness is no longer fungible.

---

## Open Unknowns

1. **Exactly-once for destructive tool calls with external DB.** DBOS's transaction-piggyback trick (write the step checkpoint IN the user's transaction, `_core.py:1448`) gives zero-window exactly-once for tools that touch the same Postgres as the checkpoint store. For tools touching a different DB or an external API (Stripe, GitHub), exactly-once is impossible; the correct contract is at-most-once with idempotency keys. Verso must decide: (a) document this boundary clearly, (b) provide an `idempotency_key` parameter on `ctx.step()` that is stored and returned on re-entry so the tool author can implement their own idempotency, or (c) mandate `max_attempts=1` for `destructive=True` tools (PRD already does this). Needs dogfood on a real tool that touches an external API.

2. **Transaction-piggyback for DB-touching tools.** If a Verso tool writes to the same Postgres as the checkpoint store, the optimal design is to expose a `session` parameter to the tool so it can write its checkpoint in the user's transaction (DBOS pattern). This requires the `CheckpointBackend` to expose a `transaction()` context manager that the tool executor can pass in. Worth implementing but requires care to not force Postgres on all tool authors. Prototype-gate.

3. **Continue-as-new / journal compaction.** Temporal's `continue_as_new` (`_workflow_instance.py:1143`, KNOWN) solves "unbounded history = slow replay." For long-running Verso agents (days, thousands of steps), `verso_step_outputs` grows without bound. Two options: (a) a periodic `compact_run(run_id, keep_last_n=100)` that deletes old step outputs and writes a `COMPACTED` event carrying the essential state as a snapshot; (b) a `fork_run(run_id, from_step=N)` that copies steps `[0..N]` to a new run_id (AX `fork`, Centaur `fork_workflow`). Both are sound; the right default (compact-in-place vs fork) depends on whether Verso wants audit-grade immutability (fork) or minimal storage (compact). Decide after first dogfood run that produces >500 steps.

4. **HITL routing and external-resolver DX.** The `verso_hitl_promises` table is the internal model, but the external-facing DX for human approvers is undecided: (a) a minimal REST endpoint (`POST /verso/hitl/{promise_id}/resolve`), (b) a Slack/email integration (Centaur's model), (c) a hosted dashboard. For v1 dogfood, option (a) is sufficient. The `tags` column on `verso_hitl_promises` is the routing hook for option (b)/(c) — don't pay the integration cost until there's a real workflow to drive it.

5. **Sub-agent (`child_run_id`) durable fan-out.** The schema supports `parent_run_id` / `root_run_id` / `child_run_id` for multi-agent coordination, but the `fan_out()` path in `orchestrate/` (PRD §6.2) needs a concrete durable implementation. AX's `sub-exec-id = parent + "-" + child` and DBOS's `fork_workflow` are the two reference models. This is deferred to Phase 3 (PRD §8) but the schema fields are laid in now so the shape doesn't change.

6. **SQLite vs Postgres behavioral divergence.** The schema above targets Postgres (`SELECT ... FOR UPDATE SKIP LOCKED`, `ON CONFLICT DO NOTHING`, `RETURNING seq`). SQLite lacks `FOR UPDATE SKIP LOCKED`; `aiosqlite` is WAL-mode only and doesn't support true concurrent writers. The dev/test SQLite backend should use a Python-level `asyncio.Lock` per `run_id` instead of DB-level row locking. Verify this is sufficient for single-process dogfood (it will be); note it's NOT sufficient for multi-worker SQLite (which is a non-use-case).

7. **`internal_only` event semantics.** AX uses `internal_only` to persist tool-plumbing state that must survive crashes without polluting the client stream or sub-agent prompts (AX `ax.proto:58-61`, KNOWN). Verso's exact rule for which events are `internal_only` — specifically, whether raw tool arguments and results are `internal_only` (recommended: yes, they're plumbing; the `tool_result` user-visible event carries a compact representation) — needs a concrete decision before implementing `agent.attach()`. Over-including in the user stream wastes bandwidth and leaks internal state; under-including breaks crash-resume fidelity. Needs one full end-to-end trace to calibrate.
