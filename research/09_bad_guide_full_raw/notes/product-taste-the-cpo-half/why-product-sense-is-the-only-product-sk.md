# Why Product Sense is the Only Product Skill That Will Matter in the AI Age

**Source:** https://shreyasdoshi.substack.com/p/why-product-sense-is-the-only-product  
**Author:** Shreyas Doshi (ex-Stripe, Twitter, Google PM; creator of Product Sense course)  
**Publisher:** Shreyas Doshi Substack  
**Date:** 2023 (post-ChatGPT; references October 2022 tweet as pre-ChatGPT prediction)  
**Status:** read_full (WebFetch + WebSearch cross-verification)

---

## FAITHFUL DIGEST

### Core Argument

The article's logic chain runs forward from a plausible near-future:

> "Within a few years, every company that wants to remain competitive will be using AI for virtually every activity: user research, competitive analysis, design ideation, coding, testing, analytics, and more."

Since AI tools that confer advantage become common knowledge rapidly, selecting or adopting better AI tools cannot be a sustainable career or competitive moat. Therefore: the differentiation must come from the *judgment humans apply to AI outputs*, not from the outputs themselves.

The central claim: "the only real long-term career moat for product people is how you can improve on the already-brilliant, already-comprehensive inputs and outputs that AI will provide."

### The "Working Backwards" Structure

Doshi uses an explicit working-backwards structure: he examines a sufficiently advanced point in time (1-2-3-5-7 years), establishes what will be true (AI tool parity across competitors), then asks what differentiates. This is not speculation — it's a forcing function for identifying which skills are structural vs. contingent.

The analog: "Spreadsheets didn't make everyone a great analyst." The tool's availability is table stakes; the judgment applied to tool outputs is the actual value layer.

### Product Sense — Five-Component Decomposition

Doshi decomposes Product Sense into five interconnected skills. Critically, he argues that dropping *any one* of the five creates a visible blind spot:

1. **Strong empathy** — understanding needs beyond what AI analysis surfaces; the human signal AI can't fully capture
2. **Excellent simulation skills** — anticipating future possibilities based on domain knowledge; modeling second-order effects before they materialize
3. **Stellar strategic thinking** — identifying key segments and differentiators; knowing which surface area matters for which audience
4. **Great taste** — selecting the optimal recommendation from among several plausible options, aligned with business goals and user needs simultaneously
5. **Creative execution** — conceiving unique features or approaches that competitors cannot easily copy

The interdependency argument: "Empathy without taste gives you someone who knows what users want but can't pick the right tradeoff. Taste without simulation gives you someone with good instincts but no ability to anticipate second-order effects." The five are load-bearing together.

### Survival vs. Differentiation

Doshi draws a sharp distinction:

- **Survival tier (table stakes):** Building effective systems around AI — data pipelines, feedback loops, eval infrastructure. Separates "will survive" from "will become obsolete." Required but not differentiating among well-organized companies.
- **Differentiation tier:** Product Sense. Among companies that have cleared the survival tier, this is what determines who wins.

### The Seven Powers / Enduring Advantages Connection

Doshi references his broader framework of enduring competitive advantages in the AI era: exclusive data, uniquely correct insights, optimal UX, distribution/bundling, niche business models, regulatory advantages, and long runway. His claim: "Product Sense drives most of these outcomes." A strong Product Sense practitioner identifies and builds toward whichever of these powers is accessible in their context.

### Self-Reference as Evidence

Doshi notes the October 2022 tweet (pre-ChatGPT) where he identified this shift, arguing he created his Product Sense course *because* he anticipated the change. This is a subtle credibility move: the prediction preceded the obvious evidence, so it's not hindsight-fitted.

### Shift in Degree, Not Kind

The article ends with a key nuance: "This represents a shift in degree, not kind." Existing advantages — brand, data, relationships, taste — matter more in an AI-native world precisely because execution capabilities become equalized across competitors. The human differentiators are amplified, not eliminated.

---

## VERSO RELEVANCE

### §1 Bet / Moat [SHARPENS]

Doshi's survival-vs-differentiation framing maps precisely onto Verso's positioning problem. The survival tier for agent teams is: build eval infrastructure, close the observation loop, don't fly blind. Verso is the artifact that clears that tier *structurally* (it's built-in, not bolted-on). But Verso's actual differentiation claim is a rung above: it enables the Product Sense loop (simulate, taste, execute) to operate at the *agent* layer rather than the product layer. The one-flag durable promotion is a simulation primitive; `agent.inspect()` is a taste-feedback surface. Verso is not selling evals — it's selling the capability to exercise judgment at the agent layer at the same cadence as at the product layer.

**Verdict: SHARPENS** — adopt-now as a two-tier framing for Verso's positioning (survival tier / differentiation tier)

### §12 Positioning [SHARPENS]

Doshi's five-component model gives Verso a vocabulary for what the harness actually enables vs. what the loop (LangChain etc.) provides. A graph-first framework handles execution mechanics (simulation is implicit, not explicit). Verso explicitly surfaces simulation (the one-flag durable path for testing what checkpoint/resume feels like before committing), taste (inspect() as a feedback surface for which agent decisions to revisit), and creative execution (the seam design that enables "never a rewrite"). This is a precision positioning move: Verso doesn't just run agents, it enables Product Sense *at the agent layer*.

**Verdict: SHARPENS** — lock-defer (powerful but needs careful translation to avoid sounding like marketing)

### §7 Demo-able Wedge [NEW-IDEA]

Doshi's simulation skill ("anticipating future possibilities based on domain knowledge; modeling second-order effects before they materialize") directly maps to Verso's one-flag promotion demo. The side-by-side is literally a simulation artifact: "here is what your agent does today (ephemeral); here is what it does after promotion (checkpoint/resume/HITL) — same logic, different durability." The demo should be framed as *enabling simulation of your agent's second-order behavior* — not just "easier durability" but "you can actually reason about what happens at step 7 before you deploy."

**Verdict: NEW-IDEA** — adopt-now as a reframe for the one-flag demo narrative

### §2 Non-Goals [CONFIRMS]

Doshi is explicit: AI tools are table stakes; Product Sense is the differentiator. Verso should not claim to be the thing that makes agents good — it claims to be the thing that makes agent-building teams fast enough to iterate their way to good. The harness clears the survival tier; the human judgment does the differentiation. This is already in Verso's "explain it without AI" register.

**Verdict: CONFIRMS** — no delta

### Founder-OS Layer [SHARPENS]

Doshi's five skills (empathy, simulation, strategic thinking, taste, creative execution) are exactly the operating surface for Verso's founder. The dogfood-first discipline maps to: (1) empathy through using your own agent in real workflows; (2) simulation through the one-flag promo; (3) strategic thinking through the eval corpus analysis; (4) taste through inspect() — surfacing the judgment calls the agent makes; (5) creative execution through the seam design (one-rewrite-never). Verso's founder OS should be explicitly structured around these five practices applied to the agent layer.

**Verdict: SHARPENS** — adopt-now in founder-OS index (research/04_bad_guide_full)

---

## TOP DELTAS FOR RETURN

1. **[SHARPENS / §1+§12]** Survival tier (eval infrastructure) vs. differentiation tier (Product Sense at the agent layer) — Verso positions as clearing both, not just one. Two-tier framing for positioning.
2. **[NEW-IDEA / §7]** One-flag promo demo = *simulation* primitive in Doshi's sense: makes second-order effects of the durable path visible before commitment. Reframe demo narrative accordingly.
3. **[SHARPENS / founder_os]** Doshi's five skills (empathy/simulation/strategic/taste/creative) applied to the agent layer = the behavioral substrate of Verso's founder-OS operating principles. Map each to a Verso practice.
