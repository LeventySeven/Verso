# Verso — Plan 19: OpenAI-compatible providers (Groq, OpenRouter, … + any base_url)

> The "don't limit the user" principle applied to providers. Almost every LLM provider exposes an **OpenAI-compatible** Chat Completions endpoint — Groq, OpenRouter, Together, Fireworks, DeepSeek, xAI/Grok, Mistral, and local servers (Ollama, vLLM, LM Studio). Each is just the OpenAI wire format at a different `base_url` + API key. So one additive change to `OpenAIModel` (accept `base_url`/`api_key`) unlocks **all of them**, and an `init_model` registry makes the popular ones one-liners — the same approach as Vercel AI SDK (`createOpenAICompatible`), LangChain (`ChatOpenAI(base_url=)`), Pydantic AI (`OpenAIModel(provider=)`). A raw `base_url` (via direct construction or `init_model(..., base_url=)`) means we never cap the user to a fixed list.

**Done (machine-checkable):** `uv run pytest -q` green + `uv run ruff check verso tests` clean — every prior test passes UNMODIFIED. 239 currently pass. Additive: `OpenAIModel("gpt-x")` with no `base_url`/`api_key` constructs `AsyncOpenAI()` exactly as today (byte-identical).

> **STATUS: SHIPPED 2026-06-14.** Both tasks (Batch W) implemented test-first, independently rechecked (APPROVED — every registry `base_url` + env-var verified against live provider docs via WebSearch), and pushed. `uv run pytest -q` → **258 passed, 1 skipped**; `ruff` clean. Recheck Minors applied: Together host updated to the current `api.together.ai/v1`, and a parametrized test now pins every hosted registry entry (base_url + env-key) against regression. Suite stays SDK-free.

**Invariants:** lazy SDK import unchanged (suite stays SDK-free); `None ⇒ omit` (no `base_url`/`api_key` set ⇒ not passed to `AsyncOpenAI`, so env/default resolution is untouched).

---

## ✅ Task 1 — `OpenAIModel` accepts `base_url` + `api_key`  *(Batch W; `verso/model/openai.py`)*

The universal enabler: point the OpenAI client at any compatible endpoint.

- [ ] **Failing test** (`tests/test_openai_compatible.py`): `OpenAIModel("m", base_url="https://x/v1", api_key="k")` stores `.base_url`/`.api_key`; and the lazy `client` property forwards them to the SDK — assert by monkeypatching a fake `openai` module into `sys.modules` whose `AsyncOpenAI(**kw)` records `kw`, then read `model.client` and assert `kw == {"base_url": "https://x/v1", "api_key": "k"}`. A bare `OpenAIModel("m")` ⇒ the recorded `kw == {}` (byte-identical: `AsyncOpenAI()` with no args).
- [ ] **Implement**: add `base_url: str | None = None, api_key: str | None = None` to `__init__` (store them). In the `client` property, build `opts = {}`; `if self.base_url: opts["base_url"] = self.base_url`; `if self.api_key: opts["api_key"] = self.api_key`; `self._client = AsyncOpenAI(**opts)`. Update the class docstring: works with any OpenAI-compatible endpoint (Groq/OpenRouter/Together/Ollama/…); pass `base_url`+`api_key`, or use `init_model("groq:…")`.
- [ ] Run + commit: `feat(model): OpenAIModel base_url/api_key — any OpenAI-compatible endpoint`

## ✅ Task 2 — `init_model` registry of OpenAI-compatible providers + kwargs passthrough  *(Batch W; `verso/__init__.py`)*

Ergonomic one-liners for the popular providers; explicit kwargs override everything.

- [ ] **Failing test** (`tests/test_openai_compatible.py`): `init_model("groq:llama-3.3-70b-versatile")` → an `OpenAIModel` with `.model_id=="llama-3.3-70b-versatile"` and `.base_url=="https://api.groq.com/openai/v1"`; same shape for `openrouter:` (`https://openrouter.ai/api/v1`). With the provider's env var set (monkeypatch `GROQ_API_KEY`), `.api_key` is resolved from it. `init_model("openai:gpt-4o")` still has `.base_url is None` (native, unchanged). `init_model("openai:gpt-4o", base_url="http://localhost:11434/v1", api_key="x")` → kwargs reach the model (the universal local/self-hosted escape). Unknown provider → `ValueError` listing the known set.
- [ ] **Implement** in `verso/__init__.py`:
  - `import os` (top).
  - A module-level registry (prefix → `(base_url, api_key_env)`):
    ```python
    _OPENAI_COMPATIBLE = {
        "openai":     (None, "OPENAI_API_KEY"),
        "groq":       ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
        "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
        "together":   ("https://api.together.xyz/v1", "TOGETHER_API_KEY"),
        "fireworks":  ("https://api.fireworks.ai/inference/v1", "FIREWORKS_API_KEY"),
        "deepseek":   ("https://api.deepseek.com/v1", "DEEPSEEK_API_KEY"),
        "xai":        ("https://api.x.ai/v1", "XAI_API_KEY"),
        "mistral":    ("https://api.mistral.ai/v1", "MISTRAL_API_KEY"),
        "ollama":     ("http://localhost:11434/v1", "OLLAMA_API_KEY"),
    }
    ```
  - `def init_model(spec, **kwargs)`: partition. `anthropic` → `AnthropicModel(model_id, **kwargs)`; `google` → `GoogleModel(model_id, **kwargs)`; `provider in _OPENAI_COMPATIBLE` → build `opts={}`; `base_url, env = registry[provider]`; `if base_url: opts["base_url"]=base_url`; `key = os.environ.get(env)`; for `ollama`, default `key = key or "ollama"` (the SDK requires a non-empty key; local servers ignore it); `if key: opts["api_key"]=key`; `opts.update(kwargs)` (explicit wins); `return OpenAIModel(model_id, **opts)`. Else `raise ValueError(f"unknown provider '{provider}' (supported: anthropic, google, {', '.join(_OPENAI_COMPATIBLE)} — or construct the Model class directly for any OpenAI-compatible base_url)")`.
- [ ] Run + commit: `feat(model): init_model registry for Groq/OpenRouter/Together/… + base_url passthrough`

## Verification plan
**Automated:** `uv run pytest -q && uv run ruff check verso tests` → green; prior tests unmodified; suite needs no `openai`/SDK (lazy import + fake module / attr assertions). 
**Manual (out-of-session, needs keys):** `init_model("groq:llama-3.3-70b-versatile")` and `init_model("openrouter:anthropic/claude-3.5-sonnet")` on a real key + tool-calling task.

## Recheck must verify (against current provider docs — use WebSearch)
Each registry **base_url** and **env-var name** is correct as of mid-2026 (Groq `…/openai/v1`, OpenRouter `…/api/v1`, Together, Fireworks `…/inference/v1`, DeepSeek, xAI `api.x.ai/v1`, Mistral, Ollama `localhost:11434/v1`). A wrong base_url = green tests, broken live ⇒ **Critical**.

## Done criteria
`init_model` builds Anthropic, Google, native OpenAI, AND any OpenAI-compatible provider (Groq/OpenRouter/Together/Fireworks/DeepSeek/xAI/Mistral/Ollama) by name; ANY other compatible endpoint via `base_url`/`api_key`. Additive; lazy; thesis intact. OpenRouter's optional ranking headers (`HTTP-Referer`/`X-Title`) ride the existing `extra_headers`.

## Out of scope
Native non-OpenAI-wire SDKs (e.g. a dedicated `groq` package — the OpenAI-compatible endpoint is the standard path); per-provider model-list validation; live integration tests (need keys).
