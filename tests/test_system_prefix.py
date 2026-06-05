# tests/test_system_prefix.py
from verso.model.fake import FakeModel
from verso.model.base import Message, ModelResponse
from verso.model.anthropic import AnthropicModel
from verso.tools.tool import tool
from verso.types import Usage


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


async def test_fake_model_records_system():
    fm = FakeModel([ModelResponse(text="ok", tool_calls=[], usage=Usage())])
    await fm.complete([Message(role="user", content="hi")], [], system="be terse")
    messages, tools, system = fm.calls[0]
    assert system == "be terse"
    assert messages[0].content == "hi"


async def test_fake_model_system_defaults_none():
    fm = FakeModel([ModelResponse(text="ok", tool_calls=[], usage=Usage())])
    await fm.complete([], [])
    assert fm.calls[0][2] is None


class _Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Resp:
    def __init__(self, content, it, ot):
        self.content = content
        self.usage = _Block(input_tokens=it, output_tokens=ot)


class _Msgs:
    def __init__(self, resp):
        self._resp = resp
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return self._resp


class _Client:
    def __init__(self, resp):
        self.messages = _Msgs(resp)


async def test_anthropic_maps_system_param():
    client = _Client(_Resp([_Block(type="text", text="hi")], 1, 1))
    m = AnthropicModel("claude-x", client=client)
    await m.complete([Message(role="user", content="hi")], [add], system="be terse")
    assert client.messages.kwargs["system"] == "be terse"


async def test_anthropic_omits_system_when_none():
    client = _Client(_Resp([_Block(type="text", text="hi")], 1, 1))
    m = AnthropicModel("claude-x", client=client)
    await m.complete([Message(role="user", content="hi")], [add])
    assert "system" not in client.messages.kwargs
