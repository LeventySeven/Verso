# Adversarial Critique — eval-trace-engine — CORRECTNESS lens

**Decision under review:** Verso OWNS an eval/trace layer: VersoSpan 10-kind taxonomy + VersoScore 5-element schema + dotted_order tree key, dual-emit gen_ai.* OTel primary + OpenInference enrichment, one EvalJob engine for online+offline.
**Lens:** CORRECTNESS — Does the cited RE evidence actually prove this works for Verso's exact case?
**Date:** 2026-06-05
**Verdict:** REVISE

---

## The attack

Two load-bearing claims in the resolution are factually wrong when checked against the actual cloned source. Both are silent failures — they produce no error at build time but silently lose data at runtime.

### Bug 1: The 10-kind taxonomy is NOT what Langfuse has proven

The resolution at Decision 2 says: *"The 10-kind taxonomy is proven: Langfuse adopted it (migration 0001/0002/0003)"* and cites `domain/observations.ts:5`. **This is a misread.**

Langfuse's actual taxonomy (verified at `/tmp/verso-re-eval/langfuse/packages/shared/src/domain/observations.ts:5`):

```
SPAN, EVENT, GENERATION, AGENT, TOOL, CHAIN, RETRIEVER, EVALUATOR, EMBEDDING, GUARDRAIL
```

Verso's proposed VersoSpan taxonomy (`schema.py` SpanKind):

```
SPAN, GENERATION, AGENT, TOOL, CHAIN, RETRIEVER, EMBEDDING, GUARDRAIL, EVALUATOR, RERANKER
```

The two differ in two ways: Verso **drops EVENT** (which Langfuse has) and **adds RERANKER** (which Langfuse does not have). RERANKER exists only in OpenInference (`OpenInferenceSpanKindValues.RERANKER` at `semconv/trace/__init__.py:522`).

The consequence, verified in Langfuse's `ObservationTypeMapper.ts`: the P2 OpenInference mapper at line 236 maps `RERANKER` to... nothing (no entry for `RERANKER`). The final fallback at line 483 returns `"SPAN"`. So any Verso span emitted with `openinference.span.kind=RERANKER` is **silently downgraded to a generic SPAN in Langfuse**. The Decision 2 rationale says "every downstream eval metric consumes typed span kinds" and "coarser taxonomies break downstream eval" — but RERANKER is itself the coarser case when the backend is Langfuse. A reranker-quality scorer querying for RERANKER spans in Langfuse finds none.

The Langfuse OTel mapper has been independently verified to contain no RERANKER entry in any path (`grep -rn "RERANKER" /tmp/verso-re-eval/langfuse/` returns zero results in non-test production code).

The rationale at Decision 2 only defends GUARDRAIL and EVALUATOR as "required for Verso's safety hooks and judge spans to be queryable as first-class objects." It does not defend RERANKER for Verso's case. Verso's PRD §4.2 has no dedicated RERANKER module in v1; its memory/ module uses RRF k=60 as a pluggable reranker but this is not a first-class span kind. The claim that RERANKER's inclusion is "proven" by Langfuse is false — it is borrowed from OpenInference but incompatible with the primary stated target backend (Langfuse).

### Bug 2: Wrong OTel attribute names for cache tokens

Decision 3 specifies these attributes to emit on a GENERATION span:

```
gen_ai.usage.cache_read_input_tokens    # from usage["cache_read"] if present
gen_ai.usage.cache_creation_input_tokens  # from usage["cache_write"] if present
```

The actual OTel GenAI spec attribute names, verified in OpenInference `_genai_attributes.py:43-44`:

```python
GEN_AI_USAGE_CACHE_CREATION_INPUT_TOKENS = "gen_ai.usage.cache_creation.input_tokens"
GEN_AI_USAGE_CACHE_READ_INPUT_TOKENS = "gen_ai.usage.cache_read.input_tokens"
```

The resolution uses underscores throughout (`cache_read_input_tokens`). The spec uses a dot in the middle (`cache_read.input_tokens`). These are **different attribute names**.

Langfuse confirms this. Its `OtelIngestionProcessor.ts` extracts cache tokens at lines 2468-2479 by stripping the `gen_ai.usage.` prefix and looking for:

```
"cache_read.input_tokens"   ← expects the dot form
"cache_creation.input_tokens" ← expects the dot form
```

The resolution's underscore form `cache_read_input_tokens` does NOT appear in Langfuse's cache token extraction chain. Langfuse's own test suite at `otelMapping.servertest.ts:2107` uses `gen_ai.usage.cache_read.input_tokens` (dot form), not the underscore form. If Verso emits the resolution's attribute names, Langfuse will not extract `cacheReadTokens` and `cacheCreationTokens` — those fields will be null and the cache cost data will be silently lost.

---

## Does it break the decision?

**Partially.** The two bugs are real and would cause silent data loss in production. However they are **correctable without redesigning anything structural** — only the specific attribute name strings and the taxonomy membership need adjustment. The core architectural decisions (own the schema, 5-element score shape, dotted_order, EvalJob engine, contextvars span tree, G-Eval logprob weighting, HITL flywheel) are all verified correct by the source evidence.

What specifically breaks:

1. **RERANKER kind emitted to Langfuse → silently becomes SPAN.** Any downstream scorer or query that filters on RERANKER span kind returns empty results in Langfuse. The correct resolution: drop RERANKER from VersoSpan's SpanKind for v1 (Verso has no dedicated reranker primitive) OR add EVENT (which Langfuse does have) and acknowledge RERANKER is Arize-only. Alternatively, if RERANKER matters: Verso should emit `openinference.span.kind=RERANKER` only when `enrichment=true` and document that Langfuse loses the kind.

2. **Cache token attributes silently lost in Langfuse.** The fix is trivial: replace `cache_read_input_tokens` with `cache_read.input_tokens` and `cache_creation_input_tokens` with `cache_creation.input_tokens` in the emitted OTel attributes. This is a one-line fix per attribute.

What does NOT break: the five-element VersoScore shape (confirmed across 6 platforms), the dotted_order encoding (confirmed at `run_trees.py:1245` exactly), the EvalJob queue + sampling + delay design (confirmed at `evalService.ts:180,620,644,677,699`), the dataset_run_items snapshot denormalization (confirmed in migration 0024), the agenticToolsThresholdTokens=50_000 constant (confirmed in `OnlineScoringConfig.java:76`), the define_outcome bounded loop (confirmed in `research-deepresearch.md:512`). The contextvars-based span tree is sound for Python asyncio.

---

## Evidence checked

Files cloned and read:
- `/tmp/verso-re-eval/langfuse/packages/shared/src/domain/observations.ts` — actual 10-kind taxonomy; no RERANKER
- `/tmp/verso-re-eval/langfuse/packages/shared/src/server/otel/ObservationTypeMapper.ts` — P2 OpenInference mapper; RERANKER absent; fallback is SPAN at line 483
- `/tmp/verso-re-eval/openinference/python/openinference-semantic-conventions/src/openinference/semconv/trace/__init__.py:515` — OpenInferenceSpanKindValues; RERANKER is OpenInference-only
- `/tmp/verso-re-eval/openinference/python/openinference-instrumentation/src/openinference/instrumentation/_genai_attributes.py:43-44` — authoritative OTel attribute names; `cache_read.input_tokens` (dot, not underscore)
- `/tmp/verso-re-eval/langfuse/packages/shared/src/server/otel/OtelIngestionProcessor.ts:2468-2479` — cache token extraction logic; requires dot form
- `/tmp/verso-re-eval/langfuse/web/src/__tests__/server/api/otel/otelMapping.servertest.ts:2107` — Langfuse test uses `gen_ai.usage.cache_read.input_tokens` (dot)
- `/tmp/verso-re-eval/autoevals/py/autoevals/llm.py` — DEFAULT_MODEL:91, build_classification_tools:115, tool_choice:232; all CONFIRMED as cited
- `/tmp/verso-re-eval/autoevals/py/autoevals/templates/factuality.yaml` — score map CONFIRMED {A:0.4, B:0.6, C:1.0, D:0.0, E:1.0}
- `/tmp/verso-re-eval/autoevals/py/autoevals/string.py:197` — scale_score CONFIRMED; expected_min=0.7 default CONFIRMED
- `/tmp/verso-re-eval/langsmith-sdk/python/langsmith/run_trees.py:1245` — _create_current_dotted_order CONFIRMED at exact line
- `/tmp/verso-re-eval/deepeval/deepeval/metrics/g_eval/template.py:44` — score_range=(0,10) CONFIRMED
- `/tmp/verso-re-eval/deepeval/deepeval/metrics/g_eval/utils.py:336,351` — calculate_weighted_summed_score, log(0.01) filter CONFIRMED
- `/tmp/verso-re-eval/deepeval/deepeval/metrics/g_eval/g_eval.py:56` — top_logprobs=20 default CONFIRMED
- `/tmp/verso-re-eval/langfuse/packages/shared/src/domain/scores.ts:4` — ScoreSourceArray CONFIRMED at exact line
- `/tmp/verso-re-eval/langfuse/worker/src/features/evaluation/evalService.ts:180,644,677,699` — createEvalJobs, PENDING, delay, CANCELLED CONFIRMED (±10 line drift from stated numbers)
- `/tmp/verso-re-eval/opik/apps/opik-backend/src/main/java/com/comet/opik/infrastructure/OnlineScoringConfig.java:76` — agenticToolsThresholdTokens=50_000 CONFIRMED
- `/tmp/verso-re-eval/opik/apps/opik-backend/src/main/java/com/comet/opik/api/resources/v1/events/OnlineScoringEngine.java:82-83` — SCORE_FIELD_NAME="score", REASON_FIELD_NAME="reason" CONFIRMED
- `/tmp/verso-re-eval/langfuse/packages/shared/clickhouse/migrations/clustered/0024_dataset_run_items.up.sql` — snapshot denormalization CONFIRMED
- `/tmp/verso-re-eval/langfuse/packages/shared/clickhouse/migrations/clustered/0030_add_eval_execution_trace_id_to_scores.up.sql` — execution_trace_id migration CONFIRMED
- `/Users/seventyleven/Desktop/Verso/research/03_teardowns/agents-character-deep.md:503-508` — JudgeJudy weights (0.4/0.4/0.2), threshold=0.7 CONFIRMED
- `/Users/seventyleven/Desktop/Verso/research/03_teardowns/research-deepresearch.md:512` — define_outcome default=3/max=20 CONFIRMED

Not found / could not verify: the `sumMap` reference at `repositories/events.ts:3287` is now at line 3361 — expected line drift, mechanism is correct.

---

## Recommendation

**REVISE** on two specific points before committing to PRD/implementation:

1. **Fix cache token OTel attribute names.** In `verso/evals/otel_compat.py` and wherever GENERATION spans are built, replace:
   - `gen_ai.usage.cache_read_input_tokens` → `gen_ai.usage.cache_read.input_tokens`
   - `gen_ai.usage.cache_creation_input_tokens` → `gen_ai.usage.cache_creation.input_tokens`
   This is a one-word fix. The resolution's stated source (`openinference/_genai_conversion.py`) uses the dot form — the resolution incorrectly transcribed it with underscores.

2. **Resolve the RERANKER kind.** Three honest options:
   - **Drop it from v1 VersoSpan.** Verso's PRD has no dedicated reranker primitive in v1; the PRD's memory module uses RRF as a pluggable reranker but this doesn't need a first-class span kind. A RERANKER call inside a tool becomes a generic SPAN or TOOL span. Add it back when Verso v2 ships a first-class reranker.
   - **Add EVENT instead.** Langfuse has EVENT, not RERANKER. If Verso wants to be forward-compatible with Langfuse's actual taxonomy, add EVENT and drop RERANKER. The 10-kind taxonomy that is "proven" is Langfuse's, not the proposed hybrid.
   - **Document the Arize-only gap explicitly.** If RERANKER is kept, the resolution must acknowledge: "RERANKER spans are SPAN in Langfuse; they only retain kind identity in Arize Phoenix." The current claim that the taxonomy is "proven" by Langfuse is false for RERANKER.

The rest of the decision — 5-element score shape, dotted_order, EvalJob queue, G-Eval logprob weighting, dataset snapshot denormalization, online/offline unification, HITL flywheel, judge structured output — is well-evidenced and compositionally sound for Python async ReAct. The two bugs above are attribute-level mistakes in an otherwise solid design.
