# Verso Phase 0 — Plan 4: Model-Layer Depth (reliability)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the model layer reliable: classify provider failures, retry transient ones with capped exponential backoff + jitter, and fail over across candidate models error-typed (retry-then-advance; raise immediately on auth/content-policy), recording every attempt.

**Architecture:** Three small, provider-neutral pieces that compose with the existing `Model` protocol. `classify(exc) -> FailureKind` maps any provider exception to a kind via status-code + message heuristics. `call_with_retry(fn, policy)` retries only retryable kinds, backing off (injectable `sleep`/`rand` for tests). `FailoverModel([m1, m2, ...])` is itself a `Model`: it `call_with_retry`s each candidate, and on a *failover-able* failure advances to the next; auth/content-policy/other re-raise without trying others. Because `FailoverModel` *is* a `Model`, `Agent`/loop need no changes.

**Tech Stack:** unchanged — Python 3.12 (uv-pinned), Pydantic v2 (not needed here), pytest + `FakeModel`. No new dependencies.

**Prereq:** Plans 1–3 merged and green (`uv run pytest` → 76 passed / 1 skipped). Paths relative to repo root `~/Desktop/Verso`. Run with `uv run`. Commit after every green test.

**Out of scope (deferred to the "2nd provider" plan — by design, to avoid a premature one-provider abstraction):** `ProviderProfile` + `OMIT` 3-state sentinel, per-provider param maps, forcing `include_usage`, OpenAI/Google providers, learned routing, PeakEWMA/P2C load-balancing, budget-Redis. This plan adds reliability around the providers we have, not the provider abstraction.

---

## File Structure

```
verso/
├── model/
│   ├── errors.py     # NEW — FailureKind, classify(), RETRYABLE, FAILOVERABLE
│   ├── retry.py      # NEW — RetryPolicy, AttemptRecord, call_with_retry()
│   └── failover.py   # NEW — FailoverModel, AllCandidatesFailed
└── __init__.py       # MODIFY — export the new names
tests/
├── test_errors.py
├── test_retry.py
├── test_failover.py
└── test_failover_e2e.py
```

---

## Task 1: Error classification

**Files:**
- Create: `verso/model/errors.py`
- Test: `tests/test_errors.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_errors.py
from verso.model.errors import FailureKind, classify, RETRYABLE, FAILOVERABLE


class HTTPErr(Exception):
    def __init__(self, status_code, msg=""):
        self.status_code = status_code
        super().__init__(msg or f"HTTP {status_code}")


def test_rate_limit_by_status():
    assert classify(HTTPErr(429)) is FailureKind.RATE_LIMIT


def test_rate_limit_by_message():
    assert classify(Exception("Overloaded, please slow down")) is FailureKind.RATE_LIMIT


def test_auth():
    assert classify(HTTPErr(401, "invalid x-api-key")) is FailureKind.AUTH
    assert classify(HTTPErr(403)) is FailureKind.AUTH


def test_context_window():
    assert classify(HTTPErr(400, "prompt is too long: 250000 tokens")) is FailureKind.CONTEXT_WINDOW
    assert classify(HTTPErr(400, "maximum context length exceeded")) is FailureKind.CONTEXT_WINDOW


def test_transient_5xx_and_connection():
    assert classify(HTTPErr(503)) is FailureKind.TRANSIENT
    assert classify(TimeoutError("timed out")) is FailureKind.TRANSIENT
    assert classify(ConnectionError("connection reset")) is FailureKind.TRANSIENT


def test_content_policy():
    assert classify(Exception("blocked by content policy")) is FailureKind.CONTENT_POLICY


def test_other_400_is_not_context_window():
    assert classify(HTTPErr(400, "invalid tool schema")) is FailureKind.OTHER


def test_membership_sets():
    assert FailureKind.RATE_LIMIT in RETRYABLE and FailureKind.TRANSIENT in RETRYABLE
    assert FailureKind.AUTH not in RETRYABLE
    assert FailureKind.CONTEXT_WINDOW in FAILOVERABLE and FailureKind.AUTH not in FAILOVERABLE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_errors.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.model.errors'`.

- [ ] **Step 3: Write the implementation**

```python
# verso/model/errors.py
from __future__ import annotations
from enum import Enum


class FailureKind(str, Enum):
    RATE_LIMIT = "rate_limit"
    CONTEXT_WINDOW = "context_window"
    AUTH = "auth"
    TRANSIENT = "transient"          # 5xx / timeout / connection
    CONTENT_POLICY = "content_policy"
    OTHER = "other"


# kinds worth retrying on the SAME candidate
RETRYABLE = frozenset({FailureKind.RATE_LIMIT, FailureKind.TRANSIENT})
# kinds worth advancing to the NEXT candidate (a superset of RETRYABLE)
FAILOVERABLE = frozenset({FailureKind.RATE_LIMIT, FailureKind.TRANSIENT, FailureKind.CONTEXT_WINDOW})


def classify(exc: BaseException) -> FailureKind:
    """Map any provider exception to a FailureKind via status-code + message heuristics."""
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(exc, "status", None)
    msg = str(exc).lower()

    if status == 429 or "rate limit" in msg or "overloaded" in msg or "too many requests" in msg:
        return FailureKind.RATE_LIMIT
    if status in (401, 403) or "api key" in msg or "api-key" in msg or "unauthorized" in msg or "authentication" in msg:
        return FailureKind.AUTH
    if "content" in msg and "policy" in msg:
        return FailureKind.CONTENT_POLICY
    if status == 400 and ("too long" in msg or "context" in msg or "maximum context" in msg):
        return FailureKind.CONTEXT_WINDOW
    if (isinstance(status, int) and 500 <= status < 600) \
            or isinstance(exc, (TimeoutError, ConnectionError)) \
            or "timeout" in msg or "timed out" in msg or "connection" in msg:
        return FailureKind.TRANSIENT
    return FailureKind.OTHER
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_errors.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add verso/model/errors.py tests/test_errors.py
git commit -m "feat(model): FailureKind + classify() (status+message heuristics)"
```

---

## Task 2: Retry with backoff + `AttemptRecord`

**Files:**
- Create: `verso/model/retry.py`
- Test: `tests/test_retry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_retry.py
import pytest
from verso.model.retry import RetryPolicy, AttemptRecord, call_with_retry
from verso.model.errors import FailureKind


class HTTPErr(Exception):
    def __init__(self, status_code, msg=""):
        self.status_code = status_code
        super().__init__(msg or f"HTTP {status_code}")


def _recorder():
    slept = []

    async def fake_sleep(d):
        slept.append(d)

    return slept, fake_sleep


async def test_success_first_try():
    async def fn():
        return "ok"
    records: list[AttemptRecord] = []
    slept, fake_sleep = _recorder()
    out = await call_with_retry(fn, RetryPolicy(), records=records, sleep=fake_sleep)
    assert out == "ok"
    assert slept == []
    assert len(records) == 1 and records[0].kind is None


async def test_retries_transient_then_succeeds_with_backoff():
    calls = {"n": 0}

    async def fn():
        calls["n"] += 1
        if calls["n"] < 4:
            raise HTTPErr(503)
        return "done"

    records: list[AttemptRecord] = []
    slept, fake_sleep = _recorder()
    out = await call_with_retry(fn, RetryPolicy(initial=4.0, max=240.0, jitter=False),
                                records=records, sleep=fake_sleep)
    assert out == "done"
    assert slept == [4.0, 8.0, 16.0]            # exp backoff, no jitter
    assert [r.kind for r in records] == [FailureKind.TRANSIENT] * 3 + [None]


async def test_non_retryable_raises_immediately():
    async def fn():
        raise HTTPErr(401, "bad key")
    records: list[AttemptRecord] = []
    slept, fake_sleep = _recorder()
    with pytest.raises(HTTPErr):
        await call_with_retry(fn, RetryPolicy(), records=records, sleep=fake_sleep)
    assert slept == []
    assert len(records) == 1 and records[0].kind is FailureKind.AUTH


async def test_exhausts_max_attempts():
    async def fn():
        raise HTTPErr(503)
    records: list[AttemptRecord] = []
    slept, fake_sleep = _recorder()
    with pytest.raises(HTTPErr):
        await call_with_retry(fn, RetryPolicy(max_attempts=3, jitter=False),
                              records=records, sleep=fake_sleep)
    assert len(slept) == 2                       # slept between the 3 attempts
    assert len(records) == 3


async def test_backoff_is_capped_at_max():
    async def fn():
        raise HTTPErr(503)
    slept, fake_sleep = _recorder()
    with pytest.raises(HTTPErr):
        await call_with_retry(fn, RetryPolicy(max_attempts=6, initial=100.0, max=240.0, jitter=False),
                              sleep=fake_sleep)
    assert slept == [100.0, 200.0, 240.0, 240.0, 240.0]   # capped


async def test_jitter_uses_injected_rand():
    async def fn():
        raise HTTPErr(503)
    slept, fake_sleep = _recorder()
    with pytest.raises(HTTPErr):
        await call_with_retry(fn, RetryPolicy(max_attempts=2, initial=10.0, jitter=True),
                              sleep=fake_sleep, rand=lambda: 0.5)
    assert slept == [10.0]    # factor = 0.5 + 0.5 = 1.0 -> delay == base
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_retry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.model.retry'`.

- [ ] **Step 3: Write the implementation**

```python
# verso/model/retry.py
from __future__ import annotations
import asyncio
import random
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

from verso.model.errors import RETRYABLE, FailureKind, classify

T = TypeVar("T")


@dataclass
class RetryPolicy:
    max_attempts: int = 6
    initial: float = 4.0
    max: float = 240.0
    jitter: bool = True


@dataclass
class AttemptRecord:
    attempt: int                       # 1-based
    kind: FailureKind | None           # None == this attempt succeeded
    error: str | None
    delay: float                       # seconds slept AFTER this attempt (0 if none)


def _backoff(policy: RetryPolicy, failed_attempt: int, rand: Callable[[], float]) -> float:
    base = min(policy.max, policy.initial * (2 ** (failed_attempt - 1)))
    if policy.jitter:
        return base * (0.5 + rand())   # in [0.5*base, 1.5*base)
    return base


async def call_with_retry(fn: Callable[[], Awaitable[T]], policy: RetryPolicy | None = None, *,
                          records: list[AttemptRecord] | None = None,
                          sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
                          rand: Callable[[], float] = random.random) -> T:
    """Await fn(); retry RETRYABLE failures with capped exponential backoff. Non-retryable
    failures (and the final attempt) re-raise. `sleep`/`rand` are injectable for tests."""
    policy = policy or RetryPolicy()
    last_exc: BaseException | None = None
    for n in range(1, policy.max_attempts + 1):
        try:
            result = await fn()
            if records is not None:
                records.append(AttemptRecord(attempt=n, kind=None, error=None, delay=0.0))
            return result
        except Exception as exc:  # noqa: BLE001 — failures are classified, not swallowed
            kind = classify(exc)
            last_exc = exc
            if kind not in RETRYABLE or n == policy.max_attempts:
                if records is not None:
                    records.append(AttemptRecord(attempt=n, kind=kind, error=str(exc), delay=0.0))
                raise
            delay = _backoff(policy, n, rand)
            if records is not None:
                records.append(AttemptRecord(attempt=n, kind=kind, error=str(exc), delay=delay))
            await sleep(delay)
    assert last_exc is not None  # unreachable (loop always returns or raises)
    raise last_exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_retry.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add verso/model/retry.py tests/test_retry.py
git commit -m "feat(model): call_with_retry + RetryPolicy + AttemptRecord (injectable sleep/rand)"
```

---

## Task 3: `FailoverModel`

**Files:**
- Create: `verso/model/failover.py`
- Test: `tests/test_failover.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_failover.py
import pytest
from verso.model.failover import FailoverModel, AllCandidatesFailed
from verso.model.retry import RetryPolicy
from verso.model.errors import FailureKind
from verso.model.base import Message, ModelResponse
from verso.types import Usage


class HTTPErr(Exception):
    def __init__(self, status_code, msg=""):
        self.status_code = status_code
        super().__init__(msg or f"HTTP {status_code}")


class FailingModel:
    """Test double: raises `exc` (if set) else returns `response`."""
    def __init__(self, exc=None, response=None, supports_tools=True):
        self.exc = exc
        self.response = response
        self.supports_tools = supports_tools
        self.calls = 0

    async def complete(self, messages, tools, *, system=None):
        self.calls += 1
        if self.exc is not None:
            raise self.exc
        return self.response


RESP = ModelResponse(text="ok", tool_calls=[], usage=Usage())
ONE = RetryPolicy(max_attempts=1)   # no sleeping in tests


def test_empty_candidates_raises():
    with pytest.raises(ValueError):
        FailoverModel([])


def test_require_parameters_rejects_tool_incapable_candidate():
    bad = FailingModel(response=RESP, supports_tools=False)
    with pytest.raises(ValueError):
        FailoverModel([bad], require_parameters=True)
    # but allowed when require_parameters is off
    FailoverModel([bad], require_parameters=False)


async def test_primary_success_no_failover():
    primary = FailingModel(response=RESP)
    fallback = FailingModel(response=RESP)
    fo = FailoverModel([primary, fallback], retry=ONE)
    out = await fo.complete([Message(role="user", content="hi")], [])
    assert out is RESP
    assert primary.calls == 1 and fallback.calls == 0


async def test_failover_on_rate_limit_then_succeeds():
    primary = FailingModel(exc=HTTPErr(429))
    fallback = FailingModel(response=RESP)
    fo = FailoverModel([primary, fallback], retry=ONE)
    out = await fo.complete([], [])
    assert out is RESP
    assert primary.calls == 1 and fallback.calls == 1
    assert [r.kind for r in fo.attempts] == [FailureKind.RATE_LIMIT, None]


async def test_auth_reraises_without_failover():
    primary = FailingModel(exc=HTTPErr(401, "bad key"))
    fallback = FailingModel(response=RESP)
    fo = FailoverModel([primary, fallback], retry=ONE)
    with pytest.raises(HTTPErr):
        await fo.complete([], [])
    assert primary.calls == 1 and fallback.calls == 0


async def test_all_candidates_fail():
    a = FailingModel(exc=HTTPErr(503))
    b = FailingModel(exc=HTTPErr(429))
    fo = FailoverModel([a, b], retry=ONE)
    with pytest.raises(AllCandidatesFailed) as ei:
        await fo.complete([], [])
    assert a.calls == 1 and b.calls == 1
    assert len(ei.value.attempts) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_failover.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.model.failover'`.

- [ ] **Step 3: Write the implementation**

```python
# verso/model/failover.py
from __future__ import annotations
from typing import Sequence

from verso.model.base import Message, Model, ModelResponse
from verso.model.errors import FAILOVERABLE, classify
from verso.model.retry import AttemptRecord, RetryPolicy, call_with_retry
from verso.tools.tool import Tool


class AllCandidatesFailed(Exception):
    def __init__(self, attempts: list[AttemptRecord]):
        self.attempts = attempts
        super().__init__("all model candidates failed; see .attempts")


class FailoverModel:
    """A Model that tries candidates in order, retrying each (call_with_retry) and advancing
    to the next on a FAILOVERABLE failure. AUTH/content-policy/other re-raise immediately."""

    def __init__(self, candidates: Sequence[Model], *, retry: RetryPolicy | None = None,
                 require_parameters: bool = True):
        if not candidates:
            raise ValueError("FailoverModel needs at least one candidate")
        if require_parameters:
            for c in candidates:
                if getattr(c, "supports_tools", True) is False:
                    raise ValueError("require_parameters=True but a candidate cannot use tools")
        self.candidates = list(candidates)
        self.retry = retry or RetryPolicy()
        self.attempts: list[AttemptRecord] = []   # from the most recent complete()

    async def complete(self, messages: Sequence[Message], tools: Sequence[Tool],
                       *, system: str | None = None) -> ModelResponse:
        self.attempts = []
        last_exc: BaseException | None = None
        for candidate in self.candidates:
            try:
                return await call_with_retry(
                    lambda c=candidate: c.complete(messages, tools, system=system),
                    self.retry, records=self.attempts,
                )
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if classify(exc) not in FAILOVERABLE:
                    raise                      # auth/content-policy/other → do not try others
                # else: advance to the next candidate
        raise AllCandidatesFailed(self.attempts) from last_exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_failover.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add verso/model/failover.py tests/test_failover.py
git commit -m "feat(model): FailoverModel — error-typed retry-then-advance across candidates"
```

---

## Task 4: Exports + Agent integration e2e + README

**Files:**
- Modify: `verso/__init__.py`
- Test: `tests/test_failover_e2e.py`
- Modify: `README.md`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_failover_e2e.py
import pytest
from verso import Agent, FailoverModel, RetryPolicy
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse
from verso.types import Usage


class HTTPErr(Exception):
    def __init__(self, status_code, msg=""):
        self.status_code = status_code
        super().__init__(msg or f"HTTP {status_code}")


class FailingModel:
    def __init__(self, exc):
        self.exc = exc
        self.calls = 0

    async def complete(self, messages, tools, *, system=None):
        self.calls += 1
        raise self.exc


async def test_agent_recovers_via_failover():
    primary = FailingModel(HTTPErr(429, "rate limit"))
    fallback = FakeModel([ModelResponse(text="recovered", tool_calls=[], usage=Usage())])
    fo = FailoverModel([primary, fallback], retry=RetryPolicy(max_attempts=1))
    result = await Agent(model=fo).run("hi")
    assert result.output == "recovered"
    assert primary.calls == 1
    assert any(r.kind is None for r in fo.attempts)        # fallback succeeded


async def test_agent_raises_on_auth_without_calling_fallback():
    primary = FailingModel(HTTPErr(401, "bad api key"))
    fallback = FakeModel([ModelResponse(text="unreached", tool_calls=[], usage=Usage())])
    fo = FailoverModel([primary, fallback], retry=RetryPolicy(max_attempts=1))
    with pytest.raises(HTTPErr):
        await Agent(model=fo).run("hi")
    assert primary.calls == 1
    assert len(fallback.calls) == 0                        # FakeModel.calls is a list
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_failover_e2e.py -v`
Expected: FAIL — `ImportError: cannot import name 'FailoverModel' from 'verso'`.

- [ ] **Step 3: Update `verso/__init__.py`**

Add these imports and append the names to `__all__`:

```python
from verso.model.failover import FailoverModel, AllCandidatesFailed
from verso.model.retry import RetryPolicy, AttemptRecord, call_with_retry
from verso.model.errors import FailureKind, classify
```

Append to `__all__`: `"FailoverModel"`, `"AllCandidatesFailed"`, `"RetryPolicy"`, `"AttemptRecord"`, `"call_with_retry"`, `"FailureKind"`, `"classify"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_failover_e2e.py -v`
Expected: 2 passed.

- [ ] **Step 5: Run the full suite + lint**

Run: `uv run pytest -q` → all green (live skipped). Then `uv run ruff check verso tests` → clean.

- [ ] **Step 6: Append to `README.md` Quickstart (before `## Status`)**

````markdown
**Reliability** — retry + cross-model failover, error-typed:

```python
from verso import Agent, FailoverModel, RetryPolicy, init_model

model = FailoverModel(
    [init_model("anthropic:claude-sonnet-4-6"), init_model("anthropic:claude-opus-4-8")],
    retry=RetryPolicy(max_attempts=6, initial=4.0, max=240.0),
)
agent = Agent(model=model)
# transient errors + rate limits retry with backoff, then fail over to the next candidate;
# auth / content-policy errors raise immediately (no blind retry). Every try is in model.attempts.
```
````

- [ ] **Step 7: Commit**

```bash
git add verso/__init__.py tests/test_failover_e2e.py README.md
git commit -m "feat(model): export reliability layer + Agent failover e2e + README"
```

---

## Done criteria (Plan 4)

- `uv run pytest -q` green (live skipped); `uv run ruff check verso tests` clean.
- `classify(exc)` maps 429→RATE_LIMIT, 401/403→AUTH, 400+"too long/context"→CONTEXT_WINDOW, 5xx/timeout/connection→TRANSIENT, content-policy→CONTENT_POLICY, else OTHER.
- `call_with_retry` retries only RETRYABLE kinds with capped exponential backoff (verified delays, no real sleep in tests via injected `sleep`), re-raises non-retryable immediately, and records every attempt.
- `FailoverModel` is a drop-in `Model`: an `Agent` with one recovers from a primary rate-limit via the fallback, and raises on auth without touching the fallback; `model.attempts` reflects the path.

## Deferred to later plans
`ProviderProfile` + `OMIT` 3-state sentinel + per-provider param maps + a 2nd provider (OpenAI/Google) + forced `include_usage` (build the abstraction once 2+ providers exist, not before); learned routing + PeakEWMA/P2C load-balancing + budget guard (Phase 2). Then: streaming (Plan 5) completes Phase 0.
