# Design Engineering at Vercel
**Source:** https://vercel.com/blog/design-engineering-at-vercel
**Authors:** Glenn Hitchcock, Henry Heffernan, John Phamous, Rauno Freiberg, Yasmin Pessoa
**Published:** March 29, 2024
**Format:** Article (medium length)
**Fetched:** 2026-06-12

---

## Faithful Digest

This is Vercel's public definition of design engineering as an organizational discipline, written by five practitioners on the team. It is simultaneously a job post, a role definition, and a philosophical manifesto about what it means to own outcomes rather than tasks in product development.

### The Core Definition
"Design Engineers at Vercel blend aesthetic sensibility with technical skills. This allows us to deeply understand a problem, then design, build, and ship a solution autonomously."

The critical phrase is **autonomously** — the design engineer is not a relay baton. The traditional software delivery model (PM → Designer → handoff → Engineer → handoff → QA) is explicitly dismantled: "Design Engineers work closely with designers to implement designs, **skipping the traditional handoff process**." Instead, designers and design engineers iterate together in Figma or directly in code.

### What Design Engineers Care About (as a checklist)
- Delightful user interactions and affordances
- Building reusable components/primitives
- **Page speed**
- **Cross-browser support**
- Support for inclusive input modes (touch, pointers, etc.)
- **Respecting user preferences** (reduced motion, contrast, etc.)
- Accessible to users of assistive technology

The article names this explicitly: "There is a lot of work behind the pretty pixels." Design engineering is not decoration — it's the integration of performance, accessibility, and craft into a single discipline owned by one person.

### Three Operating Modes
The article describes three distinct modes of work for Vercel design engineers:

**Mode 1: Design Collaboration (embedded iteration)**
Consulting on implementation cost vs experience impact, whether components are one-off or reusable, and "prototyping explorations better executed in code than Figma." This is the "design in code" mode — the feedback loop runs through running software, not static mockups.

**Mode 2: Product Team Integration (feature-embedded)**
For features >1 month in scope. Design engineers embed with product teams, handling UI while product engineers own API/infra. When designers are not involved, the design engineer "sketches initial solutions and gathers feedback from both designers and engineers" — effectively acting as a full product designer for the UI layer.

**Mode 3: Independent Ownership (self-directed craft)**
For improvements addressable in "days to weeks": "The Design Engineer will sketch in Figma or code a solution, socialize the change, incorporate feedback, then ship it." Examples of design-led projects at Vercel:
1. Geist font with interactive playground
2. Design system documentation with interactive docs
3. Design Team homepage for testing web techniques
4. Delighters in the Vercel Dashboard

The stated principle governing this mode: **"Iterate to Greatness is one of Vercel's principles, allowing us to balance business goals with craft by shipping continuous improvements."**

### The Toolbox
"There's no fixed toolset for a Design Engineer. There's no best background." The team collectively uses: Figma, code-based design, production code, browser performance debugging, GLSL shaders, copy writing, Three.js 3D, Blender, video editing with CGI. The breadth signals: the role is defined by *judgment*, not by a tool or a credential.

### The Organizational Philosophy
"Design Engineering at Vercel means more than being a designer and an engineer. It's about **shifting from owning a specific part of the product development process to owning results**."

This is the core organizational claim: the design engineer is accountable for the outcome (user experience quality), not for a step in the pipeline. The role eliminates handoff latency by eliminating the handoff.

---

## VERSO RELEVANCE

### [NEW-IDEA] Design engineering as the structural frame for Verso as a solo CTO product
The guide note calls this "your structural advantage as a solo CTO." This article makes that advantage explicit: a founder who can design, build, and ship autonomously runs the same operating model Vercel's design engineers run — "deeply understand a problem, then design, build, and ship a solution autonomously." The solo CTO is not the designer AND the engineer in sequence; they are the design engineer in the Vercel sense: one person, one feedback loop, one owner of outcomes. Verso's product quality advantage is not "I built it myself" — it's "I eliminated the handoff entirely, which means there's no degradation between the intended experience and the shipped experience."
**Tag:** [NEW-IDEA] | **Section:** founder_os / §12 (positioning) | **Verdict:** adopt-now as a framing device for how Verso describes its product quality claim.

### [SHARPENS] "Owning results not tasks" = the precise counter-position to LangChain's abstraction layers
LangChain's architecture is a classic task-ownership decomposition: framework team owns the abstraction → user owns the application → third-party ecosystem owns the evaluations (LangSmith). Every handoff is a degradation point. Verso's counter-position — the harness is one integrated layer, owned end-to-end — is the product-organizational equivalent of Vercel's design engineering model: "shifting from owning a specific part of the product development process to owning results." This makes the counter-position concrete and human: it's about who owns the outcome, not just about what the framework does.
**Tag:** [SHARPENS] | **Section:** §1 (bet/moat / counter-positioning) / §2 (non-goals) | **Verdict:** sharpen — use "owning results not tasks" as a frame in the counter-position to LangChain.

### [SHARPENS] "Iterate to Greatness" + continuous improvement = the right GTM cadence for Verso
Vercel's stated principle of "balancing business goals with craft by shipping continuous improvements" is the correct operating model for an OSS-first, DX-led product. Verso should not be announced as "complete" — it should be launched and then visibly iterated. The design engineer's Mode 3 (days to weeks, self-directed craft improvements) is the exact cadence for a solo-founder OSS project: small, visible, opinionated improvements that accumulate into a quality signal. The GTM implication: the build-in-public loop IS the product quality demonstration.
**Tag:** [SHARPENS] | **Section:** §12 (GTM / distribution loops) | **Verdict:** sharpen — frame the X build-in-public channel as "Iterate to Greatness" in public.

### [CONFIRMS] Performance, a11y, and craft as integrated, not siloed
The checklist (page speed, cross-browser, reduced motion, assistive tech, inclusive input modes) confirms that Verso's taste invariants — performance-first, accessibility-by-default, preference-respecting — are correct. For Verso's CLI/SDK surfaces: speed of output, graceful degradation in constrained environments (no TTY, CI, etc.), and respecting terminal preferences (color, width, verbosity) are the exact analogs. Already established; no new action.
**Tag:** [CONFIRMS] | **Section:** §7 (product taste) | **Verdict:** confirm, already in the PRD.

### [NEW-IDEA] "No fixed toolset, no best background" → Verso's persona breadth argument
The design engineer role is defined by judgment not credential. The article explicitly states: "There's no fixed toolset for a Design Engineer. There's no best background." This is a direct analog to Verso's primary persona definition: the structurally-aware senior/AI engineer. That persona is not defined by a tool (not "LangChain user") or a credential (not "ML researcher") — it's defined by the judgment to know when to use a framework and when to build a primitive. This makes the persona statement sharper: Verso is for engineers who own outcomes, not for engineers who use tools.
**Tag:** [NEW-IDEA] | **Section:** §12 (positioning / persona) | **Verdict:** adopt-now as a sharpening lens for the persona description.

### [NEW-IDEA] "Code-based design" and "prototyping in code not Figma" → Verso's demo-as-product argument
Vercel design engineers prototype "better executed in code than Figma." The same principle applies to Verso's demo strategy: the authoritative demo is the running code (the 3-line side-by-side, the one-flag durable diff), not a slide or diagram. Any Verso "design" decision — how inspect() formats output, how streaming deltas appear, how error messages read — should be prototyped in running code, not in a spec doc. The artifact IS the argument.
**Tag:** [NEW-IDEA] | **Section:** §7 (demo-able wedge / product taste) | **Verdict:** adopt-now as a process principle for how Verso decisions are prototyped.

---

## No-Overkill Verdict Summary
- Solo CTO = design engineer (eliminates handoff degradation) → adopt-now as a positioning frame
- "Owning results not tasks" → sharpen as the counter-position to LangChain's abstraction decomposition
- "Iterate to Greatness" = build-in-public cadence → sharpen GTM language
- Performance + a11y + craft as integrated → confirm, already established
- Persona = judgment not credential → adopt-now to sharpen the primary persona description
- Code-as-prototype → adopt-now as a process principle for Verso's design decisions
