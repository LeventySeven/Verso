# tests/test_recheck_fix2.py — Plan 21 FIX-2: model adapters don't crash on real provider response shapes
from verso.model.errors import classify, FailureKind
from verso.model.openai import OpenAIModel
from verso.model.google import GoogleModel
from verso.model.base import Message
from verso.types import Usage


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


# --- classify(): the SDK timeout/connection types do NOT subclass the builtins ---
class APIConnectionError(Exception):
    pass


class APITimeoutError(APIConnectionError):
    pass


def test_classify_sdk_connection_by_typename_even_with_odd_message():
    # without the type-name check these route to OTHER (NOT retried, NOT failed-over)
    assert classify(APIConnectionError("Network is unreachable")) == FailureKind.TRANSIENT
    assert classify(APITimeoutError("deadline exceeded")) == FailureKind.TRANSIENT


def test_classify_builtin_timeout_still_transient():
    assert classify(TimeoutError("x")) == FailureKind.TRANSIENT


def _openai(resp):
    class _Compl:
        async def create(self, **kw):
            return resp
    return OpenAIModel("m", client=_Obj(chat=_Obj(completions=_Compl())))


async def test_openai_usage_none_does_not_crash():
    # vLLM/Ollama/proxies return usage=null on non-streaming completions
    resp = _Obj(choices=[_Obj(message=_Obj(content="hi", tool_calls=None))], usage=None)
    r = await _openai(resp).complete([Message(role="user", content="x")], [])
    assert r.text == "hi" and r.usage == Usage()


async def test_openai_malformed_tool_args_recover_via_jsonish():
    tc = _Obj(id="t1", function=_Obj(name="f", arguments='{"a": 1,}'))   # trailing comma
    resp = _Obj(choices=[_Obj(message=_Obj(content="", tool_calls=[tc]))],
                usage=_Obj(prompt_tokens=1, completion_tokens=1))
    r = await _openai(resp).complete([Message(role="user", content="x")], [])
    assert r.tool_calls[0].arguments == {"a": 1}     # recovered, not a crash


async def test_openai_unfixable_tool_args_degrade_to_empty():
    tc = _Obj(id="t1", function=_Obj(name="f", arguments="totally not json"))
    resp = _Obj(choices=[_Obj(message=_Obj(content="", tool_calls=[tc]))],
                usage=_Obj(prompt_tokens=1, completion_tokens=1))
    r = await _openai(resp).complete([Message(role="user", content="x")], [])
    assert r.tool_calls[0].arguments == {}


def _google(resp):
    class _Models:
        async def generate_content(self, **kw):
            return resp
    return GoogleModel("g", client=_Obj(aio=_Obj(models=_Models())))


async def test_google_empty_candidates_does_not_crash():
    # Gemini returns zero candidates on a safety/recitation block
    resp = _Obj(candidates=[], usage_metadata=_Obj(prompt_token_count=3, candidates_token_count=0))
    r = await _google(resp).complete([Message(role="user", content="x")], [])
    assert r.text == "" and r.tool_calls == [] and r.usage == Usage(input_tokens=3, output_tokens=0)


async def test_google_none_candidates_does_not_crash():
    resp = _Obj(candidates=None, usage_metadata=_Obj(prompt_token_count=2, candidates_token_count=0))
    r = await _google(resp).complete([Message(role="user", content="x")], [])
    assert r.text == "" and r.tool_calls == []
