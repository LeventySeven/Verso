# The Shift from Models to Compound AI Systems

**Source:** https://bair.berkeley.edu/blog/2024/02/18/compound-ai-systems/  
**Authors:** Matei Zaharia, Omar Khattab, Lingjiao Chen, Jared Quincy Davis, Heather Miller, Chris Potts, James Zou, Michael Carbin, Jonathan Frankle, Naveen Rao, Ali Ghodsi (Databricks / Berkeley)  
**Date:** February 18, 2024  
**Status:** READ FULL — complete text retrieved via WebFetch

---

## Full Digest

The central claim: "state-of-the-art AI results are increasingly obtained by compound systems with multiple components, not just monolithic models." The authors define a Compound AI System as "a system that tackles AI tasks using multiple interacting components, including multiple calls to models, retrievers, or external tools." The contrast is with "an AI Model [as] simply a statistical model, e.g., a Transformer that predicts the next token in text."

### Evidence for the Shift

- **AlphaCode 2**: generates up to 1 million solutions, filters via code execution + clustering — reaches 85th percentile of humans on coding contests
- **AlphaGeometry**: LLM + symbolic math engine, alternating construction suggestion and deductive verification — between silver and gold IMO medalists
- **Medprompt**: GPT-4 + nearest-neighbor search in correct-example database + LLM-generated CoT + multiple samples + ensembling — outperforms specialized medical models
- **Gemini CoT@32**: 32 chain-of-thought samples, top choice if enough agree, fallback otherwise — 90.04% MMLU vs. 86.4% for GPT-4 5-shot
- **Databricks survey data**: 60% of enterprise LLM applications use RAG; 30% use multi-step chains
- **Microsoft Medprompt**: chaining strategy exceeded GPT-4 accuracy on medical exams by 9%

### Four Reasons Why Compound Systems Win

1. **Some tasks are easier to improve via system design.** "Suppose that the current best LLM can solve coding contest problems 30% of the time, and tripling its training budget would increase this to 35%; this is still not reliable enough to win a coding contest! In contrast, engineering a system that samples from the model multiple times, tests each sample, etc. might increase performance to 80% with today's models." Key phrase: "iterating on a system design is often much faster than waiting for training runs."

2. **Systems can be dynamic.** Models are trained on static datasets — their knowledge is fixed. Retrieval, search, and data serving components inject timely information. Access controls are also only enforceable at the system level, not the model level.

3. **Improving control and trust is easier with systems.** "Neural network models alone are hard to control: while training will influence them, it is nearly impossible to guarantee that a model will avoid certain behaviors. Using an AI system instead of a model can help developers control behavior more tightly, e.g., by filtering model outputs." Hallucination mitigation via citation + automatic fact verification.

4. **Performance goals vary widely.** Fixed-quality, fixed-cost model vs. applications needing variable parameters. GitHub Copilot uses "carefully tuned smaller models and various search heuristics" because GPT-4 is too expensive for inline suggestions. Conversely, users would pay more for a correct legal opinion than GPT-4's marginal cost — but you need a system to utilize that larger budget.

### Key Challenges Identified

**Design space:** For even simple RAG, the authors enumerate: (i) choice of retrieval and language model; (ii) query expansion, reranking; (iii) output verification. "Developers have to explore this vast space to find a good design." Plus resource allocation: "if you want to answer RAG questions in 100 milliseconds, should you budget to spend 20 ms on the retriever and 80 on the LLM, or the other way around?"

**Optimization:** Single models are differentiable; compound systems contain "non-differentiable components like search engines or code interpreters." DSPy is cited as the first framework attempting end-to-end optimization of LLM pipelines to maximize a target metric — users write natural language signatures (e.g., `user_question -> search_query`), DSPy automatically constructs prompts with instructions, few-shot examples, or even weight updates.

**Operation / LLMOps:** "While it is easy to track success rates for a traditional ML model like a spam classifier, how should developers track and debug the performance of an LLM agent for the same task, which might use a variable number of 'reflection' steps or external API calls?" Key MLOps problems: monitoring traces from complex systems; DataOps (data pipeline quality affects system behavior); security (compound systems create unforeseen security risks).

### Emerging Paradigms Cataloged

- **Composition frameworks:** LangChain, LlamaIndex (component libraries); AutoGPT, BabyAGI (LLM-driven control); Guardrails, Outlines, LMQL, SGLang (output control)
- **Inference strategies:** chain-of-thought, self-consistency, WikiChat, RAG
- **DSPy:** end-to-end pipeline optimization via natural language signatures
- **FrugalGPT and AI gateways:** route inputs to different model cascades, "outperform the best LLM services by up to 4% at the same cost, or reduce cost by up to 90% while matching their quality"
- **LLMOps:** LangSmith, Phoenix Traces, Databricks Inference Tables for trace monitoring

### Closing Argument

"We believe that compound AI systems will remain the best way to maximize the quality and reliability of AI applications going forward." The authors explicitly reject the "just wait for better models" view: even with continued model scaling, system-level engineering will remain the primary lever for production-grade reliability.

---

## VERSO RELEVANCE

### Finding 1: "Iterating on system design is much faster than waiting for training runs" — the core product velocity argument [CONFIRMS §1 / §12]

The authors' framing that system design iteration beats model scaling for practical reliability directly validates Verso's bet on the harness over the model. The compound system IS the product; the model is one component. "A good LLM creates a compelling but frustratingly unreliable first demo, and engineering teams then go on to systematically raise quality." This is precisely the Verso workflow: the harness (context engineering, evals, durable execution) is where reliability is built. **Verdict: confirm §1 — this is exact validation of the "harness is the product" core thesis.** confirm

### Finding 2: DSPy's `user_question -> search_query` signature model as a possible Verso interface tension [SHARPENS §5.3 / §5.2]

DSPy represents an alternative architecture where the "tool" interface is a typed signature optimized by the framework, not a Python function decorated by the developer. DSPy's approach is powerful for pipeline optimization but it abstracts away Python — you write a declarative signature, not a function. Verso's hard invariant is that native Python `@tool` is THE tool path. DSPy shows there is real demand for auto-optimization of tool invocations; Verso's response should be that `@tool` functions can be composed, wrapped, and selected by the evals layer without forcing a declarative DSL. The tension is real: DSPy's optimization story (end-to-end, metric-driven) is compelling; Verso needs a credible answer for pipeline-level optimization that doesn't sacrifice native Python. **Verdict: sharpen §5.3 — articulate how Verso's eval-driven approach (define_outcome + judge panel) substitutes for DSPy-style auto-optimization without leaving Python.** sharpen

### Finding 3: Non-differentiable components require new optimization methods — this IS the evals problem [SHARPENS §5.5]

"Compound AI systems contain non-differentiable components like search engines or code interpreters, and thus require new methods of optimization." This is a precise technical framing of why evals are non-negotiable in Verso's design: gradient descent doesn't work on agent loops, so the only optimization signal is outcome measurement. The eval layer is the backward pass for compound systems. The "new methods of optimization" the authors gesture at — DSPy, LaMDA tool-training, AlphaGeometry — are all in essence eval-driven loops: define a metric, generate outputs, score them, update components. Verso's define_outcome + judge-panel is directly in this category. **Verdict: sharpen §5.5 — add language that evals are the gradient for non-differentiable systems, not just a quality gate.** sharpen

### Finding 4: Access control only enforceable at system level [SHARPENS §6.3]

"More complex systems are needed to build AI applications with access controls (e.g., answer a user's questions based only on files the user has access to)." Model training cannot encode access control — it's a runtime concern. This directly validates the safety/hooks layer (§6.3) as a first-class system concern, not a downstream add-on. Verso's RunContext injection pattern (typed context at loop entry) is exactly the right architectural choice: access tokens, user permissions, and security boundaries belong in the typed context, not in the prompt text. **Verdict: sharpen §6.3 — make explicit that RunContext is the access-control enforcement point.** sharpen

### Finding 5: FrugalGPT / routing — a direct argument for role-tiered models in Verso [CONFIRMS §6.4]

FrugalGPT "can outperform the best LLM services by up to 4% at the same cost, or reduce cost by up to 90% while matching their quality" via cascade routing. The already-known role-tiered model architecture (cheap loop / mid retry / reasoning synthesis) is exactly a specialized instance of FrugalGPT's routing idea, but baked in at the framework level rather than as a middleware layer. The BAIR essay confirms this as a real and significant capability pattern in production systems. **Verdict: confirm §6.4 — role-tiered models are now field-validated as a production pattern, not just a theoretical idea.** confirm

### Finding 6: "Variable number of reflection steps" as observability challenge [NEW-IDEA §6.3 / §5.5]

"How should developers track and debug the performance of an LLM agent for the same task, which might use a variable number of 'reflection' steps or external API calls?" This is a precise description of the observability gap in current frameworks. Verso's append-only event log (loop harness) is the right infrastructure response: every step is an event, every tool call is a traced span, so the number of steps is not a surprise — it's a queryable fact. The implication for evals: traces should be first-class inputs to the eval system, not just final outputs. Verso should allow eval judges to evaluate not just answer quality but reasoning trace quality (did the agent use the right tools in the right order?). **Verdict: new idea — add trace-level eval to §5.5 as an explicit capability.** lock-interface-defer

### Finding 7: Security in compound systems [SHARPENS §6.3]

"Research has shown that compound AI systems, such as an LLM chatbot with a content filter, can create unforeseen security risks compared to individual models." The paper cites arXiv:2309.05610 (prompt injection / jailbreak research). The hooks layer in Verso (§6.3) must be designed with the understanding that each tool call is a potential attack surface. Pre-call and post-call hooks are not optional — they are the primary mechanism for enforcing security boundaries in a compound system. **Verdict: sharpen §6.3 — hooks are a security mechanism first, an observability mechanism second.** sharpen

---

## Summary Verdict

The BAIR essay is the field-defining compound systems manifesto. It directly validates Verso's core thesis (harness > model), identifies DSPy as the most serious alternative architecture (requiring a pointed answer in §5.3), confirms role-tiered models as production-validated, and sharpens the case for evals as non-differentiable-system optimization and hooks as security infrastructure. The single most important new finding is the DSPy tension: if Verso doesn't have an answer to "how do I optimize my pipeline without leaving Python," DSPy is the answer a user will reach for instead.
