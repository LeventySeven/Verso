# Generative AI's Act Two

**Source:** https://sequoiacap.com/article/generative-ai-act-two/  
**Authors:** Sonya Huang, Pat Grady, and GPT-4 (Sequoia Capital)  
**Published:** September 20, 2023  
**Status:** read_full (via WebFetch + WebSearch corroboration)  
**Themes:** strategy, loop_harness, evals, context

---

## Faithful Digest

### The Act 1 → Act 2 Transition

The organizing thesis: the first wave of generative AI ("Act 1") came "from the technology-out" — a new hammer (foundation models) unleashed a wave of novelty apps that were "lightweight demonstrations of cool new technology." Act 2 shifts to "customer-back" innovation that solves human problems end-to-end. Foundation models become a *piece* of a more comprehensive solution rather than the entire solution.

The core indictment of Act 1 products: users try them once but don't return. The article identifies this as the central problem that must be solved to build enduring businesses.

### The Retention Problem — The Central Statistical Finding

**"Generative AI's biggest problem is not finding use cases or demand or distribution, it is proving value."**

The retention data is damning:
- **14%** — median DAU/MAU for generative AI apps
- **51%** — median DAU/MAU for incumbent software companies
- **60-65%** — DAU/MAU ratio for top consumer companies
- **85%** — WhatsApp's DAU/MAU (the gold standard)

This is the "guide-note" benchmark the instructions flag: the 60-85% DAU/MAU range is the test that separates sticky products from wrappers. Generative AI apps at 14% median are failing this test catastrophically.

Users adopt but don't retain. The month-one drop-off is severe. The "awkward teenage years" framing: products are flashy demos that haven't matured into daily-use essentials.

### The Killer Apps — What's Actually Working

The article identifies a small cohort of exceptions, each with concrete metrics:

1. **Character.AI**: "2 hour average session time" — the most jaw-dropping engagement number in the entire AI space. Deep emotional connection, roleplay, companionship use cases that create genuine daily habits.

2. **GitHub Copilot**: "55% more efficient" — measurable productivity gain in a professional workflow context. This is sticky because it embeds in daily dev work, not novelty exploration.

3. **Midjourney**: "hundreds of millions of dollars in revenue" with an eleven-person team — the economic efficiency miracle. Proof that generative AI unit economics can work at lean scale.

4. **ChatGPT**: Fastest to 100M MAU organically in 6 weeks (vs. Instagram 2.5yr, WhatsApp 3.5yr, YouTube/Facebook 4yr). But MAU ≠ DAU; the 14% median indicts this category.

**What these winners have in common:** they embed in specific, high-value workflows (coding, creative production) or create genuine emotional engagement (Character.AI). They are not demos.

### What Sequoia Got Wrong in Act 1

- Underestimated the speed of change
- Missed supply-side bottlenecks
- Assumed vertical separation of the stack would happen faster
- Underestimated competitive intensity from incumbents
- Thought data ownership would be the moat — actually "workflows and user networks seem to be creating more durable sources of competitive advantage"

This last point is important: the moat is not data, it is workflow integration + network effects.

### The Technical Playbook (Act 2 Stack)

Founders are doing the hard, boring work:

**Reasoning techniques:**
- Chain-of-thought, tree-of-thought, reflexion
- These improve output quality without model retraining

**Transfer learning:**
- RLHF and domain-specific fine-tuning
- Dataset curation as competitive moat

**Retrieval-augmented generation (RAG):**
- Reduces hallucinations
- Enables grounding in real data
- The main response to reliability concerns

**Developer tooling:**
- Langchain, Hugging Face, Pinecone, Langsmith, Weights & Biases
- These are the plumbing that lets Act 2 builders move fast

**Infrastructure:**
- Coreweave, Lambda Labs, Foundry, Replicate, Modal
- GPU access as a service

The insight: brick by brick, founders are building "flashy demos into whole product experiences."

### The Four Product Blueprints

**1. Generative interfaces**  
Moving beyond text-only conversation to voice and multimodal experiences. Perplexity (search), Inflection AI's Pi (human-like voice) as examples. The interface itself is the differentiator.

**2. Advanced editing experiences ("Copilot to Director's Mode")**  
Shift from zero-shot generation to "ask-and-adjust" workflows. Users direct, AI executes. Midjourney and Runway as examples. The editing layer creates stickiness that pure generation cannot.

**3. Increasingly sophisticated agentic systems**  
"Applications are increasingly not just autocomplete or first drafts for human review; they now have the autonomy to problem-solve, access external tools and solve problems end-to-end on behalf of users." Systems progressing from level 0 to level 5 autonomy. This is the Act 2 north star.

**4. System-wide optimization**  
Not embedding in a single user's workflow but tackling whole-system efficiency: picking off a chunk of support tickets or pull requests and autonomously solving them. "Making the whole system more effective." This is the enterprise play.

### The Compound Solution Architecture

Act 2 apps use foundation models as one component in a compound system:
- New editing interfaces make workflows stickier
- Multi-modal by design
- Foundation model + RAG + fine-tuning + custom UI + integrations

**Quote:** "Applications tend to use foundation models as a piece of a more comprehensive solution rather than the entire solution."

This is the blueprint for non-trivial AI products.

### Defensibility Thesis (Sequoia's Evolved View)

Surviving applications require defensibility through:
1. Proprietary data (weaker than expected)
2. Workflow integration (stronger than expected)
3. Vertical expertise
4. Network effects (user networks > data)

**Huang's "Act Three" foreshadowing** (from later 2025 analysis): vertical agents trained end-to-end for specific workflows using RL, synthetic data, and user feedback. This is the natural extension of the Act 2 compound system thesis.

---

## VERSO RELEVANCE

### [CONFIRMS §5.1 loop] Agentic autonomy as the north star
The "level 0 to level 5 autonomy" framing and the description of agentic systems that "problem-solve, access external tools and solve problems end-to-end" confirms Verso's bet on the loop as the core primitive. The retention winners are workflow-embedded, tool-using agents.  
**Verdict: confirm**

### [SHARPENS §5.5 evals — HIGH VALUE] The 60-85% DAU/MAU retention test
The specific benchmark (60-65% for top consumer, 85% for WhatsApp, 14% median for AI apps) is a precise evaluation criterion for whether an agent framework is building sticky products. For Verso, this translates directly to a design question: does the framework's default behavior pattern produce agents that users return to daily? The "prove value, not novelty" mandate is the right frame for evaluating Verso's eval framework design. If Verso evals only measure task completion, they miss the retention dimension.  
**Verdict: sharpen** — adopt the retention dimension as an eval axis

### [NEW-IDEA §5.5 evals] Agentic-level autonomy rating as an eval dimension
The level-0-to-level-5 autonomy progression is a new eval axis not previously captured: how autonomously does an agent complete tasks vs. how much human intervention it requires? This could map to a define_outcome() dimension in Verso's eval framework.  
**Verdict: lock-interface-defer** — worth building toward in eval design

### [SHARPENS §12 positioning/GTM] "Workflows and user networks" > data as moat
The explicit correction of the data-as-moat thesis (Sequoia saying they got it wrong) sharpens Verso's positioning argument. Verso's value is that it makes building workflow-embedded agents easy — the framework earns its place by enabling sticky workflow integration, not by storing data. This is a Verso GTM angle: "frameworks that enable workflow integration create the real moat."  
**Verdict: sharpen** — use in positioning

### [SHARPENS §4 architecture] Compound system = the harness, not the model
"Foundation models as a piece of a more comprehensive solution rather than the entire solution" is the Sequoia blessing of Verso's exact thesis. The model is a commodity; the harness (Verso's value) is the compound system. Sequoia validated this in 2023 — it's now the consensus view, which means Verso's competitive advantage must lie in *how well* it helps you build compound systems.  
**Verdict: confirm + sharpen** — this is the architectural proof point

### [CONTRADICTS §2 non-goals — minor] Act 3 foreshadows graph-based vertical agents
Huang's "vertical agents trained end-to-end for specific workflows using RL" could imply graph-structured pipelines. However this is the Act 3 vision (2025+), not the immediate opportunity. Verso's no-graph invariant is safe for Act 2; the contradiction is about the future trajectory of the field.  
**Verdict: resist (for now)** — monitor but don't concede the graph

---

## Key Verbatim Data Points

- "median DAU/MAU of 14%" vs. "60-65% for top consumer companies" vs. "85% for WhatsApp"
- "2 hour average session time" (Character.AI)
- "55% more efficient" (GitHub Copilot)
- "hundreds of millions of dollars in revenue" with eleven-person team (Midjourney)
- Act 1: "technology-out"; Act 2: "customer-back"
- "proving value" as the core challenge
- "workflows and user networks seem to be creating more durable sources of competitive advantage"
- "compound solution" using foundation models as "a piece of a more comprehensive solution"
