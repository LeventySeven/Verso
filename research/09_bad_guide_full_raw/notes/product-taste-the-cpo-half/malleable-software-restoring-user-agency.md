# Malleable Software: Restoring User Agency in a World of Locked-Down Apps

**Source:** Geoffrey Litt, Josh Horowitz, Peter van Hardenberg, Todd Matthews · Ink & Switch  
**URL:** https://www.inkandswitch.com/essay/malleable-software/  
**Published:** June 2025  
**Status:** read_full  
**Read time:** ~35 min  

---

## Faithful Digest

Ink & Switch's landmark essay argues that the original promise of personal computing — malleable materials users could reshape freely — was hijacked by sealed appliances. The essay is not a manifesto for a hypothetical future; it synthesizes years of working prototypes (PushPin, Cambria, Farm, Patchwork, Potluck, Embark) and articulates a coherent research program.

### Core Definition

> "Malleable software — a software ecosystem where anyone can adapt their tools to their needs with minimal friction."

Four key terms:
- **"Software ecosystem"**: technical and cultural environment, not just technical capability
- **"Anyone"**: community cooperation matters as much as individual self-sufficiency
- **"Adapting tools"**: small tweaks, deep renovations, or creating new coordinated tools — not starting from scratch
- **"Minimal friction"**: editing should feel fast and light, ideally at the moment of need

### The Core Problem: Mass-Produced Software Is Too Rigid

The guitar-maker and home-cook analogies establish the physical world baseline: "In the physical world, the act of crafting our environments comes naturally, because physical reality is malleable." Software broke this. The index-card team lost card-zone practices the moment they moved to web-based tracking: "Computerizing work led to a loss of agency."

Atul Gawande's burnout-of-physicians example is structurally important: EHR software forces doctors to fill irrelevant fields. The doctor "wasn't angered by extra time but by its pointlessness." This is the harm of inflexible software — not inefficiency, but *loss of agency and meaningfulness*.

> "When different users have different needs, a centralized development team can't possibly address everyone's problems."

### The Existing Approaches and Their Limits

The essay surveys five current approaches to customization:

| Approach | What it allows | Where it fails |
|---|---|---|
| Settings | Behavior changes developers anticipated | Disappoint when the specific need isn't there |
| Plugins | Third-party extensions within authorized API | "Plugin systems still can only edit an app's behavior in specific authorized ways" |
| Modding | Permissionless extension (browser extensions, game mods) | Requires reverse-engineering; "browser extensions can't modify server-side behavior" |
| Open Source | Full code access | "Modifying a serious open source codebase usually requires significant expertise and effort" |
| AI-Assisted Coding | NL-to-code generation | "Bringing AI coding tools into today's software ecosystem is like bringing a talented sous chef to a food court" |

The AI-as-sous-chef analogy is load-bearing: AI helps *create* but the *environment* is still closed. The problem is not code-generation capability; it is the ecosystem architecture.

### The Gentle Slope Principle

Allan MacLean's 1990 proposal (Buttons, EuroPARC):

> "Each incremental increase in tailoring power should only require a small incremental investment of learning and skill."

Systems following this rule have no vertical "cliffs." Spreadsheets are the canonical example: users begin as passive viewers, then edit input cells, then adjust formatting, then write formulas, then add sheets. No cliff; each step requires only marginal new skill.

Key qualities of gentle-slope systems:
- **In-place toolchains**: everyone using spreadsheets runs the full editor — no separate dev environment required
- **Scrappy aesthetics**: "Any change is likely to be an improvement… Do what you want. The place can't get much worse anyway." (Stewart Brand, via the essay)
- **Explicit modes** (HyperCard's 5 levels): guardrails that allow safe exploration without unintended consequences

> "Not everyone needs to reach the top of the slope." Many users stop at the level where a skilled community member can fill the gap.

### Tools, Not Apps

The avocado-slicer vs. knife distinction is the essay's sharpest analogy:

> "Many applications are avocado slicers." They bundle functionality targeting specific use cases: trip planning, workout tracking, recipe organization.

Knives are general tools — high learning cost, high generality. Text editors and spreadsheets are the knife-like software exceptions.

The two sub-problems for achieving composability:
1. **Sharing data between tools**: filesystem approach (edit same file in Lightroom and Preview); Airtable model (shared database, multiple views); Smalltalk (shared objects with behavior)
2. **Composing the user interface**: compound-document systems (OpenDoc, OLE); Tchernavskij's entanglers (a UI layer that dynamically detects and connects related elements); Dynamicland (physical-world composability as model)

> "When each application manages its own data, introducing a new tool into a workflow incurs more friction."

### Communal Creation

Individualistic malleability has limits: "We use computers together!" The essay argues for *situated software* (Clay Shirky) and *home-cooked meals* (Robin Sloan) — software built for local communities where you can respond to users directly, don't need to anticipate everyone's needs, and don't need industrial-grade reliability.

Nardi and Miller studied company spreadsheet use and found **"local developers"** — amateur enthusiasts writing coworker code bits. These are the slope-climbers who carry communities to the next level.

> "Building software for 'local' contexts is sometimes easier than building software for world-wide use."

### The Patchwork Prototype and AI Integration

Key finding from deep dogfood use (the essay itself was written in Patchwork):

> "Opportunities for software improvement can naturally emerge within malleable systems." 

The Section Word Counter tool was created *during* the writing session, in minutes, with AI assistance, without rebuilding or redeploying Patchwork. The tool immediately used existing essay documents with live updates.

> "When combined with malleable environments, AI-assisted development can make tool editing much faster."

And: generated tools in Patchwork automatically support persistence and multi-user collaboration — because the environment, not the generated code, provides these capabilities.

---

## VERSO RELEVANCE

### [NEW-IDEA] §1 Bet/Moat — "the environment is the moat, not the code generation"

The AI-as-sous-chef analogy cuts directly to Verso's defensibility argument. AI coding tools (Cursor, Claude, Copilot) can generate agent code — but they're generating into an environment that is still closed. The harness IS the environment: it provides context-density guarantees, eval surfaces, checkpoint/resume — the capabilities that make AI-generated agent code actually useful and reliable.

> "Bringing AI coding tools into today's software ecosystem is like bringing a talented sous chef to a food court."

Verso flips this: Verso IS the kitchen. AI can generate the sous chef work (the loop body), but the kitchen — the harness, the context seam, the eval corpus — is what Verso provides. This is a crisper articulation of the harness-is-the-moat argument than any prior framing.

**Verdict: adopt-now** — "Verso is the kitchen, not the recipe" should be a candidate positioning line. Strengthens §1 defensibility against the counter-argument that LLMs will auto-generate agent frameworks.

### [NEW-IDEA] §2 Non-Goals — the "avocado slicer trap" names the framework-bloat non-goal precisely

> "Many applications are avocado slicers." 

This is the exact non-goal: tool-shaped agent primitives (EmailAgent, SlackAgent, RAGAgent) are avocado slicers. They bundle functionality for specific use cases and are useless elsewhere. The Verso non-goal is not "we don't have integrations" — it is "we are not an avocado slicer." The knife analogy is the positive statement: general-purpose judgment primitives (context seam, eval surface, checkpoint) that handle every use case, not one-shot gadgets.

**Verdict: adopt-now** — "We are not an avocado slicer" should be explicit §2 language. It names the non-goal more vividly than "no feature-shaped primitives."

### [SHARPENS] §12 Positioning — "tools, not apps" as Verso's category name

The essay's own framework gives Verso a category framing sharper than "agent framework": Verso is a *tool*, not an *app*. Apps are avocado slicers. Tools are knives. An agent *framework* can be an app (LangChain's pre-built chains, agents, integrations) or a tool (Verso's harness primitives). Positioning Verso as "the tool-shaped alternative to app-shaped agent frameworks" is a precise counter-position that does not require mentioning LangChain by name.

**Verdict: sharpen** — §12 positioning: explore "tool-shaped" vs "app-shaped" as the axis of the counter-position.

### [SHARPENS] §7 Demo-able Wedge — "in-place toolchains" as the inspect() taste surface

The gentle-slope quality "everyone using spreadsheets runs the full editor — no separate dev environment required" is exactly what `agent.inspect()` does. The inspection surface is in-place: you don't leave your Python environment to observe agent state, evaluate runs, or introspect context. This is the tool taste principle: the editing/inspection capability is co-located with the using capability.

LangChain's alternative (LangSmith) requires leaving the Python environment — a cliff. Verso's inspect() is a slope.

**Verdict: sharpen** — frame inspect() as the "in-place toolchain" taste signal in §7: "you don't leave Python to observe your agent, the same way you don't leave Excel to understand your formula."

### [NEW-IDEA] §12 GTM — "local developers" as the cold-start distribution model

Nardi and Miller's finding about spreadsheet "local developers" — amateur enthusiasts who write code for coworkers and guide community slope-climbing — describes Verso's actual cold-start target: not the decision-maker, but the structurally-aware senior engineer who builds the harness that 5 junior engineers then use. That engineer IS the local developer. They carry the community. Verso's distribution model should explicitly target the local developer persona: the one person per team who has hit the harness problem and has the skill to recognize the solution.

**Verdict: adopt-now** — explicitly name this persona in §12 GTM: "the local developer" — the structurally-aware engineer who builds the harness their team lives in. This maps to the superconsumer-first DX-led GTM model already established.

### [SHARPENS] §1 Bet/Moat — "gentle slope" as the switching-costs framing

The gentle-slope framework illuminates why Verso's context seam creates switching costs: each step up the slope (ephemeral agent → checkpointed → HITL) requires only incremental learning, but the corpus of runs, invariants, and eval artifacts accumulated at each step is sunk cost that doesn't transfer. The slope itself generates lock-in. This is the switching-costs-at-the-seam argument in the Malleable Software vocabulary.

**Verdict: sharpen** — §1: articulate that the checkpoint/eval corpus accumulated via Verso's gentle slope is the switching cost. Users who reach the HITL/durable level have "learned the spreadsheet" — their corpus is not portable.

### [CONFIRMS] founder_os — dogfooding as the mechanism for taste development

The Patchwork team wrote the essay inside Patchwork. The Section Word Counter emerged from a real need during writing. This is the dogfood-first operating principle: "opportunities for software improvement can naturally emerge within malleable systems." Verso's equivalent is using Verso to build the agents that build Verso. The taste signal is internal: do Verso's own maintainers notice improvement opportunities that come from living in the tool?

**Verdict: confirm** — already established; the Ink & Switch model provides the research-backed version of the same principle.

---

## One-Line Verdict Per Finding

| Finding | Verdict |
|---|---|
| "Verso is the kitchen, not the recipe" — harness = environment that makes AI-generated code useful | adopt-now |
| "Not an avocado slicer" — non-goals: general judgment primitives, not use-case bundles | adopt-now |
| "Local developer" persona = cold-start distribution target | adopt-now |
| "Tool-shaped vs app-shaped" as positioning axis (no mention of LangChain required) | sharpen |
| inspect() as "in-place toolchain" — no cliff to LangSmith | sharpen |
| Gentle slope = switching costs from corpus accumulation | sharpen |
| Dogfood-first confirmed by Patchwork methodology | confirm |
