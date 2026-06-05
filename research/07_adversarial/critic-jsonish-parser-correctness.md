# Adversarial Critique — jsonish-parser / CORRECTNESS lens
**Decision under review:** Build a BAML-style jsonish 5-stage SAP repair parser as the DEFAULT structured-output path (SAP over native function-calling), Pydantic v2 hard dependency, constrained decoding opt-in.
**Lens:** CORRECTNESS — does the cited RE evidence actually prove this works for Verso's exact case?
**Verdict:** REVISE
**Severity:** medium
**Date:** 2026-06-05

---

## The Attack

The resolution rests on two evidence pillars:
1. BAML source code (`entry.rs`, `score.rs`, `array_helper.rs`, `coerce_class.rs`) proves the waterfall and cost function work.
2. SAP benchmark numbers (gpt-4o-mini: 92.4% SAP vs 19.8% FC; claude-3-5-sonnet: 94.4% vs 78.1%) prove SAP beats native function-calling.

Both pillars have a correctness gap that the resolution does not acknowledge.

### Gap 1: The coercer is not portable — it requires BAML's compiled symbol table (KNOWN, verified in source)

The resolution says Verso "implements the BAML jsonish 5-stage SAP repair parser verbatim." The 5-stage waterfall (`entry.rs:15-238`) is portable — it is a pure text parser that produces a `Value` enum. The resolution is correct about this half.

But the cost-function coercer — the part that does schema-aware edit-distance ranking and produces a typed, validated output — is NOT portable as described. Verified in source:

- `coerce_class.rs` calls `ctx.of.find_class(mode, name)` and `ctx.of.find_enum(name)` (`ir_ref/mod.rs:27-36`).
- `ctx.of` is an `OutputFormatContent` object (`jinja-runtime/src/output_format/types.rs:93-94`) holding `Arc<IndexMap<String, Enum>>` and `Arc<IndexMap<(String, StreamingMode), Class>>` — a compiled symbol table built by BAML's own Rust toolchain from `.baml` DSL files.
- `TypeCoercer` is implemented on `TypeIR` (`field_type.rs:22`), which is `TypeGeneric<T>` — a BAML-internal enum with variants like `Class { name, mode, dynamic, meta }`, `RecursiveTypeAlias { name, mode, meta }`, `Tuple`, `Arrow`, `Top` — none of which exist in Pydantic's type system.
- `ParsingContext` carries `do_not_use_mode: baml_types::StreamingMode` (a BAML-specific streaming mode enum) and the `of: &OutputFormatContent` symbol table.

**What this means for Verso's port:** To use the BAML coercer's schema-guided logic against a Pydantic v2 model, Verso must build an equivalent of `OutputFormatContent` from Pydantic's `model_json_schema()` output and `model_fields`. This is a real translation layer:
- Pydantic `$defs` / `$ref` must be resolved into a flat class map.
- Pydantic `Union` / `Optional` / `Literal` / `Annotated` types must map to BAML's `TypeIR::Union`, `TypeIR::Literal`, etc.
- BAML's `StreamingMode` and `@@stream.done` annotations have no Pydantic equivalent and must be inferred or omitted.
- Recursive types (Pydantic models with `model_rebuild()` cycles) require the same `(class_name, value)` visited-set logic, but the lookup is against Python `type` objects, not BAML name strings.

The resolution says "port the five stages; the `ParsingMode` re-entry guard and `depth>100` are non-optional correctness details" — this is accurate for the parser half but omits the equally non-trivial coercer translation. The component spec for `verso/tools/coerce.py` shows `coerce_to_model(value: JsonishValue, model: type[BaseModel])` — but this function does not exist in BAML; Verso would be writing it from scratch using BAML's algorithm as a template, not porting it verbatim. The resolution over-claims the portability.

**Severity of gap:** This is a real implementation risk, not a design flaw. The algorithm is correct; the complexity of the Pydantic-to-TypeIR bridge is real but bounded. A Pydantic `model_json_schema()` dict contains enough information to reconstruct the TypeIR variant map. But the resolution's claim that this is a "verbatim" port is false, and the Open Unknown section does not flag this translation as a risk. It flags only the off-by-one porting trap in `should_close_unescaped_string` — the coercer translation is harder.

### Gap 2: The SAP benchmark proves BAML-SAP beats function-calling, not "SAP" generically

The resolution states: "BAML Berkeley Function Calling Leaderboard shows SAP strictly beats native function-calling across every model tested (gpt-4o-mini: 92.4% SAP vs 19.8% FC)."

**What the benchmark actually proves:** The BAML blog benchmark tests BAML's own SAP implementation (Rust, TypeIR-native) against function-calling. The "SAP" in the benchmark is the complete BAML pipeline: BAML-compiled schema → BAML jsonish waterfall → BAML TypeIR coercer. It is not a test of "any Python port of the waterfall and cost function." Verso's port — which must bridge Pydantic → JSON Schema → reconstructed TypeIR-equivalent — is a different implementation. The accuracy claim transfers only insofar as the Pydantic bridge faithfully reconstructs the coercer behavior.

The gap is specifically on cases where the Pydantic bridge diverges from BAML TypeIR semantics:
- **Union discrimination:** BAML TypeIR has tagged unions with explicit variant indices and `union_variant_hint` optimization. Pydantic `Union[A, B]` with discriminators uses a different resolution path. A misimplemented bridge could break the variant-hint optimization or produce different pick-best outcomes.
- **Enum/Literal handling:** BAML's `coerce_enum.rs` matches against the BAML-compiled enum's `value_list` (name + aliases). Pydantic `Literal['foo', 'bar']` exposes these via `model_json_schema()["enum"]` — straightforward to bridge, but the 4-tier match cascade (`match_string.rs:39-130`) must operate against those values, not against BAML-compiled aliases.
- **`DefaultFromNoValue=100` and required fields:** BAML marks a field as required via TypeIR field metadata. Pydantic required fields are detectable via `model_fields[name].is_required()`. The mapping exists, but a wrong bridge (e.g., treating `Optional[X]` fields as required) would shift penalty scores by 99 points per field.

The benchmark accuracy numbers are not transferable as hard guarantees to the Python port. They are the best available signal for what the algorithm achieves, but the resolution presents them as if they prove the Python port will perform equivalently.

**Severity of gap:** Medium. The accuracy numbers correctly establish SAP is the right algorithm. The issue is the resolution cites them as proof of the Python port's accuracy rather than as evidence for the algorithm's effectiveness. The actual Python port accuracy is unknown until calibrated against real provider output.

### Gap 3: Decision 3 mis-counts the canonical modes (minor, verified)

The resolution states the `DEPRECATED_TO_CORE` map "collapses 40+ modes onto 5 canonical ones — `TOOLS`, `PARALLEL_TOOLS`, `JSON`, `JSON_SCHEMA`, `MD_JSON`."

Verified in `/tmp/instructor-check/instructor/v2/core/mode.py:203-250`: `DEPRECATED_TO_CORE` actually includes `RESPONSES_TOOLS` as a canonical target (line 208: `Mode.RESPONSES_TOOLS_WITH_INBUILT_TOOLS: Mode.RESPONSES_TOOLS`). The Verso component spec (`CanonicalMode` enum) defines exactly 5 values and omits `RESPONSES_TOOLS`. This is a minor accuracy error: the map collapses to 6 targets, not 5, and the omitted one (`RESPONSES_TOOLS` — the OpenAI Responses API) is a real production path that Verso's provider table will need eventually. Not a blocking correctness issue for v1 (the Responses API is newer and lower priority), but the claim "5 canonical modes" is technically wrong per the source.

### What Does NOT Break

The following claims are verified correct against source and survive adversarial review:

- The 5-stage waterfall logic (`entry.rs:15-238`): verified. The stages, the `ParsingMode` re-entry guard, and the `depth>100` guard are all accurate.
- The penalty table (`score.rs:34-77`): verified verbatim. All values match exactly.
- The ×10 child multiplier (`score.rs:20-27`): verified at lines 21 and 26-27 (`s.score() + 10 * items.iter().map(...).sum::<i32>()`).
- The `DefaultFromNoValue=100` and `DefaultButHadValue=110` cliffs: verified at `score.rs:39,40`.
- `pick_best` semantic tie-breaks (`array_helper.rs:29-314`): verified. The exact tie-break sequence (SingleToArray → markdown string → ArrayItemParseError → all-default class → ImpliedKey string-in-union → JsonToString cast) is accurately described.
- Instructor `function_calls.py:91-110` as the seam for jsonish plug-in: verified. The `_validate_model_from_json` function at those exact lines is where `json.loads` precedes `model_validate`.
- `DEPRECATED_TO_CORE` collapsing provider modes to canonical ones: verified. The pattern is correct; the count is off by 1.
- SAP benchmark numbers (92.4%, 19.8%, 94.4%, 78.1%): verified against the BAML SAP blog (n=1000 per model, Berkeley Function Calling Leaderboard dataset, cited correctly).
- Reask loop (`retry.py:87-244`, `handlers.py:119-268`): not re-cloned in detail but the teardown file:line citations are consistent with the v2 structure confirmed by the clone.

---

## Does It Break the Decision?

**No, it does not break the core decision.** SAP over native function-calling as the default path is the right architecture for Verso. The algorithm is proven correct in source. The waterfall is portable. The cost function is the correct semantic distance measure. The reask loop and mode map from Instructor are accurately described.

The attack lands on **scope and honesty of the evidence claims**, not on the correctness of the design:

1. The "verbatim port" claim is overstated. The waterfall is verbatim-portable; the coercer requires a non-trivial Pydantic-to-TypeIR bridge that is not acknowledged in the Open Unknowns section.
2. The benchmark numbers prove the algorithm's accuracy, not the Python port's accuracy. The distinction matters for calibration planning.
3. The canonical-mode count is off by 1 (6 not 5), and `RESPONSES_TOOLS` is omitted from the provider table.

None of these break the decision. They are implementation risks that the Open Unknowns section should be extended to include.

---

## Evidence Checked

| Claim | File Checked | Verdict |
|---|---|---|
| `entry.rs:15-238` waterfall stages | `/tmp/baml-check/engine/baml-lib/jsonish/src/jsonish/parser/entry.rs` (full read) | CORRECT |
| `score.rs:34-77` penalty table | `/tmp/baml-check/engine/baml-lib/jsonish/src/deserializer/score.rs` (full read) | CORRECT |
| ×10 child multiplier `score.rs:20-27` | Same file, lines 20-27 | CORRECT |
| `array_helper.rs:29-314` pick_best | `/tmp/baml-check/engine/baml-lib/jsonish/src/deserializer/coercer/array_helper.rs` (full read) | CORRECT |
| Coercer uses BAML-specific TypeIR / OutputFormatContent | `coercer/ir_ref/mod.rs`, `coercer/field_type.rs`, `jinja-runtime/src/output_format/types.rs` | CONFIRMED — portability over-claimed |
| TypeIR is BAML-specific, not JSON Schema | `baml-types/src/ir_type/mod.rs` | CONFIRMED |
| Instructor `function_calls.py:91-110` | `/tmp/instructor-check/instructor/v2/core/function_calls.py` | CORRECT (exact lines, `_validate_model_from_json`) |
| DEPRECATED_TO_CORE: 5 canonical modes | `/tmp/instructor-check/instructor/v2/core/mode.py:203-250` | OFF BY 1 — 6 targets including RESPONSES_TOOLS |
| SAP benchmark numbers | BAML SAP blog (WebFetch verified) | CORRECT — but test is BAML-native, not generic-SAP |

---

## Recommendation

**REVISE — do not reject, do not defer.** The core decision is correct and should be kept. Three targeted additions are needed:

1. **Add Open Unknown #8: Pydantic-to-TypeIR bridge.** The coercer port from BAML TypeIR to Pydantic v2 models requires building a `OutputFormatContent`-equivalent from `model_json_schema()` + `model_fields`. Concretely: resolve `$defs`/`$ref` chains, map Pydantic `Union`/`Optional`/`Literal`/`Annotated` to TypeIR-equivalent structures, handle `model_rebuild()` recursive cycles via the same visited-set logic but keyed on Python `type` objects. This is bounded and solvable but is the highest-risk porting step — more so than the off-by-one in `should_close_unescaped_string` already flagged in Open Unknown #1. It should be the first thing exercised in Phase 0 dogfooding.

2. **Qualify the accuracy claim.** Change "BAML Berkeley Function Calling Leaderboard shows SAP strictly beats native function-calling" to "BAML's implementation of SAP beats native function-calling; Verso's Python port is expected to achieve similar accuracy once the Pydantic bridge is correctly implemented, but needs calibration against actual provider output before claiming the same numbers." The numbers establish the algorithm is right; they do not prove the port.

3. **Add `RESPONSES_TOOLS` to Decision 3's canonical mode table** as a 6th entry, or explicitly note it is deferred for v1. The current "5 canonical modes" claim is technically incorrect per the source.

None of these require changing the architecture. They require making the Open Unknowns section honest about where the implementation work lies.
