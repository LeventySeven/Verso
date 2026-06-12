# Web Interface Guidelines
**Source:** https://github.com/raunofreiberg/interfaces
**Author:** Rauno Freiberg
**Published:** living document (repo: 1.9k stars, 60 forks at time of read)
**Status:** read_full

---

## Faithful Digest

A version-controlled living checklist of implementation-level DX/UX decisions. Not a philosophy essay — a compiled diff of the thousand micro-decisions that separate "feels good" from "default." The document's form IS its argument: the fact that these decisions are enumerable, versioned, and checkable means that taste is not mysterious. It is a sum of specific, learnable calls.

### Complete Guidelines by Category

#### Interactivity
- Clicking input labels should focus the input
- Inputs wrapped in `<form>` for Enter submission
- Appropriate input `type` attributes (`password`, `email`, etc.)
- Disable `spellcheck` and `autocomplete` most of the time
- HTML form validation via `required` attribute
- Input prefix/suffix icons: absolutely positioned with padding (not layout-shifting)
- **Toggles should immediately take effect — no confirmation dialogs**
- **Buttons disabled after submission to prevent duplicate requests**
- Interactive elements: disable `user-select` for inner content
- Decorative elements (glows, gradients): disable `pointer-events`
- **No dead zones between list items — increase padding instead**

#### Typography
- `-webkit-font-smoothing: antialiased` for legibility
- `text-rendering: optimizeLegibility`
- Fonts subset to content/alphabet/language
- **Font weight must NOT change on hover/selected state** (prevents layout shift)
- Font weights below 400 not used
- Medium headings: 500–600 weight
- Fluid sizing: `clamp(48px, 5vw, 72px)` for headings
- **`font-variant-numeric: tabular-nums` for numbers** — timers and number columns don't reflow
- `-webkit-text-size-adjust: 100%` to prevent iOS landscape resize

#### Motion
- Theme switches: no transitions/animations (prevents flash artifacts)
- **Animation duration ≤ 200ms for interactions to feel immediate**
- Animation values proportional to trigger size
- **Dialog scale: fade and scale from ~0.8, not 0→1**
- **Button press scale: ~0.96 or ~0.9, not 1→0.8**
- Frequent/low-novelty actions: avoid extraneous animation
- **Looping animations: pause when not visible** — offloads CPU/GPU
- `scroll-behavior: smooth` for in-page anchor navigation

#### Touch
- Hover states invisible on touch press — use `@media (hover: hover)`
- **Input font-size ≥ 16px** to prevent iOS zoom on focus
- No input auto-focus on touch (keyboard covers screen)
- `muted` + `playsinline` on `<video>` for iOS autoplay
- Disable `touch-action` for custom pan/zoom gesture components
- `-webkit-tap-highlight-color: rgba(0,0,0,0)` to remove iOS tap highlight

#### Optimizations
- Large `blur()` values for `filter`/`backdrop-filter` may be slow
- Scaling/blurring filled rectangles causes banding — use radial gradients
- Sparingly use `transform: translateZ(0)` for underperforming animations
- Toggle `will-change` on scroll animations only during the animation
- Auto-playing too many videos on iOS chokes the device
- **Bypass React's render lifecycle with refs for real-time values**
- Detect and adapt to hardware and network capabilities

#### Accessibility
- Disabled buttons: no tooltips (not accessible)
- Focus rings: `box-shadow`, not `outline` (respects border-radius)
- Sequential list navigation: ↑ ↓ keys
- Sequential list deletion: ⌘ Backspace
- Dropdowns: trigger on `mousedown`, not `click` (opens immediately on press)
- SVG favicon with `style` tag for system theme adherence
- Icon-only elements: explicit `aria-label`
- Hover-triggered tooltips: no interactive content inside
- Images: always `<img>` for screen readers
- HTML illustrations: explicit `aria-label`
- Gradient text: unset gradient on `::selection`
- Nested menus: use a "prediction cone"

#### Design
- Optimistic UI updates with server rollback
- Auth redirects on server before client loads
- Style `::selection` state
- Display feedback relative to its trigger
- Empty states: prompt to create with optional templates

---

## VERSO RELEVANCE

### [NEW-IDEA] §7 Demo-able wedge — The checklist form as a taste surface for Verso's DX

Freiberg's repo exists because taste IS enumerable at the implementation level. The analogy for Verso: `agent.inspect()` could ship with a comparable internal checklist of invariant checks — not a vague "agent health" score but named, checkable assertions the engineer can audit. The checklist form itself is a taste signal — it says "we thought about this specifically enough to name it."

**Verdict:** adopt-now — the checklist-as-taste-surface idea is directly applicable to how Verso presents its eval/inspect output.

### [SHARPENS] §7 / §12 — "Feel after a few minutes" operationalized

The Linear piece said users feel quality after a few minutes; Freiberg's list is what produces that feeling. The specific items that map onto Verso's DX:
- **Toggles should immediately take effect** → the one-flag durable promotion should be instantaneous, no confirm dialog, no ceremony
- **No dead zones between list items** → in a CLI output, no dead space between step traces — padding/density should be intentional
- **Animation ≤ 200ms for interactions** → CLI streaming response should feel below perceptual threshold, not batched/chunky
- **Buttons disabled after submission** → Verso's `run()` should be idempotent-by-design, not double-submit-safe by accident

**Verdict:** adopt-now — use as a DX implementation checklist analog when designing the CLI output surface and inspect() display format.

### [CONFIRMS] §2 Non-goals — defaults are where slop lives

Every item on Freiberg's list exists because a framework/library/browser left a bad default in place. This confirms Verso's non-goal: do not expose raw defaults. Every surface Verso presents to the user (CLI output format, inspect() return shape, checkpoint file structure) should have an explicit taste decision behind it, not a default.

**Verdict:** confirm.

### [NEW-IDEA] §12 Positioning — "a thousand small decisions no model makes for you"

The guide-note for this source in the brief says exactly this: "The literal operationalization of this section's thesis that great-versus-slop is a thousand small decisions no model makes for you." This phrase is usable verbatim in Verso's positioning narrative — specifically in the anti-framework counter-position. The vibe-coding wave produces agents that hit every bad default; the structurally-aware engineer needs a harness that encodes the thousand right decisions.

**Verdict:** adopt-now — this framing is sharper than "better than LangChain." Use it.

### [SHARPENS] Founder-OS / product taste — `font-variant-numeric: tabular-nums` as the test for care

The tabular-nums item is the canonical example of a decision a model never makes: it requires knowing that timers and number columns reflow without it, which requires having been burned by the reflow, which requires having shipped production UIs at sufficient fidelity to notice. This is exactly the kind of thing that distinguishes a taste-carrying founder from a first-draft-shipping founder. For Verso: the equivalent is knowing that checkpoint files need deterministic key ordering (not JSON default insertion order) so diffs are readable — the kind of thing you only know if you've actually operated an agent in production.

**Verdict:** sharpen — use as an example in the §7 taste surface section to concretize "what the harness encodes."
