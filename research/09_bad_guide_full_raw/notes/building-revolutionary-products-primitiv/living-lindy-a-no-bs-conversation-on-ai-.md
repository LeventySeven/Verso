# Living Lindy: a No-BS Conversation on AI Agents

**Speaker:** Flo Crivello (CEO, Lindy AI) — interviewed by Nathan Labenz on The Cognitive Revolution
**Format:** Podcast · 1h26m
**URL:** https://www.youtube.com/watch?v=rRwNn-TL5eI
**Transcript sources:** (1) Full episode page at cognitiverevolution.ai — substantive transcript extracted; (2) Chroma interview at trychroma.com/interviews/flo-on-lindy — deep technical content extracted; (3) E2B blog interview at e2b.dev/blog/about-building-tools-for-llm-agent-with-flo-crivello-ceo-at-lindy-ai
**Status:** READ FULL — no single clean transcript of the Cognitive Revolution episode, but cognitiverevolution.ai page yielded full argument structure, all major claims and multiple direct quotes; supplemented by two other Crivello interviews covering the same technical ground with additional depth

---

## What the speaker actually argues

### 1. Task ambiguity, not task length, is the right complexity metric

The standard framing ("can the agent do a long task?") is wrong. The right question is: **how ambiguous is the task?**

> "Anything you would feel comfortable giving to an intern with a Google Doc that describes a succession of steps."

Low-ambiguity workflows can be described as sequences of steps. The metric that matters: "the maximum complexity of any of these steps." A task composed of twenty two-minute steps is tractable; a task with one step requiring open-ended judgment is not. This reframe covers a much broader set of work tasks, since a surprising amount of work is a succession of short, low-ambiguity steps.

### 2. Few-shot gold examples from human corrections beat instructions and fine-tuning

> "Big time. Absolutely. Much better than instructions."

From the Chroma interview, the mechanism: users review agent outputs before execution in safe mode; their corrections are embedded in a vector database and retrieved by semantic similarity, then injected into context as few-shot examples.

> "you take that signal, you embed it in the vector database...retrieve the closest examples, and you inject them in context"

> "It doesn't take a lot of examples...after five examples" performance improves substantially.

Result: "this approach proved by far, the most effective method across everything — forget about prompting, basically, just do this."

The bottleneck is not the technique — it is that humans resist creating examples: they are "fragmented across context" or "the chain of thought was always in their heads." The solution: make corrections happen organically through HITL, then harvest them.

This is what Crivello calls **"poor man's RLHF"** or "in-context reinforcement learning from human feedback."

### 3. Tools must not be agentic — the sharp line

> "You should draw a sharp line between your agents and your tools, and your tools should not be agentic."

> "Empirically, it just doesn't work well...It's hard enough to make one agent work. Now you need to make two agents work."

Example: Lindy's "search web" action is literally a Google search — not an agentic tool with decision-making. The tool is dumb. The agent is smart. Composing two agents as a "tool call" multiplies reliability problems.

### 4. Lindy v1 was too open-ended — they backtracked to deterministic scaffolding

Lindy v1 overestimated LLM capabilities with pure open-ended agents. They backtracked to add deterministic scaffolding.

Current approach: users control how tight the guardrails are. Deterministic steps for critical paths:

> "You're not asking the LLM, you're not asking the LLM god, go ahead and check this knowledge base. You want that to happen deterministically all the time."

**Temperature zero for all LLM calls.** Crivello confirmed: "running at temperature zero...it doesn't tend to be the LLM" for failures; "most of the time" engineering changes cause issues. Advantage: easier to debug and reproduce bugs.

### 5. Model is for judgment; scaffolding is deterministic

The architectural principle: **use deterministic scaffolding for known-good steps; call the model only when judgment is genuinely required.**

From the Chroma interview: "The prompt is not just an intention. The prompt is a functional component in your architecture." A naive pass-through of the user's initial intention to the LLM rarely works: "what are the odds that the way you phrased your intention, happens to be exactly the right set of tokens that the LLM need in order to do this job? That's actually pretty low."

The solution: build a compilation layer between user intention and execution — examples, retrieval, cognitive scaffolding.

### 6. RAG is "limping" — hybrid handcrafted + vector search

> "RAG is...not dead, but it's limping."

Current practice at Lindy:
1. Hand-curated knowledge branches for predictable queries (e.g., five pages on billing)
2. Direct context insertion when token budgets allow
3. Vector search as fallback for edge cases

> "It basically becomes this hybrid between a handcrafted pipeline, a handcrafted RAG pipeline, and a BM25, vector similarity search."

The key move: don't rely on vector search for anything you can predict. Hardcode the predictable paths; reserve retrieval for the long tail.

### 7. Multi-agent systems are still immature

> "Multi-agent systems...are still being defined and does not work nearly as reliably" as single-agent + tools.

MCP progress is needed but early. The recommendation: stay single-agent + dumb tools as long as possible. Delegate to sub-agents only for genuine parallelism or isolation needs.

Example of a working multi-agent pattern: meeting note-taker Lindy delegates to Chief of Staff Lindy with a natural language message — but this works because the inter-agent communication is structured and the sub-agent's task is well-specified.

### 8. Performance optimization hierarchy

1. Few-shot examples from human corrections (highest impact)
2. Clear instructions (secondary)
3. Model selection and token budgeting
4. Fine-tuning only for narrow, high-volume, critical tasks at scale

Fine-tuning: "a bit of a thing of the past" for most use cases. The value proposition is too low. Fine-tuning on a 40B+ parameter model with 8k+ context window is "very painful."

### 9. Model selection: labels not pinned versions

> "You should be...model maxing. You should talk to all models."

Use model labels so "Lindys that are using the default model use the new default model" automatically. Don't pin versions — changing defaults affects all dependent agents, so the abstraction layer matters.

Current defaults (at time of recording): Claude 3.5 Sonnet as default/balanced, Gemini 2.5 Flash for speed, o3 for "smartest."

### 10. Reliability comes from architecture, not model upgrades

> "reliability be 10X better" — same model, different cognitive architecture.

Approach: continuous architectural iteration rather than waiting for next-generation models. "We're not running out of ideas. We have a huge roadmap, and we know what to do next."

The "Sycophantocalypse" lesson: GPT-4o's swift policy changes showed dangers of rapid model swaps. Mitigation: fast detection + faster rollback protocols. Model agnosticism is not just a nice-to-have — it is a reliability requirement.

### 11. Safety: per-action confirmation, not blanket safe mode

> "you can check my email, but you cannot send emails in that safe mode."

Uncertainty detection via semantic similarity: if the current situation has no close historical examples in the vector database, the agent should surface for confirmation: "this is a scenario, it's the first time I see it...I'm out of my depth on this one."

### 12. The "build time vs. runtime" distinction

Lindy distinguishes between agent creation (build time) and agent execution (runtime). People conflate these. The prompt is a functional component of the runtime architecture, not just an instruction. This distinction drives the compilation-layer design.

### 13. Evaluation framework

Custom testing framework:
- Mock APIs and expected API call parameters
- Simulated end-user responses via LLM
- Observation of interaction failures
- Daily evals tracking performance changes: "we run daily evals and we're like, Hey, this call dipped, like X percentage since yesterday."
- Timeout protection: "You failed" outcome after token limits

---

## VERSO RELEVANCE

**[CONFIRMS §5.3 tools]** "Tools must not be agentic" is a direct, empirically-grounded confirmation of VERSO's native Python @tool design. If sub-agents are treated as tool calls, you multiply reliability problems. VERSO's position (MCP demoted, native @tool is THE path, sub-agents as quarantine not as first-class tool) is exactly the right call. Verbatim: "It's hard enough to make one agent work. Now you need to make two agents work." No-overkill verdict: this is a production operator with 2+ years of data confirming §5.3.

**[SHARPENS §5.5 evals / §5.2 context]** "Poor man's RLHF" — embed human corrections as few-shot examples retrieved by semantic similarity — is a specific, high-value addition to VERSO's evals story. VERSO already has `define_outcome(bounded)` and judge-panel, but this mechanism (HITL corrections → vector DB → in-context few-shot) is a concrete path to *improving* agent quality over time without fine-tuning. Maps to §5.5 (evals) and §5.2 (context — just-in-time retrieval of gold examples). No-overkill verdict: add this as a concrete pattern in §5.5.

**[SHARPENS §5.1 loop]** Task ambiguity (not task length) as the tractability metric is a sharper framing than anything in the VERSO PRD for explaining when an agent will succeed. The "intern with a Google Doc" heuristic is usable as a one-liner in §5.1 or §1 bet section to explain the design space. No-overkill verdict: borrow this framing for the scope/tractability boundary.

**[CONFIRMS §6.1 durable — HITL]** Per-action confirmation (not blanket safe mode) + uncertainty detection (no close examples → surface for confirmation) maps directly to VERSO's durable layer HITL design. The Lindy pattern shows the mechanism: semantic similarity against example history drives the confirmation threshold. This is "just-in-time HITL" — exactly the right granularity. No-overkill verdict: confirms §6.1 HITL design, adds the semantic-similarity-driven trigger as a refinement.

**[SHARPENS §6.4 model]** Model labels not pinned versions + "model maxing" (talk to all models) + fast detection/rollback on model behavior regression confirms and sharpens VERSO's cross-model failover / role-tiered model design. The "Sycophantocalypse" lesson adds a specific failure mode to design for: model policy changes can silently break agent behavior. VERSO needs fast rollback at the model layer. No-overkill verdict: add "fast rollback on model behavior regression" as an explicit concern in §6.4.

**[CONTRADICTS partial — §6.2 multi-agent]** Crivello's strong skepticism about multi-agent reliability ("still being defined, does not work nearly as reliably") partially contradicts VERSO's first-class multi-agent design (§6.2). However, this is about *current reliability of protocols*, not about the architectural value. His specific concern (MCP maturity, compounding errors) is addressed by VERSO's sub-agents-as-failure-quarantine + scheduler-offload framing. No-overkill verdict: not a true contradiction — confirms the need to keep single-agent + dumb tools as the default, reserve multi-agent for explicit parallelism/quarantine cases.

**[CONFIRMS §5.2 context — RAG]** "Hybrid handcrafted + vector search" confirms VERSO's RRF k=60 + asymmetric embeddings + just-in-time retrieval design. The key addition: hardcode predictable paths (hand-curated branches), use retrieval only for the long tail. This is context engineering with tiers. No-overkill verdict: confirms §5.2, adds the "tiered RAG" pattern as a concrete design principle.
