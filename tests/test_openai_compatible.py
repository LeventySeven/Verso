"""OpenAI-compatible provider support (Plan 19 Batch W).

`OpenAIModel` reaches any OpenAI wire-format endpoint via base_url + api_key, and `init_model`
carries a registry of such providers (Groq, OpenRouter, Together, …) plus a kwargs escape hatch.

The `openai` SDK is NOT installed, and these tests must not require it. Two techniques:
  - attribute/registry assertions construct the model and read stored fields (no SDK touched);
  - the client-forwarding tests inject a fake `openai` module into ``sys.modules`` so the lazy
    ``from openai import AsyncOpenAI`` resolves to a recorder.
"""
import sys
import types

import pytest

from verso import init_model
from verso.model.openai import OpenAIModel


def _install_fake_openai(monkeypatch):
    """Replace the `openai` module with a fake whose AsyncOpenAI records its kwargs."""
    calls = {}

    class _FakeAsyncOpenAI:
        def __init__(self, **kw):
            calls["kw"] = kw

    mod = types.ModuleType("openai")
    mod.AsyncOpenAI = _FakeAsyncOpenAI
    monkeypatch.setitem(sys.modules, "openai", mod)
    return calls


# ---------------------------------------------------------------------------
# Client forwarding (fake SDK)
# ---------------------------------------------------------------------------

def test_base_url_and_api_key_forwarded_to_client(monkeypatch):
    calls = _install_fake_openai(monkeypatch)
    m = OpenAIModel("m", base_url="https://x/v1", api_key="k")
    _ = m.client
    assert calls["kw"] == {"base_url": "https://x/v1", "api_key": "k"}


def test_default_client_is_byte_identical_bare_constructor(monkeypatch):
    calls = _install_fake_openai(monkeypatch)
    m = OpenAIModel("m")
    _ = m.client
    # OMIT discipline: nothing set ⇒ AsyncOpenAI() with no kwargs, exactly as before this batch.
    assert calls["kw"] == {}


def test_only_base_url_forwarded_when_key_unset(monkeypatch):
    calls = _install_fake_openai(monkeypatch)
    m = OpenAIModel("m", base_url="https://x/v1")
    _ = m.client
    assert calls["kw"] == {"base_url": "https://x/v1"}


# ---------------------------------------------------------------------------
# init_model registry (no SDK needed — only stored attributes are read)
# ---------------------------------------------------------------------------

def test_groq_registry_base_url_and_model_id():
    m = init_model("groq:llama-3.3-70b-versatile")
    assert type(m).__name__ == "OpenAIModel"
    assert m.model_id == "llama-3.3-70b-versatile"
    assert m.base_url == "https://api.groq.com/openai/v1"


def test_groq_registry_picks_up_api_key_from_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gk")
    m = init_model("groq:llama-3.3-70b-versatile")
    assert m.api_key == "gk"
    assert m.base_url == "https://api.groq.com/openai/v1"


def test_openrouter_registry_model_id_keeps_slash_after_first_colon():
    # partition(":") splits on the FIRST colon only, so a slash-bearing model id survives intact.
    m = init_model("openrouter:anthropic/claude-3.5-sonnet")
    assert m.base_url == "https://openrouter.ai/api/v1"
    assert m.model_id == "anthropic/claude-3.5-sonnet"


def test_native_openai_unchanged_base_url_none():
    # Byte-identical to before this batch: openai has no base_url override.
    m = init_model("openai:gpt-4o")
    assert type(m).__name__ == "OpenAIModel"
    assert m.model_id == "gpt-4o"
    assert m.base_url is None


def test_kwargs_escape_overrides_for_local_endpoint():
    # The self-hosted / local escape: explicit kwargs win over the registry defaults.
    m = init_model("openai:gpt-4o", base_url="http://localhost:11434/v1", api_key="x")
    assert m.base_url == "http://localhost:11434/v1"
    assert m.api_key == "x"


def test_ollama_gets_dummy_api_key_when_unset(monkeypatch):
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    m = init_model("ollama:llama3")
    # Local servers ignore the key, but the OpenAI SDK requires a non-empty one.
    assert m.api_key == "ollama"
    assert m.base_url == "http://localhost:11434/v1"


def test_ollama_real_key_overrides_dummy(monkeypatch):
    monkeypatch.setenv("OLLAMA_API_KEY", "real")
    m = init_model("ollama:llama3")
    assert m.api_key == "real"


@pytest.mark.parametrize("provider, model, base_url, env", [
    ("groq", "llama-3.3-70b-versatile", "https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    ("openrouter", "anthropic/claude-3.5-sonnet", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    ("together", "meta-llama/Llama-3.3-70B", "https://api.together.ai/v1", "TOGETHER_API_KEY"),
    ("fireworks", "accounts/fireworks/models/llama-v3", "https://api.fireworks.ai/inference/v1", "FIREWORKS_API_KEY"),
    ("deepseek", "deepseek-chat", "https://api.deepseek.com/v1", "DEEPSEEK_API_KEY"),
    ("xai", "grok-2", "https://api.x.ai/v1", "XAI_API_KEY"),
    ("mistral", "mistral-large-latest", "https://api.mistral.ai/v1", "MISTRAL_API_KEY"),
])
def test_registry_base_url_and_env_key_resolution(provider, model, base_url, env, monkeypatch):
    # pins every hosted registry entry: the exact base_url AND that init_model resolves api_key from its env var.
    # guards against a typo'd URL/env-var in the registry (a wrong base_url = green tests, broken live).
    monkeypatch.setenv(env, f"{provider}-key")
    m = init_model(f"{provider}:{model}")
    assert type(m).__name__ == "OpenAIModel"
    assert m.model_id == model
    assert m.base_url == base_url
    assert m.api_key == f"{provider}-key"


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        init_model("nope:x")


def test_existing_anthropic_init_still_works():
    # kwargs passthrough didn't break the original anthropic path.
    m = init_model("anthropic:claude-x")
    assert type(m).__name__ == "AnthropicModel"
    assert m.model_id == "claude-x"
