# Adversarial Critique: seam-mechanism / THESIS & SCOPE

**Decision under review:** The tactical↔durable seam = `durable=True` appends exactly one `PersisterHook` (a `PostRunStepHook`); the ReAct loop body is byte-identical both ways (Burr `application.py:2565`). The "one-line diff, zero loop changes" seam test holds.
**Lens:** THESIS & SCOPE — does this betray "keep it simple; dogfood-first; no non-bottleneck dependency; tactical layer simple"?
**Date:** 2026-06-05
**Files read:** `06_design_resolutions/durable-runtime.md`, `06_design_resolutions/api-and-peers.md`, `03_teardowns/fw-py-peers.md`, `docs/PRD_v1.md`, `research/THESIS_VERIFICATION.md`. Burr source verified via `git clone --depth=1 https://github.com/apache/burr` into `/tmp/verso-re-pyfw`.

---

## The Attack

**The seam mechanism itself is clean. The attack is on what was bundled with it.**

The decision-under-review is stated narrowly: one `PersisterHook` appended, loop byte-identical. That is 4 lines of Burr code (`persistence.py:214-234`) confirmed from source. The seam itself cannot be attacked — it is the simplest possible implementation and is exactly right.

The attack is that `durable-runtime.md` — the resolution document cited for this decision — does not just specify the seam. It specifies an entire durable engine that the seam enables, and bundles both under a single decision label. The engine contains:

- 4 SQL tables: `verso_runs`, `verso_step_outputs`, `verso_run_events`, `verso_hitl_promises`
- 8-state status machine (`queued / running / sleeping / waiting / completed / failed / cancelled / max_recovery_exceeded`)
- 11-method `CheckpointBackend` ABC (`create_run`, `update_run`, `get_run`, `get_step_output`, `put_step_output`, `append_event`, `get_events`, `claim_pending_runs`, `extend_lease`, `recover_expired_runs`, `delete_run`)
- Inngest SHA-1 step-identity scheme with loop counters
- Lease/heartbeat/worker loop (`WORKER_LEASE_SECONDS=30`, `WORKER_HEARTBEAT_SECONDS=10`, `WORKER_CONCURRENCY=2`, `WORKER_RECONCILE_INTERVAL=0.5`)
- Resonate-style named durable promise system (5 states, two idempotency keys, timeout scanner, `verso_hitl_promises` table, external resolve/reject endpoints)
- AX two-log separation (`verso_run_events` + `verso_step_outputs`)
- DBOS startup recovery thread pattern
- SQLite vs Postgres behavioral divergence (note 6 in the open unknowns)
- `DurableExecutor` class with `run`, `submit`, `attach`, `_worker_loop` methods
- `ctx.step()` async context manager with fencing (`SELECT ... FOR UPDATE` zombie-worker guard)
- 7 open implementation questions flagged as unresolved

The resolution's own Component Spec section is 289 lines of schema + interface code alone. The 14 code blocks total 482 lines. The 7 open unknowns include non-trivial correctness problems: exactly-once for destructive tool calls with external DBs, transaction-piggyback for same-Postgres tools, journal compaction for runs >500 steps, SQLite behavioral divergence for concurrent writers.

**The thesis says:** "the simplest thing that works for a dogfood-first v1 by a solo builder." **The durable engine as spec'd is not that thing.**

### The specific cheaper alternative

Burr (`apache/burr`) already ships everything needed to satisfy the seam test with zero bespoke engine:

1. **Burr's `PersisterHook` + `AsyncPostgreSQLPersister`** — confirmed from source (`b_asyncpg.py`, 425 lines including a full Postgres backend). Burr saves the full agent state after every step (append-only INSERT). A crashed run resumes from the last `completed` row; a failed step is re-run. `pip install 'apache-burr[asyncpg]'`.
2. **Burr's `halt_before`/`halt_after`** — confirmed from source (`application.py:1169-1221`). The generator-return HITL mechanism is already production-tested. It does not support mid-step suspension, but for v1 dogfood the coarser pause-at-action-boundary is almost certainly sufficient.
3. **The `InMemoryPersister`** — confirmed from source (`persistence.py:612`). This is the tactical runtime's backend: same interface, zero I/O.

What this gives: `durable=True` compiles to `ApplicationBuilder.with_state_persister(AsyncPostgreSQLPersister(...)).abuild()`, with HITL via `halt_before`. The loop is byte-identical. The seam test passes. No bespoke tables, no 11-method ABC, no lease machinery, no promise system, no step-memoization engine to write and debug.

**What is lost by using Burr vs. the bespoke engine:**

| Capability | Burr (compose) | Bespoke engine (build) |
|---|---|---|
| Crash-resume (skip completed steps) | Re-runs the crashed action from its start — does NOT skip the LLM call if it succeeded before the crash | Memoizes individual step outputs; crashed mid-step means only that step re-runs, not the whole action |
| HITL granularity | Pause at action (node) boundaries | Pause mid-step (`await ctx.hitl.request()` anywhere in the loop body) |
| Submit/background job queue | Not built-in; caller must manage re-entry | Built-in `submit()` + worker loop + `claim_pending_runs` |
| Idempotent step identity (SHA-1 name) | Ordinal sequence_id (fragile under action reordering) | Name-content-addressed (refactor-tolerant) |
| Event stream for `attach()` | Not built-in; no `verso_run_events` equivalent | Built-in seq-cursor replay |

These gaps are real. But the thesis question is: **does a solo dogfood-first builder need them before Phase 2, when Phase 0 and Phase 1 haven't shipped yet?**

The PRD's own phasing says the durable runtime is **Phase 2**. Phase 0 is the tactical core: loop, context, tools, streaming. Phase 1 adds memory and evals. The bespoke engine is not needed until Phase 2, and by Phase 2 the builder will have dogfooded Phase 0 and Phase 1 enough to know whether the mid-step granularity and background queue actually matter for their real workload.

### The over-engineering indictment

The resolution's D2 alone (durability model) resolves four separate design choices (step identity scheme, event log separation, resume algorithm, merge of DBOS + Inngest + AX + Centaur) before a single line of Phase 0 code has been written. This is exactly the "find the right abstraction on paper, not by using it" anti-pattern the PRD explicitly calls out (§2: "the right abstraction cursor cannot be found on paper — only by using the thing").

The open unknowns in the resolution prove the engine has not been validated against any real Verso workload:
- Unknown 1 ("exactly-once for destructive tool calls") — cannot be resolved without a real tool that touches an external DB
- Unknown 3 ("continue-as-new") — cannot be decided without "first dogfood run that produces >500 steps" (their words)
- Unknown 7 ("internal_only event semantics") — "needs one full end-to-end trace to calibrate"

The resolution deferred these correctly — but designing the 11-method ABC, 4-table schema, and lease machinery WITHOUT being able to resolve these questions means the schema will need to change after dogfooding. The result is a multi-quarter build that is underspecified at the points that matter most, and over-specified at the points that can be deferred.

### The "non-bottleneck dependency" angle

The thesis says: "don't add a non-bottleneck dependency." For a solo builder in Phase 0, Postgres-as-checkpoint-store is not a bottleneck — it is a first-run friction cost. Burr's `SQLitePersister` (Phase 0 dev path) + Burr's `AsyncPostgreSQLPersister` (Phase 2 production path) is a zero-friction upgrade. The bespoke engine adds Postgres as a mandatory dependency from Phase 2 onward without a demonstrated bottleneck. Phase 2 dogfooding would reveal whether Burr's whole-state-per-step persistence is actually a bottleneck (it almost certainly isn't for a ReAct loop where each step is 1–5 seconds of LLM latency).

---

## Does It Break the Decision Under Review?

**Partially — and the split matters.**

The seam mechanism itself (one `PersisterHook`, loop byte-identical) **survives**. The Burr evidence confirms it. The loop-awareness test passes. This is the right architecture.

What the attack breaks is the **scope of what is bundled with the seam decision**: the 11-method ABC, 4-table schema, worker loop, promise system, and 7 open unknowns belong to a Phase 2 implementation plan, not to a Phase 0/1 architecture decision. Committing them now — before any Phase 0 code has been dogfooded — violates the thesis ("find the right abstraction by using it") and produces over-specification at the precise points that require empirical validation.

The over-specification is not harmless. It creates a migration tax if the schema changes (likely, given the 7 unresolved unknowns), anchors expectations that will be wrong, and builds a multi-quarter mental model that competes for attention during Phase 0/1 (the phases that actually matter for finding the right abstraction).

The cheaper alternative (Burr as the Phase 2 backend, wrapped behind the seam interface) keeps the seam architecture clean while deferring the engine until there is dogfood evidence about which gaps actually matter.

---

## Evidence Checked

1. **Burr `application.py:2565`** — `_set_sync_state_persister()` confirmed. Line 2588: `self.lifecycle_adapters.append(persistence.PersisterHook(self.state_persister))`. Exactly as cited. [VERIFIED from source]
2. **Burr `persistence.py:214`** — `PersisterHook` is a `PostRunStepHook`, 4-line body. Confirmed. [VERIFIED]
3. **Burr `application.py:949-993`** — `_step()` fires `post_run_step` in a `finally:` with zero persistence awareness. Confirmed. [VERIFIED]
4. **Burr HITL: `application.py:1169-1221`** — `halt_before`/`halt_after` generator-return mechanism. Confirmed in source. [VERIFIED]
5. **Burr no step-memoization** — Burr saves the full state dict after each action (`persistence.py:577` bare INSERT). On crash-resume, it re-runs the crashed action from its start. Confirmed; no per-step-output memoization exists. The step-memoization engine is genuinely new work, not a Burr adaptation.
6. **Burr no worker/queue** — No `claim_pending_runs`, no `FOR UPDATE SKIP LOCKED`, no lease machinery in the Burr codebase. The async submit + background queue is genuinely new work.
7. **Burr `b_asyncpg.py`** — Full async Postgres persister in 425 lines. Functional, production-tested, `pip install 'apache-burr[asyncpg]'`. Available today.
8. **durable-runtime.md Component Spec** — 289 lines in the spec section; 14 code blocks totaling 482 lines; 7 open implementation unknowns; 11 abstract methods in `CheckpointBackend`; 4 tables; 8 run statuses; 6 step kinds; lease constants, promise table, recovery thread. [COUNTED from file]
9. **PRD §8 phasing** — durable runtime is explicitly Phase 2. Phase 0 is tactical core. Confirmed: the engine is not needed to exit Phase 0. [READ from PRD_v1.md]

---

## Recommendation

**Split the decision into two separate decisions:**

**Decision A (SEAM ARCHITECTURE — LOCK NOW):** The seam is one `PersisterHook` (a `PostRunStepHook`) appended to the `LifecycleAdapterSet`. The loop never branches on durability. This is proven, minimal, and correct. `CheckpointBackend` as an interface principle (tactical = no-op in-memory, durable = Postgres-backed) is sound. Lock it.

**Decision B (DURABLE ENGINE IMPLEMENTATION — DEFER TO PHASE 2 ENTRY):** The 11-method ABC, 4-table schema, worker loop, promise system, and step-memoization engine should NOT be locked until Phase 0 and Phase 1 have been dogfooded. The recommended Phase 2 starting point:

- **Use Burr's `AsyncPostgreSQLPersister` as the first backend** behind the `CheckpointBackend` interface. This covers crash-resume (re-run-from-last-completed-action, not step-memoized), HITL at action boundaries, and SQLite/Postgres swap — with zero bespoke engine. `pip install 'apache-burr[asyncpg]'` is the entire dependency cost.
- **Build the step-memoization engine only if Phase 2 dogfooding reveals that re-running a crashed LLM call is a real problem** (i.e., LLM calls crash after the model has responded but before Verso can write the output — a narrow race window). This is likely a rare enough failure mode that the Burr model (re-run from action start, idempotent LLM call) is acceptable for v1.
- **Build the background submit/queue only when there is a real background job** to run. If the Phase 2 dogfood agent only uses `agent.run(durable=True)` (synchronous durable path), the queue is not needed.
- **Build the promise-based HITL only when `ctx.hitl.request()` is needed mid-step.** Burr's action-boundary HITL covers most approval gates at lower complexity.

The specific capabilities lost by deferring (mid-step memoization, background queue, mid-step HITL) are **real but not bottlenecks before a single Phase 2 agent has been written.** The thesis demands this exact deferral.

**Verdict: REVISE.** The seam mechanism (Decision A) SURVIVES. The bundled engine spec (Decision B) should be deferred to Phase 2 entry, starting with Burr as the backend. Do not build a multi-quarter engine before the seam has been exercised in a real agent.
