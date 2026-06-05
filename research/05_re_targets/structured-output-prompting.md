# RE Targets: Structured Output + Prompt-Compiler Libraries

> Category: `structured-output-prompting`
> Written: 2026-06-05
> Relevance anchor: Verso needs a correct, production-grade answer to three questions:
> (1) How do @tool-decorated Python functions get compiled to JSON schemas the model sees?
> (2) How does a structured output (Pydantic/TypedDict/dataclass) flow from model response tokens back to a typed Python object, including streaming partials and repair?
> (3) What is the right seam between "constrained decoding at the inference engine" and "post-hoc parsing + validation" for an agent framework that does NOT own the inference engine?

---

## Already Covered

These products appear in `teardowns/` and have direct structured-output content — no re-RE needed:

- **`teardowns/PYDANTIC_AI.md`** — deep coverage of `_function_schema.py` (Python signature → Pydantic schema → JSON schema, griffe docstring parsing, ctx-param stripping), `_output.py` (output modes: `tool` / `native` / `prompted`, `Partial[T]` streaming with `allow_partial='trailing-strings'`), and the self-healing loop (ValidationError.errors() as the reask prompt). This is the reference implementation for Verso's @tool schema path.

- **`teardowns/SGLANG.md`** — complete coverage of the inference-engine side: compressed-FSM jump-forward decoding (`constrained/outlines_jump_forward.py`), three grammar backends (xgrammar default, outlines, llguidance), per-step vocab bitmask via Triton op, grammar compilation async queue, `SamplingParams.json_schema`/`regex`/`ebnf` fields. Teaches what the serving layer provides; Verso should know what to request from it.

- **`teardowns/DSPY.md`** — detailed coverage of `ChatAdapter` (the `[[ ## field ## ]]` scaffolding + regex parser), `JSONAdapter` fallback (strict `response_format`), `TwoStepAdapter` (reasoning model → cheap extraction model), structured-output schema rewriting (all-required + additionalProperties:false for OpenAI strict mode), and the `dict[str,Any]` downgrade path. Teaches the "prompt-as-schema" compilation pattern Verso needs for its context engineering layer.

---

## RE Targets

### 1. BAML (BoundaryML)

**what**: A domain-specific language (`.baml` files) for declaring LLM functions as typed contracts. A Rust compiler parses `.baml` → emits Python/TS/Go/Ruby clients with a built-in "Schema-Aligned Parsing" (SAP) post-hoc repair parser, type-safe streaming partials, and a VSCode playground for live prompt preview.

**why_for_verso**: SAP is the most carefully engineered post-hoc repair parser in the space and its design directly informs Verso's output-parsing layer. Three specific questions: (a) How does the Rust `jsonish` parser attempt standard JSON → extract from markdown fences → apply heuristic fixes → schema-guided coercion, in that waterfall order? (b) The SAP streaming design uses `@stream.done`/`@stream.not_null`/`@stream.with_state` field annotations — this is the cleanest public API for streaming partial typed objects and Verso needs to decide whether to adopt an equivalent. (c) BAML claims 80% token reduction vs JSON Schema by letting the model write naturally and repairing at parse time — what is the exact accuracy cost vs constrained decoding, and is that tradeoff correct for Verso's use case?

**what_to_RE**: (1) `engine/baml-lib/jsonish/src/` in the monorepo — the Rust `jsonish` parser and SAP core; trace every fallback stage. (2) `engine/baml-lib/baml-core/src/ir/` — how the `.baml` type system compiles to Python `Partial<T>` streaming types. (3) The SAP blog post at `boundaryml.com/blog/schema-aligned-parsing` for the cost-function design (schema-guided edit distance). (4) GitHub issue #998 ("Expose jsonish parser to language bindings") for the boundary between Rust and Python. Skip the VSCode extension and TS codegen.

**source_pointer**: `github.com/BoundaryML/baml` (open-source, MIT) — primary source is `engine/` (Rust). Blog: `boundaryml.com/blog/schema-aligned-parsing`.

**priority**: P0 — SAP vs constrained decoding is a core Verso architecture decision. Verso will not own inference; it must parse model output. The repair parser design + streaming partial type system are the two most replicable patterns here.

---

### 2. Instructor

**what**: The dominant Python library (~3M monthly downloads) for structured LLM output. Patches provider SDK clients (`instructor.from_provider()`), adds `response_model` + `max_retries` parameters, routes through a mode system (TOOLS / JSON / MD_JSON / FUNCTIONS / ANTHROPIC_TOOLS / etc.), and implements a retry/reask loop that feeds `ValidationError.errors()` back to the model.

**why_for_verso**: Instructor has the most battle-tested answer to "what happens when the model ignores your schema." Its mode system is the canonical map of every structured-output API each provider actually supports. Verso needs: (a) the exact mode dispatch logic — how does Instructor decide which of 8+ modes to use for a given provider, and what does each mode send to the wire? (b) the `Partial[T]` streaming implementation — how does it buffer tokens, reconstruct partial JSON, and emit progressively-filled Pydantic objects without requiring a schema-valid chunk? (c) the hooks system (`client.on(PARSE_ERROR, ...)`) as a reference for Verso's observability seam. (d) `InstructorRetryException` — what does it expose per-attempt (attempt N, usage, last error) and can Verso replicate this for its own retry budget?

**what_to_RE**: Install `pip install instructor` and read: `instructor/patch.py` (how `create()` is monkey-patched), `instructor/retry.py` (the reask loop + error feedback construction), `instructor/process_response.py` (mode dispatch → parse → validate), `instructor/dsl/partial.py` (streaming `Partial[T]` implementation). Focus on the retry loop and partial streaming — not on provider-specific adapters.

**source_pointer**: `github.com/jxnl/instructor` (open-source, MIT). Architecture docs at `python.useinstructor.com/architecture/`.

**priority**: P0 — Verso's output-validation retry loop will be directly informed by this. The mode system also tells Verso exactly what structured-output capabilities to request from each provider adapter.

---

### 3. Outlines (dottxt-ai) + outlines-core

**what**: The reference open-source constrained decoding library. `outlines-core` is a Rust crate (PyO3 bindings) that: converts JSON schema → regex via `json_schema::regex_from_str()`, compiles regex → FSM, builds an `Index` (state → allowed token IDs → next state), and exposes `allowed_tokens(state)` for the inference loop. The Python `outlines` library wraps this for local models (Transformers, llama.cpp). The "coalescence" optimization collapses redundant FSM paths (same prefix → keep longest token only) for ~5x speedup over naive masking.

**why_for_verso**: Verso won't implement constrained decoding itself, but it needs to know precisely what the interface contract is between a grammar constraint and an inference engine — because it will pass `json_schema` / `regex` / `ebnf` parameters to providers like SGLang/vLLM/Ollama. Understanding the `Index` data model (state machine over vocab) clarifies what Verso's schema-compilation step must produce. The coalescence insight is also directly relevant to any schema the Verso compiler emits: redundant paths waste inference budget.

**what_to_RE**: (1) `github.com/dottxt-ai/outlines-core` — read `src/` Rust: the `Index` struct, `Vocabulary`, `build_regex_from_schema` pipeline. Focus on the Python-facing API: `Index.allowed_tokens(state)`, `Index.next_state(state, token_id)`. (2) `outlines/fsm/json_schema.py` in the main repo — how Pydantic/TypedDict types are walked to produce the regex. (3) The coalescence blog post at `blog.dottxt.ai/coalescence.html` — the algorithmic insight is short and high-value. Skip the Transformers/llama.cpp backend integration code; Verso doesn't run inference.

**source_pointer**: `github.com/dottxt-ai/outlines` and `github.com/dottxt-ai/outlines-core` (open-source, Apache 2.0). Blog: `blog.dottxt.ai/coalescence.html`.

**priority**: P1 — Verso needs to speak this interface fluently when configuring structured output on local-model backends. The coalescence optimization is also a schema-design lesson. Lower than P0 because Verso won't write the decoding engine.

---

### 4. XGrammar / XGrammar-2

**what**: The default constrained-decoding backend for vLLM, SGLang, TensorRT-LLM, and MLC-LLM. Compiles JSON schema/regex/EBNF → token bitmask (int32 bitset over vocab) with near-zero per-token overhead (~50µs). XGrammar-2 (Jan 2026, arXiv 2601.04426) adds TagDispatch (mid-request structure switching for tool-calling agents), Cross-Grammar Cache (substructure reuse across requests), Earley-based adaptive mask cache (replaces PDA), and JIT compilation. Claims 6x faster compilation than prior art.

**why_for_verso**: XGrammar is the production reality for any Verso user running SGLang/vLLM locally. TagDispatch is directly relevant: an agent that calls tools and then continues generation needs to switch grammars mid-request — Verso needs to know whether to model this as one request with TagDispatch or two sequential requests. The Cross-Grammar Cache also implies Verso should reuse schema objects across agent turns rather than recompiling per call.

**what_to_RE**: (1) arXiv paper 2601.04426 — full read for TagDispatch and Cross-Grammar Cache design. (2) `github.com/mlc-ai/xgrammar` — `python/xgrammar/` and `include/xgrammar/` for the public API: `GrammarCompiler`, `GrammarMatcher`, `apply_token_bitmask_inplace`. (3) `xgrammar.mlc.ai/docs/tutorials/engine_integration.html` — the canonical integration pattern for inference engines. Focus on: what does the engine call at each decode step, what does xgrammar return, and how does TagDispatch change this contract?

**source_pointer**: `github.com/mlc-ai/xgrammar` (open-source, Apache 2.0). Paper: arxiv.org/abs/2601.04426.

**priority**: P1 — Verso needs to generate grammar constraints that xgrammar can compile efficiently. TagDispatch shapes whether Verso models tool-call + continuation as one structured request or two.

---

### 5. Guidance (guidance-ai/guidance + llguidance)

**what**: Microsoft's constrained generation library. `guidance` (Python, 21.5k stars, v0.3.2 Mar 2026) provides a programming model: interleave Python control flow with `gen()` primitives, constrained by regex/CFG, using the `@guidance` decorator for composable programs. The backend is `llguidance` (Rust, open-source) — an Earley parser on top of a lazy regex-derivative lexer, computing token masks dynamically via vocabulary prefix trie traversal at ~50µs per token with negligible startup cost. OpenAI credited llguidance as foundational for their Structured Outputs.

**why_for_verso**: `guidance` is the most explicit published model of "interleave control flow with generation" — which is exactly what Verso's agent loop does. The `@guidance` decorator and `gen()` primitive are the cleanest prior art for composable constrained generation programs. llguidance's lazy mask computation (no pre-compilation) vs outlines-core's eager index build is a key architectural tradeoff: startup cost vs per-token cost. Verso's schema compiler should understand both tradeoffs to pick the right backend for different use cases (short prompt vs repeated schema).

**what_to_RE**: (1) `github.com/guidance-ai/guidance` — read `guidance/library/` for the core primitives: `gen()`, `select()`, `capture()`, `system()`/`user()`/`assistant()` context managers, `@guidance` decorator. Read `guidance/_grammar.py` for how the constraint DSL maps to llguidance inputs. (2) `github.com/guidance-ai/llguidance` — read `src/` Rust: the `LLInterpreter` struct, Earley parser, regex-derivative lexer, prefix trie traversal for mask computation. Focus on the `compute_mask()` call contract. Skip the llama.cpp integration and `transformers` backend code.

**source_pointer**: `github.com/guidance-ai/guidance` (MIT) and `github.com/guidance-ai/llguidance` (MIT). Microsoft Research project page: `microsoft.com/en-us/research/project/guidance-control-lm-output/`.

**priority**: P1 — The `@guidance` programming model is strong prior art for Verso's context-engineering DSL. llguidance's lazy mask computation is relevant if Verso wants to support local models with dynamic schema switching.

---

### 6. Mirascope

**what**: A "minimal-footprint" Python LLM library (self-described "anti-framework"). The `@llm.call("provider/model")` decorator wraps a function as an LLM call; `response_model=SomePydanticModel` triggers structured output via provider-native modes (tool call if supported, JSON mode as fallback). Provider abstraction is explicit and thin — no hidden routing, each provider has its own adapter class. v1 supports Python + TypeScript; observability via Langfuse/OpenTelemetry.

**why_for_verso**: Mirascope is the closest public reference for Verso's own design principle of "explicit, no magic." Its provider adapter pattern (one adapter class per provider, unified interface) directly maps to Verso's pluggable-edges design. The specific question: how does Mirascope decide whether to use `tool_call` vs `json_mode` vs `prompted` structured output for a given provider, and what is the exact wire format for each? This is the decision Verso's output-schema module will make on every agent turn.

**what_to_RE**: Install `pip install mirascope` and read: `mirascope/core/base/_call.py` (the `@llm.call` decorator machinery), `mirascope/core/base/structured_stream.py` (streaming partial typed objects), `mirascope/core/<provider>/` for 2-3 providers (openai, anthropic, google) to see the per-provider structured output dispatch. Focus on the `response_model` path and provider fallback logic — not on the observability integrations.

**source_pointer**: `github.com/Mirascope/mirascope` (open-source, MIT). Docs: `mirascope.com/docs/v1/guides/getting-started/structured-outputs`.

**priority**: P1 — Best open-source reference for a "thin provider abstraction + structured output dispatch" design, which is exactly Verso's pluggable-edges + output schema layer.

---

### 7. Guardrails AI

**what**: Output validation framework (~6.8k stars, v0.10.0 Apr 2026). Declarative RAIL spec (XML-based schema + validator chains), 70+ pre-built validators (PII, factuality, format, domain-specific), composable validator pipelines, corrective actions (fix / reask / filter). Post-generation only — no constrained decoding. Validator architecture: each validator is a Python class with `validate(value, metadata) -> PassResult | FailResult | FixedValue`.

**why_for_verso**: Guardrails is the reference implementation for "output validation as a composable pipeline" — a first-class concern for Verso's reliability layer. The specific lessons: (a) the Validator class contract (validate → pass/fail/fix) is a clean interface Verso should adopt or explicitly reject. (b) the "reask on fail" loop: when a validator fails with a FixedValue vs when it triggers a new LLM call — this is the decision Verso's retry budget logic must encode. (c) 70+ validators = a catalog of what output quality problems agents actually encounter in production.

**what_to_RE**: Install `pip install guardrails-ai` and read: `guardrails/validator_base.py` (the Validator ABC), `guardrails/guard.py` (the Guard pipeline: parse → validate → correct or reask), `guardrails/schema/` (RAIL spec parser + schema types). Read the Hub validator catalog at `hub.guardrailsai.com` for the taxonomy of production output problems. Skip the enterprise telemetry and server mode.

**source_pointer**: `github.com/guardrails-ai/guardrails` (open-source, Apache 2.0). Hub: `hub.guardrailsai.com`.

**priority**: P2 — Verso's reliability layer will need an output validation story, but Guardrails' RAIL spec is heavyweight XML and unlikely to be Verso's approach. The validator contract and reask-on-fail loop are worth stealing; the RAIL spec is not.

---

### 8. LMQL

**what**: ETH Zurich academic project — a Python superset DSL that mixes LLM `generate` calls with Python control flow and `where` constraints (type constraints, regex, `STOPS_AT`, `STOPS_BEFORE`). Compiles to a query plan that batches token generation with constraint checking. Last meaningful commit: May 2024; README update May 2025.

**why_for_verso**: LMQL's `where` constraint syntax is the most explicit published design for mid-generation constraints interleaved with Python logic. Useful as a survey of the design space — what constraints are expressible, how they compose, and what the query-plan compilation looks like. However, the project is effectively in maintenance mode as of mid-2026.

**what_to_RE**: Read `github.com/lmql-lang/lmql` (the ETH research fork) — `src/lmql/language/` for the constraint compiler and `src/lmql/runtime/` for the query execution engine. The LMQL paper (NeurIPS 2023) is the authoritative design document. This is a 2-3 hour read, not a full RE.

**source_pointer**: `github.com/lmql-lang/lmql` (open-source, Apache 2.0). Paper: LMQL NeurIPS 2023.

**priority**: P2 — Academic reference for constraint DSL design. Not a production dependency candidate. Maintenance mode as of 2026.

---

## Notes

**What is NOT worth RE-ing in this category:**

- **jsonformer** — superseded. Pre-dates native structured output APIs; uses `fill-mask` style token forcing that bypasses the autoregressive loop. No production usage in 2026. Replaced by xgrammar/outlines for local models and native APIs for hosted models.

- **Ollama structured output** — Ollama uses llama.cpp's grammar backend (GGML BNF grammar) for constrained generation. The Verso-relevant surface is already covered by the SGLANG teardown's grammar backend section. No dedicated RE needed.

- **SGLang structured** — already covered in `teardowns/SGLANG.md` (see §8, "Sampling + Structured / Guided Decoding").

- **Marvin (PrefectHQ)** — thin wrapper over Instructor/Pydantic AI with `@ai_model` decorator and `cast`/`classify`/`extract` utilities. No novel architecture relative to what Instructor and PydanticAI already teach. Latest release Jan 2026; skip.

**Key architectural decision XGrammar-2 surfaces for Verso:**

TagDispatch (grammar switching mid-request) means Verso should NOT assume one structured-output schema per agent turn. A tool-call turn has structure: `<free text reasoning> + <JSON tool call> + <free text continuation>`. TagDispatch handles this as a single request with a grammar that switches at tag boundaries. Verso's context builder should be aware of this and pass a TagDispatch-compatible grammar spec to the inference engine where supported, rather than splitting into multiple requests.

**The SAP vs constrained-decoding tradeoff Verso must resolve:**

- Constrained decoding (xgrammar/llguidance/outlines): zero invalid tokens, no repair needed, but requires inference-engine integration and penalizes model reasoning (masked tokens can distort distribution). Only works with local models or providers that expose it.
- SAP/post-hoc repair (BAML, Instructor): works with any provider, lets model reason freely, requires a repair parser, has a non-zero failure rate (~6-8% on hard schemas). Verso will need the repair path as a universal fallback even if it uses constrained decoding as the fast path on local models.
