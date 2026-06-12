# The Bitter Lesson

**Source:** http://www.incompleteideas.net/IncIdeas/BitterLesson.html  
**Author:** Richard S. Sutton  
**Date:** March 13, 2019  
**Length:** ~1,600 words  
**Status:** READ FULL — full text retrieved via PDF mirror (UT Austin course materials)

---

## Full Digest

Sutton's opening claim is sweeping and direct: "The biggest lesson that can be read from 70 years of AI research is that general methods that leverage computation are ultimately the most effective, and by a large margin." The mechanism driving this is Moore's law — "its generalization of continued exponentially falling cost per unit of computation." The asymmetry Sutton identifies: most AI research is conducted as if computation were constant (so leveraging human domain knowledge is the natural strategy), but over any timeframe longer than a typical research project, "massively more computation inevitably becomes available." The human-knowledge approach and the computation-scaling approach "need not run counter to each other, but in practice they tend to. Time spent on one is time not spent on the other. There are psychological commitments to investment in one approach or the other."

### Four Historical Cases

**Computer chess.** The methods that defeated Kasparov in 1997 were based on "massive, deep search." At the time, the chess research community had invested in methods leveraging human understanding of chess structure. The reaction to deep search winning was denial: "they said that 'brute force' search may have won this time, but it was not a general strategy, and anyway it was not how people played chess." The chess researchers "wanted methods based on human input to win and were disappointed when they did not."

**Computer Go.** "A similar pattern of research progress was seen in computer Go, only delayed by a further 20 years. Enormous initial efforts went into avoiding search by taking advantage of human knowledge, or of the special features of the game, but all those efforts proved irrelevant, or worse, once search was applied effectively at scale." The added component beyond pure search: "learning by self play to learn a value function." Sutton explicitly frames learning as equivalent to search in its mechanism: "Learning by self play, and learning in general, is like search in that it enables massive computation to be brought to bear. Search and learning are the two most important classes of techniques for utilizing massive amounts of computation in AI research."

**Speech recognition.** 1970s DARPA competition: hand-coded methods (words, phonemes, vocal tract models) vs. statistical HMMs. HMMs won. This "led to a major change in all of natural language processing, gradually over decades." Deep learning is the latest step: "Deep learning methods rely even less on human knowledge, and use even more computation, together with learning on huge training sets." Verdict: "researchers always tried to make systems that worked the way the researchers thought their own minds worked — they tried to put that knowledge in their systems — but it proved ultimately counterproductive, and a colossal waste of researcher's time."

**Computer vision.** Early methods: edges, generalized cylinders, SIFT features. "But today all this is discarded. Modern deep-learning neural networks use only the notions of convolution and certain kinds of invariances, and perform much better."

### The Four-Step Bitter Pattern

Sutton distills the pattern to four observations: "(1) AI researchers have often tried to build knowledge into their agents, (2) this always helps in the short term, and is personally satisfying to the researcher, but (3) in the long run it plateaus and even inhibits further progress, and (4) breakthrough progress eventually arrives by an opposing approach based on scaling computation by search and learning. The eventual success is tinged with bitterness, and often incompletely digested, because it is success over a favored, human-centric approach."

### Two Positive Lessons

First: "the great power of general purpose methods, of methods that continue to scale with increased computation even as the available computation becomes very great. The two methods that seem to scale arbitrarily in this way are search and learning."

Second (more philosophical): "the actual contents of minds are tremendously, irredeemably complex; we should stop trying to find simple ways to think about the contents of minds, such as simple ways to think about space, objects, multiple agents, or symmetries. All these are part of the arbitrary, intrinsically-complex, outside world. They are not what should be built in, as their complexity is endless; instead we should build in only the meta-methods that can find and capture this arbitrary complexity."

The essay closes with a sharp distinction: "We want AI agents that can discover like we can, not which contain what we have discovered. Building in our discoveries only makes it harder to see how the discovering process can be done."

---

## VERSO RELEVANCE

### Finding 1: The harness-as-handcrafted-structure risk [SHARPENS §1 / §4]

Sutton's pattern maps directly onto framework design. Agent frameworks that hand-code orchestration structure — fixed graph topologies, hard-wired retry logic, baked-in routing heuristics — are doing exactly what chess researchers did: leveraging human understanding of the "special structure" of the domain to reduce the need for general methods. Each such design choice is a claim that we know how agents should reason better than the model does. The claim is often right in the short term (it ships faster, it works on the known cases) and exactly wrong in the long term (it ossifies, it breaks with each model generation). **Verdict for Verso: the loop should contain no hand-coded reasoning structure. The loop is meta-method; the model is the solver. This SHARPENS the "no graph required" invariant — graphs are a form of knowledge-building-in.** adopt-now

### Finding 2: The 1–2 year churn prediction is precisely Sutton's pattern [CONFIRMS §1]

The already-known finding that "tactical workarounds churn ~1-2yr; durable architecture persists 3+ model generations" is the Bitter Lesson applied to framework timescales. Sutton's four-step pattern predicts exactly this churn rate: hand-coded knowledge helps short-term, plateaus, then gets replaced by scale. This confirms the core Verso bet with 70 years of evidence behind it. **Verdict: confirm.** confirm

### Finding 3: "Build in only the meta-methods" as a positive design principle [SHARPENS §4 / §5.1]

The positive prescription — "build in only the meta-methods that can find and capture this arbitrary complexity" — is a precise design constraint for the loop. The Verso loop should provide: (a) the scaffolding for a model to call tools, (b) the infrastructure to observe and checkpoint state, (c) the mechanisms to evaluate outcomes. It should NOT encode: specific reasoning strategies, domain heuristics, task-specific flow control. This is a sharper formulation than "simple loop": it's not just about line count, it's about whether the loop is a meta-method or an object-level method. **Verdict: sharpen §5.1 — add language about "meta-method not object-method" to loop rationale.** sharpen

### Finding 4: "Personally satisfying to the researcher" as an anti-pattern signal [NEW-IDEA §2 / §12]

Sutton identifies a psychological mechanism: "this always helps in the short term, and is personally satisfying to the researcher." Graph-based orchestration and hand-crafted tool routing FEEL like good engineering. They feel clean, reasoned, intentional. This personal satisfaction is precisely the warning sign Sutton flags. For Verso's GTM/positioning: the argument against Sutton-style over-engineering is not just technical but cognitive — frameworks that let you feel in control by encoding your knowledge are doing you a psychological disservice. **Verdict: worth adding to §12 positioning — "the satisfaction trap."** lock-interface-defer

### Finding 5: "Search and learning scale arbitrarily" — implications for inference-time compute [SHARPENS §6.4]

"The two methods that seem to scale arbitrarily in this way are search and learning." Combined with Raschka's findings on inference-time scaling and reasoning models: Verso's model/provider layer should treat inference-time compute (longer chains, multiple samples, verification passes) as a first-class scaling dimension, not an afterthought. The loop infrastructure must support streaming long CoT responses and potentially multiple parallel model invocations without architectural change. **Verdict: sharpen §6.4 — reasoning model support (long context, streaming CoT) is not optional infrastructure.** sharpen

---

## Summary Verdict

The Bitter Lesson is the single most load-bearing external reference for Verso's core bet. It provides 70 years of empirical evidence for exactly the architectural choice Verso makes: minimal hand-coded structure, general meta-methods, trust the model (the search/learning substrate) to do the object-level work. The essay should be cited in the PRD introduction, not just as color but as the evidentiary foundation for the no-graph invariant.
