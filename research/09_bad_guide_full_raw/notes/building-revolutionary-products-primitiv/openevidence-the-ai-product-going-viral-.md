# OpenEvidence: The AI Product Going Viral With Doctors

**Source:** Sequoia Capital "Training Data" Podcast (March 4, 2025)
**Guest:** Daniel Nadler, CEO/co-founder of OpenEvidence
**URL:** https://www.youtube.com/watch?v=huR0Oa2odxA
**Transcript location:** https://sequoiacap.com/podcast/training-data-daniel-nadler/ (show notes + summary); https://research.contrary.com/company/openevidence (detailed research report); https://www.healthcare.digital/single-post/clinical-intelligence-a-strategic-analysis-of-openevidence-and-the-multi-agent-medical-ai-ecosystem (architecture analysis)
**Duration:** 1h05m
**Status:** read_partial (no verbatim transcript located; substantive reconstruction from Sequoia show notes, Contrary Research deep dive, and multiple technical analyses. Core arguments are well-attested across sources.)

---

## Speaker Background

Daniel Nadler founded OpenEvidence in 2021 with Zachary Ziegler (Harvard/MIT NLP). Nadler's prior company was Kensho, which applied domain-specific AI to financial data synthesis — the analogy he draws explicitly: "Doctors needed the same type of intelligent information synthesis that proved successful in financial markets."

---

## The Core Bet: Curation Over Monolith

Nadler's fundamental thesis is that training a smaller, specialized model on a curated high-quality corpus outperforms prompting a large generalist at medical tasks. This was validated empirically: OpenEvidence's research won Best Paper at the 2023 ML Healthcare Conference for demonstrating "smaller, highly-specialized models trained on in-domain medical data could outperform much larger general models."

The negative target is clear: "none of that [hallucination, fabrication, internet-sourced reasoning] is fair game" in medicine. The generalist model failure mode — confident wrong answers from internet-scale training — is structurally eliminated by only training on peer-reviewed sources.

---

## Technical Architecture

### The Ensemble (Not a Monolith)

OpenEvidence is not a single fine-tuned model. It is an **ensemble of approximately 6 specialized smaller models**, each handling a distinct task in the pipeline:

1. **Retrieval** — searches the corpus of ~35-40 million peer-reviewed publications
2. **Ranking** — scores retrieved documents by relevance to the clinical query
3. **Routing** — a "conductor" model analyzes query intent and routes to specialty-specific sub-models (160+ medical sub-specialties)
4. **Specialty Models** — domain-specific models for oncology, cardiology, neurology, etc. provide domain expert output
5. **Synthesis** — assembles the final response with citation grounding
6. **Verification / Citation Labeling** — proprietary "relevancy labeling system" ranks citations

The architectural topology is a **hub-and-spoke directed tree**: a central conductor routes to specialists; information flows strictly parent-to-child. This prevents "groupthink" (correlated errors in a flat network) and isolates state between specialists.

### Why Not RAG on a Large Model?

The question is why not just use GPT-4/Claude with a medical retrieval layer. Nadler's implicit argument (reconstructed from multiple sources):
- Large generalists are trained on internet data that includes misinformation, out-of-date clinical guidance, and non-peer-reviewed content — contamination at the weight level, not solvable by retrieval alone
- Overtraining on in-domain data ("overtrain on in-domain data") creates models with stronger priors for medical reasoning
- Ensemble routing allows each specialist to be a deeper expert in its domain than a single generalist can be across all of medicine

### Anti-Hallucination by Architecture

Three mechanisms:
1. **Corpus constraint**: only trained on peer-reviewed, FDA/CDC-approved sources — never the public internet
2. **Abstention policy**: "If medical research is inconclusive regarding a question, the platform will not provide a response" — explicit refusal over confabulation
3. **Citation grounding**: every response includes direct citations with relevancy labels; physicians can drill to the primary source

### Corpus and Freshness

- **~35 million** peer-reviewed publications indexed (as of early 2025; other sources cite ~40M)
- Daily refresh: new publications, FDA updates integrated within one day of online publication
- Key content partnerships: New England Journal of Medicine, JAMA + 11 specialty journals, Wiley, American College of Cardiology, NCCN

---

## Distribution Strategy: Free to Win

The conventional healthcare AI sales motion is institutional procurement — months of meetings, hospital IT approval, budget cycles. OpenEvidence bypassed this entirely:

- Distributed directly through app stores (iOS/Android) — direct-to-physician, not direct-to-hospital
- Priced at **$0** for all practicing clinicians
- Growth vector: word of mouth among physicians (similar to Tesla's early consumer-first marketing)
- NEJM partnership arose organically: "Senior NEJM editorial board members became power users, then approached OpenEvidence about partnership"

**Adoption results:** ~40% of US physicians (as of July 2025); 10-20% began using it "overnight" in some reporting; 65,000 new verified clinicians registering monthly; 8.5 million clinical consultations/month.

The case for free: Nadler frames physicians as consumers, not purchasing agents. Win the doctor first; institutional access and revenue follow.

---

## The Problem Being Solved

Medical knowledge doubles every 5 years (conservative). Two new papers publish every minute. The "long tail" problem: every patient has unique comorbidities and drug interactions that no single physician can stay current on across all specialties.

> "Every single patient is a long tail. Every patient has their own comorbidities and context, and it's just really hard to be a doctor."
> — Daniel Nadler (via Sequoia/OpenEvidence writeup)

The in-flight emergency case study: an internal medicine physician used OpenEvidence during a medical emergency at altitude to determine whether a cancer-immunosuppressed patient required emergency landing. The platform guided treatment without diverting the flight.

---

## Talent Philosophy

Nadler hires for "neuroplasticity" — rapid learning and adaptation — over credential conformity. Co-founders came from Harvard/MIT NLP labs not for institutional prestige but because those environments created high-velocity learners who could compound quickly on hard problems.

---

## Future Vision

"Capturing the collective wisdom of millions of wet brains" — aggregate clinical wisdom from physicians worldwide layered on top of the published literature. Answers augmented by "the aggregate clinical wisdom of some of the best GI doctors in the entire world." Personalized medicine: matching patient-specific factors against the entire knowledge base to generate hyper-tailored care plans.

---

## VERSO RELEVANCE

### [CONFIRMS §5.3 — Tools / MCP vs. Native]
**OpenEvidence's ensemble is a production example of the "native over monolith" principle.** Six specialized models each do one thing well (retrieval, ranking, routing, synthesis, verification) rather than one large model doing everything. This directly maps to Verso's position that tool-calling via native @tool functions beats routing through a single overburdened agent. The hub-and-spoke topology (conductor + specialists) is structurally analogous to Verso's planned orchestrator + sub-agent patterns.
**Verdict:** Confirms §5.3 tool-specialization design and §6.2 multiagent patterns.

### [SHARPENS §5.5 — Evals / Define Outcome]
**Abstention as an eval primitive.** OpenEvidence treats "refuse to answer" as a valid, architecturally enforced output state — not a failure mode. This sharpens Verso's `define_outcome(bounded)` pattern: a bounded outcome should explicitly include "abstain/escalate" as a valid terminal state alongside success and failure. Forcing an answer when evidence is insufficient is worse than no answer in high-stakes domains.
**Verdict:** Sharpen §5.5 — add "abstain" as a first-class outcome in the outcome-definition pattern.

### [NEW-IDEA — §5.4 Memory / §5.2 Context]
**Corpus freshness as a memory-layer concern.** OpenEvidence refreshes its grounding corpus daily. This is the "just-in-time retrieval" problem applied to a continuously updated knowledge base. Verso's 4-tier memory model should explicitly include a "corpus staleness" concern for domain agents: when building a domain-specific agent on top of Verso, the memory layer needs a freshness policy (TTL, delta-refresh) not just retrieval. This is a harness feature — the framework should support declaring corpus refresh cadence alongside the retrieval spec.
**Verdict:** New extension idea for §5.4 memory tier — corpus TTL/freshness as a first-class concern.

### [CONFIRMS §6.3 — Safety]
**"State isolation" between agents prevents error propagation.** OpenEvidence's directed-tree topology with parent-to-child state isolation directly confirms Verso's sub-agents-as-failure-quarantine pattern. If one specialist sub-agent produces a bad answer, it doesn't corrupt the conductor's state. Design principle: sub-agents should never write to shared mutable state; results pass upward through well-typed return values only.
**Verdict:** Confirms §6.3 safety isolation design.

### [SHARPENS §12 — Positioning / Strategy]
**The data-curation-over-monolith bet shows that framework positioning should include the "what data you train/retrieve on" layer.** OpenEvidence wins not because it has a better architecture in the abstract, but because it curates the right data and refuses to train on anything else. For Verso, this suggests that evals and context engineering are not just runtime features — they must support the "define what's in-scope" problem at design time. A Verso agent that cannot declare its grounding corpus is missing a positioning primitive.
**Verdict:** Sharpens §12 competitive positioning — Verso should make "data scope declaration" a first-class design-time concept, not just a runtime retrieval concern.
