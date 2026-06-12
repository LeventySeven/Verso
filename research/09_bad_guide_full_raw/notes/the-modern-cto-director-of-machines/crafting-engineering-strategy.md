# Crafting Engineering Strategy — Will Larson
**Source:** https://lethain.com/crafting-engineering-strategy/ (book launch post) + chapters at https://lethain.com/tags/crafting-eng-strategy/
**Key chapters fetched:** LLM adoption strategy, Diagnosis, Policy, Is engineering strategy useful?, Wardley mapping the LLM ecosystem, Steps to build a strategy
**Status:** read_full (index page + 6 substantial chapters; primary content from published chapter extracts)
**Themes:** strategy, loop_harness, context

---

## Faithful Digest

### Core Argument
Good decisions are the core of creating software; strategy is the art of reproducibly making good decisions. Every organization has a strategy — most just don't write it down. The unwritten version exists as oral tradition, which creates inconsistency over time, vulnerability to misinterpretation, and problems onboarding new leaders. Writing it down is the single highest-leverage act for advancing strategy.

The five-step framework: **Explore → Diagnose → Refine → Set Policy → Operate**. The primary purpose of this structure is to prevent practitioners from skipping hard steps — especially diagnosis, which is where almost every failed strategy went wrong.

### LLM Adoption Strategy (most relevant chapter)

The hypothetical company "Theoretical Ride Sharing" models a rigorous strategy for LLM adoption. Key policies:

1. **Single foundational model provider:** "Start with Anthropic" — anchored by a Wardley map showing low lock-in risk and cost-effective switching. The rationale: switching costs are economically cheap; existing models already vary over time (GPT 3.5 "allegedly got lazier"); regulatory DPA friction is the main friction, not technical lock-in.

2. **Staged learning investment:** Require DX team to offer at least one LLM-backed developer productivity tool; require Internal Tools team to offer at least one ad-hoc prompting tool; refresh policy in six months. The explicit goal is "quickly learning about this unfamiliar domain where internal expertise is limited."

3. **Avoid irreversible commitments:** "LLMs don't appear to fall into [the irreversible category]." Current uncertainty (models may plateau, open source may dominate, providers may decouple from platforms) argues for optionality over large bets.

4. **Diagnosis challenge framing:** The core diagnosis was *not* "which LLM is best" but "switching costs between models and providers is economically cheap and manageable." That frames policy toward optionality and rapid iteration.

**On LLM capability trajectory:** "The only high-confidence prediction is that model improvement will likely double one or two more times over the next three years, after which improvement might either continue doubling at that rate or plateau at that performance level—either outcome seems plausible."

### Wardley Mapping the LLM Ecosystem

The central prediction: LLM platforms (agents, RAG, evals) will *decouple* from model providers. Strongest position for product companies: "adopt the broadest available LLM pattern platforms while explicitly decoupling pattern platforms from model providers."

The map identifies: Product Engineers (want fast, simple LLM deployment), ML Infrastructure (steers adoption, owns common LLM infrastructure like search for RAG), Security/Compliance (model hosting safety, data controls).

Evolutionary pressure: "every plausible combination will exist to some degree until the ecosystem eventually stabilizes in one dominant configuration." Companies running narrow platform providers or being locked to model providers face eventual headwinds.

### Diagnosis as Strategy Foundation

> "Every strategy that I've seen fail, did so due to a lazy or inaccurate diagnoses."

Six-step diagnostic approach:
1. Braindump from blank sheet
2. Summarize exploration (what did others do in similar situations?)
3. Mine for distinct, adversarial perspectives — "talk to stakeholders likely to disagree"
4. Synthesize into one internally consistent perspective with a single accountable author
5. Test drafts with expected disagreers until they agree you've captured their view accurately
6. Focus on directional rather than perfect correctness

Key principle: "There are never reasons why strategy simply cannot succeed, only diagnoses you've failed to recognize." Blockers become part of the diagnosis, not excuses.

The "whisper the controversial parts" technique: when a diagnosis can't be stated bluntly without causing damage, reframe it factually without blame. Example: "Based on general practice, it seems likely that our new Private Equity ownership will expect us to reduce R&D headcount costs through a reduction." This maintains honesty without political damage.

### Policy Setting

Four categories of policy:
- **Approvals**: recurring decision gates, builds trust through explicit consultation
- **Allocations**: "the most concrete statement of organizational priority" — reveals what the company actually believes accelerates productivity
- **Direction**: explicit mandates when consistency outweighs individual judgment (appropriate for clear destinations)
- **Guidance**: recommendations when nuance/complexity prevents mandates but outcomes are clear

> "What makes a policy good is that it's effective, not that it's novel or inspiring."

Three criteria for evaluating policies: **Applicable** (navigates real scenarios), **Enforced** (teams face accountability), **Creates Leverage** (compounds impact).

Anti-pattern: multiple competing policy proposals usually expose *diagnostic* gaps, not legitimate policy choices. Resolution comes from diagnostic clarity, not from comparing options.

### On Written vs. Implicit Strategy

> "With oral history, what you believe is highly dependent on who you talk with, which shapes your view of history and the present. With written history, it's far more possible to agree at scale, which is the prerequisite to growing at scale rather than isolating growth to small pockets of senior leadership."

"Information herd immunity": organizations don't need everyone knowing something, just enough people that confusion doesn't propagate too far. Target: all Staff+ engineers and engineering managers understand strategy.

### Verbatim Quotes

1. "Every strategy that I've seen fail, did so due to a lazy or inaccurate diagnoses."
2. "There are never reasons why strategy simply cannot succeed, only diagnoses you've failed to recognize."
3. "What makes a policy good is that it's effective, not that it's novel or inspiring."
4. "With oral history, what you believe is highly dependent on who you talk with... With written history, it's far more possible to agree at scale."
5. "Strategy testing, covered in the Refinement section, enables recursive diagnosis through real-world evidence rather than speculation."
6. "If you don't demonstrate concrete progress quickly and excite leadership, your strategy will fail."
7. "LLMs don't appear to fall into [the irreversible category]." [On LLM provider lock-in]
8. "The only high-confidence prediction is that model improvement will likely double one or two more times over the next three years, after which improvement might either continue doubling at that rate or plateau at that performance level—either outcome seems plausible."

---

## VERSO RELEVANCE

### [SHARPENS §12 — Positioning/GTM] Written strategy as moat
Larson's core claim: written strategy that can be debated, agreed upon, and explicitly evolved is the single highest-leverage organizational act. Verso's positioning benefits from applying this to itself — a framework that cannot be debated and evolved will calcify. The "six-month refresh" policy in the LLM adoption chapter is a concrete mechanism: Verso's own roadmap/positioning should have a similar explicit expiration and re-evaluation cadence built into the plan.

**Verdict:** sharpen — adopt the explicit "6-month refresh" framing for Verso's roadmap sections that touch model-capability assumptions.

### [SHARPENS §1 — The Bet] Model capability doubling as conservative, not certain
Larson's LLM trajectory view: "The only high-confidence prediction is that model improvement will likely double one or two more times over the next three years, after which improvement might either continue doubling at that rate or plateau at that performance level—either outcome seems plausible." This is *more conservative* than the METR paper's exponential curve (doubling every 207 days since 2019). Larson is writing from an engineering executive's perspective, not a researcher's. This conservative framing is actually strategically useful: Verso's "18-month horizon" bet doesn't need to predict acceleration — it just needs the trajectory to continue at its current pace. The conservative floor is enough.

**Verdict:** sharpen — Verso's §1 bet language should note that *even the conservative estimate* (Larson's "1-2 more doublings in 3 years") validates the architectural bet. Don't depend on acceleration.

### [NEW-IDEA §6.4 — Model/Provider] Decoupling platform from provider as first-class architecture
Larson's Wardley map conclusion: "adopt the broadest available LLM pattern platforms while explicitly decoupling pattern platforms from model providers." The specific prediction that RAG/agent platforms will separate from model providers is directly relevant to Verso's model abstraction layer. Verso currently treats MCP as a "demoted opt-in adapter" — the same decouple-from-provider logic should be applied at the eval layer, the memory layer, and the orchestration harness. If Verso is tightly coupled to any model provider for eval infrastructure, that becomes a strategic liability as these components commoditize separately.

**Verdict:** adopt-now — enshrine provider/platform decoupling as explicit constraint in §6.4 and §5.5.

### [SHARPENS §12 — Positioning] LLM adoption diagnosis: expertise gap is the real constraint
Larson's most useful diagnosis for Verso's GTM: "The organization believes that making major investments now, before developing expertise, would be relatively high-risk and low-reward given that no other industry players have identified meaningful advantages yet." This describes Verso's *target customers exactly* — teams that have LLM capability pressure but haven't yet developed the internal expertise to extract durable value. Verso's positioning should name this diagnosis explicitly: "You're under pressure to ship LLM features. You don't yet know which architecture decisions are reversible. Verso keeps your commitments reversible until you do."

**Verdict:** adopt-now — use the "limited internal LLM expertise + low switching costs = invest in optionality first" diagnosis directly in Verso's positioning narrative.

### [CONFIRMS §4 — The Seam/Architecture] Allocation policy as expression of priority
The Uber case: allocation of one engineer to manual provisioning, rest to self-service automation. The Verso parallel is the seam decision: default everything to the cheap/fast tactical path, promote to durable only when the value of persistence becomes clear. The allocation isn't "build graph vs. build loop" — it's "use tactical until you can diagnose the need for durable, then promote without rewrite."

**Verdict:** confirm — already captured in seam architecture, but the "allocation reveals actual priority" framing sharpens how Verso explains the tactical default to CTOs.

### [NEW-IDEA §5.5 — Evals] Strategy testing as recursive diagnosis
Larson: "Strategy testing, covered in the Refinement section, enables recursive diagnosis through real-world evidence rather than speculation." The eval layer in Verso is exactly this: define_outcome creates hypotheses, judge-panel runs them, results feed back into revised prompting/tooling decisions. Verso's eval system is a *strategy testing engine* for agents. This is a powerful reframe for positioning evals: not just "did it work?" but "what does this tell us about our diagnosis of the task?"

**Verdict:** sharpen — reframe Verso's evals positioning in §5.5: evals-as-strategy-testing, not just pass/fail metrics.

### [NEW-IDEA §12 — Positioning] "Information herd immunity" for agent harnesses
Larson's concept: you don't need everyone to know the strategy, just enough people that confusion doesn't propagate too far. The target is "all Staff+ engineers and engineering managers." For Verso, this maps directly to the RunContext / ContextBundle inspection model: the human-in-the-loop doesn't need to understand every inference step, just enough to course-correct before architectural dead ends compound. The "herd immunity" framing is unusually precise for explaining why Verso's hooks/interrupt model is positioned where it is — not every turn, just enough turns.

**Verdict:** lock-interface-defer — useful framing for §6.3 safety/hooks documentation; not a feature change.
