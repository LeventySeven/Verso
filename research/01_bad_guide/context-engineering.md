# Context engineering for agents

## Context Engineering: Lessons from Scaling CoCounsel — https://www.youtube.com/watch?v=sLFv3RSj_d8 — transcribed

Speaker: Jake Heller, founder of Casetext (YC S13), acquired by Thomson Reuters 2023. Built CoCounsel — first AI assistant for lawyers — on GPT-4 before ChatGPT launched.

### Why GPT-4 was the inflection point
- GPT-3.5 scored 10th percentile on bar exam; GPT-4 scored 90th percentile on the same exam (not in training set)
- GPT-4 was the first model able to do complex legal tasks at roughly human-equivalent accuracy, plus scalable across hundreds of simultaneous tasks
- This discovery caused Casetext to pivot the entire company to CoCounsel

### Architecture methodology: "How would the world's best person do this?"
- Step 1: Define the experience/skill to deliver (CoCounsel uses "skills" — legal research, contract review, document review, etc.)
- Step 2: Ask "How would the world's best lawyer do this task with infinite time?" — this becomes your task architecture
- Example — legal research decomposed into micro-steps:
  1. Clarification step (understand angles, scope: federal vs. state case law, etc.) — "prompt one: clarify"
  2. Query formulation (generate 20–50 different search queries, varied vocabulary and angles)
  3. Execute search queries and review each result individually
  4. Relevance scoring per result (is this actually relevant? How does it help answer the question?)
  5. Note-taking pass (notes on how each case relates to the final answer)
  6. Final synthesis (compile all notes into the final answer)
- "Each micro step is either code or prompt. And increasingly in difficult tasks, those are mostly going to be prompts."
- Sometimes steps are linear/deterministic → implement as `def step_one, def step_two` in Python code; do NOT make it agentic if the flow is predictable
- Sometimes steps are agentic → "if you do a number of searches but realize you're not finding what you're looking for, go back to step one and try more searches"
- Rule: understand whether your pipeline is linear (code it deterministically) or genuinely requires agentic looping (then allow it)

### The eval-driven prompt development loop
- Write first prompt (best guess at instructions + context) — test against 10 examples
- First prompt typically passes ~6/10; most developers give up here ("AI is stupid")
- "The definition of a good prompt engineer is somebody who can write well AND is willing to not sleep for two weeks straight until they get it right."
- Iterate: find where instructions are unclear, fix instructions, adjust model/temperature settings, re-test
- Ratchet from 10 → 50 → 100 → 1,000 test cases per prompt
- 1,000 tests should NOT all be invented by you in isolation — drive test cases from actual user input via beta programs
- CoCounsel was "shocked by how dumb the legal research queries people put in" — users are the best source of edge cases
- Target: pass 999/1,000 before wider release
- "Never tell your customers it's going to be perfect; it'll be really good if you anticipated all the edge cases"

### Context quality is the hidden bottleneck
- "There are times where we couldn't believe the AI was getting the answer wrong, but when we read the context — all 10 or 100 pages — we realized: given this information, I would say the same thing the AI does."
- Critical instruction pattern: "Do not answer based on any previously existing knowledge, just based on what I'm giving you right now. If this thing says the sky is purple, the sky is damn purple." — forces grounding, eliminates hallucination from training-set drift
- Retrieval quality bottleneck: "How could you expect a human, let alone an AI, to answer accurately if the retrieval sucks?"
- OCR was a massive bottleneck for CoCounsel — legal documents are messy, OCR output was often gibberish; model occasionally got it right with garbled text but should not be relied upon
- Rule: "If it's hard for you to read, it'll be hard for the AI to read." Read the actual context verbatim (including spacing) before debugging the prompt
- Debugging protocol: before changing the prompt, read the raw context as the AI sees it — you may have an OCR problem, not a prompt problem

### Token efficiency tricks
- For classification/scoring: constrain output to one token (a number 1–10, "true"/"false"/"maybe")
- Mechanism: the model reads the entire context and all previously generated tokens for each new token — constraining to one token = one pass through, not N passes
- Clever trick: prompt the model to output a number + explanation, but use stop words or `max_tokens=1` to cut it off after the number. The model will give a "slightly better answer because it thinks it's about to give an explanation to defend its number" — then discard everything after token 1
- For structured outputs: make the model give its objective/numeric answer FIRST, then the explanation — makes evals much simpler ("matches word X" rather than LLM-as-judge)
- "LLM-as-judge is sometimes the only option, but avoid it when you can" — force structured evaluation targets

### Breaking tasks into micro-prompts
- "Give the AI a simple task and it's more likely to do it right more often" — decompose into smallest coherent steps
- Resist the temptation to have one prompt do 12 steps; break it down even if it feels over-engineered

### Reinforcement fine-tuning vs. classic fine-tuning
- Classic fine-tuning: needed thousands of examples, minimal gains, sometimes the model got dumber — "why am I generating thousands of examples just for it to perform at the same rate?"
- Reinforcement fine-tuning (RFT): requires max 50–100 examples of (prompt, good answer, objective judge) — "the hardest part is creating the objective judge, not the examples"
- RFT "goes a really long way" — CoCounsel is moving toward a different fine-tuned model for every single micro-step prompt
- "We're starting to reach a place where we have hundreds if not thousands of prompts throughout the CoCounsel ecosystem; each micro step gets its own reinforcement fine-tune model"
- Can push eval from 9,900/10,000 → 9,990/10,000

### Model routing
- No rule that every step uses the same model — "try different models for different prompts"
- Gemini 2.5 Flash: "beautiful model, cheap as [hell]. If it works, use that. Don't use 2.5 Pro."
- GPT-4o mini vs. GPT-4o: significant cost savings if mini achieves acceptable accuracy
- Use tooling (Prompt Fu free/open-source; Vellum paid) to run the same prompt across multiple models for comparison

---

## Context Engineering for Engineers — https://www.youtube.com/watch?v=3jN77Aw7Utk — transcribed

Speaker: Jeff Huber, founder of Chroma (vector/search/retrieval database).

### Framing: AI systems as programs
- "An AI system is ultimately just a program: instruction set + relevant information + tools + user input → magic box → output. It is ultimately just software."
- Context engineering = "quite simply deciding what's in the context window. That's it."
- Encompasses: the prompt, retrieval (if applicable), tools, conversation history — everything that enters the context
- "Context engineering is a much better term than prompt engineering or RAG — those are subsets. Context engineering implies the existence of context engineers and a context engine."

### Why long context does NOT solve the problem
- Chroma technical report (~120k YouTube views): tested model performance vs. input token length on simple tasks (repeating back a set of words) — performance drops precipitously; blue dot at far bottom right (worst performance) = 10,000 tokens
- "Model performance at 40% at 170k tokens across some tasks — and it may be even much sooner than that"
- Needle-in-a-haystack is a misleading benchmark: (1) only requires attending to a single needle, not the full context; (2) reasoning power is zero ("What was the best writing advice I got from my college classmate?" → "to write every week" — trivial extraction)
- Real-world tasks require either more attention span (wide coverage of context) AND/OR more reasoning — needle-in-haystack is bottom-left of both axes
- Chroma tested: full context vs. focus context (human-curated oracle) — "massive gains in performance by curating context. You SHOULD curate your context."
- Verdict: long context is not a substitute for good context engineering

### The gather-and-glean model
- Two-stage process for assembling context per turn:
  1. **Gather (maximize recall)**: get all possible relevant tokens/information, even at risk of including irrelevant material
  2. **Glean (maximize precision)**: remove irrelevant information — cut until you have only a pristine set of highly relevant, non-distracting information
- "Out of all the information in the universe, what information should be in the context window THIS turn?" — the core problem statement of context engineering

### Gathering strategies
- Query planning: LLM generates a query plan ("based on this query I'll use these tools, search in these ways") → may produce 10 or 30 different search probes
- Sources to gather from: structured data (SQL queries), unstructured data (Chroma vector search), local file system, MCP tools, web search, chat conversation history
- Fan-out approach: send probes across all sources simultaneously, collect a big pool

### Gleaning / ranking strategies (in order of sophistication)
1. Top-k vector similarity — first pass, most common
2. Reciprocal Rank Fusion (RRF) — fuses multiple ranked lists
3. Learning to Rank (LTR) — OG information retrieval technique, implemented in Elasticsearch
4. Dedicated reranking models — common
5. LLMs as rankers — "more and more developers are calling this 'cheating at search' or 'brute-forcing search' — just use more intelligence, spend more money on tokens"
   - Use small/fast/cheap models in parallel for this curation stage; don't need state-of-the-art
   - Trend: throw more parallel LLM calls at gleaning instead of sophisticated IR

### Context engineering in agents (the hard problem)
- In a deep research agent, gather-and-glean happens many times inside nested sub-agents; orchestrator judges sub-agents; sub-agents carve up the web
- Agent conversation history becomes a major factor in context window size — "prompt histories can be really, really big"
- SWE-bench example: the code and logs from a few turns of SWE-bench fill an insanely large context; no human could parse it
- Finding: giving the agent access to past **failure cases** improves agent performance — helps it break out of local minima
- Finding (counter-intuitive): giving the agent access to prior **success cases** did NOT reliably help — "the agent would slip into a local minima and just pattern match, kind of lazy: 'Oh, you gave me the answer, thank you, I'll just say that back'"
- Verdict: success case history is a double-edged sword; failure case history is reliably useful

### Compaction is critical — and current approaches are broken
- "Compaction is a really important point of leverage" — distilling the context for the next turn of the model
- "Today's approaches don't really work" — the difference between NO summary and the built-in compaction from open-code is NEGLIGIBLE; you could throw away the compaction and it's only marginally worse
- BUT: a smarter compaction with a better prompt CAN be much better
- Key insight: default compaction tools are essentially no-ops; you need to engineer your own compaction prompt carefully

---

## Advanced Context Engineering for Agents — https://www.youtube.com/watch?v=IS_y40zY-hc — transcribed

Speaker: Dex Horthy, founder of HumanLayer (YC F24). Author of "12-Factor Agents" manifesto (April 2022). Talk originally titled differently, renamed to "context engineering" on June 4th.

### Why context engineering matters for coding agents
- Stanford study on 100,000 developers: AI coding leads to a lot of rework — "even if you get benefits, you're throwing half of it away because it's sloppy sometimes"
- AI doesn't work well for complex tasks or brownfield tasks (legacy codebases) — "for complex brownfield tasks, it can be counterproductive, not even just 'doesn't help much' but can actually slow people down"
- Amjad from Replit (six months ago): "product managers use this to build prototypes, then when we figure it out, we give it to engineers and they build production"
- Context engineering = how to get the most out of today's models for complex problems

### The workflow transformation: spec-first development
- Working with "one of the best AI coders I've ever met" — receiving 20,000-line Go PRs every few days for complex systems code with race conditions, shutdown ordering
- "I couldn't review it" — forced adoption of spec-first development as the only way to stay on the same page
- Outcome: "I haven't opened a non-markdown file in an editor in almost two months"
- Shipped 6 PRs in one Thursday; intern Sam shipped 2 PRs on day 1, 10 PRs on day 8
- Demonstrated: one-shotted a fix to a 300,000-line Rust codebase (podcast episode, 75 min) — PR was so good the CTO merged it without knowing it was a test
- Sat down with Boundary CEO for 7 hours and shipped 35,000 lines of code (estimated 1–2 weeks of work at normal pace)

### LLMs are pure functions — context is the only lever
- "The only thing other than training your own models and messing with temperature that improves the quality of your outputs is the quality of what you put in — your context window"
- In a coding agent, the agent loops over: what is the right next tool to call? What is the right next edit to make? — the ONLY thing determining its ability to do this well is what is in the context window
- "Everything that makes agents good is context engineering"
- Four things to optimize for: **correctness, completeness, size, and trajectory**
  - Trajectory = where the agent is heading; important but currently "very vibes-based"
- Worst things in a context window (in order): (1) bad info, (2) missing info, (3) too much noise
- Equation: the fewer tokens you use to do the work (out of your 170k budget), the better results you get

### The naive failure modes
- Naive: shout at the agent back and forth until you run out of context, give up, or cry
- Slightly smarter: notice it's off-track, stop, restart, say "try again but don't do that thing" — still ad-hoc
- Warning sign that it's time to start over: agent going in circles (specific failure state mentioned but not shown in transcript)
- `slash/compact` (built-in): "I think slashcompact is trash. I never use it."

### Intentional compaction: the core workflow

#### What takes up space in the context window (in a coding agent)
- Looking for files
- Understanding the flow of the code
- Doing edits
- MCP tools returning big blobs of JSON — "that's going to flood your context window with a bunch of nonsense"

#### The three-phase workflow with explicit compaction
Three phases, each with its own context window, goal: keep context utilization **under 40%** at all times.

**Phase 1 — Research:**
- Understand how the system works, which files matter, where a problem is located
- Research prompt is long, open-source (linked in talk)
- Output is a research file with exact file names AND line numbers — "so the agent reading this research knows exactly where to look; it doesn't have to search 100 files"
- "A bad line of research — a misunderstanding of how the system works and how data flows — can be thousands of bad lines of code"

**Phase 2 — Planning:**
- "Tell me every single change you're going to make — not line by line, but include the files and the snippets of what you're going to change and be very explicit about how we're going to test and verify at every step"
- Planning prompt and plan format are open-source
- "A bad part of a plan can be hundreds of bad lines of code"
- The plan is always much shorter than the resulting code changes
- "If the plan is good, I'm never shouting at Claude anymore. If I'm shouting at Claude, it's because the plan was bad."

**Phase 3 — Implement:**
- Go write the code using the plan
- Implement prompt is open-source
- As implementing: constantly update the plan; mark things done → "on to the next phase, new context window"
- Target: keep context under 40% throughout implementation; compact at each phase boundary

#### Intentional compaction file format (the "progress file")
- Written out very specifically at each compaction boundary
- Used to onboard the next agent into the current state
- Contains: what was found (research), what was planned, what was implemented, what remains, file names with line numbers
- This is explicitly NOT the default `/compact` command — it's a hand-crafted prompt that produces a structured handoff document

### Sub-agents as context isolation (not role separation)
- "A lot of people saw Claude Code sub-agents and thought it was about having a product manager, data scientist, front-end engineer. It's really about context control."
- Common use: parent agent needs to find where something happens in a codebase → calls sub-agent with that specific task → sub-agent returns location without polluting parent's context
- Sub-agent returns: file names and line numbers → parent can go directly to work without carrying the search burden
- "Playing telephone" problem: what comes back from the sub-agent matters — you have to prompt the parent model to prompt the child model about HOW it should return its information
- "This is a deterministic system and it gets chaotic — imagine with nondeterministic systems"
- Sub-agent response should look like the research output: structured, specific, minimal

### Code review reframed as mental alignment
- "Code review is about mental alignment — keeping people on the team aware of how the system is changing and why as it evolves over time"
- Can't read 2,000 lines of Go every day, but can read 200 lines of an implementation plan
- Plans → early problem detection + shared understanding of code evolution
- Key structural insight: the hierarchy of leverage is research > planning > code. A bad research insight creates thousands of bad lines of code. A bad plan line creates hundreds. A bad line of code is just a bad line.

### Token spend is a positive signal
- Team of 3 in one month: large Anthropic credits usage — "I don't think we're going to switch to the max plan because it saves us a lot of time as engineers. It's worth it."
- "Spend as many tokens as possible" — explicitly a goal, not a cost concern

### Commoditization warning
- "Coding agents are going to get a little bit commoditized, but the team and the workflow transformation will be the hard part"
- "Getting your team to embrace new ways of communicating and structuring how you work is going to be really, really hard and uncomfortable"

---

## → Verso implications

### 1. Context assembly is a first-class primitive, not a utility function
- All three speakers agree: what's in the context window is THE primary lever for agent quality. Verso must expose context assembly as a named, composable component in the agent loop — not buried in `run()` internals.
- Verso's context assembly API should be explicit and observable: each turn, the framework should log/emit what was assembled, where it came from, how many tokens it used, and what was dropped.
- Design: every agent step produces a `ContextBundle(instruction: str, retrieved: list[Chunk], history: list[Message], tools: list[ToolDef], budget_used: int, budget_total: int)` that is inspectable before it hits the model.

### 2. Gather-and-glean as the canonical retrieval pattern
- Jeff Huber's two-stage model (maximize recall → maximize precision) should be the default retrieval pipeline in Verso's built-in RAG/search integration.
- Stage 1: fan-out query planning (LLM generates N search probes across structured + unstructured sources). Stage 2: glean/rerank before injecting into context.
- Verso should provide: `GatherStep(sources: list[Source], n_probes: int)` → `GleanStep(ranker: Ranker, top_k: int)` as composable primitives.
- Support ranker hierarchy: vector similarity → RRF → reranker model → LLM-as-ranker (brute-force option for high-stakes gleaning).

### 3. Context budget as a hard constraint, not a suggestion
- Dex Horthy's rule: keep context utilization under 40% at all times. This is not a soft guideline — it enables reliable compaction/handoff at phase boundaries.
- Verso should have a `context_budget` per agent step with a default ceiling (e.g., 40% of model's max context). Attempting to inject more than the budget should be a framework-level warning or blocking error, not a silent overflow.
- KV-cache implications: structuring context so that the stable parts (system prompt, tool schemas, base instructions) always appear first and are identical across turns enables prefix caching (Anthropic, OpenAI). Verso must keep its stable context prefix canonical and immutable per session.

### 4. Compaction is a first-class agent lifecycle event, not an afterthought
- Jeff Huber: built-in compaction (e.g., Claude's `/compact`) is essentially a no-op — negligible difference from no compaction. Good compaction requires a carefully engineered compaction prompt.
- Dex Horthy: intentional compaction at phase boundaries (research → plan → implement) with a structured handoff file containing file names, line numbers, what's done, what remains.
- Verso must offer: `agent.compact(prompt=CompactionPrompt(...))` as an explicit API call, not auto-magic. The compaction should output a structured `CompactionBundle` (not raw text) that can be deserialized by the next agent instance.
- Anti-pattern to avoid: `/compact` being the only option, with no user-controllable prompt or structured output schema.

### 5. Failure-case memory is more reliable than success-case memory
- Chroma's finding: injecting past failure cases reliably improves agent performance (breaks out of local minima). Injecting past success cases often causes lazy pattern-matching ("just return the cached answer").
- Verso's episodic memory design: store failures explicitly and make them easy to inject into context. Be cautious with success case injection — only inject when the task is demonstrably similar AND there is explicit user intent to reuse the solution.
- Memory API: `memory.store(case_type='failure'|'success', content=..., tags=[...])` with `memory.retrieve(case_type='failure', ...)` as the primary retrieval path.

### 6. Context window position matters for eval speed and quality
- Jake Heller's trick: make the model output the objective answer FIRST (number, true/false, verdict) before explanation, then use `max_tokens=1` + stop words to capture the single token.
- Implication for Verso's eval integration: structured output schemas should always put the scorable/parseable field first. Verso's default output schema for classification/scoring agents should be `{verdict: ..., confidence: ..., explanation: ...}` — not `{explanation: ..., verdict: ...}`.
- The "think-before-commit" effect: model gives a higher quality one-token answer because it thinks a full explanation follows. Verso can exploit this via a `ForceExplainFirst=True` mode that appends explanation to the output schema even if the caller only needs the verdict.

### 7. Micro-step decomposition maps directly to per-step evals
- CoCounsel's architecture: each skill is a chain of micro-steps (clarify → query formulation → execute search → relevance score → notes → synthesis). Each micro-step has its own prompt, its own evals, eventually its own fine-tuned model.
- Verso's agent design should make it natural to define eval suites at the step level, not just the workflow level: `step.eval(cases=[...], judge=...)`. Step-level evals are faster to iterate than end-to-end evals.
- The "evals per prompt" loop (write → test 10 → fix → test 50 → fix → test 1,000) is the core development workflow; Verso should have opinionated tooling for this loop built in.

### 8. Linear vs. agentic branching as an explicit design choice
- Jake Heller: "Sometimes the task is linear and predictable — don't be agentic behind the scenes. Just program it: def step_one, def step_two." Only make it agentic if the task genuinely requires re-planning based on results.
- Verso's positioning: clean ReAct loop is the default; deterministic pipelines (DAGs) are the escape hatch for linear workflows. The framework should make it easy to declare a step as "deterministic" (no LLM branching, just code) vs. "agentic" (LLM decides next action).
- Anti-pattern: wrapping a linear 5-step pipeline in a full ReAct loop just because it uses an LLM — this adds latency and unpredictability with no benefit.

### 9. Sub-agents as context isolation, not role simulation
- Dex Horthy: sub-agents are not about simulating org charts. They are about preventing context pollution — offload expensive search/read tasks to a sub-agent that returns a focused summary, so the parent's context window stays clean.
- Verso's sub-agent API should be designed around context budgets: spawning a sub-agent is essentially delegating a "context-expensive" operation so its token cost doesn't accumulate in the parent.
- The sub-agent's response format should be structured and compact (file names + line numbers, not the raw file content) — Verso should encourage/enforce this via typed sub-agent return types.

### 10. Context quality debug loop: read what the model reads
- Jake Heller: before changing any prompt, read the raw context verbatim — including spacing and OCR artifacts. If the context is unreadable by a human, it will be unreadable by the model.
- Verso should offer a `context.inspect()` method that returns the exact bytes/tokens that will be sent to the model — making the "read what the model reads" debug protocol easy and standard.
- Retrieval quality gates: Verso's built-in RAG should include a `quality_check` hook that validates retrieved content before injection — e.g., OCR quality score, encoding validity, minimum coherence check.

### 11. Model routing per step is a cost and quality lever
- Jake Heller: run different models for different micro-steps. Gemini 2.5 Flash or GPT-4o mini for simple classification; GPT-4o or Claude Opus for synthesis/reasoning.
- Verso's step definition should accept a `model` parameter per step, not just at the agent level. Default: inherit from agent config. Override: per-step explicit model.
- Cost-aware routing: Verso should expose cost estimates per step so developers can identify which steps to down-model.

### 12. Specs/plans as the durable artifact, not code
- Dex Horthy: the spec (research file + plan) is more valuable than the generated code. A misunderstanding in research creates thousands of bad code lines; a bad plan line creates hundreds.
- For Verso's workflow orchestration: the plan/spec should be a first-class persisted artifact — not thrown away after execution. Plans should be versionable, reviewable, and used as the compaction handoff document between agent sessions.
- "Code review is about mental alignment" — similarly, Verso's run logs should show the plan/spec the agent was executing, not just tool calls and outputs.
