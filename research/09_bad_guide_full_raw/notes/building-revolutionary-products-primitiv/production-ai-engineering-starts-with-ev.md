# Production AI Engineering Starts with Evals

**Source:** https://www.latent.space/p/braintrust
**Speaker:** Ankur Goyal (co-founder/CEO, Braintrust)
**Host:** Latent Space (AI Engineer Podcast)
**Date:** October 2024
**Format:** Podcast (~2h)
**Themes:** evals, strategy, model, loop_harness
**Transcript source:** WebFetch of latent.space/p/braintrust (full show notes / summary page)

---

## Full Digest

### Career Arc and the Genesis of Braintrust

Goyal's path: employee #2 at SingleStore (MemSQL) for six years → founded Impira (unstructured-data-as-structured via ML) → eight months at Figma AI → founded Braintrust.

Impira's key failure mode: pre-LLM models lacked power; GPT-3 made their computer-vision approach obsolete by 2022. The deeper lesson was that "technical solutions aren't always business priorities" — customers prefer greenfield innovation over efficiency gains, and deeper customer understanding drives competitive advantage.

Figma AI revealed the friction between integrating AI into high-quality products on periodic release cycles versus a continuous shipping culture.

### The Core Insight: Evals as Organizational Alignment

The fundamental bottleneck Goyal observed in every AI team: teams debate which model/prompt/approach is better without objective measurement. His framing:

> "Evals give you a clear set of tools to get people to agree" on technical direction.

Before evals, debates reduce to anecdotal examples. After evals, discussions use measurable outcomes with clear regressions and improvements visible across experiments.

### Product Evolution (Bottom-Up)

1. **Evals platform** — easiest possible developer experience for software engineers (not ML scientists). Declarative eval specifications that eliminate manual for-loop parallelization.
2. **Logging layer** — automatic ETL from application traces into eval datasets. Traces become training/testing data automatically.
3. **Debugger** — filtering, grouping, regression analysis across experiments.
4. **IDE-like Playground** — durable, shareable, collaborative prompt engineering with embedded tool support.

The trajectory mirrors how a CI/CD system accumulates surface area once adopted.

### Strategic Bets (Against Conventional Wisdom)

**Hybrid on-prem/data-residency from day one.** VCs called this stupid. Goyal pushed it anyway because Airtable, Coda, Stripe, and Zapier demanded data residency. It won enterprise customers who now constitute Braintrust's core (Instacart, Stripe, Zapier, Airtable, Notion, Replit, Brex).

**TypeScript SDK priority.** 75%+ of Braintrust users use the TypeScript SDK. This was a deliberate bet to capture the product-builder segment rather than traditional ML scientists. The insight: "Software engineers can now participate" in model discussions via Transformers, but existing ML tools remained inaccessible to them.

**Evals-first positioning despite VC skepticism.** VCs compared evals to "non-valuable CICD." Goyal proved the pain point was real. The analogy is precisely right, but VCs undervalued CICD in its early days too.

### Market Observations

**Model market share shift:**
- Prior to Claude 3: OpenAI near 100% market share among Braintrust's production customers.
- Post Claude 3.5 Sonnet/Haiku: Claude made significant inroads.
- Open source in production: **<5% and declining.** Inference providers lack API maturity matching OpenAI's platform. Cloud-partner access (Claude via AWS, OpenAI via Azure) shows surprisingly low adoption.

**Fine-tuning reality:**
> "Fine-tuning is a very compelling method that achieves an outcome. The outcome is not fine-tuning."

Fine-tuning is one mechanism for automatic optimization — not a goal. Alternatives (prompt engineering with few-shot examples, in-context learning, DSPy-style prompt optimization) are often superior with large-context models. The trend: most customers want optimization capability, few actively fine-tune in production — and the number is declining.

### Vector DB Decision

Goyal explicitly declined to build a vector DB despite database expertise. Reasoning: vector search is rarely the bottleneck; adjacent problems (permissions, RBAC, joins) dominate complexity. Database success requires storage-execution paradigm integration; vector queries are too constrained for this leverage.

### Customer Stories

**Brian (Zapier) — first user:** Demanded iterative improvements until DX met his standards, forcing product polish that became Braintrust's DX standard.

**Malte Ubl (Vercel):** Articulated the goal as "workflow transformation incorporating evals into mainstream engineering."

**World's Fair:** Zapier's Olmo Robledo embedded at Braintrust during conference prep, surfaced usability bugs while building narratives — serendipitous QA.

### The Discrete vs. Continuous Mathematician Gap

Goyal identifies a cultural gap: ML is the domain of "continuous mathematicians" (NumPy-fluent), while software engineers are "discrete mathematicians" (loop-preferred). Braintrust's eval API is designed to bridge this — declarative specifications that feel like software testing, not statistical experiments.

### Series A

$36M Series A. Demonstrated PMF among top AI teams before the raise.

---

## VERSO RELEVANCE

**[CONFIRMS §5.5 — Evals]** Evals as organizational-alignment mechanism (turning subjective model debates into measurable facts) is exactly the embedded, in-process evals rationale in the PRD — evals live in the development loop, not as a post-hoc audit. Goyal's "anecdote → measurement" flip is the core argument Verso makes for why evals must be first-class.
*No-overkill verdict:* Confirms the evals bet strongly; no new implementation direction needed.

**[SHARPENS §5.5 — Evals]** Goyal's product evolution (evals → logging layer that auto-ETLs traces into datasets → debugger for regression analysis) implies a natural growth path: the logging layer is the bridge between the live agent loop and the eval harness. Verso's observation-masking compaction and append-only history already create this trace surface; surfacing it explicitly as "dataset construction" is a sharpening.
*No-overkill verdict:* Worth noting in eval-pipeline design; no new infra required.

**[SHARPENS §6.4 — Model]** Open source in production at <5% and declining among sophisticated teams (Braintrust's customer base = Stripe, Notion, Replit) directly supports Verso's cross-model failover and role-tiered model design prioritizing frontier APIs over local models. The "cloud-partner access surprisingly low" finding (Claude via AWS, OpenAI via Azure under-adopted) is a flag: direct API access remains the dominant path.
*No-overkill verdict:* Confirms frontier-first model strategy; reinforces not building elaborate local-model infra.

**[NEW-IDEA — §5.5 / §5.1]** The "discrete vs. continuous mathematician" framing suggests Verso's eval API should feel like `assert` / `pytest`, not like a statistical experiment harness. Declarative `define_outcome(bounded)` is on this track; the framing sharpens the DX requirement: eval definitions should read like Python test functions, not YAML configs or NumPy pipelines.
*No-overkill verdict:* DX principle only — no new abstraction needed, just naming/API surface confirmation.

**[CONFIRMS §12 — Positioning]** VCs dismissed evals as "non-valuable CICD." Goyal's counter-narrative — that CICD was undervalued in its early days too — maps to Verso's anti-overkill positioning: the harness is the product, not the loop. The loop is 10 lines; the harness (evals, context engineering, durable seam) is where value accumulates. Identical strategic logic.
*No-overkill verdict:* Direct validation of Verso's positioning thesis.
