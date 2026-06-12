# Do Things That Don't Scale
**Source:** https://paulgraham.com/ds.html  
**Author:** Paul Graham (Y Combinator)  
**Format:** Essay · ~20 min  
**Section:** B2B Go-To-Market (founder-led sales)

---

## Faithful Digest

### The Central Claim

Paul Graham's argument is structurally simple and almost universally ignored: **the way to get early users is to recruit them by hand, one at a time**. Founders wait for users to come to them. The ones who win go get them. The essay is a permission structure — it tells founders that the grind is not a sign of weakness, it's the method.

The frame is that startups are initially fragile and this fragility is normal. You don't need a viral loop or a channel strategy in week one. You need the first ten users, then the first hundred. Those come through founder effort, not through systems.

### The Collison Installation

Graham's most-cited example: the founders of Stripe (the Collison brothers) didn't send interested merchants a signup link. They said "right, let's get you set up" and did it on the spot. This became known as the "Collison installation." The key insight is that **the activation step that seems like it should be self-serve almost never is at the beginning** — friction kills conversion, and founders can eliminate friction by being present.

This is not just a recruitment tactic; it's an information-gathering system. Every manual setup teaches you exactly where the UX breaks.

### Compound Growth Dynamics

Graham gives the math: start with 100 users, grow 10% per week. After one year: 14,000 users. After two years: 2 million. The implication is that small weekly growth rates on a small base compound to massive outcomes — so the obsession with scale at week one is premature. What matters is the weekly growth rate, and what determines the weekly growth rate early is founder effort.

"The most common unscalable thing founders have to do at the start is to recruit users manually."

### Customer Delight as a Competitive Surface

Wufoo sent handwritten thank-you notes to each new user. Graham's framing: small startups can provide service levels that large companies cannot match. This is not charity — it's a competitive advantage that incumbents literally cannot replicate. The large company can't afford to send handwritten notes. The startup can, and it compounds into loyalty, word of mouth, and qualitative insight that large companies don't have.

"Though it doesn't scale, it's not wasted effort. You're giving users a level of service no large company could."

### Narrow Focus Creates Urgency

Facebook launched exclusively at Harvard before opening to other universities. This created urgency within a concentrated user base — the product felt scarce and relevant to a specific identity. The distribution lesson: early concentration creates a quality signal that broadcast launch does not. "You can only get so far by trying to please everyone."

### The Consulting Model

Graham recommends treating early customers "like a sole client" — doing everything for them, over-delivering, learning what they actually need vs. what you built. This is the phase before product-market fit, where the product is still wrong and the founder's presence compensates. The goal is to become so valuable to a small group that you know exactly what to build next.

"In effect, you're doing sales by doing consulting."

### What Doesn't Work

Big launches, massive partnerships, broadcast strategies. These are appropriate for companies that have already found product-market fit and need to scale a proven thing. Early stage, they create noise without signal and waste the narrow time window when a founder's personal attention can actually close users.

"Startups building things intended for the general public will also likely find that this initial period is the only chance they'll ever get to do such things."

### Hardware Caveat

Pebble hand-assembled early watches. This wasn't inefficiency — it was information. Manual assembly revealed design flaws that automated production would have baked in at scale. The principle generalizes: the unscalable version of anything teaches you what the scalable version needs to be.

### Airbnb's Near-Death

Airbnb nearly failed before the founders spent 30 days doing door-to-door recruitment in New York. This isn't a success story about a channel — it's a story about founders who almost quit, didn't, and discovered that manual effort was sufficient. The near-failure was caused by waiting for users to come. The recovery was caused by going to get them.

---

## VERSO RELEVANCE

### [CONFIRMS] §12 GTM — DX-Led Organic Is the Right Model, But "Collison Install" Has a Verso Analog

Graham's essay is the primary-source argument for Verso's already-established DX-led organic GTM (no sales motion, superconsumer-first). The confirmation is strong: the first 100 users should come through founder direct recruitment — Show HN, X threads, Discord DMs — not through a funnel.

But the Collison installation has a specific Verso analog that's worth naming: **the "Collison install" for Verso is a live pairing session where the founder helps a senior engineer integrate Verso into their existing project**. Not a signup link. Not a README. A real-time setup where friction is eliminated and the founder learns exactly where the DX breaks. This is the unscalable thing that teaches Verso how to make onboarding self-serve.

*Tag: [CONFIRMS] §12 GTM*  
*Verdict: adopt-now — explicitly plan Collison-install sessions with first 10-20 adopters; treat each session as a DX audit*

### [NEW-IDEA] §7 Demo-able Wedge — The "Delight First 10 Users" Frame Sharpens Wedge Sequencing

Graham's "delight a small number of users rather than a large number of mediocre users" reframes how to think about the demo-able wedge. The 3-line side-by-side and one-flag durable diff aren't just demo artifacts — they're the first delight moment. But delight requires that the user actually *experiences* the before/after, not just sees it in a README.

The implication: the first version of the wedge demo needs to be executed live, with the founder present, on the user's actual codebase. Not a toy example. The toy example is the Show HN artifact; the Collison install is the conversion moment.

*Tag: [NEW-IDEA] §7 demo-able wedge*  
*Verdict: adopt-now — design a "live wedge session" protocol: founder + user's codebase + real loop + one-flag promotion; 30-min session, documented outcome*

### [SHARPENS] §12 GTM — Narrow Launch Focus (Don't Be for Everyone)

Facebook's Harvard-first approach sharpens Verso's positioning constraint. The structurally-aware senior / AI engineer persona is the Harvard cohort equivalent — concentrated, high-density, good at spreading within their network. Launching to a broader persona (vibe-coders, ML researchers) before saturating the core persona would create noise without the signal that makes word-of-mouth work.

This confirms the non-goal (§2) of NOT targeting non-technical users and NOT trying to be LangChain-for-everyone. The narrow focus isn't just principled refusal — it's the growth mechanic.

*Tag: [SHARPENS] §12 GTM / §2 non-goals*  
*Verdict: confirm / sharpen — explicitly frame narrow persona as the growth mechanic, not a concession*

### [SHARPENS] founder_os — Manual Effort at Early Stage Is Not a Failure to Automate

Graham's essay is a permission structure: founders who do unscalable things are not failing to build a real business, they're doing the only thing that works at their stage. For Verso's founder-OS layer, this maps to: the right move is to personally respond to every GitHub issue, every DM, every failed Show HN comment. Not because you can't automate it — because the information value of doing it manually is irreplaceable.

"If you're building something that you yourself would use, and your friends use it, you've already got better feedback than most startups get from their first hundred users."

*Tag: [SHARPENS] founder_os*  
*Verdict: adopt-now — treat every early support interaction as a DX audit, not a support ticket*

### [NEW-IDEA] §12 Distribution — "Consulting Model" Has a Specific OSS Analog

Graham's "treat early customers like a sole client" has a specific form for OSS projects: **offer async pairing / office hours to early adopters**. Not for revenue — for information. The goal is to get close enough to real usage that you know what to build next. This is different from documentation or a Discord server; it's deliberately high-touch before the self-serve loop is ready.

*Tag: [NEW-IDEA] §12 distribution*  
*Verdict: adopt-now — launch "office hours" as a formal channel for early adopters; cap at 5/week, treat each session as a research session, not support*

---

## Load-Bearing Quotes

- "The most common unscalable thing founders have to do at the start is to recruit users manually."
- "Though it doesn't scale, it's not wasted effort. You're giving users a level of service no large company could."
- "In effect, you're doing sales by doing consulting."
- "You can only get so far by trying to please everyone."
- "Startups building things intended for the general public will also likely find that this initial period is the only chance they'll ever get to do such things."

---

## Verdict Summary

| Finding | Action |
|---|---|
| Collison install = live pairing session for Verso | adopt-now — plan first 10-20 as live DX audits |
| Live wedge session on user's codebase, not toy example | adopt-now — design "live wedge session" protocol |
| Narrow persona as growth mechanic, not concession | sharpen |
| Manual support = DX audit | adopt-now |
| Office hours as formal early-adopter channel | adopt-now |
