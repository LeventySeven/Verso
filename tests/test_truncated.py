# tests/test_truncated.py — provider truncation (max_tokens cut) is surfaced, not silently discarded
from verso.core.loop import run_loop
from verso.model.anthropic import AnthropicModel
from verso.model.base import Message, ModelResponse
from verso.model.fake import FakeModel
from verso.model.google import GoogleModel
from verso.model.openai import OpenAIModel
from verso.types import StopReason, Usage


class _Obj:
    """Sets attributes from kwargs — stands in for the providers' nested response objects."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _async_return(value):
    async def _call(**kwargs):
        return value
    return _call


def test_model_response_truncated_defaults_false():
    # additive field: every existing ModelResponse(...) call stays byte-identical
    assert ModelResponse(text="hi", tool_calls=[], usage=Usage()).truncated is False


# --- OpenAI: finish_reason == "length" ---

def _openai_client(finish_reason):
    msg = _Obj(content="partial answer", tool_calls=None)
    resp = _Obj(choices=[_Obj(message=msg, finish_reason=finish_reason)],
                usage=_Obj(prompt_tokens=5, completion_tokens=5))
    return _Obj(chat=_Obj(completions=_Obj(create=_async_return(resp))))


async def test_openai_truncated_on_length():
    m = OpenAIModel("gpt-x", client=_openai_client("length"))
    assert (await m.complete([Message(role="user", content="hi")], [])).truncated is True


async def test_openai_not_truncated_on_stop():
    m = OpenAIModel("gpt-x", client=_openai_client("stop"))
    assert (await m.complete([Message(role="user", content="hi")], [])).truncated is False


# --- Anthropic: stop_reason == "max_tokens" ---

def _anthropic_client(stop_reason):
    resp = _Obj(content=[_Obj(type="text", text="partial answer")],
                usage=_Obj(input_tokens=5, output_tokens=5), stop_reason=stop_reason)
    return _Obj(messages=_Obj(create=_async_return(resp)))


async def test_anthropic_truncated_on_max_tokens():
    m = AnthropicModel("claude-x", client=_anthropic_client("max_tokens"))
    assert (await m.complete([Message(role="user", content="hi")], [])).truncated is True


async def test_anthropic_not_truncated_on_end_turn():
    m = AnthropicModel("claude-x", client=_anthropic_client("end_turn"))
    assert (await m.complete([Message(role="user", content="hi")], [])).truncated is False


# --- Google/Gemini: finish_reason MAX_TOKENS (enum-with-.name OR bare string) ---

def _google_client(finish_reason):
    cand = _Obj(content=_Obj(parts=[_Obj(text="partial answer", function_call=None)]),
                finish_reason=finish_reason)
    resp = _Obj(candidates=[cand],
                usage_metadata=_Obj(prompt_token_count=5, candidates_token_count=5))
    return _Obj(aio=_Obj(models=_Obj(generate_content=_async_return(resp))))


async def test_google_truncated_on_max_tokens_enum():
    m = GoogleModel("gemini-x", client=_google_client(_Obj(name="MAX_TOKENS")))
    assert (await m.complete([Message(role="user", content="hi")], [])).truncated is True


async def test_google_truncated_on_max_tokens_string():
    m = GoogleModel("gemini-x", client=_google_client("MAX_TOKENS"))
    assert (await m.complete([Message(role="user", content="hi")], [])).truncated is True


async def test_google_not_truncated_on_stop():
    m = GoogleModel("gemini-x", client=_google_client(_Obj(name="STOP")))
    assert (await m.complete([Message(role="user", content="hi")], [])).truncated is False


# --- the signal reaches AgentResult so evals/callers can assert on it ---

async def test_agent_result_surfaces_truncation_on_end_turn():
    fm = FakeModel([ModelResponse(text="cut off mid-", tool_calls=[], usage=Usage(), truncated=True)])
    r = await run_loop(fm, [], "go", max_steps=5)
    assert r.stop_reason is StopReason.END_TURN and r.truncated is True


async def test_agent_result_truncated_defaults_false():
    fm = FakeModel([ModelResponse(text="done", tool_calls=[], usage=Usage())])
    r = await run_loop(fm, [], "go", max_steps=5)
    assert r.truncated is False
