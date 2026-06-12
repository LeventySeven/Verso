# Why Chatbots Are Not the Future

**Source:** Amelia Wattenberger  
**URL:** https://wattenberger.com/thoughts/boo-chatbots/  
**Type:** Essay with live interactive demos (~2k words)  
**Section:** Product Taste (the CPO half)  
**Status:** read_full

---

## Faithful Digest

Wattenberger's essay is the canonical statement of the **anti-chat affordances case** — not from a skeptic of AI, but from someone who actively builds AI interfaces. The argument is four-pronged, converging on a single design principle: chat is the wrong substrate for most AI-augmented work.

### Argument 1: Text Inputs Lack Affordances

The opening is architectural. "Good tools make it clear how they should be used. And more importantly, how they should _not_ be used." A blank text input violates this principle completely. It looks identical to a search box, a login form, a Google query. It provides zero signal about:

- What kinds of questions the system can answer well
- What constraints or capabilities are built in
- What format of input produces good output

The glove analogy is precise: a glove communicates its purpose through physical shape — the five-fingered form tells you what it's for, what it fits, what it can't fit. The chat box communicates nothing. Users are left to discover capabilities by trial and error, which is not the same as having affordances baked in.

### Argument 2: Prompts Are Accumulated Context That Belongs in the UI

Every token a user types into a prompt is context that _could_ be embedded as a control. The "Awesome ChatGPT Prompts" project — which lists hundreds of elaborate prompt templates — is cited as evidence of this failure: we've outsourced UI design to a text file. A dream interpretation prompt might specify: "You are a dream interpreter. You respond in the style of a Jungian analyst. The dreamer wants symbolic associations, not literal readings." All of that is UI that someone else had to write.

Wattenberger contrasts this with:
- **PenPal**: An AI writing interface with explicit controls for writing type, audience, tone, and inspirations — each constraint is a slider/toggle rather than a paragraph of prompt preamble.
- **Copilot for Docs**: Sliders that let developers specify their experience level, adjusting response verbosity and assumed context without any prompt engineering.

The implication: the less UI a team builds around an AI capability, the more cognitive burden they've silently transferred to the user. This is a product failure, not a user failure.

### Argument 3: Responses Are Isolated — No Working Buffer

Once a chatbot responds, the prior state disappears into the scroll. Using a Walden Pond text-editing example, Wattenberger shows the problem viscerally: ask ChatGPT to rewrite a paragraph, receive a new paragraph, now try to compare them. You must scroll back and forth, read line by line, reconstruct the diff in your head. There's no visual representation of what changed. No "working buffer" that tracks modifications.

This isn't just inconvenient — it breaks the feedback loop that makes iterative creative work possible. You can't evaluate what you can't see side-by-side.

### Argument 4: The Implementation-Evaluation Loop Is Broken

This is the deepest claim. Wattenberger identifies a fundamental cognitive rhythm in skilled work: **implement** (make a change) → **evaluate** (assess the change) → repeat. Good tools give the practitioner control over when they switch between these modes.

Chat inverts this. The user initiates, then waits, then receives a completed artifact they must evaluate before they can act again. There's no mid-stream intervention. There's no "pause and look." The latency compounds the problem — the gap between action and feedback is long enough to break flow state entirely.

The word "flow state" appears explicitly. The diagnosis: chatbots make flow impossible because the user is always reacting rather than acting.

### The Automation Spectrum / "No Man's Land"

Wattenberger frames a 0%–100% automation spectrum. The dangerous zone is the middle:

> When "the human is still required to make decisions, but they're not in control of the outcome."

This is "No Man's Land." It produces **passive machine operators** — people who push a button, receive content, and approve it without real engagement. The output doesn't feel like theirs. The cognitive buy-in is absent. This is both a quality problem (the work is worse because the human isn't engaged) and a value problem (the human doesn't value what they didn't make).

The prescription: design for the extremes of the spectrum. Either automate fully (the human doesn't need to decide) or give the human genuine control (the human is in the driver's seat). The middle is where bad products live.

### The Vision

The closing is constructive, not pessimistic. The ask is for "more tools and fewer operated machines." Specific vision elements:

- Interfaces that embed contextual controls rather than requiring textual specification
- Visual diff representations so edits are traceable
- "Manipulating geometry in the latent space" for prose editing — the user adjusts along axes (formality, density, rhythm) rather than issuing rewrites
- Tools "that offer suggestions to help us gain clarity" rather than replacing human judgment

The tone is: this is a design problem, and it's solvable. The failure is not AI — the failure is the lazy default of the empty text box.

---

## Key Verbatim Quotes

1. "Good tools make it clear how they should be used. And more importantly, how they should _not_ be used."
2. "Every element that a user types into a prompt is context."
3. "When the human is still required to make decisions, but they're not in control of the outcome." [on No Man's Land]
4. "More tools and fewer operated machines."
5. "Manipulating geometry in the latent space" [the prose-editing vision]

---

## VERSO RELEVANCE

### §7 / §12 — Demo-able Wedge + Product Taste [SHARPENS]

Wattenberger's affordances argument directly validates Verso's `agent.inspect()` surface. The empty chat box has no affordances; `inspect()` is the exact opposite — it makes the agent's state, context window, and decision points visible. This is not a diagnostic tool; it's a **taste statement**: we believe the practitioner should be able to see what the system is doing at every point. The glove analogy maps cleanly: Verso's API shape should communicate what it's for.

**Finding:** The absence of affordances in chat is the same failure as a black-box agent. `inspect()` is Verso's affordance claim.  
**Tag:** SHARPENS  
**PRD section:** §7 (demo-able wedge)  
**Verdict:** adopt-now — make `inspect()` the explicit affordance argument in the demo

### §7 — The Working Buffer / Eval Visibility [NEW-IDEA]

The "isolated responses" argument maps to a gap in Verso's current positioning: we haven't named the **traceability problem** as a first-class product concern. The diff analogy is precise: without a working buffer, practitioners iterate blind. Verso's eval layer implicitly solves this (evals are the persistent record of what changed and why), but the positioning hasn't connected this to the practitioner's need to *see* the delta.

**Finding:** Evals-as-working-buffer is an undeveloped product-taste claim. The question "how do you compare run v1 to run v2?" is the same as Wattenberger's Walden diff problem.  
**Tag:** NEW-IDEA  
**PRD section:** §7 (product taste / demo-able wedge)  
**Verdict:** sharpen — add "trace what changed across runs" as a named value of the eval harness

### §2 — Non-Goals: The Anti-Chatbot Position [CONFIRMS]

Verso is not a chat framework. This essay provides the principled-design language for why: chat has no affordances, forces users into the dangerous middle of the automation spectrum, and breaks the implementation-evaluation loop. Verso's principal persona (the structurally-aware senior engineer) explicitly does not want to build "passive machine operators" — they want tools that preserve human agency and give practitioners control over when they evaluate.

**Finding:** The "No Man's Land" framing is quotable for §2 non-goals: Verso is explicitly not building for the passive-operator middle.  
**Tag:** CONFIRMS  
**PRD section:** §2 (non-goals / principled refusal)  
**Verdict:** confirm — use "No Man's Land" framing in the non-goals section

### §12 — Positioning: Counter-Position to Prompt-Engineering Frameworks [SHARPENS]

LangChain's core UX is essentially a programmable chatbot harness — you pass prompts, you get responses, you chain them. Wattenberger's critique of "the Awesome ChatGPT Prompts" problem applies directly: LangChain has systematized context-pile prompt engineering as a paradigm. Verso's counter-position — "we don't force the graph, we give you the harness" — can be sharpened with this language: we don't make you write the prompt; we make the context visible.

**Finding:** The "prompts as accumulated context" critique of chat maps to a sharper LangChain counter-position: Verso's harness externalizes context as structure, not as text.  
**Tag:** SHARPENS  
**PRD section:** §12 (positioning / counter-position)  
**Verdict:** sharpen — the affordances argument supports "context engineering" over "prompt engineering" as Verso's vocabulary

### §1 — Bet / Moat: Implementation-Evaluation Loop as Defensibility [NEW-IDEA]

The flow-state argument has a moat implication. If the implementation-evaluation loop is broken by latency and mode-switching, then the frameworks that fix it accumulate data (eval corpora) that represent the practitioner's judgment expressed as a working buffer. Verso's eval layer is that buffer. Over time, a team's eval corpus is a captured version of their taste — and taste captured as data is a switching cost.

**Finding:** The implementation-evaluation loop is not just UX — it's the mechanism by which eval corpora accumulate. Teams that build their taste into Verso's eval harness create switching costs that mirror the "working buffer" Wattenberger describes.  
**Tag:** NEW-IDEA  
**PRD section:** §1 (bet / moat / switching costs)  
**Verdict:** lock-defer — this is a second-order moat argument; surface it in §1 once the eval flywheel is named more explicitly

---

## No-Overkill Verdicts

| Finding | Verdict |
|---|---|
| `inspect()` as the affordance statement | adopt-now |
| Evals-as-working-buffer positioning | sharpen |
| "No Man's Land" in non-goals | confirm |
| Prompts-as-context → harness-externalizes-context | sharpen |
| Eval corpus as captured taste / switching cost | lock-defer |
