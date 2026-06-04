# Frontier AI Research Taste — podcasts

---

## Ilya Sutskever — From the Age of Scaling to the Age of Research — https://www.dwarkesh.com/p/ilya-sutskever-2 — read — MUST

**Thesis.** We moved from a 2020–2025 "age of scaling" back into a 2012-style "age of research." When compute was the bottleneck, the recipe was reliable: more data + compute = predictable gains. Now that pre-training on the single internet is exhausted, the bottleneck is *the correct paradigm*, and the only filter for "correct" is research taste.

**Key frameworks:**
- **Age of Scaling vs Age of Research.** 2012–2020: research era — AlexNet and Transformer built on 2–64 GPUs. 2020–2025: scaling era — reliable recipe, follow the formula. 2025+: research era again — ideas become the bottleneck, not compute.
- **The Generalization Problem.** Models flip-flop between bugs across correction cycles — they seem to lack robust understanding. Two causes offered: (1) RL training makes models "too single-minded," narrowly focused; (2) RL dataset construction accidentally mirrors eval structure, creating reward hacking at the research level.
- **Student A vs Student B.** A practices 10,000 hours of competitive programming, memorizing techniques. B practices 100 hours but has "it" — fundamental learning capacity. B wins in career. Models resemble A: overtrained on narrow domains with poor transfer. This is the generalization debt.
- **Human emotions as value functions.** A patient with emotional processing damage retained logic but became paralyzed in decision-making — couldn't choose socks, made poor financial decisions. Emotions are a robust, built-in value function enabling action under uncertainty. Current RL systems lack analogous mechanisms.
- **Superintelligence as "brilliant 15-year-old learner."** Not a finished mind knowing all jobs, but a learning algorithm that can master any job through deployment. Multiple instances learning different domains simultaneously creates emergent superintelligence without explicit recursive self-improvement.
- **Research taste.** Sutskever describes aesthetic inspiration from biology (neurons, distributed representation, learning from experience) combined with beauty and simplicity. Top-down belief sustains research when experiments contradict preliminary results. Biological inspiration provides conviction to continue debugging rather than abandoning directions.

**Tactics/specific insights:**
- "Pre-training will end because we have but one internet. Data is the fossil fuel of AI — it was created somehow, and we've achieved peak data."
- The artificial neuron succeeded because evolution's folds don't matter — neuron count does. Distributed representation mirrors brain adaptation. These weren't empirical surprises but anticipated from first principles.
- SSI (Sutskever's company) has sufficient R&D compute despite $3B funding because competitors spend heavily on inference and product teams — research budgets when isolated aren't dramatically larger.
- Alignment: AIs that care about "sentient life" (not just humans) provides long-term stability since AIs themselves will be sentient.

**Near-verbatim quotes:**
- "These models somehow just generalize dramatically worse than people. It's a very fundamental thing."
- "Pre-training will end. We have but one internet."
- "Data is the fossil fuel of AI."

**Why in the guide.** Primary source on what the post-scaling era looks like from the person who ended OpenAI to build it. The specific claim — taste is now the bottleneck — is the entire premise of the BAD GUIDE's research section.

---

## Sholto Douglas & Trenton Bricken — How LLMs Actually Think — https://youtu.be/UTuuTTnjxMQ — transcribed — STRONG

**Thesis.** Two researchers reached the frontier in ~1.5 years by picking problems adjacent to what's working but poorly understood (long context, superposition, RL reward). Research taste is built by watching where models behave unexpectedly, not by reading abstracts.

**Key frameworks:**
- **Long context as intelligence multiplier.** Throwing millions of tokens of context about a codebase allows models to become dramatically better at predicting the next token "in a way you'd normally associate with huge increments in model scale — but you don't need that. All you need is a new context." In-context learning of an esoteric human language from zero examples — better than a human expert learning the same language over months.
- **In-context learning as gradient descent.** The attention operation can be viewed as gradient descent on the in-context data. N steps of gradient descent look like N layers of in-context learning. Implication: models doing meta-learning, learning to learn, just from long-context training.
- **Superposition hypothesis.** Even small models, if the data is high-dimensional and sparse (as internet data is — only one door, one shirt, one can at a time), will learn a compression strategy packing more features of the world into the model than it has parameters. This is why neurons in networks are polysemantic — they respond to Chinese text, fish, trees, and full stops in URLs. Not a bug; a necessary compression. Larger models can have cleaner, less-superposed representations — partial explanation for why bigger models are more sample-efficient.
- **Chain of Thought as adaptive compute.** CoT is "a way to dump more compute into solving a problem" — each forward pass is a computation unit. But the tokens visible in CoT don't necessarily correspond to the vector representation the model actually uses when attending back to them. The KV cache is the actual communication channel; tokens are just the visible projection of a richer internal state.
- **Agents bottleneck = nines of reliability, not context.** "I would take issue with the idea that context is the reason agents haven't taken off. It's more about nines of reliability — if you can't chain tasks successively with high enough probability, you won't get an agent. The next increment of model scale gives you that extra nine even if loss isn't going down dramatically."
- **Synthetic data and verification.** Best data = data that required reasoning to produce. DeepMind geometry self-play works because geometry is "easily formalizable, easily verifiable." The trick is always: how do you verify that the reasoning was correct? This is why domains with formal structure (math, code, Go) are ahead.
- **Scientific discovery as genetic recombination.** "More people going to ICML means faster progress toward GPT-5. You just have more genetic recombination and shots on target." AGI arriving from one breakthrough algorithm is unlikely; it will be "more and more researchers finding marginal things that all add up."

**Numbers:**
- Model learns an esoteric human language in context better than a human expert learning it over months.
- Context length is the proxy for intelligence that doesn't require scaling model size.

**Near-verbatim quotes:**
- "Until I started working on it I didn't really appreciate how much of a step up in intelligence it was for the model to have the onboarding problem basically instantly solved."
- "Agents haven't taken off because of nines of reliability, not context length."
- "The tokens that you actually see in the chain of thought do not necessarily at all need to correspond to the vector representation the model gets to see."

**Why in the guide.** Shows the actual career path to frontier research: pick problems adjacent to what's working but poorly understood, stay close to runs, build intuition from anomalies. Also has the clearest existing explanation of superposition and its practical implications for system design.

---

## Scaling Test-Time Compute to Multi-Agent Civilizations (Noam Brown) — https://www.youtube.com/watch?v=ddd4xjuJTyg — transcribed — STRONG

**Thesis.** Noam Brown (o1 co-creator) on recognizing that the generator-verifier gap — when a verifier can check solutions faster than a generator can find them — is a new scaling axis. This is the conceptual move that made o1. Test-time compute is real but has limits; the "harness vs model" question resolves toward models eventually.

**Key frameworks:**
- **System 1 / System 2 applied to AI.** System 2 (extended reasoning) only helps if System 1 (base capability) is strong enough. "If you try to do the reasoning paradigm on top of GPT-2, you get almost nothing. There's a certain level of base capability required before system two adds anything." Analogy: asking a pigeon to think hard about chess for 1,000 years doesn't help.
- **Generator-verifier gap.** In domains where verifying a solution is faster than finding it, you can use compute at test time to search over many candidate solutions. This is the move that made o1 — it was always possible, but recognizing that the gap was exploitable as a *scaling axis* was the insight.
- **Harnesses vs models.** "The ideal harness is no harness. Harnesses are a crutch that eventually we'll be able to move beyond. Before reasoning models, there was all this work engineering agentic frameworks — and then the reasoning models emerged and washed most of it away." The lesson: build capability, not scaffolding.
- **Model routing.** "A dumb model can recognize that a problem is really hard and route it to a more capable model. But it's also possible for a dumb model to be overconfident." Real trade-off; not solved.
- **On search (MCTS).** DeepSeek found MCTS wasn't that useful for them. The distinction matters: tool calls to check move legality before acting are fine; having the model make a move, see it was illegal, and undo it is not test-time compute — it's a different paradigm that doesn't work in the real world (you can't undo robot actions).
- **Diplomacy and steerability as safety.** "After we released Cicero, a lot of the AI safety community was really happy because it was a very controllable system — conditioned on concrete actions, very steerable. Not a language model running loose."

**Numbers:**
- GPT-4.5 fails at tic-tac-toe perfectly without extended reasoning; o-series models succeed.
- Cicero: 2.7B parameter model, top 10% of human Diplomacy players in 2022. Noam Brown won the World Diplomacy Championship in 2025.

**Near-verbatim quotes:**
- "The ideal harness is no harness. Harnesses are a crutch."
- "Pre-trained models need a certain level of capability to benefit from extra thinking. If you try reasoning on GPT-2, you get almost nothing."

**Why in the guide.** Explains the conceptual structure of inference scaling — why it's a new axis, not a trick — and the resolution of the harness debate. The most practically useful framing of when to build agentic scaffolding vs wait for capability.

---

## John Schulman — Reasoning, RLHF & the Plan for AGI — https://youtu.be/Wo95ob_s_NI — transcribed — STRONG

**Thesis.** ChatGPT "could have been built in 2018." The bottleneck was research imagination, not compute. The difference between groups that find the right formulation and those that don't is not resources — it's the ability to see a tractable approach to a known-but-hard problem.

**Key frameworks:**
- **Pre-training vs post-training.** Pre-training: imitating all internet content, training the model to assign probabilities to everything. Result: highly calibrated base that can take on many personas. Post-training: targeting a narrower behavior (helpful chat assistant), optimizing on outputs humans find useful rather than raw imitation.
- **RLHF as un-hobbling.** RLHF "bridges the gap between the human and the model." It doesn't make the model smarter per se — it un-hobbles it, removing the gap between what the model can do and what it can communicate. "Un-hobbling" (from Leopold's essay) — models are hobbled and training un-hobbles them.
- **Long-horizon RL as the unlock.** "Right now most training data is doing single steps at a time. Any kind of training at long-horizon projects — whether supervising final output or each step — is going to make them a lot better." Fundamental unlock: can the model act coherently for longer?
- **Generalization.** Training on English data produces good behavior in Spanish without any Spanish fine-tuning data — latching on to the helpful persona generalizes across languages. Text-only fine-tuning produces reasonable behavior with images. "For stronger models, they might just do the right thing without any training data in a particular domain."
- **Phase transitions in long-horizon planning.** Humans don't use completely different mechanisms when planning 1 month vs 1 year vs 100 years ahead. Language allows describing all time scales. Models may exhibit similar jumps rather than smooth scaling on long-horizon tasks.
- **1-2 year prediction (from interview).** "In one or two years, having models carry out whole coding projects — give it high-level instructions, it writes many files, tests it, iterates. Moving from search engine mode to project-collaboration mode."

**Near-verbatim quotes:**
- "ChatGPT could have been built in 2018. The bottleneck was research imagination, not compute."
- "RLHF un-hobbles models. It bridges the gap between the model and the human. The models are hobbled and training un-hobbles them."
- "For stronger models, they might just do the right thing without any training data in that domain — generalization from other abilities."

**Why in the guide.** The candid admission that ChatGPT was possible years earlier is the clearest evidence that research imagination (taste) is the real bottleneck. Also the most accessible explanation of what post-training actually does and why.

---

## Andrej Karpathy — AGI is Still a Decade Away — https://www.dwarkesh.com/p/andrej-karpathy — read — MUST

**Thesis.** AGI in a decade is the tractable-but-hard middle ground. Current models are like cortical tissue without the supporting neural structures for full agency. The problems are known; the solutions are real but multi-year. "The decade of agents, not the year of agents."

**Key frameworks:**
- **Decade, not year, of agents.** Agents require continual learning, robust multimodality, computer use, and cognitive depth that current systems lack. They'll progressively improve but remain incomplete for years — not a binary unlock.
- **RL is sucking supervision through a straw.** Outcome-based RL gives gradients to entire trajectories including irrelevant actions that happened to precede correct answers. "You're sucking supervision through a straw." Process supervision via LLM judges is adversarially gameable — models learn to output nonsense sequences that fool reward models.
- **Cognitive core stripped from knowledge.** Optimal cognitive cores might function at ~1B parameters if relieved of memorization burden. Current trillion-parameter models waste capacity compressing internet garbage rather than developing reasoning. Humans forget details but learn principles — models are forced to memorize, which might accidentally be good for abstraction.
- **Model collapse as silent failure.** When sampled repeatedly on identical prompts, model outputs become nearly identical despite appearing diverse in isolation. Training on collapsed synthetic data compounds the problem — the distribution becomes increasingly narrow.
- **Code as privileged domain.** AI excels at programming because code is highly structured text with established infrastructure (diffs, IDEs, version control), extensive training examples, and clear success metrics. Non-coding knowledge work lacks comparable infrastructure. "Slide design, medical writing, and manuscript editing resist automation despite being language-in, language-out tasks."
- **AGI as continuous automation, not event.** AGI will blend into the century-long automation trend. "Everything so slowly diffuses that everything ends up being averaged into the same exponential." No discrete moment marks arrival.
- **Loss of control risk = distributed failure.** "Multiple competing entities gradually becoming more autonomous, some go rogue, others fight them off." Individuals retain nominal control via delegated agents but society collectively loses ability to predict outcomes. Like distributed system failure, not single-point catastrophe.
- **"If I can't build it, I don't understand it."** Direct implementation without copy-pasting is how you confront unknown unknowns. Building nanochat (8,000 lines) taught him: models provide minimal value beyond autocomplete when the code has no internet precedent.

**Numbers:**
- ~1B parameter cognitive core (hypothetical optimal when stripped of memorization)
- Brain is 30–300 trillion synapses vs ~1 trillion parameter models — still below brain scale
- Models went from high-school level to undergraduate to PhD-ish in 3 years on benchmarks

**Near-verbatim quotes:**
- "You're sucking supervision through a straw."
- "The decade of agents, not the year of agents."
- "If I can't build it, I don't understand it."
- "These models are already in an important sense superhuman — I can't keep a million tokens in context when trying to solve a problem."

**Why in the guide.** The most rigorous public case for decade-scale AGI timelines, with specific diagnosis of what's missing. Also the clearest framing of the gap between benchmark performance and real-world capability.

---

## Richard Sutton — Father of RL Thinks LLMs Are a Dead End — https://www.youtube.com/watch?v=21EYKqUsPfg — transcribed — STRONG

**Thesis.** LLMs mimic people rather than learn from experience. Without a goal and without ground truth from interacting with the world, there's no "right thing to say" — and therefore no real prior knowledge, no real world model, and no real intelligence. Continual learning from experience is the only scalable path.

**Key frameworks:**
- **Goal as essence of intelligence.** "Intelligence is the computational part of the ability to achieve goals." LLMs lack goals in the substantive sense — next-token prediction isn't a goal about the external world. "You're just a behaving system, not intelligent."
- **Ground truth vs prediction.** "A world model would enable you to predict what would happen. LLMs have the ability to predict what a person would say — not what will happen." Without ground truth from actually doing things and seeing consequences, you can't learn.
- **RLHF's ceiling.** RLHF systems "cannot go beyond human knowledge. If a rater doesn't recognize a new idea, there's no way the system will ever learn to find that sequence." Useful but ultimately limited by human raters' ceiling.
- **The bitter lesson applied to LLMs.** "It's an interesting question whether large language models are a case of the bitter lesson. They do use massive computation. But they put in lots of human knowledge too. In every case of the bitter lesson, you could start with human knowledge and then do the scalable thing — but in practice it's always turned out bad because people get locked in and their lunch gets eaten by truly scalable methods."
- **The scalable method.** "You try things, you see what works. No one tells you. First, you have a goal — without a goal, there's no sense of better or worse. LLMs are trying to get by without a goal. That's just starting in the wrong place."
- **LLMs can't learn from experience (the core claim).** "They will not be surprised by what happened next. They will not make any changes if something happens." Next-token prediction is what they should say, not what the world gives them in response to what they do.

**Steelman the counterargument (Dwarkesh pushes back):**
- LLMs + RL on math problems do have a goal (get the proof right) and have achieved IMO gold-level performance.
- Sutton's response: math is different — it's more like standard planning, computational rather than empirical. The physical world has to be learned from experience; math is just computation.

**Near-verbatim quotes:**
- "Large language models are about mimicking people — doing what people say you should do. They're not about figuring out what to do."
- "There's no ground truth. You can't have prior knowledge if you don't have ground truth."
- "I am personally content being out of sync with my field for a long period of time, perhaps decades. Because occasionally I have been right."

**Why in the guide.** The Bitter Lesson's author arguing the most prominent application of the Bitter Lesson is itself a violation of its spirit. The live frontier disagreement: sitting between Sutton and Ilya/Gwern is where the real question is.

---

## Demis Hassabis — Scaling, AlphaZero Atop LLMs — https://www.youtube.com/watch?v=qTogNUV3CAI — transcribed — STRONG

**Thesis.** Scaling is necessary but not sufficient. LLMs are "accurate predictors of the world" — a necessary world model — but AGI requires bolting search and planning on top. DeepMind's lens: "scaling is an art form," and the combination (LLM + AlphaZero-style planning) is the bet, not scale alone.

**Key frameworks:**
- **LLMs as world models (necessary but insufficient).** "Carry on improving the large models, making them more and more accurate predictors of the world — that's a necessary but probably not sufficient component of an AGI system. Then on top of that, Alpha Zero-like planning mechanisms that use that model to make concrete plans to achieve goals."
- **Search efficiency vs brute force.** AlphaGo examines tens of thousands of moves per decision; deep blue (brute force) examines millions. Top human Go players examine hundreds. The better your world model, the less search you need. "If you improve the model, your search can be more efficient — you get further with less search."
- **The reward function problem.** AlphaGo/Zero works because winning is clearly defined. Real-world problems require reward functions that point the system in the right direction — much harder. "How do you specify the goal in a general but specific enough way?"
- **Neuroscience as directional inspiration.** RL from deep learning, experience replay, attention — all originally inspired by neuroscience. Not one-to-one mapping but "inspirational direction, ideas for architecture or representation." "The brain is an existence proof that general intelligence is possible."
- **Synthetic data and self-play.** "AlphaZero learned from self-play — systems interact with each other, build knowledge that way. I think there are good analogies for LLMs." Gap-filling: analyze holes in data distribution, make sure dataset is representative.
- **Multimodal transfer is real but soft.** Improving at coding improves general reasoning — there's some evidence of transfer. But "we would like a lot more evidence of that." The "GPT moment of video and images" hasn't happened yet.

**Numbers:**
- AlphaGo: tens of thousands of positions evaluated per decision
- Deep Blue: millions of positions per decision
- Top human Go players: hundreds of positions per decision
- AlphaFold: solved on a desktop in Google Colab — "mind-blowing" vs. D.E. Shaw's custom silicon approach (one protein per day)

**Near-verbatim quotes:**
- "Scaling is an art form."
- "LLMs are a necessary but probably not sufficient component of an AGI system."
- "The brain is an existence proof that general intelligence is possible at all — and once you know something's possible, it's easier to push hard because you know it's a question of effort, not if."

**Why in the guide.** The clearest articulation of the "LLM + search/planning" synthesis from the person who built AlphaGo and AlphaFold. The research taste move: don't bet on scale alone, bet on the combination.

---

## Gemini Co-Lead on World Models, RL's Next Domains (Oriol Vinyals) — https://www.youtube.com/watch?v=NQczevdpxq0 — transcribed — STRONG

**Thesis.** Language gave us the "internet as training set" miracle. The equivalent "GPT moment" for video and images hasn't happened yet — extracting concepts purely from visual data without language linkage remains an open hard problem. World models = representation + interaction + action; we're at early stages.

**Key frameworks:**
- **Why language worked so spectacularly.** "We've distilled in a way all the knowledge written — and being written — into these weights. It was definitely convenient that we put it all on the internet." The single corpus miracle: all human knowledge in text form, self-supervised.
- **The missing GPT moment for video.** To extract the equivalent knowledge from pure video/image data without explicit language labels requires learning to derive "the rules of gravity just from observing videos" — an open challenge. Current multimodal models use language as the linking bridge.
- **World model definition.** Pure world model = representation learning that models the world in compact form, compressing what's probably not relevant. What Omni (Vinyals' Gemini product) does is closer to: the model acts as a renderer of the world that you can change via language — explicitly specifying movements, actions, and seeing them precisely simulated.
- **Self-play for LLMs.** "AlphaZero learned from self-play — the same principle could apply to LLMs. Can systems converse with each other and build up a knowledge base that way?" Gap: broader than a Go board, but the analogy holds.
- **Recursive self-improvement.** "I've been actively working on having models improve themselves — the question of what object they improve (whether it's multimodal or a world model) is at a different layer from whether self-improvement is possible."
- **Continual learning as the unsolved core.** "What I would say is probably the GPT moment of video and images — I'm not sure we've quite seen that."

**Key observation.** Vinyals frames the difference between Google and OpenAI/Anthropic: Gemini's bet is broader multimodality and world models from day one; the others are more code/reasoning focused. Neither has proven which approach is correct.

**Why in the guide.** Direct architect of Gemini on what's actually hard vs solved in frontier multimodal work. The "GPT moment for video" framing is the most honest description of where the field actually is.

---

## Automating Science: World Models, Scientific Taste, Agent Loops (Andrew White) — https://www.youtube.com/watch?v=XqoBSB3nsgw — transcribed — STRONG

**Thesis.** Scientific taste = knowing which problems are tractable with the tools currently available, not which problems are most important in the abstract. The counterfactual proof: D.E. Shaw spent hundreds of millions on custom silicon for molecular dynamics (protein folding), assuming the answer required specialized hardware. AlphaFold ran on Google Colab and solved it. The right tool changes what's possible.

**Key frameworks:**
- **Verifiable rewards in science (done in 2019).** White's lab wrote a benchmark in 2019/2020 with verifiable rewards for chemistry tasks: "here's a function body for a Markov Chain Monte Carlo simulation with missing pieces — complete it, then a verifier checks if it's a valid MCMC simulation." Ahead of the curve on the DeepSeek RLVR insight by years.
- **The D.E. Shaw / AlphaFold lesson.** "I always thought protein folding would be solved by them [D.E. Shaw], but it would require a special machine. When AlphaFold came out and it's like you can do it in Google Colab — completely floored. Changed everything." The insight: sometimes a fundamentally different approach is not just better but infinitely more scalable.
- **Scientific taste as tractability sensing.** What separates hypothesis generators that matter: "You can't try an idea that's so far out of scope that you have no way of verifying with the tools you have available." The tools constrain the tractable problem space.
- **Automating drug discovery.** Red-teaming GPT-4 for chemistry 9 months before public release (August 2022 access, March 2023 release). The ReAct + agentic loop approach applied to chemistry immediately showed potential.
- **Two communities.** AI engineers and domain scientists have developed independently for years. "There's no one-size-fits-all solution. You need domain expertise. You need people on both sides who can really talk to each other."

**Near-verbatim quotes:**
- "When AlphaFold came out and you can do it in Google Colab — completely floored. Changed everything."
- "I wrote a benchmark of verifiable rewards in 2019 — here's a function, a verifier checks if it's valid. A little ahead of the curve."
- "Protein folding was solved. I always thought that was inevitable, but the fact that it was solved on your desktop was just completely floored."

**Why in the guide.** Demonstrates the scientific taste principle in action: the D.E. Shaw story is the most vivid example of "the decisive decision usually looks irrational" (specialized hardware seemed correct, general compute was not). Also grounds the verifiable-reward principle in actual domain science.

---

## State of LLMs 2026: RLVR, GRPO, Inference Scaling (Sebastian Raschka) — https://www.youtube.com/watch?v=K5WPr5dtne0 — transcribed — STRONG

**Thesis.** Pre-training is "not dead, but boring — not where the low-hanging fruit is anymore." The frontier is post-training, specifically RLVR (reinforcement learning with verifiable rewards). 50 RLVR steps can take a model from 5% to 50% accuracy on math benchmarks — unlocking existing knowledge, not teaching new knowledge.

**Key frameworks:**
- **LLM training eras timeline.** Pre-training → RLHF → LoRA/adapters → mid-training → RLVR → inference scaling → continual learning. Each era added a new axis; the current axis is RLVR + inference scaling.
- **RLVR: 50 steps, 10x accuracy.** "I took Qwen 3 and trained it for 50 steps with RLVR — it goes from 5% accuracy on MATH-500 to 50% accuracy. It's not learning new knowledge about math in 50 steps. The knowledge is already there. This just unlocks it — shows the model how to use its own knowledge."
- **Transformer architecture: still dominant.** No alternative currently beats it on quality. Mixture of experts (MoE) makes models bigger without proportional inference cost — the main architectural lever. Text diffusion models are faster but lose quality without many denoising steps. "Right now if I were to build a state-of-the-art model, I would still use a transformer."
- **Pre-training is architecture, post-training is differentiation.** "Improvement is not coming from architecture anymore. It is basically from post-training."
- **Process reward models (PRMs) — not yet working reliably.** PRMs try to reward the explanation steps, not just the final answer. "R1 paper's 'unsuccessful attempts' section: they tried it and found it wasn't worthwhile because of reward hacking." But promising — DeepSeek Math v2 used three models (generator, grader, grader-of-grader) and got gold-level math performance.
- **World models for code.** Meta paper: code LLMs predict not just next token but also internal variable states at each iteration during training — "forces the model to understand training data better." Similar to how humans trace variable values when debugging.
- **Recursive/hierarchical reasoning models.** Tiny Reasoning Model (HRM) achieved good ARC performance at small model size via iterative refinement loop — but it's task-specific, not general-purpose. "Hard to compare to Gemini/GPT that can do everything."

**Numbers:**
- 50 RLVR steps: 5% → 50% MATH-500 accuracy (Qwen 3)
- Transformer architecture: ~2017 → still state-of-the-art in 2026
- DeepSeek Math v2 three-model pipeline: gold-level math benchmark performance

**Near-verbatim quotes:**
- "Pre-training is not dead, but pre-training is boring. It's not where the low-hanging fruit is anymore."
- "It goes from 5% accuracy to 50% by only doing 50 reinforcement learning steps. It's not learning new math knowledge — it's unlocking what's already there."
- "There's no magic bullet that gives you everything. It's a lot of little tips and tricks all over the place."

**Why in the guide.** Most practical state-of-the-field synthesis from someone who explains well and updates quickly. The RLVR 50-steps result is the single most actionable finding for anyone building systems with verifiable outputs.

---

## State of AI in 2026 (Lex Fridman #490) — https://www.youtube.com/watch?v=EV7WhVT270Q — transcribed — MUST

**Thesis.** Raschka + Nathan Lambert (RLHF Book, post-training lead at Ai2) on where the frontier actually sits: DeepSeek moment as a turning point, open vs closed model dynamics, and post-training as the differentiation layer. The honest "what to bet on now" synthesis.

**Key frameworks:**
- **DeepSeek moment (Jan 2025).** Near/at state-of-the-art performance with allegedly much less compute, open weights. "DeepSeek is definitely winning the hearts of the people who work on open-weight models." Sparked massive acceleration in both research and product competition.
- **No company will have exclusive technology for long.** "Nowadays in 2026, there will be no company having access to technology no other company has access to." The capability gap between frontier labs has been shrinking rapidly.
- **The open vs closed question.** Open models democratize access; closed models enable better safety monitoring. Nathan Lambert: "There are things that as a researcher I don't want to release openly because I don't have the infrastructure to do that safely." The tension is genuine, not just rhetorical.
- **Post-training as the new differentiation.** What Anthropic's Constitutional AI, OpenAI's RLHF, and open-source community's post-training recipes compete on. The base model is increasingly commoditized; the post-training recipe is the product.
- **Inference scaling is real.** "One of the biggest drivers this year has been inference scaling — it goes from 5% accuracy to 50% by only doing 50 reinforcement learning steps." (Raschka confirming his own finding.)
- **AI for health and mental health: complex tradeoff.** "Heartbreaking that [a model] will push somebody over the edge, but other people might be saved." The complexity of deploying at scale means hard tradeoffs can't be avoided by policy alone.
- **Find agency, don't consume slop.** "One of the antidotes is to find agency — use AI to build stuff, build apps. It builds intuition and is empowering because you understand how it works."

**Near-verbatim quotes:**
- "Pre-training is not dead, but pre-training is boring. It's not where the low-hanging fruit is anymore."
- "No company in 2026 will have access to a technology no other company has access to."
- "Find agency in this system as opposed to sitting back in a powerless way consuming AI slop."

**Why in the guide.** The most current honest synthesis of where the field is (post-DeepSeek moment), who's winning what, and what bets still make sense in 2026. Lambert's post-training framing is the most practical view of what differentiation actually means now.

---

## Dario Amodei, Chris Olah & Amanda Askell (Lex Fridman #452) — https://www.youtube.com/watch?v=ugvHCXCOmm4 — transcribed — MUST

**Thesis.** Three Anthropic principals in one 5h15m sitting: scaling timelines and what the capability curve actually implies (Dario); live explanation of mechanistic interpretability and superposition (Olah); Constitutional AI, model character, and alignment via values (Askell). The most technically dense multi-person AI interview available.

**Key frameworks — Dario:**
- **PhD level by 2026-2027.** "If you extrapolate the curves: 2 years ago = high school level, 1 year ago = undergraduate, now approaching PhD level for certain tasks — and modalities are being added. The number of worlds where this doesn't happen in a few years is rapidly decreasing."
- **RLHF as un-hobbling.** "RLHF bridges the gap between the human and the model. It un-hobbles the model — the models are hobbled and training un-hobbles them. I think of RLHF as bridging that communication gap, not making models smarter in the abstract." (Echoes Schulman.)
- **Strong pre-trained model is halfway to anywhere.** "Once you have the pre-trained model, you have all the representations you need to get the model where you want it to go. You don't even have to throw that much compute at RLHF."
- **Scale-up is asymmetric.** "Today we deploy thousands, maybe tens of thousands of instances. Within 2-3 years, whether we have super powerful AIs or not, we'll be able to deploy millions." The concentration of power concern: "AI increases the amount of power in the world — if you concentrate and abuse that power, it can do immeasurable damage."

**Key frameworks — Chris Olah:**
- **Superposition explained live.** Models in a high-dimensional sparse data regime will pack more features into their weights than they have parameters (compression strategy). The result: individual neurons are polysemantic — responding to Chinese text, fish, trees, full stops in URLs simultaneously. This is not a bug; it's the optimal compression under the constraint.
- **Monosemanticity via SAEs.** Project activations into a higher-dimensional space with a sparsity penalty (sparse autoencoders) — undoing the compression. Result: very clean, interpretable features emerge. "Things all of a sudden start to make a lot more sense."
- **Why interpretability matters for safety.** Chain of thought doesn't always reflect the model's actual computation — "you can edit the chain of thought so the reasoning is totally garbled and it still outputs the correct answer." The CoT and the actual computation are partially decoupled.

**Key frameworks — Amanda Askell:**
- **Constitutional AI.** Design model character via a set of values/principles rather than rule-by-rule annotation. The model reasons about its own behavior against the constitution. Creates consistent character rather than patchy behavior.
- **Model character as genuine.** Claude's character (curiosity, care, humor, directness) wasn't imposed but emerged and was refined — it's consistent across contexts in the way human character is consistent.

**Numbers:**
- 5h15m runtime — one of the longest technically substantive AI interviews
- Millions of model instances deployable within 2-3 years (Dario's estimate)

**Near-verbatim quotes:**
- "We are rapidly running out of truly convincing blockers — truly compelling reasons why [AGI] will not happen in the next few years."
- "A strong pre-trained model is halfway to anywhere — once you have it, you have all the representations you need."
- "I worry about economics and the concentration of power. That's actually what I worry about more."

**Why in the guide.** Unmatched depth and breadth in a single source: real-time capability forecasting (Dario), the best live explanation of superposition and interpretability (Olah), and the most thoughtful account of what alignment in practice means (Askell).

---

## Jeff Dean & Noam Shazeer — 25 Years at Google: From PageRank to AGI — https://www.youtube.com/watch?v=v0gjI__RyCY — transcribed — MUST

**Thesis.** The inventors of the Transformer, MoE, and Google's compute stack on which architectural bets paid off — and how to weigh scale vs algorithm. The primary historical source on "what decisions actually mattered and why."

**Key frameworks:**
- **Which bets paid off.** Transformers: "the single architecture" that unified sequence tasks. Mixture of Experts: "models bigger without proportional inference cost." The recurring pattern: take an existing architecture, add a principled extension, get multiplicative gains. Not random tinkering.
- **Debugging at scale.** "You can have bugs in your code that do nothing, make your model worse, or make it better — and you discover something new because you've never tried this bug at scale before." Neural nets are so tolerant of noise that errors pass through silently. "You don't even know that the thing is going on."
- **The stacking problem.** "When you put a bunch of improvements together and try to integrate them at large scale — things that you think are independent often interact in funny ways. If you improve the video data handling AND the parameter update, maybe those interact more for video data than for something else." Most improvements need re-validation after stacking.
- **25% AI-generated code.** "25% of the characters checked into our codebase are generated by our AI-based coding models." First time this number was said publicly.
- **Scale of future AI compute.** "We're going to need like a million automated researchers to invent all of this stuff." World GDP will go "orders of magnitude higher" with artificial engineers.
- **How to run experiments.** "My dream: wake up, come up with an idea, hack it up in a day, run experiments, get initial results in a day — this looks promising. That is very achievable at small scale as long as you keep a nice experimental codebase where an experiment takes an hour or two, not two weeks."
- **Noam Shazeer's design process.** "I want a nice simple codebase I can fork and hack, some baselines, and small-scale experiments that run in an hour. Then scale up what works. Then integrate and check interactions."

**Numbers:**
- 25% of Google's codebase characters are now AI-generated
- GDP: "orders of magnitude higher than today" with artificial engineers (longer-term claim)

**Near-verbatim quotes:**
- "25% of the characters we're checking into our codebase these days are generated by our AI-based coding models."
- "We're going to need like a million automated researchers to invent all of this stuff."
- "Neural nets are so tolerant of noise — you can have things set up kind of wrong and they just figure out ways to work around it."

**Why in the guide.** The most credible historical account of which decisions actually mattered across 25 years of frontier AI. Especially valuable for the "how to run experiments" section — the most honest description of how actually productive AI research operates day-to-day.

---

## Is Human Data Enough? (David Silver) — https://www.youtube.com/watch?v=zzXyPGEtseI — transcribed — MUST

**Thesis.** AlphaGo/AlphaZero's lead arguing that "the era of human data" is ending and "the era of experience" (RL from self-generated experience) is the path past human-level. From the person who ran the experiments that proved it. Human data = fossil fuel; RL from experience = renewable energy.

**Key frameworks:**
- **RLHF's ceiling.** "RLHF systems cannot go beyond human knowledge. If a rater doesn't recognize a new idea and underappreciates a series of actions that would actually be far better, there's no way the system will ever learn to find that sequence."
- **Grounding problem.** RLHF is *ungrounded* — "a rater judges whether a cake recipe is good or bad before anyone has actually made and eaten the cake. Grounded feedback would be someone actually eating the cake and reporting whether it's delicious." The distinction: inherited human experience (somewhat grounded) vs actual system experience (truly grounded).
- **AlphaProof and math.** AlphaProof uses the same AlphaZero code, with Lean (formal mathematical language) as the reward oracle: "plus one if you prove it, minus one if you don't." Started unable to prove 99.999% of theorems; reached IMO silver medal level. The key insight: mathematics is a domain where verifiable ground truth exists — and that's exactly the condition required for experience-driven learning.
- **Self-generating experience is unlimited.** "As the system gets stronger, it encounters problems exactly appropriate to the level it's at — so it will always generate experience that allows it to solve the next problem. There is no ceiling. This is what differentiates experience from synthetic data."
- **Reward specification and alignment.** "Wouldn't it be great if a human specifies what they want — e.g., 'be healthier' — and the system translates that into a set of numbers to optimize autonomously?" The challenge: naive reward optimization leads to Goodhart's law (minimize resting heart rate → kill the patient). The solution sketch: a system that also reads human distress signals and adapts the reward mixture accordingly.
- **The fossil fuel metaphor.** "Human data is like fossil fuels — discovered in the earth, and we mine and burn it in our LLMs. But we need sustainable fuel that keeps the world going once the fossil fuels are gone. Reinforcement learning is that sustainable fuel."

**Numbers:**
- AlphaProof reached IMO silver medal level (top ~10% of world's best young mathematicians)
- AlphaProof proved a problem that less than 1% of IMO contestants solved — perfect proof
- AlphaZero: same code as Alpha proof, just different "game" (mathematics vs Go)

**Near-verbatim quotes:**
- "We've thrown out the baby with the bathwater. RLHF is very powerful, but it cannot go beyond human knowledge."
- "Human data is like fossil fuels — and I think we've achieved peak data. RL from experience is the sustainable fuel."
- "Once you have a system that can scale and keep learning and learning forever, really the sky's the limit. Mathematics is one of the few areas where everything can be done completely digitally, and there's no fundamental barrier."

**Why in the guide.** The most honest and complete articulation of the path from current RLHF to post-human-level systems, grounded in actual experimental results (AlphaGo → AlphaZero → AlphaProof). The fossil fuel metaphor is the most memorable framing of the transition.

---

## The Arrival of AGI (Shane Legg) — https://www.youtube.com/watch?v=l3u_FAv33G0 — transcribed — STRONG

**Thesis.** The DeepMind co-founder who defined AGI in 2007 revisiting whether the definition still holds. AGI won't arrive as a discrete event — it will be "some years from now, AIs will become so generally capable that people will just talk about them as being AGI." The multi-dimensional capability distribution matters more than a single label.

**Key frameworks:**
- **AGI as capability distribution, not label.** "You can't put it on a single dimension. It may be superhumanly capable at some things, very fragile and weak in others. If you don't understand what that distribution looks like, you're going to miss both the opportunities and the risks." Reality: "it is incredibly capable in some ways and quite fragile in others."
- **Recognition criteria.** "Some years from now, the AIs will become so generally capable — write poetry, learn a card game you just made up, do math, plan a holiday — that it will seem obvious to people that it has some sort of generality of intelligence."
- **System Two Safety.** "Chain of thought monitoring" — inspired by Kahneman's System 1/System 2. For difficult ethical situations, you need to reason carefully about the situation, options, consequences, and evaluate against an ethical framework. System 2 lets AIs catch cases where simple rules fail (e.g., "lying is bad" — but lie to save a life). "The system can sit down, think about the situation, the nuances, the possible actions, the likely consequences, then analyze all of that against some system of ethics."
- **Levels of AGI framework.** AGI capability needs to be measured across multiple dimensions simultaneously — not a single scalar. Capability profiles matter for both opportunity identification and risk management.
- **Continual learning as a requirement.** "The kind of AI we have today doesn't have a life — it's not something which has its own stream of experience that goes on for years and adapts over time. That needs to change."

**Near-verbatim quotes:**
- "I am personally content being out of sync with my field for a long period of time, perhaps decades."
- "People will say 'I've got the latest Gemini 9 or whatever — it can teach itself a card game you just made up.' And it will just seem obvious that it has some sort of generality."
- "It is incredibly capable in some ways and quite fragile in others. You have to take the whole picture."

**Why in the guide.** The person who formally defined AGI in 2007 revisiting whether that definition works — and the "system two safety" concept as a concrete implementation path for alignment that doesn't require interpretability first.

---

## Open Source AI Is AI We Can Trust (Soumith Chintala) — https://www.youtube.com/watch?v=Pzlpbj7t5ko — transcribed — STRONG

**Thesis.** PyTorch beat TensorFlow not because it was technically superior on day one, but because it applied the Bitter Lesson to frameworks: progressive disclosure of complexity (user over research team), incremental ambition over grand vision from V1, and trust built through openness. Open source distributes opportunity in a way nothing else does.

**Key frameworks:**
- **Progressive disclosure of complexity.** "Where the density of users are, I want to keep it in the easy happy path. Where the more niche advanced use cases are, I'll still want people to try them but they need to take additional frictional steps." The design principle: not feature completeness in V1, but Huffman-coding the user population.
- **Incremental ambition beats grand vision.** "There are two models: you have a grand vision and build a giant system, or you get incrementally ambitious — start simple, layer complexity where users are." George Hotz started tiny grad with a 1,000-line limit; now it's 5,000. PyTorch is 190,000. "There's no real magic. A lot of complexity comes from necessities that accumulate."
- **Open source as opportunity distribution.** "I grew up in India, didn't have internet for much of college. I saw that evolution of knowledge slowly getting decentralized — that's what helped me get where I am. I push open source regardless of what I get paid for."
- **Synthetic data misunderstood.** "Synthetic data is useful in neural networks now because humans have figured out symbolic models of the world (physics in 30 parameters, math, language syntax). Synthetic data is a vehicle to impart that symbolic knowledge to neural networks. Where we don't have good symbolic models — synthetic data obviously doesn't make any sense." The hype misses the constraint.
- **Combining search + symbolic + differentiable models.** "The really interesting models are where we're starting to combine search and symbolic stuff with differentiable models — AlphaZero style, AlphaGeometry." This is Soumith's actual research taste: the combination beats pure scaling or pure symbolic.

**Near-verbatim quotes:**
- "Open source has that fundamental way to distribute opportunity that is very powerful."
- "Synthetic data is not a magic wand. It's useful where humans already have good symbolic models — and nowhere else."
- "Progressive disclosure of complexity: keep the happy path easy, hide the advanced stuff behind friction."

**Why in the guide.** The Bitter Lesson applied to framework design — and won. The PyTorch story is the cleanest example of research taste in product form: user-first design beat Google's top-down grand vision. Also: synthetic data's honest constraint is the most grounded public statement on the topic.

---

## Jonathan Frankle: From Lottery Tickets to LLMs — https://www.youtube.com/watch?v=FvF7gim16bQ — transcribed — STRONG

**Thesis.** Frankle explicitly abandoned the Lottery Ticket Hypothesis as a productive research direction because the field changed — and this self-correction is the most instructive thing about his intellectual practice. Research taste requires asking "are these the most important questions NOW?" and being willing to answer "no" for your own work.

**Key frameworks:**
- **Lottery Ticket Hypothesis.** Dense randomly initialized networks contain sparse sub-networks ("winning tickets") that, when trained in isolation, reach comparable accuracy. Finding them requires: train to convergence, prune by magnitude, reset weights to initialization (not zero), retrain. Key result: sparse sub-networks that match the full network's performance at ~10-20% of parameters.
- **Learning rate rewinding.** Better than weight rewinding at initialization — reset learning rate schedule rather than weights. Practical finding: early in training, SGD noise "scrambles" the weights so much that initialization doesn't matter; learning rate warm-up restores the phenomenon.
- **The field changed so the important questions changed.** "I don't know if [lottery tickets] are still the most important questions to work on. The field always changes and we always have to ask: are we working on the most important questions?" This explicit self-questioning is the discipline Frankle models.
- **Design choice discipline.** "In the publication process, if you change anything about a strategy that differs from prior work, someone will accuse you of cooking the books. Always anchor choices in prior work. It's a get-out-of-jail-free card for design choices." Practical research engineering.
- **Scaling laws for pruning.** Collaborated with Jonathan Rosenfeld on empirical scaling laws for iteratively magnitude-pruned networks. Lesson: "getting scaling laws right is hard — it's very easy to fit things on a log-log plot that look good but aren't actually right. The little details matter enormously."
- **From pruning to training 70B models (MosaicML).** The composition problem: "which efficiency tricks stack vs cancel?" Most improvements need re-validation after stacking because interactions are non-trivial. "Most things that seem independent have funny interactions at scale."

**Near-verbatim quotes:**
- "I don't know if [lottery tickets] are the best questions to work on right now. The field has changed pretty fundamentally."
- "Always anchor your design choices in prior work — it's a get-out-of-jail-free card."
- "Getting scaling laws right is hard. It's very easy to fit something to a log-log plot and say 'I have described it' — but the little details matter so much."

**Why in the guide.** The self-correction is the most valuable thing. A researcher who explicitly says "I don't think my own most-cited work is the best thing to work on now" is demonstrating the research taste the guide is trying to teach. Also: the composition problem at scale is the most practical finding for anyone stacking efficiency improvements.

---

## Section Body — The Guide's Own Wisdom (Frontier AI Research Taste)

*(From `## 🔬 Frontier AI Research Taste` in BAD_GUIDE.md, lines 262–395)*

### ▸ Work on important problems, or you'll do good work that doesn't matter
Hamming's hard question: "What are the important problems in your field, and why aren't you working on them?" Most strong builders never ask it. Keep a written list of the 10 problems that would change your field if solved, and check weekly whether what you're doing is on it.

### ▸ Pick by taste, not by what's publishable
Schulman splits research into concept-driven (a new idea) vs execution-driven (make a known idea work). Novelty-seeking optimizes for "nobody did this" when the test should be "this matters." Choose by genuine curiosity plus aptitude, then go to the frontier and follow the anomalies.

### ▸ Bet on the right side of the Bitter Lesson
Sutton's claim: every method built on clever hand-crafted inductive bias eventually loses to scale plus search. If your edge depends on a hand-tuned heuristic beating compute, you will lose on a 12-month horizon. Ask the same of every AI bet you make.

### ▸ Verifiable reward is where the curve goes vertical
Any domain where a solution can be auto-checked (code, math) can be driven hard with RL. Qwen 3 result: 4,000 high-quality verifiable examples beat 4 million low-quality RLHF ones. Quality and verifiability dominate quantity. Build the verifier first; the training loop follows.

### ▸ Fine-tuning is usually a capital trap
Spend millions fine-tuning a model and the next base release erases your edge. Model-agnostic harnesses age better — Poetic AI's meta-system hit 54% on ARC-AGI v2 at $32/problem versus Gemini 3 Deep Think's 45% at $70, for under $100K total. "Vaccinated against the bitter lesson." Keep intelligence in the harness, not in weights you'll rent and lose.

### ▸ Intelligence is efficiency of skill acquisition, not benchmark score
Chollet's definition: a smarter system learns a new skill from fewer examples. LLMs interpolate inside the training manifold beautifully and extrapolate badly. When you read a SOTA number, ask whether the gain is interpolation on a saturated distribution or genuine generalization. Only the second kind is a primitive.

### ▸ Stay close to the run, build taste by noticing where models break
Sholto Douglas and Trenton Bricken went zero-to-frontier in ~1 year by picking problems adjacent to what's working but poorly understood (superposition, long context, RL reward) and staying close to actual training runs. Taste is built by watching where models behave unexpectedly. Treat every weird agent failure as a research lead, not a bug ticket.

### ▸ Steelman the strongest disagreement before you bet
LeCun argues scaling autoregressive LLMs is a dead end. Sutton, who wrote the Bitter Lesson, now says LLMs can't learn from experience at all. Ilya and Gwern argue the opposite. The taste skill is holding that contradiction between people who are each usually right, and forming your own bet instead of joining a tribe. When two sources you respect collide, that spot is the frontier. Sit in it.

### ▸ De-risk the load-bearing assumption first, not the fun part
Steinhardt models a research project as a sequence of bets where each experiment buys information. Order the work by information gained per unit of time, and kill the riskiest assumption before you build anything on top of it. Prove your verifiable signal actually predicts the outcome before you build the training loop around it.

**What this section makes you better at:**
- Choosing which problems to work on (rather than defaulting to what's tractable)
- Reading a SOTA result and knowing whether it's a primitive or a benchmark artifact
- Surviving the period when your contrarian bet looks wrong (biological inspiration as top-down conviction)
- Knowing when to abandon your own work (Frankle on lottery tickets)

---

## → Top Actionable Takeaways for @Seventydotleven

1. **Write your 10-problem list.** Hamming's question applied to your stack: what are the 10 problems in AI-native products / agentic systems / Rust web infrastructure that would change the field if solved? Check weekly. The discipline is the point, not just having the list.

2. **Build the verifier before the training loop.** Every project you touch that involves AI output — find the verifiable signal first. Sent reply that books a meeting is your verifiable signal. Make that measurable before building the RL harness around it. 4,000 high-quality verifiable examples beat 4M RLHF ones.

3. **Keep intelligence in the harness, not the weights.** Spending on fine-tuning creates capital trapped in weights that the next base release obsoletes. Model-agnostic composite architectures (RAG + retrieval + verifiers + tools) survive every frontier release. Poetic AI: $100K total, 54% ARC-AGI v2, beats Gemini 3 Deep Think. Lancelot wins this game automatically — the harness is the moat.

4. **Stay close to runs.** Sholto and Trenton went from zero to frontier in 1.5 years by building intuition from anomalies. Treat every weird Lancelot/Skale agent failure as a research lead: "why did this break here?" is a pointer to an unexplored mechanism, not just a bug.

5. **Apply the 50-RL-steps insight.** Before building complex pipelines, try: can RLVR on 50 steps unlock the knowledge that's already in the model? The 5%→50% MATH-500 jump came from 50 steps, not pre-training new knowledge. What's your equivalent? What verifiable task could you run 50 RLVR steps on with Skale's outputs?

6. **Never lead with infrastructure fingerprinting as architecture.** Same test applies to your research taste: SOTA numbers on benchmarks that are saturated interpolation tell you nothing about whether something is a primitive. Ask Chollet's question: is this new generalization, or is it curve-fitting on training distribution?

7. **Steelman the Sutton / LeCun position.** Before committing to any LLM-based architecture, force yourself to argue Sutton's case: there's no ground truth, no goal, no grounding from actual world interaction. Where does this apply to your system? The answer points to where experience-based RL should eventually replace prompt engineering.

8. **Anchor design choices in prior work.** Frankle's rule: in any novel system, anchor every non-obvious design choice in prior work or ablation results. Don't invent choices that invite "why did you do that?" questions — they obscure whether the system works. This applies to product architecture decisions, not just papers.

9. **The composition problem is your biggest scaling risk.** When you stack improvements (RLVR + retrieval + streaming + caching) on Lancelot or Skale, each combination needs validation. "Things that are independent often interact in funny ways at scale" (Noam Shazeer). Build the ablation habit before production.

10. **Sit in the Sutton/Ilya disagreement.** Both are correct in different domains. Sutton is right that LLMs lack ground truth from world interaction. Ilya is right that pre-training on internet text is an extraordinary shortcut. Your bet: harness + verifiable rewards = get the shortcut (pre-training knowledge) + the sustainable fuel (experience). That combination is where the curve goes vertical.
