# Why One of OpenAI's Top Researchers Walked Away

**Source:** Core Memory podcast, EP 53 — Jerry Tworek
**URL:** https://www.youtube.com/watch?v=VaCq4u5c78U (YouTube mirror) | https://www.corememory.com/p/he-left-openai-jerry-tworek (primary)
**Duration:** ~1h 16m
**Speaker:** Jerry Tworek, former VP of Reinforcement Learning at OpenAI (7 years, 2019–2026)
**Key works:** Codex, ChatGPT, Q*, Strawberry, o1, o3

---

## Transcript Status

**Partial / reconstructed** — the Core Memory podcast page is paywalled (subscriber-only for full audio at time of research). Substantive content was obtained from:
1. The-Decoder.com article reporting on the episode: https://the-decoder.com/openais-former-top-researcher-says-google-caught-up-because-openai-stumbled/
2. Subsequent The-Decoder.com article on Core Automation launch: https://the-decoder.com/ex-openai-researcher-jerry-tworek-launches-core-automation-to-build-the-most-automated-ai-lab-in-the-world/
3. Redpoint Ventures video page (video/embed, not transcript): https://www.redpoint.com/content-hub/video/ex-openai-researcher-on-why-he-left-his-honest-agi-timeline-the-limits-of-scaling-rl/

Full verbatim transcript was NOT accessible. Notes below reconstruct the argument from secondary reporting.

---

## Speaker Background

Jerry Tworek joined OpenAI in 2019 when the lab had ~30 employees. He was VP of Reinforcement Learning and lead on the RL team behind Codex (the earliest code model), ChatGPT's underlying RLHF work, and the reasoning model line (Q* → Strawberry → o1 → o3). He departed January 2026 and subsequently founded Core Automation.

---

## Core Arguments

### 1. RL Scaling Hit a Real Wall

Tworek's AGI timeline shifted significantly after discovering that "scaling RL, the training method behind reasoning models, didn't turn out as mighty as he originally believed." He initially expected post-training RL (the technique behind o1/o3) would be a direct path to AGI. It produced major gains but revealed a ceiling: scaling compute during inference and training on RL signal alone is not sufficient. Additional building blocks are required.

This is a rare insider admission — the RL lead on o1/o3 saying the paradigm that produced those models is not enough on its own.

### 2. Structural Conservatism at Scale: Why Big Labs Bet Safe

Tworek argues that "all the major AI labs are doing the same thing: optimizing the same Transformer technology with products that barely differ from each other." The causes he identifies are structural:

- **Rigid org charts and siloed teams** reduce cross-pollination and experimental surface area
- **High compensation reduces risk appetite** — researchers chasing short-term wins instead of risky bets
- **Commercial metrics (user growth, revenue) dominate** — "risky fundamental research is no longer possible in an environment heavily focused on commercial metrics like user growth"
- **Financial incentives cause researchers to "chase short-term wins instead of risky bets"**

The key insight: *the organizations best positioned to run the next paradigm are also the ones most structurally incentivized not to*. This is a timing trap — the lab with the most resources is also the most conservative at the moment a paradigm shift requires a bet.

### 3. The Next Frontier: Two Bets

Tworek identifies two research directions as prerequisites before AGI:

1. **Entirely new architectures beyond Transformers** — the current architecture has scaling limits that won't be solved by more compute or better training recipes
2. **Continuous learning** — "one of the last important building blocks before AGI." Humans don't have separate learning and inference modes; current models are frozen at deployment. Online weight updates in production are necessary

His Core Automation project ("Ceres") targets 100x reduction in training data through continual learning — a model that updates weights during deployment rather than requiring full retraining cycles.

### 4. Praise for Anthropic

In a notable aside, Tworek praised Anthropic: "with less compute and a smaller team, it has shown focus and strong execution." He cited their coding models and developer adoption as evidence that focused execution beats resources-first strategy.

### 5. The "Most Automated AI Lab" Thesis

Core Automation's vision: small teams + capable AI agents doing work that previously required entire organizations. The lab is itself an AI-augmented lab — Tworek wants to run the kind of research-intensive, architecturally novel bets that are blocked by big-lab incentive structures, using AI agents to compress the team size required.

---

## Key Quotes (from secondary reporting)

> "He found it hard to keep doing high-risk, pioneering work at OpenAI as the company shifted toward more conservative ways."

> "All the major AI labs are doing the same thing: optimizing the same Transformer technology with products that barely differ from each other."

> "[Continuous learning is] one of the last important building blocks before AGI."

> "[Financial incentives cause researchers to] chase short-term wins instead of risky bets."

> "[Regarding Anthropic:] with less compute and a smaller team, it has shown focus and strong execution."

> "Deep learning research is done [at OpenAI-scale labs]." (paraphrase from secondary reporting on Core Automation)

---

## VERSO RELEVANCE

### [NEW-IDEA] The timing trap for paradigm bets (§12 positioning / §1 bet)

The structural argument Tworek makes — labs are most conservative exactly when the next paradigm needs a bet, because commercial-metrics gravity is highest when you're most successful — directly validates Verso's counter-positioning rationale. The same trap applies to agent frameworks: the dominant players (LangChain, LangGraph) are locked into their graph model by user base, not by technical superiority. A challenger can make the bet the incumbent cannot. Verso should name this dynamic explicitly.

**Verdict:** HIGH VALUE. Adds a structural / timing argument to Verso's positioning that goes beyond "simpler is better" to "incumbents are structurally blocked from making the right bet."

### [SHARPENS §5.1 loop / §6.1 durable] Continuous learning as a loop primitive future

Tworek's "continuous learning" thesis (online weight updates during inference) points toward a loop design consideration: the Verso harness should be architected so that fine-tuning / feedback loops from completed runs can be piped back to training. The durable layer (event-sourced checkpoint/resume) is exactly the kind of run log that would feed a continuous learning pipeline. The durable layer isn't just about HITL — it's the data infrastructure for model improvement.

**Verdict:** Forward-looking. Verso's durable event log should be treated as training data, not just audit trail. A low-cost addition that makes the architecture future-proof.

### [CONFIRMS §12 positioning] RL-on-tool-return has a ceiling

The RL lead on o1/o3 admitting RL scaling "didn't turn out as mighty as originally believed" confirms that reinforcement-on-tool-return (already in Verso's known list) is a finite signal — necessary but not sufficient. Verso should not over-index on RL-based eval as the endgame; judge-panel + define_outcome(bounded) as the eval primitive is the right layer to invest in, not waiting for RL to solve reliability.

**Verdict:** CONFIRMS Verso's eval-first stance. The people who built the best RL systems are now betting against RL as the only path.

### [NEW-IDEA] "Small teams + AI agents" as the lab model (§6.2 multiagent / §1 bet)

Core Automation's operating thesis — AI agents replacing organizational scale — is the same bet Verso is making about developer teams. Tworek is building a lab where AI agents handle the volume work so 10 people can do what 200 required. This is a concrete external validation of the "harness quality matters more than loop lines" thesis: the bottleneck is not the loop, it's the harness infrastructure that makes agents reliable enough to trust with serious work.

**Verdict:** CONFIRMS §1 bet. The most credentialed RL researcher alive is building his next company on top of the thesis that agent harnesses are the bottleneck.
