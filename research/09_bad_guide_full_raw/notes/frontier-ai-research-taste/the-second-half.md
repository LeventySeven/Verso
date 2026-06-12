# The Second Half
**Source**: https://ysymyth.github.io/The-Second-Half/
**Author**: Shunyu Yao (builder of ReAct, SWE-bench, tau-bench; OpenAI researcher)
**Date**: April 10, 2025
**Length**: ~15 min read
**Status**: read_full

---

## Summary of the Source's Actual Argument

Shunyu Yao argues AI is entering a qualitative phase shift — the "second half" — defined by the axis of research effort moving from *solving problems* to *defining and evaluating them*. The essay is written from a uniquely credentialed position: Yao built ReAct (the agentic reasoning-action loop), co-created SWE-bench (the software engineering benchmark), and tau-bench (tool use / agent eval). He's making this argument while building the things it critiques.

### The First Half: Methods Beat Benchmarks

The first half of AI was defined by method innovations. Architectural breakthroughs — backpropagation, CNNs, Transformers — proved universally applicable across multiple domains, which is why methods got all the citations. Yao's citation data: AlexNet has 160,000+ citations; ImageNet has less than 1/3 of that. Transformer has ~160,000 citations; WMT'14 (the translation benchmark it was tested on) has ~1,300 citations. The benchmark was just the occasion to demonstrate the method.

Why did methods dominate? Because the benchmarks weren't the hard part — human activities (translation, image classification) were the obvious thing to evaluate. Novel methods were the differentiator.

### The Working Recipe

Three ingredients converged: (1) language pre-training, (2) computational scale, (3) reasoning-as-action. Together these produced what Yao calls "a working recipe" — a standardized formula that effectively tackles diverse tasks without requiring new ideas. Classical RL failed because it over-invested in algorithms and under-invested in *priors*. "It turned out the most important part of RL might not even be the RL algorithm or environment, but the priors." Language pre-training is the key prior source. Reasoning-as-action (thinking as an implicit action with no world-state change) paradoxically enables RL generalization despite expanding action spaces.

A "great new method can hillclimb many different benchmarks because it's simple and general" — the same method scales across chess, Go, math, coding, writing. This means incremental method improvements yield ~5% gains, while next-generation model scaling yields ~30%.

### The Utility Problem

The "utility problem" is the central paradox: AI has surpassed humans on SAT, bar exams, IOI, IMO, SWE-bench, chess, Go — but this hasn't translated to economic impact or GDP growth. The gap between benchmark performance and real-world utility is wide and widening.

Yao attributes this to misaligned evaluation assumptions, specifically two that were invisible when capabilities were lower:

**1. The auto-execution assumption**: Benchmarks assume tasks execute automatically, without human engagement. Real-world tasks require iterative human interaction — clarification, course correction, approval gates. No benchmark captures the feedback loop quality.

**2. The i.i.d. assumption**: Benchmarks evaluate tasks independently and identically distributed. Real-world workflows are sequential: Google SWE agents gain familiarity with a codebase over repeated runs, users adapt to system behavior, agents build context over time. Sequential performance (not independent trial performance) is what matters economically, but no benchmark measures it.

These assumptions were acceptable when capabilities were low — you couldn't even get a model to do the task once, so measuring it once in isolation was fine. Now they are the bottleneck.

### The Second Half: Define Problems, Don't Solve Them

"The second half of AI — starting now — will shift focus from solving problems to defining problems." Research value moves from proposing methods that hillclimb existing benchmarks to constructing novel evaluation setups that break the recipe. "Game-changing research requires breaking the recipe through new assumptions rather than incremental method improvements."

The benchmark race has industrialized: "The recipe has essentially standardized and industrialized benchmark hillclimbing without requiring much more new ideas." Historical benchmark saturation rate has compressed from years to ~3 years (human exam-based benchmarks saturated within 3 years of GPT-4).

The recipe-breaking moves are:
- Design evaluations that capture real-world utility (human-in-the-loop, sequential/non-i.i.d.)  
- Find task structures where the recipe fails — where language priors and RL aren't enough
- Solve these new evals (which may require new methods) and iterate

Yao explicitly says: "Players in the second half get to build billion or trillion dollar companies by building useful products out of intelligence."

---

## Key Verbatim Quotes

1. "RL finally generalizes. After several major detours and a culmination of milestones, we've landed on a working recipe."

2. "The second half of AI — starting now — will shift focus from solving problems to defining problems."

3. "In the first half of AI, methods were harder and more exciting than tasks."

4. "A great new method can hillclimb many different benchmarks because it's simple and general."

5. "It turned out the most important part of RL might not even be the RL algorithm or environment, but the priors."

6. "Language generalizes through reasoning in agents."

7. "The recipe has essentially standardized and industrialized benchmark hillclimbing without requiring much more new ideas."

8. "Our evaluation setups are different from real-world setups in many basic ways."

9. "When the intelligence is low, improving intelligence generally improves utility."

10. "Players in the second half get to build billion or trillion dollar companies by building useful products out of intelligence."

---

## VERSO RELEVANCE

### Finding 1: The Auto-Execution Assumption Gap — Human-in-the-Loop as First-Class Concern
**Text**: "The auto-execution assumption" — benchmarks assume tasks run without human engagement, but real-world high-value tasks require iterative human interaction. This gap explains why SWE-bench scores don't translate to deployed agent value.

**Verso mapping**: [SHARPENS §6.1 durable runtime, §4 the seam/architecture] — This is the most direct argument for why Verso's human-in-the-loop (HITL) durable layer is not a niche feature but the central production differentiator. The auto-execution assumption gap is precisely what the durable layer closes. A framework that treats HITL as an add-on is still in "first half" thinking. Verso's seam — the single flag that promotes from ephemeral to durable with HITL — is the exact mechanism for closing this gap. This is the Verso thesis stated in eval terms: the benchmark doesn't capture what makes an agent deployed vs. demoed.
**Verdict**: sharpen — use Yao's framing in §6.1 durable runtime docs. "The auto-execution assumption gap is what the durable layer closes."

### Finding 2: The i.i.d. Assumption Gap — Sequential Context as Value Driver
**Text**: "The i.i.d. assumption" — real agents gain value through sequential runs, accumulated codebase familiarity, user adaptation, and context persistence. Benchmarks measure each run independently, hiding where most of the real value is created.

**Verso mapping**: [SHARPENS §5.4 memory, §6.1 durable runtime] — This is a direct argument for multi-session memory and event-sourced state. The value of a deployed agent compound over interactions, not just within a single run. If Verso only handles single-run ephemeral agents, it can't capture this compounding value. The durable layer is what makes i.i.d. assumptions false in practice — by maintaining checkpointed state, event history, and typed memory across sessions, the agent benefits from sequential context exactly as Yao says deployed value requires.
**Verdict**: sharpen — add to §5.4 memory rationale: multi-session sequential context is where deployed agent value compounds. The i.i.d. assumption is why good benchmark scores don't translate to production value without it.

### Finding 3: Define Evals First, Then Solve Them
**Text**: "The second half" thesis: research value moves from methods to eval design. "Game-changing research requires breaking the recipe." Benchmarks that capture real-world utility require questioning the auto-execution and i.i.d. assumptions.

**Verso mapping**: [CONFIRMS §5.5 evals] — This powerfully confirms Verso's first-class evals stance. But it sharpens it: evals should not merely re-run existing benchmarks (they're already industrialized). Verso's `define_outcome(bounded)` and judge-panel approach are correct, but the killer differentiator is that Verso should help users define evals that *violate* the auto-execution and i.i.d. assumptions — multi-turn HITL evals, sequential/stateful evals, deployed-context evals. These are the second-half evals.
**Verdict**: sharpen — the judge-panel + define_outcome design is correct; add multi-turn HITL eval support and sequential/stateful eval infrastructure as second-half priority.

### Finding 4: Method Deprecation Cadence
**Text**: "Novel methods achieve 5% improvement while next model generation achieves 30% without specific targeting." Benchmarks saturate within ~3 years. Classical CALM project (2019) required millions of RL steps per single game with no transfer capability.

**Verso mapping**: [CONFIRMS §1 the bet] — This is the empirical complement to Gwern's Bitter Lesson: the numbers. A 5% method improvement vs. 30% generational model improvement means any framework component that exists to compensate for current model limitations has a ~1-model-generation shelf life (~1-2 years). This is the quantitative version of Verso's "tactical workarounds churn 1-2yr; durable architecture persists 3+ model generations" already in the harvest. The 5%/30% ratio is the number.
**Verdict**: confirm — already in harvest as the bitter lesson; the 5%/30% numbers sharpen the point.

### Finding 5: The Builder's Paradox / Eval Design as Competitive Moat
**Text**: Yao built ReAct AND SWE-bench, and argues the benchmark is now more valuable than the method. "Players in the second half get to build billion or trillion dollar companies by building useful products out of intelligence." He's explicitly saying the category of "build evals for deployed real-world utility" is the trillion-dollar move.

**Verso mapping**: [NEW-IDEA §5.5 evals, §12 positioning] — Verso should position its eval infrastructure not just as a quality-assurance tool but as a *competitive moat builder*. The teams using Verso's evals to measure real-world utility (HITL, sequential, stateful) will have better outcome feedback loops than competitors using benchmark scores. The eval is the product, not just the test. This is a GTM angle: "Build your second-half evals before your competitors do." Verso is the framework that makes second-half eval design tractable.
**Verdict**: adopt-now — significant GTM framing: Verso evals = second-half competitive moat. Not "quality assurance" but "define what success means before competitors do."

### Finding 6: Language Pre-Training Priors — Why Tool Design Matters
**Text**: "It turned out the most important part of RL might not even be the RL algorithm or environment, but the priors." Language pre-training is the source of generalization. This is what made ReAct work when hand-designed RL environments failed.

**Verso mapping**: [SHARPENS §5.3 tools] — This validates the native Python @tool design at a deep level. Good tool design means writing tool descriptions in natural language that aligns with the model's pre-trained priors. The model generalizes through language — which means tool docstrings, parameter names, and return value descriptions are load-bearing. This is not just convenience; it's exploiting the prior structure that makes RL (and agentic tool use) generalize. MCP tools that arrive as JSON schema without natural language descriptions fight the prior structure; native Python @tool with docstrings aligns with it.
**Verdict**: sharpen — add to §5.3 tools: tool descriptions exploit language priors; docstrings are not documentation, they are the prior.

---

## Summary Verdict
The Second Half is the most directly actionable source for Verso's eval design and HITL durable runtime. Yao's framework (auto-execution assumption gap, i.i.d. assumption gap) gives precise language for WHY the durable layer matters and WHY evals beyond single-run benchmarks are the real product. The GTM implication is significant: Verso is a second-half framework in a world of first-half tools. Position accordingly.
