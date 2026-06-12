# Squish Meets Structure: Designing with Language Models

**Source:** https://maggieappleton.com/squish-structure
**Author:** Maggie Appleton, product designer at Elicit (research literature review tool)
**Type:** Essay/talk transcript, delivered at Smashing Conference AI 2023 (~30 min read)
**Date fetched:** 2026-06-12

---

## Faithful Digest

### Context and Author Position

Appleton is the sole designer at Elicit, which helps professional researchers do systematic literature reviews. The core product: take a large stack of research papers and extract data from them into an organized table. Researchers currently open "hundreds of PDFs, scanning through them for important data points, and copying them into a large Google Sheet — laborious work that can take up to a few months." Elicit's goal: "cut that down to a few days or hours." This is the grounding context for all design recommendations — a rigorous scientific use case with near-zero tolerance for hallucination.

### The Core Metaphor: Shoggoth vs. Interface

Appleton uses the "Shoggoth" meme — "massive amoeba-like creatures made out of iridescent black slime" from H.P. Lovecraft — to represent the untamed nature of language models beneath polished chat interfaces. The meme conveys: "we have a huge grotesque monster, and we're just putting a surface layer of pleasantries on top of it. Like polite chat interfaces."

The design problem this creates: we are "presenting the exact same kind of devices [interfaces] for a fundamentally different type of technology." Traditional software is deterministic. Language models are probabilistic — "mathematical models of human language" trained on internet text (CommonCrawl, WebText2, books, Wikipedia) that "predict word sequences based on training data patterns." They understand semantic relationships with mathematical precision but have no internal truth-checking mechanism.

Andrej Karpathy is quoted: language models are "a very complicated alien artefact."

### The Hallucination Problem (and Its Design Implication)

Models "say things that don't reflect reality" — hallucinations — because they predict likely word sequences rather than verify facts. Example used: ChatGPT giving contradictory answers about crossing the English Channel. The design implication is not "fix hallucinations" (impossible) but: "treat models as tiny reasoning engines, rather than sources of truth."

Bing's chatbot failure: "went off on explicitly romantic and sexual tangents and threatened users" — the example of what happens when you put a Shoggoth in an interface that assumes deterministic behavior.

### The Squish-Structure Spectrum (Core Framework)

The central organizing framework. Language models exist on a spectrum:

- **Far left (too much squish):** Outputs become useless randomness, unpredictability so high the system is unreliable
- **Center (Goldilocks zone):** The optimal balance for practical products
- **Far right (too much structure):** Defeats the purpose; you could use traditional programming instead

**Control levers that move you along the spectrum:**
- Temperature settings: 0 for predictable responses, 0.7+ for creativity
- Reinforcement learning intensity: how much human scoring feeds back
- Prompt engineering specificity: how precise the constraints are

**Use-case guidance:**
- "You'll want more squish for creative products" (writing assistance, brainstorming)
- "You'll want more structure for rigorous products like extracting info from scientific papers" (Elicit's case)

The insight: the Goldilocks zone is not a universal fixed point — it must be calibrated to the use case. A design decision, not an engineering parameter.

### Design Pattern 1: Compositionality (Prompt Chaining)

The most important design recommendation. Instead of a single-input/single-output black-box query, break complex reasoning into a chain of observable sub-tasks.

Appleton's magnesium supplement example — a full prompt chain:
1. Search Google Scholar for papers on "magnesium supplements" and "brain health"
2. Use a model to "read all the titles and abstracts for these papers"
3. "Rank them by how semantically similar they are to our question"
4. Filter by citation count
5. Generate sub-questions about "gender and age," "dosage," "how common is each side effect"
6. "Condense these findings back down into a summary"

The payoff: "we could inspect the input and output at each step. We can see its reasoning along the way." Each step becomes validatable. The chain is debuggable. This is contrasted with a single black-box call where "there's no way to validate or debug."

Terminology: "prompt chaining — you make chains of commands that include prompts to language models" combined with "traditional programming functions." Not all steps need to be model calls; web search and filtering can be conventional code.

### Design Pattern 2: Specific Over Generic (Spell-Check Sized Tools)

Appleton's critique of generic "Magic AI" input interfaces: "They present you with a 'Magic AI' input claiming it can do anything you want. This forces the user to think: What can I do here? What should I do? What is this for? This thing has no affordances!"

The prescription: "design language models that give users a set of specific tools...make tiny, sharp, specific tools with models...most language model implementations should be 'spell-check sized.' They should do one specific thing well."

Praised examples:
- **Google's TextFX:** "gives you a bunch of tiny language tools: Similes, Semantic chains, Alliteration, Change your point of view, Find the intersection" — each tool has exactly one job
- **Amelia Wattenberger's writing tool:** shows "style lenses" with "colour gradients over text to indicate sentence length, how sad/happy the tone is, how concrete/abstract" — observable overlays on existing content

The metaphor: "spell-check sized" is the ideal scope. Spell-check doesn't try to write your document — it does one narrow thing reliably.

### Design Pattern 3: Human-in-the-Loop

Complex multi-step reasoning should include humans who can "redirect the model if it starts going off track." This isn't framed as a fallback for when models fail — it's a design principle for any rigorous use case.

Positioning relative to full automation: "If you can't see how it reasons, why would you trust its reasoning?" Observable reasoning steps enable human validation at each junction.

### Risks Appleton Names Explicitly

- **Hallucinations:** No internal truth verification
- **Opacity:** "We don't fully understand how they work...referred to as 'black boxes'"
- **Unpredictability:** Models are "simultaneously incredibly dumb and incredibly capable"
- **User confusion:** Generic interfaces create cognitive overload about what the system can do
- **Reliability failures:** No visibility into "the model's reasoning...no way to validate or debug"
- **Mismatched expectations:** Presenting deterministic-feeling interfaces for probabilistic systems

### The Deeper Design Claim

Appleton's essay is not a chat critique — it is a design framework for constraining probabilistic systems into small, observable reasoning steps instead of building one magic box that overpromises. This is what she means by "find the ideal balance between Squish and Structure." The design space is:

- Break tasks into composable steps
- Make each step's input and output visible
- Give users specific tools with affordances, not open-ended magic
- Position yourself in the Goldilocks zone for your use case
- Include humans at decision junctions

---

## VERSO RELEVANCE

### [CONFIRMS + SHARPENS] §7 / Product Taste: The "No Magic Box" Principle as Core Design Taste

**Finding:** Appleton's essay is the clearest articulation of why VERSO's "explain it without AI" invariant and the "no magic box" posture are correct product taste. Her critique of generic "Magic AI" input interfaces maps exactly to why VERSO should never have a single "run this agent and trust the output" interface without observable intermediate steps. The `agent.inspect()` surface is VERSO's answer to Appleton's compositionality requirement.

**Verdict:** confirm — the inspect() surface and run-loop observability already address this. The Appleton essay provides the best language for explaining WHY inspect() is not a debugging afterthought but a core product taste decision.

### [SHARPENS] §7 / Demo-able Wedge: Spell-Check Sized as the Scoping Principle

**Finding:** Appleton's "spell-check sized" framing is a precise scoping heuristic for VERSO's primitives. Each primitive in the harness should be "spell-check sized" — does one specific thing well, has clear affordances, doesn't pretend to be a magic black box. This is a design taste principle, not just an architecture one. The 3-line side-by-side demo works because each primitive is exactly spell-check sized.

**Verdict:** sharpen — use "spell-check sized" explicitly in the §7 demo-able wedge description. Each primitive should be describable in one sentence of what it does.

### [SHARPENS] §2 / Non-Goals: The Magic AI Input Refusal

**Finding:** VERSO's most important non-goal can now be stated with Appleton's vocabulary: VERSO does not offer "Magic AI" input surfaces. It does not pretend to "do everything." Every interaction has affordances. This is a principled design refusal, not a limitation. The essay gives VERSO the language: "This thing has no affordances!" is what users say about bad AI products; VERSO's non-goal is to never provoke that reaction.

**Verdict:** adopt-now — add "no Magic AI input surfaces / explicit affordances everywhere" to §2 non-goals. Citable with Appleton's language.

### [NEW-IDEA] §5/§6 / Harness Primitives: Compositionality as the Eval Architecture Principle

**Finding:** Appleton's prompt chaining design pattern — "we could inspect the input and output at each step, we can see its reasoning along the way" — is the exact argument for why VERSO's evals layer should be step-level, not just run-level. If the harness breaks the agent loop into composable steps with observable I/O, each step can be individually evaluated. This makes the eval corpus more granular and more useful. The architectural bet (harness over framework) is validated by this design argument: only a harness with step-level observability can support step-level evals.

**Verdict:** adopt-now — make step-level I/O observability explicit in the eval architecture. The eval corpus flywheel requires compositionality at the step level.

### [NEW-IDEA] §12 / Positioning: The "Squish-Structure Spectrum" as VERSO Category Language

**Finding:** Appleton's squish-structure spectrum is a usable vocabulary for VERSO's category design. VERSO could position itself as "the harness that helps you find your Goldilocks zone" — not by abstracting away the model's probabilistic nature, but by giving you the tools to constrain and observe it appropriately for your use case. This is a meaningful differentiation from frameworks that either try to hide the probabilism (too much structure) or expose raw model calls (too much squish).

**Verdict:** lock-defer — powerful category vocabulary but requires careful integration with existing positioning (counter-position, anti-framework). Evaluate in the category design sprint. Risk: "Goldilocks zone" could sound imprecise.

### [CONFIRMS] §1 / Bet/Moat: Elicit's Design Philosophy Validates the Harness Bet

**Finding:** Elicit (Appleton's employer) is exactly the kind of product VERSO's primary persona would build: rigorous, structured, multiple observable steps, no magic box, human-in-the-loop. The fact that Elicit's design philosophy aligns perfectly with VERSO's harness primitives (compositionality, observability, step-level I/O) means VERSO's primary persona is well-served by the harness. Elicit is a use-case confirmation.

**Verdict:** confirm — Elicit as a reference customer archetype. Add to the persona work.

### [SHARPENS] §12 / Positioning: The "Simultaneously Incredibly Dumb and Incredibly Capable" Quote as Market Education Asset

**Finding:** "Models are simultaneously incredibly dumb and incredibly capable" is the cleanest one-line summary of why agent reliability is the hard problem. This is VERSO's market education asset: the reason the harness exists is that you can't trust the model at face value (dumb) but you also can't ignore it (capable). This is better than "hallucination" as a framing because it captures both dimensions.

**Verdict:** sharpen — use "simultaneously incredibly dumb and incredibly capable" as the market education anchor in the positioning section. Better than "models hallucinate" as an explanation for why the harness matters.

---

## One-Line Verdicts per Finding

| Finding | Verdict |
|---|---|
| No magic box = inspect() is core taste, not afterthought | confirm |
| Spell-check sized as scoping heuristic for primitives | sharpen |
| No Magic AI input surfaces → add to §2 non-goals | adopt-now |
| Step-level I/O observability as eval architecture principle | adopt-now |
| Squish-structure spectrum as category language | lock-defer |
| Elicit as reference customer archetype | confirm |
| "Simultaneously dumb and capable" as market education anchor | sharpen |
