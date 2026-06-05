# Adversarial Review — durable-engine (THESIS & SCOPE lens)

**Decision under review:** BUILD an in-house durable-execution engine (pure Python + Postgres, DBOS-style step-memoization, SHA-1 step ids, AX two-log, 3 durability modes, 4-table schema); reject Temporal/Trigger.dev/Restate for v1.

**Lens:** THESIS & SCOPE — does this betray "keep it simple; don't over-engineer; no non-bottleneck dependency; tactical layer simple; find the right abstraction by using it, not on paper"?

**Reviewer stance:** DEFAULT TO SKEPTICISM. A decision only survives if the attack genuinely cannot break it.

---

## The attack

**The decision builds a multi-quarter engine before the builder has run a single production agent.**

Count what the resolution has designed:

- 4-table Postgres schema (`verso_runs`, `verso_step_outputs`, `verso_run_events`, `verso_hitl_promises`) with 15–25 columns each, 7 partial indexes, 3 foreign-key cascades.
- An 11-method async ABC (`CheckpointBackend`) with full `InMemoryBackend` + `PostgresBackend` implementations.
- SHA-1 step-id scheme with a `StepIDCounter` per-name loop counter.
- 3 durability modes (`sync`/`async`/`exit`) with per-step override.
- Lease management (`worker_lease_expires_at`, `extend_lease`, `recover_expired_runs`) with specific constants (30s lease, 10s heartbeat, 0.5s reconcile interval).
- A full `DurableExecutor` with `run()`, `submit()`, `attach()`, and a `_worker_loop()`.
- A `HITLManager` with `request()`, `resolve()`, `reject()` implementing the full Resonate Durable Promise spec (5-state machine, two idempotency keys, timeout scanner).
- A fencing guard (`StaleWorkerError` on checkpoint write when `worker_id` mismatches).
- Serialization layer (JSON default, msgpack upgrade path, AES-GCM encryption wrapper, Pydantic v2 extension codes, RCE-guard construction allowlist).
- `RunStatus`, `StepKind`, `RunEventType`, `DurabilityMode` enums and `RunRow`, `StepOutput`, `RunEvent`, `RunHandle` dataclasses.
- 7 "Open Unknowns" the document explicitly leaves unresolved: exactly-once for external APIs, transaction-piggyback path, journal compaction / continue-as-new, HITL routing DX, sub-agent durable fan-out, SQLite behavioral divergence, `internal_only` semantics.

That is not a design. It is the scope of a 2–3 month engineering project. The thesis says: **"the right abstraction cursor cannot be found on paper — only by using the thing."** That is the single most important claim in `THESIS_VERIFICATION.md`, and it is stated explicitly in `PRD_v1.md §2` as the primary justification for the dogfood-first scope. This design builds the abstraction completely on paper before using it.

**The specific cheaper alternative: use DBOS directly for Phase 0/1.**

`dbos-transact-py` (`pip install dbos`) is:

1. Pure Python + Postgres. No Rust binary. No orchestration server. `pip install`, annotate `@DBOS.workflow()` / `@DBOS.step()`, point at a Postgres DSN, done. The "dogfood-first, personal infra" framing is fully satisfied.

2. The two-table schema the resolution designs (`verso_runs` + `verso_step_outputs`) is `dbos.workflow_status` + `dbos.operation_outputs` — described verbatim in `infra-durable-execution.md:180–202` with the exact SQL. Verso's design copied it, then named it differently. Using DBOS directly IS using this schema.

3. The `startup_recovery_thread`, `MAX_RECOVERY_ATTEMPTS=100`, `executor_id` filter, idempotency via `SetWorkflowID`, `fork_workflow(id, start_step)` restart-from-step, `@DBOS.scheduled(cron)` — every constant and mechanism Verso hard-codes from DBOS (`_registrations.py:10`, `_recovery.py:26-52`, `_context.py:169`, `_scheduler.py:25`) is already in DBOS and already works. The decision is copying proven production code into a new codebase for no thesis-stated reason.

4. The HITL surface: `DBOS.recv(topic, timeout=60)` + `DBOS.send(dest, msg, topic)` is a working durable pause/resume today. It is less elegant than the Resonate Durable Promise spec (no named HTTP-resolvable promise), but it is **sufficient to dogfood** and to discover whether named HTTP promises are actually needed before building them.

5. The `CheckpointBackend` ABC the resolution defines has 11 abstract methods. `DBOS.workflow()` + `DBOS.step()` decorators ARE that interface — implemented, tested, in production, with a `DBOSClient` out-of-process control API (`list_workflows`, `retrieve_workflow`, `fork_workflow`) that Verso's Phase 0 will not have at all.

**What is actually lost by deferring past Phase 0/1:**

| Feature | Deferred cost | When actually needed |
|---|---|---|
| Inngest SHA-1 step ids over DBOS ordinal | DBOS's call-order ordinal breaks if the developer *reorders* steps in the loop body between runs. For a dogfood loop the builder writes and controls, this is not a practical problem until the loop is stable enough to refactor. | Phase 2: when the loop shape is stable and you start refactoring |
| AX two-log split (`run_events` vs `step_outputs`) | DBOS has `workflow_events` (set_event/get_event) and `notifications` (recv/send). Not the AX two-log, but enough to dogfood streaming and resume. | Phase 2: when `agent.attach()` and cursor replay are needed by users |
| Resonate Durable Promise / named HTTP HITL | DBOS `recv(topic)` satisfies "pause agent, inject approval, resume" for a solo builder using their own infra. The HTTP-resolvable named promise is DX polish for *external resolvers* — only needed when other systems (Slack bots, humans, webhooks) need to resolve HITL gates without running Verso code. | Phase 2+: when HITL resolvers are external third parties |
| 3 durability modes (`sync`/`async`/`exit`) | DBOS writes synchronously (step result before return). That is `sync` mode. The `async` optimization (persist concurrently with next step) shaves one DB round-trip off the hot path — invisible to a solo builder doing dogfood work. `exit` mode is a p99 latency optimization. | Phase 2+: when latency matters for end-users |
| Encryption at rest + msgpack | Not needed for personal infra (solo builder, controlled Postgres). Matters at OSS-release scale. | Phase 3: before first external users |

**The violation is specifically against this thesis clause: "don't add a non-bottleneck dependency."**

The `CheckpointBackend` ABC + `PostgresBackend` + `InMemoryBackend` is a non-bottleneck dependency written before the bottleneck is known. The resolution itself lists 7 Open Unknowns — including `internal_only` event semantics, journal compaction strategy, and HITL routing DX — each of which will change the schema and the interface once the system is actually used. Writing the full engine before running even one production agent means these unknowns will be resolved by re-reading source code a second time, not by evidence from use.

**The thesis states it directly:** `THESIS_VERIFICATION.md §7` cites "the right abstraction cursor cannot be found on paper — only by using the thing" as the hardest-learned lesson in the harvest. The durable-engine decision is the exact anti-pattern it warns against: a 4-table schema, 11-method ABC, and complete implementation designed entirely from reading other projects' code, never from running one's own.

**The correct alternative is not Temporal or Trigger.dev.** The resolution correctly rejects those (operational overhead, wrong model for the use case). The correct alternative is:

Phase 0/1: `pip install dbos`. Use `@DBOS.workflow()` + `@DBOS.step()` + Postgres DSN. Build 3–5 real agents using it. Discover what the real friction is (call-order id brittleness? HITL DX? serialization limits?). Define `CheckpointBackend` from the pain, not from the synthesis.

Phase 2: if DBOS's ordinal ids are causing actual reorder bugs, replace the step-id scheme with SHA-1 names — a localized change to one function. If the HITL DX is inadequate for real workflows, build the named-promise layer. If the two-log split is needed for streaming cursor replay, add `verso_run_events`. Each of these is a 1–2 day change, not a 2-month pre-build.

**The attack lands specifically on the scope mismatch:** the decision is right that pure Python + Postgres + memoization is the correct architecture, and right that Temporal/Trigger.dev/Restate are too heavy. It is wrong to build the full engine before using it. DBOS satisfies the v1 requirement with zero additional build cost, and the `CheckpointBackend` interface can be defined once the friction points are known.

---

## Does it break the decision?

**PARTIALLY. It breaks the Phase 0/1 execution plan, not the architecture target.**

The architecture is correct: Family B memoization, DBOS-shaped two-table schema, Inngest SHA-1 step ids, Resonate Durable Promise for HITL, LangGraph-shaped `CheckpointBackend` interface, 3 durability modes. The teardown evidence for all of these is sound — the source citations are real (verified: `infra-durable-execution.md` cites real file:line from cloned repos; `discovery-wildcard.md` cites real AX source). None of the load-bearing claims are misread.

What the decision fails is the **scope gate**: it designs the complete final form of the engine as the Phase 0 deliverable, for a builder who has not yet built one agent on it. The thesis says the abstraction cursor is found by use, not paper. The decision builds the full abstraction on paper.

The break is real: 7 admitted Open Unknowns in a "resolved" design are not a sign of completeness, they are a sign that the design was done before the evidence was available.

---

## Evidence checked

1. **DBOS pip-installability confirmed:** `dbos-transact-py` is a `pip install dbos` package. Source `_core.py`, `_recovery.py`, `_schemas/system_database.py` all cloned and read in `infra-durable-execution.md`. The two-table schema (`workflow_status` + `operation_outputs`) is identical in structure to Verso's `verso_runs` + `verso_step_outputs` — the resolution document acknowledges this explicitly (`durable-runtime.md:22`: "DBOS `_core.py` + schema `dbos.workflow_status` + `dbos.operation_outputs` — the entire durable engine is Python + Postgres, startup recovery runs in a background thread, no server needed").

2. **DBOS source read at `infra-durable-execution.md:161–276`** (KNOWN label, cloned): `startup_recovery_thread` (`_recovery.py:26`), `MAX_RECOVERY_ATTEMPTS=100` (`_registrations.py:10`), transaction-piggyback (`_core.py:1448`), step identity `function_id` counter (`_context.py:169`). All of these are what Verso would implement from scratch.

3. **"Find the abstraction by using it" is the thesis:** `PRD_v1.md §2`: "The single loudest meta-lesson in the harvest is that the right abstraction cursor *cannot be found on paper — only by using the thing* (it's why LangChain had to rewrite)." `THESIS_VERIFICATION.md §7`: "Keep it simple; you'll regret over-engineered code in 1–2 years — vindicated as a default heuristic." The durable-engine design is the longest resolution document in the set (801 lines, 7 Open Unknowns).

4. **Open Unknowns count as scope risk:** The 7 Open Unknowns in `durable-runtime.md` include: exactly-once for destructive tools with external DB (real), transaction-piggyback for DB-touching tools (real), journal compaction (real), HITL routing and external-resolver DX (real), sub-agent durable fan-out (deferred), SQLite behavioral divergence (real for dev/test), `internal_only` event semantics (real). These will each require schema or interface changes. Building the full engine before resolving them means the schema and interface will change during implementation — and during implementation of the first real agent.

5. **The CheckpointBackend ABC has 11 abstract methods.** LangGraph's `BaseCheckpointSaver` — cited as the model — has 5. The additional 6 (`claim_pending_runs`, `extend_lease`, `recover_expired_runs`, `delete_run`, and the two HITL-adjacent ones) are worker-queue management that DBOS already implements. Writing a second worker queue management layer before using the first violates "no non-bottleneck dependency."

---

## Recommendation

**REVISE: separate the architecture target from the Phase 0 execution.**

The design is architecturally correct and the evidence is sound. The problem is scope sequencing.

**Keep (architecture is right):**
- Family B memoization as the model.
- DBOS-shaped two-table schema as the canonical target.
- Inngest SHA-1 step ids as the Phase 1+ target.
- Resonate Durable Promise spec as the HITL target.
- LangGraph-shaped `CheckpointBackend` interface as the seam.

**Change (execution is wrong):**
- Phase 0/1: use DBOS directly. `pip install dbos`. Write `@DBOS.workflow()` + `@DBOS.step()` decorators as thin wrappers that satisfy the seam test (`agent.run(durable=True)` = same loop). The `CheckpointBackend` interface is a 5-method stub backed by DBOS's own internals. Build 3–5 real agents.
- Phase 2: replace DBOS's ordinal step ids with SHA-1 names when the first real reorder bug is hit. Replace `DBOS.recv` with the named-promise HITL only when an external resolver (webhook, Slack bot) is actually needed. Define the final `CheckpointBackend` ABC from the pain points discovered.
- Phase 3: build the full in-house engine to replace DBOS once the interface is frozen from evidence, not from synthesis.

The specific cheaper alternative at Phase 0/1 is DBOS: pip-installable, pure Python + Postgres, no orchestration server, identical schema, working recovery thread, and sufficient HITL. Nothing is architecturally foreclosed by this sequencing — the `CheckpointBackend` interface means DBOS is swappable behind it later. What is gained: the builder finds the right abstraction by running agents, not by re-reading the source code of other people's agents.

**Verdict: REVISE** — not because the architecture is wrong, but because the scope is Phase 2 work presented as Phase 0 delivery, violating the "find the abstraction by use" thesis clause the PRD itself identifies as the highest-stakes design lesson.
