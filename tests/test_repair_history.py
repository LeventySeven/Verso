# tests/test_repair_history.py
# repair_history makes a (crash-recovered / forked / hand-built) message history a valid provider
# payload — no-op on healthy history, and converts the structural faults that cause cryptic resume-400s.
from verso.context.history import repair_history
from verso.model.base import Message, ToolCall


def _asst(*ids):
    return Message(role="assistant", content="", tool_calls=[ToolCall(id=i, name="t", arguments={}) for i in ids])


def _res(i, c="ok"):
    return Message(role="tool", tool_call_id=i, name="t", content=c)


def _shape(h):
    return [(m.role, m.tool_call_id) for m in h]


def test_healthy_history_is_unchanged():
    h = [Message(role="user", content="hi"), _asst("a"), _res("a"), Message(role="assistant", content="done")]
    assert _shape(repair_history(h)) == _shape(h)


def test_healthy_multi_call_turn_preserves_order():
    h = [_asst("a", "b"), _res("a"), _res("b")]
    assert _shape(repair_history(h)) == [("assistant", None), ("tool", "a"), ("tool", "b")]


def test_orphan_tool_call_gets_synthetic_result():
    out = repair_history([_asst("a", "b"), _res("a")])          # 'b' never answered (crash mid-turn)
    tool_ids = [m.tool_call_id for m in out if m.role == "tool"]
    assert tool_ids == ["a", "b"]
    synth = next(m for m in out if m.tool_call_id == "b")
    assert "interrupted" in synth.content


def test_orphan_tool_result_is_dropped():
    out = repair_history([_asst("a"), _res("a"), _res("zzz")])  # 'zzz' has no matching tool_call
    assert all(m.tool_call_id != "zzz" for m in out)


def test_duplicate_result_id_deduped_first_wins():
    out = repair_history([_asst("a"), _res("a", "first"), _res("a", "second")])
    a = [m for m in out if m.role == "tool" and m.tool_call_id == "a"]
    assert len(a) == 1 and a[0].content == "first"


def test_no_tool_calls_history_is_untouched():
    h = [Message(role="user", content="hi"), Message(role="assistant", content="hello")]
    assert _shape(repair_history(h)) == _shape(h)
