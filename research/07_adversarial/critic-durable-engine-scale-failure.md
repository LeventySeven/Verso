# Adversarial Critique — durable-engine (SCALE & FAILURE lens)

**Decision under review:** Build an in-house durable-execution engine (pure Python + Postgres, DBOS-style step-memoization, sha1 step ids, AX two-log, 3 durability modes, 4-table schema); reject Temporal/Trigger.dev for v1.
**Lens:** SCALE & FAILURE — concrete failure modes the resolution does NOT handle. Does the chosen default survive production, or only the happy path?
**Resolution sources read:** `06_design_resolutions/durable-runtime.md`, `06_design_resolutions/production-topology.md`
**Teardowns read:** `03_teardowns/infra-durable-execution.md`, `03_teardowns/discovery-wildcard.md`

---

## The Attack

The resolution is architecturally sound for the dogfood phase. It is NOT sound as a production default at 10×. The single failure mode that bites hardest, and that the resolution does NOT handle, is:

**The ASYNC durability mode — the advertised default — has a structural double-fire window for non-idempotent tool calls, and the resolution's own mitigation ("use SYNC for destructive tools") only shifts the problem rather than closing it.**

Here is the failure chain, concretely:

### Failure Mode 1 — ASYNC default + crash = double tool fire on resume (NOT "acceptable")

The resolution states ASYNC mode as the default:

> "step fn runs → `asyncio.create_task(backend.put_step_output(...))` → step result returned IMMEDIATELY (the write completes concurrently with the next loop iteration)"

And then dismisses the risk:

> "The `ASYNC` mode risk: if the process crashes between the step completing and the background write committing, the step re-runs on resume. This is acceptable for LLM calls (idempotent-in-practice) and read-only tool calls."

This dismissal is wrong in two ways that compound at scale:

**a) LLM calls are NOT idempotent in practice with streaming.** A streaming LLM call that completes but whose result is not checkpointed before the crash will re-fire on resume. At $0.01–0.05/call (Opus-class), a 10-step agent crashing halfway through fires 5 LLM calls twice. At 1,000 concurrent durable runs this is a real cost vector. More importantly: the re-fired LLM call on a non-deterministic model will produce a DIFFERENT result than the one that was lost, so `verso_run_events` will contain two different ASSISTANT_DELTA sequences for the same logical step once resume completes — a corrupted event log, not a retried one.

**b) "Use SYNC for destructive tools" is an opt-in escape hatch that will be missed.** The resolution relies on the tool author to know to write `ctx.step(..., durability=DurabilityMode.SYNC)` for every destructive tool. At scale this is a protocol the API consumer must remember under time pressure. The failure mode is: a developer writes a `send_email` tool, uses the default ASYNC mode, the process crashes after the email is sent but before the step is checkpointed, and the email fires again on resume. The user gets two emails. This is not a theoretical risk — it is exactly the class of bug that Temporal's activity model was designed to close, and that the resolution explicitly rejects. The resolution's own "Open Unknown #1" acknowledges this:

> "For tools touching a different DB or an external API (Stripe, GitHub), exactly-once is impossible; the correct contract is at-most-once with idempotency keys."

That acknowledgment is honest. But then the resolution sets ASYNC as the DEFAULT and makes SYNC an opt-in, which means the safe contract (no double-fire) requires explicit per-step opt-in from every tool author. This is backwards: unsafe should be opt-in, safe should be default.

### Failure Mode 2 — Postgres as a single write bottleneck under concurrent step-write + event-append + claim-poll

The resolution routes ALL of the following through one Postgres instance:

- `put_step_output` — per-step INSERT into `verso_step_outputs` (every loop iteration)
- `append_event` — per-step INSERT into `verso_run_events` (every loop iteration, often twice: once for `tool_use`, once for `tool_result`)
- `claim_pending_runs` — `SELECT ... FOR UPDATE SKIP LOCKED` polling every `RECOVERY_POLLER_INTERVAL_S = 0.5s` from every worker
- `extend_lease` — heartbeat UPDATE every `LEASE_HEARTBEAT_INTERVAL_S = 10s` per active run
- `recover_expired_runs` — UPDATE query every 0.5s
- `timeout_scan` for HITL promises — additional background poller

At `WORKER_CONCURRENCY = 2` (the Centaur default the resolution copies) this is manageable. But at 10× — say 50 durable runs active — the write rate looks like:

- 50 runs × ~2 LLM calls/min × 4 writes per step (2 step_outputs + 2 run_events) = 400 writes/min sustained
- Plus 2 pollers × 120 polls/min = 240 range-scans/min contending on the same tables

The `claim_pending_runs` query is `SELECT ... FOR UPDATE SKIP LOCKED WHERE status IN ('queued', 'sleeping')`. DBOS runs this same pattern and acknowledges a `polling_interval_sec = 1.0` default precisely because sub-second polling grinds Postgres at scale. The resolution copies Centaur's `RECOVERY_POLLER_INTERVAL_S = 0.5` without noting this is for a private Paradigm deployment (likely modest concurrency). At 100+ concurrent durable runs this poller becomes a hot sequential scan even with the partial index — Postgres's planner will start full-scanning `verso_runs` when selectivity degrades.

The specific failure: under high concurrency, `claim_pending_runs` + `put_step_output` start contending on the same row-lock (the `SELECT ... FOR UPDATE` in `_persist_checkpoint` against `verso_runs` per the D9 fencing detail). Two workers will retry the lease claim simultaneously and serialize on the lock, adding latency to EVERY step checkpoint write. This is not an edge case; it is the designed behavior of `SELECT ... FOR UPDATE` under concurrent workers.

The resolution does not mention connection pool sizing, lock-wait timeouts, or deadlock detection. asyncpg defaults to a pool of 10 connections. 50 concurrent runs × 4 writes/step means bursts of 200 concurrent write requests against a 10-connection pool — queue buildup, latency spikes, and eventually timeout errors that surface as spurious step failures, triggering retries, making the problem worse.

### Failure Mode 3 — Seq allocation for `verso_run_events` is a hot-spot under concurrent appends

The resolution adopts the AX sqlite.go:82-90 seq allocation pattern: `seq = MAX(seq) + 1` per run, with `PRIMARY KEY (run_id, seq)`. This is an `ON CONFLICT` guard, not an atomic allocation. The actual allocation of seq is a read-modify-write:

```sql
-- from production-topology.md schema
seq INT NOT NULL,   -- monotonic per run; allocated as MAX(seq)+1 (AX sqlite.go:82-90)
```

Under concurrent event appends to the same run (which WILL happen — a multi-tool-call step fires multiple `append_event` calls, some of which are issued concurrently in the event stream), this pattern has a race: two appenders both read `MAX(seq) = 5`, both try to insert seq=6, one fails the PK constraint. The resolution says nothing about how this conflict is handled. `ON CONFLICT DO NOTHING` silently drops the event — catastrophic. `ON CONFLICT DO UPDATE` breaks idempotency. The correct answer is `SELECT nextval(...)` on a per-run sequence or a row-level advisory lock on the run during append. Neither is specified.

AX's `sqlite.go:82-90` handles this correctly because SQLite is single-writer (WAL mode, serialized writes) — there is no concurrent-append problem. The resolution copies the pattern without noting the Postgres concurrency difference.

### Failure Mode 4 — Step hash collision is silently catastrophic

The resolution uses `sha1(name)` (40-hex characters, 160 bits) as the `step_key`. SHA-1 collision probability is negligible for normal step names. But the resolution also allows loop disambiguation via `sha1(f"{name}:{n}")`. Consider: a run that has step names `"tool_call"` (n=1..500, producing sha1("tool_call:1") through sha1("tool_call:499")). SHA-1 collision across 500 names is still astronomically unlikely.

The actual problem is not collision — it is **silent truncation / encoding mismatch at the database layer**. If `asyncpg` serializes `step_key` as a TEXT column and the application is multi-process (workers on different machines, different Python builds), there is no guarantee that `sha1(name.encode())` in Python 3.11 on ARM and Python 3.12 on x86 produce the same bytes for non-ASCII step names. Tool names containing unicode (emojis, CJK) in the step name will produce different sha1s under different encodings. The resolution hardcodes `.encode()` without specifying the codec. If a step name is produced by f-string interpolation of user-supplied content (e.g. `f"tool_{tool_name}_{n}"` where `tool_name` comes from an LLM's tool_use block), a non-ASCII tool name produces an unreproducible step_key between workers. The step is treated as a cache miss on every resume, re-firing indefinitely. `max_attempts=3` doesn't save you — the step succeeds and writes to the DB, but the next resume still misses the cache.

### Failure Mode 5 — Recovery thread and worker loop both running = phantom double-claim window

The resolution specifies:

- A startup `recovery_thread` that claims PENDING rows assigned to this executor
- A `_worker_loop` that polls `claim_pending_runs` continuously
- A `WORKER_LEASE_SECONDS = 30` with `WORKER_HEARTBEAT_SECONDS = 10`

On startup, there is a window where both the recovery thread (re-claiming this executor's PENDING rows) AND the worker loop (claiming any claimable row via SKIP LOCKED) are running concurrently. If the recovery thread is slow (it re-enters the loop, which may block on an LLM call), and the worker loop is fast, the same run can be claimed twice: once by recovery (which sets `worker_id = this_worker_id`) and once by the worker loop poll (SKIP LOCKED skips rows with an active lock, but the lock is released the moment recovery completes its `SELECT ... FOR UPDATE`).

The D9 fencing detail says: "the write does `SELECT status, worker_id FROM verso_runs WHERE run_id=? FOR UPDATE` — if `worker_id != self._worker_id` the run was stolen; raise `StaleWorkerError`." This guard fires only at checkpoint write time, not at loop entry. So the double-claim is only detected at the end of the first successful step, not before the agent has been running for (potentially) multiple LLM calls. The resolution does not specify whether the `_worker_loop` skips runs that the recovery thread is actively processing, nor whether there is an in-process `asyncio.Lock` per `run_id` to prevent the double-entry. Without it, at startup under load, two coroutines drive the same agent for up to one full step's duration before fencing fires.

### Failure Mode 6 — 1M-token context + JSONB storage = write amplification on every step

For a long-running durable agent where the LLM response grows to 1M tokens (Claude's window is 1M input + 128K output), the `output_json JSONB` column in `verso_step_outputs` stores the full LLM response per step. At `step_kind = 'llm_call'`, each row is the full text of the LLM response. For a 50-step agent with 10K-token responses per step, that is 500K tokens × ~4 bytes/token = ~2MB of JSONB in `verso_step_outputs`. This is stored redundantly with the `verso_run_events` table, which also stores `ASSISTANT_DELTA` events with the same payload. That is 4MB of Postgres JSONB per 50-step agent run, stored twice — once in the step journal and once in the event log.

At 1,000 active durable runs, this is 4GB of JSONB growth per 50 steps across the fleet. Postgres JSONB writes are WAL-amplified: each row INSERT generates a WAL record approximately 2–3× the row size. So 4GB of logical data generates 8–12GB of WAL traffic per 50-step fleet cycle. The resolution explicitly defers journal compaction to "after the first dogfood run that produces >500 steps" (Open Unknown #3), but 500 steps at even 5K tokens/step is 2.5M tokens × 4 bytes = 10MB per run, uncompressed, in JSONB. That is the `verso_step_outputs` table alone; `verso_run_events` doubles it.

The resolution does not specify a JSONB size cap, a compression strategy, or even `output_json` type constraints. DBOS's `operation_outputs.output TEXT` stores serialized values too, but as plain text with an implicit size boundary set by the application. Verso's schema is unbounded by design.

---

## Does It Break the Decision?

**No — it does not break the "build in-house rather than delegate to Temporal" call.** The failure modes above are implementation defects that an in-house engine can fix. They are not architectural arguments for Temporal. The "one flag, same loop" seam decision is correct. The DBOS/Centaur/AX evidence is real and the convergence is genuine.

**But it DOES break the sub-decisions:**

1. **ASYNC should NOT be the default.** The resolution should flip: SYNC as default, ASYNC as an explicit performance opt-in. The "acceptable" characterization of ASYNC's crash window is wrong. LLM re-fires produce different outputs, corrupting the event log. Non-idempotent tool re-fires are a safety defect. SYNC mode adds one round-trip (the checkpoint write) per step — at Postgres LAN latency (~1ms) this is invisible against any LLM call (>100ms). The "latency win" from ASYNC is not visible at the wall-clock level for agent workloads. The risk is real and the win is negligible.

2. **The `append_event` seq allocation must be specified correctly.** `MAX(seq)+1` with `ON CONFLICT DO NOTHING` will silently drop events under concurrent appends. The production-topology.md schema needs a fix: either a `SERIAL`/`sequence` per run (expensive), a `SELECT ... FOR UPDATE` on the run row during append, or accept sequential-per-run appends enforced by a Python `asyncio.Lock`. The last is simplest and correct for a single-process worker.

3. **The `WORKER_CONCURRENCY = 2` constant from Centaur must not be inherited without a Postgres connection pool sizing note.** At least document: pool size must be `>= (WORKER_CONCURRENCY × max_writes_per_step) + background_pollers`. For `WORKER_CONCURRENCY=2`, `max_writes_per_step=4`, and 2 pollers: minimum pool = 10. This is fine. But if someone increases `WORKER_CONCURRENCY` to 20, the pool must scale proportionally or every step write queues.

4. **Step name encoding must be documented as UTF-8 explicitly.** `sha1(name.encode("utf-8"))` not `sha1(name.encode())`. Non-ASCII step names from LLM-generated tool names must be handled deterministically.

---

## Evidence Checked

- `durable-runtime.md:751–767` — ASYNC mode specification and the "acceptable" risk dismissal. The dismissal is the load-bearing claim this attack challenges.
- `durable-runtime.md:38–46` — the resolution's "convergent invariant 1: write-before-advance." Contradicted by ASYNC mode, which explicitly violates write-before-advance for the crash window between step completion and background write commit.
- `production-topology.md:308–388` — the schema, specifically the `MAX(seq)+1` seq allocation.
- `production-topology.md:392–406` — the constants table: `RECOVERY_POLLER_INTERVAL_S = 0.5`, `WORKER_LEASE_S = 30`, `WORKER_CONCURRENCY not specified` in production-topology.md.
- `durable-runtime.md:492–509` — D10 worker model, the resident vs stateless split and the double-claim window.
- `infra-durable-execution.md:162–278` — DBOS schema and step-write analysis. DBOS uses `function_id` ordinal (not SHA-1) and stores output as TEXT, not JSONB — the JSONB write-amplification issue is a Verso addition, not inherited from DBOS.
- `infra-durable-execution.md:512–530` — Inngest SHA-1 scheme, confirming `.encode("utf-8")` is the correct form.
- `infra-durable-execution.md:1127–1129` — convergent invariant 1 ("every memoization system persists the step result before allowing the loop to advance"). ASYNC mode is explicitly an exception to this invariant and is called out in the resolution, but the resolution undersells the severity.
- The `durable-runtime.md` Open Unknown #1 and #3 both acknowledge the double-fire and the journal compaction problems. They are correctly identified as unknowns. The issue is that ASYNC is set as DEFAULT before those unknowns are resolved, not after.

**Claim verification:** The Centaur `workflow_engine.py:338-435` reference for the `_persist_checkpoint` fencing detail is cited in the resolution. The specific `workflow_engine.py:272-326` fencing detail (check `worker_id` before writing) is cited correctly. The attack's claim about the startup double-claim window is a gap the Centaur code addresses at checkpoint time (not at loop entry), which the resolution copies correctly but incompletely — the guard fires at the right place but allows duplicate loop execution before the first checkpoint.

---

## Recommendation

**Verdict: REVISE — on two specific sub-decisions; the top-level build-in-house call survives.**

1. **Flip the durability default to SYNC.** Make ASYNC an explicit opt-in (`ctx.step(..., durability=DurabilityMode.ASYNC)`). The latency argument for ASYNC is not real at agent timescales (1ms checkpoint vs 100ms+ LLM call). The safety argument for SYNC is real (no double-fire, no event-log corruption, true write-before-advance). "ASYNC as default" is a premature optimization that violates the resolution's own convergent invariant 1 and the project's "keep it simple" thesis.

2. **Fix the seq allocation.** Replace `MAX(seq)+1` with an in-process `asyncio.Lock` per `run_id` for all `append_event` calls within a single worker, and document that multi-worker concurrent event appends to the same run are prevented by the single-writer-per-run guarantee (D10). This is the correct fix for the concurrency model Verso has chosen (resident single-writer worker), not a schema change.

3. **Document a JSONB size cap or compression requirement.** Add a note to D4 that `output_json` in `verso_step_outputs` should store a compact representation (e.g. truncated/summarized for large LLM responses), not the full streaming content — full streaming content belongs in `verso_run_events` where it is already stored. Storing it twice in both tables at full length is the write-amplification source.

4. **Add an in-process `run_id` guard to the worker loop entry point** (before re-entering the agent loop, not only at checkpoint write) to close the startup double-claim window. A single `asyncio.Lock` keyed by `run_id` in the worker loop's claim handler is sufficient.

These are all small, contained fixes. None of them require changing the fundamental architecture.
