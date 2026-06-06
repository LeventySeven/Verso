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
