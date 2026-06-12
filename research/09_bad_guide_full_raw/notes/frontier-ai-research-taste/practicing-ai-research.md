# Practicing AI Research

**Author:** Jason Wei (OpenAI; author of Chain-of-Thought prompting paper)
**URL:** https://www.jasonwei.net/blog/practicing-ai-research
**Status:** read_full — WebFetch returned comprehensive content across two fetches; all four skills sections, meta-level guidance, and recommendations confirmed.

---

## Faithful Digest

Wei frames research as a learnable skill decomposed into four competencies, comparable to sports or music. The essay is practical and opinionated. Its core contribution relative to Schulman's guide is the execution layer: Schulman covers problem selection and goal-setting; Wei covers experiment design, writing, and (critically) impact maximization as distinct learnable skills.

### The Frame

*"Research is a learnable skill, decomposed into four core competencies."* Not talent, not luck — four discrete, improvable skills. Wei's thesis is that most researchers implicitly treat research as a single thing, but training each skill separately produces faster improvement.

### Skill 1: Idea Conception and Selection

Wei's taste criterion: favor research that is *"simple, general, and stands the test of time"* — avoid *"complicated, task-specific, or short-lived"* work. This directly echoes Schulman's goal-driven framing but gives a tighter criterion: simple + general + durable.

Two strategies: (a) dominate hot topics through superior execution, or (b) pioneer emerging areas before they become hot. Both require taste. Critically: *"spending more time on idea selection"* provides substantial returns — narrow topics with limited potential cannot achieve major impact regardless of execution quality. This is a direct statement that idea-selection skill has the highest leverage of the four.

**Recognizing sunk costs**: Wei abandoned medical imaging work to pursue NLP when progress stalled. *"Sunk cost fallacy kills research careers."* Knowing when to abandon a direction is itself a learnable skill.

### Skill 2: Designing and Executing Experiments

Experimental design benefits from colleague review to catch gaps. Wei values rapid execution due to time's opportunity costs ("time has opportunity costs; slow execution forecloses options") but warns: *"it's important to develop a reputation for doing rigorous and comprehensive experiments."*

The tension: speed vs. rigor. Wei's resolution: fast iteration on the *design* phase (colleague review catches gaps early), then rigorous execution. Don't be fast-and-sloppy; be fast-at-design, rigorous-at-execution.

Building credibility: *"brilliant ideas fail through poor implementation."* Credibility is a career asset that compounds — papers with well-run experiments get cited; sloppy ones get dismissed.

### Skill 3: Writing the Paper

Framing results within broader field context matters more than the results themselves. Wei conducts explicit meetings with authors and non-authors to test presentation strategy before writing. The key questions: Can non-experts follow the motivation? Is the abstract self-contained? Do the figures stand alone?

Practical mechanics:
- Prioritize abstract and introduction (most people read only these)
- Create standalone figures (figures are the paper's summary for skimmers)
- Use simple language; avoid jargon; many readers are non-native English speakers
- Provide sufficient background for non-specialists

### Skill 4: Maximizing Impact (the most underrated skill)

Wei calls this *"the most underrated skill"*. It involves: Twitter/X promotion, conference talks, follow-up papers, videos, blog posts, code and data open-sourcing. Personal branding via website and technical blog.

The Hamming quote Wei invokes: *"at least 50% of the time must go for the presentation."* (Richard Hamming) — i.e., the effort to communicate results is not less important than the effort to produce them.

Code/data release: *"facilitates others building on published work"* — the multiplier on impact from open-sourcing is not incremental but exponential (others cite, extend, and apply your work).

Personal branding: Wei advocates websites and technical blogs as durable signals of taste and communication skill. "It is a portfolio of your thinking, not just your papers."

### Meta-Level Guidance

**Collaborators as skill accelerators**: Working with exceptional researchers forces higher standards across all four skills. *"Strong collaborators accelerate skill development and force higher research standards."*

**Study admired researchers**: Understand *why* specific people succeeded. Reverse-engineer their taste, their execution patterns, their communication choices.

**Balancing input vs. output metrics**: Input metrics (hours worked, papers read) must be balanced with output metrics (citations, reproductions, follow-up work). Optimizing only for inputs is a trap; optimizing only for outputs encourages shortcuts.

**Additional reading**: Wei recommends Hamming, John Schulman, Michael Nielsen, and Andrej Karpathy as complementary perspectives.

---

## Key Verbatim Quotes

1. *"simple, general, and stand the test of time"* — Wei's taste criterion for research
2. *"spending more time on idea selection"* provides substantial returns
3. *"it's important to develop a reputation for doing rigorous and comprehensive experiments"*
4. *"brilliant ideas fail through poor implementation"* (paraphrase from Wei's framing)
5. *"at least 50% of the time must go for the presentation"* — Hamming, quoted by Wei
6. *"the most underrated skill"* — Wei on impact maximization
7. *"Strong collaborators accelerate skill development and force higher research standards"*

---

## VERSO RELEVANCE

This essay's relevance to Verso is primarily in how Verso should think about its own research and communication practices, and secondarily in what it reveals about the target Verso user's workflow.

### Finding 1: "Simple, general, stands the test of time" is the exact filter for Verso's primitive design
[SHARPENS §2 non-goals / §5.1 loop]
Wei's taste criterion for research ideas maps directly onto Verso's design filter for primitives. Every primitive in Verso should be tested against: Is it simple? Is it general (not tied to one model, one task type, one use case)? Will it stand the test of time (not a workaround for current model limitations)? The loop itself passes (10-20 lines, model-agnostic, ReAct). The `{data, error, ok}` dispatch passes. The question is which *proposed* primitives fail this test. **This is a sharper formulation of "every primitive must earn its place"** — earn it by being simple + general + durable, not just by being useful today. Verdict: **sharpen §2 non-goals** — use Wei's three-part criterion as the explicit design filter.

### Finding 2: "50% on presentation" (Hamming) = Verso's docs/DX are not secondary to the code
[SHARPENS §12 positioning/GTM]
Wei's invocation of Hamming's "50% on presentation" is a direct challenge to the common engineer instinct to build first, document later. For Verso, this means: the README, the type signatures, the error messages, and the tutorial are as load-bearing as the loop implementation. The ContextBundle.inspect() method is a presentation choice as much as an engineering choice. **DX is research communication applied to frameworks** — Verso's adoption depends on it. Verdict: **sharpen §12** — DX and documentation should receive explicit resourcing equal to the core loop, not be treated as polish.

### Finding 3: Code open-sourcing as exponential impact multiplier = Verso's open-source strategy
[CONFIRMS §12 positioning/GTM]
Wei's observation that code/data release facilitates others building on your work — producing exponential rather than linear impact — confirms that Verso's open-source strategy is correct positioning. A closed Verso is a product; an open Verso is a standard. The citation analogy is apt: the first framework to get cited (imported, depended on, extended) as the "boring durable core" wins the category. Verdict: **confirm §12** — open source is not just a distribution choice; it is the impact multiplier mechanism.

### Finding 4: Sunk cost recognition = Verso's relationship to graph-based approaches
[SHARPENS §2 non-goals]
Wei's explicit point about abandoning medical imaging for NLP when progress stalled — recognizing sunk costs — maps to how Verso frames its counter-positioning on graphs. The graph-based agent frameworks (LangGraph et al.) represent a large sunk cost in the community: years of development, tutorials, integrations. Verso's counter-positioning is the sunk-cost recognition argument: those approaches are wrong, not just complex, and the community should abandon them for the simple loop. **This is a hard sell precisely because sunk costs are psychologically powerful.** Verso's GTM needs to provide cover for developers to make the switch — a migration path, not just a critique. Verdict: **sharpen §12** — GTM should include a sunk-cost recognition frame (help devs justify the switch internally).

### Finding 5: The four-skill decomposition maps onto Verso's four-layer architecture
[NEW-IDEA §4 the seam/architecture]
Wei's four skills (idea selection, experiment design, writing, impact) decompose research into distinct learnable layers. Verso decomposes the agent problem similarly: loop (idea), context engineering (experiment design), evals (writing/measurement), durable runtime (impact/persistence). The parallel suggests that each Verso layer has distinct skill requirements and should be designed to be teachable independently — a developer can learn context engineering without first mastering the durable runtime. **This suggests Verso's documentation should be structured as four independent skill tracks**, not a single linear tutorial. Verdict: **new-idea §12** — document Verso as four learnable skills, not one monolithic framework.

---

## One-line Verdicts per Finding
- Simple + general + durable = the explicit design filter for Verso primitives: **sharpen §2**
- 50% on presentation = DX/docs are as load-bearing as the loop: **sharpen §12**
- Code open-sourcing as exponential multiplier = open-source strategy confirmed: **confirm §12**
- Sunk-cost recognition needed for Verso GTM vs. graph-framework adopters: **sharpen §12**
- Four-skill decomposition → four independent learnable tracks in Verso docs: **new-idea §12**
