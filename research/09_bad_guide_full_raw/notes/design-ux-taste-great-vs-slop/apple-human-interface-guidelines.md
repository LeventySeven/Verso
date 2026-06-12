# Apple Human Interface Guidelines
**Source:** https://developer.apple.com/design/human-interface-guidelines
**Author:** Apple
**Format:** Reference documentation (very long; paginated)
**Fetched:** 2026-06-12
**Status:** read_partial — the top-level HIG index page blocked direct fetch (JavaScript-rendered, no static content returned). Fetched the archived iOS HIG fundamentals page (developer.apple.com/library/archive/…/Fundamentals.html) which contains the foundational principles section in full text. The current HIG landing page was not fetchable but the Design Principles sub-page content was partially recovered via search.

---

## Faithful Digest

The HIG is Apple's canonical articulation of what makes software feel native, trustworthy, and intuitive. The source fetched is the foundational principles section from the iOS HIG (archival), which is the part most relevant to Verso's product taste layer. The organizing claim: "An app (or a device) is easy and enjoyable for people to use when its human interface builds on the ways in which people actually think and behave."

### The Six Core HIG Principles

**1. Aesthetic Integrity**
"Aesthetic integrity is not a measure of how beautiful an app is; rather, it's a measure of how well the appearance of the app integrates with its function." A visually elaborate app with incoherent function has poor aesthetic integrity. A plain app where every visual decision serves a functional purpose has excellent aesthetic integrity. This is the principle that separates taste from decoration.

**2. Consistency**
"Consistency in the interface allows people to transfer their knowledge and skills from one app to another." Three layers of consistency: with platform standards, within itself, and with earlier versions of itself. Inconsistency forces relearning — it is a tax on the user. The backward-compatibility dimension ("with earlier versions of itself") is underemphasized in most discussions but critical: breaking consistency with prior behavior is a trust violation.

**3. Direct Manipulation**
"When people directly manipulate onscreen objects instead of using separate controls to manipulate them, they're more engaged with the task and they more readily understand the results of their actions." The intervention of an abstraction layer (a control that manipulates an object rather than the object itself) creates distance between intent and effect. Direct manipulation eliminates that distance.

**4. Feedback**
"Feedback acknowledges people's actions and assures them that processing is occurring. For example, people expect immediate feedback when they operate a control, and they appreciate status updates during lengthy operations." Two modes: immediate acknowledgment (control response) and progress assurance (long operations). Both are forms of the same commitment: the system is honest about what is happening.

**5. Metaphors**
"When virtual objects and actions in an app are metaphors for objects and actions in the real world, users quickly grasp how to use the app. The most appropriate metaphors suggest a usage or experience without enforcing the limitations of the real-world object or action on which they're based." The key qualifier: the metaphor should suggest without constraining. A folder metaphor that can hold unlimited items is better than one that enforces a physical capacity limit.

**6. User Control**
"Although an app can suggest a course of action or warn about dangerous consequences, it's usually a mistake for the app to take decision-making away from the user. The best apps find the correct balance between giving people the capabilities they need and helping them avoid dangerous outcomes." This is the philosophical basis for HITL: the system should not take consequential actions on behalf of the user without explicit authorization.

### Supplementary Principles (from the iOS HIG fundamentals text)

The document also lists practical guidelines that operationalize the six principles:
- Focus on the primary task
- Make usage easy and obvious
- Use user-centric terminology
- Make targets fingertip-size (Fitts's Law)
- De-emphasize settings
- Use UI elements consistently
- Use subtle animation to communicate
- Ask people to save only when necessary

The "ask people to save only when necessary" guideline is notable: it is the UI analog of Verso's checkpoint/resume design — the system should persist state automatically except when explicit user decision is required.

### The Perceptual Reasoning Behind Metaphor
The document's framing: design principles "codify several high-level aspects of human-device interaction that have a perceptible effect on the user experience." The word "perceptible" is load-bearing — these principles are not abstract values, they are causal explanations for why users feel wrong when interfaces violate them. A popover that "seems to emerge from different areas on the screen without apparent reason" is a spatial consistency violation. A control that doesn't respond immediately is a feedback violation. Users don't articulate these principles — they just feel that something is wrong.

### The User Control Principle as a Design Argument
The HIG's framing of user control is more nuanced than "always ask the user." It is: suggest and warn, but do not decide for the user. "It's usually a mistake for the app to take decision-making away from the user." The phrase "usually a mistake" acknowledges that some automation is correct — but the burden of proof is on the automation, not on the human override.

---

## VERSO RELEVANCE

### [SHARPENS] "Aesthetic integrity = function-appearance coherence" → Verso's taste invariant sharpened
The HIG definition of aesthetic integrity is a better formulation than "looks good." Applied to Verso: every visual or textual element in Verso's output surfaces (CLI output, inspect() formatting, error messages, streaming deltas) should be justified by function. A progress bar that adds visual richness without communicating actionable state has poor aesthetic integrity. A plain timestamped log line that tells the engineer exactly what the agent did has excellent aesthetic integrity. This sharpens the existing taste invariants.
**Tag:** [SHARPENS] | **Section:** §7 (product taste / demo-able wedge) | **Verdict:** sharpen — use "function-appearance coherence" as the definition of taste in Verso's design language.

### [SHARPENS] Consistency with prior versions → API stability as a trust invariant
The HIG's three-layer consistency requirement (platform, self, prior versions) makes explicit that breaking changes are trust violations, not just inconveniences. For Verso: API stability across versions is not an engineering concern — it is a taste and trust concern. The DX-led GTM relies on developer trust; breaking changes erode it disproportionately for a framework product where migration cost is high. "Consistent with earlier versions of itself" should be a stated Verso principle.
**Tag:** [SHARPENS] | **Section:** §2 (non-goals / principled refusal) / §1 (switching costs at the seam) | **Verdict:** sharpen — make API stability a named product principle, not just an engineering constraint.

### [CONFIRMS] User Control principle = the philosophical basis for HITL
"It's usually a mistake for the app to take decision-making away from the user." This is the HIG's formulation of exactly why Verso's HITL seam is correct. It also calibrates the claim: HITL is not about distrust of AI — it is about the fundamental HIG principle that consequential decisions should remain with the human. This is a long-standing design principle applied to agent systems, not a novel AI-safety claim.
**Tag:** [CONFIRMS] | **Section:** §1 (bet/moat) / §2 (non-goals) | **Verdict:** confirm — the HITL argument is already established; the HIG provides a 40-year-old citation.

### [NEW-IDEA] "Metaphors suggest without constraining" → Verso's seam should not inherit the limitations of its metaphor
The HIG principle: "The most appropriate metaphors suggest a usage or experience without enforcing the limitations of the real-world object or action on which they're based." If Verso uses a "git branch" metaphor for the tactical-to-durable promotion, it must not inherit git's merge conflicts, branching complexity, or push/pull mental model. If it uses a "checkpoint" metaphor, it must not enforce video-game checkpoint limitations (you must reach the checkpoint, you can't checkpoint anywhere). The seam's metaphor should be chosen to suggest resumability and persistence without constraining the developer's agency.
**Tag:** [NEW-IDEA] | **Section:** §12 (naming / positioning) / §7 (product taste) | **Verdict:** adopt-now as a constraint on choosing the right metaphor for the seam.

### [NEW-IDEA] "Ask people to save only when necessary" → Verso's auto-checkpoint principle
The HIG guideline "ask people to save only when necessary" is the 1987 version of Verso's checkpoint/resume design principle. The agent framework should persist state automatically; the developer should only be asked to make a persistence decision when the decision is genuinely consequential (e.g., before a destructive action, before crossing the HITL seam). "Save dialogs" — asking the developer to configure checkpointing in advance — are an anti-pattern. The system should checkpoint silently and surface the checkpoint only when it's needed.
**Tag:** [NEW-IDEA] | **Section:** §7 (product taste) / §5/§6 (primitives) | **Verdict:** adopt-now as a design principle for checkpoint UX.

### [SHARPENS] Direct manipulation → Verso's inspect() as direct manipulation of agent state
The HIG principle: "when people directly manipulate onscreen objects, they're more engaged with the task and they more readily understand the results of their actions." For Verso: `agent.inspect()` is the direct manipulation surface for agent state. It should not be a read-only diagnostic report — it should be an interactive surface where the engineer can directly adjust context, inject messages, or modify state. The current framing of inspect() as a "taste surface" is correct but undersells it: inspect() is Verso's direct manipulation primitive.
**Tag:** [SHARPENS] | **Section:** §7 (demo-able wedge / product taste) | **Verdict:** sharpen the inspect() vision toward interactive state manipulation, not just read-only inspection.

---

## No-Overkill Verdict Summary
- Aesthetic integrity = function-appearance coherence → sharpen as Verso's taste definition
- Consistency with prior versions = trust → sharpen as a named API stability principle
- User Control = HITL philosophical basis → confirm, 40-year citation
- Metaphors suggest without constraining → adopt-now for seam metaphor selection
- "Save only when necessary" → adopt-now as auto-checkpoint design principle
- Direct manipulation → sharpen inspect() toward interactive state surface
