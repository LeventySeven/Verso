# inv-verso-adapt-2026-08-22 — ALL-transcripts sweep + teardowns + guides + pydantic-ai 2.33.0

## The question
What should Verso build/adapt next, and what should it decline — grounded in the FULL transcript
corpus (all 40 files), related teardowns, the three named talks, the guides, and pydantic-ai's
newest version (2.33.0)?

## Required fields (every candidate must fill all six)
- MECHANISM — what Verso would build, in Verso's vocabulary
- SHAPE — the exact API / parameter / flag surface
- PREVENTS — the failure it prevents, or the capability it adds
- EVIDENCE — one-line QUOTE + path:LINE
- FIT — against the 5 binding rules (additive-or-byte-identical · loop stays small · not a graph DSL ·
  non-goals · tests are the contract)
- VERDICT — ADOPT | ADAPT | DECLINE | DEFER + reason

## Coverage matrix (over the ASK, phrase by phrase)
| phrase (verbatim) | sub-question | scope check | primary sources | Gap? |
|---|---|---|---|---|
| "ALL transcripts ... literally all" | every one of the 40 transcript files read | must NOT narrow to "the 10 relevant ones" | 40 files / 39 agents | |
| "in workflow investigation skill" | use the skill's lanes + evidence contract | | skill loaded | |
| "via parallel agents workflow" | fan-out shape, one wave | | Workflow tool | |
| "some related teardowns" | framework peers · durable-exec · coding harnesses | "related" = related to VERSO's design, not all 395 | 3 lanes | |
| video CEvIs9y1uog | "Don't Build Agents, Build Skills Instead" (Barry Zhang + Mahesh Murag, Anthropic) | | TRANSCRIPTS_CODE_WITH_CLAUDE.md:1667 | ON DISK |
| video CxXgV54KzpQ | "Jeff Dean: The 1% Rule for Building in AI" (YC) | | TRANSCRIPTS_YC.md:30811 | ON DISK |
| video aR20FWCCjAs | Ilya Sutskever / Dwarkesh — age of scaling -> age of research | | full text NOT on disk | **WEB LANE** |
| "some guides" | BAD_GUIDE x2 · GUIDES_AI_ENGINEERING · CLAUDECODEMAXXXING · GUIDES_30PAPERS | | guides lane | |
| "once again check pydantic ai" | DELTA vs the existing 1.x teardown, not a re-read | | PYDANTIC_AI.md = 1.x baseline | |
| "their newest version" | 2.33.0 source specifically | must be 2.33.0 SOURCE, never the teardown | extracted to scratchpad | |
| "to what we can adapt" | adaptation candidates WITH fit verdicts | not "a summary of pydantic-ai" | Verso self-fit lane | |

## Enumeration (lane | files listed | candidates selected | cut line)
| lane | listed | selected | cut line |
|---|---|---|---|
| researchfms/Transcripts/*.md | 39 | 39 | none — user said ALL |
| guidesfm/TRANSCRIPTS_HORMOZI.md | 1 | 1 | heading-routed, distribution/positioning angle only |
| researchfms/teardowns/*.md | 395 | ~24 | framework peers + durable-exec + coding harnesses; rest = unrelated products |
| guidesfm/research/articles/*.md | 190 | ~16 | agent-design + evals canon via _manifest.json routing |
| guides (BAD_GUIDE x2, GUIDES_*, CLAUDECODEMAXXXING) | 6 | 4 | GUIDES_APPLE_HIG + GUIDES_DESIGN_ENGINEERING cut (UI, not agent design) |
| pydantic-ai 2.33.0 source | 114,275 LoC | ~12 modules | engine/durable/capabilities/toolsets/output |
| live web | — | 1 | Ilya/Dwarkesh only; everything else is on disk |
| Verso self | ~4k LoC + docs | 8 | PRD, README, loop, durable, orchestrate, safety, research/12 |

## Open questions
(standing block — read before dispatch, reconciled before answering)

- **[BASELINE CORRECTION, orchestrator, pre-fan-in]** UNIT-40/41/42 were briefed that the teardown
  baseline is the 1.x line (`cff2825`, 2026-05-30). That is only half true. `PYDANTIC_AI.md:796`
  carries a **Deep Refresh dated 2026-07-10 at PyPI `2.8.0`** (HEAD `8432869`). The real delta to
  compute is therefore **2.8.0 -> 2.33.0**, and the refresh section (L794-918) already records:
  `end_strategy` default flipped `'early'` -> `'graceful'`; `_tool_execution.py` parallel-execution
  rewrite; `Agent.from_spec()` (declarative agents from YAML/JSON/dict); a 3rd durable backend;
  `builtin_tool_*` streaming events removed. The source agents read 2.33.0 directly so their findings
  stand; the ORCHESTRATOR owns re-basing the delta at synthesis. Do not accept a "this is all new
  since 1.x" framing from UNIT-40/41/42 without checking it against L794-918.

## Fleet — dispatched 53 agents, one wave (run wf_0c78be69-d6b)
Phase 1 Transcripts: UNIT-01..39 (40 files; STANFORD/YC x3, COURSERA/A16Z/DLAI_COURSES x2, HORMOZI narrow)
Phase 2 Frameworks:  UNIT-40..42 pydantic-ai 2.33.0 SOURCE · 43..45 teardowns · 46..47 primary essays
                     · 48 guides · 49 web/Ilya · 50 Verso self-map
Phase 3 Adversary:   UNIT-51 against the additions · UNIT-52 against VERSO'S OWN THESIS · UNIT-53 gaps + round-2 nouns

## Fan-in reconciliation (orchestrator, post-run)
- Units: 53 dispatched / 53 returned. UNIT-01..53, no blank anchors. Unit count == block count.
- Outcomes: DONE 53 · EMPTY 0 · FAILED 0. Findings: 422.
- **Quote relocation: 422/422 pass, 0 mismatches** (positional `sed -n 'Np'` + fixed-string match).
- Numeric drift: 52 claims carry a number outside their quote; audited — 51 are course codes / version
  numbers / line refs. ONE real drift: HaluEval 53.8–58.5% is measured on "ChatGPT and Claude 2"
  (2023-era), NOT frontier models as UNIT-51 framed it. Corrected in VERDICT.md §0 and §6.3.
- Cap saturation: 51/53 units returned exactly 8 findings. The CAP bound, not the corpus — recorded as
  a limit on the run, not hidden.
- Contradictions resolved by orchestrator re-read (not by preferring the better-written finding):
  multi-agent (§3.1), evals-as-moat (§3.2), harness durability (§3.3).
- Orchestrator re-opened at source before writing: the 3 pydantic deprecation markers, the graph-spine
  question (graph ALIVE, persistence GONE — the fleet blurred this), `kind='unapproved'`,
  `_reject_runtime_toolsets`, HaluEval, the fail-open count, the harness-survival quote.
- Open question closed: baseline correction applied — delta computed 2.8.0 → 2.33.0, not 1.x → 2.x.

Deliverable: VERDICT.md · full evidence: FINDINGS.md
