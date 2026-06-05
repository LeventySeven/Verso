# Structured Output + @tool Schema — Verso Design Resolution

**Subsystem:** `tools/` schema-gen + `model/` structured-output parse/repair pipeline
**PRD refs:** §5.3 (Tools), §5.1 (loop dispatch), §10 item 2 (schema substrate)
**Teardown source:** `03_teardowns/structured-output.md` (BAML/jsonish, Instructor, Outlines/outlines-core, XGrammar, llguidance, Mirascope, Guardrails AI — all git clone --depth=1, 2026-06-05)
**Date:** 2026-06-05

---

## Decisions Resolved

### Decision 1 — SAP vs Constrained Decoding: the universal fallback path

**Choice:** SAP (Schema-Aligned Parsing) via the jsonish waterfall is the default and universal fallback. Constrained decoding is an opt-in fast-path on local engines only, never a mandatory requirement.

**Rationale:**
Verso does not own inference. That single constraint settles the argument. Constrained decoding (Outlines/XGrammar/llguidance) requires either direct access to the logits layer or a local engine that exposes grammar backends — neither is available when calling Anthropic/OpenAI/Gemini over HTTP. SAP works on every provider because it operates post-hoc on the completion text. The accuracy data makes SAP the right default even where constrained decoding is available: BAML Berkeley Function Calling Leaderboard shows SAP strictly beats native function-calling across every model tested (gpt-4o-mini: 92.4% SAP vs 19.8% FC; claude-3-5-sonnet: 94.4% vs 78.1%), with the gap largest on the cheap/small models Verso will route to most. The reason: constrained decoding enforces syntactic legality but cannot fix a model that produced the *wrong value* — it perturbs the sampling distribution and the coalescence tradeoff (Outlines blog: "risks degrading output quality if the wrong token path is selected") makes it an inferior *semantic* guarantee even at full syntax correctness. SAP lets the model reason freely and repairs the output; CD forces the syntax and hopes the semantics follow.

**Constrained decoding remains opt-in** on local engines (SGLang/vLLM/llama.cpp/Ollama) because there are real cases where it wins: a stable, frequently-reused schema generated at length (amortizes the eager Index build), token-budget-sensitive loops where even occasional reask round-trips are expensive, and structured spans that are trivially short (dates, enums, booleans) where distortion is irrelevant. Expose it as `StructuredOutputConfig(constrained_decoding=True)` on the model edge — never auto-enable.

**Evidence:** BAML `engine/baml-lib/jsonish/src/jsonish/parser/entry.rs:15-238` (the waterfall); `score.rs:34-77` (the flag cost function); BAML SAP blog benchmarks (KNOWN); XGrammar arXiv:2411.15100 §2 (constrained decoding mechanics and the context-dependent cost); Outlines `coalescence` blog (distribution distortion caveat). Cross-ref: `infra-serving.md` (vLLM/SGLang grammar backends — what the engine does with a schema).

**Alternatives rejected:**
- *"Use constrained decoding as default, SAP as repair"* — rejected because the universal fallback must work on hosted providers. A Verso agent that only produces valid output when pointed at a local engine is not a Verso agent.
- *"Always do two passes: CD if available, SAP if not"* — rejected as over-engineering. The SAP accuracy numbers mean there is no accuracy loss from using SAP-only; the cost of CD is a non-zero rewrite surface and per-provider feature detection logic with no accuracy payoff.

---

### Decision 2 — Schema Substrate: Pydantic v2 vs TypedDict

**Choice:** Pydantic v2 is the schema substrate for Verso's structured outputs (`@tool` return annotations, agent output types, memory entry types). `TypedDict` is supported as a schema *source* (via `get_type_hints` + manual field-walk) but not as the primary runtime validation layer. Pydantic v1/v2 dual-support is explicitly forbidden in the codebase.

**Rationale:**
PRD §10 item 2 locks "Pydantic v2 optional, never v1/v2 dual." This resolution operationalizes that. The reasons are concrete:
1. Pydantic v2's `model_json_schema()` is the best-in-class Python-type-to-JSON-schema compiler in the ecosystem. It handles `Optional`, `Union`, `Literal`, `Annotated`, `constr`/`conint` constraints, `$defs` for recursive types, and `additionalProperties:false` injection — all needed for the format-tool path and for OpenAI strict mode.
2. `model_validate()` / `model_validate_json()` with `strict=False` is the clean seam where jsonish-repaired JSON enters the schema world — the teardown documents this as the explicit plug point: "instead of `json.loads`, run the jsonish repair waterfall, then `model_validate`" (`structured-output.md` Instructor section, `function_calls.py:91-110`).
3. `model_construct()` (skip validation, store raw partial values) is essential for the construct-not-validate streaming path — there is no TypedDict equivalent.
4. The `validation_context` passthrough (`model_validate(data, context=ctx)`) lets `@field_validator`s see request-scoped data (user limits, allowed values) without globals. TypedDict has no equivalent.

`TypedDict` annotations on `@tool` functions ARE supported because they are a natural Python typing idiom. The schema-gen layer uses `typing.get_type_hints()` + `typing.get_origin()`/`get_args()` to walk the TypedDict structure and produce a JSON schema fragment — but this path produces a schema *for the LLM to consume*, not a Pydantic model for Verso to validate with. If a user wants Verso-side validation of a TypedDict return, they can opt into `response_model=MyModel` explicitly; the framework never silently bypasses validation.

Docstring enforcement: every type that crosses the LLM boundary (tool parameter models, output types) MUST have a non-empty docstring — enforced at registration time with a `ValueError`. This is copied from Atomic Agents `BaseIOSchema._validate_description()` (`base/base_io_schema.py:22`) and is a cheap, high-value LLM-contract discipline (the docstring becomes the schema `description`).

**Evidence:** Instructor `function_calls.py:91-110` (strict/loose validate fork + `validation_context` passthrough, KNOWN); Mirascope `formatting/format.py:96-139` (`additionalProperties:false` + all-required rewrite for format-tool, KNOWN); Atomic Agents `base/base_io_schema.py:22-33` (docstring enforcement + `model_json_schema` injection, KNOWN); PRD §5.3 (`@tool` decorator, docstring + type hints → JSON schema); PRD §10 item 2.

**Alternatives rejected:**
- *"TypedDict-only, no Pydantic dependency"* — rejected because TypedDict lacks `model_construct()`, `validation_context`, and runtime `model_validate()`. Pydantic v2 is a zero-friction dependency (it is already in virtually every Python AI project).
- *"Accept both v1 and v2 at runtime"* — explicitly banned by PRD §10 item 2. The v1/v2 dual-support bug farm (LangChain's original sin, per PRD §1) is a non-starter.
- *"dataclass-only"* — dataclasses lack JSON schema generation, `model_construct`, and `validation_context`. They appear in the tool-param annotation walk but are not the validation runtime.

---

### Decision 3 — Instructor Per-Provider Mode Map: what to request per provider

**Choice:** Verso uses 3 semantic format intents (`strict`, `tool`, `json`) exposed to the caller, with each provider edge owning the wire-format fallback ladder. Internally, 5 canonical modes (`TOOLS`, `PARALLEL_TOOLS`, `JSON_SCHEMA`, `JSON`, `MD_JSON`) map to the 40+ Instructor provider-specific modes via a per-provider capability table baked into the adapter, not runtime-probed.

The default fallback ladder per provider (when the caller does not pin a format):
1. Try `strict` (`JSON_SCHEMA` with `strict:true` + `additionalProperties:false`) — only if the provider supports it (OpenAI, some Gemini models).
2. Fall back to `tool` (forced single tool call, `TOOLS` mode with `tool_choice={"type":"function","function":{"name":...}}`) — the most reliable extraction on providers with tool-calling.
3. Fall back to `json` (`MD_JSON` — dump schema into the system prompt, ask for a ```` ```json ```` fence, parse with jsonish stage 2) — the universal lowest-common-denominator path.

The provider capability table (from Instructor `v2/core/mode.py:10-127` + `DEPRECATED_TO_CORE`, KNOWN):
| Provider | Primary mode | Notes |
|---|---|---|
| OpenAI (o-series, gpt-4o+) | `JSON_SCHEMA` | strict=True + additionalProperties:false |
| OpenAI (gpt-3.5, older) | `TOOLS` | strict not supported |
| Anthropic | `ANTHROPIC_TOOLS` → maps to `TOOLS` | tool_choice forced |
| Google Gemini | `GEMINI_TOOLS` → `TOOLS` / `GEMINI_JSON` → `MD_JSON` | varies by model |
| Mistral | `MISTRAL_TOOLS` → `TOOLS` | |
| Cerebras/Fireworks/Writer/Bedrock/Perplexity | `MD_JSON` | no native structured outputs |
| Vertex AI | `VERTEXAI_TOOLS` → `TOOLS` | |

The `DEPRECATED_TO_CORE` map (Instructor `mode.py:203-250`) collapses 40+ modes onto these 5 canonical ones — Verso ships this table, never re-derives it. "The provider is determined by the client, not by the mode" (Instructor comment, verbatim): Verso's provider edge receives the canonical mode and shapes the wire request.

**Rationale:** Runtime feature probing (send a test request to check if a provider supports strict mode) is unacceptable in an agent loop — it adds latency to the first structured call and introduces failure modes when the probe itself fails. The capability table is stable on the 6-12 month horizon a Verso v1 dog-food session covers; providers announce breaking changes. Baking it into the adapter and exposing a clean 3-intent surface to the caller gives users a provider-agnostic API while letting the adapter evolve independently. Mirascope's `FormattingMode` (Literal["strict","json","tool"]) + "provider auto-selects" is the right caller surface; Instructor's per-provider capability map is the right internal implementation.

**Evidence:** Instructor `v2/core/mode.py:10-127`, `DEPRECATED_TO_CORE:203-250`, `v2/auto_client.py:25-108` (per-provider default mode, KNOWN); Mirascope `formatting/types.py:44-74` (`FormattingMode`, `FeatureNotSupportedError`, KNOWN); `structured-output.md` §Cross-System Synthesis "Mode surface = 3 intents".

**Alternatives rejected:**
- *"Expose the full 40-mode enum to callers"* — rejected because it leaks implementation detail about provider quirks into the caller's code, creating tight coupling to a specific SDK version.
- *"Runtime probe the provider on first call"* — rejected (latency + failure surface).
- *"Always use MD_JSON, it works everywhere"* — rejected because it is the lowest reliability tier (no enforcement), and providers with native strict structured outputs give materially better results.

---

### Decision 4 — The jsonish Waterfall as the Universal Post-hoc Parser

**Choice:** Verso implements the BAML jsonish 5-stage waterfall verbatim as its universal output parser. The waterfall is the only parser for all provider responses — no per-provider special-casing except what the mode selection already handles (mode determines where the JSON string is in the response, not how it is parsed once extracted).

The 5 stages (from `entry.rs:15-238`, KNOWN):
1. **Strict JSON** — `json.loads()` (Python equivalent); fast-path for well-formed responses.
2. **Markdown fence extraction** — regex scan for ` ```{lang} ` blocks; prefer first closing fence whose content sub-parses; do not merge across another opening fence.
3. **Grep-embedded-JSON** — find every balanced `{...}`/`[...]` substring in prose; handles "yapping" wrappers.
4. **Fixing parser** — character-level state machine that repairs: unquoted keys, trailing commas, single-quoted strings, triple-quoted/backtick strings, trailing comments, unterminated strings. First-stage-aware re-entry with `ParsingMode` guard and `depth>100` cycle kill.
5. **As-string** — last resort; the whole input becomes a string value.

The `ParseOptions` boolean gates (all default `true`) let any stage be disabled; the `ParsingMode` re-entry guard prevents recursive stage-reapplication. Stage 1 marks bare trailing numbers as `Incomplete` (they might still be growing in a stream); quoted strings as `Complete`. This is correct by construction — a half-parsed stream always yields something, and the completeness state propagates through the cost function.

The fixing parser's key repair invariants (reimplementation checklist):
- `StringQuoteTracking` (trailing-backslash count + unescaped-quote count) decides whether a `"` closes a string in O(1).
- `should_close_string`: close on structural token legal for current position, only when unescaped-quote count is even — prevents premature closure on interior quotes.
- `should_close_unescaped_string`: terminate bare words on the delimiter legal in grandparent context; handle `, ` comma-space by peeking for a following `"` or comment.
- EOF with open collections → force-close all with `CompletionState::Incomplete`. Return disambiguation: 0 values = error; 1 = return it; N all-strings = `Array`; N mixed = keep only Object/Array.

**Rationale:** The waterfall is provider-agnostic, handles all known LLM output pathologies (yapping, markdown fences, unquoted keys, trailing commas, single quotes, code block wrapping), and is the component with the best published accuracy data (SAP benchmark, above). Implementing it in Python (one module, ~500 lines, no C extension needed) is a Phase 0 deliverable since every structured tool call and every output type requires it. The `depth>100` guard and `ParsingMode` re-entry are correctness details that prevent infinite recursion on adversarial inputs — non-optional.

**Evidence:** `engine/baml-lib/jsonish/src/jsonish/parser/entry.rs:15-238` (waterfall, KNOWN); `parser/fixing_parser/json_parse_state.rs:26-764` (fixing parser state machine, KNOWN); `markdown_parser.rs:39-135` (fence algorithm, KNOWN); regression tests at `json_parse_state.rs:106-148,926-949` (the off-by-one correction for the final char).

**Alternatives rejected:**
- *"Use `json.loads` with a try/except fallback to `json5`"* — rejected because `json5` does not handle markdown fences, embedded-object grep, or stream-truncation with `Incomplete` state. The PRD §5.3 already specifies `json.loads → ast.literal_eval → json5 → repair_json` for the tool *input* repair ladder — that is tool-args repair, not output-schema parsing. Output parsing requires the completeness-aware waterfall.
- *"Per-provider output extractors"* — rejected because it multiplies surface area with each new provider. The waterfall subsumes all cases; the mode selection already handles the structural question of where to find the JSON.

---

### Decision 5 — SAP Cost Function: typed Flag edit-distance, not Levenshtein

**Choice:** Verso's schema-guided coercion uses the BAML Flag penalty table as the edit-cost function, not string-level Levenshtein. The coercer implements two-phase `try_exact → coerce_and_score`, picks the min-cost candidate via `pick_best` with the BAML semantic tie-breaks, and every edit operation records a typed `Flag`.

The penalty table (from `score.rs:34-77`, KNOWN — lower is better):
| Flag (coercion applied) | Penalty |
|---|---|
| `UnionMatch`, `ObjectFromFixedJson`, `InferredObject` | 0 (free) |
| `OptionalDefaultFromNoValue`, `ObjectToMap`, `SingleToArray`, `StringToBool/Null/Char/Float`, `FloatToInt`, `NoFields`, `FirstMatch` | 1 |
| `SubstringMatch`, `ImpliedKey`, `JsonToString`, `ObjectToString`, `ObjectToPrimitive`, `DefaultButHadUnparseableValue` | 2 |
| `StrippedNonAlphaNumeric` | 3 |
| `ArrayItemParseError(x, _)` | 1 + x (compounds per item) |
| `DefaultFromNoValue` | 100 (required field filled from nothing) |
| `DefaultButHadValue` | 110 (value existed but didn't fit, defaulted) |
| `ExtraKey` | 1 (strip yapping) |
| `Incomplete`, `Pending`, `ConstraintResults` | 0 (streaming state, not parse cost) |

Composite score: `List.score = list_flags + 10 × Σ item.score`; `Class.score = class_flags + 10 × Σ field.score`. The ×10 multiplier means a deeply-nested required-field default dominates everything else — this is the "type-aware edit distance" claim: schema structure determines the magnitude, not just the count of edits.

`pick_best` semantic tie-breaks (from `coercer/array_helper.rs:29-314`, KNOWN, applied before pure score):
1. Prefer a non-`SingleToArray` list over a coerced one.
2. Prefer a list with fewer raw-markdown-string items.
3. Prefer fewer `ArrayItemParseError`s.
4. On a union: devalue a class that is just one `ImpliedKey`'d string.
5. Devalue a class whose every field is a default.
6. Devalue a primitive string cast from a composite (`JsonToString`).
7. Final comparator: `(is_default_empty, score, index)` — stable tie-break on original candidate order.

Two-phase coercion:
- `try_exact(ctx, target, value)` — zero-cost exact attempt; for a union, short-circuit the moment one variant scores 0; carry a `union_variant_hint` (index of the last-matched variant) across array elements to try the likely variant first.
- `coerce_and_score(ctx, target, value)` — lossy flagged fallback when no exact fit exists; records every edit as a `Flag`; runs `pick_best` across all candidates.

Enum / literal matching cascade (4-tier, from `match_string.rs:39-130`, KNOWN):
1. Exact match (case-sensitive, ignore punctuation). Cost: 0.
2. Strip punctuation from both sides, retry. Cost: 0.
3. Lowercase + strip, retry. Cost: 1 (`StrippedNonAlphaNumeric`-class).
4. Substring match (gated `allow_substring_match`). Cost: 2 (`SubstringMatch`).

Cycle safety: `(class_name, value)` visited sets prevent infinite recursion on recursive schemas (`type A = A[]`). `scope` stack gives every parse error a dotted field path (`"outer.inner.field"`).

**Rationale:** Levenshtein measures how many characters differ between two strings. The cost function Verso needs measures how much semantic schema-violation occurred. A `DefaultButHadValue=110` deep in a nested class should dominate a `SingleToArray=1` at the root — raw string distance cannot express this. The BAML table has 4 years of production validation across a wide model surface; the specific cliffs (100/110 for required-field defaulting) are calibrated against real model outputs, not arbitrary constants. Adopting it verbatim (rather than designing a custom table) eliminates a design-by-guessing step.

**Evidence:** `score.rs:34-77` (exact penalty table, KNOWN); `score.rs:20-27` (×10 child multiplier, KNOWN); `coercer/array_helper.rs:29-314` (`pick_best` comparator, KNOWN); `match_string.rs:39-130` (enum cascade, KNOWN); `coercer/mod.rs:303-317` (two-phase contract, KNOWN).

---

### Decision 6 — Reask Loop: feed `str(ValidationError)` back, framed per mode, with per-attempt usage accounting

**Choice:** Verso's reask loop is a tenacity-style `stop_after_attempt(max_retries) | stop_after_delay(timeout)` that retries **only on `pydantic.ValidationError`** (not transport errors). Per attempt: call model → parse via jsonish waterfall → `model_validate` → on success return; on `ValidationError`, mutate the message list with the error framed per mode, accumulate usage, then retry.

Reask framing per mode (from Instructor `handlers.py:119-268`, KNOWN):
- **TOOLS mode:** append the assistant message with its `tool_calls`, then for each tool_call append a `role:"tool"` message with `tool_call_id`, `name`, and `f"Validation Error found:\n{exception}\nRecall the function correctly, fix the errors"`. This preserves a valid tool-call/tool-result transcript for the next turn.
- **JSON / MD_JSON modes:** append assistant message + a `role:"user"` message `"Correct your JSON ONLY RESPONSE, based on the following errors:\n{exception}"`.
- **Streaming responses:** single user message with the error (can't replay tool_calls mid-stream).

On exhaustion, raise `VersoRetryException` carrying:
```python
last_completion: ProviderResponse
n_attempts: int
total_usage: UsageStats          # summed across ALL attempts (critical for token-budget accounting)
messages: list[Message]          # full message list at exhaustion
create_kwargs: dict
failed_attempts: list[FailedAttempt(attempt_number, exception, completion)]
```

The `total_usage` sum across attempts is non-negotiable: the parent loop's token-budget accounting MUST see the full reask cost, not just the final attempt. The `failed_attempts` list is the per-attempt observability surface for debugging why a structured turn took 3 round-trips.

Reask vs FIX: Verso integrates the Guardrails `OnFailAction` policy alongside the Instructor reask loop. Validation failures first route through the policy:
- `FIX` — apply `fix_value` from the validator, no LLM call. Cheap local correction for known-fixable patterns (strip extra whitespace, normalize enum casing).
- `FIX_REASK` — apply `fix_value`, re-validate; only reask if the fix fails.
- `REASK` — escalate to a model round-trip with structured failure context: `FieldReAsk(incorrectValue=<what the model produced>, failResults=[<typed fail result with error_message + error_spans>])`. This is richer than `str(exception)` alone — it shows the model exactly what it produced and why each part failed.
- Default: `EXCEPTION`.

**Rationale:** Most structured-output failures are recoverable without a model round-trip. The Guardrails `OnFailAction` ordering (FIX → FIX_REASK → REASK → EXCEPTION) means only genuine validation failures that cannot be locally corrected burn a reask call. This is the "reask is the expensive last resort" principle from the teardown synthesis. The per-attempt usage sum is critical because a 3-reask turn uses 3× the tokens of a single turn; if the parent loop's token-budget accounting only sees the final attempt it will undercount by 2×.

**Evidence:** Instructor `retry.py:87-244` (tenacity loop, ValidationError-only retry, per-attempt `FailedAttempt`, usage sum via `update_total_usage`, KNOWN); `handlers.py:119-268` (reask message framing per mode, KNOWN); Guardrails `on_fail.py:24-31` + `validator_service_base.py:73-117` (`OnFailAction` dispatch, FIX/FIX_REASK/REASK/EXCEPTION, KNOWN).

---

### Decision 7 — Streaming Partial Typed Objects: construct-not-validate

**Choice:** Verso's streaming partial-object path uses `model_construct()` (skip validation) until the root JSON object is structurally closed, then a final `model_validate()`. All fields are made optional via a memoized `Partial[T]` rewrite. Per-chunk parsing uses `jiter` with `partial_mode="trailing-strings"` (keeps unterminated strings as partial content rather than dropping them).

The `Partial[T]` construction (from Instructor `v2/dsl/partial.py:522-633`, KNOWN):
- `Partial[Model]` is created once via `__class_getitem__`, walks the model's `model_fields`, and for each wraps the annotation as `Optional[Partial[annotation]]` — every field becomes optional and recursively partial. The resulting class stores `partial_model._original_model = wrapped_class`.
- The partial-model rewrite is **memoized per wrapped class** (`_partial_model_cache` in Mirascope `partial.py:19,92-93,129`, KNOWN) — the optional-field transform is pure; never recompute per stream chunk.

Per-chunk processing:
1. Accumulate `potential_object` string across chunks (after stripping control chars).
2. `parsed = jiter.from_json(json_str.encode(), partial_mode="trailing-strings")` — partial Rust parser; unterminated strings kept as their partial content.
3. Determine `is_root_closed`: strict `jiter.from_json` succeeds → root is structurally closed; else partial.
4. **If root closed and has data → `original_model.model_validate(parsed)`** (full validation with Pydantic). **Else → `Partial[T].model_construct(**parsed)`** (skip validation, store raw values).
5. Nested complete sub-objects are validated even mid-stream; incomplete ones constructed.
6. Yield the object each chunk — consumer sees a progressively-filled instance.

**Sibling completeness heuristic** (from Instructor `json_tracker.py:57-96`, KNOWN): if a value has a next sibling key in the parsed partial, it is provably complete (jiter had to finish parsing it to discover the next sibling). Only the last value at each level is of unknown completeness. This gives per-field streaming completeness without a custom parser, derived from any partial JSON parser that preserves order.

Type-driven emission (from BAML `semantic_streaming.rs:34-52`, KNOWN): scalars (`Int`, `Float`, `Bool`, enums) are always `done` (a half-streamed number is never emitted). Strings/lists/objects are streamable. A "needed" field (the BAML `@stream.not_null` equivalent) withholds the object until that field arrives.

**Rationale:** Naive per-chunk `model_validate()` fails on required fields (they're absent mid-stream). `model_construct()` is the correct bypass for partial objects. The jiter `trailing-strings` mode is the only way to get partial content of a streaming string (vs dropping it entirely). The memoized partial-model rewrite is a one-time cost that should never be paid per chunk. BAML's type-driven done/needed annotations add a valuable emission-control layer: a half-streamed number would confuse UI consumers; marking scalars as `done` means they never appear until complete.

**Evidence:** Instructor `v2/dsl/partial.py:376-408` (construct-not-validate path, KNOWN); `json_tracker.py:57-96` (sibling completeness heuristic, KNOWN); Mirascope `formatting/partial.py:19,92-93` (partial-model cache, KNOWN); BAML `semantic_streaming.rs:34-52` (type-driven done/needed, KNOWN); BAML `streaming.rs:7-213` (Partial[T] compiler from TypeIR, KNOWN).

---

### Decision 8 — @tool Schema Generation: type-hints → JSON Schema

**Choice:** `@tool` schema generation uses Python's `inspect` + `typing.get_type_hints()` → JSON Schema, with Pydantic v2 `TypeAdapter` for complex types. The generated schema is the authoritative representation passed to the provider. Schema generation is synchronous and memoized per function.

Schema generation algorithm (adapted from the ecosystem — Instructor `generate_openai_schema`, Mirascope `format.py:96-139`, Atomic Agents `BaseIOSchema`, KNOWN):

```python
def tool_to_json_schema(fn: Callable) -> dict:
    hints = get_type_hints(fn, include_extras=True)  # includes Annotated
    sig = inspect.signature(fn)
    # exclude ctx (RunContext) — injected, never LLM-visible
    params = {k: v for k, v in sig.parameters.items()
              if k != "ctx" and k != "return"}
    properties = {}
    required = []
    for name, param in params.items():
        annotation = hints.get(name, Any)
        field_schema = _annotation_to_json_schema(annotation)  # TypeAdapter(annotation).json_schema()
        # docstring of param via Annotated[T, Doc(...)] or parsed from fn.__doc__
        if doc := _get_param_doc(fn, name):
            field_schema["description"] = doc
        properties[name] = field_schema
        if param.default is inspect.Parameter.empty:
            required.append(name)
    return {
        "name": fn.__name__,
        "description": fn.__doc__ or "",   # enforced non-empty at registration
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,  # OpenAI strict mode requires this
        }
    }
```

Key invariants:
1. `ctx` / `RunContext` parameters are always excluded from the emitted schema — they are injected by the framework, never visible to the LLM.
2. Every `@tool` docstring is **enforced non-empty at registration time** with a `ValueError` (copied from Atomic Agents `BaseIOSchema._validate_description()`, `base_io_schema.py:22`). The docstring becomes the schema `description` — missing docstrings silently degrade LLM tool selection.
3. `additionalProperties: False` is always injected. Required for OpenAI strict function calling and for the format-tool path.
4. `Annotated[T, Doc("description")]` is the first-class per-parameter documentation path — `get_type_hints(include_extras=True)` picks it up without a custom decorator.
5. Complex return types (for output schema) use `TypeAdapter(return_annotation).json_schema()` + `$defs` flattening.

The schema is **cached per function object** (keyed by `id(fn)`) — schema generation is pure and should not run on every agent loop iteration.

For the **format-tool** (forced-tool-call extraction of a structured output type `T`):
```python
FORMAT_TOOL_NAME = "_verso_format_output"
def make_format_tool_schema(model: type[BaseModel]) -> dict:
    schema = model.model_json_schema()
    return {
        "name": FORMAT_TOOL_NAME,
        "description": f"Use this tool to return a structured response as {model.__name__}.",
        "parameters": {
            **schema,
            "required": list(schema.get("properties", {}).keys()),  # ALL fields required
            "additionalProperties": False,
        }
    }
```

**Evidence:** Mirascope `format.py:96-139` (universal format tool, `required=list(properties.keys())`, KNOWN); Atomic Agents `base_io_schema.py:22-33` (docstring enforcement + `model_json_schema`, KNOWN); Instructor `handlers.py:582-593` (`tools=[{"type":"function","function":schema}]` + forced `tool_choice`, KNOWN); PRD §5.3 (`@tool` decorator, `ctx` injected and filtered from the LLM view).

---

### Decision 9 — Constrained Decoding (Local Engines): TagDispatch is the correct tool-call model

**Choice (opt-in, local-engines only):** When Verso targets a local engine and constrained decoding is enabled, a tool-call turn is framed as ONE request with a `TriggeredTagsFormat` (XGrammar structural tag / TagDispatch) grammar — not two sequential requests (one for reasoning, one for structured args). The grammar is compiled once per `(tool_set, model_vocab)` and reused across turns.

The TagDispatch format (from XGrammar `structural_tag.py:156-209`, KNOWN):
```python
# Verso emits this to the engine's grammar param:
TriggeredTagsFormat(
    triggers=["<function="],              # tool-call open marker
    tags=[
        TagFormat(
            begin=f"<function={tool.name}>",
            content=JSONSchemaFormat(tool.parameters_schema),
            end="</function>",
        )
        for tool in active_tools
    ],
    at_least_one=False,                   # allow free-text response (no forced tool call)
    stop_after_first=False,               # allow multi-tool in one response
)
```

This models: `<free reasoning> + <trigger> + <begin tag> + <JSON tool args, schema-constrained> + </tag> + <free continuation> + ...` — all in one decode loop, one KV cache, one sampling pass. Reasoning and args are coherent.

Grammar cache: one `GrammarCompiler(tokenizer_info, cache_enabled=True, max_memory_bytes=<256MB default>)` per model vocabulary, never per turn. `CompiledGrammar` objects are serializable (`SerializeJSON`/`DeserializeJSON`) — hot grammars can be persisted across process restarts. Key cache: `(frozenset(tool_parameter_schema_hashes), model_id)`.

Schema design rules for constrained decoding (to minimize the uncertain-token set and avoid whitespace pathologies):
- Structural whitespace: emit `"whitespace_pattern": " ?"` (≤1 space, copy of Outlines `WHITESPACE=[ ]?`) or use XGrammar's `max_whitespace_cnt=1` — prevents small-model whitespace loops.
- Prefer `enum`/`const`/`format` constraints over open `string` fields — each constrained string field reduces the context-dependent token set.
- Avoid unbounded `anyOf` on complex types — blow up the uncertain-token set and compile cost.

**Evidence:** XGrammar `structural_tag.py:156-209` (`TriggeredTagsFormat`, KNOWN); `openai_tool_call_schema.py` (builtin tool-schema → TagDispatch builder, KNOWN); `compiler.h:50-111` (`GrammarCompiler` + cache, KNOWN); `compiled_grammar.cc:16-67` (adaptive token mask cache, KNOWN); `structured-output.md` §XGrammar TagDispatch synthesis ("a tool-call turn is ONE request with a TagDispatch grammar, not two sequential requests").

---

## Component Spec

### `verso/tools/schema.py` — @tool schema generation

```python
# Public interface
from verso.tools.schema import (
    tool_to_json_schema,       # Callable → OpenAI-compatible function schema dict
    make_format_tool_schema,   # type[BaseModel] → forced-extraction tool schema
    FORMAT_TOOL_NAME,          # "_verso_format_output"
    ToolSchema,                 # TypedDict: name, description, parameters (JSON Schema dict)
)

def tool_to_json_schema(fn: Callable) -> ToolSchema:
    """
    Extracts name, description (from docstring), and parameters
    (from type hints) from a Python function.
    - ctx/RunContext params are excluded from the schema.
    - additionalProperties: False always injected.
    - Raises ValueError if fn.__doc__ is missing or empty.
    - Result is cached per id(fn) (pure, safe to memoize).
    """

def make_format_tool_schema(model: type[BaseModel]) -> ToolSchema:
    """
    Builds the forced-extraction 'format tool' for structured output
    in TOOLS mode. All fields required, additionalProperties:false.
    Description: "Use this tool to return a structured response as {model.__name__}."
    """

FORMAT_TOOL_NAME: str = "_verso_format_output"
```

Constants:
- `_SCHEMA_CACHE: dict[int, ToolSchema]` — keyed by `id(fn)`, populated lazily.
- `_PARTIAL_MODEL_CACHE: dict[type, type]` — keyed by original model class, partial variant value.

### `verso/tools/jsonish.py` — the universal post-hoc parser

```python
# Public interface
from verso.tools.jsonish import (
    parse_jsonish,             # (text: str, is_done: bool) → JsonishValue
    JsonishValue,              # Union[dict, list, str, int, float, bool, None, AnyOf]
    CompletionState,           # Literal["complete", "incomplete", "pending"]
    ParseOptions,              # dataclass: all bool gates, all default True
    ParsingMode,               # Literal["default", "json_markdown", "json_markdown_string", "all_json"]
)

@dataclass
class ParseOptions:
    allow_markdown_json: bool = True
    allow_all_finding_json: bool = True
    allow_fixes: bool = True
    allow_as_string: bool = True

def parse_jsonish(
    text: str,
    is_done: bool = True,
    options: ParseOptions = ParseOptions(),
    mode: ParsingMode = "default",
    _depth: int = 0,           # internal recursion guard: bail at depth > 100
) -> JsonishValue:
    """
    5-stage waterfall (strict JSON → markdown-fence → grep-embedded → fixing → as-string).
    Returns a JsonishValue tagged with CompletionState.
    Idempotent — safe to call on each streaming chunk.
    """
```

The `JsonishValue` must carry `completion_state` so callers can distinguish `"12"` (might grow) from `'"foo"'` (closed string, definitely done).

### `verso/tools/coerce.py` — schema-guided coercion with typed Flag cost function

```python
# Public interface
from verso.tools.coerce import (
    coerce_to_model,           # (value: JsonishValue, model: type[BaseModel], ctx: CoerceCtx) → BaseModel
    CoerceCtx,                 # carries scope path, visited sets, union_variant_hint
    Flag,                      # Enum of edit operations with penalty weights
    CoercionError,             # carries dotted field path + list of failed fields
    PENALTY,                   # dict[Flag, int] — the BAML table, verbatim
)

class Flag(Enum):
    UNION_MATCH = "union_match"                       # 0
    OPTIONAL_DEFAULT_FROM_NO_VALUE = "..."            # 1
    SINGLE_TO_ARRAY = "single_to_array"               # 1
    STRING_TO_BOOL = "string_to_bool"                 # 1
    FLOAT_TO_INT = "float_to_int"                     # 1
    FIRST_MATCH = "first_match"                       # 1
    SUBSTRING_MATCH = "substring_match"               # 2
    IMPLIED_KEY = "implied_key"                       # 2
    JSON_TO_STRING = "json_to_string"                 # 2
    DEFAULT_BUT_HAD_UNPARSEABLE = "..."               # 2
    STRIPPED_NON_ALPHA_NUMERIC = "..."                # 3
    ARRAY_ITEM_PARSE_ERROR = "..."                    # 1 + child_score
    DEFAULT_FROM_NO_VALUE = "default_from_no_value"   # 100
    DEFAULT_BUT_HAD_VALUE = "default_but_had_value"   # 110
    EXTRA_KEY = "extra_key"                           # 1

PENALTY: dict[Flag, int] = {
    Flag.UNION_MATCH: 0,
    Flag.OPTIONAL_DEFAULT_FROM_NO_VALUE: 1,
    Flag.SINGLE_TO_ARRAY: 1,
    Flag.STRING_TO_BOOL: 1,
    Flag.FLOAT_TO_INT: 1,
    Flag.FIRST_MATCH: 1,
    Flag.SUBSTRING_MATCH: 2,
    Flag.IMPLIED_KEY: 2,
    Flag.JSON_TO_STRING: 2,
    Flag.DEFAULT_BUT_HAD_UNPARSEABLE: 2,
    Flag.STRIPPED_NON_ALPHA_NUMERIC: 3,
    Flag.DEFAULT_FROM_NO_VALUE: 100,
    Flag.DEFAULT_BUT_HAD_VALUE: 110,
    Flag.EXTRA_KEY: 1,
}

CHILD_SCORE_MULTIPLIER: int = 10    # from score.rs:20-27

@dataclass
class CoerceCtx:
    scope: list[str] = field(default_factory=list)         # dotted field path
    visited_try_cast: set[tuple[str, int]] = ...           # (class_name, id(value)) cycle guard
    visited_coerce: set[tuple[str, int]] = ...
    union_variant_hint: int | None = None                  # last-matched variant index

def coerce_to_model(
    value: JsonishValue,
    model: type[BaseModel],
    ctx: CoerceCtx | None = None,
    validation_context: dict | None = None,    # threaded to model_validate()
) -> BaseModel:
    """
    Two-phase: try_exact (zero-cost, short-circuit on score==0) → coerce_and_score (lossy, flagged).
    pick_best comparator applies semantic tie-breaks before pure score.
    On failure: raises CoercionError with dotted field path and structured fail results.
    On success: calls model.model_validate(result, context=validation_context).
    """
```

### `verso/tools/structured_output.py` — the parse/repair/reask pipeline

```python
# Public interface
from verso.tools.structured_output import (
    StructuredOutputConfig,    # configuration for the full pipeline
    parse_structured,          # one-shot parse (no retry)
    parse_with_reask,          # retry loop with per-attempt tracking
    Partial,                   # Partial[T] streaming partial type
    VersoRetryException,       # raised on retry exhaustion
    FailedAttempt,             # (attempt_number, exception, completion)
    FormatIntent,              # Literal["strict", "tool", "json"] — the 3 caller-facing intents
    OnFailAction,              # Enum: FIX | FIX_REASK | REASK | FILTER | REFRAIN | NOOP | EXCEPTION
)

@dataclass
class StructuredOutputConfig:
    max_retries: int = 2
    timeout_seconds: float | None = None
    default_on_fail: OnFailAction = OnFailAction.EXCEPTION
    constrained_decoding: bool = False      # opt-in, local engines only
    format_intent: FormatIntent | None = None  # None = adapter auto-selects

async def parse_with_reask(
    *,
    model_fn: Callable,                    # async provider call
    response_model: type[BaseModel],
    messages: list[Message],
    mode: CanonicalMode,                   # internal: TOOLS | JSON_SCHEMA | JSON | MD_JSON
    config: StructuredOutputConfig,
    validation_context: dict | None = None,
    hooks: HookRegistry | None = None,     # emits: request_built, response_received, parse_error, last_attempt
) -> tuple[BaseModel, UsageStats]:
    """
    Retry loop:
    1. Call model_fn(*args, **kwargs).  Emit request_built / response_received hooks.
    2. Extract JSON string from response (mode-dependent location).
    3. parse_jsonish(json_str) → JsonishValue.
    4. coerce_to_model(value, response_model, ctx, validation_context) → BaseModel.
    5. On ValidationError: apply OnFailAction policy → FIX (no LLM call) or REASK.
       REASK: append reask message framed per mode; loop.
    6. On exhaustion: raise VersoRetryException(last_completion, n_attempts,
       total_usage, messages, failed_attempts).
    """

@dataclass
class VersoRetryException(Exception):
    last_completion: ProviderResponse
    n_attempts: int
    total_usage: UsageStats    # SUMMED across all attempts — critical for budget accounting
    messages: list[Message]
    failed_attempts: list[FailedAttempt]

class Partial(Generic[T]):
    """
    Partial[T] makes all fields Optional and recursively partial.
    Cached per T in _PARTIAL_MODEL_CACHE.
    Use Partial.stream(chunks) to get an async iterator of progressively-filled T instances.
    """
    @classmethod
    def stream(
        cls,
        chunks: AsyncIterable[str],
        model: type[T],
    ) -> AsyncIterator[T]:
        """
        Per chunk:
        - Accumulate potential_object string.
        - jiter.from_json(buf, partial_mode="trailing-strings").
        - If root structurally closed: model.model_validate(parsed). Yield.
        - Else: Partial[model].model_construct(**parsed). Yield.
        - Final: full model.model_validate() once stream ends.
        """
```

### `verso/tools/validator.py` — Guardrails-style Validator contract

```python
# Public interface
from verso.tools.validator import (
    Validator,                 # ABC: validate(value, metadata) → ValidationResult
    PassResult,
    FailResult,                # error_message, fix_value, error_spans
    OnFailAction,              # FIX | FIX_REASK | REASK | FILTER | REFRAIN | NOOP | EXCEPTION | CUSTOM
    FieldReAsk,                # (incorrectValue, failResults) — the structured reask payload
    perform_correction,        # dispatch OnFailAction → outcome
)

class Validator(ABC):
    def __init__(self, on_fail: OnFailAction = OnFailAction.EXCEPTION): ...
    @abstractmethod
    def validate(self, value: Any, metadata: dict) -> ValidationResult: ...
    def validate_stream(self, chunks: Iterator[str]) -> Iterator[ValidationResult]:
        """Default: split on sentence boundary, validate each complete sentence."""

@dataclass
class FailResult:
    error_message: str
    fix_value: Any | None = None     # validator's proposed correction — no LLM call needed
    error_spans: list[tuple[int, int]] | None = None  # which parts of value failed

@dataclass
class FieldReAsk:
    incorrect_value: Any
    fail_results: list[FailResult]

def perform_correction(
    result: FailResult,
    value: Any,
    validator: Validator,
) -> Any | Filter | Refrain | FieldReAsk:
    """
    FIX → result.fix_value (no LLM).
    FIX_REASK → apply fix_value, re-validate; if still fails → FieldReAsk.
    REASK → FieldReAsk(value, [result]).
    EXCEPTION → raise ValidationError.
    FILTER → Filter().
    REFRAIN → Refrain().
    NOOP → value unchanged.
    """
```

### `verso/model/provider_profile.py` additions — structured output wire shaping

```python
# Additions to existing ProviderProfile
class CanonicalMode(Enum):
    TOOLS = "tools"
    PARALLEL_TOOLS = "parallel_tools"
    JSON_SCHEMA = "json_schema"
    JSON = "json"
    MD_JSON = "md_json"

# Provider capability table — baked in, not runtime-probed
PROVIDER_STRUCTURED_OUTPUT_CAPS: dict[str, list[CanonicalMode]] = {
    "openai/gpt-4o": [CanonicalMode.JSON_SCHEMA, CanonicalMode.TOOLS, CanonicalMode.MD_JSON],
    "openai/gpt-4o-mini": [CanonicalMode.JSON_SCHEMA, CanonicalMode.TOOLS, CanonicalMode.MD_JSON],
    "anthropic/claude-*": [CanonicalMode.TOOLS, CanonicalMode.MD_JSON],
    "google/gemini-*": [CanonicalMode.TOOLS, CanonicalMode.MD_JSON],
    "cerebras/*": [CanonicalMode.MD_JSON],
    "fireworks/*": [CanonicalMode.MD_JSON],
    "perplexity/*": [CanonicalMode.MD_JSON],
    # ...
}

class ModeHandlers:
    request_handler: Callable[[type[BaseModel], dict], dict]   # model → wire request kwargs
    response_parser: Callable[[ProviderResponse], str]          # extract JSON string
    reask_handler: Callable[[list[Message], ProviderResponse, ValidationError], list[Message]]

# ProviderProfile grows:
def get_mode_handlers(
    self,
    intent: FormatIntent,
    response_model: type[BaseModel],
) -> tuple[CanonicalMode, ModeHandlers]:
    """
    Resolve intent → canonical mode → handler bundle.
    intent=None → auto-select most capable mode this provider supports.
    Raises FeatureNotSupported if caller pinned an unsupported intent.
    """
```

### Key Constants (load-bearing — do not change without benchmarking)

| Constant | Value | Source | Location |
|---|---|---|---|
| `DEFAULT_MAX_REASK` | `2` | Instructor default `max_retries=2` | `StructuredOutputConfig.max_retries` |
| `CHILD_SCORE_MULTIPLIER` | `10` | BAML `score.rs:20-27` | `verso/tools/coerce.py` |
| `PENALTY[DEFAULT_FROM_NO_VALUE]` | `100` | BAML `score.rs:63` | `verso/tools/coerce.py` |
| `PENALTY[DEFAULT_BUT_HAD_VALUE]` | `110` | BAML `score.rs:65` | `verso/tools/coerce.py` |
| `JSONISH_MAX_DEPTH` | `100` | BAML `entry.rs:19` | `verso/tools/jsonish.py` |
| `WHITESPACE_MAX_CNT` | `1` | Outlines `types.rs:13-17`, XGrammar `max_whitespace_cnt` | grammar schema emit |
| `FORMAT_TOOL_NAME` | `"_verso_format_output"` | Mirascope `format.py` convention | `verso/tools/schema.py` |
| `ENUM_TIER4_COST` | `2` (SubstringMatch) | BAML `score.rs:55` | `verso/tools/coerce.py` |
| `UNION_VARIANT_HINT_SCOPE` | per-array (reset per new list) | BAML `ParsingContext.union_variant_hint` | `verso/tools/coerce.py` |
| `PARTIAL_JITER_MODE` | `"trailing-strings"` | Instructor `partial.py:381-383` | `verso/tools/structured_output.py` |

---

## Open Unknowns

1. **jsonish Python port correctness vs edge cases.** The BAML fixing parser has ~900 lines of Rust with 15+ regression tests for specific off-by-one and stream-truncation behaviors. Porting to Python requires running the BAML test suite (adapted) against the Python implementation before trusting it in production. The off-by-one `counter += 1` in `should_close_unescaped_string` (`:249,265,381,397`) is the most likely porting trap — dogfood validation needed.

2. **`jiter` Python availability and behavior.** Instructor uses Rust-extension `jiter` (`from_json(..., partial_mode="trailing-strings")`). This is available as a PyPI wheel (`pip install jiter`) but is a Rust extension. If the dependency is unwanted, an alternative is the pure-Python `json_repair` library — but it does not expose `trailing-strings` semantics or per-field `CompletionState`. Decision: use `jiter` for streaming (it is already a transitive dependency of Pydantic v2) or implement a minimal pure-Python structural-completeness check (the sibling heuristic from `json_tracker.py` works with any partial parser).

3. **Format-tool vs native structured outputs: when to prefer which.** The PRD's `require_parameters=True` constraint ensures that if the fallback provider doesn't support tools, the failover chain won't silently degrade. But the exact policy for when the adapter auto-selects `JSON_SCHEMA` vs `TOOLS` for providers that support both (e.g., OpenAI GPT-4o) needs dogfood calibration. Current recommendation: prefer `JSON_SCHEMA` (strictly enforced, no extra tool-call overhead) for pure output-schema use cases; prefer `TOOLS` when the model is also calling real tools in the same turn (avoids the awkward "force one tool + allow other tools" combinatorics).

4. **Guardrails `validate_stream` sentence-boundary split on arbitrary tokens.** The streaming-validator path splits on sentence boundaries to run validators on complete sentences mid-stream. The sentence splitter (`split_sentence_*` in Guardrails) is language-specific (punkt tokenizer). For Verso's v1 (English-dominant), the default punkt splitter is fine; for multilingual or code-heavy outputs it will split incorrectly. Deferred to dogfood.

5. **Grammar compiler cache sizing.** XGrammar `GrammarCompiler` takes `max_memory_bytes=-1` (unbounded by default). For a long-running agent process with many distinct tool sets, the cache can grow. The right default for Verso's cache cap (`256 MB` above) needs profiling against a realistic tool-schema churn rate. The `SerializeJSON` path is a valid cold-start optimization but adds file I/O complexity — defer until profiling shows the compile cost is material.

6. **`ctx` parameter injection: detection heuristic robustness.** The `@tool` schema gen excludes `ctx` from the LLM schema by name and by type annotation (`RunContext`). If a user names a non-context parameter `ctx` or annotates something else as `RunContext`, the exclusion will misbehave. The safer detection is: exclude parameters whose annotation is `RunContext[T]` for any `T`, regardless of name. This requires a `get_origin`/`get_args` check on the annotation. The name-based exclusion is a fallback for unannotated parameters. Needs a test covering both paths.

7. **Streaming `Partial[T]` and union types.** The `Partial[T]` rewrite recurses into fields and makes them all optional. For fields typed as `Union[A, B]`, the partial type becomes `Optional[Union[Partial[A], Partial[B]]]` — which Pydantic v2 handles, but the discriminator information (if any) is lost at the partial level. BAML's `@stream.done` on union variants is a more principled approach (mark the union done when a variant's type-specific `done` condition is met). For v1 dogfood, non-union partials are sufficient; union streaming is a known gap.
