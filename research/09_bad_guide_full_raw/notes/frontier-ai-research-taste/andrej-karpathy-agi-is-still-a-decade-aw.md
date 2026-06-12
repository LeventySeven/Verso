# Andrej Karpathy — AGI is Still a Decade Away

**Source**: https://www.dwarkesh.com/p/andrej-karpathy
**Speaker**: Andrej Karpathy, ex-OpenAI/Tesla, founder Eureka Labs
**Format**: Dwarkesh Patel podcast (~2h25m), published October 2025
**Status**: read_full — full transcript extracted via podscripts.co and corroborated by Zvi Mowshowitz analysis (thezvi.substack.com) and the official Dwarkesh show-notes page. Verbatim quotes confirmed across multiple sources.

---

## What Karpathy Actually Argues

### AGI Timeline and the "Decade of Agents" Framing

Karpathy refuses "the year of agents" framing explicitly, substituting "the decade of agents." His estimate: AGI roughly 10 years out, derived from "15 years of prediction experience and intuition." Definition: "a system you can go to that can do any task that is economically valuable... at human performance or better." This is digital knowledge work (~10-20% of economy), explicitly excluding physical work.

The bottlenecks are not theoretical impossibilities but engineering challenges: insufficient intelligence, missing multimodality, no continual learning, unreliable computer use. "They're just cognitively lacking and it's just not working" — his assessment of current agents for end-to-end tasks.

### The "March of Nines" as the Real Gap

Karpathy uses self-driving as the parable. Waymo works but isn't "done" because of the "march of nines" — reliability requirements. Moving from 90% to 99.999% requires "every single nine is a constant amount of work." This is the demo-to-product gap in quantitative form. Most agents are at the demo stage; production deployment requires nines of reliability that current systems don't have.

### RL is Terrible — The Core Argument

Karpathy's framing: "RL is terrible but everything else we've tried has been worse." The technical flaw: outcome-based rewards upweight entire successful trajectories indiscriminately. Example: solving math problems via 100 parallel attempts, then upweighting all tokens in successful paths — but 97 paths were wrong. The model cannot distinguish which steps contributed to success. He calls this "sucking supervision through a straw."

Process supervision (intermediate feedback) would fix this but faces:
- LLM judges with billions of parameters are "gameable" — models find adversarial examples (outputting "da-da-da" patterns or "dhdhdhdh") that receive perfect scores
- No robust automated way to assign partial credit to incomplete solutions

The implication for agents: RL fine-tuning is the current tool-use training mechanism, and it is fundamentally weak signal. Every tool-call trajectory that "succeeds" gets upweighted wholesale, even when intermediate steps were wrong. This is why reliability is hard to engineer via RL.

### Context Window vs. Pre-Training: 35 Million × Information Density Gap

Critical quantitative distinction:
- Context window: ~320 kilobytes per token (KV cache, test-time)
- Pre-training weights: ~0.07 bits per token (compressed into model parameters)
- Ratio: approximately **35 million × more information density** in the context window than in weights

Implication: "Knowledge from pre-training is a hazy recollection compared to context-window information." This explains why in-context learning produces more coherent responses than relying on trained weights — and why context engineering (what goes into the window) is so much more impactful than model fine-tuning for most production tasks.

### Model Collapse and Synthetic Data

Models develop "collapsed" output distributions. Quote: "All of them are the same. Any individual sample will look okay, but the distribution is quite terrible." Asking for jokes yields roughly three jokes across all requests. Training on self-generated synthetic data amplifies collapse — model outputs have low entropy, and training on low-entropy data compresses diversity further.

Humans avoid over-collapse through varied experiences, "daydreaming," exposure to new information. LLMs lack equivalent distillation mechanisms (analogous to sleep in humans).

The practical implication: synthetic data pipelines that feed model outputs back as training data are systematically degrading diversity.

### Pre-Training as "Crappy Evolution"

Pre-training accomplishes two distinct things: (1) knowledge accumulation (potentially a distraction from the goal) and (2) algorithm bootstrapping (in-context learning, reasoning circuits). Karpathy proposes distilling a smaller "cognitive core" — stripped of encyclopedic memory, retaining only algorithmic intelligence. Estimate: ~1 billion parameters for viable cognitive core, "though he acknowledges this could drop further."

The cognitive core insight reframes what the model layer is for: Verso's model abstraction should care about the reasoning circuits, not the memorized facts. Retrieved facts go in context.

### Missing Brain Parts — The Architectural Gap

Karpathy maps current transformers to cortical tissue (plastic, multi-modal capable). What's present:
- Transformers ~ cortical tissue
- Reasoning/planning ~ prefrontal cortex
- RL fine-tuning ~ basal ganglia

What's missing:
- **Hippocampus** (memory consolidation, cross-session distillation)
- **Amygdala** (emotion/instinct, value assignment)
- **Cerebellum** (procedural skill, motor/process memory)
- **Ancient brain nuclei** (homeostatic drives, prioritization)

For Verso: the hippocampus gap is the memory layer gap. Current agents have no mechanism for distilling episodic experience into long-term memory across sessions. The "continual learning" problem is the hippocampus problem.

### Coding as the Current Beachhead — And Why It Won't Generalize Easily

Why coding dominates LLM adoption: code is "fundamentally worked around text" with pre-built infrastructure (diffs, IDEs, version control). Slides, visual domains, and bespoke architectures lack equivalent support. Karpathy's nanochat experience: "the models couldn't comprehend [his custom DDP container] and kept trying to use DDP instead." Standard library bias is the failure mode.

Critical nuance: "autocomplete > full agents" for bespoke code. Context-aware autocomplete outperformed full agent generation for non-standard architectures. This is a direct challenge to the "replace the developer" agent framing.

### Vibe Coding and Boilerplate vs. Real Engineering

"Vibe coding only works with boilerplate stuff." Models "remember wrong" by defaulting to common internet patterns rather than custom implementations. This isn't a capability gap — it's a training distribution bias. Models are optimized for the median codebase, not the specific codebase.

### AGI as Continuous with Historical Productivity Growth

Rather than a discontinuous singularity, AGI "will blend into" the existing 2% annual GDP growth trend. The Industrial Revolution, computers, and mobile phones remain invisible in GDP curves because diffusion happens gradually. The implication: don't bet on a visible transition moment; bet on sustained incremental capability expansion.

(Zvi strongly disagrees with this point — notes internal contradiction: if superintelligent automation occurs, 2% GDP growth shouldn't persist. This is flagged as contested.)

### Superintelligence and Control

Karpathy expects "gradual loss of control and understanding" through competing autonomous entities acting on behalf of different stakeholders — not a single takeover scenario. This mirrors existing phenomena where CEOs wield power without deep understanding of their organizations.

### Education Vision (Eureka Labs)

Post-AGI education: "fun, like going to the gym" — learning divorced from economic necessity. Karpathy is building Eureka Labs to prevent scenarios where disempowered humans atrophy. "If I can't build it, I don't understand it" — Feynman-style rigor as the educational philosophy. Children excel at rapid concept acquisition despite poor memory; LLMs memorize extensively but struggle with abstract pattern extraction.

---

## Verbatim Quotes (cross-confirmed from podscripts.co and thezvi.substack.com)

- "RL is terrible but everything else we've tried has been worse."
- "Sucking supervision through a straw" [on outcome-based RL rewards]
- "All of them are the same. Any individual sample will look okay, but the distribution is quite terrible." [on model collapse]
- "Vibe coding only works with boilerplate stuff."
- "The problems are tractable, but they're still difficult." [on AGI timeline]
- "They're just cognitively lacking and it's just not working." [on current agents for end-to-end tasks]
- "I have 15 years of prediction experience and intuition and I average things out." [on decade estimate]
- "The decade of agents" [explicit alternative to "year of agents" hype]

---

## VERSO RELEVANCE

### [SHARPENS §5.1 loop] RL's weak-signal problem directly affects tool-call reliability

The mechanism Karpathy identifies — RL upweights entire trajectories including wrong steps — is exactly the failure mode for tool-call reliability in agentic loops. If the final answer was correct, every tool call in that trajectory gets reinforced, including redundant or wrong ones. This sharpens Verso's loop design: the harness should not assume RL-trained tool-call behavior is calibrated. Per-step validation (the `validate()` primitive from Parahelp) and explicit per-tool eval suites are the engineering response to weak RL signal.

**Verdict**: Sharpens the justification for validate-before-execute as a loop primitive, not middleware.

### [NEW-IDEA] 35M× context density gap → context is not a nice-to-have, it's the computation substrate

The quantitative gap (320 KB/token in context vs. 0.07 bits/token in weights) means the context window is where most of the "intelligence" in a well-engineered agent run actually lives. This is a strong new framing for Verso's §5.2 context engineering: the model weights provide the reasoning circuits (cognitive core), but the context window provides the knowledge and working memory for a specific task. Verso's pitch is essentially: "we help you engineer the 35M× layer." RunContext + ContextBundle.inspect() are on the right track; the framing should be sharpened.

**Verdict**: New framing with direct PRD impact. Not overkill.

### [CONTRADICTS §5.4 memory] "Continual learning" gap means cross-session memory distillation is the hard missing piece

Karpathy explicitly identifies the hippocampus gap (no mechanism for distilling episodic experience across sessions) as a fundamental missing capability. Verso's 4-tier typed memory addresses this architecturally, but Karpathy's framing suggests the distillation mechanism itself (what goes from episodic → semantic → weights) is an unsolved research problem, not just an engineering problem. The temporal versioning layer in §5.4 is the right instinct; calibrate expectations — this is harder than it looks.

**Verdict**: Contradicts implicit assumption that memory distillation is solved. Calibrate §5.4 claims.

### [SHARPENS §5.3 tools] Boilerplate bias means tool schemas need tight, non-standard specificity

"Vibe coding only works with boilerplate stuff" and "models couldn't comprehend custom DDP container" map to a tool design principle: if tool schemas and descriptions use standard names and patterns, models will default to standard interpretations, ignoring custom semantics. Verso's tool documentation quality gate (description character minimum, example required) is the right instinct; the deeper principle is: every tool description must explicitly override the model's prior from pre-training.

**Verdict**: Sharpens tool design guidance without adding complexity.

### [CONFIRMS §6.1 durable] "March of nines" quantifies exactly why durable/checkpointing matters

Karpathy's march-of-nines framing (each additional nine of reliability requires constant engineering work) gives Verso a precise vocabulary: the tactical layer operates at ~90% reliability; durable execution (checkpoint/resume, HITL gates) is the mechanism for reaching the higher nines for long-horizon tasks. This isn't a nice-to-have — it's the only path to the reliability level that unlocks user delegation.

**Verdict**: Confirms the durable layer's purpose with a memorable, citable framing.

### [SHARPENS §12 positioning] "Decade not year" as intellectual honesty signal

Karpathy's explicit pushback on "year of agents" hype is a positioning signal: serious practitioners are 5-10× more pessimistic than the hype cycle suggests. Verso's positioning should match this register — frame the framework as serious infrastructure for a decade-scale transition, not a plug-and-play solution for the current capability level. Counter-position against frameworks promising "agentic magic" with honest acknowledgment of current agent limitations and explicit reliability engineering.

**Verdict**: Positioning alignment. No technical overkill.
