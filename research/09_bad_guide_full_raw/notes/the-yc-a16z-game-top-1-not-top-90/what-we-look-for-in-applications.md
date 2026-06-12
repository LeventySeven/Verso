# What We Look for In Applications (a16z Speedrun)

**Source:** https://speedrun.substack.com/p/what-we-look-for-in-applications
**Author:** a16z speedrun partners (Emily Bennett, Marcus Segal, Fareed Mosavat, Kenan Saleh, Sam Shank, Josh Lu, Troy Kirwin)
**Format:** Multi-partner essay — medium length
**Themes:** founder_os, gtm_distribution, positioning

---

## Full Digest

This piece compiles signals from multiple a16z speedrun partners on what they look for when evaluating early-stage applications. It is a multi-voice document, so each section tracks a specific partner's framing.

---

### Co-Founder Relationships (Emily Bennett)

"Find co-founding teams that really know each other and have depth of relationship." Shared history — working together previously, college connections, or prior coding partnerships — creates better sustainability than recently-formed pairings.

The signal being sought: **durability of relationship under pressure**, not just complementarity of skills. Partners who have already navigated conflict together have demonstrated something that can't be faked in an application.

Josh Lu adds: "really clear, defined roles also helps us understand that the founders have worked through some conflict together."

---

### Velocity vs. Traction (Marcus Segal, Sam Shank)

Marcus Segal distinguishes these as distinct signals:
- **Velocity:** "how fast are they developing, releasing, and learning?" — a rate, not a level
- **Traction:** varies in quality; must be interpreted, not just measured

Segal values "founders talk to potential customers or find design partners" as a signal of customer engagement. Sam Shank provides the traction hierarchy:
1. Demo partnerships (lowest signal)
2. Short-term revenue contracts
3. Long-term recurring revenue with significant companies (highest signal)

**The implication:** velocity is a leading indicator; traction quality is a lagging indicator. At early stage, velocity is more predictive than any specific traction number.

---

### Ideas and Earned Insight (Fareed Mosavat)

"Ideas matter more than a lot of people think they do" because they demonstrate team effectiveness. Mosavat seeks "non-obvious stuff" and asks: "What's that thing you can teach me that I wouldn't have otherwise seen?"

He values founders who pursue "truth-seeker" approaches through market research — not founders who build a narrative around a market, but founders who genuinely mapped the terrain and found something hidden.

The SCQA framework: **Situation, Complication, Question, Answer** — lead with critical information within the first three sentences rather than building narrative suspense. This is the communication model Mosavat advocates.

---

### Market Validation (Kenan Saleh)

Saleh prefers "really great validation at the early stage than small amounts of traction." The signal:
- Talking to numerous customers about willingness to pay
- Mapping industry players systematically
- Understanding market history and competitor failures
- Meeting 30+ industry participants before building

The meta-point: validation is about *understanding the market*, not just *getting early users*. Founders who can explain why competitors failed and what they missed have done the real work.

---

### Interview Stage Signals (Multiple Partners)

From Emily Bennett: founders should be able to "brag about yourself in a way that builds deep conviction that if there are 50 teams trying to tackle this, you are the one." This is not about arrogance — it's about being able to articulate *specific unfair advantage* in a crowded field.

From Troy Kirwin: technical founders should be "a student of company building" beyond just product development. The implication: technical depth alone is insufficient; founders must have internalized how companies scale, not just how systems scale.

---

### Signals of Exceptionality (Fareed Mosavat)

"Founders are outliers, and what we want is evidence that you've done outlier things." Examples given:
- YouTube channels
- Unusual projects outside conventional career paths
- Work that demonstrates pattern-breaking rather than pattern-following

The signal is **prior outlier output**, not credentials or pedigree. A 10-year ML career at Google is less signal than a project that 50,000 developers adopted because it solved a real problem better than anything else.

---

### Common Mistakes Catalogued

- Over-emphasizing the product without articulating *why it matters*
- Neglecting team narrative — not explaining why you're the right people for this
- Inflated TAM claims
- Failing to articulate differentiation from competitors
- Weak validation evidence (no impressive advisors, buyers, or insider connections)
- Presentation issues: typos, burying important news, excessive slides (7–10 slide maximum)
- Missing or outdated LinkedIn profiles

---

## VERSO RELEVANCE

### [SHARPENS] Velocity over traction — Verso's early GTM metric is shipping velocity, not user count
**Finding:** Segal's velocity/traction distinction is the precise metric framework for Verso's early stage. The relevant metric is not "how many developers downloaded Verso" but "how fast are practitioners shipping with it, iterating their context engineering, and promoting ephemeral agents to durable ones?" That rate is the velocity signal. Any traction number (downloads, stars) is a lagging indicator with low quality; the velocity of practitioner iteration is the leading indicator.
**PRD section:** §12 (GTM, metrics)
**Verdict:** adopt-now — frame Verso's success metric as practitioner iteration velocity, not aggregate adoption numbers. Track "time from install to first promoted durable agent" as the core velocity metric.

### [NEW-IDEA] "Brag in a way that builds conviction that if 50 teams try this, you are the one" — Verso needs a specific unfair-advantage sentence
**Finding:** Emily Bennett's formulation is a direct test Verso must be able to pass. With LangChain, DSPy, Pydantic AI, CrewAI, and others in the space, the question "if 50 teams are building agent frameworks, why are you the one?" demands a specific answer, not a category claim. Verso's answer cannot be "harness-is-the-moat" (now consensus) — it must be specific: the seam (tactical-to-durable via one flag), the eval corpus flywheel, and the dogfood-first operating principle that generates production signal no framework-builder-without-production-users can match.
**PRD section:** §1 (moat), §12 (positioning, pitch sharpening)
**Verdict:** adopt-now — write the specific unfair-advantage sentence. Draft: "We run this on our own production agents, so every invariant we expose has been validated against real failure modes — no other framework builder has that loop closed."

### [CONFIRMS] "Student of company building" beyond product — Verso founder must show systems thinking at org level
**Finding:** Troy Kirwin's signal (technical founders must be students of company building, not just product development) maps to Verso's founding posture: the framework is not the company. The company is the flywheel: dogfood → evals → corpus → community → retained practitioners → more production signal. Demonstrating understanding of this flywheel is the "student of company building" signal.
**PRD section:** founder-OS layer
**Verdict:** confirm — the pitch must demonstrate understanding of the company flywheel, not just the product architecture.

### [SHARPENS] "What can you teach me that I wouldn't have otherwise seen?" — Verso's earned insight
**Finding:** Mosavat's "non-obvious stuff" test is a direct prompt for Verso's POV. The earned insight is: "We measured that a single uninstrumented context step compounds 10% reliability loss, and across 10 steps that's 65% failure rate. No one talks about this because no framework builder has to run their code in production. We do." This is a teachable insight derived from dogfood, not from literature review.
**PRD section:** §12 (positioning, POV / category design)
**Verdict:** sharpen — the "march of nines" / 0.9^10 finding should be the opening teachable insight in every pitch, talk, and Show HN. It passes the Mosavat test because it's derived from production experience, not theory.

### [NEW-IDEA] The SCQA framework as Verso's pitch structure
**Finding:** Mosavat's SCQA model (Situation, Complication, Question, Answer) is a specific communication structure that front-loads the insight instead of building to it. Applied to Verso: Situation = "every senior AI engineer now runs an agent loop in production"; Complication = "each uninstrumented step compounds 10% reliability loss — across 10 steps you're at 35% success rate"; Question = "how do you control the context without rebuilding everything as a graph?"; Answer = "Verso — the harness layer that makes the seam visible and promotable with one flag." This is more compressed and less narrative-dependent than a features-first pitch.
**PRD section:** §12 (positioning, GTM, pitch structure)
**Verdict:** adopt-now — adopt SCQA as the canonical pitch structure for Show HN, X posts, and any investor context. Front-load the complication.

### [CONFIRMS] 30+ customer conversations before building — maps to Verso's practitioner-first research discipline
**Finding:** Saleh's validation standard (30+ industry participant conversations, understanding competitor failure modes) is a process standard Verso should be able to demonstrate: conversations with practitioners who've shipped with LangChain, DSPy, raw API, about what failed, what cost them the most debugging time, what they wished existed. This is the "earned insight" that validates the positioning.
**PRD section:** §12 (GTM, validation)
**Verdict:** confirm — document the practitioner conversation count and failure-mode findings as evidence of real market validation.

---

## Summary Verdict

The a16z speedrun piece is rich with operational criteria that translate directly to Verso's pitch and early GTM. The three highest-value deltas: (1) the specific unfair-advantage sentence requirement, (2) SCQA as the canonical pitch structure front-loading the 0.9^10 complication, and (3) velocity (practitioner iteration rate) over traction as the correct early metric. The "student of company building" signal reinforces that Verso's flywheel narrative must be present in every investor context, not just the product architecture.
