# Interrupt 2025 Keynote

**Source:** https://www.youtube.com/watch?v=DrygcOI-kG8  
**Speaker:** Harrison Chase (LangChain)  
**Venue:** Interrupt 2025 (LangChain's inaugural agent conference)  
**Duration:** 23 min  
**Transcript found:** Partial — detailed analysis at sequoiacap.com/podcast/context-engineering-our-way-to-long-horizon-agents-langchains-harrison-chase/ (Sequoia Capital interview, same period, covering the same arguments in depth) + conference recap at lawwu.github.io/posts/2025-05-23-langchain-interrupt-2025-recap/. No verbatim video transcript located; the Sequoia piece is the richest single source.

---

## Core Argument

Chase argues that the hard part of production agents is not the loop — it is context engineering. The harness layer (what he calls the "harness" vs. the "framework") is where production success lives. He presents LangChain's two-year retrospective on what actually works, announces LangGraph's GA, and introduces the "agent engineer" as a new professional role.

---

## Key Arguments

### 1. Context Engineering Is Everything

"Everything's context engineering" — Chase states he wishes he had coined the term, noting it "describes everything we've done at LangChain."

The problem it solves: in a multi-step agent, you cannot predict what information will be in context at step 14 because 13 prior steps could pull arbitrary data. The critical observation: "you don't actually know what the context at step 14 will be, because there's 13 steps before that that could pull arbitrary things in."

Unlike deterministic software where all logic is in code, agent behavior emerges from both code and model outputs. This makes traces — not breakpoints — the primary debugging tool. Software teams say "show me the code"; agent teams now say "send us a trace."

### 2. Frameworks vs. Harnesses

Chase draws an important distinction:
- **Framework**: unopinionated abstractions (model switching, tool interfaces)
- **Harness**: "batteries included" opinionated implementations — planning tools, compaction logic, file system integration, MCP connections

This is not just vocabulary. Harnesses require "hundreds of lines" of prompting for subagent coordination. Different model families require different harnesses because OpenAI models were trained heavily on Bash while Anthropic built explicit file-editing tools into their training. Success requires knowing what each model family was trained on.

### 3. What Actually Works in Production

**Current killer applications:**
- Coding (primary domain)
- AI SREs and incident investigation
- Research and report generation
- Customer support (with human-in-loop review for final output)

**Success pattern:** Agents excel at producing "first drafts" for human review rather than autonomous production decisions. Chase is explicit: agents aren't "reliable to nine nines" but can "do a ton of work" over extended periods.

**Critical infrastructure:** File system access. Chase says he is "completely file system pilled" — durable file-based state is the practical substrate for long-horizon agents.

### 4. The Development Stack Has Shifted

| Traditional software | Agent development |
|---|---|
| Logic lives in code | Logic splits between code and model behavior |
| Offline unit tests | Online testing with real-world inputs |
| Breakpoint debugging | Trace analysis + human annotation |
| Code reviews | Prompt iteration (more frequent than code changes) |
| LLM-as-judge is supplementary | LLM-as-judge is part of the eval stack |

### 5. Memory: Only Valuable in Recurring Workflows

Chase's finding: memory does not create stickiness in one-off interactions (ChatGPT example). Memory shows value only in recurring, workflow-specific agents — his email agent example. This sharply constrains where memory investment pays off.

**Future pattern: "sleep time compute"** — nightly analysis of trace data with automatic instruction refinement. Agents ingest their own traces, use LLMs to reflect on failures, and modify system prompts without developer intervention.

### 6. Browser Automation Still Doesn't Work Well

"The models just aren't good enough right now" for browser-based tasks compared to coding. This is a current limitation, not a structural one.

### 7. The "Agent Engineer" Role

Four required skill areas:
1. Prompting — optimizing LLM outputs
2. Engineering — robust tools and deployment
3. Product design — converting user workflows to AI solutions
4. Machine learning — evaluation metrics and fine-tuning

His observation: junior developers without "preconceived notions" adopt agentic development more readily than senior engineers.

### 8. Manual Compaction Still Preferred

Currently, harness authors manually decide context compaction strategies. Anthropic experiments with model-driven compaction, but few teams use it — suggesting developer control over compaction remains preferable in 2025.

### 9. Async/Sync Hybrid for Long-Horizon Tasks

Long-horizon agents need **asynchronous task management** (kick off multiple agents) but require **synchronous chat modes** when human feedback is needed on generated artifacts. This creates an architectural seam between fire-and-forget execution and HITL checkpoints.

---

## Key Quotes

- "Everything's context engineering."
- "you don't actually know what the context at step 14 will be, because there's 13 steps before that that could pull arbitrary things in."
- "Software teams say 'show me the code'; agent teams now say 'send us a trace.'"
- "Reliable agents start with the right context."
- LangChain exceeds OpenAI's Python SDK in monthly downloads (70 million) — cited as evidence teams value model-switching flexibility.

---

## VERSO RELEVANCE

**[CONFIRMS §5.2 / context]** Chase's "everything's context engineering" framing strongly confirms Verso's §5.2 bet. The specific mechanism — unpredictability of context at step N due to N-1 prior steps — is the exact problem Verso's ContextBundle + RunContext is designed to address. The trace-as-source-of-truth observation confirms why Verso's append-only history is the right default.  
*Verdict: strong confirmation, use the framing.*

**[SHARPENS §4 / seam]** The **async/sync hybrid** finding — async for fire-and-forget, sync when artifacts need human review — is a precise description of Verso's tactical/durable seam (§4). The "one flag promotes an ephemeral agent to event-sourced checkpoint/resume + HITL" design is exactly the architectural answer to this. Chase names the problem; Verso names the solution.  
*Verdict: sharp confirmation of the seam design.*

**[CONTRADICTS §5.4 / memory]** Chase's finding that memory only creates value in **recurring, workflow-specific** agents (not one-off interactions) directly challenges any assumption that Verso should prioritize general-purpose memory. The 4-tier typed memory design is correct only if Verso targets recurring workflow agents — which it should make explicit.  
*Verdict: sharpens scope of memory investment; don't oversell memory for tactical one-shot agents.*

**[SHARPENS §5.5 / evals]** The shift from offline unit tests to **online testing with trace annotation** is a specific design constraint for Verso's embedded evals (§5.5). The evals harness needs to support trace-based annotation and LLM-as-judge scoring on real traces, not just offline scenarios.  
*Verdict: sharpens evals design, actionable.*

**[NEW-IDEA / loop_harness]** **Sleep-time compute** — nightly trace analysis feeding automatic prompt refinement — is a named pattern for autonomous self-improvement that Verso hasn't addressed. This could be a durable-layer feature: agents that update their own instructions based on trace retrospectives.  
*Verdict: genuinely new, high potential, not for v1.*

**[CONFIRMS §6.1 / durable]** "Completely file system pilled" + the explicit statement that long-horizon agents require durable file-based state confirms Verso's §6.1 durable layer design. File system access is the practical substrate.  
*Verdict: confirms durable layer priority.*

---

## Unreachable Content

No verbatim transcript of the YouTube keynote video (DrygcOI-kG8) was found. The Sequoia Capital interview (same speaker, same period, same arguments) provided the richest available source. Conference recap blogs provided supporting confirmation.
