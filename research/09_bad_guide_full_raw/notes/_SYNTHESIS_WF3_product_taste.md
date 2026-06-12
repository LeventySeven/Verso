# _SYNTHESIS_WF3 — Product & Design/UX Taste + the Demo-able Wedge (§2 / §7 / §12)

**Theme scope:** product taste (the CPO half), design/UX taste (great-vs-slop), the demo-able wedge, plus the GTM/distribution and founder-mind sources that bear on §12 and the founder-OS layer.
**Sources read in full:** 35 note files across `design-ux-taste-great-vs-slop/` (7), `product-taste-the-cpo-half/` (16), `the-yc-a16z-game-top-1-not-top-90/` (1), `b2b-go-to-market-founder-led-sales/` (3), `distribution-growth-b2c-launch-in-hours/` (3), `the-founder-mind-high-agency-top-1/` (3), `leverage-becoming-hunted-x-career-capita/` (3).
**Date:** 2026-06-12

---

## 0. The one-paragraph cross-source picture

Across 35 sources spanning design engineering, product management, PMF mechanics, distribution, and founder psychology, the single convergent claim is: **taste is a real, demonstrable, partial-order property — and the only durable form of it in the AI era is the irreducible judgment layer, not the execution layer.** Graham ("Is There Such a Thing as Good Taste") proves taste is non-arbitrary via partial-order; McCormick ("Most Human Wins") isolates *which* taste survives commoditization (the Einstein layer = judgment/question-asking; the Grossmann layer = execution = table stakes); the design-engineering cluster (Freiberg, Kowalski, Linear, HIG) operationalizes taste as a *thousand named, checkable micro-decisions no model makes for you*; and the product cluster (Cagan, Traynor, Saarinen, Doshi, Husain) supplies the vocabulary for refusing scope. For VERSO this resolves to four sharp moves the prior passes had not nailed: **(1)** the wedge is *epistemic, not promotional* — it "isolates the force" so the structurally-aware engineer independently echoes a concern they already had; **(2)** the non-goals must be written as *opinionated design constraints with a "why we refused"*, not a scope list — and crucially as *modes, not optional checkboxes*; **(3)** `inspect()` is not a debugger but a **data-viewer / affordance / direct-manipulation surface** whose feature-spec is already written (Husain's viewer requirements; HIG direct manipulation; Wattenberger's affordances); **(4)** the competitor is *the engineer's own un-promoted `while True:` loop ("doing nothing" / "floors in the building")*, not LangChain — which kills the Better-Trap and replaces it with JTBD "struggling-moment" timing. Everything else is GTM-execution apparatus (PMF survey, Collison-install sessions, Show HN timing, the 5 D's, garage-door-up cadence) that is genuinely useful but **must live in the founder-OS index / GTM playbook, NOT in the PRD's product sections.**

---

## 1. What the prior passes ALREADY established (do NOT re-list as deltas)

For reference only — these recur heavily across this batch and are CONFIRMED again, but are not new:
harness-is-the-moat is consensus; name a category + POV; ban "-er-than-LangChain"; the anti-framework triumvirate; embedded in-process evals vs monetize-LangSmith; "why not DSPy"; Helmer 7-Powers counter-position + switching-costs-at-the-seam; the Framework→Runtime→Harness tier vocabulary; measured harness lift; march-of-nines + context-density + OS analogy; intellectual-honesty register ("decade not year", no magic box, "explain without AI"); primary persona = structurally-aware senior/AI engineer; DX-led organic GTM / superconsumer-first; the demo-able wedge (3-line side-by-side / one-flag durable diff / inspect()); Aggregation-Theory eval-corpus flywheel; invariants-as-taste.

This batch re-confirmed every one of these. The synthesis below reports only what *sharpens, contradicts, or adds*.

---

## 2. DELTAS (genuinely new / sharpening, deduped across sources)

Each delta lists: finding · tag · prd_section · recommendation · source (with verbatim quote).

### A. §7 / §12 — `inspect()` is over-scoped in the PRD as a "taste surface"; four independent sources converge on a much sharper spec

**A1. `inspect()` is a DATA VIEWER with an already-written feature spec — not a debugger.**
Husain ("A Field Guide to Rapidly Improving AI Products") gives the literal spec: *"Teams with thoughtfully designed viewers iterate 10x faster than those without them."* Requirements: all context in one place, one-click feedback capture, open-ended annotation (not thumbs up/down), quick filtering/sorting, keyboard shortcuts for velocity. This is the implicit feature-spec for `inspect()` — and it reframes it from a diagnostic into *"the primary surface through which product intuition about the agent's behavior is built."*
- tag: SHARPEN · §7 · recommendation: **sharpen** (re-spec inspect() as a data-viewer, adopt Husain's 5 requirements as the bar)
- source: Husain, hamel.dev/blog/posts/field-guide

**A2. `inspect()` is the *affordance* claim (the anti-chatbox).**
Wattenberger ("Why Chatbots Are Not the Future"): *"Good tools make it clear how they should be used. And more importantly, how they should not be used."* The empty chat box has zero affordances; `inspect()` is the inverse — it makes state, context window, and decision points visible. inspect() is VERSO's affordance statement, the glove whose shape tells you what it's for.
- tag: SHARPEN · §7 · recommendation: **sharpen** (frame inspect() as the affordance/glove argument in the demo)
- source: Wattenberger, wattenberger.com/thoughts/boo-chatbots

**A3. `inspect()` should be DIRECT MANIPULATION, not read-only.**
HIG: *"When people directly manipulate onscreen objects... they more readily understand the results of their actions."* The PRD frames inspect() as read-only introspection; the HIG argues the higher-value version lets the engineer adjust context / inject messages / modify state in place. Reinforced by Malleable Software's "in-place toolchains" (*"everyone using spreadsheets runs the full editor — no separate dev environment"*) — inspect() is a slope; LangSmith (leave Python to observe) is a cliff.
- tag: SHARPEN · §7 · recommendation: **sharpen** (push inspect() vision toward in-place state manipulation; name the "you don't leave Python" contrast)
- source: Apple HIG; Litt et al., inkandswitch.com/essay/malleable-software

**A4. The "four risks" frame gives inspect()/evals a functional (not aesthetic) purpose.**
Cagan ("Product vs. Feature Teams"): value / usability / feasibility / viability. `inspect()` + the eval surface = *the four-risk ownership surface* the team sees and owns in real time. This makes the taste argument functional: "we give you the surface to own your risks," not "we have nice output."
- tag: SHARPEN · §7 · recommendation: **sharpen**
- source: Cagan, svpg.com/product-vs-feature-teams

> **No-overkill note on cluster A:** these four resolve to ONE PRD change — re-spec `inspect()` in §7 from "taste surface" to "the in-place, affordance-bearing, four-risk data-viewer (Husain's 5 requirements) that supports direct manipulation of agent state." Do not add four bullet points; add one sharpened definition.

---

### B. §2 — Non-goals must be rewritten as opinionated *design constraints with a "why"*, and the seam must be a MODE not an option

**B1. The seam flag must be a MODE, not an optional checkbox — the "optional feature fallacy."**
Traynor ("Product Strategy Means Saying No"): making a feature optional *"hides interface complexity but spreads it throughout the system. This weakens product definition — you become a vague collection of capabilities rather than a focused solution."* CONTRADICTS any framing of the one-flag durable promotion as "an optional feature you can turn on." It must be communicated as *the axis that reveals the system's architecture*, not a toggle bolted on the side.
- tag: SHARPEN · §2 (+ §7) · recommendation: **sharpen** (PRD must state: the durable flag is a mode/axis, not an option)
- source: Traynor, intercom.com/blog/product-strategy-means-saying-no

**B2. Each non-goal needs "and here's WHY we refused" (the negative-space discipline).**
Walter ("How to Develop Product Sense") on Slack's framing-first lesson: the negative space (what was rejected and why) is as load-bearing as the positive claims. Concretely: *"We don't provide graph primitives because forcing a graph makes the seam rigid — and a rigid seam is the failure mode we exist to prevent."* Reinforced by Saarinen Rule 7 (design-with-opinion → non-goals are the opinionated refusal that makes the product work for its someone).
- tag: SHARPEN · §2 · recommendation: **sharpen** (every §2 non-goal gets a one-line refusal rationale)
- source: Walter, lennysnewsletter.com/p/product-sense; Saarinen, figma.com/blog/karri-saarinens-10-rules

**B3. New, vivid non-goal vocabulary that beats "no feature-shaped primitives":**
- **"We are not an avocado slicer"** — Litt et al. (Malleable Software): apps are avocado slicers (bundled for one use case); tools are knives (general). EmailAgent/SlackAgent/RAGAgent are avocado slicers. *"Many applications are avocado slicers."*
- **"Judgment primitives, not feature primitives"** — Norton ("How to Hire a PM"): the specialist-hire trap maps onto framework bloat. *"We don't build feature-shaped primitives. We build judgment-shaped ones."*
- **"We are a product, not a feature repository"** — Traynor: the "potential argument" failure mode *"yields feature repositories instead of products."* (Do not name LangChain; let the category speak.)
- **"No Magic AI input surfaces / explicit affordances everywhere"** — Appleton ("Squish Meets Structure"): *"This thing has no affordances!"* is what users say about bad AI products; VERSO's non-goal is to never provoke that.
- tag: SHARPEN · §2 · recommendation: **sharpen** (adopt 1–2 of these as the §2 register; do NOT stack all four — pick the avocado-slicer + feature-repository pair)
- source: Litt et al.; Norton bringthedonuts.com/essays/productmanager; Traynor; Appleton maggieappleton.com/squish-structure

**B4. CONTRADICTION to watch — non-goals are lower-level decisions that should UPDATE on evidence, not identity commitments.**
Graham ("The Right Kind of Stubborn"): top-level goals persist; lower-level decisions stay rational/flexible. VERSO's non-goals (no forced graph, no visual workflow, no platform) are *lower-level* conclusions-today, not the goal. Frame them as *"current rational conclusions, not identity commitments"* to avoid the obstinacy failure mode (becoming attached to a non-goal because it's yours). This is a genuine tension with B1/B2's "write them as firm opinionated constraints" — resolve by: firm in *voice*, explicitly revisable in *status*.
- tag: SHARPEN · §2 · recommendation: **sharpen** (add a one-line preamble: non-goals are evidence-revisable, not dogma)
- source: Graham, paulgraham.com/persistence.html

---

### C. §7 / §12 — The wedge is EPISTEMIC, not promotional (this is the biggest reframe in the batch)

**C1. The demo "isolates the force" so the property becomes visible — it does epistemics, not marketing.**
Graham ("Is There Such a Thing as Good Taste"): *"It's only when you isolate this force, for example by trying to paint and comparing your work to Bellini's, that you can see that it does in fact exist."* The 3-line side-by-side is the "try to paint and compare" mechanism: without that test artifact, "we have better taste" is just noise. Reinforced by Graham's partial-order register: VERSO claims to be *demonstrably better on the specific dimension of harness taste for structurally-aware engineers* — a defensible partial-order claim, not a global-superiority claim.
- tag: SHARPEN · §7 / §12 · recommendation: **sharpen** (frame the demo explicitly as "isolating the force"; lead Show HN with the isolating demo BEFORE any positioning claim, so judgment forms before extraneous signals — stars/backing/familiarity — corrupt it)
- source: Graham, paulgraham.com/goodtaste.html

**C2. The wedge should trigger the "independent echo" / "think harder" response, not conversion.**
Norton: the highest taste-signal is when someone *independently echoes a concern you already privately had*, and when they *teach you something about your own product*. Reinforced by Graham ("The Right Kind of Stubborn"): the demo is a *persistence test* — does seeing it make the viewer think harder about their approach (Collison-brothers behavior = the target persona) or defend it (not the target)? Design the wedge to maximize "here's something that surprised us," not "here's why you should switch."
- tag: SHARPEN · §7 · recommendation: **sharpen** (wedge copy resolves the reader's *half-formed* concern; opens with the insight they were already carrying, unnamed)
- source: Norton; Graham persistence.html

**C3. The wedge sells a FEELING — name it: "structural confidence."**
Puri ("How Would You Build an Audience"): *"I'm not selling things, I'm selling a feeling."* The 3-line diff's payload is not information ("here's how the flag works") but the feeling *"I can now see exactly what my agent does under failure, and I don't have to rewrite anything to get there."* Reinforced by the JTBD emotional layer (Christensen: *"confidence that the agent won't silently degrade or get me paged at 2am"*).
- tag: SHARPEN · §7 · recommendation: **sharpen** (reframe demo script around the signature feeling — structural confidence — not the feature list)
- source: Puri, shaanpuri.com/mailbag; Christensen et al., hbr.org/2016/09/know-your-customers-jobs-to-be-done

**C4. NEW concrete demo SCRIPT — the "invisible bug" shape (NurtureBoss).**
Husain: a date-handling bug failed 66% of the time and was *completely invisible to generic metrics* (33%→95% after targeted fix). This is the exact shape of the eval-wedge demo: run the same agent with generic logging vs. VERSO's embedded eval harness, and show the specific bug class that the generic approach misses. Stronger than "evals are important" → "here is the bug you WILL miss without this."
- tag: ADOPT-NOW · §7 · recommendation: **adopt-now** (this is a concrete, buildable second demo beyond the 3-line diff; it is product-scope, not GTM apparatus)
- source: Husain, hamel.dev/blog/posts/field-guide

**C5. The one-flag promotion is a SIMULATION primitive (reframe its narrative).**
Doshi ("Why Product Sense is the Only Skill That Will Matter"): simulation = *"anticipating future possibilities... modeling second-order effects before they materialize."* The side-by-side is literally a simulation artifact: "here's your agent today (ephemeral); here's what it does after promotion (checkpoint/resume/HITL) — same logic, different durability." Frame as *"you can reason about what happens at step 7 before you deploy,"* not merely "easier durability."
- tag: SHARPEN · §7 · recommendation: **sharpen**
- source: Doshi, shreyasdoshi.substack.com/p/why-product-sense

---

### D. §12 — The competitor is "doing nothing," and the resonant external language is NOT "harness"

**D1. The real competitor is the engineer's own un-promoted loop — "doing nothing" / "floors in the building."**
Christensen et al. (JTBD/SNHU): the real competitor was *inaction*, not a named rival. Saarinen ("Linear's Path to PMF"): *"The incumbent in this market is like the floors in the building — you don't think about the floors, you just walk on them."* VERSO's actual competitor is the hand-rolled `while True:` loop with ad-hoc retry and a mental note to "fix this later." This kills the Better-Trap structurally: the GTM frame is *"the upgrade path from your working prototype that you've been putting off,"* positioned at the *struggling moment* (first prod failure / first 2am page) — not before (no pain), not at week-three-of-a-redesign (too late).
- tag: SHARPEN · §12 (+ §2) · recommendation: **sharpen** (reframe positioning around "doing nothing" as the competitor and the struggling-moment as the trigger)
- source: Christensen et al.; Saarinen review.firstround.com/linears-path-to-product-market-fit

**D2. CONTRADICTION / RISK — "harness" may be the right *internal* category word but the WRONG *external* GTM word.**
Lerner ("Finding Language/Market Fit"): customer language beats founder language by 10–20x conversion (Mindstone 30% vs 3%). The structurally-aware engineer's vocabulary is *"my agent broke in production," "I can't debug what happened," "I had to rewrite everything when requirements changed," "the context window filled up and it just stopped."* "Harness > framework" is VERSO's language; it is unvalidated against the persona's actual words. Do NOT assume "harness" is the resonant external word — it must be A/B tested against problem-language alternatives.
- tag: SHARPEN · §12 · recommendation: **sharpen** (PRD should mark "harness" as the internal category anchor, explicitly flagged as pending language-market-fit validation for external copy; the *method* — JTBD decision-journey interviews — is GTM apparatus, see §3)
- source: Lerner, review.firstround.com/finding-language-market-fit

**D3. Category name determines the ROADMAP, not just the pitch.**
Walter (Slack: "enterprise communication" vs "team coordination" produced different roadmaps). If VERSO frames itself as "agent framework," it inherits the wrong roadmap (graph primitives, tool routing, multi-agent orchestration). The name is a cognitive constraint on what gets built. Reinforced by Zhuo ("The Power of Product Thinking"): "framework" implies *methodology* (a process you follow); "harness" implies the artifact that holds the shape — name a category that signals *judgment-in-a-box*, not process-to-follow.
- tag: SHARPEN · §12 · recommendation: **sharpen**
- source: Walter; Zhuo, future.com/product-thinking

**D4. The counter-position vocabulary upgrade: "Verso is the kitchen, not the recipe" + "tool-shaped vs app-shaped" + "product-team vs feature-team."**
- Litt et al.: *"Bringing AI coding tools into today's software ecosystem is like bringing a talented sous chef to a food court."* AI generates the loop body (sous-chef work); the harness is the kitchen (context guarantees, eval surface, checkpoint). **"Verso is the kitchen, not the recipe"** is a candidate line, and it directly rebuts "LLMs will auto-generate agent frameworks."
- Litt et al.: "tool-shaped vs app-shaped" as the counter-position axis (no LangChain mention needed).
- Cagan: LangChain = feature-team framework (gives you `LLMChain`, `AgentExecutor`, tools — solutions to plug in); VERSO = product/empowered-team framework (gives you the ownership surface). *"It's all about solving problems, not implementing features."* → candidate line **"built for builders who own outcomes, not builders who implement roadmaps."**
- tag: SHARPEN · §12 / §1 · recommendation: **sharpen** (these are the precise counter-position lines that replace Better-Trap language; the "harness-is-moat" claim itself is consensus, so positioning wins on *this specific shape* — exactly per the prior-pass instruction)
- source: Litt et al.; Cagan

**D5. NEW moat layer — "feature-blackmail immunity" / "mental-model capture."**
- Traynor names the "retention argument" / feature blackmail (*"a customer will leave if we don't build this"*). Incumbents with large enterprise bases get blackmailed into coherence-diluting integrations; *VERSO is small enough to refuse.* This sharpens §1 beyond "we don't force the graph": the incumbent's *inability to say no* is a structural weakness to position against.
- Saarinen (10 Rules): *"High quality builds irrational loyalty where users won't leave"* — irrational loyalty = switching costs + brand simultaneously = **mental-model capture**. If the harness/seam becomes how the engineer *thinks about reliability* (not just how they implement it), the switching cost is abandoning a mental model, not just migrating an API. Reinforced by Saarinen ("Linear's Path"): opinionated constraints (one flag, not a config matrix) install a mental model.
- tag: ADOPT-NOW · §1 · recommendation: **adopt-now** (add two distinct moat layers to §1: "feature-blackmail immunity" as a counter-position asset; "mental-model capture" alongside API switching costs — both are product/moat-scope, not GTM)
- source: Traynor; Saarinen (both pieces)

---

### E. §7 / Product taste — design-engineering invariants that sharpen the output-surface bar

**E1. Frequency × Novelty: high-frequency output surfaces must NOT carry animation/ceremony.**
Kowalski ("Great Animations") + Freiberg ("Invisible Details"): *"never animate keyboard-initiated actions"*; high-frequency low-novelty interactions earn zero animation. The CLI/`inspect()` analog: anything satisfying on first use feels sluggish on the 50th. The design test: *"how does this feel after 200 invocations today?"* This is the primary taste filter for all VERSO output surfaces (CLI progress, streaming deltas, inspect output).
- tag: ADOPT-NOW · §7 · recommendation: **adopt-now** (state the Frequency×Novelty filter as a named output-surface invariant)
- source: Kowalski emilkowal.ski/ui/great-animations; Freiberg rauno.me/craft/interaction-design

**E2. "Aesthetic integrity = function-appearance coherence" is the precise definition of taste (not "looks good").**
HIG: *"Aesthetic integrity is... a measure of how well the appearance of the app integrates with its function."* A progress bar adding visual richness without communicating actionable state has poor aesthetic integrity; a plain timestamped line that says exactly what the agent did has excellent integrity. Use this as VERSO's *definition* of taste in design language.
- tag: SHARPEN · §7 · recommendation: **sharpen**
- source: Apple HIG

**E3. "A thousand small decisions no model makes for you" — usable verbatim; tabular-nums is the canonical tell.**
Freiberg ("Web Interface Guidelines"): the list exists because taste is *enumerable at the implementation level*. `font-variant-numeric: tabular-nums` is the canonical example of a decision a model never makes (you only know it if you've been burned by reflow). VERSO's equivalent: *checkpoint files need deterministic key ordering so diffs are readable* — the kind of thing you only know if you've operated an agent in production. Plus: "toggles take effect immediately, no confirm dialog" → the one-flag promotion is instantaneous, no ceremony.
- tag: SHARPEN · §7 / §12 · recommendation: **sharpen** ("a thousand small decisions no model makes for you" is sharper than "better than LangChain" — use it; concretize with the deterministic-key-ordering example)
- source: Freiberg github.com/raunofreiberg/interfaces

**E4. The 98→3 variable reduction (LCH) as the harness-simplification analogy.**
Saarinen ("How We Redesigned the Linear UI"): Linear reduced 98 theme variables to 3 by finding the generative primitives. *"We did to the agent loop what LCH did to Linear's theme system"* — reduce the combinatorial surface to a generative minimum. Usable rhetorical parallel for "the loop is ~10 lines."
- tag: ADOPT-NOW · §7 / §12 · recommendation: **adopt-now** (as a taste analogy in positioning)
- source: Saarinen, linear.app/now/how-we-redesigned-the-linear-ui

**E5. "Spell-check sized" as the primitive-scoping heuristic + step-level observability for evals.**
Appleton: *"most language model implementations should be 'spell-check sized' — do one specific thing well."* Each VERSO primitive should be describable in one sentence. Plus the compositionality argument: step-level I/O observability (*"we could inspect the input and output at each step"*) is *why* evals must be step-level, not run-level — only a harness with step observability supports step evals. (This last point is also a §5/§6 primitive implication.)
- tag: SHARPEN · §7 (+ §5/§6) · recommendation: **sharpen**
- source: Appleton, maggieappleton.com/squish-structure

**E6. Market-education anchor: "simultaneously incredibly dumb and incredibly capable" beats "hallucination."**
Appleton: the cleanest one-line reason the harness exists — you can't trust the model at face value (dumb) but can't ignore it (capable). Better framing than "models hallucinate."
- tag: SHARPEN · §12 · recommendation: **sharpen**
- source: Appleton

> **No-overkill note on cluster E:** E1, E2, E3 are the load-bearing additions (output-surface invariants + taste definition + the "thousand decisions" line). E4/E5/E6 are sharpenings of existing positioning/scoping; adopt the lines, don't expand the section.

---

### F. §1 — Bet/moat sharpenings (product-scope, not GTM)

**F1. Problem-selection > feature-differentiation — VERSO's bet is the choice of an *unfashionable* problem.**
Graham ("How to Do Great Work"): *"Originality in choosing problems seems to matter even more than originality in solving them."* The harness problem is unfashionable; the loop problem is fashionable — *"Working on an unfashionable problem can be very pleasing. There's no hype or hurry. Opportunists and critics are both occupied elsewhere."* Internal framing for the bet: "problem selection, not feature differentiation." Plus the rhetorical frame: *"What becomes possible if you discard [the graph requirement]?"* — the Show-HN-able version of the counter-position.
- tag: SHARPEN · §1 / §12 · recommendation: **sharpen**
- source: Graham, paulgraham.com/greatwork.html

**F2. The taste moat = "reliably produces recognition/confidence responses in structurally-aware engineers" (the vaccine analogy) — and it's MEASURABLE.**
Graham (goodtaste): a vaccine "works" because of what it reliably does to human immune systems even though immunity "happens in" individuals. Reframes the moat from *"we have good taste"* (assertion) to *"we reliably produce recognition + confidence in the target population"* (measurable via DX interviews, activation, time-to-first-working-agent). Makes "invariants-as-taste" a studied property, not an aesthetic claim.
- tag: ADOPT-NOW · §1 · recommendation: **adopt-now** (sharpen the moat language; pair with an activation metric — see F3)
- source: Graham, paulgraham.com/goodtaste.html

**F3. The activation metric should be a *product outcome*, not a traction metric.**
Torres ("Opportunity Solution Trees"): product outcomes (behavior change) over traction metrics (single-feature adoption / stars). Candidate VERSO activation node: *"engineer completes a durable checkpoint + resume cycle within their first week,"* not "starred the repo." This is the test for whether the demo-wedge is doing its job. (The OST/three-solution discovery method itself is internal process, see §3.)
- tag: SHARPEN · §1 / §7 · recommendation: **sharpen** (name the product-outcome activation metric in the PRD; it's the success-check the wedge is measured against)
- source: Torres, producttalk.org/opportunity-solution-trees

**F4. Einstein-vs-Grossmann stress test for every moat claim.**
McCormick ("Most Human Wins"): *"Einstein commoditized Grossmann... He used Grossmann's output as his input, while he himself provided the spark that could not be reduced."* Stress-test: is a given VERSO claim Grossmann (execution, commoditizable → table stakes) or Einstein (judgment, irreducible → moat)? The graph abstraction is Grossmann; *when* to promote, *what* invariants to enforce, *which* context to preserve is Einstein. Sharpens "invariants-as-taste": a competitor can copy the API; they cannot copy the judgment about which invariants matter.
- tag: SHARPEN · §1 · recommendation: **sharpen** (adopt the Grossmann/Einstein test as the internal filter for moat claims; frame invariants as "decided X non-negotiable after seeing Y fail in production," not "framework enforces X")
- source: McCormick, notboring.co/p/most-human-wins

---

## 3. RESIST — GTM-execution apparatus and founder-OS material that must NOT leak into the PRD's product sections

These are genuinely useful but belong in the **founder-OS index (research/04_bad_guide_full)** or a **GTM playbook**, not in PRD §1/§2/§7/§12. Listed so the PRD author can refuse them cleanly.

- **The PMF survey instrument** (Superhuman/Vohra: Q1 "how would you feel if you could no longer use VERSO," 40% "very disappointed" threshold, segment-to-HXC, 50/50 delight/necessity roadmap, PMF-score-as-only-OKR). → **founder-OS / GTM playbook.** It is a measurement *process*, not product scope. (The *output* — a concrete HXC profile — can sharpen §12 persona, but the survey machinery does not belong in the PRD.)
- **Collison-install / live-wedge sessions, office hours, "feedback call" framing, three-bucket email templates, pilot-success metric, minimal Airtable CRM, Tue/Wed/Thu calendar batching** (Graham "Do Things That Don't Scale"; Kracov; Levels). → **founder-OS GTM playbook.** Sales/onboarding mechanics.
- **Show HN / Product Hunt tactical mechanics** (submit 1am SF time, founder-present in thread, real-time iteration, micro-blogger→national press staircase, "court one HN/X-prominent engineer," 3-line diff must be tweetable, "keep launching" each primitive = its own Show HN, spin-off micro-packages). → **GTM playbook.** Channel execution. (NOTE: "each primitive = its own Show HN" is a *launch-sequencing* idea, not a product roadmap directive — keep it out of §7/§8.)
- **The 5 D's, magnet-not-audience, Ferrari-not-GM, binge-bank, garage-door-up cadence / <20% promotional post cap, "known well not well-known," neti-neti X framing** (Puri; McCormick; Matuschak). → **founder-OS / X content strategy.** Audience-building apparatus. (Ferrari-not-GM *can* lightly reinforce the §1 "fewer-higher-value-users" moat framing, but the analogy itself is GTM color, not PRD substance.)
- **"Verso Fellow" / free-superconsumer distribution tier** (Kwok freemium gradient). → **GTM playbook.** Pricing/distribution mechanism.
- **The whole founder-mind / high-agency cluster as operating principles:** Graham earnestness ("formidable + earnest" dual Show-HN signal; "bit-rotting sophistication" as the rebuttal to "isn't this too simple?"; "interest in the problem for its own sake" as persona filter); Graham persistence ("self-check at the wall: evidence vs pride"; "start narrower than ideal, expand from signal"; non-goals are lower-level decisions); Garry Tan ("craft-and-finish / back-of-the-drawer" signal, "fundraising is downstream of real customers," co-founder-conflict-as-#1-killer, meta-prompting V-27); Saarinen operating rules (solo-generate-then-critique, small/curated/no-handoff team, "spec is the baseline not the finish line," multiple-launches, profitability-as-quality-preservation); Adams ("100→1,000 customer conversations" domain-judgment threshold, cargo-cult-contrarianism warning, researcher paradox, three-rates-of-change refusal heuristic); Mehta ("know your shape" self-assessment, spiky-individual/well-rounded-team, Product-Innovator failure mode, Business-Outcome-Ownership = always lead with a number); Zhuo/Doshi/Walter/Husain weekly cadences. → **research/04_bad_guide_full (founder-OS index).** These are how the *founder operates*, not what the *product is*.

  - **Two founder-OS items worth flagging as high-value for the index** (not PRD):
    - **"Bit-rotting sophistication"** (Graham earnestness) — the precise, reusable rebuttal to the "isn't 10 lines too simple?" objection: the objector's sophistication is calibrated against a pre-Claude-3.5 / pre-GPT-4-turbo model baseline that is decaying. *"Naive optimism can compensate for the bit rot that rapid change causes in established beliefs."*
    - **"Formidable + earnest" as the dual Show-HN signal** — the wedge supplies *formidable* (technically specific), the intellectual-honesty register supplies *earnest*; either alone is weaker (formidable-only reads academic; earnest-only reads blog post). This is launch *execution* guidance, hence founder-OS, but it is the cleanest synthesis of why both registers must co-fire.

- **Two cross-source convergences worth recording as research notes (not PRD):**
  - **Story-based JTBD interviewing is DOUBLE-confirmed** (Christensen + Torres independently: "tell me about a time when...", circumstances over preferences, why over what). This is the canonical early-user research protocol → founder-OS.
  - **"Toy dismissal is a good sign"** (Graham: *"An early version of a new project will sometimes be dismissed as a toy. It's a good sign... it has everything a new idea needs except scale"*) — psychological prep for the "just a thin wrapper" Show HN response → founder-OS.

---

## 4. Net recommendation to the PRD author (the no-bullshit short list)

If only the highest-leverage changes are made to §1/§2/§7/§12, make these and stop:

1. **§7 — Re-spec `inspect()`** from "taste surface" to "the in-place, affordance-bearing, four-risk data-viewer (Husain's 5 viewer requirements) that supports direct manipulation of agent state." (Cluster A — one sharpened definition, not four bullets.)
2. **§2 — Rewrite non-goals as opinionated design constraints with a one-line "why we refused" each; state the durable flag is a MODE not an option; adopt "avocado slicer" + "product-not-feature-repository"; add a preamble that non-goals are evidence-revisable.** (Cluster B.)
3. **§7/§12 — Reframe the wedge as epistemic** ("isolate the force"; lead with the isolating demo before claims; trigger the independent-echo/think-harder response; sell *structural confidence*; add the NurtureBoss "invisible bug" demo). (Cluster C.)
4. **§12 — Make the competitor "doing nothing"/"floors in the building," position at the struggling-moment, flag "harness" as internal-only pending language-market-fit, and adopt the kitchen-not-recipe / product-team-not-feature-team counter-position lines.** (Cluster D.)
5. **§1 — Add two moat layers: "feature-blackmail immunity" and "mental-model capture"; reframe the taste moat as a measurable recognition/confidence response (vaccine analogy) tied to a product-outcome activation metric (durable-cycle-in-first-week); adopt the Grossmann/Einstein test as the internal moat filter.** (Clusters D5, F.)
6. **§7 — Name the output-surface taste invariants: Frequency×Novelty ("how does it feel after 200 invocations"), aesthetic-integrity = function-appearance coherence, and "a thousand small decisions no model makes for you" (concretized with deterministic checkpoint key-ordering).** (Cluster E.)

Everything else in this batch is confirmation of prior passes or GTM/founder-OS apparatus — route it to research/04_bad_guide_full, not the PRD.
