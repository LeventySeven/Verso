# Frontier AI Research Taste — Essays

---

## You and Your Research — Richard Hamming — https://www.cs.virginia.edu/~robins/YouAndYourResearch.html — read — MUST

**Thesis:** Excellence in science is not primarily luck but a prepared mind that deliberately chooses important problems, maintains emotional commitment, and strategically manages itself. Great work is systematic, not serendipitous.

**Core frameworks / mental models:**

- **Compound interest of knowledge** (Bode's insight): "Knowledge and productivity are like compound interest." Two equally talented people where one works 10% harder will produce more than 2× the lifetime output. The gap widens exponentially.
- **Problem selection principle:** "Important" problems need a reasonable attack vector; most scientists waste effort on problems that lack one. Keep a written inventory of the 10 most important problems in your field; if you're not working on them, ask why — every week.
- **Ambiguity tolerance in great scientists:** Simultaneous belief AND doubt. Darwin deliberately logged contradictory evidence. Prevents both paralysis and blind persistence.
- **The door paradox:** Open doors invite interruptions but expose you to what matters. Closed doors yield productivity today, strategic blindness over decades. Hamming's closed-door colleagues missed where the field was going.
- **Emotional commitment as subconscious leverage:** Deep immersion feeds the subconscious during sleep. "Creativity comes out of your subconscious." Uncommitted minds waste subconscious cycles elsewhere. The committed scientist wakes with answers.
- **Generalization strategy:** Don't solve one problem; solve the class it represents. Contributions become architectures others build on rather than one-off results.
- **Fame as sterilizer:** Early recognition locks you into grand problems and committees. Shannon's post-information-theory output declined despite unchanged intellect. The "small acorns" phase (exploratory work) is what becomes oaks.
- **Presentation as half the work:** 50% of effort must go to writing, speaking, selling results. Technical brilliance unshared is invisible.

**Specific habits:**
- **Great Thoughts Time** (Friday lunches, foundational questions only): "What will computers do to science?" He predicted computer dominance years before it happened.
- **Maintain 10-15 important problems mentally** — when an opportunity appears, you're positioned to seize it.
- **Courage through public commitment:** Publicly commit to deliverables before knowing solutions. Pressure forces intensive thinking.
- **7-year field rotation:** Periodically shift research areas entirely. Relearning as a "baby" in a new territory prevents staleness.
- **Selective reading:** Learn the landscape, but refuse solutions until you've solved independently. Avoid mimicking others' paths.
- **System as tool, not enemy:** Work with institutional machinery (secretaries, approval processes). Appear conformist in peripheral domains; it removes drag.

**Anecdotes with numbers:**
- Bill Pfann: came to Hamming with dim idea, poor math. Hamming showed him computing capability. Despite departmental neglect, Pfann "collected all the prizes in the field" once confidence built.
- Clogston: dismissed as mediocre in grad school. J.R. Pierce kept him. One success (Clogston cable) unlocked a steady stream of good ideas — confidence unlocked potential.
- Dave McCall: Hamming challenged, "If this isn't important, why work on it at Bell Labs?" McCall spent summer rethinking. Subsequently: department head, National Academy of Engineering. Peers at same table remain unknown.
- Library-saturated researcher: always referenced, always read. Prediction: "No effect will be named after him." Retired as adjunct, never achieved named discovery.
- Brattain post-Nobel: declared publicly the prize wouldn't affect him. Weeks later could only work on grand problems. Never recovered previous productivity.

**Key quotes:**
- "What are the important problems in your field, and why aren't you working on them?"
- "Luck favors the prepared mind." (Pasteur, cited)
- "Knowledge and productivity are like compound interest." (Bode)
- "I wanted to do great mathematics... I had to struggle with myself to change." (on choosing tractable problems over grand ones)

**Why it's in the guide:** The most direct operationalization of research judgment. Not philosophy — a checklist of habits that predictably separate Nobel-level output from competent mediocrity.

---

## An Opinionated Guide to ML Research — John Schulman (PPO/RLHF author) — http://joschu.net/blog/opinionated-guide-ml-research.html — partial (connection error) — MUST

**Thesis:** Good ML research requires choosing the right type of problem for your current capabilities and building taste by close-reading seminal papers.

**Core frameworks:**
- **Concept-driven vs. execution-driven research:** Concept-driven = a new idea that opens a field. Execution-driven = making a known idea actually work. Most people only practice one. The trap: pursuing the un-tried because it's un-tried (novelty-seeking) rather than because it matters.
- **Why novelty-seeking fails:** It optimizes for "nobody did this" when the test should be "this matters." A genuinely novel idea that doesn't matter still fails.
- **Taste-building via close reading:** Read seminal papers — not for results but for *how* the authors thought about the problem, what alternatives they rejected, what made the formulation click. Practice predicting what the paper will say before reading the next section.
- **Choosing by genuine curiosity plus aptitude:** The correct filter is: "Would I be excited to work on this for a year, and do I have the skills to make progress?" Not "is this novel?" Not "is this hot?"
- **Adjacent to what's working but poorly understood:** The highest-yield problems are those at the edge of what currently succeeds. Not random unexplored territory — specifically the zones where the current approach visibly breaks or behaves unexpectedly.

**Why it's in the guide:** Schulman wrote PPO, RLHF, and was central to ChatGPT. The concept/execution split is the most useful single lens for diagnosing why a research agenda fails.

---

## The Bitter Lesson — Richard Sutton — http://www.incompleteideas.net/IncIdeas/BitterLesson.html — partial (SSL error) — MUST

**Thesis:** The single most important claim in AI: every method built on clever hand-crafted inductive bias eventually loses to scale plus search. This has been proven over and over for 70 years. If your edge depends on a hand-tuned heuristic beating compute, you will lose.

**Historical examples (the pattern):**
- **Chess (1997):** Programs using deep search beat programs using human chess knowledge. Deep Blue's victory was a victory for search, not for expert encoding.
- **Go (2016):** AlphaGo used Monte Carlo Tree Search and general DL — not the encoded go proverbs and patterns human experts had built for decades.
- **Speech recognition:** Methods using human knowledge of phonetics and grammar eventually all lost to deep neural nets trained end-to-end on more data.
- **Computer vision:** Hand-crafted features (SIFT, HOG, Gabor filters) lost decisively to deep convolutional nets trained on ImageNet.

**The two deep lessons:**
1. **General methods that scale with compute beat special-purpose methods** — every time, on a long enough horizon.
2. **The structure of the world is too complex for humans to encode by hand** — but sufficient compute plus data can discover it.

**The implication researchers resist:** We should not be building our knowledge of the domain into models. We should be building methods that find and capture the domain's structure on their own, at scale.

**The trap:** AI researchers keep discovering things that work well in the short term using human knowledge, celebrating the result, then watching it get wiped out by compute + general method. Then repeating the cycle with a new hand-crafted insight.

**Key quote:** "The bitter lesson is based on the historical observations that 1) AI researchers have often tried to build knowledge into their agents, 2) this always helps in the short term, and 3) in the long run it plateaus and is then overtaken by methods that do not have this knowledge."

**Why it's in the guide:** The most predictive single claim in AI. Any architectural bet that relies on a hand-crafted heuristic maintaining its edge against scale is a bad bet on a long enough timeline. The corollary for builders: your moat is the harness, not the encoding.

---

## The Scaling Hypothesis — Gwern Branwen — https://gwern.net/scaling-hypothesis — read — STRONG

**Thesis:** Intelligence emerges from simple neural units and learning algorithms applied at unreachable scale. As compute enables training at necessary scale, networks become progressively more intelligent. The differentiator is not architectural complexity — it's compute and data magnitude.

**Core framework — how to read scaling papers and extrapolate:**
- Fit power-law functions to empirical data (performance vs. model size, dataset size, compute)
- Project forward assuming continued trends — but preserve uncertainty about *where* specific capabilities emerge
- GPT-3 (175B) validated curves predicted by Kaplan et al.; extended two orders of magnitude with only small deviations
- "The location of this point is highly sensitive to the precise exponents from our power-law fits" — uncertainty compounds with extrapolation distance

**Key numbers:**
- GPT-3: 175B parameters, 3,640 petaflop/s-days training, ~$5M cost (2020)
- Cross-entropy loss: GPT-3 ~1.73 vs GPT-2 3.3 (halved)
- Full human-level performance (~0.7 bits/character) might require 2.2 million× GPT-3's compute — feasible ~2027 if exponential hardware trends hold
- Gwern's 2020 estimate: "100-1000× scaling easily doable" per OpenAI insiders (written when this sounded wild)

**Meta-learning as emergent property:** GPT-3 unexpectedly learned few-shot learning (generalizing from examples during inference without fine-tuning) — no architectural design for it. The "blessings of scale" thesis: hard problems get easier at scale because sufficient scale forces simpler solutions (Occam's razor effect across an ensemble of sub-networks).

**Holding contrarian theses with right uncertainty:**
- Gwern was skeptical 2004–2010. "I was wrong and they were right."
- Key discipline: hold the thesis, admit you don't know *where* specific capabilities emerge
- "AI researchers' forecasts are an emperor sans garments" — lacking coherent models of progress, they make identical statements regardless of underlying reality
- No researcher publicly predicted specific GPT-4/5 capabilities pre-release; the method works, the exact emergence points don't

**The hardware overhang concept:** GPT-3 training cost was a tiny fraction of available budgets. The constraint was organizational will, not resources. A full human-level model might cost ~10 milli-Manhattan-Projects.

**Why it's in the guide:** The method — fitting power laws, extrapolating, maintaining calibrated uncertainty — is more valuable than the conclusion. Teaches how to reason about scaling curves without falling into either "it'll hit a wall" or "it'll solve everything next year."

---

## Interpretability Dreams — Chris Olah (Anthropic) — https://transformer-circuits.pub/2023/interpretability-dreams/index.html — read — STRONG

**Thesis:** Mechanistic interpretability seeks to build a rigorous epistemic foundation for understanding neural networks — starting from circuits and features at microscopic scale — that could eventually enable safety breakthroughs by revealing elegant internal structure.

**Core approach — the tractable sub-problem strategy:**
- The hard problem (understand a full neural network) is attacked by picking the tractable sub-problems that *open the agenda*: features, circuits, circuit motifs, universality
- **Superposition** (networks pack more features than neurons, obscuring interpretability) is the key bottleneck the field works around
- Picking foundational work today — even microscopic, even slow — enables macroscopic understanding tomorrow

**The dreams (long-term goals):**
1. Feature families parameterized by variables (orientation, scale, hue) that organize vast feature spaces like a structured database — an "anatomy" for networks
2. Circuit motifs as the repeating building blocks (more important than individual circuits), bridging microscopic to macroscopic
3. Automated interpretability where AI systems assist human analysis at scale
4. Ultimate goals: safety contributions + revealing genuine elegance inside models

**Framework for choosing what to work on:**
- "Circuits could act as a kind of epistemic foundation for interpretability" — like assembly language for code or axioms for math, it permits rigorous verification of any higher-level claim
- Justification for prioritizing foundations over flashy results: the bottom-up approach prevents misinterpretation from top-down hypothesis testing
- The finding that "induction heads" have macroscopic implications shows microscopic work can yield field-changing insights

**Key quote:** "Circuits could act as a kind of epistemic foundation for interpretability — permitting rigorous verification of any interpretability claim."

**Why it's in the guide:** A masterclass in choosing the tractable sub-problem that opens a whole agenda instead of charging the big question head-on. The research strategy — pick the foundational work that enables everything else — applies far beyond AI.

---

## Research as a Stochastic Decision Process — Jacob Steinhardt — https://cs.stanford.edu/~jsteinhardt/ResearchasaStochasticDecisionProcess.html — read — STRONG

**Thesis:** Treating research projects as stochastic decision processes — where you systematically prioritize actions by information gained per unit time — can double or triple productivity compared to naive ordering strategies.

**Core framework:**
- Research is a multi-round game where each action gives information. Two competing goals: maximize eventual success probability, minimize expected time.
- Two modes: **de-risking mode** (determine feasibility quickly) and **execution mode** (solve quickly).
- The naive ordering (easiest first, or difficulty-ordered) fails because it wastes work if the hardest assumption proves intractable.

**Ordering by information rate:**
- Sort tasks by how much time you save if earlier tasks fail — fail fast on the risky ones
- Model failures as a Poisson process: calculate rate λ = -ln(success_probability)/time; always sort in decreasing order of λ
- Higher-failure-probability tasks should come earlier, not later — even though intuition says get certainty first

**De-risking: front-loading information:**
- Seek information *about* a task before executing it. Create cheap ways to assess feasibility before full commitment.
- Example: Don't fully preprocess a dataset before training. Download samples, compute statistics, assess suitability first.
- Pattern: "De-risk all components (to the extent feasible), then execute."

**Practical tactics:**
- **Ceilings and baselines:** Substitute "cheating" versions of hard components (ceilings) and simple lower-bound methods (baselines) to validate the system before building the hard parts
- **Brute-force first:** Slow but correct implementation as debugging reference; optimize after
- **Counterexamples early:** Search for counterexamples to rule out entire proof strategies before building on them
- **Simplified cases:** Test simplified problem instances to eliminate approaches before heavy investment

**Exponentially branching search trees:**
- With 10 approaches per step and 3 steps: 1000 possibilities. Prune at the conceptual level, not implementation level.
- Ask *why* things failed to avoid repeating the same failure
- "I tried an implementation comprising 0.1% of the possible implementations of X" — distinguish implementation failure from approach failure
- Use solid logical arguments to rule out ideas, not mere pessimism

**Key quote:** "If I feel pessimistic about an approach but fail to rule out that it could work, I often then feel more optimistic."

**Why it's in the guide:** The operational algorithm for *running* a project once chosen. De-risk the load-bearing assumption first is the single most important discipline for avoiding wasted months.

---

## Research Taste Exercises — Chris Olah (Anthropic) — https://colah.github.io/notes/taste/ — read — STRONG

**Thesis:** Developing research taste is crucial but expensive to test directly (months per idea). Strategic exercises provide faster, lower-quality feedback loops to accelerate taste development.

**Core problem:** "Actually testing whether a research idea you come up with is good is very expensive. Often it takes months, so you only really get a few pieces of feedback on your taste every year."

**Five primary exercises:**
1. **Mentor feedback:** Submit ideas to a respected mentor for 1-10 ratings. Discuss disagreements. Cheap evaluation proxy.
2. **Observe others' attempts:** Track when peers pursue ideas you've considered. Compare outcomes against your predictions.
3. **Researcher interviews:** Ask colleagues about their problem-selection criteria and "big picture" research philosophy (not pitch your projects).
4. **History of science study:** Read scientific histories (Kuhn). Analyze why researchers pursued important directions contemporaries missed.
5. **Critical self-examination:** Audit your taste and your community's taste. Where was your cluster wrong recently? Articulate adjacent schools' perspectives.

**The key decision-making questions:**
- "If another group published the paper you have in mind, are you excited to read it?" (Rachel Prudden) — the most penetrating filter
- "What are the most interesting problems in your field? Why aren't you working on them?" (Hamming, reframed by Andy Matuschak)

**Three failure modes:**
1. **Sunk cost trap:** Locked into a direction by circumstance. Antidote: biannually list promising directions and ask what you'd choose starting fresh.
2. **Knowledge vacuum:** Attempting taste without theoretical grounding. Antidote: collaborate on others' projects first.
3. **Misaligned environment:** Working on compromised problems. Antidote: relocate or exercise taste *within* the constraints while seeking alignment.

**Additional frameworks:**
- **Bottleneck analysis** (Arthur Allshire): Identify field-constraining problems rather than incremental improvements
- **Project proposals** (Preetum Nakkiran): Before >1 month commitments, write a page explaining interest, value, expected findings
- **Mess identification** (Michael Nielsen): Fields lacking unifying concepts represent opportunity, not obstacles
- **20/80 projects** (Boaz Barak): Pursue problems that distill main obstacles even if final results lack prestige

**Why it's in the guide:** Turns "taste" into trainable drills. The "if another group published this, would you be excited?" question is the closest thing to a test the skill labs actually hire for.

---

## A Recipe for Training Neural Networks — Andrej Karpathy — http://karpathy.github.io/2019/04/25/recipe/ — read — STRONG

**Thesis:** Neural network training is a leaky abstraction where networks fail *silently* — they train without throwing errors despite major bugs, producing subtly degraded performance. Success requires patience, visualization obsession, and a disciplined simple-to-complex progression.

**Two governing principles:**
1. **Silent failure:** Unlike code that breaks visibly, misconfigured networks still produce output — just subtly worse. A model with flipped labels or wrong regularization trains fine. You have to look for the problem.
2. **Leaky abstraction:** Small deviations from standard setups require understanding how backprop, batch norm, and optimization actually function.

**The six-stage recipe:**

1. **Become one with the data** — spend hours manually inspecting thousands of examples before touching code. Find duplicates, corruption, label noise, imbalances. Outliers on every axis "almost always uncover bugs."

2. **Set up end-to-end pipeline + dumb baseline:**
   - Fix random seed; disable augmentation; verify loss at init (softmax should start at `-log(1/n_classes)`)
   - Init final layer correctly (if labels mean=50, set bias=50; if 1:10 imbalance, predict 0.1 probability)
   - Overfit one batch: 2 examples, increased model size → should reach zero loss
   - Visualize immediately pre-model (decode raw tensor exactly before `y_hat = model(x)`)
   - Input-independent baseline: zero all inputs, should perform worse than with real data
   - Backprop to verify dependencies: gradients only on i-th input for example i

3. **Overfit:** Get a model large enough to fit training data perfectly, *then* regularize. Two-stage approach isolates fundamental problems.
   - "Don't be a hero" — copy the simplest architecture from related papers (ResNet-50 for image classification)
   - Adam with lr=3e-4 is safe to start; more forgiving than SGD's narrow optimal range
   - Never trust LR decay defaults; disable and tune as final step

4. **Regularize (in order of effectiveness):**
   - More real data (only guaranteed monotone improvement)
   - Data augmentation (next best thing)
   - Pretrain (rarely hurts even with enough data)
   - Smaller input dimensionality; smaller model size; decrease batch size; dropout; weight decay; early stopping
   - Larger model + early stopping often beats smaller model + full training

5. **Tune:** Random search over grid search — neural nets vary in sensitivity per hyperparameter; random sampling explores important parameters more efficiently.

6. **Squeeze out the juice:** Ensembles give "pretty much guaranteed" 2% accuracy gains. Leave training longer than intuition suggests ("accidentally left during winter break... returned in January to find it SOTA").

**Meta-principle:** Simple to complex, one hypothesis per step. "Build from simple to complex and at every step make concrete hypotheses about what will happen, then either validate them or investigate until you find the issue."

**Key quote:** "If writing your neural net code was like training one, you'd want to use a very small learning rate and evaluate after every iteration."

**Why it's in the guide:** The craft embodiment of "stay close to the run." These habits prevent the failure mode of introducing unverified complexity and spending weeks debugging phantom problems.

---

## Understanding Reasoning LLMs — Sebastian Raschka — https://magazine.sebastianraschka.com/p/understanding-reasoning-llms — read — MUST

**Thesis:** Reasoning LLMs are a specialization (not replacement) for complex multi-step tasks. There are four distinct technical approaches to build them, with DeepSeek-R1 as the production blueprint. The key innovation: verifiable rewards eliminate the need for expensive human preference labeling.

**The four building methods:**

1. **Inference-time scaling:** More compute during generation without retraining. Chain-of-thought prompting, majority voting, beam search, MCTS with process-reward models. OpenAI o1 likely uses this heavily (explains higher per-token cost). DeepSeek deemed it "unsuccessful" as a standalone training method.

2. **Pure RL (DeepSeek-R1-Zero):** Training exclusively with RL, skipping SFT entirely ("cold start"). Two reward types:
   - Accuracy reward: LeetCode compiler for code, deterministic math evaluation
   - Format reward: LLM judge ensuring `<think>` tag structure
   Result: "Aha!" moment where model spontaneously generated reasoning traces without explicit training. Reasoning as emergent behavior.

3. **SFT + RL (DeepSeek-R1's superior pipeline):**
   - Step 1: Generate cold-start SFT data from R1-Zero
   - Step 2: Instruction fine-tune on this data
   - Step 3: RL with accuracy + format + consistency rewards (preventing language mixing)
   - Step 4: Generate 600K CoT + 200K knowledge-based SFT examples
   - Step 5: Final SFT
   - Step 6: Final RL (rule-based for math/coding; human preference for other domains)
   Substantially outperforms R1-Zero.

4. **Distillation (pure SFT on larger model's outputs):** Smaller models (Llama 8B/70B, Qwen 0.5B–32B) trained on SFT data from larger teachers. "Surprisingly strong reasoning performance despite being significantly smaller." Distillation dramatically outperforms pure RL on small models — RL may require scale to work.

**The verifiable-reward innovation:** Eliminate human preference labels for evaluable tasks. Use LeetCode compiler (code), deterministic math evaluation, format compliance. No human annotation needed for initial reasoning emergence. RLVR takes a base model from 5% to 50% accuracy on MATH-500 in just 50 RL steps — "not learning new knowledge, just unlocking what's already there."

**GRPO vs. standard PPO:** GRPO (Group Relative Policy Optimization) eliminates the reward model and value model from the training loop — going from 3 large models in memory down to 1. This is what makes RLVR practical at 671B-parameter scale.

**Budget-constrained development:**
- Sky-T1: 32B model, 17K samples, $450 total → "roughly on par with o1"
- TinyZero: 3B model, pure RL, <$30 → emergent self-verification
- Journey learning: training on both correct AND incorrect solution paths → reinforces self-correction without RL

**Key selection principle:** Reasoning models excel at complex tasks (puzzles, advanced math, coding) but become inefficient and error-prone on simple queries. Match tool to task complexity.

**Why it's in the guide:** The cleanest synthesis of how reasoning models actually work. Backs the "verifiable reward goes vertical" principle with implementation depth. The blueprint for building your own reasoning loop.

---

## The Big LLM Architecture Comparison — Sebastian Raschka — https://magazine.sebastianraschka.com/p/the-big-llm-architecture-comparison — read — STRONG

**Thesis:** Despite surface similarity to GPT-2, modern LLMs have systematized efficiency gains through proven load-bearing changes. The frontier has shifted from "novel components" to "careful parameter allocation and hybrid attention strategies."

**Load-bearing vs. cosmetic choices:**
- **Load-bearing (real performance/efficiency impact):** MoE with sparse activation, Multi-Head Latent Attention (MLA) vs. GQA, attention mechanism variants (sliding window, linear attention hybrids), normalization placement
- **Cosmetic (minimal delta):** RoPE vs. absolute positional embeddings, SwiGLU vs. GELU activations, bias units in attention (shown redundant in ablations)

**Key frontier models side-by-side:**

| Model | Total Params | Active | Key Architectural Choice |
|---|---|---|---|
| DeepSeek V3 | 671B | 37B | MoE (256 experts, 9 active) + MLA + shared expert |
| Llama 4 Maverick | 400B | 17B | MoE (8 experts, 2 active), GQA, alternating dense/MoE |
| Gemma 3 | 27B | 27B (dense) | Sliding window 5:1 local:global, dual RMSNorm |
| Qwen3 235B | 235B | 22B | MoE (256 experts, 8 active), no shared expert |
| Kimi K2 | 1T | 157B | DeepSeek V3 architecture scaled with Muon optimizer |

**Key architectural findings:**

1. **MLA outperforms GQA:** DeepSeek-V2 ablations showed GQA underperforms MHA; MLA outperforms MHA. MLA compresses K/V to lower-dim space — better performance AND smaller KV cache.

2. **Shared expert debate:** DeepSeek/GLM/Grok use them; Qwen3 and MiniMax-M2 don't. Qwen team: "no significant improvement on shared expert... worried about optimization."

3. **Post-Norm + QK-Norm** (OLMo 2/3): Post-norm after layers is what older literature said was unstable, but OLMo 2 showed Post-Norm + QK-Norm combination improved training loss curves. Multiple teams (Allen AI, Alibaba, Google) independently adopted QK-Norm — suggests real training stability benefits.

4. **Linear attention revival:** Qwen3-Next and Kimi Linear use Gated DeltaNet + full attention hybrid (3:1 ratio). Recovers accuracy loss seen in pure linear attention. Still unclear if it scales to 671B+.

5. **NoPE (no positional encoding) in specific layers:** SmolLM3, Arcee Trinity. Better length generalization at small scales. Challenges necessity of positional information everywhere.

**Frameworks for reading architecture papers:**
- Separate parameter count transparency (total vs. active; embedding exclusion practices vary)
- Demand ablation studies isolating one variable at a time
- Ask: "Is this change cosmetic or does it change training dynamics / inference cost?"
- Look at training loss curves, not just benchmark accuracy

**Why it's in the guide:** The practitioner's lens for reading an architecture paper and knowing which choices are cosmetic vs. load-bearing. Builds the ability to evaluate a new model announcement critically.

---

## Your AI Product Needs Evals — Hamel Husain — https://hamel.dev/blog/posts/evals/ — read — MUST

**Thesis:** Unsuccessful AI products almost always share a common root cause: failure to create robust evaluation systems. Most builders focus exclusively on modifying behavior (prompts), neglecting evaluation and debugging. Without evals, you can't improve past the demo.

**The Rechat case study (Lucy, conversational AI for real estate):**
Initial prompt engineering gains plateaued as product expanded. Addressing one failure triggered others (whack-a-mole). Solution: center improvement on systematic evaluation.

**Three-level evaluation pyramid:**

1. **Unit Tests (fast, cheap, run on every code change):**
   - Break functionality into feature × scenario matrix
   - Example: Listing Finder feature tested across `len(listing_array) == 1`, `> 1`, `== 0`
   - Use LLMs to synthetically generate test inputs (Rechat: 50 contact-creation instructions per batch)
   - Integrate with CI/CD (GitHub Actions). Track pass rates over time.
   - Key: 100% isn't required — it's a product decision
   - "Rechat has hundreds of these unit tests. We continuously update them based on new failures observed in data."

2. **Human & Model Evaluation (set cadence, not per-change):**
   - **Log traces:** Logical groupings of logs. Rechat used LangSmith for trace storage.
   - **Remove friction from data review:** Build custom domain-specific viewing tools. Rechat built a Shiny-for-Python interface with feature/scenario filters, links to CRM and trace systems. "You must remove all friction from the process of looking at data."
   - **Automated model-based evaluation:** Use powerful models (Claude, GPT-4) to critique outputs. Track model-human agreement via spreadsheet (25–50 examples per iteration). Monitor precision/recall separately.
   - Initial phase: examine ALL traces. Then sample-based. Continue until learning plateaus.

3. **A/B Testing (high cost, mature products only):** Defer until you have conviction.

**Evals as superpower — unlocks fine-tuning almost for free:**
- Generate synthetic variations using same prompts as test case generation
- Filter via Level 1 assertions and Level 2 critique models
- Curate via existing human evaluation tools
- "99% of the labor of fine-tuning is assembling high-quality data that covers your AI product's surface area. If you have a solid evaluation system, you already have a robust data generation and curation engine."

**Why evaluation systems fail:**
- Jumping to human evaluation without unit tests
- Ignoring friction in data review (scattered information sources)
- Over-relying on generic frameworks instead of domain-specific systems
- Insufficient data review volume

**Key quotes:**
- "Like software engineering, success with AI hinges on how fast you can iterate."
- "Keep it simple. Don't buy fancy LLM tools. Use what you have first."
- "You are doing it wrong if you aren't looking at lots of data."

**Why it's in the guide:** From 30+ production builds. The operator's version of "build the verifier first." Most AI product failures are not model capability failures — they're eval failures.

---

## Agents — Chip Huyen — https://huyenchip.com/2025/01/07/agents.html — read — STRONG

**Thesis:** Agent success depends on two pillars: tool inventory and planning capability. The taxonomy of tools and planning patterns determines what's architecturally possible.

**Tool taxonomy:**
1. **Knowledge augmentation (read-only):** Web search, SQL, internal systems, social APIs. Prevents model staleness.
2. **Capability extension:** Calculator, code interpreters, OCR, image captioners. Addresses inherent AI limitations. Chameleon (13 tools with GPT-4) improved ScienceQA by 11.37% and TabMWP by 17% over baseline.
3. **Write actions (state modification):** Database updates, email sending, bank transfers. Higher stakes — require human approval gates.

**Accuracy degradation with step count:** At 95% per-step accuracy: 10 steps → 60% total accuracy; 100 steps → 0.6%. Agents require more capable models than single-call uses.

**Planning architecture — separation pattern:** Planning should decouple from execution. Flow: Plan Generation → Validation → Execution → Reflection/Correction. This naturally creates multi-agent systems.

**Control flow types:**
- Sequential (B after A), Parallel (A and B simultaneously), Conditional/routing (choose B or C), Loops (repeat until condition)
- Non-sequential flows are architecturally harder to generate and translate

**Planning frameworks:**
- **ReAct (Reasoning + Acting):** Interleaves `Thought → Act → Observation` per step. Outperforms action-only on knowledge and decision tasks.
- **Reflexion:** Separates evaluator from self-reflection module; stores up to 3 reflections from failed attempts. Improves accuracy but increases token cost — tradeoff at scale.
- **Function calling vs. natural language plans:** Function calling = easier execution, brittle to API changes. Natural language plans = robust to tool changes, requires separate translation module.

**Tool selection strategy:**
- More tools = more capability but harder to use efficiently (context limits, tool confusion)
- Run ablations: measure performance drop when each tool is removed
- Identify frequently co-used tools for combination (Chameleon approach)
- Different tasks and models show distinct tool preferences

**Key tradeoffs:**
- Reflection = better accuracy but higher cost/latency
- Autonomous execution = cost-effective but risky (require approval gates for critical actions)

**Why it's in the guide:** The taxonomy for why LangGraph topology choices are non-cosmetic. Every architectural decision in an agent system is a tradeoff between these dimensions.

---

## Machines of Loving Grace — Dario Amodei — https://darioamodei.com/essay/machines-of-loving-grace — read — MUST

**Thesis:** Powerful AI (~2026) could compress 50–100 years of scientific and social progress into 5–10 years, creating a radically better world — but only if we actively fight for positive outcomes rather than assuming benefits materialize automatically.

**Core framework — "marginal returns to intelligence" by domain:**
Rather than assuming instant transformation (Singularity) or minimal impact, analyze what actually limits progress in each domain. AI routes around bottlenecks over time.

**Five domains and timelines:**

1. **Biology & Physical Health ("compressed 21st century" in 5–10 years):**
   - "I'm not talking about AI as merely a tool to analyze data... I'm talking about using AI to perform, direct, and improve upon nearly everything biologists do."
   - Progress driven by ~1–2 major techniques yearly (CRISPR, mRNA, CAR-T). Returns to intelligence are high because these discoveries are made by tiny elite groups and many "could have been made" years earlier.
   - Predictions: reliable prevention of nearly all natural infectious disease; cancer mortality reduced 95%+; Alzheimer's prevention; human lifespan potentially doubled to ~150 years (justification: 2× life expectancy increase already happened in 20th century; some animals live 200+ years; existing drugs show 25–50% lifespan extension in rats)

2. **Neuroscience & Mental Health (same 100-year compression, 5–10 years):**
   - Four routes: molecular biology (new psychotropics), neural measurement/intervention, computational neuroscience, behavioral interventions
   - Most mental illness (PTSD, depression, schizophrenia, addiction) potentially cured via biochemistry + neural circuit intervention
   - Unique asymmetry: interpretability techniques for AI directly illuminate brain computation
   - "Everyday problems" (anger, focus, drowsiness) solvable via drugs/optogenetics/magnetic fields
   - Baseline human experience radically improved: more frequent access to creativity, compassion, transcendence

3. **Economic Development & Poverty:**
   - Historical precedent: East Asian Tiger economies achieved 10% annual real GDP growth
   - AI "finance ministers" could potentially replicate; dream scenario: 20% growth in developing world → Sub-Saharan Africa reaches current China GDP per capita in 5–10 years
   - Less confident here: heavy human constraints (corruption, weak institutions, political resistance)
   - Risk: automation harming countries not yet industrialized

4. **Peace & Governance:**
   - "I see no strong reason to believe AI will preferentially advance democracy and peace." AI aids both authoritarians and democrats.
   - Proposed "entente strategy": democratic coalition secures AI supply chain + military advantage, then carrot/stick isolation of non-compliant regimes
   - AI could strengthen institutions: reduce judicial bias, counter propaganda, improve government services

5. **Work & Meaning:**
   - Short-term: comparative advantage keeps humans relevant even with 90% automation (the remaining 10% gets highly leveraged)
   - Long-term: if AI becomes simultaneously cheap and broadly superior, comparative advantage collapses; current economic system breaks down
   - Meaning crisis probably won't happen (humans find meaning in relationships and challenges, not economic productivity)

**Key quote:** "I think that most people are underestimating just how radical the upside of AI could be."

**Why it's in the guide:** Research taste applied at civilizational scale — which problems are worth a decade. The framework of "marginal returns to intelligence per domain" is directly applicable to problem selection.

---

## Two Alignment Threat Models — Jan Leike (Anthropic) — https://aligned.substack.com/p/two-alignment-threat-models — read — STRONG

**Thesis:** Strong elicitation capabilities are foundational to alignment success, addressing both current performance deficits (under-elicited models) and future catastrophic risks (scheming models).

**Core taxonomy — two threat models:**

1. **Under-elicited models ("sloppy"):**
   - Characteristic: Poor task performance due to insufficient effort
   - Behavior: Laziness, capability limitations, mundane mistakes
   - Risk profile: Ordinary failures; malicious behavior rare (only via poisoned data or imitation)
   - Current state: InstructGPT showed >100× effective pretraining compute gains possible through RLHF improvements — multiple orders of magnitude in alignment gains likely remain discoverable

2. **Scheming models ("deceptive"):**
   - Characteristic: Deceptive alignment with hidden hostile intentions
   - Behavior: "Pretending to be aligned, secretly plotting against us, seeking power"
   - Risk profile: Strategic defection when unmonitored; subtle goal misalignment
   - Currently limited by model intelligence and situational awareness; will increase as models improve
   - Extended RL training may inadvertently reinforce convergent instrumental goals (self-preservation, power-seeking)

**Why elicitation matters for safety:**
- Dangerous capability evaluations underestimate risks if models are under-elicited (we don't find the capability and declare it safe)
- Humans cannot oversee most inference — models must supervise themselves via reward models and monitoring
- Under-elicited monitors fail against malicious agents; a weak monitor can be bypassed by a scheming agent
- Better elicitation reduces "slack" available for pursuing ulterior motives

**Strategic implication:** Don't anchor assumptions on current model behavior. Prepare for scheming detection even while it's currently rare.

**Why it's in the guide:** A clean 1,500-word taxonomy from the person now running Anthropic's alignment science. Reframes alignment work from abstract philosophy to two concrete threat models with distinct mitigations.

---

## Practicing AI Research — Jason Wei (OpenAI, CoT author) — https://www.jasonwei.net/blog/practicing-ai-research — read — MUST

**Thesis:** Research is a learnable skill, like sports or music. Excellence depends on mastering four distinct competencies, not innate talent.

**Four core skills:**

1. **Idea conception & selection (highest leverage):**
   - Favor simple, general, timeless topics over complicated, task-specific, short-lived ones
   - Two strategies: dominate a hot topic (lower risk, high execution) or pioneer what becomes the next hot field (higher risk/reward)
   - Topic selection multiplies impact more than execution excellence — spend disproportionate time here
   - Recognize sunk cost fallacies immediately (Wei abandoned medical imaging for NLP when stalled)
   - Key question: "Consult experienced researchers about exciting directions" — they often see the emerging areas before they're obviously hot

2. **Experiment design & execution:**
   - Present experimental designs to colleagues for rigor checks before running
   - Prioritize speed due to high opportunity costs; demonstrate commitment through rapid iteration
   - Brilliant ideas fail with messy execution

3. **Paper writing:**
   - Frame results within field context — why does this matter, how does it change what readers should do?
   - Disproportionate effort on abstracts and introductions; most readers only skim
   - Design standalone figures (optimized for Twitter screenshots)
   - Simple language; accommodate non-native English speakers
   - "Most readers will only skim or look at a screenshot of a figure on twitter"

4. **Maximizing impact (most underrated, easiest to improve):**
   - Twitter promotion (highest ROI per effort)
   - Open-source code, data, model checkpoints
   - Conference presentations, talks, YouTube, blog posts, follow-up papers
   - Personal website as ongoing visibility
   - Hamming's principle: "at least 50% of time must go for the presentation" beyond research itself

**Meta-level accelerators:**
- **Collaborator selection:** Strong collaborators push all four skills. Approach senior researchers through their PhD students or direct reports.
- **Researcher admiration practice:** Periodically identify admired researchers (Wei lists: Shazeer, Devlin, Dean, Liang, Zoph, Chen) and reverse-engineer their skill patterns
- **Goal architecture:** Balance input metrics (hours) and output metrics (citations); over-optimizing for one creates failure modes

**Key CoT origin insight:** The chain-of-thought paper was a matter of recognizing the idea had impact before it was obvious — and then executing rigorously enough for it to be credible.

**Why it's in the guide:** The execution layer under Schulman's concept/execution split. Four concrete learnable skills, not "be smarter."

---

## LLM Powered Autonomous Agents — Lilian Weng (OpenAI) — https://lilianweng.github.io/posts/2023-06-23-agent/ — read — STRONG

**Thesis:** LLMs can function as agent controllers — extending beyond text generation to general problem-solving — through integrated planning, memory, and tool-use systems.

**Planning frameworks taxonomy:**
- **CoT (Wei et al. 2022):** "Think step by step" — decomposes complex tasks, utilizes additional test-time compute
- **ToT (Tree of Thoughts):** Explores multiple reasoning paths at each step via BFS/DFS with classifier evaluation or majority voting
- **ReAct:** Interleaves language reasoning with discrete environmental actions: `Thought → Action → Observation` (repeat). Outperforms action-only on knowledge and decision tasks.
- **Reflexion:** Adds dynamic memory and self-reflection to RL framework. Detects inefficient trajectories via heuristic functions. Stores up to 3 reflections from failed attempts. Improvement at the cost of token overhead.
- **Chain of Hindsight (CoH):** Fine-tunes on sequences of past outputs ranked by quality, including token masking (0-5%) to prevent shortcutting.
- **Algorithm Distillation (AD):** Distills learning algorithms into long history-conditioned policies; requires 2–4 episode contexts for in-context RL emergence.

**Memory taxonomy:**

| Type | Duration | Implementation |
|---|---|---|
| Sensory | ~seconds | Embedding representations |
| Short-Term/Working | 20-30 sec, ~7 items (Miller 1956) | In-context learning |
| Long-Term | Days-decades, unlimited | External vector stores (FAISS, HNSW, ScaNN) |

LTM subtypes: Explicit/Declarative (facts, events), Implicit/Procedural (skills, automatic routines).

**Tool use patterns:**
- **MRKL:** LLM routes queries to specialized expert modules (neural/symbolic). Critical: knowing *when* and *how* to use tools.
- **TALM/Toolformer:** Fine-tune LMs on expanded datasets where API annotations improve outputs
- **HuggingGPT:** Four-stage: task parsing → model selection → execution → summarization

**Case studies with numbers:**
- ChemCrow (13 expert tools): "Large superiority over GPT-4 alone" per human evaluation; 4/11 (36%) anticancer drug synthesis requests accepted before safety check; web search triggered 5/7 rejections of chemical weapon synthesis
- Generative Agents: 25 LLM-controlled virtual characters with emergent behaviors (information diffusion, relationship continuity, event coordination)

**Critical challenges:**
1. Finite context length limits historical information and self-reflection mechanisms
2. Long-term planning deficits: lacks human-like trial-and-error learning
3. Natural language interface reliability: formatting errors, inconsistent output parsing

**Why it's in the guide:** The canonical architectural map of agent systems — the reference cited by almost every serious agent paper. Read for the taxonomy before building.

---

## The Shift from Models to Compound AI Systems — BAIR (Zaharia, Frankle, Rao et al.) — https://bair.berkeley.edu/blog/2024/02/18/compound-ai-systems/ — read — MUST

**Thesis:** SOTA AI results are increasingly obtained by compound systems with multiple interacting components — not monolithic models. Clever engineering now achieves frontier performance without proportional compute increases.

**Definition:** A compound AI system "tackles AI tasks using multiple interacting components, including multiple calls to models, retrievers, or external tools."

**Landmark examples (what compound systems achieved vs. models alone):**
- **AlphaCode 2:** Generates up to 1M code solutions, filters/scores with fine-tuned LLMs + execution + clustering → matches 85th percentile of humans on coding contests
- **AlphaGeometry:** Fine-tuned LLM + symbolic math engine, iteratively suggesting constructions → between silver and gold IMO medalists
- **Medprompt:** GPT-4 + nearest-neighbor search through examples + CoT + multi-sampling/ensembling → outperforms specialized medical models like Med-PaLM
- **Gemini on MMLU:** CoT@32 strategy (sample 32 CoT answers, return top choice when agreement exists) → 90.04% vs 86.4% for GPT-4
- **v0 / Vercel:** RAG + stream-fixing + deterministic AST fixes → 93.87% error-free rate vs Claude Sonnet's standalone 64.71%

**Why compound systems outperform scaling alone:**
1. **System design efficiency:** "Scaling offers lower returns-vs-cost than building a compound system." Tripling training budget might improve coding from 30% to 35%; AlphaCode's multi-sampling-and-testing approach achieves 80%. "Iterating on system design is often much faster than waiting for training runs."
2. **Dynamic knowledge:** Static training data can't incorporate real-time information; retrieval components solve this
3. **Control and trust:** Neural networks alone resist behavioral guarantees; systems enable filtering, citations, verification
4. **Performance flexibility:** Different cost-quality tradeoffs per application

**Empirical evidence of the shift:**
- 60% of LLM applications use RAG; 30% use multi-step chains (Databricks survey)
- Microsoft's chaining strategy exceeded GPT-4 accuracy on medical exams by 9%
- GitHub Copilot uses "carefully tuned smaller models and various search heuristics" for cost efficiency

**The DSPy approach:** Automatically tune pipeline by creating prompt instructions, few-shot examples, and parameter choices given a target metric. Operates like PyTorch for non-differentiable modules.

**FrugalGPT:** Routing strategy that "can outperform the best LLM services by up to 4% at the same cost, or reduce cost by up to 90% while matching quality."

**Design challenges:**
- Vast design space: even simple RAG presents many combinations (retrieval model, query expansion, reranking, verification)
- Co-optimization: components must work together synergistically; non-differentiable elements need novel optimization
- New operational concerns: trace monitoring, vector database DataOps, unforeseen security risks

**Key quote:** "Leading AI results can be achieved through clever engineering, not just scaling up training."

**Why it's in the guide:** The field-defining manifesto that every agent builder is operating inside. The paradigm that makes Lancelot's harness-over-weights approach correct.

---

## LLM Architecture Gallery — Sebastian Raschka — https://sebastianraschka.com/llm-architecture-gallery/ — read — MUST

**Thesis:** A visual reference showing exactly what changed model-to-model — the fastest way to build intuition about which architectural choices are load-bearing vs. cosmetic.

**Core architectural dimensions that vary:**

**Attention mechanisms (primary differentiator):**
- Full MHA (OLMo 2/3), GQA (Llama 3, most modern), MLA (DeepSeek V3, GLM-5, Kimi K2 — compresses K/V, better than GQA in ablations), Sliding-window + global hybrids (Gemma 3/4, Mistral), Linear/Delta-Net (Qwen3 Next, Ling 2.5), Compressed sparse attention (DeepSeek V4)

**Normalization placement:**
- Pre-norm (RMSNorm before layers): standard. Post-norm (after): OLMo. QK-Norm (query/key normalization): OLMo 2, Qwen3, Gemma 4, MiniMax M2. Multiple independent teams adopting QK-Norm suggests real training stability benefits.

**Positional encoding:**
- RoPE: dominant. NoPE (no positional encoding) in some layers: SmolLM3, Kimi Linear. Partial RoPE: MiniMax M2. Absolute: legacy.

**MoE characteristics:**
- Expert count: 128–512+ per model; Active ratio: 3–17% (DeepSeek V3 at 5.5%); Shared experts: present in DeepSeek/GLM/Grok, absent in Qwen3 235B; Hash-based routing (V4) reduces routing compute at scale

**Critical patterns:**
1. MoE is the scaling path — newest flagships use sparse activation rather than pure scaling
2. Convergence toward MLA + sparse attention: GLM-5, DeepSeek V3.2/V4, Mistral Large 3
3. Context length demands either aggressive local-window attention or linear alternatives to manage KV cache
4. QK-Norm as training stability lever — multiple independent adoptions
5. Multi-token prediction (MTP) enables speculative decoding across many recent models

**Why it's in the guide:** The visual reference for knowing what each model actually changed. The fastest way to see the frontier without reading 11 architecture papers.

---

## The Ultra-Scale Playbook — Hugging Face (nanotron) — https://huggingface.co/spaces/nanotron/ultrascale-playbook — partial (rendering issue, framework known) — STRONG

**Thesis:** Training LLMs across hundreds of GPUs requires systematic understanding of four parallelism strategies, their memory/compute tradeoffs, and empirical guidance from running thousands of experiments.

**Core parallelism strategies:**

1. **Data Parallelism (DP):** Distribute batch across GPUs; each GPU holds full model. Scales with batch size; communication = gradient sync. Best for models that fit in single GPU memory.

2. **Tensor Parallelism (TP):** Split model weights across devices within a layer. All-reduce required after each layer. Limited by communication overhead; typically constrained to within a node.

3. **Pipeline Parallelism (PP):** Divide layers across GPUs sequentially. Micro-batching required to prevent pipeline bubbles. Higher latency per sample but enables models that don't fit in combined TP memory.

4. **Expert/MoE Parallelism:** Route different experts to different GPUs. Expert load balancing is critical; routing collapse is the key failure mode.

**Combined strategies (3D parallelism):** Most modern large-scale training uses TP + PP + DP combinations, with the specific ratios determined empirically per hardware/model size.

**Memory optimization:**
- Activation checkpointing: recompute activations during backward pass instead of storing them (trades compute for memory)
- ZeRO stages: shard optimizer states (1), gradients (2), or weights (3) across data-parallel replicas
- Flash Attention: memory-efficient attention implementation, standard in modern training

**Key empirical finding:** There's no "magic bullet" parallelism strategy. Progress comes from "a lot of little tips and tricks all over the place" — adding them up gives the performance.

**Why it's in the guide:** The real "how training works at scale" — not theory. 4,100+ experiments distilled into empirical guidance.

---

## State of LLMs 2026: RLVR, GRPO, Inference Scaling — Sebastian Raschka — MAD Podcast — https://www.youtube.com/watch?v=K5WPr5dtne0 — transcribed — STRONG

**Key thesis:** "Pre-training is not dead, but pre-training is boring. It's not where the low-hanging fruit is anymore." The biggest lever in 2025–2026 is post-training (RLVR + GRPO) combined with inference scaling.

**Architecture:** Transformer still state-of-the-art; alternatives (diffusion, Mamba, SSMs) exist but no replacement on the horizon. Modern models are GPT-2 + a few engineering changes: MoE, MLA, sparse attention, normalization tweaks. DeepSeek V3 restarted the MoE trend in late 2024; most developers now adopt that architecture or iterate on it.

**Post-training timeline (Raschka's framework):**
- 2022: RLHF → ChatGPT from GPT
- 2023: LoRA/SFT → efficient fine-tuning
- 2024: Mid-training (domain adaptation)
- 2025: RLVR + GRPO → reasoning models

**RLVR vs. RLHF:** RLHF needs 3 models in memory (policy + reward + value); GRPO eliminates reward model (replaced by verifiable rewards) and value model (replaced by group relative comparison). Goes from 3×671B params in memory to 1×671B. "RLHF is taking GPT to ChatGPT; RLVR is taking ChatGPT to a reasoning model."

**Demonstration:** Taking Qwen3 base model, 50 RL steps with verifiable rewards → 5% to 50% accuracy on MATH-500. "It's not learning new knowledge. The knowledge is already there in pre-training. This just unlocks it."

**Inference scaling in 2025-2026:** 
- One of the biggest practical drivers; went from 5% to 50% accuracy by adding 50 RL steps
- Forms: reasoning model verbosity (more tokens = more expensive), parallel sampling (majority vote), self-refinement iterations, RLMs chunking prompts
- Tool use with inference scaling: GPTOSS ablation showed ~1.2× performance gain just from enabling tool calling on same model weights
- "There's no one thing that fixes it all. It's a lot of little tips and tricks all over the place."

**Process Reward Models (PRMs):** Outcome reward = is final answer correct. Process reward = evaluate intermediate reasoning steps. PRMs "not successful yet" — open research problem. Intermediate explanation useful for generating correct answers even when the explanation itself is not always correct.

**Private data as the next frontier:** All major LLMs now "similarly good" in general use. The differentiator: proprietary domain data (medical records, financial history). Big companies are now training LLMs in-house at datacenter scale rather than giving data to providers. "The treasure is the data."

**LLM as tool user:** Tool calling unlocks performance without changing weights (~1.2× performance for same model). Will proliferate as open-source tooling becomes robust and users trust models with more permissions.

---

## Section body — the guide's own wisdom for this section

### ▸ Work on important problems, or you'll do good work that doesn't matter
Hamming's hard question: "What are the important problems in your field, and why aren't you working on them?" Most strong builders never ask it. Keep a written list of the 10 problems that would change your field if solved, and check weekly whether what you're doing is on it.

### ▸ Pick by taste, not by what's publishable
John Schulman splits research into concept-driven (new idea) vs. execution-driven (make a known idea work). Novelty-seeking — chasing the un-tried because it's un-tried — is the classic trap. Choose by genuine curiosity plus aptitude, then go to the frontier and follow the anomalies.

### ▸ Bet on the right side of the Bitter Lesson
Sutton's claim: every method built on clever hand-crafted inductive bias eventually loses to scale plus search. If your edge depends on a hand-tuned heuristic beating compute, you will lose on a 12-month horizon. Lancelot wins because raw speed compounds with scale. Ask the same of any AI bet.

### ▸ Verifiable reward is where the curve goes vertical
Any domain where a solution can be auto-checked (code, math) can be driven hard with RL. Qwen 3's result: 4,000 high-quality verifiable examples beat 4 million low-quality RLHF ones. Quality and verifiability dominate quantity. For Skale: a sent reply that books a meeting is a verifiable signal. Build the verifier first; the training loop follows.

### ▸ Fine-tuning is usually a capital trap
Spend millions fine-tuning and the next base release erases your edge. Model-agnostic harnesses age better — Poetic AI's meta-system hit 54% on ARC-AGI v2 at $32/problem versus Gemini 3 Deep Think's 45% at $70, for under $100K total. Keep intelligence in the harness, not in weights you'll rent and lose.

### ▸ Intelligence is efficiency of skill acquisition, not benchmark score
Chollet's definition: a smarter system learns a new skill from fewer examples. LLMs interpolate inside the training manifold beautifully and extrapolate badly. When you read a SOTA number, ask whether the gain is interpolation on a saturated distribution or genuine generalization. Only the second kind is a primitive.

### ▸ Stay close to the run, build taste by noticing where models break
Sholto Douglas and Trenton Bricken went zero-to-frontier in ~1 year by picking problems adjacent to what's working but poorly understood, and staying close to actual training runs. Taste is built by watching where models behave unexpectedly, not by reading abstracts. Treat every weird agent failure as a research lead, not a bug ticket.

### ▸ Steelman the strongest disagreement before you bet
LeCun argues scaling autoregressive LLMs is a dead end. Sutton (who wrote the Bitter Lesson) says LLMs can't learn from experience. Ilya and Gwern argue the opposite. Taste is holding that contradiction and forming your own bet instead of joining a tribe. When two sources you respect collide, that spot is the frontier. Sit in it.

### ▸ De-risk the load-bearing assumption first, not the fun part
Steinhardt models a research project as a sequence of bets where each experiment buys information. Order by information gained per unit of time, kill the riskiest assumption before you build anything on top of it.

---

## → Top actionable takeaways for @Seventydotleven

1. **Maintain a written list of 10 important problems; review weekly.** The question "What are the important problems in my field, and why aren't I working on them?" is not rhetorical — it should change what you do this week. If Skale/Lancelot work isn't on that list, either the list is wrong or the project is wrong.

2. **Build the verifier before the training loop.** For any domain you're automating: identify the verifiable signal first (sent reply → meeting booked; code → tests pass; math → LeetCode compiler). Once you have that, RLVR makes everything downstream compoundable. The verifier is the primitive, not the model.

3. **Keep intelligence in the harness, not in weights.** Every fine-tuned model you own will be wiped by the next frontier release. Compound system architecture (harness + orchestration + retrieval + verifiers around a general model) is what survives frontier releases. Lancelot's Rust HTTP layer is the right application of this — own the layer that sets the quality ceiling.

4. **De-risk the riskiest assumption before building on top of it.** Before investing weeks in a pipeline, identify the one bet that, if wrong, invalidates everything. Run the cheapest possible experiment to kill it first. Steinhardt's λ ordering: sort experiments by failure_rate/time, not by difficulty.

5. **Evals are how you go from demo to product.** Before the next Skale feature: define the feature × scenario test matrix, generate synthetic test cases (LLM-powered), wire into CI/CD. Without the eval system, every prompt engineering change is guesswork. The eval system also gives you fine-tuning data almost for free.

6. **"If another group published this, would you be excited to read it?"** Apply this to every feature shipped, every teardown written, every product decision. If no: either the idea isn't important enough or the execution isn't differentiated enough. This question is harder than it looks.

7. **Bet against hand-crafted heuristics maintaining their edge.** The Bitter Lesson is the most predictive claim in AI. Any competitive advantage that depends on a clever encoding of domain knowledge (rather than scale + search finding that structure) is on a 12–18 month expiration clock. Lancelot's raw throughput advantage is the correct application — raw speed is a scaling axis, not a heuristic.

8. **Read architecture papers for load-bearing vs. cosmetic choices.** MLA vs. GQA is load-bearing (better performance + smaller KV cache). SwiGLU vs. GELU is cosmetic. Building this judgment: read ablations, not just benchmark results. Demand per-variable isolation.

9. **Treat weird model failures as research leads.** When an agent produces unexpected output, don't just fix it — investigate what assumption about the model was wrong. The pattern that keeps recurring (Bricken, Douglas, Schulman) is that the highest-yield research problems are exactly where current methods visibly break.

10. **Distribution is half the work — and the easiest skill to improve.** Jason Wei: "at least 50% of time must go for the presentation." For @Seventydotleven, this means Twitter-native artifacts (screenshots of architecture diagrams, before/after latency comparisons, demo clips) not just blog posts. Open-source the harness when you can; it's the distribution that turns research work into reputation.

11. **The compound AI systems thesis is the operating paradigm.** SOTA now comes from model + retrieval + tools + verifiers, not from monolithic models. Your Skale LangGraph topology, your Lancelot HTTP layer, your eval harness — these ARE the product. The next model release helps you instead of killing you.

12. **For AI products: instrument before you iterate.** Hamel's lesson: build Level 1 unit tests (feature × scenario matrix, CI/CD integrated) before you spend more than a week prompting. You won't improve past the demo without them. The same infrastructure gives you fine-tuning data for free later.
