# Sandboxes & Multi-Agent — Verso Design Resolution
*Subsystem: `orchestrate/` + `tools/code_sandbox.py` | PRD §6.2 + §10.9*
*Evidence base: `03_teardowns/infra-sandboxes-multiagent.md` (E2B/Daytona/microsandbox/Cloudflare/Parlant, 494 lines source-first) + `03_teardowns/coding-codex.md` (Code Mode V8) + `03_teardowns/_SYNTHESIS.md` (multi-agent convergence summary)*
*Date: 2026-06-05*

---

## Decisions Resolved

### Decision 1 — Default sandbox tier for Code Mode

**Choice:** `microsandbox` (local libkrun microVM) is the v1 default for `CodeSandbox`. E2B Firecracker cloud is the `cloud` adapter. Daytona container is the `container` adapter. All three back a single `CodeSandbox` protocol.

**Rationale:**
Verso is personal infrastructure, dogfood-first. The local dev experience must work with `pip install verso` and zero cloud accounts. microsandbox meets this bar: `pip install microsandbox` pulls a 32 MB self-contained wheel (`cp310-abi3`) with the `msb` binary embedded; no Docker daemon, no Nomad, no separate server. The VM is a real KVM microVM (libkrun via the `msb_krun = "0.1.14"` safe wrapper), so isolation is hardware-grade, not container-grade — stronger than Daytona for security-conscious Code Mode. Sub-100 ms cold boot (measured from boot/init/ready timestamps in the in-VM `agentd`). Disk-only snapshot (`upper.ext4` CoW overlay) matches the use-case: Code Mode sessions are "install deps, edit files, run code" — live-RAM restoration of a running process tree is not needed at this tier.

The default ordering is therefore: **microsandbox local → E2B cloud (opt-in `CodeSandbox(backend="e2b")`) → Daytona container (opt-in `CodeSandbox(backend="daytona")`)**. The cloud tier is a config flag, not a rewrite.

**Alternatives rejected:**
- E2B as default: requires `E2B_API_KEY` at import time; kills the local-dev story and the "zero-infra dogfood" phase requirement.
- Daytona as default: requires a running Daytona server (`apps/api` NestJS + `apps/runner` Go daemon + Docker); container isolation is weaker than microVM. Valid for teams already running Daytona.
- V8 isolate (Codex Code Mode) as default: JS-only, no Python stdlib, no pip installs — too narrow for general Code Mode. Keep as an opt-in ephemeral-tool-function path (see Decision 3).

**Evidence:** `infra-sandboxes-multiagent.md` §microsandbox — "pip install microsandbox is genuinely self-contained"; "no server, no daemon, no orchestrator"; "boot_time_ns / init_time_ns / ready_time_ns" from agentd ready-frame; "Three sandbox backends now map cleanly for Verso's CodeSandbox protocol: E2B (cloud, microVM, memory snapshot) · Daytona (server, container, disk snapshot) · microsandbox (local, microVM, disk snapshot, no daemon, <100 ms cold boot)."

---

### Decision 2 — Snapshot semantics per tier

**Choice:** All three adapters expose `snapshot()` / `resume(snapshot_id)`. The semantics differ by tier and are **declared in the adapter**, not hidden:

| Adapter | Snapshot captures | Resume | Implementation |
|---|---|---|---|
| `microsandbox` (default) | writable filesystem overlay (`upper.ext4`) | cold microVM boot from captured overlay | `await handle.snapshot("name")` → overlay dir copy |
| `e2b` | live guest RAM + disk (UFFD full) | warm resume ~150 ms (lazy UFFD page-fault) | `SandboxConfig{snapshot:true, auto_pause:true}` |
| `daytona` | filesystem only | cold container recreate from `docker commit` image | `sandbox.backup()` → registry push; restore = `start(Snapshot:imageName)` |

The protocol's `snapshot()` method returns a `SnapshotResult(id, kind: Literal["disk","memory"])` so callers know what they got. `resume(snapshot_id)` is always valid; the adapter handles the boot semantics.

**Rationale:** The snapshot axis is the most important architectural axis in the whole cluster (`infra-sandboxes-multiagent.md` §Cross-System Patterns). Conflating disk-snapshot and memory-snapshot silently (e.g. advertising "resume" when it's actually a cold boot) is a DX lie. Surface the distinction explicitly; let users choose the right tier for their use-case.

**Alternatives rejected:** A unified "smart snapshot" that always does the cheapest thing — wrong because E2B's UFFD live-RAM restore and microsandbox's cold boot from overlay are not interchangeable when the task needs a *running* process tree (e.g. a warm Python REPL with a loaded ML model). The kind tag makes the contract honest.

**Evidence:** `infra-sandboxes-multiagent.md` §Cross-System Patterns: "The CodeSandbox.snapshot() protocol must declare which it is. Only UFFD-class preserves a running process tree; the rest preserve disk and cold-boot." E2B UFFD: `packages/orchestrator/pkg/sandbox/uffd/uffd.go`, `PageSize=4096`, lazy page-fault, ~150 ms warm resume. microsandbox: "A snapshot is a portable, on-disk capture of a sandbox's writable filesystem... memory contents are explicitly not captured."

---

### Decision 3 — Ephemeral tool-function path (the V8/JS Code Mode analogue)

**Choice:** Ship an `exec_code` built-in tool backed by a Python subprocess inside the default `microsandbox`, **not** a V8 isolate, for v1. The Python path subsumes the JS Code Mode use-case for Verso's Python-first users. The key Code Mode insight — *one LLM sampling round-trip that orchestrates N tool calls in parallel via the sandbox's tool bindings* — is preserved by having `exec_code` call the agent's tool registry from inside the sandbox.

The V8/JS Code Mode (Codex `exec`+`wait`, `DEFAULT_EXEC_YIELD_TIME_MS=10_000`, `DEFAULT_MAX_OUTPUT_TOKENS_PER_EXEC_CALL=10_000`) is a **Phase 3+ opt-in** for teams that want JS-isolate speed and want to avoid a microVM. It maps directly onto Cloudflare's Worker Loader `get(id, getCode)` pattern (id-keyed, evictable, reconstructable from code-string) and is the right shape for `tool_as_code` one-shot transforms with no install step.

**Rationale:** Codex's Code Mode yields the biggest benefit when N tool round-trips are the bottleneck. In Verso's case, the fan-out pattern (Decision 6) already collapses parallel tool dispatch to one asyncio gather — the latency benefit is partially addressed. The microsandbox Python subprocess gives the user a real Python runtime with pip, whereas V8 has no stdlib and no package installs. For v1 dogfood, Python-in-microVM is the higher-value path. Adding rusty_v8 or QuickJS is a Phase 3 decision.

**Evidence:** `coding-codex.md` §Code Mode: "No Node APIs, no fs, no network, no console. Hard isolation... the single most impactful addition for high-tool-count tasks." `_SYNTHESIS.md` §Copies item 15: "Verso should provide an exec tool backed by a sandboxed JS runtime (rusty_v8, QuickJS, or a Python equivalent) as an opt-in escape hatch." PRD §10.9 explicitly defers the sandbox provider decision.

---

### Decision 4 — Credential boundary (egress proxy, not secrets-in-sandbox)

**Choice:** The `CodeSandbox` protocol enforces a **no-secrets-in-sandbox rule**. The sandbox always boots with `egress_policy="deny_all"` by default. To call an external API from inside the sandbox, the agent parent spawns an **egress proxy** that holds the credentials and is reachable inside the sandbox as `http://verso.internal:<port>`. The sandbox is allowed to reach only that proxy address; the proxy routes, authenticates, and forwards.

For microsandbox: implemented via the userspace smoltcp network stack. `NetworkPolicy{default_action: Deny, rules: [Rule{action:Allow, destination:Domain("verso.internal"), ports:[proxy_port], protocol:Tcp}]}`. The proxy is a host-side asyncio HTTP server that splices credentials into forwarded requests. The sandbox never sees the real API key.

For E2B: use `SandboxNetworkConfig` with an `allow_internet_access=false` flag (`orchestrator.proto:144`) and a `POST /init` token injection via MMDS (`process.go:605`, `setMmds` injects `envd_access_token` hash). Verso's cloud proxy lives at the `envd_access_token`-authenticated boundary.

For Daytona: the runner has no equivalent network isolation; document this as a limitation and require users to manage credential injection manually via `env_vars` in `CreateSandboxFromSnapshotParams`. Upgrade path: run a proxy container on the same Docker network.

**Rationale:** The strongest pattern in the cluster is the CF `globalOutbound` model: the sandbox gets *capability stubs*, not raw secrets. The sandbox calls `tools.search(...)`, the parent holds the API key, the proxy splices it before the packet leaves the host. This is strictly safer than injecting the key as an env var (which ends up in the snapshot) or trusting the microVM boundary alone. microsandbox's userspace netstack makes this a one-struct-field change, not a host-firewall config race.

**Alternatives rejected:**
- Inject credentials as env vars into the sandbox: they end up in the snapshot and in the process environment visible to arbitrary code the model generates. Rejected.
- Rely on microVM isolation and let the sandbox hold real keys: correct *today*, but snapshot leakage and future escape vulnerabilities make "trust the VM + the snapshot" weaker than "credential never enters the VM."
- Full iptables/nftables firewall per sandbox: requires root, platform-specific, races with container runtimes. microsandbox's userspace approach is strictly preferable.

**Evidence:** `infra-sandboxes-multiagent.md` §microsandbox §Network policy: "NetworkPolicy{default_action, rules: Vec<Rule>}... per-field serde default is Deny (fail-closed)"; "the sandbox never gets raw network; the host proxy decides what each connection reaches and can splice credentials in." §E2B: "Access-token hash is injected via FC MMDS at resume... never snapshot secrets; inject at resume and validate in the daemon." §Cloudflare `globalOutbound`: "the proxy worker... holds the real API keys/access tokens and *adds them into requests*." §Cross-System Patterns §Egress credential injection: "never put the secret in the sandbox."

---

### Decision 5 — Daemon-in-sandbox protocol

**Choice:** Verso's in-sandbox agent daemon (`verso-daemon`) uses a **two-tier protocol** copied from E2B's `envd` shape:
1. **REST lifecycle tier (port `49983`, same as `envd`):** `POST /init` (bootstrap + credential gate + env injection), `GET /health` (readiness poll), `GET /version`.
2. **Streaming RPC hot path:** a lightweight line-delimited JSON stream over a Unix relay socket (microsandbox) or TCP (E2B/Daytona). Process events follow the `ProcessEvent` oneof pattern: `StartEvent{pid}` → N× `DataEvent{stdout|stderr bytes, stream:"stdout"|"stderr"}` → `EndEvent{exit_code, success}`. Processes addressable by `pid` **or** a client-assigned `tag` for reconnect after network blip.

The daemon binary is **bind-mounted read-only** into the container at a fixed path (Daytona: `common.DAEMON_PATH`), not baked into the image. Readiness = poll `GET /health` on the container/VM IP. The microsandbox `agentd` uses a binary frame protocol over the `AGENT_PORT_NAME` virtio-console relay — Verso adopts the same "relay socket" approach for the local adapter.

Keepalive: `KEEPALIVE_PING_INTERVAL_SEC=50` (copied from E2B `connection_config.py:13`); `REQUEST_TIMEOUT=60.0`.

**Rationale:** The two-tier split is proven across three independent implementations (E2B envd ConnectRPC, Daytona toolbox Gin REST, microsandbox agentd binary frames). The REST lifecycle tier is simple and stateless; the streaming RPC hot path needs process-addressability by tag for reconnect. Daytona's `tag`-based reconnect pattern is the right call — without it a network blip kills a long-running `exec` irreversibly. Injecting the daemon by bind-mount keeps every base image usable without modification.

**Evidence:** `infra-sandboxes-multiagent.md` §E2B envd: `CONNECTION_CONFIG.envd_port=49983`; `KEEPALIVE_PING_INTERVAL_SEC=50`; `REQUEST_TIMEOUT=60.0`; ProcessEvent oneof Start/Data/End; `pid|tag` addressing. §Daytona: "daemon binary is bind-mounted read-only into every container... runner polls the daemon's /version before marking the sandbox ready." §microsandbox: `AGENT_PORT_NAME` virtio-console relay socket. §Cross-System Patterns §Daemon-in-sandbox: "standardize on one in-sandbox agent with a two-tier protocol."

---

### Decision 6 — Multi-agent topologies to ship in v1

**Choice:** Three topologies ship in `verso.orchestrate`, all opt-in, all depth-capped at 1 by default:

1. **`subagent_delegate(task, agent, fork_mode="none"|"last_n"|"full")`** — single sub-agent spawned for context isolation. The sub-agent runs its own full ReAct loop; the parent never sees the sub-agent's internal steps. Returns a **typed compact summary** (`SubagentResult(summary: str, files: list[FileRef], artifacts: list[Artifact])`) — NOT the raw history. `fork_mode` controls how much parent history is injected: `none` (default, clean context), `last_n` (last N turns), `full` (complete history — only for short-horizon delegation). No parent-history inheritance by default because inherited history pollutes the sub-agent's context and costs tokens in the worker's window.

2. **`fan_out(tasks: list[Task], workers: list[Agent] | Agent, max_concurrency: int = 5)`** — parallel dispatch; `asyncio.gather` under the hood with a `Semaphore(max_concurrency)`; results collected in input order (order preservation is non-negotiable — `results[i]` corresponds to `tasks[i]` regardless of completion order). The parent synthesizes; workers never write the final report.

3. **`Orchestration(lead: Agent, workers: list[Agent], pattern: "orchestrator_workers")`** — the durable-layer shape. Workers write to a **shared typed state store** (a `dict[str, Any]` with typed access helpers, not message passing). Lead reads the store and synthesizes. The lead IS the final synthesizer, not a separate aggregation model — mirrors Grok's "leader IS one of the N agents and IS the synthesizer."

Depth cap is enforced: `max_depth: int = 1` on all three. A sub-agent spawned by `subagent_delegate` cannot itself call `subagent_delegate`. Violation raises `DepthCapExceeded`. This is configurable (`max_depth=2`) but not defaulted higher.

**Not shipped in v1:**
- Nested orchestrators (no `Orchestration` inside a worker's loop).
- Convergence-based termination (never — termination is always `turns ∧ time ∧ tokens`, resource-bound only, per Grok's model).
- Symmetric peer ensemble with leader election — the evidence conflict (`_SYNTHESIS.md` §10.4: "Anthropic +90.2% vs Agent-S3 +13% from removing hierarchy") means instrument before shipping.
- Adversarial self-play.
- Sub-agents writing the final output report.

**Rationale:** The PRD specifies exactly these three topologies (§6.2). The depth cap of 1 is the convergence point across all RE'd systems: Claude Code hard-bans nesting, Anthropic Research depth-limit=1, Codex `max_depth=1`. The `SubagentResult` compact-summary return type is the key correctness invariant — returning the sub-agent's full token stream to the parent defeats the purpose of context isolation and re-introduces the token cost the delegation was meant to avoid.

**Evidence:** `_SYNTHESIS.md` §Avoid #15: "Claude Code hard-bans nesting; Anthropic Research depth-limit=1; Codex max_depth=1. Exponential token cost." PRD §6.2: "Sub-agent = context isolation... typed compact summary... Depth cap default = 1." `_SYNTHESIS.md` §Avoid #18: "Letting subagents write the final report. Hard architectural boundary: orchestrator synthesizes, workers research." PRD §6.2: "parallel fan-out: fan_out(tasks, max_concurrency=4..6)."

---

## Component Spec

### `CodeSandbox` adapter protocol

```python
# verso/orchestrate/sandbox.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import AsyncIterator, Literal, Optional
from enum import Enum


class SnapshotKind(str, Enum):
    DISK = "disk"      # filesystem-only (microsandbox / Daytona)
    MEMORY = "memory"  # live-RAM + disk (E2B UFFD)


@dataclass
class SnapshotResult:
    id: str
    kind: SnapshotKind
    backend: str  # "microsandbox" | "e2b" | "daytona"


@dataclass
class ExecOutput:
    exit_code: int
    success: bool
    stdout: str
    stderr: str
    artifacts: list[Artifact] = field(default_factory=list)


@dataclass
class Artifact:
    # Daytona/Verso chart-extraction pattern:
    # code emits `verso_artifact_<nonce>: <json>` on stdout;
    # daemon strips the marker lines and returns structured artifacts.
    type: str   # "chart" | "file" | "rich_object"
    data: dict


@dataclass
class ProcessEvent:
    # Two-tier daemon protocol hot-path event shape (E2B ProcessEvent oneof)
    kind: Literal["start", "data", "end"]
    pid: Optional[int] = None            # start only
    stream: Optional[Literal["stdout", "stderr"]] = None  # data only
    bytes: Optional[bytes] = None        # data only
    exit_code: Optional[int] = None      # end only
    success: Optional[bool] = None       # end only


@dataclass
class EgressPolicy:
    # microsandbox NetworkPolicy shape; default = deny_all
    default_action: Literal["deny", "allow"] = "deny"
    # each rule: (action, destination_domain_or_cidr, ports, protocol)
    rules: list[EgressRule] = field(default_factory=list)


@dataclass
class EgressRule:
    action: Literal["allow", "deny"]
    destination: str       # domain, domain_suffix (prefix with "*."), or CIDR
    ports: list[int] = field(default_factory=list)   # empty = any port
    protocol: Literal["tcp", "udp", "any"] = "any"


class CodeSandbox:
    """
    Pluggable adapter protocol for Code Mode sandboxes.
    Concrete implementations: MicrosandboxAdapter, E2BAdapter, DaytonaAdapter.
    All three expose this surface; snapshot semantics differ per backend
    and are declared in SnapshotResult.kind.
    """

    async def create(
        self,
        image: str = "python:3.12",
        *,
        cpus: int = 1,
        memory_mb: int = 512,
        timeout_s: int = 300,
        env: dict[str, str] | None = None,
        workdir: str = "/work",
        egress_policy: EgressPolicy | None = None,  # default: deny_all
        snapshot_id: str | None = None,  # resume from snapshot if provided
    ) -> "SandboxHandle": ...

    async def exec(
        self,
        cmd: str | list[str],
        *,
        tag: str | None = None,   # client-assigned; enables pid|tag reattach
        env: dict[str, str] | None = None,
        cwd: str | None = None,
        timeout_s: float = 60.0,
    ) -> ExecOutput: ...

    async def exec_stream(
        self,
        cmd: str | list[str],
        *,
        tag: str | None = None,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
    ) -> AsyncIterator[ProcessEvent]: ...

    async def run_code(
        self,
        code: str,
        *,
        language: Literal["python", "bash", "node"] = "python",
        env: dict[str, str] | None = None,
        timeout_s: float = 60.0,
    ) -> ExecOutput:
        # Wraps exec with magic-marker artifact extraction.
        # Injects verso_artifact_<nonce>: prefix protocol into code preamble.
        # Daemon demuxes marker lines from stdout into ExecOutput.artifacts.
        ...

    async def write_file(self, path: str, content: bytes | str) -> None: ...
    async def read_file(self, path: str) -> bytes: ...
    async def list_files(self, path: str = "/work") -> list[str]: ...

    async def snapshot(self, name: str | None = None) -> SnapshotResult: ...

    async def kill(self) -> None: ...

    async def __aenter__(self) -> "SandboxHandle": ...
    async def __aexit__(self, *args) -> None: ...


# Factory function — the user-facing entry point
def make_sandbox(
    backend: Literal["microsandbox", "e2b", "daytona"] | None = None,
    **kwargs,
) -> CodeSandbox:
    """
    Default: "microsandbox" (local, zero-infra).
    Override via VERSO_SANDBOX_BACKEND env var or explicit backend= argument.
    """
    ...
```

---

### `MicrosandboxAdapter` — local default

```python
# verso/orchestrate/sandbox_microsandbox.py

# KNOWN: microsandbox==0.5.4 API (infra-sandboxes-multiagent.md §microsandbox §Python SDK)

MICROSANDBOX_DEFAULT_CPUS = 1
MICROSANDBOX_DEFAULT_MEMORY_MB = 512
MICROSANDBOX_UPPER_SIZE_MIB = 8192     # writable overlay size (KNOWN: Image.oci default)
MICROSANDBOX_SECURITY = "RESTRICTED"   # no_new_privs, drop mount-admin cap, nosuid,nodev
MICROSANDBOX_DEFAULT_TIMEOUT_S = 300

# Egress proxy constants
VERSO_INTERNAL_PROXY_HOST = "verso.internal"  # alias in smoltcp NetworkPolicy
VERSO_INTERNAL_PROXY_PORT = 18443

# Daemon protocol
ENVD_PORT = 49983                              # KNOWN: e2b connection_config.py:54
KEEPALIVE_PING_INTERVAL_SEC = 50               # KNOWN: e2b connection_config.py:13
REQUEST_TIMEOUT_S = 60.0                       # KNOWN: e2b SDK default

class MicrosandboxAdapter(CodeSandbox):
    """
    Wraps microsandbox.Sandbox.
    Spawn model: re-exec the `msb` binary in child process mode (rootless KVM).
    Network: smoltcp userspace stack with deny-all default + verso.internal proxy allow-rule.
    Snapshot: disk-only (upper.ext4 overlay), kind=DISK.
    Daemon: verso-daemon bind-mounted read-only, polled on /health before ready.
    """

    async def create(self, image="python:3.12", *, cpus=1, memory_mb=512,
                     timeout_s=300, env=None, workdir="/work",
                     egress_policy=None, snapshot_id=None) -> "SandboxHandle":
        from microsandbox import Sandbox
        policy = egress_policy or EgressPolicy(default_action="deny")
        # Inject verso.internal allow-rule if a proxy is configured
        sb = await Sandbox.create(
            f"verso-{uuid4().hex[:8]}",
            image=image if not snapshot_id else None,
            snapshot=snapshot_id,
            cpus=cpus,
            memory=memory_mb,
            workdir=workdir,
            env=env or {},
            security=MICROSANDBOX_SECURITY,
        )
        # Poll /health (bind-mounted verso-daemon)
        await self._wait_for_daemon(sb)
        return SandboxHandle(adapter=self, _sb=sb)

    async def snapshot(self, name=None) -> SnapshotResult:
        name = name or f"verso-snap-{uuid4().hex[:8]}"
        await self._sb.snapshot(name)
        return SnapshotResult(id=name, kind=SnapshotKind.DISK, backend="microsandbox")
```

---

### `E2BAdapter` — cloud adapter

```python
# verso/orchestrate/sandbox_e2b.py

# KNOWN: e2b==2.25.1 API (infra-sandboxes-multiagent.md §E2B §Python SDK surface)

E2B_DEFAULT_TIMEOUT_S = 300      # KNOWN: Sandbox.create(timeout=300)
E2B_MAX_TIMEOUT_HOBBY_S = 3600   # KNOWN: max 3_600 (Hobby)
E2B_MAX_TIMEOUT_PRO_S = 86400    # KNOWN: max 86_400 (Pro)
E2B_COMMANDS_TIMEOUT_S = 60      # KNOWN: sandbox.commands.run default timeout=60

class E2BAdapter(CodeSandbox):
    """
    Wraps e2b.Sandbox.
    Network: SandboxConfig{allow_internet_access=False} + MMDS credential injection.
    Snapshot: live-RAM UFFD + 4KiB-diff-vs-base, kind=MEMORY, ~150ms warm resume.
    Credentials: NEVER put in the sandbox. Inject hash via MMDS at resume; validate
                 at envd /init every wake. Source: infra-sandboxes-multiagent.md §E2B
                 process.go:605 setMmds.
    """

    async def snapshot(self, name=None) -> SnapshotResult:
        # E2B: auto_pause=True means on_timeout→pause (snapshot) instead of kill
        # SandboxConfig{snapshot:true} for resume from snapshot
        snap_id = await self._sbx.pause()   # pause() → creates checkpoint, returns id
        return SnapshotResult(id=snap_id, kind=SnapshotKind.MEMORY, backend="e2b")
```

---

### `ExecOutput` artifact extraction (magic-marker protocol)

```python
# verso/orchestrate/sandbox_artifacts.py
# Adapted from Daytona apps/daemon/pkg/toolbox/process/coderun/artifacts.go

ARTIFACT_MARKER_PREFIX = "verso_artifact_k39fd2:"   # KNOWN: Daytona uses "dtn_artifact_k39fd2:"

MATPLOTLIB_PREAMBLE = """
import sys as _sys
try:
    import matplotlib.pyplot as _plt
    import json as _json, base64 as _b64, io as _io
    _orig_show = _plt.show
    def _patched_show(*a, **kw):
        for fig in _plt.get_fignums():
            buf = _io.BytesIO()
            _plt.figure(fig).savefig(buf, format='png')
            buf.seek(0)
            data = _b64.b64encode(buf.read()).decode()
            print(f'{MARKER}' + _json.dumps({{"type":"chart","data":{{"format":"png","b64":data}}}}), flush=True)
        _orig_show(*a, **kw)
    _plt.show = _patched_show
except ImportError:
    pass
""".replace("{MARKER}", ARTIFACT_MARKER_PREFIX)

def parse_artifacts(raw_stdout: str) -> tuple[str, list[Artifact]]:
    """
    Split stdout into clean_stdout (artifact lines removed) + structured artifacts.
    KNOWN pattern: Daytona artifacts.go:18 ParseArtifacts.
    """
    lines, artifacts = [], []
    for line in raw_stdout.splitlines():
        if line.startswith(ARTIFACT_MARKER_PREFIX):
            import json
            try:
                a = json.loads(line[len(ARTIFACT_MARKER_PREFIX):])
                artifacts.append(Artifact(type=a["type"], data=a["data"]))
            except Exception:
                lines.append(line)
        else:
            lines.append(line)
    return "\n".join(lines), artifacts
```

---

### Multi-agent orchestration primitives

```python
# verso/orchestrate/delegate.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Any


# KNOWN: depth cap from Claude Code (hard ban), Anthropic Research (depth-limit=1),
# Codex max_depth=1. Source: _SYNTHESIS.md §Avoid #15.
DEFAULT_DEPTH_CAP = 1
MAX_DEPTH_CAP = 3       # configurable upper bound; warn if set >2

# KNOWN: fan-out concurrency from PRD §6.2 "max_concurrency=4..6"
FAN_OUT_DEFAULT_CONCURRENCY = 5


@dataclass
class FileRef:
    path: str
    description: str = ""


@dataclass
class SubagentResult:
    """
    Typed compact summary returned by a sub-agent to its parent.
    The sub-agent's full internal history is NEVER returned — doing so defeats
    context isolation and re-incurs the full token cost.
    KNOWN anti-pattern: _SYNTHESIS.md §Avoid #18 "sub-agents write the final report."
    """
    summary: str
    files: list[FileRef] = field(default_factory=list)
    artifacts: list[Any] = field(default_factory=list)
    stop_reason: str = "end_turn"
    usage: dict[str, int] = field(default_factory=dict)


async def subagent_delegate(
    task: str,
    agent: "Agent",
    *,
    fork_mode: Literal["none", "last_n", "full"] = "none",
    last_n: int = 5,   # used when fork_mode="last_n"
    depth: int = 0,
    max_depth: int = DEFAULT_DEPTH_CAP,
) -> SubagentResult:
    """
    Spawn agent as a sub-agent for context isolation.
    depth tracks nesting level; raises DepthCapExceeded if depth >= max_depth.
    fork_mode controls parent-history injection:
      "none"   → clean context (default; sub-agent pays zero parent-history tokens)
      "last_n" → inject last N parent turns
      "full"   → inject complete parent history (short-horizon only)
    Returns SubagentResult (typed compact summary), never the raw history.
    """
    if depth >= max_depth:
        raise DepthCapExceeded(
            f"Subagent depth {depth} >= max_depth {max_depth}. "
            "Increase max_depth or redesign the orchestration topology."
        )
    ...


async def fan_out(
    tasks: list[str | "Task"],
    workers: list["Agent"] | "Agent",
    *,
    max_concurrency: int = FAN_OUT_DEFAULT_CONCURRENCY,
    depth: int = 0,
    max_depth: int = DEFAULT_DEPTH_CAP,
) -> list[SubagentResult]:
    """
    Parallel dispatch of tasks to workers.
    Results are returned in INPUT ORDER (results[i] ↔ tasks[i]) regardless
    of completion order — order preservation is non-negotiable.
    KNOWN: _SYNTHESIS.md §multi-agent "synchronize only at dependency boundaries."
    The parent synthesizes; workers never write the final output.
    """
    import asyncio
    sem = asyncio.Semaphore(max_concurrency)
    # ... gather with semaphore, collect in order ...


class DepthCapExceeded(RuntimeError):
    """Raised when subagent nesting exceeds max_depth."""


class Orchestration:
    """
    Orchestrator-workers topology. Lead agent synthesizes; workers write to
    a shared typed state store (not message-passing).
    KNOWN: PRD §6.2 "orchestrator-workers is the default durable-layer shape;
    shared typed state store for coordination."
    Termination: turns ∧ time ∧ tokens (resource-bound only).
    NOT convergence-based. KNOWN: _SYNTHESIS.md §Avoid #13 (Grok: no convergence metric).
    """

    def __init__(
        self,
        lead: "Agent",
        workers: list["Agent"],
        pattern: Literal["orchestrator_workers"] = "orchestrator_workers",
        max_depth: int = DEFAULT_DEPTH_CAP,
        max_concurrency: int = FAN_OUT_DEFAULT_CONCURRENCY,
    ): ...

    async def run(
        self,
        task: str,
        *,
        max_turns: int = 10,
        max_budget_usd: float | None = None,
    ) -> SubagentResult:
        """
        Lead dispatches sub-tasks to workers via fan_out.
        Workers write results to shared_state (typed dict).
        Lead reads shared_state and calls synthesize().
        Lead IS the synthesizer — no extra aggregation model.
        KNOWN anti-pattern: "A separate orchestrator + judge as extra model calls."
        Source: _SYNTHESIS.md §Avoid #14 (Grok: leader IS the synthesizer).
        """
        ...

    @property
    def shared_state(self) -> "SharedTypedState":
        """
        The coordination primitive. Workers write; lead reads.
        Not message-passing. A simple typed dict with version stamps
        and optional conflict-resolution (last-writer-wins default).
        """
        ...
```

---

### Constants summary (all attributed)

| Constant | Value | Source |
|---|---|---|
| `ENVD_PORT` | `49983` | E2B `connection_config.py:54` (KNOWN) |
| `KEEPALIVE_PING_INTERVAL_SEC` | `50` | E2B `connection_config.py:13` (KNOWN) |
| `REQUEST_TIMEOUT_S` | `60.0` | E2B SDK default (KNOWN) |
| `E2B_DEFAULT_TIMEOUT_S` | `300` | E2B `Sandbox.create(timeout=300)` (KNOWN) |
| `E2B_MAX_TIMEOUT_HOBBY_S` | `3600` | E2B SDK (KNOWN) |
| `E2B_MAX_TIMEOUT_PRO_S` | `86400` | E2B SDK (KNOWN) |
| `E2B_COMMANDS_TIMEOUT_S` | `60` | E2B `commands.run default timeout=60` (KNOWN) |
| `MICROSANDBOX_DEFAULT_CPUS` | `1` | microsandbox SDK default (KNOWN) |
| `MICROSANDBOX_DEFAULT_MEMORY_MB` | `512` | microsandbox SDK default (KNOWN) |
| `MICROSANDBOX_UPPER_SIZE_MIB` | `8192` | `Image.oci` default (KNOWN) |
| `DEFAULT_DEPTH_CAP` | `1` | Claude Code / Anthropic Research / Codex (KNOWN, converged) |
| `FAN_OUT_DEFAULT_CONCURRENCY` | `5` | PRD §6.2 "4..6"; `max_workers=5` Composio (KNOWN) |
| `MAX_STEPS_SUBAGENT` | `25` | Inherits from PRD §5.1 loop default (DESIGNED) |
| `EXEC_YIELD_TIME_MS` | `10_000` | Codex `DEFAULT_EXEC_YIELD_TIME_MS` (KNOWN, if V8 path added in Phase 3) |
| `MAX_OUTPUT_TOKENS_EXEC` | `10_000` | Codex `DEFAULT_MAX_OUTPUT_TOKENS_PER_EXEC_CALL` (KNOWN, Phase 3) |
| `E2B_PAGE_SIZE_BYTES` | `4096` | E2B `shared/pkg/storage/header/diff.go:9` (KNOWN; informational) |
| `VERSO_INTERNAL_PROXY_PORT` | `18443` | DESIGNED (no RE source; pick well-known-free port) |

---

## Open Unknowns

1. **Egress proxy implementation depth for v1.** The deny-all default with `verso.internal` proxy is specified; the proxy itself (a host-side asyncio HTTP server that splices credentials) needs a prototype to confirm the microsandbox smoltcp `Domain`-rule-based routing actually resolves `verso.internal` at SYN time (before SNI). The documented behavior says domain rules are matched from a "resolved-hostname cache from the guest's DNS lookups" — needs a real integration test to confirm the `verso.internal` alias is resolved before the first guest SYN.

2. **Daytona credential injection path.** Daytona has no equivalent to microsandbox's userspace netstack or E2B's MMDS credential injection. The current spec documents this as a limitation requiring users to inject via `env_vars` in `CreateSandboxFromSnapshotParams`. The correct solution (a sidecar proxy container on the same Docker network) needs to be prototyped against a real Daytona instance to confirm the network topology is what we expect.

3. **`verso-daemon` binary: build tool and image injection.** The spec calls for bind-mounting a `verso-daemon` binary read-only into the microVM/container. The build step (what produces the binary — PyO3 extension? standalone Go binary? Python + shiv?) and the mount injection mechanism for microsandbox (virtio-fs tag? host directory mount?) need a concrete decision. E2B uses a Go binary (`envd`); Daytona uses a Go Gin server. For Verso's Python-first repo, a shiv-packaged Python script may be simpler than a compiled binary, but startup latency under microsandbox's libkrun needs measurement.

4. **Shared typed state store for `Orchestration`.** The spec calls for a typed dict with version stamps; the actual storage backend (in-memory dict vs SQLite row per key vs the same `memory/` backend from `‹edge2›`) needs a decision after Phase 2's durable substrate lands. The design should not add a new storage primitive — `SharedTypedState` should be a thin wrapper over whatever the durable runtime's checkpoint store provides.

5. **`fan_out` result ordering guarantee under cancellation.** If one worker is cancelled mid-flight (e.g. due to `max_budget_usd` exhaustion), the order-preservation contract (`results[i] ↔ tasks[i]`) needs to define what `results[i]` is for the cancelled worker: a sentinel `SubagentResult(stop_reason="cancelled")` or a raised exception. Needs dogfood to find the right ergonomic.

6. **Multi-agent topology instrumentation before recommending either.** PRD §10.4 and `_SYNTHESIS.md` §10.4 both note the evidence genuinely conflicts (Anthropic +90.2% from hierarchy vs Agent-S3 +13% from *removing* hierarchy). The three topologies are shipped; which one to recommend for which task class requires running evals on real workloads. This is explicitly deferred to post-dogfood.
