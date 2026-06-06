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
    if status == 400 and ("too long" in msg or "context length" in msg
                          or "context window" in msg or "maximum context" in msg):
        return FailureKind.CONTEXT_WINDOW
    if (isinstance(status, int) and 500 <= status < 600) \
            or isinstance(exc, (TimeoutError, ConnectionError)) \
            or "timeout" in msg or "timed out" in msg or "connection" in msg:
        return FailureKind.TRANSIENT
    return FailureKind.OTHER
