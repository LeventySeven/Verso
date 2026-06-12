# Agents — Chip Huyen

**URL**: https://huyenchip.com/2025/01/07/agents.html  
**Author**: Chip Huyen  
**Published**: January 7, 2025  
**Source**: Adapted from *AI Engineering* (O'Reilly, 2025), Chapter 6

---

## Source Description

A comprehensive framework essay — book-length — on AI agents covering definition, tools, planning, reflection, tool selection, and failure modes/evaluation. Self-described as "more experimental" than the rest of the book and explicitly conceptually aligned with Anthropic's "Building Effective Agents" (Dec 2024) but "focused more on planning, tool selection, and failure modes."

---

## Full Digest

### Agent Overview

"An agent is anything that can perceive its environment and act upon that environment." Characterized by (1) the *environment* it operates in and (2) the *set of actions* it can perform (augmented by tools).

> "The success of an agent in an environment depends on **the tool it has access to** and **the strength of its AI planner**."

Compound mistake cost: 95% accuracy per step → 60% after 10 steps → 0.6% after 100 steps. This math directly motivates both shorter loops and hard loop-step caps.

### Tools: Three Categories

1. **Knowledge augmentation** (read-only): retrievers, SQL executors, web browsing, internal search APIs — all are context-construction tools.
2. **Capability extension**: calculator, calendar, code interpreter, modality bridges (text-to-image, transcription, OCR). Key insight: "instead of trying to train the model to be good at arithmetic, it's a lot more resource-efficient to just give the model access to a tool."
3. **Write actions**: SQL mutation, email send, bank transfer — these "enable more, but the prospect of giving AI the ability to automatically alter our lives is frightening."

Chameleon (Lu et al., 2023): GPT-4 + 13 tools outperforms GPT-4 alone on ScienceQA by 11.37% and TabMWP by 17%.

**Tool count tension**: "More tools give an agent more capabilities. However, the more tools there are, the harder it is to efficiently use them." Direct analogy: harder for humans to master a large toolset.

**Tool transition**: If tool X is frequently followed by tool Y, combine into a higher-order tool. Voyager (Wang et al., 2023) proposes a *skill library* for accumulating and reusing synthesized tools.

**Tool preferences differ by model**: GPT-4 selects a wider set and favors knowledge retrieval; ChatGPT favors image captioning. Implies tool inventory must be tuned per model, not just per task.

### Planning

"Planning, at its core, is a search problem. You search among different paths towards the goal, predict the outcome (reward) of each path, and pick the path with the most promising outcome."

Key tension: **planning should be decoupled from execution** to avoid burning resources on bad plans. Generate plan → validate plan (heuristics or AI judge) → execute → reflect.

Control flow taxonomy (Huyen mirrors Anthropic routing):
- **Sequential**: B depends on A
- **Parallel**: A and B simultaneously (latency optimization)
- **If statement** ("routing"): branch on tool output
- **For loop**: repeat until condition

> "When evaluating an agent framework, check what control flows it supports."

**Planning granularity tradeoff**: detailed plan = harder to generate, easier to execute; high-level plan = easier to generate, harder to execute. Hierarchical planning circumvents this.

**Function calling mechanics**: tool inventory declared upfront with name, parameters, documentation. Settings: `required / none / auto`. Model generates tool + parameter values; parameters can be hallucinated.

Tips to improve planning:
- Better system prompt + more examples
- Better tool descriptions (simpler parameters)
- Refactor complex tools into simpler ones
- Use a stronger model
- Finetune for plan generation

**Natural-language plans vs. exact function names**: natural language is more robust to tool API churn; requires a downstream "program generator" translator. "Translating is a much simpler task than planning and can be done by weaker models."

### Reflection and Error Correction

ReAct (Yao et al., 2022): interleave Thought → Action → Observation per step, until the model decides done. Format:
```
Thought 1: …
Act 1: …
Observation 1: …
…
Act N: Finish [Response]
```

Reflexion (Shinn et al., 2023): separate evaluator (scores outcome) from self-reflection module (diagnoses failure). Agent proposes a new trajectory after each evaluate+reflect cycle.

> "Compared to plan generation, reflection is relatively easy to implement and can bring surprisingly good performance improvement."

Downside: each Thought/Observation costs tokens; ReAct and Reflexion both use heavy few-shot prompt examples → large input token cost.

**Human-in-the-loop integration points**: after query receipt, after plan generation, after each step, after plan completion. Humans can provide high-level plans, validate, or execute risky steps.

### Tool Selection

> "There's no foolproof guide on how to select the best set of tools."

Practical approach: ablation study — remove a tool, see if performance drops. If no drop, remove it. Plot distribution of tool calls (most-used / least-used). Benchmark tools that the agent frequently fails on; consider redesigning or swapping.

Different frameworks have different tool focuses: AutoGPT = social media APIs; Composio = enterprise APIs.

### Failure Modes & Evaluation

**Planning failures**:
- Invalid tool (hallucinated function name)
- Valid tool, invalid parameters (wrong arity)
- Valid tool, incorrect parameter values
- Goal failure (task solved without constraints, or wrong task)
- Time failure (finished too late)
- Reflection error ("convinced it's done when it hasn't")

**Evaluation dataset**: tuple `(task, tool inventory)`. Generate K plans; measure: fraction valid, attempts-to-first-valid, fraction of valid tool calls, invalid tool rate, invalid-parameter rate, wrong-value rate.

**Tool failures**: wrong output from a correct tool. Each tool needs independent benchmarking.

**Efficiency metrics**: steps per task, cost per task, time per action. Note: "humans and AI have very different modes of operation" — 100 web page visits is trivial for parallel AI, laborious for a human.

---

## VERSO RELEVANCE

### [SHARPENS §5.1] — Loop step budget / compound error math
Huyen's explicit 95%^N compound error calculation provides a crisp external validation for why Verso must expose a `max_steps` / loop budget config and surface it prominently. The number isn't just a safety rail — it's the primary determinant of task feasibility. The argument also motivates Verso's loop being short and legible (every step visible, cost trackable). **Verdict: adopt-now** — include the compound-error math in Verso's loop documentation.

### [SHARPENS §5.3] — Tool design ergonomics: simpler tool > clever tool
"Rewrite the functions themselves to make them simpler, such as refactoring a complex function into two simpler functions." This is a concrete design principle for Verso's `@tool` decorator: the ergonomic must push users toward single-responsibility tools. If function calling fails, the first fix is tool simplification, not prompt iteration. This reinforces Verso's native-Python `@tool` path — Python naturally supports small well-scoped functions. **Verdict: adopt-now** — document this in `@tool` API guidance.

### [SHARPENS §5.3] — Tool count has a cognitive-load ceiling
"The more tools there are, the harder it is to efficiently use them." Gorilla tested 1,645 APIs and struggled. This is a concrete empirical observation that justifies Verso's design choice of keeping the MCP adapter demoted: MCP's value is large tool discovery/integration, but large tool counts degrade planning. Verso's native `@tool` path by default is a *deliberate constraint* that serves planning quality. **Verdict: sharpen** — make this the explicit justification for MCP being opt-in rather than default.

### [SHARPENS §5.3] — Tool transition → composite tools
Voyager's skill library / Chameleon's tool-transition analysis suggests that frequently co-invoked tools should be combinable. This is a NEW-IDEA for Verso: expose `@tool` composition (a tool that calls sub-tools) as an explicit pattern in the harness, making synthesized skills first-class. **Verdict: lock-interface-defer** — don't build the skill library now, but the `@tool` API must not prevent composition.

### [SHARPENS §4/§5.1] — Plan/execute decoupling ≠ graph
Huyen describes plan generation → validation → execution as three stages, but explicitly says all three can be done in a single prompt (chain-of-thought) or across separate components. The key insight is that *decoupling is optional and should be driven by task risk, not framework mandate*. This SHARPENS Verso's "no forced graph" counter-position: even the planning literature doesn't require a graph; a well-prompted ReAct loop already instantiates plan/reflect/execute in one pass. **Verdict: confirm** — this supports Verso's one-loop-default, graph-optional design.

### [SHARPENS §6.3] — Write-action safety gates and human-in-the-loop checkpoints
Huyen names 4 explicit HITL checkpoints (query receipt / plan validation / step execution / completion) and ties write-action trust to "clearly defining the level of automation an agent can have for each action." This maps directly to Verso's `§6.3 safety/hooks` and the need for a `before_write_action` hook that routes to human approval. The permission model isn't one on/off switch — it's per-action-class trust levels. **Verdict: sharpen** — differentiate read vs. write hook granularity in the safety spec.

### [SHARPENS §5.5] — Agent eval dataset structure
Tuple `(task, tool_inventory)` → K plans → six metrics (valid-plan rate, attempts-to-valid, valid-call rate, invalid-tool rate, invalid-param rate, wrong-value rate). This is a concrete eval schema for Verso's `§5.5 evals` harness. The per-tool ablation study pattern (remove tool → measure performance drop) is a standard Verso users should be able to run automatically. **Verdict: adopt-now** — incorporate this eval schema into Verso's eval harness design.

### [NEW-IDEA for §6.2] — Role-tiered models by task complexity within planning
Huyen says: generate high-level plan with planner → translate each natural-language step with "weaker model." This is distinct from the already-known cross-model failover pattern: it's *intentional per-phase model assignment* within a single task (reasoning/synthesis model for plan, cheap model for translation). Verso's multi-agent dispatch could formalize this as a named pattern: `HierarchicalPlanner(plan_model, translate_model)`. **Verdict: lock-interface-defer** — track as multi-agent pattern.

### [CONFIRMS §12] — Anthropic alignment validation
Huyen confirms explicit conceptual alignment with Anthropic's "Building Effective Agents" — different terminology, same mental models. This means Verso's architecture, which is built on Anthropic-aligned patterns, will be recognizable and adoptable by teams reading both sources. No new action needed.
