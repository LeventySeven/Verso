# Block CTO Dhanji Prasanna: Building the AI-First Enterprise with Goose

**Source:** Training Data podcast (Sequoia Capital), YouTube / Sequoia Substack (Inference by Sequoia)
**URL:** https://www.youtube.com/watch?v=64J2lHxP0ok
**Transcript source:** https://inferencebysequoia.substack.com/p/block-cto-dhanji-prasanna-building + https://sequoiacap.com/podcast/training-data-dhanji-prasanna/
**Status:** read_partial (two detailed secondary digests; primary paywall via Lenny's)
**Runtime:** ~1 hour · Published ~Sept 2025

---

## Speaker & Context

Dhanji Prasanna is Block's CTO (formerly Google engineer, Framework author). He is speaking to Sequoia's Sonya Huang and Roelof Botha. Block is a 4,000+ engineer fintech org (Square, Cash App, Tidal, platform). This is their account of how they reorganized and built Goose, their open-source general-purpose AI agent.

---

## Core Arguments

### 1. The Org Restructure: GM Silos → Functional Teams

Block had a General Manager structure — each business unit (Square, Cash App) ran its own tech stack. They deliberately dismantled this and moved to centralized **functional teams** specifically to accelerate AI adoption.

> "Having this depth and singular organizational focus is really important" during periods of technological disruption.

The functional structure enabled: unified technical policies across Square, Cash App, Tidal, and platform services; treatment of all operations as interconnected "capabilities" that AI can orchestrate; and faster cross-unit adoption of AI tooling.

### 2. Goose: Open-Source, MCP-Backed General-Purpose Agent

Goose is Block's internal AI agent, now open-sourced. Built by a **6-7 person team led by Brad Axen**.

- Runs on the laptop; uses **MCP (Model Context Protocol)** to orchestrate existing enterprise systems
- Connects to: Gmail, Google Docs, Snowflake, Square Payments, Salesforce
- "Give it a little prompt and say, 'I want a marketing report of how we did in Q3,' and then it goes away, looks in Snowflake, pulls out data...builds charts...delivers as PDF or Google Doc."
- Safety: operates within the user's own authorization level — "its blast radius is highly limited to any actions humans take"
- Three modes: (a) human-in-the-loop for destructive actions, (b) autonomous with self-interruption, (c) headless in CI pipelines (mandatory human code review)
- Uses "**recipes**" — reusable workflow patterns teams share across org

Block was an **early MCP adopter and co-contributor** alongside Anthropic. They also built "**Toolshim**" — an adapter enabling open-source models to call MCP tools.

### 3. Measuring Real Impact

Primary metric: **manual hours saved per week**.

- Engineers using Goose report saving **8-10 hours/week**
- Year-end target: **25% reduction in manual hours** across the org
- Code generation share: ~30-40% in complex legacy systems; **near 100% in AI-native apps** (including Goose's own codebase)

### 4. Non-Technical Adoption ("Vibe Coding Era")

Unexpected finding: sales personnel, financial staff, and non-engineers are building real applications via conversational interfaces. Examples:
- Figma designs → functioning websites
- Custom travel optimization tools
- Treasury dashboards with one-click sharing

> "Let agents learn from doing things...figures things out in surprising ways that you wouldn't think of as a human."

Key principle: **don't over-engineer integrations upfront** — let Goose discover workflows organically.

### 5. Model Flexibility as a First-Class Concern

Prasanna does not bet on a single model provider:
- Proprietary: Claude family (preferred for coding), GPT models
- Open-source: Qwen, DeepSeek
- Privacy-sensitive ops: embedded models running locally on MacBooks

He frames model optionality as a design requirement, not an afterthought.

### 6. Future Vision: Swarms of Smaller Open Models

Rather than one big proprietary model, Prasanna predicts:

> "Swarms of smaller, open models working together — unlocking complex software creation...that surpasses what any single model can do."

Hypothetical: "50 instances of Goose...working for hours with each other to build fairly complex applications." Architecture: capable models for planning + smaller models for discrete "nano services" → applications of "Cash App scale."

### 7. The "Utility Phase" Framing

> "The utility phase of LLMs and agents is still ahead of us...we're just starting to see some of that."

Prasanna expects 2025-2026 to produce organizational divergence: companies committed to utility extraction vs. those abandoning AI initiatives prematurely. Roelof Botha's historical perspective: Amara's Law — 2026 as trough of disillusionment before 2030 breakthroughs.

### 8. Open-Source Rationale

> "We can either have our community of 3,000+ engineers work on something, or we could have the broader community of 30,000+ engineers...benefit from that, too."

Block's open-source heritage: Android (~4B devices), Bitkey (blockchain), mining hardware (Rig). Goose is the same logic applied to AI agents.

### 9. Square AI (Customer-Facing)

Public beta: merchants query financials conversationally. Example — a wine bar owner asked "If we close an hour early on Thursdays, how much would we lose?" Analysis revealed waiters earned significant tips in that window; decision reversed. This is the "utility curve" Prasanna claims most critics haven't found yet.

---

## VERSO RELEVANCE

### [SHARPENS §6.3 safety] Blast-radius-scoped authorization
Goose's safety model is: agent inherits user's auth level, no privilege escalation, explicit human-in-the-loop gate for destructive actions, headless mode with mandatory code review. This is a concrete implementation of VERSO's safety seam. Verdict: confirms Verso's HITL seam approach; the "blast radius = human auth level" framing is a sharp one-liner worth adopting.

### [SHARPENS §5.3 tools] MCP as protocol layer, recipes as persistence
Block uses MCP broadly but wraps it with "Toolshim" for open-source models and organizes learnable patterns as "recipes." The native path is MCP-backed; the pattern-sharing mechanism is separate. This sharpens §5.3: tool discovery can be separated from tool execution, and reusable workflow patterns are a distinct product primitive. Verdict: useful; Verso should consider a recipe/pattern mechanism above raw tool calls.

### [CONFIRMS §6.4 model] Model optionality is non-negotiable at scale
Block runs Claude, GPT, Qwen, DeepSeek, and local embedded models — routing by task sensitivity. This confirms Verso §6.4 (cross-model failover, role-tiered models) is the right call for any agent framework targeting enterprises. Verdict: strong confirmation.

### [NEW-IDEA] Swarms-of-smaller-models framing as competitive positioning
Prasanna's prediction — swarms of small open models outperforming single large proprietary models — maps directly to Verso's multi-agent §6.2 and to the non-graph positioning (§12). A swarm that does not need a graph, just an orchestrator that dispatches and collects, is precisely what Verso's tactical loop enables. This is a useful positioning hook: "swarms without graphs." Verdict: high value for §12 messaging; should be tested against Verso's sub-agent dispatch model.

### [SHARPENS §5.5 evals] Hours-saved as the primary eval signal
Block's primary eval is not model accuracy — it is hours saved per week, measured continuously. This is outcome-grounded evaluation at the org level. Verso's §5.5 (judge-panel + define_outcome(bounded)) should include a note that the "correct" eval for agentic systems is workflow-level time/cost savings, not task-level accuracy. Verdict: useful framing addition; non-overkill.

### [CONFIRMS §6.2 multiagent] 6-7 person team shipping org-scale agent infra
Goose's team is tiny (6-7 engineers). The agent harness can be kept minimal and still operate at org scale via MCP and recipe sharing. This confirms Verso's minimal-loop philosophy and argues against over-engineered graph orchestration for the core. Verdict: confirms §6.2 anti-overkill stance.

---

## Source Notes

- Primary: Sequoia Training Data podcast (YouTube: https://www.youtube.com/watch?v=64J2lHxP0ok)
- Transcript extracted from: Inference by Sequoia Substack digest + Sequoia Capital show notes page
- Lenny's Newsletter deep-dive is paywalled; not used
- Status: read_partial (secondary digests; full 1h audio not transcribed)
