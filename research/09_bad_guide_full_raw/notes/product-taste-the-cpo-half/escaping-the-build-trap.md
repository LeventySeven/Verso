# Escaping the Build Trap

**Speaker:** Melissa Perri
**Source:** Talk (multiple versions: Mind the Product SF 2017, Agile Arizona 2019); book distillation
**URL:** https://www.youtube.com/watch?v=jWfI8yXBLsM
**Duration:** ~26 min
**Transcript source:** Mind the Product write-up (mindtheproduct.com) + detailed book summary via Medium (t-ziegelbecker)

---

## Core Argument

Organizations fall into the "build trap" when they measure success by outputs (features shipped) rather than outcomes (customer value created). The remedy is restructuring around problems, not solutions — requiring changes to process, strategy, and culture simultaneously. This is not a PM technique; it is an organizational operating system.

---

## Key Frameworks

### 1. The Build Trap Defined

"The build trap occurs when organizations measure their success by outputs rather than outcomes."

The false linear model: **feature ideas + code = profit**. This produces endless feature factories where teams ship but don't know if anything worked. Perri's diagnosis: Agile taught teams *how* to build, not *what* to build.

The correct model: product development is a value-exchange system. Customers give money (business value) when their problems are solved (customer value). Product managers must optimize both sides simultaneously.

### 2. The PM Archetype Problem

Three bad PM archetypes:
- **Mini CEO**: Commands instead of explores; alienates cross-functional teams
- **The Waiter**: Routes stakeholder requests without prioritization or vision
- **Project Manager**: Manages timelines, not problems-being-solved

Great PMs: start from vision and deep user understanding, emphasize problems over solutions, align business goals with user needs, run systematic experiments, set clear success metrics.

### 3. Knowledge Category Framework

Four types of organizational knowledge:
- **Known knowns**: Table-stakes features — don't differentiate
- **Known unknowns**: Answerable through experiments
- **Unknown knowns**: Experience-based intuition — needs validation
- **Unknown unknowns**: Surprising customer discoveries from direct engagement

Product strategy is primarily navigating known unknowns and surfacing unknown unknowns.

### 4. Strategy as Decision Framework, Not Plan

"Strategy is not a plan but a framework that helps to make decisions."

Strategy connects vision to economic outcomes via:
1. **Vision** — long-term direction
2. **Strategic Intent** — 1-3 critical focus areas to reach vision
3. **Product Initiatives** — problems users need solved
4. **Options** — experiments and bets addressing those problems

Spotify's DIBB framework (Data → Insights → Beliefs → Bets) is cited as an exemplar.

OKRs link organizational cadences: executives (2-5 year cycles), leadership (1-2 years), PMs (quarters), teams (weeks).

### 5. Three Strategy Gaps

- **Knowledge Gap**: Leadership uncertainty → excessive information requests rather than alignment. Fix: define what you need to learn, not what you need to report.
- **Alignment Gap**: Leadership direction ≠ team action. Fix: outcome-focused goals with solution freedom (teams choose how to hit the outcome).
- **Effect Gap**: Planned ≠ actual outcomes. Fix: empower teams to learn and adjust mid-course.

### 6. The Product KATA

Four-step problem-solving loop:
1. Translate strategic intent into solvable problems
2. Evaluate current state through data
3. Determine solvable problem + measurement approach
4. Iterate: What's the goal? Where are we? What's the obstacle? What's our hypothesis? What did we learn?

The KATA is recursive — applied at every cadence level, not just quarterly planning.

### 7. Three Solution Exploration Methods

- **Concierge**: Manual, unscaled execution to prove value before building
- **Wizard of Oz**: Realistic-feeling experience with manual backend
- **Concept Testing**: Generative feedback on concepts without a working product

The Marketly example: team initially identified poor course-creation workflows; direct user engagement revealed the real problem was teacher inexperience with video uploading — solved with a written guide, not months of engineering.

### 8. Product-Led Organization Attributes

Culture requires:
- **Outcome-focused communication** — patience for outcomes; living roadmaps with themes + hypotheses + success metrics
- **Roadmap format**: Themes, hypotheses, goals, success metrics, development stage (Alpha/Beta/GA), milestones
- **Product ops unit**: alignment, capacity, goal integration, data automation
- **Rewards aligned to outcomes**, not feature counts
- **Bounded experimentation**: fail safely, inexpensively, fast
- **Venture capital mindset**: treat ideas as investment decisions, not annual plan line-items

### 9. "Fall in Love with the Problem"

The orienting principle. Shipping v1.0 is not the end goal. Iterating until desired outcomes are achieved is. The Marketly pivot from engineering months to a written guide is the canonical example: the solution was correct only after falling in love with the real problem.

---

## Key Quotes

- "The build trap occurs when organizations measure their success by outputs rather than outcomes."
- "Agile teaches how to build software but not what to build."
- "Strategy is not a plan but a framework that helps to make decisions."
- "Fall in love with the problem, not the solution."
- "The majority of people you're competing with are non-users." [echoed by Shear]
- "Bounded experimentation where teams can fail safely, inexpensively, and quickly."
- "Treat ideas as investment decisions rather than following artificial annual cycles."

---

## VERSO RELEVANCE

### §12 Positioning / GTM

**[SHARPENS]** The alignment-gap framing (leadership direction ≠ team action because goals specify *solutions* not *outcomes*) is a precise description of why "we built the harness" is the correct positioning frame for Verso. Verso's value prop is enabling outcome-focused work: the team picks its loop behavior; Verso makes the outcome (reliability, resumability, observability) measurable. This is outcome-infrastructure, not solution-prescription.

**[NEW-IDEA — positioning]** The "fall in love with the problem" orientation suggests Verso should name the *problem* in its positioning, not the solution. The problem: production agents fail quietly, invisibly, at scale, and recovery is a full rewrite. Verso's category claim should be anchored to this specific pain, not to "a harness framework."

### §7 Demo-able Wedge / Product Taste

**[SHARPENS]** The Marketly counter-example (don't build what you *think* the problem is — talk first) is a product-taste discipline that maps directly to the wedge design rule. The 3-line side-by-side demo should show the *problem* (silent failure, forced rewrite) before showing the solution (promote-in-place flag). Problem-first sequencing in demos is validated here.

**[CONFIRMS]** The bounded experimentation / "fail safely, inexpensively, fast" culture principle aligns with Verso's embedded-eval design: evals-in-process, not a separate SaaS portal. Perri's organizational prescription and Verso's technical architecture are solving the same problem at different altitudes.

### §2 Non-Goals / Principled Refusal

**[SHARPENS]** The "three bad PM archetypes" — especially The Waiter (routes requests without vision) — is a precise anti-pattern description for what Verso should refuse to be: a feature factory that adds whatever pattern the most vocal user requests. The non-goals list is not identity; it's upstream evidence about what a waiter-style framework becomes. Perri gives the organizational language for why Verso's principled refusals matter.

### §1 Bet / Moat

**[CONFIRMS]** The strategy-as-decision-framework (not plan) aligns with the harness-as-moat thesis. The seam between tactical and durable is a *decision framework* encoded in the API — one flag, one moment, you decide. This is the Verso equivalent of Perri's strategic intent: not a feature, but a decision surface.

### Verdict per finding

- Alignment-gap → "outcome infrastructure" positioning language for §12. Strong signal; validate with persona interviews.
- Problem-naming → name the failure mode in the positioning, not the solution. Ship to §12.
- Problem-first demo sequencing → show the struggling moment before the solution moment. Ship to §7.
- Bounded experimentation ↔ embedded evals → confirms architectural direction. Confirms.
- Waiter anti-pattern → hardening non-goals discipline. Confirms §2.
