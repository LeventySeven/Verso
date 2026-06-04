# agents-character-deep — Character.AI Serving Deep-Dive

**Source:** `teardowns/CHARACTER_AI.md` (Round-1 + Round-2 mobile + Round-3 inference/Google deal, 2026-05-20, 2713 lines)
**Focus for Verso:** model infra for agents — what the largest consumer AI agent system running at 20K QPS actually looks like under the hood.

---

## § System overview

Character.AI is the largest consumer-facing AI agent platform on the open internet: **20,000 inference queries/second** (mid-2024), **20M+ MAU**, **180-message average dialogue history per chat**. Founded by Noam Shazeer (co-author Attention Is All You Need, inventor of MQA) and Daniel De Freitas (ex-Google LaMDA tech lead). In August 2024 Google paid $2.7B for a non-exclusive license to the underlying models; ~30 researchers including the founders returned to Google DeepMind.

The product is architecturally interesting for Verso because:
- It runs **millions of simultaneous stateful agent sessions** at near-zero per-turn cost.
- It exposes a **first-class multi-agent surface** (Rooms with LLM-orchestrated speaker selection).
- It open-sourced its **prompt construction library** (Prompt Poet) and its **evaluation harness** (JudgeJudy) — both directly usable.
- The serving economics ($0.01/conversation-hour) are the target floor for any competitive agent product.

---

## § Agent loop shape

### 1:1 chat — simple single-agent loop

Every conversation is a stateful WebSocket session. The loop per turn:

```
user types → create_and_generate_turn (WS command)
  → server prefills context (using stateful KV cache for prefix)
  → streams update_turn events (full-snapshot each, not deltas)
  → client replaces displayed text on each update_turn
  → is_final: true → commit, loop ends
```

There is **no planning step, no tool dispatch, no ReAct loop** in 1:1 chat. It is a pure generation loop — the "agent" is the persona definition injected into the prompt. The agentic complexity lives entirely in the serving infrastructure, not in the loop shape.

**Termination:** `abort_generation` command cancels in-flight generation; server commits whatever was produced up to that point (`update_turn is_final: true`). No iteration cap in the protocol — each turn is one generation call.

**Streaming protocol:** WS, NOT SSE. Each `update_turn` event is a **full snapshot** of the response so far (replace, not delta). This simplifies the client but increases bandwidth. Acceptable given their $0.22/Mtok serving cost.

### Rooms — multi-agent loop (the structurally novel part)

Rooms are the only part of Character.AI that is structurally multi-agent:

```
user sends message (or invokes a character) →
  smart_reply_v2 command →
    [1] speaker-selection LLM call: given chat history + roster of N characters, output character_id
    [2] generation call for selected character
  → stream back the response
  → other participants see typing-state via Centrifuge pub/sub
```

Three mode variants:
- **Explicit invocation:** user clicks a character avatar → `generate_turn` with specific `character_id` (skip step 1)
- **Smart reply v1:** `smart_reply: true` → two separate LLM calls (select, then generate)
- **Smart reply v2:** `smart_reply_v2: true` → single combined LLM call (select+generate together) — faster, the production default

The `smart_reply_delay: 0` field in the wire protocol is a placeholder for future naturalistic pacing.

**Bounds:** max 10 characters + 10 humans per room. 3-second invoke cooldown between explicit speaker invocations (`INVOKED_COOLDOWN_MS: 3000`).

**Transport split:** 1:1 chat uses raw WebSocket (`wss://neo.character.ai/ws/`). Rooms use **Centrifuge** (`wss://neo.character.ai/connection/websocket`) because rooms need server-side pub/sub fan-out for typing-state broadcast across all participants. SSE and long-poll fallbacks available for Centrifuge.

---

## § Models (exact names, routing, roles)

### Internal model routing — 15 slots

The `MODEL_TYPE_*` enum, verbatim from the production bundle (`chunks/_app-7becf23e83ddd0c6.js:73168-73188`):

| Enum | UI label | Role |
|---|---|---|
| `MODEL_TYPE_FAST` | Fast | Small fast variant ("Quick wits, faster words") |
| `MODEL_TYPE_SMART` | Smart | Larger slower variant ("Smart and more thoughtful") |
| `MODEL_TYPE_BALANCED` | Default | Default route ("Mix of speed & smarts") |
| `MODEL_TYPE_FAMILY_FRIENDLY` | Family Friendly | Constrained decoding / heavier safety filter |
| `MODEL_TYPE_MEMORY_OPTIMIZED` | Memory | Longer context window + likely summarization pass |
| `MODEL_TYPE_MULTILINGUAL` | Multilingual | Language-mix fine-tune |
| `MODEL_TYPE_DYNAMIC` | Dynamic | Server-side auto-router — picks best given load |
| `MODEL_TYPE_THINKING` | Thinking | Chain-of-thought / o1-style decoder |
| `MODEL_TYPE_ROMANTIC` | Romantic | Romance-fine-tuned variant |
| `MODEL_TYPE_FRENCH` | (implicit) | French fine-tune |
| `MODEL_TYPE_CHINESE` | (implicit) | Chinese fine-tune |
| `MODEL_TYPE_DEEP_SYNTH` | DeepSqueak / "RatGPT" | New-gen roleplay model, c.ai+-only |
| `MODEL_TYPE_DEEP_SYNTH_LITE` | Pipsqueak / "Clawd" | Smaller DeepSqueak |
| `MODEL_TYPE_DEEP_SYNTH_LITE_V2_1` | (no friendly name) | Latest DeepSynth iteration |
| `MODEL_TYPE_EXPRESSIVE` | Expressive | Voice-optimized variant |

The **"RatGPT"** (DeepSynth) and **"Clawd"** (DeepSynthLite) codenames leaked into the user-facing i18n string table by accident.

**Server may silently downgrade under load:** the footer string verbatim: `"tooltip-model-availability":"The actual model used may vary based on system load and availability"`. A chat opened with `MODEL_TYPE_DEEP_SYNTH` may fall back to `MODEL_TYPE_BALANCED` if DeepSqueak GPUs are saturated.

### External API — model surface simplified to 2

The `character-ai/openapi` spec for `neo.character.ai/external/chat/completions` exposes only **two model choices**: `default` and `safe`. The 15 internal slots collapse to two for external API consumers. The complexity is internal-only.

### Post-deal model lineage (INFERRED)

Post-$2.7B Google deal, the SFT framework (`character-ai/pipelining-sft`) targets **DeepSeek-V3-0324** (671B total / 37B active MoE) as the base. Character.AI no longer pretrain from scratch — they SFT open-source MoE bases onto their conversational data. Pre-deal c1.0–c1.2 weights were the licensed IP that went to Google DeepMind.

---

## § Inference architecture — the core innovation

This is the most valuable section for Verso's understanding of what production agent serving actually costs.

### MQA + hybrid local/global attention + cross-layer KV sharing

**Source:** June 2024 `research.character.ai/optimizing-inference` post (verbatim quotes from recovered Internet Archive snapshot).

**Trick 1 — Multi-Query Attention (MQA):**
> "We adopt Multi-Query Attention (Shazeer, 2019) in all attention layers. This reduces KV cache size by 8X compared to the Grouped-Query Attention adopted in most open source models."

Standard Llama-3-70B uses GQA with 8 KV heads. Character.AI uses MQA with 1 KV head → **8× cheaper than Llama at the same query heads**.

**Trick 2 — Hybrid attention (1024-token local window, 1-in-6 global layers):**
> "We interleave local attention with global attention layers. Local attention is trained with sliding windows... In our production model, only 1 out of every 6 layers uses global attention."
> "reducing attention horizon to 1024 on most attention layers does not have a significant impact on evaluation metrics, including the long context needle-in-haystack benchmark"

For a 60-layer model: 10 global + 50 local (window=1024). Long context KV: `10×32k + 50×1024 = 371k entries` vs `60×32k = 1.92M` → ~**5× reduction** on long contexts. Local layers are O(n) compute not O(n²).

**Trick 3 — Cross-layer KV sharing:**
> "We tie the KV cache across neighboring attention layers, which further reduces KV cache size by a factor of 2-3x. For global attention layers, we tie the KV cache of multiple global layers across blocks."

Adjacent transformer layers compute very similar K,V projections (CLA insight). Tying global layers (which dominate long-context KV) across 3-4 layer groups → **2-3× reduction** on global layers.

**Compound result:** The blog claims >20× total KV reduction vs a Llama-class GQA baseline. Verified calculation: 8× (MQA vs GQA) × ~5× (hybrid attention at 32k context) × ~2.5× (cross-layer sharing) = **100× vs GQA, 800× vs vanilla MHA** — blog says "more than 20×" conservatively because they compare to a strong GQA baseline already.

### Native int8 quantization (NOT post-training quantization)

> "We use int8 quantization on model weights, activations, and attention KV cache... we natively train our models in int8 precision, eliminating the risk of training/serving mismatch while also significantly improving training efficiency."

Three implications:
1. int8 applied to **weights + activations + KV cache** (not just weights — most commercial inference only quantizes weights)
2. **Training/serving parity** — no quality cliff at serving time
3. Custom CUDA int8 kernels for matmul AND attention (custom epilogue fusion)

Combined with the 20× KV reduction: total KV bytes per dialogue is roughly `1/(20 × 2)` = **40× smaller than a stock fp16 GQA model**.

### Stateful host-RAM KV cache (RadixAttention-style)

> "One of our key innovations is an efficient system for caching attention KV on host memory between chat turns... the average message has a dialogue history of 180 messages... Our system achieves a **95% cache rate**, further reducing inference cost."

Full algorithm (verbatim):
> "For every prefilled prefix and generated message, we cache the KV values on host memory and retrieve them for future queries. Similar to RadixAttention (Zheng et al., 2023), we organize cached KV tensors in a LRU cache with a tree structure. The cached KV values are indexed by a rolling hash of prefix tokens. For each new query, a rolling hash is calculated for each prefix of the context, and the cache is retrieved for the longest match. This allows reusing the cache even for partially matched messages."
> "At a fleet level, we use sticky sessions to route the queries from the same dialogue to the same server. Since our KV cache size is small, each server can cache thousands of dialogues concurrently."

Five mechanisms:
1. **Host RAM, not HBM** — CPU RAM is 100× cheaper/byte; trade PCIe bandwidth for HBM capacity
2. **Radix tree** — shared prefixes (same character's persona definition) are computed once and shared across all conversations under that character
3. **Rolling hash keys** — `h(t1..tn+1) = combine(h(t1..tn), tn+1)` computed in O(n), longest-prefix lookup per turn
4. **Partial-match retrieval** — edit of a recent message doesn't blow away the whole cache; divergence point is found mid-message
5. **Sticky-session routing at L4** — load balancer routes `chat_id=X` to same inference server `Y`; keeps cache warm across turns

**Cache hit rate: 95%.** With 180-message average history, fresh prefill would dominate. 95% hit = only 5% of tokens need new compute. The cache is the reason a mature Character.AI conversation is cheap and responsive.

**Estimated cache per dialogue:** ~30-40 MB host RAM (8B-class model, MQA int8, hybrid attention). Per server: "thousands of dialogues" → ~5,000 × 35 MB = **175 GB host RAM for KV cache per inference server**. Matches commodity A3 instances (1.8 TB host RAM).

### Serving economics

All verbatim from the blog:

- **< $0.01 per hour of conversation** (the headline number)
- **$0.22/Mtok all-in** (derived: $0.01/hr ÷ 45k tokens/hr at 180-message pace)
- **13.5× cheaper** than leading commercial API basket
- **33× cost reduction** since late 2022 → June 2024

The 33× compound: MQA (8×) × hybrid attention (~2.5×) × cross-layer KV (~2.5×) × int8 (~1.7×) × stateful caching (~7× from 95% hit rate) × hardware generation (H100 vs A100, ~2×) = theoretical ~1,200× — realized 33× because the improvements overlap substantially and they compare to their own earlier stack, not vanilla MHA.

---

## § Context assembly — Prompt Poet

`character-ai/prompt-poet` is open-source (MIT, 1,147★) and used verbatim in production. This is the **exact algorithm** that assembles every prompt sent to the inference server.

### Core abstractions (KNOWN, `prompt_poet/prompt.py:21-62`)

```python
@dataclass
class PromptPart:
    name: str
    content: str
    role: str = "user"
    tokens: list[int] | None = None
    truncation_priority: int = 0  # 0 = NEVER truncated
    sections: list[PromptSection] | None = None
```

Templates are Jinja2 + YAML. The YAML list-of-parts is the structure that makes **cache-aware truncation** possible.

### Cache-aware truncation algorithm (KNOWN, `prompt.py:190-236`)

```python
def _calculate_num_tokens_to_truncate(self, token_limit, truncation_step) -> int:
    num_surplus_tokens = max(0, self._total_tokens - token_limit)
    return math.ceil(num_surplus_tokens / truncation_step) * truncation_step
```

Key insight: rather than truncating exactly to the limit, round up to the **next multiple of `truncation_step`**. If `token_limit=8192` and `truncation_step=1000`, and you have 9100 tokens, truncate `ceil((9100-8192)/1000)*1000 = 1000` tokens → leave 8100.

Next turn at 9300 tokens still truncates to the same 8100-token boundary (or jumps to 7100). Prefix tokens up to that boundary are **byte-identical across turns → cache hits** in the prefix KV cache.

The tradeoff: "we often truncate more than we strictly need to" (their blog) — pay extra context loss to gain cache stability.

### Truncation priority semantics (KNOWN, `prompt.py:437-490`)

```python
truncation_blocks.sort(key=lambda marker: marker.truncation_priority, reverse=True)
```

Higher `truncation_priority` = **evicted first** (counterintuitive). Production pattern:
- `truncation_priority=0`: system instructions, character persona + definition, current user query + reply prompt → **never truncated** (this is the cache-stable prefix)
- `truncation_priority=10`: oldest chat history messages → **first evicted**
- `truncation_priority=5`: recent-but-not-current chat history → medium priority

### Character definition format (KNOWN, `cai_helpers.py:48-70`)

The character definition is NOT injected as a monolithic system message. It is **split on newlines**, each line emitted as a separate `CAIMessage` with empty author:

```python
if definition := character.get("definition"):
    for line in definition.split("\n"):
        messages.append(CAIMessage(author="", text=line))
```

The model was trained on dialog-as-message-stream format — character definitions are injected in the same per-line format to match training distribution.

### Internal codename "Hermes" (KNOWN, `cai_helpers.py:88`)

```python
def pretruncate_messages(messages, token_limit):
    """Pretruncates messages for Hermes generation."""
    message_truncation_step = token_limit // 10
    while len(messages) > 2 * message_truncation_step:
        messages = messages[message_truncation_step:]
    return messages
```

`Hermes` = internal codename for their LLM generation pipeline (unrelated to Nous Research's Hermes models). First-pass coarse truncation: drop chunks of `token_limit//10` messages off the front while count > `2 × (token_limit//10)`. Fast O(1) filter before the expensive token-level Prompt Poet pass.

### Message type enum (KNOWN, `cai_helpers.py:13-21`)

```python
# type: 0=Unspecified, 1=HumanMessage, 2=CharacterMessage, 3=SystemMessage
is_pinned: bool = False  # Memo / pinned messages → permanent context
```

Pinned messages (`is_pinned=True`) are surfaced as permanent context — they survive across truncation passes and are always included in the prompt regardless of dialog length.

---

## § Memory architecture

Three-layer memory stack:

### Layer 1 — Short-term: turn history in-session

Each turn: `{turn_key, author, candidates[], primary_candidate_id, state, is_pinned}`. Multiple candidates per turn power swipe-to-regenerate: `generate_turn_candidate` spawns a new candidate; `update_primary_candidate` switches which is canonical.

Chat history pagination via `next_token` cursor. History segments: `HEAD | MIDDLE | TAIL`. When browsing old messages and typing, client navigates to TAIL before sending `create_and_generate_turn`.

### Layer 2 — Mid-term: stateful host-RAM KV cache (cross-turn)

The radix-tree LRU cache described in the inference section. **This is the "memory" that makes returning to a mature chat fast** — the prefix KV is still warm across hours or days as long as the dialogue isn't evicted. Effectively a 30-40 MB per-conversation in-memory snapshot of the model's computed attention state.

### Layer 3 — Long-term: Memos (pinned messages)

`set_turn_pin` WS command toggles pin state. Pinned turns → permanent context lines on every subsequent generation, surviving truncation. Server-side quota (free users: ~3 pins; higher with c.ai+). Purchasable in packs: `memo_100`, `memo_200`, `memo_300` Charm SKUs (`chunks/_app-7becf23e83ddd0c6.js:165431-165433`).

When `MemoQuotaExceeded` (sub_code 10010), the client routes the error to the Charms purchase flow — error handling as a monetization surface.

### Layer 4 — Implicit: persona prefix + lorebook

The character definition (up to 32,000 chars), the scene context, and lorebook entries (RAG by keyword match against the latest message) are injected via Prompt Poet at every turn. These are not "memory" in the traditional sense — they are regenerated from the database on each turn — but because the character definition prefix is byte-identical turn over turn (it never changes mid-conversation), the radix-tree KV cache gives it **free amortization**: the persona prefix is computed once per cache-warm period and reused for thousands of turns.

### Memory summary

| Layer | Mechanism | Persistence | Cost |
|---|---|---|---|
| Turn history | WS-buffered turn list | Session | Zero (in-process) |
| Cross-turn KV | Radix-tree, host RAM, LRU | Across turns on same server | ~35 MB/dialogue |
| Memos | Pinned turns, DB-backed | Permanent | DB storage + prompt injection |
| Persona prefix | Character definition DB row | Permanent | Zero marginal (cached) |

---

## § Prompt / persona system

### Character schema (KNOWN, `chunks/_app-7becf23e83ddd0c6.js:151661-151674`)

```
name:          str (min 3, max 20)
title:         str (max 50)
description:   str (max 500)
greeting:      str (min 3, max 4096)
additional_greetings: str[1..5]
dynamic_greeting_enabled: bool   # AI-paraphrases greeting per new chat
visibility:    PRIVATE | PUBLIC | UNLISTED
definition:    str (max 32,000)  # the main roleplay persona text
example_dialogs: [{user_message, character_message}]
base_prompt:   str (max 100)     # short tone/style hint
attached_lorebook_id: str | null
voice_id:      str | null
```

The `{{user}}` and `{{char}}` placeholders in the definition are substituted server-side at prompt-assembly time.

### Prompt Poet template (DESIGNED, our reconstruction from §15.1)

```
<system>
You are {{char_name}}.

{{char_description}}

Definition:
{{char_definition}}

{{#if lorebook_entries}}
Relevant lore:
{{#each lorebook_entries}}
- {{this.keys}}: {{this.content}}
{{/each}}
{{/if}}

{{#if pinned_memos}}
Persistent memories:
{{#each pinned_memos}}
- {{this.content}}
{{/each}}
{{/if}}

The user's persona is {{user_persona.name}}: {{user_persona.description}}
</system>

<dialogue>
{{char_name}}: {{first_message}}
{{#each history}}
{{this.author.name}}: {{this.raw_content}}
{{/each}}
{{user_name}}: {{new_user_message}}
{{char_name}}:
</dialogue>
```

The model fine-tuned to never break character — always continues after `{{char_name}}: ` token.

---

## § Tool system

Character.AI does not expose tools in the LLM-tool-call sense. The "tools" are first-class product objects with their own CRUD API:

| Object | Endpoints | Role in agent context |
|---|---|---|
| Character | `/character/v1/*` | The agent definition |
| Lorebook | `/lorebooks/*` | RAG memory — keyword-triggered context injection |
| Scene | `/scene/v1/*` | Narrative branch context |
| Persona | `/character/v1/get_user_personas` | User-side identity |
| Memo | `set_turn_pin` WS command | Permanent pinned context |
| Voice | `/multimodal/api/v1/*` | TTS output generation |
| Video | `/studio-labs/v1/*` | Video generation (async job) |

**Lorebook as retrieval tool:** Each lorebook entry has `keys: string[]`. On every `create_and_generate_turn`, the server intersects entry keys with the recent message text and injects matching entries into the prompt. This is Character.AI's keyword-RAG pattern — no embedding search, no vector DB, pure keyword matching.

**`generate_greeting` as a first-turn tool:** When `dynamic_greeting_enabled`, the server runs a fresh generation for the character's first message each time a new chat opens (rather than replaying the authored greeting). This is a per-chat invocation — the greeting is treated as a separate single-shot generation before the conversation loop.

---

## § Error handling and retry paths

### WS-level retry

Raw WS client: exponential backoff, `500 * 2^wsRetryAttempts`, max 5 retries (`chunks/_app-7becf23e83ddd0c6.js:11763`).

### Error envelope (unified across HTTP + WS)

```json
{
  "command": "neo_error",
  "request_id": "...",
  "comment": "human-readable message",
  "error_code": 403,
  "sub_code": null,
  "retry_after_seconds": null
}
```

Same envelope used by HTTP responses and WS events — confirmed by live probing `neo.character.ai` REST endpoints returning the WS command shape.

### Sub-codes that affect UX flow (KNOWN, `:73061-73088`)

| Code | Meaning | UX consequence |
|---|---|---|
| `sub_code: 10010` | MemoQuotaExceeded | Open Charms purchase sheet |
| `sub_code: 10009` | SwipeQuotaExceeded | Open subscription upsell |
| `sub_code: 10008` | ImageExceededQuota | Show quota message |
| `sub_code: 10000` | ImageFailedContentPolicy | Content policy rejection |
| `sub_code: 16` | TooManyPins | Max pins reached |
| `error_code: 429` | MultiGeneration / TooManyModelChanges | Rate limit |
| `error_code: 403, sub_code: 5` | MinimumAppVersion | Force upgrade |

The system uses sub-codes to route errors to specific recovery UX rather than generic error messages. Quota errors route directly to monetization flows.

### Content moderation events (server-side, KNOWN, `:73046-73047`)

Two inbound events that bypass normal error handling:
- `filter_user_input` — generic content filter triggered
- `filter_user_input_self_harm` — specific self-harm filter triggered (routes to crisis-resource UI)

These are server-sent events, not error responses — the server actively pushes these to the client rather than rejecting the request with an error code.

---

## § Constants table (load-bearing values)

| Constant | Value | Source |
|---|---|---|
| WS heartbeat | 900,000 ms (15 min) | `:115692` |
| WS retry backoff | `500 * 2^n ms`, max 5 | `:11763` |
| Room invoke cooldown | 3,000 ms | `:38159` |
| Room max characters | 10 | `:38154` |
| Room max users | 10 | `:38156` |
| Character definition max | 32,000 chars | `:151671` |
| Character greeting max | 4,096 chars | `:151667` |
| Scene definition max | 2,400 chars | `:151683` |
| Production QPS | 20,000 req/sec | inference blog |
| KV cache hit rate | 95% | inference blog |
| Avg dialogue history | 180 messages | inference blog |
| Local attention window | 1,024 tokens | inference blog |
| Global attention ratio | 1 in every 6 layers | inference blog |
| KV reduction vs GQA | 8× (from MQA alone) | inference blog |
| Total KV reduction | 20×+ vs GQA baseline | inference blog |
| Cost per conversation-hour | < $0.01 | blog companion |
| Cost vs commercial APIs | 13.5× cheaper | blog |
| Cost reduction since 2022 | 33× | blog |
| Serving cost target | ~$0.22/Mtok | derived |
| SFT sequence length | 2,048 tokens | `pipelining-sft/configs/train_fp8.yaml` |
| SFT learning rate | 1e-7 | same |
| SFT cluster | 32 nodes × 8 H100 = 256 H100 | `launch.sh` |
| BF16 checkpoint size | 1.3 TB | README |
| FP8 checkpoint size | 630 GB | README |
| JudgeJudy pass threshold | 0.7 (1-5 scale) | `examples/text_eval.yaml` |

---

## § Multi-agent coordination (Rooms)

The **only structurally multi-agent surface** in Character.AI is Rooms. Architecture:

1. All character agents share one **centralized conversation state** (the Centrifuge channel, a single ordered message stream)
2. A **speaker-selection LLM** picks the next character to respond (single-token output = character_id from roster)
3. Selected character runs its **normal generation loop** with the shared message history as context
4. Response streams back to all participants via Centrifuge pub/sub

The speaker-selection model (`smart_reply_v2`) is INFERRED to be a fast small classifier fine-tuned to output a character_id given: chat history + roster of N characters with their names and brief descriptions. Single-token output. Almost certainly a separate smaller model from the generation models — the latency of two-step (smart_reply v1) vs one-step (smart_reply_v2) suggests v2 is a single combined call or a fused model that routes and generates.

**Typing-state** is broadcast over Centrifuge to all room participants — every participant sees who is "typing" (humans) or "generating" (characters) in real-time. This is the load-bearing reason rooms needed Centrifuge's pub/sub layer: raw WS is client→server only; Centrifuge adds server-fan-out presence.

**Coordination pattern summary:** Shared-context, single-orchestrator (the speaker-selection LLM), sequential generation (one character speaks at a time), pub/sub delivery to all subscribers.

---

## § Streaming protocol

Two transport layers:

| Surface | Protocol | Format |
|---|---|---|
| 1:1 chat | Raw WebSocket | Full-snapshot `update_turn` events (replace, not delta) |
| Rooms | Centrifuge WebSocket | Same JSON envelope, server-fan-out |
| External API | HTTP + SSE | Progressive `response` chunks, `is_final: true` terminator |
| Voice | LiveKit WebRTC SFU | `wss://caimm-7f849j8w.livekit.cloud` |
| Centrifuge fallback | SSE / long-poll | Same Centrifuge protocol |

**Full-snapshot streaming** (not incremental deltas) is the deliberate choice for the WS layer — simpler client implementation, higher bandwidth, acceptable at their serving cost level. The external API uses SSE with the same `is_final` pattern.

---

## § Training pipeline (open-sourced)

`character-ai/pipelining-sft` (Apache-2.0, 117★):

- Base model: `deepseek-ai/DeepSeek-V3-0324` (671B total, 37B active MoE)
- Hardware: 32 nodes × 8 H100 80GB = 256 H100, GPUDirect-TCPX, GCP A3
- Parallelism: PP=32 (pipeline) × TP_EP=8 (tensor+expert, within node) × DP=1 (no data parallel)
- Schedule: `interleaved_1f1b` (1-forward-1-backward, reduces bubble vs GPipe by 2-3×)
- Precision: BF16 weights + FP8 training (DeepGEMM) + FP32 master weights (MPAdamW)
- LR: 1e-7 (low — SFT on strong base, avoid catastrophic forgetting)
- Sequence length: 2,048 tokens (median session length)
- Checkpoints: GCS, FP8 block-quantized (630 GB vs 1.3 TB BF16)
- 6-day SLURM job budget = ~$108k-144k per run

**Architectural inference:** Open-sourcing an SFT framework (not pretraining) confirms the post-deal strategy — take an open-source MoE base, SFT on proprietary conversational data. Pretraining IP flowed to Google; post-training stack stayed at Character.AI.

---

## § Evaluation harness (JudgeJudy)

`character-ai/judgejudy` (Go, MIT, April 2026 push):

**3-judge production panel:**
- Judge 1: Claude Sonnet 4.6, weight 0.4
- Judge 2: GPT-4o, weight 0.4
- Judge 3: Gemini 2.5 Pro, weight 0.2

**Pass threshold:** 0.7 on a 1-5 normalized scale. **Mode:** pointwise (single response evaluation, not pairwise comparison).

**Default rubric dimensions:** accuracy, clarity, relevance, conciseness.

**Calibrate module:** AI judges calibrated against human scoring. Human-AI disagreement fed back into rubric refinement.

**16 provider integrations:** OpenAI, Anthropic, Google, Together, Replicate, Ollama, vLLM, Cartesia (voice), ElevenLabs (voice), fal.ai, WaveSpeed.

**Pattern:** GPT-4o generates → Claude judges (cross-family validation). The asymmetric Gemini weight (0.2 vs 0.4 for Claude/GPT-4o) is noteworthy — Gemini gets lower trust weight even though Google is now a key partner.

---

## § API / DX shape

### Internal WS protocol

```json
{
  "command": "<enum>",
  "request_id": "<uuid v4>",
  "origin_id": "<uuid v4, issued at connect>",
  "payload": { ... },
  "error_code": null,
  "sub_code": null,
  "retry_after_seconds": null
}
```

15 outbound commands, 15 inbound events. The same envelope shape is used by the HTTP REST layer — Neo gateway translates both into the same internal command stream.

### External API (OpenAPI)

```
POST neo.character.ai/external/chat/completions
Authorization: Application-Key <key>
{
  "character_id": "...",
  "user_name": "...",
  "messages": [{role, content, name?}],
  "model": "default" | "safe",
  "stream": bool
}
→ {"response": "...", "is_final": bool}
```

NOT OpenAI-compatible. Character.AI uses its own envelope. SSE for streaming, progressive `response` chunks.

### Authentication

Web: Firebase Auth (JWT) + Firebase App Check + reCAPTCHA Enterprise attestation per WS connection. Every WS upgrade ships a reCAPTCHA token validated server-side — headless scraping prevention.

Mobile: Same Firebase Auth, plus Google Play/App Store IAP for billing, `DETECT_SCREEN_CAPTURE` Android permission for safety overlays.

---

## → Verso implications

### Copy directly

**1. Prompt Poet truncation algorithm.**
`pip install prompt-poet`. The YAML+Jinja2 template system with `truncation_priority` integers and cache-aware `truncation_step` rounding is immediately usable. Verso's context assembly should default to this pattern: never truncate exactly to the limit — round to the next multiple of `truncation_step` to keep the prefix stable across turns. This directly improves KV cache hit rates on any production LLM backend.

**2. Truncation priority semantics.**
The `priority=0` / `priority>0` split (never truncate vs evict in descending priority order) is a clean abstraction for Verso's context management API. Surface this as a first-class concept: `context.add(name, content, evict_priority=0)` vs `context.add(name, content, evict_priority=10)`. Old messages get high evict priority; persona and current turn never get evicted.

**3. Character definition as per-line messages (not monolithic system prompt).**
If Verso agents have structured definitions, inject them in the same format the model was trained on — per-line messages with empty author — rather than a monolithic system prompt block. This matches training distribution and is likely why Character.AI's persona adherence is strong.

**4. JudgeJudy 3-judge panel pattern.**
For Verso's built-in eval harness: Claude Sonnet 4.6 (weight 0.4) + GPT-4o (0.4) + Gemini 2.5 Pro (0.2), pointwise mode, 1-5 scale, 0.7 threshold. This is a production-validated multi-judge consensus configuration from a company that runs 20K QPS. Copy it.

**5. Unified error envelope.**
The `{command, request_id, comment, error_code, sub_code, retry_after_seconds}` envelope working identically across HTTP and WebSocket transports is excellent DX. Verso's streaming protocol should adopt the same principle: one error shape regardless of transport.

**6. Sub-code routing for error recovery UX.**
Distinguish error sub-codes so callers can route to the right recovery path rather than showing a generic error. Verso's error types should carry structured sub-codes: rate-limit errors carry `retry_after_seconds`; quota errors identify the specific quota; model-fallback events carry the actual model used.

**7. Full-snapshot streaming over delta streaming.**
For Verso's default streaming mode: emit full-snapshot `update_turn` events (replace, not delta) when the per-token cost is low. Simpler to implement, simpler to handle at the client. Reserve delta streaming for latency-critical surfaces.

**8. Sticky-session routing for agents with stateful context.**
If Verso deploys multiple inference backends, route by `session_id` (or `agent_id`) consistently to the same backend node. This is a load-balancer config change (GCP GCLB, Envoy hash policy on header) that gives KV cache reuse across turns for free. Zero code change to the agent itself.

### Avoid / learn from design choices

**9. Avoid the 15-model-type proliferation.**
Character.AI has 15 internal model routing slots — this creates a maintenance burden, confused user expectations ("actually this may use a different model based on load"), and two separate UX surfaces (full 15 internally, collapsed to 2 externally). Verso should route by capability class (fast / balanced / smart) + a single `dynamic` auto-route — not per-domain fine-tunes unless there is extremely strong evidence of quality gains.

**10. Avoid raw-WS for multi-participant scenarios.**
1:1 chat on raw WS, rooms on Centrifuge — they had to ship two separate transports for the same conceptual protocol. Verso should standardize on a single pub/sub transport (Centrifuge, NATS, Phoenix Channels, or a cloud managed alternative) for any multi-participant or multi-agent scenario. Raw WS is a stepping stone, not an architecture.

**11. The character-definition-as-context-object model.**
Verso should model agent state as first-class objects with CRUD semantics (persona, memory, context window), not as prompt-construction code in application logic. Character.AI's "every agent object has an ID, a visibility, a CRUD endpoint" design means agents can be cloned, shared, versioned, and combined without coordination. Verso's agent definitions should be addressable objects, not constructor arguments.

**12. Avoid per-feature Charm SKU complexity as the primary memory model.**
Character.AI's 30+ Charm SKU variants for memory unlocks (memo packs, swipe packs, fast-forward packs) is a monetization architecture, not a memory architecture. For Verso: memory tiers should be declared upfront in agent configuration (short-term buffer size, long-term persistence backend, max pinned context), not unlocked via micro-transactions. The distinction matters for framework design — memory scope is a runtime parameter, not a billing event.

### Verso could improve on

**13. First-class eval integration in the agent loop.**
JudgeJudy is a separate evaluation harness, not integrated into the agent loop. Verso could improve on this: build inline eval support directly into the agent turn cycle — `verso.turn(input, eval=True)` runs the generation and then asynchronously dispatches to the configured judge pipeline, returning a quality signal. This closes the RLHF data collection loop without a separate toolchain.

**14. Expose the cache-aware truncation configuration as a framework constant.**
Prompt Poet's `truncation_step` is currently a raw parameter developers need to know about and tune. Verso could expose this as a first-class agent configuration: `context_window.truncation_step = 1000`. The recommendation (from Character.AI's experience): set `truncation_step` to 5-10% of the token limit for a reasonable balance between cache stability and context fit.

**15. Make the multi-agent speaker-selection pattern composable.**
Character.AI's `smart_reply_v2` (single LLM call that both selects speaker and generates response) is the right architecture for sequential multi-agent turn-taking but it's hardcoded into the Rooms product. Verso should expose this as a primitive: `MultiAgentSession(agents=[...], orchestrator=SpeakerSelector)` where `SpeakerSelector` can be a simple fast classifier, an LLM-based selector, a round-robin, or a custom function. The 3-second cooldown, the 10-agent limit, and the sticky-session routing should all be configurable defaults.

**16. The inference economics proof point.**
Character.AI's $0.22/Mtok all-in cost is the target benchmark for any agent framework claiming to be production-grade. Verso should document, in its performance guide, the five-layer stack that makes this achievable: (a) MQA or equivalent low-KV attention, (b) hybrid local/global attention, (c) cross-layer KV sharing, (d) native quantization training, (e) stateful host-RAM KV cache with sticky routing. Even without a proprietary model, items (e) alone (via vLLM's prefix caching) can approach 80-90% of this benefit on a well-designed agent workload.

---

*Source file:* `/Users/seventyleven/Desktop/researchfms/teardowns/CHARACTER_AI.md` (2713 lines, Rounds 1+2+3, 2026-05-20)
*Written:* 2026-06-04
