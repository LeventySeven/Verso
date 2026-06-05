# Adversarial Critique — multiagent-sandbox / THESIS & SCOPE lens
*Decision under review:* Ship in v1: 3 opt-in multi-agent topologies (subagent_delegate / fan_out / orchestrator_workers, depth-cap 1) + a CodeSandbox escape hatch (microsandbox local default, E2B/Daytona adapters).
*Resolution note attacked:* `06_design_resolutions/sandboxes-multiagent.md`
*Critic lens:* THESIS & SCOPE — does this betray the "keep it simple; don't over-engineer; no non-bottleneck dependency; tactical layer simple; dogfood-first" thesis?
*Date:* 2026-06-05

---

## The attack

**The resolution calls this "v1" but the PRD's own phase plan assigns both features to Phase 3. That is the entire attack.**

PRD §8 (build phasing, lines 291-294):
- Phase 0: core loop + context + tools + model + stream.
- Phase 1: memory + evals + safety hooks.
- Phase 2: the durable seam.
- **Phase 3: `orchestrate/` (subagent-as-context-isolation, fan_out, orchestrator-workers, reviewer hook, graph escape hatch).**

PRD §10.9 (open decisions, line 321):
> "Code-execution escape hatch (Code Mode): **deferred to ≥ Phase 3**; sandbox provider TBD (E2B/Modal/V8 isolate)."

The resolution note (`sandboxes-multiagent.md`) uses the word "v1" nine times (lines 12, 20, 50, 97, 109, 573, etc.) and specifies:
- A three-adapter `CodeSandbox` protocol (microsandbox + E2B + Daytona), complete with a two-tier daemon protocol, egress proxy, magic-marker artifact extraction, SnapshotResult(kind) semantics, and an egress `NetworkPolicy` struct.
- Three multi-agent topology implementations (`subagent_delegate`, `fan_out`, `Orchestration`) with typed `SubagentResult`, `DepthCapExceeded`, `SharedTypedState`, and a `DEFAULT_DEPTH_CAP`.
- Six open unknowns that explicitly cannot be resolved without a running prototype (the verso.internal DNS alias, Daytona sidecar proxy, verso-daemon build/mount, SharedTypedState storage backend, fan_out cancellation ergonomics, and topology instrumentation).

The resolution has redesignated Phase 3 work as "v1" without changing the build order or providing a reason why Phase 0/1/2 dogfooding requires these features.

**Concretely: what is being built here, and does dogfood-first Phase 0/1/2 need any of it?**

The builder's stated v1 is a "personal AI product": a single async ReAct agent with context engineering, evals, and a durable seam. The PRD's own success criteria (§9) does not mention sandboxed code execution or multi-agent coordination anywhere. The wedge demos (W1, W2, W3) are: a 10-line agent, a one-flag durable seam, and `agent.inspect()`. None of these require a sandbox or a fan_out call.

**The thesis says: "you find the right abstraction by USING it, not on paper."** The resolution designs six subsystems with eleven open unknowns across three sandbox backends and three multi-agent topologies — entirely on paper. It is exactly the category of work the thesis warns against. The resolution note itself acknowledges in Open Unknown #4 that the `SharedTypedState` backend "needs a decision after Phase 2's durable substrate lands" — meaning the design depends on infrastructure that doesn't exist yet and explicitly cannot be validated before Phase 2 completes.

**What does "ship in v1" actually cost for a solo builder?**

The sandbox subsystem alone requires:
1. `verso/orchestrate/sandbox.py` — the abstract protocol (CodeSandbox, SnapshotResult, EgressPolicy, EgressRule, ProcessEvent, Artifact — 6 dataclasses, 8 abstract methods).
2. `verso/orchestrate/sandbox_microsandbox.py` — MicrosandboxAdapter with egress proxy integration.
3. `verso/orchestrate/sandbox_e2b.py` — E2BAdapter with MMDS credential injection.
4. `verso/orchestrate/sandbox_daytona.py` — DaytonaAdapter (no credential isolation path; marked as limitation).
5. `verso/orchestrate/sandbox_artifacts.py` — magic-marker artifact extraction + matplotlib preamble injection.
6. `verso-daemon` — an in-sandbox binary (build toolchain TBD: PyO3? shiv? Go?), bind-mounted into every image.
7. An egress proxy (host-side asyncio HTTP server with smoltcp `verso.internal` routing).
8. Integration tests against a real microsandbox VM to validate the DNS alias timing (Open Unknown #1).

The multi-agent subsystem adds:
1. `verso/orchestrate/delegate.py` — `subagent_delegate`, `fan_out`, `Orchestration`, `SubagentResult`, `DepthCapExceeded`, `SharedTypedState`.
2. `verso/orchestrate/__init__.py` — the separate import boundary.
3. A cancellation contract for fan_out (Open Unknown #5: "needs dogfood to find the right ergonomic" — this is an admission that the API is not finalized, it needs to be built to discover what it should be).

This is Phase 3 work. Building it before Phase 0 is shipped and dogfooded contradicts the thesis's core mechanism for finding the right abstraction: the builder cannot know what the fan_out cancellation contract should be, what SharedTypedState actually needs to store, or whether microsandbox egress works as documented until a real agent running on the Phase 0/1/2 stack generates the need for these features.

**Is there a cheaper alternative?**

For the sandbox: `subprocess.run` inside an existing Docker container or `asyncio.create_subprocess_exec` with a timeout. Python's stdlib `subprocess` module is a one-file implementation of "run code, get stdout/stderr, kill after N seconds." The builder can dogfood Code Mode with this. If the use case demands microVM isolation, `pip install microsandbox` and a direct call to `Sandbox.create()` without building a three-adapter abstraction layer on top of it is 50 lines, not 500. The abstract `CodeSandbox` protocol with SnapshotResult.kind and SnapshotKind enum is generalization ahead of evidence — evidence that only exists after using the feature on a real task.

For multi-agent: `asyncio.gather` is already in the language. `fan_out` as designed is roughly 15 lines of asyncio gather + semaphore. The caller can write this directly until the abstraction has been earned by repeated use. `subagent_delegate` is a call to `agent.run(task)` on a second agent instance. None of the three topologies require new primitives until dogfood reveals the actual coordination pain.

**Does it break the thesis?**

Yes, on two of the four thesis rules:
1. **"Don't over-engineer"** — six open unknowns in the design before a line of Phase 0 code is written is the definition of over-engineering. Building `verso-daemon` (unknown build toolchain) and an egress proxy before the first personal agent runs on the framework is building infrastructure for a future use case, not for the current bottleneck.
2. **"You find the right abstraction by USING it, not on paper"** — the resolution designs the full API surface for features the builder hasn't dogfooded yet. The `fan_out` cancellation ergonomic is not knowable without real usage. The SharedTypedState backend is not knowable until Phase 2 lands. The resolution explicitly acknowledges both of these.

The other two thesis rules are not betrayed: microsandbox is a real dependency with a real bottleneck (KVM-grade isolation is not a non-bottleneck), and the tactical layer stays simple (the CodeSandbox protocol is not in the core loop).

**What is lost by deferring past Phase 0/1?**

Nothing in Phase 0 or Phase 1 requires a sandbox or multi-agent. Phase 2 (the durable seam) does not require multi-agent. The only cost of deferral is that the Phase 3 build happens later — which is exactly where the PRD already placed it. There is no opportunity cost to keeping the PRD's own phase plan intact.

---

## Does it break the design?

**It breaks the thesis-fidelity constraint (PRD §9: "no graph required for any tactical agent"... confirmed, but also "thesis-fidelity" as a success criterion).** More precisely: the resolution collapses Phase 3 into Phase 0 without stating why the phase order should change. This is a PRD self-contradiction, not a downstream implementation risk — the design document contradicts itself on the build order, and the resolution does not acknowledge or justify the contradiction.

The functional design of the sandbox and multi-agent primitives is sound — the evidence trail is real, the constants are well-sourced, the architecture choices are defensible for when these features are built. The issue is only the timing claim ("v1") and the implied instruction to build this before the durable seam or the eval wedge.

---

## Evidence checked

- `PRD_v1.md` §8 (phase plan, line 294): `orchestrate/` is Phase 3. Verified directly.
- `PRD_v1.md` §10.9 (line 321): Code Mode sandbox is "deferred to ≥ Phase 3." Verified directly.
- `PRD_v1.md` §9 (success criteria): does not mention sandbox or multi-agent. Verified directly.
- `sandboxes-multiagent.md` line 97: "Decision 6 — Multi-agent topologies to ship in v1." Direct quote.
- `sandboxes-multiagent.md` line 12: "microsandbox is the v1 default for CodeSandbox." Direct quote.
- `sandboxes-multiagent.md` Open Unknowns (lines 573-583): six unresolved unknowns requiring prototypes and dogfood. Verified directly.
- `THESIS_VERIFICATION.md` §Claim 7 ("keep it simple — vindicated as a DEFAULT heuristic"): "the right abstraction cursor cannot be found on paper — only by using the thing." Verified directly.
- No source claim in the resolution was found to misread the RE evidence — the sandbox architecture facts (microsandbox self-contained wheel, smoltcp egress policy, agentd binary frame protocol, E2B UFFD semantics) all check out against `infra-sandboxes-multiagent.md`. The attack is on scope and timing, not on the technical accuracy of the RE.

---

## Recommendation

**REVISE the timing claim, not the design.**

The resolution note contains excellent, well-sourced design work that should be built in Phase 3 exactly as specified. The fix is a one-sentence edit: replace "ship in v1" with "ship in Phase 3 (per PRD §8)" throughout the resolution note, and treat the current document as the design spec for Phase 3 rather than a v1 implementation mandate.

No feature should be cut. No architecture should be changed. The `CodeSandbox` three-adapter protocol, the two-tier daemon design, the egress proxy pattern, and the three multi-agent topologies are all the right calls for when these features are built.

The specific revision:
1. `sandboxes-multiagent.md` Decision 1 header: "v1 default" → "Phase 3 default."
2. `sandboxes-multiagent.md` Decision 6 header: "topologies to ship in v1" → "topologies to ship in Phase 3."
3. Open Unknown #4: already correctly notes "needs a decision after Phase 2's durable substrate lands" — this is evidence the design itself knows it belongs after Phase 2.

The cheaper Phase 0/1/2 substitute for Code Mode if the builder needs it before Phase 3: `asyncio.create_subprocess_exec` with a timeout, wrapped as a single `@tool`. No adapter layer, no daemon, no egress proxy. Promote to the full `CodeSandbox` protocol in Phase 3 after dogfooding reveals which of the six open unknowns actually matter.
