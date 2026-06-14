# tests/test_model_reliability.py
"""Reliability-engine tests: provider Retry-After honoring (retry.py) and instant failover
(failover.py). Mirrors the sleep-injection style of test_retry.py / test_failover.py — no
test ever sleeps for real."""
import pytest

import verso.model.failover as failover_mod
from verso.model.base import Message, ModelResponse
from verso.model.errors import FailureKind, classify
from verso.model.failover import AllCandidatesFailed, FailoverModel
from verso.model.retry import (
    AttemptRecord,
    RetryPolicy,
    _backoff,
    _retry_after_seconds,
    call_with_retry,
)
from verso.types import Usage


class HTTPErr(Exception):
    def __init__(self, status_code, msg="", **attrs):
        self.status_code = status_code
        for k, v in attrs.items():
            setattr(self, k, v)
        super().__init__(msg or f"HTTP {status_code}")


class _FakeResponse:
    """Minimal stand-in for an SDK response object carrying header mappings."""
    def __init__(self, headers):
        self.headers = headers


def _recorder():
    slept = []

    async def fake_sleep(d):
        slept.append(d)

    return slept, fake_sleep


RESP = ModelResponse(text="ok", tool_calls=[], usage=Usage())


# --- F1: helper unit coverage ------------------------------------------------

def test_retry_after_helper_reads_attribute_int_and_string():
    assert _retry_after_seconds(HTTPErr(429, retry_after=2)) == 2.0
    assert _retry_after_seconds(HTTPErr(429, retry_after="2")) == 2.0
    assert _retry_after_seconds(HTTPErr(429, retry_after=2.5)) == 2.5


def test_retry_after_helper_reads_dashed_attribute():
    exc = HTTPErr(429)
    setattr(exc, "retry-after", "7")          # providers sometimes use the dashed spelling
    assert _retry_after_seconds(exc) == 7.0


def test_retry_after_helper_reads_response_headers_mapping():
    exc = HTTPErr(429)
    exc.response = _FakeResponse({"retry-after": "2"})
    assert _retry_after_seconds(exc) == 2.0
    exc2 = HTTPErr(429)
    exc2.response = _FakeResponse({"retry_after": 3})
    assert _retry_after_seconds(exc2) == 3.0


def test_retry_after_helper_ignores_http_date_and_junk_and_missing():
    assert _retry_after_seconds(HTTPErr(429)) is None                       # no hint
    assert _retry_after_seconds(HTTPErr(429, retry_after="Wed, 21 Oct 2099 07:28:00 GMT")) is None
    assert _retry_after_seconds(HTTPErr(429, retry_after="soon")) is None   # unparseable
    assert _retry_after_seconds(HTTPErr(429, retry_after=True)) is None     # bool is not a duration
    exc = HTTPErr(429)
    exc.response = _FakeResponse({"retry-after": "not-a-number"})
    assert _retry_after_seconds(exc) is None
    exc2 = HTTPErr(429)
    exc2.response = _FakeResponse(headers=None)                             # headers not a mapping
    assert _retry_after_seconds(exc2) is None


# --- F1: call_with_retry honors Retry-After on RATE_LIMIT --------------------

async def test_retry_after_attribute_sleeps_hint_not_backoff():
    # initial is far from the hint so a backoff fallback would be obvious.
    err = HTTPErr(429, retry_after=2)
    calls = {"n": 0}

    async def fn():
        calls["n"] += 1
        if calls["n"] == 1:
            raise err
        return "done"

    records: list[AttemptRecord] = []
    slept, fake_sleep = _recorder()
    out = await call_with_retry(fn, RetryPolicy(max_attempts=3, initial=50.0, jitter=False),
                                records=records, sleep=fake_sleep)
    assert out == "done"
    assert slept == [2.0]                                  # the hint, NOT initial=50.0
    assert [r.kind for r in records] == [FailureKind.RATE_LIMIT, None]
    assert records[0].delay == 2.0                         # bookkeeping reflects the honored hint


async def test_retry_after_via_response_headers_string():
    err = HTTPErr(429)
    err.response = _FakeResponse({"retry-after": "2"})
    calls = {"n": 0}

    async def fn():
        calls["n"] += 1
        if calls["n"] == 1:
            raise err
        return "done"

    slept, fake_sleep = _recorder()
    out = await call_with_retry(fn, RetryPolicy(max_attempts=3, initial=50.0, jitter=False),
                                sleep=fake_sleep)
    assert out == "done"
    assert slept == [2.0]


async def test_retry_after_is_clamped_to_policy_max():
    err = HTTPErr(429, retry_after=99999)                  # absurd provider hint
    calls = {"n": 0}

    async def fn():
        calls["n"] += 1
        if calls["n"] == 1:
            raise err
        return "done"

    slept, fake_sleep = _recorder()
    out = await call_with_retry(fn, RetryPolicy(max_attempts=3, initial=4.0, max=240.0, jitter=False),
                                sleep=fake_sleep)
    assert out == "done"
    assert slept == [240.0]                                # clamped to policy.max


async def test_no_retry_after_header_is_byte_identical_to_backoff():
    # A RATE_LIMIT with NO hint must use _backoff exactly as before (same value, same RNG draw).
    policy = RetryPolicy(max_attempts=2, initial=4.0, max=240.0, jitter=True)
    err = HTTPErr(429)                                     # 429, no retry_after anywhere
    assert classify(err) is FailureKind.RATE_LIMIT

    async def fn():
        raise err

    slept, fake_sleep = _recorder()
    with pytest.raises(HTTPErr):
        await call_with_retry(fn, policy, sleep=fake_sleep, rand=lambda: 0.5)
    # identical to feeding the same policy/attempt/rand straight to _backoff
    assert slept == [_backoff(policy, 1, lambda: 0.5)]


async def test_retry_after_ignored_for_non_rate_limit():
    # A TRANSIENT (503) carrying retry_after must STILL use _backoff (hint only applies to 429s).
    err = HTTPErr(503, retry_after=2)
    assert classify(err) is FailureKind.TRANSIENT

    async def fn():
        raise err

    policy = RetryPolicy(max_attempts=2, initial=4.0, jitter=False)
    slept, fake_sleep = _recorder()
    with pytest.raises(HTTPErr):
        await call_with_retry(fn, policy, sleep=fake_sleep)
    assert slept == [4.0]                                  # _backoff(initial), not the hint


# --- F2: instant failover ----------------------------------------------------

class FailingModel:
    """Test double mirroring test_failover.py: raises `exc` (if set) else returns `response`."""
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


@pytest.fixture
def recording_failover(monkeypatch):
    """Patch failover's call_with_retry to inject a sleep recorder, so we can observe the
    per-candidate backoff sleeps that FailoverModel would otherwise pass to real asyncio.sleep
    (the real sleep is a bound default arg and cannot be monkeypatched in place). Returns the
    shared `slept` list."""
    slept = []

    async def fake_sleep(d):
        slept.append(d)

    real = call_with_retry

    async def wrapper(fn, policy=None, *, records=None, **kw):
        kw.setdefault("sleep", fake_sleep)
        return await real(fn, policy, records=records, **kw)

    monkeypatch.setattr(failover_mod, "call_with_retry", wrapper)
    return slept


async def test_instant_failover_skips_backoff_then_succeeds(recording_failover):
    # First candidate always rate-limited; with a generous retry ladder, instant_failover must
    # NOT burn the ladder before trying the healthy fallback.
    primary = FailingModel(exc=HTTPErr(429))
    fallback = FailingModel(response=RESP)
    fo = FailoverModel([primary, fallback],
                       retry=RetryPolicy(max_attempts=6, initial=4.0, jitter=False))
    out = await fo.complete([Message(role="user", content="hi")], [])
    assert out is RESP
    assert primary.calls == 1 and fallback.calls == 1     # primary tried once, advanced instantly
    assert recording_failover == []                       # zero backoff sleeps before fallback
    # AttemptRecord bookkeeping intact: both candidates recorded.
    assert [r.kind for r in fo.attempts] == [FailureKind.RATE_LIMIT, None]


async def test_instant_failover_false_exhausts_then_advances(recording_failover):
    # The OLD behavior: retry the primary to exhaustion (full backoff ladder) before advancing.
    primary = FailingModel(exc=HTTPErr(429))
    fallback = FailingModel(response=RESP)
    fo = FailoverModel([primary, fallback],
                       retry=RetryPolicy(max_attempts=3, initial=4.0, jitter=False),
                       instant_failover=False)
    out = await fo.complete([], [])
    assert out is RESP
    assert primary.calls == 3 and fallback.calls == 1     # primary retried to exhaustion first
    assert recording_failover == [4.0, 8.0]               # full per-candidate backoff ladder
    # bookkeeping: 3 primary attempts + 1 successful fallback attempt
    assert [r.kind for r in fo.attempts] == [FailureKind.RATE_LIMIT] * 3 + [None]


async def test_last_candidate_keeps_full_budget_under_instant_failover(recording_failover):
    # Even with instant_failover on, the LAST candidate gets the full retry ladder (nowhere
    # left to fail over to).
    primary = FailingModel(exc=HTTPErr(429))
    last = FailingModel(exc=HTTPErr(429))
    fo = FailoverModel([primary, last],
                       retry=RetryPolicy(max_attempts=3, initial=4.0, jitter=False))
    with pytest.raises(AllCandidatesFailed) as ei:
        await fo.complete([], [])
    assert primary.calls == 1                              # primary: instant (1 try, no sleep)
    assert last.calls == 3                                 # last: full ladder (3 tries)
    assert recording_failover == [4.0, 8.0]               # sleeps belong to the LAST candidate only
    # 1 primary attempt + 3 last-candidate attempts all recorded
    assert [r.kind for r in ei.value.attempts] == [FailureKind.RATE_LIMIT] * 4


async def test_instant_failover_default_does_not_break_single_candidate(recording_failover):
    # A lone candidate IS the last candidate → it keeps the full configured budget.
    only = FailingModel(exc=HTTPErr(429))
    fo = FailoverModel([only], retry=RetryPolicy(max_attempts=3, initial=4.0, jitter=False))
    with pytest.raises(AllCandidatesFailed):
        await fo.complete([], [])
    assert only.calls == 3
    assert recording_failover == [4.0, 8.0]
