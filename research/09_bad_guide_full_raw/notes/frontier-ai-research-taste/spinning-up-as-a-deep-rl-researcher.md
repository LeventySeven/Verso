# Spinning Up as a Deep RL Researcher
**Source:** Joshua Achiam (OpenAI), spinningup.openai.com, October 13 2018
**URL:** https://spinningup.openai.com/en/latest/spinningup/spinningup.html
**Status:** read_full
**Themes:** strategy, evals, loop_harness

---

## Full Digest

An OpenAI researcher's curriculum for entering deep RL research. The essay is structured as: (1) required background, (2) learning-by-doing with implementation discipline, (3) developing a research project, (4) rigorous experiment design. The last section contains the most directly applicable material for Verso.

### The Right Background

Prerequisites: probability and statistics (random variables, Bayes' theorem, chain rule, expected values, importance sampling); multivariate calculus (gradients, optionally Taylor series); a general knowledge of deep learning (standard architectures MLP/RNN/LSTM/GRU/conv/resnets/attention; regularization: weight decay, dropout; normalization: batch norm, layer norm, weight norm; optimizers: SGD, momentum SGD, Adam); familiarity with the reparameterization trick; fluency in one DL library (TF or PyTorch).

### Learn by Doing

**The simplicity-first imperative:** "You should organize your efforts so that you implement the simplest algorithms first, and only gradually introduce complexity. If you start off trying to build something with too many moving parts, odds are good that it will break and you'll lose weeks trying to debug it."

**Algorithm sequence:** vanilla policy gradient (REINFORCE) → DQN → A2C → PPO (clipped objective variant) → DDPG. "The simplest versions of all of these can be written in just a few hundred lines of code (ballpark 250-300), and some of them even less (for example, a no-frills version of VPG can be written in about 80 lines)."

**Silent failure is the central hazard:** "Broken RL code almost always fails silently — the code appears to run fine except that the agent never learns how to solve the task. Usually the problem is that something is being calculated with the wrong equation, or on the wrong distribution, or data is being piped into the wrong place. Sometimes the only way to find these bugs is to read the code with a critical eye, know exactly what it should be doing, and find where it deviates from the correct behavior."

**Debug in simple environments first:** "Don't try to run an algorithm in Atari or a complex Humanoid environment if you haven't first verified that it works on the simplest possible toy task. Your ideal experiment turnaround-time at the debug stage is <5 minutes."

**Assume bugs, not hyperparameter problems:** "Spend a lot of effort searching for bugs before you resort to tweaking hyperparameters: usually it's a bug. Bad hyperparameters can significantly degrade RL performance, but if you're using hyperparameters similar to the ones in papers and standard implementations, those will probably not be the issue."

**Measure everything:** "Do a lot of instrumenting to see what's going on under-the-hood. The more stats about the learning process you read out at each iteration, the easier it is to debug — after all, you can't tell it's broken if you can't see that it's breaking." Recommended metrics: mean/std/min/max for cumulative rewards, episode lengths, value function estimates; losses for objectives; exploration parameter details (entropy for stochastic policy, epsilon for DQN).

**Don't overfit to papers OR existing implementations:** Papers often include unnecessary tricks; "some of the best-reported results for DDPG use simpler networks." Implementations add abstraction layers for code reuse that are "unnecessary if you're only writing a single algorithm or supporting a single use case."

### Developing a Research Project

**Three project frames:**

*Frame 1 — Improving on existing approach (incrementalist):* Tied to existing methods, narrow scope, wraps up in months. Risk: tweaks fail and there's no clear signal on what to do next.

*Frame 2 — Focusing on unsolved benchmarks:* Try many methods including new ones invented for the project. Broad scope, several months to year-plus. Risk: the benchmark is unsolvable without a breakthrough, leading to long time without progress. "Even if a project like this fails, it often leads the researcher to many new insights that become fertile soil for the next project."

*Frame 3 — Create a new problem setting:* "Instead of thinking about existing methods or current grand challenges, think of an entirely different conceptual problem that hasn't been studied yet." Standard benchmark doesn't exist yet; you have to design one. "Great benchmarks move the whole field forward."

**Avoid reinventing the wheel:** "Don't just take the results from the best or most interesting runs to use in your paper." Do the most thorough check possible for prior work before committing. "Do good research and finish out your projects with complete and thorough investigations, because that's what counts, and by far what matters most in the long run."

### Doing Rigorous Research in RL

This section is Achiam's most load-bearing content:

**Set up fair comparisons:** "If you implement your baseline from scratch... it's important to spend as much time tuning your baseline as you spend tuning your own algorithm. This will make sure that comparisons are fair." Key constraint: "hold 'all else equal' even if there are substantial differences between your algorithm and the baseline." Example: if investigating architecture variants, keep parameter counts approximately equal. "Under no circumstances handicap the baseline!"

**Multiple random seeds are non-negotiable:** "Run everything for many random seeds (at least 3, but if you want to be thorough, do 10 or more). This is really important and deserves a lot of emphasis: deep RL seems fairly brittle with respect to random seed in a lot of common use cases. There's potentially enough variance that two different groups of random seeds can yield learning curves with differences so significant that they look like they don't come from the same distribution at all."

**Pre-commit to final runs:** "Don't just take the results from the best or most interesting runs to use in your paper. Instead, launch new, final experiments — for all of the methods that you intend to compare — and precommit to report on whatever comes out of that." This is "a weak form of preregistration: you use the tuning stage to come up with your hypotheses, and you use the final runs to come up with your conclusions."

**Ablation analysis is mandatory:** "Any method you propose is likely to have several key design decisions... each of which could separately impact performance. The claim you'll make is that those design decisions collectively help, but this is really a bundle of several claims in disguise: one for each such design element. By systematically evaluating what would happen if you were to swap them out with alternate design choices, or remove them entirely, you can figure out how to correctly attribute credit."

---

## VERSO RELEVANCE

### Finding 1: "Broken agent code almost always fails silently" — this is the primary case for evals [SHARPENS §5.5]

Achiam's central warning maps perfectly to agent frameworks: "Broken RL code almost always fails silently — the code appears to run fine except that the agent never learns how to solve the task." Agent bugs are structurally identical: the agent runs, produces output, doesn't crash — but the output is wrong in subtle ways (hallucinated tool names, context-window contamination, wrong dispatch branch taken, observation masked incorrectly). This is not just an RL concern. This is THE argument for Verso's eval infrastructure as a first-class product primitive. The agent runs, it looks fine. You need structured evals to see it's broken.

**Verdict: adopt-now.** This quote is the single best justification for why agent evals can't be an afterthought. Use it directly in §5.5 motivation text and in GTM messaging.

### Finding 2: Multi-seed rigor → multi-run evals with statistical baseline [SHARPENS §5.5]

Achiam's multi-seed requirement ("at least 3, but 10 or more to be thorough; there's potentially enough variance that two groups of random seeds yield results that look like they don't come from the same distribution") applies directly to Verso's `define_outcome(bounded)` eval design. A single eval run of an agent is as meaningless as a single RL run. Verso's eval harness must default to multi-run aggregation, and the `define_outcome` interface should surface statistical summary (mean/std/min/max) not just pass/fail.

**Verdict: adopt-now.** The current known design (judge-panel evals, define_outcome) is good but incomplete without multi-run aggregation defaults. This is a gap.

### Finding 3: Pre-commit to final runs = the pre-registered eval set [NEW-IDEA §5.5]

Achiam's "launch new, final experiments and precommit to report on whatever comes out" is a concrete methodological primitive Verso can expose to users: a *locked eval set*. During development you tune against one eval split; your "release confidence" comes from a pre-committed holdout set you run once before shipping. This is not just advice — it's an interface design: Verso evals should have a concept of "development evals" vs "pre-committed release evals" that the harness tracks separately. The latter cannot be re-run selectively; you see all results.

**Verdict: adopt-now.** This is a concrete interface primitive for §5.5 that has not been captured previously. Eval sets should be typed as `EvalMode.DEV` or `EvalMode.PRECOMMIT` with the harness enforcing that precommit evals are run in full and not cherry-picked.

### Finding 4: The 80-line VPG = validation of the <200-line loop invariant [CONFIRMS §5.1]

Achiam explicitly states: "a no-frills version of VPG can be written in about 80 lines." VPG (vanilla policy gradient/REINFORCE) is the structural equivalent of a ReAct loop: the minimal correct thing. The fact that the leading open-source RL curriculum says the simplest correct implementation is ~80 lines validates Verso's <200-line loop target. More importantly, Achiam notes that going beyond this length too early causes silent failure and weeks of lost debugging time — same pathology Verso avoids by keeping the loop short.

**Verdict: confirm.**

### Finding 5: Ablation analysis = primitive-level contribution attribution [SHARPENS §5.5]

"Any method you propose is likely to have several key design decisions... the claim you'll make is that those design decisions collectively help, but this is really a bundle of several claims in disguise." Verso's context-engineering primitives (ContextBundle, KV-cache prefix discipline, observation masking/compaction) each need their own ablation. The harness should make it easy to run an agent with and without each primitive to demonstrate that each earns its place. This is exactly the "every primitive must earn its place" invariant operationalized as an eval type.

**Verdict: adopt-now.** The eval harness should include an `AblationSuite` concept: run the agent with each feature toggled off individually, measure outcome distribution change, confirm each primitive's contribution is statistically distinguishable.

### Finding 6: "Don't overfit to implementation abstractions" — warns against framework bloat [CONFIRMS §2]

Achiam's warning: "RL libraries frequently make choices for abstraction that are good for code reuse between algorithms, but which are unnecessary if you're only writing a single algorithm or supporting a single use case." This is the non-goal statement for Verso's loop: every abstraction in the loop that exists for code-reuse-between-agent-types (not for correctness of the single ReAct pattern) should be removed. The loop serves one pattern. Abstractions that serve multiple patterns belong in the harness, not the loop.

**Verdict: confirm.** Use this framing explicitly in §5.1 to justify removing any shared base classes or pluggable loop backends.

### Finding 7: "Frame 3 — Create a new problem setting" = Verso's eval benchmark play [NEW-IDEA §5.5]

Achiam notes that Frame 3 projects (creating new problem settings + benchmarks) have the highest impact: "great benchmarks move the whole field forward." Verso's opportunity is not just to build a framework — it's to define the canonical agent eval benchmark that the field converges on. No one owns this yet (AgentBench, GAIA, etc. are not standard). The Verso eval primitives (`define_outcome(bounded)`, judge-panel, pre-committed runs) position the project to ship *the* reference benchmark suite for ReAct agents. This is a GTM play: if Verso ships the benchmark, it becomes the reference implementation.

**Verdict: adopt-now.** §12 GTM should include a benchmark publication goal alongside the framework release. Winning the benchmark framing is structurally more durable than winning on feature count.
