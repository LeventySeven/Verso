# Teardown Cluster: Stardrift + Gordian + Wedge

**Cluster focus:** Production agent systems in healthcare and travel — real agentic pipelines built by small teams under latency and compliance constraints. Three distinct patterns: (1) a polished travel-planning conversational agent with a novel streaming layer (Stardrift), (2) a non-LLM ML-ranking engine wrapped in a gRPC service mesh with a thin REST/browser-SDK surface (Gordian), and (3) a healthcare voice-agent shop whose full AI stack is reconstructed from confirmed employees' side projects (Wedge).

---

## Stardrift

**Source:** `teardowns/STARDRIFT.md`, 4,802 lines, multiple RE rounds through May 2026.

### What it is

Travel-planning conversational AI agent — a user describes a trip in natural language, the agent plans a full itinerary via multi-step tool calls, streams output token-by-token back to the client, and persists the result as an editable trip object in a Postgres-backed data model. Entity: Kopfkino, Inc. 3-person founding team. YC-backed.

### Agent loop shape

Single-agent, tool-use loop. No multi-agent orchestration (no LangGraph/CrewAI/AutoGen signatures anywhere). Uses Vercel AI SDK v5's `streamText({ model, messages, tools, maxSteps })` pattern. `maxSteps` inferred at 10–20 (typical for a cascade of search tool calls: flights → hotels → attractions → rail). Tool calls are likely serial (parallel via Anthropic `parallel_tool_calls` unconfirmed).

Loop: user turn → build context (history + prefs + tools) → LLM streamText → tool execution → append to history → continue until assistant emits a final non-tool response or `maxSteps` reached. Termination: implicit (max steps or tool-free LLM reply). No explicit planner/verifier split.

### Models

- **Primary (in-call LLM):** Claude (Anthropic) — INFERRED. Haiku already confirmed in stack for cheap structured-output classification; blog explicitly evaluates Claude for the streaming problem. Vercel AI SDK is provider-agnostic so GPT-4/5 is also possible. Mark INFERRED.
- **Claude Haiku:** confirmed for `query_to_place()` — converting freeform text like "Isle of Skye road trip" into typed `{type: "city"|"country"|"region", name: str}` objects. Described by team as "the best AI products don't use AI for everything; they use it for what it's good at." Haiku = fast/cheap structured-output, not the generalist planner.
- No fine-tuning, no local models, no routing between multiple planners.

**Model-selection lesson for Verso:** the two-model pattern (cheap fast classifier + capable generalist planner) is a documented intentional choice, not accidental. Verso should make this router pattern ergonomic: declare a lightweight `classifier_model` next to the `planner_model` in the agent definition, not buried in tool config.

### Tool registry

KNOWN surfaces (from CSP allowlist + API probes + blog + HN job post):

| Tool | Confirmed? | Notes |
|---|---|---|
| `query_to_place(query: str) -> List[Place]` | KNOWN (blog verbatim) | Haiku-backed. Place = `{type: Literal["region","city","country"], name: str}` |
| `search_flights` | KNOWN (HN job post: "Amadeus and Duffel") | Duffel for NDC booking-grade; Amadeus for GDS long-tail |
| `search_hotels` | KNOWN (CSP: Booking, Agoda, Vrbo, Airbnb image hosts) | Via Amadeus + affiliate OTA |
| `search_rail` / `search_amtrak` | KNOWN (CSP `form-action amtrak.com`) + INFERRED for intl rail | |
| `search_attractions` / `search_places` | KNOWN (CSP `places.googleapis.com`, `media-cdn.tripadvisor.com`) | |
| `geocode` | KNOWN (blog) | Google Maps lat/lng for nearest-neighbor match |
| `get_destination_photo` | KNOWN (blog, S3 bucket) | Haiku → Place → curated S3 → Google geocode fallback → manual backfill |
| `get_starlink_likelihood(flight_number, date)` | KNOWN (HN post, public API) | 3-signal scoring: airline → aircraft body → tail number |
| `add_activity` / `update_itinerary` / `remove_activity` / `create_itinerary` / `move_day` | INFERRED (required by product surface + Vercel AI SDK pattern) | |
| `feedback_capture(user_question, assistant_response, is_helpful)` | KNOWN (extracted from `/api/feedback` Pydantic schema) | Feeds evals pipeline (HN job post: "building evals") |

**Total visible tool surface:** ~10 tools, all domain-specific. No generic web-search tool. No code execution. Tools are thin HTTP wrappers around external APIs.

**Verso lesson:** narrow tool registries with clear domain-specific purpose beat wide "search anything" registries for agents with a known task class. Verso should support declaring a tool registry at agent-definition time and injecting the full schema into the system prompt automatically — the team explicitly manages tool docs in the system prompt (INFERRED from product behavior).

### Context assembly

- Conversation history: persisted in Postgres per trip (`messages` table). Reloaded in full on conversation open.
- User context: preferences (passport, home city/airport, frequent-flier, dietary) captured at `/onboarding` and injected into system prompt at session start. Trip state (existing itinerary) injected per turn.
- Token budget: INFERRED to rely on Claude's 200K context window without aggressive trimming — typical travel chat is 5–10 turns, well within budget.
- No cross-trip memory: memory is trip-scoped. Prior trips are not surfaced to the planner.
- `MINIMUM_VALID_TIME` equivalent: no explicit basket-style time budget in the agent loop, but booking handoffs have expiry logic at the supplier level.

**Verso lesson:** inject trip/session state as a structured block at the start of context (not interleaved in messages) — easier to update on mutation, easier for the LLM to reference as a ground truth anchor.

### System prompt (INFERRED, not directly extracted)

Mega-repos (x1xhlol, asgeirtj, CL4R1T4S) checked — no Stardrift prompt leaked. Inferred structure:

1. Identity: "You are Stardrift, an AI travel agent..."
2. Time anchor: current date (needed for relative date handling: "leaving next Friday")
3. User context: name, home city/airport, passport nationality, dietary preferences, frequent-flier programs
4. Tool documentation: full schemas for ~10 tools listed above
5. Output format: structured itinerary edits + conversational replies
6. Constraints: prefer bookable inventory, respect budget tier (economy/business/premium), visa-awareness
7. Taste/curation prompts: "prefer locally-owned hotels" style guidance (INFERRED from blog: "designing AI with taste")

**Verso lesson:** the system prompt is the integration point between agent identity, user state, and tool documentation. Verso should provide a first-class `system_prompt_builder` that takes (identity_block, user_context, tool_schemas, output_format, constraints) and assembles them in a consistent order — prevents teams from ad-hoc string concatenation scattered across the codebase.

### Streaming protocol (KNOWN — primary novel finding)

The streaming infrastructure is the most architecturally distinctive piece of Stardrift's stack. Felipe Mautner's engineering blog post ("Is resumable LLM streaming hard? No, it's just annoying") describes four evolutionary steps:

**Step 1 (MVP):** Next.js → FastAPI (Modal) → LLM via SSE. Simultaneous token storage to DB for persistence.

**Step 2 (Streamstraight, abandoned):** Third-party WebSocket fallback service. Replaced — limitations unspecified.

**Step 3 (Infrastructure refactor):** Separated conversation-loop logic into Modal serverless workers (`modal.spawn`). Implemented Redis streams as a buffer between LLM-worker and web backend. Web backend subscribes to Redis stream and relays to client via SSE. Decoupled LLM call from SSE connection lifetime.

**Step 4 (Current — resumable, KNOWN):**
- Frontend: Vercel AI SDK v5 `useChat` hook + custom `StardriftTransport` class
- `reconnectToStream()` method on the transport, triggered on component remount
- **Redis KV:** `chat_id → active_message_id` (tracks whether a stream is currently active for a chat)
- **Redis Streams:** keyed by `(chat_id, message_id)` — actual token-by-token buffer
- **Reconnection logic:** check Redis KV on reconnect → if `active_message_id` exists → resume from last delivered cursor on the Redis stream → relay via SSE to client
- **Race condition fix:** KV store is separate from the stream itself because "direct stream inspection proved unreliable" (verbatim quote) when streams complete before backend reads final chunks
- **Message ID quirk:** Vercel AI SDK's `useChat` hook doesn't expose `message_ids` until stream completes → Stardrift maintains its own message-ID state in Redis
- **Constraint enforced:** maximum one active stream per chat at all times

**Full stack:**
- Client ↔ Web backend: SSE
- LLM worker → Web backend buffer: Redis Streams
- Active stream tracking: Redis KV
- Workers: Modal serverless containers (spawned via `modal.spawn`)
- Fallback WebSocket: `wss://realtime.stardrift.ai` (AWS ELB us-west-2, "flight-chat-realtime")
- Token SSE format: Vercel AI SDK v5 standard: `data: {"type":"text-delta","textDelta":"..."}\n\n`

**Verso lesson (critical):** streaming resumption requires three independent concerns:
1. Decoupled LLM execution from the HTTP connection (worker process or background task)
2. Durable token buffer with cursor semantics (Redis Streams is the proven solution)
3. Active-stream KV store separate from the buffer itself

Verso should provide a `StreamingTransport` abstraction with built-in resumption semantics — the framework decouples LLM worker from HTTP response handler automatically. Teams should not have to rebuild this from scratch.

### Constants

- Inspiration cards (homepage prompt templates): **23** (from `/api/explore` — public endpoint)
- Place classification taxonomy: `Literal["region", "city", "country"]` (verbatim Python)
- Vercel AI SDK `maxSteps`: INFERRED 10–20
- Stream: max 1 active per chat (enforced)
- Unsplash rate limit: 20 places/hour (manual curation throughput)
- AWS ALB cookie: 7-day TTL

### Error handling

- UI degrades gracefully on SSE drop → `reconnectToStream()` transparently resumes from cursor
- LLM worker crash → `modal.spawn` restarts independently; Redis stream buffer persists the tokens already sent
- No explicit retry logic observed for tool call failures (INFERRED: Vercel AI SDK default error propagation)
- Feedback loop for quality: `feedback_capture()` tool (thumb up/down per turn → evals pipeline)

### Evals

HN job post: "optimizing LLM performance and building evals." Mechanism: `POST /api/feedback` schema confirmed: `{user_question: str, assistant_response: str, is_helpful: bool}`. Each (Q, A, helpful?) tuple persisted to a DB table. 23 public `/api/explore` prompt templates serve as the calibration corpus.

**Verso lesson:** first-class feedback capture as a built-in tool (not an afterthought). Verso should provide a `FeedbackCaptureTool` that automatically attaches to any agent conversation and persists (turn, response, signal) triples to a configurable store.

### API/DX shape

**Backend:** FastAPI + Pydantic v2 on Modal serverless (confirmed via Pydantic v2 error format from 422 probes). Fronted by Vercel API route proxies (Next.js 14 App Router).

**Chat endpoint:** `POST /api/chat` body schema (Pydantic v2, extracted from 422 errors):
```python
trip_id: str
message: str
message_id: str
history: list  # conversation history
metadata: dict | None
```

**Auth:** Stytch (magic links + OAuth). Frontend token: `public-token-live-eb52ed5e-1e3f-429c-9345-478831083eda` (safe to expose — Stytch public token design).

---

## Gordian

**Source:** `teardowns/GORDIAN.md`, 5,083 lines, two RE rounds through May 2026.

### What it is

B2B travel ancillary upsell platform — a JavaScript SDK that airline and OTA partners embed to let passengers select and purchase seats, bags, and check-in from within the partner's checkout flow. Revenue model: takes a cut of per-ancillary markup. Two Python stacks in prod (Pyramid legacy corev1, Flask corev2), a FastAPI macroservice, and 24+ internal Go gRPC microservices. ML ranker for seat recommendation and dynamic pricing.

**Gordian is primarily a non-LLM ML system**, not a generative AI system. The architecture lesson for Verso is about how tabular ML and agent systems must coexist, and about SDK/API design for complex B2B integrations.

### Agent loop shape

No LLM agent loop. The "intelligence" is a **tabular ML ranking pipeline**, not an LLM. The closest thing to an agent loop is the basket-revalidation poll (`basketValidator.ts`): 30 attempts at 2-second intervals (60 seconds total hard ceiling) waiting for async seat/bag search results, with basket validity enforcement (`MINIMUM_VALID_TIME = 360,000 ms = 6 minutes`). The seat-search timeout is a hard 100,000 ms (100 seconds), polling every 1 second.

### Models

Not LLMs. Tabular ML:

| Component | Inferred model | Evidence |
|---|---|---|
| Conversion-probability scorer | LightGBM / XGBoost → ONNX export | 9M labeled samples/year; CEO ex-Skyscanner ML; `gonum` transitive dep in Go workspace |
| Optimal-price recommender | Contextual bandit on top of conversion scorer | Dynamic pricing + multi-arm A/B tests confirmed in SDK (`test_seatmap_one_click_*`, `test_seatmap_confetti` feature flags) |
| Seat-rank scorer | Pairwise/listwise LTR (LambdaMART, LightGBM-Ranker) | Same telemetry stream as conversion; ranking loss output |
| Per-traveler segmentation | K-means / K-prototypes | Fast, interpretable; cluster ID as one-hot feature into GBT |
| Fare-family/fare-basis embedding | Entity embedding trained jointly with GBT | High-cardinality categorical standard treatment |

**Serving:** `pricing-service` Go gRPC service (internal, not public). Models exported to ONNX, loaded via `onnxruntime_go` (inferred from `gonum` transitive dep in Go workspace). **Latency target: <50ms p99 for a single ranking call.**

**Training data collection mechanism (KNOWN — `macroservice` OpenAPI leak):** `POST /pricing_data/input` endpoint receives `{session_id, unique_id, screenshot: str, request_metadata: dict, pricing_data: dict, carrier, product_type, arrival/departure_airports, times, itinerary}`. Browser automation bots (`browsermanager` service, Playwright pool) scrape airline pricing pages, extract structured JSON + screenshot, and POST to this endpoint. This is the ML training data pipeline.

**Verso lesson:** Verso agents will often need to feed telemetry back into training pipelines. Build a `TelemetryCapture` primitive that is as easy to attach to an agent conversation as the tools themselves — not a separate instrumentation concern.

### Tool registry

No LLM tools. The SDK exposes a **REST + browser-widget** surface, not a tool-calling loop. The closest analog:
- `POST /v2.2/trip` — creates a trip session, kicks off seat/bag search inline
- `GET /v2.2/trip/:id/search/:search_id` — polls search status (Gordian's "tool result retrieval")
- `POST /v2.2/trip/:id/basket/check` — async basket revalidation (`{status: "queued"}`)

The polling pattern (100s hard timeout, 1s interval) is functionally equivalent to Verso's concept of a "long-running tool" that yields status updates rather than blocking.

**Verso lesson:** support long-running tools that emit intermediate status updates before a final result. Design: `tool.status()` returns `"in_progress" | "success" | "failed"` with a cursor the framework re-polls at configurable intervals. The 100s/1s pattern from Gordian is a real production requirement for tool calls that hit slow external APIs.

### Context assembly

No LLM context. The widget assembles a `tripCreationToken` or `(tripId + tripAccessToken)` context per session. Three distinct auth token lifecycles:
- `tripCreationToken` — S2S from partner backend, used to POST /trip, short-lived
- `tripAccessToken` — returned by /trip, used by browser SDK for all subsequent calls, trip-scoped
- `searchToken` — for view-only seatmap searches without a trip (shopping-flow previews)

**Verso lesson:** scoped session tokens (not just API keys) are the right auth primitive for agentic workflows where different agents/phases have different privilege levels. Verso should support declaring token scopes per agent step.

### Memory

No agent memory. Trip state persists in Postgres, keyed by `trip_id`. Basket state has a TTL (`MINIMUM_VALID_TIME = 360,000 ms`). The `pricing_data/output` endpoints provide historical per-route pricing for ML training — this is ML feature store, not agent memory.

### Streaming protocol

No LLM streaming. Results are polled via GET with `status: 'in_progress' | 'success' | 'failed'`. The async pattern is: fire POST → get `{search_id}` → poll GET until status resolves.

**Verso lesson:** polling with exponential backoff is the right primitive for tools that call slow external services. Verso should build this in, not require teams to implement polling loops manually for every slow tool.

### Schema / data model (KNOWN — full extraction)

The full trip/passenger/seat/pricing data model is recoverable from the public SDK sourcemap (17 TypeScript files extracted). Key shapes:

**Trip state:** `{trip_id, trip_access_token, search_id, integration, organization, trip_state_hash, journeys[], orders[], passengers[]}`

**Basket validity:** `validity: {status: 'valid'|'checking'|'price_changed'|'unavailable', valid_from: ISODate, valid_until: ISODate}`

**Identity documents:** 8 types (passport, national ID, resident alien card, known traveler number, redress number, visa, global entry, NEXUS).

**Auth error shape:** `{"error_type": "...", "message": "..."}` — consistent across corev2 (Flask). corev1 (Pyramid) has a different shape with `{error_type, in_progress, message, session_id, status_code, success}`.

**Token format (KNOWN via error probing):** Bearer tokens are NOT JWTs. They are opaque base64-encoded byte strings decoded by Python before auth logic runs. Error probes show Python's `binascii.Error` string, indicating Fernet tokens or `itsdangerous.URLSafeSerializer` format.

### Constants

- Basket poll: `MINIMUM_VALID_TIME = 360,000 ms (6 minutes)` — minimum basket validity at all times
- Seat-search timeout: `100,000 ms (100 s)`, interval `1,000 ms (1 s)` (verbatim from `api.ts:142-152`)
- Basket revalidation: 30 attempts × 2,000 ms = 60 s total
- ML model serving target: <50ms p99 for ranking call
- ML training volume: 9M ancillary sales/year → labeled conversion events
- Confidence haircut on conflict: `-0.1` to field confidence (specific to Gordian pricing model)

### Error handling

Custom JSON envelope: `{"error_type": "...", "message": "..."}`. Version-differentiated:
- corev2 (Flask): `{"error_type":"not_found","message":"Not Found"}` — simpler
- corev1 (Pyramid): `{error_type, in_progress, message, session_id, status_code, success}` — richer (legacy)

HTTP Basic auth vs Bearer token: dual scheme for S2S (API key) vs browser (trip-scoped token).

Basket validity state machine: `valid → checking → price_changed | unavailable` with time-gated enforcement. Items with `validity.status: "price_changed"|"unavailable"` are silently removed from basket during revalidation.

### Gordian's internal service mesh (gRPC, KNOWN service names / INFERRED per-service logic)

24+ internal Go gRPC microservices, all internal-only DNS. Notable for Verso context:

| Service | Purpose |
|---|---|
| `pricing-service` | ML ranker + markup optimizer; inferred ONNX-in-Go inference |
| `centaur` | Per-airline NDC/EDIFACT/direct API bridge (one per integrated airline) |
| `chimera` | Multi-source aggregator (fans out to N centaur instances) |
| `nexus` | Gateway / event bus / mesh ingress |
| `macroservice` | FastAPI reference data service (currencies, i18n, airline-pair bookability, pricing telemetry) — NOT a saga orchestrator (prior hypothesis corrected) |
| `browsermanager` | Playwright browser automation pool for airlines without APIs |
| `blackbox` | Per-airline scraping adapters |
| `corev1` | Legacy Pyramid/waitress Python monolith |
| `corev2` | Flask/gunicorn Python API (the v2.2 public surface) |

`macroservice` lesson: the name "macro" is a trap. It is the *macro-level globally-consistent reference data service* (currencies, phrases, airline-pair bookability), not a macro-orchestrator. Naming is confusing in distributed service meshes.

**Verso lesson:** for framework design — Gordian's service mesh architecture shows that the "agent" is just a thin coordination layer over durable domain services (pricing, inventory, identity, bookability). Verso should make it easy to integrate domain services as first-class tool providers rather than requiring agents to re-implement domain logic.

### ML telemetry design pattern (key finding)

The `Seat Confirmed` Mixpanel event ships **ratio metrics that re-normalize each booking against available inventory at the moment of decision**: `available_seats_percent`, `free_seats_percent`, seat-category metrics, price-bucket metrics per passenger class. This eliminates confounders: "bought paid seat in a sold-out cabin" vs "bought paid seat in an empty cabin" produce different ratio signals even though the raw label is the same.

**This is a deliberate architectural choice to make ML training data clean, not an accidental telemetry dump.** The SDK is designed to generate training data, not just track conversions. Every ancillary purchase is a labeled training point.

**Verso lesson:** instrument agents to emit normalized evaluation signals at decision points — not just "tool called / tool succeeded" but the full context (what alternatives existed, what was chosen, what the outcome was). This is what makes an agent system trainable and improvable over time.

---

## Wedge

**Source:** `teardowns/WEDGE.md`, 4,871 lines, multiple RE rounds through May 2026.

**Honest framing:** Wedge has no public production code. The production AI architecture is reconstructed from (a) confirmed team members' side-project repos (Tier-1A source for the pattern, INFERRED relevance to Wedge production), (b) a confirmed team member's own résumé (verbatim disclosures), and (c) the Moorcheh/Memanto SDK and paper (the memory layer the team is demonstrably fluent in). No Wedge production URL, repo, or prompt is public.

### What it is

Healthcare AI agent company (YC S25). "Palantir for Healthcare AI Agents." Forward-deployed engineering model: small team embeds inside hospital environments and builds/deploys custom AI agents for revenue-cycle, prior-auth, and referral management. Target workflows: insurance payer calls, fax-based referral intake, follow-up automation. Two confirmed production pipelines (from Het Patel's résumé, verbatim):

1. **Insurance Caller voice agent:** outbound LiveKit agent calling payers for prior-auth verification/follow-up. Stack: Deepgram STT + OpenAI (gpt-4o-mini in reference implementation) + ElevenLabs TTS + Twilio SIP.
2. **Automated Referral System:** fax ingestion + pdfplumber text extraction + Groq LLM structured extraction → structured Supabase records → triage agent + scheduled follow-up. Stack: FastAPI + Supabase + Groq.

### Agent loop shape (SD-voice-ai-service reference implementation — Tier-1A)

The canonical reference for the voice agent is `het0814/SD-voice-ai-service` — a complete outbound LiveKit Agents 1.3 pipeline, read line-by-line from source. This is the confirmed pattern for the "Insurance Caller" described in Het's résumé.

**Process topology: 4 independently-launched processes, no single server:**
1. `python src/agent.py` — LiveKit Agents worker (STT→LLM→TTS), voice conversation
2. `python -m src.workers.call_scheduler` — polls Redis priority queue, dispatches SIP calls (1 call per 1.5s, `DISPATCH_INTERVAL = 1.5s`)
3. `python -m src.workers.data_processor` — polls Supabase for `status='completed'` calls, runs post-call extraction (`POLL_INTERVAL = 10.0s`)
4. `uvicorn src.api_server:app --port 8000` — FastAPI control plane (schedule/initiate calls, review queue, specialist CRUD)

Glue: Redis (ephemeral: priority queue, per-call state hash, active-call set, retry backoff) + Supabase/Postgres (durable: specialists, calls, data_updates, audit_log). Processes communicate only through shared state in Redis/Supabase — no direct RPC between processes.

**The voice pipeline (exact wiring, `agent.py:139-160`):**
```python
AgentSession(
    stt=deepgram.STT(model="nova-3-general"),
    llm=openai.LLM(model="gpt-4o-mini"),   # in-call; no temperature set (SDK default)
    tts=elevenlabs.TTS(model="eleven_flash_v2_5", voice_id="cgSgspJ2msm6clMCkdW9"),
    vad=silero.VAD.load(),                  # default params, no custom thresholds
)
```

**Turn detection:** `MultilingualModel` imported but never instantiated — **dead code**. Actual endpointing = VAD-only (Silero default).

**In-call "agent loop":** there is no structured tool-call loop. The model is steered by **system prompt + appended context injection**. A `ConversationManager` has a 7-question state machine and a `GREETING → QUESTIONS → CLARIFICATION → WRAP_UP → ENDED` enum, but **the question index is never advanced at runtime** — `mark_answered()` is never wired to any tool or callback. In practice, the appended instruction block is frozen on "you're on question 1/7" for the entire call. Behavior is driven by the static base system prompt, not the state machine. The state machine is latent code, not live architecture.

**This is a critical finding for Verso:** the simplest prompt-state-machine (rewrite the appended context block to steer the model) is what ships in production, not a sophisticated tool-calling state graph.

### System prompt (verbatim, `agent.py:42-68`)

```
You are an automated directory verification assistant calling on behalf of {clinic_name}. Your job is to verify and update specialist office information in our referral directory.

PERSONALITY:
- Professional, warm, and efficient
- Speak naturally like a friendly office coordinator
- Keep responses concise — this is a phone call, not a chat
- Never use markdown, bullet points, or special formatting in speech

CURRENT TASK:
- You are calling a specialist office to verify their directory information
- Ask about: new patient capacity, accepted insurance plans, scheduling process, required referral documents, wait times, and contact info
- Be conversational — don't read questions like a survey

CONVERSATION FLOW:
- First, greet them and ask how they are
- After they respond, ask if they have about 2 minutes for a quick directory verification
- If they say yes, begin the verification questions one at a time
- If they say no, ask when would be a better time and end politely

IMPORTANT RULES:
- If you reach voicemail, leave a brief message and end the call
- If asked who you are, explain you're an automated system verifying directory info
- If they ask to be removed or refuse, thank them politely and end the call
- If transferred, re-introduce yourself to the new person
- Do NOT discuss patient information — you only handle directory data
- Keep the call under 3 minutes
```

Base prompt is `SYSTEM_INSTRUCTIONS + "\n\nCURRENT CONTEXT:\n" + context` (simple concatenation pattern). This is the production-deployed shape.

### Post-call extraction pipeline (gpt-4o-mini JSON pass — KNOWN, verbatim)

After call completion, a separate worker runs a `gpt-4o-mini` structured extraction on the transcript. Raw HTTP POST, not SDK:

```python
POST https://api.openai.com/v1/chat/completions
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "You are a precise data extraction system. Return only valid JSON."},
    {"role": "user", "content": <EXTRACTION_PROMPT with {transcript}>}
  ],
  "response_format": {"type": "json_object"},
  "temperature": 0.1
}
```

`httpx.AsyncClient(timeout=30.0)`. The extraction prompt asks for `{field_name, value, confidence: 0.0-1.0, source_segment}` for each of 14 predefined field keys. Confidence scoring guide is explicit and verbatim in the prompt (1.0 = explicitly stated; 0.8–0.9 = clearly implied; 0.6–0.7 = indirectly stated; 0.4–0.5 = vague; 0.1–0.3 = inferred from context).

**Three-tier confidence routing (exact predicates, `data_extraction.py`):**
```python
HIGH_CONFIDENCE_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.70
REJECTION_THRESHOLD = 0.40
```

- `confidence >= 0.85 AND "CONFLICT" not in source_segment` → **auto-apply** (write to DB, `reviewed_by="auto"`)
- `confidence < 0.70 OR "CONFLICT" in source_segment` → **human review queue**
- `confidence < 0.40 AND not in review_fields` → **discard** (logged only)
- `[0.70, 0.85) AND clean` → **dead zone: silently dropped** (production bug — the `[0.70, 0.85)` band is neither applied, reviewed, nor logged)

**Conflict detection:** when `existing_data` present, `detect_conflict()` appends `" [CONFLICT: {desc}]"` to `source_segment` AND `field.confidence = max(0.0, field.confidence - 0.1)`. Conflicts always route to human review regardless of confidence.

**Audit trail:** every auto-applied update writes an `audit_log(entity_type, action, actor="system", changes)` row. Human approvals write `action="approve"`. This append-only log is the "governance" primitive.

**Verso lesson (critical):** the two-pass pattern (live agent call → post-call extraction → confidence-gated human review) is a production-deployed governance architecture. Verso should make this pattern a first-class workflow:
- `AgentSession.on_complete()` hook fires a configurable post-processing pipeline
- Post-processing pipeline: `[extractor(model, prompt), confidence_router(thresholds, review_queue)]`
- Built-in human-in-the-loop review queue with approve/reject/correct actions
- Append-only audit log per session, per field mutation

### CollectWise-Agent (Retell AI pattern — confirmed engineer, KNOWN)

`shaan101patel/CollectWise-Agent` (the same confirmed Wedge engineer) is a take-home prototype for a debt-collection voice agent using **Retell AI** instead of LiveKit. This shows the team is fluent in both architectures.

**Retell AI agent config (`retell_agent.json`):**
- `response_engine.type: "retell-llm"`, in-call model: **`gpt-4.1` (full, not mini)**
- `post_call_analysis_model: "gpt-4.1-mini"` — Retell's built-in post-call analysis (no custom extraction prompt)
- `tool_call_strict_mode: true` — forces OpenAI strict-mode JSON-schema tool calls
- `kb_config: {top_k: 3, filter_score: 0.6}` — real config but inert (`knowledge_base_ids: []`)
- `pii_config.mode: "post_call"` — PII redaction deferred to after-call
- `start_speaker: "user"` — agent waits for human to speak first (inbound pattern)

**The dialogue prompt (B.2):** numbered STATE machine hardcoded into the single `general_prompt` string. States: GREETING → CAPTURE ACCOUNT NUMBER → 3A ACCOUNT FOUND / 3B ACCOUNT NOT FOUND → WRAP UP. The LLM follows the states as natural-language instructions, not as code-driven state transitions.

**The custom tool:** `lookup_account` — a Retell custom GET tool calling a Railway-hosted Express endpoint at `https://web-production-7c32.up.railway.app/accounts/{{account_number}}`. `timeout_ms: 120000` (2 minutes, tolerating Railway cold-starts). JSONPath `response_variables` map response fields into Retell template variables.

**Retell's tool execution model:** the LLM signals a tool call → Retell executes the GET/POST to the configured URL → response variables injected back into LLM context. The framework handles the tool-call lifecycle; the developer only writes the endpoint and declares the response mapping.

**Verso lesson:** Retell's config-file approach (agent config is a JSON schema + a prompt string + tool declarations) is the right DX target for simple stateless agents. Verso should support this pattern: declare agent behavior as a config artifact, not as code. The `tool_call_strict_mode: true` convention should be Verso's default.

### NavisCopilot AI dialogue contract (KNOWN — voice copilot for human agents)

`shaan101patel/NavisCopilot_NP_1.0` (the same engineer) is a browser-tab audio copilot: transcribes a live customer call using Groq Whisper, retrieves grounded context via pgvector, and emits tiered guidance to a human agent in real-time.

**Three response verbosity levels (exact API contract):**
- `instant` → one terse sentence, no suggestions, `confidence ≈ (default)`
- `quick` → 2–3 sentence grounded answer + `suggestions: string[]` (next-action prompts), `confidence ≈ 0.85`
- `immediate` → structured multi-section markdown brief (numbered: policy/verification/condition/exceptions/next-steps with `**bold**` headers + "RECOMMENDED APPROACH:" line) + longer `suggestions[]`, `confidence ≈ 0.92`

**RAG constants (KNOWN, verbatim from source):**
- Embedding: hash-based mock in public repo (real embedder is a server-side Supabase edge function, black box)
- Vector dimension: 384
- HNSW cosine ops (`vector_cosine_ops`)
- Retrieval threshold: **0.7** (minimum cosine similarity)
- Top-K: **10** chunks per retrieval
- Chunk size: **220 tokens**, overlap: **60 tokens**
- Chunking strategy: boundary-aware (`\n\n` → `[.!?]+[\s\n]+` → whitespace → hard-cut with `snapEndBackward`)
- STT: Groq `whisper-large-v3-turbo`, temp 0, `verbose_json` with segment timestamps, skip < 200 KB, 25 MB cap, **3× retry at 500ms intervals**
- Audio capture: 16 kHz mono 128 kbps, **`CHUNK_DURATION = 4000 ms (4 s)`** WebM/Opus chunks

**Verso lesson:** the tiered verbosity contract (`instant` / `quick` / `immediate`) is a clean API pattern for agents that need to tune response depth to context. Verso should support a `verbosity_level` parameter on agent responses — different downstream consumers (voice interface vs chat UI vs API) need different response depths from the same underlying reasoning.

### Memory layer — Moorcheh + Memanto (KNOWN, INFERRED relevance to Wedge)

Het Patel (confirmed part-time Wedge engineer, full-time Moorcheh) co-authored and implemented Memanto — a universal memory layer for AI agents. This is the strongest available signal for Wedge's agent persistence architecture.

**Memanto design (KNOWN, from source):**
- Rejects hybrid semantic-graph memory (LLM-mediated entity extraction + graph schema maintenance + multi-query retrieval). Replaces with: (a) 13 typed memory categories, (b) automated conflict resolution, (c) temporal versioning. Benchmarks: LongMemEval 89.8%, LoCoMo 87.1% (claimed SOTA, single retrieval query).
- Backend: Moorcheh text namespaces (server-side embeddings, ITS scoring, sub-90ms, zero ingestion delay).
- Namespace scoping: `memanto_{scope_type}_{scope_id}` — deterministic string. `scope_type ∈ ["user", "workspace", "agent", "session", "project", "task"]`. Multi-scope recall = one Moorcheh `/search` call with `namespaces=[user_X, workspace_Y, session_Z]`.
- Memory record: `{id, type (1 of 13), title, content, scope, confidence (default 0.8), status, provenance, superseded_by, created_at, expires_at, ttl_seconds}`.
- Stored in Moorcheh as: `text = "[{TYPE}] {title}\n\n{content}\n\nTags: ..."` + flat metadata dict (enables `#memory_type:fact` filter syntax).

**13 memory types (verbatim):** `fact`, `preference`, `goal`, `decision`, `artifact`, `learning`, `event`, `instruction`, `relationship`, `context`, `observation`, `commitment`, `error`.

**Confidence decay engine (exact constants):**
- `contradiction_detected` → `max(0.1, confidence * 0.3)`
- `superseded` → `0.0`
- base = `confidence × provenance_weight` where: `explicit_statement:1.0, validated:0.95, corrected:0.9, observed:0.85, imported:0.8, inferred:0.7`
- `+ validation_boost = min(0.15, validation_count × 0.03)`
- age penalty (preference/observation types only): `>90d → -0.2`, `>30d → -0.1`, else `0`

**Trust score buckets:** `≥0.8 → high "Safe to use"`, `≥0.5 → medium "Use with caution"`, else `low "Verify before using"`

**Type classifier:** regex rule-based + rapidfuzz keyword fallback — **NOT LLM-based**. Only the `/answer` (RAG) and `daily_summary` paths call an LLM (`claude-sonnet-4-6` via Bedrock). Write path adds essentially zero LLM overhead.

**MCP integration (KNOWN, `integrations/mcp/`):** FastMCP server named `memanto`, **11 tools**: `remember`, `batch_remember`, `recall`, `recall_recent`, `recall_as_of` (time-travel to any past date), `recall_changed_since` (delta since timestamp), `answer` (RAG over memory), `create_agent`, `list_agents`, `get_agent`, `delete_agent`.

**Session defaults:** `DEFAULT_TTL_SECONDS = 3600`, `SESSION_DEFAULT_DURATION_HOURS = 6`, `SESSION_EXTEND_THRESHOLD_MINUTES = 30`. Consolidation: a `daily_summary_service` rolls session memories into a daily summary card.

**Verso lesson (memory):** typed memory categories with temporal versioning and confidence decay are the right primitive for production agent memory — not a raw vector store and not a knowledge graph. The 13-type taxonomy maps onto most agent domains. Verso should provide a first-class `MemoryProvider` interface (pluggable backend: Memanto/Moorcheh, Mem0, pgvector, etc.) with standard `remember(type, content)` and `recall(query, types, scope)` methods that decouple agents from the specific memory backend.

**The `recall_as_of(date)` tool is especially valuable for compliance-heavy domains (healthcare, finance):** it provides an audit-grade record of what the agent knew at the time of a specific decision. Verso should support this as a standard memory operation.

### Call-session state machine (KNOWN — NavisCopilot, transferable to Insurance Caller)

Per-call isolation enforced in the app via a `CallStateContext` React provider keyed by `callId`. Each call gets an isolated `{notes, documentNotes, aiChatMessages, transcript, quickSuggestion}` slice. This solved a real production bug ("Multiple call tabs were sharing the same state").

Transfer is implemented as **new-row-clone + old-row-close** (not in-place owner reassignment) — gives an immutable per-agent call record, exactly what a HIPAA audit trail requires.

Hold state is shoehorned into the `ai_suggestions` jsonb column — acknowledged technical debt (`// Note: We need to extend the calls table to support 'on-hold' status`).

UI degrades gracefully if backend write fails: `catch` → `console.warn("⚠️ Using fallback hold operation")` → local-only state change. Call does not drop on DB write failure.

**Verso lesson:** per-session isolation with graceful degradation on storage failure is a production requirement for voice agents. Verso's session management should enforce this by default — isolated state slices per session, fallback to local-only state on storage failure.

---

## Cross-cutting → Verso Implications

### 1. Agent loop: ReAct-style single-agent with tool-use loop is the production default

All three systems use single-agent, tool-use loops. No multi-agent orchestration in Stardrift (confirmed absence of LangGraph/CrewAI). Wedge's voice agent has no tool-call loop at all — state is steered by system prompt injection. Gordian has no LLM loop. The common pattern: **one agent, one loop, tools are thin HTTP wrappers**.

Verso thesis confirmed: keep the agent loop simple. The escape hatch for multi-agent should exist but the default must be simple.

### 2. Streaming: decoupled LLM worker + Redis stream buffer is the production pattern for resumable streaming

Stardrift's 4-step streaming evolution is the authoritative case study. Key insight: the SSE connection to the client and the LLM computation must be decoupled at the infrastructure level (Modal worker + Redis Streams). The web container can crash and the LLM work continues. On reconnect, replay from last delivered cursor.

Verso must provide this as a built-in transport option — not something each team reimplements. Minimal viable: `verso.chat(agent, message, stream=True)` returns a resumable `StreamHandle` with a `resume_token` that works across client reconnects.

### 3. Post-call / post-turn extraction: two-pass pattern is the right architecture for structured output from open-ended conversations

Both Stardrift (feedback capture tool) and Wedge (gpt-4o-mini JSON extraction at temperature 0.1) use a separate extraction pass after the conversation. The live turn model is optimized for dialogue; the extraction model is optimized for structured output from the transcript. These are different concerns with different model requirements.

Verso: `agent.on_complete(extractor)` hook that fires a configurable extraction pipeline with a separate model, prompt, and output schema. Default: `extractor(model="gpt-4o-mini", temperature=0.1)`.

### 4. Confidence-gated human-in-the-loop is the production governance pattern

Wedge's three-tier gate (0.85 auto-apply / 0.70 human review / 0.40 discard) is a concrete, running example of how production agents handle uncertainty. Key features: every field carries a `source_segment` (the verbatim evidence for the extraction), conflict detection haircut (-0.1 on confidence), and an append-only audit log.

Verso should provide a `ConfidenceRouter(high_threshold, review_threshold, discard_threshold)` primitive that attaches to any extraction pipeline and routes results to the appropriate handler (auto-apply / review queue / discard). The review queue should have a standard approve/reject/correct API.

Note the dead zone bug at [0.70, 0.85)-clean in Wedge's implementation: fields in that band are silently dropped. Verso's implementation should close this gap — either extend auto-apply to [0.70, 1.0)-clean or extend review to [0.40, 0.85).

### 5. Memory: typed semantic memory with temporal versioning beats raw vector stores for agent persistence

Memanto's thesis (and benchmark results) show that 13 typed categories + confidence decay + temporal versioning on a semantic search backend outperforms hybrid graph approaches at 1/10th the complexity.

Verso's memory API should be typed: `memory.remember(type="fact"|"preference"|..., content=..., confidence=0.8)`. Default backend should be an embeddable semantic store (not a raw vector DB). The `recall_as_of(date)` operation is critical for compliance domains and should be first-class.

Type classification should be deterministic/regex-based by default (zero LLM cost), with an optional LLM-based classifier for ambiguous cases.

### 6. Long-running tools: polling with exponential backoff must be built into the framework

Gordian's seat-search pattern (100s hard timeout, 1s interval) and basket-revalidation pattern (60s, 2s interval) show that production tool calls regularly take 10–100 seconds against slow external APIs. The current standard (await a tool call, block until done) is the wrong default.

Verso: `@verso.tool(polling=True, timeout_ms=100000, interval_ms=1000)` decorator that converts a tool into a polling tool with a standard `{status: "in_progress"|"success"|"failed"}` response pattern. The agent loop re-polls automatically at the configured interval without blocking the main conversation loop.

### 7. Tiered verbosity is the right API for multi-surface agents

NavisCopilot's `instant / quick / immediate` response levels show that the same underlying reasoning needs to produce different output shapes for different consuming surfaces (voice interface needs one sentence; API consumer needs structured markdown; dashboard UI needs suggestions + confidence). This is a real production requirement that should not be ad-hoc per deployment.

Verso: `agent.respond(verbosity="instant"|"quick"|"detailed")` parameter on the response method, where the agent compresses/expands its output to the target verbosity level. The framework handles the response formatting; the agent logic stays the same.

### 8. Auth: scoped session tokens are the right primitive for multi-step agentic workflows

Gordian's three-token lifecycle (tripCreationToken → tripAccessToken → searchToken) shows that different phases of an agentic workflow should have different privilege scopes. Server-to-server calls use HTTP Basic (API key), browser-side calls use scoped Bearer tokens that expire with the session.

Verso: define token scopes at the agent-step level, not just at the API level. A planning step should not have the same privileges as an execution step.

### 9. SDK/DX: config-file agent declarations beat imperative code for simple stateless agents

Retell's `retell_agent.json` config approach (agent name, model, prompt, tool declarations, voice) is the right DX for agents that don't need complex control flow. The whole agent is a config artifact, not a Python/TypeScript program. This makes it easy to version, diff, and test.

Verso should support both paths: a config-file path for simple agents (`verso.yaml` or `agent.json`) and a programmatic path for complex agents with custom control flow. The config-file path should be the default for getting started.

### 10. Observability: telemetry at decision points beats post-hoc logging

Gordian's ML training data collection via the `Seat Confirmed` event with normalized ratio metrics is the production example of deliberate observability for continuous improvement. The SDK is designed to generate training data, not just track events.

Verso: every agent decision point should emit a normalized telemetry event: `{turn_id, tool_called, alternatives_available, chosen_option, outcome}`. This is the foundation for offline evaluation and continuous improvement, and it should be built into the framework by default, not added as an afterthought.

---

## Summary table

| System | Loop shape | Models | Tool count | Memory | Stream | Governance |
|---|---|---|---|---|---|---|
| Stardrift | Single-agent ReAct, maxSteps 10–20 | Haiku (classifier) + Claude (planner) — INFERRED | ~10 domain tools | Trip-scoped, Postgres | SSE + Redis Streams resumption, modal.spawn worker | Feedback capture → evals |
| Gordian | No LLM loop; ML ranking + REST polling | LightGBM/XGBoost (tabular) + ONNX serving in Go | N/A (REST API surface) | No agent memory; ML feature store | REST polling (100s/1s) | N/A |
| Wedge | No structured tool loop; system-prompt injection + post-call extraction | gpt-4o-mini (voice + extraction, temp 0.1); Groq Whisper STT; ElevenLabs TTS; gpt-4.1 (Retell) | 0 in-call tools (LiveKit); 2 (Retell: end_call + lookup_account) | Memanto/Moorcheh — 13 typed categories, confidence decay, MCP-exposed | LiveKit Agents WebRTC (not SSE) | Three-tier confidence gate + append-only audit log |
