# Your AI Product Needs Evals — Hamel Husain (2024)

**URL:** https://hamel.dev/blog/posts/evals/
**Author:** Hamel Husain
**Published:** March 29, 2024
**Format:** Long-form blog post / case study essay
**Status:** read_full

---

## Source Digest

Hamel Husain draws on five years of LLM consulting (30+ production builds, work on CodeSearchNet = GitHub Copilot precursor) to argue that "unsuccessful products almost always share a common root cause: a failure to create robust evaluation systems." The essay is structured around a concrete case study (Rechat / Lucy, a real estate AI assistant) and a three-level evaluation framework. This is the operator's version of "build the verifier first."

### The Core Causal Claim

> "Many people focus exclusively on #3 above [changing behavior — prompt engineering, fine-tuning, coding], which prevents them from improving their LLM products beyond a demo."

The three-activity virtuous cycle that distinguishes exceptional from mediocre products:
1. **Evaluate quality** (tests, tracing)
2. **Debug issues** (logging, inspection)
3. **Change behavior** (prompting, fine-tuning, coding)

Most developers focus only on #3 and end up trapped in whack-a-mole: fix one failure, break something else, no visibility into whether things are net-improving.

**Structural insight:** evals are not a nice-to-have; they are the *coupling* between change and learning. Without them, each iteration is open-loop. With them, each iteration is closed-loop.

### The Three Levels of Evaluation

Husain defines three levels with explicit cost and cadence tradeoffs:

| Level | Type | Cadence | Cost |
|---|---|---|---|
| 1 | Unit tests (assertions) | Every code change | Low |
| 2 | Human & model eval | Set cadence | Medium |
| 3 | A/B testing | After major product changes | High |

Cost ordering: Level 3 > Level 2 > Level 1. Frequency is inverse: run Level 1 constantly, Level 2 periodically, Level 3 rarely. The hierarchy is not "pick one"—you need all three; they catch different failure modes.

---

### Level 1: Unit Tests

Unit tests for LLMs are pytest-style assertions organized around **features** and **scenarios**. Crucially: they serve double duty — beyond testing, they are used for data cleaning and automatic retries.

**Lucy's Listing Finder example:**

Feature: Listing Finder (converts natural language → CRM query)

| Scenario | Assertion |
|---|---|
| One listing matches | `len(listing_array) == 1` |
| Multiple listings match | `len(listing_array) > 1` |
| No listings match | `len(listing_array) == 0` |

A structural assertion (not LLM-graded): regex to prevent UUID exposure in output.

> "Rechat has hundreds of these unit tests. We continuously update them based on new failures we observe in the data as users challenge the AI or the product evolves."

This is a living document of domain knowledge, not a static test suite. The tests encode what "correct" means for this product, and that encoding evolves with usage.

**On synthetic data for test cases:**

> "You don't need to wait for production data to test your system. You can make educated guesses about how users will use your product and generate synthetic data."

LLMs generate 50 variants of user instructions per feature (see the contact management prompt in the essay). The generated test cases are paired: (instruction, follow-up question) to test both action and retention.

**Key heuristic:**
> "One signal you are writing good tests and assertions is when the model struggles to pass them."

If the model passes everything trivially on day one, the tests aren't testing anything hard enough.

**Infrastructure:** Rechat runs tests in CI (GitHub Actions / GitLab Pipelines). Results tracked in a simple analytics system, visualized in Metabase. Minimal friction: use your existing tech stack, don't build bespoke eval tooling.

---

### Level 2: Human & Model Evaluation

**Prerequisites: logging traces.** A trace is a sequence of events—in LLM contexts, typically a conversation. Rechat uses LangSmith (integrated with LangChain) for automatic trace logging. The tool provides human-readable views and interactive prompt iteration.

**The zero-friction imperative:**
> "You must remove all friction from the process of looking at data."

Rechat built a custom trace viewer in Shiny for Python in *less than a day*. Features: tool/feature identification, scenario labeling, source tag (synthetic vs. real user), navigation filters, links to CRM and logging systems. The key property: domain-specific rendering. Generic trace viewers don't show you what matters for your product.

**Labeling approach:** Start with binary good/bad, not granular scoring. Advanced techniques (active learning, consensus voting) can be added later; they don't help until you have volume.

**Data volume guidance:**
> "When starting, you should examine as much data as possible. I usually read traces generated from ALL test cases and user-generated traces at a minimum. You can never stop looking at data—no free lunch exists."

There is no amount of data beyond which you can stop looking. This is a permanent operational commitment, not a startup phase.

**LLM-as-judge setup:**

Three-column spreadsheet workflow:
- Column 1: Model response
- Column 2: Model critique (from more powerful LLM)
- Column 3: Model outcome (binary good/bad)

Human evaluator fills parallel columns for 25–50 examples periodically. This tracks **correlation** between model-based and human evaluation — the goal is to calibrate the LLM judge, not to replace the human.

Tips:
- Use the most powerful affordable model for judging (better reasoning for critique)
- Maintain a mini-eval system tracking evaluator quality (evaluating the evaluator)
- Monitor ongoing model-human agreement periodically
- Raw agreement metrics are misleading with imbalanced datasets; measure precision and recall separately

**Critical warning:**
> "The author cautions against vendor claims eliminating human review. Periodic human sampling remains essential because 'correctness' is subjective."

Vendor claims that LLM judges eliminate human review are false by design—correctness is domain-specific and subjective, and no model can be calibrated without ground truth from a human expert.

---

### Level 3: A/B Testing

Deferred to mature products. Only appropriate after the system proves suitable for real users. Husain defers to Eppo for implementation guidance. The key point: don't start here; start at Level 1.

---

### Evals Unlock Superpowers

#### Fine-Tuning

> "Fine-tuning is best for learning syntax, style, and rules, whereas techniques like RAG supply the model with context or up-to-date facts."

> "99% of the labor involved with fine-tuning is assembling high-quality data that covers your AI product's surface area."

The key insight: eval infrastructure provides fine-tuning data *automatically*. Level 1 assertions filter bad examples; Level 2 human ratings label quality; the trace database becomes a curated training corpus. Rechat resolved failure modes through fine-tuning that were impossible to solve with prompting alone.

Synthetic data generation for fine-tuning is nearly the same pipeline as for test case generation. The Listing Finder fine-tuning prompt generates 50 NL search query variants.

#### Debugging

> "There is an incredibly large overlap between the infrastructure needed for evaluation and that for debugging."

The same searchable trace database, the same assertions, the same domain-specific viewer, the same labeling system — these serve debugging directly. The eval infrastructure is also the debug infrastructure. Building them separately is redundant.

---

### Key Design Principles (Extracted)

1. **Minimum viable eval is unit tests + trace logging.** Everything else builds on this.
2. **Domain-specific rendering beats generic tooling.** Build a thin viewer for your data; don't rely on vendor dashboards alone.
3. **LLM judges require calibration against human ground truth.** Track precision/recall, not raw agreement.
4. **Eval, debug, and fine-tuning infrastructures overlap ~80%.** Design them as one system from the start.
5. **Start with binary good/bad labels.** Don't let scoring granularity become a blocker.
6. **Synthetic data is the unlocker for testing pre-launch.** Generate before you have users.
7. **The eval system is the product's domain knowledge, encoded.** Each test added is a captured business rule.

---

## Selected Verbatim Quotes (Load-Bearing)

1. "Unsuccessful products almost always share a common root cause: a failure to create robust evaluation systems."
2. "Many people focus exclusively on #3 above, which prevents them from improving their LLM products beyond a demo."
3. "One signal you are writing good tests and assertions is when the model struggles to pass them."
4. "You must remove all friction from the process of looking at data."
5. "You can never stop looking at data—no free lunch exists."
6. "Rechat has hundreds of these unit tests. We continuously update them based on new failures we observe."
7. "99% of the labor involved with fine-tuning is assembling high-quality data."
8. "Fine-tuning is best for learning syntax, style, and rules, whereas RAG supplies context or up-to-date facts."
9. "There is an incredibly large overlap between the infrastructure needed for evaluation and that for debugging."
10. "Correctness is subjective." (on why LLM judges cannot replace humans)

---

## VERSO RELEVANCE

### Finding 1: The three-activity cycle as the structural argument for Verso's evals layer
**Tag:** [CONFIRMS §5.5 evals]
Husain's three-activity cycle (evaluate → debug → change) is the production-operator's restatement of Verso's "evals+reliability" first-class positioning. The "many people only do #3" observation directly explains *why* other frameworks bury evals: they were designed by people optimizing for #3 (changing behavior) and never made the other two first-class. Verso's design explicitly inverts this.
**Verdict:** confirm — use as external evidence in §5.5 and §12 positioning that the market failure is structural, not accidental.

### Finding 2: Eval + debug infra overlap ~80% — design as one system
**Tag:** [SHARPENS §5.5 evals]
> "There is an incredibly large overlap between the infrastructure needed for evaluation and that for debugging."

This sharpens the design of Verso's eval harness: the trace database, domain viewer, and assertion system should *also* be the debugging surface. The same `define_outcome` / judge-panel infrastructure that runs evals should be the first thing you reach for when debugging a failing run. Design-as-one from the start; don't add "debug mode" as an afterthought. This is NEW in the sense that the harvest captured `define_outcome` and judge panels as eval constructs but did not explicitly frame them as the debugging surface too.
**Verdict:** adopt-now — unify eval and debug infrastructure in §5.5 spec; the trace viewer is both.

### Finding 3: Domain-specific rendering is the zero-friction key
**Tag:** [NEW-IDEA §5.5 evals]
The most under-appreciated recommendation: Rechat built a custom trace viewer in *less than a day* using Shiny for Python. The insight is that domain-specific rendering is necessary for any eval system to be used. Generic vendor dashboards have high friction because they don't know what "a good response" looks like for your domain. Verso should ship: (a) a programmable render hook for traces (not a fixed schema), (b) opinionated defaults for the common case (tool call in/out, final answer, step count), and (c) easy override for domain-specific display. The render hook IS a UX decision.
**Verdict:** adopt-now — add programmable trace renderer as a first-class §5.5 component. This is not in the harvest.

### Finding 4: LLM-as-judge calibration via precision/recall, not raw agreement
**Tag:** [SHARPENS §5.5 evals]
The harvest captured "judge-panel evals + define_outcome(bounded)." Husain sharpens the evaluation of the *evaluator*: raw agreement with human labels is misleading on imbalanced datasets; precision and recall must be tracked separately. Additionally: maintain a "mini-eval system tracking evaluator quality" — the evaluator itself needs to be evaluated. This is a meta-eval loop that Verso's `define_outcome` infrastructure should natively support.
**Verdict:** sharpen — add precision/recall tracking for judge calibration to §5.5; add the meta-eval concept explicitly.

### Finding 5: Synthetic test data unblocks pre-launch quality loops
**Tag:** [SHARPENS §5.5 evals]
> "You don't need to wait for production data to test your system."

The harvest already includes mention of evals but does not specifically address the pre-launch problem. Husain is explicit: you can generate synthetic user inputs via LLM before you have real users. Verso's eval harness should ship with: a `generate_test_cases(feature_description, n=50)` utility or pattern that helps developers bootstrap their test suite before launch. This is the entry ramp into the eval system.
**Verdict:** adopt-now — add synthetic test case generation as a first-class pattern in §5.5; consider a `verso eval bootstrap` CLI command.

### Finding 6: Fine-tuning / RAG decomposition clarifies Verso's memory architecture
**Tag:** [SHARPENS §5.4 memory]
> "Fine-tuning is best for learning syntax, style, and rules, whereas RAG supplies context or up-to-date facts."

This is a clean decomposition that maps onto Verso's 4-tier memory architecture: fine-tuned model weights = tier 0 (implicit model knowledge); RAG / just-in-time retrieval = tiers 2–3 (working memory, external knowledge). The harvest has these tiers but doesn't articulate the *functional distinction* as clearly as Husain. This sentence should be in §5.4 design rationale: each tier has a different purpose, and conflating them leads to using RAG for things that need fine-tuning and vice versa.
**Verdict:** sharpen — add the Husain decomposition sentence to §5.4 memory tier rationale.

### Finding 7: The "update tests based on new failures" living-document principle
**Tag:** [NEW-IDEA §5.5 evals]
> "We continuously update them based on new failures we observe in the data as users challenge the AI or the product evolves."

The harvest treats evals as static artifacts. Husain makes them a living knowledge base. Each production failure that is diagnosed should immediately produce a new unit test. The eval suite is the encoded domain knowledge of what has gone wrong. Verso's harness should support a first-class `verso eval capture <run_id>` command that converts a failed production run into a test case.
**Verdict:** adopt-now — add "failure-to-test-case" capture as a §5.5 workflow primitive; this closes the production-to-eval feedback loop.

### Finding 8: The "model struggles to pass" quality signal for test design
**Tag:** [NEW-IDEA §5.5 evals]
> "One signal you are writing good tests and assertions is when the model struggles to pass them."

This is a non-obvious quality signal for the *tests themselves*. If a test passes trivially, it is not covering a hard case. Verso's harness should encourage or expose this: run the eval suite against a deliberately weakened model (or no-op tool) to verify that the assertions actually fail when they should. This is the "test your tests" principle applied to LLM evals.
**Verdict:** adopt-now — add a "test hardness check" capability to §5.5 (run suite against baseline/stub to verify assertions are discriminating).

---

## Summary Verdict

This is the most directly actionable source in the batch for Verso's §5.5 evals design. The three-activity cycle is the product-level argument; the three-level hierarchy is the engineering taxonomy; the domain-specific renderer is the overlooked UX insight; the "failure-to-test-case" capture pattern closes the production loop. Six of the eight findings are NEW or SHARPEN, not mere confirmations. The key structural argument — eval + debug infrastructure overlap 80% — should reshape how the §5.5 spec is written: it is one unified system, not two separate concerns.
