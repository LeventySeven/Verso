# The Curious Case of User Interfaces — Rasmus Andersson (Config 2023)

**Source:** https://www.youtube.com/watch?v=76b3c_ssyPQ  
**Speaker:** Rasmus Andersson (creator of Inter typeface; software painter at Playbit; formerly Figma)  
**Event:** Config 2023, Figma's annual design conference  
**Format:** Talk, ~1h 02m  
**Transcript via:** summarize.tech (AI-generated video summary); supplemented by staff.design/rasmus-andersson and secondary search synthesis  
**Status:** read_partial — no verbatim transcript available; sourced from AI video summary + design community coverage. Content is faithful to documented claims but verbatim quotes are unverified.

---

## What Rasmus Actually Argues

### 1. Consistency Is Psychological Safety Infrastructure

The talk's central thesis: consistent interface behavior is not an aesthetic preference but **psychological safety infrastructure**. When an action triggers a behavior in one place, users expect identical behavior throughout the system. Changing established patterns — like menu behavior — disrupts user mental models and creates background stress.

The mechanism: clear visual feedback about what is clickable and what will happen allows users to form accurate mental models. When users trust the rules, they can operate without fear of negative consequences. The moment a rule breaks, the user must re-enter a state of vigilance — background CPU cost paid on every interaction.

This frames consistency not as stylistic conservatism but as a **user contract**. The contract is: if I click here, this will happen. Violating it — even once, even justifiably — is a broken promise.

### 2. Cursor Micro-Behavior as a Case Study in Invisible Contracts

Andersson uses the blinking text cursor as a detailed example. Rules:
- Cursor should **stop blinking while typing** and resume when at rest (guided by a timer)
- Cursor movement should be **predictable and stable in motion** — no movement artifacts
- The blink rate must balance findability vs. distraction

Why does this matter? Because the cursor's behavior communicates a contract: "I know where you are, I know what you're doing, and I will behave predictably." Each deviation from expected behavior is a small psychological tax.

This is Rasmus's method: take a micro-behavior most designers ignore, expose its full decision surface, and show how each decision either honors or violates a user contract.

### 3. Input Modality Awareness

Design must account for different interaction methods (touch, mouse, keyboard). A double-click fails on touchscreens. Touch events that ignore scroll state create confusion. Designers should leverage input context — the mode the user is in — to align on-screen behavior with mental model.

He criticizes confusion arising from touchdown events that ignore scrolling behavior, and menu-open states that should alter expected interactions but don't.

### 4. Figma's Selection Model — First-Class Undoable Actions

When asked about Figma's undo/redo system for selection, Andersson explains Figma treats **selection as a first-class action**, undoable rather than just a state. Extensive user research informed this — it aligns with how users naturally think about selection: as something they did, not just something that is.

This is a concrete case where honoring the user's mental model (selection = action) required a non-trivial implementation choice.

### 5. Novelty vs. Familiarity Tension

The best interfaces balance novelty with familiarity:
- Too much novelty creates confusion; users must learn instead of do
- Too much familiarity feels stale; no delight, no progress

Figma succeeds by blending obvious familiar patterns with unfamiliar novel ones at the right ratio. The key: **users must be able to start working without learning** — then discover the novel parts through use.

### 6. Against Untested Innovation

Andersson explicitly criticizes deploying untested ideas — slow cookie banners, popup ads, animations that obstruct content. His standard: innovations must be tested rigorously before deployment. The failure mode is novelty for novelty's sake, which breaks the user contract without delivering value.

### 7. The Future of UI — Emergent Medium Problem

He compares current VR and AI interfaces to early automobiles: *"First cars were essentially carriages without horses."* VR interactions still lack industry consensus. AI interfaces are mostly limited to text inputs. Prediction: interfaces will eventually become native to their medium, but we're in the carriage-without-horses phase.

### 8. Design as Material Knowledge

From staff.design interview: senior designers must understand their materials deeply. The furniture design analogy — a chair designer must comprehend injection molding — applies to software: design is connecting humans and computers, and choosing to design software UI means choosing to work with materials.

"Coordination vs. creation represent different universes of concern." His preference: stay close to users and materials, not to org charts.

---

## Key Principles (Reconstructed — no verbatim transcript)

1. Consistency = psychological safety = user contract
2. Micro-behaviors (cursor blink, click target size) are the atomic unit of contract honoring
3. Selection as first-class undoable action = align implementation with mental model
4. Input modality must drive behavior, not just presentation
5. Novel + familiar at the right ratio = taste in interface design
6. "First cars were essentially carriages without horses" — VR and AI UI are in the carriage phase
7. Untested innovation is a broken promise written in code

---

## VERSO RELEVANCE

### [SHARPENS] §7 demo-able wedge — User Contract as Eval Standard

Rasmus's "user contract" framing is the interaction-design version of VERSO's eval primitives. An eval is a formalized user contract for agent behavior: "when the agent is given X context, it will do Y." Every time the contract breaks — the agent halts, loops, or produces slop — that is exactly the broken promise Rasmus describes. VERSO's "embedded in-process evals" are contract-specification tools.

**Tag: SHARPENS** → §7 demo-able wedge  
**Verdict:** Use "contract" language when describing evals to structurally-aware seniors. An eval is not a test; it's a promise you can execute.

### [SHARPENS] §12 positioning — "Carriage without horses" = current agent framework critique

The AI interface = carriage without horses analogy is a sharp competitive frame for VERSO. Most agent frameworks (LangChain, LangGraph) are carriages built for LLM-era constraints — sequential chains, rigid graphs — that were invented before we understood the loop. VERSO bets on native-to-medium: the harness is what's native to production agents, not the graph or the chain.

**Tag: SHARPENS** → §12 positioning  
**Verdict:** Consider using the "carriage without horses" frame when describing why existing frameworks are structural dead-ends.

### [NEW-IDEA] §1 bet/moat — Consistency-as-contract applies to the VERSO API surface

Andersson's consistency principle (same behavior everywhere = psychological safety) directly applies to VERSO's API design. If `inspect()` works one way at tactical depth and differently at durable depth, the developer is in background vigilance mode — same psychological tax. API consistency is moat: the developer's mental model shouldn't have to reload when they cross the seam.

**Tag: NEW-IDEA** → §1 bet/moat / product_taste  
**Verdict:** Add as explicit design constraint: the tactical-to-durable seam must not break the developer's mental model. One concept, two depths — not two concepts.

### [CONFIRMS] product_taste — Frequency x Novelty filter for VERSO features

The novelty vs. familiarity tension Rasmus describes maps directly to VERSO's frequency x novelty taste filter (already established). High-frequency interactions (the run loop, the eval call) should have zero animation, zero novelty — pure reliability. Novelty reserved for the upgrade path (one-flag durable seam). This confirmation gives the filter a perceptual/psychological grounding.

**Tag: CONFIRMS** → product_taste  
**Verdict:** Solid confirmation. Cite Rasmus when explaining why VERSO's core API is boring-on-purpose.
