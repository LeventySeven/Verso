# tests/test_durable_serde.py
from verso.model.base import Message, ToolCall
from verso.durable.serde import msg_to_dict, msg_from_dict
from verso.durable.context import RunContext, Hitl, Paused, HumanRequest


def test_message_round_trips_including_tool_calls():
    msgs = [
        Message(role="user", content="add 1 and 2"),
        Message(role="assistant", content="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})]),
        Message(role="tool", content="3", tool_call_id="t1", name="add"),
    ]
    restored = [msg_from_dict(msg_to_dict(m)) for m in msgs]
    assert restored == msgs                      # dataclass equality — every field survived


def test_hitl_request_raises_paused_with_the_prompt():
    ctx: RunContext[None] = RunContext(trace_id="x")
    assert isinstance(ctx.hitl, Hitl)
    import pytest
    with pytest.raises(Paused) as ei:
        ctx.hitl.request("approve the refund?", key="refund")
    assert isinstance(ei.value.request, HumanRequest)
    assert ei.value.request.prompt == "approve the refund?" and ei.value.request.key == "refund"
