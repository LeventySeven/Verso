# Adversarial Critique: eval-trace-engine — THESIS & SCOPE lens

**Decision under review:** Verso OWNS an eval/trace layer — VersoSpan 10-kind taxonomy + VersoScore 5-element schema + dotted_order tree key, dual-emit gen_ai.* OTel primary + OpenInference enrichment, one EvalJob engine for online+offline — vs just emitting OTel to Langfuse/Phoenix.
**Resolution note:** `research/06_design_resolutions/evals-trace.md`
**Lens:** THESIS & SCOPE — does this betray "keep it simple; no non-bottleneck dependency; solo dogfood-first; tactical layer simple"?
**Critic date:** 2026-06-05

---

## The Attack

### The core claim to break

The resolution argues that Verso must OWN the schema, the store, and the EvalJob engine because (a) the universal score shape is trivially adopted by all backends with field renames only, so there's no per-backend adapter churn, (b) the judge machinery is what makes "evals == run" work, and (c) the dotted_order + VersoSpan taxonomy are needed for downstream eval metrics to consume typed span kinds. The resolution then specifies ~600 lines of data-class code, a SQLite schema with 8 indexes, a ClickHouse prod schema, an async EvalQueue protocol, an EvalRule engine, an EvalRun/DatasetRunItem model, 9 built-in scorers, a JudgePanel, and a G-Eval logprob path.

**The attack:** this is the right DESTINATION but the wrong PHASE. The resolution confounds two separate questions: (1) what is the correct data model?, and (2) who should implement and own the store, queue, and judge engine in Phase 0/1? The resolution answers (1) correctly from RE evidence and then silently uses that correctness to justify (2) — but (2) has a cheaper alternative that defers the multi-quarter implementation surface to Phase 2+.

### What the "just emit OTel" path actually buys

The explicit alternative the resolution rejects is: "just emit OTel spans to Langfuse/Phoenix." Let's price this concretely.

**What Verso needs at Phase 0/1 (dogfood, solo):**
- Know what the agent is doing (traces).
- Run a judge on a trace and see the score.
- Catch regressions in CI.

**What "emit OTel + Langfuse/Phoenix SDK" covers immediately:**
- `opentelemetry-sdk` + `opentelemetry-exporter-otlp` = 2 pip installs.
- Langfuse's OTLP endpoint reads `gen_ai.*` natively (P3 in `ObservationTypeMapper.ts`). Spans appear in the Langfuse UI with zero custom code.
- `langfuse` SDK ships `langfuse.score(trace_id, name, value, comment)` — that IS the VersoScore write path, externalized.
- Langfuse's eval scheduler (the `EvalJob` engine) is already built, already running, already proven at scale (it's the entire `worker/.../evalService.ts` the resolution RE'd). You configure it in the UI or via API; it reads from its own store.
- For offline eval: Braintrust `Eval(name, data, task, scores)` runs your agent function over a dataset and produces a CI-gatable result. It is `pip install braintrust` + 10 lines of user code — the resolution RE'd this exact pattern.

**The cost of the OTel-out path:**
- No custom span schema (use `gen_ai.*` attributes on plain OTel spans).
- No SQLite schema, no ClickHouse schema, no `ReplacingMergeTree`, no `sumMap` rollup.
- No EvalQueue, no EvalRule, no EvalWorker coroutine.
- No EvalRun, no DatasetRunItem, no snapshot denormalization.
- No JudgePanel, no G-Eval logprob path, no 9 built-in scorer implementations.
- Defer all of that to Phase 2+ when dogfood proves what's missing.

**What is actually lost by deferring:**

The resolution's strongest argument is the "eval == run" seam — the trace is produced by the Verso loop, the scorer operates on the Verso trace, CI gates on the result. This IS better than exporting to an external tool. But the question is whether the seam requires building the store and queue in Phase 0/1, or only designing the schema.

The answer is: **you need the schema now; you do not need the store now.** The schema (VersoSpan, VersoScore, the 10-kind taxonomy, dotted_order, the 3-source enum) must be correct from day 1 because spans emitted in the wild are hard to rename. But the schema is ~80 lines of dataclasses. The store (SQLite DDL, ClickHouse migrations, EvalQueue, EvalWorker, EvalRun, DatasetRunItem, ScoreSummary, snapshot denormalization, asyncio.Queue + Redis Streams pluggable backend, the 9 scorer implementations, G-Eval logprob path, JudgePanel with weighted aggregation) is ~500+ lines that can be replaced by Langfuse + Braintrust for the dogfood phase.

### Where the resolution over-builds relative to the thesis

The thesis has a specific formulation in THESIS_VERIFICATION.md: "build for the *durable* layer and stay ruthlessly simple in the *tactical* layer." The THESIS_VERIFICATION.md meta-verdict explicitly says "durable architecture persists; tactical workarounds churn." The eval schema is durable. The eval job engine is an implementation detail — Langfuse rebuilt it (BullMQ → ?), Opik built it differently (Redis Streams), Braintrust uses their own Brainstore. The implementation of the queue is not durable architecture; it is operational plumbing.

Specifically, these components in the resolution are **non-bottleneck at Phase 0/1:**

1. **EvalQueue (asyncio.Queue + Redis Streams pluggable backend):** Langfuse already ships this. The solo builder dogfooding Verso does not need their own at-least-once delivery queue on day 1.
2. **EvalWorker coroutine with sampling gate, delay, dedup:** Again, Langfuse's `evalService.ts` does this. This is a background service, not a core agent primitive.
3. **9 built-in scorer implementations** (Factuality, ClosedQA, GEval, Faithfulness, ToolCorrectness, AgentGoalAccuracy, EmbeddingSimilarity, LLMRubric, DAGMetric): Braintrust's `autoevals` and DeepEval ship these as `pip install`. The resolution RE'd them specifically to know the exact constants (FACTUALITY_CHOICE_SCORES, EMBEDDING_SIM_FLOOR, G_EVAL_TOP_LOGPROBS) — and those constants SHOULD be recorded and used. But the implementation wrapping them can call `autoevals.Factuality()` instead of reimplementing the identical Mustache render + forced tool-call + score-map chain.
4. **EvalRun / DatasetRunItem / snapshot denormalization / ScoreSummary:** This is a data model for experiment tracking. Braintrust already has it. MLflow already has it. Langfuse already has it. Verso building its own in Phase 0/1 is building a competitor to tools that already exist and that the solo dogfood builder already has access to.
5. **SQLite DDL + ClickHouse schema:** This is significant implementation work. The resolution specifies 3 CREATE TABLE statements with 8+ indexes, CODEC hints, Map columns, bloom filters on the ClickHouse side. For a solo dogfood-phase build, this is weeks of schema management work.

### The cheaper alternative, named precisely

**Phase 0/1 alternative:**

1. **Emit OTel spans with `gen_ai.*` attributes** from Verso's loop and `@tool` decorator using the standard `opentelemetry-sdk` + OTLP exporter. Cost: ~50 lines of instrumentation code. The span KIND can be carried as an attribute (`openinference.span.kind` or `gen_ai.operation.name`) without owning a custom store.

2. **Lock the VersoSpan + VersoScore dataclasses as the canonical internal representation** (the ~80-line schema). Emit these to OTLP. This is the "right schema from day 1" without the store.

3. **Use Langfuse (self-hosted, free tier, or cloud free tier) as the Phase 0/1 trace store and online eval engine.** `pip install langfuse` + `LANGFUSE_SECRET_KEY` env var. The entire EvalJob engine the resolution RE'd is already running there.

4. **Use `autoevals` directly for the built-in scorers.** `pip install autoevals`. The FACTUALITY_CHOICE_SCORES, EMBEDDING_SIM_FLOOR constants the resolution correctly identified are the autoevals source constants — using autoevals is using those constants.

5. **Use Braintrust `Eval()` for offline CI runs.** `pip install braintrust`. The eval==run pattern works against any Python callable.

6. **Phase 2+: build VersoTraceStore (SQLite → ClickHouse) and VersoEvalQueue.** At that point dogfood will have proven exactly what the external tools are missing — the seam integration, the HITL flywheel, the per-step reliability metrics the PRD specifies (`p50_horizon`, `p80_horizon`), the `verify_grounding` mode. None of those are in Langfuse or Braintrust today. That is the correct trigger for building the owned layer.

**What is actually lost by deferring to Phase 2:**
- The `correction` HITL→dataset flywheel (not in Langfuse or Braintrust as a first-class primitive).
- The `source_span_id` recursive observability (the judge's own trace linked to the score — not exposed in external tools in a way Verso controls).
- The `agent_version_id` tag on every span for regression gating (configurable in external tools but requires setup).
- The `verify_grounding` mode and `p50_horizon/p80_horizon` reliability metrics (Verso-specific, not generic).
- The eval == run integration at the Verso loop level (external tools require the user to instrument separately).

This is the correct payload to defer: the Verso-specific extensions that external tools don't have and that dogfood will sharpen. It is NOT a multi-quarter loss — it is a 2-month deferral of operational plumbing behind the Langfuse/Braintrust proxy.

### Does the resolution's evidence justify the scope?

The evidence is sound — the RE is genuine (Langfuse migrations, autoevals constants, Opik Java source, LangSmith `run_trees.py`). The issue is not the evidence quality; it is the inference drawn from it. The evidence proves:

- The universal score shape is `(name, value, source, trace_id, reason?)` — TRUE, and this justifies locking VersoScore now.
- The 10-kind taxonomy is proven correct — TRUE, and this justifies locking the SpanKind enum now.
- The EvalJob engine design (delayed queue, dedup, sampling, structured verdict) is the right architecture — TRUE, and this justifies designing it now for Phase 2.
- Building the EvalJob engine, SQLite schema, ClickHouse schema, EvalQueue, EvalWorker, 9 scorer implementations, JudgePanel, EvalRun, and DatasetRunItem IN PHASE 0/1 is the right call for a solo dogfood builder — **this inference is NOT supported by the evidence.** The evidence shows that mature platforms took years to build these systems. The thesis says find the abstraction by using it, not on paper. The resolution builds the full engine before using it.

### The single sharpest formulation

The resolution correctly identifies what the eval layer should look like when Verso matures. It then builds all of it before writing the first dogfood agent. The thesis says the opposite: "the right abstraction cursor cannot be found on paper — only by using the thing." The eval store, queue, and scorer implementations are exactly the kind of operational infrastructure that should be validated by use before being built. Langfuse + autoevals + Braintrust are not "non-bottleneck dependencies" in the pejorative sense — they are the validation substrate. Building the Verso-owned versions before the dogfood proves what the external tools are missing is over-engineering around a non-bottleneck.

---

## Does It Break the Decision?

**Partially. The attack lands on scope/phase, not on the schema choices.**

The schema decisions (VersoSpan dataclass, VersoScore shape, 10-kind taxonomy, dotted_order, 3-source enum, the specific constants from autoevals/DeepEval/Opik) are CORRECT and should be locked now. They are cheap (80-100 lines of dataclasses) and expensive to change later. These do not betray the thesis.

The implementation scope (SQLite DDL, ClickHouse schema, EvalQueue protocol, EvalWorker coroutine, EvalRun / DatasetRunItem / ScoreSummary data model, 9 scorer implementations wrapping autoevals/DeepEval patterns, JudgePanel with G-Eval logprob) is buildable by a solo developer but represents 2-3 months of work that can be deferred to Phase 2 behind the Langfuse/autoevals/Braintrust proxy without losing anything the Phase 0/1 dogfood actually needs.

The attack does NOT break the destination. It breaks the phase assignment — the resolution treats Phase 0/1 as the right time to build a full eval platform when the thesis calls for finding the abstraction by use first.

**Verdict: REVISE** — not the schema, but the phase gate. Split the decision into: (a) lock schema now (VersoSpan + VersoScore + enums + constants — build this), and (b) build store/queue/scorers in Phase 2 after dogfood, backed by Langfuse + autoevals proxy in Phase 0/1.

---

## Evidence Checked

1. `research/06_design_resolutions/evals-trace.md` — read in full. The Component Spec section (lines 493–742) catalogs the full implementation surface: 5 dataclasses, 2 SQLite tables (8 indexes), ClickHouse prod schema, EvalQueue protocol, EvalWorker loop, EvalRule, 9 scorer stubs, JudgePanel, EvalRun, DatasetRunItem, ScoreSummary. Confirmed this is a multi-quarter implementation surface, not a schema lock.

2. `research/03_teardowns/eval-observability.md` — read lines 1–500. Confirmed: Langfuse ships `evalService.ts` (the EvalJob engine), Braintrust ships `autoevals` with the exact scorer implementations Verso plans to replicate, Opik ships the Redis Streams consumer-group engine. All are `pip install` / self-hostable today.

3. `research/THESIS_VERIFICATION.md` — read in full. The meta-verdict at line 72: "build for the *durable* layer and stay ruthlessly simple in the *tactical* layer." The eval store and queue are tactical infrastructure, not durable architecture. The schema is durable architecture.

4. `docs/PRD_v1.md` §2 (Scope): "v1 optimizes for 'I can build my own AI products on this and feel where it's wrong,' not for external adoption metrics." A full eval platform built before the first dogfood agent contradicts this directly.

5. `docs/PRD_v1.md` §5.5 (Evals): "No framework ships this; every winning *product* does." This is the motivation for evals being first-class — but "first-class" in the PRD sense means the eval API is a core construct, not that the eval store is built from scratch in v1.

6. Load-bearing source claims verified: Langfuse `domain/scores.ts:4` (ScoreSourceArray), MLflow `assessment.py` (AssessmentSourceType), autoevals `py/autoevals/llm.py:91` (DEFAULT_MODEL), autoevals `templates/factuality.yaml` (score map), DeepEval `metrics/g_eval/utils.py:336` (logprob weighting), Opik `OnlineScoringEngine.java` (agenticToolsThresholdTokens). All are consistent with what the resolution cites — no misread sources found.

---

## Recommendation

**REVISE the implementation scope, not the schema.**

**Keep as-is (correct, build now):**
- VersoSpan and VersoScore dataclasses with the 10-kind taxonomy, dotted_order construction, 3-source enum, and all named constants (FACTUALITY_CHOICE_SCORES, EMBEDDING_SIM_FLOOR, G_EVAL_TOP_LOGPROBS, AGENTIC_JUDGE_THRESHOLD_TOKENS, etc.). These are 80-100 lines and are expensive to change later.
- The OTel emit layer (gen_ai.* primary + openinference enrichment). This is a ~50-line OTLP exporter wrapping the VersoSpan.

**Defer to Phase 2 (build after dogfood proves the gap):**
- SQLite DDL and ClickHouse schema. Use Langfuse (self-hosted free tier) as the Phase 0/1 trace store.
- EvalQueue protocol + EvalWorker coroutine. Use Langfuse's online eval scheduler.
- EvalRun / DatasetRunItem / ScoreSummary. Use Braintrust `Eval()` for offline CI runs.
- The 9 built-in scorer implementations. Call `autoevals.Factuality()`, `autoevals.EmbeddingSimilarity()`, DeepEval's `GEval`, etc. directly. The correct constants are already in Verso's resolution note; the implementation is `pip install autoevals deepeval`.
- JudgePanel with G-Eval logprob path and weighted aggregation.

**The phase-2 trigger:** when dogfood reveals a gap the external tools can't fill. The candidates from the resolution's Open Unknowns are the correct triggers: the `correction` HITL→dataset flywheel (not in Langfuse/Braintrust), the `source_span_id` recursive observability, the `p50_horizon`/`p80_horizon` reliability metrics, the `verify_grounding` integration at the loop level. Build the owned layer when the gap is proven, not before.

**What this saves:** approximately 2-3 months of Phase 0/1 time building operational infrastructure (store, queue, 9 scorer implementations) that Langfuse + autoevals + Braintrust already provide for free. The thesis is "find the abstraction by using it." The proxy phase IS the use.
