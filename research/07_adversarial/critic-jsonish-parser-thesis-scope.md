# Adversarial Critique — jsonish-parser decision
**Lens:** THESIS & SCOPE
**Decision under review:** Build a BAML-style jsonish 5-stage SAP repair parser as the DEFAULT structured-output path, Pydantic v2 hard dep, Guardrails-style validator contract — vs composing Instructor (3M downloads/mo, existing library).
**Resolution note:** `06_design_resolutions/structured-output.md`
**Teardown source:** `03_teardowns/structured-output.md`
**Date:** 2026-06-05

---

## The Attack

The resolution makes a build-vs-compose call across six interlocking sub-decisions (the waterfall, the coercion layer, the validator contract, the provider mode map, the reask loop, the streaming partial model). The thesis-scope lens asks: is this the simplest thing that works for dogfood-first v1, or did the design build a multi-quarter engine where an existing library or a careful deferral would do?

The answer is **split**: two of the six sub-decisions are genuinely unjustifiable BUILD at Phase 0/1, one is correctly built but partially misframed, and three are correctly built with good justification. The compounded error is that the resolution presents all six as one unified decision and uses a benchmark that conflates two different modes to justify the whole stack. The attack has two prongs.

### Prong 1 — The benchmark cited to justify SAP-over-FC does not justify the waterfall; it justifies SAP over native function-calling, which is a different thing than what Instructor's TOOLS mode does

The load-bearing accuracy claim is: BAML SAP blog benchmarks showing gpt-4o-mini 92.4% SAP vs 19.8% FC.

**The problem:** FC (function-calling / `response_format: function_call`, the deprecated API) is not the same as forced TOOLS mode. Instructor's TOOLS mode uses `tool_choice={"type":"function","function":{"name":...}}` — a forced, single tool call, where the provider returns the arguments already extracted and structured inside `function.arguments`. That JSON is post-hoc parsed by Instructor via `json.loads(tool_call.function.arguments)` → `model_validate`. The model's output IS the JSON (not prose with JSON embedded), because tool-calling enforces structural extraction at the provider level. The SAP benchmark compares against `function_call` (the deprecated API, available only on gpt-3.5/early gpt-4 era models), not against modern forced-tool-call. The resolution's conclusion — "SAP strictly beats native function-calling across every model tested" — is true for legacy FC mode but does not apply to the forced-TOOLS path Instructor actually uses. The benchmark does not show SAP beating modern forced-tool-call.

**Why this matters for scope:** the primary justification for the waterfall is that it is more accurate than alternatives. If the waterfall's accuracy advantage is narrow or non-existent against forced TOOLS mode (which is what Instructor gives you by default), the argument for building 500 lines of waterfall+coercion in Phase 0 weakens considerably. The resolution should have compared against Instructor TOOLS mode, not against deprecated FC.

**Evidence checked:** Instructor `processing/function_calls.py:728-754` (TOOLS mode `parse_tools` — calls `model_validate_json(tool_call.function.arguments)` directly; the JSON is already structured by the provider, no fence extraction needed); BAML SAP blog benchmark framing ("native function calling", measured against gpt-4o-mini/claude-3-5-sonnet — confirmed the comparison is against the now-deprecated `function_call` API, not forced-tool-call); teardown `structured-output.md` §BAML ("gpt-4o-mini 92.4% vs 19.8% FC").

### Prong 2 — Instructor is NOT the right compose target for the waterfall, but it IS the right compose target for the provider mode map and the reask loop — and the resolution builds both when it could defer the latter

This is the over-engineering prong. Let me be precise about which pieces Instructor actually provides vs doesn't:

**What Instructor provides that the resolution builds from scratch:**
- Provider mode map / `DEPRECATED_TO_CORE` (40+ modes → 5 canonical): fully implemented, battle-tested, kept current by the Instructor maintainers. The resolution builds a bespoke capability table (`PROVIDER_STRUCTURED_OUTPUT_CAPS`) for no benefit over Instructor's map.
- Reask loop with tenacity, per-attempt `FailedAttempt`, `total_usage` summation, mode-framed reask messages (tools vs json vs streaming): fully implemented. Instructor `core/retry.py` and `processing/response.py:652` (mode-to-reask-handler map). The resolution builds a near-identical `parse_with_reask` that duplicates this.
- `jiter`-based streaming partial model with `model_construct` + sibling completeness heuristic: fully implemented in `dsl/partial.py` and `dsl/json_tracker.py`. The resolution's `Partial[T]` is a replication.
- Memoized partial-model cache: `_partial_model_cache` in Instructor, `_PARTIAL_MODEL_CACHE` in the resolution — identical.

**What Instructor does NOT provide (and therefore must be built regardless):**
- The jsonish waterfall proper: Instructor's fence extraction is `extract_json_from_codeblock` = find first `{`, find last `}`, return substring. Verified at `utils/core.py:43-65`. No markdown fence preference logic, no grep-embedded-JSON stage, no fixing parser (unquoted keys / trailing commas / single quotes / truncated streams), no `CompletionState`. This is genuinely not composable from Instructor.
- The typed Flag cost function / `pick_best` coercion: Instructor calls `json.loads` → `model_validate`. It has no schema-guided semantic coercion layer whatsoever.
- The `validation_context` passthrough (from Instructor's `function_calls.py:91-110`): this is a plug Instructor exposes; Verso should thread it through rather than duplicate the reask loop just to add it.

**The compose gap is real — but only for two of the six sub-decisions.** The resolution correctly identifies the waterfall and coercion layer as unbuildable from Instructor. But it then also rebuilds the provider mode map, reask loop, and streaming partial — pieces that Instructor already ships at production quality.

**Specific cheaper alternatives:**

1. *Provider mode map and reask loop:* use Instructor as a thin composition target at the response-parsing seam. Verso's architecture already defines a `ModeHandlers` bundle (three callables: `request_handler`, `response_parser`, `reask_handler`). Instructor's `process_response` + `retry_sync` IS exactly this bundle. Verso can call `instructor.from_openai(client, mode=Mode.TOOLS)` and get the reask loop for free, then plug in the jsonish waterfall at the `response_parser` seam (the teardown itself identifies this: "instead of `json.loads`, run the jsonish repair waterfall" — `structured-output.md` §Instructor "function_calls.py:91-110"). The openai hard-dep issue (below) is real but addressable.
2. *Streaming partial:* use `jiter` directly (already a transitive dep of Pydantic v2 — verified that pydantic-core requires jiter). The memoized `Partial[T]` rewrite + sibling completeness check is 60-80 lines in Python. Lift from Instructor's `dsl/partial.py` and `dsl/json_tracker.py` directly rather than reimplementing identically.

**The Instructor hard-dep problem:** Instructor v1.15.1 requires `openai>=2.0.0` as a non-optional hard dependency (verified in METADATA). This is not acceptable for a provider-agnostic framework — Verso could not declare Instructor a dependency without also mandating the OpenAI SDK. This **does** block naive composition.

However, this blocking fact validates the plug-in-at-seam approach (call specific functions from Instructor that don't invoke the openai SDK at import time) or motivates a one-time fork of the 4-5 modules that matter (`core/retry.py`, `processing/function_calls.py`, `mode.py`, `dsl/partial.py`, `dsl/json_tracker.py`) stripped of the openai import. This is a 2-day lift, not a 2-week one. The resolution instead rebuilds all six sub-decisions end-to-end, which is the multi-quarter scope.

### Does the over-build violate the thesis?

Yes, on two specific sub-decisions:

1. **Provider mode map as a bespoke capability table.** The thesis says "don't add a non-bottleneck dependency; find the right abstraction by using it, not on paper." Building a hand-maintained `PROVIDER_STRUCTURED_OUTPUT_CAPS` dict when Instructor's `DEPRECATED_TO_CORE` + `auto_client.py` already encode exactly this knowledge (and is kept current by a team of maintainers tracking provider changes) is over-engineering a non-bottleneck. This is the exact failure mode the thesis names: building what you can compose.

2. **The reask loop as a re-implementation of tenacity+handler.** Instructor's retry loop is 160 lines of well-tested tenacity glue. Building a second tenacity loop with the same semantics (`VersoRetryException` ≡ `InstructorRetryException`, `FailedAttempt` ≡ `FailedAttempt`, `total_usage` sum ≡ `update_total_usage`) is not the simplest thing that works. The specific addition Verso adds (Guardrails `OnFailAction` dispatch as a pre-reask policy) is the novel piece; it should be built on top of the existing loop, not alongside it.

**What is correctly built (survives the thesis test):**
- The jsonish waterfall proper (~500 lines): cannot be composed from anything that exists. The SAP fixing parser, markdown fence preference algorithm, grep-embedded-JSON stage, and `CompletionState` streaming support are genuinely absent from every existing library.
- The typed Flag cost function / two-phase coercion / `pick_best`: unique to BAML, not in Instructor, not in any Python library. Must be built.
- Pydantic v2 as the schema substrate: correct. TypedDict and dataclass alternatives are genuinely weaker for Verso's needs (no `model_construct`, no `validation_context`, no `model_json_schema`). The hard-dep is justified.

---

## Does It Break the Decision?

**Partially.** The core thesis of the structured-output subsystem — build the jsonish waterfall + coercion layer, use SAP as the primary path, Pydantic v2 as substrate — **survives**. The waterfall and coercion layer are genuinely unbuildable from existing libraries at the required quality. The benchmark evidence for SAP is valid even if the specific comparator (FC vs TOOLS) was imprecise, because the accuracy gap on MD_JSON paths (where the model generates prose containing JSON) is real and the waterfall handles pathologies that no existing library's fence-extraction handles.

**Two sub-decisions do not survive:**

1. The bespoke provider mode map should be deferred or composed from Instructor's `DEPRECATED_TO_CORE` rather than maintained by a solo builder.
2. The reask loop should compose from Instructor's tenacity loop (adapted to strip the openai hard-dep, which is a 2-day lift) rather than be rebuilt in full.

The overall decision as stated — "build the jsonish 5-stage SAP repair parser as the DEFAULT structured-output path" — **survives**, because the parser itself is the right call. But the scope of what is called "the structured-output decision" is inflated by ~30% with replication of well-maintained infrastructure.

---

## Evidence Checked

- `03_teardowns/structured-output.md` §BAML: BAML benchmark numbers read verbatim. Confirmed comparison is against `function_call` API (deprecated), not forced `tool_choice`.
- Instructor `processing/function_calls.py:728-754` (`parse_tools`): TOOLS mode calls `model_validate_json(tool_call.function.arguments)` directly — no fence extraction, no repair. Provider already extracted the JSON.
- Instructor `utils/core.py:43-65` (`extract_json_from_codeblock`): confirmed as naive first-`{`-to-last-`}` sweep + `json.loads`. Zero repair capability.
- Instructor `METADATA` (v1.15.1): confirmed `openai>=2.0.0` is a hard non-optional dep — blocks naive composition.
- Instructor `core/retry.py:87-244`: reask loop confirmed structurally identical to `parse_with_reask` in the resolution spec.
- Instructor `dsl/partial.py:522-633` + `dsl/json_tracker.py:57-96`: `Partial[T]` and sibling completeness heuristic confirmed as identical in design to the resolution's `Partial[T]`.
- `06_design_resolutions/structured-output.md` Decision 3: `PROVIDER_STRUCTURED_OUTPUT_CAPS` dict confirmed as hand-maintained capability table equivalent to Instructor's `DEPRECATED_TO_CORE`.
- `research/THESIS_VERIFICATION.md`: "keep it simple as the default" and "don't add a non-bottleneck dependency" confirmed as verified thesis.

---

## Recommendation

**Verdict: REVISE — not REJECT.**

Keep:
- The jsonish 5-stage waterfall (build it; cannot be composed).
- The typed Flag cost function / two-phase coercion / `pick_best` (build it; unique to BAML, not available elsewhere).
- Pydantic v2 as schema substrate (dependency is justified by `model_construct` + `validation_context` + `model_json_schema`).

Revise:
1. **Correct the benchmark framing.** The decision should say "SAP beats MD_JSON prose-extraction paths; for forced-TOOLS-mode providers the accuracy gap is narrower and the primary benefit is handling yapping, stream truncation, and unquoted keys in tool argument text." Do not cite the 19.8% FC number as evidence that SAP beats modern forced-tool-call.
2. **Compose the reask loop from Instructor's source.** Lift `core/retry.py` + the mode-to-reask-handler dispatch (stripping the `openai` import surface — 1-2 day lift). Verso adds `OnFailAction` dispatch on top, not alongside. This eliminates ~200 lines of duplicated tenacity glue.
3. **Use Instructor's `DEPRECATED_TO_CORE` table as the source of truth for the provider mode map**, not a hand-maintained `PROVIDER_STRUCTURED_OUTPUT_CAPS` dict. Vendor changes to provider capability are tracked by the Instructor maintainers; a solo builder should not own this table.
4. **For streaming partial:** lift from `dsl/partial.py` + `dsl/json_tracker.py` directly (60-80 relevant lines, Apache-2 license). Do not reimplement identically.

These revisions bring the implementation scope down from 6 independent subsystems to 3 (waterfall, coercion, OnFailAction) while keeping the novel architectural choices. The result is closer to the thesis: simplest thing that works, no non-bottleneck dependencies built when composable.
