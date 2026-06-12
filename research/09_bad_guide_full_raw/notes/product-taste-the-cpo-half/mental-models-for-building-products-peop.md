# Mental Models for Building Products People Love ft. Stewart Butterfield

**Source:** Lenny's Podcast (Nov 20, 2025)
**URL:** https://www.youtube.com/watch?v=kLe-zy5r0Mk / https://www.lennysnewsletter.com/p/slack-founder-stewart-butterfield
**Speaker:** Stewart Butterfield (co-founder, Flickr and Slack)
**Duration:** 1h31m
**Transcript found:** Partial — Lenny's newsletter landing page is paywalled; content sourced from pod.wave.co episode digest + augusteo.com writeup + the original "We Don't Sell Saddles Here" Medium essay (public) + search-aggregated quotes. Status: read_partial.

---

## Core Frameworks and Arguments

### 1. Utility Curves
An S-curve where the horizontal axis is effort/cost and the vertical is value/convenience delivered. The curve has three segments:
- **Flat start:** initial investment produces near-zero user value
- **Steep middle:** a critical threshold where payoff accelerates sharply
- **Plateau:** diminishing returns; additional investment captures very little

**The decision heuristic:** Before committing to a feature, ask: Where are we on the curve? If the feature is in the flat zone, shipping it is actively harmful — users will encounter it, find zero value, and form a negative impression before you ever reach the value inflection. If you're past the plateau, stop investing. Most products fail because teams under-invest across the threshold (the feature "almost works") or over-invest past the plateau.

**Butterfield quote:** Implied — teams should use this to avoid "features that ship but fail before reaching value."

### 2. Tilt Your Umbrella
Observed in Vancouver: only ~1/3 of people walking in rain angle their umbrella to avoid poking passersby. The other 2/3 are oblivious. The metaphor becomes Slack's internal standard for product empathy: notice and fix small irritations that competitors ignore.

**Key insight:** "Your failure to be considerate and empathetic is an advantage you can create." Competitive advantage does not only come from big architectural bets; it accumulates from thousands of micro-acts of consideration. Emotional connections built through care drive organic word-of-mouth.

**Application in product:** Time-zone pickers, drag-and-drop, account creation flows — details most teams classify as "not worth the sprint" are precisely where you build durable affinity.

### 3. Friction vs. Comprehension (the real enemy)
**Common mistake:** Assume friction = bad, always reduce steps.
**Correction:** The enemy in low-intent contexts is not friction but incomprehension. When users don't understand what will happen next, they feel stupid and abandon — regardless of how few clicks are required.

**Slack examples:**
- Magic links (no password on mobile) — removes a comprehension barrier, not just friction
- Notification gradual adoption — start with all notifications, then suggest better defaults after 10 messages, not on day one
- The "Shouty Rooster" — when @everyone is typed, a visual warns about cross-timezone impact; shapes behavior without gate-keeping

**Corollary:** "Don't Make Me Think" is not about minimizing steps; it's about making every element trivially obvious so users never burn glucose wondering what happens next.

### 4. Owner's Delusion
Restaurant owners build websites with slow-loading hero images and unclickable phone numbers — despite having personally been frustrated by this exact pattern on other restaurants' sites. They forget their users are not a captive audience in the theater of their creation; they are busy, distracted people with minimal intent and zero loyalty to context.

**Quote (reconstructed from multiple sources):** "You have to take a breath, pretend you're a regular person, and then look at this again and see if it makes sense."

**Application:** Product creators systematically overestimate how much their users care, how much patience they have, and how well they understand the mental model of what they've built. Counteracting this requires deliberate perspective-shifts: user-testing, regularly pretending you are a first-time visitor.

### 5. Hyper-Realistic Work-Like Activities (HRWLA)
As organizations grow, the supply of "known valuable work" (tasks where both objective and value are clear) declines relative to headcount. Parkinson's Law fills the gap: work expands to fill available time. Managers hire subordinates because team size correlates with authority and compensation — not from malice.

The result: HRWLA — activities superficially identical to real work (A/B tests, meetings, analyses, reviews) that generate no value.

**Example from Butterfield:** Slack spent thousands of person-hours A/B testing whether to pre-populate the mention field in threads. Result: 0.03 message difference. Not worth it. But it looked exactly like real work throughout.

**The leader's obligation:** Ensure sufficient supply of "known valuable work." When people cannot find it, they will generate HRWLA to justify their existence. The problem is structural, not motivational.

### 6. "We Don't Sell Saddles Here" (Market Creation)
From the original 2013 memo sent to the Tiny Speck team before Slack's launch (https://medium.com/@stewart/we-dont-sell-saddles-here-4c59524d650d):

**Core argument:** The best way to find product-market fit is to define your own market. For genuinely new products, you cannot just compete on features against incumbents — the market doesn't yet know it needs you.

**The Acme Saddle Company analogy:** If you sell horseback riding rather than saddles, you grow the whole category and occupy the category leader position while discussing your saddle. The product becomes proof of a transformation, not a thing to be compared.

**The hard implication:** Because potential buyers don't yet recognize the need, tolerance for flaws is near zero. Butterfield's standard: execution "as smooth as lacquered mahogany." Every rough edge is a reason for an unconvinced prospect to walk away.

**What you're selling:** Not software. Not features. "Organizational transformation" — in Slack's case, "a reduction in the cost of communication" and "zero-effort knowledge management."

**Quote:** "The real, direct measure of 'innovation' is change in human behaviour."

### 7. When to Pivot
Butterfield has pivoted twice — Flickr from Game Neverending, Slack from Glitch. Both succeeded. His rule:

- Perseverance is over-glorified. "Hang in there" is not always correct.
- Pivot after exhausting every non-ridiculous path.
- The decision must be coldly rational, not emotional, because it requires publicly admitting failure.
- He shut down Glitch despite $9M remaining and ongoing success: the **expected value** of continuing had turned negative.

**Quote:** "Creating distance so you can make an intellectual, rational decision...rather than an emotional decision is essential."

### 8. Generosity as Strategy (Prisoner's Dilemma logic)
Acts of organizational generosity — 100x SLAs for downtime automatically applied, no charges for unused seats during COVID, direct listing structure that preserved employee equity — are not altruism. They signal cooperative intent in a repeated game, attract ethical employees, reduce internal friction, and build customer trust.

**Core mantra:** "In the long run, the measure of our success will be the amount of value we create for customers."

### 9. Taste is Learnable
Taste is not innate. It is built through practice, the same way culinary training works. Competitive advantage accrues from practicing taste in neglected product areas — because most teams don't bother.

**Butterfield in 2014:** "What we have right now is just a giant piece of shit...we should be humiliated that we offer this to the public." This is the standard-setting move of someone using dissatisfaction productively rather than defensively.

---

## VERSO RELEVANCE

### [SHARPENS] §7 + §12 — The "Tilt Your Umbrella" / taste-in-neglected-areas principle
Butterfield's competitive advantage from micro-empathy maps directly onto Verso's `inspect()` as a DX investment and the "knives-not-avocado-slicers" taste vector. Most agent frameworks don't tilt their umbrella on introspection ergonomics. The principle: the structural moat comes from practicing quality precisely where incumbents classify the task as "not worth the sprint."

Tag: SHARPENS §7 demo-able wedge / §12 positioning
Verdict: Towards the pitch — "we tilt our umbrella where others don't."

### [SHARPENS] §1 — Utility Curves as the harness investment model
The utility curve argument gives Verso a precise language for WHY the harness is the bet: the loop itself is past the plateau (10 lines, everyone ships it). The harness is still in the steep middle — enormous lift still available per additional investment. Competitors who keep investing in the loop are over-investing past their curve.

Tag: SHARPENS §1 bet/moat
Verdict: Use utility curves explicitly in investor/team framing of the product bet.

### [CONFIRMS] §12 Positioning — "We don't sell saddles here" = sell transformation, not framework
Already confirmed: the anti-"-er-than-LangChain" positioning rule. Butterfield's original essay provides the founding text for why category definition beats feature comparison. Verso sells "production-grade agents your team can actually own" (the horseback ride), not "a framework with typed events and checkpointing" (the saddle).

Tag: CONFIRMS §12 positioning
Verdict: The essay is the canonical reference for this principle; cite it explicitly in positioning sections.

### [NEW-IDEA] §12 GTM / Product-Market Fit — Market creation via behavioral metric
Butterfield: "The real measure of innovation is change in human behaviour." This suggests Verso's GTM health metric is NOT adoption but behavioral shift: does the lead move from "manual loop" to "harness-first" development pattern? Does the team ship their second and third production agent faster than the first? This is a measurable, behavioral leading indicator — not NPS or signups.

Tag: NEW-IDEA §12 GTM
Verdict: Define the behavioral shift metric explicitly; use it as the real PMF signal.

### [NEW-IDEA] founder_os — HRWLA as the enemy of builder-velocity
Butterfield's HRWLA framework is the organizational risk for any team that moves from 1 agent to 10. As internal tooling grows, the ratio of "real harness work" to "alignment theater" inverts. This is the leverage argument for the structurally-aware senior: they recognize HRWLA and refuse it. Verso targets exactly that person — the one who identifies fake-work patterns in their team's agent-building ritual.

Tag: NEW-IDEA founder_os (also feeds persona definition)
Verdict: Use HRWLA in persona writing — the "structurally-aware senior" is explicitly the person who has seen their team generate agent-building HRWLA and wants to eliminate it.

### [CONFIRMS] §2 Non-goals — Friction vs. Comprehension
The enemy is not friction but incomprehension. Verso's non-goal: don't reduce the framework to fewer API calls (that's "removing friction") — instead, ensure that what each primitive does is trivially obvious (that's "eliminating comprehension cost"). This is why `inspect()` and the `--durable` one-flag seam are the right defaults: they make the system's state legible, not just minimal.

Tag: CONFIRMS §2 non-goals / §7 product taste
Verdict: Articulate the distinction explicitly in API design notes.

---

## Source Notes
- Full Lenny's transcript is paywalled (paid subscriber tier). Content reconstructed from:
  - pod.wave.co episode digest (main framework summaries)
  - augusteo.com writeup (utility curves, friction/comprehension, HRWLA)
  - Original "We Don't Sell Saddles Here" Medium essay (https://medium.com/@stewart/we-dont-sell-saddles-here-4c59524d650d) — full text publicly available
  - Web-aggregated quotes from multiple podcast directories
- All frameworks above are well-corroborated across multiple independent sources; no invented content.
