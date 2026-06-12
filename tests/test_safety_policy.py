from verso import Agent, tool
from verso.safety.hooks import Hooks, PermissionDecision as PD
from verso.safety.policy import (
    PermissionPolicy, PermissionRule, allow_all, ask_every, ask_once, confidence_router,
)
from verso.durable.inmem import InMemoryCheckpointStore
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage, StopReason


def test_policy_first_matching_rule_wins_else_default():
    p = PermissionPolicy(rules=[
        PermissionRule(lambda c: c[0] == "delete_db", PD.DENY),
        PermissionRule(lambda c: c[0] == "send_email", PD.ASK),
    ], default=PD.ALLOW)
    assert p(("delete_db", {})) == PD.DENY               # first match wins
    assert p(("send_email", {})) == PD.ASK
    assert p(("read_file", {})) == PD.ALLOW              # no rule matched → default


def test_allow_all_and_ask_every():
    assert allow_all()(("anything", {})) == PD.ALLOW
    gate = ask_every("send_email")
    assert gate(("send_email", {})) == PD.ASK and gate(("read", {})) == PD.ALLOW
    assert ask_every()(("anything", {})) == PD.ASK       # no names → gate every tool


def test_ask_once_gates_first_call_then_allows():
    gate = ask_once("send_email")
    assert gate(("send_email", {})) == PD.ASK            # first time → ask
    assert gate(("send_email", {})) == PD.ALLOW          # subsequent → allow (approve-once UX)
    assert gate(("read", {})) == PD.ALLOW                # ungated tool is always allowed


def test_confidence_router_thresholds():
    scores = {"safe": 0.9, "iffy": 0.5, "risky": 0.1}
    route = confidence_router(lambda c: scores[c[0]], ask_below=0.7, deny_below=0.3)
    assert route(("safe", {})) == PD.ALLOW
    assert route(("iffy", {})) == PD.ASK
    assert route(("risky", {})) == PD.DENY


async def test_policy_as_pre_tool_hook_composes_with_the_durable_pause():
    # a session-mode preset plugged straight into hooks.pre_tool drives the Plan-10 durable pause
    @tool
    def send_email(to: str) -> str:
        "Send."
        return f"sent to {to}"

    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="send_email", arguments={"to": "x"})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    agent = Agent(model=fm, tools=[send_email], hooks=Hooks(pre_tool=[ask_every("send_email")]),
                  checkpointer=InMemoryCheckpointStore())
    paused = await agent.run("email")
    assert paused.stop_reason == StopReason.PAUSED and paused.pending.tool_name == "send_email"
