# Note: Karri Saarinen's 10 Rules for Crafting Products That Stand Out

**Source:** https://www.figma.com/blog/karri-saarinens-10-rules-for-crafting-products-that-stand-out/
**Author:** Karri Saarinen, CEO & Co-founder of Linear
**Published:** March 10, 2026 (Config 2025 talk writeup)
**Format:** Essay / blog post (medium length)
**Status:** read_full (WebFetch returned full argument structure; supplemented by multiple secondary sources confirming verbatim phrases)

---

## Faithful Digest

Saarinen's thesis: in a crowded software market, craft is the last real differentiator. The "move fast and break things" era no longer resonates with a design-conscious buyer class. Quality is not an aesthetic preference — it is a strategic posture that must be installed at the leadership level and propagated through every team structure, hiring decision, and process norm.

### The 10 Rules (with load-bearing specifics)

**Rule 1 — Commit to Quality at the Leadership Level**
Craft must be the CEO/founder's most visible organizational priority — not a stated value but a permission structure. Saarinen's diagnosis: "companies often fail by stating craft is important without implementing it strategically." The gap between declared value and operational reality is where quality dies. Leaders who don't personally review and reject work below standard send the real signal.

**Rule 2 — Build Small, High-Quality Teams**
"Smaller teams with fewer opinions produce better work faster." Output metrics are the wrong signal. The hiring frame shifts: find people who already produce excellent work and already hold high standards — then create an environment that keeps those standards visible. Cultural dilution from fast headcount growth is a primary quality-killer (Linear intentionally caps at ~doubling per year, stayed ~80 people at $1.25B valuation).

**Rule 3 — Eliminate Handoffs**
"At Linear, there's no handoff to dev." Everyone understands implementation and shares accountability for the quality outcome. Specialized silos produce local optimizations and diffused ownership — no one is responsible for the final felt quality because everyone is responsible only for their slice.

**Rule 4 — Avoid Over-Specialized Product Teams**
Rigid per-feature team structures create quality inconsistencies across the product — different teams developing different quality thresholds, different tastes. Rotating responsibilities keeps ideas fresh, prevents teams from becoming siloed defenders of their single feature, and maintains a coherent product-wide aesthetic.

**Rule 5 — Treat Specifications as Baselines, Not Goals**
Key verbatim: "The spec is the baseline, not the finish line." A door that opens technically functions — craft demands that the door opens well, feels right, closes with the right sound. Excellence requires going beyond meeting the specification, treating it as the floor not the ceiling.

**Rule 6 — Quality Isn't Perfection**
Public release requires meeting quality thresholds, not perfection. The threshold is qualitative and hard to quantify — "success appears in organic conversations about quality solutions." Beta users help shape this. The point: quality ≠ infinite polish; it's a defensible bar, iteratively raised.

**Rule 7 — Design with Opinion**
"Great products serve specific users intentionally. Designing for everyone produces mediocrity; specificity creates stronger market positions and user trust." Saarinen's formulation: "You should design something for someone. It's impossible to design something really good for everyone." Opinionated software with a strong workflow model outperforms the customizable sandbox because it does the thinking for the user in the right way.

**Rule 8 — Reduce Scope to Increase Quality**
"Building one feature exceptionally well, then gathering feedback, works better than spreading effort thin across many features." People struggling with quality are almost always attempting too much. Scope reduction is a quality strategy, not a compromise.

**Rule 9 — Establish Values Over Rigid Processes**
Rather than prescribing methods, Linear establishes principles that guide *how teams think*. Direct user access through shared Slack channels keeps teams empirically connected to customer problems (vs. getting feedback through PM-mediated filters).

**Rule 10 — Question Data-Driven Decision-Making**
Linear avoids A/B tests and data-driven decisions in favor of cultivating team intuition. Verbatim: "You can't expect data to tell you how to surprise users." Quality requires informed expert judgment from people who understand both product and business context. The critique: data tells you what happened, not what should happen — and the surprise/delight dimension of craft is never in the dataset.

### Synthesis from secondary sources (Antoine Buteau / First Round supplemental coverage)

Additional Saarinen quotes confirmed across sources:
- "Quality is our first principle. Every other metric and decision flows from that."
- "High quality builds irrational loyalty where users won't leave."
- "Startups compromise quality for metrics. We win through quality-first."
- "We curate, not scale, when it comes to people."
- "Nobody enjoys corporate complexity. We build for builders."
- "Don't boil the ocean — just boil the pot."

On profitability as quality-preservation: Linear is "net negative lifetime burn" (more cash than ever raised), which creates operational independence from external pressure. This enables quality prioritization without the compromise that fundraising pressure introduces.

On word-of-mouth as the growth model: Linear does not run aggressive marketing — product quality drives natural advocacy. This implies the flywheel: quality → irrational loyalty → word-of-mouth → ICP-matched users → richer feedback → better product → quality.

---

## VERSO RELEVANCE

### [CONFIRMS] §7 — Demo-able Wedge as a Taste Surface
Saarinen's Rule 5 ("spec is the baseline, not the finish line") directly validates Verso's stance that the demo-able wedge (3-line side-by-side, one-flag durable diff, agent.inspect()) must exceed what "technically works." The inspect() surface, the seam API, the zero-rewrite promotion — these must each be crafted above spec level, not merely functional.
**Verdict:** confirm — already in PRD, sharpens the execution bar.

### [SHARPENS] §12 — Positioning / Category Design
Rule 7 ("Design with opinion / design for someone") sharpens the Verso persona lock. The structurally-aware senior/AI engineer persona is not just a targeting choice — it is the design constraint that makes the product coherent. "Designing for everyone produces mediocrity" means the impulse to add escape hatches, configurable everything, and "but you can also do it this way" paths is a quality-destroyer, not a feature. Verso's non-goals (§2) should be framed as the *opinionated refusal* that makes the product work for its someone.
**Verdict:** sharpen — §2 non-goals should be written as the design-with-opinion constraint, not just a scope limit.

### [NEW-IDEA] §1 / §12 — "Quality builds irrational loyalty → users won't leave"
This is a 7-Powers framing Saarinen lands without naming: irrational loyalty = switching costs + brand power simultaneously. For Verso, if the harness + seam become the user's operational model, the switching cost is not just API migration — it's abandoning a mental model. This is the same mechanism Linear exploits: the "cycles" workflow becomes how ICs think about work, not just how they track it. The corollary for Verso: the harness should become how AI engineers think about reliability, not just how they implement it.
**Verdict:** adopt-now — add to §1 (moat section) as "mental model capture" alongside API switching costs.

### [SHARPENS] §7 / Founder-OS — Anti-A/B-test + intuition cultivation
Rule 10 (no A/B tests, cultivate expert intuition) is directly relevant to Verso's embedded in-process evals stance. Verso's argument against LangSmith-style external eval dashboards is partly this: quantitative dashboards cannot tell you how to *improve* quality, only whether it changed. Saarinen's point that "data tells you what happened, not what should happen" is a clean articulation of why evals-as-intuition-building (embedded, in-loop, confronting the AI engineer with the regression directly) beats evals-as-monitoring. This gives Verso a quality-philosophy framing that connects Linear's operating principle to the eval design choice.
**Verdict:** sharpen — use Saarinen's intuition-cultivation framing when explaining why embedded evals beat external dashboards.

### [CONFIRMS] Founder-OS — Small team / curator mentality / no-handoff culture
Rules 2, 3, 4 (small teams / eliminate handoffs / avoid over-specialization) confirm the Verso dogfood-first, personal-infra operating posture. The framework should be built and maintained the way Linear builds Linear: small connected team, shared accountability for quality, no handoffs between "the AI part" and "the rest of the app."
**Verdict:** confirm — validates the personal-infra / solo-or-small-team build posture as quality-preserving, not constraint.

### [NEW-IDEA] §12 — "Multiple launches" as GTM principle
From secondary sources: Linear does "multiple launches" rather than a single big-bang release — "repeated launches compound interest and build brand narrative over time." For Verso's X build-in-public + Show HN channel strategy, this means each new primitive (stream transport, one-flag durable, agent.inspect()) should be a distinct launch moment, not held until a "complete" v1. The narrative compounds across each launch.
**Verdict:** adopt-now — structure Verso's OSS GTM as a launch sequence, each primitive = one Show HN / thread.

---

## One-Line Verdicts per Finding
- Rule 5 / spec-as-baseline → Verso taste bar: **confirm, already in PRD**
- Rule 7 / design-for-someone = §2 refusal frame: **sharpen — rewrite non-goals as opinionated constraint**
- Irrational loyalty = mental model capture as moat: **adopt-now — add to §1**
- No A/B tests / intuition framing → embedded evals philosophy: **sharpen**
- Small/curated/no-handoff = dogfood quality posture: **confirm**
- Multiple launches → Verso OSS GTM sequencing: **adopt-now**
