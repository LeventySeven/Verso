# Durable-Reality Validation — Prefect (raw extraction)

**Source read:** `/Users/seventyleven/Desktop/researchfms/teardowns/PREFECT.md` (1415 lines, 95 KB; bounded reads + full grep).
**Target of teardown:** `PrefectHQ/prefect` — but **scoped explicitly to the FastAPI REST server layer only** (`prefect.server`). Per line 4: *"the FastAPI layer only … **Not the orchestration engine, the scheduler, the event system, or the CLI.**"*

> **CRITICAL CAVEAT FOR THIS UNIT.** This teardown does **not** read Prefect's durable-execution engine. The Temporal-like primitives the task asked for — task retries, idempotency keys, result caching/checkpointing, resume, flow state machines — are the *domain* of this server (it serves `flow_runs`, `task_runs`, `deployments`, `work_queues`, `states`) but the **engine internals that implement durability are out of scope and NOT in the source.** What IS extractable is (a) the *shape* of the durable-orchestration domain as exposed over REST, and (b) a set of genuinely strong **server-side reliability primitives** that are directly comparable to Verso's checkpoint/resume/repair seam. Everything below is marked KNOWN (in source) vs INFERRED. I do **not** fabricate engine internals.

---

## A. Durable-orchestration domain shape (KNOWN, as exposed by the REST surface)

The server's resource model *is* the Temporal-like vocabulary, even though the engine logic is elsewhere:

- **Routers (line 11):** `api/{flows,flow_runs,deployments,task_runs,work_queues,admin}.py` plus `workers.py`, `concurrency_limits`, `automations`, `variables`, `block_types`, `block_schemas`, `csrf_token`, `events`.
- **The durable unit hierarchy:** `flow` → `flow_run` → `task_run`; `deployment` (a schedulable, parametrized flow); `work_queue` / `work_pool` / `worker` (the dispatch substrate); `state` (run lifecycle). KNOWN from router list + `download_logs` columns `["timestamp","level","flow_run_id","task_run_id","message"]` (line 406).
- **Concurrency limits as a first-class resource** (`concurrency_limits` router, line 287) — distributed run-concurrency caps live server-side, not in the worker.
- **Idempotent create at the API contract** (line 363, `api/flows.py:28,42-43`): `create_flow` injects `response: Response` and sets `response.status_code = 201` only when the row was **newly created** (`model.created >= right_now`); a duplicate create returns the **existing** row with 200. KNOWN. This is idempotency expressed as "create-or-return-existing" with status-code disambiguation — not an idempotency-key table, but the same intent at the HTTP layer.

**INFERRED (not in source, do not cite as fact):** Prefect's actual retry/idempotency-key/result-caching/checkpoint engine lives in `prefect.client` + `prefect.results` + the state-transition orchestration (`orchestration/` rules) — none of which this teardown opened.

---

## B. Server-side reliability primitives that DO validate against Verso's seam (KNOWN)

### B1. DB-error → retryable HTTP status mapping (the standout) — `server.py:326-352,402-424`
The catch-all exception handler discriminates **transient** DB faults from **deterministic** ones and encodes retry semantics in the status code so an SDK can blindly retry:

| Condition | Status | Meaning |
|---|---|---|
| `is_client_retryable_exception(exc)` True | **503** | transient — client retries |
| `IntegrityError` (unique/FK) | **409** | deterministic conflict — retry won't help |
| `ObjectNotFoundError` | **404** | domain not-found |
| `RequestValidationError` | **422** | (echoes `request_body` back) |
| else | **500** | genuine bug — do NOT retry |

`is_client_retryable_exception` (line 1126, full verbatim in source D4) returns True for:
- SQLite `OperationalError` **only if** `sqlite_errorname ∈ {SQLITE_BUSY, SQLITE_BUSY_SNAPSHOT}` or message == "database is locked";
- asyncpg `QueryCanceledError` (statement timeout), `ConnectionDoesNotExistError`/`CannotConnectNowError` (failover/restart);
- SQLAlchemy `DBAPIError`, `InvalidRequestError`, `DetachedInstanceError` (session-state races).

**Load-bearing subtlety (line 1202):** the predicate does an **early `return False`** for non-busy SQLite `OperationalError` because `OperationalError` *is a* `DBAPIError` — without the early return, a SQLite *syntax* error would wrongly fall through into the broad `DBAPIError` retryable branch and become a spurious 503. *"a subtle bug-magnet."*
A logging `Filter` (`_SQLiteLockedOperationalErrorFilter`, line 133-167) suppresses uvicorn spam for these expected, client-handled lock errors unless `log_retryable_errors` set.

### B2. Explicit transaction control via injected DB *interface* (not session) — `database/interface.py:148-168`
Handlers inject `PrefectDBInterface` and open transactions themselves:
```python
async with db.session_context(begin_transaction=True) as session:  # COMMIT on clean exit, ROLLBACK on exception
```
`begin_transaction=True` wraps a real SQL transaction; `with_for_update=True` adds `SELECT … FOR UPDATE` row locking (line 357). Rationale (INFERRED, line 359): one request may need *multiple independent transactions* or *none*; per-handler control beats session-per-request. **Cost called out honestly (line 691):** a forgotten `begin_transaction=True` *"silently fails to commit"* — a real footgun.

### B3. Idempotent lifespan with a guard set — `server.py:903-937`
`LIFESPAN_RAN_FOR_APP` (module-global `set`) guards migrations/services from running twice for the same app object in one process (ephemeral mode spins up many apps). All background runtime (a `Docket` task queue, `background_worker`, `Services.running()`) is owned by **one `AsyncExitStack`** entered in the lifespan and unwound in reverse on shutdown (line 456). `Services` *type* is selected by deployment mode (`RunInEphemeralServers`/`RunInWebservers`/`Service`).

### B4. Concurrency cap as backpressure for the durable store — `server.py:277-292, 989-994`
`RequestLimitMiddleware` is **raw-ASGI** (3-arg `__call__`), wrapping the app in `anyio.CapacityLimiter(100)` — at most 100 requests in flight. Installed **only for the SQLite dialect** (line 989-994) because *"SQLite serializes writes; past a concurrency threshold, concurrent write transactions throw SQLITE_BUSY"* (line 1072). `CapacityLimiter` chosen over `asyncio.Semaphore` for anyio-task integration + runtime-adjustable limit (line 1073). Must be raw-ASGI, not `BaseHTTPMiddleware`, or it buffers the response and breaks streaming.

### B5. Migrations on start — `server.py:440`
`run_migrations()` does alembic create/upgrade in the lifespan if `PREFECT_API_DATABASE_MIGRATE_ON_START`. The durable store's schema is versioned and auto-migrated at boot. KNOWN.

### B6. Subprocess ephemeral-server supervisor — `SubprocessASGIServer` (D5, line 1205, 1411)
- **Port-keyed singleton** via `__new__` + `_initialized` guard: `SubprocessASGIServer(port)` returns the same object per port; re-`__init__` is a no-op.
- Launched with uvicorn `--factory "prefect.server.api.server:create_app"` (import string, not an app object) + `--lifespan on` so migrations/services run in the child.
- **Exit-code-3 = "address in use"** → pick a new random port from 8000-9000, respawn (`time.sleep(random.uniform(0.1,0.5))  # Random backoff`, line 1263), then poll `GET /health` until 200 or timeout.
- `stop()` reaps `terminate → wait(5) → kill → wait` (no zombies), cleans registry under `_instance_key` (port may have changed during collision retry).

---

## C. Validation verdict for Verso's checkpoint/resume/repair_history seam

**What a REAL durable substrate confirms Verso must OWN (to keep the "one flag" promise):**
1. **Transient-vs-deterministic error discrimination** (B1) — Verso's `RetryPolicy`/typed error taxonomy (auth/content fail fast) is *exactly* the B1 pattern at the model layer; B1 validates that this discrimination must be a first-class predicate, not ad-hoc. **Verso already has this.**
2. **Idempotency at the boundary** (A idempotent-create, B3 lifespan guard) — Verso's durable seam already advertises "idempotent-up-to-request" HITL and `repair_history` orphan-tool-call repair. B3's `LIFESPAN_RAN_FOR_APP` guard is the same shape: a crash-safe "did this side-effect already run?" gate. **Verso already has the concept; the seam must keep owning the replay-idempotency guard itself** (you can't delegate "did this tool already fire?" to the store).
3. **Explicit transaction/commit boundaries with a named footgun** (B2) — the *"forgotten begin_transaction silently fails to commit"* warning maps directly onto Verso's "checkpoint each step / crash-recoverable" claim: the seam must make the commit-point explicit and hard to forget (Verso checkpoints per-step, which is the safer default than per-handler).

**What Verso correctly DEFERS/composes (does NOT need to build):**
- **The durable store engine itself** — Prefect leans entirely on SQLAlchemy + alembic + a SQL DB for durability. Verso defers identically (`SqliteCheckpointStore`; can compose DBOS/Temporal as the backing store). Confirmed correct: even Prefect, a dedicated orchestrator, does **not** invent its own durable log — it sits on SQL.
- **A distributed worker/work-queue/work-pool dispatch substrate** (A) — this is orchestration-platform territory, NOT agent-framework territory. Verso's NON-GOAL ("no orchestrator-as-primitive") is validated: Prefect needs `work_queues`/`workers`/`concurrency_limits` because it schedules arbitrary user flows across a fleet; an agent loop does not.
- **The full flow/deployment/schedule resource model** — graph-of-tasks scheduling is exactly the "force the graph" Verso refuses.

**What Verso must NOT copy (avoid-overkill):**
- The three-FastAPI-app mount composition, `del router.routes`+`gc.collect()` 50 MB reclaim, response-scoped `AsyncExitStack`, CSRF double-submit middleware, app-caching keyed on `settings.hash_key()` — all are **HTTP-server engineering**, irrelevant to an in-process agent library. Verso is "Python-only library, not an SDK/server" — these are the wrong layer.
- The per-handler `session_context` boilerplate (line 691) is explicitly flagged as a DRY cost; Verso's per-step checkpoint default avoids this entire class of "forgot to commit" bug.

---

## D. One genuinely additive idea worth flagging (low bar caution)
B1's `is_client_retryable_exception` predicate with the **early-`return False` to stop a specific exception leaking into a broader retryable branch** is a *quality* refinement of error-taxonomy classification. Verso already has a typed error taxonomy + FailoverModel + RetryPolicy, so this is **verso-already-has at the primitive level**; the only stealable nuance is the *discipline* of ordering specific-before-general in the classifier so a non-transient subclass of a transient base never wrongly retries. Additive, byte-identical-when-unused (it's just classifier ordering), on-thesis (reliability). Borderline — flagged honestly, not oversold.
