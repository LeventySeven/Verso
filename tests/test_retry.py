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
