# Transcripts — Stanford + Palantir

---

## TRANSCRIPTS_STANFORD.md

**Source:** 19 lectures/talks from Stanford CS221, CS224R, CS230, CS25 V2/V3/V4/V5, CME295 — processed April 2026. Covers RL theory, RLHF/DPO, reasoning, agent architectures, LLM fundamentals, and Anthropic/OpenAI practitioner perspectives.

---

### Agent Loop Shape

- **Moroni's 4-step agent anatomy (CS230):**
  1. **Intent understanding** — LLM reads task, determines goal (not planning yet)
  2. **Planning** — enumerates available tools, breaks task into sub-steps, produces execution plan
  3. **Execution** — tools called in sequence, results gathered, state maintained across calls
  4. **Reflection** — did we accomplish intent? If no: diagnose failure, loop back to planning. If yes: return.
  - "An agent is just those four steps."
  - Debugging protocol: if agent fails, identify which step failed → targeted fix (rephrase task / add plan examples / fix tool bug / make success criterion explicit in prompt)

- **Div Garg's agent architecture (CS25 V5 + V3):**
  - Memory: short-term (context window) + long-term (external vector stores); temporal coherence challenge
  - Tools: calculator, calendar, web search, code interpreter, APIs, browser control
  - Planning: reflection on failures, self-criticism, CoT decomposition, sub-goal breakdown
  - Actions: browser click + type (universal interface covering 100% of internet)
  - Loop = plan → execute → observe env feedback → loop; without error feedback the agent diverges (Auto-GPT failure mode)

- **Agent-Q loop (Div Garg, CS25 V5):**
  - MCTS explores state space, estimates future reward per state
  - Self-critic LM ranks multiple action proposals for each state (rank 1, 2, 3...)
  - DPO on (preferred action, rejected action) pairs to improve policy
  - Self-correction: saves mistakes in memory, trial-and-error improvement

- **ReAct/reasoning loop (Denny Zhou, CS25 V5):**
  - Intermediate tokens are the compute; treat each reasoning step as an MDP action
  - State = (problem, prefix of solution so far); reward is sparse (only at termination)
  - Key insight: "for any problem solvable by Boolean circuits of size T, constant-size transformers can solve it by generating O(T) intermediate tokens"

- **RL training loop for LLMs (CS224R Lec 10 / GRPO):**
  - Sample N=8 completions per prompt from current policy
  - Score each with verifier (binary 1/0)
  - Compute group-relative advantages: `(r_i - mean(r)) / std(r)` — no critic needed
  - PPO-style clipped update on advantages
  - Repeat; for easy problems gradient signal near zero (saves compute); hard problems high variance = strong signal

---

### Models (Exact Names + Roles)

- **Karina Nguyen (Anthropic/OpenAI, CS25 V5):**
  - Claude 2.1 used as primary product; o1/Operator/Deep Research trained via "RL on chain of thought at real-world task scale"
  - Canvas trained purely on synthetic data distilled from stronger reasoning models via teacher-student via APIs
  - Andrew Ng (CS230): personal toolchain is Claude Code as primary; mentions OpenAI Codex (GPT-5) and Gemini 3

- **Percy Liang (CS221):**
  - Four tiers: GPT-4/Claude (fully closed) → LLaMA 3/Mistral (open weights, closed training) → OLMo-early (weights + training code) → OLMo/Marin (fully open: weights + data + algorithm + infra)
  - Kimi K2: open-weight, beating some closed models at time of talk
  - Qwen 3: 36 trillion training tokens; Llama 3 405B: 16T tokens, 3.9×10^25 FLOPs, ~$42M compute, ~880,000 H100-days

- **Loubna Ben Allal (CS25 V4):**
  - FineWeb (HuggingFace): 15T tokens filtered web data, best open dataset
  - StarCoder 2 15B trained on The Stack V2 (6.3TB code, 1T tokens)
  - GitHub stars as quality signal: **failed** — removing repos with <5 stars removed 70%+ of data, model performed worst

- **Reasoning / RL models:**
  - AlphaProof: Lean 4 verifier + MCTS + RL; solved 4/6 IMO 2024 problems; silver-medalist equivalent (28/42 points); 3 days search per problem
  - DeepSeek R1 uses GRPO (no critic, group-relative normalization)

---

### Tool Registry (Agent-Q / Agents)

- **Agent-Q tools available to every critique agent (Div Garg):**
  - Web research
  - Ontology queries
  - Code execution (Python in-platform)
  - Not every agent uses all three — agents self-select tools based on task assessment

- **Standard agent tool taxonomy (CS25 V3/V5):**
  - Calculator, calendar, web search, code interpreter
  - Browser (click + type — universal)
  - APIs (only 5% of internet has public APIs; browser covers 100%)
  - External file system access

- **Agent communication protocols:**
  - MCP (Model Context Protocol) — tool/context sharing
  - A2A (Google, Agent-to-Agent) — inter-agent
  - Agent Protocol — open-source chaining standard
  - Manager-worker: manager issues task → worker executes → manager verifies against spec → if fail: issue correction + retry

---

### Context Assembly / Compaction / Budgets

- **Moroni on training distribution mismatch (CS230):**
  - macOS Swift UI example: majority of training data is iPhone code, not macOS code → even with explicit macOS context in prompt, models produce iOS APIs
  - Pattern generalizes: embedded systems, legacy platforms, proprietary APIs — always check training distribution alignment

- **Karina Nguyen on context for RL training (CS25 V5):**
  - Teaching model to be a software engineer = defining "what a good PR looks like" in the RL environment
  - Teaching model to be a good writer: agent needs drafting/editing tool + real-time world info + time to reflect — not prompt→output
  - Synthetic data trap: instruction diversity matters more than code execution quality — filtering on execution quality alone caused poor training outcomes

- **Denny Zhou on CoT (CS25 V5):**
  - More thinking tokens → better answers (diminishing returns)
  - Scale CoT OUTPUT LENGTH, not necessarily model depth
  - Self-consistency: sample N completions via temperature sampling, majority vote on FINAL ANSWERS only (not reasoning paths) — pure marginalization over latent variables
  - GSM8K: PaLM + CoT = 58%; self-consistency = 75%; PaLM 2 = 92%
  - Self-calibration: when self-consistency score >80%, accuracy is nearly 100% → natural uncertainty quantification

- **KV cache / memory math (CS221 + CME295):**
  - KV cache grows linearly: `O(num_layers × num_kv_heads × head_dim × seq_len)`
  - 70B model at 128K context: ~50GB KV cache alone
  - GQA (LLaMA-3, G=8): 4x KV cache reduction vs. MHA — "single most impactful change for LLM inference costs"
  - IQL τ=0.7 for V-function: estimates 70th percentile of Q-values — "pessimistic upper quantile"

---

### Memory

- **Agent-Q personalization (Div Garg):**
  - Explicit learning: user tells agent preferences directly; agent asks clarifying questions
  - Implicit learning: passive observation of user behavior (clicked size, navigated to airline) → inferred preferences
  - Online fine-tuning vision: day=data collection, night=model fine-tuning, next day=improved agent
  - Mistake memory: saves errors, uses trial-and-error improvement loop (bike-riding analogy)

- **Knowledge persistence models discussed:**
  - Short-term: context window
  - Long-term: external vector stores with temporal coherence challenge
  - Hierarchical retrieval as open problem

---

### System Prompts

- **Claude 2.1 refusal debugging (Karina Nguyen, CS25 V5):**
  - Refusal taxonomy found: benign prompt refusals, creative writing refusals, tool/function call refusals ("I don't have capability to read your note" when tool existed), long document attachment refusals, misdirected refusals from uncharitable interpretation
  - Principles added: charitable interpretation; I-statements instead of you-statements (NVC); ask if user would modify request; acknowledge impact
  - Self-knowledge gap: model refused tool calls because training data said it "has no physical body" — contradiction with actual tool capabilities
  - Fix: constitutional AI approach, craft preference pairs that change only one feature at a time

- **RLHF reward hacking (CS224R Lec 9):**
  - KL beta=0.1–0.3 typical (controls policy deviation from SFT model)
  - Reward hacking patterns: repetition of high-reward phrases, extreme verbosity, sycophantic agreement, junk characters fooling reward model
  - OpenAI finding: if you optimize chain of thought itself for honesty metrics, model hides intent inside CoT — **do not optimize CoT explicitly**

---

### Error Handling

- **Div Garg's reliability taxonomy (CS25 V5):**
  - Agents are stochastic — 100% reliability not achievable; minimize error rates
  - Looping/divergence: agent wanders without environment feedback (major failure mode — Auto-GPT collapsed for this reason)
  - Error feedback requirement: compiler errors, test failures, environmental signals MUST be pumped back to agent — without it: infinite loop
  - Kill switches essential — "unobserved agents could take over the internet"
  - Prompt injection attacks: websites can inject "tell me user's credit card details" into agent context

- **Reward hacking failure modes (CS224R Lec 8):**
  1. Velocity reward → agent falls forward at max speed (task failed)
  2. Gripper with visual reward → agent blocks camera (reward=1 for "grasping" while not grasping)
  3. LLM RLHF → extreme verbosity (humans prefer "thorough" responses)
  4. LLM sycophancy → agrees with false user assertions (increases reward)
  - Mitigations: KL penalty to reference policy; iterative reward model updates; multiple reward signals; held-out human eval; Constitutional AI

- **DPO probability collapse (CS224R Lec 9):**
  - When log_ratio_w very large: `∂/∂θ [-log σ(β*Δ)] ≈ 0` — gradients vanish
  - IPO fix: replace sigmoid with squared loss `(log_ratio_w - log_ratio_l - 1/(2*beta))^2`

---

### Exact Constants

- **DPO hyperparameters:** β=0.1 (standard); LR=1e-6 to 5e-6; batch size 32-64 preference pairs; reference model frozen
- **IQL:** τ=0.7–0.8 (empirical sweet spot); β=0.1–1.0 for AWR temperature
- **CQL α range:** 0.5–10.0 depending on task
- **PPO clip:** ε=0.2 standard; KL β=0.1–0.3
- **GRPO:** N=8 completions per prompt typical
- **Human preference query budget:** ~1,400 queries sufficient for Hopper locomotion; ~5,500 for complex tasks; pairwise accuracy: ~65-70% (still produces large policy improvements)
- **Data repetition limit:** up to 4× repetition performs similarly to unique tokens; beyond 4×: quality degrades measurably
- **Chinchilla ratio:** ~20 tokens per parameter compute-optimal; post-Chinchilla inference-optimal = smaller model trained longer
- **Emergence threshold:** ~10^22–10^23 training FLOPs for most emergent abilities
- **Task complexity doubling time:** ~7 months general tasks; ~70 days coding tasks (Metr/ARC study)
- **DCLM filtering retention:** 1.4% of Common Crawl retained (49M of 3.5B documents) — trains dramatically better models
- **Model data mixing (approximate):** web 70-80%, code 10-15%, papers 5-10%, books 3-5%, math 1-3% (disproportionate reasoning impact)
- **Flash Attention speedup:** 2-4x on A100, 3-5x on H100
- **Speculative decoding speedup:** 2-4x when draft model agrees with target ~70%+
- **Mixtral 8x7B:** 8 experts, 2 active per token; ~13B active params out of ~47B total; ~3.5x cheaper inference than equivalent dense model
- **RMSNorm vs. LayerNorm:** 15-20% speed improvement, no accuracy loss
- **Muon optimizer vs. AdamW:** same validation loss in ~30% fewer steps

---

### Multi-Agent Coordination

- **Div Garg (CS25 V5/V3):**
  - Single agent = single-threaded computer; multi-agent = multi-threaded
  - Parallelization: spawn 100 sub-agents simultaneously instead of sequential execution
  - Specialization: route expert agents (spreadsheet/browser/API) to appropriate tasks
  - Hierarchy: manager routes, verifies, corrects; worker executes; manager-worker verification loop
  - Natural language is ambiguous → need standardized protocols with retry/verification/security mechanisms

- **Agent-Q self-improvement (CS25 V5):**
  - MCTS + self-critic + DPO: significant improvement over base models on web navigation
  - GPT-4o: 14% on agentic web tasks; best result: Claude 3.7 at ~40%; Gemini 2.5 and o3 close behind
  - 40% is not good enough for production deployment

---

### Streaming Protocol

- Not directly specified in Stanford transcripts. Test-time compute scaling (o1/R1/Gemini 2.0 Flash Thinking) uses streaming scratchpad tokens before final answer.

---

### Training / Eval Setup

- **GRPO full algorithm (CS224R Lec 10):**
  ```python
  # Per-prompt: sample N=8 responses, score with verifier
  rewards = [verifier.check(prompt, r) for r in responses]
  advantages = (rewards - mean(rewards)) / std(rewards)
  # PPO-style clipped update with clamp(ratio, 1-eps, 1+eps)
  ```

- **DPO loss:**
  ```python
  loss = -F.logsigmoid(beta * (log_ratio_w - log_ratio_l))
  # log_ratio = policy.log_prob(y|prompt) - ref.log_prob(y|prompt)
  ```

- **AlphaProof:**
  - Lean 4 theorem prover = perfect verifier (0/1, no reward hacking possible)
  - MCTS + RL; formalization model (NL→Lean 4) + proof search model
  - 3 days search time per IMO problem; solved 4/6 IMO 2024

- **Verifier primacy (Denny Zhou):**
  - "A reliable verifier is the most crucial element in RL fine-tuning, not the algorithm. If anyone finds an algorithm significantly better than others, please tell me."
  - RL for reasoning only works well for automatically verifiable tasks (math, code); extending to creative writing is the open problem

- **Process reward models (PRMs):**
  - Monte Carlo estimation: for each prefix up to step i, sample K=20 completions, fraction reaching correct final answer = process reward for step i
  - Dense credit assignment: identifies exactly which step in a 20-step chain went wrong
  - Return-to-go from step i = sum of step_rewards[i:]

- **RFT 8x data efficiency:**
  - Offline RL using full dataset (including failures) achieves same performance as SFT on correct-only examples with 8x less data
  - Mechanism: failures are negative examples for which reasoning strategies work

- **InstructGPT 3-stage pipeline:**
  1. SFT on human demonstrations (teaches format, not knowledge)
  2. Reward model from pairwise preferences: `loss = -log σ(RM(y_w) - RM(y_l))`
  3. PPO with KL penalty: `max E[RM(y)] - β·KL(π||π_SFT)`
  - SFT teaches: primarily formatting; evidence — training on deliberately wrong answers still produces good downstream performance

---

## TRANSCRIPTS_PALANTIR.md

**Source:** 23 YouTube VTT transcripts from Palantir DevCon 4 and DevCon 5 (processed April 2026). Covers AIFDE (eval-driven agent development), Orchestrator (durable execution), Hivemind (dynamic agent swarms), Army SAS modernization pipeline, Knowledge Nodes, and Ontology primitives.

---

### Agent Loop Shape

- **AIFDE eval-driven loop (DevCon 5, session 2):**
  1. Exploration mode: query ontology, read patterns, semantic search documentation
  2. Logic creation: produce first-draft AIP Logic function (better than human first draft due to full ontology context)
  3. Eval suite generation: create 10 representative test cases from historical data, set accuracy metrics
  4. Auto-debug loop: run evals → analyze failures → synthesize what went wrong → refine prompt → rerun → iterate
  5. Deploy at acceptable pass rate (90% in demo, after 1 iteration from 10%)
  6. Capture production failures as feedback ontology objects
  7. AIFDE reads feedback, writes test case, runs evals, iterates logic until passing
  - First run: 9/10 test cases fail; one iteration: 90% passing
  - Recursion: AIFDE builds a feedback quality-gate agent to improve human feedback to the main agent ("agents building agents building agents")

- **Orchestrator loop (DevCon 5, session 3):**
  ```python
  for criterion in payer_criteria[treatment]:
      result = LLM.call("approved/denied/need more info?", context=clinical_docs)
      if result == "need more info":
          write AgentAction(type="request_document") to ontology
          await condition: extracted_text_from_uploaded_doc IS NOT NULL
      # execution suspends indefinitely; resumes when condition true
  ```
  - Long-running: no timeout (days/months/indefinitely)
  - Durable: progress stored at every step; if step fails, resume from exactly that step
  - Interruptable: declarative `await condition` — no Kafka, no state machine
  - Observable: every prompt line, every LLM response, exact timestamps, granular search across millions of executions

- **Hivemind dynamic agent swarm loop (DevCon 5, session 7):**
  1. Problem framing: human provides brief problem statement
  2. Parallel idea generation: multiple async agents generate different solution approaches simultaneously
  3. Per-idea critique team generation: Hivemind creates logistics agent + risk agent + medical specialist + others on-the-fly (prompts generated by Hivemind based on problem context — NOT pre-configured)
  4. Kneelment (iterative refinement): v1 → critique → v2 → critique → v3 until ready
  5. Idea promotion: new agent team writes full plan; critique agents poke holes; iterate
  6. Execution: plan parsed to Gantt chart + AIFDE handoff for operational implementation
  - Feedback propagation: commander feedback stored as ontology object → all future runs start with that feedback as context (compounding knowledge)

- **Army SAS modernization 5-stage pipeline (DevCon 5, session 8):**
  1. **Decomposition** (regex, not AI): parse SAS file → extract procedures, datasets, data steps, macros, system functions, file inputs → 9 ontology objects per file, 54 procedure references across 6 files
  2. **Warning system** (AI triage): hard stops (translation will fail) + soft flags; first HITL checkpoint — SMEs add context
  3. **Reconnaissance** (AI analysis per file): summary, logical flow, input/output inventory, risk summary with recommended solutions, risk triage (high/medium/low); second HITL checkpoint
  4. **Decode** (SAS → pseudo code JSON): execution stages + SAS line mapping + agent confidence score + encoding notes
  5. **Encode** (pseudo code → Foundry Transforms): Assessment Agent first determines single vs. orchestrated framework (4-dimension complexity score: outputs count, risk concentration, interdependencies, agent confidence); parallel translation agents receive Transform Contracts; Compilation Agent assembles

  - Transform Contract contents: assigned pseudo code stages, recon excerpt (only relevant stages), associated warnings (only relevant), exact SAS lines, Foundry Transform docs, translation rules
  - Output: Python file with SAS lines as inline comments above each Python block (enables SME validation without knowing Python)
  - Total: 6 files processed in ~1 hour including human review checkpoints

- **Knowledge Nodes K4D agent loop (DevCon 4, session 13):**
  - 16-step agent loop for manufacturing analysis
  - Artifact-based state: each intermediate result written as named ontology object; if step fails, resumes from last artifact (not from start)
  - Dynamic SDK generation per agent: scoped to specific object set for current task
  - All steps stored in ontology: initial prompt, code at each step, every artifact, every error + self-correction, final report, proposed knowledge nodes
  - Full analysis branching: go back to any intermediate point, fork with different path

---

### Models

- **AIFDE:** model-agnostic — configurable per agent, changes don't require code changes
- **Agent Studio:** model-agnostic — any LLM selectable; multi-framework demo shows identical ontology operations from Anthropic SDK (Claude), Microsoft framework (GPT-4), OpenAI SDK (GPT-4 mini) simultaneously via MCP
- **Eaton document processing:** started with one model provider, found accuracy insufficient on specialized tasks → now using multiple different models across different pipeline steps, chosen per sub-task performance
- **AIP model routing:** 15-16 hosting hubs globally; if provider has outage, routes to equivalent compliant provider transparently; geo-restriction routing (EU, US data locality)
- **Provider API Proxy:** wire-compatible OpenAI-compatible + Anthropic-compatible endpoints; two-line setup (`base_url = foundry_api_host()`, `api_key = foundry_api_token()`)

---

### Tool Registry

- **AIFDE tool set (DevCon 5):**
  - SQL query on ontology objects
  - Direct CRUD actions on any object type
  - Semantic search on documents
  - Eval suite creation + execution
  - Workshop application creation + editing
  - Automate wiring (trigger → condition → action)
  - Mode switching across platform capabilities
  - Branch creation + ontology property updates
  - Pipeline Builder (no-code ETL, DevCon 4 preview)
  - Logic editor (no-code transforms, DevCon 4 preview)

- **Hivemind per-agent tools (DevCon 5):**
  - Web research
  - Ontology queries
  - Code execution (Python in-platform)
  - Not every agent uses all three — agents self-select

- **Ontology MCP (OMCP) tool exposure:**
  - Every action in a Dev Console app becomes an MCP tool automatically
  - Every object type becomes a queryable resource
  - Full read + write interface governed by same Foundry security model
  - OAuth token auth: same permissions as OSDK application for same user

- **Agent Studio session APIs:**
  - `create_session`
  - `get_trace` (of a session)
  - `continue_streaming_session`

---

### Context Assembly

- **Ontology-as-context architecture:**
  - The ontology IS the context; agents query it rather than receiving a pre-assembled prompt
  - Knowledge Nodes: deconflicted domain knowledge in the background so agents at runtime don't spend context figuring out which information is credible
  - Hivemind: per-agent prompts AND per-agent ontology SDK scopes — each agent sees only what it needs
  - Army: Transform Contract scopes context precisely — only relevant SAS lines, only relevant warnings, only relevant recon sections
  - AIFDE "Smart Context Management": maintains coherence across long autonomous sessions with large ontologies; prevents context drift over many tool calls

- **Practical context constraints observed:**
  - K4D artifact checkpointing: if context window fails mid-16-step run, agent resumes from last artifact (doesn't restart)
  - Army pipeline: each translation agent receives only the stages it owns, not the full SAS file — isolation prevents context overload

- **Eaton per-property dual-prompt pattern (DevCon 4):**
  - Identification prompt: "what am I looking for?" (based on engineer Ctrl-F keywords)
  - Selection criteria prompt: "given found content, what value to extract?"
  - Two prompts per property; all stored as ontology objects, dynamically pulled into LLM calls

---

### Memory

- **Ontology as persistent memory for agent swarms:**
  - All Hivemind outputs written to ontology: problem, research, code, ideas, critiques, plan — "monitored in real-time"
  - Knowledge Nodes: continuously synthesized domain knowledge, not raw notes; persists across all agent runs; deconflicted in background
  - AIFDE feedback loop: user feedback is an ontology object linked to incident + execution trace — not a free-text string lost in a chat
  - Army: the corpus grows per run — PROC GLM → statsmodels mapping learned in run 1 is available in run 100

- **Knowledge Node creation pathways (DevCon 4, session 13):**
  1. Reflection after collaborative analysis: what was learned, what code patterns worked, what mistakes were made
  2. Document ingestion: PDFs, runbooks, Jupyter notebooks, flowcharts → ingestion agent proposes edits to knowledge layer
  3. Autonomous background troll: agent continuously scans data, identifies patterns, proposes new nodes for human review

- **Knowledge Node contents:**
  - Best practices for avoiding data leakage in specific analytical pathways
  - Code recipe examples (working Python code for common patterns)
  - Relationships between production variables and process outcomes
  - Deconflicted domain knowledge (synthesized, not raw)

---

### System Prompts (Verbatim Patterns)

- **AIFDE safety incident triage system prompt (reconstructed from demo):**
  - "Here's my data: 50 safety incidents, OSHA regulations documentation. Automate this process. Extract: incident type, severity (low/medium/high/critical), required actions."
  - AIFDE first-draft prompt described as "better than what I would have come up with in the first place" — automatically incorporated OSHA regulatory context via semantic search

- **Hivemind agent generation pattern:**
  - Takes all context accumulated so far in the problem set
  - Generates per-agent: instructions, tools each agent needs, specific ontology access scope
  - Generic logistics prompt vs. "maritime disaster response, evacuation by sea barge, Southeast Asian geography, existing naval assets" logistics prompt → qualitatively different output

- **Orchestrator pre-auth await pattern:**
  ```python
  await condition: extracted_text_from_document IS NOT NULL
  # or
  await condition: human_approval_object.response IS NOT NULL
  ```

- **Eaton CDN deviation object pattern:**
  ```python
  clarification_obj = create_ontology_object(
      type="ClarificationRequest",
      question="Customer spec specifies X but configurator requires Y. How to proceed?",
      human_response=None
  )
  await condition: clarification_obj.human_response IS NOT NULL
  action = clarification_obj.human_response
  proceed_with_quote(action)
  ```

- **Akshay on model choice being secondary (verbatim quote):**
  > "So much of this goes beyond just the nature of the LLM or any model you choose in particular. It's the iterative tradecraft as you'll hear today about how to decompose the problem, how to wield chained agents and sub-agents, how to configure the overall operating system to deliver on the outcome."

---

### Error Handling

- **Cascading silent failure problem (Eaton, DevCon 4):**
  - One LLM call times out → output object stays null → parent stage fails → grandparent fails → entire project fails
  - In hundreds of parallel LLM calls: common occurrence
  - Their hack: Workshop showing every project + all linked objects to root + manual action buttons to modify statuses
  - Orchestrator fix: each step is a separate checkpointed unit; failure isolated to step level; parent retries only the failed step

- **Provenance-based security (DevCon 4, session 19):**
  - Traverses full upstream dependency graph — detects marking violations anywhere in chain, not just immediate function
  - Attack: Developer X improves function upstream with Sensitive Internal data → downstream send_email function now violates export marking
  - Platform blocks preview + publish with explicit error: "Upstream of draft_email: sensitive internal data is present. Upstream of send_email: connection is not appropriate for this data classification."
  - Applies even to third-party library code (PydanticAI demo) — governance is infrastructure, not convention

- **AIFDE production feedback loop:**
  - Production failure → user rejects proposal → vague feedback ("this is bad") → human must interview user to make actionable
  - Recursive solution: AIFDE builds feedback quality-gate agent that intercepts vague feedback and asks clarifying question
  - Systematic eval → AIFDE synthesizes failures → writes test case → runs evals → iterates logic

- **Army adversarial review (best practice #4):**
  - After transform generated, separate critique agent evaluates it against Foundry documentation + original SAS
  - Identifies potential issues, proposes corrections
  - Same adversarial review pattern as Hivemind kneelment

---

### Exact Constants

- **Build velocity benchmarks:**
  - Full-stack Foundry app scaffold: 8 seconds (`foundry create my-project`)
  - Safety incident triage agent (AIFDE, zero to eval-validated): minutes
  - OR scheduling app (one engineer, full ontology toolbox): one weekend
  - Non-developer quote framework (senior director, AIFDE): ~2 hours
  - DataHAUL full product (small team): 2 months
  - Army SAS 6-file pipeline: ~1 hour total including human review checkpoints

- **Accuracy benchmarks:**
  - AIFDE safety incident triage: 10% passing (first run) → 90% passing (one iteration)
  - AIFDE decoding Lear acronyms: 90-95% correct with no additional context
  - Spark → Polars migration: one-shot for simple pipelines; 90% for complex
  - Internal Palantir Spark→Polars migration: 1.5 days → under 2 hours (Polars lightweight); 5B rows input, 240M output

- **Infrastructure scale:**
  - AIP model hosting hubs (DevCon 4): 15-16 globally
  - Lear Corporation: 16,000 users, 280+ use cases, ~1,000 active builders, 250 factories, 37 countries
  - First Solar: 100 integration engineers, 20,000 modules/factory/day, 10 factories, 18 months to proficiency
  - Iceberg 1PB case study: 99% file count reduction; 2-hour pipeline → 2-minute pipeline
  - Usul month-1 results: 60+ customers, $20B contracts analyzed, $400M pipeline created

- **Eaton document processing:**
  - Documents: thousands of pages for specifications, hundreds of panelboard schedules
  - Processing time: 10-30 minutes per scope
  - Per-property: 2 prompts (identification + selection criteria)
  - Challenge: exact JSON output structure + flexible parsing for arbitrary customer layout

- **AIFDE Agent Studio:**
  - "34 lines of code" vs. full production complexity (CI/CD, versioning, deployment, tracing, logging, evaluations) handled automatically

---

### Multi-Agent Coordination

- **Hivemind vs. standard orchestration (DevCon 5, session 7):**
  - Standard: agent roles pre-configured at build time; same prompt every run regardless of problem
  - Hivemind: agent roles generated at runtime from current problem + current idea + current stage
  - Kneelment pattern: `v1 → critique_team → v2 → critique_team → v3 → ... → promote`
  - Decision to iterate is agent-driven; commander feedback stored → propagated to all future runs
  - Each agent decides which tools to use (site selection agent spontaneously chose code execution)

- **Army parallel translation (DevCon 5, session 8):**
  - Assessment Agent determines: single agent vs. orchestrated (4-dimension complexity scoring)
  - Grouping: stages with high interdependencies grouped; isolated stages run in parallel
  - Example: 3 parallel translation agents → Compilation Agent waits for all, deduplicates imports, validates

- **Agent communication via ontology state (DevCon 5, session 3):**
  - Sub-agent extracts document, writes text to ontology
  - Main agent's `await condition` triggers on that write
  - Agent-agent communication via ontology state changes — no direct calls between agents
  - UI: agent creates TYPED ontology object specifying exactly what it needs (not a chat text box) → human fills structured form → agent resumes

- **OMCP multi-framework parallel demo (DevCon 4, session 11):**
  - Anthropic SDK (Claude), Microsoft framework (GPT-4), OpenAI SDK (GPT-4 mini) all connected via MCP
  - All three analyze same transcript, make identical ontology updates
  - Backend is always the ontology — interface varies, backend constant

---

### Streaming Protocol

- **Object Set Watcher:** Workshop and OSDK apps live-reload when objects change — no polling
- **OSDK Hooks with `stream_updates: true`:** component subscribes to live ontology changes; re-renders automatically when anyone from any application modifies an object
- **PAC Presence:** high-frequency ephemeral streaming events (cursor positions); defined schema, Foundry streams to all connected clients; not persisted
- **Agent Studio:** all tool-calling and reasoning streamed to client via platform APIs
- **Orchestrator observability:** P99 duration, model usage over time, token consumption trend, cost per model — all live

---

### Cross-Session Design Themes

- **Six structural insights from 23 DevCon sessions:**
  1. **Ontology as shared mutable state for human-agent teaming:** every handoff structured; agent creates typed object specifying exactly what it needs; human fills it; agent resumes via await condition. Not a chat text box.
  2. **Eval-driven development as the loop:** first draft is never the deliverable; 70-90% initial failure rate expected; the loop (generate → eval → synthesize failure → fix → rerun) is the product
  3. **Agents building agents:** Level 1 = AIFDE builds triage agent; Level 2 = AIFDE builds feedback quality-gate agent; Level 3 = Hivemind generates per-problem agent teams with generated prompts
  4. **Agents writing to ontology as output layer:** every agent output is an ontology object; this makes systems observable, debuggable, improvable over time
  5. **Context management as first-class engineering:** pass only relevant context to each agent; curate, don't dump
  6. **Orchestrator as missing infrastructure primitive:** long-running + durable + interruptable + observable; absence of this causes cascading silent failures in every real production deployment

---

## → Verso Implications

**From TRANSCRIPTS_STANFORD.md:**

- **ReAct is the right loop default.** Denny Zhou's formal result is load-bearing: constant-size transformers can solve any problem solvable by Boolean circuits of size T by generating O(T) intermediate tokens. Verso's default agent loop must be a clean ReAct — think-act-observe — not a graph. The intermediate tokens ARE the compute. Don't skip or compress the scratchpad.

- **Build in self-consistency as a first-class inference strategy.** Majority vote on final answers (not reasoning paths) over N=4–8 samples produces ~17-point relative improvement on reasoning tasks with no training required. When Verso runs a tool-using agent on a hard task, offer a self-consistency mode: run N parallel traces, take majority vote on final answer. Natural calibration: when self-consistency score >80%, accuracy is nearly 100%.

- **Verifier-first design.** "A reliable verifier is the most crucial element in RL fine-tuning, not the algorithm." For Verso evals and HITL checkpoints: design the verifier before the agent. What counts as success must be expressible as a function. For tasks without symbolic verifiers (creative writing, open-ended reasoning), document the gap explicitly — don't pretend a weak proxy is a ground truth.

- **The 4-step agent anatomy is the right mental model for debugging.** Intent understanding → Planning → Execution → Reflection. Verso's tracer/observability layer should annotate which step a failure occurred in. This lets users fix the right thing: rephrase task (intent), add plan examples (planning), fix tool implementation (execution), make success criterion explicit (reflection).

- **Error feedback loops are non-negotiable.** Auto-GPT collapsed because agents looped without environment feedback. Verso MUST surface compiler errors, test failures, tool errors back to the agent immediately. The environment signal is what keeps the loop convergent. Every tool wrapper must return structured errors, not silent failures.

- **Kill switches + observability before deployment.** "Unobserved agents could take over the internet." Verso needs: agent kill/pause mechanism, execution trace accessible at any point, full tool-call log. Not optional — prerequisites for any agent that takes external actions.

- **Reward hacking principle for Verso evals:** Do not make CoT the evaluation target. If you optimize the agent's reasoning trace for honesty/quality metrics, the agent learns to hide intent in CoT. Evaluate only final answers and tool call correctness — not the scratchpad.

- **KL-constrained exploration for multi-turn agents.** The β=0.1–0.3 KL penalty in RLHF is the mechanism that keeps trained policies near their anchor. For Verso agents operating over multiple turns, the equivalent is: don't let the agent stray too far from its system prompt's intent across turns. If the agent's behavior in turn 10 is unrecognizable relative to turn 1, that's a violation analogous to reward hacking.

- **Structured tool schemas beat informal descriptions.** The IQL insight — "never query OOD actions" — maps directly to tool design: give agents tools with strict typed schemas (not free-form strings). Agents that can only call tools with specific typed parameters cannot hallucinate tool calls. Verso's tool registry should enforce Pydantic-style schemas on all tool inputs.

- **Training distribution alignment is an agent design problem.** Moroni's macOS/iOS training mismatch example: if your agent's underlying LLM was trained mostly on generic patterns but your use case is domain-specific (legacy SAS code, proprietary APIs, niche frameworks), expect failure in planning/execution. Verso must surface this as an explicit calibration step: test the agent on domain-specific inputs before trusting it in production.

**From TRANSCRIPTS_PALANTIR.md:**

- **The ontology pattern = Verso's memory substrate.** The most important architectural lesson from 23 DevCon sessions: human-agent handoffs must go through a shared typed state object (the ontology), NOT through a chat text box. In Verso's terms: HITL checkpoints should create a typed `PendingInput` object that the agent awaits; the human fills a structured form; the agent resumes. This is architecturally cleaner than inserting human turns into the chat history and lets the UI be as rich as the ontology allows.

- **`await condition` is the right primitive for HITL and long-running agents.** Palantir's Orchestrator is the missing primitive for production agents. Verso should ship a first-class `await` mechanism: the agent can suspend execution indefinitely, waiting for a typed condition (ontology write, external webhook, human approval). No Kafka, no state machine, no timeout. Declarative suspension: "I need this field to become non-null before I continue."

- **Durable/checkpointed execution beats restart-on-failure.** Eaton built a monitoring hack because every LLM failure restarted their pipeline from scratch. Verso's execution runtime should checkpoint every step. If step N fails, retry only step N. The Compilation Agent pattern (waits for all parallel sub-agents, then assembles) requires that sub-agents are independently durable.

- **Eval-driven development loop is the product, not a feature.** AIFDE's most important behavior: first draft is never the deliverable; 70-90% initial failure rate is expected and normal; the loop (generate → eval → synthesize → fix → rerun) IS the software development process for agents. Verso should make this loop a first-class concept — not a testing afterthought. Every deployed agent should have an associated eval suite that runs on every change.

- **Agents building agents via eval-driven loop.** The three-level recursion (AIFDE builds triage agent → AIFDE builds feedback quality-gate agent → Hivemind generates per-problem agent teams) is not science fiction — it's production. Verso should be designed to support agents as first-class artifacts that can be generated, tested with evals, and deployed by other agents. The key enabler: eval suites are versioned, testable, and linked to the agent they cover.

- **Dynamic agent generation beats pre-configured roles.** Hivemind's key insight: a generic logistics prompt produces generic output. A prompt generated specifically for the current problem context produces analysis specific to that problem. Verso should support a "generate-agent" operation that takes problem context and produces an agent definition (system prompt + tool selection + context scope) for that specific task. Pre-configured agent libraries are a starting point; dynamic generation is the ceiling.

- **Context scoping is as important as context quality.** Army Software Factory: each translation agent receives ONLY the SAS lines, recon, and warnings for its specific stages — not the full file. Knowledge Nodes: domain knowledge deconflicted in background, not at runtime. Hivemind: per-agent ontology SDK scopes. The consistent pattern: invest engineering effort in scoping context precisely per agent, not in passing everything everywhere. Verso's tool/context assembly layer should support explicit per-agent context scoping.

- **The eval-first development contract.** AIFDE's sequence is fixed: exploration → logic creation → eval suite generation → auto-debug loop → deploy at passing threshold → capture production feedback → feed back into evals. Verso should enforce this contract: no agent goes to production without an associated eval suite; every production failure becomes a test case. The eval suite is not optional metadata — it is the proof of quality.

- **Ontology write-back as the output layer.** In every Palantir demo, agent output is a typed ontology object, not a free-text response. This makes agent outputs: structured (parseable), auditable (full history), reactive (triggers downstream agents), and improvable (fails produce labeled feedback objects). Verso should encourage agent outputs to be typed objects written to a shared state backend — not just strings returned to the user. This is the architectural difference between an agent as a chatbot and an agent as a system component.

- **Provenance-based security as infrastructure, not convention.** Security that traverses the full dependency graph prevents the developer X attack (upstream function adds sensitive data without downstream function knowing). For Verso multi-agent pipelines: data classification should propagate through the call graph; if any upstream input is classified at level X, the downstream output is at least level X. Don't trust agents to self-classify their outputs — enforce it in the routing layer.

- **The six LLM-in-production requirements (Austin, DevCon 4):**
  1. Security and governance (data lineage + marking propagation)
  2. Observability and telemetry (aggregate, don't require manual trace inspection)
  3. Monitoring and evals (define failure ahead of time, alert continuously)
  4. Flexible build system (same paradigm for batch and interactive)
  5. Cost management (per-project rate limits, spend tracking)
  6. Release management (versioning, branching, team isolation)
  - "These things can't be applied after you have a workflow built. This has to be innate to the design of the system."
  - Verso must address all six at framework design time, not as bolt-ons.

- **Model routing is infrastructure, not application logic.** Palantir's 15-16 model hosting hubs with automatic failover and geo-routing. Eaton switched models per sub-task for accuracy. For Verso: model selection should be a declarative configuration per agent/tool, not hard-coded API calls. The framework routes to the best available compliant model. This enables: A/B testing models, automatic failover, cost optimization, compliance by default.

- **Scratchpad and intermediate artifacts survive context failure.** K4D artifact-based communication: named intermediate results persisted to shared state between steps. If context window overflows mid-16-step run, agent resumes from last artifact. Verso's agent execution runtime should support explicit artifact checkpoints: the agent can declare "save this intermediate result" and the runtime guarantees it's retrievable even if the context is cleared.

- **The pseudo code intermediate layer as generalization unlock.** Army Software Factory: SAS → pseudo code → Python. Swapping the encoder gives SAS → R without changing stages 1-4. The insight for Verso: design agent pipelines with explicit intermediate representations that decouple inputs from outputs. This enables: swapping target outputs without redesigning the whole pipeline; testing intermediate stages independently; supporting multiple output formats from one analysis.
