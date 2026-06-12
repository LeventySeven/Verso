# Aggregation Theory

**Source:** Ben Thompson (Stratechery)  
**URL:** https://stratechery.com/2015/aggregation-theory/  
**Fetched:** 2026-06-12  
**Status:** read_full  
**Themes:** strategy

---

## Full Digest

Ben Thompson's foundational 2015 essay establishing the structural logic of internet-era winner-take-all dynamics. The theory derives from Christensen's Conservation of Attractive Profits and applies it to post-Internet value chain dynamics.

### Core Mechanism

The pre-Internet value chain structure: **suppliers → distributors → consumers**. Profits lived with whoever could integrate backwards toward supply because distribution was scarce (physical delivery, broadcast access, shelf space, taxi medallions). Controlling distribution meant controlling the supplier relationship, which meant controlling consumers by proxy.

> "In the pre-Internet era the latter depended on controlling distribution... Note how the distributors in all of these industries integrated backwards into supply: there have always been far more users/consumers than suppliers, which means that in a world where transactions are costly owning the supplier relationship provides significantly more leverage."

The Internet's two structural disruptions:

1. **Distribution of digital goods became free** — the pre-Internet distributor's leverage evaporated.
2. **Transaction costs dropped to zero** — a distributor can now integrate *forward* with consumers at global scale instead of backwards into supply.

The result:

> "No longer do distributors compete based upon exclusive supplier relationships, with consumers/users an afterthought. Instead, suppliers can be commoditized leaving consumers/users as a first order priority. By extension, this means that the most important factor determining success is the user experience: the best distributors/aggregators/market-makers win by providing the best experience, which earns them the most consumers/users, which attracts the most suppliers, which enhances the user experience in a virtuous cycle."

### The Aggregator Pattern (Generalized)

For each major internet company, the move is identical:
- **Modularize** the incumbent's integrated supply (atomize pages, rooms, cars, attention)
- **Integrate** the consumer/user side with data + experience

Examples:
- **Google:** modularized individual pages from publishers → integrated search results + user profile data
- **Facebook:** modularized ad inventory from publishers → integrated News Feed + profile data
- **Amazon:** modularized distribution from book publishers → integrated customer data + payment
- **Netflix:** modularized broadcast schedule from networks → integrated library + subscriber management
- **Uber:** modularized fleet management from taxi medallion owners → integrated dispatch + customer management
- **Airbnb:** modularized vacant rooms from hotel brand trust → integrated property management + customer management

### Winner-Take-All Logic

> "In all of these examples there are strong winner-take-all effects. All of the examples I listed are not only capable of serving all consumers/users, but they also become better services the more consumers/users they serve — and they are all capable of serving every consumer/user on earth."

This is the positive feedback: more users → better service → more suppliers → better user experience → more users. The platform becomes literally better the larger it gets, with no physical constraint on global reach.

### The Diagnostic Framework

Thompson's forward-looking test:

> "What is the critical differentiator for incumbents, and can some aspect of that differentiator be digitized? If that differentiator is digitized, competition shifts to the user experience, which gives a significant advantage to new entrants built around the proper incentives."

> "I suspect that nearly every industry will belatedly discover it has a critical function that can be digitized and commodified, precipitating this shift."

---

## VERSO RELEVANCE

### Finding 1: The agent framework space has the structure of a pre-aggregation market
[NEW-IDEA §12]

Aggregation Theory provides a diagnostic for Verso's competitive position. Current agent frameworks (LangChain, LangGraph, AutoGen, CrewAI) are **supply-side integrators** — they compete on feature breadth and framework integrations (tools, connectors, models), mirroring pre-Internet distributors who integrated backwards into supply. They do not own the developer/user relationship; developers use them instrumentally and switch freely.

The aggregation move in developer tooling is: **commoditize the model/tool/connector layer, own the developer workflow experience**. This is what GitHub Copilot did to code editors and what Cursor is doing to IDEs. The question for Verso: can the *developer experience* of building and running agents become the sticky layer, with models/tools/MCP as commoditized supply?

Verso's "no graph required, native Python @tool, one flag to durable" is a UX-first positioning — it wins by being a better experience, not by having more integrations. This is structurally correct per Aggregation Theory. The risk: if Verso is too framework-like and not workflow-like, it stays on the supply-side treadmill.

**Verdict:** sharpen §12 GTM — explicitly frame Verso as the *experience aggregator* in the agent-building workflow, not another integration hub.

### Finding 2: MCP as the modularization event
[SHARPENS §5.3]

The Aggregation Theory lens makes explicit what Verso's MCP positioning already implies but doesn't say loudly: **MCP is the modularization event for the tool/connector layer**. Just as Google modularized individual web pages from publishers, MCP modularizes tool integrations from the frameworks that used to bundle them. If MCP becomes the standard, then competitive moat via "we have more connectors" collapses. The value shifts entirely to the agent experience and loop quality.

This validates Verso's hard design choice: native @tool Python is the first-class path; MCP is a demoted opt-in adapter. Verso is not betting on being the MCP aggregator — it is betting on being the developer experience that sits on top of a commoditized MCP layer.

**Verdict:** confirm §5.3 positioning — the Aggregation Theory logic independently validates "native Python @tool first, MCP as adapter."

### Finding 3: The virtuous cycle is possible but requires a demand-side first move
[NEW-IDEA §12]

For Verso to be an aggregator rather than a connector/integration hub, it must build a developer relationship — feedback loops, eval data, usage telemetry — that improves the product for all users as more developers use it. This is not automatic. The eval infrastructure (§5.5) is the seed of this: define_outcome + judge panels produce signal that Verso can use to improve defaults, prompt templates, and guidance. No other framework has this feedback loop natively.

This is a specific, actionable GTM asymmetry: **Verso's eval layer is its demand-side aggregation mechanism**. Other frameworks can copy the loop; they cannot easily copy accumulated eval signal and community-contributed outcome definitions.

**Verdict:** adopt-now as a positioning insight — surface in §12 that eval infrastructure is the aggregation flywheel.

### Finding 4: "Proper incentives" as a moat
[SHARPENS §1]

> "Competition shifts to the user experience, which gives a significant advantage to new entrants built around the proper incentives"

The "proper incentives" for Verso as a developer tool: align incentives with the developer who wants *correct, maintainable, debuggable* agents — not with the framework vendor who wants more lock-in via abstractions. This is the "no overkill, no bullshit, simplicity" design principle translated into competitive strategy. Frameworks that optimize for feature density (to look impressive in demos/docs) are misaligned with the developer's actual incentive (shipping reliable production agents).

**Verdict:** confirm §1 — the "proper incentives" principle is structurally load-bearing, not just a values statement.

---

## One-Line Verdicts Summary

| Finding | Verdict |
|---|---|
| Verso should position as experience aggregator, not integration hub | sharpen §12 |
| MCP as modularization event validates native @tool first | confirm §5.3 |
| Eval layer is the aggregation flywheel / demand-side moat | adopt-now §12 |
| "Proper incentives" alignment = durable structural advantage | confirm §1 |
