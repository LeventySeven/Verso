# Engineering Practices That Make Coding Agents Work

**Source:** https://www.youtube.com/watch?v=owmJyKVu5f8  
**Speaker:** Simon Willison  
**Venue:** The Pragmatic Summit (The Pragmatic Engineer)  
**Duration:** ~28 min  
**Transcript found:** Partial — Fireside chat writeup at simonw.substack.com/p/fireside-chat-about-agentic-engineering + Agentic Engineering Patterns guide at simonwillison.net/guides/agentic-engineering-patterns/. No verbatim video transcript located; content is from Willison's own contemporaneous newsletter posts about the same talk and guide.

---

## Core Argument

Willison argues that the discipline of "agentic engineering" — building software *using* coding agents that can both generate and execute code — requires specific engineering practices to be safe and productive. The practices cluster around three problems: (1) verifying agent output, (2) containing blast radius, and (3) maintaining code quality across long sessions.

---

## Key Practices and Arguments

### 1. Tests Are Now Non-Optional

"Writing tests is no longer even remotely optional when using coding agents."

Previously he "hated test-first TDD throughout my career." Now: "Getting agents to do it is fine." The reason is economic: test creation is "effectively free" computationally, and tests are the primary mechanism for catching agent-generated code that passes a surface review but fails at runtime.

Pattern: **Red/Green TDD** — start every session by having the agent run tests first. Described as "a minimal prompt that dramatically improves code reliability."

### 2. Manual Testing Supplements Automation

He built **Showboat** — a tool that creates Markdown documentation of manual API testing, capturing curl commands and outputs. Motivation: automated test suites can pass while code fails in actual runtime. Showboat captures what `exec`-level testing produces so agents cannot hallucinate results.

The specific Showboat pattern: prompt the agent to run `showboat exec` plus `sed/grep/cat` to include live code snippets rather than letting the agent copy them manually ("since that could introduce a risk of hallucinations or mistakes").

### 3. Sandboxing Is the Most Important Practice

"The most important thing is sandboxing."

He uses Claude Code's Anthropic-hosted Linux containers. His risk calculus: worst case of a breach in his open-source projects is source code exposure, which is acceptable. For local use, he runs with `--dangerously-skip-permissions` while mitigating risk by not following untrusted repository instructions.

### 4. The Lethal Trifecta (Security Model)

Willison coined "prompt injection" in 2022. He identifies a **lethal trifecta** that creates catastrophic risk:
1. Access to **private data** (API keys, emails, credentials)
2. Exposure to **malicious instructions** (untrusted input in context)
3. **Exfiltration capability** (ability to send data outward)

Example: a digital assistant with email access that receives instructions in an email to forward password-reset emails. The trifecta model is a checklist for evaluating agent scope.

### 5. Code Quality Is a Choice

"Having poor quality code from an agent is a choice that you make."

Single-page "vibe-coded" tools: 800 lines of spaghetti is fine. Long-term maintained systems: agents can refactor code that humans would skip because of time constraints. The constraint is no longer time — it is intentionality.

Pattern: use **cookiecutter templates** that establish testing conventions, README structure, and CI setup upfront. Agents follow patterns "almost to a tee" when given a codebase with established conventions.

### 6. Conformance-Driven Development

A powerful pattern for porting: write a test suite that passes across multiple reference implementations, then use those shared conformance tests to guide a new implementation. Example: 25,000 lines of Rust ported from C++ in two weeks with zero regressions.

### 7. Hoard What You Know How to Do

Competitive advantage shifts from execution to knowledge of what is possible — knowing obscure platform capabilities, edge cases, and constraints. This directs agents toward viable solutions they might otherwise miss.

### 8. Linear Walkthroughs

Request agents to produce a structured linear walkthrough of a codebase. This pattern catches post-hoc understanding of "vibe-coded" projects. The Showboat tooling captures live execution output alongside Markdown commentary to prevent hallucination.

---

## Key Quotes

- "The most important thing is sandboxing."
- "Having poor quality code from an agent is a choice that you make."
- "I have hated [test-first TDD] throughout my career... Getting agents to do it is fine."
- "They're incredibly consistent. If you've got a codebase with patterns, they will follow those patterns almost to a tee."
- "This stuff is absolutely exhausting. I often have three projects working simultaneously." (on managing multiple agents)
- "Can you explain what your startup does without mentioning AI?" (his test for product clarity, from related Register interview)

---

## Production Maturity Signals

- GPT-4: first model where outputs were useful rather than hallucinated.
- Claude Code + Sonnet 3.5 (approx. one year before the talk): enabled reliable terminal-level navigation.
- November 2025 milestone: Willison completes complex multi-step tasks with two-sentence prompts without questioning success — described as unprecedented reliability.
- He estimates six months of discovery work remaining to understand what current frontier models (Opus 4.6) can do that remains unexplored.

---

## VERSO RELEVANCE

**[SHARPENS §5.5 / evals]** The **Showboat pattern** — agent uses `exec` to capture live outputs rather than narrating results — is a concrete mechanism for anti-hallucination in evals. Verso's embedded evals harness should distinguish between "agent self-reports success" and "harness verifies observable output." The exec-capture pattern is a direct implementation idea.  
*Verdict: sharp, actionable, not overbuilt.*

**[CONFIRMS §6.3 / safety]** The **lethal trifecta** (private data + untrusted input + exfiltration capability) is a clean threat model that maps directly to Verso's §6.3 safety scope. When Verso documents its HITL and permission model, the trifecta is a checklist-level framing the audience already knows.  
*Verdict: confirms and sharpens the framing.*

**[CONFIRMS §5.3 / tools + loop_harness]** The emphasis on **sandboxing as the single most important practice** confirms that the harness layer — not the loop — is where safety lives. Willison's trust calculus (what is the worst-case blast radius?) is exactly the question a Verso RunContext should help users answer.  
*Verdict: strong confirmation.*

**[NEW-IDEA / loop_harness]** **Conformance-driven development** — a shared test suite that multiple implementations must pass — is a pattern for multi-model/multi-agent verification that Verso hasn't named. In a multi-agent context, a canonical harness conformance suite could verify that swapped sub-agents produce equivalent outputs.  
*Verdict: interesting, don't over-index yet.*

**[CONFIRMS §5.1 / loop_harness]** Willison's observation that "agents follow codebase patterns almost to a tee" confirms Verso's position that the harness layer (the patterns, the context engineering) does more work than the loop logic itself.  
*Verdict: confirms core bet.*

**[SHARPENS §12 / strategy]** The cultural divide he describes — craft engineers vs. pragmatists — is the audience segmentation question Verso must answer. Verso's "no bullshit / simplicity" positioning speaks to pragmatists. This suggests leaning into the pragmatist framing explicitly in positioning.  
*Verdict: sharp, low effort to act on.*

---

## Unreachable Content

No verbatim transcript of the YouTube video (owmJyKVu5f8) was found. Content above is from Willison's own published newsletter and guide posts that cover the same material as the Pragmatic Summit talk.
