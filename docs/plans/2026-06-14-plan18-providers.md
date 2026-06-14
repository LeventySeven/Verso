# Verso — Plan 18: Second & third model providers (OpenAI, Google)

> Verso is Anthropic-only today (`init_model` wires just `anthropic`; the PRD §13 scoped Anthropic/OpenAI/Google but only the first shipped). The `Model` Protocol (`complete(messages, tools, *, system) -> ModelResponse`) is the swappable seam — adding providers behind it removes provider lock-in, the most concrete "don't limit the user" gap left. On-thesis (a thin adapter per provider, no new abstraction), additive (existing code/tests untouched), and held to the SAME test bar as the shipped `AnthropicModel`: a **fake client** captures the outbound kwargs and feeds a canned response, so the suite needs no network and no provider SDK installed.

**Honesty caveat (state it in the report + docs):** these adapters are **unit-tested against a fake client** (the mapping is pinned), exactly like `AnthropicModel` — they are NOT exercised against the live OpenAI/Google APIs in-session. The mapping reflects the well-known Chat Completions / Gemini shapes; `extra_body`/config passthrough is the escape hatch for anything model-specific.

**Done (machine-checkable):** `uv run pytest -q` green + `uv run ruff check verso tests` clean — every prior test passes UNMODIFIED. 227 currently pass.

> **STATUS: SHIPPED 2026-06-14.** Both batches implemented test-first, independently rechecked (APPROVED — the OpenAI mapping verified field-by-field against the Chat Completions contract; the Gemini mapping verified against the live `google-genai` docs, including the config-as-dict question), and pushed. `uv run pytest -q` → **239 passed, 1 skipped**; `ruff` clean. The suite stays SDK-free (lazy imports + injected fake clients). Honesty: unit-tested to the `AnthropicModel` bar, **not** run against live OpenAI/Google APIs in-session.

**Invariants:**
- The adapter imports its SDK **lazily** (only in the `client` property), so importing `verso` and running the suite never requires `openai`/`google-genai`. Tests inject `client=`.
- `None ⇒ omit` (the OMIT discipline) for every optional param, so a bare `OpenAIModel("gpt-x")` sends only `model` + `messages` (+ `tools` when present).
- Streaming needs NO new code: `AnthropicModel` has no `stream`, so `iter_model_stream` already wraps `complete()` for any provider. Do not add a `stream` method.

---

## ✅ Task 1 — `OpenAIModel` (Chat Completions)  *(Batch U; `verso/model/openai.py` + `init_model` + `pyproject`)*

Mirror `AnthropicModel` (read it — same constructor shape, lazy `client` property, OMIT loop, `extra_body`/`extra_headers`). Map Verso's internal message/tool format → OpenAI Chat Completions.

- [ ] **Failing test** (`tests/test_openai_model.py`, fake-client style — copy the `_Block`/`_Client` pattern from `tests/test_model_params.py`, adapted to the nested `client.chat.completions.create` + `resp.choices[0].message` shape):
  - **mapping**: `complete([... user, assistant-with-tool_calls, tool ...], [a_tool], system="S")` captures kwargs where `messages[0]=={"role":"system","content":"S"}`; the assistant turn carries `tool_calls=[{"id":..,"type":"function","function":{"name":..,"arguments": <JSON string>}}]`; the tool turn is `{"role":"tool","tool_call_id":..,"content":..}`; and `tools==[{"type":"function","function":{"name","description","parameters"}}]`.
  - **response parsing**: a canned response with `content="hi"` + one tool_call `arguments='{"a": 1}'` → `ModelResponse.text=="hi"`, `tool_calls[0].arguments=={"a":1}` (parsed to a dict), `usage==Usage(input_tokens=prompt_tokens, output_tokens=completion_tokens)`.
  - **OMIT / byte-identical**: bare `OpenAIModel("gpt-x", client=c)` sends none of `max_tokens/temperature/top_p/stop/extra_body/extra_headers`; setting them sends them through. `complete(..., [])` (no tools) ⇒ `"tools" not in kwargs`.
  - **init_model**: `init_model("openai:gpt-4o")` returns an `OpenAIModel` with `.model_id=="gpt-4o"`.
- [ ] **Implement** `verso/model/openai.py`:
  - `__init__(self, model_id, *, client=None, max_tokens=None, temperature=None, top_p=None, stop=None, extra_body=None, extra_headers=None)` — store all; `self._client=client`. (Note `max_tokens` defaults **None** here, unlike Anthropic's 4096: OpenAI doesn't require it, and forcing it breaks o-series `max_completion_tokens`. Document: set `max_tokens=` or use `extra_body={"max_completion_tokens": N}` for o-series.)
  - `client` property: lazy `from openai import AsyncOpenAI; self._client = AsyncOpenAI()`.
  - `_to_openai_messages(messages, system)`: prepend `{"role":"system","content":system}` when `system`; `user`→`{"role":"user","content":m.content}`; `assistant`→`{"role":"assistant","content": m.content or None}` plus `"tool_calls"` (id/type=function/function{name, arguments=`json.dumps(tc.arguments)`}) when `m.tool_calls`; `tool`→`{"role":"tool","tool_call_id":m.tool_call_id,"content":m.content}`.
  - `_to_openai_tools(tools)`: `[{"type":"function","function":{"name":t.name,"description":t.description,"parameters":t.parameters}}]`.
  - `complete`: build `kwargs={"model","messages"}`; add `tools` only when `tools`; OMIT-loop over `(("max_tokens",..),("temperature",..),("top_p",..),("stop",..))`; add `extra_body`/`extra_headers` when truthy; `resp = await self.client.chat.completions.create(**kwargs)`. Parse `msg = resp.choices[0].message`; `text = msg.content or ""`; `tool_calls=[ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments) if tc.function.arguments else {}) for tc in (getattr(msg,"tool_calls",None) or [])]`; `usage=Usage(input_tokens=resp.usage.prompt_tokens, output_tokens=resp.usage.completion_tokens)`.
  - `verso/__init__.py` `init_model`: add `if provider == "openai": from verso.model.openai import OpenAIModel; return OpenAIModel(model_id)`. Update the error string to list `'anthropic'|'openai'`.
  - `pyproject.toml`: add `openai = ["openai>=1.40"]` to `[project.optional-dependencies]`.
- [ ] Run + commit: `feat(model): OpenAIModel (Chat Completions) behind the Model Protocol + init_model openai:`

## ✅ Task 2 — `GoogleModel` (Gemini, `google-genai`)  *(Batch V; `verso/model/google.py` + `init_model` + `pyproject`)*

Same seam, Gemini shape. Gemini uses role `"model"` (not `"assistant"`), a separate `system_instruction`, `contents` with `parts`, and `function_call`/`function_response` parts. Use the current `google-genai` SDK (`from google import genai`), async via `client.aio.models.generate_content`.

- [ ] **Failing test** (`tests/test_google_model.py`, fake-client): `complete` maps user→`{"role":"user","parts":[{"text":..}]}`, assistant→`role:"model"` with `function_call` parts for tool_calls, tool→`function_response` part; system goes to the request `config.system_instruction`; tools → `function_declarations`. Response parsing: a candidate with a text part + a `function_call` part → `ModelResponse` with text + `ToolCall(arguments=<dict>)`; usage from `usage_metadata` (`prompt_token_count`/`candidates_token_count`). OMIT discipline; `init_model("google:gemini-2.0-flash")` → `GoogleModel`.
- [ ] **Implement** `verso/model/google.py` mirroring Task 1's structure (lazy `from google import genai; genai.Client()`; map to `contents` + `config`); `init_model` `google:` branch; `pyproject` `google = ["google-genai>=0.3"]`. Keep a raw `extra_config: dict | None` passthrough (the Gemini escape hatch). **If the live `google-genai` async surface differs from the mapping, implement what the SDK docs specify and note any uncertainty in the report — do not guess silently.**
- [ ] Run + commit: `feat(model): GoogleModel (Gemini) behind the Model Protocol + init_model google:`

## Verification plan
**Automated:** `uv run pytest -q && uv run ruff check verso tests` → green; prior tests unmodified; suite runs with NO `openai`/`google-genai` installed (lazy import + injected fake client). 
**Manual (out-of-session, needs keys):** `init_model("openai:gpt-4o")` / `("google:gemini-2.0-flash")` against a real key on a tool-calling task.

## Done criteria
`init_model` builds Anthropic, OpenAI, and Google models; each maps Verso's message/tool format to its provider and back to `ModelResponse`; all behind the unchanged `Model` Protocol (so `Agent`, `FailoverModel`, streaming, evals work unchanged). Additive; thesis intact (thin adapter, no new abstraction). Honesty: unit-tested to the `AnthropicModel` bar, not live-verified in-session.

## Out of scope
Live integration tests (need keys/network); provider-native streaming deltas (the `complete()`-wrapping fallback already streams); a provider-specific cache breakpoint for OpenAI/Google (Anthropic-only feature today); `init_model` sugar for passing params (construct the model class directly, per Plan 16).
