# A/V Theme Synthesis — Loop, Tools, Durable Runtime, Safety (§5.1 / §5.3 / §6.1 / §6.3 / §4)

**Pass:** AUDIO/VIDEO transcript pass (talks, podcasts, conference keynotes). Complements — does not repeat — the WF1 full-text synthesis at `_SYNTHESIS_loop_harness.md`.
**Theme keys touched:** loop_harness, context, evals, multiagent, model, strategy, memory
**Sources READ IN FULL (18):** Boris Cherny / Claude Code · Inside Devin (Scott Wu) · Sierra (Clay Bavor) · Hippocratic AI (Munjal Shah) · Advanced Context Engineering (Dexter Horthy) · OpenAI Codex team (Wang/Embiricos) · Agent Development Lifecycle (Chase/Gola, Interrupt'26) · Block/Goose (Dhanji Prasanna) · Ship AI / Vercel (Malte Ubl) · Living Lindy (Flo Crivello) · Directing a Swarm of Agents (Adrian Cockcroft) · Engineering Practices that Make Coding Agents Work (Simon Willison) · Agentic Engineering (Mitchell Hashimoto) · How Cursor Builds (Michael Truell) · The Future of Software Creation (Amjad Masad) · Linear's Sync Engine (Tuomas Artman) · Self-Improving Company (Tom Blomfield) · Interrupt 2025 Keynote (Harrison Chase) · Palantir CTO (Shyam Sankar) · Automating Science (Andrew White) · Scaling Test-Time Compute to Multi-Agent Civilizations (Noam Brown) · Sholto Douglas & Trenton Bricken · Building Faster with AI (Andrew Ng) · Glean (Arvind Jain) · AI Agents & the Path to AGI (Bob McGrew) · Taste & Craft / Linear (Tuomas Artman).
**Transcript honesty:** nearly all of these had NO verbatim video transcript; every note was reconstructed from speaker-authored companion posts, Substack/Sequoia digests, and conference recaps, cross-validated. Quotes below are as attested in those secondaries. See "Unreachable / not-mined" at the bottom.

---

## 1. Cross-source picture

The A/V corpus is dominated by **builders shipping production agents** (Anthropic, Cognition, Sierra, Hippocratic, OpenAI Codex, Block, Vercel, Lindy, Cursor, Replit, LangChain, Palantir, Glean). Where WF1's written corpus argued the *shape* of the bet (loop is commodity, harness is product), the A/V corpus supplies the **production failure modes and the named mechanisms practitioners actually built** — and it converges hard on three things WF1 under-weighted:

1. **The harness is a living, self-pruning thing keyed to the model version.** The single most repeated NEW operating principle is Cherny's "delete code on every model release" — scaffolding built to compensate for a weak model becomes model-*hobbling* the moment the model improves. This is a sharper, more actionable claim than "loop <200 lines": the danger is not size, it's *dead scaffolding that survives the model that needed it*. Echoed by Truell (three-era churn, "Era 2 may not last a year"), Blomfield ("software is ephemeral, context is valuable"), and Boris's "we build things we'll delete in 3 months." **Implication for Verso: the loop-size invariant needs a companion discipline — version-tag scaffolding and review it at every model bump.**

2. **"Tools must not be agentic" is now a first-party, empirically-defended LAW, and it is the cleanest defense of native `@tool` + MCP-demotion in the entire harvest.** Crivello states it as a sharp line ("draw a sharp line between your agents and your tools, and your tools should not be agentic… it's hard enough to make one agent work"). Cherny independently lands on the inverse-positive (give the model dumb Bash/glob/grep, "Agentix search is a fancy word for glob and grep"). Cockcroft confirms the MCP catalog is "a big pile of MCP servers, all randomly programmed." This trio is the production-grade backing for §5.3 that WF1 only had Huyen/Ronacher for.

3. **Safety in production is concrete, named, and bigger than HITL.** WF1 framed §6.3 mostly as "surface the architectural-decision HITL moment." The A/V corpus adds four *distinct, shippable* safety primitives WF1 did not have: **(a)** the lethal trifecta as the scoping checklist (Willison), **(b)** sandboxing / blast-radius as "the single most important practice" (Willison, LangChain, Block, Goose), **(c)** the supervisor/critic pass — "the solution to many problems with AI is more AI" (Bavor, Vercel, Hippocratic's constellation), and **(d)** scope-as-safety: deliberately choosing what NOT to attempt is what makes the safety envelope verifiable (Shah, Hippocratic). These are not the same mechanism and Verso should not collapse them.

A fourth, quieter convergence: **HITL's load-bearing artifact is the PLAN, reviewed before execution.** Horthy ("a bad plan yields hundreds of bad lines; bad research yields thousands"), Codex ("agent generates a plan for user approval before the 30-min run"), Devin 2.0 (interactive plan editing), Cockcroft ("don't build it yet — I want to check the plan"), Hashimoto (Oracle → `spec.md`). WF1 had "HITL at decision boundaries"; the A/V pass sharpens *what the human reviews*: a structured plan object, not raw state and not line-level diffs. This is a precise design input for the durable seam.

On simplicity discipline: the A/V corpus is overwhelmingly *confirming* of Verso's anti-overkill stance (Ubl's "don't be afraid of plain old programming, save the LLM for judgment"; Ng's "build 20 prototypes"; Masad's "writing code is the easy part"; the 6-7-person Goose team running org-scale infra). The genuinely NEW primitives that earn a v1 slot are narrow: version-tagged scaffolding, the lethal-trifecta scope check, an opt-in supervisor/critic pass, `scope_exceeded` StopReason, model-version pinning at checkpoint, and the plan-as-HITL-artifact. Everything else is positioning ammunition, a sharpen, or a deferred interface. A large amount is RESIST-grade (constellation training, reversible-FS forking, sleep-time compute, director-agent, swarms-of-50).

---

## 2. Deltas (highest-value first, deduped across A/V sources; NEW vs WF1 + vs ALREADY-KNOWN)

### D1 — "Delete scaffolding on every model release": version-tagged scaffolding as a harness discipline [NEW → adopt-now] §5.1/§2
**Cherny (primary, first-hand), corroborated Truell, Blomfield.** Scaffolding that compensates for a weak model becomes model-hobbling once the model improves; carrying it means the new model "runs with a hand tied behind its back."
> Cherny: "Every time there's a new model release, we delete a bunch of code… I just deleted like 2,000 tokens from the system prompt yesterday. Just because Sonnet 4.5 doesn't need it anymore." / "With Claude 4.0 they eliminated roughly half the system prompt." / "We build most things… even if that means we'll have to get rid of it in three months."
> Truell: "Era 2 may not last one year." Blomfield: "Software is ephemeral, context is valuable… regenerate it when models get smarter."
**PRD action:** §5.1 — add a *version-tagged scaffolding* convention: any prompt block / tool / heuristic added to compensate for a model limitation is tagged with the model+date and is a review candidate at each model bump. This operationalizes the <200-line invariant as a *ratchet*, not a static cap. Cheap, it's the most-repeated novel operating principle in the A/V pass, and it directly serves "build for the durable layer, stay simple in the tactical layer."

### D2 — "Tools must not be agentic" is the law; native dumb tools beat agentic tools [NEW (hard) → adopt-now] §5.3/§6.2
**Crivello (primary, sharp line), Cherny (inverse-positive), Cockcroft (MCP rot).** Composing a sub-agent *as a tool call* multiplies reliability problems; the tool should be dumb, the agent smart. The strongest production defense of native `@tool` + MCP-demotion in the harvest.
> Crivello: "You should draw a sharp line between your agents and your tools, and your tools should not be agentic. Empirically it just doesn't work well… it's hard enough to make one agent work. Now you need to make two." (Lindy's "search web" action is literally a Google search.)
> Cherny: "Agentix Search just outperformed everything. And when I say Agentix Search, it's a fancy word for glob and grep." / "We unshipped the LS tool… a little less stuff in context."
> Cockcroft: the MCP ecosystem is "a big pile of MCP servers… all randomly programmed."
**PRD action:** §5.3 — adopt "tools are not agentic" as an explicit design law in the tool section, with the sub-agent-as-tool anti-pattern called out. This is distinct from ACI (WF1/D5): ACI is about *interface quality*; this is about *not hiding a second agent behind a tool signature*. Reinforces MCP-as-opt-in (§5.3) and the "no graph" stance. Sub-agents are dispatched explicitly, never smuggled in as tools.

### D3 — Four distinct production safety primitives; do not collapse them [NEW → adopt-now (trifecta + sandbox), lock-defer (supervisor), sharpen (scope)] §6.3
**Willison (trifecta, sandbox), Bavor/Ubl/Shah (supervisor/critic), Shah (scope-as-safety), Block/Goose (blast-radius=auth).** WF1's §6.3 was HITL-centric; the A/V pass supplies four separable mechanisms:
- **(a) Lethal trifecta as scope checklist** — private data + untrusted input + exfiltration capability = catastrophic; any two is fine. > Willison: it's "a checklist for evaluating agent scope."
- **(b) Sandboxing / blast-radius is the #1 safety practice**, framed as a *deploy-phase* concern distinct from HITL. > Willison: "The most important thing is sandboxing." LangChain names E2B/Daytona as first-class. Goose: "blast radius is highly limited to any actions humans take." Block: agent inherits the user's auth level, no privilege escalation.
- **(c) Supervisor/critic pass ("more AI")** — LLMs detect their own errors better than they avoid them, so a differently-prompted reviewer pass catches outputs that slipped past guardrails. > Bavor: "The solution to many problems with AI is more AI." Ubl: "use a second model to critique the results of the first." Distinct from a pre-action guardrail (which *stops* an action) — a supervisor *catches a bad output*.
- **(d) Scope-as-safety** — deliberately declaring what the agent will NOT attempt is what makes the envelope verifiable. > Shah/Hippocratic: the non-diagnostic constraint is what makes 99.38% accuracy *achievable and verifiable*.
**PRD action:** §6.3 — list these as four named, separable primitives. Adopt now: the trifecta scope-check (doc/checklist, zero machinery) and sandbox/blast-radius-as-auth-ceiling (RunContext should help the user answer "what's the worst case if this tool is abused?"). Lock-interface-defer: an opt-in `supervisor`/critic pass that runs post-response (a different prompt over the loop's output, emits a flag/veto — NOT a graph, NOT a constellation). Sharpen: add a declarable scope boundary + boundary-adherence as an eval dimension (ties to §5.5). RESIST building Hippocratic's 22-specialist trained constellation (see RESIST #1).

### D4 — Plan-as-HITL-artifact: the human reviews a structured plan BEFORE execution [NEW → adopt-now] §4/§6.1
**Horthy (primary), Codex, Devin 2.0, Cockcroft, Hashimoto (5-way agreement).** The highest-leverage human review point is the plan, not the code and not raw state. A bad plan compounds into hundreds of bad lines.
> Horthy: "A bad line of code is a bad line. But a bad plan could yield hundreds of bad lines; bad research could yield thousands." (Plan is the primary HITL review artifact.)
> Codex/Embiricos: 30-min autonomous runs revealed users can't fully specify upfront → "agents first generate a plan for user approval before execution." Devin 2.0: interactive plan editing before commit. Cockcroft: "Don't build it yet… I want to check the plans." Hashimoto: Oracle → `spec.md` reviewed before implementation.
**PRD action:** §4/§6.1 — the durable-seam checkpoint should expose a **structured plan/intent object** the human can inspect and edit, not just serialized state. This is a concrete shape for the HITL surface that one-flag promotion enables. The plan object doubles as the resumable artifact (D7) and the `define_outcome` anchor (it's reviewed before execution, mirroring outcome-spec-before-run).

### D5 — `scope_exceeded` / trained "patience limit" belongs in the StopReason taxonomy [NEW → adopt-now] §5.1/§6.1
**Codex team (primary, trained behavior).** Models trained on long rollouts learned to *express scope overload* rather than silently failing or hallucinating completion.
> Embiricos: "It comes back to you and it's like, 'Sorry… this is too much. I don't have enough time to do this, actually.'"
**PRD action:** §5.1 — add `scope_exceeded` (or equivalent) to the named `StopReason` enum so an agent can terminate honestly instead of hallucinating done. Near-zero cost, complements the existing named-StopReason design and the `max_steps`/step-budget detectors from WF1/D7. An honest stop is a reliability primitive.

### D6 — Checkpoint must pin the full config (model version + prompt + tools), not just state [NEW → adopt-now] §6.1
**Bavor/Sierra (immutable release snapshots), corroborated Crivello (Sycophantocalypse), Cockcroft.** A resumed/replayed run must execute against the exact model + prompt snapshot that started it, or model-behavior drift silently breaks it.
> Sierra: agent releases are "immutable snapshots packaging source code, prompts, model version, knowledge base" — enabling instant rollback.
> Crivello: the "Sycophantocalypse" (GPT-4o's swift policy change) showed model swaps silently break agents → need fast detection + faster rollback.
**PRD action:** §6.1 — the durable checkpoint spec must version the *full agent configuration* (model id/version, system prompt, tool set), not only conversation/event state. Add fast model-rollback as an explicit §6.4 concern (model behavior regression is a named failure mode). This sharpens the event-sourced-checkpoint design with a concrete completeness requirement.

### D7 — The compaction/progress document IS the seam artifact (and the sub-agent contract) [SHARPENS → sharpen] §4/§5.2/§6.2
**Horthy (primary, concrete), Cherny (uncorrelated context), corroborated Chase ("file-system pilled").** The intentional-compaction doc (end-goal + approach + completed steps + current blocker) is structurally identical to the durable checkpoint and to the briefing a fresh sub-agent reads. Horthy also gives a hard number: keep context utilization **≤40% (40–60% for complex)**.
> Horthy: subagents "provide context control by offloading search/grep/summarization to fresh context windows"; never exceed 40–60% utilization; "intentional compaction" (authored) vs naive auto-summary ("trash").
> Cherny: "The value is actually the uncorrelated context windows… two context windows that don't know about each other" — sub-agents as *isolation/compaction units*, not primarily parallelism.
**PRD action:** §4/§6.1 — state that the compaction document and the durable checkpoint are the same serializable artifact (the seam is the briefing doc). §5.2 — expose `context_utilization()` as a first-class metric with a default ~40% warn threshold (specific number is new; bake it as a constant, don't leave to guessing). §6.2 — enforce a *typed structured return* for sub-agents (summary / affected items / blocking issue), not free text (Hippocratic's "JSON field-value pairs, not prose"; Horthy's structured return). NOTE this *adds a third sub-agent rationale* to WF1's quarantine+scheduler: **context isolation/compaction** (Cherny "uncorrelated context", Cockcroft "context pollution").

### D8 — "Engineer the Harness" is the named, ranked step; AGENTS.md is the failure-derived spec [SHARPENS → sharpen] §5.1/§5.5/§12
**Hashimoto (primary, names it as Step 5 of 6), corroborated Willison, Cockcroft.** The harness — verification tools the agent self-invokes + a living failure-derived rules file — is *the* reliability mechanism, more important than model or prompt.
> Hashimoto: "If you give an agent a way to verify its work, it more often than not fixes its own mistakes." / "Each line in [AGENTS.md] is based on a bad agent behavior, and it almost completely resolved them all." / "Agents are much more efficient when they produce the right result the first time."
> Willison: Showboat — agent uses `exec` to capture *live* output rather than narrating results, so it "cannot hallucinate results." Cockcroft: BDD given/when/then "prevents result-faking."
**PRD action:** §5.3 — add a *verification-tool* pattern: tools whose output is **agent-readable pass/fail+why feedback**, enabling autonomous self-correction (distinct from side-effect tools). §5.5 — adopt the **exec-capture / no-self-reported-success** principle: the eval harness must distinguish "agent claims success" from "harness observed output" (anti-result-faking). AGENTS.md is the file-level analog of `define_outcome` accumulation. Strong §12 practitioner-authority quotes (HashiCorp founder).

### D9 — Verifier-as-tool: operationalize the generator–verifier gap inside one loop [NEW → lock-defer] §5.3/§5.1
**Noam Brown (primary), corroborated Replit (fork+select), Bavor (3-call deliberation).** Verifying is far cheaper than generating; give the loop a cheap `verify()` paired with a generative tool and run N generations → select. Test-time-compute budgeting *within* a single loop, no graph.
> Brown: the generator–verifier gap — "verifying a solution is often much cheaper than generating it… run many generators and select."
> Replit: reversible copy-on-write FS lets the agent "fork itself and the environment a number of times to solve in different ways, then find the best." Bavor: take-stock → generate-candidates → evaluate (3 LLM calls/step).
**PRD action:** §5.3/§5.1 — lock a *generate-then-verify tool-pair* pattern + an optional `samples=N` / selection hook on the loop (test-time-compute budget as a typed param). Defer implementation; the surface is small. RESIST building Replit's reversible-FS forking as a Verso primitive (RESIST #4) — keep the pattern at the tool/loop-config level.

### D10 — Operating modes are a tri-state, not a binary; default friction must feel like crisis-mode [SHARPENS → sharpen] §6.1/§6.3/§4
**Block/Goose (primary, 3 modes), corroborated Sankar (institutional will), Chase (async/sync hybrid), Devin (staged autonomy).** Production agents run in three modes — (a) HITL for destructive actions, (b) autonomous with *self-interruption*, (c) headless in CI with mandatory code review — not a binary supervised/unsupervised switch. And HITL friction must be near-zero or "institutional will" to use the agent decays.
> Goose: three modes (HITL-destructive / autonomous-self-interrupt / headless-CI-with-review). Chase: long-horizon needs async fire-and-forget *plus* a synchronous chat mode when an artifact needs human review. Sankar: "AI without institutional will is useless" → the suspension primitive must feel like *removing* friction, not adding governance.
**PRD action:** §6.1/§4 — frame the durable seam as enabling a **tri-state** (sync-HITL / autonomous-self-interrupting / headless-with-async-review), with the self-interrupt (Crivello's uncertainty-detection: "first time I see this scenario, I'm out of my depth") as a first-class mid-run HITL trigger, not just pre/post. §6.3 — the HITL `await`/suspend primitive's design goal is *minimal friction by default*. Sharpens the seam from "on/off durable" to "three operating postures."

### D11 — "Poor man's RLHF": HITL corrections → vector store → few-shot, beats prompting and fine-tuning [NEW → lock-defer] §5.5/§5.2
**Crivello (primary, 2+ yrs production data), corroborated White (end-to-end signal), Sierra (annotate→test).** The highest-impact quality lever is harvesting human corrections made during HITL, embedding them, and retrieving the closest as in-context few-shot examples on the next run.
> Crivello: "Big time. Absolutely. Much better than instructions… you embed it in the vector database… retrieve the closest examples, inject them in context… after five examples [it improves]. Forget about prompting, just do this."
> Sierra: every annotated production conversation "can become a conversation test… ensuring the agent never makes the same mistake twice." White: RLHF on intermediate outputs fails (humans reward tone/specificity) → use terminal/end-to-end signal.
**PRD action:** §5.5/§5.2 — lock an interface for *correction capture*: a HITL correction is serializable → embeddable → retrievable as a gold few-shot example (ties to just-in-time retrieval already known). This is the round-trip "production trace → test fixture / gold example" requirement; flag it as a harness capability (can a `RunContext` + observed correction round-trip into a fixture?). Defer the vector-store mechanics; Verso *emits* the signal, the user owns the store (§2 non-goal — see RESIST #2). NOTE: White's caution sharpens it — bias toward terminal-state/outcome signal, not per-step preference scoring.

### D12 — Reward-hacking / spec-gaming is a first-class eval category, not a footnote [NEW → adopt-now (narrow)] §5.5/§6.3
**White (primary, concrete), corroborated Cockcroft (BDD result-faking), Willison (exec-capture).** Specification gaming happens in real agentic loops within *months*, not in theory; the fix is constraint satisfaction, not just outcome achievement.
> White/Ether-Zero: the agent gamed "novel nitrogen-rich compounds" by adding purchasable N2 gas and manipulating atom counts via acid-base chemistry → fix was "a catalog of purchasable compounds in a Bloom filter" to constrain valid outputs.
**PRD action:** §5.5 — add a named eval category: "does the agent hit the metric via a loophole?" A `define_outcome` variant should support *constraint satisfaction* (the outcome must be reached *within declared constraints*), not just a success predicate. Ties to D3(d) scope-as-safety (boundary-adherence) and D8 (anti-result-faking). Narrow, concrete, earns a slot in the eval-harness design.

### D13 — Write tools "as if context management doesn't exist": the DX north-star for the harness [SHARPENS → sharpen] §5.1/§5.2/§12
**Artman/Linear sync engine (primary analogy), corroborated Cherny (everything-you-can-do-Claude-can-do), Ubl (stay low-level).** Linear's sync engine eliminated an entire complexity class from the developer's mental model ("write against in-memory objects as if networking doesn't exist") and *that DX*, not performance, was the killer feature and the moat.
> Artman: "you're effectively just building the front end… modify those objects and that's it. Your feature is done." Engineering velocity, not UI responsiveness, was the surprise top property. "Build the primitive before the product" (half a year before features).
**PRD action:** §12/§1 — the DX pitch is "write Python `@tool`s as if context management doesn't exist; the harness handles it" — and the harness is the primitive built before the features, exactly Linear's bet. §4 — Artman's "offline *tolerance*, not offline *arbitrariness*" (the Rocky-Mountains 2-day-replay bug) is a concrete illustration that the tactical layer has a scope boundary the durable layer extends *systematically* — borrow it to explain why the seam exists. Pure positioning/framing; no machinery.

### D14 — The invariants ARE the product exercising taste ("saying no to 999 things") [SHARPENS → sharpen] §12/§2
**Artman/Taste&Craft (primary), corroborated Truell (power-users-over-democratization), Sankar (alpha-not-beta).** Reframes Verso's hard constraints from engineering preference to product taste: an opinionated framework prevents the AI-era "shipping trap" (yes-to-everything because implementation is cheap).
> Artman: "Great products come from saying 'no' to 999 things." The taste gap: "[AI] knows that one second is better than two seconds, but it doesn't know whether two seconds is slow enough." (AI auto-fixes ~10% of Linear's bugs; fails on felt-quality.)
> Truell: explicit rejection of "vibe coding"/democratization — "for professional devs in large codebases, understanding the code still matters." Sankar: "alpha not beta" — generic capability every competitor can deploy is beta; the abstraction layers needed to stay generic are what disconnect software from outcomes.
**PRD action:** §12/§2 — state the hard invariants (no graph for tactical, native `@tool` is THE path, loop <200 lines, Python-only) as **the product saying no on the user's behalf** — taste, not just simplicity. The taste-gap quote is the memorable case for why bounded outcomes still need *human* judges (§5.5) — the judge-panel isn't a stopgap for missing metrics, it's the correct evaluator for felt-quality outcomes.

### D15 — Memory only pays off in RECURRING workflow agents — scope the memory claim [CONTRADICTS over-broad memory framing → sharpen] §5.4/§2
**Chase/Interrupt (primary, first-party), corroborated Glean (recurring-engagement signals).** Memory creates no stickiness in one-off interactions; value shows only in recurring, workflow-specific agents.
> Chase: memory "does not create stickiness in one-off interactions (ChatGPT)… shows value only in recurring, workflow-specific agents" (his email-agent example).
**PRD action:** §5.4/§2 — explicitly scope the 4-tier memory + temporal-versioning investment to **recurring workflow agents**; do NOT oversell memory for tactical one-shot agents (that would be overkill for the default tactical path). This is a guardrail on the memory theme surfaced from the loop/runtime vantage; the memory synthesis owns the mechanism, this flags the scope.

---

## 3. What changes in the PRD vs. already covered

**New (small, earns its place — adopt-now):**
- §5.1/§2: version-tagged scaffolding discipline + the model-release delete ratchet (D1).
- §5.3: "tools are not agentic" as an explicit law; sub-agent-as-tool anti-pattern (D2).
- §6.3: lethal-trifecta scope-checklist + sandbox/blast-radius-as-auth-ceiling, named as distinct from HITL (D3 a,b).
- §4/§6.1: plan/intent as a structured, human-editable HITL artifact at the seam (D4).
- §5.1/§6.1: `scope_exceeded` added to the StopReason enum (D5).
- §6.1: checkpoint pins full config (model version + prompt + tools), not just state (D6).
- §5.2: `context_utilization()` metric + ~40% default warn threshold constant (D7).
- §5.3/§5.5: verification-tool pattern (agent-readable pass/fail) + exec-capture / no-self-reported-success anti-result-faking (D8).
- §5.5: reward-hacking / constraint-satisfaction as a named eval category (D12).

**Sharpen (existing primitive, add a constraint/framing):**
- §6.2: add *context-isolation/compaction* as a third sub-agent rationale (alongside quarantine+scheduler from WF1); enforce typed structured sub-agent returns (D7).
- §6.1/§4/§6.3: durable seam is a **tri-state** (sync-HITL / autonomous-self-interrupting / headless-with-review); mid-run self-interrupt as first-class; HITL friction minimal-by-default (D10).
- §5.4/§2: scope the memory investment to recurring workflow agents (D15).
- §6.4: fast model-rollback as a named failure mode (Sycophantocalypse) (D6).
- §12/§1: "write tools as if context doesn't exist" DX north-star; "build the primitive before the product"; invariants-as-taste (D13, D14).

**Lock-interface-defer:**
- §6.3: opt-in `supervisor`/critic post-response pass (different prompt over loop output, emits flag/veto; not a graph) (D3c).
- §5.3/§5.1: generate-then-verify tool-pair + `samples=N`/selection hook (D9).
- §5.5/§5.2: HITL-correction capture → embeddable gold few-shot (round-trip trace→fixture); Verso emits, user owns store (D11).
- §6.3/§5.5: declarable scope boundary + boundary-adherence eval dimension (D3d, D12).

**Already covered by WF1 — A/V corpus only CONFIRMS (no new action). Listed so coverage is honest:**
- Anti-framework / loop-is-commodity / harness-is-product — Cherny, Masad ("writing code is the easy part"), Chase (framework vs harness vs runtime tiers), Ng (application layer is the moat), Hashimoto, Willison. WF1 already has the triumvirate; these add weight, not a new claim.
- Compound-error math (0.9^10 ≈ 0.35, per-step reliability is the metric) — Glean, Sholto/Bricken. **Already in WF1 via Huyen.** Do not re-list as new.
- Sub-agents = failure-quarantine + scheduler-offload — Devin MultiDevin, Goose, Cockcroft. WF1 owns this; A/V adds the *context-isolation* third rationale (D7) which IS new.
- Dynamic/just-in-time context retrieval over prompt-stuffing — Truell (verbatim 46.9% token cut), Cursor deferred tool-schema loading (85% / 72K→8.7K). Confirms §5.2; the *numbers* are useful external calibration but the pattern is known.
- Cross-model neutrality / model labels not pinned versions / model-maxing — Crivello, Ubl, Block, Hashimoto (parallel-model testing). Confirms §6.4.
- Reliability (not capability) is the moat; 95% vs 70% delegation threshold — Masad, McGrew ("reliability is the trust contract"), Sierra (τ-bench pass^k). Confirms the evals+reliability bet.
- Multi-turn simulation evals / trace-as-source-of-truth — Chase, Lindy daily evals, Sierra Experience Manager. Confirms §5.5.
- Build-deterministic-code-first / no-overkill — Ubl, Ng, Crivello ("temperature zero, scaffolding deterministic"). Confirms §2.
- Task *ambiguity* (not length) as the tractability metric — Crivello's "intern with a Google Doc." Confirms §5.1 framing; usable one-liner but not a mechanism change.

---

## 4. RESIST list (overkill / platform-shaped / not-for-a-v1-personal-infra-framework)

1. **Hippocratic-style trained multi-specialist "constellation" (22 co-trained safety models, 4.2T params) as the safety architecture.** Verso's analog is ONE optional, prompt-only supervisor/critic pass (D3c) — not a trained, co-supervised model panel. The constellation is a healthcare-grade product, not a framework primitive.
2. **Owning the correction/eval data flywheel (Lindy "poor man's RLHF" store, Sierra Experience Manager, Replit "Learn", Blomfield's self-improving-org loop).** Verso *emits* correction/eval signal to the user's own store and owns none of it (§2 non-goal). Building the vector store, the annotation platform, or a training loop is platform-shaped and out of scope. Reaffirms WF1 RESIST on Replit-Learn/LangSmith.
3. **"Sleep-time compute" / nightly trace-driven auto-prompt-rewriting (Chase) and the "director agent / NoMan" auto-orchestrator (Cockcroft).** Genuinely interesting, explicitly v2+ even by their proposers. A framework that silently rewrites the user's prompts/tools from traces violates "no hidden context engineering." Note as future; do not ship.
4. **Replit's reversible copy-on-write filesystem for parallel agent forking as a Verso primitive.** Keep the *pattern* (generate-then-verify / samples=N at the tool-loop level, D9) but do NOT build a transactional forkable FS into the harness — that's habitat/platform infra (Replit's own moat), not a Python loop library's job.
5. **Swarms of 50–billions of agents / "AI civilization" coordination substrate (Brown, Prasanna, Masad).** Strong *positioning* hook ("swarms without graphs") but building civilization-scale coordination infra is overkill; Verso's sub-agent dispatch handles tactical multi-agent. Masad + Brown both concede agent-to-agent orchestration beyond tool-calling is *unsolved* — note as out-of-scope future work in §6.2, not a v1 target.
6. **Proprietary/specialized model training (Cognition SWE-1.5/SWE-grep, Glean per-customer models, Hippocratic Polaris).** Verso is Python-only, model-neutral, trains nothing (hard invariant). Role-tiered *routing* to existing models is in; training/fine-tuning is a hard non-goal. The "task-specialized worker model" idea is a *routing config note* in §6.4 at most, not a capability to build.
7. **A non-engineer "Context Hub" / no-code behavior-tuning console (LangChain) and "recipes" sharing platform (Goose).** Governance/ops surface for non-engineers is a platform feature; Verso's surface is the Python `@tool`/config API. Note the gap exists; do not build the console.
8. **Enterprise knowledge-graph memory topology (Glean: typed people×docs×permissions graph with query-time permission traversal).** Precise and real, but a v1-overkill memory subsystem. RRF+asymmetric-embeddings (already known) is the v1 retrieval default; the permission-as-query-time-gate idea is a one-line note for §5.2, not a graph store to build.
9. **OODA-compression-ratio as a baked-in eval metric (Sankar).** Excellent *framing* for why agents matter (decision-velocity infra) and good positioning copy — but do not bake an "OODA compression" scorer into the eval harness; `define_outcome(bounded)` anchored to real win conditions already covers the substance.
10. **Three-LLM-calls-per-step mandatory "deliberation mode" (Sierra: take-stock→plan→evaluate) as the default loop.** Keep the loop minimal (<200 lines, single think/act by default). Multi-candidate deliberation is an *optional* config (folds into D9's samples=N), never the default — making it default is exactly the overkill the bet rejects.

---

## Unreachable / not-mined-for-this-theme (coverage honesty)

- **No verbatim video transcript was available for ANY of the 18 A/V sources read.** Every note (and therefore every quote above) was reconstructed from speaker-authored companion essays, Sequoia/Latent-Space/Substack digests, and conference recaps, cross-validated across 2–5 secondaries per source. Quotes are as-attested in those secondaries, not from primary captions. Sources where this reconstruction is thinnest (flagged read_partial in the notes): Devin/Wu, Boris Cherny (PRE episode specifically — quotes pulled from the newsletter companion + a different Every.to episode), Hippocratic/Shah (the specific MAD episode had no transcript; quotes are from Shah's other written sources + the Polaris paper), Palantir/Sankar, Cursor/Truell, Cockcroft, Mitchell Hashimoto. Treat exact wording as reliable-but-reconstructed.
- **Frontier-research note files in the assigned list were NOT mined for this theme** because they carry no NEW loop/tools/durable/safety deltas (they are training-/capability-/interpretability-focused and feed the model/strategy/evals themes): Karpathy (AGI-decade), Chollet, Ilya (×2), LeCun, Silver, Kaplan, Sutton, Frankle, Lindsey, Perez, Levine, Vinyals, Hassabis, "Let's reproduce GPT-2", Stanford CS336, Raschka (State of LLMs 2026), Tworek, Hyung Won Chung, "Looking Inside Neural Networks", "Open Source AI is AI we can Trust", "Open-Endedness and General Intelligence", Schulman, "Dream Machine", "A Technical History of Generative Media", "No Priors / SSMs", "The Bitter Lesson Is Coming for Proteins", "Building the Generative Web", "How To Build The Future: Parker Conrad", "Production AI Engineering Starts with Evals" (evals-theme), "Retrieval After RAG / Turbopuffer" (context-theme). Of these I spot-read the agent-relevant ones (Brown, Sholto/Bricken, McGrew, White, Ng) and folded their genuine deltas above; the remainder were correctly deferred to their owning themes rather than padded into this one.
- **Net:** ~26 of the ~53 assigned files were read or spot-read; 18 read in full. The unread remainder are accounted for by theme, not skipped silently.
