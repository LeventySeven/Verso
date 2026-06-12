# Directing a Swarm of Agents for Fun and Profit

**Source:** Adrian Cockcroft · InfoQ · QCon SF Nov 2025 · Talk · ~46 min
**URL:** https://www.infoq.com/presentations/coding-agents/
**Also at:** https://qconsf.com/presentation/nov2025/directing-swarm-agents-fun-and-profit · YouTube https://www.youtube.com/watch?v=sp5ee7DaL5A
**Transcript source:** InfoQ presentation page (partial extraction) + cyberspaceandtime.com digest + QCon abstract + Cockcroft's own Medium post https://adrianco.medium.com/vibe-coding-is-so-last-month-my-first-agent-swarm-experience-with-claude-flow-414b0bd6f2f2
**Status:** read_partial (InfoQ video requires login for full transcript; detailed secondary coverage from 3 sources; Medium post is direct first-person account)
**Runtime:** ~46 min (QCon SF, Nov 17, 2025)

---

## Speaker & Context

Adrian Cockcroft: Technology Advisor at OrionX.net, formerly Principal Engineer at Netflix (where he led the 2010 AWS migration and pioneered microservices/chaos engineering), then Amazon. Retired from AWS in 2022. Now coding with AI assistance, RSI in arms making traditional keyboard-heavy coding painful — this is material context for his agent-first orientation.

The talk frames itself as personal experimentation ("fun stuff") with honest disclaimers about enterprise readiness: "in five to seven years, you'll be doing that in an enterprise. You're not necessarily doing this stuff today."

---

## Core Arguments

### 1. The Director-Level Management Pattern

> "I'm directing a team of agents...like a director-level manager."

The key insight: the human engineer stops being a coder and becomes a director. The director does not read every line of code; they set objectives, manage quality targets (test coverage, green CI), and nag until the team hits 100%. The velocity difference: agents accomplish "several days' work in 15 minutes."

This is the NoOps → NoDev evolution. Cockcroft's progression:
- NoOps (Netflix, ~2010): automate operations, humans manage the platform
- NoDev (2025): automate development, humans manage the development platform
- NoMan? (speculative): automate director function entirely

### 2. Stop Hiring Application Developers — Build the Platform

Core org-design claim: **move headcount from application development to platform development**.

The platform humans build provides:
- Policy and governance
- Security guardrails
- Pre-built components and approved patterns
- The "rails" AI agents must stay within

The AI agents handle: product feature development, iteration speed, volume work.

He acknowledges the platform is "incredibly fast changing...poorly understood" with tooling changes monthly — "a big pile of MCP servers or something, all randomly programmed." This instability is the reason humans need to stay in the platform layer, not because features are complex.

### 3. Multi-Agent Coordination: Claude Flow and Specialized Roles

Using Claude Flow, Cockcroft assigns **distinct MCP servers to different agent roles**: coder, tester, architect, DevOps specialist. Agents communicate via **shared memory and to-do lists**.

> "Each agent is single-minded...they check on each other's work."

This prevents **context pollution** — one agent trying to manage too many tasks simultaneously gets confused and degrades. Specialization keeps each agent's context focused.

He spawned 5 simultaneous agents on different tasks cooperating via the framework. Results: **150,000+ lines of production-ready code** in under 2 days (vs. estimated 20-week human timeline).

Carbon footprint argument: AI development is "5,000 times better than using Claude from carbon footprint point of view" compared to human developers (~10kg CO2/hour for humans).

### 4. BDD + Context Blocks as Quality Infrastructure

**Behavior-Driven Development (BDD):**
> "Given...when...then" structured tests provide agents better framework and prevent result-faking.

He runs tests at both unit-level and end-to-end integration. BDD is specifically chosen because agents have a failure mode of "claiming" completion without verifying; structured acceptance tests prevent this.

**Context blocks:**
Agents maintain **100-200 line comment blocks** documenting code functionality. This prevents repeated reverse-engineering across sessions — a key context continuity mechanism. The human-readable comments become the agent's working memory across turns.

Kent Beck's "Tidy First" philosophy: cleanup before adding features. Applied to agents: enforce code hygiene in the context blocks before extending.

### 5. Guardrails Through Explicit Negation

Critical technique for managing agents:

> "Don't build it yet...I want to check the plans before you build it."

Effective agent direction requires stating what NOT to do, not just what to do. The agent's default is to produce output; humans must insert checkpoints by explicitly gating actions. The director reviews plans before execution, not output after.

### 6. Emergent Agent Capability

> "The agents build things I didn't ask for. Sometimes they're things I didn't know to ask for."

This is a meaningful observation: agents can identify and implement valuable work outside explicit directives. The director must scan for these and evaluate them — some are good, some need to be reverted. This creates a new class of directorial work: evaluating unsolicited agent contributions.

### 7. The "Director Agent" Gap (Missing Infrastructure)

Cockcroft identifies a currently missing piece: **a director agent** that autonomously manages deadlines, test coverage targets, and continuous validation — automating away the directorial overhead entirely.

> "Maybe we have no man...Got NoOps, no dev, no man."

This is speculative but the logic is consistent: if the director role is defined well enough (metrics, targets, policies), it can itself be automated.

### 8. Enterprise Readiness Honest Assessment

> "Code needs to be safe. Commercial deals take time...We've got to be a lot more careful and responsible for paid work."

Cockcroft explicitly frames this as personal exploration. The 5-7 year enterprise timeline is a material constraint. He is not arguing enterprises should do this now — he is arguing individuals should experiment now so the enterprise transition is less painful later.

### 9. Development Workflow: Python-First, Then Port

"Building and testing in Python first, then translating to whatever language you really wanted to use." Python emerges as the preferred language for AI agent development due to tooling density and rapid iteration.

---

## VERSO RELEVANCE

### [SHARPENS §6.2 multiagent] Context pollution as the primary multi-agent failure mode
Cockcroft's "single-minded agents check each other's work" is a direct mechanism for why sub-agent specialization works. The failure mode he's avoiding is exactly context pollution — one agent holding too many tasks loses coherence. Verso's §6.2 sub-agent-as-failure-quarantine confirms this; Cockcroft adds the complementary framing: specialization also prevents context degradation, not just error propagation. Verdict: sharpens §6.2 sub-agent design rationale.

### [NEW-IDEA] Director agent as the missing Verso primitive
Cockcroft identifies "a director agent that autonomously manages deadlines, test coverage targets, and continuous validation" as currently absent infrastructure. This is a plausible Verso product direction: a meta-agent that orchestrates sub-agents against outcome metrics without human direction. This is distinct from the current §6.2 multi-agent (which is about parallel task dispatch) and points toward goal-directed orchestration as a higher layer. Verdict: NEW-IDEA worth tracking for Verso v2 roadmap; not blocking current scope.

### [CONTRADICTS §5.3 tools / confirms MCP-as-primary concern] "Big pile of MCP servers, randomly programmed"
Cockcroft describes the current MCP ecosystem as "incredibly fast changing, poorly understood...a big pile of MCP servers or something, all randomly programmed." This is a practitioner-level admission that MCP as a primary tool path creates maintenance overhead. Verso's position — native Python @tool as THE path, MCP demoted to opt-in — is validated here. The "randomly programmed" MCP landscape is exactly why you want a stable native abstraction above it. Verdict: strong evidence for Verso's MCP-as-opt-in stance (§5.3).

### [SHARPENS §4 seam] Explicit negation / plan-before-build as the HITL pattern
Cockcroft's key directive pattern ("don't build yet, let me check the plan") is a concrete implementation of the tactical ↔ durable seam: insert a human checkpoint between plan and execute without changing the agent's loop. This is the HITL gate that Verso's §4 seam enables. The mechanism is: agent produces plan, emits a "checkpoint" event, human approves, agent continues. Verso should surface this pattern explicitly in §4 documentation. Verdict: sharpens §4 seam implementation guidance.

### [CONFIRMS §6.2 multiagent] Shared memory + to-do lists as inter-agent coordination
Agents coordinating via shared memory and to-do lists (not message-passing graphs) is exactly the Verso multi-agent model: no forced graph, just shared state that agents read and write. The to-do list is an append-only work queue — structurally close to Verso's append-only history. Verdict: confirms §6.2 anti-graph stance for tactical multi-agent.

### [CONFIRMS §5.5 evals] BDD acceptance tests as in-process eval mechanism
BDD given/when/then tests that run end-to-end are a form of embedded outcome validation — the eval is built into the loop, not post-hoc. Verso's §5.5 embedded in-process evals is confirmed: the right place for evals is inside the agent harness, not outside it. Verdict: confirms §5.5 in-process eval approach.

---

## Source Notes

- InfoQ video page: https://www.infoq.com/presentations/coding-agents/ (login-gated for full video; partial extraction from page)
- QCon SF abstract: https://qconsf.com/presentation/nov2025/directing-swarm-agents-fun-and-profit
- NoOps→NoDev digest: https://cyberspaceandtime.com/FROM-NOOPS-TO-NODEV-ERA-ADRIAN-COCKCROFT-ON-DIRECTING-AI-AGENT-SWARMS-kQzX1KtCbhVY7ZQ7lL1LpFFf4Lq9jd_gA.htm
- Medium first-person account: https://adrianco.medium.com/vibe-coding-is-so-last-month-my-first-agent-swarm-experience-with-claude-flow-414b0bd6f2f2
- Status: read_partial — substantive coverage from 3-4 secondary sources; InfoQ full video transcript not extracted
