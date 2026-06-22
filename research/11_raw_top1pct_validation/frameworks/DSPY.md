# DSPy — Raw Extraction (top-1% validation)

Source read: `/Users/seventyleven/Desktop/researchfms/teardowns/DSPY.md` (1566 lines, RE teardown of stanfordnlp/dspy v3.2.1, commit `da1f0871`, MIT, ~51,927 LoC). Omar Khattab + Stanford NLP. Originated "Demonstrate-Search-Predict" (2022).

All findings KNOWN-from-source unless tagged INFERRED. Verso-relation tags applied against VERSO CURRENT STATE.

---

## 1. The core primitive (KNOWN)

> "DSPy's primitive is the `Signature` + the `Module` + the *compiler* (Teleprompter). It is not a prompt-engineering framework; it is a programmatic language for LLM programs and a compiler that *optimizes* those programs." (line 14)

Mental model (lines 18-22):
1. `Signature` = Pydantic-derived class naming typed input/output fields + per-field instructions. `class GenerateAnswer(dspy.Signature): question: str = dspy.InputField(); answer: str = dspy.OutputField()`. String form: `dspy.Signature("context, question -> answer", "Answer questions...")`.
2. `Module` = a `forward()` composing `Predict`/`ChainOfThought`/`ReAct` calls; nestable; share LM via `dspy.configure(lm=...)`.
3. `compile()` with a `Teleprompter` — give it trainset + metric + budget → returns a *modified copy* with optimized prompts/demos baked in.

> "The compiler is the whole point. Without compilation, DSPy is just a slightly-tedious way to call an LLM." (line 22)
> "in classical prompt engineering, the prompt IS the program. In DSPy, the prompt is *generated* by the framework from the Signature, and then *rewritten* by the compiler. The author calls this 'programming, not prompting.'" (line 24)

**What compile mutates (THE key constraint, line 267):** "The optimizer ONLY mutates two things per `Predict` inside the student: (a) `predictor.demos` (list of few-shot examples) and (b) `predictor.signature.instructions` (the docstring on the Signature). Nothing else changes — same code, same module wiring."

---

## 2. Signature mechanics (KNOWN — `signatures/signature.py`, 836 LoC)

- Pydantic `BaseModel` with custom `SignatureMeta` metaclass.
- `instructions` = the class docstring; **mutable at compile time** via `signature.with_instructions(new_str)`.
- `input_fields`/`output_fields` = computed props that partition `model_fields` by JSON-schema-extra marker `__dspy_field_type__ = "input"|"output"`.
- Each output field has a mutable `prefix` (literal "starter token" string in rendered prompt).
- String parse: `_parse_signature()` (line 615); fields default to `str` unless `:type` annotated.

## 3. Adapter — deterministic prompt construction (KNOWN — `chat_adapter.py`, 290 LoC)

- Turns `(Signature, demos, inputs)` → chat-messages list, calls LM, parses response back into typed output dict. "completely deterministic given a signature."
- System message = `format_field_description + format_field_structure + format_task_description`.
- Field-structure marker format: `[[ ## field ## ]]` + a `[[ ## completed ## ]]` terminator.
- Parser: `field_header_pattern = re.compile(r"\[\[ ## (\w+) ## \]\]")` (line 211); each chunk deserialized via `parse_value(value_string, type_annotation)` (handles int/float/bool/list[T]/Pydantic).
- Demos formatted as user/assistant message pairs BEFORE the actual user input.
- **Adapter fallback family (4 adapters, §R2.2):** `ChatAdapter` → `JSONAdapter` (auto fallback on parse failure) → plus explicit `BAMLAdapter`, `XMLAdapter`, `TwoStepAdapter`.
  - `JSONAdapter` uses `json_repair.loads()` not `json.loads` (trailing commas/unescaped quotes/truncation). Then regex `r"\{(?:[^{}]|(?R))*\}"` recursive extraction. Then raise `AdapterParseError`.
  - OpenAI Structured Outputs path: builds Pydantic model from output_fields, `extra="forbid"`, every object gets `additionalProperties:false` + all props required.
  - `BAMLAdapter` (subclasses JSONAdapter): emits BAML-style simplified schema (`#` comments + braced blocks, `Literal["US","CA"]`→`"US" or "CA"`, optional→`T or null`) — more token-efficient than JSON Schema, easier for small models. Refuses recursive Pydantic models.
  - `XMLAdapter`: `<field>value</field>`, parse `r"<(?P<name>\w+)>((?P<content>.*?))</\1>"`.
  - `TwoStepAdapter`: first call free-form text, second cheap LM converts to structured fields (strategy for reasoning models that emit prose).

## 4. Predict / Module / built-ins (KNOWN — `predict/`)

- `Predict.forward`: preprocess (resolve lm+config; **auto-temp: if temperature ≤ 0.15 and n>1 set 0.7**) → `adapter(lm, config, signature, demos, inputs)` → postprocess. `Prediction.from_completions()` wraps outputs; if `settings.trace is not None`, appends `(self, kwargs, prediction)` to trace.
- `named_predictors()` auto-collects each owned Predict via `self.__dict__` introspection — what the compiler iterates.
- `ChainOfThought` (42 LoC): literally `signature.prepend("reasoning", OutputField(desc="${reasoning}"))` + Predict. **"No magic prompt engineering" / "No special 'let me think step by step' prompt"** (line 1243) — the reasoning field just renders before answer in the template.
- `ReAct` (236 LoC): `max_iters=20`; `finish` tool always #1; `next_tool_name` is `Literal[tuple(tool_names)]` constrained output + `next_tool_args: dict[str,Any]`; trajectory dict; on context overflow drops OLDEST tool-call entry, up to 3 truncation attempts; separate `extract` sub-call (a ChainOfThought over fallback_signature) translates trajectory → user output fields.
- `Refine(module, N, reward_fn, threshold)`: N rollouts with `rollout_id = start..start+N-1` at `temperature=1.0`; return first over threshold else best. On all-fail, runs `OfferFeedback` signature producing per-module `advice: dict[str,str]` ("blame and advice") injected into next call — "self-improvement loop, different from retry-with-error-message."
- `ProgramOfThought`/`CodeAct`: generate→execute→regenerate-on-error (max_iters=3)→extract; preloaded `SUBMIT(...)` function signals final output.

## 5. THE OPTIMIZERS / Teleprompters (the unique thing) (KNOWN — `teleprompt/`)

### BootstrapFewShot (`bootstrap.py`, 272 LoC) — the foundation
Algorithm: deepcopy student → teacher (seeded with `LabeledFewShot`, ≤16 random labeled demos). For each trainset example: set `dspy.settings.trace=[]`, run teacher (each inner Predict appends `(predictor, inputs, outputs)`), grade `metric(example, prediction, trace)`; if truthy/≥threshold, every traced inner call becomes `dspy.Example(augmented=True, **inputs, **outputs)` in that predictor's demo bucket. Stop at `max_bootstrapped_demos=4`. Final: `predictor.demos = bootstrapped[:4] + random_labeled[:16-4]`.

**THE TRACE TRICK (line 289, the clever core):** "when a top-level prediction is correct, the *intermediate* predictions that produced it are all assumed correct too, and become demos for those inner predictors. So a multi-step program self-bootstraps demos for every component by just running examples end-to-end and grading the final answer. You never label intermediate steps."

Constants: `max_bootstrapped_demos=4`, `max_labeled_demos=16`, `max_rounds=1`. Rounds 2+ forced to `temperature=1.0` via `lm.copy(rollout_id=round, temperature=1.0)` cache-bypass.

### MIPROv2 (`mipro_optimizer_v2.py`, 866 LoC) — flagship, "Multi-prompt Instruction Proposal + Bayesian search"
Three stages:
- **Stage 1:** `create_n_fewshot_demo_sets` = BootstrapFewShot run `n` times w/ different seeds → n candidate demo-sets per predictor.
- **Stage 2:** `GroundedProposer` uses a meta-LLM to propose `n` new instructions per predictor, "grounded" in: original instructions, **the student program's SOURCE CODE** (`program_aware_proposer=True`), a batch of training data (`data_aware_proposer`, `view_data_batch_size=10`), a randomly-sampled TIP from a tip bank (`tip_aware_proposer`), and bootstrapped demos (`fewshot_aware_proposer`).
- **Stage 3:** Optuna `TPESampler(seed=seed, multivariate=True)` Bayesian search over categorical vars: per predictor an `instruction_idx ∈ [0,n)` and `demo_idx ∈ [0,n)`. Joint space `(n×n)^P`. **Minibatch eval** (`minibatch_size=35`); every `minibatch_full_eval_steps=5` trials, full-eval current best and inject result back as a synthetic Optuna trial.

Constants: `AUTO_RUN_SETTINGS = {light:{n:6,val:100}, medium:{n:12,val:300}, heavy:{n:18,val:1000}}`, `init_temperature=1.0`, `seed=9`, `max_labeled_demos=4` (note: fewer than BootstrapFewShot's 16). num_trials derived: `max(2*num_vars*log2(n), 1.5*n)`. Comment (line 938): "it's generally better to spend optimization budget on few-shot examples when they are allowed" (6 demo candidates vs 3 instruction candidates).

`GroundedProposer` TIPS bank (verbatim, lines 17-24): `creative`, `simple`, `description`, `high_stakes`, `persona` ("Include a persona... 'You are a ...'"). `MAX_INSTRUCT_IN_HISTORY=5`. Signatures: `DescribeProgram`, `DescribeModule`, `GenerateSingleModuleInstruction`.

### COPRO (`copro_optimizer.py`, 355 LoC) — pure instruction optimization, no demos
`BasicGenerateInstruction` ("You are an instruction optimizer for large language models...") then `GenerateInstructionGivenAttempts` (score-sorted history, propose better). `breadth=10, depth=3, init_temperature=1.4`. Optimizes TWO fields: docstring + output-field prefix.

### SIMBA (`simba.py`, 377 LoC) — Stochastic Iterative Mini-Batch Ascent
Bandits + minibatch hill-climbing over a population. Pluggable strategies: `append_a_demo`, `append_a_rule` (extracts a learned NL rule from the model's reasoning on successful examples and injects into system prompt), `propose_new_instructions`.

### GRPO (`grpo.py`, 635 LoC) — RL fine-tuning of the LM WEIGHTS
DeepSeek-style Group Relative Policy Optimization on the underlying LM serving the program. `num_train_steps=100`, `failure_score=0`, `format_failure_score=-1` (partial credit for valid-format-but-wrong). `multitask=True` (shared backbone). Runs via `LocalProvider` (HF) or `DatabricksProvider`.

### GEPA (`teleprompt/gepa/`) — Genetic-Evolutionary Pareto Optimization, LLM-as-judge mutate/crossover on a Pareto frontier (not deeply read).

---

## 6. Models / cache / tools / memory (KNOWN)

- `dspy.LM` = LiteLLM wrapper (`clients/lm.py`, 596 LoC). Format `<provider>/<model>`. Reasoning-model regex `^(?:o[1345](?:-(?:mini|nano|pro))?(?:-\d{4}-\d{2}-\d{2})?|gpt-5(?!-chat)(?:-.*)?)$` forces `temperature=1.0|None`, `max_tokens>=16000|None`, renames to `max_completion_tokens`. `num_retries=3` exponential backoff. `model_type: "chat"|"text"|"responses"`.
- **`rollout_id`** — DSPy-specific cache-key param to re-roll an identical request with a fresh sample while still caching everything else. Cache key = SHA256 of transformed request; callables hashed by `inspect.getsource` (patch a tool body → cache busts). Cache key EXCLUDES api_key/api_base/base_url.
- Two-layer cache: `cachetools.LRUCache(maxsize=1_000_000)` + `diskcache.FanoutCache(shards=16, size_limit=10MB)`. `restrict_pickle` security mode (default pickle = RCE if attacker plants a cache file).
- Tools: `@dspy.tool` extracts name/desc/args via Pydantic introspection. Two paths: native function-calling (`tool.format_as_litellm_function_call()` → OpenAI/Anthropic JSON) OR in-prompt enumeration (ReAct). **No generic sandbox shipped except** `PythonInterpreter` = Deno+Pyodide subprocess with `--allow-read/write/net/env` capability flags (all empty by default), WASM isolation, thread-bound.
- **"DSPy is fundamentally stateless. There is no memory module, no conversation history primitive beyond what your forward threads through."** (line 544). Only `dspy.History` field type, the compile-time `trace` (bounded ~1024, pop-from-front), and serializable compiled state via `dump_state()`/`load_state()`.

---

## 7. HARD JUDGMENT vs Verso (skeptical)

**The compile/optimize idea is research-grade and OFF Verso's thesis.** It requires: a labeled trainset, a numeric metric, a separate validation split, an Optuna dependency, minutes-to-hours of compute, and a meta-LLM that reads your program's source code to rewrite docstrings. That is a *prompt-optimization-as-a-service* product, not "the boring core done right / just build agents." Verso's counter-position ("we don't force the graph", "cut anything that buys ~1% or complexity-for-its-own-sake") applies doubly here: MIPRO/GRPO/SIMBA/GEPA are exactly the "research-cult" machinery Verso refuses. They also collide with Verso NON-GOALS: not a router/planner cult, no learned routers, not the model/kernel (GRPO trains weights).

**However — the SUBSTRATE that makes compilation possible is on-thesis and Verso largely already has it:** typed I/O signatures (≈ Verso `output_type=` + structured output), trace capture (≈ VersoSpan/from_trace), a metric over a captured trajectory (≈ Verso Eval.unit/TrajectoryCheck), and the principle "captured failure IS a regression test." DSPy's optimizer is the layer ABOVE that substrate; Verso has the substrate and chooses (correctly, per thesis) not to build the optimizer.

The few genuinely additive, byte-identical-when-unused mechanisms are tiny utility tricks, NOT the optimizer concept.
