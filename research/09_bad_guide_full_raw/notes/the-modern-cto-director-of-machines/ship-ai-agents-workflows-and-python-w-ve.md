# Ship AI: Agents, Workflows, and Python — w/ Vercel CTO Malte Ubl

**Source:** https://www.youtube.com/watch?v=RXx5ZN69Z3E  
**Speaker:** Malte Ubl, CTO Vercel  
**Format:** Latent Space podcast · ~42 minutes · October 31, 2025  
**Latent Space episode page:** https://www.latent.space/p/ship-ai-recap-agents-workflows-and  
**Transcript status:** No full transcript found. Content reconstructed from: (1) Latent Space episode show notes page (partial); (2) Vercel blog "The no-nonsense approach to AI agent development" (vercel.com/blog/the-no-nonsense-approach-to-ai-agent-development); (3) Vercel blog "What we learned building agents at Vercel" (vercel.com/blog/what-we-learned-building-agents-at-vercel); (4) startuphub.ai summaries; (5) web search aggregations. The episode audio was not accessed directly.

---

## What Ubl Actually Argues

### Core Philosophy: Humility in the Nascent AI App Space
Ubl's overarching thesis is that the AI application space demands epistemic humility — fundamentally unlike mature web development where patterns are established. Direct quote: "We know absolutely nothing and we still know absolutely nothing. Things are emerging… you have to stay low-level so that this can be flexibly used as trends emerge."

This humility informs the AI SDK's design: deliberately low-level and flexible rather than opinionated. The contrarian stance vs. opinionated agent frameworks: premature abstraction is the failure mode.

### Dogfooding as the Only Valid Abstraction Filter
Vercel's principle: "never shipping abstractions they haven't battle-tested themselves." The AI SDK was extracted from v0 (Vercel's internal code-gen product), not designed in the abstract. This means every SDK primitive has a production proof-of-concept behind it.

Applied design test for any framework primitive: Can the team that built it point to a live internal use case where it solved a real problem? If not, it's a theoretical abstraction — a cargo cult pattern.

### The Three-Step Agent Development Framework
From "The no-nonsense approach to AI agent development":

**Step 1: Manual Prototyping Before Coding**
"Before coding, simulate the agent by hand using real inputs. Understand the task the way a person would approach it, step by step." Observe "which parts feel repetitive or mechanical" as automation candidates. The v0.dev origin story: "LLMs struggled to generate reliable HTML. The breakthrough wasn't from better models, but from narrowing the scope and using structured inputs with Tailwind."

**Step 2: Automate with Deterministic Code First**
"LLMs are non-deterministic. If you can write a normal function to handle a step, do it. Use plain code for parsing, calculating, or sorting." The explicit rejection of over-engineering: "Don't be afraid of plain old programming. Save the LLM for parts that truly need judgment."

**Step 3: Optimize Reliability, Not Features**
Focus on "tightening the loop," refining prompts, making "tool calls more precise." Use "a second model to critique the results of the first model and continue the work" when needed. Success criterion: agent "reliably produces acceptable results with little to no intervention."

### The Agentic Sweet Spot
From "What we learned building agents at Vercel":
Success comes from tasks with "low cognitive load and high repetition from humans" — "too dynamic for traditional automation, but predictable enough for AI to handle reliably." The discovery methodology is deliberately simple: ask teams "what part of your job do you hate doing the most?" This identifies the sweet spot.

The scope principle: "The most effective AI agents are narrow, tightly scoped, and domain-specific."

When agents make sense: tasks that are "difficult to automate with traditional code" AND "where prompting the model manually shows signs of success." Both conditions required.

### Production Case Studies (Vercel's Own Agents)

**Lead Processing Agent**
- Problem: manual lead qualification research was "mind-numbing" (described by top performer)
- Workflow: deep research → qualification (using `generateObject`) → email composition → human review via Slack → approval & send
- Result: "One person handles the work of 10"

**Anti-Abuse Agent**
- Problem: "Human reviewers investigated every report manually, running a formulaic process to make an initial judgment call"
- Workflow: URL intake → analysis (visual/textual) → recommendation → human review → resolution
- Result: "59% reduction in time to ticket closing" in first iteration

**Anomaly Detection (Vercel Agent beta)**
- Addresses the "recall-precision problem" in traditional alerting: too many false-positive alerts
- Automatically investigates production anomalies by querying observability data and analyzing logs
- Makes alert triage more precise, reducing alert fatigue

### Human-in-the-Loop: Non-Optional for Safety-Critical Work
"Human-in-the-loop is non-negotiable for safety-critical operations, not optional." The WDK (Workflow Development Kit) implements this: webhook patterns for orchestrating long-running processes with HITL approvals. WDK enables TypeScript functions to "pause, resume, and wait indefinitely without cost."

The `needsApproval: true` parameter in AI SDK 6.0 — a first-class primitive, not an afterthought.

### Build vs. Buy Stance
Ubl frames the decision not as cost/make-vs-buy efficiency calculus but as: does the off-the-shelf agent actually solve YOUR problem or a generic proxy of it? The build-vs-buy decision reduces to the dogfooding test: can the off-the-shelf vendor demonstrate the specific use case in production?

"An Agent on Every Desk" program — Vercel's enterprise adoption push providing reference templates and consultations for companies building first production agents. Signal: the hardest part is not the agent, it's finding the right problem.

### Python Support: Strategic Signal
First-time native Python backend support with zero-config deployment for Flask and FastAPI. The strategic logic: Python is where the AI/ML ecosystem lives. Agents built by data scientists and ML engineers need deployment that isn't TypeScript-first. Python support lowers the friction for production-grade agents written by the people who understand model behavior best.

### Framework Design: Stay Low-Level
The explicit contrast with mature web development: React/Next.js have decades of converged patterns; AI application patterns are still emerging. Forcing premature convergence (via an opinionated framework) would freeze the wrong patterns into production codebases.

The AI SDK's design principle: type safety across providers (OpenAI, Anthropic, Mistral) via identical function signatures, but no opinionated orchestration. Provider-agnostic at the model layer; pattern-agnostic at the application layer.

### Key Numbers
- v0 extraction: AI SDK extracted from Vercel's own production use of v0
- 59%: reduction in time-to-close for anti-abuse tickets in first iteration
- "One person handles work of 10": lead processing agent result
- Agents ecosystem: CodeRabbit, Corridor, Sourcery, Autonoma, Braintrust, Browser Use at launch

---

## VERSO RELEVANCE

### [CONFIRMS §5.1 + §12 — loop + positioning]
**Finding:** Ubl's three-step framework (manual first, deterministic code second, LLM only where judgment required) directly CONFIRMS Verso's "no overkill" hard invariant. The explicit instruction "Don't be afraid of plain old programming. Save the LLM for parts that truly need judgment" is a practitioner endorsement of Verso's anti-abstraction position. An infra CTO at production scale landed on the same principle independently.
**Verdict:** Validates loop design philosophy; good positioning quote for anti-framework narrative.

### [SHARPENS §6.1 — durable execution / HITL]
**Finding:** The WDK's "pause, resume, and wait indefinitely without cost" + `needsApproval: true` as a first-class parameter is a live production implementation of Verso's tactical→durable seam. The 59% ticket-close-time reduction from the anti-abuse agent demonstrates the quantifiable value of HITL-by-default design. This sharpens the claim: HITL is not safety theater, it's the mechanism that makes agents deployable in real stakes environments.
**Verdict:** Use the 59% number + "human review via Slack → approval & send" pattern as concrete evidence for Verso's HITL design.

### [NEW-IDEA — §5.2 context / §5.5 evals]
**Finding:** The "agentic sweet spot" discovery methodology — asking "what part of your job do you hate doing the most?" — is a novel eval-seeding heuristic. It identifies the ground truth of what constitutes a successful outcome (relief of pain) before any code is written. For Verso's `define_outcome(bounded)`: the bounded outcome spec should be anchored to the human's pain signal, not a developer's abstraction of it.
**Verdict:** Pre-eval user-pain mapping as the correct starting point for `define_outcome` — worth integrating into Verso onboarding guidance.

### [CONFIRMS §5.3 — tools]
**Finding:** "The most effective AI agents are narrow, tightly scoped, and domain-specific" directly confirms Verso's native Python @tool design — tools should be small, specific, and composed by the user, not provided by the framework as fat abstractions.
**Verdict:** CONFIRMS ACI tool-design principle; the framework should resist providing domain-specific tools.

### [SHARPENS §6.4 — model]
**Finding:** Provider-agnostic via identical function signatures across OpenAI/Anthropic/Mistral — Ubl's production implementation of cross-model abstraction confirms that provider-agnostic is table stakes, and the right level to do it is function signature, not runtime routing. Sharpens Verso's cross-model failover design: the abstraction belongs at the call site, not in the loop.
**Verdict:** Confirms model-layer abstraction design; reinforces that model selection is config, not architecture.
