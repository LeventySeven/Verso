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


async def test_anthropic_system_carries_one_ephemeral_cache_breakpoint():
    client = _Client(_Resp([_Block(type="text", text="hi")], 1, 1))
    m = AnthropicModel("claude-x", client=client)
    await m.complete([Message(role="user", content="hi")], [add], system="be terse")
    system = client.messages.kwargs["system"]
    # system is now a content-block list with ONE ephemeral cache breakpoint on the (last) block;
    # render order tools→system→messages means this single breakpoint caches the tools+system prefix.
    assert isinstance(system, list) and len(system) == 1
    assert system[-1]["text"] == "be terse"                       # system text preserved
    assert system[-1]["cache_control"] == {"type": "ephemeral"}
    # exactly one breakpoint — tools are NOT separately marked (the system block already covers them)
    assert all("cache_control" not in t for t in client.messages.kwargs["tools"])


async def test_anthropic_omits_system_when_none_but_caches_tool_prefix():
    client = _Client(_Resp([_Block(type="text", text="hi")], 1, 1))
    m = AnthropicModel("claude-x", client=client)
    await m.complete([Message(role="user", content="hi")], [add])
    assert "system" not in client.messages.kwargs
    # with no system, the single breakpoint moves to the last tool so the tool prefix still caches
    tools = client.messages.kwargs["tools"]
    assert tools[-1]["cache_control"] == {"type": "ephemeral"}
    assert tools[-1]["name"] == "add"                             # tool definition intact
