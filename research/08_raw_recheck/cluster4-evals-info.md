# Cluster 4 — Evals Wedge (§5.5) + Memory/Retrieval (§5.4) — Raw Recheck

**Date:** 2026-06-12
**Method:** Full raw text fetched (curl, tag-stripped) for all 4 sources — not summaries. Verbatim quotes below.
**Verso anchors read:** `research/06_design_resolutions/evals-trace.md` (§5.5), `research/06_design_resolutions/memory.md` + `research/06_design_resolutions/retrieval-backend.md` (§5.4).
**Scope:** report DELTAS only vs the existing harvest (Hamel slogan, judge panels, RRF k=60, Exa highlights, typed-entity RAG already covered).

Tag key: [CONFIRMS §x] / [CONTRADICTS §x] / [SHARPENS §x] / [NEW-IDEA].

---

## Source 1 — Shunyu Yao, "The Second Half" (https://ysymyth.github.io/The-Second-Half/)

Reachable. Full text read (≈2,600 words, blog post dated April 10, 2025). This is the single most important source for the eval wedge thesis.

### Load-bearing specifics (verbatim)

1. **The thesis, stated flatly** — [CONFIRMS §5.5 wedge; RAISES priority]
   > "The second half of AI — starting now — will shift focus from solving problems to defining problems. **In this new era, evaluation becomes more important than training.** Instead of just asking, 'Can we train a model to solve X?', we're asking, 'What should we be training AI to do, and how do we measure real progress?'"

   And the kicker on *who does this work*:
   > "To thrive in this second half, we'll need a timely shift in mindset and skill set, ones perhaps **closer to a product manager**."

   This is the exact argument that makes "evals+reliability in the box" a wedge and not a feature. Yao — who built ReAct, SWE-bench, tau-bench — is saying the frontier *value* is migrating into the eval layer. Verso's bet that evals are a first-class subsystem (not an afterthought bolted onto a tracing tool) is precisely this thesis instantiated as a framework.

2. **Why incremental method work is dead, and eval-authoring is what's left** — [CONFIRMS §5.5; NEW-IDEA for entry point]
   > "The recipe has essentially standardized and industried benchmark hillclimbing without requiring much more new ideas. As the recipe scales and generalizes well, **your novel method for a particular task might improve it by 5%, while the next o-series model improve it by 30% without explicitly targeting it.**"

   The prescription:
   > "I think we should fundamentally **re-think evaluation**. It means not just to create new and harder benchmarks, but to **fundamentally question existing evaluation setups and create new ones**, so that we are forced to invent new methods beyond the working recipe."

   The new game loop (verbatim):
   > "We develop novel evaluation setups or tasks for real-world utility. / We solve them with the recipe or augment the recipe with novel components. Continue the loop."

   Note the ordering: **eval-authoring comes FIRST in the loop**, the solve comes second. This is "build-the-verifier-first" (Verso §13 invariant) stated by an independent authority.

3. **The two hidden assumptions — these map directly onto Verso primitives** — [SHARPENS §5.5 + §5.4]
   > "Evaluation 'should' run automatically, so typically an agent receives a task input, do things autonomously, then receive a task reward. But in reality, **an agent has to engage with a human throughout the task** — you don't just text customer service a super long message, wait for 10 minutes, then expect a detailed response... new benchmarks are invented to either engage real humans (e.g. Chatbot Arena) or user simulation (e.g. tau-bench) in the loop."

   > "Evaluation 'should' run i.i.d. If you have a test set with 500 tasks, you run each task independently... But in reality, you solve tasks sequentially rather than in parallel. A Google SWE solves google3 issues increasingly better as she gets more familiar with the repo, but **a SWE agent solves many issues in the same repo without gaining such familiarity. We obviously need long-term memory methods** (and there are), but academia does not have the proper benchmarks to justify the need, or even the proper courage to question i.i.d. assumption."

   The i.i.d. critique is a direct CONFIRM of Verso's §5.4 memory bet ("agent gets better across runs" is the cross-run memory thesis) AND a critique of Verso's own §5.5 offline-eval design, which currently runs `for each DatasetItem: run the agent` independently (evals-trace.md Decision 5/6). See "Sharpen" below.

   The "utility problem" framing:
   > "AI has beat world champions at chess and Go, surpassed most humans on SAT and bar exams... But the world hasn't changed much, at least judged by economics and GDP. I call this **the utility problem, and deem it the most important problem for AI**... the root cause of this problem might be deceptively simple: **our evaluation setups are different from real-world setups in many basic ways.**"

### Answer to Question A (does this RAISE the eval wedge priority; missing primitive?)

**Yes — strongly, and it names a missing primitive.** The eval wedge is not just "important," Yao argues it is where frontier value is *relocating*. Two concrete implications:

- **The eval is the spec.** Verso's three tiers (`eval.unit` → `eval.judge` → `eval.experiment`) are the *grading* machinery, but Yao's loop starts one step earlier: **authoring the evaluation setup**. The missing first-class entry point is **eval-authoring as the way you start a project**, not a thing you add after the agent works. Verso has `agent.define_outcome(rubric, max_iterations=3)` — which is exactly the right shape (the rubric IS a tiny eval authored up-front and used as the spec the agent must satisfy). The NEW-IDEA delta: **promote `define_outcome` / rubric-authoring to the documented `agent` starting point** ("write the outcome rubric first, then the agent") so the framework's narrative matches "build the eval, not the next method." This is a docs/DX + ordering change, not new engine code — fits "no overkill."

- **Verso's offline eval silently bakes in the i.i.d. assumption Yao says to question.** evals-trace.md Decision 6 runs each `DatasetItem` independently. That is correct for unit/judge CI, but it cannot express "the agent should get *better* across a sequence" — the exact memory utility Verso §5.4 sells. SHARPEN: reserve a **sequential/stateful eval mode** (a dataset whose items share one persistent `Memory` scope across the run, measuring trajectory improvement) as a named future hook on `EvalRun`. Do not build it for v1 — but the interface should not assume i.i.d. forever. (Lock-interface-defer.)

**No-overkill verdict: ADOPT NOW (the framing + the docs/ordering of `define_outcome` as entry point); LOCK-INTERFACE-DEFER the sequential/stateful eval mode.** No new heavy machinery — Verso already has the pieces; this raises confidence the wedge is correctly chosen and sharpens how it is presented and what the eval interface must not foreclose.

---

## Source 2 — Hamel Husain, "Your AI Product Needs Evals" (https://hamel.dev/blog/posts/evals/)

Reachable. Full text read (the canonical long-form, March 29 2024). The harvest already has the slogan; the DELTA is the concrete **workflow** and several specifics the slogan omits.

### Load-bearing specifics (verbatim)

1. **The three-level taxonomy with explicit cost-ordered cadence** — [CONFIRMS §5.5 three-tier design, near-exactly]
   > "There are three levels of evaluation to consider: Level 1: Unit Tests / Level 2: Model & Human Eval (this includes debugging) / Level 3: A/B testing. The cost of Level 3 > Level 2 > Level 1. This dictates the cadence... **I often run Level 1 evals on every code change, Level 2 on a set cadence and Level 3 only after significant product changes.**"

   This is a 1:1 match for Verso's `eval.unit()` (CI/every change) → `eval.judge()` (cadence) → `eval.experiment()` (post-ship A/B). Verso's tier model is Hamel's model with names. Strong independent CONFIRM.

2. **The feature × scenario matrix — Verso's `eval.unit` shape is literally this** — [CONFIRMS §5.5 "feature×scenario matrix"]
   > "The most effective way to think about unit tests is to **break down the scope of your LLM into features and scenarios.** For example, one feature of Lucy is the ability to find real estate listings, which we can break down into scenarios..."

   The verbatim assertion table (this is the Lucy/Rechat case the harvest references, now with the actual assertions):
   > | Only one listing matches user query | `len(listing_array) == 1` |
   > | Multiple listings match user query | `len(listing_array) > 1` |
   > | No listings match user query | `len(listing_array) == 0` |

   Plus the generic UUID-leak regex assertion (CONFIRMS Verso's generic-assertion idea + the `verify_grounding`/PII-leak motivation): a regex over the message asserting `matches.length == 0` for exposed UUIDs, because "CRM results returned to the LLM contain fields that shouldn't be surfaced to the user."

3. **Assertions are reused beyond tests — the load-bearing design note** — [SHARPENS §5.5 Decision 7]
   > "Unlike typical unit tests, you want to **organize these assertions for use in places beyond unit tests, such as data cleaning and automatic retries (using the assertion error to course-correct) during model inference.**"

   This is a direct CONFIRM + SHARPEN of Verso's `define_outcome` bounded generate→grade→revise loop: Hamel independently says the *same* assertion object should drive both CI and runtime self-correction. Verso's `Assertion` (evals-trace.md Decision 7) should be the *same* object usable as a `define_outcome` stop condition. Worth making explicit in the API: one `Assertion`, two call sites (CI gate + runtime course-correct).

4. **Why generic frameworks fail (the verbatim line the harvest paraphrased)** — [CONFIRMS §13 "compose behind locked interfaces, build only VersoSpan/VersoScore"]
   > "**Don't rely on generic evaluation frameworks to measure the quality of your AI. Instead, create an evaluation system specific to your problem.**" [from the Conclusion takeaways]

   And the data-friction principle:
   > "**You must remove all friction from the process of looking at data.** This means rendering your traces in **domain-specific ways.** I've often found that it's better to build my own data viewing & labeling tool so I can gather all the information I need onto one screen."

   Tension worth noting: Hamel says *don't rely on generic frameworks* — Verso §13 says *compose* Langfuse/autoevals/Braintrust behind locked interfaces. These are reconcilable: Hamel's target is generic *metrics* (off-the-shelf scorers that don't know your domain), not generic *plumbing* (trace store, score object). Verso composes the plumbing and ships domain-shaped primitives (`VersoScore`, trajectory assertions, `define_outcome`). But the DELTA is a caution: **Verso must not ship a bag of generic built-in scorers as the headline** — the headline is "author *your* assertions / *your* rubric." The built-in scorers (Factuality, GEval, etc. in Decision 4) are the floor, not the product.

5. **The error-analysis → data-curation flywheel + the "look at your data" mandate** — [SHARPENS §5.5; the `correction` flywheel]
   > "Rechat has **hundreds of these unit tests. We continuously update them based on new failures we observe in the data** as users challenge the AI or the product evolves."
   > "When starting, you should examine as much data as possible. I usually read traces generated from ALL test cases and user-generated traces at a minimum. **You can never stop looking at data—no free lunch exists.**"
   > "**99% of the labor involved with fine-tuning is assembling high-quality data** that covers your AI product's surface area. However, if you have a solid evaluation system... you already have a robust data generation and curation engine!"

   This is the exact justification for Verso's `VersoScore.correction` field (HITL→dataset flywheel, evals-trace.md Decision 1) and the synthetic-test-case generation. CONFIRM that the flywheel field is load-bearing, not cosmetic. The workflow Hamel actually runs: failures observed in traces → new assertions appended → synthetic cases generated by an LLM ("Write 50 different instructions...") → run through Level 1/2 to filter → curated dataset.

6. **Judge-alignment is measured with precision/recall, NOT raw agreement** — [SHARPENS §5.5 judge design — a correctness fix]
   > "**using raw agreement is generally not recommended and can be misleading when classes are imbalanced. Instead, you should typically measure precision and recall separately** to get a more accurate picture of your judge's alignment."

   Verso's judge design (evals-trace.md Decision 4) ships scorers and a panel but the human-alignment *measurement* is under-specified. SHARPEN: when Verso surfaces "judge ↔ human alignment," it should compute **precision/recall (and TPR/TNR), not accuracy**, because eval datasets are usually class-imbalanced (most traces pass). Cheap to get right, expensive to retrofit into dashboards. Add to `ScoreSummary` or the alignment report.

### No-overkill verdict

**ADOPT NOW (all confirmations + the two sharpenings: one-Assertion-two-call-sites, and precision/recall for judge alignment).** Both sharpenings are small and correctness-preserving. No new subsystem. RESIST any urge to ship a big generic-scorer catalog as the product surface — Hamel's whole point is the opposite.

---

## Source 3 — Ankur Goyal (Braintrust), Latent.space podcast (https://www.latent.space/p/braintrust)

Reachable — the **full transcript is public** (not paywalled; "sign in / paywall" strings are nav/CTA chrome, the entire ≈1h57m transcript renders). Read in full. Oct 11 2024.

### Load-bearing specifics (verbatim)

1. **Evals as organizational alignment — the exact mechanism (subjective debate → measurable fact)** — [CONFIRMS §5.5 wedge framing; NEW-IDEA for positioning]
   > "And so you end up going in circles. **If you introduce evals into the mix, then you sort of change the discussion from being hypothetical or one example and another example into being something that's extremely straightforward and almost scientific.** ... it gives you a framework to have that. And ... aside from the fact that it literally lets you run the sort of scientific process of improving an AI application, **organizationally, it gives you a clear set of tools, I think, to get people to agree.** And ... in the absence of evals, what I saw at Empira, and I see with almost all of our customers before they start using BrainTrust, is **this kind of stalemate between people on which prompt to use or which model to use or which technique to use, that once you embrace engineering around evals, it just goes away.**"

   This is a *second* axis of value beyond "catch regressions": evals are how a *team* stops arguing from anecdotes. NEW-IDEA for Verso's pitch: the wedge is not only "reliability in the box," it is "**evals turn model/prompt debates into measurable facts**" — an organizational, not just technical, sell. Costs nothing to adopt as positioning; reinforces why eval==run matters (the fact must come from the production path, or the "scientific" claim is hollow).

2. **The Eval() primitive — Verso's `evals.run()` is the same shape** — [CONFIRMS §5.5 Decision 6 eval==run + Decision 7 API]
   > "you just create something called eval, and you give it an argument which has some data, then you give it **a task function, which is some function that takes some input and returns some output. Presumably it calls an LLM, nowadays it might be an agent**, ... and then **one or more scoring functions.** And then Braintrust basically takes that specification of an eval and then runs it as efficiently and seamlessly as possible."

   And the declarative-data insight (this is a genuine design idea):
   > "because this data structure is totally declarative, **an eval is actually not just a code construct, but it's actually a piece of data.** So when you run an eval in Braintrust now, you can actually optionally bundle the eval and then send it... you can run an eval in your code base, save it to Braintrust, and then **hit it with an API and just try out a new model.**"

   Verso's `EvalRun` (data, agent/task, scorers) is exactly `{data, task, scoring_fns}`. CONFIRM the signature is industry-canonical. The DELTA worth weighing: Braintrust treats the eval as **serializable data** so a saved eval can be re-run against a new model from the UI/API. Verso's `EvalRun` + `DatasetRunItem` snapshot already serializes inputs; making the whole eval-spec (task ref + scorers + dataset) a portable record would enable "re-run last eval on `gpt-X`" — a small, high-leverage addition. (Lock-interface-defer: keep `EvalRun` serializable enough to support this later.)

3. **Regression analysis is the actual job — granular, per-case, not a single number** — [SHARPENS §5.5 `compare()` / p50/p80]
   > "you'd look at our web UI and sort of see a chart... But then you wanted to interrogate that and say, **okay, great, 8% better. Is that 8% better on everything, or is that 15% better and 7% worse? And where it's 7% worse, what are the cases that regressed?** How do I look at the individual cases? They might be worse on this metric. Are they better on that metric?"

   Verso's `result.compare(baseline_run_id)` (evals-trace.md Decision 6) returns a regression report — CONFIRM that's the right primitive. SHARPEN: the report must be **per-case diff-able (which items regressed, on which metric), not just aggregate deltas.** Verso surfaces p50/p80 horizons (good for "did the distribution move") but the per-case regression list ("these 3 items got worse") is what makes it actionable. Ensure `compare()` yields the item-level set, not only summary deltas.

4. **On-prem / data-residency from day zero — the moat** — [CONFIRMS §13 deployment posture; market evidence]
   > "everyone thought this hybrid thing was stupid. But I was talking to customers and Zapier was our first user and then Coda and Airtable quickly followed. And **there was just no chance they would be able to use the product unless the data stayed in their cloud.** ... it never felt like a question to me."
   > "we literally engineered brain trust from day zero to have this model. If you treat it as an opportunity and then engineer a very, very good solution around it... **we viewed it as an opportunity rather than a challenge.** ... **serverless is probably one of the most important unlocks for us because it sort of allows us to bound failure into something that doesn't require restarting servers.**"

   For an OSS Python framework this is somewhat native (the user runs it in their own process/cloud already). But it CONFIRMS a design constraint: Verso's eval/trace store must be **operable entirely inside the customer boundary** — the dev SQLite tier and the prod ClickHouse/Postgres tier (evals-trace.md Decision 8) both satisfy this; the judge-panel default must never *force* egress to a vendor. Verso's "judge panel pluggable, no vendor lock" (§5.5) is the right call; this is market validation that data-residency is a buying gate, not a nice-to-have.

5. **Market data point (DELTA, useful for thesis-sizing)** — [NEW-IDEA / context]
   > swyx: "What % of your workload is open source?" / Goyal: "Among customers running in production, **it's less than 5%**" — and the writeup's gloss: "Open source model adoption is <5% and **DECLINING**... virtually none of Braintrust's customers are really finetuning open source models for cost, control, or privacy."
   And on fine-tuning as a product:
   > "**Fine-tuning is not a viable standalone product** ... The outcome is not fine-tuning, it is can I automatically optimize my use case to perform better if I throw data at the problem?"

   Implication for Verso: do not over-invest the eval flywheel in *fine-tuning* outputs specifically — the durable outcome is "optimize the use case," of which fine-tuning is one path (and a declining one among production teams). Verso's flywheel (`correction` → dataset) is correctly *outcome-agnostic* (dataset can feed prompt-opt, few-shot, or FT). Keep it that way; resist building FT-specific tooling in v1.

### No-overkill verdict

**ADOPT NOW the positioning ("evals turn debates into measurable facts") and the per-case-regression sharpening of `compare()`. LOCK-INTERFACE-DEFER the serializable/portable eval-spec ("re-run this eval on a new model"). RESIST fine-tuning-specific flywheel tooling.** Nothing here demands new heavy engine work; the `compare()` per-case-diff sharpening is the only concrete code nudge and it is small.

---

## Source 4 — Hebbia, "Goodbye, RAG" (https://www.hebbia.com/blog/goodbye-rag-how-hebbia-solved-information-retrieval-for-llms)

Reachable. Full text read (Adithya Ramanathan, Feb 14 2025). **The raw text materially changes the verdict vs the summary** — Hebbia is NOT throwing out vector retrieval at corpus scale; it is replacing vector *passage-ranking* with model passes *inside an already-scoped document/dataroom*, and **explicitly keeps classical hybrid search for document retrieval.** This is the crux for Question B.

### Load-bearing specifics (verbatim)

1. **The precise critique of vector RAG — two conflations** — [SHARPENS §5.4; partial CONTRADICT of naive vector-default]
   > "**Information that conveyed document filtering was conflated with information relevant to the ideal semantic search query.** For example, rarely in a 10Q filing does Pepsi make a statement that says 'Pepsi's revenue in 2022 is $X.' Rather, they may state 'Revenue was $X'."
   > "**Portions of the query lead to hits in incredibly dense portions of the vector space.**" (many growth rates coexist in one dense region → cosine can't separate them)
   > "Regardless of our decomposition process or filter generation process, **the embedding process struggled to appropriately encapsulate chains of thought or conditional logic.** How do you embed a query to find a section that you don't know about yet?"
   > "**Traditional RAG systems conflate passage and document retrieval.**" / "**RAG lacks the sophistication to answer complicated and meaningful user queries.**"

   Where it works vs fails (verbatim):
   > Works: "What was Pepsi's revenue in 2022?", "Who are the key members of the deal team?"
   > Fails: "What sounds like a lie in the latest Disney earnings?", "What loopholes exist in this NDA?", "If the section says this, go to the section that it refers to and check the definition, otherwise if it says this, evaluate this other clause."

2. **The Full Attention pipeline (precise, 5 steps) — operates over a document, not a corpus** — [NEW-IDEA; the agentic-retrieval shape]
   > "- **Document Chunking:** chunking a document into contextually dense, temporally connected, and modally homogenous components that were all **smaller than a context window.**
   > - **Component Gathering:** **Parallelizing across these chunks, our system then identifies the document components that benefit from full attention** in relation to the original question.
   > - **Synthesis:** we run a final pass over the selected document pieces to synthesize a single comprehensive answer.
   > - **Highlighting:** we use this final response and **reverse engineer the highlight worthy document text** [for citations].
   > - **Validation:** ... programmatic and probabilistic measures to mitigate hallucination including leveraging **token level log-likelihoods** and text/character level heuristics."

   Decouple objectives (verbatim):
   > "we wanted to explicitly **decouple the objectives of document retrieval from document understanding.** ... **document retrieval is secondary to the need for pristine question understanding & answering.** Finding the right document did not matter if you'd eventually fail to answer."

   Scaling = scope the data, then full-attention the relevant subportion (verbatim):
   > "At each phase ... there is a total volume of data and a **relevant subportion of data that requires the application of Full Attention.** Hebbia's goal is to design a collection of systems that, depending on the data volume ... are able to **identify the relevant portion of data needing full attention.**"
   > Multi Document Agent: "apply self attention against a **concatenated collection of attention-needy components from all of the provided documents.**"
   > Matrix Agent: coordinates per-document QA, then "treat the generated total answer space (a Matrix) as the domain... **cell selection is the process of gathering attention to needy components.**"

3. **THE decisive caveat the summary buried — Hebbia STILL uses vector/hybrid for document retrieval** — [resolves Question B; protects §5.4]
   > "Hebbia has improved staggeringly with regards to document understanding, yet **document retrieval remains pinned to the same classic technologies. Today, we enable traditional document retrieval mechanisms in the Hebbia application, leveraging classical hybrid search approaches and filtering techniques**, but we are grossly unsatisfied with our innovation here."
   > "We believe that **vector and full text representation of documents will play a part in the solution but likely not be the entire solution.** Retrieval systems should be adaptive and consider the outcomes of individual document understanding processes."

   So Hebbia did NOT replace vector search with model passes. It split the problem: **(a) document retrieval = still hybrid vector+lexical+filter** (exactly Verso §5.4's RRF(semantic+BM25)+typed filters), and **(b) document *understanding*/answer-synthesis = parallel model passes** over the scoped set. The "goodbye RAG" is a goodbye to *vanilla single-cosine-score passage RAG as the whole answer*, not to vector retrieval as the candidate-gatherer.

### Answer to Question B (does this challenge Verso's RRF/vector-first §5.4? reserve an agentic-retrieval path?)

**It does NOT contradict §5.4's retrieval default — it CONFIRMS it for the layer §5.4 actually covers (candidate gathering), and it identifies a genuinely DIFFERENT layer (answer synthesis over scoped chunks) that §5.4 does not own.** Specifically:

- **Verso's §5.4 default is correct and Hebbia agrees where it matters.** Hebbia's "works" cases ("Pepsi revenue 2022", "key members of the deal team") are exactly factoid lookups where hybrid vector+BM25+filter wins — Verso's RRF(k=60) + typed filters + asymmetric embeddings is the right default and Hebbia *kept the same thing* for document retrieval. No CONTRADICT. The one SHARPEN: Hebbia's conflation critique ("document-filter info vs passage-relevance info collide in one query vector") is a real failure of *naive single-vector* search — Verso already mitigates it with **typed-memory filters pushed to the backend** (retrieval-backend.md Decision 10) and **asymmetric query/document embeddings** (Decision 5). Worth a doc note: Verso's filter-before-ANN is the structural answer to Hebbia's conflation problem.

- **The thing Hebbia built is NOT retrieval — it's bounded-fan-out reasoning over already-retrieved chunks.** Step 2 ("parallelize across chunks, identify components that benefit from full attention") + Step 3 ("synthesize") is a **map-select-reduce over a scoped document**, with citations reverse-engineered after. Verso *already has the primitive for this*: `fan_out` (parallel sub-tasks over chunks) + a synthesis step + `verify_grounding` (claims tied to retrieved content + provenance — which is exactly Hebbia's "reverse engineer the highlight worthy document text" + log-likelihood validation). So an agentic/iterative *answer* path is expressible in Verso **today as a composition** (retrieve → `fan_out` model passes → synthesize → `verify_grounding`) without a new retrieval subsystem.

- **Should §5.4 reserve an "agentic/iterative retrieval" path for v1?** No — that would be overkill and is the wrong layer. The correct posture: (1) keep RRF/vector+BM25+filter as the §5.4 retrieval default (unchanged); (2) recognize that "Full Attention over a scoped set" is an **agent/orchestration pattern, not a memory-backend feature** — it belongs to `fan_out` + `verify_grounding`, which exist; (3) the ONE forward-looking note worth locking: Hebbia's closing thesis — "**retrieval systems should be adaptive and consider the outcomes of individual document understanding processes**" — i.e. feed answer-quality signals back to bias future retrieval. That is a *learned/feedback retrieval* idea. Verso should NOT build it in v1 but the `Memory`/retrieval interface should not foreclose passing relevance feedback (the `access_count`/`proof_count` boosts in memory.md Decision 6 are a primitive seed of exactly this).

### No-overkill verdict

**RESIST building an "agentic retrieval" backend in §5.4 — it is overkill and mislocated.** ADOPT NOW (doc-level): position "parallel model passes over scoped chunks" as a **composition of existing primitives** (`fan_out` + synthesis + `verify_grounding`), and add a doc note that Verso's filter-before-ANN + asymmetric embeddings already answer Hebbia's two conflation failures. LOCK-INTERFACE-DEFER: keep a seam for feedback-biased retrieval (answer-quality → retrieval priors); the memory boost fields already gesture at it. §5.4's vector/RRF default stands — Hebbia is not a counterexample once you read past the title.

---

## Cross-source synthesis (the 3 highest-value deltas)

1. **The eval wedge is correctly chosen and UNDER-sold — fix the framing, not the engine (Yao + Braintrust).** Two independent authorities (Yao: frontier value moves to defining/evaluating; Goyal: evals turn team stalemates into "almost scientific" facts) say the eval layer is where value concentrates. Verso's tiers already match Hamel's three levels 1:1. The missing move is **making eval/rubric-authoring the documented entry point** (`define_outcome` first), and pitching evals as organizational alignment, not just regression-catching. ADOPT NOW (framing + DX/ordering). No new subsystem.

2. **Two small correctness sharpenings to §5.5, both cheap-now/expensive-later (Hamel + Braintrust).** (a) Judge↔human alignment must be **precision/recall, not raw agreement** (imbalanced classes). (b) `compare()` must yield a **per-case regression list** ("which items got worse on which metric"), not just aggregate p50/p80 deltas. Both are dashboard/report-shape decisions hard to retrofit.

3. **Hebbia does NOT threaten §5.4 — read past the title (Hebbia).** It keeps hybrid vector+lexical+filter for document *retrieval* and adds parallel model passes for answer *synthesis* — a `fan_out` + `verify_grounding` composition Verso already supports. §5.4's RRF/vector default stands. RESIST an agentic-retrieval backend in v1; keep a seam for feedback-biased retrieval (the `proof_count`/`access_count` boosts are the seed).

### Net "no-overkill" ledger
- ADOPT NOW: `define_outcome`/rubric-first as documented entry point; "evals as alignment" positioning; precision/recall for judge alignment; per-case diffs in `compare()`; doc note that filter-before-ANN + asymmetric embeddings answer Hebbia's conflation; one-`Assertion`-two-call-sites (CI + runtime course-correct).
- LOCK-INTERFACE-DEFER: sequential/stateful (non-i.i.d.) eval mode on `EvalRun`; serializable/portable eval-spec ("re-run on new model"); feedback-biased retrieval seam.
- RESIST: agentic-retrieval backend in §5.4 v1; generic-scorer catalog as the headline product; fine-tuning-specific flywheel tooling.
