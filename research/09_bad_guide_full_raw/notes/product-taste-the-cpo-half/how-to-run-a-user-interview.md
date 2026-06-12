# How to Run a User Interview

**Speaker:** Emmett Shear (co-founder, Justin.tv / Twitch; YC partner)
**Source:** YC / How to Start a Startup 2014, Lecture 16
**URL:** https://www.youtube.com/watch?v=qAws7eXItMk
**Duration:** ~46 min
**Transcript source:** 31-quote compilation via Medium (Rajen Sanghvi) + two additional Medium notes + Awesound episode page; annotated Genius transcript blocked. Content assessed as read_partial (quotes + summaries, not full transcript flow).

---

## Core Argument

User interviews are the highest-ROI activity for early-stage founders, but most do them wrong: they show users the product (instead of learning what's already in users' heads), they talk to whoever is convenient (instead of who they need), and they ask opinion questions (instead of behavior questions). Getting this right is a skill that requires deliberate methodology.

---

## Key Frameworks

### 1. Who You Interview Is as Important as What You Ask

"Who you talk to is just as important as what questions you ask and what you pull away from it."

The first question for almost any startup: "Who is my user and where am I going to find them?" There is no recipe — "it comes down to think really hard and use your judgment." The selection decision is judgment-intensive and cannot be delegated to whoever is available.

Corollary: Don't talk only to current users. Most of your potential market is non-users:
- "This is true for most new products. The majority of people you're competing with are non-users."
- "What they say is the thing that blocks you from expanding the size of your market with your features."

### 2. The Horseless Carriage Effect

"Users think they know what they want, but you get the horseless carriage effect where you're getting asked for a faster horse."

Direct feature requests are usually the wrong unit of analysis. The job is to understand the underlying problem, not to implement the stated solution. Feature requests surface the symptom; interviews reveal the root cause.

### 3. Behavior Over Opinions

Opinion questions: what do you want? what would you pay? what's wrong with this?  
Behavior questions: what did you actually do last time? how do you handle this now? what happened when...?

Opinions are cheap (people are polite). Behavior reveals real pain. "Those kinds of questions will distract us from solving the problem because we're getting answers based on the assumption that people know what they want."

### 4. Don't Show Them Your Product

"The most common mistakes are showing people your product — don't show them your product, it's sort of like telling them about a feature."

"You want to learn about what's already in their heads. You want to avoid putting things there."

Showing the product contaminates the signal. Users shift from describing their real experience to evaluating your prototype — which invites polite, useless feedback.

### 5. The Money Test

Willingness to pay is the strongest validation signal:
- "Sales is this cure all for this problem. Get people to give you their credit card and I guarantee you they're actually interested."
- "It's one of the most validating things you can do for a product is go out there and get them to commit to pay you up front."
- Even $5 matters. If users won't pay $5, they lack genuine enthusiasm.

Corollary: "when it comes to money, it appears, they are not that excited about your product anymore" — distinguishing authentic demand from courtesy responses.

### 6. Detective Mode: The Silence Technique

"The most interesting things you learn in an interview come from the: 'interesting', 'tell me more.'"

"The instant they say something you don't expect or already know, you should drop into detective mode."

"People don't like silence, so they'll keep talking to fill the void."

The technique: let silence sit after unexpected answers. The interviewer's job is to follow the unexpected, not to cover the checklist.

### 7. Record Everything

"Recording interviews is like magic. a) It stops you from taking notes in the middle and b) you can play that recording for people."

The dual benefit: note-taking during the interview breaks rapport and divides attention; recordings let the team hear the actual user voice, not a paraphrase.

### 8. Sample Size: 6-8 Per Segment

Interview 6-8 people per distinct user segment to identify genuine patterns. More per segment yields diminishing returns; fewer misses patterns.

### 9. Negative News Is the Point

"That's actually one of the most disappointing things about doing user interviews and user feedback, which is why I think people don't do it. You're going to get negative news about your favorite pet feature most of the time."

Most teams avoid user interviews *because* they expect bad news. This is exactly backwards — bad news at interview stage is free; bad news post-launch is expensive.

### 10. The Market Shifts Over Time

"The pool of people you care about is going to shift over time."

"The crucial people to get your product started for the first 6 months are not who will be using it 3 years later."

Early adopter users and late-majority users are different people with different problems. The interview target must be re-evaluated as the product matures.

### 11. Avoid Convenient Targets

"The other mistake I think people make is talking to who's available rather than talking to who they need to talk to."

"If you just talk to who's easy to talk to, you're not really getting the best data."

Family, close friends, and existing fans provide systematically biased feedback.

---

## Key Quotes (verbatim from Shear)

1. "Who you talk to is just as important as what questions you ask and what you pull away from it."
2. "Who is my user and where am I going to find them?"
3. "Users think they know what they want, but you get the horseless carriage effect where you're getting asked for a faster horse."
4. "The most common mistakes are showing people your product — don't show them your product."
5. "You want to learn about what's already in their heads. You want to avoid putting things there."
6. "Recording interviews is like magic."
7. "The instant they say something you don't expect or already know, you should drop into detective mode."
8. "People don't like silence, so they'll keep talking to fill the void."
9. "Sales is this cure all for this problem. Get people to give you their credit card and I guarantee you they're actually interested."
10. "You're going to get negative news about your favorite pet feature most of the time."
11. "The majority of people you're competing with are non-users."
12. "The crucial people to get your product started for the first 6 months are not who will be using it 3 years later."

---

## VERSO RELEVANCE

### §12 GTM / Cold-Start

**[SHARPENS]** The "non-users are the most important signal" point is a direct sharpener for Verso's cold-start strategy. At Stage-1, the natural gravitational pull is toward people already experimenting with LangChain/LangGraph — but Shear argues these are the *existing user* segment. The critical signal comes from the structurally-aware senior engineer who has *not yet committed to a harness* (non-user). Verso should be explicitly interviewing people who are currently doing nothing — the "struggling moment" persona — not just people who've already chosen a competitor.

**[NEW-IDEA — gtm_distribution]** The 6-8-per-segment rule gives a concrete cold-start research budget: interview 6-8 non-users (senior/AI engineers not yet using a harness) before drafting any positioning copy. This is cheap, high-signal, and currently unscheduled in the Verso GTM plan.

### §7 Demo-able Wedge / Product Taste

**[SHARPENS]** "Don't show them your product" applies directly to how Verso's demo is sequenced. The demo must begin with the *problem being lived* (agent failing silently, forced rewrite, no observability) before showing the product. Leading with the inspect() call or the promote flag is showing the product; leading with the failure mode is the Shear-compliant approach.

**[CONFIRMS]** The behavior-not-opinions distinction reinforces that the wedge-is-epistemic principle has a specific interviewing mechanic: ask about the last time an agent failed in production — what did they actually do, step by step — not "would you want resumability?" The former reveals the real pain; the latter is a leading opinion question.

### §2 Non-Goals / Principled Refusal

**[NEW-IDEA — product_taste]** The "market shifts over time" observation means Verso's non-user persona (the structurally-aware senior who hasn't yet committed to a harness) has a time-limited window. The early-adopter cohort that starts production agents in 2024-2025 is not the same cohort that will be starting them in 2027. The interview program needs to track this shift — non-goals and persona definitions should be reviewed at 6-month intervals, not locked in forever.

### Founder-OS

**[NEW-IDEA — founder_os]** The "detective mode" technique — drop into the unexpected immediately, follow silence rather than the checklist — is the exact epistemic posture the "explain without AI" and "intellectual honesty" register principles require in user conversations. Verso's user research operating principle: *the checklist is a backstop, not the interview*. The most important findings always come from the unexpected answer followed by silence.

### Verdict per finding

- Non-users as primary interview target → explicit operational shift in cold-start research plan. Ship.
- 6-8-per-segment budget → concrete pre-positioning research task. NEW-IDEA, ship.
- Problem-first demo sequencing → confirmed from Perri as well; double-confirmed. Ship.
- Behavior-not-opinions interview mechanic → specific wording for Verso persona research. Ship.
- Market-shift / persona-review cadence → 6-month non-goals review. NEW-IDEA, ship.
- Detective-mode epistemic posture → founder-OS operating principle for user conversations. Ship.
