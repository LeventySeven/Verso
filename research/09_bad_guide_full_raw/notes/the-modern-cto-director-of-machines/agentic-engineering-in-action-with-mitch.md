# Agentic Engineering in Action with Mitchell Hashimoto

**Source:** https://www.youtube.com/watch?v=XyQ4ZTS5dGw  
**Transcript:** Multiple sources assembled:  
- https://mitchellh.com/writing/my-ai-adoption-journey (primary essay, six-step framework)  
- https://mitchellh.com/writing/non-trivial-vibing (Ghostty session transcripts + commentary)  
- https://zed.dev/blog/agentic-engineering-with-mitchell-hashimoto (blog post with selected quotes)  
- https://newsletter.pragmaticengineer.com/p/mitchell-hashimoto (Pragmatic Engineer writeup, paywalled — partial)  
**Status:** read_partial (no word-for-word video transcript found; constructed from Hashimoto's own primary essays and a detailed Zed blog summary; video is a ~1h01m screenshare session; key patterns well-documented in written primary sources by same speaker)  
**Speaker:** Mitchell Hashimoto, HashiCorp co-founder (Vagrant, Terraform, Packer, Consul), creator of Ghostty terminal emulator  
**Event:** Zed video session with Richard Feldman  
**Duration:** ~1h01m

---

## Core Philosophy: Architect, Not Typist

Hashimoto's fundamental position: the human developer remains the software architect. *"I want you to achieve this end goal, but using this shape."*

He explicitly rejects the "agent writes everything freely" model. The human defines code structure, data flow, where state lives, and the expected architecture. Agents fill in the blanks within that structure.

*"Good AI drivers are experts in their domains and utilize AI as an assistant, not a replacement."*

---

## The Six-Step Framework (from `my-ai-adoption-journey`)

Hashimoto documents a progression from chatbot skeptic to "always have an agent running":

1. **Drop the Chatbot** — Move from chat interfaces to agents capable of reading files, executing programs, making HTTP requests. "Chatbots have real value" but correcting mistakes "involves a human to tell them they're wrong repeatedly. It is inefficient."

2. **Reproduce Your Own Work** — Complete tasks manually, then force agents to produce identical results. The critical discipline: *"discovering it myself resulted in a stronger fundamental understanding."* No shortcutting the learning phase.

3. **End-of-Day Agents** — Block final 30 minutes daily to spawn agents for research, parallel exploration, and triage while human regains freshness. Agents work while you sleep.

4. **Outsource the Slam Dunks** — Delegate only tasks with "really high confidence" the agent will succeed. Filter manually by reviewing prior-session outputs for near-certain success before delegation.

5. **Engineer the Harness** — Build verification systems and documentation to prevent agent mistakes. The core reliability mechanism. (See below.)

6. **Always Have an Agent Running** — Maintain continuous background agent work. Goal: agents running "10 to 20% of a normal working day."

---

## Step 5: Engineer the Harness (Primary Mechanism)

This is Hashimoto's most important contribution. Agents perform better when they receive immediate feedback about errors. Two complementary approaches:

### Implicit Prompting via AGENTS.md
Document agent-discovered mistakes in a dedicated `AGENTS.md` file. From the Ghostty project: *"Each line in that file is based on a bad agent behavior, and it almost completely resolved them all."*

This is a living document that grows from observed failures. Each mistake becomes a rule. Rules accumulate into a behavioral specification the agent reads at session start.

### Programmed Verification Tools (the "harness")
Build specific scripts and tools enabling agents to validate their own outputs: screenshots, filtered test runs, automated validators. *"If you give an agent a way to verify its work, it more often than not fixes its own mistakes."*

The key insight: *"agents are much more efficient when they produce the right result the first time."* Investment in verification tooling compounds — every tool written once saves repeated human feedback loops across all future sessions.

---

## Fill-in-the-Blank Technique (from `non-trivial-vibing`)

Hashimoto creates scaffolding with incomplete functions, descriptive names, and TODO comments, then directs the agent to complete the work.

*"AI is very good at fill-in-the-blank or draw-the-rest-of-the-owl."*

This pattern succeeds because the structure is predefined (human architectural decision), leaving only bounded implementation work to the agent. Prevents architectural drift.

---

## The Oracle Technique

A slower, higher-cost subagent (in Amp Code: "deep mode," taking "upwards of 30+ minutes") used exclusively for planning and thinking tasks before implementation. Applied at feature outset:

1. Oracle generates comprehensive plan → saved as `spec.md`
2. Cheaper/faster agents reference `spec.md` during implementation sessions
3. Oracle consulted again before final shipping to identify potential improvements

This is a practical role-tiered model pattern: expensive model for planning and review, cheaper model for execution.

---

## Session Architecture from Non-Trivial Ghostty Feature

The Ghostty unobtrusive auto-update UI feature demonstrates the pattern at scale:

- **16 separate sessions** across 3 calendar days
- **$15.98 total token cost** on Amp platform
- **~8 hours wall-clock time** (fragmented with other tasks)
- Sessions broken into discrete chunks: planning → prototyping → cleanup → backend → integration → final review

Session structure matters: each session has a bounded scope. Frequent commits as "save points" to reset if agents diverge.

**Anti-slop sessions**: cleanup between functional sessions is critical defensive practice. Better organized code helps future agents perform better. *"I don't think I can figure this out on my own, so I decide to pivot"* — recognizing agent failure patterns and switching approaches is a core human-in-loop skill.

---

## Parallel Model Testing on Cloned Repos

Hashimoto runs identical tasks across multiple cloned repositories with different models to identify optimal performers. This is empirical model selection — not assuming a model is best, testing it against actual tasks on actual code.

Claude showed superior results over Gemini in his testing; Gemini "produces an excessive amount of text in response to simple questions, which he finds inefficient."

---

## Parallel Human-Agent Workflow

*"I couldn't do those cleanups and concurrently be QA testing."*

While the agent refactors, Hashimoto conducts QA testing simultaneously. He also defers routine work to agents while maintaining manual focus on high-value architectural decisions.

---

## Simulation and Validation Pattern

For the Ghostty update feature, Hashimoto created a dedicated simulation file with multiple scenarios (happy path, not-found, errors) to manually exercise different update flow states before full integration. This is a lightweight eval suite built inline during development.

Final mandatory: *"Please don't ever ship AI-written code without a thorough manual review."*

---

## Key Limitations Acknowledged

- **Architecture and folder structure**: "LLMs not very good at architecture and folder structure" — stays in human hands
- **Complex data structures**: Poor performance on high-performance/low-level data structures
- **Language constraints**: Complex Zig code problematic; requests rewrites in C/Rust, then converts back manually
- **Scope**: Agents "mostly only good for junior/mid-level problems, not senior level" for complex architectural decisions

---

## The Shipping Policy

*"Only ship code he understands."* When AI produces unfamiliar solutions, treat as learning opportunity. If unable to understand it, discard and reimplement manually. No autonomous shipping of opaque code.

---

## Notifications Off

*"Turn off agent desktop notifications. Context switching is very expensive."* Run agents asynchronously; check outputs at natural breakpoints.

---

## Infrastructure Evolution Concerns

Hashimoto notes "Git and GitHub may not survive the agentic era in their current form." Agents generate excessive churn, making merge queues untenable. Systems must shift from deletion-based to archival-based workflows (analogous to email's evolution). Open source must shift from "default trust" to "default deny" verification models.

---

## Verbatim / Near-Verbatim Quotes

- *"I want you to achieve this end goal, but using this shape."*
- *"Bowling with bumpers, so that they can reach the pins."*
- *"Each line in that file [AGENTS.md] is based on a bad agent behavior, and it almost completely resolved them all."*
- *"If you give an agent a way to verify its work, it more often than not fixes its own mistakes."*
- *"Agents are much more efficient when they produce the right result the first time."*
- *"AI is very good at fill-in-the-blank or draw-the-rest-of-the-owl."*
- *"Good AI drivers are experts in their domains and utilize AI as an assistant, not a replacement."*
- *"Please don't ever ship AI-written code without a thorough manual review."*
- *"Turn off agent desktop notifications. Context switching is very expensive."*
- *"I couldn't do those cleanups and concurrently be QA testing."*

---

## VERSO RELEVANCE

### [CONFIRMS §5.1 — loop_harness]
AGENTS.md as a living behavioral specification accumulated from observed failures directly confirms Verso's embedded in-process evals approach. The harness is not a monitoring layer bolted on — it's the first-class mechanism that makes the loop improve over time. Verso's `define_outcome(bounded)` and judge-panel are the programmatic equivalent of AGENTS.md. Verdict: confirms; Hashimoto provides the practitioner testimony for why harness engineering is the product.

### [SHARPENS §5.3 — tools]
"Programmed verification tools" — scripts agents self-invoke to validate their own outputs — sharpens Verso's tool design principle. The key pattern: tools are not just for side effects, they are for self-assessment. A tool that returns a validation result (pass/fail + why) enables autonomous error correction. This is more specific than ACI tool-design: the tool's output must be agent-readable feedback, not just human-readable results. Verdict: sharpens §5.3; consider adding verification-tool pattern to tool design guide.

### [SHARPENS §5.5 — evals]
The inline simulation file (multiple scenarios for different states) is a lightweight eval suite built during development, not as separate QA infrastructure. This sharpens Verso's "embedded in-process evals" thesis: evals are authored during feature development, not retrofitted. The 16-session cost trace ($15.98) also demonstrates that eval-driven development is economically practical at small scale. Verdict: sharpens §5.5; the "evals built during development" framing is concrete.

### [NEW-IDEA — §6.4 model]
The Oracle technique — expensive slow model for planning/spec generation, cheaper fast models for implementation, expensive model again for final review — is a practical role-tiered model pattern not yet fully elaborated in the PRD. Currently PRD has "role-tiered models" but the specific oracle-for-planning / worker-for-execution / oracle-for-review cycle is a concrete pattern Verso could formalize as a recommended workflow. The spec.md artifact (oracle output preserved for future sessions) also maps to Verso's context bundle: pass the plan forward as a named context artifact.

### [CONFIRMS §4 — seam]
The fill-in-the-blank technique (human defines structure/scaffold, agent implements within it) is the tactical-agent pattern in practice. The human provides the "shape of the solution" (Zed blog quote) and the agent provides the keystrokes. This is exactly the tactical agent's role in Verso: bounded, scoped, with the human retaining architectural control. The seam is where the human hands off the scaffold and reclaims ownership at review. Verdict: confirms §4 design intent.

### [SHARPENS §12 — strategy]
Hashimoto's practitioner authority (HashiCorp founder, serious open-source pedigree, not an AI hype figure) makes the "harness is the product" argument credible to skeptical engineers. His framing "Step 5: Engineer the Harness" as the most important step in the adoption journey — not the model, not the prompt — is the clearest external endorsement of Verso's product thesis. The quote "agents are much more efficient when they produce the right result the first time" is the one-line case for investing in harness engineering. Verdict: sharpens §12; usable as external validation in positioning.
