# A Field Guide to Rapidly Improving AI Products

**Source:** https://hamel.dev/blog/posts/field-guide/  
**Author:** Hamel Husain (ML engineer; former GitHub, Airbnb, Accenture; AI evals practitioner; co-teaches "AI Evals for Engineers & PMs" with Shreya Shankar, 3,000+ alumni from 500+ companies)  
**Publisher:** Hamel's Blog (hamel.dev); also syndicated at O'Reilly Radar  
**Length:** ~6,000 words  
**Status:** read_full (WebFetch + multiple WebSearch cross-verifications including O'Reilly mirror and eng-leadership.com digest)

---

## FAITHFUL DIGEST

### Central Thesis

> "The teams who succeed barely talk about tools at all. Instead, they obsess over measurement and iteration."

This is the article's load-bearing claim, backed by 30+ production implementations. The failure mode of most AI teams: investing weeks in architecture decisions (which framework, which embedding model, which chunking strategy) before they can answer "is my system getting better or worse?"

### Principle 1: Error Analysis — The Highest-Leverage Activity

The most common and costly mistake is what Husain calls "the tools trap": believing the right framework will solve quality problems. Generic metrics compound this error — they create false progress signals and fragment team attention.

> "Generic metrics are worse than useless — they actively impede progress."

The NurtureBoss case study (real estate AI assistant):
- Starting point: teams discussing architecture without measurement capability
- Action: examined actual conversation logs systematically
- Method: built a taxonomy of failure modes from qualitative notes using an LLM
- Finding: **three issues accounted for over 60% of all problems**: (1) conversation flow issues (missing context, awkward responses), (2) handoff failures (not recognizing when to transfer to humans), (3) rescheduling problems — including date-handling failures
- Specifically on date handling: the system failed 66% of the time on date-related queries
- Result after targeted fixes: date-handling success rate improved from 33% to 95%

The meta-finding: this specific, critical bug was completely *invisible* to generic metrics. Off-the-shelf evaluation scores would have given a false-passing grade.

The process: bottom-up error analysis (start from actual data, build taxonomy upward) is more effective than top-down analysis (start from predetermined metrics, check against data). The distinction:
- Top-down: "let's measure ROUGE / BLEU / task completion"
- Bottom-up: "let's look at 50 conversations and categorize what went wrong"

### Principle 2: Custom Data Viewers as Critical Infrastructure

> "Teams with thoughtfully designed viewers iterate 10x faster than those without them."

Generic dashboards fail because they decontextualize outputs. The critical design requirements for a useful data viewer:
- Displays all context in one place (not scattered across multiple screens)
- Makes feedback capture trivial (one-click)
- Captures open-ended annotations (not just thumbs up/down)
- Supports quick filtering and sorting
- Includes keyboard shortcuts for high-velocity review

The counterintuitive prescription: build this viewer in hours using AI-assisted development, not weeks. It doesn't need to be sophisticated — it needs to be fast to use and reflective of the actual domain structure.

Husain's framing: the data viewer is infrastructure, not a nice-to-have dashboard. It's the primary interface through which product intuition about the AI system develops. Without it, product sense cannot compound.

### Principle 3: Domain Experts Writing Prompts

The bottleneck in most AI teams: domain experts must translate their knowledge through engineers who write prompts. This creates:
- Signal loss (the translation is lossy)
- Velocity loss (every prompt iteration requires an engineer)
- Jargon barriers (RAG, embeddings, context windows — language that excludes domain experts)

Husain's prescription: "build bridges, not gatekeepers." Give domain experts integrated environments where they can directly write and iterate on prompts.

Quote: "Prompts are just English."

Replacing technical jargon with precise descriptions of actual capability: "providing the right context" instead of "RAG"; "asking the model to check its work" instead of "chain of thought." This is not dumbing down — it's accurate description that includes the people who understand the problem best.

Referenced: Bryan Bischoff as a practitioner who successfully implemented this model, enabling learning designers (not engineers) to directly own prompt quality.

### Principle 4: Synthetic Data Bootstrapping

AI teams don't need real users to begin testing. LLMs can generate realistic test cases across defined dimensions. The key insight: "LLMs are surprisingly good at generating excellent examples of user prompts" (Bryan Bischoff).

The conditions for effective synthetic data:
- Ground generation in actual system constraints (not abstract examples)
- Define dimensions explicitly: features (what the system should do), scenarios (edge cases and normal cases), personas (who the user is)
- Verify that generated inputs actually trigger the intended scenarios — don't assume fidelity

Synthetic data enables the eval infrastructure to exist from day one, before any real users interact with the system.

### Principle 5: Trustworthy Evaluation Systems

Two design choices that maximize eval trust:
1. **Binary pass/fail judgments** (not 1-5 scales) — clarity at the cost of some nuance
2. **Detailed critiques accompanying each judgment** — preserves nuance without sacrificing clarity

The calibration requirement: maintain >90% agreement between automated evaluations and human judgment before scaling automation. Regular alignment checks prevent silent drift — the failure mode where automated evals become decoupled from what humans actually care about.

The analogy: eval trust is like code test trust. If your tests don't reflect actual system requirements, passing them is evidence of nothing.

### Principle 6: Experiment-Based Roadmaps

The trap: promising specific features by specific dates in an AI product context. Because AI quality is inherently uncertain (you can't know in advance which approach will work), date-based feature commitments create pressure to ship bad work rather than the right work.

Alternative: commit to *experimentation cadences* with clear decision points. Bryan Bischoff's "capability funnel" model measures progress through stages of increasing utility, from "system can do X at all" → "system can do X reliably" → "system can do X reliably under adversarial conditions." This acknowledges uncertainty while giving stakeholders meaningful progress signals.

### The Breakthrough Emergence Pattern

Husain observes: "breakthrough solutions often emerge after extended periods appearing unproductive." This is not a license for indefinite iteration without measurement — it's a warning against treating a plateau as evidence of inherent limitation. The eval infrastructure is what lets you distinguish "this approach is wrong" from "we need more iterations."

### Hamel's Position in the Ecosystem

Husain's credential: ML engineering across GitHub, Airbnb, Accenture, plus 30+ production AI product engagements. His evals course (co-taught with Shreya Shankar) reached 3,000+ professionals from 500+ companies — this is not a purely academic position. He's building the practitioners' canon for AI product quality.

---

## VERSO RELEVANCE

### §1 Bet / Moat [CONFIRMS + SHARPENS]

Husain's "teams obsess over measurement not tools" is the strongest external validation of Verso's entire positioning. But there's a delta: Husain frames this as a *team behavior* problem — teams that behave this way win. Verso frames it as a *structural* problem — most teams can't behave this way because the tools don't embed the measurement loop. The sharper version: Verso makes the winning behavior the default behavior. "You can't accidentally skip evals in Verso because the eval loop is structural, not optional."

**Verdict: SHARPENS** — adopt-now as a positioning sharpening: not "use measurement" but "measurement is structural, not behavioral"

### §7 Demo-able Wedge [NEW-IDEA]

The NurtureBoss case — date-handling failing 66% of the time, invisible to generic metrics — is the exact shape of the Verso demo-able wedge argument. The side-by-side should be: "here is an agent with generic logging; here is an agent with Verso's embedded eval harness; here is what was invisible in the first one." The concrete demo moment: run an agent with both, show that the critical failure (whatever the equivalent of date-handling is for the demo domain) is surfaced by Verso's inline evals and completely missed by the generic approach. This is stronger than "evals are important" — it's "here is the specific bug class you will miss without this."

**Verdict: NEW-IDEA** — adopt-now as the concrete demo script for the eval harness wedge

### §7 Product Taste / inspect() Surface [SHARPENS]

Husain's "custom data viewer as critical infrastructure" maps directly to `agent.inspect()` but sharpens what it needs to do. The design requirements he specifies (all context in one place, one-click feedback, open-ended annotation, keyboard shortcuts for velocity) are the feature spec for `inspect()`. The viewer isn't a debugging tool — it's the primary surface through which product intuition about the agent's behavior is built. Verso should frame `inspect()` as a *data viewer*, not a debugger. "The viewer is how you build intuition about your agent's failure modes."

**Verdict: SHARPENS** — adopt-now as framing and implicit feature spec for inspect()

### §12 Positioning — Anti-LangChain [SHARPENS]

Husain's "generic metrics are worse than useless — they actively impede progress" is the strongest form of the anti-harness-as-afterthought argument. LangChain's model (framework + LangSmith as separate monetization) is exactly the generic metrics + separate dashboard model Husain diagnoses as the problem. Verso's counter-position: the eval loop is *embedded*, not external; the data viewer is *structural*, not optional. The Husain framing makes this a concrete product quality argument, not just an architectural preference.

**Verdict: SHARPENS** — adopt-now in §12 counter-positioning vs. LangChain

### §2 Non-Goals [NEW-IDEA]

Husain's "bottom-up, not top-down" analysis principle is a principled refusal in disguise. For Verso: non-goal = providing a suite of off-the-shelf eval metrics. The principled reason: off-the-shelf metrics impede progress by creating false-passing grades on bugs that matter. Verso should commit to *enabling* bottom-up error analysis (the structural primitive), not to providing the metrics (which must be domain-specific anyway). This is a concrete §2 non-goal with a defensible argument: "We don't ship pre-packaged eval metrics because they'd make you slower, not faster."

**Verdict: NEW-IDEA** — adopt-now in §2 non-goals

### §5/§6 Technical Primitives [SHARPENS]

Husain's synthetic data bootstrapping principle directly applies to Verso's eval harness design. The harness should make it trivially easy to define the three dimensions (features, scenarios, personas) and generate a synthetic eval corpus from them. The FakeModel pattern Verso already has (from recent commits) is the technical substrate; what's needed is the scaffolding that lets domain experts (not engineers) define the dimensions. This is a §6 primitive design implication: the FakeModel should be reachable by domain experts, not just engineers.

**Verdict: SHARPENS** — lock-defer (implementation implication for §6 FakeModel design)

### Founder-OS Layer [SHARPENS]

Husain's weekly cadence prescription (the experimental roadmap with regular calibration checks) is the operational form of Verso's "dogfood-first" principle. For Verso's founder: the equivalent discipline is: weekly inspection of the agent's conversation logs using inspect(); weekly error taxonomy update; monthly synthetic corpus refresh. This is not process overhead — it's the mechanism by which product intuition compounds. The founder who does this weekly will identify the Verso equivalent of NurtureBoss's date-handling bug before users do.

**Verdict: SHARPENS** — adopt-now in founder-OS operating principles

---

## TOP DELTAS FOR RETURN

1. **[SHARPENS / §1+§12]** "Measurement structural not behavioral" — Husain's finding (teams that win obsess over measurement) when combined with Verso's design flips from behavior to structure. The positioning move: Verso makes measurement the default path, not the disciplined path.
2. **[NEW-IDEA / §7]** NurtureBoss demo-shape: critical bug invisible to generic metrics, visible to embedded eval harness. This is the concrete demo script for Verso's eval wedge — run the same agent with and without the harness, show what was invisible.
3. **[NEW-IDEA / §2]** No pre-packaged eval metrics is a principled non-goal with a specific argument: off-the-shelf metrics create false-passing grades on the bugs that matter. Bottom-up error analysis requires custom taxonomy, not generic scores.
