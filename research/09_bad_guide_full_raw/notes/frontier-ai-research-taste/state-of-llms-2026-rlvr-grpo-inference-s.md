# State of LLMs 2026: RLVR, GRPO, Inference Scaling — Sebastian Raschka

**Source:** MAD Podcast with Matt Turck · January 29, 2026
**URL:** https://www.youtube.com/watch?v=K5WPr5dtne0
**Speaker:** Sebastian Raschka (researcher, author of "Build a Large Language Model from Scratch")
**Duration:** 1h08m

---

## STATUS: read_partial

No full transcript retrieved. Sources consulted:
1. MAD Podcast search results — episode description with timestamps recovered
2. Raschka's companion Substack article "The State of LLM Reasoning Model Training" (magazine.sebastianraschka.com) — substantial technical content
3. Raschka's Substack note on LLM eras (substack.com/@rasbt/note/c-190575668)
4. Raschka interview on Lex Fridman Podcast #490 "State of AI in 2026" (Feb 1, 2026) — verbatim quotes
5. Raschka interview with Hugo Bowne-Anderson "LLM Architecture in 2026" (Apr 13, 2026)

The MAD podcast episode is the canonical video; the Substack articles and Lex Fridman appearance (same week, same framing) substantively replicate its content and are used as the primary source for technical claims.

---

## The LLM Eras Timeline

Raschka proposes a periodization of LLM development:

| Year | Dominant Technique |
|---|---|
| 202x | Pre-training (foundation era) |
| 2022 | RLHF + PPO |
| 2023 | LoRA / parameter-efficient SFT |
| 2024 | Mid-training (synthetic data, domain specialization, long-context stages) |
| 2025 | RLVR + GRPO |
| 2026? | Inference-time scaling |
| 2027? | Continual learning |

The question marks on 2026–2027 are intentional — Raschka treats these as plausible next axes rather than confirmed bets.

---

## Core Claims

### 1. RLVR (Reinforcement Learning with Verifiable Rewards)

RLVR bypasses learned reward models by using deterministic verification tools for feedback:

- **Accuracy rewards:** symbolic verifiers (calculators for math, compilers for code) provide binary correctness signals
- **Format rewards:** structural requirements like `<think></think>` tags

Key efficiency gain: eliminates "expensive models in the training procedure: the reward model and the value model (critic)." Unlike RLHF, which requires annotators and a separate reward model, RLVR scales with automated verification.

The mechanism "unlocks" reasoning already latent in base models — self-verification and reflective reasoning "emerged naturally during training without explicit instruction."

### 2. GRPO (Group Relative Policy Optimization)

GRPO modifies PPO by eliminating the critic/value model. Instead it "samples multiple answers from the policy model itself and uses their relative quality to compute the advantages."

**Key efficiency:** removes one full-sized LLM from the training pipeline, significantly reducing memory and compute.

**Known problems with naive GRPO:**
- Length bias: "GRPO inadvertently favors longer responses due to mathematical biases in loss calculations"
- Solutions: Dr. GRPO (removes length/std normalization), token-level reward models, explicit length penalties

**2025 GRPO stability improvements:**
- Zero gradient signal filtering + active sampling (filter prompts where all responses are always right or always wrong)
- Token-level loss computation
- Elimination of KL penalty terms in certain scenarios
- Truncated importance sampling
- Adjusted advantage normalization

### 3. Inference-Time Scaling

> "inference scaling...took a smaller model further than pre-training a larger model like Claude 4.5"

Definition: allocating additional compute during answer generation rather than during training, trading latency/cost for quality. Evidence: DeepSeekMath-V2 achieved gold-medal math competition performance through parallel sampling + internal meta-judges + iterative refinement.

Raschka's framing: accuracy improvements can come from either training-time or test-time compute — these are substitutable, with test-time compute favored when base model training cost is already sunk.

O3 required "10× more training compute compared to o1" — demonstrating post-training RL investment yields measurable gains beyond conventional pre-training scaling.

### 4. Architecture Stability

> "It's still the same architecture...you can convert one from one into the other by just adding these changes, basically."

The transformer has not been fundamentally replaced despite years of alternatives. Architectural tweaks (MoE, sliding window attention, multi-head latent attention, normalization changes) are incremental, not discontinuous.

Notable: Hybrid architectures (Qwen 3.5, Nemotron 3) show "near-linear scaling properties" making long-context agentic workflows "significantly more affordable and performant."

DeepSeek's Multi-head Latent Attention (MLA) "wins the KV cache war by drastically reducing memory overhead without performance hits."

### 5. Mid-Training as a Distinct Phase

Mid-training addresses dataset distribution problems: "you focus, for example, on long context documents...you don't have that many long context documents" during initial pre-training, warranting a dedicated intermediate phase. This is different from fine-tuning (SFT) — it uses the same pre-training objective but on curated domain-specific data.

### 6. Emergent Behaviors from RL

Paper evidence: logic puzzle training transfers to mathematical benchmarks. Reasoning extends to medicine, chemistry, psychology via soft-scoring methods. Models learn search integration without hand-coded strategies.

**Caveat:** Paper [13] suggests "self-correction already appears earlier during pre-training," complicating attribution of reasoning solely to RL. Another paper found many reported RL improvements "might just be noise" on small benchmarks like AIME24, with "gains not statistically significant" in controlled settings.

### 7. Benchmaxxing Concern

Raschka "increasingly trusts real usage over benchmark scores." RLVR enables optimization for benchmark performance at the cost of generalization — models can game known benchmark formats while reasoning quality on novel problems lags.

### 8. Agentic Implications

> "Agent Harnesses need to be continuously simplified as frontier models are post-trained on agent trajectories. Teams that don't strip back their scaffolding risk the harness getting in the way of a more capable model."

This is a direct consequence of post-training: as models internalize tool-use and multi-step reasoning from RLVR training, the orchestration scaffolding that compensated for weaker base models becomes actively harmful.

### 9. Process Reward Models (PRMs)

Identified as "the next frontier" — verifying intermediate reasoning steps to solve hallucination in the middle for complex math and code tasks, as opposed to outcome-only verification.

### 10. Domain-Specific Scaling

Untapped value: specialized domains (pharma, law) with proprietary data that cannot go into public pre-training. "They at some point will hire people from other frontier labs to build their in-house models on their proprietary data, which will be another unlock."

### 11. Diminishing Returns Observation

"We are approaching the limits of what scaling model size and data alone can achieve" — evidenced by muted reception to GPT-4.5 and Llama 4 releases. The implication: the next axis of progress is post-training depth (RLVR, PRMs, mid-training) rather than raw pre-training scale.

---

## Key Timestamps (from show notes)

| Time | Topic |
|---|---|
| 14:04 | MoE efficiency tweaks |
| 24:54 | Process Reward Models |
| 38:41 | Benchmarking concerns |
| 47:36 | Tool use |

---

## VERSO RELEVANCE

### [SHARPENS §5.4 memory / §5.1 loop] — Inference-time compute as model capability proxy

Raschka's claim that inference-time scaling "took a smaller model further than pre-training a larger model" directly informs Verso's model selection layer (§6.4). Role-tiered model selection should account for inference-compute budget as a first-class parameter, not just model size or cost per token. A model run with chain-of-thought + tool verification may outperform a "larger" model on the same task at lower training-compute cost.

### [SHARPENS §6.1 durable / §5.1 loop] — Harness simplification imperative

*"Teams that don't strip back their scaffolding risk the harness getting in the way of a more capable model."* This directly validates Verso's anti-scaffolding positioning. The harness must be minimally prescriptive — not because minimalism is philosophically pure, but because RLVR-trained models have internalized orchestration patterns that external scaffolding will contradict. The <200-line loop discipline is a practical hedge against scaffolding rot.

### [NEW-IDEA §5.5 evals] — GRPO length bias as an eval contamination signal

The documented GRPO length bias (models score higher on benchmarks by generating longer outputs) is a concrete eval-failure mode that Verso's `define_outcome(bounded)` must guard against. If Verso's judge-panel evaluates agent outputs, output-length must not be a latent proxy for quality. This is a specific, implementable invariant: judge panels should normalize for output length, or at minimum flag when winning outputs are systematically longer.

### [CONFIRMS §12 positioning] — Post-training era favors harness simplicity

The periodization (pre-training → RLHF → LoRA → mid-training → RLVR → inference scaling) shows each era deprecates the scaffolding workarounds of the previous era. Verso's bet that "the loop is not the product" is confirmed: as RLVR-trained models make tool-use and multi-step reasoning more reliable, the value of elaborate loop orchestration decreases. The product is the harness discipline (evals, context engineering, seam) that survives model generational changes.

### [SHARPENS §6.4 model] — PRMs as next-generation tool-verification pattern

Process Reward Models verify intermediate reasoning steps, not just final outcomes. For Verso's tool dispatch layer (§5.3), this suggests a forward-looking pattern: rather than only checking final tool output correctness, the harness should support intermediate verification hooks. The `{data, error, ok}` dispatch pattern would extend naturally to per-step PRMs.

---

## No-Overkill Verdict Per Finding

| Finding | Verdict |
|---|---|
| Inference-time compute substitutes for model size | Implement as model selection hint, not a new subsystem |
| Harness simplification imperative | Validates existing <200-line constraint; no new code needed |
| GRPO length bias in evals | Add length-normalization note to eval spec; one-liner invariant |
| RLVR era confirms anti-scaffolding bet | Positioning confirmation; no code change |
| PRMs as intermediate verification | Flag for future tool dispatch extension; not MVP |
