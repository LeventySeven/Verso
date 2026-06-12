# How We Redesigned the Linear UI
**Source:** https://linear.app/now/how-we-redesigned-the-linear-ui
**Authors:** Karri Saarinen, Yann-Edern Gillet, Andreas Eldh, Romain Cascino
**Published:** March 28, 2024
**Status:** read_full

---

## Faithful Digest

This is a build-in-public narration of Linear's full UI redesign — not a philosophy essay but a real decision log from the people who shipped it. It is the rarest kind of writing: taste made operational, with the actual names of decisions and the cost of making them.

### The Animating Problem

The redesign was triggered by product evolution, not visual refresh itch. Linear had grown "from a simple issue tracker into a purpose-built system for product development" and the existing chrome couldn't carry that semantic weight. Three specific problems were named:

1. The product had outgrown its original information architecture
2. Clarity of application chrome and views had degraded
3. Navigation had become incoherent

Navigation was explicitly deprioritized: "the problems were complex and no longer solely a design issue." This is a surgical call — they refused to conflate a design sprint with a systems architecture problem.

### The Inverted-L Shape as the Conceptual Wedge

Karri Saarinen identifies the "inverted L-shape" as the core conceptual unit — the global chrome that controls content in the main view. Naming the shape focuses the design problem. This is an example of giving the structural decision a name before building it.

### How the Work Actually Happened

Saarinen initiated concept work **during parental leave**, working in Figma independently, designing "hundreds of screens," doing complete screen sets daily, varying by feature area (Inbox one day, roadmap/projects the next). This solo generative phase produced multiple major directions which were then shared for feedback.

Yann-Edern Gillet then stress-tested the direction. He continuously asked: **"How real could this concept car be?"** — pushing toward the north star while keeping it buildable. Two designers divided project sections simultaneously to accelerate decision-making.

### Stress Testing Dimensions

**Environment testing:** The design had to work across macOS, Windows, and browser (Electron). Navigation elements needed to be "easily removable to work with browsers." The constraint wasn't aesthetic — it was architectural. Gillet used "Apple standards" as the feel reference for native app behavior. He spent significant time "aligning labels, icons, and buttons, both vertically and horizontally in the sidebar and tabs" — acknowledging this is something users "will feel after a few minutes of using the app" rather than immediately observe.

**Appearance testing:** Saarinen used "opacities of black and white" in explorations — a decision that communicates hierarchy relationships while keeping the palette technically portable across any base color.

### The LCH Color Migration (The Most Technical Decision in the Piece)

This is the surgical detail that separates a taste essay from a craft essay.

Linear's previous theme system used HSL. The team rebuilt it around **LCH (Lightness-Chroma-Hue)**, which is "perpetually uniform" — meaning "a red and yellow both at lightness 50 appear roughly equally light to the human eye." This is a perceptual color space, not a mathematical one. HSL lightness is not perceptually linear; LCH is.

The result: "more consistently good-looking themes, regardless of which base colors are used."

The migration wasn't complete until this redesign. Custom themes had continued using HSL; only new elevated/translucent surfaces used LCH. The UI refresh extended LCH to light and dark themes.

**The quantitative result: variable definitions reduced from 98 per theme to just 3:**
1. Base color
2. Accent color
3. Contrast

The contrast variable "defines how contrasty a theme should be" and automatically generates "super high-contrast themes for users who need it for accessibility reasons." Accessibility as a derivative of a principled system — not bolted on.

Eldh on why: "We kept using LCH for our theme generation, as it is one of the closest color spaces to the human eye and allowed us to deal with different elevations for our surfaces (e.g. background, foreground, panels, dialogs, and modals)."

The team "migrated the light and dark themes to adopt the same theme generation, so it was easier for Yann and me to share the same language and iterate." Shared language between designers is a downstream product of the color system decision.

### Typography: Inter Display for Hierarchy

The team adopted **Inter Display for headings** "to add more expression to our headings while maintaining their readability" — regular Inter retained for body text. The hierarchy is encoded typographically, not through size alone.

### The Five-Phase Execution Model

1. Stress tests: Testing in main views (Inbox, Triage, My Issues, Issues List, Project, Cycles, Roadmap, Search)
2. Behavior definitions: Documenting sidebar, tabs, app headers, view headers
3. Sidebar and chrome refresh: Implementation + feature flags for internal testing
4. Private beta: Gradual rollout to selected users, expanded daily
5. GA: Full release

**Total timeline: approximately six weeks.**

Romain Cascino: "We knew that in order to move quickly and ship our work successfully, we needed to dedicate time and team resources to it. We couldn't treat it as a side project."

### The Athens Offsite as Forcing Function

An offsite in Athens early 2024 tackled the initial bulk of work on sidebar, tabs, and headers. Afternoons divided: "coding portions into groups of two engineers while designers iterated on other parts of the project, building a pipeline for us to work from." Daily back-and-forth yielded "the first working version of the new UI by the end of the week."

### Internal Testing via Feature Flag

After the offsite week, the feature flag was enabled company-wide. Feedback was routed through a dedicated Slack channel linked to the Linear project — "discussions and questions on our weekly project updates in Slack automatically synced to Linear, so we didn't lose any context between the tools or teams." They dogfooded their own tool to run the redesign.

They added "a toggle to our internal developer toolbar, as a shortcut to quickly switch the new UI feature flag on or off, which helped the team to compare different parts of the app more easily."

Different departments were strategically valuable: Product/Sales for roadmap views, project leads for documents, Customer Experience for Triage/issue views.

### Key Quotes

- "no infinite-loop processes, workshops, or sticky notes were involved"
- "How real could this concept car be?"
- "a red and yellow both at lightness 50 appear roughly equally light to the human eye"
- "We knew that in order to move quickly and ship our work successfully, we needed to dedicate time and team resources to it. We couldn't treat it as a side project."
- users will "feel after a few minutes of using the app" rather than immediately observe

---

## VERSO RELEVANCE

### [SHARPENS] §7 / §12 — The "feel after a few minutes" principle as the taste standard for CLI/API DX

The Linear team explicitly distinguishes between things users _see immediately_ versus things they _feel after a few minutes of use_. This is precisely the standard Verso's DX should be evaluated against: `agent.inspect()`, the one-flag durable promotion, the 3-line diff — these are "feel after a few minutes" features, not "wow at the demo" features. The framing gives Verso language to defend slow burns in taste.

**Verdict:** adopt-now — use this framing when writing the demo-able wedge section.

### [SHARPENS] §12 Positioning / naming — "inverted L-shape" as the model for naming structural decisions

Saarinen named the thing before building it. Verso has a structural decision — the tactical<->durable seam — that also needs a name that can be internalized before it's built. The "inverted L-shape" showed that naming a geometric/structural metaphor creates shared language between builders and later between builders and users. Verso's seam doesn't yet have a one-word anchor.

**Verdict:** sharpen — the seam needs its own named metaphor, not just "the promotion flag."

### [NEW-IDEA] §7 — 98→3 variable reduction as an analogy for the harness simplification claim

Linear went from 98 color variables to 3 by finding the underlying generative primitives. Verso's claim about "the loop is ~10 lines" is structurally the same move: reduce the combinatorial surface to a generative minimum. This is a usable rhetorical parallel — "we did to the agent loop what LCH did to Linear's theme system."

**Verdict:** adopt-now — include in the positioning/counter-positioning section as a taste analogy.

### [CONFIRMS] §2 Non-goals — "navigation was deprioritized because the problems were complex and no longer solely a design issue"

Linear explicitly refused to solve a systems architecture problem in a design sprint. Verso's non-goals section should encode the same discipline: refusing to solve orchestration topology (multi-agent graph routing) in the harness layer.

**Verdict:** confirm.

### [SHARPENS] Founder-OS — Solo generative phase before collaborative critique

Saarinen's parental-leave concept work — hundreds of screens, complete screen sets daily, solo — produced the conceptual raw material that collaborative critique then refined. This is a repeatable operating pattern: generate at volume alone first, critique collaboratively second. Anti-pattern is: design-by-committee from day one.

**Verdict:** lock-defer — file under founder-OS operating principles.

### [SHARPENS] Founder-OS / GTM — Dogfooding the product to run the product's own development

Linear used Linear (with Slack sync) to manage the redesign. The loop is tight and visible. Verso's dogfood-first principle should be equally literal: use Verso to run Verso's own CI/evals/incident response — and say so publicly. The Linear example gives a concrete model of what "dogfood-first" looks like operationally.

**Verdict:** adopt-now — make the dogfood loop explicit in GTM narrative.
