# Theme Synthesis (AV pass): Multi-Agent / Orchestration (§6.2)

**Theme keys touched:** multiagent, loop_harness, safety, model, strategy
**Pass:** Audio/Video sources (talks, podcasts) — complements the WF1 full-text pass in `_SYNTHESIS_multiagent.md` (D1–D9). This file reports only what the AV corpus adds or contradicts beyond WF1 + the ALREADY-KNOWN list.

**Sources consolidated (21 note files; multi-agent-relevant content extracted):**
- Directing a Swarm of Agents — Adrian Cockcroft (QCon SF 2025)
- Block CTO Dhanji Prasanna: Building the AI-First Enterprise with Goose (Sequoia)
- Interrupt 2025 Keynote — Harrison Chase (LangChain)
- Scaling Test-Time Compute to Multi-Agent Civilizations — Noam Brown (Latent Space)
- Jeff Dean & Noam Shazeer — 25 Years at Google (Dwarkesh)
- Automating Science — Andrew White / Future House (Latent Space)
- Open-Endedness and General Intelligence — Tim Rocktäschel (talk)
- Sholto Douglas & Trenton Bricken — How LLMs Actually Think (Dwarkesh)
- The Arrival of AGI — Shane Legg (DeepMind podcast)
- Why One of OpenAI's Top Researchers Walked Away — Jerry Tworek (Core Memory)
- Inside Devin — Scott Wu / Cognition (Lenny's)
- OpenEvidence — Daniel Nadler (Sequoia)
- Sierra — Clay Bavor (Sequoia)
- Hippocratic AI — Munjal Shah (MAD Podcast + Polaris paper)
- How AI Breakout Harvey Is Transforming Legal — Winston Weinberg (Sequoia)
- Living Lindy — Flo Crivello (Cognitive Revolution)
- Advanced Context Engineering — Dexter Horthy (YC Root Access)
- Building Claude Code — Boris Cherny (Pragmatic Engineer)
- A Technical History of Generative Media — Fal.ai (Latent Space)
- Retrieval After RAG — Turbopuffer (Latent Space)
- The Future of Software Creation — Amjad Masad / Replit (YC)

---

## Cross-Source Picture

The AV corpus does three things WF1 could not, because these are **production operators with deployed multi-agent systems** (Sierra, Cognition/Devin, Hippocratic, OpenEvidence, Harvey, Block/Goose, Lindy) rather than essayists. WF1 settled the *philosophy* ("don't force the graph," convergently). The AV layer settles the *empirical shape* of the small amount of multi-agent machinery that production teams actually ship — and it lands on a strikingly narrow and consistent design.

**1. The dominant production multi-agent pattern is NOT task-decomposition — it is the concurrent SUPERVISOR/WATCHER.** This is the single biggest AV delta and it is not in WF1 or the known list. Three independent production systems converge:
- Sierra pairs every primary agent with **specialist supervisor agents** that review outputs post-hoc, exploiting the empirical asymmetry that "LLMs are better at detecting errors in their own output than at not making them" (Bavor). Three LLM calls per agent step (take-stock → plan → evaluate-candidates).
- Hippocratic's **Constellation** (Polaris): one primary conversational agent + 22 specialist agents running *concurrently as real-time safety checkers* on orthogonal dimensions (medication, escalation, compliance). The specialists exist to catch primary-model failures, not to parallelize throughput. Drove severe-harm rate 0.06% → 0.00%.
- OpenEvidence: a verification/citation-labeling model sits downstream of synthesis; abstention is architecturally enforced.

This is structurally different from WF1's frames (failure-quarantine, scheduler-offload, primary-context-as-scheduler) and from the orchestrator-workers frame. It is a *vertical* (oversight) topology, not a *horizontal* (decomposition) one. Verso's §6.3 should name a "parallel safety-watcher / supervisor" pattern: a concurrent monitor over the primary loop's outputs, one-flag-enabled, no graph, typed veto/flag signal back.

**2. The typed inter-agent boundary is the load-bearing reliability mechanism, stated unusually crisply.** WF1 had "bounded sub-agents." AV sharpens *what crosses the boundary*: Hippocratic's specialists emit **JSON field-value pairs, not prose**, precisely so the primary "cannot be contaminated by a specialist's prose style or hallucinated reasoning." Horthy independently requires sub-agent returns to be **structured compaction documents** (goal/status/approach/blocker), not raw output. Boris Cherny's "uncorrelated context windows" gives the *why* from the other side: isolation is the point, contamination is the enemy. Verso's `dispatch_sub_agent` should enforce a typed return schema, not freeform text — this is now triple-attested by production sources.

**3. Two operators with multi-agent products in market openly say multi-agent is still immature — and prescribe the SAME fallback Verso already defaults to.** Crivello (Lindy, 2+ yrs data): "multi-agent systems are still being defined and do not work nearly as reliably" as single-agent + dumb tools; "draw a sharp line between agents and tools, and your tools should not be agentic… it's hard enough to make one agent work." Masad (Replit): MCP is "a traditional RPC protocol" that "won't solve agent-to-agent coordination — new marketplace protocols are required" — i.e. true A2A orchestration is *unsolved*, not merely un-built. This is strong external cover for Verso keeping §6.2 small and explicitly labeling A2A protocols as out-of-scope/future-work rather than pretending to solve them.

**The counterweight (so the section isn't one-sided):** the *frontier-research* sources push the opposite direction on ambition — Noam Brown's "multi-agent civilizations" (value *compounds* over time, not just parallelizes), Shazeer's Giga-MoE (heterogeneous independently-developed expert modules = sub-agent specialization), Rocktäschel's quality-diversity (schedule *diverse* sub-agents, not identical ones). These are real and worth one forward-looking paragraph, but they are 5–10-year framings, not v1 machinery. The honest synthesis: **build the supervisor + typed-boundary + bounded-spawn primitive now; cite civilization/QD/MoE as the long-horizon "why this primitive scales," not as features.**

**Net for the PRD:** the AV pass does not overturn WF1. It (a) adds one genuinely new *production* pattern (concurrent supervisor) that belongs in §6.3 more than §6.2, (b) hardens the typed-return-schema requirement from "nice" to "triple-attested reliability primitive," (c) supplies named operator quotes that A2A is unsolved (defends keeping §6.2 small), and (d) adds an enterprise blocker WF1 missed: **permissioning/ethical-walls must precede multi-agent memory** (Harvey, Goose). Resist the temptation to import the civilization/MoE/QD ambition into v1 scope.

---

## Deltas (highest value first; NEW or CONTRADICTING vs WF1 D1–D9 + known list)

### A1 — Concurrent supervisor/watcher is the dominant *production* multi-agent topology [ADOPT-NOW, §6.3 (+§6.2)]
Three deployed systems independently use a vertical oversight topology — a second agent that watches/reviews the primary's output in real time — distinct from every frame already in the PRD (failure-quarantine, scheduler-offload, orchestrator-workers, primary-as-scheduler). This exploits a stable empirical asymmetry, so it survives model upgrades.
- Bavor (Sierra): *"The solution to many problems with AI is more AI… LLMs are better at detecting errors in their own output than at not making those errors in the first place."* Supervisor persona → more discerning behavior.
- Hippocratic/Polaris: 22 specialist agents run *concurrently* as safety checkers; *"if the primary model fails or misses a task, the specialist ensures the system continues correctly and safely."* Severe-harm 0.06% → 0.00%.
- **Recommendation: adopt-now** as a named §6.3 pattern "parallel safety-watcher / supervisor agent" — a concurrent monitor over loop outputs, one-flag promotion, typed veto/flag return, no graph. Distinguish from pre-action guardrails (a guardrail blocks an action; a supervisor catches a bad *output* that slipped through). This is the AV pass's headline finding.
- **Source:** Sierra (Bavor) / Hippocratic (Shah, Polaris).

### A2 — Typed (non-prose) inter-agent return schema is a reliability primitive, triple-attested [SHARPEN, §6.2]
WF1's "bounded sub-agent" said nothing about *what crosses the wire*. Production sources are emphatic: the boundary payload must be structured, never prose, or the parent gets contaminated.
- Polaris: specialists emit *"JSON-like field-value pairs, not free text"*; the primary *"cannot be contaminated by a specialist's prose style or hallucinated reasoning."*
- Horthy: subagent output must be an *intentional compaction document* (goal/status/approach/blocker), *"a structured summary, not raw results."*
- Cherny: the value of sub-agents is *"uncorrelated context windows"* — isolation, so noise doesn't propagate.
- **Recommendation: sharpen.** Make `dispatch_sub_agent` enforce a typed return schema (e.g. summary/affected-state/blockers) rather than accept freeform strings. Sharpens WF1 D3's bounded-spawn signature with a return-type contract. Connects to known typed `StopReason` / `ContextBundle`.
- **Source:** Hippocratic / Advanced Context Engineering / Building Claude Code.

### A3 — Operators with shipped multi-agent products say A2A orchestration is UNSOLVED; keep §6.2 small [CONFIRM, §6.2 (+§2)]
Two practitioners with multi-agent in market explicitly de-scope true agent-to-agent coordination. Stronger than WF1's essayist warnings because they ship the thing.
- Crivello (Lindy): *"multi-agent systems… are still being defined and does not work nearly as reliably"*; *"draw a sharp line between your agents and your tools, and your tools should not be agentic… it's hard enough to make one agent work. Now you need to make two agents work."*
- Masad (Replit): *"MCP is a more traditional RPC protocol and won't solve agent-to-agent coordination — new marketplace protocols are required."*
- **Recommendation: confirm.** §6.2 should state, with these named quotes, that A2A protocols/marketplaces are *unsolved future work, not current scope* — and that the v1 default is single-agent + dumb tools, sub-agents only for quarantine/parallelism. Reinforces WF1 D1 and the RESIST list with production voices.
- **Source:** Living Lindy / Replit (Masad).

### A4 — Permissioning / ethical-walls must precede multi-agent memory (enterprise blocker WF1 missed) [SHARPEN, §6.1 (+§5.4, §6.2)]
A multi-tenant blocker not surfaced anywhere in WF1 or the known list: when multiple agents share institutional/matter memory, isolation is a *data-leakage* problem before it's a coordination problem.
- Weinberg (Harvey): *"If you don't have ethical walls in place and you try to do that, it's gonna be an absolute nightmare."* Permissioning is sequenced *before* the 4-tier memory roadmap (personal → matter → institutional → client).
- Prasanna (Goose): agent inherits the *user's own authorization level*; *"its blast radius is highly limited to any actions humans take."*
- **Recommendation: sharpen.** Add a callout to §6.1/§5.4: promoting to the durable/shared-memory layer requires declaring which memory tiers each (sub-)agent may read/write; default sub-agent auth = caller's auth (blast-radius-scoped). Without this, multi-agent + durable memory silently creates cross-context leakage. Concrete, low-cost, enterprise-credibility.
- **Source:** Harvey (Weinberg) / Block-Goose (Prasanna).

### A5 — Capability-composition (build many narrow workflows, then auto-select/collapse) as a distinct multi-agent frame [SHARPEN, §6.2]
A product-shaped multi-agent frame distinct from WF1's three (quarantine/offload/scheduler): individual agents as *modular capabilities* a meta-agent selects and sequences — without exposing a graph to the user.
- Weinberg (Harvey): expand (many narrow workflows) → collapse (*"uploading a share purchase agreement triggers relevant workflows automatically without visible complexity"*); Workflow Builder = user-configurable composition over primitives.
- Wu (Devin): MultiDevin manager + ≤10 workers; *"particularly effective for repetitive, isolated subtasks"*; manager decomposes, workers execute, manager merges.
- **Recommendation: sharpen.** Note capability-composition in §6.2 as a *third* legitimate reason to go multi-agent (after quarantine and offload) — selection/sequencing of bounded capability-agents, still no graph DSL. Pairs with WF1 D5's "ship a worked orchestrator-workers example in plain async Python."
- **Source:** Harvey / Inside Devin.

### A6 — Quality-diversity scheduling: schedule *diverse* sub-agents, not identical ones [LOCK-DEFER, §6.2 (+§6.4)]
Genuinely new scheduling idea, absent from WF1 (which only had pipeline-vs-fanout topology). Between "parallel identical workers" and "hierarchical decomposition" sits a diversity-aware option.
- Rocktäschel (Rainbow Teaming / QD): populate an archive spanning diversity dimensions (risk category, attack style); open-ended search over a *diverse* population beats single-objective. >90% attack success on Llama 2/3.
- **Recommendation: lock-defer.** Do not ship a QD scheduler. But the spawn/fan-out interface should not *preclude* assigning different strategies/models per sub-agent (falls out of WF1 D7's per-sub-agent model override). Track as a named pattern; build nothing.
- **Source:** Open-Endedness (Rocktäschel).

### A7 — Multi-agent value *compounds* over time, not just parallelizes (the "why it scales" framing) [SHARPEN, §6.2 (+§6.1)]
Reframes the *purpose* of the multi-agent layer beyond throughput — relevant because it argues the durable event log (known) is what makes compounding possible.
- Brown (OpenAI): *"have them cooperate and compete with billions of AIs over a long period… build up a civilization… far beyond what is possible today."* Single agents are "caveman-level"; coordination substrate unlocks compounding.
- Shazeer: Giga-MoE = large heterogeneous *independently-developed* expert modules updated without full retrain — functionally the sub-agent-specialization argument.
- **Recommendation: sharpen.** One paragraph in §6.2: multi-agent value is *compounding institutional knowledge over deployment time*, not just parallelism; the durable layer (event log) is the substrate that lets it compound. Forward-looking framing, not a feature. Avoid over-claiming — this is 5–10yr horizon.
- **Source:** Noam Brown / Jeff Dean & Noam Shazeer.

### A8 — Self-play / model-vs-model scoring degenerates outside zero-sum; supervisor ≠ self-play [SHARPEN, §6.3 (+§5.5)]
A correctness constraint on the supervisor pattern (A1): if you build the watcher as an *adversarial* second agent, you risk minimax degeneracy in cooperative/open-ended tasks. Not in WF1.
- Brown: *"Once you go outside a two-player zero-sum game, that's actually not a useful policy anymore"*; self-play produces "really weird behavior" without a defined adversary (why Cicero needed an LLM, not pure self-play).
- **Recommendation: sharpen.** When documenting A1's supervisor, specify it is a *rubric-scored reviewer*, not an adversarial self-play opponent. Protects against importing RL-game intuitions into a cooperative agent harness. One-liner caveat.
- **Source:** Scaling Test-Time Compute (Noam Brown).

### A9 — Autonomy level is orthogonal to capability; collaborative/approval-gated multi-agent is the stable default [SHARPEN, §6.2 (+§4)]
Theoretical backing that the *default* multi-agent operating mode should be approval-gated, not full-autonomy — independent of how capable models get.
- Legg (Levels of AGI): autonomy is a *deployment choice*, not a capability readout; even at Expert AGI the framework recommends "AI as Expert" (human guides) over "AI as Agent" (full autonomy). Level-3 "AI as Collaborator" maps to approval-gated multi-agent.
- **Recommendation: sharpen.** §6.2 should make the collaborative/checkpoint-gated mode the *default* for multi-agent deployments, with full autonomy opt-in — and tie it to the tactical↔durable seam (§4) as the autonomy dial. Reinforces, does not duplicate, WF1's bounded-spawn.
- **Source:** The Arrival of AGI (Legg).

### A10 — Cache-aware / warm-vs-cold sub-agent routing as a scheduler concern [LOCK-DEFER, §6.2]
Operational scheduling concern for multi-agent at scale, absent from WF1: keeping tool registries / context bundles / model configs "warm" across parallel sub-agent invocations is a real cost lever.
- Fal.ai: hardest infra problem is keeping 600 models warm across 35 datacenters; top customers chain 14 models simultaneously. The agent analog is warm vs cold sub-agent/context invocation cost.
- Turbopuffer: agentic retrieval = *"one agent firing many parallel queries… 8+ parallel requests"* per reasoning round; optimize for burst concurrency, not single-call latency.
- **Recommendation: lock-defer.** No scheduler in v1. But (consistent with WF1 D4's interface-slot stance) the sub-agent/tool-dispatch interface should be async/parallel-friendly and able to express a cache/affinity hint later. Reserve the slot; build nothing.
- **Source:** Fal.ai / Turbopuffer.

---

## RESIST (overkill / bullshit for a v1 personal-infra framework)

- **"Multi-agent civilizations" / billions-of-agents framing as a v1 feature.** Brown's compounding thesis is a 5–10yr *why*, not machinery. Use one paragraph of framing (A7); ship nothing civilization-scale.
- **A `Constellation`/`SupervisorPanel` class with N built-in specialist roles.** Hippocratic runs 22 domain specialists because *healthcare*. Verso ships *one* generic concurrent supervisor primitive (A1) with a user-supplied rubric — not a zoo of named watcher roles.
- **A quality-diversity scheduler / archive (Rainbow Teaming-style).** A6 is a pattern, not a primitive. A per-sub-agent strategy/model override is sufficient; no QD search engine, no diversity-archive store.
- **Giga-MoE / heterogeneous-module orchestration as an agent abstraction.** Shazeer's framing is a model-architecture analogy for *why specialization works*; it is not a Verso runtime feature. No module-router, no distillation pipeline.
- **A new agent-to-agent protocol / marketplace layer.** Both Masad and Crivello say it's unsolved — so Verso must *not* pretend to ship it. One in-process `spawn`, MCP opt-in, A2A explicitly future-work (A3). No message bus, no agent marketplace, no A2A RPC.
- **Adversarial self-play between agents as a reliability mechanism.** A8: degenerates outside zero-sum. The supervisor is a rubric-scored reviewer, not a self-play opponent. Do not build agent-vs-agent adversarial scoring into the harness.
- **A "director agent" that auto-manages deadlines/coverage (Cockcroft's NoMan).** Explicitly speculative even in-source ("maybe we have no man"); goal-directed meta-orchestration is a v2+ research direction, not v1 scope. Track, build nothing.
- **Resolution/cost accounting, recipe stores, and other product-surface around multi-agent** (Sierra resolution-pricing, Goose "recipes"). Org/product features of specific companies, not framework primitives. The `@tool` + `spawn` surface must merely not preclude them.

---

## Coverage / Reachability (honest accounting)

This was a transcript hunt over audio/video sources. Of the 21 assigned note files, the **underlying primary AV transcript was fully captured for only 2**: *A Technical History of Generative Media (Fal.ai)* and *Living Lindy (Crivello)*. The other **19 are reconstructed from secondary sources** (show-notes, companion blog posts, paywalled/login-gated video, or — for several — the companion academic paper rather than the talk itself): the speaker's verbatim framing in the specific video is, in those cases, not directly verifiable. Notably reconstruction-heavy (no verbatim primary transcript located at all): Tworek/Core Memory (paywalled), Hippocratic/MAD (no mirror; leaned on Polaris paper), Harvey/Sequoia (no transcript mirror), Interrupt-2025 keynote (leaned on a same-period Sequoia interview), Cockcroft/InfoQ (login-gated video; leaned on his Medium post + digests), Open-Endedness/Rocktäschel (no video transcript; leaned on the ICML position paper). Quotes attributed above are as recorded in the note files; treat single-source paraphrases (vs. attested-verbatim) accordingly. **Unreachable (primary AV transcript not fully captured): 19 of 21.**
