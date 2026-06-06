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


def test_bare_context_word_400_is_other_not_context_window():
    # a 400 that merely mentions "context" must NOT trigger a wasted failover (recheck nit)
    assert classify(HTTPErr(400, "missing required context field")) is FailureKind.OTHER
    # real context-overflow phrasings still classify correctly
    assert classify(HTTPErr(400, "context window exceeded")) is FailureKind.CONTEXT_WINDOW
