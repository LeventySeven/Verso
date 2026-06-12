# Mike Krieger: Building AI Products From the Bottom Up

**Source:** https://www.youtube.com/watch?v=Js1gU6L1Zi8
**Speaker:** Mike Krieger (CPO, Anthropic; co-founder, Instagram)
**Format:** Sequoia Capital AI Ascent 2025 · talk · ~24 min
**Status:** read_partial — no verbatim transcript retrieved. Primary sources: Sequoia's official Inference by Sequoia Substack writeup, GlobalGPT Medium summary, Lenny's Newsletter episode (separate but overlapping content), and secondary coverage. Content is sourced.

---

## Core Thesis

The plan-then-ship loop that works in traditional software breaks at a frontier-AI company. The model changes faster than the planning cycle. The best AI products are built *closest to the model* — meaning in direct collaboration with researchers and the evolving capabilities — not planned from the outside in via specs and roadmaps. Product taste at a frontier-AI company is about engineering the *conditions* that let the right thing surface, not writing the right spec.

*"You just have to allow for much more bottoms up creativity, because the best products are the ones that are built very close to the model, and you can only kind of tell what they're capable of pretty late in the process."*

---

## The Instagram Contrast

At Instagram, Krieger ran "tops down, 3 to 6 month time frame of planning" — deliberate, structured, predictable. Frontier AI inverts this. The model's capability envelope shifts monthly; any top-down spec written today encodes assumptions that may be obsolete before the feature ships.

The implication: stop trying to outsmart the model's trajectory. Instead, create organizational permission for rapid bottom-up experimentation, and let the best surfaces emerge.

---

## Case Study: Artifacts

Artifacts — Claude's ability to render live, interactive artifacts alongside conversation — began as a research prototype. A designer and an engineer picked it up, refined it, and shipped it to production. No VP mandated it. No roadmap tracked it. Leadership's contribution was recognizing it and not killing it.

This is the operating principle made concrete: *"a research prototype that then got taken up by a designer and an engineer and then shipped to production."*

---

## Case Study: Model Context Protocol (MCP)

Two engineers were repeatedly building bespoke integrations — Google Drive, GitHub, etc. Each integration was its own snowflake. They noticed: *"We were implementing Google Drive integration, and then we're implementing GitHub integration. And those things should have more in common than not."*

No leadership directive. They extracted the common pattern, built a reusable protocol, and MCP became what Krieger now describes as potentially Anthropic's most consequential release — Microsoft integrated it into Windows; it's the fastest-growing standard in tech history.

The lesson: MCP is what "schlep-as-moat" looks like from the inside. The engineers were doing annoying grunt work, recognized the pattern, and had organizational permission to solve the general problem instead of the specific one.

---

## The Productivity Paradox

AI-generated code now accounts for 70–95% of Anthropic's internal code. This doesn't eliminate bottlenecks; it *reveals* them:

*"The bottlenecks have shifted from engineering (writing code) to decision-making (what to build) and merge queues."*

A 1-hour alignment meeting now blocks the equivalent of 4–8 hours of AI-amplified engineering output. This is a forcing function: organizational drag becomes visible and painful in a way it wasn't when humans were the speed limit.

---

## Agent-to-Agent and Agentic Products

Krieger flags two emerging challenges in agentic systems:
1. Enabling models to take automated action beyond context-provision (long-horizon, multi-step)
2. Managing agent-to-agent transactions — including trust/discernment ("knowing when to share sensitive data versus rejecting unknown agents")

His framing: the future product is models that can "work for hours at a time," which requires memory, advanced tool use, and self-onboarding into organizational contexts.

---

## The Usability Gap

Despite capability growth, *"these products are really hard to use effectively for most people approaching it for the first time."* This troubles Krieger. The ability gap between power users who extract massive value and first-time users who bounce is a structural product problem, not a model problem.

First-time UX simplicity is a core design imperative — not an afterthought.

---

## Principles for AI Product Teams

Distilled from multiple coverage sources:

- **Normalize AI use transparently** — Krieger shares his Slack-Claude integration workflow publicly inside Anthropic. Modeling visible usage destigmatizes it.
- **Design for agents, not sidebars** — AI capabilities embedded in core workflows outperform bolt-on chat panels.
- **Prioritize first-time UX** — the usability gap is real and painful.
- **Embed PMs with researchers, not just engineers** — the highest-leverage PM contribution at a frontier lab is at the research/product seam, where model capabilities first become visible.
- **True value metric = time/effort saved** — "When Claude prototypes something in 25 minutes versus six hours of manual work, *that* is the meaningful metric, not conversation counts."

---

## Three Defensible Moats for AI Startups

1. **Deep domain expertise** — e.g., Harvey in legal; the model is commodity, the domain encoding is the moat
2. **Differentiated customer relationships** with proprietary knowledge
3. **Novel interaction paradigms** incumbents can't easily replicate (e.g., Cursor's edit-in-place UX vs. GitHub Copilot's sidebar)

---

## VERSO RELEVANCE

### [SHARPENS] §7/§12 Demo-able wedge — "Built close to the model" validates VERSO's dogfood-first principle

Krieger's "best products are built closest to the model" is structural support for VERSO's personal-infra, dogfood-first operating principle. The senior engineer using VERSO to build real agents *is* the equivalent of the designer who picked up Artifacts and shipped it. The founding team's daily use of their own harness is not just a credibility signal — it is, by Krieger's logic, the mechanism that produces good AI products.
*Tag: SHARPENS §7 demo-able wedge / dogfood-first principle*

### [SHARPENS] §1 Moat — Bottom-up emergence vs. top-down spec as the product development model

Krieger's insight on why AI products can't be planned top-down has a direct implication for VERSO's product strategy: the harness primitives that actually matter will be discovered through production use, not specified in advance. This argues for aggressive internal dogfooding (already VERSO's position) over feature roadmapping. The non-goals list ("non-goals are evidence-updatable, not identity") is the right posture precisely because of this.
*Tag: SHARPENS §1 / bet-moat: harness primitives discovered through use*

### [NEW-IDEA] §12 GTM — MCP origin story as a cold-start archetype

MCP emerged as a schlep-as-moat move: do the annoying integration work repeatedly, recognize the pattern, solve it generally. For VERSO, the cold-start analog is: build agents that are genuinely annoying to build without the harness, build them yourself first, then make the pattern legible and reusable. The MCP story is a proof point that "two engineers frustrated with repetitive work" is a legitimate founding story for infrastructure standards.
*Tag: NEW-IDEA §12 GTM cold-start / MCP-as-archetype*

### [CONFIRMS] §12 Positioning — "Novel interaction paradigm" moat confirms the inspect() / seam angle

Krieger's third startup moat — novel interaction paradigms incumbents can't replicate — maps directly onto VERSO's inspect()-as-data-viewer and the one-flag durable seam. These are not features; they are interaction paradigms that change how the senior engineer *relates* to their agent. LangChain can't replicate them without a full rewrite because they require architectural choices made at the harness level.
*Tag: CONFIRMS §12 positioning / inspect() and seam as interaction-paradigm moats*

### [NEW-IDEA] Product taste layer — "Engineering conditions for the right thing to surface"

Krieger reframes product taste at a frontier-AI company: not "write the right spec" but "engineer the conditions that let the right surface emerge." For VERSO, this implies: keep the primitives minimal and composable (not opinionated), maintain short feedback loops to production (dogfood-first), and treat non-goals as boundary conditions that create space for the right things. The harness is the condition-engineering infrastructure, not the product itself.
*Tag: NEW-IDEA — product taste as condition-engineering; connects to §2 non-goals and §7 demo-able wedge*

---

## Verdict

High-signal for VERSO's product-development and positioning layers. The Artifacts/MCP case studies provide concrete archetypes for how the right primitives emerge from bottom-up use rather than top-down spec. The "usability gap" framing is a useful tension: VERSO targets the structurally-aware senior (who can close the gap themselves), but the primary persona insight is that even expert users experience this gap, and legibility is a moat.
