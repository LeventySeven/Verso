# verso/model/retry.py
from __future__ import annotations
import asyncio
import random
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping, TypeVar

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


def _coerce_seconds(value: Any) -> float | None:
    """Accept an int/float (seconds) or a numeric string; reject HTTP-dates / junk."""
    if isinstance(value, bool):            # bool is an int subclass; not a duration
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())    # numeric string ("2", "2.5"); HTTP-date -> ValueError
        except ValueError:
            return None
    return None


def _retry_after_seconds(exc: BaseException) -> float | None:
    """Duck-type a provider Retry-After hint off the exception (seconds).

    Looks (in order) at ``exc.retry_after`` / ``getattr(exc, "retry-after")`` and at
    ``exc.response.headers["retry_after" | "retry-after"]`` (a mapping). Returns the parsed
    seconds, or ``None`` when absent / an HTTP-date / otherwise unparseable (caller falls
    back to ``_backoff``). Providers differ (Anthropic/OpenAI/Groq), hence the duck-typing."""
    for name in ("retry_after", "retry-after"):
        secs = _coerce_seconds(getattr(exc, name, None))
        if secs is not None:
            return secs
    headers = getattr(getattr(exc, "response", None), "headers", None)
    if isinstance(headers, Mapping):
        for key in ("retry_after", "retry-after"):
            secs = _coerce_seconds(headers.get(key))
            if secs is not None:
                return secs
    return None


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
            if kind is FailureKind.RATE_LIMIT:
                hint = _retry_after_seconds(exc)        # honor provider Retry-After on 429s
                if hint is not None:
                    delay = min(max(hint, 0.0), policy.max)   # clamp to [0, policy.max]
            if records is not None:
                records.append(AttemptRecord(attempt=n, kind=kind, error=str(exc), delay=delay))
            await sleep(delay)
    assert last_exc is not None  # unreachable (loop always returns or raises)
    raise last_exc
