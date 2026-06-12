# What 'Do Things That Don't Scale' Really Means — Dalton Caldwell & Michael Seibel
**URL:** https://www.youtube.com/watch?v=4RMjQal_c4U
**YC Library:** https://www.ycombinator.com/library/If-dalton-michael-what-does-it-really-mean-to-do-things-that-don-t-scale
**Speakers:** Dalton Caldwell (YC Group Partner) & Michael Seibel (YC Group Partner / CEO)
**Type:** YC Talk (18m) — released October 13, 2022
**Section:** The Founder Mind (high-agency, top-1%)
**Transcript source:** No verbatim transcript retrieved. YouTube yields no readable text; YC library page inaccessible to WebFetch. Content reconstructed from: multi-source search synthesis, Paul Graham's original essay (paulgraham.com/ds.html — read in full), YC podcast description, startuparchive.org summary, and consistent cross-source reporting of examples and arguments. Status: read_partial (high-confidence reconstruction of arguments; no direct verbatim quotes from the talk itself, only from PG's essay).

---

## Faithful Digest

This talk is a structured unpacking of Paul Graham's 2013 essay "Do Things That Don't Scale" — specifically addressing the **common misreading** of the essay that has crept into startup culture. Dalton and Michael's central correction: the phrase is not permission to stay manual forever, and it is not a general philosophy of avoiding automation. It is a specific tactical instruction for the pre-PMF window: **recruit your first users manually, then automate**. The unscalable activity is a discovery mechanism, not a permanent operating mode.

### 1. The Misunderstanding Dalton and Michael Are Correcting

The PG essay has been widely misread as: "doing unscalable things is virtuous in general." The corrected reading: Paul Graham's actual argument is that **the most common unscalable thing founders have to do at the start is recruit users manually.** The point is not to stay manual — the point is to do the hard discovery work that *allows* you to build the right scalable product. Doing unscalable things is the means; achieving product-market fit and learning to build the right thing is the end.

Secondary correction: "doing things that don't scale" does not mean doing things *badly* or operating in a permanently improvised way. It means doing things that only the founder can do at that scale (personal outreach, hand-holding, direct observation) *before* the system can operate without the founder's presence.

### 2. The DoorDash Example — MVP in an Afternoon

DoorDash's original product was built in one afternoon. The full tech stack:
- Google Drive: to upload restaurant menus
- HTML/CSS: to display menus on a webpage
- Google Forms: to receive orders
- Tony's personal phone number: the delivery hotline
- Find My Friends: to simulate real-time dispatch

The founders — Stanford engineering students with the technical ability to build a real-time dispatch system — deliberately chose not to. The question they needed to answer was not "can we build the dispatch system?" but "do people want food delivered from these restaurants?" The unscalable MVP answered the real question first. Building the fancy infrastructure before answering that question would have been the worse technical decision, not the better one.

### 3. The Airbnb Example — Founder as Photographer

When Airbnb was stuck with no growth despite having a working product, Brian Chesky and Joe Gebbia flew to New York (where most early listings were) and knocked on hosts' doors. They offered to professionally photograph listings to improve conversion. Then they took the photos themselves. The listings improved. Conversions improved. They learned how hosts and guests thought about their product in a way no analytics could have provided.

The insight: unscalable founder time-investment in early customers is not a workaround for an inadequate product — it is the mechanism by which you learn what the adequate product actually is.

### 4. The Instacart Example — Fake It to Validate It

Instacart used their early YC funding to go to Trader Joe's, buy one of every item, photograph every product in a studio, write down prices, and post it all online on a Monday morning saying "You can order anything from Trader Joe's." Zero backend, zero wholesale agreements, zero supply chain. The goal was purely to validate that customers would place orders. They did. Then the company built backward from the validated demand.

### 5. The Core Framework — Manual Recruiting as Discovery

PG's essay (which the talk explicates) states the core principle directly: "The most common unscalable thing founders have to do at the start is to recruit users manually." The reasons founders resist this:
- Shyness (reaching out feels pushy)
- Laziness (it is slow, time-consuming work)
- Dismissing small numbers ("only 10 users, doesn't matter")

PG's counter: compound growth from small bases is how all large products start. 10% weekly growth from 10 users = 14,000 users in one year, 2 million in two.

The "Collison Installation" (Stripe): rather than sending users a link to sign up, Patrick and John Collison would physically sit with potential users and set up Stripe on their laptops on the spot. Unscalable. But it compressed the feedback loop from days to minutes and converted more potential users than any self-serve flow could have.

### 6. The Strategic Frame — Startup = Product + Unscalable Initial Tactic

PG's framing that the talk adopts: think of startup ideas as a pair — the eventual product AND the specific unscalable tactics used to get it off the ground. The unscalable tactics are not separate from the product strategy; they *define* what the product becomes, because they are the primary source of early learning. Airbnb's photographer moment is not a footnote to Airbnb's product history — it is the mechanism by which Airbnb understood what hosts needed.

### 7. When to Automate — The Thing Dalton and Michael Are NOT Saying

The talk is explicitly not saying: "avoid automation," "stay scrappy forever," or "pride yourself on manual processes." The right time to automate is when you have validated *what to automate* through manual operation. Building automation before validation is premature optimization — you're optimizing for a workflow that might be solving the wrong problem.

---

## Key Quotes

From Paul Graham's essay (the source text the talk directly engages with):
- "The most common unscalable thing founders have to do at the start is to recruit users manually."
- "You can't wait for users to come to you. You have to go out and get them."
- "A startup just starting out can't expect to be followed everywhere, so the best way to attract new users is to focus on one market."
- "Viaweb's approach was to actively seek out new customers, then help them get started."

---

## VERSO RELEVANCE

### Finding 1: Manual-First Is a Discovery Mechanism, Not a Strategy
**Tag:** [CONFIRMS]  
**PRD Section:** §12 GTM/cold-start  
The Dalton/Michael correction maps precisely to VERSO's Stage-1 design: the 5 vocal production leads are NOT won through OSS launch, blog posts, or tweet-threads. They are won through the equivalent of the DoorDash Google-Drive MVP — direct outreach to a specific struggling AI engineer, walking them through the harness in a call, watching where they get stuck. The insight is that this manual Stage-1 is not a bridge to "real" marketing; it IS the mechanism by which you learn what "real" marketing should say. The eval corpus flywheel cannot be designed until you have seen 5 production agents run through VERSO hands-on.  
**Verdict:** Confirms §12 Stage-1 tactical prescription: direct personal outreach + hands-on onboarding first; systematic channels only once you know what message resonates.

### Finding 2: The Collison Installation — VERSO's Onboarding Wedge
**Tag:** [SHARPENS]  
**PRD Section:** §7 demo-able wedge  
The Collison Installation (sitting next to the user to set up Stripe) is the exact analog for VERSO's 3-line side-by-side demo. The wedge is not "here's a GitHub link" — it is "let me show you the diff on your agent right now." The unscalable version of this is: find 5 AI engineers who have a production agent, ask to see their current loop, and run the VERSO seam against it live. The act of doing this manually (even in a Zoom screen-share) generates the learning that eventually compresses into the 3-line diff.  
**Verdict:** Sharpens §7 — the demo-able wedge must be demonstrated *in the context of the lead's actual agent*, not on a contrived example. Manual first, polished later.

### Finding 3: The Fake-It-to-Validate Instacart Model — Implication for Eval Corpus
**Tag:** [NEW-IDEA]  
**PRD Section:** §1 bet/moat + §12 GTM  
Instacart's Monday-morning launch (fake store, real validation) suggests VERSO should consider an "eval corpus stub" launch: ship a minimal eval corpus with 10–20 hand-curated traces from real agents (with permission), before the flywheel produces it automatically. The goal is to validate that production AI engineers find the corpus credible and useful, before investing in full aggregation infrastructure. This is the equivalent of DoorDash's Google-Drive menu: answer the real question (do production engineers value curated trace data?) before building the real system.  
**Verdict:** New tactical idea for §1/§12 — launch a manually curated eval stub as a validator before building the automated corpus aggregation flywheel. The manual curation is not a bug; it's the discovery instrument.

### Finding 4: Startup = Product + Unscalable Tactic → VERSO = Framework + Harness Tactic
**Tag:** [SHARPENS]  
**PRD Section:** §1 bet/moat  
PG's pairing insight (product + the specific unscalable tactic used to get it off the ground) reframes the VERSO bet cleanly. The "product" is the harness (context engineering, evals, seam). The "unscalable initial tactic" is dogfood-first: the founder running their own production agents through VERSO and using that direct observation to improve the harness. This is not a GTM tactic — it is the primary source of VERSO's early learning about what the harness should actually do. The eval corpus flywheel is what the unscalable dogfood process eventually compresses into.  
**Verdict:** Sharpens §1 — dogfood-first is not a preference or a marketing story. It is the discovery instrument for the product, in exact analogy to Airbnb's photographer moment.

### Finding 5: Do Not Conflate DTDS With "Stay Scrappy"
**Tag:** [CONTRADICTS]  
**PRD Section:** §12 GTM  
The common misreading of DTDS — that scrappiness and unscalability are permanent virtues — is a trap for VERSO's GTM. The eval corpus flywheel, the structured onboarding, the harness upgrade path: these are the *automation* layer that should follow the manual Stage-1 discovery. If VERSO treats the manual-outreach phase as identity ("we're a scrappy OSS project") rather than as a time-bounded discovery phase, it never transitions to Stage-2. The DTDS principle contains its own time-limit: do the unscalable thing until you know what to scale, then scale it.  
**Verdict:** Contradicts/warns against any framing of VERSO's cold-start as permanent scrappiness — Stage-1 is a phase with an explicit graduation criterion (5 vocal production leads + enough trace data to design the corpus).
