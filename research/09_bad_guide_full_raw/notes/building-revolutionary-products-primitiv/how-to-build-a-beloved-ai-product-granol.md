# How to Build a Beloved AI Product: Granola

**Source:** https://www.youtube.com/watch?v=IcbuTTVUY7M
**Format:** The MAD Podcast with Matt Turck (FirstMark) · 1h09m · Aug 21, 2025
**Speakers:** Chris Pedregal (co-founder & CEO, Granola), Matt Turck (host)
**Transcript status:** read_partial — no official MAD Podcast transcript found; reconstructed from multiple secondaries: Every's AI & I transcript (Dec 2024), Creator Economy writeup, StateOfBrand analysis, aividsummary, NessLabs, Spotify/Metacast episode description. The MAD Podcast episode itself (Aug 2025) overlaps heavily with these sources on the same decisions.

---

## What Pedregal Actually Argues

### The No-Bot Decision

Granola's single most decisive product choice: **no meeting bot joins the call; no audio is stored on a server.** Investors told them this was crazy. They refused to budge.

The mechanism: Granola runs locally on the user's laptop, captures audio through the system microphone (no special install on Zoom/Teams/Meet), transcribes locally via Deepgram and Assembly, processes with on-device echo cancellation, then destroys audio immediately. Nothing reaches a cloud server.

Pedregal's framing of why competitors' bots fail:

> "The product is telling every person in that meeting one thing: This conversation is being surveilled by a third party you did not choose."

The surveillance perception creates a behavioral change that corrupts the very data the tool is trying to capture — people speak differently, censor themselves, or organizations ban the bot outright. Granola's invisible presence is not a privacy gimmick; it is the prerequisite for the tool working at all in high-stakes conversations.

The strategic consequence: "The best AI meeting tool is the one nobody else knows is running."

### The 50% Feature Cut

During a year of stealth development (onboarding users individually, 100-150 beta users), the team cut roughly half the features they had built. The original real-time AI-assisted note-taking interface was found to be actively harmful:

> "If you have any kind of AI augmentation that happens real-time, you can't help but read [it]."

Users' attention left the meeting to read AI output, which is the opposite of the product's goal. The cut produced the current UX: user writes sparse notes during the meeting; AI fills in the gaps from the transcript afterward. Augmentation happens post-meeting, not in-flight.

Pedregal's decision rule whenever investors pushed back on cuts: "Those features would compromise who Granola is." He rejected additions when they would change the product's identity rather than extend it.

### Privacy as Trust as Memory Outsourcing

Pedregal's deeper argument: the real product is letting users **outsource their memory** to Granola. This requires a level of trust that cannot coexist with bot presence or audio retention.

> "We want to remove the busy work so that you can better apply your judgment."

The explicit non-goal: having AI agents handle tasks completely. Granola's target state is users retaining decision-making authority while shedding cognitive overhead. This is a deliberate philosophy, not a capability gap.

### Data Wedge: Why Meetings, Not Email

Two structural reasons Pedregal chose meetings as the data wedge:
1. Meetings create natural engagement hooks — calendar triggers, notifications users actively welcome
2. LLMs excel specifically at distilling long transcript streams into structured summaries (better fit than email summarization, which is noisy)

### Context Engineering Inside Granola

Pedregal describes their LLM usage:

> "Rather than prescriptive instructions, provide LLMs with situational awareness: meeting participants' roles, their priorities, and what matters to your users."

They route across OpenAI, Anthropic, and Google models dynamically (multi-model strategy), selecting per task. Transcription costs exceed LLM token costs — a counter-intuitive infrastructure reality at their scale.

### Targeting Strategy: Founders and Investors First

Deliberate initial focus on VCs and founders — "senior professionals with meeting-heavy schedules" making high-leverage decisions. This seeded word-of-mouth in the exact cohort whose endorsement carries the most market signal, while avoiding the "VCs only" product trap by diversifying early enough.

70%+ weekly retention is the headline metric they cite.

### Rule: Avoid Soon-to-Obsolete Problems

One of Pedregal's explicit product principles: don't build solutions to problems that model improvements will render unnecessary. Early Granola faced context window limitations; building workarounds would have burned engineering on infrastructure that became irrelevant when next-generation models extended windows natively.

> "You don't have a lot of users, which is amazing" — because small teams can afford frontier models and experiment with expensive features, anticipating future cost reductions.

### "Soul" as Design Principle

Pedregal invokes a concept of products having "soul" — an authentic human perspective at their core that users can feel. He cites Snapchat as a product with soul that "couldn't have been designed through focus groups."

Product decisions based on intuition, informed by 4-6 user calls weekly, rather than dashboards and metrics. Intuition requires mental space: "how did this make me feel?" requires slowing down, which conflicts with startup intensity. He addresses this by hiring strategically to reclaim time for product thinking.

### Future Direction

Beyond note-taking: cross-meeting insights, self-updating documents, post-meeting workflow automation (follow-up emails, ticket creation), eventually AI coaching that flags workplace blind spots. The vision is a "second brain" at the team level, not just individual.

---

## Selected Near-Verbatim Quotes

- "If you have any kind of AI augmentation that happens real-time, you can't help but read [the AI output]" — on why real-time suggestion UI was cut
- "We want to remove the busy work so that you can better apply your judgment" — on the human/AI division
- "The best AI meeting tool is the one nobody else knows is running" — on invisible architecture as product strategy
- "Those features would compromise who Granola is" — on investor pressure to add bots or audio storage
- "Rather than prescriptive instructions, provide LLMs with situational awareness" — on prompt/context engineering approach
- "You need to make product decisions based on your intuition" — on data vs. judgment
- "You don't have a lot of users, which is amazing" — on the startup AI cost advantage

---

## VERSO RELEVANCE

### [NEW-IDEA for §5.2 context / §5.3 tools] "Situational awareness" framing over prescriptive instructions

Pedregal's articulation of what makes LLM calls work — not prescriptive instructions but **situational context** (who is in the meeting, their roles, what matters) — is a practitioner validation of Verso's RunContext + ContextBundle.inspect() approach. The insight: good context engineering is about putting the model in the right epistemic position, not dictating its behavior. This is a user-facing explanation worth borrowing for Verso documentation/marketing.

**No-overkill verdict:** Strong practitioner confirmation of §5.2 context philosophy. Use in docs.

### [CONFIRMS §2 non-goals / §12 positioning] "Privacy as trust as memory outsourcing"

Granola's architectural constraint — no audio storage — is not a compromise; it is the mechanism that makes the product's core promise (outsource your memory) credible. This validates Verso's approach of building safety/trust constraints **into** the harness architecture rather than as add-ons. The user will not delegate memory (or agent execution authority) to a system they do not trust. Architectural trustworthiness is a product differentiator.

**No-overkill verdict:** Confirms §6.3 safety and §2 non-goals framing. Trust is structural, not rhetorical.

### [SHARPENS §5.1 loop / §4 seam] "No in-flight augmentation" — augment at the seam, not mid-loop

Granola's discovery that real-time AI augmentation breaks the user's cognitive flow maps directly onto agent design: injecting AI-generated content into an ongoing task loop (mid-execution tool suggestions, intermediate steering) can disrupt the human-in-the-loop more than it helps. Verso's HITL model sits at the durable seam — checkpoints, not interrupts. Pedregal's empirical finding supports putting human review at natural completion boundaries, not inline.

**No-overkill verdict:** Empirical support for seam-level (not mid-loop) HITL design in §4 and §5.1.
