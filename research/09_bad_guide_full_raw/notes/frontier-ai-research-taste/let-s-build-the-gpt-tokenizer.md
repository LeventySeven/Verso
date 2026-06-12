# Andrej Karpathy — Let's Build the GPT Tokenizer
**Source:** YouTube · <https://www.youtube.com/watch?v=zduSFxRajkE> · February 2024 · 2h13m
**Transcript sources:** <https://www.fast.ai/posts/2025-10-16-karpathy-tokenizers> (fast.ai book-chapter conversion, most complete written version); <https://misbahsy.github.io/KarpathyLLMChallenge/TokenizationLLMChallenge.html> (technical walkthrough); <https://medium.com/@ritika.kapoor27/lets-go-deeper-into-the-gpt-tokenizer-2ac715df2309>; <https://francescopochetti.com/byte-pair-encoding-building-the-gpt-tokenizer-with-karpathy/>; Karpathy's own tweet thread at <https://x.com/karpathy/status/1759996549109776702>
**Status:** read_partial — no verbatim transcript found; fast.ai produced a "book chapter" conversion of the video, which is the most complete written source. Several technical blog posts independently verified key claims. Core content reliably reconstructed; verbatim quotes are limited.

---

## Core Arguments

### 1. Tokenization Is a Separate Stage — and It's Where Most Production Bugs Come From

Karpathy's framing:
> "Tokenizers are a completely separate stage of the LLM pipeline: they have their own training set, training algorithm (Byte Pair Encoding), and after training implement two functions: encode() from strings to tokens, and decode() from tokens back to strings."

This separation is conceptually important: the tokenizer's training corpus, vocabulary decisions, and merge priorities are *independent* of the language model's training. Mismatches between them cause the failure classes below.

> "Many issues that seem to stem from the neural network architecture or the LLMs itself actually originate from tokenization."

### 2. The BPE Algorithm From Scratch

Starting point: 256 byte tokens (all possible UTF-8 bytes). The BPE loop:
1. Find most frequent consecutive byte pair using `get_stats()`
2. Create a new token for that pair
3. Replace all occurrences with the new token using `merge()`
4. Repeat until target vocabulary size reached

Concrete compression result from the video: using a full blog post (~24,597 bytes), just 20 merge rounds reduced token count from 24,597 to 19,438 (1.27x compression) while expanding vocabulary from 256 to 276. The later merges in GPT-4's 100,000-token vocabulary achieve ~2x compression over GPT-2 — "the same text in roughly half the tokens."

Critical constraint: **merges must apply in training order at inference**, because later merges depend on earlier ones. Training-inference mismatch on merge order corrupts the vocabulary.

### 3. GPT-2 vs. GPT-4 Tokenization: The Regex Pre-Tokenization Step

GPT-2 and later GPT-4 (tiktoken) add a regex pre-tokenization step that forces splits across character categories before BPE runs:
- Words/letters, numbers, punctuation, whitespace are split before any merging.
- This prevents pathological cross-category merges like "dog." becoming a single token.

GPT-4 improvements over GPT-2:
- Case-insensitive contraction matching
- Numbers require 2+ digits (prevents single-digit tokens from dominating merges)
- Better newline handling
- More sophisticated whitespace merging

### 4. SentencePiece (Llama) vs. tiktoken (GPT)

tiktoken: byte-level BPE. Everything starts from bytes; all characters are reachable through byte combinations.

SentencePiece: operates on Unicode code points directly. Rare code points fall back to UTF-8 bytes with special byte tokens. Llama 2 config: vocab size 32,000, character coverage 0.9999 (leaving 0.0001 to byte fallback), `<s>` / `</s>` / `<unk>` special tokens.

Key difference: SentencePiece can merge entire multi-byte characters as units, making it more efficient for non-English languages that use multi-byte Unicode characters. tiktoken's byte-level approach is more robust but less efficient for non-ASCII heavy text.

### 5. The Tokenization Failure Catalog (Production Bugs)

These are the **experienced-only view** of the layer most developers treat as a black box:

**Non-English degradation:**
> "Hello world" in English = 2 tokens. In Korean = 20 tokens.
Tokenizers trained predominantly on English data have few learned merges for non-English scripts. Rare characters fragment into many byte tokens, consuming context and providing sparse statistical signal. The model sees the *same character* differently depending on context because byte boundaries shift.

**Arithmetic failures:**
The numeral "677" splits into " 6" and "77" — two separate tokens. Whether a number is one token or several is *arbitrary* (based on training corpus frequency). Addition, multiplication, and digit manipulation require the model to operate on fragmented representations. "127" might be a single token; "128" might be two. There is no systematic rule.

**Spelling and string reversal:**
"hello" is token 123 — the model has no direct access to the letters h, e, l, l, o. Tasks like "reverse this string" or "count the e's" require character-level access the model doesn't have. Longer merged tokens like ".DefaultCellStyle" may appear only as a unit; the model never learned the split components.

**Python code / whitespace:**
GPT-2 assigned separate tokens to each indentation space. Four-space indentation in Python generated four tokens per indent level, creating excessive repeated tokens that degraded coding performance. GPT-4's tokenizer consolidated whitespace more aggressively, substantially improving code generation quality.

**Trailing space artifacts:**
Prompts ending in a trailing space produce "mysterious warnings." The tokenizer processes "word " differently from "word" — the trailing space merges into the next token in normal text but becomes anomalous at end-of-sequence. A well-known source of subtle degradation when prompts are assembled programmatically.

**SolidGoldMagikarp and token vocabulary gaps:**
This class of failure: a token exists in the tokenizer's vocabulary (was a frequent string in the tokenizer's training corpus) but was **never seen in the language model's training data** because those two training sets differ. The LM's embedding for that token is uninitialized or random. Prompting with "SolidGoldMagikarp" (a Reddit username that appeared in tokenizer training data) caused GPT-2 to produce hallucinations, go off on tangents, or refuse to respond — the embedding vector had no coherent meaning.
> "SolidGoldMagikarp breaks GPT-2 because it was present in the training set of the Tokenizer, but not the LM later."

The broader lesson: tokenizer training corpus and LM training corpus should be aligned. Karpathy flagged a paper that systematically discovered many more such tokens.

**Special token injection / `<|endoftext|>` attack:**
> "When we ask GPT4 to print the special token `<|endoftext|>`? Nothing. We break it completely."
Special tokens like `<|endoftext|>` signal document boundaries to the model. If a user injects these tokens into prompts (or if a system assembles prompts that accidentally include them), the model halts or behaves erratically. This is a prompt-injection vector at the tokenizer layer, not the model layer.

**YAML vs. JSON format preference:**
YAML represents the same structured data in fewer tokens than JSON, because JSON's required syntax characters (`{`, `"`, `:`, `,`, `}`) each consume tokens while YAML's whitespace-based structure merges more aggressively. For LLM I/O that carries structured data, YAML is meaningfully more efficient.

### 6. Vocabulary Size Effects

GPT-4's cl100k_base (~100K vocabulary) vs. GPT-2's ~50K vocabulary: GPT-4 achieves roughly 2x compression — the same text fits in approximately half the context window. This is a major reason GPT-4 can attend to more effective context.

But larger vocabularies have a cost: more token types to learn embeddings for, more sparse coverage of each token in training data, higher softmax computation.

### 7. Decoding Edge Cases

Decode path: token IDs → vocabulary lookup → concatenate bytes → UTF-8 decode.

Edge case: invalid UTF-8 sequences (e.g., a token sequence that corresponds to an incomplete multi-byte character). Standard handling: "replace" mode inserts a replacement character (U+FFFD). This is silent corruption — the model's output may be technically invalid UTF-8 for a single token but "corrected" by the decoder. Production systems should validate decoded text explicitly.

---

## Key Quotes (Partial / Reconstructed)

1. "Tokenizers are a completely separate stage of the LLM pipeline: they have their own training set, training algorithm, and after training implement two functions: encode() from strings to tokens, and decode() from tokens back to strings."
2. "Many issues that seem to stem from the neural network architecture or the LLMs itself actually originate from tokenization."
3. "Tokenization underlies many of these problems." (on the failure catalog)
4. "SolidGoldMagikarp breaks GPT-2 because it was present in the training set of the Tokenizer, but not the LM later."
5. "When we ask GPT4 to print the special token `<|endoftext|>`? Nothing. We break it completely."
6. "Hello world" in English = 2 tokens. In Korean = 20 tokens. (reconstructed from multiple sources)

---

## VERSO RELEVANCE

### Finding 1: Special Token Injection Is a Tokenizer-Layer Prompt-Injection Vector
`<|endoftext|>` injected into prompts breaks the model entirely. This is below the agent layer.
**[NEW-IDEA §6.3 safety]** — Verso's safety layer should include tokenizer-aware prompt sanitization: strip or escape special tokens from tool outputs, user inputs, and memory retrievals before they reach the model. This is a concrete, implementable safety check that most agent frameworks ignore entirely. The attack surface is real: any tool that returns scraped web content could return `<|endoftext|>`. No-overkill verdict: a single regex/filter step in the context assembly path — one function, prevents a class of silent failures.

### Finding 2: Tokenizer Training Corpus ≠ LM Training Corpus → Vocabulary Gaps
The SolidGoldMagikarp class: tokens that exist in vocabulary but whose embeddings are uninitialized or random because they never appeared in LM training. Prompting with them produces incoherent outputs.
**[SHARPENS §6.4 model]** — Verso's model abstraction layer and cross-model failover need to account for tokenizer-level behavioral differences, not just capability differences. When switching models (cross-model failover), the *tokenizer* changes too — vocabulary size, merge priorities, special tokens all differ. A prompt that works on GPT-4 may produce vocabulary-gap failures on a model with a different tokenizer training corpus. No-overkill verdict: model metadata in the ModelSpec should include tokenizer family (tiktoken/sentencepiece) and known quirks.

### Finding 3: YAML Is More Token-Efficient Than JSON for Structured Agent I/O
Same data structure, fewer tokens in YAML vs. JSON, because JSON's required syntax characters each consume tokens.
**[NEW-IDEA §5.2 context]** — Verso's ContextBundle and tool output formatting should default to YAML (or a compact format) for structured data passed between tools and the model. For agents that make many tool calls with structured parameters, this is compounding context efficiency. Directly relevant to KV-cache prefix discipline: a stable YAML preamble is more cache-friendly than JSON. No-overkill verdict: format choice in the tool output serializer — one enum value, zero architecture change, measurable token reduction.

### Finding 4: Tokenization Failures Are a Black Box to Most Practitioners
The "experienced-only view" framing: arithmetic failures, non-English degradation, trailing-space bugs are not documented in model cards. They're discovered by running the model.
**[CONFIRMS §5.5 evals]** — Verso's embedded evals should include a tokenization-aware test suite: arithmetic spot-checks, non-English round-trips, trailing-space sensitivity, special-token injection attempts. These are the class of failures that only appear in production if you don't test for them. The define_outcome(bounded) infrastructure gives Verso a place to encode this knowledge systematically. No-overkill verdict: a `tokenizer_sanity` eval suite (~10 test cases) belongs in the default eval bundle, requiring no new infrastructure.

### Finding 5: Numbers Tokenize Arbitrarily — Agents That Handle Numeric Reasoning Are Exposed
"677" → [" 6", "77"]. Whether numbers are one or multiple tokens is arbitrary and frequency-determined.
**[SHARPENS §5.3 tools / §5.5 evals]** — Agent tools that return numeric data (financial figures, measurements, IDs) should format numbers in ways that match the model's tokenization patterns — specifically, avoid numbers that fragment at token boundaries. Where possible, pass numbers as structured fields (not free text) so the model doesn't need to parse them character-by-character. No-overkill verdict: a documentation note in the @tool decorator guide, not a code change.
