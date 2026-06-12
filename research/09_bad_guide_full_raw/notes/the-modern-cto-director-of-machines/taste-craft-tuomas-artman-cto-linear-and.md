# Taste & Craft: Tuomas Artman (CTO Linear) and Gergely Orosz

**Source:** https://www.youtube.com/watch?v=wjk0ulMAkbc  
**Speakers:** Tuomas Artman (Co-founder & CTO, Linear) + Gergely Orosz (@pragmaticengineer)  
**Format:** Talk at AI Engineer Europe 2026 · ~29 minutes · April 21, 2026  
**Transcript status:** No official transcript found. Content reconstructed from: (1) tldrecap.tech full recap (tldrecap.tech/posts/2026/aie-europe/ai-taste-competitive-advantage/); (2) webconsulting.at AI Engineer Europe 2026 summary; (3) finance.biggo.com Artman prediction article; (4) startuphub.ai AI Engineering: Scaling Quality Over Speed; (5) Artman's own X posts. The video was not accessed directly.

---

## What Artman Actually Argues

### Core Thesis: Taste Is the Moat After AI
The central claim: when code generation is trivial, the scarcest input becomes **taste** — "the instinct for sound design, appropriate abstractions, and consistent opinionation." AI lowers the cost of implementation to near-zero; the bottleneck shifts entirely to judgment about what to build and how it should feel.

Quote: "Great products come from saying 'no' to 999 things to ensure the one thing you ship is perfect." (Jobs philosophy, which Artman endorses as even more critical under AI.)

### The Shipping Trap: AI Removes the Natural Gate
Pre-AI, engineering difficulty acted as a natural filter forcing deep thinking before committing to implementation. AI eliminates this constraint. The result is "convoluted software and fractured user experiences from feature bloat" — teams say yes to everything because implementation is cheap.

The paradox: moving faster in wrong directions is worse than moving slowly in right ones. The primary risk in AI-era software is not execution speed but **direction quality**.

### AI's Taste Limitation: The Animation Experiment
Artman's most specific demonstration of where AI fails:

Emil Widlund's animation experiment: AI-generated animations were functionally correct (technically completed the transition) but felt unnatural. The AI could optimize a parameter (one second vs. two seconds) but couldn't perceive whether the timing *felt* right to a user.

Direct quote: "It knows that one second is better than two seconds, but it doesn't know whether two seconds is slow enough."

The limitation is not about complexity or capability — it's about the absence of felt experience. AI cannot feel frustration at a slow interface, cannot notice that an animation has unnatural easing, cannot perceive the difference between "correct" and "delightful."

Current measurement: AI automatically fixes ~10% of Linear's bugs. It excels at objective technical tasks (clear right/wrong answer) but fails at tasks requiring aesthetic or perceptual judgment.

### Quality Wednesdays: Making Taste Institutional
**Mechanism:** 25-person engineering team, 30-minute weekly call, every engineer must demonstrate one quality fix they implemented that week.

Examples of the types of fixes: one-pixel misalignments, 150ms button fade-out timing.

**Scale:** 2,500–3,000 minute details fixed through this practice.

**Purpose beyond the fixes:** creates a "psychological shift toward constant quality vigilance." Engineers stop treating quality as a project phase and start treating it as a continuous property of the product.

**Origin story:** Artman realized a tiny menu in the app had 35 hidden UI problems. This triggered the realization that quality rot is invisible until you look systematically.

Context from Artman's own X post (August 2024): "We have a separate ongoing process for things that could work slightly better. We have quality Wednesdays where each team member shows off at least one thing that they've slightly improved in the product in the previous week."

### Zero Bug Policy: Bugs as Priority Inversion
**Mechanism:**
- AI automatically assigns reported bugs to the relevant engineer
- Bug becomes highest priority; engineer drops everything else
- Target resolution: 7 days; many fixed within 2–3 hours
- Linear paused all feature work for 3 weeks to achieve zero bug count

**Rationale:** "Fixing bugs today costs same effort as later, preserves product pristineness." More precisely: bugs get fixed eventually regardless; fixing immediately means customers discover the fix within 24 hours of reporting, turning every bug into a customer delight moment rather than a customer frustration incident.

The economics argument: the marginal cost of fixing early vs. late is essentially the same; the customer-relationship value of fixing early is dramatically higher.

### The Product Engineer as the New Role
**Prediction:** "You won't be needing engineers that sort of pipe data from one place to another." Generative AI will eliminate demand for engineers whose core value is translating requirements into implementation code — specifically within four years.

**What remains essential:** "You still will be needing engineers who know what a customer wants and what a good feature looks like or what a good user experience looks like."

Direct quote: "Everybody will become a product engineer in some sense" — functioning as a mini product manager who works directly with customers, defines features, and has strong design sensibility.

**Linear's hiring process as filter:** one-week paid trial building a greenfield project. Filters for "why" (product sense) over "how" (implementation speed). The paid trial also functions as a signal of seriousness — candidates who care about the craft complete it.

**Engineer exposure to customers:** all engineers have access to customer feedback via shared Slack channels and recordings. Goal: engineers become informed about pain points, not just executing tickets handed down by PMs.

### Opinionated Software: Constraint as Feature
Linear deliberately constrains flexibility rather than accommodating every workflow. The system enforces one preferred approach, reducing decision fatigue and accelerating execution.

This is directly counter to the "infinitely customizable enterprise software" pattern — which Artman implicitly argues paralyzes users through choice and obscures the product's point of view.

**AI PM integration:** Linear embeds AI not as a chatbot addon but as a first-class product component handling triage, backlog grooming, and issue creation. Deep MCP integrations let developers launch local agent sessions directly from issues.

### Quality Measurement: The Slow Erosion Problem
On why quality effects are hard to measure: "Quality effects appear gradual — Uber focused on revenue/trips while competitors like Lyft shipped superior-feeling apps, causing slow user migration rather than sudden drops."

Quality degradation is invisible in metrics until it's catastrophic. This is why taste cannot be delegated to dashboards — the lag between quality decline and metric movement is long enough that damage is permanent by the time it registers.

Artman's prescription: rely on design judgment and intuition rather than "endless optimization loops and performance dashboards." Trust human expertise over algorithmic guidance for quality judgment.

### Closing Recommendations
Engineers who want to develop product sense should:
- Build and ship personal projects; listen to early users
- Study "Apple's Human Interface Guidelines" as UX gold standard

On pace in the AI era: move faster by automating mindless tasks (targeting 100% bug-fix automation) to allocate more human time toward design and UX — not by compressing the quality judgment cycle.

---

## VERSO RELEVANCE

### [NEW-IDEA — §5.5 evals + §12 positioning]
**Finding:** The "taste gap" — AI fixes ~10% of bugs automatically but cannot perceive felt quality — is a concrete, quantified statement of where human judgment remains irreplaceable. For Verso's eval design: `define_outcome(bounded)` must include a class of outcomes that cannot be measured programmatically (user felt experience, timing perception, aesthetic coherence). These require human judges, not automated scorers. The judge-panel design is not a workaround for missing metrics; it's the correct evaluator for taste-dependent outcomes.
**Verdict:** Sharpens the claim for human-in-the-loop evals; "AI knows 1s > 2s but not whether 2s is slow enough" is a memorable framing for why bounded outcomes need human graders.

### [SHARPENS §12 — positioning]
**Finding:** "Great products come from saying no to 999 things." The shipping trap (AI makes yes-to-everything cheap) is the exact failure mode that an opinionated framework prevents. Verso's hard invariants (no graph for tactical agents, native Python is THE tool path, loop <200 lines) are not just simplicity — they are the framework exercising taste on behalf of the user. The invariants ARE the product saying no.
**Verdict:** Reframes Verso's hard constraints as product taste, not just engineering preferences — strong positioning move.

### [CONFIRMS §5.1 — loop]
**Finding:** "Move faster by automating mindless tasks to allocate more human time toward design and UX" directly confirms the tactical/durable seam design. The tactical layer (thin, <200-line loop) handles the automatable repetitive work; the durable layer (HITL, checkpoints) is where human taste plugs in. The seam is exactly where the AI's taste limitation hits.
**Verdict:** CONFIRMS seam design; the transition from tactical to durable is where the "taste gap" lives.

### [NEW-IDEA — §6.2 multiagent / §5.5 evals]
**Finding:** Zero Bug Policy + AI auto-assignment is a live production pattern for using an agent as a routing and triage layer over human workers, not as a replacement. The 7-day SLA + auto-assignment without human decision overhead shows that agents can dramatically compress the organizational OODA loop (bug report → fix → customer delight in 24h) while keeping humans on the judgment-heavy path. This is the multiagent-as-scheduler-offload pattern from §6.2 in practice.
**Verdict:** Zero Bug Policy is a concrete production case for Verso's sub-agent-as-scheduler-offload; the 24h delight cycle is the measurable outcome of correct agent/human division of labor.
