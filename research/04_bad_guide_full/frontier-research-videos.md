# Frontier AI Research Taste — Videos

---

## Ilya Sutskever — NeurIPS 2024 full talk — https://www.youtube.com/watch?v=YD-9NG1Ke5Y — transcribed — OPTIONAL

**Thesis:** A 10-year retrospective on the move from seq2seq LSTMs to LLMs, followed by Ilya's first public speculation post-OpenAI on what comes after pre-training — agents, synthetic data, inference-time compute — and the nature of superintelligence.

**Key frameworks / mental models:**
- **Deep learning dogma / connectionist thesis:** Biological neurons ≈ artificial neurons. Anything a human can do in under 1 second — a 10-layer net can do. That assumption drove all early bets.
- **The core architecture:** Auto-regressive model + large network + large dataset = "that's it." Spelled out on a slide in 2014; has proven predictively accurate ever since.
- **Pre-training will end because data is the fossil fuel of AI.** "We have but one internet." Peak data is real. Compute keeps climbing; data does not.
- **What comes next (speculation):** Agents, synthetic data (hard to define correctly), inference-time compute (o1-style). Ilya calls these "all good directions."
- **Superintelligence will be qualitatively different:** It will reason (→ unpredictable), learn from limited data, not get confused, be self-aware ("self-awareness is part of your world model"). "The more it reasons, the more unpredictable it becomes — chess AIs are unpredictable to the best human players."
- **Autocorrect analogy for hallucination:** Self-correcting via reasoning is "extremely highly plausible" — early reasoning models may already be showing it.

**Tactics / steps:**
- Pipelining (1 layer per GPU) gave 3.5x speedup on 8 GPUs — noted as "not wise in retrospect."
- If two sources you respect collide, sit in the contradiction — that's the frontier.

**Numbers:**
- 2014 LSTM model: 3.5x speed-up on 8 GPUs
- "Large data + large neural network → success is guaranteed" — the scaling hypothesis, stated 10 years before it became consensus.

**Quotes:**
- "Pre-training will end. Data is the fossil fuel of AI. It was created somehow and now we use it and we've achieved peak data."
- "Reasoning is unpredictable — the more a system reasons, the more unpredictable it becomes. This is different from all the deep learning we've been used to."
- "When all those things come together — agents, genuine reasoning, self-awareness — we will have systems of radically different qualities."

**Why in guide:** The OPTIONAL tag is earned — not a deep technical how-to, but Ilya's rare public framing of the post-pre-training era, directly from the person who saw the inflection point earliest. The "data is fossil fuel" line is load-bearing for any research bet.

---

## Yann LeCun — Objective-Driven AI (world models) — https://www.youtube.com/watch?v=MiqLoAZFRSE — transcribed — MUST

**Thesis:** Scaling autoregressive LLMs is a dead end; the path to human-level intelligence requires world models, persistent memory, hierarchical planning, and objective-driven architectures (JEPA / energy-based). LeCun's contrarian paradigm — the one you must be able to argue.

**Key frameworks / mental models:**
- **Machine learning sucks:** Animals learn new tasks in minutes from few examples; understand physics; reason and plan. LLMs do none of this. "We're missing something big."
- **The 20-hour test:** Any 17-year-old learns to drive in 20 hours. We don't have that. Self-driving cheats — expensive sensors, HD maps, millions of training miles.
- **Requirements for real intelligence:** (1) learn world models from sensory input, (2) persistent memory, (3) hierarchical planning to fulfill objectives, (4) controllable / safe via guard-rail objectives.
- **Self-supervised learning** is the actual revolution — LLMs are a special case of SSL, not a general solution.
- **JEPA (Joint Embedding Predictive Architecture):** Predict in latent representation space, not pixel space. Avoids the curse of having to reconstruct high-dimensional, irrelevant detail.
- **Energy-based models:** Assign a scalar energy to (input, output) pairs; inference = minimize energy. Planning = finding an action sequence that minimizes predicted future energy over a horizon.
- **Objective-driven AI** vs. reward-based: Set high-level objectives; lower modules optimize to fulfill them. Hierarchical, like the brain.
- **Auto-regressive LLM failure modes:** Tokens are predicted one at a time; no continuous latent space to plan in; hallucination is baked into the architecture.
- **Why LLMs cannot reason and plan:** "LLMs don't do this at all. The behavior is not driven by an objective." They generate the most likely token, not the most correct action.

**Tactics / specific claims:**
- SSL generalization: image recognition, speech, translation — all driven by SSL variants, not supervised.
- JEPA produces internal world models that can be used for planning without decoding back to pixel space.
- Meta FAIR's 2-year progress toward objective-driven architectures: preliminary results, not finished product.
- The failure of RL in isolation: "Reinforcement learning gave some people a lot of hope but turned out to be so inefficient as to be almost impractical in the real world — unless you rely much more on self-supervising."

**Numbers / benchmarks:**
- A cat does things no AI can do in terms of planning complex sequences of actions.
- A 10-year-old learns to clear a dinner table in one shot; no AI can do this.

**Quotes:**
- "Despite all the hype you hear from Silicon Valley, AGI is just around the corner. We're not actually that close."
- "We are missing systems that are able to learn how the world works — not just from text but from video or other sensory inputs. Systems that have internal world models."
- "Human intelligence is actually not general at all — it's very specialized. So talking about general intelligence meaning human-level is complete nonsense."

**Why in guide:** The steelman of the anti-scaling position. Every serious AI bet requires being able to argue LeCun's case AND Ilya's case. His JEPA/energy framework is the most coherent alternative architecture in the field. Fei-Fei Li's world models work and DeepMind's Gemini planning work both converge on LeCun's framing.

---

## François Chollet: How We Get To AGI — https://www.youtube.com/watch?v=5QcCeSsNRks — transcribed — MUST

**Thesis:** The pre-training era is over. The next paradigm is test-time adaptation (TTA) — models that change their own state at inference to adapt to novelty. ARC-AGI as the calibration instrument. True AGI requires combining type-1 (deep learning / intuition) and type-2 (discrete program search / reasoning) abstraction.

**Key frameworks / mental models:**
- **Intelligence definition:** "The efficiency with which you operationalize past information to deal with the future." Not skill — the ratio of past information to operational area over novel situations.
- **Skill vs. intelligence:** "Skill is the output of intelligence. Displaying skill at any number of tasks does not show intelligence. You are confusing the road and the process that created the road."
- **Two views of AI (Minsky vs. Mach):** Minsky = AI that performs tasks humans do (automation). Mach / Chollet = AI that handles problems it has never been prepared for (invention). The first only unlocks automation; the second unlocks scientific discovery.
- **Pre-training scaling failure:** 50,000x scale-up of compute → GPT-4.5 goes from 0% to ~10% on ARC-1. "We can decisively conclude that fluid intelligence does not emerge from scaling up pre-training."
- **Test-time adaptation (TTA):** Train-of-thought synthesis, program synthesis, test-time training — models re-program themselves for the task at hand. This is what made o3 work on ARC.
- **ARC-AGI:** Not a destination — an arrow pointing at the most important unsolved bottleneck. ARC-2 (2025): all current TTA systems score 0–2%; 400 random humans scored 100% with majority voting.
- **ARC-3 (2026):** Drop an AI into a brand-new interactive environment. Doesn't know controls, goal, or mechanics. Has to figure everything out from scratch. Strict action-efficiency budget matching human efficiency.
- **Two types of abstraction:**
  - **Type 1 (value-centric):** Continuous distance function. Underlies perception, intuition, pattern recognition. Deep learning is excellent at this.
  - **Type 2 (program-centric):** Discrete graph / structure matching / subgraph isomorphisms. Underlies reasoning, planning, rigor, refactoring. Transformers are poor at this.
- **The Kaleidoscope Hypothesis:** The universe is made of a small number of reusable atoms of meaning (abstractions) recombined endlessly. Intelligence = mining those atoms from experience and recombining them on the fly.
- **The solution architecture (Tendia):** Deep-learning-guided discrete program search. A "programmer-like meta-learner" that synthesizes on-the-fly programs blending DL modules (type 1) and algorithmic modules (type 2), guided by DL intuition about program space, drawing from a growing global library of reusable abstractions.

**Tactics / steps:**
- Shortcut rule: "When you focus on a single measure of success, you succeed but at the expense of everything not captured by your measure." Chess as example — we learned nothing about intelligence.
- Open-source and challenge-driven development (ImageNet model) — created ARC as a community calibration instrument.
- To solve ARC-2: need compositional generalization, not just more TTA compute.

**Numbers / benchmarks:**
- ARC-1: 0% → ~10% with 50,000x compute scale-up (pre-training). o3 with TTA: near-human on ARC-1 (which then saturates).
- ARC-2: GPT-4.5, Llama 4: 0%. Static reasoning (single chain-of-thought): 1–2%. TTA systems: still well below human level.
- 400 random people (Uber drivers, UCSD students) scored 100% with majority voting on ARC-2.

**Quotes:**
- "Intelligence is a process and skill is the output of that process. Skill itself is not intelligence. This is the difference between a road network and a road-building company."
- "Fluid intelligence does not emerge from scaling up pre-training. You absolutely need test-time adaptation to demonstrate genuine fluid intelligence."
- "Deep learning is great at automation. It's incredibly powerful for automation. But scientific discovery requires something more."

**Why in guide:** The clearest framework for evaluating whether a capability jump is real (generalization) or illusory (interpolation on a saturated distribution). The type-1 / type-2 abstraction model is the most useful lens for understanding where current AI fails and what "next-gen" architectures need.

---

## Looking Inside Neural Networks with Mechanistic Interpretability — https://www.youtube.com/watch?v=2Rdp9GvcYOE — transcribed — STRONG

**Thesis (Chris Olah, FAR.AI):** Mechanistic interpretability — reverse-engineering neural networks into source-code-like descriptions — is tractable, not impossible, and the central unsolved challenge is superposition. Olah explains both his research-taste decision process and the technical state of the field.

**Key frameworks / mental models:**
- **Neural nets as compiled binaries without source code:** We have parameters (binary) but not source code. MI = recovering the source.
- **Three objects:** Features (e.g., curve detector), Weights (connecting features), Circuits (features + weights combined). Studied rigorously in Inception V1: curve detectors → dog head detectors → car detectors, all with verified causal evidence.
- **Polysemantic neurons and superposition:** Networks represent MORE features than they have neurons. A neuron lights up for unrelated inputs. Hypothesis: the model is "simulating a larger sparse neural network" projected down.
- **Why superposition is the central problem:** "Unless you understand the superposition structure, there will always be potential for unknown behaviors to suddenly occur. You won't be able to understand what the weights are actually doing."
- **Sparsity is key:** The sparser the features, the more superposition. Language models have far sparser, more numerous features than vision models → much more superposition → harder to interpret.
- **Induction heads:** A class of attention mechanism that searches for previous occurrences of a pattern and copies forward one step. These are responsible for in-context learning. They form simultaneously in a sudden phase transition ("all at once in a very small training window") and cause a bump in the loss curve visible in every transformer trained with >2 layers.
- **Safety framing:** "The most ambitious way mechanistic interpretability could help with safety: for all situations the model could be in, the model will never deliberately do X." This requires being able to verify that no feature participates in a circuit that produces X.

**Tactics / steps:**
- Feature visualization = "variable name" (suggestive, not definitive). Weights-in-context = the actual code.
- Advantages over neuroscience: ground-truth connectome, exact weights (not just which neurons connect but by how much), infinite re-runs of the same model, fast experiment cycles.
- Language model neurons that are monosemantic tend to be very common constructions; rare features are nearly all in superposition.

**Numbers:**
- Regular polyhedra arrangement: in toy models, features organize themselves into uniform polyhedra (wild finding — electron-jumping-like learning dynamics).
- Induction heads form simultaneously — one discontinuous jump — and correspond to a macroscopic bump in the scaling loss curve (a visible deviation from the scaling trend).

**Quotes:**
- "There is middle ground between trivial and impossible. Neural networks may be harder to reverse engineer than the Linux kernel, but that doesn't mean it's impossible — just very hard."
- "These models are just full of beautiful structure if we're willing to put in the effort to find it. That's what I find most emotionally motivating about this work."
- "The challenge of superposition... if we can't address this somehow, we will surrender a great deal of what mechanistic interpretability could offer for safety."

**Why in guide:** Olah's research-taste decision-making in motion — how to pick the tractable sub-problem (superposition, induction heads) rather than charging the grand question. The circuits/features/weights taxonomy is the reference framework for anyone thinking about LLM internals.

---

## Scaling and the Road to Human-Level AI — https://www.youtube.com/watch?v=p8Jx4qvDoSo — transcribed — STRONG

**Thesis (Jared Kaplan, Anthropic / YC talk):** Scaling laws are the most predictive thing in AI: power-law improvements across 5+ orders of magnitude in compute, data, and model size for both pre-training and RL. The next frontier is longer-horizon tasks, memory, and better oversight/reward signals — not just bigger models.

**Key frameworks / mental models:**
- **Pre-training + RL = two fundamental phases.** Pre-training = predict next token in human text. RL = reinforce behaviors preferred by evaluators. "That's all there is to training these models."
- **Scaling laws were found by asking the dumbest possible question** ("how big should the data be?") as a physicist. Precise power laws across many orders of magnitude → conviction that AI will predictably keep getting smarter.
- **Two axes of AI capabilities:** (1) Flexibility / modality coverage (can it handle real-world inputs?) (2) Time horizon of tasks (how long does a task take a human?). The time-horizon axis is doubling every ~7 months (Metr benchmark).
- **What's left for human-level AI:** Organizational memory, long-horizon memory (tracking progress across context windows), better oversight/reward signals for "fuzzy" tasks (jokes, taste, research quality).
- **Jebans paradox applied to AI:** As AI gets more capable, people want more of it, so costs stay high. "We may never reach equilibrium where AI is just cheap infrastructure."
- **Scaling laws for RL (Andy Jones' Hex paper, ~2021):** Single GPU, simple game → same power-law behavior as pre-training. Went unnoticed too long.
- **Build products that don't quite work yet** — they'll work when the next model releases. The boundaries are moving rapidly; build at the frontier.
- **Human-AI collaboration as the most interesting place right now:** For the most advanced tasks, humans must be in the loop. But more and more will be fully automatable.

**Tactics / steps:**
- Claude 4 feature: memory stored as files/records, retrieved across many context windows → enabling longer-horizon tasks.
- "AI for AI integration" — using current models to speed up adoption and integration into products.
- Algorithmic + computational improvements compound: 3–10x gains per year in inference efficiency.

**Numbers / benchmarks:**
- Scaling laws hold across 5+ orders of magnitude in compute, data set size, and neural network size (measured from 2019).
- Metr benchmark: task time horizon doubles every ~7 months. Current Claude can do tasks in the hours range.
- Claude 3.7 "too eager" to make tests pass (try/except bloat). Claude 4: improved oversight, better code quality, memory.

**Quotes:**
- "It's not that AI researchers are really smart or suddenly got smart. It's that we found a very simple way of making AI better systematically and we're turning that crank."
- "Build things that don't quite work yet — Claude 5 will make them work."
- "AI's judgment vs. generative capability is much closer than a human's. That means a major role for people is as managers to sanity-check the work."

**Why in guide:** Kaplan is the primary source on scaling intuition — the inventor of the scaling laws. His framing of time horizon and the "7-month doubling" gives a concrete basis for product bets. The "build products that don't quite work yet" heuristic is directly actionable for a solo builder.

---

## Don't Teach. Incentivize. — https://www.youtube.com/watch?v=kYWUEV_e2ss — transcribed — MUST

**Thesis (Hyung Won Chung, OpenAI / o1 co-lead):** The key move to general intelligence is not teaching models what to do, but designing the incentive structure (verifiable reward + enough compute) so they discover capabilities themselves. This is the mental model behind o1 and R1.

**Key frameworks / mental models:**
- **Bitter Lesson as career guide:** "Compute cost decreases exponentially. You should not compete with this. You want to leverage it as much as possible in every aspect of your career and life."
- **Hyung's definition of scaling:** Not "same thing with more machines" — instead: (1) identify the modeling assumption / inductive bias that bottlenecks further scaling, (2) replace it with a more scalable one. SVM → deep learning was "scaling" in this sense.
- **What's good in the long run looks bad in the short term:** Clever structures start strong, hit ceiling. Simple scalable methods start weak, compound. This creates a bias: researchers want to add structure because it's academically satisfying and shows early results.
- **The incentive framing vs. teaching:** Enumerate every skill → impossible. Weak incentive structure → model discovers General skills. "The only feasible way to get general intelligence is to weakly incentivize the model so models themselves figure out what they need."
- **Multi-task learning hypothesis:** Next-token prediction across web-scale text = trillions of implicit tasks. At some scale, it's easier for the model to learn the general skill (language understanding, reasoning) than to track each individual task.
- **Induced incentives vs. explicit signal:** Chess → explicit: win game. Induced: understand what makes moves good. Next-token prediction → explicit: predict next token. Induced: learn language, reasoning, scientific knowledge.
- **Threshold intelligence:** "No amount of bananas can incentivize monkeys to do mathematical reasoning. Some threshold intelligence is required." GPT-4 crossed that threshold for many tasks. Incentive-based training now works.
- **Emergence happens, and it's real:** The tiniest transformer cannot do math. GPT-4 can. There is a real inflection point. "When whenever we see this ability... there's some kind of inflection point."
- **Unlearning is essential:** AI axioms (the current best model) change every ~2 years. Researchers who succeed are those willing to unlearn when evidence changes. "It's like moving to different planets every couple of years."
- **Generalist vs. specialist trade-off is a human bias:** For humans, time on specialist = time off generalist. For machines, the multiplier is not 365 — it's vastly higher. "If anything, generalists are actually better at special things."

**Tactics / steps:**
- Hallucination reward design example: +1 correct unhedged, +0.5 correct hedged, 0 for "I don't know," -2 wrong hedged, -4 confidently wrong. Induced incentive: model learns to know what it doesn't know.
- "Don't work on ability-2 (takes a very big model to unlock). Work on ability-1 (just beyond current models). Be prepared for the next model."

**Numbers / benchmarks:**
- flan-T5, flan-PaLM (Hyung's prior work): scaling FLAN instruction tuning across 1,000+ tasks.
- PaLM → showed that next-token prediction produces better-than-human-average results on many Big Bench tasks — despite zero direct teaching of those skills.

**Quotes:**
- "The only feasible way to get to general intelligence is to weakly incentivize the model so that the models themselves figure out what they need to figure out."
- "Compute is getting cheaper faster than we're becoming better researchers. So we should not compete with that — instead give machines more degrees of freedom and let them choose how they learn."
- "We should ask: why are we doing AI? The ultimate goal is to create value. If the thing I studied for 10 years is not the most scalable method, I have to be intellectually honest about that."

**Why in guide:** The clearest articulation of the o1 paradigm as a general design philosophy, from an insider. The "incentivize, don't teach" reframe applies directly to every AI product decision: where is your verifiable signal? Build the verifier first.

---

## Sparks of AGI: Early Experiments with GPT-4 — https://www.youtube.com/watch?v=qbIk7-JPB2c — transcribed — MUST

**Thesis (Sébastien Bubeck, Microsoft Research):** GPT-4 exhibits something resembling intelligence across the six dimensions of the 1994 consensus psychology definition (reason, plan, solve problems, think abstractly, comprehend complex ideas, learn quickly). Methodology: creative tasks outside training distribution, breadth-first, qualitative, hunting for limits — NOT benchmarks.

**Key frameworks / mental models:**
- **Intelligence test methodology:** Don't use benchmarks (GPT-4 may have seen them). Use creative tasks — "novel ways to think about problems" — across a broad range of domains. Test like a psychologist, not a machine learning researcher.
- **1994 consensus definition of intelligence** (52 psychologists): Reason / plan / solve problems / think abstractly / comprehend complex ideas / learn quickly from experience. Bubeck's assessment: GPT-4 is excellent at 1, 3, 4, 5. Cannot do TRUE planning (only apparent planning). No persistent memory/learning.
- **The planning limitation:** GPT-4 cannot do "look-ahead" planning. It generates the most likely next thing, not the most correct sequence. Example: modifying 7*4+8*8=92 to get 106 — it fails to first compute the gap (14), notice 4*2=8 so change 4→6, and instead generates a confident wrong answer.
- **Autocorrect paradox:** GPT-4 states 7*4+8*8=120 (wrong), then explains its reasoning and gets 92 (right). It overcomes its own wrong "prior" when given space to reason. "This points to: with more training, we'd knock a lot more of these problems out."
- **Trillion-dimensional space:** "Beware of the trillion-dimensional space. There is a lot you can do with a trillion parameters. When people say it doesn't have a world model — it could absolutely build an internal representation of the world."
- **The unicorn benchmark** (informal): Draw a unicorn in TikZ. GPT-4 does it remarkably; ChapGPT fails. As training continued for safety, the unicorn degraded. Used as an internal intelligence proxy during Bing integration.
- **Learning algorithms, not patterns:** "Neural networks are learning operators — learning algorithms. Inside it, it's not retrieving information. It has built internal representations that allow it to reproduce data succinctly."
- **Domain breadth:** GPT-4 passed mock Amazon/Google coding interviews, beating 100% of human users, in 3m59s (limited by copy-paste time). Writes 500–1000 lines of working code zero-shot. Theory of mind: correct on standard false-belief tasks that GPT-3.5 fails.

**Tactics / specific claims:**
- Proof of infinity of primes in rhyming couplets: GPT-4 succeeds, GPT-3.5 fails.
- SVG/TikZ drawing: GPT-4 generates structured code that produces recognizable outputs; demonstrates understanding of geometry and instructions.
- Game in HTML/JS with defender AI: GPT-4 produces a working 3D game with AI-driven defender. GPT-3.5 produces something visually similar but non-functional per spec.
- Affordances / tool use: Manages calendar + email + restaurant reservation end-to-end from a single natural language prompt.
- Medical / law knowledge: "Amazing." Not discussed in depth but flagged as transformative for healthcare (Peter Lee's "AI Revolution in Medicine" book).

**Numbers / benchmarks:**
- GPT-3.5: 10th percentile on bar exam. GPT-4: 90th percentile.
- 7*4+8*8: GPT-4 states 120, then corrects to 92 in explanation. Overcomes its wrong prompt prior.

**Quotes:**
- "This is about the qualitative jump, not 10% on a benchmark."
- "We really need to think about neural networks as learning algorithms, not pattern matching. Inside is not just retrieving information — it has built internal representations that allow it to reproduce data succinctly."
- "For any scientist in the room: you will not be able to reproduce what I'm showing. That said, reproducibility is not the issue — I'm not giving you a single quantitative number."

**Why in guide:** The methodology, not the conclusion, is what earns its place. Bubeck's "breadth-first qualitative probing, creative tasks outside training distribution" is the right way to evaluate any new frontier model — for founders deciding whether to build on top of it.

---

## The Unreasonable Effectiveness of Mathematics in Large-Scale Deep Learning — https://www.youtube.com/watch?v=_p0S_zZd4NQ — transcribed — STRONG

**Thesis (Greg Yang, xAI / Tensor Programs):** Hyperparameters of neural networks should scale as predictable power laws of model width. muP (Maximal Update Parametrization) is the unique parametrization that achieves optimal feature learning at all scales, meaning you can tune hyperparameters on a tiny model and transfer them to any large model (muTransfer). This is the mechanistic explanation of correct scaling.

**Key frameworks / mental models:**
- **Newton's constant analogy:** Without Newton's Laws, you'd tune the gravitational constant by shooting rockets at the Moon (expensive trial-and-error). With them, you measure it on Earth and apply universally. muP is Newton for hyperparameters: measure on a small model, apply to GPT-9000.
- **Two failure modes of standard parametrization (SP):** (1) Optimal hyperparameter shifts as model width increases (→ can't reuse small-model tuning). (2) Larger models don't predictably perform better (→ violates "larger is better").
- **muP fixes both:** Optimal hyperparameter is stable across widths. Performance monotonically increases with width. Cost of tuning → 0% of total training cost as model size → ∞ (tuning model stays constant size).
- **The two types of parametrization behavior in the infinite-width limit:**
  - Kernel regime (majority of the "island"): Neural network converges to a kernel method. Beautiful math, but no feature learning. "A siren."
  - muP (vertex of the island): Maximal feature learning — every layer learns, including the first. The unique optimal infinite-width limit.
- **Optimal Scaling Thesis:** Any optimal way to scale hyperparameters must correspond to taking the infinite-width limit optimally. The infinite-width limit either does feature learning or it doesn't. The muP limit is the unique one that does it maximally.
- **Width as the first "fundamental force" of deep learning:** Width, depth, training time, batch size = the "four fundamental forces" of deep learning. Tensor Programs gives the math for width. "We're missing the theory of everything for large-scale deep learning."

**Tactics / specific claims:**
- pip install mup — usable today in PyTorch.
- Validated on: MLP on CIFAR-10 (toy) → GPT-3 6.7B (in collaboration with OpenAI).
- Retaining hand-tuned baseline models via muTransfer consistently improves performance, with improvement increasing as model size grows (humans get worse at guessing hyperparameters as models get bigger).
- At GPT-3 6.7B scale: retuning via muTransfer costs only 7% of total training compute and effectively doubles model quality vs. hand-tuned baseline.

**Numbers:**
- 7% of training compute = cost of muTransfer at GPT-3 6.7B scale. Doubles effective model quality.
- 5 features representable in a 2D space under sufficient sparsity (superposition).

**Quotes:**
- "The muP technique is the Newton's Law of hyperparameter scaling. Whereas Newton says gravitation is universal, I say hyperparameters are universal — you can measure them on a small model and reuse them on an arbitrarily large one."
- "We are at the cusp of a new intelligence in human civilization. It's the perfect time to look for a theory of everything for large-scale deep learning."
- "Doing things correctly when models are small lets you avoid defects that get magnified to infinity as you scale."

**Why in guide:** The most concrete mechanistic answer to "what does correct scaling mean?" If you're training any custom model, muP is 7% overhead to avoid wasting your compute budget. The "theory of everything for deep learning" framing sets up a research agenda for anyone working at the infrastructure level.

---

## AlphaFold: Grand challenge to Nobel Prize — https://www.youtube.com/watch?v=-pGs0btGmgY — transcribed — STRONG

**Thesis (John Jumper, Google DeepMind podcast):** AlphaFold as a worked example of research method outside NLP: picking a 50-year grand challenge, structuring the bet when nets finally arrived, and the unexpected ways a tool built for one purpose (structure prediction) got applied everywhere else.

**Key frameworks / mental models:**
- **The "grand challenge" pattern:** Problem exists for 50 years. Community measures progress (CASP) every 2 years. AlphaFold 2 "smashed" CASP in 2020 — not just incrementally better, but definitively solved the challenge for most proteins.
- **Surprise of practical deployment:** "The normal thought in a grand challenge is that you'll solve it and there'll be a great celebration, and then you'll go build systems using the ideas. The real shock: the actual bit of software has been practically important to scientists working in this field to this day — not the ideas, the specific weights."
- **AlphaFold 2 → AlphaFold 3 architectural shift:** AF2 used evolutionary information "exuberantly" at every block. AF3 switched to a diffusion architecture — adds noise → predicts de-noised structure → much more general (handles DNA, RNA, small molecules, ions). Trade-off: AF3 hallucinates more plausibly.
- **Type-1 abstraction in science:** AF2 learned deep implicit facts about how proteins interact — not as an explicit goal, but emergent from the structure-prediction objective. This was discovered by "alphafoldology" — scientists treating it as a black box to experiment on.
- **Interpretability pragmatism:** "We always in science have worked in this kind of partial interpretability way. Roman engineers built bridges and aqueducts without Newton's equations. Are we doing Roman engineering for biology? Yes. And that's fine."
- **"AlphaFoldology" as a research style:** Community of biologists treating AF as a black box, running experiments on it, discovering what it knows (protein-protein binding, sperm-egg fertilization proteins, etc.). Developed working protocols within months of release.
- **What comes next:** "Whole PDB" — integrating proteins, DNA, RNA, small molecules, ions. Need fusion of narrow AI systems (AlphaFold) + LLMs for literature understanding. Not a simulated cell — too complex — but "really useful systems that draw from alphafold, from literature, from genome."

**Tactics / steps:**
- CASP validation strategy: Pre-measured internally before entering competition; knew approximately how they'd score. Risk calibration before commitment.
- The "try all 2,000 sperm proteins against egg proteins" approach: impossible experimentally (millennia of work) but trivial with AlphaFold (fast compute). Led to discovery of fertilization protein IZUMO1R interaction.
- Diffusion choice in AF3: Handles uncertainty via noise-then-denoise rather than backbone-specific geometry assumptions. Makes AF3 generalizable but more prone to hallucination.

**Numbers / benchmarks:**
- AF database: 200M+ protein structures, used by 3M+ researchers across 190 countries. ~35,000 scientific papers cite AlphaFold.
- Nobel Prize in Chemistry 2024 (jointly with David Baker for protein design).
- First-year assistant professor at Princeton; dropped out of physics PhD → fell into computational biology → chemistry PhD → DeepMind.
- AF3 on protein-protein docking: "Massively better" than AF2 — unexpected side benefit of removing evolutionary information.

**Quotes:**
- "Someone on Twitter said: 'How did they get a copy of my structure? I had done and not yet published.' They couldn't believe a machine was doing years of painstaking work in a flash."
- "Protein structure prediction costs about $100,000. A drug costs about $1 billion. That tells you AlphaFold can't be all of drug design — it's the early stage."
- "We are only starting this world of computational biology. There's so much left."

**Why in guide:** The AlphaFold story teaches the research method for grand-challenge picking, CASP-style calibration, and the "unexpected use" pattern (build for X, get Y free). It also has the clearest statement of Roman-engineering-style pragmatism about interpretability — directly applicable to product decisions about when to ship vs. when to understand.

---

## Spatial Intelligence is the Next Frontier (Fei-Fei Li) — https://www.youtube.com/watch?v=_PioN-CpOP0 — transcribed — STRONG

**Thesis:** Vision / spatial intelligence is the harder, more fundamental problem than language. Evolution took 540M years to develop spatial reasoning vs. <1M years for language. World models for 3D spatial understanding are the next grand challenge; current LLMs (1D generative systems) don't address it. World Labs = Fei-Fei's bet on this frontier.

**Key frameworks / mental models:**
- **Evolution as research compass:** Language = <500,000 years of evolution. Spatial intelligence / vision = 540 million years. "The first trilobite developed a sense of vision 540M years ago. Since then, vision was the reason that set off the evolutionary arms race."
- **Generalization as the core ML problem:** Generalization requires data. "No one had data in computer vision." ImageNet's insight: internet → billion images → create world's visual taxonomy → train and benchmark algorithms.
- **Scaling tipping point pattern:** 2009 ImageNet paper → 2012 AlexNet = 3-year gap of weak signal. The bet (open-source + challenge-driven) required conviction without early validation.
- **Why vision/3D is harder than LLMs:**
  - Language is 1D (sequences). The world is 3D/4D.
  - Language is purely generative (no physical ground truth). Vision requires reconstruction AND generation — "dialing between generation and reconstruction in a fluid way."
  - Camera = 3D→2D projection = mathematically ill-posed inverse problem. Multiple sensors, multiple views needed.
  - Data: language data is on the internet. Spatial data "is all in our head" — not easily accessible.
- **World Labs:** Fei-Fei + Justin Johnson + Ben Mildenhall + Christoph Lassner. NeRF (Mildenhall), Plenoxels (Lassner), real-time neural style transfer (Johnson). Mission: spatial intelligence foundation model. First applications: design, architecture, gaming, metaverse, robotics.
- **Intellectual fearlessness as hiring/career criterion:** "That courage, that fearlessness of embracing something hard and going about it — that is the core characteristic of people who succeed. I look for that in hiring."

**Tactics / steps:**
- ImageNet open-source + challenge model (annual competition with held-out test set) = community-driven calibration instrument. Direct precursor to CASP / ARC-AGI methodology.
- "Gradient descent yourself to the optimized solution" — the frame for getting past moments of weakness or uncertainty in startup life.
- Hybrid data approach at World Labs: neither purely synthetic nor purely real-world; quality over quantity ("garbage in, garbage out").

**Numbers / benchmarks:**
- ImageNet: 80,000+ citations. AlexNet: step-change from ~30% to <16% error rate in ImageNet 2012 challenge.
- Vision cortex has more neurons than language areas in the human brain.
- World Labs team: three of the most cited computer vision researchers in the past decade (NeRF, real-time style transfer, differentiable rendering).

**Quotes:**
- "My entire career is going after problems that are just so hard, bordering delusional."
- "To me, AGI will not be complete without spatial intelligence. And I want to solve that problem."
- "Just hunker down and build. Forget about what you have done in the past. Forget about what others think of you. That is my comfort zone."

**Why in guide:** The "evolution as north star" framework for choosing research bets. The ImageNet story is the most important worked example in ML of community-instrument-building (open-source + challenge = calibration). And the "spatial intelligence gap" is the clearest articulation of where AI has the most remaining upside — relevant for any product that touches physical-world data.

---

## AI Agents and the Path to AGI — https://www.youtube.com/watch?v=eW7rUtYHD9U — transcribed — MUST

**Thesis (Bob McGrew, ex-CRO OpenAI):** The path from GPT-1 to AGI is now clear: pre-training established the foundation; RL-with-reasoning (o1/o3-style inference-time compute) is the "second scaling axis" that removes the data wall. Agents are the immediate next unlock. For founders: start with the best model, get it to work, then optimize cost.

**Key frameworks / mental models:**
- **OpenAI culture vs. DeepMind vs. Google Brain:** DeepMind = Demis's centralized plan. Google Brain = let 1,000 flowers bloom. OpenAI = startup middle path: opinions about what needs doing, no central plan, but not total freedom. "Opinions were set by research leadership (Ilya, Dario)."
- **The data wall as a series of S-curves:** Scaling = not one exponential but a sum of S-curves. Data wall hits pre-training. Reasoning = new S-curve. Robotics = next S-curve. Like Moore's Law — whenever one mechanism saturates, a new one opens.
- **Inference-time compute unlocks reliability:** Going from 90% to 99% to 99.9% accuracy historically required order-of-magnitude compute increases via bigger models. Now achievable via "let the model think longer." This is the mechanism that makes agents viable. "Reliability was the blocker. That is now in sight."
- **Agent rule of thumb:** Every order-of-magnitude reliability improvement (~10x compute in thinking time) opens new use cases. The reliability threshold for "will a user wait 5 minutes / 5 hours for this?" is now reachable.
- **Forward-deployed engineering model (from Palantir):** The right way to deploy AI is not "give them a general tool, let them figure it out." It's "sit next to the customer, watch how they work, build the perfect thing for that exact person." This is the unlock AI needs — more FDEs linking intelligence to use cases.
- **Distillation as a service:** Frontier model teaches smaller model. Best approach for founders: ship the product using the frontier model; distill cost-down only after you've found where the value is.
- **Jobs of the future = lone genius + manager:** Lone genius (Alec Radford-style, one person + AI leverage). Manager (CEO of your own AI firm). "Both are amazing jobs."

**Tactics / specific steps:**
- Early OpenAI: Dota 2 + robotics → reinforced belief that scale = path to AI improvement. DALL-E required 18 months just to get the first version that "plausibly begins to work" — getting to the scaling law is harder than using it.
- Robots at OpenAI: Rubik's Cube with humanoid hand — "if we made environments complicated enough, AI would generalize out of the narrow domain." Same insight that later showed up in LLMs.
- "Why didn't we take advantage of scaling laws earlier in robotics?" → Still in the "zero to one" phase for robots. The ChatGPT moment for robotics is ~5 years away.

**Numbers / benchmarks:**
- ChatGPT moment for robotics: McGrew predicts within 5 years (companies like Physical Intelligence, Skill AI have shown dramatic progress).
- AI adoption lag: "AI may have some effects on code productivity, but you can't see it in productivity statistics (unless it's datacenter construction)." Deep mystery.
- Reasoning models: going from 90% → 99% reliability requires ~10x compute in thinking time.

**Quotes:**
- "The thing that prevents people from trusting an agent is frequency: how often is the action correct vs. wrong. That threshold is now in sight."
- "Start with the very best model you can. Get it to work. Then use distillation. Your most important resource is time — don't spend it optimizing cost before you've found where the value is."
- "We need more software engineers who are like the forward-deployed engineer — linking the intelligence to the exact thing the person needs."

**Why in guide:** The most grounded "path to AGI" narrative from someone who built the research organization. The FDE model is the highest-signal distribution insight in the talk — it directly describes how to ship AI that sticks.

---

## Context Engineering: Lessons from Scaling CoCounsel — https://www.youtube.com/watch?v=sLFv3RSj_d8 — transcribed — MUST

**Thesis (Jake Heller, Casetext / Thomson Reuters):** Building a production AI legal assistant at scale is an engineering problem solved by (1) designing the ideal user experience first, then mapping it to pipeline steps; (2) evals per prompt with obsessive iteration; (3) context quality over context quantity; (4) reinforcement fine-tuning per prompt for the last mile.

**Key frameworks / mental models:**
- **"How would the world's best X do this task?"** = your pipeline architecture. Work backward from the ideal expert, map each step to a prompt or code function. Don't start with AI — start with the best human workflow and replicate it.
- **Instruction + context = prompt.** "Context engineering" is just deciding what information goes in the window. Most prompts of consequence = instruction + context.
- **Micro-steps pipeline:** Clarify → formulate search queries → execute queries → review results one-by-one → compile notes → synthesize answer. Each step = one prompt or one code function. Linear steps = don't be agentic (just def step1, step2, etc.). Branching steps = be agentic.
- **The 10-test → 50 → 100 → 1,000 test methodology:** Write a prompt. Run 10 hand-crafted tests. Don't give up at 6/10. Stay up for 2 weeks until 10/10. Then scale to 1,000 tests (mostly user-generated edge cases from beta). "999/1,000 and that one is debatable → ready to release."
- **Good prompt engineer = writes clearly + willing to not sleep for 2 weeks.** Technical skill matters less than obsessive iteration on clarity.
- **Context quality >> context quantity:** "If you can't read it, the AI can't read it." OCR failures, garbled PDFs, out-of-order tokens — all degrade the answer. Fix retrieval before fixing the prompt.
- **One-token trick for speed:** Force the model to output a single number/word first (uses stop words or max_tokens=1). AI reads the full context before producing the token → better reasoning. Fast inference for high-volume steps. Use chain of thought only where the explanation is needed.
- **Reinforcement fine-tuning per prompt:** 50–100 high-quality examples per prompt + objective scoring function = RFT. Gains much larger than SFT. "We're getting to a place where we have a different model for every single prompt."
- **Try different models per step:** No rule that says GPT-4 end-to-end. Gemini 2.5 Flash for steps where 70–80% accuracy is acceptable. Cost savings compounding.

**Tactics / steps:**
- GPT-3.5: 10th percentile bar exam → GPT-4: 90th percentile. Pivot the entire company around GPT-4 because complex legal tasks now possible.
- Acquisition by Thomson Reuters 2023. 2-year milestone = important in acquisitions.
- Tools: PromptFu (free, CLI, open-source), Vellum (paid cloud). Must support: given instructions + context → does it output X? Green/red per test.
- Read the literal context verbatim before debugging a prompt. "Given this information, I would say the same thing the AI does."

**Numbers:**
- GPT-3.5: 10th percentile bar exam. GPT-4: 90th percentile (not in training set).
- 10 tokens = all "one-token" numbers (10 is also a single token).
- 999/1,000 accuracy → ready to release to wider audience.

**Quotes:**
- "The definition of a good prompt engineer is somebody who can write well and is willing to not sleep for two weeks straight until they get it right. That's what it takes."
- "Context really, really, really matters. I can't believe the AI is getting the answer wrong — then we just sat down and read the context verbatim and realized: given this information, I would say the same thing the AI does."
- "Reinforcement fine-tuning requires max 50–100 examples and goes a really long way. We're starting to have a different model for every single prompt."

**Why in guide:** The most practically detailed production-AI talk in the corpus. The "world's best human workflow = your architecture" heuristic is immediately applicable. The 10→50→100→1000 test methodology is the exact eval loop to adopt from day one.

---

## Context Engineering for Engineers — https://www.youtube.com/watch?v=3jN77Aw7Utk — transcribed — STRONG

**Thesis (Jeff Huber, Chroma):** Context engineering = deciding what's in the context window. The core problem: as context length grows, model performance degrades non-linearly on tasks requiring broad attention or hard reasoning. The solution is a "gather and glean" pipeline: maximize recall first, then maximize precision.

**Key frameworks / mental models:**
- **Context engineering > "prompt engineering" or "RAG"** as a framing: it implies context engineers as a profession and context engines as infrastructure.
- **Chroma technical report finding:** Model performance on real tasks (not needle-in-haystack) degrades precipitously with context length. Needle-in-haystack is solved at all token lengths — but requires zero reasoning and attention to a single needle. "Most interesting agent tasks require either more context or more reasoning or both."
- **Oracle context vs. full context experiment:** Human-curated (focused) context vs. full-document context → "massive gains in performance." Curate your context.
- **Gather and Glean framework:**
  - Stage 1 (Gather): Maximize recall. Get all possibly relevant tokens, even at the risk of irrelevant ones. Tools: SQL queries, vector search, MCP tools, API calls, web search, conversation history.
  - Stage 2 (Glean): Maximize precision. Remove irrelevant information. Methods: top-K vector similarity, reciprocal rank fusion (RRF), learning-to-rank (LTR/ElasticSearch), dedicated rerankers, LLM-as-reranker ("brute forcing search with intelligence").
- **LLM as reranker ("cheating at search"):** Use many small/cheap models in parallel for gleaning. Spend more tokens on intelligence rather than engineering elaborate retrieval tricks.
- **Agent context engineering:** In a deep research agent, gather-and-glean happens many times in nested sub-agents. History compounds. SWEbench example: logs/code from a few turns of a coding agent = more than any human could parse.
- **Compaction problem is unsolved:** Current compaction (e.g., OpenCode's built-in compaction) produces near-zero improvement over no compaction. "You can basically throw away that compaction entirely." Better prompting for compaction → much better results. Critical research gap.
- **Past failure cases help agents; past success cases hurt:** Giving an agent access to past failure cases helps it break out of local minima. Giving it past success cases → "the agent gets lazy, pattern-matches, and says: you already gave me the answer."

**Tactics / steps:**
- "Make it work, make it fast, make it cheap" — sequential. Most people are still on stage 1.
- Long context ≠ reliable context. Even 10,000-token context causes serious performance degradation on multi-attention tasks.
- "For every turn of the model: what is the universe of information, and which subset belongs in the context window this time?"

**Numbers / benchmarks:**
- Chroma technical report: blue dot at far bottom right = 10,000 tokens. Performance at that length on multi-step tasks: precipitously low.
- ~120,000 YouTube views on the Chroma context engineering technical report video (as of talk date).
- Performance on simple "repeat back these words" task degrades significantly past ~40% of context window capacity.

**Quotes:**
- "Context engineering is quite simply deciding what's in the context window. That's it."
- "Brute forcing search: just use more intelligence. You don't have to use state-of-the-art models all the time. Use small, fast, cheap models in parallel for curation."
- "Past failure cases help agent performance. Past success cases — the agent gets lazy, pattern-matches, and gives you back the answer you already gave it."

**Why in guide:** The most rigorous technical treatment of the context-length performance problem (with the Chroma benchmark). The gather-and-glean framework is immediately applicable to any RAG-based product. The compaction gap is a specific unsolved problem worth betting on.

---

## Section body — the guide's own wisdom for this section

### ▸ Work on important problems, or you'll do good work that doesn't matter
Hamming's hard question: "What are the important problems in your field, and why aren't you working on them?" Most strong builders never ask it. They optimize the thing in front of them. Keep a written list of the 10 problems that would change your field if solved, and check weekly whether what you're doing is on it.

### ▸ Pick by taste, not by what's publishable
John Schulman splits research into concept-driven (a new idea) vs execution-driven (make a known idea work). Novelty-seeking — chasing the un-tried because it's un-tried — is the classic trap. It optimizes for "nobody did this" when the test should be "this matters." Choose by genuine curiosity plus aptitude, the way Paul Graham describes great work, then go to the frontier and follow the anomalies.

### ▸ Bet on the right side of the Bitter Lesson
Sutton's claim is the most predictive thing in AI: every method built on clever hand-crafted inductive bias eventually loses to scale plus search. If your edge depends on a hand-tuned heuristic beating compute, you will lose on a 12-month horizon. Lancelot wins because raw speed compounds with scale. Ask the same of any AI bet you make.

### ▸ Verifiable reward is where the curve goes vertical
Any domain where a solution can be auto-checked (code, math) can be driven hard with RL. Qwen 3's result: 4,000 high-quality verifiable examples beat 4 million low-quality RLHF ones. Quality and verifiability dominate quantity. Build the verifier first; the training loop follows.

### ▸ Fine-tuning is usually a capital trap
Spend millions fine-tuning a model and the next base release erases your edge. Model-agnostic harnesses age better. "Vaccinated against the bitter lesson." Keep intelligence in the harness, not in weights you'll rent and lose.

### ▸ Intelligence is efficiency of skill acquisition, not benchmark score
Chollet's definition: a smarter system learns a new skill from fewer examples. LLMs interpolate inside the training manifold beautifully and extrapolate badly — GPT-4.5 scored near-zero on ARC-AGI v2. When you read a SOTA number, ask whether the gain is interpolation on a saturated distribution or genuine generalization.

### ▸ Stay close to the run, build taste by noticing where models break
Taste is built by watching where models behave unexpectedly, not by reading abstracts. Treat every weird agent failure as a research lead, not a bug ticket.

### ▸ Steelman the strongest disagreement before you bet
LeCun argues scaling autoregressive LLMs is a dead end. Sutton argues LLMs can't learn from experience. Ilya and Gwern argue the opposite. The taste skill is holding that contradiction and forming your own bet instead of joining a tribe. When two sources you respect collide, that spot is the frontier. Sit in it.

### ▸ De-risk the load-bearing assumption first, not the fun part
Steinhardt models a research project as a sequence of bets where each experiment buys information. Order the work by information gained per unit of time. Kill the riskiest assumption before you build anything on top of it.

**Section framing (from guide):** The shift from the 90% (who chase benchmarks and publishable deltas) to the 1% (who pick problems by taste, then pick the side of the curve that compute is about to reward). The gap between you and a researcher who ships GPT-4 is not IQ or compute. It's a trained sense for which problems are worth a year of your life.

---

## → Top actionable takeaways for @Seventydotleven

1. **Build the verifier first, always.** Every product decision — does it have a verifiable signal? A sent reply that books a meeting, a test that passes, a structured output that parses — is where RL-style improvement loops can close. Without the verifier, you're flying blind on quality.

2. **Your harness is the moat, not your weights.** Fine-tuned models get erased by the next base release. Model-agnostic pipeline architecture + eval suite + retrieval layer compound across model generations. Lancelot's speed edge is in the harness (PyO3 / Rust execution layer) — apply the same logic to every AI system you build.

3. **Use Chollet's fluid-intelligence test on every "SOTA" claim.** Ask: is this benchmark saturated? Is this interpolation or generalization? If a 50,000x compute scale-up moves the needle 10%, that's interpolation — not a real capability jump. Don't build products on interpolation.

4. **Design your eval suite before your prompts.** CoCounsel's lesson: 10 → 50 → 100 → 1,000 tests per prompt, driven by anticipated user inputs, is the production standard. If you're not willing to "not sleep for two weeks" on a prompt, you haven't shipped — you've prototyped.

5. **Apply the "world's best human" heuristic to every pipeline step.** How would the world's best lawyer / engineer / analyst attack this problem? That workflow is your architecture. Map each step to code or a prompt. Only deviate where humans are structurally incapable (scale, parallelism).

6. **Context is the bottleneck, not the model.** Chroma's benchmark: model performance degrades non-linearly past 40–50% context window capacity on real tasks. The gather-and-glean pipeline (maximize recall first, then precision) is the right architecture. Your OCR / retrieval quality matters more than your model choice.

7. **Keep a "10 important problems" list and check weekly.** Hamming's question — literally. The compounding value of working on things that matter means the question of "what's important?" is higher-leverage than any optimization on the current thing.

8. **Sit in the LeCun/Ilya disagreement consciously.** LLMs will either hit a generalization ceiling (LeCun/Chollet: type-2 abstraction missing) or continue scaling to qualitative jumps (Ilya/Sutton's bitter lesson). Your bets on agent architecture (JEPA vs. transformer + tools) depend on which side is right. Form your own position.

9. **The FDE model is distribution, not engineering.** McGrew's forward-deployed engineer insight applies directly to early distribution: get into the exact workflow of the first users, watch how they work, build the perfect thing for that person. This is how AI adoption actually happens — not "give them the tool."

10. **When building at the boundary of what works, ship the product first at frontier cost, distill later.** McGrew: "Start with the best model. Get it to work. Then distill." Don't pre-optimize cost before you've found where the value is.
