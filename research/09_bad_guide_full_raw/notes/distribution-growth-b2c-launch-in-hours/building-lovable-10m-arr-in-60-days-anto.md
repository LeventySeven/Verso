# Building Lovable: $10M ARR in 60 Days — Anton Osika

**Source:** https://www.lennysnewsletter.com/p/building-lovable-anton-osika
**Transcript found at:** PodPulse.ai digest + Lovable.dev video page transcript + social summaries (read_partial — Lenny original is paywalled)
**Speaker:** Anton Osika, co-founder and CEO, Lovable
**Format:** Lenny's Podcast founder interview, published ~March 2025

---

## Numbers

- GPT-Engineer open source: **52,000 GitHub stars** before paid launch
- $4M ARR in first **4 weeks** post-launch
- $10M ARR in **60 days** (2 months)
- **300,000** monthly active users at time of interview (3 months post-launch)
- **30,000** paying customers
- Team: **15-18 people** (12+ writing code)
- Described as "Europe's fastest-growing startup ever"

---

## Origin Story: Open Source → Waitlist → Paid

1. Anton built **GPT-Engineer** (a CLI tool) as an open-source proof-of-concept that LLMs could generate functional code end-to-end. Released publicly → 52K GitHub stars. This served as:
   - Pre-product market validation
   - Community formation before a product existed
   - Credibility signal with early technical adopters

2. Operated a waitlist under the name **"GPT Engineer app"** (deliberately keeping the OS association). The waitlist pre-qualified demand and created launch-day urgency.

3. Rebranded to **"Lovable"** only once the product reached what they internally called "lovable product" standard — i.e., the bar was set by the brand promise, not the other way around.

4. Primary acquisition post-launch: **"Mainly posting what we've shipped on social media… building in public"** rather than paid acquisition or traditional marketing.

---

## Core GTM Insight: The Scarcity Shift

> "The biggest bottleneck in product development is shifting — from 'Who can build it?' to 'Who knows what to build?'"

The product addresses the post-AI scarcity: technical execution is cheap; product taste and vision are the binding constraint. This is both the positioning argument and the ICP definition: the target user is someone with ideas and domain knowledge but no coding ability.

---

## Product Taste & Prioritization

- **Engineering-led product decisions**: Product managers without technical depth can't navigate Lovable's core problems — solutions are often embedded in technical details. Anton prioritizes hiring engineers who think like product owners.
- **Weekly cadence**: FigJam for roadmap planning, demos for alignment, balance between "build weeks" and "polish weeks."
- **Bottleneck identification**: "Identifying biggest bottleneck, iterating fast on solving that problem, then picking the next." Not feature-farming; pure constraint focus.

---

## Key Technical Wedge

The team discovered and codified a method for AI to **independently identify and fix its own bugs** — what they call the "unsticking" breakthrough. This improved reliability measurably and was a key differentiator vs. competitors who required users to re-prompt for every failure. The visual editor (iterate without re-prompting the agent) also differentiated from competitors.

---

## Hiring Philosophy (Obsession Filter)

Five-part filter:
1. Deep product and user care (obsession, not interest)
2. High raw cognitive ability
3. Startup mindset: speed over process
4. Generalist with one superpower (e.g., AI prompt optimization)
5. Work trial: **minimum 1 week** for all candidates

**Screen for:** Background research on demonstrated care for past projects. Unorthodox problem-solving. "Cracked engineers" who think like owners.

---

## Operating Model

- **In-person**: All key team members co-located. Lunch together for cross-team problem-solving.
- **Codebase rewrite at inflection point**: Rebuilt entire codebase to improve performance/scalability when hitting a scaling wall — not afraid of the schlep.

---

## VERSO RELEVANCE

### [NEW-IDEA] §12 GTM/Cold-Start: Open-source following as pre-product demand pool
The GPT-Engineer → Lovable pipeline is a specific, replicable GTM pattern: (1) release a minimal open-source tool that proves the core insight; (2) accumulate GitHub stars and early community; (3) launch a paid product to that pre-qualified audience with a waitlist. For VERSO, the analog is not a full OSS framework (which would fork the positioning) but rather: release a small, self-contained open-source harness module — the inspect() debugger, or the one-flag durable diff — that demonstrates the thesis concretely. Stars → credibility → pre-qualified beta cohort.
*Verdict: gives VERSO a concrete OSS cold-start path that doesn't require open-sourcing the entire harness.*

### [SHARPENS] §12 GTM/Launch: "Lovable standard" as a launch gate
Anton waited to rebrand and launch publicly until the product met "lovable product" standard internally. This is a launch-quality discipline: the bar is the brand promise, not a calendar date. For VERSO, this maps to: don't announce "VERSO" until the one-flag durable diff + inspect() + 3-line side-by-side demo all work end-to-end and tell a coherent story. The label is earned by the experience, not the other way around. This sharpens the existing "wedge-is-epistemic" finding.
*Verdict: gives operational form to the demo-able wedge discipline — wait for the wedge to be real before naming it.*

### [CONFIRMS] §12 GTM/Channel: Building-in-public as the primary B2D/B2C organic channel
"Mainly posting what we've shipped on social media… building in public." This is structurally identical to VERSO's DX-led organic hypothesis. The specific mechanic: weekly shipped-thing posts, not polished campaign content. Engineers and founders posting, not a marketing function. This confirms the channel hypothesis from a concrete fast-growing example.
*Verdict: strong confirmation with a numbers benchmark (52K stars → 300K MAU in 3 months).*

### [SHARPENS] §7 Wedge/Demo: "Unsticking" as the reliability wedge
Lovable's key technical breakthrough was codifying how AI independently identifies and fixes its own bugs. The metric was: competitors require re-prompting on every failure; Lovable ships unblocked. For VERSO, the parallel is the checkpoint/resume + HITL seam — the moment where a production agent hits a wall and VERSO's harness lets it recover without a rewrite. The framing: "we don't re-prompt the agent, we recover the run." This sharpens VERSO's reliability wedge language.
*Verdict: gives a demo-able framing for the durable/checkpoint seam — "unsticking" is the user-visible win.*

### [NEW-IDEA] §1 Bet/Moat: Scarcity-shift positioning ("who knows what to build")
The bottleneck has moved from "who can build" to "who knows what to build." For VERSO targeting the structurally-aware senior AI engineer, the parallel claim is: the bottleneck has moved from "who can run an agent loop" (solved; 10 lines) to "who knows how to make it reliable at scale." VERSO's bet-in-one-sentence could be: "The agent loop is solved. The harness is not." This directly leverages the scarcity-shift argument that made Lovable's positioning legible.
*Verdict: NEW headline framing for VERSO's bet — more concrete than "harness-is-moat" for external audiences.*

---

**Source quality note:** Full transcript is behind Lenny paywall. Content sourced from PodPulse.ai notes and Lovable.dev video transcript page. Quantitative data (ARR, stars, team size) confirmed across multiple sources. Core arguments and quote fragments are reliable; exact wording should be verified against original before attribution.
