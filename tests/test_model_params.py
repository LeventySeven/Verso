from verso.model.anthropic import AnthropicModel
from verso.model.base import Message


class _Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Resp:
    def __init__(self):
        self.content = [_Block(type="text", text="hi")]
        self.usage = _Block(input_tokens=1, output_tokens=1)


class _Msgs:
    def __init__(self):
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return _Resp()


class _Client:
    def __init__(self):
        self.messages = _Msgs()


async def test_sampling_params_pass_through_only_when_set():
    c = _Client()
    m = AnthropicModel("claude-x", client=c, temperature=0.2, top_p=0.9,
                       stop_sequences=["STOP"], thinking={"type": "adaptive"},
                       extra_body={"output_config": {"effort": "high"}},
                       extra_headers={"anthropic-beta": "x"})
    await m.complete([Message(role="user", content="hi")], [])
    k = c.messages.kwargs
    assert k["temperature"] == 0.2 and k["top_p"] == 0.9 and k["stop_sequences"] == ["STOP"]
    assert k["thinking"] == {"type": "adaptive"}
    assert k["extra_body"] == {"output_config": {"effort": "high"}}
    assert k["extra_headers"] == {"anthropic-beta": "x"}


async def test_no_params_set_sends_none_of_them_byte_identical():
    c = _Client()
    await AnthropicModel("claude-x", client=c).complete([Message(role="user", content="hi")], [])
    k = c.messages.kwargs
    for key in ("temperature", "top_p", "stop_sequences", "thinking", "extra_body", "extra_headers"):
        assert key not in k        # additive: unset ⇒ omitted ⇒ byte-identical to today
