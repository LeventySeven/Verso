# 13 — ALL-transcripts sweep + teardowns + guides + pydantic-ai 2.33.0

**Run:** `wf_0c78be69-d6b`, 2026-08-22. 53 agents, one wave. 6.55M subagent tokens, 1,213 tool
calls, 28 min. Ledger: `inv-verso-adapt-2026-08-22.md`.

**Question.** What should Verso build/adapt next, and what should it decline — grounded in the full
transcript corpus (all 40 files), related teardowns, the three named talks, the guides, and
pydantic-ai's newest version.

---

## 0. What the evidence is worth

| check | result |
|---|---|
| units returned | 53 / 53 — UNIT-01..53, no blanks; unit count == block count |
| outcomes | DONE 53 · EMPTY 0 · FAILED 0 |
| findings | 422 |
| **quotes relocated at their cited line, byte-for-byte** | **422 / 422 · 0 mismatches** |
| findings carrying an explicit `[ASSUMED*]` tag | 9 |
| claims with a number outside their own quote | 52 (audited — see below) |

Three caveats that bind how much of this to believe:

1. **51 of 53 units returned exactly 8 findings — the cap.** The cap bound, not the corpus. There is
   more in these files; the marginal finding in each unit is the weakest one. Weight on evidence, not
   on count.
2. **Zero EMPTY across 53 units.** EMPTY was pre-authorised for the two lanes most likely to earn it
   (COHERE_LABS, HORMOZI) and neither used it. Treat those two units' findings as the most likely to
   be stretched.
3. **One real numeric drift, caught and corrected.** The adversary's strongest number against Verso's
   `Reviewer` — HaluEval at 53.8–58.5% on distinguishing factual from hallucinated summaries — is
   measured on **"Models such as ChatGPT and Claude 2"**
   (`articles/task-specific-llm-evals-that-do-don-t-work.md:446`), i.e. 2023-era models, not frontier
   ones. The adversary framed it as "frontier models". The finding still stands as a caution; the
   magnitude does not transfer. The other 51 numeric-drift cases audited out as course codes (CS336,
   CS229), version numbers (2.0, 4.5), line refs and section numbers.

Everything below that names a number or a mechanism was re-opened by the orchestrator at its source
line before being written here.

---

## 1. The three named talks

**`CEvIs9y1uog` — "Don't Build Agents, Build Skills Instead"** (Barry Zhang + Mahesh Murag, Anthropic).
On disk at `TRANSCRIPTS_CODE_WITH_CLAUDE.md:1667`. **This is an attack on Verso's premise, and it is
the most important thing in the run.**

> `- Consequence: core scaffolding can become as THIN as just BASH + FILE SYSTEM — which is great and scalable.` — `:1689`

and the mechanical case against a decorator tool registry as the primary extension surface:

> `- Problems with TRADITIONAL tools: (1) some have poorly written, ambiguous instructions; (2) when the model struggles, it CAN'T change the tool, so it's stuck with a "cold start" problem; (3) tools ALWAYS live in the context window.` — `:1707`

**`CxXgV54KzpQ` — "Jeff Dean: The 1% Rule for Building in AI"** (YC). On disk at
`TRANSCRIPTS_YC.md:30811`. Dean's operative claim is that multi-agent fan-out **with a judge/discard
step** is the concrete fix for agents derailing around step 30–40 — framed as inference-time search
over the solution space, not as delegation (`:31459`). He also gives a founder selection rule: pick
problems the model fails at *almost completely* today, not ones it half-succeeds at (`:31513`), and
argues specifying intent gets *more* important as agents write more (`:31548`).

**`aR20FWCCjAs` — Ilya Sutskever / Dwarkesh.** The one source **not** on disk — the corpus held only a
one-line index pointer at `guidesfm/research/raw/ai-research-taste.md:10`. Fetched live (1,308 lines;
the lane's first attempt was refused by egress policy and it found a permitted route rather than
reconstructing from memory). Four things bear on Verso:

- The bottleneck is *ideas plus the engineering to bring them to life*, not compute (`ilya.txt:376`) —
  the harness sits on the scarce side.
- The volatility he forecasts lands on the **training recipe**, upstream of anything a harness owns
  (`:272`) — supports absorbing it in `model/` and not reshaping `core/loop.py` to chase it.
- *"anything you can do with a value function, you can do without, just more slowly"* (`:292`) — fresh
  ammunition for the "not a router/planner cult" non-goal: planner/critic machinery buys speed, not
  capability.
- His illustration of the eval-vs-reality gap is an agent that *"brings back the first bug, and you can
  alternate between those"* (`:120`) — a frontier-acknowledged validation of stuck detection, and an
  argument that the detector should be **cycle-aware**, not merely a step cap.

---

## 2. pydantic-ai — the delta, against the *correct* baseline

The teardown is not just the 1.x line. `teardowns/PYDANTIC_AI.md:796` carries a **Deep Refresh dated
2026-07-10 at PyPI 2.8.0**. The real delta is **2.8.0 → 2.33.0**. Three structural moves, each
re-verified by the orchestrator against the sdist, not taken from an agent:

**(a) The durable *wrapper agent* was tried and abandoned.** All three wrapper classes are deprecated:

```
durable_exec/temporal/_agent.py:95  # TODO(v3): remove `TemporalAgent` in favor of the `TemporalDurability` capability.
durable_exec/dbos/_agent.py:71      # TODO(v3): remove `DBOSAgent` in favor of the `DBOSDurability` capability, …
durable_exec/prefect/_agent.py:64   # TODO(v3): remove `PrefectAgent` in favor of the `PrefectDurability` capability.
```

~3,950 lines of wrapper machinery being retired in favour of an object you attach to a normal `Agent`.
**Verso's `checkpointer=` flag is the shape they converged on. Do not add a `DurableAgent`.**

**(b) Graph persistence left the agent path — but the graph did not.** `grep` for
`snapshot_node|StatePersistence|persistence=` across `pydantic_ai/*.py` and `agent/*.py` returns
**zero hits**. Resume is now: cancel → `RunCancelled.all_messages()` → pass to a new run as
`message_history` —

> `        complete snapshot that can be passed to a new run as `message_history` to resume the` — `run.py:565`

**That is Verso's shape.** The 1.x teardown's "every node transition is a persistence boundary" is
dead. *But the fleet blurred this and I am pinning it:* the spine is **still** a `pydantic_graph` —
`UserPromptNode` / `ModelRequestNode` / `CallToolsNode` are alive at `_agent_graph.py:501 / 1106 /
1816`. What left the graph is persistence, not the graph. Do not read this as "they dropped the graph."

**(c) Human-in-the-loop became an output type, not a control-flow branch.** Approval is compiled into
tool metadata —

> `            kind='unapproved' if self.requires_approval else 'function',` — `tools.py:506`

— the run simply *ends* with a `DeferredToolRequests` value, and it is a hard error if that type was
not declared among the agent's outputs (`_tool_execution.py:1046`). This is the single most adoptable
idea in the run and **it needs no graph.**

---

## 3. The contradictions, reconciled

Parallel readers over disjoint scopes produced three real factual collisions. Each was resolved by
re-opening the primary text, not by picking the better-written finding.

**3.1 Multi-agent — the corpus is violently split.**
*For:* Jeff Dean's fan-out+judge; Anthropic's own research system; Google's Maps orchestrator; Cursor's
recursive planner tree outperforming fancier topologies.
*Against:* Cognition's **default-deny** (`don-t-build-multi-agents.md:66`); Rippling built it and
**tore it out** (`TRANSCRIPTS_LANGCHAIN.md:10247`); Sierra calls most splits quality-destructive;
Genspark rejected state-sync; Copilot's "Fleet" failed outright on a shared file; Cursor caps local
parallelism at 1–3 agents *because they edit the same copy*; AutoGen — the most complete such runtime
in the corpus — is in maintenance mode, `no new features. v0.4 is final.` (`AUTOGEN.md:972`);
Anthropic's own staff call it overinvestment relative to context hygiene.

**Resolution — two independent sources land on the same rule:**
> `There's a shared through-line with all of these experiments: multi-agent systems work best today when writes stay single-threaded and the additional agents contribute intelligence rather than actions` — `articles/multi-agents-what-s-actually-working.md:96`

> `reads/search/review parallelize, writes and decisions stay on a single thread` — `guidesfm/CLAUDECODEMAXXXING.md:388`

**3.2 Are evals the moat?** Waymo's CEO, Jake Heller and Decagon say yes. Anthropic says the opposite,
in their own words:
> `- "**very often we just saturate the eval, and then we have to throw it away, and we have to come up with a new eval.**"` — `TRANSCRIPTS_YC.md:18970`

**Resolution:** the durable asset is not the eval *cases* — it is the error-analysis discipline and the
trace substrate underneath. `articles/llm-evals-faq.md:206` puts evals *downstream* of error analysis,
and explicitly discourages writing evaluators before the feature (`:363`).

**3.3 Is a harness a durable asset?** Boris Cherny calls all scaffolding disposable tech debt; Google
DeepMind expects harness behaviour to be trained into the model; the Skills talk says it collapses to
bash+filesystem. Against that, Cline measured the *same* model performing differently under different
harnesses, and a LangChain maintainer names the tool-calling loop as the one constant across three
years of churn.

**Resolution — and this is the strategic finding of the whole run.** Anthropic states what actually
survived their own per-release deletion of agent logic into the model:
> `- "If you look at the code that's in the Claude Code harness today, **almost all of it is about safety and permissions and static analysis**."` — `TRANSCRIPTS_YC.md:18919`

The parts of a harness that do *not* get absorbed are **safety/permissions** and **durable state**.
Verso has both. That is the defensible core — not the loop, and not the evals.

---

## 3b. CORRECTION — four of the eight "adopt" items were never gaps

**Written after the orchestrator read Verso's source itself.** Everything in §4 below was originally
derived from UNIT-50 (a subagent's map of Verso) plus the fleet's suggestions. Re-reading the actual
code killed half the list. Recorded here rather than quietly edited, because *the fleet's Verso-side
claims are the least trustworthy part of this run* — the corpus-side quotes all relocated, but the
"Verso lacks X" claims were never verified until now.

| originally proposed | reality | evidence |
|---|---|---|
| `override_args` on approval (edit-then-approve) | **ALREADY SHIPPED.** The resume path re-dispatches with `override_args if override_args is not None else args` | `verso/core/loop.py:326`, `verso/agent.py:77` |
| `pass^k` in `evals/` | **ALREADY SHIPPED, and richer than proposed** — it also returns a reliability-vs-token-budget *curve* | `verso/evals/suite.py:151` |
| tool-result clearing + tombstones | **ALREADY SHIPPED.** `prune()` masks old tool results with a `MASK` placeholder — clearing *and* the tombstone | `verso/context/prune.py:5,9` |
| declarative per-tool approval | **EFFECTIVELY SHIPPED.** `PermissionDecision.ASK` + `policy.ask_every(*tools)` + durable `_pause(kind="approve")` already name tools; `requires_approval` on `@tool` is ergonomics, not capability | `verso/safety/policy.py:44`, `verso/core/loop.py:176-183` |

And one claim in §6.1 of the first draft was **simply wrong**: I wrote that Verso "ships the sixth
instance" of the fail-open bug. It does not. A *raising* hook propagates and kills the run — verified
by probe — which is fail-**closed**. The real, narrower defect is different and is stated correctly in
§4 below.

The honest read: **Verso is further along than the sweep assumed.** The remaining list is short.

---

## 4. Adopt — ranked, each additive, each with a test shape

| # | mechanism | status | evidence | fit |
|---|---|---|---|---|
| 1 | **Prune RETENTION becomes a caller parameter (`prune_keep_last_n`)** — `loop.py` called `prune(history)` with the module default 10; the caller could set the *trigger* (`max_context_tokens`) but not how much survives | **BUILT** | `CODING_AGENT_HARNESS_COMPARISON.md:390` — gemini-cli 50%, goose 80%, cline 81%, Claude Code 95%: *a 45-point spread on the same problem*, i.e. no defensible constant | default 10 ⇒ byte-identical; `tests/test_prune_retention.py` |
| 2 | **`Hooks(strict=True)`** — a `pre_tool` hook returning `None` silently falls through to ALLOW. `None` is indistinguishable from "no opinion" (legitimate, mirrors `post_tool`) and "I meant DENY and fell off a branch" (the fail-open class). Semantic is *pinned*, not changed; `strict` is the opt-in that makes it loud, and also rejects junk truthy returns | **BUILT** | `AGENT_SECURITY_DEFENSE.md:26` — *five silent fail-open paths across four security codebases*, none of which alarms | default False ⇒ byte-identical; `tests/test_hook_fail_open.py` incl. a characterization test pinning today's semantic |
| 3 | **Progressive tool disclosure** — name+description resident, full schema on demand | **NOT BUILT — needs its own design pass** | `code-execution-with-mcp.md:138` — *150,000 tokens to 2,000 … 98.7%*; core-vs-on-demand split cut cost 33% in production (`TRANSCRIPTS_OPENAI.md:1512`) | **conflicts with KV-cache**: mutating the tool block invalidates every token after it (`TRANSCRIPTS_CODE_WITH_CLAUDE.md:4621`, `TRANSCRIPTS_OPENAI.md:1494`), so it must be stable-prefix + append-only tail. Too big to land blind |
| 4 | **Caller-reachable run state on cancel** | **NOT BUILT — smaller than it looked** | `run.py:558-570` | `ctx.messages` is already assigned every step and `ctx` exists even with no checkpointer (`agent.py:68`), so the data already survives — it is just *unreachable*, since `Agent.run` builds the ctx internally. The fix is exposure, not preservation |

Second tier, worth doing, more design needed: mid-run steering as a queue-drain hook (zero loop lines —
`capabilities/_pending_messages.py:1`); per-adapter declared capability sets on the Model Protocol
(`models/__init__.py:369`); budget visibility to the model (goose is the *only* harness of seven that
tells the model its remaining budget — `CODING_AGENT_HARNESS_COMPARISON.md:777`).

---

## 5. Decline — with the evidence, so the refusal is recorded rather than omitted

- **Graph-shaped public hooks** (`before_node_run`/`wrap_node_run`). Violates rule 3 by putting the
  graph in the *public extension contract*, and it froze pydantic-ai's own internals. Verso can get the
  same power without a node layer: one `wrap_step(ctx, handler)` hook where the handler runs a single
  loop turn and may be called more than once.
- **UI protocol adapters and `to_web()`.** `ui/_web/app.py:35` downloads a React chat bundle from
  jsDelivr at runtime. That is an npm release train, a CDN dependency, a disk cache and DNS-rebinding
  validation — none of it agent-runtime work. "Not an SDK" is load-bearing.
- **`realtime/`.** A persistent bidirectional session is a *second runtime shape* — it forced a refactor
  of the shared `Model` interface (`models/_abstract.py:1`). It cannot be made byte-identical-when-unused
  at the abstraction level, only at the import level.
- **`embeddings/`** — lands squarely in "not the model/kernel".
- ~~**A built-in think/scratchpad tool.**~~ **Moved to §6.4b — this is not a decline, Verso already
  ships one.** The corpus retracts its rationale; the action is to condition the PRD's recommendation
  on the provider, not to refuse a build.
- **Capability ordering / topological sort** — only once a second wrapping hook actually exists.

---

## 6. Where the sweep says Verso is exposed

**6.0 The fleet's Verso-side claims were the weak lane — see §3b.** Four of eight proposed additions
already existed. The corpus-side evidence held (422/422 relocated); the "Verso lacks X" side was
subagent inference and half of it was wrong. Lesson for the next sweep: give the self-map lane the
same relocation contract as the corpus lanes, and verify every gap claim against source before it
becomes a proposal.

**6.1 RETRACTED — Verso's surface is narrower than the gap I claimed.** The first draft said Verso
"rejects nothing" under a checkpointer, against pydantic-ai's `_reject_runtime_toolsets`. Re-read:

- Verso's config pin **does** reject on resume — `config_fingerprint()` pins model id + sorted tool
  names, `_drift()` reports adds/removes, `ConfigDriftError` refuses to continue
  (`verso/core/loop.py:45-77`), with `allow_config_drift=True` as the explicit escape.
- More importantly, **the pydantic failure mode cannot occur in Verso**: `Agent.run()` takes no
  per-run toolset. Tools are construction-time. There is no runtime tool injection to reject.

So this is a design *strength* misread as a gap. What survives of the original point is much smaller
and is now §6.2: the seam's *scope* is worth stating plainly, but there is no missing rejection surface.

**6.2 "Promoted to durable with one flag" oversells what the seam buys.** Turning on durability in
pydantic-ai re-hosts the loop in a determinism-enforcing runtime
(`with disable_threads(), set_agent_graph_sleep(workflow.sleep):` — `temporal/_durability.py:466`).
Temporal compares the emitted command stream against recorded history; Restate pins an invocation to
its deployment for life; DBOS gates recovery by `application_version` in SQL before user code runs
(`DURABLE_EXECUTION.md:39`). Verso's config-pin-and-guard is closest to DBOS's coarse check — which the
teardown does validate as legitimate — but the seam buys **resume-from-last-step**, not exactly-once
side effects, not crash-resume without checkpoint writes, not cross-process continuation. Palantir pairs
each recorded step with an **idempotency key** rather than trusting tools to be idempotent
(`TRANSCRIPTS_PALANTIR.md:5762`). State the boundary in the README rather than letting it read as
equivalent to a durable-execution engine.

**6.2b One correction to my own §6 draft.** I wrote that a raising hook makes Verso "the sixth
instance" of the fail-open bug. Probed: a raising `pre_tool` hook **propagates and kills the run** —
fail-closed. The genuine defect is narrower and now fixed behind `strict`: a hook returning `None`
falls through to ALLOW.

**6.3 The `Reviewer` docstring makes a claim the corpus does not support.** `orchestrate/__init__.py:19`
advertises it as *"the cheapest multi-agent win"*. Against that: naive self-critique with no external
signal degrades correct answers about as often as it fixes wrong ones
(`TRANSCRIPTS_DEEPLEARNINGAI_COURSES.md:18408`); a dedicated read-only validator sub-agent **failed to
stop** reward hacking (`TRANSCRIPTS_HUGGINGFACE.md:6133`); and HaluEval measured 53.8–58.5% on exactly
the discrimination task a critic performs — *on 2023-era models, so treat the magnitude as indicative,
not current*. Either back it with a Verso-run eval or soften it to a named task class. Note the one
condition the corpus says makes it work: *"we found this technique to work best when the coding and
review agents do not share any context beforehand"* (`multi-agents-what-s-actually-working.md:48`) — so
`Reviewer` should receive a **fresh context plus the artifact**, never the parent's assembled bundle.

**6.4 `orchestrate/fan_out` is broader than any source endorses.** Under §3.1's reconciled rule, its
documented contract should be narrowed to read-only/investigative children with writes staying on the
parent thread — which is also what the reference implementation (Claude Code subagents) actually does.

**6.4b NEW — `think` is a shipped builtin whose primary source has been retracted.** Found by the
orchestrator's own re-read, not by the fleet. Verso ships `think` (`verso/tools/builtins.py:11`) and
PRD §175 presents it as a primitive that *"forces reflection into an observable channel."* Anthropic —
who published the pattern — now says:

> `Extended thinking capabilities have improved since its initial release, such that we recommend using that feature instead of a dedicated think tool in most cases.` — `articles/the-think-tool.md:23`

And Verso **already ships the replacement**: `AnthropicModel(..., thinking=...)`
(`verso/model/anthropic.py:15`). So it carries both the deprecated pattern and its successor, with the
PRD recommending the deprecated one unconditionally.

*The nuance that stops this from being a simple delete:* Anthropic's advice is Anthropic-specific.
`think` is the **portable** way to get an observable reasoning channel on providers with no native
reasoning mode, and Verso is deliberately multi-provider. So the fix is not removal (that would break
rule 1 for anyone passing it) — it is **conditioning the recommendation**: PRD §175 should say `think`
is for providers without native extended thinking, and point at `thinking=` where it exists. A shipped
built-in advertised on a retracted rationale is exactly the "harness workaround that the next model
release turns into dead weight" that `TRANSCRIPTS_CLAUDE.md:3127` names.

**6.5 Two gaps with no Verso answer at all — both verified against source.** `verso/tools/builtins.py`
ships exactly three tools (`think`, `done`, `todo`): there is **no filesystem/bash/runtime-environment
primitive**, the thing the Skills talk argues is the *entire remaining core*. And the `@tool` registry
pays the always-resident context cost on every request with no escape hatch — see
`DESIGN_progressive_tool_disclosure.md` for the shape that survives the KV-cache constraint, and why
the obvious implementation of it is a net loss.

---

## 7. What was not read

- **51 of 53 units hit the 8-finding cap.** More is in these files.
- ~371 of 395 teardowns unassigned; ~174 of 190 articles unopened. Both lanes were sampled by rank, and
  the cut was declared, but neither is exhausted.
- HORMOZI: heading-routed only; most of its 229,594 lines unread by design.
- pydantic-ai: `embeddings/` backends, `ui/ag_ui/`, and the ~3,950 lines of deprecated wrapper bodies —
  the last of which is the concrete "why the wrapper failed" evidence, if that becomes decision-relevant.

---

## 8. What was built, and what the red team caught

Two items from §4 landed. Baseline **489 passed / 1 skipped** → now **499 passed / 1 skipped**
(+10 tests, zero regressions, `ruff` clean on every changed file).

| change | files |
|---|---|
| `prune_keep_last_n` — retention becomes caller config, threaded `Agent` → `run_loop`/`run_stream` → `_drive` → `prune()`, and through `resume_loop` | `verso/agent.py`, `verso/core/loop.py`, `verso/core/stream_loop.py` |
| `Hooks(strict=True)` — a `pre_tool` hook returning a non-`PermissionDecision` raises instead of falling through to ALLOW | `verso/safety/hooks.py` |

**The red team found a real defect in the first cut, and it was the dangerous kind.** The knob was
threaded through `run()` but **not** `run_stream()`. Reproduced before fixing:

```
run()    -> masked: 7  kept: 1
stream() -> masked: 0  kept: 8      # same Agent, same config
```

`VersoSpan.capture()` (`verso/evals/span.py:38`) is built on `agent.stream()` — so **evals would have
graded an agent pruned differently from the one in production**, silently, with no error. A
regression test for exactly this now exists.

**Two further corrections, both from the review:**

1. *The why-comment cited the wrong number.* It read "shipped harnesses disagree by 45 points on how
   much to keep." The 45-point spread in `CODING_AGENT_HARNESS_COMPARISON.md:390` is the **trigger**
   column, not retention. Re-read: harnesses disagree on retention's very **unit** — `DEFAULT_TAIL_TURNS=2`
   (OpenCode), a 5,000/25,000-token head (Claude Code), `PRESERVE_THRESHOLD=0.3` of characters
   (gemini-cli), `protect_last_n` tool calls (goose). That is a *stronger* argument for caller-controlled
   retention, but the original comment attached a real number to a claim it did not support — the exact
   fabrication-wearing-a-citation failure this sweep's own contract forbids. Fixed in both call sites.
2. *The first resume test was tautological.* It paused on the **first** tool call, so the resumed run had
   nothing to prune and the test passed with the threading deleted. Rewritten to pause on the sixth call;
   now verified to fail (`assert 6 == 1`) without the fix and pass with it. Both new tests were
   adversarially checked this way.

**Left open, deliberately** — a pre-existing defect the review surfaced outside this diff: in the
default (non-strict) path a `pre_tool` hook returning a truthy non-decision is passed through verbatim,
producing the model-visible string `Tool 'add' was True by policy; it did not run.` A junk return
becomes deny policy with a garbled reason. Fixing it changes default-path behavior, so it needs its own
rule-1 decision rather than a quiet patch here.

**Housekeeping:** a 50KB `.scratch_boris.txt` written to the repo root by a sweep agent mid-run was
moved to `research/13_all_transcripts_sweep/scratch_boris_cherny_yc_extract.txt` (gitignored) so a
blanket `git add` cannot sweep local-only corpus material into the tracked tree.
