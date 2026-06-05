# tests/test_prune.py
from verso.context.prune import prune, MASK
from verso.model.base import Message, ToolCall


def _tool_msg(i):
    return Message(role="tool", content=f"result-{i}", tool_call_id=f"t{i}", name="add")


def test_no_masking_when_under_window():
    history = [Message(role="user", content="go")] + [_tool_msg(i) for i in range(5)]
    assert prune(history, keep_last_n=10) == history


def test_masks_oldest_tool_outputs_beyond_window():
    history = [_tool_msg(i) for i in range(12)]
    out = prune(history, keep_last_n=10)
    assert out[0].content == MASK and out[1].content == MASK
    assert [m.content for m in out[2:]] == [f"result-{i}" for i in range(2, 12)]


def test_never_masks_non_tool_messages():
    history = [Message(role="user", content="u"),
              Message(role="assistant", content="a", tool_calls=[ToolCall(id="t", name="add", arguments={})])]
    history += [_tool_msg(i) for i in range(12)]
    out = prune(history, keep_last_n=10)
    assert out[0].content == "u"
    assert out[1].content == "a"


def test_preserves_tool_call_id_and_structure_on_masked():
    history = [_tool_msg(i) for i in range(12)]
    out = prune(history, keep_last_n=10)
    assert out[0].tool_call_id == "t0" and out[0].role == "tool" and out[0].name == "add"


def test_idempotent():
    history = [_tool_msg(i) for i in range(12)]
    once = prune(history, keep_last_n=10)
    twice = prune(once, keep_last_n=10)
    assert [m.content for m in once] == [m.content for m in twice]
