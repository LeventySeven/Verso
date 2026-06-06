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
