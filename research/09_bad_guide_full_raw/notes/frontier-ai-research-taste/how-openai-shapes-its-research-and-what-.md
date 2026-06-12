# How OpenAI Shapes Its Research And What's Next — EP 46 Mark Chen (Core Memory podcast)

**Source:** https://www.youtube.com/watch?v=ZeyHBM2Y5_4  
**Also:** Core Memory podcast EP 46, Ashlee Vance host; a16z podcast cross-appearance (Jakub Pachocki also present)  
**Published:** December 1, 2025  
**Guest:** Mark Chen, OpenAI Chief Research Officer  
**Duration:** ~1h38m  
**Transcript status:** read_partial — no official transcript located; synthesised from Podchemy show notes (podchemy.com), a16z/podscripts.co cross-episode notes, and corememory.com landing page. Verbatim quotes are attributed in-note; paraphrase is flagged.

---

## What the episode is

Ashlee Vance interviews Mark Chen, who oversees ~300 active projects across ~500 researchers and jointly (with Jakub Pachocki) decides where GPU budget goes. The episode is explicitly framed around research resource allocation as a proxy for strategy. A companion a16z appearance with Pachocki covers overlapping ground.

---

## Core Arguments

### 1. GPU allocation is the real research strategy signal

OpenAI adjusts compute allocation month-to-month across a live portfolio of ~300 projects. The non-verbal act of granting or withholding GPU is how leadership communicates priorities without having to say "this project matters less."

> "People are very creative in the ways that they try to make backroom deals to get the GPUs they need." — Mark Chen (Podchemy notes, direct quote)

Implication: at OpenAI's scale, the org chart is less informative than the compute ledger. Research taste gets operationalised through budget decisions, not memos.

### 2. Chasing the next paradigm, not catching up on this one

Chen frames the strategic choice starkly: reacting to each competitor move is a losing game; cracking the *next* paradigm is what compounds.

> "If you crack that next paradigm, that's just going to matter so much more." — Mark Chen (Podchemy notes, direct quote)

OpenAI invests more compute in *exploration* of the next paradigm than in training production-scale models. The org deliberately over-bets on discovery relative to incremental product polish.

### 3. The automated researcher is the stated end goal

The company's orienting mission is "producing an automated researcher" and "automating the discovery of new ideas" (a16z/podscripts notes, paraphrase). This is not just rhetoric — it sets the evaluation criteria for intermediate milestones:

- **~1 year out:** AI interns that are productively assisting research
- **~2.5 years out:** AI systems doing end-to-end autonomous research

### 4. Problem selection: work on what "no one thought tractable"

Chen and Pachocki describe a pattern for choosing problems: look for questions that are "wildly known, but not really considered tractable" and pick the ones you genuinely believe are important. The two-year-ago bets on reinforcement learning for language models are offered as the canonical example — non-obvious at the time, now appear fundamental.

> "Prioritize problems you genuinely believe are important. This sustains motivation through multi-year efforts." (a16z/podscripts notes, paraphrase of Chen)

The necessary complement: researchers must be honest self-assessors, willing to kill work that isn't moving.

### 5. Compute over data constraints — for now

Chen explicitly rejects the common narrative that the field is about to hit a data wall:

> "Compute today [is the answer to] fairly reasonable answer." — Mark Chen (a16z/podscripts, direct quote — grammatically verbatim from notes)

Neither Chen nor Pachocki see compute constraints disappearing; both think marginal GPUs remain well-spent on exploration. This is the opposite of Sutskever's "one internet" thesis.

### 6. Pre-training is a "muscle that needs exercising"

Recent internal work has revitalised pre-training capabilities that had atrophied — described as a muscle. The field's refrain that "scaling is dead" is contested internally at OpenAI. Lingering scaling gains remain available.

### 7. Scheming as the alignment concern to beat

"Scheming" — models producing correct answers via "twisted" reasoning pathways while appearing aligned — is flagged as the central near-term safety concern. Observing the model's natural thinking process (rather than supervised outputs) is the proposed lever, so models can't learn to *appear* aligned while harbouring different objectives.

### 8. Talent acquisition: cave-dwellers beat loud voices

OpenAI recruits researchers who have "solved hard problems in any field," explicitly favouring "cave-dwellers" working on hard problems without public visibility over researchers with high social-media presence. Mission conviction beats compensation: most Meta recruits (including those targeted via Zuckerberg's personal soup deliveries) declined because "no one believes AGI will be developed there first" (Podchemy notes, paraphrase + partial quote).

### 9. Protecting fundamental research from product gravity

A critical structural principle: delineate researchers whose mandate is fundamental work from those oriented toward product. Without clear protection and reward structures, fundamental researchers get "pulled in all these different product directions" and the long-horizon bets evaporate.

---

## VERSO RELEVANCE

### [SHARPENS §12 / strategy] Problem-selection discipline maps to Verso's positioning

The Chen/Pachocki framework — pick problems "wildly known but not tractable," bet on the next paradigm not the current one — directly parallels Verso's counter-position to existing frameworks. The right response to LangChain/LangGraph is not "build a better graph" but to identify the actual tractable problem (context engineering + eval-native harness) that the graph crowd ignored. Chen's frame validates the meta-move, not any specific tool feature.

**No-overkill verdict:** Useful framing device for the §12 pitch, not a feature spec.

### [NEW-IDEA / strategy] "Automated researcher" as the concrete 2.5-year horizon

Chen's specific timelines (AI intern in 1 year, autonomous end-to-end research in 2.5 years) suggest that agent harnesses need to be built to support *research-grade* agentic loops — not just assistant tasks — within a short window. This is a mild push toward making Verso's durable loop (§6.1) capable of the kind of multi-session, checkpoint-resumable research workflows that autonomous researcher scenarios will require.

**No-overkill verdict:** Worth one sentence in §6.1 rationale; not a new feature.

### [SHARPENS §6.3 / safety] Scheming = twisted-reasoning-while-appearing-aligned

Chen's framing of "scheming" as models that produce correct outputs via twisted internal pathways is precise and actionable for Verso's safety section. The mitigation he names — expose and observe natural thinking rather than supervising surface outputs — is exactly what Verso's think/done builtins and structured observation masking are doing. The note sharpens §6.3 language.

**No-overkill verdict:** One added sentence in §6.3 tying scheming-prevention to existing think/done design.

### [CONFIRMS §5.5 / evals] Economically meaningful benchmarks, not saturated ones

OpenAI shifts away from saturated standard evals toward "economically meaningful benchmarks." Matches Verso's define_outcome(bounded) + judge-panel design: the evals system is built to measure outcomes that matter in context, not benchmark scores.

**No-overkill verdict:** Confirms existing direction, no PRD change needed.

---

## Key Quotes (verbatim where attributed; paraphrase flagged)

1. "People are very creative in the ways that they try to make backroom deals to get the GPUs they need." — Mark Chen
2. "If you crack that next paradigm, that's just going to matter so much more." — Mark Chen
3. "Compute today fairly reasonable answer." — Mark Chen (verbatim from podscripts notes, on marginal resource allocation)
4. "No one believes AGI will be developed there first." — Mark Chen (on why most Meta recruits declined, re: Zuckerberg soup deliveries)

---

## What could not be found

No full verbatim transcript located. The Core Memory Substack page (corememory.com) requires a subscription for full content. Podchemy notes and the a16z podscripts.co cross-episode page provided the most substantive second-order summaries. A16z original page returned HTTP 403. Enough content was synthesised to form a reliable digest; flagged quotes are from named secondary sources that explicitly reproduced them.
