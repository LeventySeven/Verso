# State of AI in 2026 (Lex Fridman Podcast #490)

**Guests**: Sebastian Raschka (Build a Large Language Model from Scratch) + Nathan Lambert (Ai2 post-training lead, RLHF Book author)  
**Host**: Lex Fridman  
**URL**: https://www.youtube.com/watch?v=EV7WhVT270Q  
**Duration**: 4h25m  
**Published**: February 1, 2026  
**Status**: read_full — official transcript found at https://lexfridman.com/ai-sota-2026-transcript/ and fetched in full. Additional cross-referenced with Raschka's own blog post (sebastianraschka.com/blog/2026/state-of-ai-interview.html) and podscripts.co transcript mirror.

---

## What They Actually Argue

### Scaling Laws: Still Alive, Shifted Axis (Raschka ~01:02, Lambert ~49:07–55:13)

All three scaling axes remain active in 2026:

1. **Pre-training scaling**: model size × dataset size follows power-law across 13+ orders of magnitude of compute. Neither speaker believes this has "ended."
2. **Inference-time scaling (o1-style)**: models spend seconds to hours generating hidden reasoning before producing output. Linear relationship between RL training time and capability improvement.
3. **RL/RLVR scaling**: reinforcement learning with verifiable rewards shows "log x-axis → linear increase" in accuracy.

> "I'm kind of bullish; they're all really still working, but the low-hanging fruit has mostly been taken." — Nathan Lambert (49:07)

> "It's held for 13 orders of magnitude of compute; why would it ever end?" — Nathan Lambert (55:13)

> "I wouldn't say pre-training scaling is dead; it's just that there are other more attractive ways to scale right now." — Sebastian Raschka (01:02:08)

The economics: pre-training costs $2–5M for frontier models; but the recurring inference cost dwarfs training investment. The ROI calculation has shifted toward post-training and inference-time compute, not because pre-training stopped working but because alternatives now offer better marginal returns.

### Post-Training Is the Skill Unlock (Raschka ~08:18, Lambert ~01:12)

> "RL post-training is more like the skill unlock, where pre-training is like soaking up the knowledge." — Sebastian Raschka (08:18)

Post-training stages:
1. **Supervised Fine-Tuning (SFT)**: instill instruction-following behavior
2. **DPO / preference learning**: align outputs with human preferences
3. **RLVR (Reinforcement Learning with Verifiable Rewards)**: train on tasks where correctness can be verified (math, code). The model uses tool feedback (Python interpreter, test runners) as the reward signal — it tries a tool, observes output, adjusts.

Lambert's team ran **5 days of RL in November 2024**, then extended to **3.5 weeks in December** with notable capability improvements. Comparing to previous year: 5 days of RL "is a very long time compared to 2024."

> "Reinforcement Learning with Verifiable Rewards training just let the models pick up these skills very easily." — Nathan Lambert (50:46)

Specific skill example: Claude Code, after RLVR training, can "use CLI commands, handle Git, search for information" — capabilities absent a year prior. This is tool use learned through RL, not SFT.

### Architecture: Fundamentally Unchanged Since GPT-2 (Raschka ~00:40–00:47)

> "It fundamentally is still the same architecture." — Sebastian Raschka (00:44:09)

> "I always start with my GPT-2 model and just add different components and you get from one to the other...a lineage." — Sebastian Raschka (00:44:37)

Tweaks that exist but haven't replaced the core:
- Mixture of Experts: sparse activation, different experts for different inputs
- Multi-head latent attention: reduces KV cache size
- Group query attention, sliding window attention
- FP8 training: reduces memory per parameter for scale
- Gated delta nets: linear-scaling attention alternatives

None has replaced the autoregressive transformer. Text diffusion and Mamba (State Space Models) are active research areas but remain alternatives, not replacements.

### Tool Use as the Hallucination Solution (Raschka ~00:47:22)

> "One of the best ways to solve hallucinations is to not try to always remember information...why not use a calculator app or Python?" — Sebastian Raschka (00:47:22)

> "gpt-oss is kind of the first open-weight model that was really trained with tool use in mind...the LLM is able to do a web search or call a Python interpreter." — Sebastian Raschka (00:32:33)

Tool use is positioned not as a convenience feature but as an architectural response to the memory/reliability limitation of next-token prediction. The model routes computation to external verifiers rather than attempting to internalize everything.

### Claude Code and the Agentic Pattern (Raschka ~00:22, Lambert ~00:27)

> "Claude Code is a bit more agentic. It touches more things; it does the whole project for you...it is not taking over completely." — Sebastian Raschka (00:22:29)

> "Claude Code makes it fun to build things...you can have an intermediary and not have to do the awful low-level work." — Nathan Lambert (00:27:45)

Both speakers describe an emerging pattern: the agent handles multi-step project-level work, the human maintains oversight ("it is not taking over completely"). This is close to Verso's tactical agent with optional HITL, not a fully autonomous system.

### Open Source: China's Licensing Bet (Raschka ~00:36, Lambert ~00:21)

> "Open weight models from China...have friendlier licenses...unrestricted open source licenses." — Sebastian Raschka (00:36:21)

> "Chinese companies...realized...open weight models as an ability to influence...the growing AI expenditure market." — Nathan Lambert (00:21:26)

Western open models (Gemma, Mistral) often have user caps or commercial restrictions. Chinese models (DeepSeek, Qwen) use truly open licenses to build global developer mindshare. Lambert argues this is a strategic play: open-weight release builds influence even when API revenue isn't the goal.

Barrier: US firms won't use Chinese APIs for security reasons, so the influence operates through open-weight adoption in developer communities.

### Data Quality and Curation (Lambert ~01:11)

> "you can sample small things...train small models on each...measure their performance on evaluations...do basic linear regression." — Nathan Lambert (01:11:56)

Data curation methodology: sample small subsets of candidate sources (Common Crawl, GitHub, Stack Exchange, Reddit, Wikipedia) → train small proxy models → benchmark performance → linear regression to find optimal mixture. High-quality sources: Semantic Scholar academic PDFs, arXiv, curated GitHub repos.

Legal exposure: Anthropic faced a $1.5B copyright lawsuit after torrenting books. This signals licensing will increasingly constrain data choices.

### Memory and Catastrophic Forgetting (Raschka ~01:06)

> "Catastrophic forgetting. So, you teach it something, it forgets other things. It's not 100% forgetting, but there's no free lunch." — Sebastian Raschka (01:06:56)

> "Mid-training is being selective in terms of quality content...the last thing the LLM has seen is the quality stuff." — Sebastian Raschka (01:08:03)

Mid-training as a dedicated phase addresses forgetting: high-quality content trained last sits freshest in the model. This is a training-time analogue to the context window's recency effect.

### Evals: Benchmark vs. Real Performance Gap (Fridman ~00:54)

> "The way it's experienced versus on a benchmark, the actual intelligence might be different." — Lex Fridman (00:54:04)

> "ablation studies: does it make it better or worse?" — Sebastian Raschka (00:39:23)

Both speakers note the divergence between benchmark scores and user experience. Gemini 3 had massive marketing spend but "lost mindshare" — users discovered failures on their actual tasks. Claude Opus 4.5 gained mindshare organically because it held up on real software engineering.

### RL Infrastructure at Scale (Lambert ~01:12)

Actor-learner architecture: actors generate completions across distributed nodes; learners perform gradient updates on tightly-networked compute. This is heterogeneous (unlike homogeneous pre-training GPU clusters). GPU failures are guaranteed at 100K+ GPU scale; redundancy handling differs fundamentally.

xAI planning 1 gigawatt of compute early 2026, 2 gigawatts by year-end.

> "that's a systems problem...in order to enable the scaling laws, especially at pre-training. You need all of these GPUs at once." — Nathan Lambert (00:59:11)

### Compute Economics and Where to Bet (Raschka ~01:02, Lambert ~00:12)

> "If you spend it more on pre-training, it's a fixed cost...With inference scaling, you spend money later per query." — Sebastian Raschka (01:02:47)

> "Google...can develop everything top to bottom...and not have to pay this margin" on chips. — Nathan Lambert (12:28)

Google's vertical integration (TPUs, no NVIDIA margin) is the structural advantage. OpenAI described as "chaotic operationally but lands research breakthroughs." Anthropic's cultural stability and code focus paying dividends.

---

## VERSO RELEVANCE

### [CONFIRMS §5.3 tools / §12 positioning] Tool use as structural hallucination fix, not convenience

Raschka and Lambert both frame tool use as the architectural solution to LLM memory unreliability (the "why not use a calculator?" argument). This is the strongest external confirmation of Verso's position that native Python `@tool` is THE tool path — tools are not bolt-ons, they are structural compensators. The RLVR training evidence strengthens this: tool use capability improves with RL training time, suggesting it's a learnable skill that compounds.

**No-overkill verdict**: confirmed; PRD §5.3 already captures this. The RL angle (tools improve with training time) is worth one line in §5.3 as a model selection consideration.

### [SHARPENS §4 seam / §6.1 durable] "Not taking over completely" describes the seam exactly

Raschka's description of Claude Code — "it does the whole project for you...it is not taking over completely" — is the sharpest user-level articulation of the tactical ↔ durable seam. The agent is agentic but human-in-the-loop on key decisions. This validates the Verso positioning that HITL is not a safety add-on but the default expectation for production agentic work.

**No-overkill verdict**: Use this quote in §4's introduction as a real-world confirmation.

### [NEW-IDEA §6.4 model] Three-axis scaling model changes the model-routing logic

The explicit three-axis scaling framework (pre-training scale, inference-time compute, RL training time) creates a richer model-routing decision space than cost/speed/quality. Verso's cross-model failover and role-tiered models (§6.4) should account for: (1) model reasoning depth (inference-time compute setting, e.g. Claude's extended thinking), (2) whether the task benefits from RL-trained tool use vs. pure completion, (3) compute budget per query. This is more nuanced than current PRD framing.

**No-overkill verdict**: One paragraph in §6.4 distinguishing "reasoning budget" from "model tier" — don't confuse extended-thinking cost with model capability tier.

### [SHARPENS §5.5 evals] Benchmark score ≠ user experience; Gemini 3 as cautionary example

The Gemini 3 case (massive marketing, lost mindshare) vs. Claude Opus 4.5 (organic growth on software engineering) is a concrete instance of why Verso's evals must be task-specific, not benchmark-score-based. Lambert's data curation methodology (train small proxy models, regression to find optimal source mixture) is applicable to Verso's eval design: sample tasks from real workloads, not academic benchmarks, to find where each model actually performs.

**No-overkill verdict**: The "proxy model" methodology for eval design is a concrete NEW-IDEA for §5.5 — use cheap small-model ablations to select context assembly strategies before running expensive full-model evals.

### [CONFIRMS §5.4 memory] Catastrophic forgetting is the production mid-training problem

Raschka's framing of mid-training as the forgetting mitigation phase confirms that memory management is not only an inference-time problem (as in Verso's 4-tier typed memory) but also a training-time architectural concern. For Verso, this reinforces the design of the durable memory layer: the agent's long-term memory store needs update strategies that don't catastrophically overwrite prior knowledge — append-only history is the correct baseline, not overwrite.

**No-overkill verdict**: already confirmed in PRD; append-only history directly addresses this.

### [NEW-IDEA §5.2 context] "Small proxy model + linear regression" for context source selection

Lambert's data mixture methodology — sample small, benchmark, regress — maps directly to Verso's just-in-time retrieval design. Instead of assuming RRF k=60 + asymmetric embeddings is optimal, Verso could use small proxy model ablations across retrieval strategies on actual task distributions to empirically determine the optimal context source mix.

**No-overkill verdict**: This is a research track, not a v1 implementation. Flag as a post-launch eval methodology improvement.

---

## Verdict

Full official transcript available and read. The most actionable VERSO findings are: (1) tool use confirmed as structural compensator (not add-on) by two credible 2026 practitioners; (2) "not taking over completely" as the validated user-level description of the tactical/durable seam; (3) three-axis scaling model requires updating the model-routing logic in §6.4 to distinguish reasoning budget from model tier; (4) small proxy model ablations as a concrete methodology for §5.5 eval design.
