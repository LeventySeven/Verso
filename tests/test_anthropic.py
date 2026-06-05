# tests/test_anthropic.py
from verso.model.anthropic import AnthropicModel
from verso.model.base import Message
from verso.tools.tool import tool


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


class _Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Resp:
    def __init__(self, content, input_tokens, output_tokens):
        self.content = content
        self.usage = _Block(input_tokens=input_tokens, output_tokens=output_tokens)


class FakeAnthropicMessages:
    def __init__(self, resp):
        self._resp = resp
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return self._resp


class FakeAnthropicClient:
    def __init__(self, resp):
        self.messages = FakeAnthropicMessages(resp)


async def test_maps_text_response():
    resp = _Resp([_Block(type="text", text="hello")], input_tokens=10, output_tokens=3)
    client = FakeAnthropicClient(resp)
    m = AnthropicModel("claude-x", client=client)
    out = await m.complete([Message(role="user", content="hi")], [add])
    assert out.text == "hello"
    assert out.tool_calls == []
    assert out.usage.input_tokens == 10 and out.usage.output_tokens == 3
    # tools were mapped into the request
    assert client.messages.kwargs["tools"][0]["name"] == "add"
    assert client.messages.kwargs["tools"][0]["input_schema"]["properties"]["a"]["type"] == "integer"


async def test_maps_tool_use_response():
    resp = _Resp(
        [_Block(type="tool_use", id="tu1", name="add", input={"a": 1, "b": 2})],
        input_tokens=5, output_tokens=4,
    )
    m = AnthropicModel("claude-x", client=FakeAnthropicClient(resp))
    out = await m.complete([Message(role="user", content="add")], [add])
    assert len(out.tool_calls) == 1
    tc = out.tool_calls[0]
    assert tc.id == "tu1" and tc.name == "add" and tc.arguments == {"a": 1, "b": 2}


async def test_maps_assistant_and_tool_messages_into_request():
    from verso.model.base import ToolCall
    resp = _Resp([_Block(type="text", text="ok")], 1, 1)
    client = FakeAnthropicClient(resp)
    m = AnthropicModel("claude-x", client=client)
    history = [
        Message(role="user", content="add 1 and 2"),
        Message(role="assistant", content="", tool_calls=[ToolCall(id="tu1", name="add", arguments={"a": 1, "b": 2})]),
        Message(role="tool", content="3", tool_call_id="tu1", name="add"),
    ]
    await m.complete(history, [add])
    sent = client.messages.kwargs["messages"]
    # assistant turn carries a tool_use block; tool turn becomes a user tool_result block
    assert sent[1]["role"] == "assistant"
    assert sent[1]["content"][0]["type"] == "tool_use"
    assert sent[2]["role"] == "user"
    assert sent[2]["content"][0]["type"] == "tool_result"
    assert sent[2]["content"][0]["tool_use_id"] == "tu1"
