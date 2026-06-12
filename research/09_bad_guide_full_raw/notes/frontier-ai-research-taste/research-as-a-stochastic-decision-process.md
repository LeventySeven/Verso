# Research as a Stochastic Decision Process
**Source:** Jacob Steinhardt (Stanford), cs.stanford.edu, undated essay
**URL:** https://cs.stanford.edu/~jsteinhardt/ResearchasaStochasticDecisionProcess.html
**Status:** read_full
**Themes:** strategy, evals, loop_harness

---

## Full Digest

Steinhardt opens with a strong prior: "Before implementing this approach, I made little research progress for over a year; afterwards, I completed one project every four months on average... I expect the ideas here to at least double your productivity if you aren't already employing a similar process."

### The Naive Strategy and Why It Fails

The default — "complete components in increasing order of difficulty, from easiest to hardest" — has a systematic failure mode: "I would do all the easy parts, then get to the hard part and encounter a fundamental obstacle that required scrapping the entire plan." The wasted work is not recoverable because "it wasn't that I could replace the hard part with a different hard part; rather, I needed to re-think the entire structure."

### The Correct Heuristic: Informativeness Per Unit Time

**Better Strategy:** "Do the components in order from most informative per unit time to least informative per unit time."

This unifies two factors: (1) tasks more likely to fail should be prioritized (remove risk early), AND (2) shorter tasks should be prioritized (waste less time if they fail). These two pull in different directions, so Steinhardt gives two formal methods.

**Method 1 — Expected Time Saved:**
If task A has 90% success and takes 30 min, and task B has 40% success and takes 4 hours:
- Doing A first: if it fails, save 240 min → expected savings = 0.1 × 240 = 24 min
- Doing B first: if it fails, save 30 min → expected savings = 0.6 × 30 = 18 min
→ Do A first.

But if B takes 2 hours instead: savings for B-first = 0.6 × 30 = 18 min vs A-first = 0.1 × 120 = 12 min → do B first. The answer flips with the exact numbers.

**Method 2 — Failure Rate (Poisson Model):**
Model failures as a Poisson process: λ = -log(p_success) / t

This gives a sortable rate independent of arbitrary counting conventions. For the same example:
- Task A: λ = -log(0.9) / 0.5 ≈ 0.211
- Task B: λ = -log(0.4) / 4 ≈ 0.229
→ Under the Poisson model, B should go first (slightly) — reversal from Method 1.

Steinhardt notes: "both of these assumptions are likely somewhat incorrect in practice" and recommends calibrating with subjective buckets:
- "I am confident this can be done and there are no unforeseen difficulties" (~95%)
- "I am confident modulo Murphy's law" (~90%)
- "I see the basic path and all steps seem like they should work" (~65%)
- "I have the intuition this should be possible but only have a murky view of the path" (~30%)

Time estimation calibration: "~30% average relative error, albeit with large tails." Improves within weeks by recording actual vs estimated in a daily log.

### De-Risking: Opening the Task Black Box

The key upgrade: rather than sorting tasks and executing each atomically, find *cheap ways to get high confidence about feasibility before full execution*. This is "de-risking."

**Basic Pattern:** "De-risk all components (to the extent feasible), then execute."

Example: to set up a large dataset and train a model, first download a few thousand examples, examine by hand, compute aggregate statistics. This collapses weeks of uncertainty into hours of signal.

For empirical work: build "ceiling" prototypes that cheat on the hard component (use test labels, use oracle information) to determine whether the overall system architecture can succeed at all before implementing the hard part.

For theoretical work: "looking for counterexamples is useful." If you find a counterexample to the main result, you need to give up or make stronger assumptions — early and cheap.

### The Stochastic Decision Process Model

Steinhardt unifies everything: "we think of research as a multi-round game, where in each round we take some action that gives us some information; the information we get is stochastic, as well as perhaps the time needed to complete the action." Two competing goals: maximize probability of eventual success AND minimize expected time spent.

Two modes: *de-risking mode* (determine infeasibility fast) and *execution mode* (solve quickly given feasibility assumed).

**Tooling aside:** "Such 'tooling' tasks are tricky to model, because it seems we should implement tooling as soon as we know we will eventually want it (since it speeds up things that come after it). However, this ignores that more experience often yields refined desiderata for the tools we implement."

### Branching Search Trees

Research = exponentially branching search: "we could try X, X', or X''. Then X could be combined with Y, Y', Y'', or X' could be combined with Z or Z'... 10 ways to attempt each step across 3 steps = 1000 possibilities."

The key insight: "it's much more useful to prune branches of the search tree at the level of *conceptual approaches* than at the level of a specific instantiation." You want to rule out entire families, not just specific implementations.

**Three anti-patterns Steinhardt diagnoses:**
1. "Trying an experiment and seeing it fail gives little information by itself." An implementation is only 0.1% of the possibility space for a conceptual approach.
2. "I am far less in favor than most people of publishing negative results, unless the negative result comes with insight into what caused the failure." (Strong claim — implies negative signal has to be structural, not merely observational.)
3. "Compared to other people I know, I try harder and earlier to show that my ideas *can't* work to solve a problem." This enables trying low-probability ideas because you exit cheaply when they fail.

**Ruling out ideas requires a high bar:** "This doesn't seem like it will work" or "I feel less motivated" are NOT ruling out an idea. Only a solid argument for why the approach is fundamentally doomed qualifies.

### Practical Patterns Summary

- **Ceilings:** Prototype with oracle/cheating version to bound max achievable performance before implementing hard component
- **Baselines:** Off-the-shelf lower bounds; sanity checks that complex methods don't underperform simple ones
- **Brute force first:** If easy-to-implement brute force exists, use it first; facilitates debugging the fast solution by comparing outputs
- **Counterexamples:** For theory, look for failures of your assumptions before formalizing the proof
- **Simplified instances:** Lower-dimensional/restricted versions of the problem provide intuition about which approaches are viable
- **Simulations:** Run simulations to verify claims *before* proving them (especially useful for asymptotic behavior)

---

## VERSO RELEVANCE

### Finding 1: De-risking = define_outcome(bounded) before the eval harness [SHARPENS §5.5]

Steinhardt's core move — "de-risk all components to the extent feasible, then execute" — is the precise algorithm for Verso's eval design process. When building a new agent primitive (a new context-engineering API, a new durable checkpoint mechanism), the right order is NOT "implement it fully, then write tests." It's: (1) write a cheap "ceiling" implementation that cheats on the hard part to see if the concept is sound; (2) define the outcome metric first (the `define_outcome(bounded)` interface); (3) then build the real implementation. The Poisson sorting gives the principle: *failure rate per unit time* is what determines which assumption to test first.

**Verdict: adopt-now.** This is directly operational for the Verso dev process itself — use it when ordering the implementation of primitives in the durable runtime (§6.1).

### Finding 2: "Most informative per unit time" is the principle behind tiered model routing [SHARPENS §6.4]

Steinhardt's sorting criterion — maximize failure detection per unit time — maps directly to Verso's role-tiered model architecture (cheap loop / mid retry / reasoning synthesis). The cheap model runs first not because it's "good enough" but because it has the *highest failure-rate-per-cost*: if the task is trivially doable, it completes cheaply; if not, you learn that fast and escalate. This is the stochastic-decision-process frame applied to model selection. Previously this was justified as cost efficiency; the better frame is *information efficiency per dollar*.

**Verdict: sharpen.** Reframe role-tiered models in §6.4 not just as cost optimization but as the stochastic-decision-process applied to inference: run the model that maximizes information gained about task feasibility per token spent.

### Finding 3: Branching search trees explain why the loop stays <200 lines [CONFIRMS §5.1]

Steinhardt's point about conceptual vs. implementation pruning directly explains the loop-length invariant. A loop that handles 10 conceptual cases (graphs, state machines, event sourcing, tool routing, streaming, etc.) is the 1000-possibility space. A loop that handles ONE conceptual case (ReAct: observe, act, repeat) and delegates everything else to the harness is the 10-possibility space. The hard constraint on loop length is not aesthetic — it's a search-tree pruning decision. Adding complexity to the loop is equivalent to failing to prune at the conceptual level.

**Verdict: confirm.**

### Finding 4: "Tooling too early → refined desiderata emerge later" is a warning for MCP adapter timing [SHARPENS §5.3]

Steinhardt's tooling aside: "implement tooling as soon as we know we will eventually want it (since it speeds up future work). However, more experience yields refined desiderata." This is a warning about shipping the MCP adapter too early. The risk: build a full MCP integration framework before real users have shown what MCP adapter patterns actually matter, then discover the interface needs to be redesigned. The counter-position is to keep MCP as a "demoted opt-in adapter" — which is correct under this framework because it defers full tooling investment until desiderata are known.

**Verdict: lock-interface-defer.** Do not invest heavily in the MCP adapter surface area until there is concrete signal from users about which patterns recur.

### Finding 5: Ceiling prototypes → the FakeModel pattern [CONFIRMS §5.5]

Steinhardt's "ceiling" prototype pattern (cheat on the hard component to test if the system architecture works at all) is exactly what Verso's `FakeModel` is. The `FakeModel.stream` enables running the entire loop harness, eval harness, and SSE transport code against a trivial model stub before you have a real model call working. This confirms the FakeModel is not just a test convenience — it's the principled ceiling prototype for the agent infrastructure.

**Verdict: confirm.** Consider naming this pattern explicitly in Verso docs as "ceiling prototype mode."

### Finding 6: Negative results require structural insight — not observational [NEW-IDEA §5.5]

Steinhardt's strong claim: "I am far less in favor than most people of publishing negative results, unless the negative result comes with insight into what caused the failure." For Verso evals, this has a direct implication: a failed agent run that returns `StopReason.MAX_TURNS` is NOT useful eval signal by itself. The eval harness needs to capture *why* the agent stopped — what type of failure occurred (context overflow? tool error? model confusion? hallucinated tool name?). The `define_outcome(bounded)` approach must include failure-mode classification, not just pass/fail.

**Verdict: adopt-now.** §5.5 should specify that judge-panel evals must classify failure modes structurally, not just report binary outcomes. A failed run with unknown failure mode is nearly useless for improving the system.
