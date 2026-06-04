# Agent loop anatomy + compound AI systems

## LLM Powered Autonomous Agents (Lilian Weng) — https://lilianweng.github.io/posts/2023-06-23-agent/ — read

### Core architecture framing
- LLM functions as the agent's brain; three complementary subsystems: Planning, Memory, Tool Use
- Planning = subgoal decomposition + self-reflection/refinement
- Memory = short-term (in-context) + long-term (external vector store)
- Tool Use = external APIs, code execution, proprietary data access
- This three-way split is the canonical anatomy; every named system in the post maps onto it

### Planning — decomposition

**Chain of Thought (CoT)** (Wei et al. 2022)
- Mechanism: prompt model with "think step by step" — uses test-time compute to break complex tasks into manageable steps
- Side effect: interpretability into reasoning process
- Baseline that every later technique extends

**Tree of Thoughts (ToT)** (Yao et al. 2023)
- Extends CoT by exploring multiple reasoning branches at each step → tree structure
- Search: BFS or DFS across branches
- State evaluation: classifier prompts or majority voting
- When to use: tasks where multiple solution paths exist and evaluation is cheap

**Task decomposition methods (three flavors):**
1. LLM prompted directly: `"Steps for XYZ.\n1."` or `"What are the subgoals for achieving X?"`
2. Task-specific instructions baked into prompt: `"Write a story outline first"`
3. Human provides the decomposition; agent executes sub-steps

**LLM+P** (Liu et al. 2023)
- Delegates planning to a classical PDDL planner rather than LLM
- Three-stage: translate problem to PDDL → classical planner generates plan → convert back to NL
- Rationale: classical planners guarantee optimality in well-defined domains; LLMs do not

### Planning — self-reflection / self-correction

**ReAct** (Yao et al. 2023)
- The foundational loop: interleaves Thought → Action → Observation, repeating
- Action space = task-specific discrete actions UNION free-form language
- Prompt format:
  ```
  Thought: <reasoning about current state>
  Action: <tool call or action>
  Observation: <result returned>
  ```
- Demonstrated: outperforms Act-only baseline on HotpotQA, FEVER (knowledge-intensive) AND AlfWorld Env, WebShop (decision-making)
- Critical property: reasoning and acting are interleaved, not sequential phases

**Reflexion** (Shinn & Labash 2023)
- Adds dynamic memory + self-reflection on top of ReAct
- RL framing: binary reward model + heuristic function h_t detecting bad trajectories
- h_t fires on two failure modes:
  1. Inefficiency: trajectory too long without success
  2. Hallucination: consecutive identical actions yield same observation (loop detection)
- Reflection generation: two-shot examples (failed trajectory → ideal reflection)
- Working memory: stores up to 3 reflections; older ones are evicted
- Empirical finding: hallucination failure more common than inefficiency in AlfWorld
- Key insight: separating "act" from "reflect" lets the model learn from its own failures within a single session without retraining

**Chain of Hindsight (CoH)** (Liu et al. 2023)
- Trains the model to improve from past outputs by presenting sequences: `(prompt, completion_i, human_rating_i, feedback_i, …)`
- Ranked by reward; model learns to prefer higher-rated completions
- Training: SFT with log-likelihood regularization on pre-training data (prevents overfitting)
- Masking: randomly masks 0–5% of past tokens → prevents shortcutting/copying
- Data sources: WebGPT comparisons, human feedback summarization, preference datasets

**Algorithm Distillation (AD)** (Laskin et al. 2023)
- Extends CoH to cross-episode RL trajectories
- Encapsulates a learning algorithm in a long history-conditioned policy (not just a single solution)
- Behavioral cloning over action sequences from source policies
- Key requirement: 2–4 episodes of history necessary for near-optimal in-context RL learning
- Result: AD approaches RL² upper bound despite offline-only training; faster convergence than ED/source baselines
- Emerges as in-context RL — the model learns to improve across tries within a context window

### Memory — types and implementation

| Memory type | Human analog | Duration | LLM implementation |
|---|---|---|---|
| Sensory | Raw input | ~seconds | Embedding representations of raw inputs |
| Short-term / working | Active workspace | 20–30 sec, ~7 items (Miller 1956) | In-context learning — bounded by Transformer context window |
| Long-term explicit | Episodic/semantic | Days–decades, unlimited | External vector store with fast retrieval (MIPS) |
| Long-term implicit | Procedural | — | Procedural/skill knowledge baked into weights |

- Core tradeoff: in-context memory has full attention power but hard limit; vector stores are unlimited but retrieval is approximate and loses cross-attention over the full corpus
- Standard practice: save embedding representations to a vector database; retrieve top-k at each turn

**Maximum Inner Product Search (MIPS) — approximate NN algorithms:**

LSH (Locality-Sensitive Hashing)
- Maps similar vectors to same buckets with high probability; bucket_count << input_count

ANNOY (Spotify)
- Random projection trees (binary trees); non-leaf nodes are hyperplanes; search traverses all trees and aggregates
- Related to KD-tree but more scalable

HNSW (Hierarchical Navigable Small World)
- Inspired by six-degrees-of-separation networks
- Hierarchical layer graph: upper layers = shortcuts for large jumps; lower layers = precise refinement
- Search: start at random top-layer node, navigate toward target, descend when stuck

FAISS (Facebook)
- Assumes high-dimensional distances follow Gaussian distribution with natural clustering
- Two-pass: coarse vector quantization finds candidate clusters; fine quantization within clusters

ScaNN (Google Research)
- Innovation: anisotropic vector quantization — quantizes x_i to x̃_i such that ⟨q, x_i⟩ ≈ ⟨q, x̃_i⟩ (optimizes for inner product, not Euclidean distance)
- Benchmark: best recall@10 of all listed algorithms (2020)

Key ANN principle: "sacrifice minor accuracy for a huge speedup" — all production retrieval systems make this trade

### Tool use

**MRKL Systems** (Karpas et al. 2022)
- "Modular Reasoning, Knowledge and Language" — neuro-symbolic architecture
- LLM routes to expert modules (neural or symbolic: calculator, converter, API)
- Empirical finding: 7B Jurassic1-large failed to reliably extract arithmetic arguments from verbal math → tool routing requires sufficient model capability; small models fail at the routing step even when the tool itself would solve the problem
- Quote: "Knowing when and how to use the tools are crucial, determined by the LLM capability"

**TALM / Toolformer** (Parisi 2022, Schick 2023)
- Fine-tune LM to use external tool APIs; annotate API calls inline in training data
- Dataset expansion via newly added API annotations improves output quality
- ChatGPT Plugins and OpenAI function calling are practical scaled implementations of this pattern

**HuggingGPT** (Shen et al. 2023) — four-stage pipeline:
1. Task Planning: LLM parses user request into typed, dependency-annotated sub-tasks `{type, ID, deps, args}`
2. Model Selection: multiple-choice framing; LLM picks from task-type-filtered model list (filtering needed due to context limits)
3. Task Execution: specialist models execute tasks; results logged
4. Response Generation: LLM synthesizes logged results into user-facing response
- Challenges identified: efficiency (multiple LLM inference rounds), long context needs for step 2, output stability issues

**API-Bank** (Li et al. 2023) — benchmark with 53 API tools, 264 dialogues, 568 API calls
- APIs span: search engines, calculator, calendar, smart home, schedule, health data, authentication
- Three-level evaluation ladder:
  1. Call correctly: determine if API needed, call properly, respond to result
  2. Retrieve: search for the right API, learn from documentation
  3. Plan: multiple API calls for complex multi-step requests (e.g., trip booking)
- Decision points tested: need-API decision, identify-right-API, iterative-parameter-refinement, satisfaction-check

### Generative Agents (Park et al. 2023) — memory + planning in simulation

Architecture — four interlocking systems:
1. **Memory Stream** (long-term external DB): natural-language records of all agent experiences; each element = observation (directly witnessed event) or statement (from inter-agent communication)
2. **Retrieval Model**: surfaces relevant memories per query; scoring = weighted sum of:
   - Recency: recent events score higher
   - Importance: LM query estimates "is this mundane or core?" (distinguishes brushing teeth from breakup)
   - Relevance: similarity to current situation/query
3. **Reflection Mechanism**: synthesizes memories into higher-level abstractions
   - Trigger: periodically or on importance threshold
   - Process: LM sees 100 most recent observations → generates 3 salient high-level questions → answers them
   - Produces higher-level summary nodes in memory stream (meta-memories)
4. **Planning & Reacting**: translates reflections + environment into actions
   - Optimizes behavioral believability across short and long time horizons
   - Prompt: `{Agent intro}. Here is X's plan today in broad strokes: 1)` → generates day plan → executes step-by-step

- Emergent behaviors from this architecture: information diffusion across agents, relationship memory (continued conversation threads), social event coordination (party planning)
- 25 virtual characters in Sims-like sandbox

### Proof-of-concept systems

**AutoGPT** — notable for demonstrating the possibility, but "quite a lot of reliability issues"
- Quote: "much of the code focuses on format parsing" — a critique of how brittle natural language interfaces are
- Short-term memory: ~4000 word limit; no user assistance during run
- 20 commands: Google Search, web browse, file ops, code analyze/improve/test, Python execute, image generate, tweet
- Response format: strict JSON `{thoughts: {text, reasoning, plan, criticism, speak}, command: {name, args}}`

**GPT-Engineer** — creates code repos from NL specs
- Phase 1: Clarification — LLM identifies unclear areas, asks prioritized questions, waits for human input
- Phase 2: Code Writing — generates full implementation with explicit architecture assumptions
- Instruction constraints: step-by-step reasoning, full code blocks (no placeholders), entrypoint-first file ordering, cross-file compatibility verification

**ChemCrow** (Bran et al. 2023)
- 13 expert-designed chemistry tools; LangChain workflow; ReAct format: Thought / Action / Action Input / Observation
- Key finding: LLM-based evaluation said GPT-4 ≈ ChemCrow; human experts said ChemCrow >> GPT-4 by a large margin
- Implication: "potential problem with using LLM to evaluate its own performance on domains requiring deep expertise" — LLM evals mislead on specialist tasks

### Failure modes and challenges (Weng's taxonomy)

1. **Finite context length**: restricts historical information, detailed instructions, API call context. "Self-reflection benefits from long/infinite context" — the loop's most critical bottleneck.
2. **Long-term planning reliability**: "Planning over lengthy history remains challenging. LLMs struggle to adjust plans when faced with unexpected errors. Less robust than human trial-and-error."
3. **Natural language interface brittleness**: formatting errors, occasional instruction refusal. "Much of agent demo code focuses on parsing model output." — This is a fundamental architectural fragility.

---

## Agents (Chip Huyen) — https://huyenchip.com/2025/01/07/agents.html — read

*Adapted from the Agents chapter of "AI Engineering" (2025)*

### Definitions and framing

- "An agent is anything that can perceive its environment and act upon that environment" via sensors and actuators
- Foundation model agents: model serves as the brain that "leverages its tools and feedback from the environment to plan how best to accomplish a task"
- Not a formal taxonomy of subtypes, but the architecture decomposes into: plan generator → executor → (optional) reflector/validator
- Multi-agent framing: "Most agentic workflows involve multiple components: plan generator, plan validator, executor, intent classifier. Each can be considered a separate agent."

### Three-stage agent lifecycle

1. Plan generation (task decomposition)
2. Execution with function calling
3. Post-execution reflection / error correction

Reflection may loop back to step 1 (replanning) or step 2 (retry with corrected parameters).

### Planning mechanisms

**Chain of Thought**: "think step by step" — baseline decomposition

**ReAct** (Yao et al. 2022): interleaves Thought / Act / Observation; each iteration is one agent turn
- Same structure as Weng's description; Huyen emphasizes this as the practical standard

**Reflexion** (Shinn et al. 2023): separate evaluation module + self-reflection module
- Evaluation judges whether plan succeeded; reflection proposes new trajectory if it failed
- Huyen's framing: evaluation and reflection are distinct modules, not one step

**Hierarchical Planning**: generate high-level plan first (quarter-level), then expand to sub-plans (month-level)
- Granularity tradeoff: "Detailed plans are harder to generate but easier to execute; high-level plans are easier to generate but harder to execute"

### Control flow primitives

- Sequential: B after A
- Parallel: A and B simultaneously (reduces latency)
- Routing (if-statement): conditional branch based on LLM or deterministic decision
- For loop: repeat until condition met

These are not metaphors — they are literal control flow structures in agent code.

### Tool taxonomy (three categories)

**Knowledge augmentation** (read-only data access):
- Text/image retrievers, SQL executors, internal people search, inventory APIs, Slack/email retrieval, web browsing, GitHub APIs

**Capability extension** (computation, transformation):
- Calculator, calendar, timezone/unit converters, translators, code interpreters, text-to-image generators, image captioning, OCR, transcription, LaTeX compilers, HTML rendering browser

**Write actions** (state mutation — highest risk):
- Database modifications, email responses, banking transfers
- These require explicit human approval or security validation in production

### Function calling mechanics

- Model declares tool inventory: function name + parameters + documentation (types, descriptions)
- Per-query settings: `required` (must use ≥1 tool), `none` (no tools), `auto` (model decides)
- Parameters are inferred from context — they can be hallucinated: incorrect tool with correct params, correct tool with wrong params, correct tool with incorrect values
- Tool descriptions and parameter docs are the primary lever for improving tool selection quality

### The compound mistake problem

- "If the model's accuracy is 95% per step, over 10 steps accuracy drops to 60%"
- Over 100 steps: 0.6% accuracy
- This is the fundamental argument for keeping agent tasks short and adding human checkpoints
- Mitigation levers: better base model, better prompts, simpler tools with clearer interfaces, reflection after each step, HITL at high-risk junctions

### Planning failure modes (Huyen's taxonomy — 6 types)

1. Invalid tool generation (hallucinated tool name)
2. Valid tool + invalid parameters (wrong parameter names)
3. Valid tool + correct parameters + incorrect values
4. Goal failure (agent reaches wrong destination or violates constraint)
5. Time/cost constraint violations
6. Reflection errors: agent falsely claims task is complete

### Tool failure modes

- Wrong tool outputs (tool itself is wrong)
- Translation/adapter module errors
- Missing tools for the required domain

### Planning improvement levers

- Better system prompts with more few-shot examples
- Clearer tool and parameter descriptions
- Simpler, more granular tool functions (large tools → harder to use correctly)
- Stronger base model
- Fine-tuning for plan generation specifically
- Ablation studies per tool: remove tool, measure performance drop — quantifies each tool's value
- Monitor tool-use frequency distribution: identify frequently misused tools

### Tool selection at scale (Voyager pattern)

- **Voyager** (Wang et al. 2023): skill manager that acquires new coding skills, evaluates their usefulness, stores in a persistent library, retrieves for future tasks
- Tool library as learned capability: tools are not static; the agent expands its toolkit over time

### Performance numbers

- **Chameleon** (Lu et al. 2023): GPT-4 + 13 tools; +11.37% on ScienceQA best published few-shot result; +17% on TabMWP accuracy
- Tool use "can significantly boost a model's performance compared to just prompting or even finetuning"
- GPT-4 vs ChatGPT tool preferences: GPT-4 uses broader tool selection, favors knowledge retrieval; ChatGPT favors image captioning

### LLM planning debate

- Yann LeCun (Sept 2023): "autoregressive LLMs can't plan"
- Huyen's counter: backtracking IS possible through path revision; models may lack adequate planning tooling/scaffolding rather than intrinsic capability
- Planning requirement: model needs (1) knowledge of available actions AND (2) ability to predict outcome states — to avoid walking off cliffs

### Human-AI collaboration design

- Expert provides high-level plan for agent to expand
- Explicit approval for risky operations (DB updates, code merges, financial transfers)
- "Level of automation" can be specified per-action type
- Write actions always warrant a human checkpoint

### Evaluation strategy

- Print all tool calls and outputs for inspection (trace logging)
- Create planning datasets: `(task, tool_inventory)` tuples
- Generate K plans per task, measure plan validity rate
- Count: invalid tools / invalid parameters / incorrect values separately
- Use a separate evaluator model (not the same model) for plan quality assessment
- Efficiency metrics: avg steps per task, avg cost per task, action latency

### Memory — explicitly deferred

- "The agentic pattern often deals with information exceeding context limits... I'll explore memory in a future post"
- Short-term vs long-term memory treatment not in this post
- Key acknowledgment: memory is a first-class component that this architecture post does not yet cover

---

## The Shift from Models to Compound AI Systems (BAIR) — https://bair.berkeley.edu/blog/2024/02/18/compound-ai-systems/ — read

*Matei Zaharia et al., UC Berkeley BAIR, February 2024*

### Core thesis

"State-of-the-art AI results are increasingly obtained by compound systems with multiple components, not just monolithic models." This trend will persist even as individual models improve — "one of the most impactful trends in AI in 2024."

Definition: A Compound AI System "tackles AI tasks using multiple interacting components, including multiple calls to models, retrievers, or external tools" — contrasted with a single statistical model like a Transformer.

### Four arguments for compound over monolithic

**1. Engineering beats scaling at the margin**
- "If the best LLM solves coding contests 30% of the time, tripling training budget might get to 35% — still not reliable enough to win." Compound system with sampling + testing gets to 80% with today's models.
- "Iterating on a system design is often much faster than waiting for training runs"
- The compound approach converts probabilistic outputs into reliable results via verification

**2. Dynamic knowledge and access control**
- Models have static knowledge from training cutoff
- Systems can incorporate real-time data via retrieval or search
- Access controls only possible in compound systems: "answer based only on files the user has access to" — a monolithic model cannot enforce per-user access

**3. Controllability and trust**
- Neural networks alone provide no guarantees against specific behaviors
- Compound systems add: output filters, citation generation, automatic fact-verification modules
- "Even the best LLMs still hallucinate, but a system combining LLMs with retrieval can increase user trust by providing citations"

**4. Variable performance-cost tradeoff**
- Different applications have different quality/cost needs
- GitHub Copilot: "carefully tuned smaller models and various search heuristics" — cheap and fast
- Legal opinions: GPT-4 at cents per query vs. outcome worth dollars — expensive is fine
- Compound systems enable point-on-Pareto-curve selection; monolithic models force a single point

### Concrete example systems with architectures

**AlphaCode 2**
- Components: fine-tuned LLMs (sampling + scoring), code execution module, clustering model
- Pattern: generates up to 1 million candidate solutions → filters → scores → selects
- Result: matches 85th percentile of human coders on competitive programming contests

**AlphaGeometry**
- Components: fine-tuned LLM + symbolic math engine
- Pattern: LLM iteratively suggests geometric constructions; symbolic engine validates deduced facts
- Result: silver-to-gold International Math Olympiad medal level performance on timed tests
- This is the definitive example of neurosymbolic compound design

**Medprompt** (Microsoft, GPT-4)
- Components: GPT-4 + nearest-neighbor search over example database + LLM-generated chain-of-thought + ensemble voting
- Pattern: retrieve similar examples for few-shot prompt → generate up to 11 solutions → vote
- Result: exceeds Med-PaLM (specialist model) on medical exams; outperforms standard GPT-4 on medical benchmarks by 9%
- Key insight: retrieval-augmented few-shot beats fine-tuning a specialized model

**Gemini CoT@32**
- Components: Gemini + custom inference logic
- Pattern: sample 32 chain-of-thought answers → return consensus if agreement; else use non-CoT generation
- Result: 90.04% MMLU vs. GPT-4 86.4% (5-shot)
- Note: authors flag that comparing this to "a single call to GPT-4" is misleading — 32 calls is very different cost

**ChatGPT Plus**
- Components: LLM + web browser plugin + Python code interpreter + DALL-E
- Pattern: LLM determines when/how to invoke each tool
- Demonstrates: tool-selection as a first-class LLM capability at scale

**RAG family** (RAG, ORQA, Bing, Baleen)
- Widespread: Databricks survey: "60% of LLM applications use RAG, 30% use multi-step chains"
- Multiple configurations: LLM-generated search query OR direct context injection
- Two-call minimum: retriever + generator

### Design space dimensions

Compound systems have a vast design space even for "simple" RAG:
1. Choice of retrieval model AND language model
2. Query expansion techniques
3. Reranking models on top of retrieval
4. Verifier LLM checking retrieved passage relevance
5. Resource allocation across components within latency budget (e.g., 20ms retrieval + 80ms LLM in 100ms total)

### Three major challenges for compound systems

**1. Correctness and reliability**
- Hard to formally guarantee outputs when components interact
- Each component can fail independently; failure compounds (c.f. Huyen's 95% per step)

**2. Latency**
- Multiple component calls add up; parallel execution helps but coordination adds overhead
- Resource allocation within a budget (the 20ms/80ms example) requires explicit engineering

**3. Optimization (the co-optimization problem)**
- Components must be optimized jointly, not independently
- "The LLM should be tuned to generate queries that work well for that particular retriever, and the retriever should be tuned to prefer answers that work well for that LLM"
- Unlike PyTorch end-to-end gradient flow, compound systems contain non-differentiable components (search engines, code interpreters) — standard backprop doesn't work

### Emerging tools and paradigms

**DSPy** (Stanford)
- Framework for end-to-end optimization of LLM pipelines
- Users write natural language signatures: `user_question -> search_query`
- Automatically tunes: prompts, few-shot examples, parameter choices across all modules
- Analogous to PyTorch autograd but for prompt pipelines; works around non-differentiability
- DSPy Assertions: leverage monitoring feedback directly to improve pipeline outputs

**FrugalGPT** (cost optimization)
- Routes inputs to different AI model cascades based on budget constraints
- Learns routing strategy from small labeled example set
- Claims: "outperform best LLM services by up to 4% at same cost, or reduce cost by up to 90% while matching quality"
- Broader concept: AI gateways (Databricks AI Gateway, OpenRouter, Martian) doing the same

**LLMOps / monitoring tools**
- Fine-grained trace tracking: LangSmith, Phoenix Traces, Databricks Inference Tables
- Quality evaluation: ARES, FAVA (AI-based automated quality evaluators)
- MT-Bench for multi-turn evaluation

### Industry parallel
- "The shift in Generative AI matches other AI fields: self-driving cars are systems with multiple specialized components, not monolithic models"
- AlphaFold itself is a compound system (attention + geometric modules)

### The key claim about frameworks
- Component libraries: LangChain, LlamaIndex (called from traditional programs)
- Agent frameworks: AutoGPT, BabyAGI (LLM drives the control flow)
- Output constraint tools: Guardrails, Outlines, LMQL, SGLang
- The proliferation of frameworks is the market's response to the design-space explosion

---

## → Verso implications

### On the canonical agent loop

- **ReAct is the proven baseline loop structure.** Every source converges on Thought → Action → Observation as the minimal viable agent loop. Verso's core loop should be this, named explicitly, with clean primitives — not abstracted away. (Weng: ReAct beats Act-only on both knowledge tasks and decision-making; Huyen: this is the practical standard.)

- **Reflection is a separate, optional module — not baked into the core loop.** Reflexion's architecture (Shinn 2023) shows that evaluation and self-reflection work best as distinct components layered on top of ReAct, not fused into it. Verso should expose `evaluator` and `reflector` as first-class optional hooks on the loop, not hardwire them. The user opts in.

- **The loop termination problem is real and unsolved.** Huyen's compound mistake math (95% per step → 60% at 10 steps → 0.6% at 100 steps) and Weng's long-term planning critique both demand that Verso provide: (a) explicit max-iteration limits, (b) heuristic early-stop detection (Reflexion's h_t: loop detection, inefficiency detection), and (c) cheap per-step confidence scoring as a first-class primitive.

- **Hierarchical planning matters.** Huyen's granularity tradeoff is real: high-level plans are easy to generate, hard to execute; detailed plans are hard to generate, easy to execute. Verso should support a two-level plan structure (sketch plan → expanded steps) as a built-in pattern, not an afterthought.

### On tools

- **Tool description quality is the primary lever on tool-selection accuracy.** MRKL showed small models fail at routing even when the tool is correct. Huyen shows invalid-tool, wrong-params, and wrong-values are three distinct failure modes. Verso's tool registration API must make descriptions, parameter types, and examples first-class — not optional docstrings. Consider making parameter descriptions required, with validation.

- **Write actions (state-mutation tools) are categorically different from read tools.** Huyen's taxonomy is sharp: read tools (knowledge augmentation, capability extension) are safe to auto-invoke; write tools (DB mutations, email send, financial transfers) require explicit gating. Verso's tool system should tag every tool with a `side_effects` flag and enforce a configurable gate (auto / confirm / require-HITL) per tool at framework level.

- **Tool inventory should be manageable at runtime.** HuggingGPT's task-type filtering, Voyager's skill library, and Huyen's ablation-study advice all point in the same direction: agents shouldn't see all tools at all times. Verso should support tool filtering per-turn (e.g., by tag, by task type, by learned routing) and a dynamic skill/tool library with add/remove/retrieve.

- **Tools trained in vs. tools injected at runtime are different systems.** LaMDA, Toolformer, AlphaGeometry all bake tool calls into training. Verso is a runtime framework — don't pretend to be a training framework. But acknowledge the capability gap: fine-tuned tool use outperforms prompting-based tool use; Verso integrations should be designed to plug into fine-tuned models as first-class targets.

### On memory

- **The three-layer memory model is the right abstraction.** Weng's sensory / short-term / long-term maps directly onto: raw-input embeddings / context window / vector store + structured DB. Verso's memory module should expose these three layers with explicit interfaces, not collapse everything into "context."

- **Retrieval scoring must be multi-factor.** Generative Agents' recency + importance + relevance formula is the right model for long-term memory retrieval. Verso's memory module should support pluggable scoring functions, not just cosine similarity. The importance dimension (LM-scored salience) is often the most useful and most-ignored.

- **Reflexion's 3-reflection working memory limit is a practical design choice.** Don't store unlimited reflections — evict old ones. Verso's reflection store should have a configurable sliding window (default: last 3–5 reflections).

- **Memory is explicitly NOT solved.** Huyen deferred it entirely. This is a product opportunity: Verso's memory module, if done well, is differentiated vs. existing frameworks.

### On compound systems and modularity

- **Verify-then-return beats generate-and-hope.** AlphaCode 2 (1M samples + filter), Medprompt (11 solutions + vote), Gemini CoT@32 (32 chains + consensus) all demonstrate the same pattern: generate multiple candidates, evaluate/verify, select. Verso should make sampling + verification loops a first-class pattern — not just a for-loop the user writes themselves.

- **Verso should expose control flow as explicit primitives.** Huyen's four control flow types (sequential, parallel, if/routing, for-loop) should be first-class constructs in Verso's API, not patterns that emerge from user code. This is the "clean primitives" philosophy applied to control flow.

- **The co-optimization problem (BAIR) is Verso's biggest systemic risk.** When users tune prompts for one component, they may break another. DSPy's approach (end-to-end pipeline optimization) is the right long-term answer. Verso should be designed to be DSPy-compatible: structured signatures, clear module boundaries, explicit input/output contracts per step — so a DSPy optimizer can slot in.

- **RAG is now table stakes, not a feature.** 60% of LLM apps use RAG (Databricks). Verso should ship with a batteries-included retrieval module that covers the full RAG design space: query expansion, reranking, verifier pass. Don't make users wire this from scratch.

- **The BAIR "system design beats scaling" argument is Verso's positioning.** "Iterating on system design is much faster than waiting for training runs" — this is the pitch for a compound AI framework. Verso's marketing and docs should lead with this: you can reach 80% reliability with today's models by engineering the system, not by waiting for a better model.

### On evaluation and evals infrastructure

- **LLM self-evaluation fails on specialist tasks.** ChemCrow showed LLM evaluators rated GPT-4 ≈ ChemCrow; humans rated ChemCrow >> GPT-4. Verso's eval system must support human-labeled ground truth and separate evaluator models (not the same model being evaluated). Build this from day one.

- **Planning datasets are the right eval primitive for agents.** Huyen's `(task, tool_inventory)` tuple with K-plan sampling + validity rate is a concrete, automatable eval pattern. Verso should ship tooling to generate, store, and score planning datasets.

- **Trace logging is not optional.** LangSmith, Phoenix Traces, Databricks Inference Tables all exist because compound system debugging requires full traces. Every Verso agent run should produce a structured trace (each Thought/Action/Observation turn, with timestamps and token counts) by default.

### On agent framework positioning

- **The natural language interface brittleness is a fundamental, known problem.** Weng (2023) noted "much of agent demo code focuses on parsing model output." Two years later, Huyen (2025) describes the same failure modes. Verso should treat structured output (JSON schemas, Pydantic models) as the default interface between LLM outputs and tool inputs — not optional. Parse-model-output-as-string is an antipattern.

- **HITL (human-in-the-loop) is a first-class design pattern, not an afterthought.** Huyen explicitly architectures it in: "level of automation per action type", approval for risky operations. Verso's escape hatch toward graph-based durable execution (the founding thesis) should be motivated exactly by HITL + checkpoint-resume cases. These are the legitimate use cases for graphs that ReAct alone cannot handle.

- **The "durable layer vs. tactical layer" thesis from Verso's founding is well-supported.** Compound AI systems (BAIR) are the macro trend. ReAct loop = tactical layer (fast, simple, per-session). Durable execution with HITL checkpoints = durable layer (cross-session, recoverable, auditable). Verso's positioning is correct — but the durable layer needs explicit design, not just an escape hatch.
