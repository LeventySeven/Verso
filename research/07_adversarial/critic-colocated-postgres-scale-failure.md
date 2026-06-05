# Adversarial Review: colocated-postgres — SCALE & FAILURE lens

**Decision under review:** ONE colocated Postgres instance (prod) holds durable checkpoints + pgvector memory (Hindsight model) + eval/trace store; ONE SQLite file (dev) holds all three. ClickHouse/Qdrant/Neo4j are opt-in upgrades only.

**Lens:** SCALE & FAILURE — enumerate concrete failure modes the resolution does NOT handle. Does the default survive production at 10×?

**Critic:** adversarial panel, SCALE & FAILURE assignment.

**Date:** 2026-06-05

---

## The Attack

The resolution's colocated Postgres story collapses three fundamentally incompatible I/O workload shapes onto a single connection pool and a single WAL. At solo-dogfood volume (one agent, a few runs a day) this is invisible. At 10× concurrent agents — the first real production deployment — three independent failure modes activate simultaneously, and the resolution acknowledges none of them.

### Failure Mode 1 — HNSW insert locks starve the checkpoint write path (the worst one)

The resolution adopts pgvector HNSW with `m=16, ef_construction=64` (KNOWN, `src/hnsw.h:46,49,52`). The teardown (`infra-retrieval-vector.md:290-292`) reveals the load-bearing implementation detail: **every pgvector HNSW insert wraps the graph mutation in generic WAL** (`GenericXLogStart → GenericXLogRegisterBuffer(GENERIC_XLOG_FULL_IMAGE) → GenericXLogFinish`) and each graph element is guarded by a **per-element LWLock** during the `m=16` neighbor-link rewrites. This is not a row-level lock; it is a shared-memory spinlock that holds across the WAL-flush boundary.

The Hindsight memory model flushes on every 1024-token trigger (`memobase env.py:86` — KNOWN). At 10 concurrent agents each flushing one batch per turn, that is 10 concurrent `INSERT INTO memory_items ... (embedding vector(1024))` operations, each of which must: (a) acquire LWLocks on up to `m=16 = 16` existing HNSW graph nodes to rewrite their neighbor lists, (b) write GENERIC_XLOG_FULL_IMAGE records into the WAL for every mutated index page, and (c) call `tsvector` update on the same row (another WAL record).

These 10 concurrent HNSW inserts compete directly with the checkpoint write path (`INSERT INTO verso_step_outputs ... ON CONFLICT DO NOTHING`) on the SAME connection pool and the SAME WAL writer. The `SELECT ... FOR UPDATE SKIP LOCKED` lease claim and the `UPDATE verso_runs SET status=...` transitions in the worker loop are lightweight — but they still hold row-level locks while the HNSW graph LWLocks are held. The result: the step-output write path (which is write-before-advance, a correctness invariant, not a latency preference) is gated behind HNSW index contention.

**The specific failure:** At 10× concurrent agents with the default `ASYNC` durability mode, the background task that commits `put_step_output` is competing with 10 in-flight HNSW inserts for WAL bandwidth and connection slots. If connection pool exhaustion occurs (asyncpg default pool is 10 connections), the background `put_step_output` task queues behind the HNSW inserts. The agent loop has already advanced (that is what ASYNC mode explicitly allows — "step result returned IMMEDIATELY"). A process crash during the queue backup produces a step that ran but was never checkpointed — the exact failure ASYNC mode documents as acceptable for LLM calls but one that now extends to tool calls via pool starvation, not the intended narrow case.

The resolution's ASYNC-mode caveat ("for destructive / non-idempotent tool calls, use SYNC mode per-step") addresses the semantic risk but not the connection pool starvation mechanism. The mitigation is "use SYNC," but if the pool is saturated, SYNC mode just blocks the agent loop at the `await backend.put_step_output(...)` call — turning a latency problem into a correctness-adjacent stall. Neither case is acknowledged.

**Threshold where this bites:** Not 10×. Given asyncpg's default pool of 10 connections and a Hindsight flush at every 1024 tokens (~1-2 turns), the contention window opens at approximately 5 concurrent agents with moderate memory use. The HNSW `m=16` constant means each insert touches 16 neighbor nodes; with `ef_construction=64` the candidate search traverses 64 nodes before settling on 16. That is 80 LWLock acquire/release cycles per insert, each flushing a WAL full-page image.

### Failure Mode 2 — The `seq` allocation is not atomic: concurrent event appenders produce silent gaps or PK violations

`verso_run_events.seq` is described as "monotonic per run; allocated as MAX(seq)+1 per run (AX sqlite.go:82-90)" (production-topology.md, durable-runtime.md §D4, confirmed in both). This is not atomic. The correct PostgreSQL implementation is either a `SEQUENCE` object or a `SELECT MAX(seq)+1 FROM verso_run_events WHERE run_id=$1 FOR UPDATE` with a row-level lock on a sentinel row. The spec says none of these.

Under the ASYNC durability default, multiple concurrent writers append to `verso_run_events` for the same `run_id`: the worker loop's `append_event` calls, the heartbeat extension path, and the HITL scanner. If two coroutines concurrently execute:
```sql
INSERT INTO verso_run_events (run_id, seq, ...) VALUES ($1, (SELECT MAX(seq)+1 FROM verso_run_events WHERE run_id=$1), ...)
```
both read the same MAX(seq) = N and both try to INSERT seq = N+1. The PRIMARY KEY `(run_id, seq)` catches this as a conflict. The resolution specifies `ON CONFLICT DO NOTHING` for step outputs, not for events. If the same pattern is applied to events, one silently disappears. If it is not applied, the second INSERT raises a unique-constraint violation, which in an asyncio background task (the ASYNC write path) produces an unhandled exception that the framework is not specified to catch at this layer.

The durable-runtime Open Unknown §7 ("which events are `internal_only`") acknowledges the event-semantics question but not the atomicity hazard. The production-topology spec notes SEQ_ALLOCATION = "MAX(seq)+1 per run, PK enforces uniqueness" treating the PK as the safety net — which it is only if writers retry, which is unspecified.

**At 10× concurrent agents:** each agent run produces ~5–10 events per turn (tool_use, tool_result, assistant_delta, status_change, etc.). At 10 agents × 5 events/turn × async flush latency, the probability of a seq collision on a busy run (e.g., a fan_out with 5 sub-agents writing events to the same parent run_id) approaches certainty within a few minutes. This is not a theoretical race; it is a standard application-level gap in the schema design that dedicated databases (Postgres sequences, SQLite autoincrement) solve for free, and that the resolution explicitly references a SQLite implementation (AX sqlite.go:82-90) without noting that SQLite's WAL serializes writes to the same row, eliminating the race — a property PostgreSQL does NOT provide for app-level MAX+1.

### Failure Mode 3 — Memory buffer loss on crash is silent and unlogged

The Hindsight-model memory write path is: (1) buffer turns in `memory_buffer` until 1024-token threshold, (2) run extraction LLM call, (3) INSERT into `memory_items`. The resolution specifies `flush()` must be called before a checkpoint ("force-consolidate before a checkpoint — the durable-seam requirement," memory.md D1). The integration point in the game loop is not specified at the code level.

Under `ASYNC` durability, there is a window:
- LLM tool call completes → step output written to `verso_step_outputs` (ASYNC: concurrently, not yet committed)
- Memory buffer accumulates turn content → 1024-token threshold reached → extraction LLM call dispatched → `INSERT INTO memory_items`
- Process crashes

On resume: `verso_step_outputs` may or may not contain the step output (ASYNC window). The `memory_buffer` rows persist in the DB (they were INSERTed synchronously). The `memory_items` extraction was in flight — if the INSERT committed before the crash, the items exist; if not, the buffer rows exist but the extracted items do not. The buffer is not cleared atomically with the items INSERT.

This means after crash-resume, `memory_buffer` rows that were already extracted (their LLM call completed, items INSERTed) sit unreprocessed alongside unextracted buffer rows. On the next `flush_buffer` call, the extraction LLM re-processes already-extracted rows, producing **duplicate memory items**. The ADD-only write policy means these duplicates are not merged — they accumulate. Over multiple crash-resume cycles, the memory store drifts toward duplication noise.

The resolution provides no buffer-cleared-atomically-with-items-insert contract. The DBOS transaction-piggyback pattern (write the checkpoint IN the user's transaction, `_core.py:1448`) is mentioned as an Open Unknown ("exactly-once for destructive tool calls") but is not extended to the memory flush path, which is the higher-frequency case.

**At 10× concurrent agents with periodic crashes (real production):** the duplicated-extraction problem compounds. The semantic gate (cosine ≥ 0.1 before fusion) and the `text_hash` dedup field (`md5(text)` — KNOWN, Mem0 `main.py:799`) would catch exact-duplicate text, but extraction LLM output is non-deterministic — the same buffer content produces slightly different extracted fact phrasings, giving `text_hash` mismatch, creating semantically identical items under different hashes. The memory store slowly fills with near-duplicate facts with no cleanup path (the ADD-only policy forbids deletion).

---

## Does It Break?

**Partially, at a concrete threshold.** The decision survives dogfood-scale (one user, <5 concurrent agents, no crashes) because all three failure modes are below the activation threshold:

- FM1 (HNSW/WAL contention): invisible below ~5 concurrent agents with active memory use
- FM2 (seq race): invisible when a single asyncio task drives a single run (SQLite's serialized WAL also hides it in dev)
- FM3 (buffer duplication): invisible without crash-resume cycles

At "first real production deployment" (10× concurrent agents, occasional crashes, long-running runs), all three modes are active. FM1 degrades latency and correctness (write-before-advance stalls or misses under ASYNC). FM2 produces silent event loss or duplicate-seq conflicts under fan_out scenarios. FM3 produces memory quality degradation that is silent and cumulative — it does not fail loudly, it quietly degrades the system's memory coherence.

The most damaging assessment: **FM1 and FM2 specifically attack the correctness guarantees that are Verso's core value proposition** — the tactical↔durable seam's promise that `durable=True` means steps are reliably checkpointed. If HNSW-induced pool starvation breaks write-before-advance, or seq collisions drop events, the seam's guarantee is voided by the storage colocated decision made in a different subsystem.

**The decision does NOT break at dogfood scale.** The resolution is correct that for the solo builder, one Postgres is right. But "survives dogfood" is the explicit scope claim, and the resolution makes no explicit claim about 10×. The lens asks whether the DEFAULT survives production at 10×. The honest answer is: FM1 and FM2 do not survive without two specific mitigations that are not in the resolution.

---

## Evidence Checked

| Claim | Source | Verified? |
|---|---|---|
| pgvector HNSW inserts use generic WAL + per-element LWLocks | `infra-retrieval-vector.md:290-292`, citing `src/hnsw.c:266-309`, `src/hnswinsert.c:194,258,339` | KNOWN from repo clone |
| HNSW m=16, ef_construction=64 chosen constants | `memory.md` D5 citing `src/hnsw.h:46,49,52` | KNOWN |
| Memory flush trigger = 1024 tokens | `memory.md` D1 citing `memobase env.py:86` | KNOWN |
| Seq allocation = MAX(seq)+1 (not atomic) | `durable-runtime.md` §D4 schema, `production-topology.md` constants table | DESIGNED (schema definition) |
| `ON CONFLICT DO NOTHING` specified for step_outputs only | `durable-runtime.md` §D8 `put_step_output` docstring | KNOWN (design spec) |
| DBOS transaction-piggyback = Open Unknown | `durable-runtime.md` Open Unknown §1 | KNOWN |
| ADD-only write policy (no deletion) | `memory.md` D1 | KNOWN |
| text_hash dedup = md5(text) | `memory.md` Component Spec citing `Mem0 main.py:799` | KNOWN |
| ASYNC mode: write dispatched concurrently, not committed before advance | `durable-runtime.md` §D5 | DESIGN |
| Connection pool starvation under concurrent HNSW inserts | Inference from FM1 | INFERRED (standard asyncpg default pool behavior) |

---

## Recommendation

**REVISE, not reject.** The colocated-Postgres story is correct at dogfood scale and the right default for the solo builder. Do not add ClickHouse or Qdrant as defaults. Three targeted fixes close the production failure modes without changing the architecture:

1. **Fix the seq allocation.** Replace `MAX(seq)+1` with `INSERT INTO verso_run_events ... RETURNING seq` combined with a Postgres `GENERATED ALWAYS AS IDENTITY` column, or a `SEQUENCE`. This eliminates FM2 with a one-line schema change and no interface change. Cost: zero. Risk of not fixing: silent event loss under fan_out at scale.

2. **Segregate connection pools.** Introduce a `CheckpointBackend` pool and a `MemoryBackend` pool as distinct `asyncpg.Pool` instances (each typically 3–5 connections). This prevents HNSW insert batches from exhausting the slots needed by write-before-advance. The `CheckpointBackend` pool gets priority; the `MemoryBackend` pool gets a separate `min_size=2, max_size=5` with a `command_timeout` so a backed-up HNSW flush cannot stall checkpoint writes indefinitely. This is a 10-line change to the backend constructors, not an architectural change. Cost: low. Risk of not fixing: write-before-advance correctness degrades under memory-heavy agents.

3. **Make the buffer→items extraction atomic.** Add a `processed_at TIMESTAMPTZ` column to `memory_buffer` (null = unprocessed, set = extraction completed). The extraction path: (a) mark buffer rows with `processing_started_at = now()` before the LLM call, (b) INSERT items, (c) set `processed_at = now()`. On flush, skip rows where `processed_at IS NOT NULL`. This gives exactly the same dedup guarantee `text_hash` gives for content, but for the extraction lifecycle. Crash-resume re-extracts only genuinely unprocessed buffer rows. Cost: low. Risk of not fixing: silent memory duplication on crash-resume at any scale.

Fix 1 is blocking (correctness at scale). Fix 2 is strongly recommended before first multi-agent deployment. Fix 3 is recommended before any deployment with `durable=True` and active memory use.

None of these require adding a new service. The colocated-Postgres design stands.
