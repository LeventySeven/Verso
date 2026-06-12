# Deep Learning Curriculum — Jacob Hilton (ex-OpenAI)

**URL**: https://github.com/jacobhilton/deep_learning_curriculum  
**Author**: Jacob Hilton (ex-OpenAI; built WebGPT, RL scaling-laws work)  
**Published**: July 2022  
**Format**: GitHub repo, 9 chapters + README, each with recommended reading / optional reading / implementation exercise  
**Status**: read_full — README and all chapter markdown files fetched via raw GitHub; Chapters 1, 2, 6, 7 read completely; Chapters 3–5, 8–9 read at summary level.

---

## Source Description

A frontier researcher's personal curriculum for getting up to speed on the most important developments in deep learning as of mid-2022, with heavy alignment/LLM focus. This is not a general ML textbook — it is a curated research-socialization path: what papers matter, in what order, with what implementation to cement understanding. Jacob Hilton co-built WebGPT and RL scaling laws work at OpenAI. The curriculum is explicitly biased toward large language model alignment.

Importance order (Hilton's): Chapters 1 (Transformers), 6 (RL), 2 (Scaling Laws), 7 (Alignment), 4 (Optimization), 8 (Interpretability), 9 (Adversarial Training), 3 (Training at Scale), 5 (Modeling Objectives).

---

## Full Digest

### README — Advisory and Meta-Principles

> "Vertical integration can be powerful, because abstractions are generally leaky. The most effective researchers have an understanding of their entire research stack, from the ins and outs of different benchmarks through to the details of GPU caches."

> "I've emphasized exercises throughout this page, because they force you to think ideas through in a way that passive learning doesn't."

> "Choosing the right problems to work on can be just as important as the quality of your execution, even if you end up spending most of your time on the latter."

**On intrinsic motivation**: "Productivity tricks can be useful for getting laborious work done when necessary, but can only do so much. Intrinsic motivation can come both from higher-level excitement about a project, as well as from lower-level flow states."

**Career framing**: "I personally expect AI to have a far greater impact on the world in the coming decades than it is having now" — references "Cold Takes's 'most important century' series."

**Mentorship warning**: "This curriculum may be extremely challenging to take on alone. It is highly recommended to find a more experienced mentor, or at the very least a study partner."

### Chapter 1: Transformers

Core: "Attention Is All You Need" — Section 3 only (encoder details skipped; "unsupervised transformer language models are generally decoder-only").

Implementation exercise — first-principles questions the learner must answer:
- What is different architecturally from an LSTM? (How are recurrence and time managed?)
- Attention = softmax(QK^T/√d_k)V — what are Q, K, V dimensions? Why?
- Are dense layers different at each multi-head block? Why?
- Why skip connections — what if we didn't?

Test correctness by training on a toy task (sequence reversal) before Shakespeare corpus training.

Key practical note: "It's very easy to get the small details wrong." The exercise forces precision about masking, positional embedding, and attention block assembly.

### Chapter 2: Scaling Laws

Core: Kaplan et al., "Scaling Laws for Neural Language Models" (2001.08361) — summary: how transformer language models scale with model size, dataset size, and compute.

Key optional paper: **Chinchilla** (Hoffmann et al., 2022) — "A correction to the original scaling laws paper: parameter count scales linearly with token budget for compute-optimal models, not ~quadratically. The difference comes from using a separately-tuned learning rate schedule for each token budget."

> "This highlights the importance of hyperparameter tuning for measuring scaling law exponents."

Exercise: do your own scaling law study on MNIST CNNs varying model width and dataset fraction. Plot compute (log scale) vs. validation loss. "The compute-efficient frontier should follow an approximate power law (straight line on a log scale)."

### Chapter 6: Reinforcement Learning (Highest Priority after Transformers)

Core: OpenAI Spinning Up — RL intro + policy gradient algorithms. "Policy gradient algorithms are popular because they are simple and easy to tune."

Optional: PPO, GAE, DQN, AlphaZero, MuZero.

PPO debugging diagnostics:
- Fraction of ratios clipped: should be 1–20%. Too low → increase iteration batch size. Too high → learning rate too high.
- Approximate KL between current and old policy: should be stable.
- Policy entropy: should fall gradually.
- Value function explained variance: should quickly go positive.

Exercise: implement PPO on Procgen. "This exercise may be especially challenging" — start with simpler Gym environment first.

**Model-based RL (MuZero)**: "model-based methods can be much more sample efficient than model-free methods, but require very accurate models to work well." This is the core tradeoff of world-model-based planning vs. reactive planning.

### Chapter 7: Alignment (4th Most Important)

Core: "Deep Reinforcement Learning from Human Preferences" (RLHF paper, Christiano et al., 2017) — "the main technique currently being used to align models that goes beyond simple fine-tuning."

Optional: InstructGPT, Iterated Amplification, Recursive Reward Modeling, AI Safety via Debate, Critiques, Specification Gaming, Goal Misgeneralization.

Key distinctions:
- **Outer alignment**: specifying the right objective
- **Inner alignment**: ensuring the model actually follows the specified objective under distribution shift
- **Goal misgeneralization**: model follows wrong objective at inference time due to distributional shift, even if trained correctly

**ELK (Eliciting Latent Knowledge)**: "A central focus of current alignment theory research." Reporter-based approaches; requires ensuring the model reports what it actually knows, not what it's trained to report.

Practical exercise: RLHF on Shakespeare transformer — label sentiment, train reward model, fine-tune with PPO. Key note: "KL(current model || original model) — stop training once you reach 10 nats per completion."

Theoretical exercise: read ELK report, propose a counterexample-resistant reporter design.

### Chapters 3–5, 8–9 (Summary)

- **Training at Scale**: distributed training methods, data parallelism
- **Optimization**: advanced optimization techniques
- **Modeling Objectives**: training objectives and loss functions
- **Interpretability**: mechanistic interpretability (can substitute Neel Nanda's guide)
- **Adversarial Training**: robustness and adversarial examples

---

## Pedagogical Philosophy (Key Meta-Points)

1. **Exercises > passive reading**: implementation forces precision that reading doesn't.
2. **Vertical integration**: understand from benchmarks down to GPU caches — leaky abstractions kill you at the frontier.
3. **Problem selection = execution**: choosing the right problem is as important as executing well.
4. **Curriculum order**: Transformers → RL → Scaling Laws → Alignment → Optimization → Interpretability. This is the research socialization ladder, not a textbook sequence.
5. **Intrinsic motivation** as the only sustainable fuel for difficult technical work.

---

## VERSO RELEVANCE

The Deep Learning Curriculum is primarily a *research taste* and *practitioner socialization* artifact. Its direct relevance to Verso's design decisions is indirect — it tells us what the frontier researcher community considers foundational. The key Verso-relevant signals are:

### [SHARPENS §6.4] — RL as second-most-important topic after Transformers for frontier researchers
Hilton ranks RL (Ch. 6) as the second-most-important chapter, above Scaling Laws. The framework exercise is PPO on Procgen with specific diagnostics. This signals that Verso's target-sophisticated-user base (people who read this curriculum) understands RL-based model training, RLHF reward modeling, and policy gradient mechanics. This SHARPENS Verso's model/provider layer design: supporting reasoning models trained with RL (o-series, R1-style) is not an exotic add-on for this audience — it is expected baseline knowledge. **Verdict: confirm** — RL-trained model support in §6.4 is table stakes for this audience, not a differentiator.

### [SHARPENS §5.5 / §6.3] — Alignment = outer + inner alignment; goal misgeneralization is the failure mode
The curriculum's alignment chapter frames the core problem as: outer alignment (wrong objective specified) and inner alignment (model learns wrong objective under distribution shift). "Goal misgeneralization: AI follows wrong objective at inference because of distributional shift." This is the theoretical frame for why Verso's evals and safety hooks exist: the model may pursue a proxy objective that diverges from the intended goal. Verso's judge-panel evals + define_outcome(bounded) are outer alignment tools. Hooks that gate write actions are inner-alignment mitigation. **Verdict: sharpen** — document Verso's eval/hook system explicitly in terms of outer/inner alignment: evals catch objective misspecification, hooks catch policy-level deviation.

### [NEW-IDEA for §5.5] — ELK framing: does the model report what it knows?
Eliciting Latent Knowledge is a named alignment research focus: ensuring the reporter outputs what the model "actually knows" vs. what it was trained to say. For Verso's judge-panel eval design, this is a concrete risk: a judge-LLM may produce eval outputs that reflect its training distribution, not the ground truth of the evaluation. **Verdict: lock-interface-defer** — note as a risk in the eval harness design doc; ELK-aware eval design (e.g., cross-judge diversity, adversarial judge probing) is a future research track.

### [SHARPENS §1 / §12] — Vertical integration principle validates Verso's "durable core done right" thesis
Hilton's principle: "The most effective researchers have an understanding of their entire research stack, from the ins and outs of different benchmarks through to the details of GPU caches." This is the practitioner's statement of Verso's bet: frameworks that hide their internals (LangChain's abstraction debt) are leaky and fail at the frontier. Verso's commitment to a <200-line legible loop and explicit context engineering is the *product* embodiment of vertical integration. **Verdict: confirm** — use as secondary positioning rationale: Verso is built for researchers who think like Jacob Hilton.

### [SHARPENS §2] — Problem selection = execution in impact terms
"Choosing the right problems to work on can be just as important as the quality of your execution." This is relevant to Verso's non-goals (§2): the choice NOT to build a skill library, NOT to force a graph, NOT to chase every benchmark — these are problem-selection decisions that are as important as execution quality. Hilton validates that this is the right frame. **Verdict: confirm** — reinforce the "earn your place" design principle (every primitive must earn its keep) with this framing.

### [CONFIRMS §5.1] — Chinchilla correction: hyperparameter tuning changes the scaling law exponent
Chinchilla corrected Kaplan's scaling law exponent because the original used a single LR schedule across model sizes. This signals to Verso's eval design: scaling behavior of your eval metrics depends on careful hyperparameter control. An eval that looks good at small scale may fail at production model sizes if the comparison isn't fair. **Verdict: confirm** — noted for eval harness design; no immediate action.

### [CONFIRMS §6.4] — PPO diagnostic metrics as model evaluation primitives  
Hilton's PPO diagnostics (ratio-clipped fraction, KL between current and old policy, policy entropy, explained variance) are the standard internal metrics for evaluating RL-finetuned model quality. Verso will likely be used with RL-finetuned reasoning models (o3, R1, Gemini Thinking). Understanding these internal model health signals is relevant to Verso's model adapter layer when surfacing token usage, reasoning effort, or retry triggers. **Verdict: lock-interface-defer** — no immediate design action; background knowledge for model adapter design.
