# Good News: AI Will Eat Application Software

**Source:** https://a16z.com/good-news-ai-will-eat-application-software/
**Authors:** Alex Immerman & Santiago Rodriguez (a16z)
**Date:** March 2, 2026
**Format:** Essay (~12 min read)
**Themes:** strategy, loop_harness (oblique)

---

## Full Digest

The article opens against the "SaaSpocalypse" narrative — a 30% drop in public software ETFs since early 2026, driven by fear that AI will commoditize software. Immerman and Rodriguez argue this is a misreading: **code was never where software value lived**. The market is treating software companies as though they are code factories, but if raw code were the value, open-source or cheap offshore labor would have already destroyed them years ago.

The bear case gets four flavors: (1) foundation model labs eat the entire application stack; (2) enterprises "vibe code" their own internal replacements; (3) incumbents use AI to sprawl into each other's markets; (4) "single-person billion-dollar company" upstarts undercut on price. The authors acknowledge AI increases competition, but argue it also dramatically expands what software companies can do and how large their total addressable markets can become.

### The Moats Argument

The article applies Hamilton Helmer's *Seven Powers* framework to the AI transition:

**Switching costs:** the ONE moat genuinely weakened. AI-assisted migration reduces lock-in friction. But the authors frame this positively: "companies will have to earn their customers' loyalty instead of relying just on vendor lock-in." Result is better products, faster innovation, healthier competition — not a collapse of profit pools.

**Network effects:** survive and potentially strengthen. Examples: Salesforce ecosystem (third-party apps, admin experts); Figma (designers, then PMs, engineers, marketers all collaborating in one space); Harvey and Hebbia as finance/legal collaboration networks where "the more people and agents who use these platforms, the more valuable the platforms become."

**Scale:** less historically important for software than for cloud/industrial, but AI may amplify scale advantages where compute costs matter. Stripe example: compliance infrastructure amortized across all clients, payment routing optimization improves with volume.

**Brand:** "no one got fired for buying IBM" remains structural. If anything, brand strengthens when the market gets crowded with AI upstarts and enterprises need a reliability signal. Caveat: agent-led procurement may optimize on price, but humans who answer for decisions still bias toward trusted brands.

**Cornered resources:** proprietary data matters more when AI can extract far more value from high-quality data than before. Examples: Bloomberg live market data, Abridge clinical conversations, OpenEvidence medical library, VLex legal database.

**Process power ("process engineering"):** named by George Sivulka of Hebbia. Application software is a "stored process" — it encodes workflows that calcify over years into organizational DNA. Quote: "If Harvey deeply understands how a particular law firm structures its work—the templates, the review processes, the institutional preferences, the way a specific partner likes her memos done—there is simply no way a new entrant can replicate that overnight, even with the cost of code being zero." This moat COMPOUNDS as software moves from system-of-record to system-of-action.

### Counterpositioning as Startup Opening

The authors identify counterpositioning as the structural advantage for AI-native entrants:

> "The 'agent' model of doing work and replacing tasks is certainly going to create some counterposition opportunities for new startups to challenge incumbents."

The canonical example is **per-outcome pricing** vs. per-seat pricing. Decagon prices customer support per conversation handled, eventually per resolution achieved. An incumbent like Zendesk cannot make this move without cannibalizing its own seat revenue — exactly as Blockbuster couldn't match Netflix's subscription model or PeopleSoft couldn't match Workday's SaaS model.

Quote: "Companies that start with the new business model don't face that dilemma, and it's the core reason why platform shifts so reliably produce new winners."

Importantly, the authors note that **total end-state pricing power does not necessarily decrease** — customers now have a *choice of business models*, and the better one wins. AI-native companies that price on outcomes typically end up in a much larger addressable market than the seat-based predecessor.

### The Great Bifurcation

The article predicts "software splits in two":

- **Vulnerable:** thin frontend wrappers around commodity functionality; archaic systems-of-record that raise prices without delivering value; seat-based models facing AI-native competitors.
- **Safe/growing:** companies with genuine network effects, cornered data, deep process engineering, or strong brand.

The overall prognosis: "We'll be looking at a much bigger software industry that provides much more value to its customers." The world remains "short software" — AI doesn't destroy demand, it expands it. Quote from colleague Anish Acharya: "the world remains 'short software.'"

---

## Verbatim Quotes (Load-Bearing)

1. "Code is never where the value has lived: if code is where the value was, these companies would have never gotten so big in the first place."

2. "When companies have to earn their customers' loyalty instead of relying just on vendor lock-in, the result is better products, faster innovation, and a healthier competitive ecosystem."

3. "Harvey's orchestration layer—the scaffolding that routes model output through specific professional workflows—compound in value. The challenging aspect was never raw intelligence; it was understanding what to do with it."

4. "Companies that start with the new business model don't face that dilemma, and it's the core reason why platform shifts so reliably produce new winners."

5. "Decagon prices its customer support product per conversation handled, not per agent seat, and will eventually price per resolution achieved: that's fundamentally a better alignment of incentives between vendor and buyer."

6. "An incumbent like Zendesk can't easily make that same move without cannibalizing its own seat-based revenue."

7. "The world remains 'short software.' We are nowhere near saturating the world's demand for high-quality software. And as code becomes cheaper, we should just expect to see the market demand more."

8. "AI isn't going to destroy the software industry; it's going to split it into two parts."

---

## VERSO RELEVANCE

### Finding 1: Counterpositioning via per-outcome pricing is the structural moat for AI-native frameworks
**Tag:** [NEW-IDEA §12 positioning/GTM]

The article makes the case that per-outcome pricing is the move incumbents *cannot copy* without cannibalization. Verso is in an analogous position relative to seat-based developer tool incumbents: LangChain/LangGraph extracts value through cloud platform lock-in (LangSmith commercial, LangGraph Platform). If Verso prices on outcomes (runs completed, tokens saved through caching discipline, eval pass-rate SLA) rather than seats or MAUs, it structurally cannot be replicated by an incumbent without destroying their own margins.

**Verdict:** lock-interface-defer — the pricing model insight is GTM-layer, not architecture. But architecture choices (context engineering, eval harness, checkpoint/resume) directly enable outcome pricing because they make outcomes measurable. Design the harness to emit the metrics outcome pricing requires.

---

### Finding 2: "Process engineering" as the compounding moat — Orchestration layer compounds with model quality
**Tag:** [SHARPENS §4 architecture / §6.1 durable runtime]

The Harvey framing is directly applicable to Verso's durable layer. Quote: "Harvey's orchestration layer—the scaffolding that routes model output through specific professional workflows—compounds in value. The challenging aspect was never raw intelligence; it was understanding what to do with it."

This is a precise analogy for why Verso should NOT chase model-layer differentiation but instead invest in the orchestration harness (durable checkpoint/resume, context engineering, eval hooks). The orchestration layer accumulates organizational workflow intelligence; the model is fungible. This SHARPENS the "build for the durable layer" invariant — it's not just architectural preference, it's where the compound moat actually lives.

**Verdict:** sharpen — reinforce in §4 that the orchestration layer is where Verso's value compounds, not the model call.

---

### Finding 3: The "short software" thesis — AI expands demand, not just competition
**Tag:** [CONFIRMS §1 the bet / NEW framing for §12]

The article's core thesis is that AI makes software demand grow, not shrink. Corollary for Verso: the market for reliable agent harnesses is NOT zero-sum with LangChain/LangGraph. Demand for multiple reliable frameworks is expanding. The "short software" framing reframes Verso's GTM from "why Verso vs LangChain" to "here's new demand that neither incumbents nor Verso yet serves."

**Verdict:** confirm + adopt-now in §12 positioning — frame Verso as expanding supply for an expanding market, not as a LangChain replacement.

---

### Finding 4: Network effects in agent platforms (data/collaboration networks)
**Tag:** [NEW-IDEA §6.2 multi-agent]

The Harvey/Hebbia and EliseAI examples show how agent platforms develop network effects through multi-sided networks: agents on one side, human professionals on the other, data accumulating as the moat. The insight for Verso: if Verso's durable runtime (§6.1) accumulates per-workflow checkpoint data, that data can be surfaced as eval signal that improves future runs — a lightweight data network effect internal to a single deployment. This is NOT currently in the known harvest.

**Verdict:** lock-interface-defer — flag for §6.1 durable runtime: checkpoint data should be structured to enable eval feedback loops, not just recovery.
