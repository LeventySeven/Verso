# My LLM Coding Workflow Going into 2026 — Addy Osmani
**Source:** https://addyosmani.com/blog/ai-coding-workflow/
**Author:** Addy Osmani (Google Cloud/Gemini)
**Published:** January 4, 2026
**Status:** read_full
**Themes:** loop_harness, context, strategy, evals

---

## Faithful Digest

### Core Argument
AI coding assistants are "incredible force multipliers, but the human engineer remains the director of the show." The framing is "AI-augmented software engineering" — not autonomous agents. The workflow disciplines that matter most are spec-first planning, small iterative chunks, context provision, and mandatory review of all output. Classic software engineering best practices (specs, tests, code reviews, version control) become *more* important when AIs write half the code, not less.

### Spec-First / Waterfall in 15 Minutes
The recommended starting sequence:
1. Collaborative brainstorm → comprehensive **spec.md** document
2. Feed spec to reasoning model → structured project plan breaking into manageable tasks
3. "Waterfall in 15 minutes" — rapid structured planning before any code

> "Planning first forces you and the AI onto the same page."

This prevents the failure mode where the AI starts immediately on an early interpretation of the task, often the wrong structural interpretation.

### Small Iterative Chunks
Large monolithic requests produce "jumbled, inconsistent results" as if "like 10 devs worked on it without talking to each other." The discipline: split into small, focused tasks tackled sequentially, each staying within context limits. This pairs with TDD — each chunk is testable.

### Context Provision
> "Don't make the AI operate on partial information."

Tools mentioned: Claude Projects (import entire repos), gitingest / repo2txt for bundling code sections. The principle: give the model the full relevant codebase, constraints, preferred approaches, and pitfalls. **Claude Skills** mentioned as "durable and reusable" modular capability packages for packaging instructions and domain expertise — though official tool support remains limited at time of writing.

### Model Selection Strategy
"Model musical chairs" — try multiple models on the same prompt. Different LLMs have distinct "personalities." Osmani gravitates toward Gemini for much coding work (interaction feels "more natural") but switches when needed. The broader principle: intentional model selection rather than defaulting to one option.

### Human-in-the-Loop as Non-Negotiable
> "We're not at the stage of letting an AI agent code an entire feature unattended."

Simon Willison quote used: LLMs are "over-confident and prone to mistakes," writing code with complete conviction even when containing bugs.

Testing strategy: weave testing into the workflow itself — generate test plans during planning, instruct agents to run test suites after implementation, have them debug failures.

Code review: manual review + AI-assisted cross-model review (have Claude write code, have Gemini critique it). Chrome DevTools MCP used to give agents "eyes" for browser-based debugging.

### Commit Discipline
Ultra-granular git habits: commit after each small task or successful edit. "Save points" for rollback. Small commits with clear messages.

Advanced: git worktrees to isolate parallel AI experiments in separate branches, preventing interference while allowing merging of successful changes.

> "Finish task, run tests, commit."

### CLAUDE.md / GEMINI.md Rule Files
Create files containing process rules and coding preferences. Feed at session start to align the model with project conventions. Provide in-line examples showing desired output format. The "Big Daddy" rule mentioned — explicit instructions about handling ambiguity: "If unsure about something, ask for clarification rather than making up answers."

### Automation as Force Multiplier
> "An AI-friendly workflow is one with strong automation."

Robust CI/CD: automated tests, linters, type checkers, staging deployments on every commit/PR. Feed linter output or test failures back to the AI explicitly — it attempts corrections when aware of tool feedback. Some agents can refuse to mark tasks "done" until tests pass.

### AI Amplifies Existing Expertise
LLMs amplify expertise most effectively when applied by developers with solid fundamentals. They expose developers to new languages/frameworks but also risk Dunning-Kruger: "AI can lead to Dunning-Kruger on steroids." Recommendation: continue periodic coding without AI to maintain raw skills.

> "AI rewards existing best practices."

### On Autonomy Level
New CLI tools (Claude Code, Codex CLI, Gemini CLI) are "semi-supervised" — direct chat in project directories. Async agents (Jules, GitHub Copilot Agent) work on cloud VMs, can run tests and open PRs — but still require specs and plans to stay focused. Neither is fully autonomous.

Osmani notes ~90% of Claude Code's own source is now written by Claude Code itself — but emphasizes this required the disciplined harness, not vibe coding.

### Verbatim Quotes

1. "Planning first forces you and the AI onto the same page."
2. "Don't make the AI operate on partial information."
3. "We're not at the stage of letting an AI agent code an entire feature unattended."
4. "The LLM is an assistant, not an autonomously reliable coder. I am the senior dev."
5. "AI can lead to Dunning-Kruger on steroids."
6. "An AI-friendly workflow is one with strong automation."
7. "AI coding assistants are incredible force multipliers, but the human engineer remains the director of the show."
8. "AI rewards existing best practices."

---

## VERSO RELEVANCE

### [SHARPENS §5.2 — Context Engineering] Spec.md as the highest-leverage context artifact
Osmani's "waterfall in 15 minutes" pattern (spec.md → project plan → chunks) is a specific, concrete instance of context engineering discipline. Verso's ContextBundle / context-engineering layer should have an idiom for this: a spec-first bootstrap that pre-populates the RunContext with a structured task decomposition. Currently Verso's context-engineering primitives are more granular (prefix discipline, observation masking, retrieval). The spec-as-context-root pattern is a higher-altitude abstraction worth formalizing: the spec.md *is* the static prefix; the task chunks become the dynamic append-only history.

**Verdict:** sharpen — §5.2 should include a "task spec as static context prefix" idiom alongside the existing KV-cache discipline.

### [CONFIRMS §5.3 — Tools] CLAUDE.md / rule files confirm the @tool-path discipline
Osmani's CLAUDE.md pattern is exactly Verso's native Python @tool path applied at the session level: a file that provides persistent instructions, preferred approaches, and examples. This is not incidental — it's evidence that the @tool (function-annotation) approach is the natural grain of how practitioners structure their agent interactions. The more important implication: Verso's @tool decorator should be as easy to write as a markdown rule file. If @tool requires more ceremony than writing a CLAUDE.md section, it will lose to informal prompt hacking.

**Verdict:** confirm — but use to sharpen the ergonomics invariant: @tool must be lower-friction than a markdown rule file.

### [SHARPENS §6.3 — Safety/Hooks] "Finish task, run tests, commit" as a natural hook cadence
Osmani's ultra-granular commit discipline ("Finish task, run tests, commit") maps naturally to Verso's durable checkpoint cadence. The hook fires at task completion (not at every tool call), tests verify the state is good, and a checkpoint is saved. This is exactly the durable runtime promotion pattern: the human operator's "commit" is the checkpoint event. Verso's checkpoint mechanism should expose a natural hook point at task completion, not just at fixed N-step intervals.

**Verdict:** sharpen — §6.1 checkpoint design: checkpoint events should align with semantic task boundaries (task complete + tests pass), not just step count.

### [SHARPENS §5.5 — Evals] Cross-model review as standard eval practice
Osmani's cross-model review idiom (Claude writes, Gemini critiques) is an informal version of Verso's judge-panel eval. The fact that a Google engineer is manually doing this as a workflow discipline validates the judge-panel approach — practitioners already understand the value. Verso's evals should make this pattern zero-friction: `verso eval --judge-model gemini-2.0` should be a one-liner, not a bespoke setup.

**Verdict:** sharpen — §5.5 eval interface should expose `--judge-model` as a first-class CLI parameter to make the cross-model review pattern trivial.

### [CONFIRMS §1 — The Bet] "~90% of Claude Code source written by Claude Code" validates the horizon trajectory
The ~90% self-authoring statistic, if accurate, is evidence that the task-horizon curve is real and already bending toward long-horizon agentic capability. Osmani is not extrapolating — he is describing current practice at a Google/Anthropic-scale project. This directly confirms Verso's §1 bet that the horizon is extending and that frameworks must be designed for longer-horizon tasks now.

**Verdict:** confirm — cite as practitioner evidence (not research paper) for the bet.

### [NEW-IDEA §5.2 — Context Engineering] "Gitingest / repo2txt" as context bundling tooling gap
Osmani mentions gitingest and repo2txt as tools for bundling code sections for ingestion. The existence of these tools implies that current agent frameworks (including Claude Code itself) do not handle repo-scale context bundling automatically. Verso's ContextBundle inspect() interface could expose a `from_repo()` constructor that automatically selects relevant files, respects token budget constraints, and applies static/dynamic prefix discipline — making gitingest-style bundling a first-class operation rather than a manual preprocessing step.

**Verdict:** new-idea — add `ContextBundle.from_repo(path, budget)` as a named interface to lock (implementation deferred) in §5.2.

### [CONTRADICTS §2 — Non-Goals] Gemini preference is a warning about monoculture
Osmani explicitly states he gravitates toward Gemini for "most coding work" — this from a Google engineer, but still notable: the market is not monolithic. Verso's model provider abstraction (§6.4) must be practically multi-provider, not theoretically multi-provider. If Verso's canonical examples and documentation all use Anthropic/Claude, practitioners who prefer Gemini or OpenAI will route around the framework. The non-goal of being model-specific must be actively maintained in docs and examples, not just in the architecture.

**Verdict:** sharpen — §6.4 and all README examples should show at least two providers in canonical usage, with Gemini and OpenAI as explicit first-class citizens alongside Claude.
