# RAW EXTRACTION — BAD_GUIDE.md §"Modern CTO" + §"Frontier AI Research Taste"

Source file: `/Users/seventyleven/Desktop/guidesfm/BAD_GUIDE.md`
Sections read VERBATIM:
- §"🛠️ The Modern CTO (director of machines)" — lines 199–358
- §"🔬 Frontier AI Research Taste" — lines 360–648

All quotes below are byte-for-byte from the source unless marked `[INFERRED]`. "Skale" / "Lancelot" / "Slava" are the guide-author's own running examples (the guide is written for a specific founder); they are NOT Verso terms.

Tagging key for Verso relation appears in the structured object, not here. This note is the "nothing is lost" artifact.

---

## PART A — THE MODERN CTO ("director of machines")

### Framing (lines 199–203) — KNOWN

> "*Stay the most technical person in the room without typing most of the code.*"

> "**The shift.** Your leverage moved from writing the code to deciding what gets built and verifying what the machines produce. The 1% CTO treats the agent harness as the product surface and their own taste as the quality gate that no model can hold. The 90% either keep coding line-by-line (and become a bottleneck) or hand the wheel to AI and lose the thread. The job now is directing a fleet of fast, fallible workers and owning the standard they ship against."

Key primitive phrases: **"agent harness as the product surface"**, **"taste as the quality gate that no model can hold"**, **"directing a fleet of fast, fallible workers"**.

### ▸ Software is three layers now — your leverage is the top one (line 207–208) — KNOWN

> "Karpathy's frame: 1.0 is hand-written code, 2.0 is trained weights, 3.0 is natural-language prompts. Each layer makes intent easier to express and precision harder to hold. Your edge as CTO is no longer the architecture diagram. It is the generate/verify loop and the product taste that decides which generation is correct."

Attribution: **Andrej Karpathy** (Software 1.0/2.0/3.0). Primitive: **"the generate/verify loop"**.

### ▸ The architecture beats the model (line 210–211) — KNOWN — HARNESS-AS-MOAT + NUMBERS

> "Same model, different harness, 5-point swing on SWE-bench Pro (Opus 4.5 ran 50.2% to 55.4% purely on context management and tool orchestration). v0 took Sonnet from 64.7% to 93.9% error-free with four engineering layers (RAG injection, stream-time fixing, deterministic AST/icon validation, a fine-tuned AutoFixer), not a single model upgrade. When Skale's agent underperforms, the fix is almost never a better model. It is your context window, your tools, your error recovery."

Hard numbers:
- **Opus 4.5: 50.2% → 55.4% on SWE-bench Pro** — same model, different harness, "purely on context management and tool orchestration" (5-point swing).
- **v0 (Vercel): Sonnet 64.7% → 93.9% error-free** — via FOUR engineering layers: (1) RAG injection, (2) stream-time fixing, (3) deterministic AST/icon validation, (4) a fine-tuned AutoFixer. NOT a model upgrade.
- Note: the task brief says "v0 ~65->94%"; source says 64.7% → 93.9%.
- The fix when an agent underperforms: **"your context window, your tools, your error recovery"** — never "a better model."

### ▸ KV-cache is your #1 cost lever (line 213–214) — KNOWN — NUMBERS

> "Production agents run ~100:1 input:output. That means cache optimization matters 100x more than output optimization. Keep a static system-prompt prefix, append-only context, deterministic JSON serialization, and route sessions to consistent workers. These are architecture decisions with 10x cost impact that most teams never make because they are staring at the model price-per-token instead."

Numbers/primitives: **~100:1 input:output ratio**; cache opt matters **100x** more than output opt; **10x cost impact**. Four concrete levers: (1) static system-prompt prefix, (2) append-only context, (3) deterministic JSON serialization, (4) route sessions to consistent workers.

### ▸ Decouple the decider from the executor (line 216–217) — KNOWN — NUMBERS

> "Cursor's apply model: a big smart model writes a sketch with placeholders, a small fast fine-tuned model performs the actual edit at ~1,000 tok/s (13x faster) because the existing code is its draft tokens. Generalize it. Wherever you have a slow expensive judgment and a fast mechanical execution, split them. For Skale's LangGraph fleet, the orchestrator decides, a cheap model executes."

Numbers: **~1,000 tok/s, 13x faster** (Cursor apply model). Pattern: **decider/executor split** = "slow expensive judgment" + "fast mechanical execution."

### ▸ Build for the capability 18 months out, not today (line 219–220) — KNOWN — NUMBERS + ATTRIBUTION

> "METR's task horizon: AI autonomously completes ~1-2 hour human tasks at >50%, doubling roughly every 7 months. So the model that is \"not quite working\" on your hardest workflow today is the one to architect around now, because the infra, evals, and domain context you need cannot be built overnight. If you wait until it works, you waited for a competitor."

Attribution: **METR** (paper line 250: Kwa, West, Becker et al., *Measuring AI Ability to Complete Long Tasks*, arXiv 2503.14499). Numbers: AI completes **~1–2 hour human tasks at >50%**, **doubling every ~7 months**. Bet: architect around the model that's "not quite working" today because **"the infra, evals, and domain context you need cannot be built overnight."**

### ▸ Taste is the moat AI cannot copy — it is objective, and it is the job (line 222–223) — KNOWN

> "Tuomas Artman (Linear CTO): AI fixes the bug but cannot feel that a 200ms delay is wrong. Graham's point that designers measurably improve proves taste has objective properties, not preferences. Karpathy's product taste, Artman's quality bar, Linear's sub-50ms interactions: that perceptual apparatus is what you set and agents enforce against. The 1% CTO is a heretic who looks at the AI's grid-perfect, tonally-flat output and sees precisely which property is violated."

Attribution: **Tuomas Artman (Linear CTO)**, **Paul Graham**, **Karpathy**. Numbers: 200ms delay "feels wrong"; Linear sub-50ms interactions. Key claim: **"taste has objective properties, not preferences"** — "what you set and agents enforce against."

### ▸ Founder mode means staying in the details, on purpose (line 225–226) — KNOWN

> "Graham's case: \"hire good people and delegate\" destroys technical companies. Charity Majors' pendulum says the best leaders oscillate between IC and management deliberately. Staying close to the code is a strategy, not a failure to scale. As director of machines, your skip-levels are reading agent traces and your direct reports are the harnesses."

Attribution: **Paul Graham** (Founder Mode), **Charity Majors** (Engineer/Manager Pendulum). Primitive metaphor: **"your skip-levels are reading agent traces and your direct reports are the harnesses."**

### "Go deeper" reading list — KNOWN — high-value primary sources cited

- **Karpathy, "Software Is Changing (Again)"** (talk, MUST): OS analogy — **"LLM = kernel, context window = RAM, tools = syscalls"** — your value is the app layer.
- **Karpathy, "Software 2.0"** (essay, MUST): "weights ARE the program."
- **Anthropic (Applied AI), "Effective harnesses for long-running agents"** (MUST): "The harness is the layer that compounds across model generations while the model stays swappable." Concrete patterns: **a feature-list-as-executable-spec the agent may toggle but not edit, git-as-state-machine for recovery, a progress file as memory across context windows, and a dual initializer/worker split.**
- **Armin Ronacher, "Agent Design Is Still Hard"** (MUST, creator of Flask): "skip the high-level SDKs because model differences force your own abstraction, prefer explicit cache control, **reinforce the objective on every tool return rather than once up front**, and isolate failures in throwaway sub-agents that report only outcomes."
- **Mitchell Hashimoto (HashiCorp founder), "Agentic Engineering in Action"** (STRONG): "build tools, validators and lint rules the agent self-invokes so a class of mistake never recurs, **supply the shape of the solution rather than the keystrokes**, and run the same task across models on cloned repos to pick the winner empirically."
- **Adrian Cockcroft, "Directing a Swarm of Agents"** (STRONG, ex-Netflix): "stop hiring application developers, build the platform that operates development... **The director does not read the code, he runs the team and nags it to 100% green.**"
- **Sean Goedecke (GitHub), "If you are good at code review..."** (STRONG, COUNTERWEIGHT): "line-level nitpicking is near-useless with agents, and the durable skill is structural judgment, catching when the agent is committing to an architectural dead end."
- **Geoffrey Huntley, "Ralph Wiggum as a software engineer"** (OPTIONAL): "a single deterministic bash loop running one focused task on a fresh context each pass makes failure modes observable and tunable, and can beat elaborate multi-agent orchestration running on a stale context."
- **OpenRouter "Fusion: Panel-of-Models Compound System"** (STRONG): fan one prompt to a panel in parallel, judge extracts consensus/contradictions/blind spots, synthesizer writes the grounded answer. NUMBER: **a budget panel (Gemini 3 Flash + Kimi K2.6 + DeepSeek V4 Pro) beats solo GPT-5.5 and Opus 4.8 and lands within 1% of Fable 5 at ~half the price**, with **~¾ of the lift from synthesis, only ~¼ from diversity.** "The harness wins, not the weights." Plus eval-contamination warning: they surfaced the benchmark's grading rubric via web search, excluded those domains, re-ran.
- **Ryan Lopopolo (OpenAI Frontier), "Extreme Harness Engineering: 1M LOC, 0% human-written code"** (MUST): "shipping a 1M+ LOC product with zero human-written and zero pre-merge-reviewed code: humans steer, agents execute and auto-merge their own PRs, review moves to post-merge. ... **a hard one-minute build loop they rebuilt their infra to protect**, code treated as disposable, and **a failure reflex of asking what capability the agent is missing and how to make it enforceable, instead of telling people to try harder.**"
- **Ryan Lopopolo, "Harness engineering: leveraging Codex"** (STRONG): "how Codex moves the unit of work from writing code to engineering the conditions an agent succeeds in."
- **OpenAI Codex, "Running Codex Safely"** (MUST): "the split between sandboxing and approval prompts, an OS sandbox (**bwrap + seccomp, with a Landlock fallback**), network access off by default, and an automatic review subagent."
- **Thibault Sottiaux (Head of Codex), "Scaffolding Is Coping, Not Scaling"** (STRONG, CONTRARIAN counterweight to harness-as-moat): "**delete the harness so a smarter model's capability overhang is not capped by your plumbing, solve context compaction in training rather than in the harness**, and make internal review mandatory."
- **Elon Musk, "The Algorithm" (Starbase Tour)** (MUST): "**make the requirements less dumb, delete the part or process, simplify, accelerate, then automate, strictly in that order**, because automating or accelerating a step you should have deleted is the classic mistake."
- **Dan McKinley, "Choose Boring Technology"** (MUST): "**innovation-tokens model: you get about three novel-technology bets** before operational complexity sinks you."
- **Thariq Shihipar (Claude Code, Anthropic), "A Harness for Every Task"** (MUST): names failure modes "**agentic laziness, self-preferential bias, goal drift across compaction**" and fixes "classify-and-act, fan-out-and-synthesize, isolated worktrees", plus "mining your last 50 sessions for recurring corrections to codify as CLAUDE.md rules."
- **Addy Osmani, "Loop Engineering"** (OPTIONAL): five building blocks (scheduled automations, git worktrees, skills, MCP connectors, maker-checker subagents) + on-disk memory file. Judgment: "**verification stays on you, comprehension debt grows faster as the loop gets smoother, and two people running the identical loop get opposite results.**"

---

## PART B — FRONTIER AI RESEARCH TASTE

### Framing (lines 360–364) — KNOWN — THE BITTER-LESSON BET + ILYA

> "*How to pick the problem that matters before it's obvious, so you ship a primitive instead of another wrapper.*"

> "**The shift.** The 90% chase benchmarks and publishable deltas. The 1% pick problems by taste, then pick the side of the curve that compute is about to reward. Ilya Sutskever's framing is the whole game now: when compute is commoditized, the bottleneck stops being scale and becomes the correct paradigm, and the only filter for \"correct\" is taste. ... The gap between you and a researcher who ships GPT-4 is not IQ or compute. It's a trained sense for which problems are worth a year of your life."

Attribution: **Ilya Sutskever** — "when compute is commoditized, the bottleneck stops being scale and becomes the correct paradigm, and the only filter for 'correct' is taste."

### ▸ Work on important problems (line 368–369) — KNOWN — HAMMING

> "Hamming's hard question: \"What are the important problems in your field, and why aren't you working on them?\" Most strong builders never ask it. They optimize the thing in front of them. **Keep a written list of the 10 problems that would change your field if solved, and check weekly** whether what you're doing is on it."

Attribution: **Richard Hamming** (*You and Your Research*, ~12k words, MUST, line 396). Concrete drill: written list of 10 field-changing problems, checked weekly.

### ▸ Pick by taste, not by what's publishable (line 371–372) — KNOWN — SCHULMAN

> "John Schulman splits research into concept-driven (a new idea) vs execution-driven (make a known idea work). Novelty-seeking, chasing the un-tried because it's un-tried, is the classic trap. It optimizes for \"nobody did this\" when the test should be \"this matters.\" Choose by genuine curiosity plus aptitude, the way Paul Graham describes great work, then go to the frontier and follow the anomalies."

Attribution: **John Schulman** (PPO/RLHF creator; *An Opinionated Guide to ML Research*, MUST, line 398). Split: **concept-driven vs execution-driven**. Trap: novelty-seeking. Test: "this matters" not "nobody did this."

### ▸ Bet on the right side of the Bitter Lesson (line 374–375) — KNOWN — SUTTON — CENTRAL

> "Sutton's claim is the most predictive thing in AI: **every method built on clever hand-crafted inductive bias eventually loses to scale plus search.** If your edge depends on a hand-tuned heuristic beating compute, you will lose on a 12-month horizon. Lancelot wins because raw speed compounds with scale. Ask the same of any AI bet you make."

Attribution: **Richard Sutton** (*The Bitter Lesson*, ~1.5k words, MUST, line 404): "scale plus search beats hand-crafted structure, always." Horizon: 12-month. ("Lancelot" = guide-author's own project example.)

### ▸ Verifiable reward is where the curve goes vertical (line 377–378) — KNOWN — RLVR + BUILD-THE-VERIFIER-FIRST + NUMBERS

> "Any domain where a solution can be auto-checked (code, math) can be driven hard with RL. **Qwen 3's result: 4,000 high-quality verifiable examples beat 4 million low-quality RLHF ones.** Quality and verifiability dominate quantity. This is your Skale advantage: a sent reply that books a meeting is a verifiable signal. **Build the verifier first; the training loop follows.**"

NUMBER: **Qwen 3 — 4,000 verifiable examples beat 4,000,000 (4M) RLHF examples** (1000x fewer). Primitive: **"Build the verifier first; the training loop follows."** Definition of a verifiable signal: a solution that can be auto-checked (code, math); operationally "a sent reply that books a meeting."

### ▸ Fine-tuning is usually a capital trap (line 380–381) — KNOWN — MOAT-IS-HARNESS-NOT-WEIGHTS + NUMBERS

> "Spend millions fine-tuning a model and the next base release erases your edge. Model-agnostic harnesses age better — **Poetic AI's meta-system hit 54% on ARC-AGI v2 at $32/problem versus Gemini 3 Deep Think's 45% at $70, for under $100K total. \"Vaccinated against the bitter lesson.\"** Keep Skale's intelligence in the harness, not in weights you'll rent and lose."

NUMBERS: **Poetic AI meta-system: 54% on ARC-AGI v2 at $32/problem, total under $100K** vs **Gemini 3 Deep Think: 45% at $70/problem.** Phrase: **"Vaccinated against the bitter lesson."** Thesis: **"Keep [the] intelligence in the harness, not in weights you'll rent and lose."**

### ▸ Intelligence is efficiency of skill acquisition (line 383–384) — KNOWN — CHOLLET + NUMBERS

> "Chollet's definition: **a smarter system learns a new skill from fewer examples.** LLMs interpolate inside the training manifold beautifully and extrapolate badly — **GPT-4.5 scored 0% on ARC-AGI v2.** When you read a SOTA number, ask whether the gain is interpolation on a saturated distribution or genuine generalization. Only the second kind is a primitive."

Attribution: **François Chollet**. NUMBER: **GPT-4.5 = 0% on ARC-AGI v2.** Definition: intelligence = efficiency of skill acquisition (learn from fewer examples). Filter: interpolation-on-saturated-distribution vs genuine generalization — "Only the second kind is a primitive."

### ▸ Stay close to the run (line 386–387) — KNOWN — SHOLTO DOUGLAS + TRENTON BRICKEN

> "Sholto Douglas and Trenton Bricken went **zero-to-frontier in ~1 year** by picking problems adjacent to what's working but poorly understood (superposition, long context, RL reward) and **staying close to actual training runs. Taste is built by watching where models behave unexpectedly, not by reading abstracts. Treat every weird Skale agent failure as a research lead, not a bug ticket.**"

Attribution: **Sholto Douglas & Trenton Bricken** (Anthropic). Mechanic: zero-to-frontier in ~1 year by picking problems "adjacent to what's working but poorly understood" + staying close to actual training runs. Primitive: **"Treat every weird agent failure as a research lead, not a bug ticket."**

### ▸ Steelman the strongest disagreement before you bet (line 389–390) — KNOWN — LeCun / Sutton / Ilya / Gwern

> "LeCun (Meta FAIR) argues that scaling autoregressive LLMs is a dead end and the future is world models. Sutton, who wrote the Bitter Lesson sitting in your principles above, now says LLMs can't learn from experience at all. Ilya and Gwern argue the opposite. The taste skill is holding that contradiction between people who are each usually right, and forming your own bet instead of joining a tribe. **When two sources you respect collide, that spot is the frontier. Sit in it.**"

Live disagreement map: LeCun (world models, scaling LLMs is dead end) vs Sutton (LLMs can't learn from experience) vs Ilya & Gwern (opposite). Heuristic: "When two sources you respect collide, that spot is the frontier. Sit in it."

### ▸ De-risk the load-bearing assumption first (line 392–393) — KNOWN — STEINHARDT

> "Steinhardt models a research project as a sequence of bets where each experiment buys information. **Order the work by information gained per unit of time, and kill the riskiest assumption before you build anything on top of it.** For Skale: prove your verifiable signal actually predicts the outcome before you build the training loop around it."

Attribution: **Jacob Steinhardt** (*Research as a Stochastic Decision Process*, STRONG, line 427). Algorithm: order by information gained per unit time; kill the load-bearing/riskiest assumption first.

### "Go deeper" reading list — KNOWN — high-value attributed primitives

- **Hyung Won Chung (OpenAI), "Don't Teach. Incentivize."** (MUST, line 467): "**the o1 co-lead's inversion of the teaching frame: design the incentive (verifiable reward), let scale surface the capability.** The mental model behind o1 and R1." → INCENTIVIZE-RATHER-THAN-TEACH.
- **Jason Wei (OpenAI), "Practicing AI Research"** (MUST, line 469): "The CoT author decomposes research into **four learnable skills — idea selection, experiment design, writing, and the underrated one: distributing your results.**" → BUILDERS-AND-THINKERS / impact-maximization (distribution is a skill).
- **Jason Wei, "Asymmetry of Verification and Verifier's Law"** (STRONG, line 578): "**some tasks are far cheaper to verify than to solve, and whatever is solvable and easy to verify gets solved. Build the verifier first**, and pick problems whose reward you can auto-check. The canonical short statement of the RLVR problem-selection filter."
- **Jason Wei, "AI Research is a Max-Performance Domain"** (STRONG, line 580): "**Research rewards your best handful of works, not your average**, so being world-class at one thing beats being uniformly competent and a failed bet costs almost nothing."
- **Sebastian Raschka, "Understanding Reasoning LLMs"** (MUST, line 445): "the four ways to build reasoning models — **inference-time scaling, SFT, RLVR/GRPO, search** — and why DeepSeek-R1-Zero's verifiable-reward move worked."
- **Hamel Husain, "Your AI Product Needs Evals"** (MUST, line 455): "From 30+ production builds: **the #1 cause of failed AI products is no eval system.** The operator's version of 'build the verifier first.'"
- **Matei Zaharia, Jonathan Frankle, Naveen Rao et al. (Databricks), "The Shift from Models to Compound AI Systems"** (MUST, line 485): "**SOTA now comes from compound systems (model + retrieval + tools + verifiers), not monolithic models.**" → MOAT-IS-THE-SYSTEM.
- **Noam Brown, "Scaling Test-Time Compute..."** (STRONG, line 412–413): "recognizing when an existing method (here, the generator-verifier gap) can be generalized into a brand-new scaling axis. This is the move that made o1."
- **Shunyu Yao (builder of ReAct, SWE-bench, tau-bench), "The Second Half"** (STRONG, line 546): "the working RL recipe (**strong priors plus reasoning-as-action**) now beats incremental method work, so the frontier value moves from solving problems to **defining and evaluating them.** ... **Build the eval, not the next method.**"
- **Karina Nguyen (OpenAI), "RL as a Co-Design of Product and Research"** (STRONG, line 602): "**asymmetric verification as the filter for which RL problems are tractable**, and designing the product interface and the RL signal together."
- **John Hughes & Ethan Perez (Anthropic Alignment Science), "Tips and Code for Empirical Research Workflows"** (STRONG, line 635–636): the actual harness — "a concurrency-managed LLM inference API, fine-tuning with experiment tracking, prompt templating, and reusable project scaffolds (`github.com/safety-research/safety-tooling`). **\"The moat is the system, not the weights\" applied to your own research loop — the reusable harness is the real takeaway.**" → EXPLICIT "moat is the system, not the weights" QUOTE.
- **Neel Nanda (DeepMind, ex-Anthropic), "My Research Process: Understanding and Cultivating Research Taste"** (MUST, line 639–640): "**Taste — the highest-weighted trait in this whole section — is learned, not innate, and the mechanism is concrete: reflect on each research decision against how it actually turned out, and borrow the priors of people with better taste.**"
- **Ethan Perez (Anthropic), "Tips for Empirical Alignment Research"** (MUST, line 633–634): "run the *minimal* experiment that reduces your uncertainty at the fastest possible rate, keep the feedback loop on LLMs tight."
- **Ethan Perez, "Easy Paper Writing Tips"** (STRONG, line 626–627): "**Concrete craft for making a paper readable, which is impact-maximization, since distribution is half of whether research lands.**"
- **Vivek (@itsreallyvivek), "Some Notes on Getting Into Frontier AI Labs"** (STRONG, line 616–617): "**frontier labs hire for judgment, not raw intelligence: research is the compression of uncertainty and engineering is the compression of complexity, and both are the same underlying skill of building a useful abstraction when the map is incomplete.** As knowledge, information and code all get cheap, the scarce resource is deciding what deserves attention."
- **Sholto Douglas, "How to Break Into a Frontier Lab: Write the Artifact"** (MUST, line 624–625): "**one world-class public artifact on a genuine open problem beats any credential.**"
- **Nicholas Carlini, "How to win a best paper award"** (STRONG, line 541–542): "**the single most important skill is taste in which problems are worth solving**, then how he generates and filters ideas, executes, writes, and ships for impact over citation count."
- **Karpathy "Let's reproduce GPT-2", "nanochat" ($100 ChatGPT clone, ~8k LOC), "A Recipe for Training Neural Networks"** (lines 527–531, 431): Karpathy re-implements from scratch — "nets fail silently, so go simple to complex, form one hypothesis per step, and never trust a result you can't explain." → BUILDERS-AND-THINKERS (Karpathy re-implements).

---

## CROSS-CUTTING THESES THAT MAP DIRECTLY ONTO VERSO

1. **Harness-as-moat / "architecture beats the model" / "moat is the system, not the weights"** — repeated in BOTH sections (CTO §210–211, §380–381; Research §485, §636). This IS Verso's core thesis ("the boring core done right," harness over weights). VERSO-ALREADY-HAS at the thesis level.
2. **Build-the-verifier-first / RLVR / "captured failure IS a regression test"** — Research §377–378, Jason Wei §578, Hamel §455, Shunyu Yao §546 ("Build the eval, not the next method"). Verso's eval wedge ("prod==eval") already embodies this.
3. **Reinforce-the-objective-on-every-tool-return** (Ronacher §283) — Verso ships `reinforce_objective` in Hooks. VERSO-ALREADY-HAS.
4. **Stay-close-to-the-run / read agent traces / "every weird failure → research lead"** — Verso has VersoSpan+OTel, from_trace evals, inspect() byte-for-byte. VERSO-ALREADY-HAS.
5. **Decider/executor split + per-call model swap** — Verso has per-call `model=` swap + `agent.override()`. VERSO-ALREADY-HAS the mechanism.
6. **KV-cache static prefix + append-only context** — Verso has KV-cache-stable system prefix + append-only/prune-masks-don't-drop. VERSO-ALREADY-HAS.
7. **Git-as-state-machine / progress file as cross-context memory / "feature-list-as-executable-spec the agent may toggle but not edit"** (Anthropic harnesses essay §281) — Verso has durable checkpoint/resume + "# SCAFFOLD() ratchet" + load_skills + verify-before-done gate. The "feature-list-as-executable-spec, toggle-but-not-edit" framing is adjacent to the SCAFFOLD ratchet; potential additive nuance, not a gap.
8. **"Delete the harness so a smarter model isn't capped" (Sottiaux §322–323) + Musk's "delete the part" + "innovation-tokens, ~3 bets" (McKinley §335)** — these are anti-overkill / leanness reinforcement, directly supporting Verso's "cut anything that buys only ~1%" law. NEUTRAL-CONTEXT / thesis-validation, not something to build.
9. **"Build for the capability 18 months out"** (METR §219–220) — a strategic/product stance, not a primitive. NEUTRAL-CONTEXT (informs roadmap, not a feature to add; would be NON-GOAL territory if mis-read as a router/planner).
10. **Incentivize-rather-than-teach** (Hyung Won Chung §467) — a model-training philosophy. Verso is explicitly NOT the model/kernel/training layer. AVOID as a Verso feature (out of scope / NON-GOAL: not the model).

---

## EXPLICIT NON-FINDINGS (so nothing is mistaken for a gap)

- These sections are a **founder field-manual / reading list**, not an API spec. Almost every "primitive" is a *judgment* or an external-source pointer, not code Verso could import.
- The numbers (Opus 50.2→55.4, v0 64.7→93.9, Qwen 4k>4M, Poetic 54%@$32 vs Gemini 45%@$70, GPT-4.5 0% on ARC-AGI v2, ~100:1 ratio, ~1000 tok/s 13x, ~7-month doubling) are **validation evidence for Verso's harness-over-weights thesis**, not features to copy.
- Nothing here argues for a graph-DSL, a learned router, an orchestrator-primitive, MCP-first, or Rust — i.e. nothing pushes Verso toward its NON-GOALS. If anything, Sottiaux/Musk/McKinley push HARDER toward Verso's leanness.
