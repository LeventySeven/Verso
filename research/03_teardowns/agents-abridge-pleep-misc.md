# Cluster: Abridge + Pleep + Aemon
## Teardown notes for Verso agent framework design

Sources: `teardowns/ABRIDGE.md` (R1-R6, 3,113 lines), `teardowns/PLEEP.md` (3,146 lines), `teardowns/AEMON.md` (2,379 lines)

---

## Abridge — Contextual Reasoning Engine for Clinical Documentation

### What it is

Abridge rebuilds the **clinical note as a primitive**, not a transcription bolt-on. The Contextual Reasoning Engine (CRE) fuses ambient audio capture, medically-tuned ASR, EHR context (prior notes, patient history, guidelines, clinician preferences), structured note generation, revenue cycle intelligence, and hallucination detection into a single integrated pipeline. Deployed exclusively inside Epic, Athenahealth, Cerner, VistA, and other EHRs — no standalone web app.

### Agent loop / pipeline shape

Not a chat agent. Abridge's "agent loop" is a linear, **statically-orchestrated multi-model pipeline** that runs once per clinical encounter:

```
Ambient audio (3 clients: Epic Haiku / clinician-app / web-recorder)
  → chunked Opus/AAC upload to audio-api.abridge.com
  → bilrost (mTLS ingress) → Riva-WebSocket-Bridge → gRPC :50051

[NVIDIA Riva ASR pipeline on Triton]
  [a] GPU mel features, 40ms frame shift, 16kHz LINEAR16
  [b] Acoustic model: medical fine-tune of Parakeet-CTC 1.1B (INFERRED)
  [c] Decoder: Flashlight WFST beam (beam_size=32, lm_weight=0.8) over medical n-gram LM
  [d] Endpointing: start_history=200, two-pass EOU detection
  [e] Post-process: BERT punctuation + WFST ITN

  → processTranscript() — deterministic O(1) rule pipeline:
      replaceSpellingErrors() — 558 clinician-reported + 4,096 synthetic entries
      replaceGenericNames() — 987 generic drug name normalizations
      number/date normalization, punctuation gap fill, oscillation detection
      DROP_THRESHOLD_PERCENT=30, MAX_API_RETRIES=3, RETRY_BASE_DELAY_SECONDS=2

  → audio-transcript entailment gate (Wav2Vec2.0/HuBERT + frozen BERT)
      project→concat→sigmoid fusion; frozen BERT forces acoustic encoder to learn
      only LOW-confidence (negative-entailment) spans escalated to expensive correction
      recall-tuned threshold (recall > precision in clinical safety context)

  → [EHR context injection: prior notes, problem list, health-system guidelines,
     visit diagnosis, specialty, care setting, patient name, insurance info]

  → decoder-only LLM note generation (fine-tuned T5→BART→decoder-only family)
      section-conditioned generation (SOAP subsections: S/O/A/P)
      Cluster2Sent architecture: classify utterances → cluster by proximity → T5/decoder per cluster
      ~27 sentences per note, ~3.84 supporting utterances per sentence

  → hallucination detection (proprietary NLI-style model, 50K+ training examples)
      5-level Support Axis: Direct / Reasonable inference / Questionable inference / Unmentioned / Contradiction
      3-level Severity: Major / Moderate / Minimal
      3-way branch: Revise / Delete / False alarm
      runs BEFORE clinician sees the note; 97% detection rate vs GPT-4o 82%

  → Linked Evidence extraction (post-hoc FEVER MidFusion RoBERTa-base model)
      NOT structural — a separate post-hoc retrieval/classification model
      caches per-sentence token embeddings; per query: one transformer layer + LSTM + classifier
      5.8x faster than prior SOTA, within 5% F-score; HA=94% vs BM25=65%
      failure mode: negative/absent assertions have no positive evidence to point to

  → coder.abridge.services: ICD-10/HCC code assignment + CDI query generation
  → orders generation (12 types: lab, imaging, referral, follow-up, medication, ...)
  → ehr-interop: write-back to Epic / Athena / Cerner / VistA

Pipeline-completion event sequence (client-visible):
  ML_STARTED → ML_PROCESSING_PRIORITY → ML_SUCCESS
  → diagnoses_generation_completed → order_generation_completed
  → association_completed → diagnoses_and_order_generation_completed
```

**Loop shape:** Not a ReAct loop — a DAG with fixed stages. No LLM self-directed tool calls. The "agent" quality is in the orchestration of specialized models at each stage, not in a general-purpose agent loop. Human-in-the-loop is the clinician reviewing/editing the final note, not mid-loop.

**Iteration / termination:** Single pass per encounter. No retry loops at the agent level. Retries exist at the infrastructure layer (MAX_API_RETRIES=3).

### Agentic roadmap (2026)

`agent-api.abridge.services` is a gRPC service (method names locked, Reflection returns HTTP 200 but no method enumeration). The `abridge-assist → abridge-agent-manage-*` flag rebrand and Lipton's "2026 = agentic transformation" signal a shift from passive scribe to active real-time co-pilot. Three agent actions in progress:

1. **Real-time prior-auth gap detection** — CRE parses conversation live; Availity's payer logic delivers determinations during the visit
2. **CDS query** — RAG over UpToDate/NEJM/JAMA/DailyMed/PubMed via `vector-store.abridge.services`
3. **HCC coding nudge** — surfaces risk-adjustment gaps during the visit ("30 seconds saves an hour later")

### Models (exact, as known)

| Stage | Model | Status |
|---|---|---|
| ASR | NVIDIA Riva, medical fine-tune of Parakeet-CTC 1.1B (INFERRED) | weights BLACK BOX |
| ASR correction gate | Wav2Vec2.0/HuBERT (acoustic) + frozen BERT (linguistic) | KNOWN from Interspeech 2022 |
| Note generation | Decoder-only LLM, fine-tuned on 1.5M encounters, SOAP section-conditioned | architecture BLACK BOX |
| Hallucination detection | Proprietary NLI-style model, trained on 50K+ examples | BLACK BOX |
| Linked Evidence | RoBERTa-base MidFusion extractor (prod), QA-pretrained on SQuAD/HotPotQA/BioASQ/SynthMed | KNOWN from FEVER@EMNLP 2024 |
| Coding / CDI | server-side model inside `coder.abridge.services` | BLACK BOX |
| Evaluation | `text-embedding-3-large` for dedup, GPT-4o/o3-mini for checklist refinement, LLM-as-judge | KNOWN from EMNLP 2025 |
| LLM backend (Assist/agent) | Vercel AI SDK + Anthropic provider (INFERRED from mobile bundle OTel instrumentation) | INFERRED |

Multi-LLM confirmed: OpenAI (2 domain verifications), Anthropic (1 domain verification), NVIDIA Riva ASR, self-hosted models.

### Tool system

No general-purpose tool registry visible. The CDS/Assist surface (`vector-store`, RAG over licensed medical content) is the closest analog. Tool-like actions are hardcoded pipeline stages, not dynamic tool calls.

`abridge-assist/streamChunk` endpoint confirms SSE streaming for the Assist chat surface. The Assist agent uses a `parts[]` array (multimodal). Saved prompts per clinician (`/abridge-assist/user/saved-prompts`).

### Context assembly

CRE exact input set (verbatim from Lipton talk):
- Conversation transcript (current encounter)
- Visit diagnosis, problem list, prior notes for this patient
- Other structured EHR data (meds, labs, allergies, appointments)
- Physician specialty, care setting
- Patient name, clinician name, preferred pronouns
- Health-insurance information (for risk adjustment)
- Health system-specific revenue cycle guidelines
- Clinician documentation preferences

No context window / compaction details published. The pipeline is chunked by encounter, not unbounded. T5-based prior work failed on Conv2Note (long inputs) — the "cluster first, generate per cluster" architecture is the compaction strategy: each cluster of ~4 utterances → exactly one sentence.

### Memory

| Type | TTL | Backend | Evidence |
|---|---|---|---|
| Conversation thread | Per encounter | `notes.abridge.services` NestJS API | KNOWN |
| Patient history / prior notes | Persistent (pulled from EHR) | EHR via `ehr-interop.abridge.services` | KNOWN |
| Embedding cache (Linked Evidence) | Session | In-memory (MidFusion caches per-sentence embeddings) | KNOWN from FEVER paper |
| Clinician preferences | Persistent | `/note-preferences`, `/settings/notes/customterms` | KNOWN |
| LaunchDarkly config | TTL per flag | `llm-gateway.abridge.services` | KNOWN |

No long-horizon agent memory across sessions beyond what the EHR provides.

### Streaming protocol

**Audio ingest:** chunked Opus-in-WebM (web) or AAC (mobile), HTTPS to `audio-api.abridge.com`. E2E encryption: hybrid RSA-wrapped AES-256-GCM, per-chunk.

**Real-time transcription preview:** LiveKit WebRTC SFU (`livekit.abridge.services`, self-hosted). Krisp noise cancellation. `useTrackTranscription` over LiveKit data channel.

**App event channel:** Socket.IO / Engine.IO v4 (`client-api-socket.abridge.services`). Constants: pingInterval 25,000ms, pingTimeout 20,000ms, maxPayload 1MB. Carries worklist/encounter/note-status subscriptions.

**Assist/agent streaming:** SSE via `POST /abridge-assist/streamChunk`, `parts[]` array format.

**Note delivery:** pull model — client polls `ML_STARTED → ML_SUCCESS`; output JSON stored in GCS (`mlOutputBucket`/`mlOutputObject`); structured as `MLOutput_SoapNoteSummary → MLOutput_SoapSection → MLOutput_SoapSentence`.

### Error / retry paths

- `MAX_API_RETRIES=3`, `RETRY_BASE_DELAY_SECONDS=2` (exponential backoff) — in the Riva WebSocket bridge
- `OSCILLATION_THRESHOLD`, `DROP_THRESHOLD_PERCENT=30`, `DETECTION_WINDOW_MINUTES=10` — transcript quality monitors
- `DELETION_GRACE_PERIOD_SECONDS=60` — recording cleanup
- Hallucination detection: 3-way branch (Revise / Delete / False alarm) — correction runs before clinician sees output
- Worklist `rejectionStatus` endpoint — failed AI processing queue for manual review

### Evaluation methodology

**5-phase eval (KNOWN from whitepaper):**
1. Automated metrics + clinician spot-checks (WER, Medical Term Recall, precision/recall, stratified by subpopulation)
2. Blinded head-to-head trials with anytime-valid sequential hypothesis testing (not fixed-horizon t-test)
3. Staged release (alpha with trained early adopters)
4. Post-deployment monitoring (edit tracking as scalable signal, 1-5 star ratings → avg 4.3/5 English)
5. Quarterly 3-layer validation: automated LLM judge + clinical success director + third-party external audit

**Automated checklist eval (KNOWN from EMNLP 2025):**
Starting from 22K physician feedback items + star ratings:
1. GPT-4o generates yes/no checklist questions from ~900-1000 feedback items per batch
2. De-dup: `text-embedding-3-large` cosine similarity ≥ 0.85 → connected components → GPT-4o merges
3. Applicability tagging: `o3-mini` zero-shot CoT flags non-universal questions
4. Enforceability: `gpt-4-mini` generates pass/fail pairs; discard if enforceability < 0.70
5. Coverage-diversity optimization: `Score(k) = α·C + (1-α)·D - λ·k` where α=0.5, λ=0.0005; beam search selects final k=20 questions
Final: 97 → 50 → 36 → 20 questions. Macro F1 improved from 0.43 (baseline) to 0.63 (feedback-driven).

This closes the feedback loop: clinician edits → 22K feedback corpus → automated checklists → model update validation → ASR weekly updates.

### Key architectural constants (exact)

| Constant | Value | Source |
|---|---|---|
| ASR frame shift | 40ms | Riva docs (framework) |
| ASR streaming chunk (low-latency) | 0.16s / ±1.92s padding | Riva docs (framework) |
| ASR streaming chunk (high-throughput) | 0.8s / ±1.6s padding | Riva docs |
| Riva gRPC port | :50051 | websocket-bridge source |
| Audio sample rate | 16kHz LINEAR16 | websocket-bridge config |
| Riva `enable_automatic_punctuation` | true | websocket-bridge config |
| Riva `max_alternatives` | 1 | websocket-bridge config |
| Riva endpointing `start_history` | 200 | Riva docs |
| Flashlight beam size | 32 | Riva docs |
| LM weight | 0.8 | Riva docs |
| Correction dict total entries | 5,641 | websocket-bridge source |
| — clinician-reported entries | 558 | websocket-bridge source |
| — synthetic entries | 4,096 | websocket-bridge source |
| — generic name entries | 987 | websocket-bridge source |
| CACHE_MAX_AGE_MINUTES | 60 | env config |
| DROP_THRESHOLD_PERCENT | 30 | env config |
| Socket.IO pingInterval | 25,000ms | probe trace |
| Socket.IO pingTimeout | 20,000ms | probe trace |
| Socket.IO maxPayload | 1,000,000 bytes | probe trace |
| Linked Evidence RoBERTa backbone | base (medical) | FEVER@EMNLP 2024 |
| Linked Evidence training set | ~0.5M annotated tuples from 6,862 visits | FEVER@EMNLP 2024 |
| Checklist cosine dedup threshold | 0.85 | EMNLP 2025 paper |
| Checklist enforceability floor | 0.70 | EMNLP 2025 paper |
| Checklist optimization α | 0.5 | EMNLP 2025 paper |
| Checklist optimization λ | 0.0005 | EMNLP 2025 paper |
| ASR model update cadence | weekly | whitepaper |

### Multi-service topology (Verso-relevant microservices)

```
client-api / client-api-socket  — main REST + Socket.IO
clinician-api                   — clinician-specific surface
agent-api / agent-api-external  — agentic workflow gRPC service
audio-api                       — audio ingest
ears-streaming                  — real-time ASR streaming
bilrost / bilrost-streaming-api — cross-system message broker
llm-gateway (+ evals / playground) — central multi-provider LLM routing
llm-gateway-evals               — eval traffic isolated from prod
abridge-models                  — proprietary model serving (separate from gateway)
coder                           — ICD-10/HCC/CDI as standalone microservice
notes / soap-dashboard          — SOAP note generation/storage
nightingale-nestjs-api          — nursing product (NestJS, separate stack)
langsmith-live / langsmith-deid — LangChain observability (deid variant for PHI compliance)
vector-store                    — RAG backend for CDS/Assist
ehr-interop                     — FHIR/HL7 write-back to EHRs
eyes / eyes-api                 — internal annotation/review tool (IAP-gated)
livekit                         — self-hosted LiveKit SFU
argocd                          — GitOps K8s deploy
skypilot                        — multi-cloud GPU orchestration
```

LLM gateway pattern: ALL LLM calls go through `llm-gateway` (multi-provider routing proxy). `llm-gateway-evals` runs eval traffic against the same gateway shape but isolated. `abridge-models` serves proprietary models separately. Two-region GKE (us-central1 + us-east4) for the PHI/inference plane; Istio mTLS mesh-internal for everything sensitive.

**LangSmith deployed in two variants:** prod-live + deid (de-identified trace store for HIPAA compliance) — a pattern for observing agent traces without storing PHI.

### Design patterns for Verso

**"Ornamentation and condensation" (Lipton, verbatim):** The production design loop is: (1) prompt your way to a behavior, (2) layer on multiple calls to different models in sequence, (3) once the pipeline is "mostly right but has a failure mode, add a guardrail call as post-processing," (4) once the full pipeline ("Byzantine workflow") works, **collapse it via distillation into a single model call** (NeurIPS 2023: "Tokens Are Not All You Need"). Repeat: extend → refine → distill → extend. This is the pattern behind the dict distillation, the hallucination guard, and the full pipeline evolution.

**"Content vs upholstery" eval decoupling:** A shared structuring/backbone layer (subject to rigorous eval across thousands of encounters) feeds multiple thin stylistic renderers (concise/verbose, narrative/bullets, specialty). Evaluate the backbone, not every renderer. This keeps the eval surface tractable.

**Cost gradient:** rule lookup is O(1) and free; the entailment gate is one forward pass of a frozen BERT + small acoustic head; the expensive correction is gated to fire only on the residual (~5% of spans). Expensive models only run on cases the cheap models can't handle.

**LLM-as-judge eval at scale:** 22K feedback items + 1-5 star ratings → automated checklist via LLM synthesis, dedup, enforceability testing, coverage-diversity optimization. Closes the feedback loop without manual annotation.

---

## Pleep — Multimodal AI Sales Agent

### What it is

Pleep is a vertical SaaS AI sales agent for CIS (Russian-speaking) markets. Core primitive: a 7-question wizard that scrapes a business website, extracts structured data, and auto-generates a sales agent that works over WhatsApp/Telegram/Instagram/voice — without the operator ever writing a prompt. Self-reported 99.87% factual accuracy (RAGAS, LLM-as-judge, 1,000 real conversations, Q1 2026).

**Assessment:** Wrapper, not revolution. Multi-LLM (Claude 3/3.5 Sonnet, GPT-4o, Gemini 2.0 Flash) per-agent, Knowledge base as RAG + structured entity store, conversational state machine in system prompt. The product insight is "remove prompt engineering from the equation for non-technical operators" — a wizard that generates the system prompt from structured data.

### Agent loop / pipeline shape

Stateless per-message inference. No persistent agent loop between turns. Full pipeline per inbound message:

```
Inbound message (WhatsApp webhook / Telegram / Instagram / Web widget)
  → Thread identification (phone/chat_id → thread_id)
  → Mode check: AI | OPERATOR (auto-handoff via keyword detection)
  → Working hours check (disableFromHour:22, disableToHour:8)

Context assembly (NestJS backend):
  → Conversation history (full thread.messages[])
  → Knowledge base retrieval:
      category-aware semantic retrieval (Products / Q&A / Procedures / Contacts / Context / Other)
      mid-conversation re-retrieval supported (Feb 2026)
      fallback: "I cannot answer" if no relevant chunk found
  → CRM data injection (amoCRM / Bitrix24 / MoySklad / Altegio / Google Calendar)
  → Agent instructions (system prompt from generateInstructions)
  → Extension configs (follow-up rules, delay, splitting, working hours)

LLM inference (per-agent provider routing):
  ANTHROPIC → Claude 3 Sonnet or Claude 3.5 Sonnet
  OPENAI    → GPT-4o (inferred)
  GOOGLE    → Gemini 2.0 Flash (confirmed as default state)
  (LLM params — temperature, max_tokens, etc. — entirely server-side, not visible in bundles)

  Tool use (April 7, 2026 feature):
  → REST API tools: arbitrary external HTTP calls mid-conversation
  → MCP server tools: connect to user-configured MCP servers
  (implementation: Claude tool_use / OpenAI function calling; unified backend abstraction inferred)

Response status: "thinking" → "generating" → "verifying"

Post-processing:
  → Message splitting (max chars per fragment, inter-fragment pause)
  → delayMessageTime (human-feel latency, 1-3 seconds recommended)
  → Typing indicator ("..." while generating)

Delivery:
  → WhatsApp: Meta Cloud API (WABA) / GupShup
  → Web widget: Socket.IO "ai.message.saved" {id, text, threadId}
  → CRM sync (amoCRM / Bitrix24 / MoySklad / Altegio / Google Calendar — on AI actions only)
  → Follow-up scheduling (30min to 3-day delays, quiet hours)
```

**Response status states** ("thinking → generating → verifying") explicitly suggest a multi-step pipeline where the "verifying" step is a post-processing accuracy check — consistent with the 99.87% claim and the mid-conversation re-retrieval mechanism.

### System prompt generation pipeline

The wizard is the core product insight. A 7-question onboarding flow produces the agent's system prompt without the operator ever writing one:

```
Phase 1: fetchAgentDataAction(url, useCase, locale)
  → scrapes website (up to 100 pages), extracts:
     { agent_name, user_company_name, company_activity_description,
       primary_conversion_goal, key_benefits,
       formality_address_ru: "formal_vy" | "informal_ty" | "adaptive",
       letter_case_style, timezone, currency }
  → scrapedContent (raw text for KB)

Phase 2 (sales only): generateSalesScript({companyName, ...})
  → returns { steps: [{step_number, instruction, id}], reasoning: string }
  → user edits via drag-and-drop step editor (react-beautiful-dnd)
  → steps serialized as "1. Step one\n2. Step two\n..."

Phase 3: generateInstructions({all structured data + assistantDialogFlow + salesCycleDays})
  → returns { prompt: string, description: string }
  → prompt becomes the agent's permanent instructions (user never sees it)
  (server-side server action — implementation not in bundles)

Phase 4: createAssistant({name, instructions: prompt, model, provider})
  → createAnthropic({assistantId, model: "CLAUDE_3_SONNET"}) or createOpenAI({assistantId})
  → upload files to knowledge base
  → deleteAssistantCache(assistantId)
```

**Improvement system** (NOT fine-tuning — prompt rewriting only):
- User describes problem in natural language ("agent gives wrong prices")
- System rejects vague requests ("make it better")
- Analysis: examines current agent settings and instructions
- Generation: rewrites relevant sections, preserves untouched sections
- A **separate fine-tuned model** for prompt-engineering (from llms.txt: "Pleep has its own LM model fine-tuned for prompt-engineering") — used for the improvement feature, not for inference

### Knowledge base / RAG system

**NOT standard RAG.** Pleep uses category-based semantic parsing:

Six content types: Products, Q&A, Procedures, Contacts, Context, Other. Documents parsed into typed entity records, not arbitrary text chunks. Each entity is individually editable and live-updateable (no re-indexing queue). Retrieval is category-aware before similarity search.

**Processing model:** Claude 3.5 Sonnet used for file upload categorization; Claude 3 Sonnet for manual content. LLM-driven entity extraction, not rule-based splitter.

Infrastructure: `rag.pleep.app` (RAG orchestrator), `embed.pleep.app` (embedding microservice), `vector.pleep.app` (vector store — likely Qdrant on Yandex Cloud Kazakhstan). Embedding model undisclosed.

**RAGAS benchmark methodology:** `text-embedding-3-large` for semantic dedup; RAGAS framework with LLM-as-judge on 1,000 real conversation samples. Accuracy trajectory: 96.3% (baseline) → 99.71% (Dec 2025, anti-hallucination system) → 99.87% (Q1 2026, mid-conversation re-retrieval).

### MCP integration (first-class, April 2026)

April 7, 2026 changelog: "Connect your AI agent to any external system via REST API or MCP servers to fetch real-time data on demand."

Architecture (inferred from NestJS backend + provider routing):
- Backend maintains unified tool abstraction mapping to Claude `tool_use` / OpenAI `tools[]` formats
- REST API tools: HTTP calls to user-configured endpoints during inference; results injected back into conversation
- MCP server tools: backend connects to user-specified MCP servers (stdio or SSE transport), discovers tools, exposes as function-calling schemas to LLM

No client-side tool definition schema visible — entirely server-side. MCP is now a first-class citizen alongside REST tools.

### Constants / behavioral tuning

| Parameter | Value / Type | Notes |
|---|---|---|
| `delayMessageTime` | 1–3s recommended | Human-feel typing pause |
| `delayThreadTime` | configurable | Pause before first response in new thread |
| `disableFromHour` | 22 | Quiet hours start |
| `disableToHour` | 8 | Quiet hours end |
| `salesCycleDays` | 3 (sales), 0 (support) | Default in generateInstructions |
| `writeQuantity` | 1–2 recommended | Follow-up count |
| Follow-up delays | 30min/1h/2h/4h/8h/12h/24h/3d | Predefined options (ms: 18e5...2592e5) |
| Website scrape limit | 100 pages | Confirmed llms.txt |
| Instagram scrape limit | 120 posts | Confirmed llms.txt |
| Trial localStorage TTL | 86,400,000ms (24h) | Unsigned user session |
| Conversion metric | 23.6% (Pleep) vs 21% (human reps) | Self-reported, 500 chats |
| Avg AI response speed | 22.7s | vs 9.36min for human operator |
| Avg messages/conversation | 5.3 | Analytics |
| Analytics analysis cadence | Every 24h (last 100 chats in 5 min) | Pipeline |

### Design patterns for Verso

**"Promptless" as product thesis:** Non-technical operators can't write system prompts. The wizard collects structured intent → LLM generates the system prompt → user edits via natural language improvement requests, never touching raw prompts. The prompt is the configuration layer, but it's managed programmatically. This is the "configuration as code, but the code is generated" pattern.

**Per-agent provider routing:** Each assistant entity has independent `model`/`provider` settings with a nullable `openai`/`anthropic` extension object. Provider switching is per-agent, not global. This decouples the LLM selection decision from the framework.

**"Thinking → generating → verifying" pipeline transparency:** The multi-step response status ("thinking" = context assembly + retrieval, "generating" = LLM inference, "verifying" = post-processing) is surfaced to operators. This gives humans visibility into the pipeline stage without exposing internals.

**Behavioral realism as first-class concern:** `delayMessageTime`, `delayThreadTime`, typing indicators, message splitting — deliberate latency injection to match human communication patterns. The design goal is not minimum latency but appropriate latency for the context.

**Mid-conversation re-retrieval:** Initial retrieval at conversation start is not sufficient — agents need a mechanism to trigger additional KB searches mid-conversation when their current context is insufficient. This was explicitly added to reduce hallucinations.

---

## Aemon — Autonomous AI R&D Engineer

### What it is

Aemon is an autonomous evolutionary R&D engineer. Input: a problem + an eval/objective function. Output: state-of-the-art solutions discovered through evolutionary search guided by LLMs that read and synthesize research papers. Forward-deployed (no self-serve), YC W26.

The primitive: the **evolutionary optimization engine** using LLMs as the mutation/generation operator within an evolutionary search framework, enhanced with a research paper RAG layer built on the founders' SOTA retrieval expertise (EMNLP 2024 FIRST paper on listwise reranking, ICLR 2025 CoRNStack on code retrieval).

Demonstrated: new SOTA on 26-circle packing (NP-hard) with <$10 compute, beating AlphaEvolve.

### Agent loop shape

**Evolutionary loop (AlphaEvolve/FunSearch pattern):**

```
[Program Database — MAP-Elites islands]
  ↑ insert successful variants
  │
  ← [Evaluator Pool — user's eval function]
        ↑ score candidates
        │
  ← [LLM Ensemble — generate mutations]
        ↑ receive prompt
        │
  ← [Prompt Sampler — context assembly]
        ↑ parent selection (quality-weighted + creative "inspiration" programs)
        │                 + evaluation results + problem description
        └←── [Research Paper RAG]
               → planning stage: LLM generates targeted research questions
               → search: arXiv/PubMed/domain corpus retrieval
               → synthesis: writing agent integrates evidence with current state
               → reflection checkpoints: continue or finalize?

Human steering (mid-run):
  user provides natural language constraint
  → Aemon interprets as architectural changes (citation_boost=0.15, statute_boost=0.10)
  → progress RESETS to 0% — full re-evolution triggered (NOT parameter tuning)
```

**5-stage pipeline (animation constants from JS bundle):**

```
{conceptualize: 9000ms, evolve: 13000ms, improve: 10000ms, steer: 8000ms, solution: 9000ms}
progress bar: {prompt: 0, conceptualize: 20, evolve: 45, improve: 70, steer: 0 (RESET), solution: 100}
```

The `steer` stage resetting to 0% is architecturally significant — human steering triggers a full re-evolution, not parameter adjustment.

**Loop termination:** When the eval metric plateaus or a target threshold is reached. Demo shows 18 configurations across ~5 generations (23 experiments total); real runs likely thousands.

### Models

LLM provider unknown (no model strings in bundles). Based on AlphaEvolve pattern + OpenEvolve community findings:
- Likely multi-model ensemble: Gemini Flash (high throughput, broad exploration) + Claude Sonnet (high quality, breakthrough mutations)
- Research RAG: contrastive embedding model (CodeRankEmbed-style, 137M params) + listwise LLM reranker (FIRST-style single-token decoding, 50% latency reduction)

Infrastructure: zero subdomains resolve (forward-deployed only, no public product). Website on Cloudflare Workers via OpenNext.

### Key research patterns (RAG-guided evolution)

DeepEvolve (arXiv 2510.06056) describes exactly Aemon's approach:
1. Planning: LLM generates targeted research questions from problem context
2. Search: questions submitted to academic corpora, results retrieved
3. Synthesis: writing agent integrates evidence + problem context + past algorithms → multiple candidate ideas with self-evaluation
4. Reflection: validates whether to continue research or finalize

Ablation results from DeepEvolve proving research augmentation:
- Pure AlphaEvolve (no research): plateaus after generation 1 on Molecular Prediction (+0.6%)
- With research: sustained progress (+2.96%)
- Circle Packing: 666% improvement vs pure evolution

**Aemon's retrieval stack advantage:** CoRNStack consistency filtering (+16 nDCG points in ablation), FIRST single-token reranking (50% faster), CodeRankEmbed (137M beating CodeRankSage-Large at 1.3B on code retrieval).

### Eval as first-class primitive

Aemon's entire architecture presupposes **a user-supplied eval function** as the entry point. The eval is the interface, not a secondary concern. Without a concrete, measurable objective function:
- Parent selection is undefined (quality-weighting has no signal)
- MAP-Elites feature grid can't be constructed
- Cascade evaluation (simple checks first) has nothing to cascade to
- Human steering has no objective to optimize toward

The demo problem: "Fix multi-hop query failures and maximize Recall@10 across all 50 test cases." The eval IS the spec. This is radically different from natural-language goal specification.

**Cascade evaluator pattern:** simpler checks first, comprehensive evaluation only for promising candidates. Multi-metric optimization "surprisingly yields better results, even when only a single metric is important" (AlphaEvolve paper).

### Design patterns for Verso

**Eval as the contract:** In an evolutionary agent loop, the eval function is the only stable interface. Everything else (LLM selection, population size, mutation strategy) is configurable. If Verso has an "optimize against an objective" mode, the eval should be the first-class entry point, not an afterthought.

**MAP-Elites for diverse exploration:** Rather than pure gradient descent toward a single optimum, MAP-Elites maintains a population distributed across a feature grid — finds many different good solutions, not just one. The diversity preserves exploration even as the fitness frontier advances.

**SEARCH/REPLACE diffs, not full rewrites:** LLMs generate mutations as SEARCH/REPLACE diffs on the existing code. This preserves structure (monotonic mapping, not arbitrary generation), reduces hallucination surface, and keeps mutations coherent with the parent.

**`# EVOLVE-BLOCK-START` / `# EVOLVE-BLOCK-END` markers:** Explicit demarcation of the evolvable section vs fixed scaffolding. This is a clean interface between the framework (fixed) and the agent-controlled code (evolved).

**Research-augmented evolution beats pure evolution by 666% on hard problems.** The RAG layer is not optional decorations — it's the primary differentiator. A general-purpose agent framework that can ingest domain-specific literature before acting will systematically outperform one that relies on pretrained knowledge alone.

---

## → Verso Implications

### Copy (proven patterns)

1. **Multi-model gateway as first-class infrastructure.** Abridge's `llm-gateway.abridge.services` is a central multi-provider LLM routing proxy, with `llm-gateway-evals` as a separate isolated eval path against the same interface. Verso should have a model gateway layer from day one — not direct provider calls in agent code. The eval path must be isolated from prod traffic.

2. **Distill pipelines into single calls via training, not prompt chaining.** Abridge's "ornamentation and condensation" loop: build a pipeline of LLM calls, validate it works, then distill the whole pipeline into a single fine-tuned model call. Verso should support this as a native lifecycle: `pipeline → eval → distill → deploy`. Agents should degrade gracefully from full pipeline (development) to distilled single call (production).

3. **Eval as a first-class deliverable alongside agent code.** Abridge: 5-phase eval including automated checklists generated from real user feedback. Pleep: RAGAS + LLM-as-judge pipeline. Aemon: eval function IS the entry point. Verso agents should have a standard eval interface (`Eval<Input, Output>`) that is authored alongside the agent, not bolted on later.

4. **Typed knowledge store, not raw vector chunks.** Pleep's category-aware KB (Products / Q&A / Procedures / Contacts / Context) outperforms standard RAG (99.87% vs 91.8% for raw Claude 3.5). Verso's memory/RAG abstraction should support typed knowledge stores where retrieval is category-filtered before similarity search. The abstraction is `TypedKnowledgeBase<T extends KnowledgeCategory>`, not just `VectorStore`.

5. **Mid-conversation re-retrieval as a first-class tool.** Pleep explicitly added mid-conversation re-retrieval (Feb 2026) after finding single-pass retrieval insufficient. Verso's RAG tool should support this natively: a `retrieve(query, context)` tool that agents can call at any point in the conversation, not just at context assembly.

6. **Dual observability: prod traces + deid traces.** Abridge's `langsmith-live` + `langsmith-deid` pattern — when PHI, PII, or sensitive data flows through agent traces, you need a deidentified trace store alongside the live one. Verso should support a `tracing.mode: "deid"` configuration that applies a sanitizer before persistence.

7. **Cost gradient: cheap → gate → expensive.** Abridge's transcription pipeline: deterministic dict lookup (O(1)) → entailment gate (one frozen-BERT forward pass) → expensive neural correction (fired on ~5% of spans). For any agent pipeline where cost matters, Verso should make this routing pattern idiomatic: fast guards first, expensive models only on residuals.

8. **Feedback-driven automated eval, not static benchmarks.** Abridge's EMNLP 2025 pipeline: user feedback → LLM-generated checklist → enforceability testing → coverage-diversity optimization. This turns user behavior signals into automated regression tests without manual annotation. Verso's eval framework should support this pattern: `FeedbackCorpus → ChecklistGenerator → EvalSuite`.

9. **`EVOLVE-BLOCK-START` / `EVOLVE-BLOCK-END` for agent-controlled code sections.** Aemon's demarcation pattern is directly applicable to Verso: an agent that modifies its own tools or prompts should have explicit markers for what is agent-controlled vs framework-controlled. Prevents agents from overwriting scaffolding they shouldn't touch.

10. **MCP as first-class tool transport, not an afterthought.** Pleep added MCP as a first-class tool source (April 2026), alongside REST APIs, with a unified backend abstraction mapping to Claude `tool_use` / OpenAI `tools[]`. Verso is building MCP-first — confirm the abstraction layer handles both transports (stdio + SSE) and maps cleanly to any underlying LLM provider's tool format.

11. **Per-agent provider routing, not global.** Pleep's each assistant has independent `model`/`provider` settings. Verso agents should support per-instance model configuration, not just global framework defaults. This enables routing different conversation types (high-stakes → Claude Opus, high-volume → Gemini Flash) within the same deployment.

12. **Provenance as a structural feature, not post-hoc.** Abridge's Linked Evidence: every note claim is linked to the transcript span that supports it. The FEVER MidFusion model achieves 94% clinician acceptance (vs BM25 65%) — a 45% improvement from using a trained extractor over similarity retrieval. In Verso, agent outputs that make factual claims should have a provenance trail to the source context that grounded them.

### Avoid (failure modes to design away)

1. **Do not make the eval pipeline an afterthought or an optional add-on.** All three systems here treat evaluation as load-bearing infrastructure. Abridge has a 5-phase eval with 4-staff-level review. Pleep has RAGAS + LLM-as-judge. Aemon's entire architecture is organized around an eval function. If Verso makes it easy to build agents without evals, most agents will be built without evals.

2. **Do not rely on single-pass RAG.** Pleep's accuracy jumped from 96.3% to 99.87% by adding an anti-hallucination system and mid-conversation re-retrieval. Single-pass RAG is the baseline, not the goal. Design for multi-retrieval loops from the start.

3. **Do not confuse prompt modification with model improvement.** Pleep explicitly calls out: the improvement system modifies the system prompt, it does NOT fine-tune model weights. This is a critical distinction — prompt rewriting is cheap and instant; fine-tuning requires data and training. Verso should make this distinction explicit in its API surface.

4. **Do not expose raw prompts to end operators in production.** Pleep's "promptless" design is a product insight: non-technical users can't maintain raw system prompts. The prompt should be a computed artifact from structured configuration, not a user-editable string field. Verso's agent config DSL should generate prompts, not store them.

5. **Do not let the agent loop "escape" into unbounded exploration without human checkpoints.** Aemon's steer stage resets progress to 0% — human intervention is a hard reset, not a soft nudge. For Verso agents running long-horizon tasks, human steering should be a first-class primitive that fully re-anchors the search, not just a hint appended to context.

6. **Do not use generative LLMs for evidence extraction from source text.** Abridge's FEVER 2024 paper: LLMs are terrible at span-level evidence extraction (Llama-13B F=5.6, GPT-3.5-turbo F=26.8 on USB). The trained MidFusion RoBERTa extractor achieves 94% clinician acceptance vs LLM-generated citations' near-zero score. For any agent that needs to attribute claims to source spans, use a dedicated trained extractor, not "ask the LLM for citations."

7. **Do not trust self-reported completeness of a single retrieval pass.** The Transformer corrector in Abridge's 2020 work catastrophically failed (WER 92.2) at 230K training pairs — 21x less data than needed. Lesson for Verso: component choices need to be validated at your actual data scale, not benchmarked at the academic dataset scale.

### Verso could improve by

1. **Native "distillation gateway":** When an agent pipeline reaches quality targets on eval, automatically offer to distill the pipeline into a fine-tuned single model call. The gateway already knows which models/prompts/tools ran — it has everything needed to construct training pairs. This closes the "ornamentation and condensation" loop within the framework.

2. **Pipeline-stage streaming transparency.** Abridge surfaces "ML_STARTED → ML_PROCESSING_PRIORITY → ML_SUCCESS" to clients. Pleep surfaces "thinking → generating → verifying." Verso's streaming protocol should support named stage events alongside token streams, so clients can show users where in the pipeline their request currently lives.

3. **Cellular deployment model.** Abridge uses a `commercial` cell and a `kaiser` cell (separate tenant stack visible in `*.kaiser.abridge.cafe`), with `NEXT_PUBLIC_ABRIDGE_CELL=commercial` in the env config. For Verso agents serving regulated industries (healthcare, finance, legal), a cell-isolation model where sensitive tenants get their own stack is a key enterprise feature.

4. **Feedback-to-eval pipeline as a standard module.** Abridge's EMNLP 2025 checklist pipeline (user feedback → GPT-4o question generation → dedup → enforceability filtering → coverage-diversity optimization → automated regression suite) is generalizable to any domain. Verso should ship this as a standard `FeedbackToEval` module with sensible defaults (α=0.5, λ=0.0005, enforceability_threshold=0.70, cosine_dedup_threshold=0.85).

5. **Cascade evaluator primitive.** Aemon's "simpler checks first, comprehensive evaluation only for promising candidates" is a general optimization for any iterative agent loop. Verso should expose a `CascadeEval([fast_check, medium_check, full_eval])` primitive that short-circuits on failure at each stage, with configurable thresholds per stage.
