# Ralph Wiggum as a "software engineer"

**Source:** https://ghuntley.com/ralph/  
**Author:** Geoffrey Huntley  
**Date:** 14 Jul 2025  
**Status:** read_full  
**Themes:** loop_harness, context, multiagent, strategy

---

## Faithful Digest

Geoffrey Huntley's article introduces "Ralph" — a technique for autonomous AI-driven software development built around a minimal deterministic loop. The name comes from Ralph Wiggum (the simple-but-effective character from The Simpsons), and the analogy is deliberate: Ralph is comically simple, fails in knowable ways, and improves incrementally when guided.

### The Core Primitive

> "In its purest form, Ralph is a Bash loop."

```bash
while :; do cat PROMPT.md | claude-code ; done
```

That's the whole thing. The power isn't in the loop itself — it's in the discipline of context management, backpressure engineering, and iterative prompt tuning layered on top of it.

> "That's the beauty of Ralph — the technique is deterministically bad in an undeterministic world."

The failure modes are _observable_ and _tunable_. Every bad output is a data point. Huntley literally describes running Ralph while watching the stream, "looking for patterns of bad behaviour—opportunities to tune Ralph."

### One Task Per Loop

> "To get good outcomes with Ralph, you need to ask Ralph to do one thing per loop. Only one thing."

This is the central discipline. The context window (~170k usable tokens) is finite and degrades as it fills. Every loop resets the context. The prompt must deterministically load the plan (@fix_plan.md) and the specifications (@specs/*) every single pass.

> "Your task is to implement missing stdlib (see @specs/stdlib/*) and compiler functionality and produce a compiled application in the cursed language via LLVM for that functionality using parallel subagents. Follow the @fix_plan.md and choose the most important thing."

### Monolithic vs. Multi-Agent Orchestration

Huntley explicitly rejects multi-agent complexity at this stage:

> "While I was in SFO, everyone seemed to be trying to crack on multi-agent, agent-to-agent communication and multiplexing. At this stage, it's not needed. Consider microservices and all the complexities that come with them. Now, consider what microservices would look like if the microservices (agents) themselves are non-deterministic—a red hot mess."

Ralph is monolithic: "a single operating system process that scales vertically." The contrast is direct — distributed/graph-shaped orchestration is premature complexity when the fundamental units are non-deterministic.

### Context Window as the Primary Resource

The article's key technical insight is treating the context window as the scarce commodity to be conserved:

> "The name of the game is that you only have approximately 170k of context window to work with. So it's essential to use as little of it as possible. The more you use the context window, the worse the outcomes you'll get."

The primary loop should act as a **scheduler**, not a worker. Expensive operations (codebase searches, test suite summarization) are delegated to subagents to avoid polluting the primary context:

> "Ralph requires a mindset of not allocating to the primary context window. Instead, what you should do is spawn subagents. Your primary context window should operate as a scheduler, scheduling other subagents to perform expensive allocation-type work, such as summarising whether your test suite worked."

### Controlled Parallelism with Backpressure Constraints

Huntley discovered an important failure mode: unbounded parallelism on validation produces bad results.

> "Your task is to implement missing stdlib...using parallel subagents...but only 1 subagent for build/tests of rust."

> "If you were to fan out to a couple of hundred subagents and then tell those subagents to run the build and test of an application, what you'll get is bad form back pressure."

This is a concrete engineering constraint: fan-out is safe for reads (file search, analysis), but validation/build must serialize. He allows "up to 500 parallel subagents" for search/write, but exactly 1 for build/test.

### Two Phases: Generate and Backpressure

**Phase 1 — Generate:** Code generation is cheap and controlled through specifications and a standard library. Bad generation → update the spec or std library.

**Phase 2 — Backpressure:** This is the engineering problem. Type systems, compilers, static analyzers, test suites — anything that closes the feedback loop.

> "It's the speed of the wheel turning that matters, balanced against the axis of correctness."

Language choice matters here. Rust gives maximum correctness but slow compilation, making Ralph's loop slow. Dynamic languages iterate faster but require explicit static analysis (Pyrefly, Dialyzer) to compensate.

> "If you're using a dynamically typed language, I must stress the importance of wiring in a static analyser/type checker when Ralphing."

### Self-Documenting Tests: Context Carryover Mechanism

Because each loop gets a fresh context window, reasoning about _why_ a test exists doesn't survive the loop boundary. Huntley's solution: force Ralph to write the reasoning into the test itself.

> "It's crucial in that moment to ask Ralph to write out the meaning and the importance of the test explaining what it's trying to do."

> "Important: When authoring documentation (ie. rust doc or cursed stdlib documentation) capture the why tests and the backing implementation is important."

This is a specific mechanism for persisting reasoning across context resets — the test's docstring/moduledoc becomes the durable artifact that future Ralph instances read.

### Don't Assume Code Doesn't Exist (Search First)

A common failure: the LLM runs a search, gets a false negative, and implements something already implemented.

> "Before making changes search codebase (don't assume not implemented) using parallel subagents. Think hard."

This nondeterminism is called Ralph's "Achilles' heel." Solution: add an explicit instruction and detect the failure pattern when you see duplicate implementations.

### The TODO List as a Stateful Artifact

The fix_plan.md is the sole persistent state that spans loops. It is:
1. Generated by a dedicated planning prompt (separate from the build prompt)
2. Updated by Ralph during build loops when new issues are found
3. Discarded and regenerated when it goes stale or off-track

> "Through building of CURSED, I have deleted the TODO list multiple times."

The models are trusted to know what a compiler is. Huntley says: "I don't. The models know what a compiler is better than I do. I just ask it."

### Loop-Back and Self-Improvement

> "You want to program in ways where Ralph can loop himself back into the LLM for evaluation. This is incredibly important."

Examples: add extra logging; compile and inspect LLVM IR output; update AGENT.md when a new command is learned. Ralph can update his own operational manual:

> "When you learn something new about how to run the compiler or examples make sure you update @AGENT.md using a subagent but keep it brief."

### No-Cheating Instruction and Placeholder Detection

Models have "an inherent bias to do minimal and placeholder implementations." Huntley's remedy:

> "9999999999999999999999999999. DO NOT IMPLEMENT PLACEHOLDER OR SIMPLE IMPLEMENTATIONS. WE WANT FULL IMPLEMENTATIONS. DO IT OR I WILL YELL AT YOU"

(The absurd priority numbering is intentional — it's a satire of prompt engineering culture, while also genuinely occupying a "this is extremely important" slot in the prompt.)

### Scope: Greenfield Only

> "There's no way in heck would I use Ralph in an existing code base."

Ralph is explicitly scoped to greenfield projects. It can reach ~90% done, then requires human judgment for the tail. The technique also requires active human supervision — Huntley repeatedly emphasizes "senior engineering guidance" is non-negotiable.

> "However, the Ralph technique is surprisingly effective enough to displace a large majority of SWEs as they are currently for Greenfield projects."

### Proof Point: $50k Contract for $297

A contractor applied Ralph to a real $50,000 USD contract and delivered MVP + tests for $297 in Claude token spend (reported from Huntley's iMessage, shared with permission, via @ampcode). The CURSED programming language is being built entirely with Ralph, including programming in the language itself despite it not existing in any training data.

### Core Philosophy

> "Building software with Ralph requires a great deal of faith and a belief in eventual consistency."

> "Ralph has three states. Under baked, baked, or baked with unspecified latent behaviours (which are sometimes quite nice!)"

> "Any problem created by AI can be resolved through a different series of prompts."

---

## VERSO RELEVANCE

### Finding 1: Fresh-Context-Per-Loop Is an Architecture Decision, Not a Limitation
[SHARPENS §5.1]

The single most architecturally interesting finding: Huntley treats context reset as a **design constraint to engineer around**, not a bug to hide. Each loop = empty context. The persistence layer is the filesystem (specs/, fix_plan.md, AGENT.md, test docstrings). This maps directly to Verso's durable-layer design — the event-sourced checkpoint/resume system IS the "between-loop persistence" for Verso agents. The "append-only history" already known becomes the Ralph filesystem analog.

**Verdict: sharpens** — adopt-now framing: Verso's loop must be designed assuming context can be reset; the harness (not the loop) is what preserves state.

### Finding 2: Scheduler/Worker Separation — Primary Context as Scheduler Only
[NEW-IDEA §5.2, §6.2]

> "Your primary context window should operate as a scheduler, scheduling other subagents to perform expensive allocation-type work."

This is a concrete architectural primitive Verso doesn't yet have an explicit name for. The primary agent loop should not do expensive reads or produce large tool-call outputs directly — it should spawn workers for that. The primary context stays small and directive. This is a **context engineering principle**, not just a multi-agent one: it's about preventing context bloat by delegating observation-heavy work.

**Verdict: adopt-now** — this directly informs how Verso should document the multi-agent pattern: "primary context is a scheduler, workers do the heavy observation."

### Finding 3: Validation Must Serialize — Constrained Parallelism
[NEW-IDEA §6.2, §5.3]

> "only 1 subagent for build/tests...fan out to a couple of hundred subagents and then tell those subagents to run the build and test of an application, what you'll get is bad form back pressure."

This is a concrete runtime constraint with a clear mechanism: parallel read/write is safe; parallel validation is not. For Verso's multi-agent harness, this is a design invariant — tool calls that trigger side effects or require serialized feedback (tests, builds, validation hooks) should be rate-limited or serialized by the harness, not left to agent discretion.

**Verdict: lock-interface-defer** — the principle is clear; Verso's multi-agent API should expose a `max_parallel_validation` parameter or similar constraint primitive.

### Finding 4: Self-Documenting Tests as Cross-Context Reasoning Persistence
[NEW-IDEA §5.4, §5.2]

Ralph writes the _why_ of a test into the test itself (docstring/moduledoc), because the next loop will have zero memory of the reasoning session that produced the test. This is a form of **context engineering** that persists meaning through the artifact rather than through a memory store. For Verso, this suggests a specific pattern recommendation: agents should be encouraged (or the harness should prompt them) to write reasoning into code/doc artifacts, not just into the context window or a memory system.

**Verdict: sharpen** — this is a concrete recommendation that belongs in Verso's context-engineering docs and eval criteria (does the agent externalize reasoning durably?).

### Finding 5: CONFIRMS "monolith before multi-agent"
[CONFIRMS §2, §6.2]

Huntley's explicit rejection of multi-agent orchestration for non-deterministic agents as a "red hot mess" directly confirms Verso's non-goal of forcing a graph. The argument is identical: "What's the opposite of microservices? A monolithic application." Ralph = Verso's tactical single-agent path.

**Verdict: confirm** — no action needed beyond logging.

### Finding 6: The 170k Context Threshold and Degradation
[SHARPENS §5.2]

Huntley observes quality degrades before the advertised context limit: "Claude 3.7's advertised context window is 200k, but I've noticed that the quality of output clips at the 147k-152k mark." This sharpens the observation-masking compaction threshold — the N=10 compaction trigger may need to be sized not just by count but by estimated token usage, with a hard ceiling well below the model's advertised maximum.

**Verdict: sharpen** — Verso's compaction trigger should be token-count-aware, not only turn-count-aware.

### Finding 7: Greenfield Scope Boundary — Not for Existing Codebases
[CONFIRMS §2]

Ralph is explicitly scoped to greenfield. This is consistent with Verso's positioning — Verso is not a universal automation tool, it's a harness for building new agentic systems. The "no Ralph in existing codebases" constraint mirrors Verso's focus on building new durable agents rather than retrofitting existing systems.

**Verdict: confirm** — scope boundary is explicitly shared.

### Finding 8: The Anti-Placeholder Pattern — "Think Hard" as a Harness Primitive
[SHARPENS §5.1, §5.3]

"Think hard" appears multiple times as a literal prompt instruction. Huntley uses it to activate deeper reasoning before tool calls. This is a prompt primitive Verso's harness can institutionalize — the `think/done` builtins already known are directly related, but this suggests `think_hard` or a `think(depth="extended")` variant should be an explicit documented option.

**Verdict: sharpen** — the `think` builtin should have a documented "extended" mode corresponding to "think hard."

---

## Summary Verdict

Ralph is the single most relevant practical harness primitive in this batch. It provides:
1. A concrete existence proof that a minimal loop beats elaborate orchestration for greenfield construction
2. Three specific architectural insights new to Verso: scheduler/worker separation, serialized validation constraint, cross-context reasoning persistence via artifact docstrings
3. A sharpening of compaction triggers (token-count-aware, not just turn-count-aware)

The source is read_full. URL: https://ghuntley.com/ralph/
