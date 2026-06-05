# Adversarial Critique — colocated-postgres · Lens: THESIS & SCOPE

**Reviewer:** Red-team panel (THESIS & SCOPE lens)  
**Decision under review:** One colocated Postgres in prod holds durable checkpoints + memory (pgvector) + eval/traces (one SQLite file in dev holds all three). ClickHouse/Qdrant/Neo4j are opt-in upgrades only.  
**Resolution sources read:** `_RESOLUTIONS.md §0`, `durable-runtime.md`, `memory.md`, `evals-trace.md`  
**Teardowns read:** `infra-durable-execution.md` (header + D1-D3), `infra-retrieval-vector.md` (header)  
**Date:** 2026-06-05  

---

## The Attack

**The design ships a mandatory Postgres dependency on Phase 2 (durable seam) for a solo-dogfood v1 — when the literal Phase 0 and Phase 1 deliverables (the tactical core + memory + evals) can and should run with zero Postgres.**

The problem is not that Postgres is a bad choice for prod. It is not. The problem is the ordering and the coupling: the colocated-Postgres story was assembled by taking four separate subsystem requirements — checkpoint store, vector memory, eval/trace store, and the optional graph arm — and binding them together into one "one flag gives you everything" story. That binding is the over-engineering. Each subsystem has a perfectly adequate simpler option that a solo dogfood builder needs, and the design chose to fuse them before there is evidence they belong fused.

### The concrete thesis violation

The verified thesis says (THESIS_VERIFICATION.md §Claim 7, strongly supported):

> *"Keep it simple; you'll regret over-engineered code in 1–2 years." … "start by using LLM APIs directly" … "the right abstraction cursor cannot be found on paper — only by using the thing."*

The PRD itself restates this explicitly (§8): **Phase 0 is the dogfoodable core (loop + context + tools + model + stream, zero memory, zero evals, zero durable). Phase 1 adds memory + evals. Phase 2 adds the durable seam.** The colocated-Postgres story primarily serves Phase 2 (the durable checkpoint store IS the reason you need Postgres at all — memory and traces can both run on sqlite-vec and SQLite respectively). But the design bundles all three into one Postgres migration, one `CREATE EXTENSION vector`, one connection pool, one mental model — implicitly making Postgres a "you need this by Phase 1" requirement.

The honest accounting:

| Subsystem | Phase it's built | What the dev tier is | What the prod tier ACTUALLY needs | Does it need Postgres specifically? |
|---|---|---|---|---|
| Durable checkpoints | Phase 2 | SQLite (`aiosqlite`) | Postgres (per DBOS/Centaur evidence — correct) | **Yes. This is the load-bearing reason.** |
| Memory (vectors) | Phase 1 | sqlite-vec | sqlite-vec is fine up to ~10k memories | **No — not until vector scale is a real problem.** |
| Eval/trace store | Phase 1 | SQLite | SQLite (per evals-trace.md D8 own conclusion) | **No — evals-trace.md says "SQLite is correct for dev" with no scale trigger.** |
| Graph arm (`memory_links`) | Phase 3 | N/A | Postgres adjacency table | **No — Phase 3 only, explicitly deferred.** |

So the actual Postgres forcing-function is **Phase 2 / durable checkpoints**. Everything else either runs fine on SQLite + sqlite-vec in dev, or is a Phase 3 concern.

The design resolves this correctly in terms of "which backend is default" (sqlite-vec + SQLite dev, Postgres prod) but then re-introduces the complexity by framing the whole colocated story as a single decision and writing a merged Postgres migration that bundles the checkpoint schema (`verso_runs`, `verso_step_outputs`, `verso_run_events`, `verso_hitl_promises`, `verso_sandboxes`) with the memory schema (`memory_items`, `entities`, `unit_entities`, `memory_links`, `memory_history`, `memory_buffer`) and the trace store. This is six memory tables, five checkpoint tables, and two trace tables in one migration.

**That is not "colocated Postgres for simplicity." That is a 13-table multi-subsystem schema migration that a solo builder will wire up once and be stuck maintaining across three phases of development — all before a single dogfood agent has confirmed whether memory + evals in prod actually need Postgres instead of sqlite-vec + SQLite.**

### The specific cheaper alternative

For Phase 0 and Phase 1, the design should be:

- **Dev everywhere:** sqlite-vec (memory) + SQLite (evals/traces). No Postgres required. This is what the design says.
- **Phase 0/1 prod:** same as dev. A solo dogfood builder's "prod" is a single VPS or their own machine. The risk of sqlite-vec failing at 10k memories is negligible for a dogfood deployment.
- **Phase 2 prod (durable seam):** Postgres is now required. This is the correct forcing function. Add ONLY the five checkpoint tables (`verso_runs`, `verso_step_outputs`, `verso_run_events`, `verso_hitl_promises`, `verso_sandboxes`) in one migration. No vector extension needed for Phase 2.
- **Phase 3 prod (memory scale):** Now add `CREATE EXTENSION vector` and the memory schema tables. User who runs Postgres for Phase 2 gets pgvector without a second service — this is the real "colocated" win.

The cheaper alternative is not a different stack. It is: **defer the merged Postgres migration until Phase 3, when the user actually runs Postgres for durable checkpoints AND the memory store actually needs vectors in Postgres.** Phase 2 installs Postgres and the five checkpoint tables only. Phase 3 adds the vector extension and memory tables to the same instance.

What is lost by deferring past Phase 0/1: nothing. sqlite-vec + SQLite handles everything through Phase 1 without question. What is lost by deferring past Phase 2: the one-migration convenience, which is a DX nicety but not a correctness requirement.

### Is the evidence base for the colocated claim actually verified?

The design cites Hindsight's `alembic/versions/5a366d414dce_initial_schema.py` as proof that "a single Postgres can be the entire memory backend and reach near-SOTA (91.4% LongMemEval)." That is true as a performance claim. But Hindsight is a **purpose-built memory system** — it started with Postgres and never had a Phase 0 that needed to be sqlite-vec-first. The claim "colocated Postgres works at parity" is correct; the claim "therefore start with it on Phase 1 dogfood" is the leap the evidence does not support.

Similarly, the DBOS `DEFAULT_MAX_RECOVERY_ATTEMPTS=100` and Centaur `workflow_engine.py:338-435` cited in durable-runtime.md are genuine proof that **Postgres is sufficient for durable checkpoints with no external server** — not proof that the memory schema should also ship in the same migration.

### The verdict on "build vs. compose"

For the durable checkpoint store: **build** is justified (durable-runtime.md D1 is correct — Temporal requires a server, Restate requires a Rust VM, Inngest's re-POST model is wrong for in-process agents). The in-house `CheckpointBackend` + five tables is the right call.

For the memory Postgres prod tier: **compose/defer** is the right call for Phase 0–2. sqlite-vec handles the dev/dogfood case. When the dogfood reveals a real need for pgvector (because memory store hits 10k+ items, or because the graph arm is worth having), add it in Phase 3 on the same Postgres instance the durable store already uses. That is exactly the "colocated Postgres = no second service" win — but earned via dogfood evidence, not paper design.

For the eval/trace store: **defer** entirely to Phase 1+ dogfood as the design already recommends. evals-trace.md D8 says "SQLite is correct for dev" with no stated scale trigger — the prod Postgres/ClickHouse arm should wait for operator-scale evidence.

---

## Does It Break the Decision?

**Partially. The design does not break its own correctness goals (the architecture is sound), but it violates the thesis specifically on the "defer non-bottleneck complexity" and "find the right abstraction by using it, not on paper" principles.**

The decision does NOT need to change in terms of the chosen backends (SQLite dev / Postgres prod is correct for all three subsystems). The decision DOES need to change in terms of the merged migration story: the colocated Postgres is presented as a Phase 1 concern, but the honest forcing function for Postgres is Phase 2 (durable seam). Bundling the memory schema and trace schema into the same migration before Phase 2 ships is over-engineering ahead of evidence — exactly the thesis failure mode.

The decision survives on architecture. It does not survive on thesis-fidelity for the sequencing claim: the colocated story is correctly designed but prematurely bundled.

---

## Evidence Checked

| Source | What I checked | Verdict |
|---|---|---|
| `_RESOLUTIONS.md §0` (colocated Postgres table) | All four subsystem rows, the "RESOLVED" framing | The subsystem backends are correct; the merged-migration implication is the problem |
| `durable-runtime.md D1-D3` | Build-vs-delegate rationale; five-table schema | D1 is sound — Temporal/Restate overhead is real. The checkpoint schema is correct and minimal. |
| `memory.md D5` | Backend ladder; Hindsight proof-of-concept | Hindsight 91.4% claim verified (arXiv:2512.12818 cited). But Hindsight is not dogfood-first. |
| `evals-trace.md D8` | SQLite dev / ClickHouse or Postgres prod split | D8 explicitly states "SQLite is correct for dev" — never claims Postgres is needed at Phase 1. |
| `infra-durable-execution.md` (header, D1-D3 in durable-runtime) | DBOS two-table schema; Centaur workflow_engine.py | Five-table checkpoint schema is evidence-backed. Memory tables in the same migration are not. |
| `infra-retrieval-vector.md` (header) | sqlite-vec brute-force threshold at ~10k | `full_scan_threshold=10_000` confirmed for Qdrant; sqlite-vec operates brute-force below this — Phase 0/1 dogfood will not hit this. |
| `THESIS_VERIFICATION.md §Claim 7` | "keep it simple; you'll regret over-engineered code in 1–2 years" | Confirmed as mainstream frontier consensus (Anthropic, Cognition). |
| `PRD_v1.md §8` | Phase build ordering (Phase 0 → 1 → 2 → 3) | Memory is Phase 1; durable seam is Phase 2; opt-in scale is Phase 3. The colocated migration story conflates Phase 2 and Phase 3 concerns. |

---

## Recommendation

**REVISE (scoping only, not architecture):**

1. **Reframe the colocated story as a Phase 2→3 progressive disclosure, not a single decision.** The Phase 2 migration is five checkpoint tables only — no `CREATE EXTENSION vector`, no memory tables. This is what the user pays for when they flip `durable=True`. The Phase 3 migration adds `CREATE EXTENSION vector` and the six memory tables to the same Postgres instance the durable store already uses. The "you already pay for Postgres → get memory + traces for free" win is preserved, just earned in the right phase.

2. **Do not change any of the chosen backends.** SQLite + sqlite-vec for dev is correct. Postgres for prod durable + memory + traces is correct. ClickHouse is correctly opt-in for operator-scale. The backends are right; the migration bundling is premature.

3. **State the actual forcing function explicitly.** The decision note should say: "Postgres becomes a requirement at Phase 2 because of the durable seam — that is the ONLY Phase 0/1/2 reason to run Postgres. Memory vectors and traces both run on sqlite-vec + SQLite through Phase 1 without degradation." This keeps the thesis-fidelity honest: Postgres is not introduced to make memory better (it cannot be better at dogfood scale than sqlite-vec brute-force) — it is introduced because the durable seam requires it, and the memory + trace colocated wins are a free side effect.

4. **The `memory.md D5` "pluggable three-tier backend" decision is the correct framing.** Do not change it. The risk is the `_RESOLUTIONS.md §0` table being read as "ship all this in one migration on Phase 1" — which is how a builder will read it unless the phase ordering is made explicit.
