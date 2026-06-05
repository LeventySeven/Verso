# tests/test_bundle.py
from verso.context.bundle import ContextBundle
from verso.model.base import Message, ToolCall
from verso.tools.tool import tool


@tool
def add(a: int, b: int) -> int:
    "Add two integers."
    return a + b


def _bundle():
    return ContextBundle(
        instructions="be terse",
        history=[
            Message(role="user", content="add 1 and 2"),
            Message(role="assistant", content="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})]),
            Message(role="tool", content="3", tool_call_id="t1", name="add"),
        ],
        tools=[add],
    )


def test_system_is_instructions():
    assert _bundle().system == "be terse"


def test_to_messages_is_a_copy_of_history():
    b = _bundle()
    msgs = b.to_messages()
    assert msgs == b.history
    msgs.append(Message(role="user", content="x"))
    assert len(b.history) == 3  # mutating the copy must not touch the bundle


def test_sections_and_total():
    b = _bundle()
    s = b.sections()
    assert set(s) == {"instructions", "tools", "history"}
    assert all(isinstance(v, int) for v in s.values())
    assert b.estimate_tokens() == sum(s.values())


def test_stable_prefix_is_byte_identical_across_different_history():
    b1 = _bundle()
    b2 = _bundle()
    b2.history = b2.history + [Message(role="user", content="another turn")]
    assert b1.stable_prefix() == b2.stable_prefix()   # prefix (system+tools) unaffected by history


def test_tool_schema_text_is_deterministic():
    b = _bundle()
    assert b.tool_schema_text() == b.tool_schema_text()
    assert '"name": "add"' in b.tool_schema_text()


def test_render_shows_system_tools_and_turns():
    out = _bundle().render()
    assert "[system]" in out and "be terse" in out
    assert "[tools]" in out
    assert "[user] add 1 and 2" in out
    assert "add(" in out  # the tool call is rendered
