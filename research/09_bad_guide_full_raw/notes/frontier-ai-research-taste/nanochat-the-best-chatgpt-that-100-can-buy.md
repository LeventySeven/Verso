# nanochat: The Best ChatGPT That $100 Can Buy — Andrej Karpathy (2025)

**URL:** https://github.com/karpathy/nanochat
**Author:** Andrej Karpathy
**Format:** GitHub repository (Python, ~8k LOC) + README + guides
**Status:** read_full (README + key source files fetched: engine.py, chat_eval.py, tasks/common.py)

---

## Source Digest

nanochat is Karpathy's "simplest experimental harness for training LLMs" — a full end-to-end pipeline from tokenization through pretraining, SFT, RL (GRPO), evaluation, and a chat web UI. All in one minimal Python codebase. It extends nanoGPT (which only covered pretraining) by adding the full post-training stack. The design philosophy is radical simplicity and hackability.

### The Core Design Claim

> "nanochat is not an exhaustively configurable LLM 'framework'; there are no giant configuration objects, model factories, or if-then-else monsters in the code base. It is a single, cohesive, minimal, readable, hackable, maximally-forkable 'strong baseline' codebase designed to run start to end and produce a ChatGPT model you can talk to."

This is the clearest possible statement of the "simplest thing that works" design philosophy applied to an ML training harness. The constraint is identical to Verso's: no framework abstraction layer, no configuration monsters, minimal surface area.

### The Single Complexity Dial Pattern

> "nanochat is written and configured around one single dial of complexity — the depth of the transformer. This single integer automatically determines all other hyperparameters (the width of the transformer, number of heads, learning rate adjustments, training horizons, weight decays, ...) so that the trained model comes out compute optimal."

One `--depth` parameter determines everything. All other hyperparameters are derived. The user doesn't configure; they express intent at the right level of abstraction and the system makes the correct choices.

**Verso parallel:** this is the design ideal for Verso's tactical/durable seam. The user expresses "I want this agent to be durable" (one flag/annotation), and all the checkpoint-resume, event-sourcing, and human-in-the-loop mechanics are derived automatically. The user should not configure individual pieces; they should set the intent.

### Training Pipeline Stages (Full Stack)

nanochat covers:
1. BPE tokenizer (GPT-4 style)
2. Pretraining on FineWeb (distributed, multi-GPU)
3. Mid-training
4. Supervised Fine-Tuning (SFT)
5. Reinforcement Learning with GRPO
6. Eval harness (6 benchmarks)
7. KV-cache inference engine
8. Chat web UI

The complete pipeline is in `runs/speedrun.sh` — one shell script that trains GPT-2 grade capability for ~$48 (2 hours on 8×H100). The fact that the entire pipeline fits in one readable script is the point.

### The Leaderboard / Speedrun Structure

> "The current leaderboard [shows 1.80 hours to beat GPT-2, down from 168 hours in 2019]"

| # | Time | CORE | Date |
|---|---|---|---|
| 0 | 168h | 0.2565 | 2019 (OpenAI) |
| 1 | 3.04h | 0.2585 | Jan 2026 |
| 6 | 1.65h | 0.2626 | Mar 2026 |

A public leaderboard with a single clear metric (DCLM CORE score), a canonical reproduction script, and contributor attribution. The leaderboard gamifies improvement and defines "good" with a number.

**Verso parallel:** evals need a single clear "north star" metric per use case, and that metric should be publicly trackable. The nanochat leaderboard is the eval harness made visible. The DCLM CORE score is the nanochat equivalent of Verso's `define_outcome(bounded)`.

### Key Source File: engine.py (KV-Cache Inference)

The engine implements Flash Attention 3 KV-cache API with shape `(B, T, H, D)`. Key design features:

1. **Single-pass prompt prefill + KV cache replication** for batched multi-sample generation
2. **Per-row state machines** for forced token injection (tool use coordination)
3. **Tool use via special token detection** — detects Python code blocks via special tokens; sandboxed evaluation via `use_calculator()`
4. **Streaming and batch APIs:** both `generate()` (streaming) and `generate_batch()` (batch)
5. **Validation test inline** — a test comparing against reference model output is part of the engine file itself

**Special token protocol for tool use:**
The engine detects tool calls by watching for special tokens marking Python code blocks. It then evaluates the expression safely (timeout 3s, expression validation against dangerous patterns, sandboxed environment). This is a clean, minimal tool-use integration that does not require a separate tool-dispatch framework.

**Critical insight for Verso:** nanochat integrates tool use at the token/generation level, not as a separate framework layer. The "tool" is just a token pattern + a Python eval. This is the purest form of native Python as the tool path — there is no tool registry, no schema, no routing logic. The function IS the tool.

### Key Source File: chat_eval.py (Eval Harness)

The eval harness supports two evaluation modes:

1. **Generative:** open-ended generation evaluated by checking if any sampled completion matches correct criteria (HumanEval, GSM8K)
2. **Categorical:** multiple-choice evaluated by examining logits *only for valid answer choices* (ARC, MMLU) — this is much more efficient than generating full responses

**Distributed processing:** Uses PyTorch DDP to parallelize eval across multiple GPUs.

**Baseline-adjusted scoring:** Implements "ChatCORE metric" that centers accuracies around random baseline performance — not raw accuracy, but accuracy above chance.

**Key design:** The eval harness is plugged into the same pipeline as training. It runs on the same infrastructure, logs to the same reporting system, and produces metrics that appear in the same leaderboard tracker. There is no separate "eval environment" — eval is a mode of the training infrastructure.

### Key Source File: tasks/common.py (TaskMixture)

TaskMixture combines multiple tasks with deterministic shuffling (fixed random seed) so "tasks are mixed throughout training, regardless of dataset size." TaskSequence provides sequential curriculum ordering. The base Task class enforces: evaluation type, example count, retrieval, and evaluation logic.

The `render_mc()` utility encodes tokenization-level insights: smaller models perform better when "the letter *after* the choice" appears, not the letter before. This is the kind of implementation detail that only appears in readable codebases where someone was close to the run.

### Precision Management: Explicit Over Autocast

> "nanochat does not use `torch.amp.autocast`. Instead, precision is managed explicitly through a single global `COMPUTE_DTYPE`."

Model weights stored in fp32 for optimizer precision; custom Linear layer casts to COMPUTE_DTYPE during forward pass; embeddings stored directly in COMPUTE_DTYPE. This gives "the same mixed-precision benefit as autocast but with full explicit control."

**Verso parallel:** explicit > autocast. Explicit control surfaces over magic defaults. The Verso equivalent is the named StopReason enum, typed RunContext injection, and the {data, error, ok} dispatch — all prefer explicit named structure over magic implicit behavior.

### Contributing Policy

> "Current AI policy: disclosure. When submitting a PR, please declare any parts that had substantial LLM contribution and that you have not written or that you do not fully understand."

The policy is not "no LLM"; it is "disclose LLM and understand what you submit." The quality gate is comprehension, not authorship.

---

## Selected Verbatim Quotes (Load-Bearing)

1. "There are no giant configuration objects, model factories, or if-then-else monsters in the code base."
2. "A single, cohesive, minimal, readable, hackable, maximally-forkable 'strong baseline' codebase."
3. "One single dial of complexity — the depth of the transformer. This single integer automatically determines all other hyperparameters."
4. "The idea is that the user doesn't have to think about or set any of this, they are simply asking for a smaller or bigger model using `--depth`, and everything 'just works'."
5. "Any candidate changes to the repo have to be principled enough that they work for all settings of depth."
6. "nanochat is not an exhaustively configurable LLM 'framework'."
7. "ChatCORE metric that centers accuracies around random baseline performance."
8. "Declare any parts that had substantial LLM contribution and that you have not written or that you do not fully understand."

---

## VERSO RELEVANCE

### Finding 1: The single dial pattern as the design ideal for the tactical/durable seam
**Tag:** [NEW-IDEA §4 the seam/architecture]
nanochat's `--depth` dial is the exact design ideal for Verso's tactical/durable seam. The user should not be setting individual durable-layer options (checkpoint frequency, event-store backend, HITL pause points). They should set `durable=True` (or similar) on the Agent, and all the mechanics derive automatically. nanochat proves this pattern is achievable: a single integer encodes an entire compute-optimal training run. Verso should aim for an equally clean "single dial" for durability.
**Verdict:** adopt-now — strengthen the §4 spec language: the seam is "one flag, not a configuration object." nanochat is the existence proof.

### Finding 2: No framework layer = the "no if-then-else monsters" principle
**Tag:** [CONFIRMS §2 non-goals / §1 the bet]
The nanochat README is the most explicit possible statement of the "no overkill, no bullshit" invariant from a respected builder. "No giant configuration objects, model factories, or if-then-else monsters" is nanochat's version of Verso's "no graph, no overkill." The hard invariants CONFIRM. This should appear in Verso's positioning as external evidence: the best ML training harness in the world is structured the same way.
**Verdict:** confirm — use as external evidence in §1 and §12 that simplicity is the correct competitive choice, not a compromise.

### Finding 3: Baseline-adjusted scoring (ChatCORE) as a model for Verso's bounded evals
**Tag:** [SHARPENS §5.5 evals]
nanochat's "ChatCORE metric centers accuracies around random baseline performance" — not raw accuracy, but accuracy above chance. This sharpens Verso's `define_outcome(bounded)` design. A bounded outcome should report not just raw pass rate but delta-above-baseline. An agent that gets 60% right when random chance gives 50% is very different from an agent that gets 60% right when chance gives 5%. The `define_outcome` API should expose baseline-adjusted scoring as a first-class option.
**Verdict:** sharpen — add baseline-adjusted scoring as a mode in §5.5 `define_outcome`; nanochat's ChatCORE is the model.

### Finding 4: Tool use as token pattern + Python eval, not a framework layer
**Tag:** [CONFIRMS §5.3 tools]
nanochat implements tool use by detecting special tokens in the generation stream and evaluating the resulting Python expression with sandboxing. There is no tool registry, no schema, no routing framework. The function IS the tool. This CONFIRMS Verso's invariant that "native Python @tool is THE tool path." nanochat shows this works in a minimal, readable codebase and requires no framework overhead.
**Verdict:** confirm — the nanochat engine.py implementation is the exact spirit of Verso's @tool decorator. Cite in §5.3 design rationale.

### Finding 5: Eval harness integrated into training pipeline, not separate environment
**Tag:** [SHARPENS §5.5 evals]
nanochat runs evals on the same infrastructure as training — same data loader patterns, same distributed setup, same reporting system. There is no "switch to eval mode" requiring a different environment. Verso's eval harness should be similarly integrated: running an eval should be a mode of the same agent runner, not a separate testing framework. The `define_outcome` evaluation should run the same agent loop with instrumentation added — not a parallel reimplementation.
**Verdict:** sharpen — strengthen the §5.5 spec: evals run the live loop with instrumentation, not a separate path. This also eliminates the class of bugs where eval behavior differs from production behavior.

### Finding 6: The "works for all settings of depth" principled-change test
**Tag:** [NEW-IDEA §5.5 evals / §6.1 durable runtime]
> "Any candidate changes to the repo have to be principled enough that they work for all settings of depth."

This is a cross-scale validity requirement. For nanochat: a change must work for GPT-1 scale AND GPT-2 scale AND larger. For Verso: a change to the loop or harness must work for the simplest tactical agent AND the most complex durable multi-agent pipeline. The invariant is a test of principled design: if your change only works at one point on the complexity dial, it is a hack, not a design. This should be a formal review criterion for Verso's core PRs.
**Verdict:** adopt-now — add "works across the tactical/durable dial" as a formal PR review criterion in §4 architecture docs. This is the nanochat principle applied to the seam design.

### Finding 7: The explicit-over-autocast principle and its Verso equivalents
**Tag:** [CONFIRMS §5.1 loop / §5.3 tools]
nanochat's choice to explicitly manage precision (global COMPUTE_DTYPE, no autocast) rather than rely on framework magic CONFIRMS Verso's preference for explicit named structure over implicit behavior. The named StopReason enum, typed RunContext injection, and {data, error, ok} dispatch are all the same philosophical choice: make the important thing visible and named, not implicit and auto-configured. Nanochat shows this pattern scales to a production-quality codebase.
**Verdict:** confirm — use as design precedent when defending explicit-over-implicit choices in §5.1 and §5.3.

### Finding 8: Leaderboard with single clear metric as eval north star
**Tag:** [NEW-IDEA §5.5 evals]
nanochat's DCLM CORE score + public leaderboard gives the community a single answer to "is this better?" Verso should define an analogous north-star eval metric for agent quality — not a suite of abstract benchmarks, but a single number that a practitioner can track over time in their own context. The `define_outcome` API should produce a "score" that can be tracked on a project-level leaderboard. Making progress visible is a motivational and technical design goal.
**Verdict:** adopt-now — add project-level eval score tracking to §5.5 harness design; the nanochat leaderboard is the model.

---

## Summary Verdict

nanochat is the closest structural analogue to Verso in the ML training world. The design choices are nearly identical: one complexity dial, no framework monsters, explicit over autocast, tool use as a token pattern, eval integrated into the pipeline. The most actionable new findings are: (1) the single dial as the design model for the durable seam, (2) the baseline-adjusted scoring (ChatCORE) as a model for `define_outcome`, (3) the "works for all settings of depth" as a PR review criterion, and (4) the leaderboard/north-star-metric concept for project-level eval tracking. Several findings CONFIRM existing Verso invariants with strong external evidence from a respected builder.
