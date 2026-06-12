# Lessons from building Vercel v0 and the d0 agent

**Speaker:** Malte Ubl (CTO, Vercel)
**Format:** Talk at The Pragmatic Summit 2026 (34 min) + related blog posts and podcast appearances
**Video:** https://www.youtube.com/watch?v=_f2WpsmW76Y
**Status:** READ PARTIAL — no full transcript of the Pragmatic Summit talk found (locked behind Pragmatic Engineer paid subscription); reconstructed from: Antoine Buteau's talk notes (antoinebuteau.com/lessons-from-malte-ubl/), Vercel blog posts ("What we learned building agents at Vercel," "The no-nonsense approach to AI agent development"), Latent Space Ship AI recap (latent.space), BigGo Finance recap of "The New Application Layer" AI Engineer talk, and Mark Norgren Pragmatic Summit 2026 notes (403 forbidden on fetch). Existing how-they-did-it.md also captures the v0 composite pipeline numbers independently.

---

## What the speaker actually argues

### 1. Composite model architecture over proprietary training

The single most repeated lesson from v0: **do not train your own foundation models if you want to iterate fast**. The value in v0 came from a composite pipeline layered on top of a frontier model, not from replacing the frontier model.

> "Don't train your own foundation models if you want to iterate fast; use a composite model architecture to stay flexible as the field evolves."

The composite pipeline is the product. Base Sonnet 4 achieves 64.71% error-free code generation. The composite pipeline achieves 93.87%. **+29 percentage points came from engineering, not from a better base model.** This is the empirical proof that the harness — context engineering, model routing, streaming post-processing, AutoFixer — is where the competitive edge lives, not the model weights.

Pipeline layers:
1. **Context layer:** System prompt + RAG (docs, hand-curated code examples, uploaded sources) + AI intent detection injecting current API versions
2. **Model routing:** Frontier model for new generation; quick-edit model for small changes
3. **LLM Suspense (streaming post-processing):** Fixes imports, URLs, formatting during streaming — icon validation via vector DB of all lucide-react icon names (<100ms latency); AST-based structural fixes
4. **AutoFixer model:** Reinforcement fine-tuning + speculative decoding (8,130 chars/sec = 10–40x faster than GPT-4o-mini), 86.14% error-free standalone

### 2. d0: coding-agent architecture generalizes beyond coding

d0 was Vercel's internal data intelligence agent:

> "We built d0 to democratize data; it uses basic Unix commands like grep and cat to navigate our data warehouse and answer questions in Slack."

The key lesson: **"coding agent architectures work surprisingly well for non-coding tasks."** The same patterns — tool use, exploration loop, natural language interface to structured data — that power v0 also power d0 without domain-specific rewrites. Unix primitives (grep, cat, awk) were the tools; the warehouse was the filesystem.

### 3. Eval-driven development is the forcing function

Vercel's iteration methodology uses LLMs to automate grading, paralleling Google's search result evaluation:

> "Eval-driven development: LLMs automate grading processes similar to unit tests — this accelerates feedback cycles for AI application refinement."

Without evals, you can't know whether a prompt change is an improvement or a regression across the full distribution of inputs. Vercel moved from intuition-based iteration to structured evaluations, treating evals as the test suite.

### 4. Agents excel at "low cognitive load, high repetition" tasks

Vercel identifies the highest-probability success zone: **work that requires low cognitive load and high repetition from humans.** Not too dynamic for traditional automation, not so complex that AI reliability breaks down.

Discovery methodology: ask employees "What part of your job do you hate doing the most?" Then shadow top performers to understand workflows.

Two production examples:
- **Lead Processing Agent:** Reduced lead triage team from 10 to 1 person. Workflow: research → qualification (using `generateObject`) → email composition → human review via Slack → approval.
- **Anti-abuse Agent:** 59% reduction in ticket-closing time on first iteration. Workflow: URL intake → visual/textual analysis → recommendation → human review → resolution.

Both maintained **human-in-the-loop validation** for edge cases requiring complex reasoning.

### 5. Infrastructure must separate harness from execution environment

A critical architectural security insight: most agent frameworks execute generated code *within the same environment as the harness itself*. This is a security and stability liability.

> "Separate the agent harness from the execution environment" — sandboxed code execution is non-negotiable for production.

This motivated the `just-bash` tool: a TypeScript bash interpreter (grep, sed, awk, "99th-percentile features") with nanosecond startup times, overlay filesystem for secure file injection, and inescapable root directory sandboxing. The codebase was "essentially entirely written by Opus 4.5."

### 6. "Humans are now in the minority" — infrastructure pivot to API-first

Over a 7-day window, **60% of Vercel's page views were generated by AI agents**, not humans. This changes the product design mandate: prioritize CLI/API interfaces over dashboards. Agents don't click buttons.

### 7. Four enterprise agent archetypes

Ubl frames practical value delivery as four patterns:
1. **24/7 Workforce** — continuous operations replacing human shifts
2. **Compressed Research** — automate Event → Research → Decision; reduce 30-minute tasks to 5 minutes
3. **Information Surfacers** — synthesize trapped organizational data (Slack threads, transcripts) into actionable insights
4. **Toil Eliminators** — internal support agent achieved 90% deflection rate

### 8. Deterministic scaffolding over LLM reliance

From the "no-nonsense" methodology post:

> "If you can write a normal function to handle a step, do it." "Use plain code for parsing, calculating, or sorting."

The standard loop: **Gather input → deterministic computation → call model when judgment is needed → evaluate result → continue or exit.** LLMs are called only when reasoning is required. Reserve model calls for judgment; handle everything else in plain code.

### 9. Application layer, not model labs, creates sustainable value

Malte's strategic thesis for AI engineering:
- As foundation models commoditize, value migrates to the application layer
- The field can be led from outside model labs
- "Agents enable creation of previously economically unfeasible software due to manual development costs"
- "We are entering an era of software that can make decisions"

AI SDK functions as a model abstraction layer: "It's like JDBC for the nineties" — enabling minimal disruption when switching underlying models.

---

## VERSO RELEVANCE

**[CONFIRMS §5.2 context]** The 29pp quality gain from composite pipeline engineering vs. base model directly confirms VERSO's premise that the harness/context layer — not model weights — is where competitive advantage lives. The v0 pipeline layers (intent detection, RAG, routing, streaming post-processing, AutoFixer) are a concrete implementation of context engineering delivering measurable quality lift. No-overkill verdict: this is the empirical proof point VERSO should cite.

**[CONFIRMS §5.5 evals]** Eval-driven development as the iteration methodology (LLM-graded test suite, daily regression detection) directly confirms §5.5. The "unit test for AI output" framing matches `define_outcome(bounded)` and judge-panel patterns. No-overkill verdict: confirms, no delta.

**[SHARPENS §5.3 tools / §6.1 durable]** The `just-bash` pattern — wrapping Unix primitives as sandboxed tools with nanosecond startup — sharpens VERSO's tool design. Tools must be narrow, deterministic, and isolated from the harness environment. The "separate harness from execution environment" principle is a security invariant VERSO should encode. The d0 case shows this generalizes: same tool primitives, different domain. No-overkill verdict: encode harness/execution separation as a first-class concern in §6.3 safety.

**[SHARPENS §4 seam]** The WDK "durable execution" pattern — making TypeScript functions pause/resume without cost — is the closest external analog to VERSO's tactical↔durable seam. Vercel arrived at it from infrastructure; VERSO arrives at it from the agent loop. The framing "pause, resume, wait indefinitely without cost" is the same seam at the infrastructure layer. No-overkill verdict: useful positioning language for §4.

**[CONFIRMS §12 positioning]** "Don't train your own foundation models" + "composite model architecture" directly confirms VERSO's §6.4 model strategy (cross-model failover, role-tiered models). The abstraction layer framing ("JDBC for the nineties") is quotable for positioning. No-overkill verdict: confirms.

**[NEW-IDEA §6.3 safety]** "60% of page views are from AI agents" → product design must pivot to API-first. For VERSO, this is a non-goal clarification: the framework itself must be CLI/API-first, not optimized for human dashboards. Agents consume agents. No-overkill verdict: worth a sentence in §2 non-goals.
