# Sandboxes & Agent Control — Verso Research Note
## Cluster: infra-sandboxes-multiagent
### Systems: E2B · Daytona · microsandbox · Cloudflare Dynamic Workers + Sandboxes · Parlant
*Sources: cloned `e2b-dev/infra` (Go orchestrator) + `e2b-dev/E2B` (Python SDK) + `daytonaio/daytona` + `superradcompany/microsandbox` (Rust) + `emcie-co/parlant`, read line-by-line; `e2b==2.25.1` / `daytona==0.184.0` / `microsandbox==0.5.4` wheels; Cloudflare blog + Sandbox SDK docs (closed runtime). Cross-refs: `03_teardowns/infra-serving.md` (streaming/cancellation), `05_re_targets/multiagent-and-sandboxes.md` (the brief), the already-covered `MODAL.md` / `MISTRAL_AGENTS_API.md` teardowns in `~/Desktop/researchfms/teardowns/`.*

> Scope per the brief: extract the *specific mechanisms* for Verso's Code-Mode escape hatch — microVM/container snapshot-resume, daemon-in-sandbox wire protocol, egress credential injection — and the per-turn context-narrowing engine (Parlant). "It runs code in a sandbox" is not a finding; the UFFD page-fault handler, the 4 KiB diff-against-base dedup, the ConnectRPC daemon protocol, the `globalOutbound:null` egress proxy, and the guideline-match algorithm are.

---

## E2B

### What It Is

E2B is hosted Firecracker-microVM sandbox infrastructure for agent code execution. Each sandbox is an isolated VM that is *resumed* from a pre-warmed memory+rootfs snapshot, not cold-booted — the resume is lazy: the VM's guest memory is never fully loaded, it is faulted in 4 KiB (or 2 MiB hugepage) at a time by a userspace `userfaultfd` page-fault handler reading from a deduplicated snapshot file. The open-source `e2b-dev/infra` repo (Go) is the orchestrator; the cloud control plane (Nomad scheduling, multi-tenant routing) is closed but the per-node sandbox machinery is fully readable. The Python SDK (`Sandbox.create()`, `sandbox.commands.run()`, `sandbox.files.*`) is the contract Verso's cloud Code-Mode adapter should mirror.

The architecture has three layers worth reimplementing: **(1)** the FC process lifecycle (REST to the Firecracker API socket), **(2)** the UFFD snapshot/resume mechanism (the actual moat — sub-150 ms resume via lazy page fault + diff dedup), and **(3)** the `envd` daemon-inside-the-VM (ConnectRPC over a fixed port) that the SDK talks to for process/filesystem control.

### Snapshot block sizes (KNOWN — `packages/shared/pkg/storage/header/diff.go:9-13`)

```go
const (
    PageSize        = 4 << 10 // 4 KiB   — guest 4K pages, also the diff granularity
    HugepageSize    = 2 << 20 // 2 MiB   — guest 2M hugepages (transparent hugepage VMs)
    RootfsBlockSize = 4 << 10 // 4 KiB   — rootfs block-device diff granularity
)
var EmptyHugePage = make([]byte, HugepageSize)
```

These three constants are the entire diff vocabulary. A snapshot is `base template + a sparse diff` where the diff is a set of 4 KiB pages that differ from the base.

### FC Process Lifecycle — REST to the Firecracker socket (KNOWN — `packages/orchestrator/pkg/sandbox/fc/process.go`, `fc/client.go`)

Each sandbox is a `fc.Process` struct (`process.go:121`) wrapping an `exec.Cmd`. The command is **not** `firecracker` directly — it is `unshare -m -- bash -c <startScript>` (`process.go:181`) with `Setsid: true`, so the VMM runs in its own mount namespace and session. Cgroup placement is atomic via `CLONE_INTO_CGROUP` (`UseCgroupFD = true`, `CgroupFD = cgroupFD`, `process.go:239`) — the cgroup is created and owned by the parent `Sandbox`, the FC process is born directly inside it.

The orchestrator talks to Firecracker's HTTP API over a **Unix socket** (`firecracker.NewUnixSocketTransport(socketPath)`, `client.go:34`) using a go-swagger-generated client. The boot sequence (`Create`, `process.go:303`) is an ordered series of REST calls, each a separate Firecracker API request:

| Order | Call (`client.go`) | FC endpoint | Purpose |
|---|---|---|---|
| 1 | `setMetrics` | `PUT /metrics` | metrics FIFO (created via `mkfifo` 0600 *before* start) |
| 2 | `setBootSource` | `PUT /boot-source` | kernel path + kernel args (see below) |
| 3 | `setRootfsDrive` | `PUT /drives/rootfs` | rootfs path, `IsRootDevice=true`, optional io-engine + rate limiter |
| 4 | `setNetworkInterface` | `PUT /network-interfaces/<id>` + `PUT /mmds/config` (V2) | tap device + MAC + MMDS V2 |
| 5 | `setMachineConfig` | `PUT /machine-config` | vCPU, mem MiB, `Smt` (false on ARM), `TrackDirtyPages=false`, `HugePages=2M` if requested |
| 6 | `setEntropyDevice` | `PUT /entropy` | virtio-rng with rate limiter |
| 7 | `installBalloon` (optional) | `PUT /balloon` | 0-MiB balloon for free-page-reporting/hinting |
| 8 | `startVM` | `PUT /actions {InstanceStart}` | actually boots |

Kernel args (`process.go:353-378`) are production-tuned for fast boot: `quiet loglevel=1 pci=off i8042.nokbd i8042.noaux random.trust_cpu=on panic=1 reboot=k`. The critical one for snapshots is **`rootflags=discard`** — ext4 issues TRIM on freed blocks so freed pages are elided from the snapshot diff (smaller diffs → faster restore + cheaper storage). `clocksource=kvm-clock` is opt-in.

### Snapshot creation — pause → dirty-page export → dedup against base (KNOWN)

Pausing a sandbox to a snapshot (`Process.Pause` → `client.pauseVM` = `PATCH /vm {State:Paused}`, `client.go:114`) then `CreateSnapshot` (= `PUT /snapshot/create {SnapshotType:Full}`, `client.go:131`). FC supports diff snapshots but E2B uses `SnapshotType:Full` and does its **own** diff in userspace — the dedup is the interesting part.

The dirty set comes from FC's WP-async pagemap (`GetDirtyMemory` → `client.go:529`, returns a roaring bitmap), reconciled with the UFFD handler's own page-state tracker via `Uffd.DiffMetadata` (`uffd.go:242`): it settles in-flight workers, samples FC's dirty bitmap, and computes `Empty = zero-installed-pages AndNot dirty` so a zero page later written is correctly counted as dirty, not empty.

The dedup itself (`block/cache.go:397 Cache.Dedup` → `dedupCompare`) walks every dirty 4 KiB page and classifies it:
1. **Zero page** (`header.IsZero(srcPage)`) → added to `pageEmpty`, dropped from the file. `IsZero` is a fast sample-3-bytes-then-`bytes.Equal(b[:n-1], b[1:])` trick (`diff.go:24`).
2. **Page identical to base template** → compared byte-for-byte against the base via `base.Slice(ctx, pageOff, 4096)` then `bytes.Equal(srcPage, basePage)`; if equal, **skipped entirely** (not in the diff). This is the 4 KiB diff-dedup-against-base.
3. **Page differs from base** → added to `pageDirty`, written to the diff cache.

A "skip-via-mapping" fast path (`cache.go` in `dedupCompare`): if the base header's shifted mapping for that page has `BuildId == uuid.Nil` (i.e. the page already came from *this* build's base, length ≥ 4 KiB), it's marked dirty without a byte compare. The result: a snapshot stores only the pages a sandbox actually wrote that differ from the warm base template — typically a few MiB for a fresh sandbox vs hundreds of MiB of guest RAM.

### UFFD resume — the lazy page-fault handler (KNOWN — `packages/orchestrator/pkg/sandbox/uffd/`)

This is the moat. On resume, the guest memory file is **not** read into RAM. Instead:

**Handshake (`uffd.go:121 handle`).** The orchestrator opens a Unix socket, Firecracker connects and sends over `SCM_RIGHTS`: a JSON array of memory `Region`s (the guest physical → host virtual mapping) plus **1 or 2 fds** — the `userfaultfd` fd, and on newer FC a `memfd` (`uffd.go:135-205`). The handler wraps the uffd fd: `userfaultfd.NewUserfaultfdFromFd(fds[0], memfile, mapping, logger)`. Page size is taken from the FC regions (must be 4 KiB or 2 MiB, all regions agree). The `uffdReady` channel (`process.go:482`, `client.go:85`) is closed once the handler is serving — `loadSnapshot` blocks on it before resuming the VM, so no fault can arrive before the handler is live.

**Resume parallelism (`process.go:477 Resume`).** Three goroutines race via `errgroup`: configure the FC process, wait for the uffd socket, symlink the rootfs overlay. Only after all three: `setMetrics` → `loadSnapshot` (`PUT /snapshot/load` with `MemBackend{BackendType:Uffd, BackendPath:socket, UseMemfd}`, `ResumeVM:false`) → reset rate limits → `resumeVM` (`PATCH /vm {State:Resumed}`) → `setMmds` (injects sandbox metadata + access-token hash — see egress section). The VM resumes with **zero pages resident**; the kernel raises a `UFFD_EVENT_PAGEFAULT` the instant the guest touches any page.

**The serve loop (`userfaultfd.go:231 Serve`).** A single `poll()` loop over three fds: the uffd, an exit fd, and a self-pipe wakeup. On `POLLIN` it drains all queued events (`readEvents`, `userfaultfd.go:185`) into two slices — `UFFD_EVENT_PAGEFAULT` and `UFFD_EVENT_REMOVE`. Each pagefault is dispatched to a worker goroutine (`u.wg.Go`, errgroup capped at `maxRequestsInProgress = 4096`, `userfaultfd.go:33`). The worker:

1. Maps fault address → file offset (`ma.GetOffset`), → page index (`header.BlockIdx`).
2. Reads the page-state tracker under `settleRequests.RLock`:
   - `block.Dirty` → page already installed, ack only, return.
   - `block.Zero` → zero-fill (page known-empty in the snapshot).
   - `block.NotPresent` → fetch from `src` (the snapshot memfile reader, which itself fetches lazily from object storage).
3. Installs the page via `faultPage` (`userfaultfd.go:476`): `UFFDIO_COPY` (4K) or `UFFDIO_ZEROPAGE` (4K zero) or `UFFDIO_COPY` of `EmptyHugePage` (2M zero). **Read faults install with `UFFDIO_COPY_MODE_WP`** (write-protect) so a later write re-faults and gets recorded dirty — this is `UFFD_FEATURE_WP_ASYNC`-based dirty tracking, used *instead* of FC's own `TrackDirtyPages` (which is set false in `setMachineConfig`).
4. On success, if it was a real page or a write, `pageTracker.SetRange(idx, idx+1, Dirty)` and records the access in `prefetchTracker` (offset + read/write) for next-resume prefetch ordering.

**Error/retry handling in `faultPage`:** source `ReadAt` retries up to `sliceMaxRetries=3` with exponential backoff (`50ms` base, `500ms` cap, jittered) for transient object-store reads. `EEXIST` → page already mapped, wake and treat as installed. `ESRCH` → faulting thread gone (teardown), discard. `EAGAIN` → `mmap_changing` raced a madvise/fork; the fault is **deferred** (pushed to a `deferredFaults` queue + a self-pipe wakeup, since the kernel won't redeliver) and retried next poll iteration.

**Prefetch.** A background prefetcher (`sandbox.go:651`, `prefetch.New`) reads the previous session's `prefetchTracker` access order from metadata and `Prefault`s those pages (`uffd.go:63`) ahead of the guest touching them — warming the working set so the first agent action doesn't pay N synchronous page-fault round-trips. This is what gets resume to the ~150 ms ballpark (INFERRED from the prefetch design + the published ~150 ms figure; the exact number is not in the repo).

### envd — the daemon inside the sandbox (KNOWN — `packages/envd/`)

The SDK never talks to Firecracker. It talks to `envd`, a Go daemon running as PID-ish inside the guest, reachable on a fixed port. The SDK's `ConnectionConfig.envd_port = 49983` (`connection_config.py:54`). The protocol is **two-tier**, exactly the split the brief asked for:

**REST lifecycle (`packages/envd/internal/api/`, OpenAPI-generated `api.gen.go`):**
- `POST /init` — called by the orchestrator's *infinite retry loop* on resume; validates the access token, sets env vars, thaws frozen cgroups via a deferred unfreeze. This is the resume-time bootstrap + credential gate (see egress).
- `GET /files` / `POST /files` / `POST /files/compose` — bulk file download/upload (multipart); large-file path separate from the RPC filesystem service.
- `GET /health` — readiness.
- `GET /metrics` — service stats.

**ConnectRPC realtime (`spec/process/process.proto`, `spec/filesystem/filesystem.proto`)** — ConnectRPC (HTTP/2 + protobuf, gRPC-compatible). The **Process** service (`process.proto:5`):
```proto
service Process {
  rpc List(ListRequest) returns (ListResponse);
  rpc Connect(ConnectRequest) returns (stream ConnectResponse);   // reattach to a running proc
  rpc Start(StartRequest) returns (stream StartResponse);          // spawn, stream stdout/stderr/pty
  rpc Update(UpdateRequest) returns (UpdateResponse);              // resize PTY
  rpc StreamInput(stream StreamInputRequest) returns (StreamInputResponse);  // ordered stdin
  rpc SendInput(SendInputRequest) returns (SendInputResponse);
  rpc SendSignal(SendSignalRequest) returns (SendSignalResponse);  // SIGTERM=15 / SIGKILL=9
  rpc CloseStdin(CloseStdinRequest) returns (CloseStdinResponse);  // EOF (non-PTY); PTY uses Ctrl+D 0x04
}
```
`ProcessConfig{cmd, args[], envs map, cwd}`. The stream yields a `ProcessEvent` oneof: `StartEvent{pid}` → N× `DataEvent{stdout|stderr|pty bytes}` → `EndEvent{exit_code, exited, status, error}`, with `KeepAlive` interleaved. A process can be addressed by `pid` *or* a client-assigned `tag` (`ProcessSelector`) — so the SDK can reconnect to a backgrounded process after a network blip. The **Filesystem** service: `Stat / MakeDir / Move / ListDir / Remove`, plus streaming `WatchDir` and a poll-based watcher trio (`CreateWatcher / GetWatcherEvents / RemoveWatcher`) for inotify-style file events.

The SDK keepalive: `KEEPALIVE_PING_INTERVAL_SEC = 50` sent as a `Keepalive-Ping-Interval` header (`connection_config.py:13`); `REQUEST_TIMEOUT = 60.0` default.

### Python SDK surface (KNOWN — `e2b==2.25.1` / repo `python-sdk`)

```python
sbx = Sandbox.create(timeout=300, ...)        # default 300s; max 86_400 (Pro) / 3_600 (Hobby)
                                              # lifecycle={"on_timeout":"pause"|"kill", "auto_resume":bool}
sbx.commands.run(cmd, background=False, envs=..., user=..., cwd=...,
                 on_stdout=cb, on_stderr=cb, timeout=60)   # default 60s; background=True → handle
sbx.files.read/write/list/...                  # → envd Filesystem RPC
sbx.set_timeout(seconds)                       # extend/reduce TTL (POST to control plane)
Sandbox.connect(sandbox_id, timeout=...)       # reattach to a running/paused sandbox
sbx.kill()
```
File URLs are HMAC-signed (`signature.py`: `v1_<base64(sha256(path|operation|user|expiration|accessToken))>`) so a presigned upload/download URL can be handed to a tool without leaking the access token.

### For Verso

- **Adopt the lazy-resume mental model, not eager restore.** A snapshot-resume adapter should be `base template (read-only, shared) + sparse per-sandbox diff`, faulted in on demand. The reimplementable kernel of E2B's resume is: register guest RAM with `userfaultfd` (`UFFD_FEATURE_WP_ASYNC`), serve `UFFD_EVENT_PAGEFAULT` by `UFFDIO_COPY` from a backing file, install read faults write-protected so writes re-fault and self-track dirty pages, and dedup the resulting dirty set against the base byte-for-byte at 4 KiB. Verso's `CodeSandbox` protocol should expose `snapshot()` / `resume(snapshot_id)` and treat resume latency (not boot latency) as the SLO.
- **Diff = 4 KiB pages that differ from base, plus a zero-bitmap.** The dedup is two `bytes.Equal` checks per page (vs zero, vs base). That's it — no rolling hash, no content store. Verso doesn't need a fancy CAS; a base + 4K-page diff covers the snapshot use case.
- **Two-tier daemon protocol is the right shape.** Slow lifecycle (init/files/health) over REST; hot path (process spawn + stream stdout/stderr/pty, stdin, signals, fs watch) over a streaming RPC (ConnectRPC/gRPC) addressing processes by `pid|tag` so reconnect survives disconnects. Verso's in-sandbox agent daemon should copy `ProcessEvent` oneof (`Start{pid}→Data{stdout|stderr|pty}→End{exit_code}`) and the `tag`-based reattach. This pairs with the streaming-cancellation discipline in `infra-serving.md` (a dropped client must abort the in-VM process, not orphan it).
- **`rootflags=discard` + WP-async dirty tracking are free wins.** TRIM-on-free shrinks the rootfs diff; `UFFD_FEATURE_WP_ASYNC` gives dirty tracking without FC's slower `TrackDirtyPages`. If Verso ever runs its own microVMs, both are one-line config.
- **Cred handling is at `/init` + MMDS, not baked into the snapshot.** Access-token hash is injected via FC MMDS at resume (`setMmds`, `process.go:605`) and re-validated by `envd /init` every resume — credentials live outside the snapshot image and are re-checked on each wake. Mirror this: never snapshot secrets; inject at resume and validate in the daemon.

### E2B — orchestrator control plane, NBD rootfs, scheduling (KNOWN — `packages/orchestrator/orchestrator.proto`, `pkg/sandbox/rootfs/nbd.go`, `iac/`)

The orchestrator (one per node) exposes a **gRPC `SandboxService`** (`orchestrator.proto:183`): `Create`, `Update`, `List`, `Delete`, `Pause`, `Checkpoint`, `ListCachedBuilds`. The cloud control plane (the closed API) calls `Create` with a `SandboxConfig` whose fields *are* the replica's input contract (`orchestrator.proto:8`):
```proto
SandboxConfig {
  template_id, build_id, base_template_id;  kernel_version, firecracker_version, envd_version;
  sandbox_id, execution_id, team_id, alias;  bool huge_pages;
  map<string,string> env_vars;  map<string,string> metadata;
  int64 vcpu, ram_mb, total_disk_size_mb, max_sandbox_length;
  bool snapshot;          // resume from a snapshot vs cold-create
  bool auto_pause;        // on timeout → pause (snapshot) instead of kill
  optional string envd_access_token;        // the per-sandbox secret (hashed into MMDS)
  optional bool allow_internet_access;       // egress gate
  optional SandboxNetworkConfig network;     // egress/ingress rules
  repeated SandboxVolumeMount volumeMounts;
  optional SandboxAutoResumeConfig auto_resume { string policy; uint64 timeout_seconds; }
}
```
This is the full create contract: `env_vars` + `envd_access_token` + `allow_internet_access` are the egress/cred surface; `snapshot` + `auto_pause` + `auto_resume{policy,timeout_seconds}` are the lifecycle surface. Verso's cloud sandbox adapter should accept exactly this shape.

**Rootfs = NBD overlay (CoW), not a copied disk (`rootfs/nbd.go`, `pkg/sandbox/block/overlay.go`).** The writable rootfs is a `block.Overlay` = read-only base template device + a writable local `cache`, exposed to the VM as a **network block device** via `nbd.NewDirectPathMount(overlay, devicePool)`. The orchestrator allocates an NBD device from a `DevicePool`, mounts the overlay on it, and gives FC that device path as the rootfs drive. Writes land in the cache layer; reads fall through to the base. On pause, `ExportDiff` (`nbd.go:73`) ejects the cache as the rootfs diff (the disk equivalent of the UFFD memory diff). So *both* memory (UFFD) and disk (NBD overlay) are CoW-over-a-shared-base — the same architecture twice, which is why a fresh sandbox's total snapshot is tiny.

**Scheduling = Nomad + Consul (`iac/modules/job-orchestrator/jobs/orchestrator.hcl`, autoscaler).** The orchestrator, template-manager, and API run as **Nomad jobs**; a `nomad-autoscaler` scales the sandbox node pool; Consul provides service discovery. (The API also has a newer Kubernetes cluster-discovery path — `packages/api/internal/clusters/discovery/kubernetes.go` — so the control plane is being made cluster-agnostic; **[CORRECTION 2026-06-05]** the brief's "Nomad/Consul" is correct for the node fleet, but discovery is now pluggable Nomad-or-K8s.) **For Verso:** the per-node orchestrator + central scheduler split is the cloud-scale shape; for Verso's purposes the *node-local* gRPC `SandboxService(Create/Pause/Resume/Checkpoint)` is the interface to replicate, and the scheduler can be anything (Nomad/K8s/your own) since it only places sandboxes onto nodes that expose that gRPC.

---

## Daytona

### What It Is

Daytona is a container-based (not microVM) sandbox platform. Each sandbox is a Docker container, not a Firecracker VM — isolation is the shared host kernel plus optional privileged/runtime hardening, which is weaker than E2B's microVM boundary but gives unlimited stateful sessions and a simpler snapshot story. The full stack is open: a **NestJS API server** (`apps/api`, the control plane with a desired-state reconciliation model), a **Go runner** (`apps/runner`, one per node, drives the local Docker daemon), and a **Go daemon-inside-the-sandbox** (`apps/daemon`, "toolbox" — a Gin REST server that handles `process.code_run`, filesystem ops, LSP, PTY, git). The Python SDK (`Daytona().create()`, `sandbox.process.code_run()`, `sandbox.process.exec()`) is the surface.

The architecturally important contrast with E2B: **Daytona's snapshot is a `docker commit` of the filesystem, not a memory snapshot.** Resuming does not restore running-process state — it recreates a container from a committed image. E2B's UFFD snapshot restores live guest RAM; Daytona's restores only the disk. This is the single most important fact when choosing between them.

### Daemon-inside-the-sandbox — the toolbox (KNOWN — `apps/daemon/pkg/toolbox/server.go`)

Unlike E2B's gRPC `envd`, Daytona's daemon is a **plain Gin HTTP/REST server** listening on `config.TOOLBOX_API_PORT` (`server.go:368`). The daemon binary is **bind-mounted read-only** into every container at `common.DAEMON_PATH` (`container_configs.go:189`: `fmt.Sprintf("%s:%s:ro", d.daemonPath, common.DAEMON_PATH)`) and used as the container entrypoint — so the host's daemon binary runs inside the guest without being baked into the image. The runner starts the container, then **polls the daemon's `/version` on the container IP** (`start.go:113 waitForDaemonRunning`) before marking the sandbox ready.

Full route table (`server.go:160-220`):
- `POST /init` — bootstrap (otelServiceName, org/region/snapshot ids).
- `GET /version` `/project-dir` `/user-home-dir` `/work-dir` — introspection.
- `/files/*` — `GET /` (list), `GET /download`, `POST /bulk-download`, `GET /find` (grep), `GET /info`, `GET /search`, `POST /folder`, `POST /move`, `POST /permissions`, `POST /replace` (find-replace in files), `POST /upload`, `POST /bulk-upload`, `DELETE /`.
- `/process/execute` — one-shot command.
- `/process/code-run` — run a code snippet (the interesting one, below).
- `/process/session/*` — **persistent shell sessions** (see below): create, list, `POST /:sid/exec`, `GET/POST .../command/:cid/...`.
- `/process/pty/*` — interactive PTY sessions (create/list/get/delete + resize + a WebSocket data channel).
- `/lsp/*` `/git/*` `/computeruse/*` — language server, git ops, and a `computeruse` controller (screenshot/click — for GUI agents).

### `process.code_run` — language-aware code execution with artifact extraction (KNOWN — `apps/daemon/pkg/toolbox/process/coderun/`)

This is what distinguishes Daytona from E2B's "run a command". `CodeRun` (`handler.go:35`) takes `{language, code, argv, envs, timeout}`, looks up a per-language `Toolbox`, and produces a shell command that runs the code. For Python (`python.go:28`):
```go
encodedCode := base64.StdEncoding.EncodeToString([]byte(code))
// → "printf '%s' '<b64>' | base64 -d | python3 -u - <argv>"
```
Code is base64-encoded and piped to `python3 -u -` (unbuffered stdin) — avoids shell-escaping the source. The command runs via `exec.Command(common.GetShell())` with `Setpgid: true` (own process group, so timeout can kill the whole tree), stdout+stderr merged into one buffer.

**Chart/artifact extraction (the clever bit).** If the code imports matplotlib (detected by 6 regexes incl. `__import__`, `importlib`, `sys.modules[...]` — `python.go:19`), the source is wrapped in an embedded `matplotlib_wrapper.py` that monkeypatches `plt.show()`/figure rendering to serialize each figure to a JSON `Chart` and print it prefixed with the magic marker `dtn_artifact_k39fd2:` (`artifacts.go:11`). The Go handler (`ParseArtifacts`, `artifacts.go:18`) then strips marker lines from stdout and collects them into `CodeRunArtifacts{Charts:[]}`. Net effect: an agent calling `code_run("import matplotlib...plt.plot(...)")` gets back clean stdout **plus** structured chart data, no display server needed. The SDK surfaces this as `response.artifacts.stdout` + `response.artifacts.charts`.

### Persistent sessions — the stateful-shell primitive (KNOWN — `apps/daemon/pkg/session/`)

A "session" is **one long-lived shell process** (`create.go:23`: `exec.CommandContext(ctx, common.GetShell())` with a `StdinPipe`, `Setpgid: true`). The daemon holds the session in a concurrent map (`session{id, cmd, stdinWriter, commands}`, `types.go:15`). Each `Execute` (`execute.go:23`) assigns a `cmdId`, creates `sessions/<sid>/<cmdId>/output.log` + `exit_code` files, writes a `cmd.sh` wrapper, and feeds it into the shared shell's stdin. Because it's the **same shell process** across commands, env vars, `cd`, and shell state persist between calls — this is the "agent lives in a stateful shell" primitive. Output is tailed from the per-command log file (async or combined-output modes); exit code from the `exit_code` file. Compare to E2B's model where each `commands.run` is a fresh `Process.Start` — Daytona's session is explicitly stateful.

### Snapshot / backup — `docker commit` + registry push (KNOWN — `apps/runner/pkg/docker/backup.go`, `container_commit.go`)

`CreateBackup` (`backup.go:24`) → `createBackup` → `commitContainer` → `PushImage`. `commitContainer` (`container_commit.go:16`) calls Docker's `ContainerCommit(containerId, {Reference:imageName, Pause:false})` with **`maxRetries=3`** and an export/import fallback if commit hits the "failed to get digest" error. The committed image is pushed to a registry (`PushImage`). Restore = the API schedules a sandbox `start` with `Snapshot:imageName`; the runner pulls that image and `ContainerCreate`s from it (`container_configs.go:133,169`). Backup state machine: `BackupStateNone → InProgress → Completed/Failed` cached per container; commit has a `backupTimeoutMin` deadline. There is **no memory snapshot** — `Pause:false` means the container isn't even paused during commit; only the writable filesystem layer is captured. The `fork` endpoint (`sandbox.controller.ts:745`, with `/forks` `/parent` `/ancestors`) is built on this: fork = snapshot the parent's filesystem, create a child from it, track lineage.

### Control plane — desired-state reconciliation (KNOWN — `apps/api/src/sandbox/`)

The NestJS API models two enums: **desired state** (`STARTED/STOPPED/ARCHIVED/DESTROYED`, `sandbox-desired-state.enum.ts`) and **current state** (`CREATING/STARTED/STOPPED/RESIZING/ARCHIVED/DESTROYED/...`, `sandbox-state.enum.ts`). The controller (`sandbox.controller.ts`) exposes CRUD + lifecycle: `POST /` (create), `start`, `stop`, `resize`, `backup`, `snapshot`, `fork`, `recover`, plus auto-lifecycle timers `autostop/:interval`, `autoarchive/:interval`, `autodelete/:interval` and `last-activity`. A reconciler drives current → desired by issuing runner jobs (`job.controller.ts` with `GET poll` / `POST :jobId/status` — the runner polls for work and reports status). This is a Temporal-free, DB-backed reconcile loop: set desired state, a background worker converges. Sandboxes are reachable for preview via signed tokens (`preview.controller.ts`: `:sandboxId/access`, `:signedPreviewToken/:port/...`).

### Computer-use + LSP — the GUI-agent and code-intelligence surfaces (KNOWN — `apps/daemon/pkg/toolbox/computeruse/`, `lsp/`)

Two daemon capabilities make Daytona a "composable computer," not just a code runner. **`/computeruse/*`** exposes a full GUI-automation surface to the agent (`computeruse/lazy.go`): `TakeScreenshot` / `TakeRegionScreenshot` / `TakeCompressedScreenshot`, `GetMousePosition` / `MoveMouse` / `Click` / `Drag` / `Scroll`, keyboard input, and an **AT-SPI accessibility-tree** API (`computeruse/accessibility.go`: "Move keyboard focus to the AT-SPI node identified by id (bus-name:object-path)") — so a vision/computer-use agent can either screenshot-and-click or drive the accessibility tree semantically. **`/lsp/*`** runs a Language Server inside the sandbox (`createLspServer(language, path)`) giving the agent completions/definitions/symbols against the real project — code intelligence without the model guessing. **For Verso:** if Code Mode ever needs GUI agents, the daemon-hosts-a-display + screenshot/mouse/AT-SPI surface is the reimplementable shape; the LSP-in-sandbox pattern is a cheap accuracy win for any code-editing agent (ground edits in real symbols, not the model's memory of the API).

### Python SDK surface (KNOWN — `daytona==0.184.0`)

```python
daytona = Daytona(DaytonaConfig(api_key=..., api_url=..., target=...))
sandbox = daytona.create(CreateSandboxFromSnapshotParams(snapshot=..., ...))  # or FromImage
sandbox.process.exec(command, cwd=None, env=None, timeout=None)   # → ExecuteResponse{exit_code, result, artifacts}
sandbox.process.code_run(code, params=CodeRunParams(...), timeout=None)  # language runtime + chart artifacts
sandbox.process.create_session(session_id); sandbox.process.execute_session_command(session_id, ...)  # stateful shell
sandbox.process.create_pty_session(...)                           # interactive PTY
sandbox.fs.upload_file / list_files / find_in_files / replace_in_files / ...
sandbox.create_lsp_server(language, path)                         # LSP for code intelligence
sandbox.create_signed_preview_url(port, expires_in_seconds)       # expose a port via signed URL
```
`exec`'s `ExecuteResponse.artifacts` carries `stdout` + `charts` even for plain `exec` — the chart extraction lives in the daemon, so it applies to any code that emits the marker.

### For Verso

- **Pick the snapshot model deliberately: filesystem-only (Daytona/`docker commit`) vs live-RAM (E2B/UFFD).** They are not interchangeable. If Verso's Code-Mode sessions are "agent installs deps, edits files, runs builds" the filesystem snapshot is sufficient and *far* simpler to implement (one `docker commit` + registry push). If sessions need to resume a *running* process tree (a paused REPL, a warm in-memory index), only the UFFD model preserves it. Verso should default to the Daytona-style filesystem snapshot for the cloud adapter and reserve UFFD-style for a future "warm pool" optimization.
- **The daemon-bind-mount trick is worth stealing.** Daytona ships the in-sandbox daemon as a host binary bind-mounted read-only and set as entrypoint, rather than baking it into every image. Verso's in-sandbox agent daemon can be injected the same way — one binary, mounted into any base image, so users bring arbitrary images without rebuilding to add the agent. Readiness = poll the daemon's `/version` on the container IP.
- **`code_run` with artifact extraction is the right Code-Mode return type.** Don't return raw stdout — return `{exit_code, stdout, artifacts}` where artifacts are structured (charts, files, rich objects) emitted via an out-of-band magic-marker protocol the daemon strips. The matplotlib monkeypatch (`plt.show()` → serialize-to-JSON → `dtn_artifact_<nonce>:` line) is a clean pattern: the language runtime emits artifacts inline on stdout, the daemon demuxes them. Verso's Code-Mode tool result schema should have first-class `artifacts`.
- **Stateful-session = one persistent shell, command = stdin write + per-command log/exit-code files.** This is the minimal correct implementation of "the agent has a shell that remembers `cd` and exports". Verso's interactive Code-Mode should keep a session shell alive and address commands by id, tailing a per-command log — not spawn a fresh process per turn (which loses `cd`/env).
- **Desired-state reconciliation beats imperative lifecycle for an agent fleet.** Daytona's `desired_state` vs `current_state` + a polling runner job loop gives crash-safe convergence (autostop/autoarchive/autodelete on idle timers) without a workflow engine. Verso's sandbox manager should set desired state and let a reconciler converge, with idle-timeout auto-stop as a first-class field — this is the cheaper cousin of the durable-seam backends in `05_re_targets`.

---

## microsandbox

### What It Is

microsandbox is the zero-infrastructure pole: a local-first microVM library (Rust, `superradcompany/microsandbox`) using the **libkrun** hypervisor (via the `msb_krun = "0.1.14"` safe wrapper crate, `crates/runtime/Cargo.toml:31`). There is **no server, no daemon, no orchestrator** — each sandbox is a child process of the calling process. You `Sandbox.create("name", image="python:3.12")` and a microVM boots as a forked `msb sandbox` subprocess. Isolation is a real KVM-backed microVM (hardware virtualization, stronger than Daytona's containers, comparable to E2B's Firecracker), but with no cloud control plane. Boot is sub-100 ms class because libkrun is a minimal VMM with no device emulation overhead. As of v0.5 the SDK is **embedded**: the Rust runtime ships as a PyO3/native extension (`microsandbox==0.5.4` is a `cp310-abi3` wheel, 32 MB — it bundles the `msb` binary), so `pip install microsandbox` is genuinely self-contained.

### libkrun invocation — the VM build sequence (KNOWN — `crates/runtime/lib/vm.rs`)

The VM is constructed by a `msb_krun::VmBuilder` (`vm.rs:723 build_vm`), a fluent wrapper over libkrun's C API. The sequence:
1. `VmBuilder::new()` → set vCPUs, memory MiB, optionally `.krunfw_path(libkrunfw_path)` (the bundled guest firmware/kernel blob).
2. **Rootfs** — three mutually-exclusive paths (`vm.rs:746`):
   - `PassthroughFs` (virtio-fs): a host directory shared into the guest tagged `/dev/root` (`builder.fs(|fs| fs.tag("/dev/root").custom(backend))`).
   - **EROFS fsmerge OCI rootfs**: a read-only VMDK base disk + a writable `upper.ext4`/qcow2 overlay (`DiskImageFormat::Vmdk` + `Qcow2`/`Raw`) — this is how an OCI image becomes a bootable rootfs without unpacking it.
   - Raw/qcow2 disk passthrough with `append_block_root_env` setting `MSB_BLOCK_ROOT`.
3. **Mounts** — each user volume is another `PassthroughFs` with its own tag; disks added with `CacheMode::Unsafe` + `SyncMode::None` for ephemeral speed (`vm.rs` disk loop).
4. **Network** (`#[cfg(feature = "net")]`, `vm.rs:867`) — a userspace `SmoltcpNetwork` (smoltcp TCP/IP stack) bound via `builder.net(|n| n.mac(guest_mac).custom(net_backend))`. Because the entire network stack runs in the host process, egress is **programmable from outside** the guest: per-rule allow/deny policies (`microsandbox_network::policy::{Action, Destination, Rule}`), a `host.microsandbox.internal` alias, and even **TLS interception** with a CA cert injected into the guest env (`ca_cert_pem`, `host_cas_cert_pem` pushed into `exec_env`). This is the network-isolation mechanism — no iptables, no host firewall; the host owns the TCP stack and can intercept/redirect every connection.
5. **Exec** (`vm.rs:933`) — `builder.exec(|e| e.path(exec_path).args(...).env(k,v).workdir(...))` sets the guest's PID 1 command + env + cwd.
6. **Console** — `builder.console(|c| c.output(kernel.log).custom(AGENT_PORT_NAME, console_backend))` wires a virtio-console port named `AGENT_PORT_NAME` as the agent control channel (see below).
7. `builder.on_exit(on_exit).build()` → `vm::enter(config)` (`vm.rs:322`) which **never returns** — it `krun_start_enter`s and the calling thread *becomes* the vCPU loop.

### Rootless child-process spawn — the "no daemon" mechanism (KNOWN — `crates/microsandbox/lib/runtime/spawn.rs`)

`spawn_sandbox` (`spawn.rs:90`) is the whole "VMs as child processes" trick:
1. Resolve per-sandbox dirs under `~/.microsandbox/<name>/{logs,runtime,scripts}`; write user scripts to `scripts/` with `0o755`.
2. Compute an agent relay Unix-socket path **outside** the name-derived tree (so a 128-byte sandbox name can't blow the `sun_path` limit).
3. `Command::new(msb_path)` with `sandbox_cli_args(...)` — i.e. **re-exec the same `msb` binary** in the hidden `msb sandbox --agent-sock <path>` subcommand mode (`sandbox_cmd.rs:258 → vm::enter`).
4. `cmd.stdin(Stdio::null())`; on `SpawnMode::Attached` install a **parent-watchdog pipe** via `pre_exec` (the child watches the pipe for parent EOF and self-terminates if the parent dies — no orphaned VMs); on `SpawnMode::Detached` call `cmd.process_group(0)` so the VM survives the launching CLI.
5. Read a startup JSON line from the child's stdout (the sandbox PID + boot info), then connect to the agent over the relay socket.

No root required: libkrun + KVM run unprivileged (rootless). The host process literally forks a copy of itself into VMM mode. This is the entire architectural difference from E2B (cloud Nomad) and Daytona (server + per-node Docker runner) — there is no separate long-running daemon at all.

### agentd — the in-VM agent + frame protocol (KNOWN — `microsandbox/agent.py`, docs)

Inside the guest runs `agentd` (built from `Dockerfile.agentd`). The host talks to it over the relay Unix socket using a **binary frame protocol** (`AgentClient`, `agent.py:69`): `request(flags, body) -> RawFrame`, `stream(flags, body) -> AgentStream`, `send(id, flags, body)`. Frame flags include `FLAG_SESSION_START = 0b0000_0010` (first frame of a streaming session). On boot the host waits for a `ready` frame carrying `boot_time_ns / init_time_ns / ready_time_ns` (`mod.rs:457`) — these are the actual measured boot/init/ready timings the runtime logs in ms, the source of the sub-100 ms boot claim. Higher-level `Sandbox.exec` / `Sandbox.shell` / `fs` calls are encoded over this frame protocol; streaming exec yields `ExecEvent`s with stdout/stderr and a final `(exit_code, success)`.

### Python SDK surface (KNOWN — `microsandbox==0.5.4` + docs)

```python
async with await Sandbox.create("name", image="python:3.12", cpus=1, memory=512,
                                workdir="/work", env={...},
                                security="RESTRICTED",  # no_new_privs, drop mount-admin cap, nosuid,nodev
                                snapshot=None,           # OR boot from a snapshot instead of image
                                detached=False) as sb:
    out = await sb.shell("echo hello")        # → ExecOutput{exit_code, success, stdout_text, stdout_bytes}
    handle = await sb.exec([...], stream=True)  # → ExecHandle: async-iter ExecEvent, take_stdin(), wait(), collect()
# lifecycle: Sandbox.start(name) reboots a stopped sandbox from persisted config; create_with_progress() → PullSession
```
Defaults: `cpus=1`, `memory=512 MiB`. `Image.oci("python:3.12", upper_size_mib=8192)` sets the writable-overlay size. The `RESTRICTED` security profile sets `no_new_privs`, drops the mount-admin capability from user commands, and forces `nosuid,nodev` on user mounts.

### Network policy — the egress firewall model (KNOWN — `crates/network/lib/policy/types.rs`)

Because the netstack is userspace, egress control is a declarative policy evaluated in the host process, not iptables. `NetworkPolicy{default_action, rules: Vec<Rule>}` (`types.rs:43`); per-field serde default is `Deny` (fail-closed). Each `Rule` (`types.rs:81`):
```rust
enum Action { Allow, Deny }
enum Direction { Outbound, Inbound, Any }       // Any default
enum Destination { Any, Cidr(IpNetwork), Domain(DomainName), DomainSuffix(DomainName) }
enum Protocol { Tcp, Udp, Any }
struct PortRange { ... }                          // empty ports = any port (guest-side port)
struct Rule { action, direction, destination, ports: Vec<PortRange>, protocol }
```
Domain rules are matched two ways (`HostnameSource`, `types.rs:212`): at **SYN time** before SNI is known (via a resolved-hostname cache from the guest's DNS lookups), and at **SNI time** for TLS (a matching `Domain`/`DomainSuffix` short-circuits). `DomainSuffix` matches the apex + any subdomain. So a policy like "allow only `*.openai.com:443/tcp`, deny all else" is enforced *inside the host's TCP stack* — the guest physically cannot open a connection the policy denies, and there's no kernel firewall to misconfigure. This is the reimplementable egress model: own the netstack, match by CIDR/domain/port/protocol, default-deny.

### Snapshot — disk-only, cold boot (KNOWN — `docs/sandboxes/snapshots.mdx`)

Like Daytona and unlike E2B, microsandbox snapshots are **disk-only**: "A snapshot is a portable, on-disk capture of a sandbox's writable filesystem... Snapshots are disk-only and require a sandbox that is not running." Booting from a snapshot is "a cold boot of a fresh VM that starts from the captured filesystem changes" — **memory contents are explicitly not captured**. A snapshot is just the writable-overlay directory (`~/.microsandbox/snapshots/<name>/`), movable by `scp` or `.tar.zst`. SDK: `await handle.snapshot("name")` / `snapshot_to("/path")`.

### For Verso

- **This is the model for Verso's *local-dev* Code Mode: re-exec self into VMM mode, no daemon.** The reimplementable kernel: ship one binary; to start a sandbox, `fork+exec` that same binary in a hidden "runtime enter" subcommand that calls `libkrun` and becomes the vCPU loop; talk to an in-VM agent over a Unix-domain relay socket. A parent-watchdog pipe (`pre_exec` watches for parent EOF → self-terminate) prevents orphaned VMs in attached mode; `process_group(0)` gives detached mode. Verso can offer `CodeSandbox(backend="local")` with exactly this shape and zero cloud dependency.
- **Userspace network stack = egress control without iptables.** microsandbox runs smoltcp in the host process and owns every guest packet, so allow/deny policies, a `host.internal` alias, and TLS interception (inject a CA into the guest, MITM outbound TLS) are all just host-side code. This is the cleanest egress-cred-injection model in the whole cluster: the sandbox never gets raw network; the host proxy decides what each connection reaches and can splice credentials in. Verso's local sandbox should adopt a userspace-netstack egress proxy rather than relying on host firewall rules.
- **OCI-as-rootfs without unpack: read-only base disk + writable overlay.** microsandbox boots an OCI image by mounting it as a read-only VMDK/EROFS base plus a sized writable `upper.ext4` overlay. Verso doesn't need to extract/flatten images — mount the layers, add a CoW overlay, done. The overlay *is* the snapshot (`upper_size_mib`).
- **Three sandbox backends now map cleanly for Verso's `CodeSandbox` protocol:** E2B (cloud, microVM, *memory* snapshot, ~150 ms warm resume) · Daytona (server, container, *disk* snapshot via `docker commit`, stateful sessions) · microsandbox (local, microVM, *disk* snapshot, no daemon, <100 ms cold boot). All three converge on the same surface — `create/exec/fs/snapshot` + a streaming exec result with exit code — so Verso's protocol can be `create(image|snapshot) → exec(cmd|code, stream) → ExecOutput{exit_code, stdout, artifacts} → snapshot()`. Only the snapshot *semantics* (memory vs disk) and the transport (gRPC/REST/frame-socket) differ.

---

## Cloudflare Dynamic Workers + Sandboxes

### What It Is

Two complementary Cloudflare primitives. **(1) Dynamic Workers / "Code Mode"** — V8-isolate sandboxes spawned at runtime from LLM-generated JavaScript *strings* via the Worker Loader binding; isolate startup is "mere milliseconds" (no container, no VM). The runtime is closed, but the loader binding implementation is **open source in `workerd`** (`src/workerd/api/worker-loader.c++`), so the security model is fully readable. **(2) Cloudflare Sandboxes (GA)** — persistent full-Linux environments built on Containers + Durable Objects, for long-horizon agent work (install deps, run builds), with snapshot-based recovery. The two-tier story: V8 isolates for fast ephemeral *tool-as-code* execution, Linux containers for stateful agent sessions.

The reason this matters to Verso: the Dynamic Worker Loader is the cleanest **capability-based** sandbox in the cluster. The sandboxed code gets *no ambient authority* — it can only call the binding stubs the parent explicitly hands it, and `globalOutbound` controls every byte of egress. This is a fundamentally different (and stronger) isolation philosophy than "run code in a VM and hope it can't escape."

### Worker Loader binding — load code from a string (KNOWN — blog + `worker-loader.c++`)

```typescript
// the documented API (Code Mode blog)
let worker = env.LOADER.get(id, async () => ({
  compatibilityDate: "2025-06-01",
  mainModule: "foo.js",
  modules: { "foo.js": "export default { async fetch(req, env) { ... } }" },  // code as a STRING
  env: { CHAT_ROOM: chatRoomStub },          // bindings = capability stubs, NOT raw values
  globalOutbound: ctx.exports.OutboundProxy({ props }),  // or null to cut the internet
}));
let entrypoint = worker.getEntrypoint();      // RPC stub to the loaded worker
await entrypoint.fetch(...);                   // call across the isolate boundary
```

`WorkerLoader::get(js, name, getCode)` (`worker-loader.c++:63`) is **id-keyed and lazily evaluated**: the `getCode` callback runs only when the runtime actually needs to (re)create the isolate. The comment at `:90` is the key operational fact — *"The runtime can actually evict the isolate while a stub still exists, as long as there is no active request on the stub, and then recreate the isolate on the next request."* So the same `id` deduplicates and the isolate is reconstructable on demand from the code-string. `extractSource` (`:174`) requires `modules.fields.size() > 0`, supports both JS and Python main modules (`isPython = mainModule.endsWith(".py")`, mutually exclusive), and rejects pre-compiled Wasm-only bundles (you must pass generated JS modules).

### `globalOutbound` — the egress control + credential-injection seam (KNOWN — `worker-loader.c++:122-139`, verbatim)

This is the mechanism the brief asked for, and it's a clean three-way switch in `toDynamicWorkerSource`:
```c++
kj::Maybe<kj::Own<IoChannelFactory::SubrequestChannel>> globalOutbound;
KJ_IF_SOME(maybeOut, code.globalOutbound) {
  KJ_IF_SOME(out, maybeOut) {
    auto channel = out->getSubrequestChannel(ioctx);
    channel->requireAllowsTransfer();      // (A) a fetcher/stub was passed → route ALL egress through it
    globalOutbound = kj::mv(channel);
  } else {
    // (B) Application passed `null` to disable internet access. Leave `globalOutbound` as `kj::none`.
  }
} else {
  // (C) absent → inherit the calling worker's global outbound channel.
  globalOutbound = ioctx.getIoChannelFactory().getSubrequestChannel(IoContext::NULL_CLIENT_CHANNEL);
}
```
- **(B) `globalOutbound: null`** → the loaded isolate's global `fetch()`/`connect()` throw; it has *zero* network. (Blog: *"In Code Mode, we prohibit the sandboxed worker from talking to the Internet. The global `fetch()` and `connect()` functions throw errors."*)
- **(A) `globalOutbound: <a Worker/fetcher stub>`** → every outbound request from the sandbox is transparently routed through *that* worker. This is the credential-injection point: the proxy worker (the "agent supervisor") holds the real API keys/access tokens, and *adds them into requests* before forwarding. The sandboxed code calls `fetch("https://api.example.com/...")` with no creds; the outbound proxy splices them in. Blog, verbatim: *"The binding itself provides an already-authorized client interface to the MCP server. All calls made on it go to the agent supervisor first, which holds the access tokens and adds them into requests sent on to MCP."*
- **Bindings carry capabilities, not secrets.** `env` is converted to a `Frankenvalue` (`worker-loader.c++:117`); the entries are *stubs* (e.g. `CHAT_ROOM: chatRoomStub`). `getEntrypoint(name, {props})` (`:13`) builds a `Fetcher` RPC stub; **`props` are set when the stub is created and the dynamic worker never sees them** (docs). So secrets live on the parent side of the boundary and the child only ever holds a method handle.

### RPC across the isolate boundary — Cap'n-Proto / Cap'n Web (KNOWN — `worker-loader.c++`, workerd RPC)

`getEntrypoint` returns a `Fetcher` backed by an `IoChannelFactory::SubrequestChannel` (`:34-35`); `getDurableObjectClass` returns a `DurableObjectClass` over an `ActorClassChannel` (`:59`). Calls on these stubs are workerd's capability-RPC (Cap'n-Proto-derived; the JS-facing flavor is "Cap'n Web") — the generated code calls typed parent methods as if local, without perceiving the isolate boundary. This is the "typed tool calls across a security boundary" pattern: the parent exposes a typed entrypoint, the sandbox calls it, the boundary is invisible to the code but absolute for security.

### Durable Object Facets — per-sub-object isolate + SQLite (KNOWN — `facet-tree-index.h`, `worker.h:901`, `actor-state.h:621`)

A Durable Object is a **tree of facets** (`ctx.facets` / `getFacets`, `actor-state.h:621`). Facet 0 is the root; every other facet has a parent + a unique-among-siblings name and is assigned a sequential numeric ID the first time it's seen. The index is an **append-only on-disk file** (`facet-tree-index.h`): each entry is `[2-byte parentID][2-byte nameLen][name bytes]`, capped at 65536 facets per DO (the format limit). Append-only means no write-ahead log is needed for index updates. Each facet, when started (`FacetManager::getFacet(name, getStartInfo)`, `worker.h:927`), gets its own actor class + its own `ctx.id` + **its own independent storage** (each facet is effectively a child Durable Object with its own SQLite). So a dynamic worker / agent can carve a fresh isolated SQLite-backed sub-state per task by naming a facet — without provisioning a new DO. `abortFacet` / `deleteFacet` tear one down.

### Cloudflare Sandboxes SDK (KNOWN — `developers.cloudflare.com/sandbox/`)

```typescript
const sandbox = getSandbox(env.Sandbox, userId);          // DO-bound, per-user persistent env
await sandbox.exec(command);                               // shell/python/node, streaming output
await sandbox.runCode(code, { context });                 // persistent state between calls
const ctx = await sandbox.createCodeContext();             // REPL-style state across runCode calls
sandbox.terminal(request, { cols, rows });                 // browser PTY over WebSocket
sandbox.wsConnect(request, port);                          // proxy WS to a service inside the sandbox
sandbox.writeFile/readFile/mkdir(...); sandbox.watch(path, opts);  // native fs-event watching
```
Built on Containers (the Linux runtime) + Durable Objects (the stateful coordination layer that keeps the environment persistent across requests). Snapshot/restore recovers a stopped sandbox far faster than a cold container start (the brief's ~2 s restore vs ~30 s cold-start figures; exact numbers not confirmable from the public docs available — marked INFERRED). `runCode` + `createCodeContext` give the same stateful-REPL primitive as Daytona's session model.

### For Verso

- **Adopt capability-based sandboxing for Code Mode where the runtime allows it.** The strongest pattern in this whole cluster is *the sandbox gets no ambient authority* — only the binding stubs the parent hands it, and a single `globalOutbound` switch that is either `null` (no net), a proxy (creds injected on the parent side), or inherited. Verso's Code-Mode tool calls should be capability stubs, not raw API keys handed into the sandbox. The agent-generated code calls `tools.search(...)`; the *parent* holds the credentials and injects them at the egress proxy. This is strictly safer than the VM-isolation model where the code holds real secrets and is merely fenced.
- **The egress-proxy-as-credential-injector is the reimplementable seam.** Concretely: run the sandbox with all outbound traffic forced through a parent-controlled proxy; the proxy matches the destination, attaches the right credential, and forwards. For Verso's VM-based backends (E2B/microsandbox) the equivalent is microsandbox's userspace netstack / E2B's network slot — point all guest egress at a Verso-controlled proxy that owns the secrets. Never put the secret inside the sandbox.
- **`globalOutbound: null` should be Verso's default.** Most tool-as-code executions need *no* network. Make "no egress" the default and require an explicit allowlist (or a credential-bearing proxy binding) to opt in — the inverse of "full network unless restricted."
- **Two-tier execution: ephemeral isolate for tool-functions, persistent sandbox for sessions.** When the tool *is* the code (a one-shot transform), an isolate-class fast path (id-keyed, evictable, reconstructable from the code-string) is ideal; when the agent *lives* in the environment across many turns, the persistent container + snapshot is right. Verso's `CodeSandbox` protocol should expose both as modes, with the isolate path keyed by a content/id hash so identical code dedupes (mirrors `WorkerLoader::get`'s id-keyed eviction-and-rebuild).
- **Facets = cheap per-task isolated state.** The append-only facet index + per-facet SQLite is a neat pattern for "give each agent task its own isolated key-value/SQL scratch state without provisioning new infrastructure" — name a facet, get a fresh storage scope, delete it when done. Verso's per-task memory scoping could copy this: a stable name → a lazily-created, independently-storable sub-state, torn down on task completion.

---

## Parlant

### What It Is

Parlant (`emcie-co/parlant`, Apache 2.0, Python) is an agent *control* framework — not an orchestrator. Its thesis: instead of one giant system prompt, behavior is a set of declarative **Guidelines** (`condition → action` pairs), and on every turn the engine **evaluates which guidelines' conditions match the current conversation state and injects only those into the LLM context** — plus only the tools bound to those matched guidelines. This is the operationalization of "context narrowing as a first-class primitive": the LLM never sees the 200 guidelines you wrote, only the 3 that apply right now. The engine lives in `src/parlant/core/engines/alpha/` (the "alpha engine"). For Verso this is the single best worked example of a per-turn context-engineering layer, and it's fully reimplementable from source.

### The per-turn loop (KNOWN — `engine.py` `_do_process`, `_run_preparation_iteration`)

`AlphaEngine.process()` → `_do_process()` (`engine.py:298`) runs:
1. Emit acknowledgement; `_initialize_response_state`; build a `Plan` from a pluggable planner.
2. **Preparation loop**: `while not context.state.prepared_to_respond:` run a *preparation iteration*. Each iteration: match guidelines → resolve relationships → split ordinary vs tool-enabled → run tools → feed tool results back and re-match. The loop is a ReAct-style feedback loop where tool outputs can flip new guidelines on.
3. **Termination** (`_check_if_prepared`, `engine.py`): prepared when *no tools executed this iteration*, *no journey-node-with-tool matched*, and *plan doesn't need another iteration*. Otherwise loop, capped at `agent.max_engine_iterations` (after which it responds anyway — a deliberate accuracy/latency trade-off).
4. **Message generation** (uncancellable, latched): inject transient guidelines, fire `on_guideline_selected`/`on_journey_selected` handlers, build the final prompt from *only* the matched/resolved guidelines + bound tools, generate, emit, persist agent state.

### Guideline matching — parallel batched LLM evaluation (KNOWN — `guideline_matching/guideline_matcher.py`, `generic/observational_batch.py`)

`GuidelineMatcher.match_guidelines(context, active_journeys, guidelines)` (`guideline_matcher.py:197`):
1. **Resolve a strategy per guideline** (`strategy_resolver.resolve(guideline)`) and bucket guidelines by strategy `id()`. Strategies: observational (no-action condition), actionable, previously-applied-actionable, customer-dependent, disambiguation, etc. — each tuned for a different guideline shape.
2. Build one `GuidelineMatchingContext` (agent, session, customer, context_variables, interaction_history, glossary terms, capabilities, staged tool events, active journeys, journey paths).
3. **Each strategy splits its guidelines into batches** sized by an `OptimizationPolicy` (`_get_optimal_batch_size` → `optimization_policy.get_guideline_matching_batch_size`; batch count = `ceil(len/batch_size)`). Batching exists because each batch is **one LLM call** evaluating a *set* of conditions at once — fewer, larger calls vs many tiny ones is the latency/cost knob.
4. **All batches run in parallel** (`async_utils.safe_gather`). Each batch's `process()` (`observational_batch.py:102`) builds a prompt and calls a `SchematicGenerator` that returns, per guideline, `{condition, rationale, applies: bool}` (`GenericObservationalGuidelineMatchSchema`, `observational_batch.py:59`). `applies=true` → a `GuidelineMatch{score:10, rationale}`; otherwise `score:1`. Retries use `optimization_policy.get_guideline_matching_batch_retry_temperatures()` (escalating temperature on retry).
5. `transform_matches` per strategy post-processes; results are flattened.

The matching prompt (`observational_batch.py:225`) is verbatim instructive: it frames each guideline as a natural-language "when" condition, asks the model to *"evaluate the relevance and applicability of a set of provided 'when' conditions to the most recent state of an interaction"*, and explicitly handles the hard case — a condition stops applying once the conversation *moves past the sub-topic*, with detailed sub-issue-vs-new-topic reasoning. This is the non-obvious part: condition matching is stateful over the conversation, not a one-shot classifier.

### Relational resolver — the dependency/exclusion/entailment graph (KNOWN — `relational_resolver.py`)

Matching tells you which conditions fire; the resolver decides which matched guidelines actually survive, using **NetworkX DiGraphs, one per relationship kind** (`relationships.py:43`): `ENTAILMENT`, `PRIORITY`, `DEPENDENCY` (AND across targets), `DEPENDENCY_ANY` (OR), `DISAMBIGUATION`, `REEVALUATION`, `OVERLAP`. Relationship targets can be a guideline, a tag (`TAG_ALL`/`TAG_ANY`), or a tool. `RelationalResolver.resolve()` (`relational_resolver.py:264`) iterates the four stages **until the match set stabilizes** or `MAX_ITERATIONS = 3` (`:232`):
1. **Dependencies** — drop a guideline whose dependency targets aren't met (topological sort, single pass; `UNMET_DEPENDENCY_ALL`/`_ANY`).
2. **Relational prioritization** — remove guidelines deprioritized by higher-priority guidelines/tags/journeys (transitive).
3. **Numerical priority** — keep only entities at the highest numeric priority level. Runs *before* entailment so an entailed guideline can't get its entailer filtered.
4. **Entailment** — *activate additional* guidelines implied by matched ones (`ENTAILED` — guidelines that fire because another matched, even if their own condition didn't).

Multiple iterations are needed because the stages interact (priority filtering may remove a dependency target, requiring another dependency pass to cascade). Output: surviving guidelines + journeys + a full `Resolution` audit trail (why each was kept/removed/added).

### Context assembly — inject only the survivors (KNOWN — `prompt_builder.py`)

`PromptBuilder` assembles named sections, each with a `SectionStatus` (`ACTIVE`/`PASSIVE`/`NONE`). `BuiltInSection` (`prompt_builder.py:56`): `AGENT_IDENTITY, CUSTOMER_IDENTITY, INTERACTION_HISTORY, CONTEXT_VARIABLES, GLOSSARY, GUIDELINE_DESCRIPTIONS, GUIDELINES, STAGED_EVENTS, JOURNEYS, OBSERVATIONS, CAPABILITIES`. The message-generation prompt (`add_guidelines_for_message_generation`, `:548`) injects **only** `ordinary` + `tool_enabled` matched guidelines (`chain(ordinary, tool_enabled)`) — the unmatched 95% are never serialized. This is the narrowing made concrete: the prompt size scales with *matched* guidelines, not *total* guidelines.

### Observations → tool-activation binding (KNOWN — `engine.py` `_find_tool_enabled_guideline_matches`)

A tool is **not** globally available to the agent. Tools are bound to guidelines via `guideline_tool_associations`. `_find_tool_enabled_guideline_matches` (`engine.py`) loads all associations, then keeps only those whose `guideline_id` is in the *matched* set — so a tool is offered to the LLM **only when its guideline's condition matched this turn**. An "observation" is a special guideline with a condition but no action (`create_observation`, `sdk.py:2763`) used purely to gate tool presence: "when the user asks about billing → make the `lookup_invoice` tool available." This kills the false-positive tool-invocation problem (the model can't call a tool it can't see because the situation didn't arise). Journey nodes also carry tools and are projected into `journey_node:`-prefixed guidelines so the same association mechanism applies.

### Tool calling — batched argument inference + skip/insight evaluation (KNOWN — `tool_calling/tool_caller.py`, `overlapping_tools_batch.py`)

Once matched guidelines carry tools, `ToolCaller.infer_tool_calls` (`tool_caller.py:174`) decides *whether and how* to call them — and it mirrors the matcher's batched design. A `ToolCallBatcher` splits work into batches (`single_tool_batch` for a tool used by one guideline; `overlapping_tools_batch` for a tool reachable via multiple matched guidelines, which need argument reconciliation). Each batch is one LLM call returning a structured schema. The overlapping schema (`overlapping_tools_batch.py:60-88`) is unusually rigorous: per candidate argument it asks for `acceptable_source_for_this_argument_according_to_its_tool_definition` (force the model to justify where each arg value comes from vs the tool's declared param) plus a `ValidationStatus`. The output is `ToolCall{tool_id, arguments}`. Crucially the engine also emits **`ToolInsights`** (`tool_caller.py:109`) with a per-tool `ToolCallEvaluation`:
- `NEEDS_TO_RUN` (`"success"`) — call it,
- `DATA_ALREADY_IN_CONTEXT` — skip; the answer is already known (avoids redundant calls),
- `CANNOT_RUN` — missing/invalid params,

plus structured `missing_data: [MissingToolData]` / `invalid_data: [InvalidToolData]`. These insights feed back into the preparation loop (`_inject_tool_insights`, `engine.py`) so the agent can *ask the user for the missing parameter* instead of failing the call. **For Verso:** tool-call inference should be batched (single vs overlapping), should force per-argument source justification (a strong hallucinated-argument defense), and should return a tri-state evaluation + missing-data list so the agent loop can recover (ask for the param) rather than just erroring — far better than the typical "LLM emitted a tool call, run it, hope the args are right."

### Journeys — a guideline-projected state machine (KNOWN — `journeys.py`, `journey_guideline_projection.py`)

A `Journey` (`journeys.py:88`) is a directed graph: `root_id` + `JourneyNode{action, tools, composition_mode}` + `JourneyEdge{source, target, condition}` — i.e. a state machine where each **edge transition is gated by a natural-language `condition`** and each **node carries an action + its own tools**. Journeys are `triggers`-activated (a guideline match starts the journey) and have a numeric `priority`. The clever unification: nodes/edges are **projected into guidelines** (`journey_guideline_projection.py`) with `journey_node:`-prefixed IDs, so the *same* matching + resolver + tool-association machinery drives journey progression — there's no separate journey interpreter. Compare to LangGraph (covered, `LANGGRAPH.md`): Parlant's journey is a lighter, condition-driven conversational state machine that reuses the guideline engine rather than a generic Pregel graph.

### Composition modes + Python SDK (KNOWN — `sdk.py`)

`CompositionMode` (`sdk.py:3318`): `FLUID` (LLM writes freely, guided), `COMPOSITED` (mix of canned + generated), `STRICT` (only canned responses — no free generation, for compliance). Set per-guideline, per-journey-node, or per-agent.
```python
guideline = await agent.create_guideline(
    condition="the customer asks about a refund",
    action="explain the 30-day refund policy and offer to start a return",
    tools=[start_return],                 # tools active ONLY when this condition matches
    criticality=Criticality.HIGH, composition_mode=CompositionMode.STRICT, ...)
obs = await agent.create_observation(     # condition + tools, no action → pure tool gate
    condition="the customer mentions an order number", tools=[lookup_order])
journey = await agent.create_journey(title=..., description=..., triggers=[guideline])
node = await journey.create_node(action=..., tools=[...])   # state-machine node
@p.tool
async def start_return(context: ToolContext, order_id: str) -> ToolResult: ...
```

### For Verso

- **This is the reference implementation for Verso's context-narrowing layer — copy the shape directly.** Per turn: (1) evaluate every registered guideline's condition against the current state in *parallel batched LLM calls* returning `{applies, rationale}` per guideline, (2) run a relationship resolver (dependency/priority/entailment as separate graphs, iterate-to-stable, cap at 3), (3) inject *only* the surviving guidelines + their bound tools into the generation prompt. Verso's "context engineering at the framework level" is exactly this: prompt size ∝ matched rules, not total rules.
- **Tool presence must be condition-gated, not global.** The highest-leverage anti-hallucination move here is binding tools to guidelines and exposing a tool to the LLM *only when its guideline matched*. Verso should make tool availability a function of matched context, not a static registry — an observation-style "when X → tool Y becomes visible" binding. This is strictly better than handing the model 40 tools and hoping it picks right.
- **Batch the condition-evaluation LLM calls, with an explicit batch-size policy.** One LLM call per guideline is too expensive; one call for all is too lossy. Parlant's `OptimizationPolicy.get_guideline_matching_batch_size` + parallel `safe_gather` + escalating retry temperatures is the right knob set. Verso's matcher should expose batch size and run batches concurrently.
- **Relationships-as-graphs beats priority-as-a-number.** Modeling guideline interactions as typed DiGraphs (dependency / priority / entailment / disambiguation) and resolving them to a stable set, *with an audit trail of why each rule was kept/dropped/added*, is far more controllable than a flat priority integer. For a compliance-grade agent, the audit trail (`Resolution`/`ResolutionDetails`) is the explainability layer Verso needs.
- **Journeys = state machine projected onto the same matcher.** Rather than a separate workflow interpreter, Parlant projects journey nodes/edges into guidelines so one engine drives both ad-hoc guidance and structured multi-turn SOPs. If Verso wants conversational workflows, this projection trick (state machine → guidelines → same matching loop) avoids maintaining two execution engines — a lighter alternative to bolting on LangGraph for conversation flows.
- **Composition modes (`FLUID`/`COMPOSITED`/`STRICT`) are the compliance dial.** `STRICT` (canned-only, no free generation) per-guideline is how you make *parts* of an agent provably safe while leaving the rest fluid. Verso should support per-context composition modes so a single agent can be free-form in low-stakes turns and locked to approved text in regulated ones.

---

## Cross-System Patterns

### Snapshot semantics: memory vs disk is the defining axis

| System | Snapshot captures | Resume is | Mechanism |
|---|---|---|---|
| **E2B** | live guest **RAM** + disk | warm resume (~150 ms) of a running VM | UFFD lazy page-fault + 4 KiB diff-vs-base dedup |
| **Daytona** | filesystem only | cold container recreate | `docker commit` + registry push |
| **microsandbox** | filesystem only (writable overlay) | cold microVM boot (<100 ms) | overlay dir copy |
| **CF Sandboxes** | container state (DO-coordinated) | fast restore vs cold start | closed (Containers + DO) |

**Verso implication:** the `CodeSandbox.snapshot()` protocol must declare which it is. Only UFFD-class preserves a *running* process tree; the rest preserve disk and cold-boot. Default to disk snapshots (simple, covers most agent work); offer memory snapshots only as a warm-pool optimization.

### Daemon-in-sandbox: every system has one, transports differ

E2B = `envd` (ConnectRPC: REST `/init`/`/files`/`/health` + gRPC Process/Filesystem streaming). Daytona = toolbox (plain Gin REST, daemon binary bind-mounted RO as entrypoint). microsandbox = `agentd` (binary frame protocol over a Unix relay socket). CF = the isolate itself + RPC stubs. **Verso implication:** standardize on one in-sandbox agent with a two-tier protocol — slow lifecycle over REST, hot path (process spawn + stream + signals + fs-watch) over a streaming RPC addressing processes by `pid|tag` for reconnect. Inject the daemon by bind-mount, not by baking it into images.

### Egress credential injection: never put the secret in the sandbox

CF (`globalOutbound` proxy that adds tokens) and microsandbox (userspace netstack + TLS interception) both keep credentials *outside* the sandbox and splice them in at an egress proxy the host controls. E2B injects an access-token *hash* via MMDS and re-validates at `/init` — secrets never enter the snapshot. **Verso implication:** Code-Mode tool calls should be capability stubs; the parent holds credentials and injects them at a controlled egress proxy. Default egress to *off*; opt into a credential-bearing proxy binding per tool.

### Context narrowing (Parlant) is the agent-control analog of snapshot dedup (E2B)

Both are "ship only the diff." E2B ships only the memory pages that differ from the base template; Parlant ships only the guidelines whose conditions match the current turn. **Verso implication:** the framework's job is to compute, per turn, the minimal relevant context (matched rules + their tools) and the minimal relevant state (the diff), not to hand the model/VM everything and let it sort it out. Verso's context-engineering layer and its sandbox-snapshot layer are the same idea applied to prompts and to memory.
