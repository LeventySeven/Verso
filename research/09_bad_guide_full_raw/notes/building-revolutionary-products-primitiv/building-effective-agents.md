# Building Effective Agents

**Source:** Erik Schluntz & Barry Zhang (Anthropic)  
**URL:** https://www.anthropic.com/research/building-effective-agents  
**Fetched:** 2026-06-12  
**Status:** read_full  
**Themes:** loop_harness, context, evals, multiagent, strategy

---

## Full Digest

Anthropic's canonical practitioner essay on agent architectures, based on working with dozens of production teams. The central thesis: **simple, composable patterns outperform complex frameworks** in production. The document is both a pattern library and a design philosophy statement.

### Core Distinction: Workflows vs. Agents

> "Workflows are systems where LLMs and tools are orchestrated through predefined code paths. Agents, on the other hand, are systems where LLMs dynamically direct their own processes and tool usage, maintaining control over how they accomplish tasks."

This is not a hierarchy — both are valid for different task classes. Most production uses are workflows, not agents.

### The Anti-Framework Stance

> "Consistently, the most successful implementations weren't using complex frameworks or specialized libraries. Instead, they were building with simple, composable patterns."

> "These frameworks make it easy to get started by simplifying standard low-level tasks like calling LLMs, defining and parsing tools, and chaining calls together. However, they often create extra layers of abstraction that can obscure the underlying prompts and responses, making them harder to debug. They can also make it tempting to add complexity when a simpler setup would suffice."

> "We suggest that developers start by using LLM APIs directly: many patterns can be implemented in a few lines of code. If you do use a framework, ensure you understand the underlying code. Incorrect assumptions about what's under the hood are a common source of customer error."

### The Five Workflow Patterns

**1. Prompt chaining:** Sequential LLM calls where each processes the output of the previous. Use for tasks cleanly decomposable into fixed subtasks. Trade latency for accuracy. Canonical example: write outline → gate → write document.

**2. Routing:** Classify input → dispatch to specialized downstream process. Enables separation of concerns. Canonical example: route easy questions to Haiku, hard questions to Sonnet 4.5.

**3. Parallelization:** Two sub-variants:
- *Sectioning:* Independent subtasks run in parallel (e.g., separate guardrail model from response model)
- *Voting:* Same task run multiple times for diverse outputs (e.g., code vulnerability scanning with multiple prompt perspectives)

**4. Orchestrator-workers:** A central LLM dynamically breaks down tasks and delegates to worker LLMs. Key difference from parallelization: subtasks are not pre-defined, they emerge from the input. Use when you cannot predict the required subtasks in advance. Canonical example: complex multi-file code changes.

**5. Evaluator-optimizer:** One LLM generates, another evaluates and provides feedback in a loop. Conditions for fit: (1) responses demonstrably improve when a human articulates feedback, and (2) the LLM can provide equivalent feedback.

> "This is analogous to the iterative writing process a human writer might go through when producing a polished document."

### When Agents (Not Workflows) Are Appropriate

> "Agents can be used for open-ended problems where it's difficult or impossible to predict the required number of steps, and where you can't hardcode a fixed path."

Key constraint: "you must have some level of trust in its decision-making." And: "The autonomous nature of agents means higher costs, and the potential for compounding errors. We recommend extensive testing in sandboxed environments, along with the appropriate guardrails."

Stopping conditions are a first-class concern: "it's also common to include stopping conditions (such as a maximum number of iterations) to maintain control."

### Tool Design as First-Class Engineering

> "For a coding agent... we actually spent more time optimizing our tools than the overall prompt."

Principles:
- Give the model enough tokens to "think" before it writes itself into a corner
- Keep the format close to what the model has seen naturally (internet-native formats)
- Eliminate formatting overhead (no requiring accurate line counts, no string-escaping code in JSON)
- Poka-yoke: change arguments to make mistakes harder (e.g., require absolute filepaths, not relative)

> "One rule of thumb is to think about how much effort goes into human-computer interfaces (HCI), and plan to invest just as much effort in creating good agent-computer interfaces (ACI)."

The ACI concept is explicit and named: the tool definition is a UI for the model. Docstrings, parameter names, example usage, edge cases, boundary conditions — all must be engineered as carefully as the system prompt.

### Three Core Principles (from Summary)

1. Maintain **simplicity** in your agent's design
2. Prioritize **transparency** by explicitly showing the agent's planning steps  
3. Carefully craft your **agent-computer interface (ACI)** through thorough tool documentation and testing

### Grounding From Environment

> "During execution, it's crucial for the agents to gain 'ground truth' from the environment at each step (such as tool call results or code execution) to assess its progress."

This is the ReAct grounding loop: every action must produce an observation the agent actually reads before the next step.

---

## VERSO RELEVANCE

### Finding 1: The ACI concept is a named, missing primitive in Verso's §5.3
[NEW-IDEA §5.3]

The essay introduces **Agent-Computer Interface (ACI)** as a first-class concept analogous to HCI. Verso's §5.3 describes tools in terms of registration (@tool decorator, type safety, MCP adapter) but not in terms of the quality of the tool's "UI" for the model. The ACI framing suggests Verso should provide:
- A tool docstring/description linting convention (similar to a mypy pass but for model-readability)
- Examples embedded in tool descriptions as a first-class field, not just kwargs
- Poka-yoke patterns: absolute paths by default, constrained enum parameters rather than open strings

This is a concrete feature gap: Verso tools are well-typed but may not be well-ACI'd.

**Verdict:** adopt-now — add ACI as named concept in §5.3; add a "tool documentation quality" checklist or lint pass.

### Finding 2: The evaluator-optimizer workflow maps exactly to Verso's eval loop
[CONFIRMS §5.5]

The evaluator-optimizer pattern — "one LLM call generates a response while another provides evaluation and feedback in a loop" — is structurally identical to Verso's judge-panel eval architecture. The two fit conditions match Verso's design philosophy: (1) LLM responses demonstrably improve with feedback, (2) LLMs can provide structured feedback. This is direct confirmation that the §5.5 evaluator architecture is solving a real, recognized pattern, not an invented one.

New nuance: the essay notes "when iterative refinement provides measurable value" as the gate condition. This maps to Verso's `define_outcome(bounded)` — the outcome must be bounded and measurable to justify the loop. Unbounded eval loops are anti-patterns.

**Verdict:** confirm §5.5 — add the "measurable improvement gate" as an explicit condition in the eval loop design.

### Finding 3: Routing as a first-class workflow pattern — maps to Verso's model-tiering
[CONFIRMS §6.4]

> "Routing easy/common questions to smaller, cost-efficient models like Claude Haiku 4.5 and hard/unusual questions to more capable models like Claude Sonnet 4.5 to optimize for best performance."

This is the role-tiered model pattern (cheap loop / mid retry / reasoning synthesis) already in Verso's known harvest, but now confirmed as the canonical Anthropic recommendation, not just a community pattern. The key addition: routing is not purely a performance optimization — it's a **separation-of-concerns workflow pattern**. The routing decision itself is a tool call or prompt chain that benefits from clear criteria.

**Verdict:** confirm §6.4 — the routing pattern validates model tiering as a workflow primitive, not just a cost optimization.

### Finding 4: Anti-framework stance is a direct validation of Verso's positioning
[CONFIRMS §1 and §12]

> "We suggest that developers start by using LLM APIs directly: many patterns can be implemented in a few lines of code. If you do use a framework, ensure you understand the underlying code. Incorrect assumptions about what's under the hood are a common source of customer error."

This is Anthropic's own practitioner team saying frameworks obscure and cause errors. Verso's "no overkill, no bullshit, you can read the loop" positioning has ground-truth backing from the people who build Claude agents for production. This is more than a confirm — it is *the* authoritative citation for Verso's anti-abstraction bet.

The essay also names the Claude Agent SDK as a framework. This means Verso is competing with (or positioning against) Anthropic's own SDK, which the Anthropic essay itself critiques when misused.

**Verdict:** adopt-now for §12 — quote the anti-framework passage in GTM/positioning materials as third-party (Anthropic) validation.

### Finding 5: Orchestrator-workers is where the graph pressure comes from
[SHARPENS §4 and §6.2]

The orchestrator-workers pattern — central LLM dynamically delegates to workers, subtasks emerge from input — is the exact use case that forces teams toward graph frameworks. The essay says it's appropriate "when you can't predict the subtasks needed." Verso's counter-position ("we don't force the graph") needs to account for this case: Verso needs to show that dynamic delegation can be implemented cleanly **without** a graph DSL, using plain async Python coroutines. This is a gap in Verso's documented patterns — the tactical agent handles the simple loop, but the orchestrator-workers pattern needs a code example showing it doesn't require LangGraph.

**Verdict:** sharpen §6.2 — add a concrete orchestrator-workers example implemented in plain Verso (no graph), demonstrating that the loop handles dynamic delegation natively.

### Finding 6: Stopping conditions as first-class infrastructure
[SHARPENS §5.1]

> "it's also common to include stopping conditions (such as a maximum number of iterations) to maintain control."

The loop file must expose stopping conditions as a first-class parameter, not as a user-implemented workaround. If stopping conditions require user-added code, Verso loses the "you can trust the defaults" claim. This should be a named `max_turns` or `stop_if` parameter in the RunContext or loop signature.

**Verdict:** sharpen §5.1 — verify that max_turns/stop conditions are first-class in the loop, not bolted on.

---

## One-Line Verdicts Summary

| Finding | Verdict |
|---|---|
| ACI concept is missing from §5.3 tool design | adopt-now |
| Evaluator-optimizer = Verso eval loop; add measurable-improvement gate | confirm §5.5 |
| Routing validates model tiering as workflow primitive | confirm §6.4 |
| Anthropic's own anti-framework quote = GTM ammunition | adopt-now §12 |
| Orchestrator-workers needs a no-graph Verso example | sharpen §6.2 |
| Stopping conditions must be first-class loop parameters | sharpen §5.1 |
