# RAW EXTRACTION — BAD_GUIDE.md: simplicity / product-taste / leverage canon

**Source file:** `/Users/seventyleven/Desktop/guidesfm/BAD_GUIDE.md` (2062 lines, 280 KB)
**Unit:** badguide-simplicity-product-leverage (track: methodology)
**Extraction date:** 2026-06-22
**Sections read (verbatim, by line):** The Bet (54-78), Founder Mind (81-130), Modern CTO / harness craft (199-298), Revolutionary Products / agent-simplicity canon (655-814), Product Taste / CPO (856-1012), Design & UX / slop-vs-craft (1014-1042), Leverage & Becoming Hunted (1277-1348), Bullshit Filter (1418-1438), Operating System (1441-1457).

Every item below is **KNOWN-from-source** unless tagged `[INFERRED]`. Quotes are verbatim from the file.

---

## A. THE AGENT-SIMPLICITY CANON (the spine of Verso's thesis)

These are the source's annotated-bibliography entries plus its own principle prose. This is the densest cluster of "just build agents / keep it simple / frameworks obscure the prompts" material.

### A1. Thorsten Ball (Amp / Sourcegraph) — "the agent loop is not the moat" `[KNOWN]`
> **[How to Build an Agent (The Emperor Has No Clothes)]** — *Thorsten Ball (Amp / Sourcegraph)* · `MUST`
> "The agent core is a model, a loop and three tools in **~315 lines of Go**, and every hard, valuable thing lives elsewhere: editor integration, prompt craft, feedback timing, orchestration. Read it to stop treating the agent loop as the moat."

This is the single most on-thesis line in the file for Verso. "model, a loop and three tools in ~315 lines" ≈ Verso's "ONE clean async ReAct loop (<200 lines)."

### A2. Anthropic, "Building Effective Agents" (Schluntz & Zhang) `[KNOWN]`
> **[Building Effective Agents]** — *Erik Schluntz & Barry Zhang (Anthropic)* · `MUST`
> "Ground truth for which architectural shape (prompt chaining, orchestrator-workers, evaluator-optimizer) fits which problem — use it to audit whether your LangGraph topology is solving the right class of problem."

Named patterns the source treats as canon: **prompt chaining, orchestrator-workers, evaluator-optimizer**. The guide explicitly uses this to *audit/cut* graph topology ("whether your LangGraph topology is solving the right class of problem").

### A3. Tips for Building AI Agents (the same authors, on camera) `[KNOWN]`
> **[Tips for Building AI Agents]** — *Barry Zhang, Erik Schluntz & Alex Albert (Anthropic) · video · 18m* · `STRONG`
> "The Building Effective Agents authors... with the decisions the essay compresses: **when not to build an agent at all**, where to put checkpoints, and how to keep a system debuggable. Eighteen minutes, no filler."

"When not to build an agent at all" + "where to put checkpoints" = directly validates Verso's tactical→durable seam and its anti-overkill stance.

### A4. Cognition — "Don't Build Multi-Agents" (Walden Yan) `[KNOWN]`
> **[Don't Build Multi-Agents]** — *Walden Yan (Cognition)* · `MUST`
> "The person who built Devin's harness against the multi-agent default: **share the full agent trace, not only the messages**, and accept that **parallel agents make conflicting implicit decisions that produce broken output**. The canonical statement of the single-threaded-context position."

### A5. Cognition update — "Multi-Agents: What's Actually Working" `[KNOWN]`
> **[Multi-Agents: What's Actually Working]** — *Walden Yan (Cognition)* · `STRONG`
> "The same team updating its own famous thesis ten months on: **multi-agent works only when writes stay single-threaded and the extra agents add intelligence (review loops, hierarchical delegation) rather than actions.** Read right after the original; the honest update is the lesson."

### A6. browser-use — "The Bitter Lesson of Agent Frameworks" (Gregor Zunic) `[KNOWN]`
> **[The Bitter Lesson of Agent Frameworks]** — *Gregor Zunic (browser-use)* · `MUST`
> "...inverting the usual design: **start with maximal capability then restrict, delete the click/type/scroll abstraction, hand the model raw DevTools Protocol, and accept that ~99% of the value lives in the RL'd model, not your harness. Every abstraction is a liability.**"

"Every abstraction is a liability" / "~99% of the value lives in the RL'd model, not your harness" — the strongest minimalist statement in the file. (Note for Verso: this is the *adversarial* edge — Verso's counter is that the harness is the *additive, byte-identical-when-unused* layer; it does not contradict "every primitive must earn its keep.")

### A7. Boris Cherny — Building Claude Code (delete code on every model release) `[KNOWN]`
> **[Building Claude Code with Boris Cherny]** — *Boris Cherny (Anthropic)* · `STRONG`
> "...the 'product overhang' (capability existed, scaffolding didn't), **deleting code on every model release and keeping ~90% self-written so the scaffolding doesn't hobble the model**, and choosing **Bash as one universal interface over dozens of bespoke tools.**"

Two Verso-relevant primitives: (1) "deleting code on every model release ... so the scaffolding doesn't hobble the model"; (2) "Bash as one universal interface over dozens of bespoke tools."

### A8. Anthropic — "How We Built Our Multi-Agent Research System" (the honest counterweight) `[KNOWN]`
> **[How We Built Our Multi-Agent Research System]** — *Jeremy Hadfield, Barry Zhang et al. (Anthropic)* · `MUST`
> "...orchestrator-worker system... **token usage explains about 80% of the performance variance, multi-agent helps for breadth-first research and hurts for coding, and the hard part is the engineering around the agents (state, retries, evaluation).** Read it directly against Cognition's 'Don't Build Multi-Agents' above to see where two serious teams disagree and why."

NUMBER: **token usage explains ~80% of performance variance.** The "hard part is the engineering around the agents (state, retries, evaluation)" is exactly Verso's durable seam + evals wedge.

### A9. Lindy (Flo Crivello) — scaffolding deterministic, model for judgment `[KNOWN]`
> **[Living Lindy: a No-BS Conversation on AI Agents]** — *Flo Crivello (Lindy)* · `STRONG`
> "Two years of running agents in the wild: **the problem is task ambiguity, not task length (if you could brief an intern with a clear doc, an agent can do it), few-shot gold examples from human corrections beat instructions and fine-tuning, and your tools must not themselves be agentic. The model is for judgment; the scaffolding is deterministic.**"

"Your tools must not themselves be agentic. The model is for judgment; the scaffolding is deterministic." + "few-shot gold examples from human corrections beat instructions and fine-tuning" (cf. Verso's LLMJudge(examples=)).

### A10. Sierra (Clay Bavor) — simulator-as-regression, supervisor chaining `[KNOWN]`
> **[Sierra: Making Customer-Facing AI Agents Delightful]** — *Clay Bavor (Sierra)* · `MUST`
> "...models detect their own errors better than they avoid making them, so they **chain supervisor agents to compound past the per-model ceiling**, and run a **conversation simulator that turns every fix into a permanent regression test.** Concrete proof you engineer the harness around today's model rather than wait for a better one."

"turns every fix into a permanent regression test" ≈ Verso's "captured failure IS a regression test."

### A11. Armin Ronacher (Flask) — "Agent Design Is Still Hard" `[KNOWN]`
> **[Agent Design Is Still Hard]** — *Armin Ronacher* · `MUST`
> "...**skip the high-level SDKs because model differences force your own abstraction, prefer explicit cache control, reinforce the objective on every tool return rather than once up front, and isolate failures in throwaway sub-agents that report only outcomes.**"

"skip the high-level SDKs" + "reinforce the objective on every tool return" (= Verso's `reinforce_objective`) + "explicit cache control" (= Verso KV-cache-stable prefix). Strong direct validation.

### A12. Anthropic — "Effective context engineering for AI agents" `[KNOWN]`
> **[Effective context engineering for AI agents]** — *Anthropic (Applied AI)* · `STRONG`
> "...treating context as a finite resource to curate: **degradation is a gradient from n-squared attention, not a cliff, and just-in-time retrieval (keep lightweight identifiers, fetch at runtime) beats pre-loading the corpus.** The discipline that succeeds prompt engineering."

### A13. Anthropic — "Effective harnesses for long-running agents" `[KNOWN]`
> **[Effective harnesses for long-running agents]** — *Anthropic (Applied AI)* · `MUST`
> "The harness is the layer that compounds across model generations while the model stays swappable. Concrete patterns you cannot look up: **a feature-list-as-executable-spec the agent may toggle but not edit, git-as-state-machine for recovery, a progress file as memory across context windows, and a dual initializer/worker split.**"

"feature-list-as-executable-spec the agent may toggle but not edit" ≈ Verso's "# SCAFFOLD() ratchet" + verify-before-done. "git-as-state-machine for recovery" / "progress file as memory" ≈ Verso checkpoint/resume.

### A14. Anthropic — "Building Agents with the Claude Agent SDK" `[KNOWN]`
> "The **gather-context, take-action, verify-work loop** generalized into a reusable pattern... How to structure an agent so context-gathering and verification are explicit stages rather than afterthoughts."

### A15. Anthropic — "Writing Effective Tools for AI Agents" (eval-driven tool design) `[KNOWN]`
> **[Writing Effective Tools for AI Agents]** — *Ken Aizawa et al. (Anthropic)* · `MUST`
> "Eval-driven tool design where you let the agent help rewrite its own tool definitions: **build a small eval, watch where the agent misuses a tool, then fix the tool's interface instead of the prompt.** The non-obvious lesson is that **tool ergonomics for a model are not the same as tool ergonomics for a human.**"

### A16. Anthropic — "Code Execution with MCP" (NUMBER: ~98% token reduction) `[KNOWN]`
> "Instead of exposing every tool as a direct call, give the agent a code sandbox and let it call tools as code, which the post measures at **roughly a 98% token reduction on a realistic workflow.**"

`[INFERRED]` This is the ONE genuinely additive idea for Verso to *consider* — code-over-tools as an opt-in tool-exposure mode. Flagged in "steal" with caveats (MCP-adjacent; Verso is native-@tool-first, MCP opt-in).

### A17. Ralph Wiggum (Geoffrey Huntley) — single deterministic bash loop `[KNOWN]`
> **[Ralph Wiggum as a 'software engineer']** — *Geoffrey Huntley* · `OPTIONAL`
> "...**a single deterministic bash loop running one focused task on a fresh context each pass makes failure modes observable and tunable, and can beat elaborate multi-agent orchestration running on a stale context.** The originating account, from someone who built a compiler this way."

"fresh context each pass" ≈ Verso resume() in a FRESH process.

### A18. Harrison Chase / LangChain — the honest tension `[KNOWN]`
> **[Reflections on Three Years of Building LangChain]** — *Harrison Chase* · `STRONG`
> "The honest tension between **ease-of-use and production reliability in agent frameworks**... so you know what LangGraph fixed and what's still unsolved."

---

## B. THE GUIDE'S OWN PRINCIPLE PROSE ON SIMPLICITY / ARCHITECTURE-BEATS-MODEL

### B1. "The architecture beats the model — stop swapping models, start building layers" (§Modern CTO) `[KNOWN]`
> "Same model, different harness, **5-point swing on SWE-bench Pro (Opus 4.5 ran 50.2% to 55.4% purely on context management and tool orchestration).** v0 took Sonnet from **64.7% to 93.9%** error-free with four engineering layers (RAG injection, stream-time fixing, deterministic AST/icon validation, a fine-tuned AutoFixer), not a single model upgrade. **When Skale's agent underperforms, the fix is almost never a better model. It is your context window, your tools, your error recovery.**"

NUMBERS: 50.2%→55.4% (5-pt swing, harness only); 64.7%→93.9% (v0, four layers).

### B2. "KV-cache is your #1 cost lever" (§Modern CTO) `[KNOWN]`
> "Production agents run **~100:1 input:output.** That means cache optimization matters 100x more than output optimization. **Keep a static system-prompt prefix, append-only context, deterministic JSON serialization, and route sessions to consistent workers.** These are architecture decisions with 10x cost impact..."

Directly maps to Verso: KV-cache-stable system prefix + append-only history + deterministic serialization.

### B3. "Decouple the decider from the executor" `[KNOWN]`
> "Cursor's apply model: a big smart model writes a sketch with placeholders, a small fast fine-tuned model performs the actual edit at **~1,000 tok/s (13x faster)**... Wherever you have a slow expensive judgment and a fast mechanical execution, split them."

`[INFERRED]` Verso supports this already via per-call model= swap + agent.override(); not a new primitive.

### B4. "Software is three layers now" — Karpathy 1.0/2.0/3.0 `[KNOWN]`
> "Karpathy's frame: 1.0 is hand-written code, 2.0 is trained weights, 3.0 is natural-language prompts... Your edge as CTO is no longer the architecture diagram. It is the **generate/verify loop** and the product taste that decides which generation is correct."

### B5. "Composite architecture beats both wrappers and your own foundation model" (§Revolutionary Products) `[KNOWN]`
> "Vercel's v0 took Claude Sonnet's **64.71% error-free rate to 93.87%** with engineering, not model training: RAG context injection, real-time stream-fixing during generation, deterministic AST fixes, a fine-tuned AutoFixer. **Malte Ubl's rule: don't train your own foundation models if you want to iterate fast; use a composite architecture to stay flexible. The compounding moat is the harness around the model, not the model itself. It survives every frontier release instead of being obsoleted by it.**"

### B6. "The only three things that compound" (§The Bet) `[KNOWN]`
> "**Taste, distribution, and a primitive nobody else has.** Everything in this manual ladders up to one of those three. **If a thing you're about to spend a week on doesn't grow your taste, your distribution, or your primitive — that's the bullshit. Cut it.**"

This is the file's core leanness law. Mirrors Verso's "cut anything that buys only ~1% or complexity-for-its-own-sake."

### B7. Bullshit Filter — subtraction discipline `[KNOWN]`
> "**Velocity comes from subtraction.**" (weekly loop, line 1451: "Cut one thing. Kill a feature, a doc, a half-built repo.")
> "Summaries of summaries. **Go to the primary source every time.**"
> The filter in one line: "**don't spend new time relearning what you have; spend it on taste, distribution, and a primitive.**"

---

## C. PRODUCT TASTE AS A TRAINED PERCEPTUAL SKILL (the CPO half)

### C1. Section thesis (line 860) `[KNOWN]`
> "The 1% treat **taste as an objective, trainable apparatus** — Paul Graham's claim that **designers measurably improve over time proves good design has real properties you can learn to see.** In the AI era this matters more, not less: when execution gets commoditized by models, the last thing that doesn't is judgment about what to build and what to cut. **Shreyas Doshi is blunt that product sense becomes the only durable PM skill.** So stop outsourcing the call to data or to the model. **The taste is the job.**"

### C2. "Taste is objective — train the perceptual apparatus" (line 870) `[KNOWN]`
> "**Graham's point: you don't say 'I don't like it,' you name *which property* is violated.** Karri Saarinen looked at Jira and saw mess where everyone else had normalized it; that intolerance, backed by domain depth, is what built Linear. **Use a huge number of products *deeply*, not casually, until you can diagnose precisely what's wrong.**"

### C3. Paul Graham — "Is There Such a Thing as Good Taste?" `[KNOWN]`
> "The argument the whole 'taste is real, not subjective' claim rests on: **good design has properties you can learn to see, shown by reductio.**"

### C4. "Product strategy is a principled refusal model" / SAY NO RELENTLESSLY (line 873) `[KNOWN]`
> "**Des Traynor's 2013 line still holds: every feature you add costs you forever. Saying no is a product capability, not a scheduling constraint.** Jobs cut Apple from **350 products to 10.** For Skale, the discipline is refusing the ten plausible integrations that would each split your attention and dull the core loop."

> **[Product Strategy Means Saying No]** — *Des Traynor* · "The clearest short case that **refusal is a product capability and every feature is a permanent liability.**"

### C5. DEPTH-OVER-BREADTH / domain-specific judgment — Paul Adams (Intercom CPO) `[KNOWN]`
> **[Product Judgment]** — *Paul Adams (CPO, Intercom)* · `STRONG`
> "...**product judgment is domain-specific and does not transfer.** He went from YouTube and Gmail to B2B with zero judgment in the new domain and rebuilt it only by **talking to 100+ customers for competence and 1,000+ for proficiency (reports and recordings do not count)**, with a three-rates-of-change model for which judgment ages well."

### C6. Shreyas Doshi — five-part product-sense model `[KNOWN]`
> "The five-part model (**empathy, simulation, strategy, taste, creative execution**) for the judgment AI won't commoditize — your defensible layer."

### C7. Cagan / Torres / Norton / Perri — the product-leadership canon `[KNOWN]`
- **Marty Cagan** — "Transformed: Moving to the Product Operating Model": "empowered teams accountable for outcomes vs roadmap-driven feature factories." And "Product vs. Feature Teams": "**give teams problems to solve, not features to build.**"
- **Teresa Torres** — continuous discovery: "Discovery as a weekly operating rhythm: continuous customer interviews, the **opportunity solution tree**, and assumption testing built into daily work, not a phase." OST = "map outcome → opportunities → solutions → testable assumptions."
- **Ken Norton** — "How to Hire a Product Manager": "what separates a real product manager from a project manager with a fancier title."
- **Melissa Perri** — "Escaping the Build Trap": "Why orgs measure **output shipped instead of outcomes achieved.**"

### C8. Tony Fadell — habituation / stay-a-beginner `[KNOWN]`
> "**Habituation blinds us to broken experiences; the job is to stay a beginner and notice what everyone else stopped seeing. 'Look broader, look closer, think younger.'**" Also: "**v1 is opinion-driven not data-driven**" + "the narrative-violation test."

### C9. Rahul Vohra — operationalized PMF `[KNOWN]`
> "turned PMF into a number: '**how would you feel if you could no longer use this?**' Track the **>40% 'very disappointed' segment**, then build only for them. Pair it with Cursor's rule: watch *paid power-user* retention, not MAU."

### C10. "Start from the experience, work backward to the tech" — Jobs WWDC 1997 `[KNOWN]`
> "Jobs at WWDC 1997: **start with the customer experience and work backward to the technology, not the reverse.** The AI-slop trap is the inverse: gradients and rounded corners that are grid-perfect but tonally dead."

---

## D. DELIBERATE POSITIONING (Dunford) + strategy cascade

### D1. April Dunford — the 5-component positioning framework `[KNOWN]`
> **[How to nail your product positioning]** — *April Dunford* · `MUST`
> "The **5-component positioning framework (competitive alternatives, unique capabilities, value, best-fit segment, category)** and **why most products are positioned by default, badly.**"

The five components verbatim: **competitive alternatives · unique capabilities · value · best-fit segment · category.** Verso's whole "counter-position to LangGraph/CrewAI: we don't force the graph" is a Dunford move (positioning against competitive alternatives, not by default).

### D2. Roger Martin — strategy cascade / play-to-win `[KNOWN]`
> "The strategy cascade — **winning aspiration, where to play, how to win** — and the difference between **playing to win and playing not to lose** (why most roadmaps are defensive backlogs)."

### D3. Gibson Biddle — DHM `[KNOWN]`
> "DHM: **delight customers in hard-to-copy, margin-enhancing ways**; GEM; GLEe."

### D4. Ravi Mehta — spiky vs round `[KNOWN]`
> "the '**spiky vs round**' insight: elite leaders are pointy and hire to cover the rest."

### D5. Stewart Butterfield — "we don't sell saddles here" `[KNOWN]`
> "utility curves for prioritization, the owner's delusion, and '**we don't sell saddles here.**'"

### D6. AI-era product timing (Weil, Cat Wu) — build where the model "barely works" `[KNOWN]`
- **Kevin Weil (ex-CPO OpenAI):** "the **10-to-30-percent frontier**: build where the model barely works today so you own the surface the moment it improves."
- **Cat Wu (Head of Product, Claude Code, Anthropic):** "plan in short sprints with deliberate side-quests, **ship the simplest implementation because it is the cheapest to throw away when the model improves, and build scaffolds knowing you will delete them.**" — direct validation of Verso's "additive, delete-on-model-release" scaffold posture.

---

## E. SAY-NO / DEPTH-OVER-BREADTH / SLOP-VS-CRAFT (Design & UX)

### E1. "Slop = generic defaults + zero opinion; craft = a thousand deliberate decisions" (line 1025) `[KNOWN]`
> "The AI slop aesthetic is now recognizable: rounded corners on everything, gradients that don't match the brand, copy edited to be inoffensive instead of clear, layouts that are grid-perfect but tonally flat... **The fix is having the taste to know when AI handed you a mediocre default, not avoiding AI. Every default the tool gives you is a decision you didn't make. Override the ones that matter.**"

### E2. "Taste is built, not innate" / Jiro's Dream (Karri Saarinen) `[KNOWN]`
> "to make great software you first **develop a palate by consuming great work across domains.** Pick three interfaces you envy (Linear, Things, Raycast), and **dissect one interaction each until you can name the exact mechanism.**"

### E3. "Constraints generate taste. Restriction is a tool, not a limit" (line 1037) `[KNOWN]`
> "Teenage Engineering's Jesper Kouthoofd... uses fixed RAL palettes and a tight geometric form language as a generative force. **Linear's redesign collapsed 98 color variables down to 3. Fewer, more opinionated primitives produce more coherence than infinite flexibility. Your design system should remove options, not add them.**"

"Fewer, more opinionated primitives produce more coherence than infinite flexibility" = a near-restatement of Verso's "every primitive additive, no graph-DSL, opinionated core." (98 → 3 collapse is a quotable number.)

---

## F. LEVERAGE-X (the leverage section)

### F1. Naval — four kinds of leverage; code + media are permissionless `[KNOWN]`
> "Naval's point: **the four kinds of leverage are labor, capital, code, and media — and the last two are permissionless.**" + "**specific knowledge plus code plus permissionless media is the modern fortune stack.**"

### F2. Spiky POV — Wes Kao `[KNOWN]`
> "a spiky POV is an **opinionated stance grounded in real expertise, not contrarianism for its own sake.** ... '**Most multi-agent setups are slower than one good loop, here's the latency data**' is a spiky POV. 'AI is exciting' is noise."

`[INFERRED]` Note: the guide *itself* uses "most multi-agent setups are slower than one good loop" as its example spiky POV — this is almost verbatim Verso's "we don't force the graph / ONE clean loop" positioning.

### F3. Personal Monopoly — David Perell `[KNOWN]`
> "own a **unique crossing of topics** instead of competing on a crowded one... The intersection is the moat."

### F4. Sell the outcome not the artifact — Patrick McKenzie `[KNOWN]`
> "**don't call yourself a programmer, sell business outcomes.** ... don't pitch Lancelot as 'a Rust HTTP framework.' Pitch it as 'the thing that makes your API 33x cheaper to serialize.'"

### F5. "Most Human Wins" / "outsource thinking not understanding" `[KNOWN]`
> Packy McCormick: "when AI commoditizes execution, the moat is **taste, judgment, and embodied reputation.**" Karpathy: "**you can outsource your thinking but not your understanding.**"

### F6. Depth-over-breadth in distribution — "Pick one channel and go deep" `[KNOWN]` (line 1178, Distribution section header)
> "**Pick one channel and go deep — most winners used exactly one.**"

---

## G. CROSS-CUTTING NUMBERS WORTH KEEPING (quotable)
- Thorsten Ball: agent core = model + loop + 3 tools in **~315 lines of Go**.
- Anthropic multi-agent: token usage ≈ **80%** of performance variance.
- Code Execution with MCP: **~98%** token reduction.
- Harness-only SWE-bench Pro swing: **50.2% → 55.4%** (Opus 4.5, context+tool orchestration only).
- v0: **64.7% → 93.9%** error-free with four engineering layers.
- Production agents: **~100:1** input:output ratio (→ KV-cache is the cost lever).
- Cursor apply model: **~1,000 tok/s, 13x faster** (decider/executor split).
- Linear redesign: **98 color variables → 3**.
- Jobs: Apple **350 products → 10**.
- Rahul Vohra PMF threshold: **>40% "very disappointed."**
- Dunford positioning: **5 components.** Shreyas product sense: **5 parts.**
- Paul Adams: **100+ customers for competence, 1,000+ for proficiency.**

---

## H. RELATION TO VERSO (one-line verdicts)
- **Mostly validation, not gaps.** The agent-simplicity canon (A1-A18) is the intellectual lineage Verso already implements: <200-line loop (A1), reinforce_objective (A11), KV-cache-stable prefix (A11/B2), captured-failure-as-regression (A10), eval-driven (A15), scaffold-ratchet (A13), durable resume (A13/A17).
- **One additive candidate:** code-over-tools execution mode (A16, ~98% token reduction) — but MCP-adjacent, so it must be an opt-in tool-exposure shim, byte-identical when unused. High bar; flagged with caveats.
- **Overkill to refuse:** multi-agent orchestration as a default (A4/A8 disagree; A6 "every abstraction is a liability"); graph topology (A2 used to *cut* graph). These are NON-GOALS Verso already refuses — keep refusing.
