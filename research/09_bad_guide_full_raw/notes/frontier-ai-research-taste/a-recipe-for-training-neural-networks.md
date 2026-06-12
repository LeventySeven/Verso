# A Recipe for Training Neural Networks — Andrej Karpathy (2019)

**URL:** http://karpathy.github.io/2019/04/25/recipe/
**Author:** Andrej Karpathy
**Published:** April 25, 2019
**Format:** Long-form blog post
**Status:** read_full

---

## Source Digest

Karpathy describes a six-stage recipe for training neural networks, grounded in two foundational observations: (1) neural net training is a leaky abstraction — you cannot treat it as plug-and-play; (2) neural nets fail *silently* — code can be syntactically correct while being fundamentally misconfigured, with no exception thrown. The recipe is a process of building trust incrementally, verifying each step before adding complexity.

> "A 'fast and furious' approach to training neural networks does not work."

The philosophical model: a good neural network engineer operates like a scientist forming one hypothesis per step, going from simple to complex, never trusting a result they can't explain.

---

### The Two Foundational Observations

**Observation 1: Neural nets are leaky abstractions**

Unlike standard software libraries (Requests, etc.), neural networks cannot be used as "black boxes." Technologies like batch normalization and RNNs don't automatically solve problems — understanding implementation details is essential. Deviating from standard tasks requires deep understanding of what is happening inside.

**Observation 2: Neural nets fail silently**

The error surface is large, logical, and difficult to unit test. Examples of subtle silent bugs:
- Forgotten data augmentation flips
- Off-by-one errors
- Gradient clipping mistakes
- Incorrect pretrained checkpoint usage

A model can appear to train (loss decreasing) while being fundamentally broken. The only defense is building in verification steps before adding complexity.

---

### Stage 1: Become One With the Data

Primary goal: understand your dataset thoroughly before writing any model code.

**Specific actions:**
- Spend hours examining thousands of examples manually
- Identify distribution patterns and anomalies
- Look for duplicates and corrupted data
- Note data imbalances and biases
- Observe your own labeling process (hints at architecture needs)
- Determine what features are locally vs. globally sufficient
- Assess label noise levels
- Write code to search, filter, and sort by various attributes
- Visualize distributions and especially outliers along multiple axes

**Key insight:** Your network's mispredictions should align with patterns you found in the data during this stage. If the model fails in unexpected ways, it means you missed something in the data exploration.

**Verso parallel:** The agent equivalent of "become one with the data" is spending time in the trace viewer before writing any prompt or tool logic. Know what the agent is actually doing before you change anything.

---

### Stage 2: Set Up End-to-End Pipeline + Establish Baselines

Primary goal: build a complete training/evaluation skeleton with a *simple* model, establishing trustworthy metrics.

**The verification checklist (the most detailed and replicable part of the recipe):**

| Check | What it Verifies |
|---|---|
| Fix random seed | Reproducibility |
| Simplify (disable augmentation etc.) | Remove confounds |
| Add significant digits to eval | Test on entire test set, not batch smoothing |
| Verify loss @ init | Confirm `loss = -log(1/n_classes)` for softmax |
| Init well | Bias final layer toward dataset statistics |
| Human baseline | Establish ceiling; double-annotate test data |
| Input-independent baseline | Zero-out inputs; verify model learns from data, not noise |
| Overfit one batch | Confirm the model CAN memorize 2–3 examples (zero loss) |
| Verify decreasing training loss | Increase capacity slightly; confirm loss decreases |
| Visualize just before the net | Decode raw tensor input to verifiable form |
| Visualize prediction dynamics | Watch fixed test batch predictions evolve during training |
| Use backprop to chart dependencies | Verify gradient isolation to specific examples |
| Generalize a special case | Write specific working code first, then generalize |

The most important of these for Verso: **overfit one batch** (can the system even solve a trivial version of the problem?), **input-independent baseline** (is the system actually using the input?), and **verify loss @ init** (are the initial conditions sane?).

**Verso parallels:**
- "Overfit one batch" → run the agent on a trivially easy case with a known answer; if it can't pass that, nothing else matters.
- "Input-independent baseline" → run the agent with zeroed/redacted input; if it performs as well, it's not using the context it was given.
- "Verify loss @ init" → for Verso's evals: does the untrained/unoptimized agent perform at chance? If it performs above chance on day one, something is wrong with the test cases.

**The generalize-a-special-case principle:**
> "Write specific working code first, then generalize while verifying equivalence."

This is the procedural operationalization of "start simple." Write the dumbest thing that solves the specific case. Verify it works. Then generalize. Never generalize first.

---

### Stage 3: Overfit

Primary goal: find a model large enough to achieve low training loss, confirming the architecture can fit the data at all.

**Two-stage philosophy:** First maximize training performance (overfit). Then regularize. Do NOT attempt both simultaneously.

**Model selection:**
> "Don't be a hero — copy architectures from related papers rather than inventing custom ones."

Start with ResNet-50 for images, proven approaches for your domain. Custom architectures come later, after you have a working baseline.

**Optimizer choice:**
> "Adam is safe — use Adam with learning rate of 3e-4 for initial baselines."

Adam is more forgiving to hyperparameter choices than SGD. SGD can outperform Adam when well-tuned but requires narrower optimal learning rate ranges. The advice: use Adam to establish baselines, switch to SGD only after you have a baseline to compare against.

**Complexity management:**
> "Complexify only one at a time."

Add one signal, one feature, one improvement per iteration. If using multiple data sources, integrate them one at a time with expected performance verification.

**Learning rate decay:**
> "Do not trust learning rate decay defaults — decay schedules are often problem-specific. Disable automatic learning rate decay during early stages."

This is a concrete warning against framework defaults. The default decay schedule was tuned for someone else's problem. Disable it early; tune it last.

---

### Stage 4: Regularize

Primary goal: improve validation performance by reducing overfitting while accepting some training loss.

**Ranked recommendations (most effective first):**

1. **Get more data** — most reliable regularization; adding real data almost always helps monotonically. Often more valuable than all engineering optimizations on limited data.
2. **Ensembles** — "pretty much guaranteed" 2% improvement; diminishing returns after ~5 models.
3. **Data augmentation** — apply more aggressive augmentation.
4. **Creative augmentation** — domain randomization, simulation, hybrid synthetic-real, GANs.
5. **Pretrain** — leverage pretrained networks even with sufficient data; "rarely hurts."
6. **Stick with supervised learning** — avoid unsupervised pretraining for computer vision (NLP differs with BERT-style methods).
7. **Smaller input dimensionality** — remove spurious features.
8. **Smaller model size** — use domain knowledge to constrain architecture.
9. **Decrease batch size** — smaller batches provide regularization via batch normalization approximation effects.
10. **Dropout** — apply sparingly (poor interaction with batch normalization for ConvNets).
11. **Weight decay** — increase L2 regularization penalty.
12. **Early stopping**.

**Counter-intuitive:**
> "Try a larger model — paradoxically, larger models stopped early sometimes outperform smaller ones."

**Confidence check:** Visualize first-layer weights — they should show recognizable edges/patterns, not noise. If they look like noise, something is fundamentally wrong with the training.

---

### Stage 5: Tune

Primary goal: explore architecture and hyperparameter space to maximize validation performance.

> "Random over grid search — use random search instead of grid search for multiple hyperparameters."

Rationale: neural networks have varying sensitivity to different parameters; random search samples sensitive parameters more thoroughly (Bergstra & Bengio 2012). The "state of the art approach" is, humorously, "to use an intern."

---

### Stage 6: Squeeze Out the Juice

**Ensembles:** "pretty much guaranteed" 2% improvement. If ensemble inference is too expensive, distill the ensemble knowledge into a single network.

**Leave it training:**
> "Don't stop when validation loss plateaus; networks continue improving for surprisingly long periods."

Karpathy's anecdote: a model left running over winter break achieved SOTA upon return in January. The plateau is not the end.

---

### Overarching Themes

1. **One hypothesis per step.** Never test two changes simultaneously.
2. **Simple to complex.** Never add complexity without first validating the simpler version works.
3. **Distrust your results until you can explain them.** A surprising result is usually a bug, not a discovery.
4. **Paranoia as a virtue.** The bug is always there; you just haven't found it yet.
5. **Visualization as verification.** You cannot trust what you cannot see.

---

## Selected Verbatim Quotes (Load-Bearing)

1. "A 'fast and furious' approach to training neural networks does not work."
2. "Neural net training fails silently — syntactically correct code can be fundamentally misconfigured."
3. "Don't be a hero — copy architectures from related papers rather than inventing custom ones."
4. "Adam is safe — use Adam with learning rate of 3e-4 for initial baselines."
5. "Complexify only one at a time."
6. "Do not trust learning rate decay defaults — decay schedules are often problem-specific."
7. "Random over grid search."
8. "Don't stop when validation loss plateaus; networks continue improving for surprisingly long periods."
9. "Write specific working code first, then generalize while verifying equivalence."
10. "Your network's mispredictions should align with patterns observed in the data; inconsistencies indicate problems."

---

## VERSO RELEVANCE

### Finding 1: Silent failure as the design environment — verification must be built in
**Tag:** [SHARPENS §5.5 evals / §5.1 loop]
> "Neural nets fail silently — syntactically correct code can be fundamentally misconfigured."

The agent equivalent is identical: an agent can "run" — produce output, call tools, return a result — while being fundamentally broken (wrong tool called, context ignored, wrong reasoning path taken). Traditional software raises exceptions on failure; agents produce plausible-looking wrong answers. This SHARPENS the Verso evals rationale: evals are not optional quality hygiene, they are the *only* mechanism that detects silent agent failures. The §5.5 harness spec should explicitly name this analogy: agent output is a leaky abstraction, just like neural net training.
**Verdict:** sharpen — add "silent failure" as the first design motivation in §5.5; the verifier is how you detect the undetectable.

### Finding 2: The verification checklist as a model for Verso's agent bootstrapping
**Tag:** [NEW-IDEA §5.5 evals]
Karpathy's Stage 2 verification checklist (12 specific checks before touching model complexity) is the precise model for a Verso "agent bootstrapping checklist" — a set of sanity checks to run before trusting an agent for production use:
- **Overfit one batch** → "Can the agent solve a trivial version of the task with a known answer?"
- **Input-independent baseline** → "Does the agent's output change when you redact its context? If not, it's not using context."
- **Verify loss @ init** → "Does the untrained/default agent perform at random chance? If it performs above chance, the eval test cases may be too easy (Hamel's 'model struggles to pass' signal)."
- **Visualize just before the net** → "What exactly is the agent receiving in its context window? Can you inspect the exact prompt?"
- **Backprop to chart dependencies** → "Which parts of the context actually affected the output?" (attention/influence analysis)

This is a concrete protocol Verso could ship as a getting-started guide or `verso agent inspect` CLI flow.
**Verdict:** adopt-now — draft a Verso "agent sanity checklist" modeled on Karpathy's Stage 2 for §5.5 getting-started docs. Six of the twelve checks map directly.

### Finding 3: Complexify one at a time as a HARD RULE for agent development
**Tag:** [SHARPENS §5.5 evals / §4 the seam/architecture]
> "Complexify only one at a time."

This is stronger than "go simple to complex" — it is a rule about the *rate* of change. In agent development: add one tool, one memory tier, one prompt change, or one routing rule per iteration. Never combine changes. This is the agent equivalent of the neural net recipe rule. Verso's harness should structurally enforce this by making each configuration option independently togglable and testable. The design implication: every feature in the harness must be individually disableable (so you can isolate its effect).
**Verdict:** sharpen — add "independently disableable" as a design requirement for every §5.x feature in Verso's harness. Each component must be A/B-testable in isolation.

### Finding 4: Do not trust framework defaults — the learning rate decay warning
**Tag:** [SHARPENS §5.3 tools / §6.4 model/provider]
> "Do not trust learning rate decay defaults — decay schedules are often problem-specific."

The Verso equivalent: do not trust provider defaults. Default model parameters (temperature, max tokens, retry behavior, timeout) are tuned for a generic use case, not your agent. Verso's §6.4 model/provider layer should expose these explicitly and make them overridable per-call, not just at initialization. The recipe warns: defaults that worked in training may not work in your context. The same applies to retry logic, token budgets, and sampling parameters.
**Verdict:** sharpen — add "no implicit provider defaults" to §6.4 design principles; all parameters should be explicitly named and overridable.

### Finding 5: The "don't be a hero" architecture principle maps to "don't force the graph"
**Tag:** [CONFIRMS §2 non-goals]
> "Don't be a hero — copy architectures from related papers rather than inventing custom ones."

The Verso equivalent is "don't force the graph." Both are warnings against premature architectural sophistication. Just as a new neural network practitioner should start with ResNet-50 (not a custom architecture), a new agent developer should start with a ReAct loop (not a custom graph). The custom architecture/graph is for after you have a working baseline. CONFIRMS Verso's non-goal of "no forced graph."
**Verdict:** confirm — use as external precedent in §2 non-goals language: "start with the proven baseline; add complexity only when you can explain why the baseline fails."

### Finding 6: Simple-to-complex sequence maps onto Verso's tactical/durable seam
**Tag:** [CONFIRMS §4 the seam/architecture]
Karpathy's recipe is explicitly a staging sequence: establish baseline → overfit → regularize → tune → squeeze. You don't start at "tune." Verso's tactical/durable seam is the same principle applied to agent development: start tactical (default, ephemeral), promote to durable only when you understand the tactical version. Forcing durability from day one is starting at "tune" before you've run the baseline.
**Verdict:** confirm — use Karpathy's recipe structure as the organizing narrative for the §4 seam design: tactical is Stage 1, durable promotion is Stage 4+.

### Finding 7: Visualization as the verification mechanism — Verso's trace viewer design
**Tag:** [SHARPENS §5.5 evals]
Karpathy returns to visualization repeatedly: "visualize just before the net," "visualize prediction dynamics," "visualize first-layer weights." The pattern is: you cannot trust what you cannot see. For Verso: the trace viewer must show what the agent received (exact context window content), what it did (tool calls, intermediate steps), and how its behavior evolved over iterations. "Visualize just before the net" = inspect the exact context bundle the agent received. This SHARPENS the trace viewer design requirement from Hamel (Finding 3 in the evals note): it must show raw inputs, not just cleaned-up outputs.
**Verdict:** sharpen — add "raw context window inspector" as a required component of Verso's trace viewer in §5.5; agents fail silently, and the bug is usually in what they were given, not what they did with it.

### Finding 8: "Leave it training" → the patience principle for agent iteration
**Tag:** [NEW-IDEA §5.5 evals / §12 positioning/GTM]
> "Don't stop when validation loss plateaus; networks continue improving for surprisingly long periods."

The agent equivalent: don't abandon an approach because the first few evals don't show improvement. Agent quality often improves non-monotonically — a prompting change that looks neutral at N=10 may show clear signal at N=50. Verso's eval harness should make it easy to accumulate evidence over time (persistent eval database, trend visualization) rather than treating each eval run as a one-off pass/fail. This also reinforces the "you can never stop looking at data" principle from Hamel.
**Verdict:** adopt-now — add persistent eval history tracking to §5.5; display trend over time, not just point-in-time results.

---

## Summary Verdict

Karpathy's recipe maps directly onto agent development with minimal translation. The highest-value findings are: (1) silent failure as the primary design constraint for §5.5, (2) the Stage 2 verification checklist as a Verso agent bootstrapping protocol, (3) "complexify one at a time" as a hard rule that requires every harness feature to be independently toggleable, and (4) visualization as a non-negotiable requirement for the trace viewer. The "don't be a hero" principle CONFIRMS the "no graph" invariant with strong external precedent. The recipe's staging structure (baseline → overfit → regularize → tune) maps cleanly onto the tactical/durable seam: tactical is the baseline stage; durable is what you add after understanding the baseline.
