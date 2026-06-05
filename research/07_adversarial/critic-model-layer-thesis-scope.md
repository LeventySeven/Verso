# Adversarial Critique: model-layer / THESIS & SCOPE

**Decision under review:** Build the model layer in-house: ProviderProfile + 5 hooks + OMIT sentinel, P2C+PeakEWMA load-balancer (decay_τ=30s), two-axis error-typed cross-model failover — vs delegating to LiteLLM / a gateway.
**Lens:** THESIS & SCOPE — does this betray "keep it simple; dogfood-first; no non-bottleneck dependency; tactical layer simple"?
**Date:** 2026-06-05
**Files read:** `06_design_resolutions/model-routing.md` (1,043 lines), `03_teardowns/infra-model-gateways.md` (1,126 lines), `docs/PRD_v1.md`, `research/THESIS_VERIFICATION.md`, `07_adversarial/critic-seam-mechanism-thesis-scope.md`.

---

## The Attack

**The thesis says:** "keep it simple; don't over-engineer; no non-bottleneck dependency; the tactical layer stays simple; you find the right abstraction by using it, not on paper." The PRD says explicitly, at §2: "Not a model router / planner cult. Routers and hand-crafted planners are *tactical* scaffolding the harvest flags as depreciating; Verso supports them but never centers them."

The model-routing resolution builds a 9-module, 10-decision, 1,043-line spec for Phase 0 that includes: a provider abstraction (ProviderProfile, OMIT), a full load balancer (PeakEWMA + P2C), two-axis failover with error taxonomy, init-time capability validation, a budget guard with Redis and cache-aware CEL cost formula, cache-sticky routing, force-include-usage streaming rewrite, retry with jitter, an attempt audit trail, AND two learned routers (RoRFRouter + ConfidenceCascade) plus a `should_reason_step()` complexity classifier — before a single line of Phase 0 code has been written and dogfooded.

**That is over-engineering.** The attack has two prongs.

### Prong 1 — The scope of the build is not the simplest thing that works for Phase 0

The Phase 0 exit criterion (PRD §8) is: "build a real personal agent on it." For that exit criterion, the model layer needs exactly: (a) call a provider (Anthropic), (b) translate the request/response shape, (c) fail over to a second provider (OpenAI) when the first fails. That is it. That is the bottleneck that needs to exist before Phase 1.

The resolution builds all of the following that are NOT needed to exit Phase 0:

| Component | Needed for Phase 0 exit? | Honest defer point |
|---|---|---|
| ProviderProfile + OMIT (D1) | YES — the core abstraction | Build |
| Failover D3 (two-axis model × provider) | Partial — basic failover yes, error-typed chains on CONTEXT_WINDOW/CONTENT_POLICY are speculative | Prune to simple chain |
| D4 `require_parameters` enforcement at init | YES — prevents silent loop breakage | Build |
| PeakEWMA + P2C load balancer (D2) | **NO** — you have one provider (Anthropic) in Phase 0. P2C requires ≥2 healthy providers. | Defer to Phase 1 |
| BudgetGuard with Redis (D5) | **NO** — a single-process dogfood agent needs at most a simple counter. No Redis, no `RedisBudgetStore`, no cache_aware_cost CEL formula. | Defer to Phase 2 (when durable/submit exists) |
| D6 learned routers (RoRFRouter, ConfidenceCascade, KNNRouter) | **NO** — RoRF requires 200–500 calibrated prompts (unknown #2), ConfidenceCascade requires logprobs (unknown #5, broken on Anthropic), KNN requires an eval corpus. None of these exist before Phase 0 is dogfooded. | Defer to Phase 3 |
| D7 `should_reason_step()` per-step reasoning gate | **NO** — unknown #3 explicitly admits it cannot be validated "without real agent traces." | Defer to Phase 1 |
| D8 cache-sticky routing (RoutingState, promote_sticky_provider) | **NO** — unknown #1 admits it needs empirical calibration. | Defer to Phase 1 |
| D8 force `stream_options.include_usage=true` body rewrite | YES — token accounting must work | Build (2 lines) |
| D9 retry with jitter (attempts=6, initial=4s, max=240s) | YES — needed for reliability | Build |
| D10 AttemptRecord audit trail | YES — needed for debugging | Build |
| 9-module layout (routers/ sub-package with 3 files) | **NO** — the `routers/` sub-package (rorf.py, cascade.py, knn.py) should not exist until there is evidence they work on Verso's real traffic | Defer to Phase 3 |

The Phase 0 model layer that satisfies the exit criterion is: ProviderProfile + OMIT + AnthropicProfile + OpenAIProfile, basic two-provider failover with error classes (rate_limit / server_error / auth), `require_parameters` enforcement, `call_with_retry` (jitter, 6 attempts), `force include_usage`, and `AttemptRecord`. That is approximately 200–250 lines across 4 files (`__init__.py`, `profile.py`, `failover.py`, `errors.py`). The resolution specifies 9 modules before Phase 0 has shipped.

**What is lost by deferring the omitted components past Phase 0:**
- No concurrency-aware load balancing → acceptable for a single-user dogfood agent where concurrent requests to the same provider are rare. P2C's benefit (avoiding thundering-herd under N concurrent deciders) does not apply to a solo developer calling one agent at a time.
- No Redis-backed budget guard → acceptable; a simple `remaining_budget: float` field on `RunContext` covers Phase 0's needs. The `max_budget_usd` hard cap can be enforced without Redis.
- No learned routing → by definition not possible before a calibration corpus exists. Building the infrastructure before the corpus is available is pre-emptive.
- No per-step reasoning gate → cannot be tuned before agent traces exist.

### Prong 2 — LiteLLM covers the Phase 0 need with zero build cost

The PRD says "Not a model router / planner cult" and explicitly rejects the 592K-LOC Portkey monolith. The resolution correctly notes that Portkey is too heavy and LangChain subclassing is wrong. But LiteLLM is neither.

LiteLLM (`litellm==1.x`, ~50K lines, Apache-2.0) provides, out of the box:
- OpenAI-canonical request shape, per-provider `Config.transform_request` / `transform_response` for Anthropic / Google / Groq / Ollama
- `litellm.completion(model="anthropic/claude-sonnet-4-6", ...)` — the provider prefix IS the dispatch
- `litellm.completion(..., fallbacks=["openai/gpt-4o", "google/gemini-2.5-pro"])` — ordered fallback chain
- `litellm.completion(..., num_retries=6, request_timeout=240)` — retry with jitter
- `litellm.stream_chunk_builder` — streaming usage accumulation
- `OMIT`-equivalent: LiteLLM strips unsupported params per provider automatically (`drop_params=True`)

The resolution rejects LiteLLM with one sentence: "without the 592K-LOC monolith trap." But that characterization is of Portkey, not LiteLLM. LiteLLM is ~50K lines (a 10× difference) and its `Config` interface is exactly what the resolution uses as its template ("LiteLLM's four-method `Config` (`transform_request`, `transform_response`, `get_error_class`, `get_supported_openai_params`) proved this shape scales to 100+ providers"). The resolution then builds a 5-hook version of that same interface — it is building a 200-line LiteLLM-Config-shaped adapter when LiteLLM itself is available.

**What LiteLLM gives Verso for Phase 0:**
- `litellm.acompletion(model="anthropic/claude-sonnet-4-6", messages=..., fallbacks=[...], num_retries=6)` — this is 1 line that covers D1, D3, D9 for Phase 0.
- The `AttemptRecord` equivalent is `litellm.ModelResponse.response_cost` + `litellm._add_key_to_alias_list` logging.
- `require_parameters` equivalent: `litellm.validate_environment(model="...")` checks credential + provider availability before calling.
- Streaming usage: `litellm.stream_chunk_builder(chunks)` accumulates the final usage dict from streaming chunks.

**What LiteLLM does NOT give Verso:**
- PeakEWMA + P2C load balancer (not needed for Phase 0 as argued above)
- `ModelPolicy` dataclass (Verso-specific per-node routing config — but this is just a wrapper around `fallbacks` + `num_retries` for Phase 0)
- Learned routers (not needed, can't be used without calibration corpus)
- Cache-sticky routing (not needed until Phase 1+)
- Budget guard with rolling Redis window (not needed until Phase 2)

**What is lost by using LiteLLM vs. build:**
| Capability | LiteLLM (compose) | Build (D1–D10) |
|---|---|---|
| Provider abstraction + OMIT | Covered — `drop_params=True` is equivalent | ProviderProfile + OMIT |
| Basic failover | Covered — `fallbacks=[...]` | Two-axis model × provider, error-typed |
| Error-typed routing (CONTEXT_WINDOW → new model) | Not automatic — LiteLLM raises `ContextWindowExceededError`; caller must catch and switch | D3 error-typed chains |
| Cache-sticky routing | Not built-in | D8 |
| PeakEWMA + P2C | Not built-in | D2 |
| `require_parameters` enforcement at init | Partial — `validate_environment` checks creds but not tool-support | D4 |
| Learned routing | Not built-in | D6 RoRF / Cascade |
| Per-step reasoning gate | Not built-in | D7 `should_reason_step` |
| Budget guard | `litellm.get_max_tokens()`, cost tracking in `Success_Handler` | D5 |
| AttemptRecord audit trail | `litellm.completion_cost()` + response metadata | D10 |

The error-typed chain (CONTEXT_WINDOW → jump to `on_context_window` model list) and `require_parameters` at init are the two genuinely Verso-specific behaviors LiteLLM does not directly provide. Both are ~50 lines of code each. Neither requires building the full 9-module spec.

### The over-engineering indictment — where the resolution's own unknowns condemn the scope

The resolution's 8 open unknowns reveal that the expensive components are not ready to build:

- Unknown #1 (`CACHE_STICKY_STEPS = 5`) — "needs empirical validation... Dogfood with real agents to calibrate." Cannot be right without Phase 0/1 dogfood. The constant is guessed.
- Unknown #2 (RoRF threshold calibration) — "needs 200–500 representative tasks and quality scores." These do not exist. Building `rorf.py` and `cascade.py` now creates dead code until Phase 3.
- Unknown #3 (`should_reason_step` keyword vs embedder) — "does the embedding path justify the latency? Measure on real agent traces." The agent traces do not exist. The correct action is: don't build `reasoning.py` yet.
- Unknown #4 (BudgetStore Redis boundary) — "Defer to Phase 2." The resolution correctly defers the Redis requirement, but still specifies the full `BudgetGuard` class with `RedisBudgetStore` Protocol, `cache_aware_cost()` with 6 parameters, and rolling window key scheme. Deferring "when to require Redis" while specifying the full Redis interface is building the infrastructure before the requirement is confirmed.
- Unknown #5 (ConfidenceCascade logprobs) — "Anthropic claude does not currently expose [logprobs]." The primary Phase 0 provider does not support the component being built. Building `cascade.py` for a Phase 0 agent on Anthropic is building a component that provably cannot work on the default provider.

The PRD's own principle (§2): "the right abstraction cursor cannot be found on paper — only by using the thing." The resolution builds D2, D5, D6, D7, D8 — five of the ten decisions — without the dogfood evidence that would validate them.

### The "non-bottleneck dependency" test

The thesis test is: "don't add a non-bottleneck dependency." The proposed build adds:
- Jina-v3 (`jinaai/jina-embeddings-v3`, `trust_remote_code=True`) — a 1GB+ model download, required for `RoRFRouter`. For a solo Phase 0 dogfood build, this is not a bottleneck dependency — it is a dependency for a capability that provably cannot be used (no calibration corpus).
- Redis — explicitly deferred in unknown #4, but the `RedisBudgetStore` Protocol and key scheme are fully specified. The infrastructure cost of writing code to an interface you can't test is nonzero.
- sklearn / pickle — for `RoRFRouter.rf = pickle.load(...)`. Again, no corpus, no classifier.

None of these are bottlenecks for Phase 0.

---

## Does It Break the Decision?

**Partially — and the split matters, just as it did for the durable-engine critique.**

The core of the decision — ProviderProfile + OMIT + basic failover + `require_parameters` + `call_with_retry` + force-include-usage + AttemptRecord — **SURVIVES**. This is the right architecture. The 5-hook ProviderProfile shape is proven correct (LiteLLM's 4-method Config at scale, cited from source). The OMIT sentinel is a genuine improvement over LiteLLM's `drop_params` global flag. The error-typed two-axis failover is the correct design. These should be built.

What the attack breaks is the **scope of what is bundled into Phase 0**:

- D2 (PeakEWMA + P2C) before multi-provider concurrency is a bottleneck: OVER-ENGINEERED for Phase 0.
- D5 (BudgetGuard + BudgetStore Protocol + cache_aware_cost) before Phase 2 durable runtime: PREMATURE.
- D6 (RoRFRouter + ConfidenceCascade + KNNRouter) before a calibration corpus exists and before the primary provider (Anthropic) supports logprobs: CANNOT BE USED.
- D7 (should_reason_step) before agent traces exist: PREMATURE.
- D8 (cache-sticky routing with RoutingState) before empirical calibration: PREMATURE.
- The 9-module layout (`routers/` sub-package with 3 files) before D6 is needed: PREMATURE STRUCTURING.

An alternative framing: the decision confuses KNOWING the right architecture (which is valid, based on solid RE evidence) with BUILDING it all now (which is premature for Phase 0). The teardown correctly identifies P2C as the right Phase 1+ load-balancing algorithm. That is not a reason to build the balancer in Phase 0.

**Comparing to the precedent set by `critic-seam-mechanism-thesis-scope.md`:** that critique found the seam architecture sound but the bundled engine premature. The same structure applies here: the provider abstraction + failover + error taxonomy is sound; the learned routers + per-step reasoning gate + Redis budget guard are bundled prematurely.

---

## Evidence Checked

1. **PRD §2 non-goals** — "Not a model router / planner cult. Routers and hand-crafted planners are *tactical* scaffolding the harvest flags as depreciating." Direct contradiction of shipping D6 (learned routers) in Phase 0. [READ from PRD_v1.md]
2. **PRD §8 phasing** — Phase 0 exit criterion: "build a real personal agent on it." No multi-provider load balancing, no learned routing, no Redis budget guard required to exit Phase 0. [READ from PRD_v1.md]
3. **Resolution open unknowns #1–5** — four of five unknowns explicitly defer to "after dogfood" or admit the component "cannot be used" (Cascade + Anthropic logprobs). Building the infrastructure for these now produces dead code. [READ from model-routing.md:999–1024]
4. **ConfidenceCascade + Anthropic** — `infra-model-gateways.md` vLLM SR section confirms logprob access is provider-specific; resolution unknown #5 explicitly states "Anthropic claude does not currently expose [logprobs]." The cascade cannot work on the default Phase 0 provider. [VERIFIED from resolution and teardown]
5. **RoRF calibration requirement** — resolution unknown #2: "needs a calibration dataset (a set of prompts run against both model_a and model_b with quality scores). For v1 personal use, this means running 200–500 representative tasks and scoring them. No substitute for this — the threshold cannot be guessed from first principles." The corpus does not exist at Phase 0. [READ from model-routing.md:1003–1006]
6. **LiteLLM scope** — the resolution's stated reason for rejecting LiteLLM is the "592K-LOC monolith trap." That characterization applies to Portkey (researchfms `PORTKEY.md`), not LiteLLM. The resolution itself uses LiteLLM's `Config` interface as the *template* for ProviderProfile ("LiteLLM's four-method Config... proved this shape scales to 100+ providers"). Rejecting LiteLLM while building a 5-hook version of its Config interface is self-undermining. [READ from model-routing.md:85–88]
7. **P2C concurrency argument** — `infra-model-gateways.md` §Helicone: "P2C avoids the thundering-herd failure mode... with N concurrent deciders, the probability any single endpoint is the worse-of-2 for ALL collapses geometrically." This benefit is specific to concurrent deciders. A solo dogfood agent issuing sequential requests to a single provider has N=1 concurrent decider; the P2C benefit is zero. [READ from infra-model-gateways.md:99]
8. **9-module layout** — `model-routing.md:971–993` specifies `verso/model/` with 9 files including `routers/` (3 files). For Phase 0 needs as argued, 4 files suffice (`__init__.py`, `profile.py`, `failover.py`, `errors.py`). The `routers/` sub-package, `balancer.py`, `budget.py`, and `reasoning.py` belong in Phase 1–3. [READ from model-routing.md]
9. **THESIS_VERIFICATION.md §Claim 5** — "~90% with a simple ReAct agent = OPINION." The harvest does not confirm that advanced routing is unnecessary; it confirms that *simplicity is the right default*. The resolution ships advanced routing as Phase 0 default, not opt-in. [READ from THESIS_VERIFICATION.md:46–49]
10. **No Phase 0 code exists** — `ls /Users/seventyleven/Desktop/Verso/` shows only `docs/`, `README.md`, `research/`. Zero lines of implementation. The resolution is specifying a 9-module architecture for code that has never been used. [VERIFIED via filesystem check]

---

## Recommendation

**Split the decision into two separate decisions:**

**Decision A (PROVIDER ABSTRACTION + FAILOVER — LOCK FOR PHASE 0):** Build now:
- `ProviderProfile` + `OMIT` (D1) — the 5-hook dataclass shape is proven and correct
- `AnthropicProfile` + `OpenAIProfile` + `GoogleProfile` (D1) — the three providers needed for Phase 0 dogfood
- Basic two-axis failover: `ModelPolicy` (simplified — keep `primary`, `models[]`, `providers[]`, `require_parameters`, `on_context_window`) (D3, pruned)
- `require_parameters` enforcement at init (D4) — the 50-line validation that prevents silent loop breakage
- `call_with_retry` with jitter, `attempts=6, initial=4s, max=240s` (D9)
- `force stream_options.include_usage=true` (D8, the 2-line body rewrite)
- `AttemptRecord` + `ProviderResponse` audit trail (D10)
- `ErrorClass` taxonomy (RATE_LIMIT / CONTEXT_WINDOW / CONTENT_POLICY / SERVER_ERROR / TIMEOUT / AUTH / MALFORMED_TOOL) (D3)
- Tool-name sanitization (D9)

This is ~4 files, ~250 lines. It covers the Phase 0 exit criterion. LiteLLM **could** substitute for most of this (providing ~80% coverage with 1 dependency), with ~50 additional lines for `require_parameters` + error-typed routing — but the bespoke ProviderProfile shape is clean enough to build in-house without the LiteLLM dependency, since it's genuinely small.

**Decision B (ADVANCED ROUTING — DEFER TO SPECIFIC PHASES):**

- **D2 PeakEWMA + P2C load balancer:** Defer to Phase 1 exit (when multi-provider concurrent traffic actually exists). Phase 1 deliverable: `balancer.py` + `RoutingState`. The algorithm is known and correct; build it when concurrency makes it useful.
- **D5 BudgetGuard (full):** Phase 0 uses `RunContext.remaining_budget_usd: float` + a simple pre-call check. `BudgetGuard` with `BudgetStore Protocol` + `InMemoryBudgetStore` + `RedisBudgetStore` + `cache_aware_cost()`: defer to Phase 2 (when `submit()` / background jobs exist and Redis becomes meaningful).
- **D6 Learned routers (RoRFRouter, ConfidenceCascade, KNNRouter):** The `LearnedRouter` Protocol (a 3-line interface) can be locked now. The implementations are deferred until: (a) a calibration corpus of 200+ labeled tasks exists from Phase 1 eval runs, (b) it is confirmed which providers expose logprobs for Cascade. Target: Phase 3, as the resolution's own unknown #7 recommends for IRT-Router. The `routers/` sub-package should not be created until an implementation is ready to populate it.
- **D7 `should_reason_step()`:** Defer to Phase 1 exit. Cannot be calibrated without real agent traces. Phase 1 deliverable: instrument the agent loop to log per-step complexity signals; Phase 2 uses those traces to validate and then ship `reasoning.py`.
- **D8 cache-sticky routing:** Defer to Phase 1 (unknown #1 explicitly requires empirical calibration; Phase 1 dogfood gives enough runs to set `CACHE_STICKY_STEPS`). Lock the `RoutingState` dataclass shape now (5 lines); implement `promote_sticky_provider` in Phase 1.

**Verdict: REVISE.** The provider abstraction + failover core (D1, D3 pruned, D4, D8 force-usage, D9, D10) SURVIVES — it is correct and is the simplest thing that works for Phase 0. The load balancer (D2), budget guard (D5), learned routers (D6), reasoning gate (D7), and cache-sticky routing (D8 full) are all premature: they cannot be exercised, validated, or calibrated before Phase 0/1 has been dogfooded. The PRD's own principle ("find the right abstraction by using it, not on paper") demands this deferral. The 9-module layout should be reduced to 4 files for Phase 0, with the remaining modules added phase-by-phase as their preconditions are met.

**The key distinction:** knowing the right eventual architecture (which the RE evidence correctly establishes) is not the same as needing to build it all now. Phase 0 needs a thin provider abstraction and failover. The rest is design-on-paper that competes with the actual work of finding the abstraction cursor through use.
