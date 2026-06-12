# Cluster 1 — Harness Craft (raw recheck)

**Date:** 2026-06-12
**Method:** Full-text WebFetch of 4 frontier essays (2 passes each on the two Anthropic + Ronacher MUST sources to confirm verbatim quotes and hunt contradictions). All 4 URLs reachable.
**Lens:** What CONFIRMS / CONTRADICTS / SHARPENS / ADDS to Verso's PRD (`docs/PRD_v1.md`). Deltas only — re-confirmations of the "already known" harvest are noted in one line and skipped.

PRD section legend: §4 seam/arch · §5.1 loop · §5.2 context · §5.3 tools · §5.4 memory · §5.5 evals · §6.1 durable · §6.2 multi-agent · §6.3 safety · §6.4 model.

---

## Source 1 — Anthropic, "Effective harnesses for long-running agents"
URL: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

This piece is about agents that must work **across many context windows / discrete sessions**, where "each new session begins with no memory of what came before." It is the single most Verso-relevant of the four because the "harness" it describes is almost exactly Verso's §6.1 durable layer + §5.2 compaction, but built out of *files + git* rather than an event log. That divergence is the high-value finding.

### Load-bearing specifics

**1. Feature-list-as-executable-spec the agent may TOGGLE but not EDIT. [NEW-IDEA → §5.5 / §6.1]**
> "We prompted the initializer agent to write a comprehensive file of feature requirements expanding on the user's initial prompt."
> "We prompt coding agents to edit this file only by changing the status of a `passes` field, and we use strongly-worded instructions like 'It is unacceptable to remove or edit tests because this could lead to missing or buggy functionality.'"

Format is JSON rows with a boolean gate:
```json
{ "category": "functional",
  "description": "New chat button creates a fresh conversation",
  "passes": false }
```
Scale: the claude.ai-clone example had **"over 200 features."** Failure-mode it fixes (verbatim table): *"Claude declares victory on the entire project too early" → "Set up a feature list file."*

This is a **write-protected acceptance checklist** that doubles as durable progress state. It is NOT the same as Verso's `eval.unit()` (which runs in CI, off the hot path). It is an *in-loop, in-context* success ledger the agent reads to know what's left and writes (one field only) to record progress. It is closer to `done(result)`'s "optional verification checklist" (§5.3) than to anything else in the PRD.

**2. Git-as-state-machine for recovery. [NEW-IDEA → §6.1]**
> "This allowed the model to use git to revert bad code changes and recover working states of the code base."
The initializer creates "an initial git commit that shows what files were added"; every session is told to "commit its progress to git with descriptive commit messages." Failure-mode fixed: *"Claude leaves the environment in a state with bugs" → "An initial git repo and progress notes file is written."*

This is a **second, orthogonal checkpoint substrate** to Verso's event-sourced durable runtime. Verso checkpoints *loop state* (steps, tool results) for crash-resume. Anthropic checkpoints *workspace state* (the filesystem) for semantic recovery — "revert to last working commit." These are different axes; Verso has nothing for the second.

**3. Progress file as memory across context windows. [SHARPENS §5.2 / §5.4]**
> "an `init.sh` script, a `claude-progress.txt` file that keeps a log of what agents have done, and an initial git commit"
Session start: *"Read the git logs and progress files to get up to speed on what was recently worked on."* Session end: *"End the session by writing a git commit and progress update."* The key insight verbatim:
> "The key insight here was finding a way for agents to quickly understand the state of work when starting with a fresh context window, which is accomplished with the `claude-progress.txt` file alongside the git history."

This sharpens Verso's compaction story. Verso's structured handoff (§5.2: "goal / done / files / failed-and-why / next / constraints") is exactly a progress file — but the PRD frames it as an *in-process compaction artifact*. Anthropic frames it as a **durable on-disk file that survives a full process death and is re-read at the next session's cold start.** The handoff schema should be persisted, not just held in the next bundle.

**4. Compaction alone is INSUFFICIENT for long horizons. [CONTRADICTS / SHARPENS §5.2]**
> "However, compaction isn't sufficient. Out of the box, even a frontier coding model like Opus 4.5 running on the Claude Agent SDK in a loop across multiple context windows will fall short of building a production-quality web app if it's only given a high-level prompt."

Verso's §5.2 leans hard on observation-masking + summarize-and-replace as the compaction answer. This is a direct counterweight: for **multi-session** horizons, in-context compaction (the thing Verso ships) is necessary-but-not-sufficient — you also need **externalized, structured, re-readable state** (spec file + progress file + git). Compaction keeps *one* session coherent; it does not carry a task across a cold start. Verso's compaction is a §5.2 within-run mechanism; this is a §6.1 across-run mechanism, and the PRD currently blurs them.

**5. Self-verification must be forced, not assumed. [CONFIRMS §5.2/§5.3 anti-hallucination, SHARPENS]**
> "One final major failure mode that we observed was Claude's tendency to mark a feature as complete without proper testing."
> Instruction: "Self-verify all features. Only mark features as 'passing' after careful testing."
Confirms Verso's existing "only mark done on explicit confirmation" anti-hallucination rule (§5.2 compaction handoff) — but extends it from compaction to the **completion gate** itself. The `passes: false → true` flip is the architectural enforcement (the model can't claim done without editing the one allowed field, and is told testing is the precondition).

**Dual initializer/worker split. [maps §4 / §6.2 — but explicitly NOT a real multi-agent split]**
> "an initializer agent that sets up the environment on the first run" + "a coding agent that is tasked with making incremental progress in every session."
Critical footnote (verbatim):
> "We refer to these as separate agents in this context only because they have different initial user prompts. The system prompt, set of tools, and overall agent harness was otherwise identical."

This strongly **CONFIRMS Verso's §6.2 stance** ("sub-agent = context isolation, not org-chart role-play"): even Anthropic's "two agents" are *one harness with two entry prompts*, not two orgs. It also maps to Verso's seam idea — same loop, different *invocation*. Worth quoting in positioning: the frontier "multi-agent" example is just one agent invoked twice.

### No-overkill filter
- Feature-spec file + progress file: **earns its place** as a thin, optional, durable-layer primitive — but only at the long-horizon end (Phase 2/3). For a tactical single-session agent it is pure overhead. Ship as an *opt-in durable convention*, not a core type.
- Git-as-recovery: **resist as a core primitive.** It's coding-agent-specific (assumes a git workspace). The *generalization* that earns a place is "the durable runtime should support a user-supplied semantic checkpoint/rollback hook," not "Verso shells out to git."
- "Compaction isn't sufficient": **not a primitive, a doc/PRD correction.** Costs nothing, prevents over-claiming.

---

## Source 2 — Armin Ronacher, "Agent Design Is Still Hard"
URL: https://lucumr.pocoo.org/2025/11/21/agents-are-hard/

Ronacher (Flask) built a production agent and reports what's hard. He is the closest thing to an adversarial witness for Verso's whole thesis, because he says the loop is easy **and** that the framework abstraction is a trap — which is Verso's bet — but he also names the one thing Verso calls its wedge (evals) as the part nobody has solved.

### Load-bearing specifics

**1. Skip high-level SDKs because model differences force your own abstraction. [CONFIRMS §1 thesis / §6.4 — strongly]**
> "The differences between models are significant enough that you will need to build your own agent abstraction."
> "with some of these higher-level SDKs you have to build on top of their existing abstractions, which might not be the ones you actually want in the end."
> On the Vercel AI SDK: "At this point we would not make that choice again."
> "the right abstraction is not yet clear, using the original SDKs from the dedicated platforms keeps you fully in control."

This is independent external confirmation of Verso's §2 non-goals ("not an SDK") and §6.4 (`ProviderProfile` thin abstraction over raw provider SDKs, OpenAI shape canonical, everything else a translation). Quote-worthy for the launch POV. **But note the double edge:** "the right abstraction is not yet clear" is also an argument *against shipping Verso's abstraction as settled* — which the PRD already internalizes (§2: "find the abstraction cursor by use, not on paper"; dogfood-first). Confirms the humility posture, not just the thesis.

**2. Reinforce the objective on EVERY tool return. [SHARPENS §5.2 / §5.3 — actionable, NEW mechanism]**
> "Every time the agent runs a tool you have the opportunity to not just return data that the tool produces, but also to feed more information back into the loop."
Examples he gives: re-inject "the overall objective and the status of individual tasks," and on failure "hints about how the tool call might succeed." And the self-reinforcement observation:
> the "todo write tool is a self-reinforcement tool ... basically just an echo tool; it really doesn't do anything else. But that is enough to drive the agent forward."

Verso already has the *channel* for this — `{data, error, ok}` with model-legible error hints (§5.3) and `RunContext` (§5.2). What's NEW is the **principle that the tool-result envelope is a re-prompting surface, not just a data return**: objective + task-status should be (optionally) re-stated on every observation, not just in the system prefix. This is in mild tension with KV-cache discipline (§5.2) — re-stating the objective in the *suffix* on each turn is fine (suffix is dynamic), but it must not touch the cached prefix. Verso could expose this as an opt-in hook (`post_tool` already exists, §6.3) that appends a reinforcement block to the observation. The `think`/`done` builtins (already known) are the same family as his "todo echo tool" → confirms those.

**3. Manual/explicit cache control beats automatic. [SHARPENS §5.2 KV-cache]**
> "I initially found the manual management pretty dumb. Why doesn't the platform do this for me? But I've fully come around and now vastly prefer explicit cache management."
> "One cache point is after the system prompt. Two cache points are placed at the beginning of the conversation, where the last one moves up with the tail of the conversation."
He keeps system prompt + tool selection "mostly static" and feeds "a dynamic message later to provide information such as the current time."

Verso's §5.2 already mandates static prefix / dynamic suffix and "prevents accidental cache breaks (e.g. timestamps in the system prompt)." This SHARPENS the *mechanism*: it's not just "don't break the prefix" — it's **explicit, named cache breakpoints**, and specifically a *moving* breakpoint that "moves up with the tail of the conversation." Verso's KV-cache discipline should model cache breakpoints as first-class (one after the static prefix; a trailing one that advances with history), not just enforce prefix immutability. The "current time as a separate dynamic message" trick is the concrete pattern behind the PRD's abstract warning.

**4. Isolate failures in throwaway sub-agents that report only the outcome. [CONFIRMS §6.2, SHARPENS]**
> "run tasks that might require iteration individually ... until they succeed and only report back the success, plus maybe a brief summary of approaches that did not work."
Plus a context-editing variant: "you can take out of the context certain failures that didn't drive towards successful completion" to "preserve tokens for further down the iteration loop."

CONFIRMS Verso's §6.2 "sub-agent returns a typed compact summary (file names + line numbers, not raw content)" and the "no parent-history inheritance" default. SHARPENS it with a specific payload spec: **report success + a brief summary of what did NOT work.** Verso's sub-agent summary type should have a slot for "approaches that failed" (cheap, high-value for the parent's next decision), not just the positive result. The "context editing to remove dead-end failures" is an alternative to spawning a sub-agent — same goal (keep failures out of the durable window). Verso's observation-masking compaction (N=10) already achieves much of this passively; his is an *active* targeted excision.

**5. Evals/testing is THE unsolved hard problem. [CONTRADICTS §5.5 confidence — HIGH VALUE]**
> "We find testing and evals to be the hardest problem here ... the agentic nature makes it even harder."
> "at the moment we haven't found something that really makes us happy."

This is the most important challenge in the cluster to Verso's plan. Verso bets evals are **the wedge** (§5.5) — "first-class, in the box." Ronacher, shipping a real agent, says evals are the hardest *unsolved* problem and he has nothing he's happy with. Two readings, both load-bearing:
  (a) **Confirms the wedge is real** — if a builder of Ronacher's caliber can't get evals right, a framework that ships a credible eval primitive is solving a genuine top-tier pain, not a manufactured one.
  (b) **Warns the wedge is hard to land** — "first-class evals in the box" is easy to *claim* and hard to make *good*; the §13 decision to COMPOSE the eval engine (Langfuse + autoevals + Braintrust) rather than build it is the right hedge, and this quote is the external evidence that owning it from scratch in v1 would be over-reach. The "agentic nature makes it even harder" specifically points at *trajectory/multi-step* eval (not single-turn scoring) — which is exactly where Verso's `define_outcome` (bounded generate→grade→revise) and per-step-vs-end-to-end pass rates (§5.5) live. Verso should treat **agentic trajectory eval as the explicit hard frontier**, not assume the three-tier API closes it.

**6. Shared virtual file system to avoid tool "dead ends." [NEW-IDEA → §5.3 / §6.2]**
> "there needs to be a system that allows the image generation tool to write the image to the same place where the code execution tool can read it. In essence, that's a file system."
He warns against tools that "only continue executing within the sub-tool that you built" (dead ends); `ExecuteCode` and `RunInference` must "have access to the same file system."

This is a **gap in Verso's tool model.** §5.3 tools return `{data, error, ok}` — a pure return-value model. Ronacher's point: multi-modal / multi-tool agents need a **shared scratch substrate** (a filesystem-like blob store) so tool A's output is addressable by tool B without round-tripping through the (token-expensive, often binary-hostile) context window. This rhymes with §5.2's "just-in-time retrieval with lightweight identifiers" (already known) — the file path IS the lightweight identifier — but Verso has no *write* side: nowhere for a tool to *put* a large/binary artifact and hand back a reference. Worth a `ctx.workspace` / artifact-store concept (could be the same on-disk dir that the durable layer and the progress file already imply).

### No-overkill filter
- Reinforce-objective-on-tool-return: **earns its place** as an opt-in `post_tool` reinforcement hook (Verso already has the hook stage; this is a documented pattern + maybe a tiny helper). No new core type.
- Explicit moving cache breakpoint: **earns its place** — it's a refinement of an existing first-class concern (KV-cache), and it's mechanically necessary to actually realize the "~10× cost" claim Verso already makes. Promote cache breakpoints from "prevented footgun" to "named, positioned object."
- "Failed approaches" slot in sub-agent summary: **earns its place** — one field, high signal.
- Shared workspace/artifact store: **earns its place, but scope-gate it.** It's genuinely needed for multimodal/code-exec agents (Phase 3 territory — sandbox, Code Mode), not for the Phase-0 text+tool core. Lock the `ctx.workspace` concept; build when a dogfood agent needs to pass a blob between tools.
- Evals-are-hard: **a PRD risk annotation**, not a primitive. Validates COMPOSE-don't-build (§13) and flags trajectory eval as the open problem.

---

## Source 3 — Thorsten Ball, "How to Build an Agent" (Amp / Sourcegraph)
URL: https://ampcode.com/notes/how-to-build-an-agent

The canonical "the loop is tiny" essay. Almost everything here **CONFIRMS** Verso's core thesis; the deltas are (a) the precise numbers to cite, and (b) one subtle tool-schema detail.

### Load-bearing specifics

**1. Agent = model + loop + tools, and it's small. [CONFIRMS §1 / §5.1 — the thesis, with citable numbers]**
> "It's not that hard to build a fully functioning, code-editing agent."
> "It's an LLM, a loop, and enough tokens."
> "It seems like it would be. When you look at an agent editing files, running commands, wriggling itself out of errors, retrying different strategies - it seems like there has to be a secret behind it. There isn't."
Volume: "less than 400 lines of code, most of which is boilerplate"; three tools — `read_file`, `list_files`, `edit_file`.

This is the cleanest external citation for Verso's "the loop is 5–10 lines and is not where anyone competes" (§1) and the <200-line loop invariant (§4). NOTE: Verso's harvest currently cites "~315 lines of Go"; the essay's own phrasing is **"less than 400 lines of code, most of which is boilerplate."** Use the author's exact number ("less than 400 lines") to avoid a misquote in launch material. The three-tools-and-it-just-works framing is the W1 side-by-side demo (§12) in someone else's words.

**2. What's hard lives OUTSIDE the loop = "elbow grease." [CONFIRMS §1 / §4 — load-bearing for positioning]**
> "The rest, the stuff that makes Amp so addictive and impressive? Elbow grease."

This is *exactly* Verso's bet stated by an Amp engineer: the loop is trivial, the product is the harness/elbow-grease around it (UX, system prompts, feedback mechanisms, tool design, integration). Verso's §1 ("the product is the harness around it — context/cache discipline, tool design, error recovery, durable state, evals") is the *itemized* version of Ball's "elbow grease." Strongest possible third-party endorsement of the wedge. **Use verbatim.**

**3. Tool = name + description + JSON schema + handler; schema auto-generated from a struct. [CONFIRMS §5.3]**
> "When we get a message back from Claude, we check whether Claude asked us to execute a tool by looking for `content.Type == "tool_use"` … if so we hand over to `executeTool`, lookup the tool by name in our local registry, unmarshal the input, execute it, return the result."
Schema via `GenerateSchema[ReadFileInput]()` from a Go struct with `jsonschema_description` tags.

CONFIRMS Verso's `@tool` → `TypeAdapter(fn)` schema-gen (§5.3 / §10 decision 2: Pydantic v2 `TypeAdapter`). The Go `jsonschema_description` struct tag is the exact analog of Verso's "docstring + type hints → JSON schema." Local tool registry + name lookup + unmarshal + execute + return = Verso's dispatch loop. No delta beyond confirmation — but it's confirmation that Verso's chosen tool shape is the *industry-standard minimal* shape, which matters for the "no overkill" claim.

**4. The loop structure itself. [CONFIRMS §5.1]**
Read input → append to conversation → inference → branch on `text` vs `tool_use` → if tool_use, execute and append results as a new user message → loop. This is byte-for-byte Verso's §5.1 pseudo-loop (`assemble → call → if tool_calls: dispatch+append else finalize`). Pure confirmation.

### No-overkill filter
Nothing here adds a primitive — it **subtracts** justification for adding any. Ball is the "resist scaffolding" anchor: the entire essay is evidence that Verso's instinct (tiny loop, ~3 builtins, schema-from-signature, everything else in siblings) is correct. The only action item is a **factual correction**: cite "less than 400 lines" (the author's words), and keep "ship the mechanism, not the toolbox" — Ball ships exactly 3 tools and lets the model figure out the rest ("we didn't say anything about 'if a user asks you about a file, read the file' … Claude realizes that it can read the file"). That directly supports Verso's "~zero opinionated domain tools" (§5.3).

---

## Source 4 — Anthropic, "Effective context engineering for AI agents"
URL: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

Verso's §5.2 already absorbed most of this. Reporting ONLY what is sharper than the "already known" list.

### Load-bearing specifics

**1. The degradation mechanism, named and quantified. [SHARPENS §5.2 — exact citation]**
> "Context, therefore, must be treated as a finite resource with diminishing marginal returns."
> "LLMs are based on the transformer architecture, which enables every token to attend to every other token across the entire context. This results in n² pairwise relationships for n tokens."
> "as the number of tokens in the context window increases, the model's ability to accurately recall information from that context decreases" — named **"context rot."**
> Also: "LLMs have an 'attention budget'" and "Models develop their attention patterns from training data distributions where shorter sequences are typically more common than longer ones."

Verso's §5.2 asserts "degradation as a gradient from n² attention" as motivation. This gives the **exact source phrasing + the named phenomenon ("context rot") + the second cause (training-distribution mismatch toward shorter sequences)** that the harvest didn't have verbatim. Use "context rot" and "attention budget" as the named concepts in Verso's docs/`inspect()` rationale. The training-distribution cause is genuinely additive: it means the problem isn't *only* compute (n²) — even with infinite compute the model is *worse* at long contexts because it rarely trained on them. That strengthens the case for aggressive compaction over "just use a bigger window."

**2. Sub-agent token economics, quantified. [SHARPENS §6.2 — exact numbers]**
> "Each subagent might explore extensively, using tens of thousands of tokens or more, but returns only a condensed, distilled summary of its work (often 1,000-2,000 tokens)."

Verso's §6.2 says sub-agents "return a typed compact summary" but gives no size target. This supplies the **concrete ratio: tens-of-thousands in, 1,000–2,000 out.** Verso can use 1–2K tokens as the documented default budget for a sub-agent summary, and as the threshold that makes context-isolation *worth it* (if the subtask won't burn ≫2K tokens, don't spawn — inline it). Directly informs the §6.2 "don't spawn for cheap subtasks" guidance.

**3. Compaction preserves/discards specifics. [SHARPENS §5.2]**
> "The model preserves architectural decisions, unresolved bugs, and implementation details while discarding redundant tool outputs or messages."
> Claude Code continues "with this compressed context plus the five most recently accessed files."

Verso's summarize-and-replace handoff schema (§5.2: goal/done/files/failed-and-why/next/constraints) is well-aligned, but this sharpens the **keep-list**: *architectural decisions + unresolved bugs + implementation details* are explicitly preserved; *redundant tool outputs* explicitly dropped (which is what observation-masking already does). The "+ five most recently accessed files" is the same pattern as Anthropic's harness piece ("compressed context plus the five most recently accessed files") — a recurring "keep the last N working files" heuristic. Verso's handoff `files` slot should bias to *recently-touched* files, and the compaction prompt should name the preserve-list explicitly.

**4. Just-in-time retrieval + structured note-taking + a file-based memory tool. [CONFIRMS §5.2/§5.4, minor sharpen]**
> "Agents built with the 'just in time' approach maintain lightweight identifiers (file paths, stored queries, web links, etc.) and use these references to dynamically load data into context at runtime using tools."
> "Structured note-taking, or agentic memory, is a technique where the agent regularly writes notes persisted to memory outside of the context window."
> "We released a memory tool in public beta on the Claude Developer Platform that makes it easier to store and consult information outside the context window through a file-based system."

Mostly CONFIRMS already-known JIT-retrieval + memory-as-tool-calls (§5.4). The minor sharpen: Anthropic's shipped memory is **file-based** (paths as identifiers), echoing the harness piece's progress.txt and Ronacher's virtual filesystem. **Three of the four sources independently converge on "a file/path is the right durable handle for agent memory"** — that convergence is itself the finding (see cross-cutting below).

**5. "Right altitude" for system prompts. [SHARPENS §5.2 — naming]**
> "The right altitude is the Goldilocks zone between two common failure modes. At one extreme, we see engineers hardcoding complex, brittle logic in their prompts ... At the other extreme, engineers sometimes provide vague, high-level guidance that fails to give the LLM concrete signals for desired outputs."

Verso's PRD doesn't name this. It's relevant to §5.2 (`instructions` are "readable/editable, never hidden") and to the `mode`-gate / instruction design. Low-priority but worth a one-liner in the context-engineering docs: Verso's `instructions` field should be authored at "the right altitude" — and `inspect()` is the tool that lets a user *see* whether they over- or under-specified.

### No-overkill filter
- "context rot" / "attention budget" naming: **free, adopt** as doc vocabulary (no primitive).
- 1–2K sub-agent summary budget: **adopt as a documented default/threshold** (no new type; tunes §6.2).
- Compaction preserve-list + "last 5 files": **fold into the existing compaction prompt** (no new primitive).
- "Right altitude": **doc note** tying to `inspect()`. No primitive.

---

## Cross-cutting findings (across sources)

**A. The "file/path as durable agent handle" convergence. [NEW-IDEA → §5.2 / §5.4 / §6.1]**
Three of four sources independently land on a filesystem-shaped durable substrate:
- Harness piece: `claude-progress.txt` + feature-spec JSON + git workspace.
- Ronacher: a "virtual file system" so tools share artifacts; file path = the handle.
- Context piece: "just in time ... file paths" + a "file-based" memory tool; "five most recently accessed files."
Verso currently has: an event log (durable runtime, §6.1), a typed memory store (§5.4), and lightweight-identifier JIT-retrieval as a *read* concept (§5.2). It does **not** have a unified, writable, on-disk **agent workspace** that (a) tools write blobs into and hand back paths, (b) the compaction handoff is persisted into, and (c) the durable layer can checkpoint/rollback semantically. This is the single most coherent NEW concept the cluster suggests: a `ctx.workspace` (a run-scoped directory) that unifies progress-file, artifact-store, and just-in-time-retrieval write-side. **No-overkill verdict: lock the concept now, scope the build to Phase 2/3** (it only earns weight once durable + sandbox + multimodal exist; for the Phase-0 text agent it's overhead).

**B. Compaction is a within-run mechanism; cross-session continuity is a different problem Verso under-specifies. [SHARPENS §5.2 vs §6.1 boundary]**
The harness piece's "compaction isn't sufficient" plus its progress-file solution exposes that Verso conflates two things under "compaction": (1) keeping ONE long run under budget (observation-masking N=10, summarize-and-replace) — well-covered; (2) carrying a task across a COLD START / new session — only implicitly covered by "the durable layer resumes from the event log." But resuming a 200-feature build from a raw event log is not the same as reading a 1-page progress file. Verso's structured handoff should be **persisted as a re-readable artifact** and surfaced at durable-resume, not just used as an in-process compaction step. Cheap, and closes a real gap the strongest source names explicitly.

**C. The objective must be RE-stated, not stated once. [SHARPENS §5.2/§5.3]**
Ronacher ("feed more information back into the loop ... the overall objective and the status of individual tasks" on every tool return) + the harness piece (the feature-spec is re-read every session, the agent re-derives "what's left" each time) both reject "system prompt sets the goal once." Verso's append-only/KV-cache discipline must accommodate a *dynamic-suffix* reinforcement block. Already-known `post_tool` hook is the vehicle; the PRD should explicitly bless "objective/task-status reinforcement on observation" as a supported (opt-in) pattern.

---

## Invariant check (did anything challenge a hard invariant?)
- **No graph required for tactical agents** — UNCHALLENGED. All four sources reinforce loop-only; Anthropic's "two agents" are one harness; Ronacher avoids high-level orchestration SDKs. Confirms.
- **Native `@tool` is THE path / MCP demoted** — UNCHALLENGED. Ball's struct-tag schema and Ronacher's hand-rolled tools both validate native-function tools; nobody reaches for MCP. Confirms.
- **Python-only, no Rust** — UNTOUCHED (Ball is Go but argues the opposite of "you need a fast language" — it's "boilerplate," latency-bound). Indirectly confirms the no-Rust rationale.
- **Loop < 200 lines** — CONFIRMED externally ("less than 400 lines of code, most of which is boilerplate" *including* tools and main; the loop proper is far smaller).
- **"No overkill, simplicity"** — CONFIRMED; Ball's "elbow grease" and Ronacher's "build your own abstraction" both say the value is in disciplined harness craft, not machinery.
- **The one genuine challenge: §5.5 evals as a confident wedge.** Ronacher: evals are "the hardest problem ... we haven't found something that really makes us happy." This doesn't break the invariant (evals still matter) but it **raises the bar**: it validates COMPOSE-not-build (§13) and flags *agentic trajectory eval* as an open frontier Verso must not claim to have solved.
