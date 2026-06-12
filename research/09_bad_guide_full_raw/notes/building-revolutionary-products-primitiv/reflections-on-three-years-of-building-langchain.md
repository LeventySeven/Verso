# Reflections on Three Years of Building LangChain

**Source:** https://www.langchain.com/blog/three-years-langchain
**Author:** Harrison Chase (CEO/Founder, LangChain)
**Date:** ~Early 2026 (timed with $125M / $1.25B valuation announcement)
**Format:** Essay (~15 min)
**Themes:** loop_harness, evals, context, strategy

---

## Full Digest

Harrison Chase recounts the arc of LangChain from a personal 800-line side project in Fall 2022 through the $125M funding round at $1.25B valuation. The article is unusually candid for a founder announcement post — it is simultaneously a retrospective on what went wrong with the original `langchain` and an explanation of the architectural decisions in LangChain 1.0. Read for Verso's purposes as a diagnostic of the failure modes Verso must avoid.

### The Origin: Speed over Control

`langchain` started by pattern-matching on what early builders were doing with LLMs: more integrations, higher-level templates, 5-line RAG setups. Quote: "A lot of langchain in the early days was experimenting with prompting techniques, and we were figuring things out alongside everyone else."

**Model neutrality** was articulated as a core principle from day one: "Especially in a dynamic industry, helping users pick a model and later change that decision was incredibly important." This validates Verso's §6.4 model/provider abstraction.

### The Company Thesis

"LLMs are this great, transformational new technology. They are even more powerful when connected to external data and APIs. We call these systems agents. And it turns out building _reliable_ agents is quite hard! When there is so much promise, but it's difficult to realize the vision, there's a massive opportunity to help."

This is Verso's exact founding thesis stated by the competitor. Key: Chase acknowledges the problem clearly but the LangChain solution became LangGraph (a graph) and LangSmith (a platform). Verso's answer is different: a clean loop + eval harness without forcing the graph.

### The LangChain Failure Mode: Ease vs. Control Tradeoff

The most valuable section for Verso. Chase is explicit about the original sin:

> "While langchain was the fastest place to get started, we traded power for ease of use. The same high level interfaces in langchain that made it easy to get started were now getting in the way when people tried to customize them to go to production."

This produced three specific complaints:
1. **Hidden prompts** — users couldn't see what was being sent to the model
2. **Hidden context engineering** — the context lifecycle was not transparent
3. **Package bloat and dependency conflicts** — monolithic design leaked everywhere

The response was **LangGraph** with two pillars:
1. "Controllability: no hidden prompts, no hidden context engineering. You had full control over your system."
2. "Runtime: streaming, statefulness, human-in-the-loop, durable execution."

### The LangGraph Answer and Its Own Failure Mode

LangGraph solved the production reliability problem but introduced a new one: **high learning curve**. Chase acknowledges this explicitly: "while we were seeing tremendous adoption of LangGraph, it did have a higher learning curve."

This is the gap Verso occupies: LangGraph imposes a graph structure that requires learning a non-Python DSL to get production runtime features (streaming, durable execution, human-in-the-loop). Verso's invariant — "no graph required for tactical agents" — is the direct answer to this acknowledged limitation.

### LangChain 1.0: What They Actually Built

The reimagined `langchain` 1.0 targets three goals:
1. Easy to get started building agents
2. More customization than before
3. Production-ready runtime

Accomplished by:
1. "Focusing on the core tool-calling loop that is now synonymous with 'agents'."
2. "Adding in a new concept of **middleware**, which is uniquely designed to give developers control over the 'context engineering' lifecycle exactly where they need it."
3. "Building upon LangGraph, a runtime that supported streaming, durable execution, human-in-the-loop, and more."

**CRITICAL:** The word "middleware" is their term for what Verso calls the harness around the loop. Chase frames context engineering as a lifecycle with hooks — but buried in a "middleware" concept that still sits on top of LangGraph's graph runtime. Verso's insight: the lifecycle/harness layer should be THE primary abstraction, not a middleware shim on top of a graph.

### LangSmith as the Commercial Bet

LangSmith was explicitly decoupled from `langchain` from the start — "completely separate from langchain." Quote: "a tool like LangSmith was much needed, so we committed to building LangSmith to be best-in-class, regardless of the framework (or lack of framework) that a developer used."

The current evolution: LangSmith becomes "the comprehensive agent engineering platform" — absorbing deployments (LangGraph Platform), observability, evals, and "other product lines in the future." Each product "independent of the existing ones but well integrated into the platform."

This reveals LangChain's commercial model: **give away the loop, monetize the platform**. The framework is a top-of-funnel for LangSmith SaaS. Verso's counterposition: the eval/observability harness is embedded in the framework itself and is first-class rather than a separate product requiring a separate login.

### Validation of Verso's Core Bets

Chase explicitly names the primitives that matter for production agents:
- Streaming
- Statefulness
- Human-in-the-loop
- Durable execution
- Observability and evals

All of these are in Verso's PRD. What's different is WHERE they live: LangChain puts them in a separate commercial platform (LangSmith) and a graph runtime (LangGraph). Verso puts them in the framework harness directly.

---

## Verbatim Quotes (Load-Bearing)

1. "While langchain was the fastest place to get started, we traded power for ease of use. The same high level interfaces in langchain that made it easy to get started were now getting in the way when people tried to customize them to go to production."

2. "Controllability: no hidden prompts, no hidden context engineering. You had full control over your system."

3. "Adding in a new concept of middleware, which is uniquely designed to give developers control over the 'context engineering' lifecycle exactly where they need it."

4. "LLMs are this great, transformational new technology... And it turns out building reliable agents is quite hard!"

5. "Model neutrality still remains one of the main benefits of our products."

6. "While we were seeing tremendous adoption of LangGraph, it did have a higher learning curve."

7. "LangSmith was our answer to this problem – observability and evals for LLM systems... We made LangSmith completely separate from langchain... neutral to the LLM and neutral to the underlying framework."

8. "We started the company in February 2023 knowing that langchain was just the first tool we would build."

---

## VERSO RELEVANCE

### Finding 1: LangChain explicitly names "context engineering lifecycle" as the unsolved problem — and their answer is "middleware"
**Tag:** [SHARPENS §5.2 context-engineering]

Chase uses the phrase "context engineering lifecycle" and introduces "middleware" as the mechanism for controlling it in LangChain 1.0. This is the same problem Verso's §5.2 addresses — but Verso's insight is that middleware implies a layer ON TOP of something, whereas context engineering should be the FIRST-CLASS abstraction in the loop itself. The fact that LangChain named the problem but reached for "middleware" as the answer confirms Verso's counterposition: context engineering as native loop discipline (ContextBundle, inspect(), prefix discipline) is architecturally cleaner than middleware hooks.

**Verdict:** sharpen — use LangChain's "middleware" framing as the foil in §5.2. Verso's ContextBundle is not middleware; it is the loop's primary input discipline.

---

### Finding 2: LangGraph solves reliability but imposes graph DSL — the acknowledged learning-curve gap Verso fills
**Tag:** [CONFIRMS §2 non-goals / SHARPENS §4 architecture]

Chase explicitly says LangGraph had "a higher learning curve" and that `langchain` 1.0 was built partly to address this. But 1.0 still builds on LangGraph's runtime underneath. This means the graph requirement never goes away for anyone wanting production features. Verso's "no graph required" invariant is directly validated as filling the acknowledged gap. This is not mere differentiation — it is solving the problem LangChain identified but didn't fully solve.

**Verdict:** sharpen — cite in §2 non-goals and §4 architecture that the graph DSL is an externally-acknowledged friction point, not just a Verso aesthetic preference.

---

### Finding 3: LangChain's commercial model is "give away loop, monetize platform (LangSmith)" — Verso's counter is embedded harness
**Tag:** [CONTRADICTS §12 positioning / NEW-IDEA §5.5 evals]

LangChain's GTM: framework is top-of-funnel, LangSmith is the commercial product (observability, evals, deployments). This creates a structural problem: the eval and observability experience is decoupled from the agent code. Developers must instrument separately, log separately, analyze separately. Verso's embedded eval harness (judge-panel, define_outcome, loop hooks) means evals are co-located with the agent code — no separate product, no separate login. This is a genuine architectural counterposition, not just a feature difference.

**Verdict:** adopt-now — explicitly frame in §12 and §5.5 that Verso's evals are embedded, not bolted-on. "First-class in-process" vs. "external platform" is the positioning claim.

---

### Finding 4: LangChain's original sin — hidden context — is the problem Verso's ContextBundle and inspect() directly solve
**Tag:** [CONFIRMS §5.2 context-engineering]

Chase identifies "hidden prompts" and "hidden context engineering" as the two complaints that drove LangGraph's creation. Verso's ContextBundle with inspect() makes context explicitly visible and auditable without requiring a graph. This is a direct architectural answer to the same complaint, solved at the loop level rather than requiring a new runtime paradigm.

**Verdict:** confirm — already captured structurally. Add to §5.2 documentation: "ContextBundle.inspect() makes the context lifecycle visible without requiring a graph or external observability platform."
