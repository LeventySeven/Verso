# Production Topology — Verso Design Resolution

> **Subsystem:** runtime topology at scale — how Session (durable log), Harness (stateless loop), and Sandbox (side-effect env) deploy physically, and the interfaces between them.
> **PRD section:** §6.1 Durable runtime
> **Teardowns consulted:** `discovery-wildcard.md` (Anthropic Managed Agents, Google AX, Centaur, CF Project Think, Salus) · `infra-durable-execution.md` (DBOS, LangGraph, Inngest, Windmill, Restate, Hatchet, Resonate, CF Workflows, Temporal, Trigger.dev, LittleHorse, AWS SFN)

---

## Decisions Resolved

### Decision 1 — The three-layer split: Session / Harness / Sandbox

**Choice:** Adopt the Anthropic Managed Agents three-entity split verbatim as the Verso topology target.

- **Session** = the durable append-only event log. Lives *outside* the loop process. Survives any process death. Provides `emit_event(run_id, event) → seq` and `get_events(run_id, since_seq=0) → list`.
- **Harness** = the stateless async ReAct loop. Holds **zero** durable state; every loop-relevant fact is an event. On boot it calls `get_events(run_id)` + `replay_to_messages()` and resumes from the last event. Any harness instance can resume any run: harnesses are a fungible, autoscalable, crash-disposable pool.
- **Sandbox** = the side-effect execution environment (code execution, file I/O, long-running shell). **Provisioned lazily — on the first tool call that requires it.** Sessions that answer from the model alone never pay sandbox boot cost.

**Rationale:** Five independent 2026 systems (Anthropic, AX, Centaur, CF Think, Windmill) converge on exactly this: a durable log + a stateless loop + a lazily-provisioned side-effect env. The Anthropic blog publishes the only quantified outcome: decoupling produced p50 TTFT −60% / p95 TTFT −90%. That is not a theory; it is the measured cost of doing it the other way (loop inside the container = sandbox boot on the critical path for every request). For a Python-only pip-installable framework, the Session is a Postgres/SQLite table; the Harness is a Python async process; the Sandbox is either a subprocess or a lazily-spawned container — the pattern holds regardless of the hosting tier.

**Evidence:**
- Anthropic Managed Agents, `discovery-wildcard.md:15-54`: "nothing in the harness needs to survive a crash"; `provision({resources})` is called only "if needed"; TTFT numbers are verbatim from the blog.
- Google AX `discovery-wildcard.md:148-310`: `wake(sessionId)` on any worker rehydrates from the log; SubstrATE actor suspended 50 ms after each turn; `AX_SUBSTRATE=1` opt-in.
- Centaur `discovery-wildcard.md:318-418`: stateless FastAPI + Postgres intent tables; `(thread_key, assignment_generation)` is the session→sandbox binding.
- CF Project Think `discovery-wildcard.md:523-538`: "an addressable entity with its own SQLite database that consumes zero compute when hibernated."

**Alternatives rejected:**
- Loop inside the sandbox (naive single-container design): loop liveness tied to container liveness; sandbox boot on the critical path for every turn. This is the design Anthropic decoupled away from for −90% p95.
- Stateful harness (keeping messages/state in the harness process): makes harnesses non-fungible; a crashed harness = work lost; precludes horizontal scaling. Hard invariant: if any loop state cannot be reconstructed by replaying the Session log, that state is a bug.

---

### Decision 2 — Event-log format and storage substrate

**Choice:** Family B memoization over Postgres/SQLite. Two tables: `verso_runs` (one row per agent run) + `verso_steps` (the step journal, `PK(run_id, step_hash)`). The event log is append-only; the step journal stores completed-step outputs keyed by a content-addressed step id.

For the Session entity, the concrete format adapts AX's two-log pattern (`ConversationEvent` + `ExecutionEvent`) into Python/Postgres:
- **Conversation log** — the user-visible, seq-ordered turn stream (`verso_runs.run_id` + monotonic `seq`). This is what `get_events(run_id, since_seq)` returns.
- **Step journal** — the internal, per-step memoization map (`verso_steps(run_id, step_hash, output)`). This is the Family B replay substrate.

Step identity = `sha1(step_name)` + `:n` loop counter disambiguation (Inngest scheme). Content-addressed, refactor-tolerant. NOT call-order ordinal (DBOS `function_id`) — ordinals break when developers reorder the loop.

Wire encoding: JSON (Python-native, inspectable; msgpack optional for large blobs). Every event carries `{seq, type, payload, ts}`.

**Rationale:** Family A (event-source replay, Temporal/Restate) requires a deterministic workflow body and a replay sandbox — both impossible/wrong for an LLM-driven ReAct loop whose next action depends on non-deterministic model output. Family B (memoization: re-enter the function, skip completed steps, run to the first miss) is the correct base for a dynamic agent loop. The convergence is overdetermined: DBOS, Inngest, Windmill, LangGraph, Cloudflare Workflows all use Family B. The Cloudflare game loop is the minimal mental model: re-run the agent function, memoize each step by key, execute only the first uncached step.

The Inngest content-addressed step id is strictly better than call-order ids for agent code that developers iterate on.

**Evidence:**
- `infra-durable-execution.md:1115-1125` (synthesis verdict): "Family B memoization is the correct base model."
- AX `discovery-wildcard.md:150`: "AX records outputs, not inputs."
- DBOS `infra-durable-execution.md:161-276`: exact two-table Postgres schema, startup recovery, `MAX_RECOVERY_ATTEMPTS`.
- Inngest `infra-durable-execution.md:513-608`: `sha1(step_name[:n])` step id + `:n` loop counter.
- Cloudflare `infra-durable-execution.md:990-1042`: the game-loop pseudocode verbatim.
- `infra-durable-execution.md:1127-1138`: "convergent invariant 2 — step identity is the whole ballgame."

**Alternatives rejected:**
- Temporal event-history replay: requires deterministic workflow body + import sandbox + custom asyncio event loop. Wrong for a non-deterministic LLM loop.
- CRIU container freeze (Trigger.dev): requires container orchestration infrastructure; wrong for a pip-installable framework.
- Kafka WAL (LittleHorse): high-throughput use case only; adds operational overhead for the common case. Keep it as a future pluggable `CheckpointBackend` option.

---

### Decision 3 — Write-before-advance (the crash-safety invariant)

**Choice:** Every step result is persisted atomically before the loop advances. This is unconditional — not a configuration option.

The write protocol in the Harness loop:
1. Run the LLM call or tool call (the "activity" in Temporal terms — the side-effectful step).
2. Atomically `INSERT INTO verso_steps (run_id, step_hash, output, completed_at) ON CONFLICT DO NOTHING`.
3. Only then advance the loop state / append the next message.

For tool steps that write to the application's own Postgres: write the step checkpoint in the **same transaction** as the tool's writes (DBOS transaction-piggyback). This yields exactly-once semantics for DB-touching tools at zero extra round-trip.

**Rationale:** Every memoization-based durable execution system enforces this invariant. A crash in the gap between "step ran" and "result persisted" re-runs the step on recovery; that is always safe (re-running a completed step is idempotent by construction). Skipping the write before advancing is not safe — it loses the step on crash.

**Evidence:**
- `infra-durable-execution.md:1127-1129`: "convergent invariant 1 — write-before-advance. Every memoization system persists the step result before allowing the loop to advance."
- DBOS `infra-durable-execution.md:218-232`: `record_operation_result` before return; transaction-piggyback pattern verbatim.
- CF Workflows `infra-durable-execution.md:1014-1015`: "`transactionSync()` write-before-advance."
- Windmill `infra-durable-execution.md:831-836`: `_StepSuspend` persists `completed_steps` before dispatch.

---

### Decision 4 — Lazy sandbox: provision on first tool call that requires it

**Choice:** The Sandbox is `None` at the start of every Harness session. The first tool call whose `@tool(sandbox=True)` annotation fires `provision()`. Sessions that answer from the model alone (no code execution, no sandboxed tools) never provision a sandbox and pay zero container overhead.

The trigger is explicit: the `@tool` decorator carries a `sandbox: bool = False` flag. The Harness loop checks this flag before dispatch:

```python
if tool.sandbox and sandbox is None:
    sandbox = await sandbox_pool.provision(resource_spec)
    await session.emit_event(run_id, {"type": "sandbox_provisioned", "payload": resource_spec})
result = await (sandbox.execute(tool.name, tool.args) if tool.sandbox else dispatch_local(tool))
```

Container death is demoted to a tool-call error: `SandboxDead` → `sandbox = None` → error result appended to the Session log → the loop continues (can re-provision on the next sandboxed call). The Session is unaffected.

**Rationale:** The Anthropic blog attributes p95 TTFT −90% specifically to removing sandbox boot from the critical path via lazy provisioning. The mechanism is universal (Centaur, AX SubstrATE all suspend/evict the execution environment between turns), and the cost of NOT doing it is quantified. "Provision on the first sandboxed tool call" is the single highest-ROI architectural decision for a hosted Verso tier.

**Evidence:**
- `discovery-wildcard.md:52-56`: "containers are provisioned by the brain via a tool call only if they are needed"; TTFT −90% is explicitly from this mechanism.
- `discovery-wildcard.md:96-101`: DESIGNED reimplementation of the lazy sandbox trigger.
- AX `discovery-wildcard.md:287-293`: SubstrATE actor suspended 50 ms after each turn; `SuspendActor` → standby pool.

---

### Decision 5 — Crash recovery: `wake(run_id)` resumes from the last event

**Choice:** The recovery protocol is `get_events(run_id) → replay_to_messages() → resume loop`. Any Harness instance can recover any run. The recovery predicate (adapted from DBOS's startup recovery):

On worker startup:
```python
SELECT * FROM verso_runs WHERE status = 'PENDING' AND executor_id = <this_worker> AND agent_version = <current_version>
```
For each: reload `verso_steps` (the completed step memo map) + the conversation log, rebuild `messages[]`, re-enter the game loop from the first uncached step.

`MAX_RECOVERY_ATTEMPTS = 100` (DBOS default). A run that crashes the worker on every recovery attempt is flipped to `MAX_RECOVERY_EXCEEDED` — a poison-pill guard, not retried forever.

Two-tier failure classification (Temporal's architecture): a transient step error (network blip, OOM) retries the step / re-enters the game loop; only an explicit terminal failure (or MAX_RECOVERY_EXCEEDED) marks the run as `ERROR` and stops retrying. Conflating the two means a transient blip permanently kills a run.

**Rationale:** AX's `tryResuming` (single pending-exec marker + replay-since-N) and DBOS's startup recovery thread are the two most concrete implementations. The DBOS `MAX_RECOVERY_ATTEMPTS` poison-pill is a non-obvious but critical safety valve. The two-tier failure classification is Temporal's most important correctness invariant and equally applicable to Family B.

**Evidence:**
- Anthropic `discovery-wildcard.md:32-36`: "`wake(sessionId)` — boot a harness for a session; it then `getSession(id)` and resumes 'from the last event.'"
- AX `discovery-wildcard.md:268-277`: worked crash-resume trace, `tryResuming` algorithm.
- DBOS `infra-durable-execution.md:238-250`: `startup_recovery_thread`; `MAX_RECOVERY_ATTEMPTS = 100` (`_registrations.py:10`).
- Temporal `infra-durable-execution.md:104-110`: the two-tier classification (fail-the-task vs fail-the-workflow).

---

### Decision 6 — Durability modes (latency↔durability knob)

**Choice:** Three modes as a per-run config, default `async`:

| Mode | Behavior | Use case |
|---|---|---|
| `sync` | Persist step before next step starts | Critical agents where data loss is unacceptable |
| `async` (default) | Persist concurrently with the next step | Normal agents; best latency without sacrificing crash recovery |
| `exit` | Persist only on run completion | Cheap throwaway agents; tactical `durable=False` shortcut |

These map directly to `agent.run(task, durable=True, durability="async")` — `durability` is a sub-option of `durable=True`.

**Evidence:** LangGraph `infra-durable-execution.md:349-351`: `Durability = Literal["sync", "async", "exit"]`; `"exit"` skips `put_writes` (`_loop.py:459`).

---

### Decision 7 — HITL: named Durable Promise over HTTP

**Choice:** The HITL primitive is a **named Durable Promise** implemented per the Resonate Durable Promise specification. `ctx.hitl.request(question)` creates a named promise keyed to the current step, checkpoints the run (`status = SUSPENDED`), releases the worker, and resumes when the promise is resolved externally.

The high-level API (`PRD §6.1` intent is preserved):
```python
answer = await ctx.hitl.request("Approve sending this email?")
```

Under the hood:
1. The Harness emits `{"type": "hitl_requested", "promise_id": <step_hash>, "question": "..."}` into the Session log.
2. The backend writes `verso_promises(id=step_hash, state=PENDING, timeout=86400, run_id, step_hash)`.
3. The run status flips to `SUSPENDED`; worker is released.
4. External system calls `PATCH /promises/{id}` with `{state: "RESOLVED", value: {answer: true}}`.
5. The backend writes the resolved value into `verso_steps(run_id, step_hash, output={answer:true})`, flips the run back to `PENDING`, and re-dispatches it.
6. On next wake, `get_events` + `replay_to_messages` + game loop — the `hitl_requested` step now has a memoized output → returns the answer, no re-prompt.

SFN refinements applied:
- **Heartbeat + timeout**: if no resolve/heartbeat in `timeout` seconds → `REJECTED_TIMEDOUT` → run flips to ERROR with reason `hitl_timeout`.
- **Fresh promise id on step retry**: a retried step gets a new `step_hash` (because the loop counter advances); stale callbacks from the prior attempt cannot resolve the retried step.

**Rationale:** Resonate's named promise, Trigger.dev's token, AWS task token, Restate's Awakeable, Hatchet's `wait_for`, LittleHorse ExternalEvent — all the same primitive. The Resonate Durable Promise spec is the open published interface; adopting it means Verso's HITL backend is interoperable with any compliant resolver. AX's "log ends on an unanswered confirmation" (no callback registry) is the data-model implementation of the same idea.

**Evidence:**
- `infra-durable-execution.md:1140-1143`: "convergent invariant 3 — the HITL token is universal."
- Resonate `infra-durable-execution.md:720-797`: Durable Promise spec, HTTP API, state machine, idempotency keys.
- AX `discovery-wildcard.md:296-310`: "HITL = 'log ends on an unanswered question.'"
- Anthropic `discovery-wildcard.md:114-131`: checkpoint-before-pause, resume on different process.
- SFN `infra-durable-execution.md:1069-1080`: heartbeat + fresh-token-on-retry refinements.

---

### Decision 8 — Worker release during waits

**Choice:** A Verso agent paused on a HITL promise or a `durable_sleep` holds **zero** compute. The Harness checkpoints, flips the run to `SUSPENDED`, and returns. A scheduler alarm (backed by `verso_runs.available_at TIMESTAMPTZ`) or the promise resolve re-dispatches the run. No in-process `asyncio.sleep` for waits longer than ~1s.

Two-tier wait:
- **Short waits (<1s):** `asyncio.sleep` in-process (acceptable to hold the worker briefly).
- **Long waits / HITL:** `verso_runs.available_at = now() + duration; status = SUSPENDED` + worker released. The poller loop `SELECT ... WHERE status='SUSPENDED' AND available_at <= now()` re-enqueues them.

**Evidence:**
- `infra-durable-execution.md:1144-1147`: "convergent invariant 4 — release the worker during a wait. No system holds a worker thread blocked during a long HITL wait."
- CF Workflows `infra-durable-execution.md:1017-1023`: `scheduler.wait()` for short, DO alarm for long.
- AX `discovery-wildcard.md:287-293`: SubstrATE suspended 50 ms after each turn; woken by `ResumeActor`.
- Centaur `discovery-wildcard.md:361-378`: `workflow_runs.available_at` + reconcile loop at 0.5s interval.

---

### Decision 9 — Credential proxy: agent holds no secret

**Choice:** Verso's tool boundary is a **credential proxy chain**. The agent process and the Harness hold only a per-session opaque token; a proxy exchanges it for the real credential per destination host at egress. The implementation target:

```
@tool call → [validate (Salus-shaped)] → [resolve session-token→credential] → [inject per-host (Centaur iron-proxy-shaped)] → forward
```

For v1 / dev tier (no k8s): a localhost proxy process (mitmproxy or custom) configured by `@tool(secrets=[HttpSecret(host="api.github.com", inject_header="Authorization: Bearer")])`. The `HttpSecret` declaration is host-scoped by construction — a credential is only offered to its declared upstream.

Hard invariant (from Anthropic): the Harness is never made aware of credentials. The credential never enters the agent process or the LLM context.

Three supported secret modes (from Centaur iron-proxy `tool_manager.py:71-374`):
1. `INJECT` — proxy adds the header; tool emits nothing.
2. `REPLACE` — tool writes a placeholder token; proxy swaps for the real value.
3. `BROKER` — a token broker mints a short-lived OAuth2 token; proxy injects it with a TTL < broker lifetime.

**Rationale:** Three independent 2026 systems converge on "a credential/policy proxy in front of every tool, agent holds no secret." This is now an overdetermined design choice. The host-scoped credential is the security primitive: a prompt-injected agent trying to POST a GitHub token to `evil.com` gets no token (the proxy's rules block it).

**Evidence:**
- Anthropic `discovery-wildcard.md:114-131`: MCP proxy architecture; "harness never aware of credentials" (verbatim).
- Centaur `discovery-wildcard.md:322-340`: iron-proxy transforms, `rules:[{host:H}]` host-scoping, 7 transform types.
- Salus `discovery-wildcard.md:428-479`: pre-call validation proxy, 4-outcome taxonomy (allow/clarify/rewrite/block/escalate), 28ms latency, 58% recovery on blocked calls.
- `discovery-wildcard.md:558-565`: synthesis — "complete Verso tool boundary = validate → resolve → inject → forward."

**Alternatives rejected:**
- In-process secret injection (env vars loaded into the agent): the agent process itself can be exploited; prompt injection can exfiltrate secrets. The proxy boundary makes secrets structurally unreachable.
- Flat env bag (no host-scoping): any tool can be tricked into sending any credential to an unrelated upstream.

---

### Decision 10 — Single-writer per run + in-flight guard

**Choice:** Exactly one Harness worker drives a given run at any time. Concurrent activation of the same `run_id` returns a conflict error (`FailedPrecondition / 409`).

Implementation: `verso_runs.executor_id TEXT` column + a `SELECT ... FOR UPDATE` row-level lock on the run row before processing. A crashed worker's run row has a stale `executor_id`; the recovery thread claims it on startup.

**Evidence:**
- AX `discovery-wildcard.md:299`: "`inFlight map[string]struct{}` under a mutex; concurrent `Exec/Fork/Delete` on the same conversation returns `FailedPrecondition 'already in flight'.`"
- DBOS `infra-durable-execution.md:241`: `executor_id` filter; only the owning worker recovers its own pending runs.
- Restate `infra-durable-execution.md:496-498`: "all mutations to one object's durable K/V state are serialized server-side."

---

## Component Spec

### Interfaces (public, Python)

```python
# runtime/session.py — the durable event log (Anthropic Session shape)
class Session(Protocol):
    async def emit_event(self, run_id: str, event: dict) -> int:
        """Append event; returns monotonic seq for this run."""
        ...
    async def get_events(self, run_id: str, since_seq: int = 0) -> list[dict]:
        """Range-read: all events with seq > since_seq."""
        ...

# runtime/harness.py — the stateless loop
async def wake(
    run_id: str,
    session: Session,
    step_backend: CheckpointBackend,
    sandbox_pool: SandboxPool | None,
    *,
    max_recovery_attempts: int = 100,
) -> AgentResult:
    """
    Load the Session log, replay to messages[], enter the game loop.
    Holds zero durable state — every loop-relevant fact is in Session.
    """
    ...

# runtime/checkpoint.py — the 5-method backend interface (LangGraph shape, adapted)
class CheckpointBackend(Protocol):
    async def get_run(self, run_id: str) -> RunRecord | None: ...
    async def list_runs(self, *, status: str | None = None, limit: int = 100) -> list[RunRecord]: ...
    async def put_step(self, run_id: str, step_hash: str, step_name: str,
                       kind: StepKind, output: Any, error: Any = None) -> None:
        """Write-before-advance: called BEFORE the loop advances."""
        ...
    async def put_run(self, run_id: str, status: RunStatus, output: Any = None,
                      error: Any = None) -> None: ...
    async def get_steps(self, run_id: str) -> dict[str, Any]:
        """Returns {step_hash: output} memo map for the game loop."""
        ...

# runtime/sandbox.py
class SandboxPool(Protocol):
    async def provision(self, resource_spec: dict) -> Sandbox: ...

class Sandbox(Protocol):
    async def execute(self, tool_name: str, tool_input: dict) -> str:
        """Returns string result; raises SandboxDead on container failure."""
        ...
    async def close(self) -> None: ...

# runtime/promises.py — HITL Durable Promise (Resonate spec)
class PromiseBackend(Protocol):
    async def create(self, id: str, timeout_s: int, run_id: str, step_hash: str,
                     param: dict | None = None, tags: dict | None = None,
                     ikey_create: str | None = None) -> PromiseRecord: ...
    async def resolve(self, id: str, value: dict, ikey_complete: str | None = None) -> PromiseRecord: ...
    async def reject(self, id: str, value: dict, ikey_complete: str | None = None) -> PromiseRecord: ...
    async def heartbeat(self, id: str) -> PromiseRecord: ...
    async def get(self, id: str) -> PromiseRecord: ...
    async def timeout_scan(self) -> None:
        """Transition PENDING promises past their timeout to REJECTED_TIMEDOUT."""
        ...
```

### Data Schema (Postgres default backend)

```sql
-- Verso runs: one row per agent run (DBOS workflow_status shape)
CREATE TABLE verso_runs (
    run_id            TEXT PRIMARY KEY,
    agent_name        TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'PENDING',
        -- PENDING | SUSPENDED | SUCCESS | ERROR | CANCELLED | MAX_RECOVERY_EXCEEDED
    input             JSONB,
    output            JSONB,
    error             JSONB,
    executor_id       TEXT,                   -- which worker owns this run (recovery filter)
    recovery_attempts INT NOT NULL DEFAULT 0, -- poison-pill counter; cap = MAX_RECOVERY_ATTEMPTS
    agent_version     TEXT,                   -- in-flight upgrade guard (reject resume on mismatch)
    durability        TEXT NOT NULL DEFAULT 'async',  -- sync | async | exit
    available_at      TIMESTAMPTZ,            -- for SUSPENDED runs awaiting a timed wakeup
    created_at        BIGINT NOT NULL,
    completed_at      BIGINT
);

CREATE INDEX verso_runs_pending
    ON verso_runs (created_at) WHERE status = 'PENDING';
CREATE INDEX verso_runs_suspended_due
    ON verso_runs (available_at) WHERE status = 'SUSPENDED' AND available_at IS NOT NULL;

-- Step journal: memoization map, one row per completed step (DBOS operation_outputs shape)
CREATE TABLE verso_steps (
    run_id      TEXT NOT NULL REFERENCES verso_runs(run_id) ON DELETE CASCADE,
    step_hash   TEXT NOT NULL,   -- sha1(step_name) or sha1(f"{name}:{n}") for loop iterations (Inngest)
    step_name   TEXT NOT NULL,   -- human-readable, for debugging / HITL display
    kind        TEXT NOT NULL,   -- RUN | LLM | TOOL | SLEEP | HITL | SANDBOX (Hatchet kind + Inngest AI_GATEWAY)
    output      JSONB,
    error       JSONB,
    started_at  BIGINT,
    completed_at BIGINT,
    PRIMARY KEY (run_id, step_hash)   -- DBOS composite PK; ON CONFLICT DO NOTHING enforces write-once
);

-- Conversation event log: the user-visible, seq-ordered turn stream (AX ConversationEvent shape)
CREATE TABLE verso_events (
    run_id  TEXT NOT NULL REFERENCES verso_runs(run_id) ON DELETE CASCADE,
    seq     INT  NOT NULL,   -- monotonic per run; allocated as MAX(seq)+1 (AX sqlite.go:82-90)
    type    TEXT NOT NULL,   -- user | assistant | tool_use | tool_result | hitl_requested |
                              -- hitl_resolved | sandbox_provisioned | error
    payload JSONB NOT NULL,
    ts      BIGINT NOT NULL,
    internal_only BOOL NOT NULL DEFAULT FALSE, -- persist but don't surface to client (AX internal_only flag)
    PRIMARY KEY (run_id, seq)
);

-- HITL Durable Promises (Resonate Durable Promise spec, verbatim + Verso lineage extension)
CREATE TABLE verso_promises (
    id           TEXT PRIMARY KEY,
    state        TEXT NOT NULL DEFAULT 'PENDING',
        -- PENDING | RESOLVED | REJECTED | REJECTED_CANCELED | REJECTED_TIMEDOUT
    timeout      BIGINT,          -- epoch ms; auto-transitions to REJECTED_TIMEDOUT
    param        JSONB,
    value        JSONB,
    tags         JSONB,
    ikey_create  TEXT,            -- two-key idempotency (Resonate spec)
    ikey_complete TEXT,
    run_id       TEXT,            -- Verso lineage (spec lacks this)
    step_hash    TEXT,            -- which step this promise is blocking
    created_on   BIGINT,
    completed_on BIGINT
);
CREATE INDEX verso_promises_pending_timeout
    ON verso_promises (timeout) WHERE state = 'PENDING';

-- Sandbox assignments: session→sandbox binding (Centaur assignment_generation shape)
CREATE TABLE verso_sandboxes (
    run_id           TEXT NOT NULL REFERENCES verso_runs(run_id),
    generation       BIGINT NOT NULL DEFAULT 1,  -- bumped on each (re)provision
    status           TEXT NOT NULL,              -- provisioning | active | dead | released
    resource_spec    JSONB,
    provisioned_at   BIGINT,
    released_at      BIGINT,
    PRIMARY KEY (run_id, generation)
);
```

### Key Constants and Defaults

| Constant | Value | Source |
|---|---|---|
| `MAX_RECOVERY_ATTEMPTS` | `100` | DBOS `_registrations.py:10` |
| `HITL_DEFAULT_TIMEOUT_S` | `86400` (24h) | SFN 1-year max; 24h is a sane production default |
| `HEARTBEAT_TIMEOUT_S` | configurable per promise, default `3600` (1h) | SFN `HeartbeatSeconds` pattern |
| `RECOVERY_POLLER_INTERVAL_S` | `0.5` | Centaur `WORKFLOW_RECONCILE_INTERVAL_S=0.5` (`workflow_engine.py:161`) |
| `WORKER_LEASE_S` | `30` | Centaur `workflow_engine.py:167` |
| `LEASE_HEARTBEAT_INTERVAL_S` | `lease_s / 3 = 10` | Centaur `workflow_engine.py:1108` |
| `DEFAULT_DURABILITY` | `"async"` | LangGraph compile default |
| `STEP_HASH_ALGO` | `sha1(name)` / `sha1(f"{name}:{n}")` | Inngest `transforms.py:30` |
| `SEQ_ALLOCATION` | `MAX(seq)+1` per run, PK enforces uniqueness | AX `sqlite.go:82-90` |
| `MAX_TOOL_CONCURRENCY` | `5` | PRD §5.3; Anthropic best practices |
| `IDLE_SUSPEND_DELAY_MS` | `50` | AX `server_ate.go:74-90` (`go suspendActor` fires 50ms after each Exec) |
| `SANDBOX_BOOT_TIMEOUT_S` | `30` | DESIGNED (no published number; reasonable container-cold-start budget) |
| `STEP_KIND` values | `RUN \| LLM \| TOOL \| SLEEP \| HITL \| SANDBOX` | Hatchet `kind ∈ {RUN,WAIT_FOR,MEMO}` extended |

### The Game Loop (Harness pseudocode)

```python
async def wake(run_id, session, step_backend, sandbox_pool, ...):
    # 1. Rehydrate from the Session log (Anthropic: "getSession(id) → load events → resume from last event")
    events = await session.get_events(run_id)
    completed_steps = await step_backend.get_steps(run_id)   # {step_hash: output}
    messages = replay_to_messages(events)

    sandbox: Sandbox | None = None   # LAZY — not provisioned until first sandboxed tool call

    ctx = DurableCtx(run_id=run_id, completed=completed_steps, backend=step_backend)

    # 2. CF game loop: re-enter, memoize by step_hash, run to first miss
    while not ctx.budget_exhausted():
        # LLM call is itself a durable step (Inngest AI_GATEWAY opcode is the reference)
        step_hash = sha1_step(f"llm:{ctx.turn_count}")
        if step_hash in ctx.completed:
            response = ctx.completed[step_hash]
        else:
            response = await model.call(assemble_context(messages, ctx))
            await step_backend.put_step(run_id, step_hash, "llm", "LLM", response)  # WRITE-BEFORE-ADVANCE
            ctx.completed[step_hash] = response
        await session.emit_event(run_id, {"type": "assistant", "payload": response})

        if response.stop_reason == "end_turn":
            await step_backend.put_run(run_id, "SUCCESS", output=response.content)
            return AgentResult(output=response.content, stop_reason=StopReason.end_turn, ...)

        for tu in response.tool_calls:
            step_hash = sha1_step(f"tool:{tu.name}:{ctx.tool_count}")
            if step_hash in ctx.completed:
                result = ctx.completed[step_hash]
            else:
                if tu.needs_sandbox and sandbox is None:   # LAZY SANDBOX (Anthropic)
                    sandbox = await sandbox_pool.provision(tu.resource_spec)
                    await session.emit_event(run_id, {"type": "sandbox_provisioned"})
                try:
                    result = (await sandbox.execute(tu.name, tu.args)
                              if tu.needs_sandbox else await dispatch_local(tu, ctx))
                except SandboxDead:
                    sandbox = None   # container death = tool-call error, NOT run death
                    result = {"error": "sandbox died; may retry"}
                await step_backend.put_step(run_id, step_hash, tu.name, "TOOL", result)  # WRITE-BEFORE-ADVANCE
                ctx.completed[step_hash] = result

            if isinstance(result, HITLRequest):              # HITL = a suspend point (AX pattern)
                await step_backend.put_run(run_id, "SUSPENDED")
                raise StepSuspend(waiting_on=result.promise_id)  # worker released

            messages.append(tool_result_message(tu, result))
            await session.emit_event(run_id, {"type": "tool_result", "payload": result})
```

### HTTP HITL Endpoints (Resonate Durable Promise spec, minimal)

```
POST   /v1/promises                     Create a promise
GET    /v1/promises/{id}                Read a promise
PATCH  /v1/promises/{id}               Complete (resolve/reject/cancel)
  headers: idempotency-key, strict
  body: {state: "RESOLVED"|"REJECTED"|"REJECTED_CANCELED", value?: {...}}
POST   /v1/promises/{id}/heartbeat     Extend the HITL timeout (SFN SendTaskHeartbeat)
POST   /v1/promises/{id}/callback      Register a webhook for completion
GET    /v1/runs/{id}/pending_hitl      List unresolved promises for this run (operator view)
```

### Resumable streaming: `seq`-watermark reconnect (AX `--last-seq`)

Client tracks `last_seq`; on reconnect sends `GET /v1/runs/{id}/events?since_seq=N`. Server re-streams all events with `seq > N`. Returns `404` if `N` is not a real event boundary (AX's hard rule: reject a stale watermark, don't silently replay all). No server-side cursor; no session affinity required. This is the entire resumable-streaming protocol.

### Credential Proxy Interface (Centaur iron-proxy shape, simplified for v1)

```python
@dataclass
class HttpSecret:
    host: str                      # destination host pattern (e.g. "api.github.com")
    mode: Literal["inject", "replace", "broker"] = "inject"
    inject_header: str | None = None   # e.g. "Authorization: Bearer {value}"
    replace_token: str | None = None   # placeholder the tool writes; proxy swaps it
    source: Literal["env", "vault"] = "env"
    env_var: str | None = None
    vault_ref: str | None = None   # e.g. "op://vault/github/token" (1Password)
    ttl_s: int = 600               # Centaur default 10m

# @tool usage:
@tool(secrets=[HttpSecret(host="api.github.com", inject_header="Authorization: Bearer", source="env", env_var="GITHUB_TOKEN")])
async def github_search(query: str) -> dict:
    ...  # tool makes ordinary HTTPS calls; proxy injects the credential at egress
```

---

## Open Unknowns

1. **Sandbox provider for v1.** PRD defers this to Phase 3 (`E2B/Modal/V8 isolate`). The topology design above is provider-agnostic (`SandboxPool` protocol), but the concrete lazy-provision latency (the "how expensive is the first sandboxed tool call") depends on the provider. Must be measured — p95 provision latency determines whether lazy is truly transparent or adds a noticeable hitch.

2. **`replay_to_messages()` fidelity.** The game loop requires reconstructing the exact `messages[]` array the LLM expects from the event log. This is straightforward for simple text+tool_use turns, but the ordering of `tool_result` messages and multi-tool-call batches can diverge from what the provider expects if not implemented carefully. Needs a test that round-trips a complex multi-step session through crash+resume and byte-compares the reconstructed context against the original.

3. **`internal_only` events and sub-agent isolation.** AX's `internal_only=true` flag (persist-but-don't-emit-to-client) is specified but the exact predicate for what goes `internal_only` in Verso's event schema is DESIGNED. Needs dogfooding to identify which scratch/tool-plumbing state should survive a crash without polluting the conversation transcript or sub-agent prompts.

4. **Credential proxy for non-k8s v1.** The Centaur iron-proxy is a full MITM-TLS Go binary with per-sandbox NetworkPolicy — right for a k8s production tier, overkill for a local dev `pip install`. The v1 equivalent (a localhost mitmproxy or a thin header-injecting httpx transport) needs a concrete implementation decision. The `HttpSecret` declaration interface above is stable; the proxy backend is not.

5. **`available_at` vs event-push for HITL resume.** The current design polls `verso_runs WHERE status='SUSPENDED' AND available_at <= now()` (Centaur's reconciler model). An event-push model (the external resolve directly re-dispatches the run via a job queue or a WebSocket/SSE channel) would reduce resume latency from up to `RECOVERY_POLLER_INTERVAL_S=0.5s` to near-instant. Whether that latency matters depends on HITL use cases (human approval: 0.5s is fine; automated tool callbacks: 0.5s may be too slow). Dogfood before deciding.

6. **`agent_version` compatibility check.** The schema includes `agent_version` to guard against resuming a run under an incompatible agent definition (DBOS `application_version`, LittleHorse `old_wf_spec_versions[]`). The exact compatibility semantics — what constitutes a "compatible" version change (e.g. adding a new tool is safe; renaming a tool used in a prior step is not) — needs a policy decision and a test harness (Temporal's `Replayer` is the reference: re-run recorded histories against new code and assert step-sequence stability).

7. **Step hash stability under loop refactoring.** The Inngest `:n` counter disambiguates repeated step names in a loop. But if a developer adds a NEW step before an existing one in the loop body, all subsequent steps in that loop iteration get a new `:n` index → step hashes shift → the recovery game loop replays them from scratch (treating them as cache misses), potentially re-calling the LLM/tools for already-completed steps. This is the same "refactor brittleness" DBOS/Windmill have with ordinal schemes, partially mitigated by name-based hashing. The question is whether Verso needs a stricter contract (e.g. "step names must be stable within a run version") or a migration tool (cf. DBOS's `fork_workflow(id, start_step)` restart-from-step). No good answer yet; needs dogfooding to see how often this bites.
