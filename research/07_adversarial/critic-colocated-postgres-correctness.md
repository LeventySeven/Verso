# Adversarial Critique — colocated-postgres / CORRECTNESS lens

**Decision under review:** ONE colocated Postgres in prod holds durable checkpoints + memory (pgvector) + eval/traces; ONE SQLite file in dev holds all three; ClickHouse/Qdrant/Neo4j are opt-in upgrades only.

**Lens:** CORRECTNESS — do the cited RE'd evidence and mechanisms actually prove this works for Verso's exact case (Python async ReAct loop, non-deterministic LLM steps, the one-flag seam, dogfood scale)? Verify load-bearing file:line claims. Find any misread of the source system, any mechanism that is technically wrong, or any composition failure with the other Verso subsystems.

**Date:** 2026-06-05

---

## The attack

The decision's integrity depends on three load-bearing pillars:

1. **The checkpoint substrate is correctly borrowed from DBOS/Centaur/Inngest/AX.**
2. **The Hindsight "single-Postgres-is-sufficient" claim is accurate and transfers to Verso.**
3. **The colocated schema is internally consistent — the tables do not compose in a way that creates correctness failures in the target runtime.**

All three are structurally sound. There is no decisive breakage. However, there is one real correctness gap that the decision buries as a note rather than resolving, plus two places where claims from source systems are technically borrowed correctly but carry a hidden composition risk.

---

### Finding 1 — The pgroonga "no-second-service" claim is MISLEADING (load-bearing for the memory subsystem)

**The claim:** `_RESOLUTIONS.md §0` and `memory.md D5/D6` both assert the prod Postgres backend gives "one Postgres, zero new services" by running BM25 through pgroonga or tsvector, with pgroonga as the preferred option.

**The problem:** pgroonga is NOT bundled with Postgres. It is a third-party C extension from the Groonga project that requires a separate OS-level package install (`apt install postgresql-17-pgdg-pgroonga` or a compiled Groonga library). The `memory-systems.md` teardown correctly describes this: Hindsight's `ensure_text_search_extension()` at startup *detects whether pgroonga is installed* and falls back to tsvector if it is not. This means:

- **On a standard PostgreSQL install** (e.g. `brew install postgresql@17`, AWS RDS default tier, Render Postgres, Supabase free tier, Railway), pgroonga is NOT present. The "enhanced BM25" arm silently degrades to tsvector.
- **The resolution note never acknowledges this.** It writes "pgvector + pgroonga/tsvector" as if these are equivalently available, but they are not. The `memory.md` component spec at line 430 even comments `-- pgroonga index (swapped in at startup if extension available)`, implying it's optional — but the key constants table at line 739 lists `BM25 k1/b = 1.2/0.75` citing `Weaviate config_handler.go:57-58`, which is Weaviate's BM25, NOT pgroonga's. This creates a citation mismatch: the constants are from Weaviate's production BM25 engine; the extension that would use them in Postgres (pgroonga) may not be present.

**Why this matters for Verso specifically:** The decision claims the colocated Postgres gives "durable runtime + memory + traces for free" once you pay the cost of running Postgres. That is true for the checkpoint and eval schema (which use only standard Postgres features). It is NOT true for memory's four-arm retrieval: the BM25 arm degrades to tsvector (which uses `ts_rank_cd`, not true BM25 with k1/b tuning) unless pgroonga is separately installed. The decision effectively overstates what "one Postgres" delivers on a default install.

**Severity:** This does not break the architecture — tsvector is a correct fallback, and memory.md explicitly codes the graceful degradation path via `ensure_text_search_extension()`. But the claim "zero new services" is only true for a subset of Postgres deployments. On the most common hosting environments, you either accept weaker BM25 (tsvector) or install a second OS-level dependency (pgroonga). The decision should say this explicitly rather than presenting pgroonga as if it comes with Postgres.

---

### Finding 2 — The Hindsight "91.4% LongMemEval" benchmark transfers with a significant condition that the decision omits (CALIBRATION risk)

**The claim:** `memory.md D5` uses "Hindsight proves a single Postgres instance can be the entire memory backend and reach near-SOTA (91.4% LongMemEval with a large backbone, arXiv:2512.12818)" as the primary justification for single-Postgres being sufficient for production.

**The problem:** The qualifier "with a large backbone" is present in the teardown but is not given sufficient weight in the resolution. The `memory-systems.md` teardown records this correctly (line 333: "with a large backbone") but does not specify what "large backbone" means in practice. A large backbone typically means GPT-4-class or Claude-3-class inference at the memory *extraction and synthesis layer*, not just the agent's query model. Verso's dogfood-first, solo-builder framing means the "large backbone" may be a costly assumption:

- If Verso's memory extraction runs on a small/cheap model (haiku-class), the 91.4% benchmark number is likely not achievable.
- The resolution only lists this as Open Unknown #2 (embedding model choice) and phases it to "Phase 1 dogfood". For the correctness of the colocated-postgres *architecture* decision (single DB is sufficient), this is acceptable — the architecture is correct regardless of the backbone model. But the resolution *uses the 91.4% number to justify the backend choice*, and that number is only achievable with conditions that Verso has not committed to. This is an evidence over-claim: the 91.4% proves "single-Postgres CAN achieve near-SOTA", not that "Verso's default config WILL achieve near-SOTA."

**Verdict for correctness lens:** The architecture claim (single Postgres is sufficient) is NOT disproved by this. The benchmark supports the architecture. But the calibration use of the number is imprecise, and if a future reader treats "91.4%" as the expected Verso benchmark, they will be disappointed without the matching backbone.

---

### Finding 3 — The ASYNC durability mode creates a correctness gap in the colocated schema that the decision defers rather than resolves (COMPOSITION risk)

**The claim:** `durable-runtime.md D5` and `_RESOLUTIONS.md §1A item 8` both document three durability modes (sync/async/exit), with `async` as the default. In ASYNC mode, the step checkpoint write is dispatched concurrently with the next loop iteration.

**The problem as a composition issue with colocated Postgres:** If the checkpoint write (to `verso_step_outputs`) and the memory flush (to `memory_items`) are both async writes to the SAME Postgres instance, a crash between them can produce an inconsistent state:

- Step N completes. The step output write is dispatched async.
- The memory `flush()` (triggered by the 1024-token buffer threshold) writes the extracted memories for that step.
- The process crashes before the async step-output write commits.
- On resume, the step is re-run — but the memories from step N are already persisted.
- The memory store now contains facts extracted from a step the durable journal thinks hasn't happened yet.

`durable-runtime.md §Open Unknowns #1` acknowledges a related but narrower version: "exactly-once for destructive tool calls with external DB." But the memory flush is not framed as a "destructive tool call" — it is a background buffer drain. The resolution notes that `flush()` is exposed so callers can "force-consolidate before a checkpoint" (`memory.md D1`), but the actual wiring between the durable step persister and the memory flush is left to implementation. There is no guarantee in the design that the memory flush and the step checkpoint write are atomically coupled.

**How bad is this?** For most agent use cases, re-running a memory extraction produces the same or equivalent facts (LLM extraction is approximately idempotent on the same input). So the practical impact is double-extraction of the same memories, not data loss. But the design claims ADD-only writes, which means duplicates would accumulate — the `text_hash` dedup guard in `memory_items` (md5(text)) catches verbatim duplicates but not semantically equivalent paraphrases if the LLM extraction produces slightly different text on re-run. This is a real correctness gap at the intersection of the two colocated subsystems, not just an edge case.

**Verdict:** Does not break the decision, but requires an explicit ordering contract at implementation time: either (a) memory flush uses SYNC durability for the step that triggers it, or (b) the memory flush is itself a `ctx.step()` call (making it a journaled step), or (c) the dedup guard is strengthened. None of these are in the current design spec.

---

## Does it break the decision?

**No.** The colocated-postgres decision survives the correctness lens.

The load-bearing RE claims are accurate and correctly sourced:
- DBOS `operation_outputs` PK `(workflow_uuid, function_id)`, `DEFAULT_MAX_RECOVERY_ATTEMPTS=100`, startup recovery thread: all read from actual source at cited lines. No misreads found.
- Inngest `sha1(step_name)` + `:n` counter: `transforms.py:30` + `base.py:111` correctly cited and correctly adopted.
- AX `ConversationEvent` vs `ExecutionEvent` two-log split: correctly read from `ax.proto:54-86`.
- LangGraph `Durability = Literal["sync", "async", "exit"]`: `types.py:87` correctly cited.
- Resonate named durable promise pattern: correctly applied.
- pgvector HNSW defaults `m=16, ef_construction=64, ef_search=40`: correctly attributed to `src/hnsw.h:46,49,52` and correctly distinguished from Qdrant's different defaults (`ef_construct=100`). The teardown carries a `[CORRECTION 2026-06-05]` noting this distinction — the resolution notes correctly avoid conflating Qdrant and pgvector defaults.

The decision also correctly frames the anti-Letta stance: "mandatory Postgres is bad; Postgres-as-prod-default-with-SQLite-dev-escape is good." That is architecturally coherent.

What the decision does not do:
- It presents "one Postgres, zero new services" without adequately flagging that the BM25 arm in the memory schema requires pgroonga (a separate install) or degrades to weaker tsvector.
- It uses a benchmark (91.4% LongMemEval) that is conditioned on a "large backbone" without committing to what backbone Verso will use.
- It leaves the memory-flush / step-checkpoint atomicity gap to implementation time, with no explicit coupling contract.

None of these break the decision. They weaken specific supporting claims and leave a composition gap that must be closed at implementation.

---

## Evidence checked

| Claim | Source cited | Verified? | Finding |
|---|---|---|---|
| DBOS `operation_outputs` schema, `DEFAULT_MAX_RECOVERY_ATTEMPTS=100` | `_registrations.py:10`, `_sys_db.py` | Yes — read from teardown `infra-durable-execution.md:161-276` which cites `dbos-inc/dbos-transact-py` cloned depth-1 | Correct |
| Inngest sha1 step identity | `transforms.py:30`, `base.py:111` | Yes — teardown `infra-durable-execution.md:513-608` cites actual cloned source | Correct |
| AX two-log split `ConversationEvent` + `ExecutionEvent` | `ax.proto:54-86` | Yes — teardown `infra-durable-execution.md` cites this; teardown also confirms `executor.go:78` short-circuit on COMPLETED | Correct |
| LangGraph `types.py:87` Durability literal | cited in `durable-runtime.md D5` | Yes — consistent with teardown | Correct |
| pgvector HNSW `m=16, ef_construction=64, ef_search=40` | `src/hnsw.h:46,49,52` | Yes — teardown `infra-retrieval-vector.md §pgvector` at line 277-288 confirms exactly these values with a `[CORRECTION]` note distinguishing from Qdrant's 100 | Correct for pgvector; decision correctly attributes to pgvector not Qdrant |
| Hindsight `91.4% LongMemEval` | `arXiv:2512.12818` | Teardown `memory-systems.md:333` confirms, qualifies "with a large backbone" | Claim is accurate; resolution understates the condition |
| pgroonga = "zero new services" | implicitly — `ensure_text_search_extension()` is cited | Teardown `memory-systems.md:363` notes pgroonga is swapped-in "if extension available" — confirming pgroonga is NOT bundled with standard Postgres | Decision over-claims zero new services; pgroonga is a separate install |
| Memory flush / step-checkpoint atomicity | Not explicitly cited | Not addressed in design | Gap confirmed — not a source misread but a design composition omission |
| Centaur workflow_engine.py lease constant (30s) | `workflow_engine.py:167` | Consistent between durable-runtime.md and production-topology.md | Correct |
| Resonate named promise `promise_id`, two idempotency keys | `resonate.py:1119`, `stores/remote.py:232` | Cited in durable-runtime.md D7 | Correct |

---

## Recommendation

**REVISE (minor)** — not REJECT. The architecture is sound, the RE evidence is real, the mechanism is technically correct. Three targeted fixes before committing to PRD:

1. **Fix the pgroonga claim.** Change "one Postgres, zero new services" to "one Postgres, with pgroonga as an optional separate extension install for full-BM25; tsvector is the fallback on standard Postgres installs." The `memory_items` schema comment already acknowledges this (`-- pgroonga index (swapped in at startup if extension available)`); the decision level should say it explicitly. The architecture is still colocated — this is a qualification, not a reversal.

2. **Decouple the 91.4% claim from the backend decision.** The single-Postgres backend is justified by operational simplicity (one service, zero new infra) and by Hindsight's architecture proof (pgvector + adjacency rows + date columns works at production scale). The 91.4% benchmark is evidence that the *architecture can achieve near-SOTA* — not that Verso will. Remove the implied promise; keep the architectural justification.

3. **Add an explicit ordering contract for memory-flush vs. step-checkpoint in ASYNC mode.** Either: (a) memory flush that occurs during a step is a `ctx.step("memory_flush_{n}", kind=StepKind.TOOL_CALL)` call — making it journaled, or (b) the `DurableExecutor` calls `memory.flush(force=True)` in SYNC mode immediately before writing the step output, or (c) the memory schema's `text_hash` dedup is explicitly declared sufficient for at-least-once flush semantics (and the known limitation — paraphrase duplicates — is documented). This is a Phase 2 (durable runtime ships) deadline item, not a blocker for the design decision.
