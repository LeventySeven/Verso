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
