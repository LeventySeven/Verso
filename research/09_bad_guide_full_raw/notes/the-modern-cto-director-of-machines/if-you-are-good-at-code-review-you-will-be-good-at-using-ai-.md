# If You Are Good at Code Review, You Will Be Good at Using AI Agents — Sean Goedecke
**Source:** https://www.seangoedecke.com/ai-agents-and-code-review/
**Author:** Sean Goedecke (GitHub staff engineer)
**Published:** September 20, 2025
**Status:** read_full
**Themes:** loop_harness, strategy, evals

---

## Faithful Digest

### Core Argument
Using AI agents correctly is a process of *reviewing code*. The durable skill is **structural judgment** — catching when an agent is committing to an architectural dead end — not line-level nitpicking. The analogy to code review is precise and load-bearing: agents behave like enthusiastic junior engineers who never develop judgment over time the way a real human would.

### The Architecture Dead-End Problem
Two concrete examples from the author's own agent sessions:

1. **VicFlora Offline (Codex):** Agent spent large amounts of effort reverse-engineering a frontend SPA to extract dichotomous key IDs — a fragile scraping pipeline. The author realized the raw data was available from a separate explicit API endpoint. "About once an hour I notice that the agent is doing something that looks suspicious, and when I dig deeper I'm able to set it on the right track and save hours of wasted effort."

2. **Spaced repetition app (Codex + Claude Code):** Both agents, independently, "really want to build a full background job infrastructure: with job entities, result polling, and so on." For short-lived parallel work, this is "very obviously overkill. Just make a non-blocking request from the frontend!"

Both examples are structural failures, not line-level failures. The agent produced syntactically correct, even impressive code — in the wrong direction.

### The Structural Review Principle
> "The best code review is *structural*. It brings in context from parts of the codebase that the diff didn't mention."

The ideal structural review makes the diff *shorter and more elegant* by identifying existing system reuse: "instead of building out a new system for operation X, we can reuse a system that already exists."

The author's taxonomy of bad reviewers, applied to AI agent users:
- **Nitpicky reviewer** → will struggle with AI tooling: "forever tweaking individual lines of code, asking for a `.reduce` instead of a `.map.filter`, bikeshedding function names. At the same time, you'll miss the opportunity to guide the AI away from architectural dead ends."
- **Rubber-stamp reviewer** → will put too much trust in AI output: "works with competent colleagues, but it doesn't work well when you're onboarding junior engineers."

The correct archetype: someone who spends approximately *zero* seconds per diff asking whether the code was written, and many seconds asking whether this is even the right approach at all.

### On "Pure Vibe Coding"
> "If you don't have the technical ability to spot when the LLM is going down the wrong track, you'll rapidly end up stuck. Trying to make a badly-designed solution work costs time, tokens, and codebase complexity. All of these things cut into the agent's ability to actually solve the problem. Once two or three of them pile up, the app is no longer tractable for the agent and the whole thing grinds to a halt."

This is a precise failure mode: complexity accumulation from locally-correct decisions that are architecturally wrong creates a *non-tractable* state for future agent work. The degradation isn't linear — it compounds.

### Centaur Chess Model
The author's dominant framing: current productive AI-agent use is "centaur chess" — skilled human paired with computer assistant. Not autonomous agents, not human-only. The human contribution is structural judgment; the AI contribution is execution speed and breadth.

He notes: "If you described early Copilot as a brand-new grad and current Claude Code as an engineer with three years of experience, would that be too far off? In another three years, will working with AI tooling be like working with an engineer with six years under their belt?" — suggesting the trajectory is real but gradual, not step-change.

### Verbatim Quotes

1. "About once an hour I notice that the agent is doing something that looks suspicious, and when I dig deeper I'm able to set it on the right track and save hours of wasted effort."
2. "I think the biggest mistake engineers make in code review: only thinking about the code that was written, not the code that *could have been* written."
3. "The best code review is *structural*. It brings in context from parts of the codebase that the diff didn't mention."
4. "If you're a nitpicky code reviewer, I think you will struggle to use AI tooling effectively."
5. "If you don't have the technical ability to spot when the LLM is going down the wrong track, you'll rapidly end up stuck... Once two or three of them pile up, the app is no longer tractable for the agent and the whole thing grinds to a halt."
6. "Working with AI agents is like working with enthusiastic juniors who never develop the judgement over time that a real human would."
7. "The dominant programming model is something like 'centaur chess', where a skilled human is paired with a computer assistant."

---

## VERSO RELEVANCE

### [SHARPENS §6.3 — Safety/Hooks] The "architectural dead end" is the primary hook trigger
Goedecke identifies the *one thing* that human review catches that agents can't: structural over-commitment. Verso's hook/interrupt model (§6.3) is currently framed around safety and audit. This essay sharpens the framing: the primary value of human-in-the-loop is not catching individual mistakes but catching **architectural commitments that compound into non-tractable states**. Hooks should fire at architectural decision boundaries, not every tool call. The question a hook prompt should surface: "the agent is about to build a background job system — is this the right structural choice for the task?"

**Verdict:** sharpen — revise hook/interrupt documentation to frame the primary use case as architectural judgment, not safety auditing.

### [CONTRADICTS §5.1 — Loop] Clean loop ≠ sufficient harness for durable value
The essay implicitly argues against the "the loop is not where anyone competes" framing by showing that loop-level discipline is necessary but insufficient. The real harness value is *making structural judgment possible at the right cadence*. Goedecke's "once an hour I notice something suspicious" cadence is not a loop-level hook — it's a task-level interrupt. Verso's current model (observe every N steps, human-in-the-loop flag) needs a mechanism for surfacing structural choices specifically, not just pausing for review. The loop being clean is a precondition; the harness surface for structural judgment is the product.

This is a partial contradiction: Verso says "the loop is not where anyone competes" but the essay implies the harness mechanism for structural judgment is the rare valuable thing. The loop being clean matters because it makes structural judgment surfaces easy to instrument.

**Verdict:** sharpen — do not weaken the "loop is not the moat" claim, but add language in §6.3 and §5.4: the harness value is surfacing structural decision points, not just auditing individual steps.

### [SHARPENS §5.5 — Evals] Non-tractability as a lagging eval signal
The "two or three bad structural choices pile up → app is no longer tractable" pattern is a real failure mode for long-horizon agents. Current eval thinking (judge-panel, define_outcome) focuses on task-level success/failure. Goedecke's pattern suggests a complementary metric: *structural debt accumulation per agent session* — does the codebase become more or less tractable for future agent work as tasks complete? This is measureable: count times agent has to backtrack, count code paths that reference novel infrastructure vs. existing patterns.

**Verdict:** new-idea — propose "tractability delta" as an optional second eval dimension for long-horizon agent tasks in §5.5.

### [CONFIRMS §4 — The Seam/Architecture] Overkill is the default failure mode
The background job infrastructure example is exactly what Verso's "no overkill" invariant exists to prevent. This is a clean confirmation: the seam architecture (tactical-by-default, promote-to-durable intentionally) directly resists the agent's natural tendency to build generalized infrastructure prematurely. The Verso "no overkill" invariant has a named failure mode now: "background job inflation."

**Verdict:** confirm — already captured, but "background job inflation" as a named pattern is worth referencing in §4 documentation.

### [NEW-IDEA §12 — Positioning] The harness buyer is a senior structural reviewer, not a beginner
Goedecke's argument about "rubber-stamp reviewers" putting too much trust in AI implicitly defines Verso's ideal user: someone with enough structural judgment to recognize architectural dead ends. This is the anti-"vibe coder." Verso's GTM should target engineers who already have this structural intuition and want tooling that makes it easier to exercise — not engineers who want autonomous agents they don't have to supervise. This contradicts (or at least narrows) any positioning toward "non-technical directors of machines" as a primary persona.

**Verdict:** sharpen — GTM persona for §12 should be "structurally-aware senior engineer" as primary, with "director of machines" as secondary or aspirational.

### [SHARPENS §6.2 — Multi-agent] Multi-agent orchestration amplifies the "tractability collapse" problem
If a single agent "once an hour" makes a bad structural choice, a multi-agent system without structural review at orchestrator level will compound this at the interaction boundaries. The centaur chess model breaks down in multi-agent: you can't review every subagent's structural choices in real time. This suggests Verso's multi-agent design needs a *structural summary protocol* — a way for subagents to surface "I chose approach X over Y for structural reason Z" so the orchestrator (human or meta-agent) can verify structural coherence across the full task tree.

**Verdict:** new-idea — add structural decision summary to subagent output protocol in §6.2 design.
