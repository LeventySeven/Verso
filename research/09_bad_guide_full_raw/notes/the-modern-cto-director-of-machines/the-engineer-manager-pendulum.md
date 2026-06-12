# The Engineer/Manager Pendulum

**Source:** https://charity.wtf/2017/05/11/the-engineer-manager-pendulum/  
**Author:** Charity Majors  
**Date:** May 11, 2017 (updated July 14, 2023)  
**Status:** read_full  
**Themes:** strategy

---

## Faithful Digest

This is Charity Majors' canonical 2017 essay advocating for a deliberate career pattern of alternating between individual contributor (IC) and engineering management roles — not as compromise or failure, but as an intentional and structurally superior path. It is one of the most-cited pieces in tech career literature. The Verso relevance is indirect: it is positioned as guidance for the "Modern CTO / Director of Machines" archetype, i.e., the person who needs both deep technical competence and organizational fluency to direct AI-powered engineering.

### Central Thesis

> "Fuck the whole idea that only managers get career progression. And fuckkkk the idea you have to choose a 'lane' and grow old there. I completely reject this kind of slotting."

The essay argues that the best technical leaders — both managers and ICs — are people who have deliberately done both, serially. Not simultaneously.

> "The best frontline eng managers in the world are the ones that are never more than 2-3 years removed from hands-on work, full time down in the trenches. The best individual contributors are the ones who have done time in management."

### The Incompatibility of Simultaneous Excellence

The essay's most structurally precise claim is that management and engineering are _cognitively incompatible at high performance_:

> "Management is highly interruptive, and great engineering — where you're learning things — requires blocking out interruptions. You can't do these two opposite things at once."

> "5. Both code and people require the same thing to thrive: focused, sustained attention. No one does both well." — @sarahmei (quoted)

The hybrid manager+tech lead is described as "an unstable combination, because your engineering skills and context-sharpness are decaying the longer you do it." It is possible as a temporary state when promoting from within (credibility from just having built the thing), but it degrades and must eventually resolve to one mode or the other.

### On Management as a Role (Not a Promotion)

> "Management is not a promotion, management is a change of profession. And you will be bad at it for a long time after you start doing it. If you don't think you're bad at it, you aren't doing your job."

> "1. Becoming a manager is not a promotion - it's a lateral move onto a parallel track. You're back at junior level in many key skills." — @sarahmei (quoted)

The damage done by treating management as a promotion: talented engineers end up in roles they hate, burning out, and the senior IC pool is depleted of the "elder wizards we need."

> "Managing because it feeds your ego is a terrific way to be sure that your engineers get to report to someone miserable and resentful, someone who should really be writing code or finding something else that brings them joy."

### On the Tech Lead Role

> "A tech lead is a manager…but their first priority is achieving the task at hand, not grooming and minding the humans who work on it."

> "They still need the full manager toolset. They'll need to know how to rally people and teams and motivate them, or how to triage and restart a stalled project that everybody dreads. They still need to connect the dots between business objectives and technical objectives, and break down big objectives into components."

Tech leads are explicitly described as "usually spending more time in meetings than building things, and they will bitch about it but do it anyway, because writing code is not the best use of their time. Tech is the easy part, herding humans is the harder part."

### What the Pendulum Builds

> "Being an IC is like reverse-engineering how a company works with very little information. A lot of things seem ridiculous, or pointless or inefficient from the perspective of a leaf node."

> "Being a manager teaches you how the business works. It also teaches you how people work. You will learn to have uncomfortable conversations."

The claim: this cycle of alternation builds "immense breadth and strength" that neither pure-track career builds. Importantly, Majors describes her own signal for when to switch:

> "I start to feel like I know what I'm doing (…a telltale sign something's wrong)."

Competence in a role is a sign to rotate — because growth requires structured discomfort and novelty.

### Closing Prescription

> "It isn't a promotion, so you don't have any status to give up. Do it as long as it makes you happy, and the people around you happy. Then stop. Go back to building things. Wait til you get that itch again. Then do it all over again."

The essay is prescriptive and personal, and it is widely cited as having shaped career norms at companies like Intercom and Automattic ("We're supportive of the engineer/manager pendulum" appears in Automattic job postings quoted in comments).

---

## VERSO RELEVANCE

This essay's relevance to Verso is **indirect and strategic**, not architectural. It is in the "Modern CTO / Director of Machines" section of the reading guide, which is about who _operates_ Verso effectively, not about how Verso is built. The Verso operator/founder archetype is explicitly someone who swings between building and directing — and this essay is the canonical argument for why that is not compromise but structural advantage.

### Finding 1: The "Director of Machines" Archetype Requires Pendulum Credentials
[SHARPENS §12 positioning/GTM]

The essay defines the specific person who is best positioned to direct AI-powered engineering: someone who has done "both, serially, not simultaneously." This person has the hands-on engineering credibility to write real tools and evaluate real outputs, AND the managerial fluency to structure work, resolve conflicts, and connect business objectives to technical ones. The Verso founder/operator persona is this person.

> "Senior engineers who have both these toolsets are the kind of tech leads you can build an org around, or a company around. They get shit done. And they are rare."

For Verso's GTM and positioning: the primary adopter is not a junior engineer nor a pure manager — it is someone in the pendulum zone, recently an IC or actively bouncing. They can evaluate Verso's abstractions, tune the harness, and trust (or reject) what the agent produces.

**Verdict: confirm** — no design action needed, but this sharpens the Verso ICP (ideal customer profile) description: the "pendulum practitioner" who can direct machines because they've built things recently.

### Finding 2: Technical Sharp Decay is the Core Risk for AI Directors
[NEW-IDEA §12, strategy]

> "That gives them credibility, while they struggle with their newly achieved incompetence in a different role."
> "your engineering skills and context-sharpness are decaying the longer you do it."

In an AI-augmented world, this decay happens faster and the consequences are worse — a manager who hasn't been in the trenches recently cannot evaluate whether the agent's output is correct, whether the context engineering is sound, or whether the harness is being gamed. Verso's positioning can explicitly address this: the framework is designed so that a "director of machines" who wants to stay sharp can remain hands-on at the harness level (writing evals, tuning tools, reading loop traces) without needing to write all the business logic themselves.

This is a **product positioning insight**: Verso's harness transparency (run_stream, typed events, eval framework) keeps the director technically legible without requiring them to code everything.

**Verdict: sharpen** — Verso's §12 positioning should explicitly call out that the harness's transparency is what keeps the pendulum practitioner's "context-sharpness" intact as they operate AI systems.

### Finding 3: The "Comfortable is Wrong" Heuristic Applied to Framework Design
[NEW-IDEA §1 the bet, strategy]

> "I start to feel like I know what I'm doing (…a telltale sign something's wrong)."

Majors uses competence-comfort as a rotation signal. Applied to Verso's design posture: the framework team itself should treat "this abstraction feels stable and complete" as a warning to stress-test it against new model capabilities. When a layer of Verso feels "done," that's the moment to bring in the next model generation and see what breaks.

This is a meta-principle for Verso's product development cycle, not a user-facing feature. It is the personal analog of the "bitter lesson" (tactical workarounds churn; architecture persists) — but applied to the builder, not the framework.

**Verdict: resist** — this is too meta to act on directly; it's a disposition principle for the Verso team, not a design primitive.

### Finding 4: Management Teaches Conflict Resolution — Relevant to Human-in-the-Loop
[SHARPENS §6.1 durable runtime]

> "You will learn to have uncomfortable conversations. You will learn how to still get good work out of people who are irritated, or resentful, or who hate your guts. You will learn how to resolve conflicts."

The human-in-the-loop design in Verso's durable runtime requires the human operator to make hard judgment calls on agent output — reject, redirect, approve. The pendulum practitioner is uniquely qualified to do this because they've developed conflict-resolution and decision-under-uncertainty skills from management. This is an implicit qualification for effective use of Verso's HITL feature: the best operators are people who can hold an uncomfortable "this is wrong" judgment without being destabilized.

**Verdict: confirm** — this reinforces the ICP, but suggests Verso's docs should frame HITL interactions in terms of "the operator as a decision-maker, not just an approver."

---

## Summary Verdict

The Charity Majors essay is strategically valuable for Verso's §12 positioning and ICP definition, but has zero architectural content. Its core finding for Verso:

1. The ideal Verso operator is a "pendulum practitioner" — someone who has done both IC and management, recently enough to be technically sharp.
2. The risk of "technical sharp decay" is real and fast in AI-augmented organizations; Verso's harness transparency is a direct countermeasure.
3. No design primitives are changed by this essay.

This is read_full. URL: https://charity.wtf/2017/05/11/the-engineer-manager-pendulum/
