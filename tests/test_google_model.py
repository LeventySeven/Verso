from verso.model.base import Message, ToolCall
from verso.model.google import GoogleModel
from verso.tools.tool import tool_from_schema
from verso.types import Usage


class _Obj:
    """Sets attributes from kwargs — stands in for google-genai's nested response objects."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _resp(parts=None, prompt_token_count=7, candidates_token_count=3):
    if parts is None:
        parts = [_Obj(text="hi", function_call=None)]
    content = _Obj(parts=parts)
    return _Obj(
        candidates=[_Obj(content=content)],
        usage_metadata=_Obj(prompt_token_count=prompt_token_count,
                            candidates_token_count=candidates_token_count),
    )


class _Models:
    def __init__(self, resp):
        self.kwargs = None
        self._resp = resp

    async def generate_content(self, **kwargs):
        self.kwargs = kwargs
        return self._resp


class _Aio:
    def __init__(self, resp):
        self.models = _Models(resp)


class _Client:
    """Fake genai.Client — the real google-genai is never imported (lazy + injected)."""
    def __init__(self, resp=None):
        self.aio = _Aio(resp if resp is not None else _resp())


def _a_tool():
    return tool_from_schema(
        "get_weather", "Look up the weather",
        {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        fn=lambda **kw: None,
    )


async def test_message_and_tool_mapping():
    c = _Client()
    m = GoogleModel("gemini-x", client=c)
    t = _a_tool()
    args = {"city": "Paris"}
    messages = [
        Message(role="user", content="weather?"),
        Message(role="assistant", content="",
                tool_calls=[ToolCall(id="call_1", name="get_weather", arguments=args)]),
        Message(role="tool", tool_call_id="call_1", content="sunny", name="get_weather"),
    ]
    await m.complete(messages, [t], system="S")
    k = c.aio.models.kwargs

    assert k["model"] == "gemini-x"
    # user → role "user", parts with a text node
    assert k["contents"][0] == {"role": "user", "parts": [{"text": "weather?"}]}
    # assistant → role "model" with a function_call part; args is the DICT, not a JSON string
    asst = k["contents"][1]
    assert asst["role"] == "model"
    fc_part = asst["parts"][0]
    assert fc_part["function_call"]["name"] == "get_weather"
    assert fc_part["function_call"]["args"] == args
    assert isinstance(fc_part["function_call"]["args"], dict)
    # tool result → role "user" with a function_response keyed by tool NAME, response wrapped in a dict
    tool_msg = k["contents"][2]
    assert tool_msg["role"] == "user"
    fr_part = tool_msg["parts"][0]
    assert fr_part == {"function_response": {"name": "get_weather", "response": {"result": "sunny"}}}
    # system_instruction (a string), not in contents
    assert k["config"]["system_instruction"] == "S"
    # tools → function_declarations shape
    assert k["config"]["tools"] == [
        {"function_declarations": [
            {"name": "get_weather", "description": "Look up the weather", "parameters": t.parameters},
        ]}
    ]


async def test_response_parsing():
    parts = [
        _Obj(text="hi", function_call=None),
        _Obj(text=None, function_call=_Obj(name="f", args={"a": 1})),
    ]
    c = _Client(_resp(parts=parts, prompt_token_count=11, candidates_token_count=5))
    m = GoogleModel("gemini-x", client=c)
    r = await m.complete([Message(role="user", content="hi")], [])
    assert r.text == "hi"
    assert r.tool_calls[0].name == "f"
    assert r.tool_calls[0].arguments == {"a": 1}        # a dict, not a string
    assert isinstance(r.tool_calls[0].arguments, dict)
    assert r.usage == Usage(input_tokens=11, output_tokens=5)


async def test_no_params_set_omits_config_byte_identical():
    c = _Client()
    await GoogleModel("gemini-x", client=c).complete([Message(role="user", content="hi")], [])
    k = c.aio.models.kwargs
    # no system, no tools, no params, no extra_config ⇒ empty config ⇒ omitted entirely
    assert "config" not in k
    assert k["contents"] == [{"role": "user", "parts": [{"text": "hi"}]}]


async def test_all_params_pass_through_when_set():
    c = _Client()
    m = GoogleModel("gemini-x", client=c, max_output_tokens=256, temperature=0.2, top_p=0.9,
                    stop_sequences=["STOP"], extra_config={"seed": 42})
    await m.complete([Message(role="user", content="hi")], [])
    cfg = c.aio.models.kwargs["config"]
    assert cfg["max_output_tokens"] == 256 and cfg["temperature"] == 0.2 and cfg["top_p"] == 0.9
    assert cfg["stop_sequences"] == ["STOP"]
    assert cfg["seed"] == 42


async def test_no_tools_means_no_tools_key():
    c = _Client()
    await GoogleModel("gemini-x", client=c).complete([Message(role="user", content="hi")], [])
    # config is omitted when nothing is set, so there is certainly no tools key
    assert "config" not in c.aio.models.kwargs


def test_init_model_builds_google():
    from verso import init_model
    m = init_model("google:gemini-2.0-flash")
    assert type(m).__name__ == "GoogleModel"
    assert m.model_id == "gemini-2.0-flash"
