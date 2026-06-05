# Adversarial Critic — multiagent-sandbox — CORRECTNESS lens
*Decision under review:* Ship in v1: 3 opt-in multi-agent topologies (`subagent_delegate` / `fan_out` / `Orchestration`, depth-cap 1) + a `CodeSandbox` escape hatch (microsandbox local default, E2B/Daytona adapters) — vs deferring ALL multi-agent + sandbox past v1.
*Lens:* CORRECTNESS — does the cited RE evidence actually prove this works for Verso's exact case?
*Resolution notes read:* `06_design_resolutions/sandboxes-multiagent.md`, `production-topology.md`
*Source teardown read:* `03_teardowns/infra-sandboxes-multiagent.md` (495 lines), `03_teardowns/multiagent-grok-heavy.md`, `03_teardowns/research-deepresearch.md`, `03_teardowns/coding-claude-code.md`, `03_teardowns/_SYNTHESIS.md`
*PRD section read:* §6.2, §8 (phases), §10 (deferred decisions)
*Date:* 2026-06-05

---

## The attack

Three distinct correctness failures, in order of severity.

### Failure 1 — The "shared typed state store" in `Orchestration` is invented, not sourced; and the sourced systems use the opposite coordination primitive

The resolution note (Decision 6, `Orchestration`) states: "Workers write to a **shared typed state store** (a `dict[str, Any]` with typed access helpers, **not message passing**)... mirrors Grok's 'leader IS one of the N agents and IS the synthesizer.'"

The Grok teardown (`multiagent-grok-heavy.md:99`) is unambiguous: Grok uses `chatroom_send(to: enum{"Benjamin","Harper","Lucas","All"}, message: str)` — directed message-passing between named agents. The teardown's For Verso note at line 381 explicitly says: "prefer the `chatroom_send`/`wait` **continuous-injection pattern** over collect-all-then-synthesize." Grok does NOT use a shared dict.

The Anthropic Research teardown (`research-deepresearch.md:506-509`) says the A2A mechanism is "typed directed messages between named threads... NOT a shared global scratchpad — typed directed messages between named threads."

The resolution note cites Grok as proof for shared-state, but Grok is proof for message-passing. The `SharedTypedState` design is DESIGNED (invented) — the constants table in the resolution note itself is missing any entry for `SharedTypedState` because there is no RE source for it. Open Unknown #4 in the resolution note admits: "the actual storage backend... needs a decision after Phase 2's durable substrate lands."

The correctness consequence: the `Orchestration` topology spec is built on a coordination primitive (`SharedTypedState`) that has no implementation, no RE source, and contradicts the sourced coordination pattern. For Verso's Python async ReAct loop, where the "durable substrate" is not yet built (PRD Phase 2, not Phase 0 or 1), the `Orchestration` topology literally cannot be implemented in v1 without first solving the storage backend problem. The resolution note is proposing to ship a topology whose coordination layer is a known open unknown.

### Failure 2 — `verso.internal` egress proxy routing at SYN time is unverified against microsandbox's actual DNS resolution path, and the resolution note admits this

The resolution note (Decision 4) proposes: "The sandbox always boots with `egress_policy="deny_all"` by default... reachable inside the sandbox as `http://verso.internal:<port>`... `NetworkPolicy{...destination:Domain("verso.internal")...}`."

The teardown (`infra-sandboxes-multiagent.md:294`) documents microsandbox's domain matching: "Domain rules are matched two ways... at **SYN time** before SNI is known (via a resolved-hostname cache from the guest's DNS lookups), and at **SNI time** for TLS."

The mechanism is: the policy engine checks a cache of domain names the *guest resolved via DNS*. For a standard domain like `openai.com`, the guest DNS-resolves it before connecting; the resolved name enters the cache; the policy matches. But `verso.internal` is not a real DNS name — it has no external DNS record. For the Domain-rule match to work at SYN time, the guest must already have resolved `verso.internal` via some DNS server. The teardown does not document a host-injected DNS server, a `/etc/hosts` injection mechanism, or a stub resolver that would make `verso.internal` resolvable inside the guest's DNS cache before the first SYN.

The only documented hostname alias in the teardown is `host.microsandbox.internal` (`infra-sandboxes-multiagent.md:249`) — a hardcoded alias in the microsandbox network layer. Whether arbitrary custom domain aliases can be added to the microsandbox NetworkPolicy and have the guest resolve them is not documented. The `VERSO_INTERNAL_PROXY_HOST` and `VERSO_INTERNAL_PROXY_PORT` constants are both explicitly labeled "DESIGNED (no RE source)" in the constants table.

The resolution note itself acknowledges this in Open Unknown #1: "needs a real integration test to confirm the `verso.internal` alias is resolved before the first guest SYN." This means the network isolation mechanism for the v1 local sandbox is a known-unverified implementation — it may or may not work, and if it doesn't, the "no-secrets-in-sandbox" security invariant cannot be enforced for microsandbox.

For a dogfood-first builder whose thesis is "don't over-engineer around a non-bottleneck," shipping an unverified security mechanism as the v1 default is a correctness liability, not a feature.

### Failure 3 — The resolution note cites `infra-sandboxes-multiagent.md` as the evidence base for multi-agent topologies, but that teardown covers sandboxes and Parlant, not multi-agent orchestration

The resolution note header says: "Evidence base: `03_teardowns/infra-sandboxes-multiagent.md` (E2B/Daytona/microsandbox/Cloudflare/Parlant, 494 lines source-first)." The multi-agent topology decisions (Decision 6) cite `_SYNTHESIS.md §Avoid #15` and `§Avoid #18` — items from the synthesis note, not the primary teardown.

The actual evidence for the three multi-agent topologies comes from: `coding-claude-code.md:213` (`max_depth=1` default), `coding-codex.md:442` (`agents.max_depth=1`), `_SYNTHESIS.md:253` (Claude Code hard-bans nesting, Anthropic Research depth-limit=1), and `research-deepresearch.md:448` (+90.2% Anthropic Research gain). None of these is `infra-sandboxes-multiagent.md`. The named teardown is a sandboxes + Parlant teardown; it contributes zero multi-agent-topology RE evidence.

The consequence is that the multi-agent topology design rests on synthesis-note bullet points from systems with divergent architectures (Claude Code's hard-ban is an architectural constraint of their specific shipping product; Anthropic Research's depth-limit=1 is for a research agent; Codex's `max_depth=1` is a config default they explicitly noted is "too conservative for many legitimate use cases" — `coding-codex.md:639`). The Codex teardown itself says: "Verso should make nesting depth configurable from the start and document the tradeoffs." The resolution note defaults depth=1 citing these sources, but one of the sources says that default is too conservative.

### Secondary correctness issue — PRD contradiction

The resolution note's v1 shipping decision directly overrides explicit PRD decisions without a stated rationale for the override:

- PRD §8 Phase 3: "`orchestrate/` (subagent-as-context-isolation, `fan_out`, orchestrator-workers...)" — Phase 3 is after Phase 0 (core loop), Phase 1 (memory + evals), and Phase 2 (durable seam). The PRD exit criterion for Phase 3 is "a multi-agent research task; OSS-readiness review."
- PRD §10 item 9: "Code-execution escape hatch (Code Mode): deferred to ≥ Phase 3; sandbox provider TBD (E2B/Modal/V8 isolate)."

Both are explicitly Phase 3. The resolution note proposes both in v1 (which maps to Phase 0 in PRD terms — the dogfoodable core). The note provides no argument for why the Phase 3 assessment was wrong.

---

## Does it break the decision?

**Partially. The sandbox (microsandbox + adapters) decision survives with caveats; the `Orchestration` topology with shared-state coordination fails the correctness bar.**

**What survives:**
- microsandbox as local default: the RE evidence is solid (pip install, self-contained, KVM isolation, <100ms boot). The choice is well-sourced.
- E2B/Daytona adapter protocol: the `CodeSandbox` protocol spec is faithfully derived from the teardown. The snapshot-semantics table (DISK vs MEMORY) correctly captures the teardown's key finding.
- `subagent_delegate` and `fan_out`: the depth-cap evidence is real (Claude Code hard-bans, Codex `max_depth=1`, Anthropic Research depth-limit=1). The SubagentResult compact-summary return type correctly captures `_SYNTHESIS.md §Avoid #18`. These are implementable without the durable substrate.
- Daemon-in-sandbox two-tier protocol: correct sourcing from E2B's `envd` and Daytona's toolbox.

**What fails the correctness bar:**
- `Orchestration` with `SharedTypedState`: no RE source for this coordination primitive; sourced systems use message-passing; the implementation requires the durable substrate which doesn't exist yet.
- `verso.internal` egress proxy: the network routing path is unverified; the resolution note's own Open Unknown #1 says integration testing is required.
- The PRD contradiction (both features are Phase 3 per the PRD) is unaddressed.

---

## Evidence checked

| Claim | Source cited | Verified? | Finding |
|---|---|---|---|
| microsandbox self-contained pip install | `infra-sandboxes-multiagent.md:238` | YES | Confirmed: 32MB cp310-abi3 wheel, msb binary embedded |
| E2B UFFD ~150ms warm resume | `infra-sandboxes-multiagent.md:83` | YES (INFERRED per teardown) | Confirmed as "INFERRED from the prefetch design + the published ~150 ms figure; the exact number is not in the repo" |
| microsandbox snapshot disk-only | `infra-sandboxes-multiagent.md:298` | YES | Confirmed: "memory contents are explicitly not captured" |
| verso.internal Domain-rule routing at SYN time | Resolution note Open Unknown #1 | UNVERIFIED | Teardown only documents `host.microsandbox.internal` as existing alias; `verso.internal` is DESIGNED |
| Grok "leader IS synthesizer" proves shared-state coordination | `multiagent-grok-heavy.md` | NO — misread | Grok uses `chatroom_send` message-passing; teardown line 381 explicitly recommends continuous-injection message passing for Verso |
| Anthropic Research uses shared state store | `research-deepresearch.md:506-509` | NO — contradicted | "NOT a shared global scratchpad — typed directed messages between named threads" |
| Claude Code hard-bans nesting | `coding-claude-code.md:213` | YES | "Subagents CANNOT spawn other subagents (hard constraint, no nesting)" |
| Codex max_depth=1 | `coding-codex.md:442` | YES | "agents.max_depth = 1 (default)" — but same source says this is "too conservative" (`coding-codex.md:639`) |
| Both multi-agent and sandbox are Phase 3 per PRD | `PRD_v1.md §8, §10` | YES | Confirmed. Resolution note overrides without stated rationale |

---

## Recommendation

**Split the decision into three separate sub-decisions with different verdicts:**

1. **CodeSandbox escape hatch (microsandbox + adapters): SHIP IN v1 IF the `verso.internal` egress proxy is replaced.** The microsandbox adapter is well-sourced and works. The egress proxy using `verso.internal` is the risk. Replace it: use `host.microsandbox.internal` (the documented existing alias) as the proxy host, or ship without the egress proxy in v1 (deny-all default is still correct security; proxy is Phase 2). Do not ship an unverified security mechanism as the v1 default. The `SnapshotResult(kind: DISK|MEMORY)` distinction is correctly sourced and should ship.

2. **`subagent_delegate` and `fan_out`: SHIP IN v1 as designed.** These are implementable without the durable substrate, the depth-cap evidence is solid, and the SubagentResult compact-summary return type correctly prevents the anti-pattern. The PRD Phase 3 assignment should be revisited — these two topologies are simple asyncio wrappers and imposing a Phase 3 gate is over-conservative relative to the actual complexity.

3. **`Orchestration` with `SharedTypedState`: DEFER past Phase 2.** This topology requires a `SharedTypedState` coordination layer that has no RE source, contradicts the sourced coordination patterns (message-passing in both Grok and Anthropic Research), and cannot be implemented without the durable substrate (which is Phase 2). Shipping it in v1 means shipping a topology whose coordination layer is an open unknown. Defer until the durable substrate exists; at that point the `SharedTypedState` can be a thin wrapper over the checkpoint store (which the resolution note itself suggests in Open Unknown #4). This is the right design — it just isn't v1 work.
