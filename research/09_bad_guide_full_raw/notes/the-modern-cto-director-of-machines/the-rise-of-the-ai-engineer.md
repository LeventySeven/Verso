# The Rise of the AI Engineer

**Source:** https://www.latent.space/p/ai-engineer  
**Author:** Shawn "swyx" Wang  
**Published:** June 2023 (Latent Space)  
**Status:** read_partial — the essay's main arguments and key statistics were confirmed via multiple independent sources (gitnation transcript, scrimba podcast transcript, AI Engineer Foundation about page, swyx.io). The exact original essay body could not be extracted verbatim due to Substack's paywall for full content, but all quantitative claims and structural arguments below are confirmed from ≥2 independent sources including swyx's own spoken elaborations.  
**Themes:** strategy · model · loop_harness

---

## Faithful Digest

### The Naming Act

Swyx did not invent the role — he documented a trend already visible in hiring data. As he explained in the Scrimba transcript: "I wasn't trying to coin a new phrase...I was already seeing that people are hiring for these roles." The essay gave the trend a name and a theoretical grounding, which is why Karpathy retweeted it with endorsement, and why it went viral.

### The Supply-Demand Argument

The core quantitative claim: approximately **~5,000 LLM researchers in the world** (some sources cite 50,000 ML engineers) versus **~50 million software engineers globally**. This creates a structural tension: the people who can train frontier models are orders of magnitude rarer than the people who can consume their APIs.

The essay's exact quote (confirmed via gitnation and search): "~5000 LLM researchers in the world, but ~50m software engineers."

Consequence: foundation model labs rationally concentrate their rare talent on training; a much larger population of engineers builds on top via APIs. The essay predicted that AI Engineer job postings would invert from "10x as many ML Engineer jobs as AI Engineer jobs on Indeed" to more AI Engineer jobs within five years. By 2025 this appears to be tracking correctly — the AI Engineer Foundation (ai.engineer) reports 1.2 million unique viewers and the title is "one of the fastest-growing job titles in tech."

### The Speed/Cost Argument

Exact quote confirmed: tasks requiring "5 years and a research team" in 2013 now "just require API docs and a spare afternoon in 2023."

The 3-stage progression to "1000x" (from scrimba transcript): "Most people start off as AI enhanced engineers...Then they progress towards AI products engineers...And then finally you have the AI agents." He says this compounds to potentially "1,000x" productivity gains through delegation to agents. This is not a clean mathematical claim — it is a directional order-of-magnitude argument.

### The Software 3.0 Argument

Swyx builds explicitly on Karpathy's Software 2.0: "What is incrementally new is the concept of software 3.0, where instead of running machine learning for a single domain, you are running machine learning across all the domains and creating foundation models." The essay traces: Software 1.0 (explicit code) → 2.0 (neural nets, weights as program) → 3.0 ("the hottest new programming language is English").

Critically, swyx argues this is *not* the end of traditional software engineering. The 2023 theme he identified: "One of the biggest themes of 2023 has very much been about re-establishing the role of human-written code to orchestrate and supplant LLM power, from the >$200m behemoth LangChain, to Nvidia-backed Voyager showing the unmistakable importance of code generation and reuse." Software 3.0 does not eat 1.0 and 2.0 — it *orchestrates* them.

### The AI Engineer vs. ML Engineer Division

The cleanest dividing line: **are you training models or consuming APIs?**

- ML Engineers: train and serve models
- AI Engineers: consume APIs and deliver solutions to end users

The "API wall" formulation (scrimba): "The API wall is a pretty clear line, where either you have an in-house ML team serving you an API, or you have a third party foundation model lab serving you an API. It doesn't really matter once you get that API what you do with it."

### What Defines a Field (Not Just a Tool)

Swyx's most philosophically interesting point: "I'm not defined as an engineer by I use Stripe." A genuine engineering discipline requires: (1) a shared set of problems, (2) a coherent tool stack, (3) community with money flowing. For AI engineers, the coherent stack in 2023 was: chain-of-thought prompting, vector databases, fine-tuning open source models, LangChain vs. LlamaIndex. The point: an engineer who uses one AI API is not an AI engineer; an engineer who has internalized the *shared problem set* of building AI products is.

### The High Salaries Signal

Essay quote: "Making $300k/yr doing prompt engineering at Anthropic and $900k building software at OpenAI." Swyx uses these numbers not to celebrate them but as a demand-side signal: talent markets are pricing AI-adjacent engineering at extreme premiums because supply is so constrained.

### Conference Announcement

The essay announced the first AI Engineer Summit (ai.engineer). This became the AI Engineer Foundation, which by 2025 had run 10+ events, 15,000+ in-person attendees, and 10 million+ talk views. The conference was both a GTM move (brand the category you named) and a community-building move (create the shared community that constitutes a real discipline).

### "AI engineering is 90% traditional software engineering"

Swyx repeatedly emphasizes that the AI Engineer role does not replace fundamentals — it extends them. "AI engineering is 90% traditional software engineering." The key differentiator is picking a domain, going deep on one subfield, and learning in public.

---

## VERSO RELEVANCE

### Finding 1: The supply-demand argument is a staffing call, not a how-to — and Verso's GTM lives exactly at the seam
**Tag:** [SHARPENS §12]  
The essay is explicitly a *staffing-and-leverage* argument: companies have 50M software engineers and 5,000 LLM researchers; the rational move is to direct the 50M toward AI products via APIs. This is the market that Verso serves: the 50 million software engineers who need a framework that behaves like Python, not like a research artifact. Verso's Python-native, @tool decorator, no-graph positioning is a direct bet that this population (who knows Python but not PyTorch) is the primary market. The staffing argument sharpens the GTM: Verso is positioned for the software engineer becoming an AI engineer, not for the ML researcher building custom pipelines.  
**Verdict:** sharpen §12 — explicitly position Verso for the "AI Engineer" persona (software engineer who consumes APIs), not for the ML researcher.

### Finding 2: "Re-establishing human-written code" in 2023 is still under-captured in 2025
**Tag:** [CONFIRMS §5.1, §5.3]  
Swyx's most important 2023 observation: the trend was toward more human-written code, not less — code that orchestrates LLMs rather than being replaced by them. This is Verso's core design bet: the @tool decorator is Python code, the loop is Python code, the agent is invoked from Python. The human stays in the loop structurally (the code is the agent definition). This confirms the design but also SHARPENS it: Verso should lean into the "code as the program" framing — the Python agent definition IS the software, not a configuration for some underlying framework.  
**Verdict:** confirm + sharpen — in §5.1 and §5.3, frame the Python code as the first-class program, not scaffolding around a model.

### Finding 3: The "1000x" claim is agents-as-compounding-delegation, not a single-step improvement
**Tag:** [SHARPENS §6.2]  
The "1000x" productivity claim is NOT about a single agent being 1000x faster. It is about a *compounding progression*: AI-enhanced engineer → AI-product engineer → AI-agents engineer, where each stage delegates to agents which themselves delegate. Verso's multi-agent architecture (§6.2) should explicitly model this compounding delegation: a human-driven agent that spawns focused sub-agents, which can themselves invoke tools — the 3-level delegation stack. The value is not one fast agent; it is the ability to safely compose delegation chains.  
**Verdict:** sharpen §6.2 — multi-agent architecture should be presented as delegation-compounding, not just parallelism.

### Finding 4: A framework is not defined by one tool — it needs a coherent shared problem stack
**Tag:** [SHARPENS §12]  
Swyx's discipline-formation argument: a field is not defined by one tool (using Stripe doesn't make you a payments engineer) but by a shared problem set. For Verso to be "the framework" for AI engineers, it needs to own a coherent problem stack — not just the loop, but context engineering + evals + durable execution as one coherent answer to the AI engineer's recurring problems. The "no overkill" positioning must still be comprehensive enough to address the shared problem set. A framework that solves only part of the stack is a library, not a discipline tool.  
**Verdict:** sharpen §12 — Verso's positioning must claim a coherent problem stack (context + evals + durable), not just "simpler loop"; the breadth is the moat.

### Finding 5: The "API wall" framing argues against MCP as default
**Tag:** [CONFIRMS §5.3]  
"The API wall is a pretty clear line." Once you have an API, it doesn't matter whether it's in-house or third-party. For tools: once you have a Python function decorated with @tool, it doesn't matter whether the underlying implementation uses an MCP server or direct code. Verso's @tool-first design is exactly right — the API wall for tools is the @tool decorator; MCP is just one way to be on the other side of that wall.  
**Verdict:** confirm — @tool-first is the correct "API wall" for tools; MCP is a provider-side implementation detail.

### Finding 6: "Learning in public" and community are how the AI Engineer field was built
**Tag:** [NEW-IDEA §12]  
Swyx built the AI Engineer category by naming it, running a conference, and learning in public. This is the same playbook Verso should consider: write about context engineering and evals publicly; define what those mean for Python agents; create the vocabulary before competitors do. The conference was both a GTM and a community-building move. For Verso, the analogous move might be: publish the context engineering and eval primitives with clear vocabulary, and own those terms the way swyx owned "AI Engineer."  
**Verdict:** adopt-now (for GTM/positioning) — publish the vocabulary of context engineering and evals before competitors; own the terms.

---

## One-line Verdicts Summary

| Finding | Verdict |
|---|---|
| Verso is for the 50M software engineers, not 5K researchers | sharpen §12 |
| Human-written code orchestrates LLMs; Python code IS the agent | confirm + sharpen §5.1/§5.3 |
| 1000x = compounding delegation stack, not single-agent speed | sharpen §6.2 |
| Framework needs coherent shared problem stack, not just simpler loop | sharpen §12 |
| @tool decorator is the correct "API wall" for tools | confirm §5.3 |
| Publish vocabulary (context engineering, evals) to own the category | adopt-now §12 |
