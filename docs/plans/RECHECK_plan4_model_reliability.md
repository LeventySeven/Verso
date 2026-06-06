# RECHECK — Phase 0 Plan 4: Model-Layer Reliability

**Date:** 2026-06-06
**Auditor:** RECHECK (review-only; no code changed)
**Verdict:** **SHIP**

---

## 1. Gate results (exact)

```
$ uv run pytest -q
98 passed, 1 skipped in 0.07s

$ uv run ruff check verso tests
All checks passed!
```

- **Prior baseline preserved:** running with the four new plan-4 test files ignored → `76 passed, 1 skipped` (the plan's stated prereq). No regression.
- **New tests:** `test_errors.py + test_retry.py + test_failover.py + test_failover_e2e.py` → `22 passed`. Total 98 + 1 skipped (the 1 skip is the live-API test, expected).
- **No real sleep in the suite:** every `call_with_retry` test injects `sleep=fake_sleep`; every `FailoverModel` test uses `RetryPolicy(max_attempts=1)` so `call_with_retry` never reaches `await sleep(delay)` (it raises on the final/only attempt first). `grep` for `asyncio.sleep` / `time.sleep` in `tests/` returns nothing; the only production `asyncio.sleep` is the injectable default in `retry.py:38`.

---

## 2. Files reviewed

- `verso/model/errors.py` (FailureKind, classify, RETRYABLE, FAILOVERABLE)
- `verso/model/retry.py` (RetryPolicy, AttemptRecord, _backoff, call_with_retry)
- `verso/model/failover.py` (FailoverModel, AllCandidatesFailed)
- `verso/__init__.py` (exports)
- `verso/core/loop.py`, `verso/agent.py`, `verso/model/base.py` (integration / Protocol)
- Tests: `test_errors.py`, `test_retry.py`, `test_failover.py`, `test_failover_e2e.py`
- `docs/plans/2026-06-06-phase0-plan4-model-reliability.md`, `docs/PRD_v1.md`

---

## 3. Correctness findings (probed, not just read)

### classify() heuristics — PASS (with two documented edge cases)
Live-probed 15 cases via `uv run python`. Confirmed:
- Generic `400 "invalid tool schema"` → **OTHER** (correctly does NOT become CONTEXT_WINDOW, and OTHER is not FAILOVERABLE → correctly does NOT fail over). ✓
- `429` / "overloaded" / "too many requests" → RATE_LIMIT; ordering puts RATE_LIMIT first so `429 "unauthorized rate limit"` → RATE_LIMIT (right). ✓
- `401/403` / "api key" / "authentication" → AUTH; AUTH checked before content-policy and before transient, so `403 "content policy"` → AUTH (defensible — an auth failure shouldn't be treated as a content block). ✓
- `400 + "too long"/"context"/"maximum context"` → CONTEXT_WINDOW (FAILOVERABLE). ✓
- `5xx` (incl. 529) / TimeoutError / ConnectionError / "timeout"/"connection" → TRANSIENT. ✓
- content+policy in message → CONTENT_POLICY (not FAILOVERABLE → raises, correct). ✓

**Edge case A (non-blocking — false positive):** a `400` whose message merely *contains the word* "context" in an unrelated sense (e.g. `"missing context field"`) is classified CONTEXT_WINDOW and would trigger a (wasted) failover. Low severity: consequence is one extra candidate attempt, not data loss; real Anthropic context errors do contain "too long"/"prompt is too long". Could tighten later to require "context length"/"context window"/"too long".

**Edge case B (non-blocking — false negative):** status `408` (Request Timeout) and `409`/`425` etc. are not matched by status; a `408` with no "timeout" word in its message → OTHER → no retry, no failover. Known providers (httpx/anthropic) surface timeouts as `TimeoutError`/5xx, so this rarely bites in practice.

**Edge case C (non-blocking):** `classify` matches `status == 429` / `status in (401,403)` by value equality, so a provider that sets `status_code` as a *string* (`"429"`) would fall through to message/OTHER. Anthropic/httpx use ints, so not a real risk for the one shipped provider.

### call_with_retry backoff + final-attempt off-by-one — PASS
- `_backoff(policy, n, rand)` uses `failed_attempt - 1` exponent → first retry sleeps `initial`, capped at `max`. Verified delays `[4,8,16]` and capped `[100,200,240,240,240]` match tests.
- **No sleep after the last attempt (the off-by-one the brief flagged):** the guard `if kind not in RETRYABLE or n == policy.max_attempts: … raise` runs *before* `await sleep(delay)`. `test_exhausts_max_attempts` (3 attempts → 2 sleeps) and `test_backoff_is_capped_at_max` (6 attempts → 5 sleeps) confirm `len(slept) == max_attempts - 1`. ✓
- **Record/raise consistency:** on the terminal attempt the appended `AttemptRecord` has `delay=0.0` and `kind=classify(exc)`, then the *original* exception is re-raised (bare `raise`, not a wrapper). Records and the raised exception are consistent. ✓
- Jitter is `base * (0.5 + rand())` ∈ [0.5·base, 1.5·base); injected `rand` makes it deterministic in tests. ✓

### FailoverModel lambda default-arg closure — PASS
`lambda c=candidate: c.complete(...)` binds each candidate by value (default-arg), defeating Python's late-binding-in-loop trap. Probed with a 3-candidate chain (503 → 429 → success): each candidate `.complete` called exactly once, success returned. ✓

### Re-raise of the RIGHT exception type — PASS
- On AUTH (and content-policy/other), `FailoverModel.complete` does a bare `raise` of the **original** exception caught from `call_with_retry`, not a wrapper. `test_auth_reraises_without_failover` and `test_agent_raises_on_auth_without_calling_fallback` assert `pytest.raises(HTTPErr)` (the original type) and that the fallback is never called. ✓
- `AllCandidatesFailed` is raised **only when every candidate failed FAILOVERABLY** (the loop only advances past a candidate when `classify(exc) in FAILOVERABLE`; a non-failoverable error short-circuits with `raise` before reaching the end). `from last_exc` preserves the cause chain. `test_all_candidates_fail` (503 then 429) confirms both called + `len(attempts)==2`. ✓

### Thread-safety of per-instance .attempts — NON-BLOCKING (documented)
`self.attempts` is reset (`self.attempts = []`) and appended to during each `complete()`. Probed 50 concurrent `complete()` calls on a single shared `FailoverModel`: the **returned responses are all correct** (the result path is not corrupted), but `model.attempts` is interleaved/last-writer-wins — concurrent readers of the introspection record get garbage. This is an introspection-only race, not a correctness bug on the response. A `FailoverModel` is intended per-agent and the loop calls it sequentially, so this does not affect the shipped path. Worth a one-line docstring note ("not safe to share one instance across concurrent runs if you read `.attempts`"); not a ship blocker.

---

## 4. CORE-GOALS / PRD alignment — PASS

- **Thin reliability core, not a provider abstraction.** Confirmed by grep: no `ProviderProfile`, no `OMIT` sentinel, no `include_usage` forcing, no balancer/PeakEWMA/P2C, no learned router, no budget guard were built (the single `budget` hit is an unrelated token-budget comment in `context/tokens.py`). Only `anthropic.py` + `fake.py` providers exist. This correctly avoids the premature one-provider-abstraction anti-pattern the PRD (lines 87, 216) and the plan's "Out of scope" both call out.
- **Matches PRD §6.4 verbatim:** retry defaults `attempts=6, initial=4s, max=240s` + jitter (PRD line 221) = `RetryPolicy` defaults. "Cross-model failover, not same-model retry … error-typed fallback (context-window vs content-policy vs general)" (line 218) = FAILOVERABLE separating CONTEXT_WINDOW from CONTENT_POLICY. `require_parameters=True` critical-for-tool-agents rationale (line 217) = the `supports_tools` guard in the constructor.
- **FailoverModel is a true drop-in Model.** It structurally satisfies the `Model` Protocol (`async complete(messages, tools, *, system)`); `verso/core/loop.py:40` calls `model.complete(...)` generically with zero knowledge of failover. No Agent/loop changes were needed. Loop stays provider-neutral. ✓

---

## 5. Plan task landing + coverage

- **Task 1 (errors):** landed exactly as specified; 8 tests incl. the two the brief asked about (`test_other_400_is_not_context_window`, membership sets). ✓
- **Task 2 (retry):** landed as specified; 6 tests cover success, backoff sequence, non-retryable immediate raise, max-attempts exhaustion, cap, injected jitter. ✓
- **Task 3 (failover):** landed as specified; 6 tests cover empty-candidates, require_parameters guard, primary-success, rate-limit failover, auth re-raise, all-fail. ✓
- **Task 4 (exports + e2e + README):** all 9 names exported in `__init__.py` `__all__`; 2 e2e tests prove Agent recovery via failover and Agent auth-raise-without-fallback. ✓

**Coverage gaps (non-blocking, additive — not required by the plan):**
- No test asserts CONTEXT_WINDOW *fails over* (it's FAILOVERABLE but only RATE_LIMIT/TRANSIENT failover is exercised). The membership set test covers the classification; the path is the same `in FAILOVERABLE` branch, so risk is low.
- No test for the multi-attempt-then-failover interaction (a candidate that retries N times *then* advances) — all failover tests use `max_attempts=1`. The two modules are independently well-tested; their composition is exercised only at depth 1.
- No test for CONTENT_POLICY re-raising through FailoverModel (only AUTH is asserted as the non-failoverable re-raise). Same branch, low risk.

None of these block ship; they are suggested follow-up tests.

---

## 6. Verdict

**SHIP.** All gates green (98 passed / 1 skipped; ruff clean), 76 prior tests intact, all four tasks landed as specified, PRD-faithful, deferred abstractions correctly NOT built, FailoverModel is a clean drop-in Model with a provider-neutral loop. The off-by-one (no sleep on final attempt), original-exception re-raise, AllCandidatesFailed-only-when-all-failoverable, and lambda late-binding were each verified by probe. The findings (classify edge cases, shared-instance `.attempts` race, three additive test gaps) are non-blocking.
