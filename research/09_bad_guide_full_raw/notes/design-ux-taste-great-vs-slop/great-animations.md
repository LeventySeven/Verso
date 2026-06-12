# Great Animations
**Source:** https://emilkowal.ski/ui/great-animations
**Author:** Emil Kowalski
**Format:** Essay (medium length)
**Fetched:** 2026-06-12

---

## Faithful Digest

Emil Kowalski opens with the premise that product selection is increasingly experience-driven, not feature-driven: "People increasingly select tools based on overall experience rather than just functionality. A predictable and delightful experience distinguishes products in crowded markets." This is the business case for animation craftsmanship — and for design engineers.

The essay presents **seven named tests** that separate great animations from decorative ones:

### 1. Natural
Motion must mirror physical reality. "Changes in web apps often occur instantly, which makes the experience feel artificial and unfamiliar, since nothing in the world around us disappears or appears instantly." The Dynamic Island is the exemplar. Technically: spring animations (stiffness, damping, mass) over linear ones.

### 2. Fast
Perceived performance is the metric, not visual richness. "Snappy animations feel responsive and connected to user's actions." The prescription: `ease-out` easing (starts fast, slows at end), durations under 300ms. Speed signals respect for the user's time.

### 3. Purposeful
Animations must earn their place by enriching information or indicating state change. The counter-principle is explicit: **"never animate keyboard-initiated actions."** Repeated actions (cmd-K, keyboard shortcuts executed hundreds of times/day) must not carry animation overhead. The purpose test: does this motion communicate something that couldn't be communicated without it?

### 4. Performant
60fps is table stakes — all other qualities are irrelevant below this threshold. The technical rule: animate only `transform` and `opacity` because they trigger only the compositor rendering step; `padding`, `margin`, `width` trigger layout → paint → composite. Critical nuance: "Hardware-accelerated animations like CSS or WAAPI will remain smooth, no matter how busy the main thread is." — CSS and Web Animation API beat requestAnimationFrame-based libraries (e.g. GSAP) when the main thread is occupied.

### 5. Interruptible
"Interruptibility makes animations feel natural and responsive, allowing users to change animation states at any time while maintaining smooth transitions." CSS transitions handle this natively. Framer Motion also supports it. Non-interruptible animations signal that the UI is not tracking the user's actual intent — the animation is a broadcast, not a response.

### 6. Accessible
Vestibular disorders and motion sensitivity are real. The `prefers-reduced-motion` media query is mandatory, not optional. Implementation: provide a fade alternative, not the full motion, for users who opt out.

### 7. Cohesive ("Feel Right")
Easing, duration, and design direction must form a unified language. The Sonner toast library is cited as an example where the animation *fits* the library's personality, not just its function. Refinement requires fresh eyes — reviewing animations the next day surfaces imperfections that fatigue hides.

---

## VERSO RELEVANCE

### [NEW-IDEA] The "keyboard-initiated actions never animate" rule maps directly to CLI/terminal DX taste
The principle that high-frequency, keyboard-driven interactions must not carry animation overhead is exactly the right frame for Verso's CLI outputs, progress rendering, and inspector output. `agent.inspect()` should be snappy; streaming output should feel like it tracks action without visual ceremony. This is the CLI analog of Kowalski's rule. If Verso ever ships a UI layer, the same test applies to any output triggered by code invocations rather than mouse clicks.
**Tag:** [NEW-IDEA] | **Section:** §7 (Demo-able wedge / product taste) | **Verdict:** adopt-now as a taste invariant for CLI and eventual UI surfaces.

### [SHARPENS] "Purpose test" as the invariant for every Verso UI surface
The question "does this motion communicate something that couldn't be communicated without it?" is a sharper formulation of the taste filter already implicit in Verso's anti-decoration stance. Applied concretely: the one-flag durable diff, the `agent.inspect()` surface, and any progress indicators should each pass this test. If the state change is already communicated by the text output, a visual flourish is cost not value.
**Tag:** [SHARPENS] | **Section:** §7 / §12 (product taste, DX positioning) | **Verdict:** sharpen — codify as a review question during any UI decision.

### [CONFIRMS] "Experience over features" as a market selection driver
The opening framing — tools are chosen on overall experience quality, not feature parity — confirms Verso's DX-led organic GTM thesis. This is not new but is useful as a citation anchor: the claim has a named author and a specific assertion.
**Tag:** [CONFIRMS] | **Section:** §12 (positioning/GTM) | **Verdict:** confirm — already in the PRD, no action needed.

### [NEW-IDEA] Cohesion as an anti-fragmentation test
The "feel right" principle — that easing, duration, and design direction must be internally consistent — translates for Verso into: every output surface (CLI progress, inspect output, error messages, streaming deltas) should share a single voice/pace. Inconsistency in output rhythm signals a framework that doesn't own its surface. This is a taste invariant that's currently implicit; it should be made explicit as a review criterion.
**Tag:** [NEW-IDEA] | **Section:** §7 (product taste) | **Verdict:** adopt-now as an output-coherence invariant.

### [SHARPENS] Interruptibility as a first-class primitive
The interruptible animation test maps to Verso's agent loop design: a running agent must be gracefully interruptible (HITL seam, checkpoint/resume). The animation framing clarifies WHY this matters beyond "correctness" — non-interruptible systems signal that the system is broadcasting, not responding. Verso's seam design should be framed in this language: "the agent loop is always interruptible because the loop tracks intent, not just schedule."
**Tag:** [SHARPENS] | **Section:** §1 (bet/moat — the seam) / §7 (product taste) | **Verdict:** sharpen — use the interruptibility framing in copy and docs.

---

## No-Overkill Verdict Summary
- "Never animate keyboard-initiated actions" → adopt-now as a CLI/terminal taste invariant
- Purpose test ("does this communicate something unavailable without it?") → sharpen into an explicit review question
- Cohesion across output surfaces → adopt-now as an invariant
- Interruptibility framing → sharpen §1/§7 language
- Experience-over-features market selection → confirm, already established
