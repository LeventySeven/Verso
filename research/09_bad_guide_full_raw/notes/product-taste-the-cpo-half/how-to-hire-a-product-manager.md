# How to Hire a Product Manager

**Source:** Ken Norton · Bring the Donuts  
**URL:** https://www.bringthedonuts.com/essays/productmanager.html  
**Published:** 2005, updated 2023  
**Status:** read_full  

---

## Faithful Digest

Ken Norton's founding essay on PM hiring is the most-cited piece in the field. Its central argument: product management's value is non-obvious (PMs are uniquely expendable — "in a world without PMs, everyone simply fills in the gap and goes on with their lives"), which means that *great* product management must prove its value through judgment, not mere coordination.

### The Six Hiring Criteria (ordered intentionally)

**1. Raw Intelligence ("Hire All the Smart People")**  
> "I'll take a wickedly smart, inexperienced PM over one of average intellect and years of experience any day."

Norton explicitly warns (2023 update) against brainteaser interviews: "At best, worthless. At worst, discriminatory." The replacement: structured work samples and situational problems with no predetermined correct answer.

**2. Strong Technical Background — with a caveat**  
Not CS degree–required, but engineering background helps for: relating to engineers, understanding technical trade-offs. The trap: "Former engineers who try controlling technical implementation will crash spectacularly." The point is not technical gatekeeping but *mutual credibility at the interface*.

**3. "Spidey-Sense" Product Instincts and Creativity**  
Explicitly "highly subjective, difficult to evaluate, and extraordinarily important." Norton believes some people *just know* what makes a great product. Three observable signals in interviews:

- **Independently echoing concerns the interviewer already had** — candidate identifies issues the hiring PM privately recognized without prompting.
- **Teaching the interviewer something new about the product** — "candidates who teach reveal they're unafraid to critique and likely intellectually superior."
- **Introducing innovative products before mainstream awareness** — great instincts correlate with early discovery.

Key interview questions surfacing taste:
- "Tell me about a great product you've encountered recently. Why do you like it?"
- "What do you dislike about my product? How would you improve it?"
- "How do you know a product is well designed?"
- "How do you decide what *not* to build?"
- "When do you know to cut corners for launch?"

**4. Leadership That's Earned**  
PMs "lead by influence," not authority. Reference checks with peers and ICs — not just managers — reveal actual leadership patterns. Key question set: "Is consensus always good?" / "What have you learned about saying no?" / "Who has ultimate accountability for shipping?"

**5. Ability to Channel Multiple Points-of-View**  
PMs must advocate for whoever isn't in the room — customers, engineering, sales, executives, marketing. Norton's implementation advice: include engineering, design, and marketing in the interview panel, each with explicit instructions ("Evaluate how well this person understands your challenges").

**6. Someone Who's Shipped Something**  
"Nothing is a better indication of someone's ability to ship great products than having done it before." Reference-check engineering counterparts and sales/marketing partners, not just managers.

### Startup vs. Big Company Difference

> "I'm not sure they're the perfect candidate, but they do seem suited for this very specific role, so let's hire them." This is deadly thinking at a startup.

Startups need strong generalists; specialization fits stable roles at scale. The startup PM hire is a bet on adaptability and judgment under uncertainty, not role-fit precision.

---

## VERSO RELEVANCE

### [SHARPENS] §12 Positioning — "the PM as proof of product judgment"

Norton's core move is making *product judgment* a first-class observable phenomenon — not background aesthetic preference, but something you can test: does the candidate echo unprompted concerns? Does the candidate *teach* the interviewer something about their own product?

This sharpens the Verso positioning argument: the framework cannot just *claim* product taste ("we are opinionated"). It must *demonstrate taste* through observable artifacts — the API shape, the inspect() surface, the one-flag durable diff. Taste is a testable property, and Verso's taste is tested by whether structurally-aware engineers feel the same recognition signal Norton describes: "they already knew what I was worried about, and they told me first."

**Verdict: sharpen** — The "independent echo" signal should inform how Verso documents its design rationale. The README / Show HN post should articulate the problem before the audience reads it, so that the audience says "yes, that's exactly the thing I'd been vaguely bothered by."

### [CONFIRMS] §7 Demo-able Wedge — making the implicit explicit

Norton's insight about taste-as-test reinforces the three-line side-by-side as the right demo shape: a structurally-aware senior engineer who sees the raw agent loop vs. the Verso harness should *independently echo* the recognition. The wedge is not explaining your product — it's showing someone their own half-formed concern resolved.

**Verdict: confirm** — already in the approach; worth stating explicitly in the launch copy.

### [NEW-IDEA] §12 GTM — "teach the interviewer something" as content strategy

The highest signal a PM candidate can give is teaching the interviewer something new about their own product. Translated to content/GTM: Verso's build-in-public content should routinely surface insights about *agent reliability/context-engineering/harness architecture* that the audience already suspects but hasn't articulated. Not "here is our feature," but "here is the uncomfortable truth about the problem you're living in." This is the content register that earns trust with structurally-aware engineers.

**Verdict: adopt-now** — this sharpens the X / Show HN voice. Every thread should open with the insight the reader was already carrying, unnamed.

### [NEW-IDEA] §2 Non-Goals — the "specialist trap" maps onto framework bloat

Norton's "deadly thinking at a startup" = hiring for a specific role when you need general judgment. Verso's non-goal parallel: building feature-specific primitives (email agent, Slack agent, retrieval agent) rather than general judgment primitives (context seam, eval surface, checkpoint). The allure of looking like you "cover more use cases" is the same trap as the specialist hire — it looks more complete and is actually weaker.

**Verdict: adopt-now** — use this framing explicitly in §2 (non-goals): "We don't build feature-shaped primitives. We build judgment-shaped ones."

### [SHARPENS] founder_os — the PM as non-authoritative leader

> "Product managers typically lack direct authority, instead leading by influence."

This applies directly to the Verso founder-OS layer: an OSS framework author has no authority over its users. Influence comes from: shipped artifacts that prove judgment, public reasoning that teaches the audience something about their own problems, and reference checks (community reputation via Show HN/HN/Twitter). Norton's criteria 3+4+6 (instinct, earned leadership, shipping) are the OSS equivalent of the PM's influence toolkit.

**Verdict: lock-defer** — useful framing for the founder-OS index (research/04_bad_guide_full), not for the PRD product sections.

---

## One-Line Verdict Per Finding

| Finding | Verdict |
|---|---|
| "Independent echo" as taste-test signal → shape README/Show HN to resolve the reader's half-formed concern | adopt-now |
| "Teach the interviewer" → content should surface the insight the audience was already carrying | adopt-now |
| Specialist-hire trap → non-goals should be "judgment primitives, not feature primitives" | adopt-now |
| PM-as-influencer → OSS author influence toolkit mirrors PM without authority | lock-defer (founder-OS) |
| Spidey-sense is testable, not merely felt → Verso taste must be demonstrable in API shape | sharpen |
