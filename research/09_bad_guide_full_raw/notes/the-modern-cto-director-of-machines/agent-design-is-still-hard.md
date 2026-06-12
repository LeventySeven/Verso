# Agent Design Is Still Hard

**Source:** https://lucumr.pocoo.org/2025/11/21/agents-are-hard/  
**Author:** Armin Ronacher (creator of Flask, Jinja2, Click; currently building production agents)  
**Published:** November 21, 2025  
**Status:** read_full — full text fetched directly  
**Themes:** loop_harness · context · evals · model · strategy

---

## Faithful Digest

Ronacher reports from the trenches of building a real production agent (not a demo) as of late 2025. The essay is a practitioner's field notes, organized around seven hard-won lessons.

### 1. Skip high-level SDKs — target the provider SDK directly

> "The first is that the differences between models are significant enough that you will need to build your own agent abstraction. We have not found any of the solutions from these SDKs that build the right abstraction for an agent."

His team adopted the Vercel AI SDK's provider abstractions but drove the loop themselves. By the time this essay was written they would *not* make that choice again. The reason is two-fold: (a) provider-side tools (e.g., Anthropic's built-in web search) corrupt message history when fed through a unifying format layer — "the web search tool from Anthropic routinely destroys the message history with the Vercel SDK, and we haven't yet fully figured out the cause"; (b) cache management is dramatically harder through an abstraction.

> "There is absolutely nothing wrong with the Vercel AI SDK, but when you are trying to build an agent, two things happen that we originally didn't anticipate."

**Mechanism:** "Using the original SDKs from the dedicated platforms keeps you fully in control. With some of these higher-level SDKs you have to build on top of their existing abstractions, which might not be the ones you actually want in the end."

### 2. Explicit cache management is superior to implicit

> "I initially found the manual management pretty dumb. Why doesn't the platform do this for me? But I've fully come around and now vastly prefer explicit cache management."

Ronacher describes Anthropic's explicit cache-point model as better for predictability and cost control. He runs three cache anchors:
- One after the system prompt
- Two at the conversation start, where the trailing one floats up with the conversation tail

**Key constraint this forces:** system prompt and tool selection must be *mostly static*. Dynamic information (e.g., current time) is injected as a separate message later in the context so it does not trash the cache.

> "Because the system prompt and the tool selection now have to be mostly static, we feed a dynamic message later to provide information such as the current time. Otherwise, this would trash the cache."

**Consequence for agent design:** he leans heavily on *reinforcement* inside tool responses to deliver dynamic context, rather than updating the static prefix.

### 3. Reinforcement on every tool return — not just up-front

This is the essay's most operationally novel point. "Reinforcement" means: every time the agent calls a tool, the tool response contains not only the data output but also re-injected objective reminders, status updates, and corrective hints.

> "Every time the agent runs a tool you have the opportunity to not just return data that the tool produces, but also to feed more information back into the loop. For instance, you can remind the agent about the overall objective and the status of individual tasks."

Three sub-cases:
- **Objective re-statement** on every tool return keeps long contexts on track
- **Parallel state injection**: if the agent uses parallel processing, updated state from background processes is injected into the next tool response
- **Self-reinforcement tools**: Claude Code's todo-write tool is cited as the canonical example — it is literally just an echo: "All it does is take from the agent a list of tasks that it thinks it should do and echo out what came in. It's basically just an echo tool; it really doesn't do anything else. But that is enough to drive the agent forward better than if the only task and subtask were given at the beginning of the context."
- **Recovery guidance**: "if our agent fails and retries from a certain step forward but the recovery operates off broken data, we inject a message informing it that it might want to back off a couple of steps and redo an earlier step."

### 4. Isolate failures in throwaway sub-agents

> "If you expect a lot of failures during code execution, there is an opportunity to hide those failures from the context. This can happen in two ways."

**Option A (sub-agent isolation):** Run iterative/retrying subtasks in a dedicated sub-agent. Report only the success outcome (plus a brief summary of what failed, for future steering). Failures never appear in the parent context.

**Option B (context editing):** Anthropic allows editing the conversation context to strip out failed attempts. Ronacher is skeptical of this in practice:
> "So far we haven't had a lot of success with context editing, but we believe it's an interesting thing we would love to explore more."

Key trade-off: context editing **invalidates caches unconditionally**. There is no way around it. So the token savings from removing failed paths must outweigh the cache-miss cost.

> "Unfortunately, context editing will automatically invalidate caches. There is really no way around it. So it can be unclear when the trade-off of doing that compensates for the extra cost of trashing the cache."

### 5. Shared file-system-like layer as the inter-agent substrate

> "You should try to build an agent that doesn't have dead ends. A dead end is where a task can only continue executing within the sub-tool that you built."

The mechanism: a virtual file system that all tools share. Image-generation tool writes to it. Code-execution tool reads from it. Inference tools consume paths. This prevents tool-level lock-in (e.g., "an image generator that can only feed output into one more tool").

> "The file system is the mechanism that we use for that. But it does require tools to be built in a way that they can take file paths to the virtual file system to work with."

Example: `ExecuteCode` and `RunInference` share the same virtual file system and tools accept `path` parameters.

### 6. Output tool challenges

They use an explicit "output tool" as the sole mechanism for communicating to the outside world (in their case, sending an email). Problems observed:
- Steering tone is harder through an output tool than through the main loop's text output — the mechanism is unclear but likely training-related
- Running a second LLM (Gemini 2.5 Flash) to reformat output increases latency and degrades quality because the sub-model lacks context
- The agent sometimes simply doesn't call the output tool. Mitigation: remember whether it was called, and if the loop ends without calling it, inject a reinforcement message.

### 7. Model choice as of late 2025

> "I think Haiku and Sonnet are still the best tool callers available, so they make for excellent choices in the agent loop."

GPT family has not worked well for the main loop. For subtask inference (summarizing large documents, processing PDFs, image information extraction): Gemini 2.5.

> "There's also probably the very obvious realization that token cost alone doesn't really define how expensive an agent. A better tool caller will do the job in fewer tokens. There are some cheaper models available than sonnet today, but they are not necessarily cheaper in a loop."

### 8. Evals — honest confession of failure

> "We find testing and evals to be the hardest problem here... the agentic nature makes it even harder. Unlike prompts, you cannot just do the evals in some external system because there's too much you need to feed into it. This means you want to do evals based on observability data or instrumenting your actual test runs. So far none of the solutions we have tried have convinced us that they found the right approach here."

He reports no solution satisfying enough to recommend.

### 9. Brief notes on tool minimalism (linked, not detailed)

In the "quick reads" section, Ronacher highlights an argument that many MCP servers are overengineered and include large toolsets that consume lots of context. The proposed minimalist alternative: simple CLI tools executed via Bash (start, navigate, evaluate JS, screenshot) to keep token usage small and workflows flexible.

---

## VERSO RELEVANCE

### Finding 1: High-level SDK abstraction is net negative for real agents
**Tag:** [SHARPENS §5.1]  
The loop abstraction that "third-party SDKs" offer breaks at exactly the places that matter for production: cache management, provider-side tool message formats, and cache-point placement. Ronacher's finding directly confirms Verso's design bet that the loop must be written by the framework itself rather than delegated to a provider-agnostic SDK. However, it SHARPENS rather than confirms because it adds a specific failure mode previously not catalogued: **message history corruption from format unification when using provider-side tools** (like Anthropic's built-in web search). Verso must ensure that when MCP is used (the demoted adapter path), it does not corrupt message history through format translation.  
**Verdict:** sharpen — add explicit test coverage for MCP tool message format round-trips.

### Finding 2: Reinforcement on every tool return is the primary dynamic context mechanism
**Tag:** [NEW-IDEA §5.1, §5.2]  
This is structurally absent from Verso's already-known context engineering primitives. The pattern is: the tool response is not just data — it is the primary site for injecting dynamic system state, re-asserting the objective, and providing error recovery hints. This is distinct from the static system prompt (which must be frozen for cache) and from observation masking (which removes data). It is a *positive injection* on each loop turn. The self-reinforcement echo-tool (Claude Code's todo-write) is a concrete implementation pattern worth studying.  
**Verdict:** adopt-now — treat tool responses as a first-class context injection site; document the pattern in §5.1 (loop) and §5.2 (context engineering).

### Finding 3: Cache invalidation is the hard constraint on context editing
**Tag:** [SHARPENS §5.2, §6.1]  
Context editing (Verso's "observation-masking compaction") unconditionally invalidates all caches. Ronacher has tried it and found the trade-off unclear — it requires token savings to exceed cache re-computation cost. Verso's compaction strategy (N=10 masking) should explicitly model this: compact only when the expected token savings over remaining loop turns justify the cache-miss cost. This is a sharpen on the already-known observation-masking mechanism.  
**Verdict:** sharpen — add a cost model (projected remaining turns × average token cost vs. cache-miss cost) before triggering compaction.

### Finding 4: Sub-agent isolation as failure quarantine, not just parallelism
**Tag:** [SHARPENS §6.2]  
Ronacher frames sub-agents primarily as *failure isolation* units: run retrying/uncertain subtasks in a disposable sub-agent, return only success. The summary of failed approaches is still fed back (to inform future steering), but the full failure context is quarantined. This reframes Verso's multi-agent architecture: sub-agents are not primarily about concurrency, they are quarantine containers that prevent local failures from corrupting the parent loop's context.  
**Verdict:** sharpen — multi-agent doc should lead with failure isolation semantics, not parallelism.

### Finding 5: Evals require instrumentation of actual test runs, not external eval systems
**Tag:** [SHARPENS §5.5]  
Ronacher's direct experience: no external eval platform works for agents because they cannot replicate the full execution environment. The practical approach is observability-based (instrument real runs, extract eval signals from traces). This argues that Verso's eval harness must be embedded in the agent execution path (in-loop hooks), not a standalone post-hoc system. The judge-panel approach already known is the right direction, but this finding argues eval *data collection* must happen inside the loop itself.  
**Verdict:** sharpen — eval hooks must be in-loop, not post-hoc; observability traces are the ground truth.

### Finding 6: MCP minimalism — large MCP toolsets burn context
**Tag:** [CONFIRMS §5.3]  
Ronacher approvingly cites the argument that large MCP server tool catalogs consume context tokens and should be replaced with minimal CLI tools. This directly confirms Verso's positioning of MCP as a demoted opt-in adapter rather than the primary tool path.  
**Verdict:** confirm (already-known).

### Finding 7: Token cost per turn ≠ agent cost; better tool callers do more per turn
**Tag:** [SHARPENS §6.4]  
"A better tool caller will do the job in fewer tokens. There are some cheaper models available than Sonnet today, but they are not necessarily cheaper in a loop." This argues that Verso's role-tiered model strategy (cheap loop / mid retry / reasoning synthesis) must use *tool-call quality* as the primary axis for loop model selection, not price per token.  
**Verdict:** sharpen — role-tiered model selection should document tool-call quality as the primary criterion for loop model tier.

---

## One-line Verdicts Summary

| Finding | Verdict |
|---|---|
| Skip high-level SDKs | confirm (already positioned correctly) |
| Explicit cache management is superior | confirm (already-known) |
| Reinforcement on every tool return | adopt-now |
| Cache invalidation vs. context editing trade-off | sharpen |
| Sub-agent as failure quarantine | sharpen |
| Evals require in-loop instrumentation | sharpen |
| MCP minimalism | confirm |
| Token cost ≠ agent cost; quality tool callers | sharpen |
