# Theme Synthesis: Evals + Verification (§5.5)

**Theme keys touched by these sources:** evals, loop_harness, strategy, model, memory
**Synthesis owner question:** what should change in Verso's §5.5 (evals) — and adjacent §5.1/§5.2/§6.1/§6.3/§12 — given the full read of the eval-relevant sources?

Sources read in full:
- Hamel Husain, *Your AI Product Needs Evals* (the operator's bible for this theme)
- Shunyu Yao, *The Second Half* (ReAct/SWE-bench/tau-bench author — eval-design-as-the-game)
- Anthropic, *Building Effective Agents* (evaluator-optimizer pattern; measurable-improvement gate)
- BAIR/Databricks, *The Shift to Compound AI Systems* (evals = the gradient for non-differentiable systems)
- METR, *Measuring AI Ability to Complete Long Tasks* (the 50%/80% horizon gap; calibration formula)
- Sean Goedecke, *If You Are Good at Code Review…* (structural failure / non-tractability as a lagging signal)
- Armin Ronacher, *Agent Design Is Still Hard* (honest confession: agent evals are the hardest unsolved problem; must be in-loop/observability-based)
- Andrej Karpathy, *A Recipe for Training Neural Networks* (silent failure; the Stage-2 verification checklist; complexify-one-at-a-time)
- Addy Osmani, *My LLM Coding Workflow into 2026* (cross-model review as standard practice; tests-as-gate)
- Harrison Chase, *Reflections on 3 Years of LangChain* (the competitor's GTM: give away the loop, monetize the eval/observability platform)

---

## The cross-source picture

There is a remarkably tight consensus across nine very different authors that **the eval/verification harness — not the loop — is where production agents are won or lost.** The harvest already had this as Verso's thesis; what the full read adds is (a) the *mechanism* of why, and (b) several concrete, low-cost primitives that sharpen §5.5 without adding machinery.

Four mechanistic framings converge on the same conclusion:

1. **Agents fail silently (Karpathy).** Unlike normal software, an agent "runs" — calls tools, returns plausible output — while being fundamentally broken. The verifier is the *only* thing that detects the undetectable. This is the deepest design motivation for §5.5 and should be its opening sentence.

2. **Evals are the gradient for non-differentiable systems (BAIR).** Gradient descent doesn't reach a compound agent loop; outcome measurement is the only optimization signal. Evals are not a quality gate bolted on at the end — they are the backward pass. This reframes §5.5 from "testing" to "the optimization substrate."

3. **The benchmark-utility gap is the whole game (Yao).** Standard benchmarks assume auto-execution (no human) and i.i.d. (each run independent). Real deployed value violates both. "Second-half" evals must capture human-in-the-loop and sequential/stateful behavior — which is exactly what Verso's durable layer enables. Verso's evals shouldn't re-run saturated benchmarks; they should help users define outcome checks over *their* deployed reality.

4. **Eval + debug infrastructure overlap ~80% (Husain).** The trace database, the domain renderer, the assertions, the labeling — all serve both. Build them as one system. This is the single most actionable structural instruction for the §5.5 spec.

Two practitioners closest to the trenches (Ronacher, building a real production agent; Husain, 30+ production builds) independently land on the same operational truth: **agent evals cannot live in an external system fed clean inputs — they must be driven off observability data / instrumenting the actual run.** Ronacher confesses outright that *no* eval solution has satisfied them yet; Husain's whole method is "remove all friction from looking at data" via a domain-specific trace viewer built in under a day. The implication for Verso is sharp and contrarian to the LangSmith model: **eval data collection happens inside the loop, and the trace viewer is part of the framework, not a separate SaaS product.**

The competitor confirms this by contrast. Chase is explicit that LangChain's GTM is *give away the loop, monetize the platform (LangSmith)* — observability and evals are a separate product with a separate login, "neutral to the framework." Verso's counter-position writes itself: **embedded, in-process, first-class evals** vs. bolt-on external platform. That is a real architectural difference, not a feature-list difference.

The METR paper adds the quantitative backbone: the **80% (reliable) horizon lags the 50% (capability) horizon by 4-6×** at the same doubling rate. Reliability is structurally behind capability — which is precisely the gap the eval+durable harness closes, and the gap that grows *more* valuable as raw models improve.

Goedecke contributes the one genuinely new eval *dimension* worth flagging (carefully, as a defer): task-level success/failure misses the slow failure where two or three locally-correct-but-architecturally-wrong choices compound until the codebase/state is "no longer tractable." That is a lagging, session-level signal current judge-panel evals don't capture.

**Net:** almost everything here resolves to *confirm* or *sharpen* the already-known design (judge-panel + `define_outcome(bounded)` + in-loop hooks). A small number of concrete, cheap primitives are genuinely additive and earn their place. A larger number of seductive ideas (DSPy-style auto-optimization, per-model logistic calibration, tractability metrics, A/B infra) are correct-but-overkill for a v1 personal-infra framework and belong on the RESIST or lock-defer list.

---

## Genuinely NEW or SHARPENING findings (deduped, with verbatim quotes)

### A. Eval + debug are ONE system — build them unified (Husain) — SHARPENS, adopt-now
> "There is an incredibly large overlap between the infrastructure needed for evaluation and that for debugging." — Husain

The trace store, the renderer, the assertions, the labeling all serve both eval and debug. The harvest captured `define_outcome`/judge-panels as eval constructs but never said they are *also* the first thing you reach for when debugging. Write §5.5 as one unified surface, not "evals" + a later "debug mode." This is the structural spine of the section.

### B. Evals must be in-loop / observability-driven, NOT an external system (Ronacher, reinforced by Husain) — SHARPENS, adopt-now
> "Unlike prompts, you cannot just do the evals in some external system because there's too much you need to feed into it. This means you want to do evals based on observability data or instrumenting your actual test runs. So far none of the solutions we have tried have convinced us that they found the right approach here." — Ronacher

This is from someone shipping a real agent who has *tried the products and rejected them*. It validates the embedded-harness bet hard and tells us the eval signal is extracted from the append-only event log that the loop already produces. Verso's append-only history is not just for resume — it is the eval ground truth. The judge runs over the trace, in-process.

### C. Domain-specific trace renderer is the zero-friction key, and it's cheap (Husain) — NEW-IDEA, adopt-now
> "You must remove all friction from the process of looking at data." — Husain (built a custom viewer in Shiny "in less than a day")

Generic dashboards have high friction because they don't know what "a good response" looks like in your domain. Ship a **programmable render hook** over the event log (tool call in/out, final answer, step count as the opinionated default; trivial override for domain display). Not a fixed schema, not a SaaS. This is the concrete form of `ContextBundle.inspect()` extended to the whole run. Pairs with Karpathy's "visualize just before the net" → the renderer must show the **raw context window the agent actually received**, not a cleaned-up version, because the bug is usually in what the agent was *given*, not what it did.

### D. The "model struggles to pass" / silent-failure sanity protocol (Husain + Karpathy) — NEW-IDEA, adopt-now (docs/recipe, not machinery)
> "One signal you are writing good tests and assertions is when the model struggles to pass them." — Husain
> "Neural net training fails silently — syntactically correct code can be fundamentally misconfigured." — Karpathy

Karpathy's Stage-2 verification checklist maps almost 1:1 onto an agent sanity protocol, and six checks translate directly:
- **Overfit one batch** → can the agent solve a trivial known-answer case at all? If not, nothing else matters.
- **Input-independent baseline** → redact/zero the context; if output is unchanged, the agent isn't using its context.
- **Verify loss @ init** → does a stub/weak agent score at chance? If it passes your evals trivially on day one, the *evals* are too weak (Husain's signal).
- **Visualize just before the net** → inspect the exact prompt/context bundle.

Ship this as a getting-started recipe / a thin `verso eval` helper, NOT as a heavy subsystem. It is mostly documentation plus the renderer from (C) and a way to run the suite against a stub model.

### E. Failure-to-test-case capture closes the production→eval loop (Husain) — NEW-IDEA, adopt-now (thin)
> "Rechat has hundreds of these unit tests. We continuously update them based on new failures we observe in the data as users challenge the AI or the product evolves." — Husain

The eval suite is *living encoded domain knowledge*, not a static artifact. Because the loop already emits an append-only event log per run, a failed run can be promoted to a fixture/test case directly. A thin `capture <run_id> → test fixture` workflow is the highest-leverage closing of the loop and costs almost nothing on top of the existing event log. This is the one workflow primitive that most distinguishes "evals are a product" from "evals are a folder of asserts."

### F. The "measurable-improvement gate" bounds the eval/optimizer loop (Anthropic) — CONFIRMS/SHARPENS, confirm
> "[evaluator-optimizer fits] when we have clear evaluation criteria, and when iterative refinement provides measurable value." — Anthropic, *Building Effective Agents*

Anthropic's evaluator-optimizer pattern is structurally identical to Verso's judge-panel, which is strong external confirmation the architecture is recognized, not invented. The sharpening: make "the outcome must be bounded and measurably improvable" an explicit precondition on `define_outcome(bounded)`. Unbounded eval loops are a named anti-pattern. This is already implied by `(bounded)` — just state it.

### G. Second-half evals = HITL + sequential/stateful, the durable layer's reason to exist (Yao) — SHARPENS, adopt-now (positioning) / lock-defer (infra)
> "Our evaluation setups are different from real-world setups in many basic ways." — Yao
> (the two broken assumptions: auto-execution, i.i.d.)

Don't position Verso evals as "re-run benchmarks" (that race is industrialized and saturating in ~3 years). Position them as the way to define outcome checks that *violate* auto-execution and i.i.d. — multi-turn human-in-the-loop evals and sequential/stateful evals. This is exactly what the durable layer (checkpoint/resume, HITL, event-sourced state) makes possible, so evals and the durable runtime are the same story told from two ends. Lock the *interface* (an eval can span a resumed/multi-turn run and inspect accumulated state); defer heavy multi-turn-replay machinery.

### H. Evals are the gradient for non-differentiable systems (BAIR) — SHARPENS, confirm (framing)
> "[compound systems contain] non-differentiable components like search engines or code interpreters, and thus require new methods of optimization." — BAIR

Reframe §5.5's opening rationale: evals aren't a QA afterthought, they are the only optimization signal a compound agent has. This is the principled answer to "why first-class evals" and it also frames the DSPy tension (see RESIST): DSPy is one eval-driven optimizer; Verso's answer is `define_outcome` + judge-panel staying in native Python, *not* a declarative DSL.

### I. Cross-model judging is already standard practice — make it a one-liner (Osmani; echoes the known judge-panel) — SHARPENS, sharpen
> "AI-assisted cross-model review (have Claude write code, have Gemini critique it)." — Osmani (paraphrased from digest)

A Google engineer manually does Claude-writes/Gemini-critiques as routine discipline. The known judge-panel design is right; the sharpening is **ergonomics**: `--judge-model <other-provider>` must be a trivial flag, and canonical examples should show a *different* provider judging than the one in the loop (also reinforces cross-model failover and the multi-provider non-goal). Friction here kills adoption.

### J. METR calibration formula + the 80% horizon gap — SHARPENS (bet/durable) / lock-defer (eval calibration)
> "the amount of time a human can complete tasks that the model can complete with 50% success rate" ; 80% horizons are "4–6x shorter" at the same ~207-day doubling. — METR

Two uses. (1) Strategic: the 80% reliability horizon lags the 50% capability horizon by 4-6× — the eval+durable harness is the mechanism that closes that gap, and it gets *more* valuable as models improve. Cite in §1/§6.1. (2) Eval-primitive temptation: the logistic `p_success = σ((log h_agent − log t_task)·β)` could auto-calibrate "is this failure a regression or just expected difficulty?" — powerful but needs per-model calibration data Verso won't have. **Lock the interface** (optional `task_duration_estimate` on an eval) and **defer** the calibration engine. Do not build this for v1.

### K. Tractability-delta as a lagging session-level eval signal (Goedecke) — NEW-IDEA, lock-defer
> "Once two or three of them pile up, the app is no longer tractable for the agent and the whole thing grinds to a halt." — Goedecke

Real long-horizon failure mode that point-in-time judge evals miss: structural debt compounding across a session until forward progress collapses. Worth *naming* in §5.5 as a known gap and reserving an interface (an optional session-level outcome that inspects backtrack count / novel-vs-reused code paths). Building a real tractability metric is research-grade and out of scope for v1 — defer.

---

## What should change in the PRD vs. what's already covered

**Already covered (leave as-is, optionally add a citation):**
- Judge-panel + `define_outcome(bounded)` as the core eval primitive — confirmed by Anthropic's evaluator-optimizer and BAIR's "evals-as-gradient." No change beyond stating the bounded/measurable precondition (F).
- Append-only event history — already in harvest; the new point is that it *doubles as the eval ground truth* (B), so no new machinery, just new role.
- Role-tiered / cross-model — already in harvest; sharpening is ergonomic (I), not architectural.
- The bitter-lesson churn argument — METR's 5%-method-vs-30%-generation and the horizon curve are quantitative reinforcement, not new.

**Change / add to §5.5 (all low-cost):**
1. Open the section with **silent failure** (Karpathy) + **evals-as-gradient** (BAIR) as the two-sentence rationale. (A/H)
2. State §5.5 as **one unified eval+debug surface** built on the event log; the trace viewer is a **programmable, domain-overridable render hook** that shows the **raw context window**. (A/C, + Karpathy "visualize just before the net")
3. Make eval **data collection in-loop / observability-driven** an explicit invariant; no external eval system. (B)
4. Add a thin **failure→test-case capture** workflow (`capture <run_id>`). (E)
5. Ship a **getting-started sanity protocol** (overfit-one / input-independent baseline / stub-passes-too-easily) as docs + a light helper, plus the **"model should struggle to pass"** test-hardness check. (D)
6. Make **`--judge-model <provider>`** a first-class one-liner; canonical example uses a different provider to judge than to run. (I)
7. State the **bounded/measurable-improvement precondition** on `define_outcome`. (F)

**Adjacent sections:**
- §1 / §6.1: cite the **80% vs 50% horizon 4-6× gap** as the quantitative case that the eval+durable harness grows more valuable as models improve. (J)
- §6.1 / §4: frame **second-half evals (HITL + sequential/stateful)** as the durable layer's reason to exist — evals and durable runtime are one story. (G)
- §12: positioning claim — **embedded, in-process, first-class evals** vs LangChain's give-away-loop/monetize-LangSmith model; evals co-located with agent code, no separate product/login. (Chase, B)
- §5.5 (named gap, deferred): **tractability-delta** as a known long-horizon failure mode the judge-panel doesn't catch. (K)

---

## RESIST list (overkill / bullshit for a v1 personal-infra framework)

1. **DSPy-style end-to-end pipeline auto-optimization / declarative signatures.** Real demand exists (BAIR), but it abstracts away native Python — violates the hard invariant that `@tool` Python functions are THE path. Verso's answer is "evals are the optimizer, and they stay in Python," not a compiler/DSL. Do not build an optimizer.

2. **Per-model logistic success-probability calibration (METR formula) as eval infra.** Needs METR-grade per-model calibration data Verso will never collect. Seductive, research-grade, zero v1 payoff. Lock an optional `task_duration_estimate` interface at most; build nothing.

3. **A real "tractability-delta" metric (Goedecke).** Naming the failure mode is useful; instrumenting backtrack-counting / novel-vs-reused-path analysis as a shipped metric is research, not personal infra. Reserve interface, defer.

4. **A built-in A/B testing subsystem (Husain Level 3).** Husain himself says A/B is for mature products and defers to Eppo. A personal-infra v1 has no traffic to split. Out of scope.

5. **A bespoke eval SaaS / platform / dashboard product (the LangSmith path).** The entire cross-source signal is that the renderer is a <1-day in-process thing and a separate platform *adds* friction. Building a hosted eval product is the exact anti-pattern Verso counter-positions against. Ship a local programmable renderer, full stop.

6. **Active learning / consensus voting / granular rubric scoring on day one (Husain).** Husain is explicit: start binary good/bad; these "don't help until you have volume." A v1 with one operator has no volume. Binary labels + precision/recall on the judge is enough; defer the rest.

7. **A second LLM pass to reformat/post-process eval or agent output (Ronacher's output-tool experience).** Ronacher found a Gemini-Flash reformat pass "increases latency and degrades quality because the sub-model lacks context." Don't add a reformatting model to the eval path.

8. **Trace-level "reasoning quality" judges as a v1 default (BAIR's variable-reflection-steps idea).** Evaluating tool-order/reasoning-path quality is appealing but is a lock-interface-defer at best; the v1 default is outcome judging over the final result + the existing event log. Don't ship reasoning-trace grading by default.
