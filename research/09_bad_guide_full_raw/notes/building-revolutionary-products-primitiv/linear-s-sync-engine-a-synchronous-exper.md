# Linear's sync engine: a synchronous experience with async data

**Speaker:** Tuomas Artman (CTO, Linear)
**Format:** Talk (26 min) — also a full podcast episode on localfirst.fm (#15)
**Video:** https://www.youtube.com/watch?v=bnOpm3a1fRE
**Transcript source:** Full transcript at https://www.localfirst.fm/15/transcript (localfirst.fm podcast episode #15, same speaker, same material)
**Status:** READ FULL — complete transcript obtained from localfirst.fm

---

## What the speaker actually argues

### 1. Build the primitive before the product — half a year before

Linear's first ticket (LIN1) was implementing a command menu. The sync engine and the full interaction stack came before issue tracking features. Tuomas describes this as a deliberate choice, not a detour:

> "we spent like half a year building out, the sync stack and the command menu and all this, all this stuff. And I think that was, that was a great success."

The primitive is the product. Features are cheap once the primitive exists; without the primitive, every feature carries hidden distributed systems debt.

### 2. How the sync engine works: annotation-based property tracking

The sync engine uses a declarative approach where developers annotate properties that need synchronization. The engine picks up changes automatically and propagates them:

> "you would annotate some properties saying, like, these need to be transferred to all the players in that room, and it would automatically pick up on those and then send them over whenever they changed"

Properties change locally first; the system handles propagation to server and other clients. Developers write front-end code against in-memory objects, as if networking doesn't exist.

> "you're effectively just building the front end. You have, data in memory, you've got data objects, which you render on screen. Then you modify those and that's it. Your feature is done."

### 3. The RPC problem: why traditional architectures create hidden complexity

When a user modifies properties and sends an RPC call *while simultaneously* receiving WebSocket updates about concurrent changes from other users, systems face unresolvable ambiguity. Multiple backend servers write to databases asynchronously, creating race conditions that cannot be resolved locally:

> "you really don't know what to do. Like, you can't rely just on that RPC call coming back...you don't know if all the values in there are up to date."

This forces developers to incrementally rebuild sync-engine-like functionality through painful debugging cycles — the "boiling frog" path.

### 4. Developer experience is the killer feature, not performance

Surprisingly, engineering velocity — not UI responsiveness — became the sync engine's most important property:

> "what we like even more was that engineers would be able to just ship features much, much faster without having to think about a vast, area of, A functionality"

Engineers avoid handling: networking complexity, error handling for distributed scenarios, dual code paths (local vs. remote), and waiting for server responses. The sync engine eliminates entire categories of bugs by construction.

### 5. Offline-first by accident, not by design — and the limits of offline

At Groupon, offline capabilities emerged from a Wi-Fi failure: the system buffered requests locally and synced between devices before reaching the internet. But this revealed a boundary case: a restaurant train across the Rocky Mountains charged customers for two days offline, then replayed all transactions upon reconnecting.

> "we probably told them to never do that again. and, it wasn't really meant for, meant for that"

The sync engine provides offline *tolerance*, not offline *arbitrariness*. There's a scope boundary.

### 6. Linear's three design priorities before writing any features

Three invariants established before product features:
1. **Command menu + keyboard shortcuts** — power-user experience (inspired by Superhuman)
2. **Native application feel via web technologies** — avoid platform fragmentation of true native apps
3. **Real-time synchronization** — eliminate page refreshes

> "the application should feel like an application, like a native application...let's try to make an application with web technologies that feels like a native application."

### 7. Narrow initial scope + grow with customers

Linear targeted 2-4 person YC-incubated startups with only basic issue tracking. This was not a limitation — it was a deliberate strategy to achieve high quality without premature feature breadth. The strategy was to grow *with* customers across funding stages (seed → Series A → Series B), incrementally adding complexity.

### 8. Preemptive infrastructure as a philosophy

Rather than scaling reactively (as Uber did during hypergrowth, creating distributed system complexity that compounds silently until production failures):

> "our take on infrastructure and the backend always has been to sort of preemptively build everything so that, we're prepared for the growth."

This avoids the "boiling frog" scenario.

### 9. The sync engine as competitive moat

In crowded markets, building features faster is insufficient if every feature carries distributed systems risk. The sync engine removes entire categories of bugs and performance footguns, allowing the team to focus on user experience differentiation:

> "if you're building, something that has, a lot of information or building a search engine...obviously not, like, you need to be able to have that data locally...But for anything that resembles an application...this model just works absolutely beautifully."

Tuomas states he would never work outside this paradigm again.

---

## VERSO RELEVANCE

**Note:** Linear's sync engine is a product primitive for a project management tool, not an agent framework. Its relevance to VERSO is architectural/methodological — about *what kind of primitive to build* and *when* — not about agent loop mechanics.

**[CONFIRMS §1 bet / §12 positioning — "build the primitive"]** Linear's half-year investment in sync engine before features is the canonical "build the primitive, not the product" story. The parallel for VERSO: the 200-line loop + context engineering + evals-first stack *is* the primitive. Features (HITL, durable, multi-agent) are cheap once the primitive is solid. No-overkill verdict: strong rhetorical support for §1 bet — the "Linear before Linear" analogy.

**[SHARPENS §5.1 loop / §5.2 context]** The sync engine's design insight — "developers write against in-memory objects as if networking doesn't exist" — is the UX analogue for VERSO's context layer. The goal in both cases: eliminate an entire class of complexity from the user's mental model. For VERSO users: "write Python tools as if context management doesn't exist." The harness handles it. No-overkill verdict: this is a strong framing for the developer experience pitch.

**[SHARPENS §4 seam]** The sync engine's "offline tolerance, not offline arbitrariness" distinction maps directly to VERSO's tactical↔durable seam. Tactical agents have a scope boundary; durable agents extend it systematically (event-sourcing, checkpoint/resume). The distinction is not cosmetic — it has consequences (Rocky Mountains transaction replay). No-overkill verdict: use this as a concrete illustration of why the seam exists.

**[NEW-IDEA §5.2 context / §5.3 tools]** The RPC race-condition problem (you don't know if values are up to date when the callback returns) has an agent-loop analogue: tool return values may be stale relative to concurrent context mutations. VERSO's append-only history + observation-masking handles this, but the framing "you really don't know what to do" is a sharp way to explain *why* you need a consistent history model. No-overkill verdict: borrow this framing for the context engineering rationale.

**[CONFIRMS §12 positioning — narrow scope]** Linear's deliberate targeting of 2-4 person YC startups before expanding confirms VERSO's non-goals (§2): don't try to be everything to everyone. Build for the developer who writes Python and runs agents, then grow. No-overkill verdict: confirms positioning discipline.
