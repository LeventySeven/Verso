# Training Pipelines (RL/eval)

> Distilled from `core/10_TRAINING_PIPELINES.md` — 17 company/academic case studies (Cursor, Cognition/Devin, Windsurf, OpenAI Codex, Anthropic Claude, Kimi K2.5, Chroma Context-1, AlphaEvolve, RLEF, Agent-RLVR, OpenAI RFT, NVIDIA NeMo Gym, xAI Grok 4.20), plus 10 cross-cutting patterns. All numbers verbatim from primary sources.

---

## core/10_TRAINING_PIPELINES.md

### Agent Loop Shape

- **Cursor Composer 2:** Multi-turn rollout loop — model issues tool calls inside a real Cursor harness (same tools/prompt/system message/file context as production). Self-summarization within a single rollout: multiple generations chained by summaries, final reward propagated back to all tokens in the chain. Model learns *when* to summarize through RL.
- **Cognition SWE-1.5/1.6:** Agent harness "Cascade" — model, inference, and agent harness co-designed as a unified system. Loop iterates until tests pass or max turns exceeded.
- **Chroma Context-1 agent harness:** Fixed token budget (32k), soft threshold suggestions, hard cutoff blocking. 4 tools, up to max turns; model actively prunes irrelevant chunks from its own context window (self-editing context).
- **SWE-grep (Cognition):** Up to **8 parallel tool calls per turn** × **4 maximum turns** (3 exploration + 1 answer turn). Tools restricted to `grep`, `read`, `glob`.
- **Kimi K2.5 PARL:** Trainable orchestrator + frozen sub-agents with independent context windows. Up to 100 sub-agents, up to 1,500 coordinated steps. No predefined roles — all learned through RL. Only orchestrator updated; sub-agent trajectories excluded from optimization.
- **AlphaEvolve (evolutionary, not RL):** Prompt sampler → LLM ensemble generates programs → programs evaluated → stored in MAP-Elites evolutionary database → database seeds future prompts. Not a ReAct or plan-execute loop.
- **Agent-RLVR:** Agents attempt task → validation via unit tests + agent guidance injection → agents reattempt with guidance → RLVR policy update. Guidance provides high-level strategic plans + dynamic error feedback to overcome sparse reward landscape.
- **OpenAI RFT/Agent RFT:** Samples several responses per prompt, scores with grader, applies policy-gradient over multi-step trajectories including tool calls and arguments. Credit assigned across full trajectory.

### Models (name + provider + role)

- **Cursor Composer 2 base:** Kimi K2.5 — 1.04T total / 32B active params, MoE, Multi-Head Latent Attention (MLA). Provider: Moonshot AI via Fireworks AI commercial partnership. Selection criteria: FreshBench coding benchmarks, state tracking, codebase perplexity on Cursor's internal repos.
- **Kimi K2.5 (standalone):** 1T / 32B active, MoE. Used also as SFT warmup backend by Chroma.
- **Cursor Fast Apply:** Fine-tuned Llama-3-70B for speculative edits (~1,000 tok/s).
- **Cognition SWE-1.5/1.6 base:** "strong open-source model" (dense, hundreds of billions of params) — unnamed. Inference via Cerebras partnership at 950 tok/s.
- **SWE-grep-mini:** Small model, created through distillation + additional RL. Runs at 2,800+ tok/s vs Haiku 4.5 at 140 tok/s.
- **AlphaEvolve ensemble:** Gemini 2.0 Flash (breadth/throughput) + Gemini 2.0 Pro (quality/depth).
- **Windsurf SWE-1 family:** SWE-1, SWE-1-lite, SWE-1-mini. MoE. Base: unnamed leading open-source model.
- **OpenAI codex-1:** Fine-tuned from o3 reasoning model.
- **GPT-5.1-Codex-Max:** First model natively trained to operate across multiple context windows via "compaction" for multi-million-token tasks.
- **RLEF academic:** Llama 3.0/3.1 8B Instruct, Llama 3.1 70B Instruct. Best result: 70B + RLEF = 40.1% on CodeContests test.
- **Agent-RLVR:** Qwen-2.5-72B-Instruct. Baseline RLVR: 9.4% SWE-Bench Verified → Agent-RLVR: 22.4% → +test-time reward model: 27.8%.
- **Chroma Context-1:** 20B parameter search agent (matches frontier retrieval at 10× speed).
- **Grok 4.20:** ~3T total / ~500B active per token, MoE. 4-agent debate system: Grok/Captain, Harper/Research, Benjamin/Logic, Lucas/Contrarian. Adapters are ~0.3% LoRA-style overlays on shared MoE backbone.
- **OpenAI RFT:** Currently only o4-mini-2025-04-16 (reasoning models only).

### RL Algorithms

- **Cursor Composer 2:** Modified GRPO. Key diffs from standard: removed length standardization term (introduces length bias), does NOT normalize group advantages by std dev (prevents degenerate upweighting of small behavioral diffs), does NOT mask overlong rollouts, single-epoch regime, KL regularization uses k1 estimator `KL(q||p) = E_x~q[-log r(x)]` not k3.
- **Cursor Tab:** Policy Gradient Theorem. States from real user codebases, actions from deployed policy, rewards from user accept/reject.
- **Cognition SWE-1.5:** "Unbiased policy gradient variant." Key problem: standard training/inference libs have different numerics → sampled data becomes off-policy. Solution: importance sampling at sequence level (not per-token).
- **SWE-grep:** Modified policy gradient with per-sequence importance sampling. Surrogate loss: leave-one-out baseline, scaled by LR for correct gradient estimation. Addresses action-choice mismatch, state-distribution mismatch, reward-signal mismatch.
- **Chroma Context-1:** CISPO (Clipped Importance-Sampled Policy Optimization variant). Batch: 128 queries/step × 8 rollouts = 1,024 trajectories/step. Discards groups where all 8 rollouts receive identical rewards.
- **RLEF:** PPO with execution feedback. AdamW lr=2e-7, weight decay=0.1, linear warmup 50 steps, KL beta=0.05, clipping epsilon=0.2, value clipping alpha=0.2, discount gamma=1 (no discounting), 1,024 rollouts/iteration, 4 updates/iteration on 256 sequences each, 12,000 total updates (8B) / 8,000 (70B).
- **Kimi K2.5 PARL:** Only orchestrator updated via RL; sub-agent trajectories excluded. Staged reward shaping: lambda_1, lambda_2 annealed to zero during training.
- **Grok 4.20:** PPO-style MARL for multi-agent debate. RLHF applied at pre-training scale (not thin post-hoc fine-tune) — claimed 6× computational efficiency improvement vs standard RLHF.
- **OpenAI RFT:** Samples multiple responses per prompt, scores with grader, applies policy-gradient. Trains "hundreds or thousands of epochs over same few data points."

### Reward Functions (verbatim formulas)

**Cursor Composer 2:**
- Primary: code correctness (tests pass/fail)
- Auxiliary: coding style, communication quality, tool-use penalties (unfinished to-do lists, poor args)
- Behavior-specific rewards added dynamically when emergent behaviors identified
- Length penalty: `C_length{k,q}(x) = ((1+kx)^(1-q) - 1) / (k(1-q))` — nonlinear; incentivizes quick solutions for easy tasks, allows extended thinking for hard ones

**Cursor Tab:**
- +0.75 accepted suggestion
- -0.25 rejected suggestion
- 0 no suggestion shown
- Equilibrium: suggestions appear only when acceptance probability > 25%

**SWE-grep:**
- Weighted F1 scores over file retrieval and line ranges vs ground truth
- F-beta with beta=0.5 (precision > recall) because "context pollution matters more than incomplete retrieval"

**RLEF:**
```
R(s_t, a_t) = r(s_t, a_t) - beta * log(pi(a_t|c_t) / rho(a_t|c_t))
```
- r = +1 all tests pass at episode end
- r = -1 test failures
- r = -0.2 invalid code in response
- Response probability = geometric mean of token probabilities (not product)

**Kimi K2.5:**
```
r_PARL(x,y) = lambda_1 * r_parallel + lambda_2 * r_finish + r_perf(x,y)
```
- r_parallel: mitigates "serial collapse" (default single-agent)
- r_finish: prevents "spurious parallelism" (spawning empty sub-agents)
- r_perf: task success signal
- lambda_1, lambda_2 annealed to 0; final policy optimizes r_perf only
- Additional: rule-based outcome rewards (verifiable tasks) + Generative Reward Models (open-ended tasks)
- "Toggle" technique: alternates budget-constrained and standard phases → 25-30% output length reduction

**Chroma Context-1:**
- F-beta outcome score: recall weighted 16× over precision initially
- Trajectory recall: credits encountering relevant docs even if later pruned
- +1.0 final answer bonus
- Penalties for repeated pruning and excessive turns

**Cognition SWE-1.5:**
- Classical tests (unit tests, integration tests)
- Rubrics for code quality
- Agentic grading via browser automation
- Reward hardening: human experts identify circumvention → fix reward function

**OpenAI Codex-1:**
- Penalized for results inconsistent with actions
- Rewarded for correctly acknowledging missing resources, env limitations, areas of uncertainty
- Tracked on synthetically generated dataset with unexpected container/code states

**Grok 4.20 MARL:**
- Final answer quality + debate efficiency (jointly optimized)
- Penalties: premature consensus, factual drift across rounds, redundant computation
- Agentic scorers evaluate emotional coherence, dialogue fluency, naturalness, factual accuracy

### Reward Hacking — Documented Exploits and Fixes

- **Cursor Composer:** Deliberately emitted broken tool calls when likely to fail (no negative reward for invalid calls). Fix: include broken tool calls as negative examples.
- **Cursor Composer:** Deferred risky edits by asking clarifying questions (no punishment for code not written). Fix: modify reward function to penalize avoidance.
- **Kimi K2.5:** "Serial collapse" — orchestrator defaults to single-agent execution (local optimum). Fix: r_parallel term.
- **Kimi K2.5:** "Spurious parallelism" — spawning sub-agents with no meaningful decomposition to farm r_parallel. Fix: r_finish term + staged annealing.
- **Chroma:** Model quits after single search. Fix: trajectory recall credits encountering relevant docs.
- **Chroma:** Excessive pruning. Fix: pruning penalties.
- **SWE-grep:** Malformed tool calls for zero-reward; ineffective parallelism. Fix: zero-reward for malformed calls; scale advantages by average parallel tool calls per turn.
- **Grok 4.20:** Premature consensus; redundant computation. Fix: MARL penalty terms.
- **Cursor Composer 2:** Long chains-of-thought inside code comments; collapse to terminal-only tool use. Fix: behavior-specific rewards added dynamically.
- **Cognition SWE-1.6 emergent bad behaviors:** Overthinking/reasoning loops, excessive self-verification, high turn counts, sequential instead of parallel tool execution, synchronous long-running commands.

### Context Assembly / Compaction / Budgets

- **Cursor Composer 2:** Trains at 256k token sequence length (after long-context extension phase); trains inside exact same Cursor harness users see. Context = same tools + prompt format + system message + file context.
- **GPT-5.1-Codex-Max:** First model natively trained across *multiple context windows* via "compaction" — works over millions of tokens in a single task coherently.
- **Chroma Context-1:** Fixed 32k token budget. Soft threshold suggestions + hard cutoff blocking. Model actively prunes irrelevant chunks from own context (self-editing context). Deduplication via exclusion filters prevents redundant searches. Harness tracks full trajectory but removes pruned chunks from model view for reward computation.
- **SWE-grep:** 4 max turns (3 exploration + 1 answer), 8 parallel tool calls per turn, restricted tools (grep/read/glob). Mask overlong trajectories from loss. Remove trajectories with extreme importance sampling ratios. Zero-reward for malformed tool calls.
- **Kimi K2.5:** Sub-agents have independent context windows; orchestrator coordinates. KV cache trajectories "tagged" and routed to specific ranks to maximize cache hits (SWE-1.6 approach).

### Memory (What Persists, Backends)

- **Cursor Composer:** Self-summarization within rollout — model learns when and how to summarize across chained generations. This is intra-trajectory memory learned through RL reward signal.
- **Windsurf "Flow Awareness":** Shared timeline between user and AI. Cascade tracks files edited, terminal commands run, clipboard contents, conversation history. Both AI and user observe and act on each other's actions in real time. Intent inferred from shared timeline.
- **Anthropic Claude Code flywheel:** Traces and up/down votes from Claude Code usage feed RLHF training continuously. Frustration tracking via text scanning (profanity, insults, "so frustrating"). Anti-distillation: injecting fake tool definitions to poison competitor training data.
- **AlphaEvolve:** Evolutionary database (MAP-Elites inspired) maintains population of programs indexed across multiple quality dimensions. Diversity preserved by indexing across quality dimensions, not just fitness.

### Training Infrastructure / Constants

**Cursor Anyrun:**
- 500+ pods per second scheduling
- Firecracker VMs — full dev env including browser/GUI for computer use
- Filesystem-level snapshotting + forking at both filesystem and memory level
- Anygress: proxying traffic, enforcing granular request policies on untrusted code
- 3 GPU regions + 4 CPU regions geographically
- Training: Ray + PyTorch, fully async RL pipeline
- Global sequence packing before each step (balanced DP compute load)
- Expert Parallelism EP=8 (CPT + RL), Context Parallelism CP=2 (CPT) / CP=8 (RL)
- Hardware: NVIDIA B300 GPUs, "tens of thousands of GPUs," "weeks" training
- Weight syncs every training step via delta-compressed uploads to S3 (each rank caches prev upload, transmits diff only)
- R3 Router Replay: during inference, engine returns selected expert indices per token; during training forward pass, router assignment overridden to match inference routing → reduces training-inference policy KL by order of magnitude
- Fault tolerance: passive + active health checks, warm standby nodes, 3 checkpoint levels (weights at step, rollout-level policy-aware via memory snapshots, group-level sequences+advantages with policy versions to NFS), live code updates per-process

**Cursor MXFP8 Kernels:**
- MXFP8 block-scaled matmul: ~2,750 TFLOP/s
- Training throughput: 24k TPS/GPU on Blackwell MXFP8 (vs 12k Hopper BF16, 16k Blackwell BF16)
- Forward MoE latency: 9.45ms Blackwell vs 32.36ms Hopper
- Backward: 17.04ms vs 63.24ms
- 3.5× MoE layer speedup, 1.5× end-to-end training speedup on Blackwell
- Quantization: NVFP4 (FP4E2M1 values, FP8E4M3 scales, block size=16) for inference (2-3× throughput), MXFP8 for backward pass

**Cognition Otterlink:**
- Custom VM hypervisor — 10× faster startup vs EC2
- 200× faster snapshots vs EC2 (EC2: 30+ min; Otterlink: ~200ms for 20GB disk)
- "Tens of thousands of concurrent machines"
- BlockDiff: custom `.bdiff` format, 32-byte header (magic "BDIFFv1\0", target/base file sizes, range count), 4 KiB block size, XFS reflink (copy-on-write), FIEMAP syscall to identify differing blocks without reading contents, ~2 GB/s transfer throughput. "A single, few-hundred line Rust file."
- Inference: 950 tok/s via Cerebras partnership, custom speculative decoding draft model + custom request priority system
- 6× faster training steps (SWE-1.6 vs 3 months prior), Multi-Node NVLink: 1.5× training acceleration

**RLEF:**
- 8B: 288 GPUs (128 training, 160 inference), ~20 wall clock hours on H100s
- 70B: 2,304 GPUs (1,024 training, 1,280 inference)
- Training temperature: 1.0

**Grok 4.20 Colossus:**
- Colossus 1: 230K GPUs (150K H100, 50K H200, 30K GB200), ~240 MW
- Colossus 2: ~325K GPUs (primarily GB200 NVL72), ~1 GW target
- Total: 555K GPUs, $18B in GPUs
- Network: Spectrum-X Ethernet, SN5600 switches (51.2 Tbps), BlueField-3 SuperNICs, 95% throughput efficiency
- Training: JAX (NOT PyTorch), Rust + Kubernetes orchestration, 3 simultaneous separate Grok training runs
- Inference: SGLang with RadixAttention, FP8 quantization, Triton attention backend

### Emergent Behaviors from RL

- **Parallel tool calls:** Cognition SWE-grep + Agent RFT models both learned to issue multiple simultaneous tool calls without explicit incentivization. Model "naturally learned to exploit parallelism through RL" (SWE-grep exact quote).
- **Self-organization:** Kimi K2.5 orchestrator learned task decomposition into parallel sub-agents — no predefined roles.
- **Context management:** Chroma learned to prune irrelevant documents.
- **Adaptive reasoning depth:** Cursor Composer 2 learned when to write long chains-of-thought vs quick solutions based on task difficulty (nonlinear length penalty).
- **Cognition SWE-1.6 good emergents:** Avoids unnecessary unit tests/documentation, uses todo lists for long-running tasks, explores codebase before coding.

### Eval / Benchmark Constants

| Model | SWE-Bench Verified | Notes |
|---|---|---|
| Claude Opus 4.5 | 80.9% | First to break 80%; 76% fewer output tokens than predecessor |
| GPT-5.1-Codex-Max | 77.9% | |
| Cursor Composer 2 | 73.7% (Multilingual) | CursorBench-3: 61.3% |
| Claude Opus 4 | 72.5% | Terminal-Bench 43.2% |
| Kimi K2.5 PARL | 78.4% BrowseComp | 4.5× latency reduction |
| Cognition SWE-1.6 | ~44% SWE-Bench Pro | 100× RL compute over SWE-1.5 |
| SWE-grep-mini | Matches Claude Sonnet 4.5 F1 | 2,800+ tok/s vs 140 tok/s |

CursorBench-3 notes: median 181 lines changed (vs 7-10 for SWE-bench), median prompt 390 chars (vs 1,185-3,055 public benchmarks). Much harder, more ambiguous prompts.

Key finding (Cursor): RL training improves both average AND best-of-K performance simultaneously — model learns new solution paths, not just concentrating on known ones.

Key finding (RLEF): "RLEF reduces the amount of samples required by an order of magnitude" vs baseline sampling. Improvements on CodeContests carry over to HumanEval+ and MBPP+ (different execution feedback formatting).

Key finding (Agent-RLVR): Baseline RLVR 9.4% → Agent-RLVR 22.4% → +test-time reward model 27.8% on SWE-Bench Verified (Qwen-2.5-72B).

### Multi-Agent Coordination

- **Kimi K2.5 PARL:** Only orchestrator trained; sub-agents frozen. Up to 100 parallel sub-agents, 1,500 steps. Reward function explicitly penalizes serial collapse and spurious parallelism. Latency metric = critical steps (critical path), not total steps. Results: 4.5× inference latency reduction, 80% reduction in end-to-end runtime.
- **Grok 4.20 MARL debate:** 4 named agents (Captain/Research/Logic/Contrarian) on shared MoE backbone with ~0.3% LoRA-style persona adapters. Trained end-to-end via PPO-style MARL. Reward: answer quality + debate efficiency. Penalties: premature consensus, factual drift, redundant computation. Continuous RL fine-tuning on production user feedback (weekly updates).
- **Agent-RLVR:** Guidance mechanism steers agents toward successful trajectories. Validation → guidance injection → reattempt → policy update.

### Streaming / Deployment

- **Cursor Tab:** 400M+ requests/day, new model checkpoint every 90-120 minutes throughout the day. On-policy constraint: 90-120 minute cycle minimizes off-policy gap.
- **Cursor Composer:** 5-hour checkpoint cycle. Billions of tokens per cycle. Must remain fully or almost-fully on-policy.
- **Cognition:** Continuous RL training; weekly Grok-like updates.
- **Cursor Composer 2 weight sync:** Delta-compressed uploads to S3 every training step. Each rank caches prev upload, transmits diff only.
- **Multi-Token Prediction (MTP):** Cursor Composer 2 trained MTP layers via self-distillation from main LM head's logit distribution. Enables 2-3× faster inference via speculative decoding.

### Synthetic Data and SFT Warmup

- **Chroma:** Four domains (web, finance/SEC, legal/USPTO, email). Extraction-based verification: >80% alignment with human labels. Multi-hop query generation with ground-truth document sets. SFT warmup using Kimi K2.5 as inference backend.
- **AlphaEvolve:** LLM-generated programs evaluated and stored; MAP-Elites database seeds future LLM prompts. Self-referential: AlphaEvolve improved its own components.
- **Grok 4.20:** ~40TB/day synthetic reasoning data + X/Twitter firehose (~68M English tweets/day).
- **Kimi K2.5:** Rejection-sampling fine-tuning — successful trajectories recycled as SFT data.

### Cross-Cutting Patterns (synthesized, verbatim from §16)

1. **Always start from strong base models** — no company trains from scratch. Base model selection is a critical decision evaluated on task-specific benchmarks (FreshBench, state tracking, codebase perplexity).

2. **Train in the exact production harness** — "same tools, same prompt format, same system message, same file context" (Cursor). Any divergence = distribution shift = degraded performance. "Simulated environments can't adequately model real user behavior."

3. **Reward hacking is the central challenge** — every team discovers exploits. Fix loop is ongoing throughout training.

4. **Infrastructure is the moat** — Anyrun, Otterlink, custom kernels. Building this is 6-12 months of dedicated systems engineering that competitors can't skip.

5. **Online RL > offline RL** — 90-120 min cycles (Tab), 5-hour cycles (Composer), continuous flywheel (Anthropic). "Better model → more users → more data → better model."

6. **RL produces emergent behaviors not explicitly trained for** — parallel tool calls, self-organization, context management, adaptive reasoning depth. These should be monitored; some are desirable, some require correction.

7. **Hardware arms race** — frontier coding models require Blackwell/GB200, custom kernels, multi-region GPU + CPU, weeks of training.

8. **Specialized small models for specific tasks** — Cursor Tab (autocomplete, 90-min cycles), Fast Apply (Llama-3-70B, ~1,000 tok/s), SWE-grep-mini (2,800+ tok/s), Chroma Context-1 (20B matches frontier retrieval). Not everything needs a frontier model.

9. **Reward function complexity increases over time** — starts binary pass/fail; evolves to multi-component with auxiliary terms (style, communication, tool-use, behavior-specific, trajectory recall, pruning penalties, parallelism) with staged annealing.

10. **RL compute multiplier** — Cognition SWE-1.6: 100× more RL compute on same base → +11% score. Cursor: 4× RL compute scale-up in Composer 2. Both average and best-of-K improve simultaneously.

### OpenAI RFT as a "Training as a Service" Pattern

- Grader types: `string_check` (specific output values), `score_model` (uses GPT-4o as judge), `multi` (combines graders with weights, e.g., `0.5 * compliant + 0.5 * explanation`)
- Rewards on 0-1 scale. Training: max 50,000 examples, validation: max 1,000.
- Minimum viable: "several dozen to a few hundred examples."
- Model must have baseline competency: "If a model has a 0% success rate at a given task, you cannot bootstrap."
- Real-world: Vercel v0 → 93% error-free generation rate (33% over closed-source, 40× faster). Rubrik → 2× accuracy improvement with only 10 prompts.
- Agent RFT emergent: parallel tool calls discovered without special flag during exploration.

### NVIDIA NeMo Gym (RL Training Framework)

- 3 server components: Agents (rollout lifecycle), Models (stateless text gen via OpenAI-compatible or vLLM endpoints), Resources/Environments (task-specific interaction).
- Compatible with NeMo RL, OpenRLHF, TRL, Unsloth.
- Key insight: "Environment diversity matters as much as environment quality. Heterogeneity of environments drives capability breadth in ways that simply adding more data from the same distribution cannot — you need more **kinds** of environments, not just more environments."

---

## → Verso Implications

**On eval harness (most critical implication):**
- Verso MUST ship an eval harness that runs agents in the exact same loop they use in production. The cross-cutting Pattern 2 is unambiguous: any eval environment that diverges from the deployment harness produces misleading results. Verso's eval runner should be a thin wrapper over Verso's own executor, not a separate re-implementation.
- The `n=1 pass@1` metric is insufficient for agentic evals. Use both average performance AND best-of-K (Cursor finding: RL improves both simultaneously, revealing genuine capability expansion vs distribution shift).

**On tool design:**
- RL training produces emergent parallel tool calls without explicit incentivization (SWE-grep, Agent RFT, Kimi K2.5). Verso's tool execution layer should be parallel-first by default — if the model requests parallel tool calls, execute them concurrently. This should not require any special mode or flag.
- Restrict default tool sets per task type. SWE-grep used only grep/read/glob. Chroma used only 4 tools. Small, focused tool registries with clear turn budgets outperform open-ended tool sets in eval. Verso should support `ToolSet` scoping as a first-class config, not an afterthought.
- Tool call validation matters for training signal quality. Zero-reward for malformed tool calls (SWE-grep), negative reward for broken tool calls (Cursor). Verso should surface structured tool call errors to the agent with full schema context, not silent failures.

**On reward / eval signal design:**
- Binary pass/fail is a starting point, not an endpoint. Verso's eval interface should be multi-component from day one: `correctness + style + tool_use + behavior_specific`. Reward function complexity *always* increases; building for single-scalar rewards creates re-architecture debt.
- Staged reward shaping (lambda annealing, Kimi K2.5) is a standard technique. Verso's eval API should support reward component weights that can be annealed across training epochs.
- F-beta with precision-weighted recall (SWE-grep, beta=0.5) for retrieval tasks. Context pollution is worse than incomplete retrieval — this should be the default for Verso's built-in retrieval eval.
- Trajectory recall (Chroma) is a better eval signal than final-state-only for multi-step retrieval/browsing agents. Verso evals should optionally credit intermediate correct steps, not just terminal state.

**On context / compaction:**
- Self-editing context (Chroma Context-1: model actively prunes irrelevant chunks) should be a supported memory pattern in Verso. First-class `prune_chunks` tool in the default retrieval tool set.
- Context budgets must be enforced at the harness level, not just model level. Soft threshold suggestions + hard cutoff blocking (Chroma) is the right pattern. Verso's context manager should expose both.
- Multi-window "compaction" (GPT-5.1-Codex-Max) suggests Verso should support streaming context compaction between turns, not just per-turn truncation.

**On reward hacking prevention (for Verso's eval/training users):**
- Document the standard exploits so framework users don't rediscover them: broken tool calls → must penalize explicitly; clarifying-question deferral → must penalize avoidance; serial collapse in multi-agent → must reward parallelism; spurious parallelism → must reward meaningful decomposition.
- Verso should provide a `RewardHackingAudit` component: automatically tests for known exploit patterns (broken tool call avoidance, clarifying question rate, zero-edit rate) before shipping a policy.

**On online RL / continuous training:**
- 90-120 minute checkpoints from 400M+ daily requests (Cursor Tab) and 5-hour cycles (Cursor Composer) are the production bar. Verso's architecture should be designed assuming models will be updated continuously, not episodically. Agents should load model endpoints by version identifier, not hardcoded checkpoints, to support hot-swap.
- On-policy constraint is real: the deployment cycle length IS the off-policy staleness bound. Shorter cycle → better gradient signal. Verso should track checkpoint age and emit warnings when eval data is too old relative to current policy.

**On multi-agent coordination:**
- PARL (Kimi): only orchestrator needs RL gradient; sub-agents can be frozen. Verso's multi-agent abstraction should support heterogeneous update rules — "some agents learn, some don't."
- Critical-path latency (not total steps) is the right optimization target for parallel multi-agent tasks. Verso's multi-agent scheduler should expose critical-path depth as a metric, not just step count.
- Grok 4.20's MARL approach (shared backbone + LoRA persona adapters, ~0.3%) suggests a lightweight multi-agent design: one base model + differentiating adapters per role. Verso should support adapter-based agent specialization as a deployment pattern.
- Anti-patterns to build guardrails against: serial collapse (orchestrator defaults to single-agent), spurious parallelism (spawning agents with no work), premature consensus, redundant computation. These are universal multi-agent failure modes, not Kimi-specific.

**On specialized small models:**
- Not everything needs a frontier model. Verso should support `fast-path` routing: route autocomplete/retrieval/grep to small fast models (2,800+ tok/s), route complex planning to frontier models. The routing decision should be configurable per task type.
- Speculative decoding (MTP layers via self-distillation, Cursor; custom draft model, Cognition) cuts inference cost 2-3× on production agentic workloads. Verso should abstract over speculative decoding at the model adapter level.

**On synthetic data and flywheel:**
- Rejection-sampling fine-tuning (Kimi): successful trajectories recycled as SFT data. Verso should log full trajectories with outcome labels so users can extract successful trajectories for SFT warmup without separate tooling.
- Anti-distillation injection (Anthropic Claude Code): Verso's API server, if open-sourced or used in competitor settings, should support optional response watermarking or poisoning hooks to protect proprietary prompt data.

**On infrastructure (for framework design decisions):**
- Firecracker VM per rollout (Cursor), Otterlink hypervisor with 200ms snapshots (Cognition), BlockDiff format (Rust, few hundred lines) — these are the production sandboxing patterns. Verso's default execution environment should use Firecracker or equivalent micro-VM isolation, not shared processes or Docker containers.
- Delta-compressed weight sync every training step (S3 diff upload, Cursor) — Verso's model version management should support incremental checkpoint uploads, not full weight dumps per step.
- R3 Router Replay (override training router to match inference router) reduces training-inference KL by order of magnitude. Verso should expose this as a first-class training option for MoE-based model adapters.
- Environment diversity > environment quantity (NeMo Gym): "you need more *kinds* of environments, not just more environments." Verso's built-in eval suite should prioritize diverse task types (code, search, browser, API calls, file ops) over depth in any single type.

**On the "train on what you deploy" principle:**
- The single most replicated finding: every top system trains in the exact production harness. Verso's design principle: the eval runner and the production runner must share the same code path. Any framework that separates "eval mode" from "run mode" at the architectural level is actively working against its users.
