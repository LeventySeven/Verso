from __future__ import annotations

from verso import Agent, tool
from verso.safety.hooks import Hooks, PermissionDecision
from verso.stream.events import EventType
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


@tool
def send_email(to: str) -> str:
    "Send an email."
    return f"sent to {to}"


async def test_stream_honors_pre_tool_deny_and_still_completes():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="send_email", arguments={"to": "x@y.z"})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    agent = Agent(model=fm, tools=[send_email], hooks=Hooks(pre_tool=[lambda c: PermissionDecision.DENY]))
    events = [ev async for ev in agent.stream("email x")]
    tool_results = [ev for ev in events if ev.type == EventType.TOOL_RESULT]
    # the denial surfaces as a failed tool-result the model can react to (decision.value is "deny", NOT "denied"):
    assert tool_results and tool_results[0].ok is False
    assert "deny" in tool_results[0].content.lower() and "did not run" in tool_results[0].content.lower()
    assert "sent to" not in tool_results[0].content          # the tool did NOT run
    assert events[-1].type == EventType.DONE and events[-1].result.output == "done"
