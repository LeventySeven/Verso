# Don't Teach. Incentivize. — Hyung Won Chung (OpenAI)

**Source:** MIT CSAIL EI Seminar, May 2, 2024; YouTube posted September 2024, 36m  
**URL:** <https://www.youtube.com/watch?v=kYWUEV_e2ss>  
**MIT CSAIL event:** <https://www.csail.mit.edu/event/ei-seminar-hyung-won-chung-openai-dont-teach-incentivize-scale-first-view-large-language>  
**PDF slides (image-only, not text-extractable):** <https://files.rdfzer.com/original/2X/c/c6e12541d5ea7105758192b3921701653eab1deb.pdf>  
**Transcript status:** read_partial — no text transcript found. The PDF is image-only and not extractable. The Podwise page requires login. The YouTube video cannot be watched. Content was reconstructed from: (1) Medium article by Brain Titan summarizing the talk; (2) Hyung Won Chung's own X/Twitter thread (tweet 3/11 is publicly indexed: "We can't enumerate every single skill we want from an AGI system because there are just too many of them. In my view, the only feasible way is to incentivize the model such that general skills emerge."); (3) MIT CSAIL event abstract. This is a partial digest — verbatim quotes are limited to what was publicly indexed.

---

## Speaker Context

Hyung Won Chung was a researcher and o1 co-lead at OpenAI when this talk was given. He is a "Foundational Contributor to o1-preview and o1" (his own description). The talk was given approximately when o1 was released (September 2024), making it the insider's explanation of the design philosophy behind o1. Full title: "Don't teach. Incentivize: Scale-first view of Large Language Models."

---

## Core Thesis: Incentivize, Don't Teach

The fundamental inversion: traditional AI training involves teaching models specific tasks one by one. But "we can't enumerate every single skill we want from an AGI system because there are just too many of them. In my view, the only feasible way is to incentivize the model such that general skills emerge." (verbatim, from indexed tweet 3/11)

The fishing analogy Chung uses: "It is better to teach a man how to fish than to give him a fish" — but his version goes further: "Let him know that fish is delicious and keep him hungry." Motivation, not instruction, is the generative force. Teaching produces narrow skill acquisition. Incentivizing produces autonomous skill discovery.

---

## Weak vs. Strong Incentives

**Weak incentive = next-token prediction.** Current large-scale LLMs (GPT-3, GPT-4, Claude) rely on weak incentive learning through next-token prediction. Chung's argument: this simple objective drives models to spontaneously develop reasoning, mathematics, and coding abilities without explicit instruction in those domains. The model learns language as a by-product — "implicit multitask learning." The incentive is weak in the sense that next-token prediction does not directly reward any specific high-level capability; it incentivizes compression of the entire distribution of language, and high-level capabilities emerge as a consequence of that compression.

**Weak incentive requires more compute.** Because the signal is indirect, weak incentives need far more compute to surface high-level capabilities than direct teaching would. This is an intentional trade-off: the model learns more generalizable skills in exchange for higher compute cost.

**Strong incentive = verifiable reward.** The o1 / reasoning model approach moves toward stronger incentive signals: verifiable tasks (math proofs, code execution, formal logic) where correctness can be checked automatically. Rather than predicting the next token, the model is rewarded for reaching correct final answers. This is still incentivizing (the model discovers the chain-of-thought strategy autonomously during training) rather than teaching (humans do not write the reasoning steps as training data).

---

## Scale-First View

The scale-first view: don't design capabilities top-down; design the incentive and scale compute, then harvest what emerges. Key empirical claim: emergent abilities arise without being explicitly programmed as models increase in size and complexity. Capabilities that did not exist at smaller scale appear suddenly at larger scale — including reasoning, coding, multi-step problem solving.

Chung frames genuine scaling as more than adding compute: "genuine scaling means identifying and replacing architectural limitations with more scalable approaches that better leverage growing resources." This is a critique of naive parameter-count scaling — the incentive structure must also be scalable.

**Threshold intelligence.** A threshold level of intelligence is necessary for the incentive structure to work. Below the threshold, the model cannot "understand" what the incentive is rewarding and cannot improve strategically. Above the threshold, the incentive produces exponential capability gains. This is why emergent abilities are threshold phenomena — they are the point at which the model crosses from below-threshold to above-threshold on a given incentive.

---

## Scale Acceleration: Hyperbolic Time Chamber Analogy

Chung compares AI's computational leverage to Dragon Ball's "Hyperbolic Time Chamber" — inside, time moves faster. AI systems can accelerate learning through exponential compute increases (doubling roughly every two years) in ways human learners cannot. A human researcher might take 30 years to develop a deep skill; an AI system with the right incentive structure can compress that into months of training time. This is not metaphor — it is the literal rate of capability acquisition if the incentive is correctly designed.

---

## Incentive Design as a Research Problem

Chung frames incentive design as the central open research problem, not model architecture. Example: designing incentives that reward honest uncertainty assessment could mitigate hallucination by encouraging meta-cognitive abilities. If the model is rewarded for being calibrated (predicting its own uncertainty correctly), it will develop calibration as an emergent skill — rather than being taught to say "I don't know" in specific cases (which fails to generalize).

This generalizes: any capability you want can potentially be induced via a correctly-designed verifiable reward, rather than directly trained via supervised examples.

---

## Connection to o1

The talk was positioned as an insider explanation of the o1 design philosophy. o1's core innovation: training with verifiable rewards on mathematical and coding tasks, allowing the model to develop its own chain-of-thought reasoning strategy without humans providing reasoning traces as training data. The model is incentivized to reach correct answers; it discovers extended thinking as a means to that end. Chung was a foundational contributor to this work.

The post-training regime for o1 is "strong incentive" learning: verifiable correctness signals rather than next-token prediction or RLHF preference pairs. The model is not taught how to reason; it is incentivized to reason correctly and discovers the mechanism.

---

## What Could Not Be Verified

The PDF slides are image-only and not text-extractable. No blog writeup with verbatim transcript was found. The full X/Twitter thread (11 tweets) was behind a paywall at the time of fetching. The Podwise transcript requires login. The exact numerical claims, specific slide content, and the Q&A sections of the talk are unknown. Only the high-level argument and examples from indexed/summarized sources are available.

---

## VERSO RELEVANCE

### [NEW-IDEA — §5.5 — Evals]
Chung's "verifiable reward" design is directly applicable to Verso's eval architecture: define_outcome(bounded) should be implemented as a verifiable reward signal, not just a judge rating. For tasks where correctness is checkable (code runs correctly, API call returns expected schema, math result matches), Verso's eval should use execution-based verification rather than LLM judging. This is stronger signal and cheaper to run. The design choice: make evals verifiable first; use LLM judges only for tasks where verification is intractable.

**One-line verdict:** verifiable evals (execution, schema checks) are stronger than judge-panel evals for any task with a ground truth.

### [SHARPENS §5.1 — Loop]
The "threshold intelligence" framing has a direct agent harness implication: the agent loop's prompt must be above the threshold for the model being used. Below-threshold prompts produce random behavior regardless of incentive quality. For Verso, this means calibrating the base system prompt and tool descriptions to the capability level of the model tier — a Haiku-class model needs more explicit guidance than a Sonnet-class model given the same incentive. The loop should not be model-agnostic in this regard; it should be model-aware.

**One-line verdict:** threshold intelligence = a reason to have model-tier-specific loop configurations, not one-size-fits-all.

### [CONFIRMS §6.4 — Model]
The weak-vs-strong incentive distinction maps to Verso's model routing: weak incentive tasks (open-ended generation, summarization) can use smaller models with next-token-prediction training; strong incentive tasks (tool call selection, code generation, structured output) benefit from models trained with verifiable rewards (o1-class). Verso's role-tiered model routing should encode this distinction: use reasoning-model tier for tasks with verifiable outcomes, standard completion tier for tasks without.

**One-line verdict:** model routing should track incentive structure, not just task complexity.

### [NEW-IDEA — §5.3 — Tools]
Incentive design for tool use: Verso could apply Chung's framework to tool learning. Rather than teaching the agent which tool to use in which situation (supervised examples), design a verifiable reward for tool effectiveness (did the tool call return useful information? did it reduce uncertainty for the next step?) and let the agent learn tool selection strategies through RL. This is "incentivize tool use, don't teach tool patterns." Requires a per-tool-call reward signal — implementable as a lightweight post-call evaluator.

**One-line verdict:** tool selection quality is a learnable skill given the right verifiable per-call reward.
