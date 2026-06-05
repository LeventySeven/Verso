# Adversarial Critique: seam-mechanism — Scale & Failure Lens

**Date:** 2026-06-05
**Decision under review:** The tactical↔durable seam = `durable=True` appends exactly one `PersisterHook` (PostRunStepHook); the ReAct loop body is byte-identical both ways (Burr `application.py:2565`). "One-line diff, zero loop changes."
**Lens:** SCALE & FAILURE — crash mid-step, high concurrency, 1M-token context, cost blow-up, partial writes, clock skew, Postgres bottleneck, eviction/replay edge cases, non-idempotent tool double-fire, hot-path latency.

---

## The attack

**The resolution's source claim holds.** Burr `application.py:2565` (`_set_sync_state_persister`) and `persistence.py:214` (`PersisterHook`) are exactly as described. The loop at `application.py:949-1003` fires hooks in a `finally` block with zero awareness of whether a persister exists. The "one-line diff, zero loop changes" seam claim is verified against HEAD. This is not the attack.

**The attack is on the default durability mode (`DurabilityMode.ASYNC`) combined with the 30-second lease, and the specific failure it causes at 10× when LLM call latency exceeds the lease window.**

### Failure mode 1 — The lease-race under a long LLM call (the primary attack)

`WORKER_LEASE_SECONDS = 30`, `WORKER_HEARTBEAT_SECONDS = 10`. The heartbeat is a background asyncio task (`extend_lease`). The LLM call is also an asyncio task. Both run on the **same event loop**.

A 1M-token context sent to Claude Opus 4 (extended thinking enabled) can hold the event loop in a streaming-receive coroutine for 90–180 seconds — well past the 30-second lease. In Python's asyncio, a coroutine that is actively consuming an SSE stream and `await`-ing tokens does yield control between `await` points, but the heartbeat task competes for scheduling on the same loop. Under high CPU contention (Python GIL, base64 JSON decode of large tool results) or a stalled stream, the heartbeat misses its window.

**The consequence:** `recover_expired_runs` on another worker flips the stale run back to `queued` and claims it. The original worker's LLM call eventually completes and tries to call `put_step_output`. The Centaur fencing guard (`SELECT status, worker_id ... FOR UPDATE`) should catch this — if `worker_id != self._worker_id`, raise `StaleWorkerError`.

**The gap the resolution does not address:** `StaleWorkerError` is described in D9's rationale but is **not in the `CheckpointBackend` ABC**, **not in the exception hierarchy**, and **not in the `DurableExecutor.run()` spec**. The resolution describes the fencing concept but does not specify what the executor does when it receives `StaleWorkerError`. The two possibilities are both bad:

- If it re-raises up to the caller → the original worker's `agent.run(durable=True)` raises an exception to the user, even though the run is still alive on the re-claiming worker. The user sees a failure that isn't one.
- If it silently absorbs it → the original worker continues to execute steps on a run it no longer owns. The re-claiming worker starts the same LLM call (cache miss in its empty in-process memo dict, since it just loaded from DB before the conflicting step was written). Now two concurrent LLM calls are in flight for the same step of the same run.

At 10× workers handling 10× agents, every agent run that touches a 1M-token context is a latent race. With `WORKER_CONCURRENCY = 2` and 10 workers, 20 concurrent runs, even one slow 90-second step per 30 seconds of lease = ~1/3 of all long-context runs are in this failure window at any given time.

### Failure mode 2 — ASYNC mode is the default, opt-out is per-step, and users won't do it

`DURABILITY_DEFAULT = DurabilityMode.ASYNC`. In ASYNC mode: "step fn runs → `asyncio.create_task(backend.put_step_output(...))` → step result returned IMMEDIATELY." The resolution acknowledges this creates a crash window, and says "for destructive / non-idempotent tool calls, use `SYNC` mode per-step."

This inverts the safe default. The dangerous mode (ASYNC, with a crash window) is the default. The safe mode (SYNC, no crash window) requires the user to identify every destructive tool and add a `durability=DurabilityMode.SYNC` kwarg. The `@tool(destructive=True)` decorator exists — but the resolution does not specify that `destructive=True` automatically forces `ctx.step` to SYNC mode. That inference is available but not made explicit. In practice: a user who writes `@tool(destructive=True)` and calls it via `ctx.step("send_email")` will still get ASYNC durability unless they also pass `durability=DurabilityMode.SYNC` to `ctx.step`. One unguarded destructive tool in a long run = a double-fire on crash.

At production scale with a team (or even a solo builder who forgets), the decorator-to-step coupling is a sharp edge that will bite.

### Failure mode 3 — `verso_run_events.seq` race in ASYNC mode

The schema uses `PRIMARY KEY (run_id, seq)` on `verso_run_events`. The resolution says `append_event` "returns the new seq." In ASYNC mode, two concurrent `asyncio.create_task(backend.append_event(...))` calls can race. If seq is application-allocated (e.g., `SELECT MAX(seq)+1`), both tasks read the same MAX and try to insert the same PK → one gets a conflict. If the implementation uses `ON CONFLICT DO NOTHING`, the second event is silently dropped. If it retries, the ordering guarantee is broken.

The correct fix is a Postgres `SEQUENCE` or `RETURNING` on a serial/identity column — but this is not specified in the schema (the schema shows `seq INT NOT NULL` with no `DEFAULT nextval(...)` or `GENERATED ALWAYS AS IDENTITY`). At 1 worker with 2 concurrent agents both emitting `TOOL_USE` events simultaneously, this race is live.

### Failure mode 4 — Unbounded replay cost on crash-resume cycles

On crash-resume, `DurableExecutor.run()` does "load all step_outputs into an in-process memo dict." This is a `SELECT * FROM verso_step_outputs WHERE run_id = ?`. For a long-running agent (1000 steps, each with a serialized LLM response of ~8KB average = 8MB of JSONB), this SELECT returns 8MB+ of data on every resume. The Open Unknown #3 (journal compaction) defers this, but deferred means there is no mechanism in the current design. At step 1000 with no compaction, a crash causes an 8MB Postgres scan before the loop can even restart. Multiply by `MAX_RECOVERY_ATTEMPTS = 100` (each attempt reschedules the run, which triggers a new full load) and a pathological single run can cause 100 × 8MB = 800MB of total DB reads just from resume overhead.

The resolution references Temporal's `continue_as_new` as the fix but says "decide after first dogfood run that produces >500 steps." This is a genuine defer (not an oversight), but it means the design has no upper bound on replay latency, which is a production correctness issue for any run that outlives its dogfood phase.

### Failure mode 5 — Postgres as a single-point serialization bottleneck for the heartbeat

`claim_pending_runs` uses `SELECT ... FOR UPDATE SKIP LOCKED`. The SKIP LOCKED clause prevents deadlocks between workers competing for the same run — this is correct. But `extend_lease` uses `UPDATE worker_lease_expires_at = NOW() + lease_seconds WHERE run_id=? AND worker_id=?`. With N workers each heartbeating at 10s intervals, this is `N × WORKER_CONCURRENCY` writes per 10 seconds, plus step writes, plus event appends, all hitting one Postgres instance. For solo dogfood at WORKER_CONCURRENCY=2, this is trivial. The resolution's claim "Postgres is sufficient" rests on DBOS/Centaur/LangGraph evidence, all of which are similarly solo/small-team systems. The claim is true for solo scale. The failure at 10× is a Postgres write throughput ceiling: at >50 concurrent workers (a reasonable production deployment for a popular agent), the heartbeat+step write+event append mix saturates Postgres at ~1000 writes/second on commodity hardware, before connection pool exhaustion even enters the picture.

This is not a design flaw — it is a documented single-DB design with a known ceiling. The resolution should name the ceiling explicitly so it can be planned around.

---

## Does it break it?

**Partially, at one specific failure mode.** Failure modes 2, 3, 4, and 5 are **real production gaps but not fatal** — they are either deferred-and-known (journaling compaction, Postgres ceiling) or fixable in implementation without changing the API or the seam design (ASYNC→SYNC auto-promotion for `destructive=True`, seq via DB-native identity column).

**Failure mode 1 is the genuine breach**: the lease-expiry race under a long LLM call leaves `StaleWorkerError` handling unspecified. The seam design (hook in `finally`, zero loop awareness) is correct and verified. But the *executor contract* has a hole: what the `DurableExecutor` does when it receives a `StaleWorkerError` from `put_step_output` is not specified, and the two sensible behaviors both produce user-visible breakage. The seam itself survives; the executor that drives the seam does not survive a 90-second LLM call at a 30-second lease.

The decision as stated ("one-line diff, zero loop changes — the seam test holds") is **true**. The seam test is not the failure. The failure is one level up: the executor-level contract for the race between a slow LLM call and a lease expiry is incomplete, and at 10× it fires on every long-context agent run.

**Verdict: REVISE** — the seam mechanism survives; the executor's `StaleWorkerError` handling must be specified before the durable runtime is production-ready.

---

## Evidence checked

| Claim | File checked | Verdict |
|---|---|---|
| `application.py:2565` `_set_sync_state_persister` appends one `PersisterHook` | Cloned apache/burr HEAD; read `burr/core/application.py:2565-2588` | CONFIRMED verbatim |
| `application.py:949-993` loop fires `post_run_step` in `finally` with no durability awareness | Read `application.py:949-1003` | CONFIRMED; `new_state` is the pre-exception state on crash, hook fires regardless |
| `persistence.py:214` `PersisterHook` is a 4-line `PostRunStepHook` | Read `persistence.py:214-234` | CONFIRMED; 4 lines exactly as described (20 with full signature) |
| `DURABILITY_DEFAULT = DurabilityMode.ASYNC` | `durable-runtime.md` D5 + D10 constants block | CONFIRMED |
| `WORKER_LEASE_SECONDS = 30`, `WORKER_HEARTBEAT_SECONDS = 10` | `durable-runtime.md` D10 constants block | CONFIRMED |
| `StaleWorkerError` described in D9 rationale | `durable-runtime.md` D9 | CONFIRMED as concept; absent from ABC, exception hierarchy, executor spec |
| `seq INT NOT NULL` with no DB-native sequence | `durable-runtime.md` D4 schema block | CONFIRMED; `seq INT NOT NULL` only; no `GENERATED ALWAYS AS IDENTITY` |
| LLM call wrapped in `ctx.step("llm_call_{n}")` | `durable-runtime.md` D9 | CONFIRMED in spec; implementation unwritten |
| `destructive=True` does NOT auto-force SYNC on `ctx.step` | Cross-read `api-and-peers.md` D4 + `durable-runtime.md` D5 | CONFIRMED as gap; `@tool(destructive=True)` sets tool policy; `ctx.step` durability is a separate kwarg |

---

## Recommendation

Four concrete fixes, ordered by severity:

**1 (Must fix before first durable run): Specify `StaleWorkerError` handling in `DurableExecutor`.**
Add to the executor spec: on receiving `StaleWorkerError` from `put_step_output`, the executor must (a) cancel any in-flight LLM streaming coroutine, (b) log and silently exit the run (the run is alive on the re-claiming worker), (c) NOT propagate an exception to the user's `await agent.run()` call. The `agent.run(durable=True)` contract must be "returns when the run completes OR yields control to a re-claiming worker; in the latter case, use `agent.attach(run_id)` to reconnect." This is a behavioral contract, not a seam change.

Alternatively: raise `WORKER_LEASE_SECONDS` from 30 to 300 (5 minutes) for long-context use, and document 30s as the low-latency default for short-step agents. Centaur's 30s is appropriate for 1-5 second steps; it is not appropriate for 90-second LLM calls. Make it configurable at the `DurableExecutor` level, not just a file-level constant.

**2 (Must fix before multi-worker deployment): Force `ctx.step` to SYNC mode when the tool is `destructive=True`.**
The `@tool(destructive=True)` decorator already signals non-idempotency. The executor should automatically use `DurabilityMode.SYNC` for any `ctx.step` call whose `kind=StepKind.TOOL_CALL` and whose tool has `destructive=True`. This removes the per-step opt-in requirement and closes the double-fire window without requiring users to remember the `durability=` kwarg. ASYNC remains the default for LLM calls and read-only tools.

**3 (Must fix before first public deploy): Use a DB-native sequence for `verso_run_events.seq`.**
Replace `seq INT NOT NULL` with `seq BIGINT GENERATED ALWAYS AS IDENTITY` in the DDL, or use a Postgres `SEQUENCE` object and `nextval()` on insert. This makes `append_event` race-safe at zero application cost. Do not allocate seq in application code.

**4 (Defer OK, but note the ceiling explicitly): Name the Postgres write throughput ceiling.**
Add to D3 a one-sentence caveat: "The single-Postgres design is production-sufficient for <50 concurrent workers; above that, a connection pool limit (PgBouncer) or a read-replica for event polling is required." This is not a design change — it is a known tradeoff that the resolution currently does not state, and that a future deployer will hit at 10×.

The seam mechanism itself — one `PersisterHook`, loop byte-identical, verified at `application.py:2565` — **survives**. It is not the failure point. The executor contract around lease expiry is.
