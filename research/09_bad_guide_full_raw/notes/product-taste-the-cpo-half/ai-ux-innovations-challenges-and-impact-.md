# AI & UX: Innovations, Challenges, and Impact (ft. Henry Modisett)

**Source:** https://www.youtube.com/watch?v=a1HZU2qEo1c
**Speaker:** Henry Modisett (VP Design, Perplexity) · NN/g UX Podcast ep. 36 · with Kate Moran · ~45m · Feb 2024
**Status:** read_partial

**What was searched / found:**
- NN/g published a companion article at nngroup.com/articles/perplexity-henry-modisett/ — fetched and read in full. This is the primary source for the digest below.
- LukeW published talk notes (Sutter Hill Ventures version of the same talk, lukew.com/ff/entry.asp?2095=) — fetched; paywalled at LukeW but key arguments surfaced via web search excerpts.
- Medium interview (medium.com/conversation-with-leaders) — fetched; partial content on team/iteration philosophy.
- Google Design Config 2024 notes and YesChat transcript of Config 2024 talk (joeVL4Hk1OQ) — fetched; partial coverage of design-engineering collaboration themes.
- No full video transcript found. YouTube auto-captions not accessible via WebFetch. No third-party transcript mirror found for the NN/g episode specifically.

The NN/g companion article is substantive (covers all major themes from the episode) and is treated as the authoritative source. Several quotes are confirmed verbatim from this article and confirmed by web search result snippets.

---

## What Henry Modisett Actually Argues

**Thesis:** Prompting is a temporary UX anti-pattern that will not survive. Most products should not be a chat and should not anthropomorphize AI. The right approach is to narrow product scope, lean on existing mental models, and treat AI as embedded infrastructure — not as the interface itself.

### 1. Narrow product scope enables better UX
Perplexity's core design decision was to focus exclusively on information-seeking rather than build a general-purpose assistant.

> "Finding information as fast as possible has been a flag that we planted really early on in our product-design and engineering principles."

By narrowing scope, the design problem becomes tractable: the team could build UI specifically optimized for that job rather than attempting a universal interface. This reflects the flexibility-usability tradeoff — broader systems become harder to use.

Perplexity's view of itself:
> "Perplexity was supposed to be just the fastest way to get information. What it's become is something even bigger than that — this bridge between you and all the information that's available in the world."

### 2. Prompting is the worst software experience ever — and it will not survive
> "I think prompting is the worst software experience ever. We're in a small blip of software experience where this is even going to be a thing; there's no way it survives."

This is Modisett's sharpest claim: the current era of prompt engineering is a transitional anti-pattern, not a durable interaction paradigm. Users don't want to become power-prompters; they want to get things done using patterns they already know.

### 3. Lean on existing mental models — don't invent new grammar
Many new users attempt simple keyword searches with AI tools, importing habits from traditional search engines. ChatGPT and Midjourney don't support this well; Perplexity does deliberately.

Perplexity's input field resembles a traditional search box, so:
> "You can type and it feels familiar. You can just type something, maybe how you would use Google or ChatGPT... My goal is just to get you to try it."

This is external consistency applied to AI: respect the mental model the user already has, lower the activation energy for the first interaction, earn the right to teach them a new pattern later.

### 4. Not everything should be a chat — and most products don't benefit from anthropomorphization
> "Not everything should be a chat. Actually, most products should not be a chat, and most products don't benefit from having an anthropomorphized concept."

This is Modisett's most counterintuitive public claim given Perplexity is itself a conversational product. His argument: anthropomorphization is a design choice that only makes sense in specific contexts. Adding a chatbot to an existing product that didn't need it introduces cognitive overhead and misleads users about the product's nature.

From the Sutter Hill talk (lukew.com notes, confirmed by web search excerpts): the "fork said bon appétit" example makes the point viscerally — if your fork greeted you warmly before every use, you'd find it insufferable. Anthropomorphizing the wrong surface poisons the experience.

### 5. AI as embedded infrastructure, not the interface
> "This technology is just going to be available in everything and everywhere. It'll just be a way to enable some core product experience."

Rather than forcing chatbot interfaces everywhere, AI will become embedded functionality — like networking or storage — invisible when it's working and only noticeable when it fails. The product experience is the interface; AI enables it.

### 6. Product mechanics matter more than aesthetics; design process must change
From the Sutter Hill / Config 2024 versions of the talk:
- The traditional PRD → Design → Engineering → Ship process is obsolete.
- Modisett's team designs directly in React, building functional prototypes to test interfaces during development.
- New cycle: Strategic conversation → Prototype to working state → Prune possibilities → Design → Ship → Observe.
- "The main focus has become less about how we'll build it and more of an ongoing evaluation of quality — is this good yet?"
- Product mechanics (how it functions) matter more than visual design — drawing from game design: mechanics → dynamics → aesthetics.

### 7. Non-determinism requires a new design discipline
AI products produce unpredictable outputs from both users and the AI. This requires:
- Designing for a range of outputs rather than a single correct state
- Deciding when to anthropomorphize AI and when to treat it as a tool (context-dependent)
- Accepting that "technological innovation is outpacing our ability to thoughtfully apply it"

The anthropomorphism decision specifically: "If your fork said 'bon appétit' every time you picked it up, people would get sick of that." Personality and warmth are features — powerful when deployed deliberately, toxic when sprayed indiscriminately.

### 8. Opinionated products and speed as quality enabler
> "If you ship something and realise it could be better a week later, users won't remember the worse version." (Medium interview)

> "If you invest in velocity, you can actually make more things good, more of the time."

> "Invest in systems that make it hard to make things bad."

> "80/20 everything, but we do that every week."

Strong opinions embedded in code produce superior software. The best software comes when people with strong opinions on how it should work are working directly in the medium.

---

## VERSO RELEVANCE

### [CONFIRMS] §2 Non-Goals / Principled Refusal — "prompting is the worst UX and will not survive"
Modisett's blunt claim validates Verso's UX posture: the harness should *hide* the prompt engineering layer from the agent-loop author wherever possible, not expose it as a power feature. If prompting is a temporary anti-pattern, then a harness that forces users to hand-craft system prompts at every call is accruing tech debt on a vanishing paradigm. Verso's context engineering layer (the part that manages system prompt composition, context density, tool injection) is precisely the abstraction that makes prompting *not a user's problem*.
**Verdict:** frames Verso's context engineering layer as eliminating a known UX anti-pattern, not just adding convenience.

### [SHARPENS] §12 Positioning — "narrow scope → better UX" as the positioning template
Modisett's case is that narrowing to a specific job (information-seeking) made Perplexity's UX better, not weaker. This directly maps to Verso's positioning discipline: "agent harness for the 2nd/3rd production agent" is the narrow scope. Trying to also be the framework for vibe-coders, or the research sandbox, or the ML pipeline orchestrator dilutes the product. The clarity of scope is what enables excellent UX on the specific job. Perplexity's example gives the clearest industry-level proof that this is the right call.
**Verdict:** use the Perplexity scope-narrowing case as a mental model for resisting expansion requests.

### [NEW-IDEA] §7+§12 Demo-able Wedge — "lean on existing mental models" as onboarding principle
Modisett's design tactic (make the input field look like a search box so the first action is familiar) points to a Verso onboarding principle not yet explicitly articulated: the first thing a new user does with Verso should feel like something they've done before. The `run()` loop should feel like a for-loop with a model call; the eval should feel like a test; the durable promotion should feel like adding a decorator. If the API surface forces users to learn a new grammar before they can do the first useful thing, Verso is making the same mistake as products that abandon users' existing mental models.
**Verdict:** explicit design principle — every Verso API surface should map to a pattern the target user already knows; new grammar only where strictly necessary.

### [CONFIRMS] §7+§12 Product Taste — "not everything should be a chat" as anti-anthropomorphization filter
Verso should not add personality, a "friendly assistant" persona, or warm conversational language to its CLI/SDK surfaces. The harness is a tool; tools should behave like tools. Modisett's principle confirms the "knives-not-avocado-slicers" and "explain without AI" taste decisions already established. The inspect() surface in particular should feel like a debugger, not a chatbot.
**Verdict:** reinforces existing taste decisions on Verso's UX tone. The "fork said bon appétit" example is useful as an internal check — would this UX choice read as the fork greeting you?

### [NEW-IDEA] §1 Bet/Moat — "invest in systems that make it hard to make things bad" as harness meta-principle
Modisett's velocity/quality frame ("invest in velocity AND systems that make it hard to make things bad") maps directly to what Verso's harness should be: a system that makes it structurally difficult to ship bad agent behavior. The eval corpus, the HITL seam, the inspect() viewer — these are systems that make certain classes of agent failures *hard to produce accidentally*. This is a cleaner articulation of harness-as-quality-infrastructure than "eval framework."
**Verdict:** candidate framing for §1 bet articulation — the harness is "a system that makes it structurally hard to make bad agents."

---

## Summary Verdict
Partial read (NN/g companion article is substantive; full video transcript unavailable). Four high-quality findings: prompting-as-anti-pattern validates Verso's context-engineering layer; scope-narrowing validates positioning discipline; mental-model-first maps to API surface design principle; "hard to make bad" is a cleaner moat framing. The Henry Modisett corpus across NN/g, LukeW, Medium, Config 2024 is consistent — these are his actual positions, not summary artifacts.
