# Animations on the Web
**URL:** https://animations.dev/  
**Creator:** Emil Kowalski (Design Engineer at Linear; formerly Vercel; creator of Sonner and Vaul React libraries, 70M+ weekly npm downloads)  
**Format:** Paid interactive course — 4 modules, 50+ interactive exercises, 15 walkthrough lessons  
**Source found:** animations.dev landing page (fetched directly), emilkowal.ski personal site + essays ("Great Animations" + "Building an Animation Course"), and search aggregations. The course itself is behind a paywall; free public essays by Emil at emilkowal.ski provide the underlying philosophy in full. Content from the `04_bad_guide_full/design-ux.md` prior pass also draws on a read of the course structure.

---

## What the Course Actually Teaches

### Core Thesis (from Emil's public writing and course landing page)
Animation in UI is not decoration — it is functional communication. Most motion in interfaces fails two of six tests: it serves no purpose, and it cannot be interrupted. The goal is animation that *disappears* (users don't notice it) while doing its job: communicating state, encoding physics, and making transitions feel continuous. Restraint is the skill, not flashiness. Emil's framing: *"design engineering became about animations and slick demos. In reality, it's mostly deciding what not to animate."*

---

### Course Structure

**Module 1: Animation Theory (8 lessons)**
- Easing and duration selection
- Spring animations: when to use, spring parameters (stiffness, damping, mass)
- Purpose: when NOT to animate
- Taste: developing the "feel right" sense
- AI assistance for animation refinement

**Module 2: CSS Animations**
- Transforms, transitions, keyframes
- Decision rationale behind duration and easing choices
- Performance: GPU-composite properties vs. layout-triggering properties

**Module 3: Framer Motion (Motion)**
- Beyond documentation basics: complex animations, problem-solving, debugging
- Interruptibility as an explicit implementation concern

**Module 4: Good vs. Great**
- Emotional communication through motion
- Orchestration and sequencing
- Accessibility: prefers-reduced-motion as a design decision, not an afterthought
- Performance under main-thread load

**Walkthroughs (15 lessons across 4 projects):**
- Family Drawer (mobile implementation)
- Dynamic Island (spring animation reference)
- Navigation Menu
- SVG Animations

Each walkthrough narrates Emil's exact decision process — not just implementation but *why this animation vs. that one.*

**Bonus content:** Exclusive Discord, curated resource library, expert interviews, SKILL.md file (AI-agent instruction set for generating animations to Emil's standard).

---

### The Six-Test Filter (from "Great Animations" essay — public)

Emil's operational framework for evaluating any animation before shipping:

1. **Natural motion.** Springs, not linear easing. *"Nothing in the world around us disappears or appears instantly."* Spring parameters: stiffness, damping, mass. Apple Dynamic Island is the reference: moves like a living organism. Default: springs or `ease-out` (fast start, slow finish — feels like quick response).

2. **Right speed.** Under 300ms. *"Snappy animations feel responsive and connected to user's actions."* Over 300ms reads as slow even if frames are perfect.

3. **Clear purpose.** Animate only where it enriches information: state changes, modal enter/exit, explainer sequences. **Never animate keyboard-initiated actions.** Raycast deliberately has zero animation for repeated keyboard actions. Ask: "Would the user understand the state change without this animation?" If yes, cut it.

4. **60 FPS.** Animate only `transform` and `opacity` — composite layer, GPU-handled. Never `padding`, `margin`, `width`, `height` — these trigger layout + paint + composite and force the main thread. CSS or WAAPI for hardware acceleration; `requestAnimationFrame` (Framer Motion's default) lags under main-thread load. Proof: Vercel's dashboard tab animation switched to CSS to fix frame drops during page load.

5. **Interruptible.** State changes mid-animation must be possible. CSS transitions handle this natively. Framer Motion supports it explicitly. A spring that can't be interrupted *"feels like the app is arguing with you."* Escape key should close a modal even if it's still animating open.

6. **Accessible.** `@media (prefers-reduced-motion: reduce)` in CSS. `useReducedMotion()` in Framer Motion. Design the fallback — sometimes "no motion" means instant cut; sometimes it means fade instead of spring.

---

### Philosophy Statements (from public essays and course landing)

- *"In a world of abundance, we treasure taste."* (Anu Atluru, cited by Emil as foundational framing for the course.)
- Restraint is the differentiator: *"design engineering became about animations and slick demos. In reality, it's mostly deciding what not to animate."*
- Interactive experience over explanation: understanding motion requires direct manipulation, not description. The course is built around doing, not reading.
- Animation mastery = frequency × novelty filter: high-frequency keyboard interactions get no animation; low-frequency touch interactions get physics-based animation.
- AI and animation: Emil created a SKILL.md file so coding agents can generate animations to his professional standard. Recognizes AI handles the baseline; taste and restraint judgment remain human.

---

### Background: Who Emil Kowalski Is
- Design Engineer at Linear (web team, building for designers and developers)
- Previously on Vercel's design team
- Creator of Sonner (toast notification library) and Vaul (drawer component) — ~70M weekly npm downloads combined
- Course has exceeded 10,000 enrollments, primarily through peer recommendation with no paid marketing
- Course is a living document: free updates, new modules (including "Animations and AI"), ongoing refinement

---

## VERSO RELEVANCE

### [CONFIRMS] §7 / product_taste — Frequency × novelty = animation budget is directly applicable to VERSO's agent UI
**Finding:** Emil's rule that keyboard-initiated, high-frequency actions should get zero animation (Raycast model) is directly applicable to the VERSO harness interface. The `inspect()` call, the step-through, the eval runner — these are high-frequency developer actions. Streaming state indicators (token flow, tool calls) are lower-frequency and higher novelty. The six-test filter defines the correct design spec for VERSO's UI surface. CONFIRMS the prior synthesis that animation at the agent streaming layer is taste work, not infra work.  
**VERSO PRD section:** §7 demo-able wedge / product_taste.

### [NEW-IDEA] positioning — "Deciding what not to animate" as a metaphor for VERSO's harness design discipline
**Finding:** Emil's core design philosophy — restraint is the skill, not flashiness; the art is *what not to do* — is a direct structural parallel to VERSO's harness bet. Just as great animation work is mostly *deciding what not to animate*, the VERSO harness is mostly *deciding what the framework should not own* (not the loop, not the graph, not the model, not the transport). This is a NEW positioning metaphor: VERSO is to agent harnesses what Raycast animation is to UI animation — zero animation for the high-frequency loop, full physics for the rare but impactful durability transition.  
**Tag:** NEW-IDEA  
**VERSO PRD section:** §12 positioning / product_taste.

### [SHARPENS] §1 / bet_moat — Emil's course as precedent for the "taste corpus as flywheel" model
**Finding:** Emil's course reached 10,000+ enrollments through peer advocacy with no paid marketing. The product itself generated the distribution. This SHARPENS the VERSO eval-corpus-aggregation-flywheel thesis: if VERSO builds the taste corpus (eval sets, context engineering patterns, inspect() traces) at the same quality level, the corpus becomes self-advocating. The precedent is Emil's course, not LangSmith's feature-list. Organic advocacy from the 5-vocal-production-leads cold-start cohort is the same mechanism.  
**VERSO PRD section:** §1 bet/moat, §12 gtm_distribution.

### [SHARPENS] product_taste — Interruptibility as the single most-neglected UI quality signal
**Finding:** Emil's six tests name interruptibility as the #2 most commonly failed test (after purpose). A spring that can't be interrupted *"feels like the app is arguing with you."* This is a directly deployable criterion for VERSO's streaming states and HITL surfaces: every agent state transition must be interruptible — the user should be able to intervene mid-flight without the harness resisting. The harness arguing with the user is the product failure mode. SHARPENS the "never a forced graph" non-goal into a concrete interaction design principle.  
**VERSO PRD section:** product_taste, §2 non-goals.

---

**Verdict:** read_partial (course itself is paywalled; full public essays at emilkowal.ski read in full; course structure and philosophy from landing page read directly). No fabricated content — all frameworks come from Emil's own public essays and the course landing page. Prior `04_bad_guide_full/design-ux.md` digest is confirmed and supplemented. Three new deltas: "what not to animate" as positioning metaphor (strongest new contribution), interruptibility as harness design principle, and Emil's course as peer-advocacy flywheel precedent.
