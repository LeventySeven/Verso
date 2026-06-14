import json

from verso.model.base import Message, ToolCall
from verso.model.openai import OpenAIModel
from verso.tools.tool import tool_from_schema
from verso.types import Usage


class _Obj:
    """Sets attributes from kwargs — stands in for OpenAI's nested response objects."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _resp(content="hi", tool_calls=None, prompt_tokens=7, completion_tokens=3):
    message = _Obj(content=content, tool_calls=tool_calls)
    return _Obj(
        choices=[_Obj(message=message)],
        usage=_Obj(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


class _Completions:
    def __init__(self, resp):
        self.kwargs = None
        self._resp = resp

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return self._resp


class _Chat:
    def __init__(self, resp):
        self.completions = _Completions(resp)


class _Client:
    def __init__(self, resp=None):
        self.chat = _Chat(resp if resp is not None else _resp())


def _a_tool():
    return tool_from_schema(
        "get_weather", "Look up the weather",
        {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        fn=lambda **kw: None,
    )


async def test_message_and_tool_mapping():
    c = _Client()
    m = OpenAIModel("gpt-x", client=c)
    t = _a_tool()
    args = {"city": "Paris"}
    messages = [
        Message(role="user", content="weather?"),
        Message(role="assistant", content="",
                tool_calls=[ToolCall(id="call_1", name="get_weather", arguments=args)]),
        Message(role="tool", tool_call_id="call_1", content="sunny", name="get_weather"),
    ]
    await m.complete(messages, [t], system="S")
    k = c.chat.completions.kwargs

    # system goes first
    assert k["messages"][0] == {"role": "system", "content": "S"}
    # user
    assert k["messages"][1] == {"role": "user", "content": "weather?"}
    # assistant with one tool call — arguments is a JSON STRING that round-trips to the dict
    asst = k["messages"][2]
    assert asst["tool_calls"][0]["type"] == "function"
    assert asst["tool_calls"][0]["id"] == "call_1"
    assert asst["tool_calls"][0]["function"]["name"] == "get_weather"
    assert isinstance(asst["tool_calls"][0]["function"]["arguments"], str)
    assert json.loads(asst["tool_calls"][0]["function"]["arguments"]) == args
    # tool result
    assert k["messages"][3] == {"role": "tool", "tool_call_id": "call_1", "content": "sunny"}
    # tools schema
    assert k["tools"][0] == {
        "type": "function",
        "function": {"name": "get_weather", "description": "Look up the weather",
                     "parameters": t.parameters},
    }


async def test_response_parsing():
    tc = _Obj(id="call_9", function=_Obj(name="get_weather", arguments='{"a": 1}'))
    c = _Client(_resp(content="hi", tool_calls=[tc], prompt_tokens=11, completion_tokens=5))
    m = OpenAIModel("gpt-x", client=c)
    r = await m.complete([Message(role="user", content="hi")], [])
    assert r.text == "hi"
    assert r.tool_calls[0].id == "call_9"
    assert r.tool_calls[0].name == "get_weather"
    assert r.tool_calls[0].arguments == {"a": 1}        # a dict, not a string
    assert isinstance(r.tool_calls[0].arguments, dict)
    assert r.usage == Usage(input_tokens=11, output_tokens=5)


async def test_no_params_set_sends_none_of_them_byte_identical():
    c = _Client()
    await OpenAIModel("gpt-x", client=c).complete([Message(role="user", content="hi")], [])
    k = c.chat.completions.kwargs
    for key in ("max_tokens", "temperature", "top_p", "stop", "extra_body", "extra_headers"):
        assert key not in k        # additive: unset ⇒ omitted ⇒ minimal request


async def test_all_params_pass_through_when_set():
    c = _Client()
    m = OpenAIModel("gpt-x", client=c, max_tokens=256, temperature=0.2, top_p=0.9,
                    stop=["STOP"], extra_body={"max_completion_tokens": 99},
                    extra_headers={"x-foo": "bar"})
    await m.complete([Message(role="user", content="hi")], [])
    k = c.chat.completions.kwargs
    assert k["max_tokens"] == 256 and k["temperature"] == 0.2 and k["top_p"] == 0.9
    assert k["stop"] == ["STOP"]
    assert k["extra_body"] == {"max_completion_tokens": 99}
    assert k["extra_headers"] == {"x-foo": "bar"}


async def test_no_tools_means_no_tools_key():
    c = _Client()
    await OpenAIModel("gpt-x", client=c).complete([Message(role="user", content="hi")], [])
    assert "tools" not in c.chat.completions.kwargs


def test_init_model_builds_openai():
    from verso import init_model
    m = init_model("openai:gpt-4o")
    assert type(m).__name__ == "OpenAIModel"
    assert m.model_id == "gpt-4o"
