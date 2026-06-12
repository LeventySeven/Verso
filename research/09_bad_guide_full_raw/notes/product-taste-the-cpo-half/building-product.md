# Note: Building Product

**Source:** https://www.youtube.com/watch?v=C27RVio2rOs
**Mirror/Transcript:** Glasp summary + Q&A (https://blog.glasp.co/michael-seibel-building-product/), Medium summary (https://medium.com/@ignacio-al/building-product-by-michael-seibel-8dc6c1a3e68), Hackerpreneur notes (https://hackerpreneur.co/michael-seibel-building-product/), YC blog (https://www.ycombinator.com/blog/michael-seibel-building-product/), jotengine transcript link found but page returned empty content
**Author:** Michael Seibel
**Organization:** YC
**Format:** Talk · 59m
**Status:** read_partial — no verbatim transcript retrieved (jotengine returned empty content); sourced from four independent summary/notes sources with overlapping coverage, sufficient for faithful digest of the operational framework. Direct quote-level accuracy cannot be guaranteed for every line; notable quotes flagged where corroborated across sources.

---

## Faithful Digest

### Core Thesis

Seibel synthesizes operational lessons from 2000+ YC companies into a repeatable framework for early-stage product building. The talk is deliberately operational, not inspirational — it covers problem definition, customer identification, metrics setup, the dev cycle, and the pivot/iterate decision. Zero filler.

### 1. Problem Definition (The Clarity Test)

The problem statement must fit in one or two sentences. Direct quote (corroborated across sources): "If you need to write an essay to explain the problem you are doing it wrong."

Four diagnostic questions:
1. Can you state the problem clearly?
2. Have you personally experienced it?
3. Can you define the problem narrowly? ("How do we get the first indication this works?")
4. Is the problem solvable?

Quote: "Identifying the problem is the genius part."

Historical evidence: Google wasn't initially a search engine; Facebook wasn't a social network; Justin.TV wasn't a streaming platform. The business that succeeded in each case started with a narrowly-defined, real problem before it became a category.

### 2. Customer Identification

Critical rule: "It is not EVERYONE."

Five evaluation criteria for early customers:
- Frequency: how often do they face this problem?
- Intensity: how much does it hurt? (more intense = higher pricing potential)
- Willingness to pay
- Ease of finding them
- Are they "desperate" enough that their business fails without your solution?

Target the most desperate users first. Quote: "Don't listen to your non-user friends." Avoid customers who take advantage or complain constantly without paying (they drain support and generate false signal).

Pricing: Avoid deep discounts. Use third-party credits with clear expiration dates instead — this maintains price integrity while providing acquisition incentives.

### 3. Metrics Framework

Standard analytics (Google Analytics alone) is insufficient. Combine with event-based analytics (Mixpanel). Select 5–10 critical user tasks as KPIs initially. "Everyone in your company must understand how to use Mixpanel and read it."

Instagram early-stage KPI tasks example:
1. Open app
2. Create account
3. Take photo
4. Apply effects
5. Share photo

KPI selection principle:
- Revenue product → track revenue
- Free product → track usage
- "99% of times you should use those KPIs"

Seibel links metrics directly to features: "Tie features and experiments to moving specific numbers." This prevents the common trap of shipping features disconnected from observable user behavior.

### 4. The Product Development Cycle

Cadence: 1–2 week cycles maximum for web products. Any longer and you're collecting too much inventory risk (speculative features) before getting feedback.

Cycle process:
1. Write specs (before delegation, not after)
2. Brainstorm — record all ideas with no dismissal
3. Categorize by effort:
   - **Easy:** multiple completable per day
   - **Medium:** 1–2 days of development
   - **Hard:** one full dev cycle for one developer
4. Prioritize by KPI impact
5. Break "hard" items into smaller "easy" pieces to ship faster

Key anti-pattern: "If your process revolves around arguing, not writing specs, and long dev cycles, you are doing it wrong."

Quote: "Don't let perfect be the enemy of better." Ship MVPs quickly, even rough, to gather real user feedback through observation rather than just asking.

### 5. Pivot vs. Iterate (The Crucial Distinction)

**Pivot** = change the customer OR the problem (rare, should be deliberate)
**Iterate** = change the solution (common, ongoing)

This is the most operationally important distinction in the talk. Most founders confuse "the solution isn't working" with "the problem/customer is wrong." The correct default response when a solution underperforms is to iterate, not to pivot.

Quote: "It's going to take at least 2 years of constant iteration and shipping to reach product-market fit."

Quote: "Be willing to change your solution, not your problem/customers."

Don't pivot after just 2 months — you haven't given the solution enough iterations to determine whether the problem/customer is actually wrong.

### 6. The Real vs. Fake Steve Jobs Problem

Seibel warns against the "fake Steve Jobs" archetype: the founder who dreams and creates in isolation, divorced from market feedback. 

Quote: "Don't be fake Steve Jobs."

**Real Steve Jobs:** iterates and talks to customers continuously.
**Fake Steve Jobs:** treats product vision as art disconnected from users.

The distinction matters because the "visionary founder" mythos actively gives founders permission to stop talking to customers once they've convinced themselves they understand the market.

---

## VERSO RELEVANCE

### [SHARPENS] §12 GTM: The "desperate users first" targeting principle maps directly to Verso's cold-start
Seibel's "five criteria for early customers" — frequency, intensity, willingness-to-pay, findability, desperation — gives a concrete scoring rubric for Verso's Stage-1 cold-start. The primary persona (structurally-aware senior / AI engineer on 2nd/3rd production agent) scores high on intensity (production agent failures are business-critical), moderate on frequency (weekly iteration on reliability), and high on desperation (their current tooling has no structural answer to the eval/reliability problem). The "easy to find" criterion is weak for organic discovery but strong for targeted community seeding (AI engineers active in specific communities). This sharpens the atomic network targeting: don't just say "~5 vocal production leads" — find the ones for whom the current tooling is actively failing them.
**Verdict:** Score the target persona against Seibel's five criteria explicitly; it will sharpen cold-start targeting.

### [CONFIRMS] §1 Bet/Moat: 1–2 week dev cycles + KPI-linked features = the discipline Verso enables, not just preaches
Seibel's dev cycle framework is the operational context in which Verso's eval flywheel lives. AI engineers running 1–2 week cycles NEED a harness that gives them reliable ground-truth signal each cycle, not just at launch. This confirms that the eval-corpus flywheel is not a research feature — it's the instrument that makes Seibel-style tight iteration possible for agent teams. The "tie features to moving specific numbers" principle maps exactly to what Verso's eval trace engine provides.
**Verdict:** Confirms eval-as-iteration-instrument framing; strengthens the case that Verso is the Mixpanel for agent cycles, not a framework.

### [NEW-IDEA] Positioning: The "problem is the genius part" framing as a positioning sword for Verso
Seibel's claim that "identifying the problem is the genius part" (not the solution) gives Verso a defensive positioning angle against competitors who compete on solution features. The counter-position: "we got the problem right" (the harness is the moat; the loop is not where anyone competes). This is a direct application of Seibel's principle to Verso's own positioning — the problem Verso solves (structural reliability for production agents, with a tactical-to-durable seam) is the genius, not the API surface. Lead with the problem in external messaging, not the feature list.
**Verdict:** NEW framing anchor for positioning copy: "identifying the problem is the genius part" → Verso leads with the problem statement, not the solution inventory.

### [SHARPENS] §12 Positioning/GTM: Pivot definition sharpens the "non-goals are updatable" principle
Seibel's hard distinction between pivot (change problem/customer) and iterate (change solution) gives precision to VERSO's established principle that "non-goals are evidence-updatable, not identity." A non-goal that falls away is an iterate — changing the solution surface. A true pivot would mean changing the problem (harness reliability for production agents) or the customer (structurally-aware senior). These should be much harder to change. The discipline: track which changes are solution-level (iterate freely) vs. problem/customer level (pivot threshold much higher).
**Verdict:** Tighten the non-goals-are-updatable principle: be explicit about which non-goals are solution-level (free to revise) vs. problem/customer-level (pivot-grade commitment).
