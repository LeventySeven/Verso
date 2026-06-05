# Adversarial Review: jsonish-parser — SCALE & FAILURE lens

**Decision under review:** Build a BAML-style jsonish 5-stage SAP repair parser as the DEFAULT structured-output path (SAP over native function-calling), Pydantic v2 hard dependency, constrained decoding opt-in — vs using Instructor (exists, ~3M downloads/mo, wraps the same pipeline already).

**Lens:** SCALE & FAILURE — enumerate concrete failure modes the resolution does NOT handle. Does the default survive production, or only the happy path? Name the specific failure that bites at 10×.

**Critic:** adversarial panel, SCALE & FAILURE assignment.

**Date:** 2026-06-05

---

## The Attack

The resolution builds a correct system for the happy path: well-formed or lightly-malformed model output, one structured turn, short streaming responses, no concurrent reask cycles, a solo dogfood user. At the production boundary — 10× concurrent agents, non-idempotent tool calls, 1M-token streaming windows, a reask loop that hits `max_retries=2` under load — three independent failure modes activate that the resolution does not address. Two of them do not fail loudly; they corrupt silently.

### Failure Mode 1 — Reask token blow-up is unaccounted in the agent loop's budget (the cost correctness failure)

The resolution correctly specifies that `VersoRetryException.total_usage` MUST be summed across all reask attempts and that this is "critical for token-budget accounting." The Instructor teardown (`retry.py:87-244`, KNOWN) confirms `update_total_usage` accumulates per attempt. The resolution's component spec (`parse_with_reask`, `structured_output.py`) returns `tuple[BaseModel, UsageStats]` where the `UsageStats` is the summed total.

**What the resolution does not specify:** how this summed `UsageStats` propagates back to the agent loop's `RunContext.budget`. The loop (PRD §5.1) has:

```python
while not cancelled and budget.remaining:
    bundle = assemble_context(...)
    response = await model.call(bundle)     # ← this is the model edge call
    if response.tool_calls:
        results = await dispatch(response.tool_calls)
```

The `model.call(bundle)` returns a `ProviderResponse`. For a structured-output turn, `parse_with_reask` is called inside the model layer — it fires the initial model call plus up to `max_retries=2` additional reask calls. Each reask is a full `model.call()` — same tokens, same cost. But the `ProviderResponse` returned to the loop carries the usage from only the **final** call, unless the reask layer explicitly accumulates and injects the full `total_usage` into the response object.

The resolution specifies the `total_usage` sum within `VersoRetryException` (the failure path) and within the return type of `parse_with_reask`. It does NOT specify the integration contract with `RunContext.budget.charge(usage)`. If `budget.charge(usage)` is called once on the final call's usage (the natural implementation), the budget sees 1× the tokens when the actual expenditure was 3×. At `max_retries=2`, a single structured turn costs up to 3× its apparent cost.

**The failure at 10×:** A workload where structured turns routinely hit 1–2 reasks (e.g., a complex nested schema with a weak model on the cheap tier) running 10 concurrent agents. Each agent's `budget.remaining` shows 3× more headroom than actually consumed. The `budget_exhausted` StopReason fires at 3× the intended token ceiling. On a per-agent basis this is a 2× overrun; across 10 concurrent agents, the aggregate token cost is 3× the expected cost. A `max_budget_usd` cap (PRD §6.3) that is calculated from the apparent per-turn cost will be breached silently — the agent runs to completion, the bill is 3× the approved budget, and no `budget_exhausted` event fires because `budget.remaining` was wrong throughout.

This is not a theoretical edge case. At `max_retries=2`, every structured turn on a provider in `MD_JSON` mode (Cerebras, Fireworks, Perplexity, Bedrock — the entire right column of the capability table) is operating on the lowest-reliability tier where reasks are most frequent. These are also the cheap providers users route to for cost savings — making the 3× multiplier land hardest on the use case where cost control matters most.

**Resolution's treatment:** The resolution documents `total_usage` summing and makes it "non-negotiable." It does NOT specify the plumbing from `parse_with_reask` return value → `RunContext.budget`. This is the missing integration spec, and at scale it is a cost correctness bug.

---

### Failure Mode 2 — Non-idempotent tool reask produces undetectable semantic corruption (the worst one)

PRD §5.3 states: "Non-idempotent tools → `max_attempts=1` (auto-retrying state-changing actions is a correctness bug)." The tool dispatch layer enforces `max_attempts=1` to prevent re-execution of a tool call that already fired. This is correct at the dispatch layer.

**The interaction the resolution misses:** the reask loop fires at the structured-output parse layer, BEFORE tool dispatch. The sequence is:

```
1. model.call() → response with tool_call(name="send_email", args_json: INVALID)
2. parse_with_reask: parse args_json → schema validation FAILS (e.g., missing required "subject" field)
3. OnFailAction.REASK → reask message appended → NEW model.call()
4. NEW model response → new tool_call(name="send_email", args_json: VALID with "subject"="Revised Subject")
5. parse_with_reask succeeds → returns valid SendEmailArgs
6. dispatch → send_email fires
```

The reask (step 3–4) regenerated the tool call. The new valid call at step 4 may differ semantically from the original (step 1) — the LLM, re-prompted with the validation error, freely modifies any field, not just the missing one. The recipient could change. The body could change. The subject is now "Revised Subject" instead of whatever was originally intended. The agent loop sees a valid `SendEmailArgs` instance; the `non_idempotent=True` flag on the tool prevents re-dispatch of the SAME call, but this is a DIFFERENT call. The email that is actually sent may be semantically different from what the LLM intended in the original response.

There is no detection mechanism. The `failed_attempts` list in `VersoRetryException` (which carries the original malformed args alongside the new valid args) exists only on the error path — on the success path, the loop sees only the final valid object with no record that the original intent may have diverged during reask. The tool's `validate()` pre-execution check (PRD §5.3) runs on the validated args — but it was designed for correctness of the FINAL args, not for intent-preservation across a reask cycle.

**The specific failure pattern at scale:** Any agent that calls a state-mutating tool (payment, email, database write, file delete) through a provider in `MD_JSON` mode (the cheapest tier) with a complex argument schema (many required fields, union types) will periodically produce a reask cycle that silently modifies the semantic content of the tool call. The probability is a direct function of schema complexity, model quality, and provider tier. On cheap models via MD_JSON with a 10-field required schema, reask probability is non-trivial — BAML's own benchmarks show gpt-4o-mini SAP achieves 92.4% vs 19.8% FC, meaning ~7.6% of responses require repair. For a 10-field required schema on a weak model, multi-field failures requiring reask are materially more frequent.

**The resolution has no guard for this.** The `OnFailAction` ordering (FIX → FIX_REASK → REASK → EXCEPTION) is designed to minimize reask calls but does not include an "EXCEPTION on non-idempotent tool" policy. The `StructuredOutputConfig` has no `allow_reask_on_nonidempotent=False` flag. The `@tool` decorator's `idempotent=False` hint does not propagate to the structured-output layer. The two systems (tool policy and reask policy) are designed independently and have no integration point.

**Evidence for the interaction being real:** The resolution's Decision 6 specifies reask framing per mode. In TOOLS mode, the reask appends the original assistant message (with its tool_calls) and a `role:"tool"` error message, then fires a new model call. The new model response is a fresh generation, not a targeted fix of only the failing field. This is documented verbatim: "Recall the function correctly, fix the errors." The model is instructed to regenerate the full function call — it is not constrained to only fix the schema violation.

---

### Failure Mode 3 — Streaming buffer accumulation is O(n²) for long responses

The `Partial[T]` streaming path (Decision 7) accumulates `potential_object` string across ALL chunks: "Accumulate `potential_object` string across chunks (after stripping control chars)." The root-closed check uses `jiter.from_json(json_str.encode(), ...)` on the full accumulated buffer each chunk.

For a short structured response (a tool-call argument JSON, typically 50–500 tokens), this is invisible. For a long streaming structured output (a 1M-token document generation schema, a deep-research report with nested sections and hundreds of string fields), `potential_object` grows to tens or hundreds of kilobytes. `jiter.from_json(json_str.encode(), ...)` is called on the FULL accumulated buffer every chunk — not just the new delta. At N chunks with average chunk size C bytes, the total work is N × N×C/2 = O(N²C). For a 4096-token streaming response at 4 bytes/token with 10-token average chunk size: N ≈ 400 chunks, buffer ≈ 16KB, total work ≈ 400 × 16KB = ~6.4MB of buffer processing. For a 128K-token streaming response: N ≈ 12,800 chunks, buffer ≈ 512KB, total work ≈ 6.5GB of buffer processing — CPU-bound, blocking the asyncio event loop.

**The resolution has no chunk-size limit or sliding-window buffer.** The sibling-completeness heuristic (`json_tracker.py:57-96`, KNOWN) identifies complete vs incomplete fields mid-stream but does not reduce the accumulation buffer — it only answers which fields are done. The `is_root_closed` check requires the full buffer each time. At 1M-token context (a stated Verso target — "1M-token context" appears in the lens brief), a single streaming structured output can be several megabytes, and the O(N²) processing blocks the event loop for seconds per chunk in the second half of the stream.

This is a concrete production failure on the context-window scale that Verso is explicitly designed to handle. The tactical core (§5.1) specifies `max_tokens` enforcement but not streaming buffer limits. The streaming module (`stream/`) normalizes chunks but the accumulation buffer grows without bound.

**Mitigation the resolution could have specified but didn't:** a maximum buffer size after which the waterfall falls back to the AS_STRING stage (graceful degradation) and triggers a `REASK` with the partial object as context. Or: switch to a lazy-parse approach (only re-parse on root-closing tokens `}` or `]`, not on every chunk). Neither is specified.

---

### Failure Mode 4 — The jsonish Python port is a 900-line state machine with 15 known regression cases and no ported test suite

The resolution acknowledges this directly: "The BAML fixing parser has ~900 lines of Rust with 15+ regression tests for specific off-by-one and stream-truncation behaviors. Porting to Python requires running the BAML test suite (adapted) against the Python implementation before trusting it in production. The off-by-one `counter += 1` in `should_close_unescaped_string` (`:249,265,381,397`) is the most likely porting trap — dogfood validation needed."

This acknowledgment, placed in the Open Unknowns section, is the most accurate part of the resolution and simultaneously its sharpest self-indictment on the SCALE & FAILURE lens. The ported implementation will have bugs. The questions are: which bugs, how often do they fire, and what does silent failure look like?

The fixing parser's failure modes are not loud. A bug in `should_close_string` produces a `QuotedString` that closes one character early or late — yielding a `JsonishValue` that the schema-guided coercer then attempts to fit to the target type. The coercer has no way to detect that the input JSON was mis-parsed vs genuinely malformed; it applies the `Flag` cost function and picks the best candidate. A parse bug produces a coercion path with a specific `Flag` pattern — say, `ImpliedKey` (cost=2) where none was intended — and returns a silently wrong field value.

**The production impact of a silent mis-parse:** The BAML test case at `json_parse_state.rs:106-124` demonstrates the known behavior for `"[12"` → `Array([Number(12, Incomplete)], Incomplete)`. A Python port that mis-handles this case could return `Number(12, Complete)` (drops the array wrapper) or `String("12", Incomplete)` (falls to as-string). The schema coercer then silently coerces a number or string where an array was expected. The `SingleToArray` flag (cost=1) may rescue the number case; the string case produces a `StringToBool/Null/Float` chain or `DEFAULT_FROM_NO_VALUE` (cost=100) for subsequent array fields. The agent loop receives a partially-wrong tool argument and proceeds to dispatch a tool call with corrupted data.

This is the canonical "silent data corruption at scale" failure: the system returns a result, marks the turn successful, and the downstream action is wrong. At 10× concurrent agents firing hundreds of structured calls per hour, a 0.1% mis-parse rate on the fixing-parser path produces several wrong tool calls per hour, none of which are flagged as errors.

**The resolution defers this to "dogfood validation needed" — which is correct discipline, but it means the Phase 0 build ships a known-unvalidated port of the most critical component in the structured-output pipeline.** The fixing parser is Stage 4 of the waterfall, activated whenever the model output is non-standard JSON. MD_JSON mode (the lowest-tier, most-used fallback) produces non-standard JSON frequently. The most-used fallback activates the least-validated component.

---

## Does It Break?

**The decision does NOT break at dogfood scale (one user, simple schemas, reliable models, short responses).** The happy path — clean model output, fast-path Stage 1 `json.loads`, or simple markdown-fence extraction (Stage 2) — exercises none of these failure modes. SAP accuracy numbers (92.4% gpt-4o-mini) mean the fast path fires 92%+ of the time, and the reask loop fires <8%. At solo dogfood, `max_retries=2` is a minor overhead.

**The decision PARTIALLY breaks at production scale on three specific vectors:**

1. **FM1 (budget under-accounting)** is a SILENT cost correctness bug that bites at any concurrency level where reask cycles are common — most acute on cheap-tier MD_JSON providers, which is the primary cost-optimization path. Severity: medium-high (financial correctness, `max_budget_usd` cap is violated silently). Fix: specify the `total_usage` → `RunContext.budget.charge()` propagation path explicitly in the component spec, and make the reask loop the loop-level accounting unit, not the per-call accounting unit.

2. **FM2 (non-idempotent tool reask)** is a SILENT semantic corruption bug that bites whenever a non-idempotent tool call has an invalid argument schema — most acute on complex schemas, cheap models, MD_JSON mode. Severity: HIGH (data integrity — wrong emails sent, wrong payments processed, no detection path). Fix: `StructuredOutputConfig.allow_reask = False` default when `tool.idempotent == False`, and explicit integration between `@tool` metadata and `parse_with_reask` config. The tool's `validate()` pre-execution check must see the reask history, not just the final args.

3. **FM3 (streaming buffer O(n²))** is a PERFORMANCE degradation that blocks the asyncio event loop for long streaming responses. Severity: medium (latency degradation, not correctness) at <100K token outputs; SEVERE at 1M-token outputs where processing time is seconds per chunk. Fix: parse only on structural tokens (`}`, `]`) or add a max-buffer-size policy with graceful fallback.

4. **FM4 (port correctness)** is a LATENT correctness risk that is explicitly deferred. Severity depends entirely on how thoroughly the BAML test suite is ported. It is correctly identified as the primary Phase 0 pre-production bloat risk. The fix IS specified in the Open Unknowns — run the adapted test suite before shipping — but the resolution does not make this a blocking gate (it says "dogfood validation needed," not "DO NOT SHIP without test parity").

**The single strongest failure is FM2 (non-idempotent tool reask).** It is invisible in dogfood (the solo user does not send emails or process payments at scale with weak models), silently dangerous in production, and absent from the resolution entirely. It exists at the intersection of two correct-in-isolation subsystems (tool policy and reask policy) that were designed without an integration contract. The resolution specifies both halves competently; it misses the seam between them.

---

## Evidence Checked

- Resolution note `/Users/seventyleven/Desktop/Verso/research/06_design_resolutions/structured-output.md` — Decision 6 (reask loop), Decision 4 (jsonish waterfall), Decision 7 (streaming partial), Open Unknown §1 (port correctness), Open Unknown §2 (jiter). Read in full.
- Teardown `/Users/seventyleven/Desktop/Verso/research/03_teardowns/structured-output.md` — Instructor `retry.py:87-244` (reask loop and `update_total_usage`, KNOWN); `handlers.py:119-268` (reask framing per mode); `function_calls.py:91-110` (extract-then-validate seam); `partial.py:376-408` (streaming accumulation, `potential_object` accumulation verbatim); `json_tracker.py:57-96` (sibling completeness heuristic). Read in full.
- BAML teardown section — `json_parse_state.rs:106-148` regression tests (truncated stream behaviors); `should_close_unescaped_string` off-by-one at `:249,265,381,397`; `entry.rs:19` depth guard; `score.rs:34-77` penalty table. Read in resolution note (KNOWN cites, source read 2026-06-05 per teardown header).
- PRD `/Users/seventyleven/Desktop/Verso/docs/PRD_v1.md` — §5.1 (loop structure, `budget.remaining` check, model.call return); §5.3 (non-idempotent tool policy `max_attempts=1`, tool `validate()` pre-execution check); §6.3 (`max_budget_usd` hard cap); §6.4 (role-tiered models, `UsageStats` in `AgentResult`). Read in full.
- THESIS_VERIFICATION.md — Claim 7 (keep it simple, dogfood-first), meta-verdict. Read in full. No direct bearing on scale failures; confirms dogfood-first scope is honest.
- Provider capability table (resolution Decision 3) — confirmed MD_JSON tier includes Cerebras, Fireworks, Perplexity, Bedrock (the cheap-provider tier). This is the tier where reask rates are highest and FM1 + FM2 are most acute.

**Claims verified against source:**
- "Non-idempotent tools → `max_attempts=1`" — PRD §5.3, verbatim. CONFIRMED.
- "`update_total_usage` accumulates per attempt" — teardown, Instructor `retry.py:87-244`, KNOWN. CONFIRMED.
- "NEW model response may change the call" — resolution Decision 6 reask framing: "Recall the function correctly, fix the errors" — the LLM is re-generating freely, not patching the one failing field. CONFIRMED.
- "potential_object string accumulated across all chunks" — resolution Decision 7 component spec `Partial.stream`: "Accumulate `potential_object` string." CONFIRMED.
- "jiter.from_json called on full accumulated buffer each chunk" — teardown `partial.py:381-383` per-chunk processing, step 2: `parsed = jiter.from_json(json_str.encode(), ...)`. CONFIRMED.
- "no integration spec between tool.idempotent and StructuredOutputConfig" — resolution component spec for `StructuredOutputConfig` has `max_retries`, `timeout_seconds`, `default_on_fail`, `constrained_decoding`, `format_intent` — no `idempotent_tool` field. Resolution mentions no integration point. CONFIRMED absent.

---

## Recommendation

**REVISE** — the decision is architecturally correct (SAP over CD for hosted providers, Pydantic v2, 3-intent surface) and the evidence base is solid. The scale failures are integration gaps, not design flaws. Three targeted additions to the component spec close the material risks:

1. **FM1 fix (budget propagation):** Add to `parse_with_reask` spec: "On return (success or failure), the SUMMED `total_usage` across all attempts MUST be charged to `ctx.budget` before the call returns. The caller sees one budget charge equal to the actual token cost, not the final-attempt cost. `model.call()` may NOT charge the budget internally when called from within `parse_with_reask` — the reask loop owns the aggregate charge." Make this a one-line invariant in the loop spec (§5.1).

2. **FM2 fix (non-idempotent reask guard):** Add to `StructuredOutputConfig`: `allow_reask: bool = True`. Add to `@tool` integration: "When the tool's `idempotent=False` (or `destructive=True`) and `allow_reask` is not explicitly overridden, `StructuredOutputConfig` for that tool's argument parsing MUST default `allow_reask=False`, `default_on_fail=OnFailAction.EXCEPTION`." This means: a non-idempotent tool call with a schema validation failure raises immediately rather than silently regenerating the call. The calling agent can catch `VersoRetryException` and choose to ask the user, retry from scratch, or abort. The tool's `validate()` pre-execution check should additionally receive `was_reask: bool` in its metadata so it can apply stricter validation after a regeneration cycle.

3. **FM3 fix (streaming buffer cap):** Add to `Partial.stream` spec: "If `len(potential_object)` exceeds `STREAMING_BUFFER_MAX_BYTES` (default: 256 KB), switch to non-incremental emission — yield nothing until the stream ends, then parse the full buffer once. Emit a `status` event with `type='streaming_buffer_capped'` so the consumer knows partial objects are no longer being emitted." This prevents the O(n²) path for long outputs while preserving correctness. For the vast majority of tool-call argument streaming (< 10 KB), the buffer cap is never hit.

4. **FM4 gate (port validation):** Promote from Open Unknown to blocking Phase 0 gate: "The jsonish Python port MUST pass all 15+ BAML regression tests (adapted for Python) before any production structured call. The off-by-one at `counter += 1` in `should_close_unescaped_string` MUST have a dedicated test with the exact inputs from `json_parse_state.rs:926-949`. DO NOT SHIP Phase 0 without this gate passing."

These are four additions to two existing component specs (~30 lines total). The underlying architecture (SAP, Pydantic v2, 5-stage waterfall, reask loop) does not change. The decision is right; the seam between the reask layer and the tool-policy layer is the gap that production will find first.
