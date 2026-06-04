# hermes-surfaces — Hermes: Providers / Surfaces

**Source files:**
- `teardowns/HERMES_DEEP_PROVIDERS.md` (2,897 lines) — provider plugin system, 4 api_mode adapters, tool-call parsers, thinking/reasoning handling, credential pooling
- `teardowns/HERMES_DEEP_TERMINAL.md` (2,650 lines) — 8 terminal execution backends with pluggable persistence
- `teardowns/HERMES_DEEP_TUI.md` (2,978 lines) — JSON-RPC TUI gateway: 64 methods, 35 event types, transport layer
- `teardowns/HERMES_DEEP_SLACK.md` (4,236 lines) — Slack adapter: Socket Mode, session keying, mrkdwn conversion, multi-workspace

**Repo HEAD:** `NousResearch/hermes-agent` @ `8191f66` / `4117fc3`

---

## 1. Provider Plugin System (`HERMES_DEEP_PROVIDERS.md`)

### 1.1 The ProviderProfile Declarative Dataclass

Hermes replaced a forest of `if provider == 'kimi'` branches with a single declarative `@dataclass` (`providers/base.py:38–80`). Every transport reads one profile object — it does not receive N boolean flags.

```python
@dataclass
class ProviderProfile:
    name: str
    api_mode: str = "chat_completions"          # chat_completions | anthropic_messages | codex_responses | bedrock_converse
    aliases: tuple = ()
    display_name: str = ""
    description: str = ""
    signup_url: str = ""
    env_vars: tuple = ()
    base_url: str = ""
    models_url: str = ""
    auth_type: str = "api_key"                  # api_key | oauth_device_code | oauth_external | copilot | aws_sdk | external_process
    supports_health_check: bool = True          # False → skip /models probe (e.g. Xiaomi MiMo)
    fallback_models: tuple = ()
    hostname: str = ""
    default_headers: dict[str, str] = ...
    fixed_temperature: Any = None               # None | OMIT_TEMPERATURE sentinel | float
    default_max_tokens: int | None = None
    default_aux_model: str = ""
```

**OMIT_TEMPERATURE sentinel** (`providers/base.py:21`): `OMIT_TEMPERATURE = object()`. Three states: `None` → use caller's default, `OMIT_TEMPERATURE` → strip field unconditionally, float → override. Kimi uses the sentinel because their server manages temperature internally and errors if sent. Identity check: `if profile.fixed_temperature is OMIT_TEMPERATURE: kwargs.pop("temperature", None)`.

**Five polymorphic hooks** (the only methods on the dataclass):
1. `get_hostname()` — URL→provider reverse mapping. Default derives from `base_url` via `urllib.parse.urlparse`. No override needed by most plugins.
2. `prepare_messages(messages)` — pre-send message normalization. Qwen only: normalizes content to list-of-dicts, injects `cache_control: {"type": "ephemeral"}` on the last system-message part to pin Qwen's prompt cache.
3. `build_extra_body(*, session_id=None, **context)` → `dict`. Injects provider-specific blobs. Nous: product-line metrics tags. Qwen: `vl_high_resolution_images=True`. OpenRouter: `provider preferences` dict + Pareto router plugin.
4. `build_api_kwargs_extras(*, reasoning_config=None, **context)` → `Tuple[dict, dict]` = `(extra_body_additions, top_level_kwargs)`. The split exists because some providers put reasoning config in `extra_body` (OpenRouter: `extra_body.reasoning`) while others want it top-level (Kimi: `api_kwargs.reasoning_effort`). This split is the entire architectural reason the dataclass exists — without it every adapter needs its own if/elif tree.
5. `fetch_models(*, api_key=None, timeout=8.0)` — catalog probe. Default builds an authenticated request to `models_url` or `{base_url}/models`. Overrides: Anthropic uses `x-api-key` + `anthropic-version` headers; Bedrock returns `None` (AWS SDK path); OpenRouter caches the 200+ model catalog module-level; Custom returns `None` if base_url empty.

### 1.2 Plugin Discovery (zero-touch override)

`providers/__init__.py:140–191`. Three discovery paths, last-writer-wins, lazy import on first `get_provider_profile()` call:

1. Bundled: `plugins/model-providers/<name>/__init__.py` (installed with the package)
2. User: `$HERMES_HOME/plugins/model-providers/<name>/__init__.py` (drops a file → overrides bundled, no repo edits)
3. Back-compat: `providers/<name>.py` (legacy single-file format still works)

Hyphen-to-underscore conversion for Python module names (`openai-codex/` → module `plugins.model_providers.openai_codex`). Failure isolation: broken plugin logs a warning, removed from `sys.modules`, registry falls back to generic profile — does NOT crash the agent.

**30 bundled plugins** across 4 api_modes:
- `anthropic_messages` (4): anthropic, minimax, minimax-cn, minimax-oauth
- `codex_responses` (2): openai-codex, xai
- `bedrock_converse` (1): bedrock
- `chat_completions` (23): everything else including Gemini (which routes to a custom native client inside the transport)

### 1.3 The Four api_mode Adapters

Every adapter outputs the same `SimpleNamespace(choices=[...], usage=...)` shape regardless of the upstream provider wire format.

**chat_completions** (`auxiliary_client.py`, 5,403 lines): standard OpenAI-compatible path for 23 providers. Key features:
- 7-step auto-resolution chain for text tasks, 5-step for vision. Codex OAuth intentionally excluded from auto-fallback because its model allow-list shifts unpredictably.
- HTTP 402 / credit-exhaustion fallback: `call_llm()` retries with next provider in chain automatically.
- Lazy `openai.OpenAI` import: the openai SDK has a ~240ms cold import tree. `_OpenAIProxy` defers it to first use while preserving all 15+ construction sites unchanged.
- `_CodexCompletionsAdapter` / `_AnthropicCompletionsAdapter`: wrap non-standard APIs into a `chat.completions` shape so auxiliary callers work unchanged regardless of main provider.

**anthropic_messages** (`anthropic_adapter.py`, 2,273 lines): Messages API used for Anthropic, MiniMax, Kimi /coding, DeepSeek /anthropic, Azure AI Foundry Anthropic.
- Output token limits: per-model table from 4,096 (Claude 3) to 128,000 (Opus 4.7). Default 128K for unknown future models.
- Thinking budget map: `{"xhigh": 32000, "high": 16000, "medium": 8000, "low": 4000}` for manual mode. Separate `ADAPTIVE_EFFORT_MAP` for Claude 4.6+ adaptive mode.
- Model detection substrings: `("4-7", "4.7")` → adaptive+xhigh+no-sampling-params; `("opus-4-6", "opus-4.6")` → fast mode supported.
- Beta header selection is per-endpoint: common betas are `interleaved-thinking-2025-05-14` + `fine-grained-tool-streaming-2025-05-14`. `context-1m-2025-08-07` is deliberately NOT included for direct Anthropic (breaks non-beta accounts on short calls) but IS added for Azure AI Foundry.
- Orphan stripping: context compression can remove either side of a tool-call pair. Anthropic rejects orphan `tool_use` (no matching `tool_result`) and orphan `tool_result` (no matching `tool_use`) with HTTP 400.
- Screenshot eviction: keeps only the most recent `_MAX_KEEP_IMAGES = 3` computer-use screenshots. Base64 images cost ~1,465 tokens each and accumulate across tool calls.
- Claude Code identity spoofing for OAuth: replaces `"Hermes Agent"` → `"Claude Code"`, adds `mcp_` tool-name prefix on outbound, strips it on inbound. "To avoid Anthropic's server-side content filters."

**codex_responses** (`codex_responses_adapter.py`, 1,089 lines): OpenAI Responses API.
- Tool-call leak detection: pattern `r"(?:^|[\s>|])to=functions\.[A-Za-z_][\w.]*"` catches when Codex serializes tool calls into message content instead of structured output. Sets `finish_reason = "incomplete"` to re-elicit.
- Deterministic `call_id`: `sha256(f"{fn_name}:{arguments}:{index}")[:12]`. "Deterministic IDs prevent cache invalidation — random UUIDs would make every API call's prefix unique, breaking OpenAI's prompt cache."
- Must include `"include": ["reasoning.encrypted_content"]` — without it, encrypted reasoning state is not returned and multi-turn coherence breaks.

**bedrock_converse** (`bedrock_adapter.py`, 1,289 lines):
- Strict alternation enforcement (Bedrock Converse requires first and last messages to be `user`).
- Static context-length table (1,245–1,289 lines) because Bedrock has no `/models` REST endpoint.
- Overflow/rate-limit classification: `context_overflow` vs `rate_limit` vs `auth` from Bedrock exception shapes.

### 1.4 Tool-Call Parser Quirks Per Provider Family

Each provider family has its own tool-call serialization format that Hermes normalizes to its internal `{id, name, arguments}` shape:

| Family | Format | Key quirk |
|--------|--------|-----------|
| Anthropic | `tool_use` blocks in content array | Signature validation; thinking blocks can interleave |
| Gemini | `FunctionCall` protobuf → JSON | No native call ID — client mints `call_{uuid.hex[:12]}`. Gemini 3 adds `thoughtSignature` per call that MUST replay on next turn |
| OpenAI | `tool_calls` array | Standard `call_*` IDs, stable across turns |
| Bedrock | `toolUse` blocks | `tool_*` IDs server-issued |
| Codex Responses | `function_call` items | TWO IDs: `call_id` (cross-turn replay) + `fc_*` response_item_id (prefix cache) |
| Hermes/Qwen/DeepSeek text-mode | Inline XML or JSON in message body | Legacy text-mode tool calls need parser |

Gemini schema munger (`gemini_schema.py:1–99`): Gemini's tool parameter schema is a strict subset of JSON Schema. Dropped features: `$schema`, `$ref`, `additionalProperties`, `not`, `if/then/else`, `allOf` (only `anyOf` allowed), `multipleOf`, `exclusiveMinimum/Maximum`, `dependencies`, `const`. Empty schema after sanitization → `{"type": "object", "properties": {}}`.

### 1.5 Reasoning / Thinking Handling

Hermes normalizes provider-specific reasoning into three internal slots: `reasoning` (human-readable summary), `reasoning_content` (provider's native text for replay), `reasoning_details` (opaque structured items — Anthropic thinking blocks, encrypted Codex items).

**Thinking signature management** (three policies):
1. Kimi/DeepSeek `/anthropic`: strip signed Anthropic blocks (can't validate), preserve unsigned blocks synthesized from `reasoning_content`.
2. Third-party OR non-latest assistant on direct Anthropic: strip all thinking blocks.
3. Latest assistant on direct Anthropic: preserve signed, downgrade unsigned to text, strip `cache_control` from thinking blocks ("cache markers interfere with signature validation").

**`reasoning_content` preservation** — four-source priority chain:
1. SDK-exposed `assistant_message.reasoning_content`
2. `model_extra` dict on the SDK object
3. Kimi/DeepSeek pad: `reasoning_text or " "` (single space — DeepSeek V4 Pro rejects empty string `""`)
4. Promoted from streaming `delta.reasoning_content` chunks (some providers accumulate through streaming but never set it on the final message object)

**Adaptive thinking** (Claude 4.6+): `{"type": "adaptive", "display": "summarized"}`. The `display: "summarized"` is forced because the 4.7+ default of `display: "omitted"` silently hides reasoning content. `output_config.effort` carries the level. Downgrade `xhigh`→`max` for models that don't list `xhigh` as a supported level.

**Manual thinking** (older Claude): `{"type": "enabled", "budget_tokens": N}`, force `temperature=1`, bump `max_tokens` to `max(effective_max_tokens, budget + 4096)`.

**Sampling param strip on 4.7+**: even after the reasoning path sets `temperature=1` (for manual thinking), the safety net strips `temperature`, `top_p`, `top_k` for models that reject sampling params (4.7+).

### 1.6 Credential Pooling

`credential_pool.py` (1,999 lines): persistent multi-credential pools for same-provider failover.

**Cooldown TTLs:**
- 401 (transient auth) → 5 minutes (allows single-key setups to recover quickly)
- 429 (rate limit) → 1 hour
- 402 (billing) → 1 hour
Provider-supplied `reset_at` timestamps override these defaults.

**Four rotation strategies:** `fill_first` (default), `round_robin`, `random`, `least_used`.

**Soft-lease semaphore:** `_active_leases: {credential_id: int}`. Per-process concurrent request counter. Prefers entries below cap; falls back to least-leased if all at cap (never blocks — always picks best available).

**Multi-process OAuth sync:** Three special-cases (Anthropic Claude Code, OpenAI Codex device_code, xAI OAuth) sync token refresh from disk because OAuth refresh tokens are single-use. Pattern: if `file_refresh != entry.refresh_token`, replace entry, re-persist. Prevents "refresh_token_reused" 4xx when another process (Claude Code CLI, browser) refreshed first.

---

## 2. Terminal Execution Backends (`HERMES_DEEP_TERMINAL.md`)

### 2.1 Backend Roster

8 concrete `BaseEnvironment` subclasses across 7 `TERMINAL_ENV` values:

| Backend | Process model | Persistence | Wakeup latency |
|---------|---------------|-------------|----------------|
| Local | `subprocess.Popen` with `os.setsid` | Host FS (always live) | n/a |
| Docker | `docker exec` into long-lived `sleep infinity` container | bind mounts `/root`+`/workspace` or tmpfs | Cold pull ~120s; restart ~2s |
| Singularity | `apptainer exec instance://` | Writable overlay dir or `--writable-tmpfs` | ~2–5s |
| SSH | `ssh -o ControlMaster ... bash -c <cmd>` | Remote host FS + FileSyncManager | ControlMaster ~1s; cold ~10s |
| Modal direct | `modal.Sandbox.create()` + `sandbox.exec.aio()` | `snapshot_filesystem()` → image ID in `~/.hermes/modal_snapshots.json` | Restore ~30–60s |
| Managed Modal | HTTPS to Nous Tool Gateway (`POST /v1/sandboxes/{id}/execs`) | Gateway-owned; opt-in snapshot | Gateway round-trip (seconds) |
| Daytona | `Daytona().sandbox.process.exec(cmd)` via SDK | `sandbox.stop()` preserves FS | Resume ~5–15s |
| Vercel Sandbox | `sandbox.run_command("bash", ["-lc", ...])` | `sandbox.snapshot()` → ID in `~/.hermes/vercel_sandbox_snapshots.json` | Cold ~5–15s; restore ~10–30s |

### 2.2 BaseEnvironment Abstract Interface

Only **two** abstract methods: `_run_bash(cmd_string, ...) -> ProcessHandle` and `cleanup()`. Everything else is provided by the base class.

`ProcessHandle` is a duck-type `Protocol` (not ABC):
```python
class ProcessHandle(Protocol):
    def poll(self) -> int | None: ...
    def kill(self) -> None: ...
    def wait(self, timeout: float | None = None) -> int: ...
    @property
    def stdout(self) -> IO[str] | None: ...
    @property
    def returncode(self) -> int | None: ...
```

`subprocess.Popen` natively satisfies the protocol. SDK-only backends (Modal, Daytona, Vercel) use `_ThreadedProcessHandle`: a daemon thread that runs the blocking SDK call, feeds output through an `os.pipe`, and exposes the same poll/wait/kill interface.

### 2.3 Session Lifecycle and `_wrap_command`

Every command runs through the same pipeline:
```
init → (source snapshot → cd → eval → re-export env → write CWD marker → exit) × N → cleanup
```

The `_wrap_command` script per command (`base.py:417–467`):
```bash
source $SNAP >/dev/null 2>&1 || true        # >/dev/null load-bearing: macOS bash 3.2 leaks declare -x to stdout
builtin cd -- {quoted_cwd} || exit 126       # 126 = "cd failed" sentinel
eval '{escaped}'
__hermes_ec=$?
export -p > $SNAP 2>/dev/null || true        # rewrites snapshot with new env; last-writer-wins, no lock
pwd -P > $CWDFILE 2>/dev/null || true
printf '\n{MARKER}%s{MARKER}\n' "$(pwd -P)" # leading \n load-bearing: ensures marker is on its own line
exit $__hermes_ec
```

CWD tracking: `__HERMES_CWD_{session_id}__` bracketing markers in stdout. Remote backends extract CWD from stdout; local backend reads a temp file. The marker is session-scoped (deterministic, unambiguous).

Session init bootstrap (`init_session`): `export -p`, `declare -f`, `alias -p` → snapshot file. On failure, falls back to `bash -l` per command.

### 2.4 `_wait_for_process` Poll Loop (236 lines)

Constants and behaviors that Verso needs to know:
- **Adaptive sleep**: starts at 5ms, grows ×1.5 per iteration, ceilings at 200ms. "For an `echo` this saves ~195ms per tool call."
- **4,096-byte read chunks** with UTF-8 `incremental_decoder` (`errors="replace"`) — multibyte char split across chunks handled.
- **Idle-after-exit counter**: after bash exits, waits for **3 idle × 100ms cycles** before declaring EOF. Solves orphaned-grandchild deadlock: a `setsid cmd & disown` grandchild inherits the write-end of bash's stdout pipe; even after bash exits the pipe stays open.
- **Interrupt**: `is_interrupted()` checked every poll iteration. On true → `_kill_process(proc)`, drain join with 2s timeout, return `returncode=130` with `"[Command interrupted]"`.
- **Timeout**: wall-clock deadline; on expiry → kill, `returncode=124`, `"[Command timed out after Ns]"`.
- **Activity callback**: fires every 10s while running so the gateway's inactivity timeout doesn't kill long-running commands.

### 2.5 Local Backend: Process-Group Kill

`local.py:549–617`. The only subclass override of `proc.kill()`:
1. Compute PGID via `os.getpgid(proc.pid)`, fallback to `proc._hermes_pgid`.
2. `os.killpg(pgid, SIGTERM)`.
3. Wait up to 1.0s for group exit (poll every 50ms).
4. If still alive: `os.killpg(pgid, SIGKILL)`.
5. Wait up to 2.0s.
6. `proc.wait(timeout=0.2)` to reap wrapper.

`_group_alive(pgid)` probes with `os.killpg(pgid, 0)` (signal 0 = existence query); returns True on `PermissionError` because the group exists even if we can't signal it.

### 2.6 Docker Security Model

Non-negotiable security args:
```python
"--cap-drop", "ALL",
"--cap-add", "DAC_OVERRIDE",   # root can write to bind-mounted dirs
"--cap-add", "CHOWN",
"--cap-add", "FOWNER",
"--security-opt", "no-new-privileges",
"--pids-limit", "256",
"--tmpfs", "/tmp:rw,nosuid,size=512m",
"--tmpfs", "/var/tmp:rw,noexec,nosuid,size=256m",
"--tmpfs", "/run:rw,noexec,nosuid,size=64m",
```

Storage-opt (`--storage-opt size=<disk>m`) only works on overlay2+XFS+pquota. Probed at first use via `docker create --storage-opt size=1m hello-world`; result cached process-wide. macOS explicitly skipped.

Persistent mode: bind-mount `~/.hermes/sandboxes/docker/<task_id>/home:/root` and `…/workspace:/workspace`. Ephemeral: `--tmpfs /workspace:rw,exec,size=10g` + `--tmpfs /home:rw,exec,size=1g`.

### 2.7 Idle Reaper and FileSyncManager

Idle reaper (`_cleanup_inactive_envs`): tears down backends after `TERMINAL_LIFETIME_SECONDS = 300` (5 min default). Backends are stored in `_active_environments[task_id]`.

`FileSyncManager` (`file_sync.py`, 402 lines): tracks `(mtime, size)` per remote path, sha256 of pushed files, batches uploads via backend-specific bulk upload (tar-over-SSH, base64-tar-over-stdin for Modal/Vercel, Daytona SDK `upload_files`, Vercel `write_files`). Runs `sync_back` on cleanup with conflict last-write-wins.

---

## 3. TUI Gateway (`HERMES_DEEP_TUI.md`)

### 3.1 Transport Layer

**Protocol: newline-delimited UTF-8 JSON-RPC 2.0, one object per line.** No length prefix, no MessagePack, no SSE framing.

```python
line = json.dumps(obj, ensure_ascii=False) + "\n"   # server.py:137
```

**Two transports, same protocol:**
- `StdioTransport`: Python stdout/stdin, Node `readline.createInterface`. Reader: `for raw in sys.stdin:` + `.strip()` + `json.loads`.
- `WSTransport`: FastAPI-mountable WebSocket. `await ws.receive_text()` + same strip/parse. One JSON object per WebSocket text frame.

**JSON-RPC shapes:**
```python
def _ok(rid, result: dict):  return {"jsonrpc": "2.0", "id": rid, "result": result}
def _err(rid, code, msg):    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": msg}}
def _emit(event, sid, payload=None):
    params = {"type": event, "session_id": sid}
    if payload is not None: params["payload"] = payload
    write_json({"jsonrpc": "2.0", "method": "event", "params": params})  # no "id"
```

Events ride the same JSON-RPC envelope with `method = "event"` and no `id`. TS client demuxes by presence of `id` (pending RPC resolution) vs `method == "event"` (event dispatch). Unknown `params.type` is silently dropped by `asGatewayEvent`.

**Request ID convention** (`gatewayClient.ts:686`): client-assigned monotonic integer, stringified. Unknown method → `-32601`.

**`TeeTransport`**: wraps another transport, fans out every emission to both the primary transport AND a `WsPublisherTransport` sidecar (best-effort dashboard mirror). Same use-case mirrored from the JS side: `HERMES_TUI_SIDECAR_URL` env var makes the TS client forward every received event frame to a secondary WS.

### 3.2 Server Lifecycle

Boot sequence (`entry.py`):
1. `sys.path` sanitation: strip `""` and `"."` (would let local `utils/` shadow installed packages).
2. Import `tui_gateway.server` (heavy — ~200–400ms cascade: run_agent, tools, hermes_cli, hermes_state).
3. Conditional MCP discovery: `discover_mcp_tools()` only if `config.mcp_servers` is non-empty. "Previously a module-level side effect that froze the gateway loop" (issue #16856). `mcp` SDK transitively pulls `pydantic`, `httpx`, `jsonschema`, `starlette` parsers — ~200ms.
4. Emit `gateway.ready` event. If first write fails → `sys.exit(0)` (no point dispatching to a dead pipe).
5. Main loop: `for raw in sys.stdin:` → `json.loads` → `dispatch` → `write_json`.

All exit paths log to `~/.hermes/logs/tui_gateway_crash.log`. Four exit paths: startup write fail, parse-error write fail, dispatch-response write fail, stdin EOF.

**Signal handling:** `SIGTERM`/`SIGINT` → log signal, `sys.exit(0)`. `SIGPIPE`/`SIGHUP` → graceful exit with crash log. Windows: `SIGBREAK` as weak equivalent of `SIGHUP`. Windows lacks `SIGPIPE` semantics.

**Thread pool** (`server.py:684`): every `prompt.submit` call runs in a `ThreadPoolExecutor` so the dispatch loop never blocks. Long-running agent turns are async/threaded.

**Shutdown drain**: on signal, the server waits for in-flight turns to complete before exiting (`server.py:719–758`). Per-session `threading.Event` `agent_ready` and a drain timeout.

### 3.3 Complete JSON-RPC Method Catalog (64 methods)

**Session lifecycle (15):** `session.create`, `session.list`, `session.most_recent`, `session.resume`, `session.delete`, `session.title`, `session.usage`, `session.status`, `session.history`, `session.undo`, `session.compress`, `session.save`, `session.close`, `session.branch`, `session.interrupt`.

`session.create` details:
- Params: `{cols?: number}`. Response: `{session_id, info: {model, tools, skills, cwd, lazy: true, profile_name}}`.
- `lazy: true` signals deferred agent build. Schedules 50ms-deferred `_start_agent_build()` so Ink can paint the composer before the heavy import.
- When build completes, emits `session.info` with full populated dict.

`session.resume`:
- Params: `{session_id, cols?}`. Response: `{session_id, resumed, message_count, messages, info}`.
- `db.reopen_session(target)` un-ends the DB row. Builds fresh `AIAgent` with `session_id=target` (memory + DB writes attach to the same row).

**Delegation / subagent (3):** `delegation.status`, `delegation.pause`, `subagent.interrupt`.

**Spawn-tree snapshots (3):** `spawn_tree.save`, `spawn_tree.list`, `spawn_tree.load` — for multi-agent task trees.

**Steering + terminal (2):** `session.steer`, `terminal.resize`.

**Prompt / submission (5):** `prompt.submit`, `prompt.background`, `clipboard.paste`, `image.attach`, `input.detect_drop`.

`prompt.submit` is the hot path — dispatches to `_run_prompt_submit()` in a thread. Emits `message.start` before any model call, `message.delta` per streaming chunk, `message.complete` on finish.

**Blocking-prompt responses (4):** `clarify.respond`, `sudo.respond`, `secret.respond`, `approval.respond` — these are the inbound responses to `clarify.request` / `sudo.request` / etc. events.

**Config (3):** `config.set`, `config.get`, `setup.status`.

**Process/reload (3):** `process.stop`, `reload.mcp`, `reload.env`.

**CLI plumbing (4):** `commands.catalog`, `cli.exec`, `command.resolve`, `command.dispatch`.

**Paste/completion (3):** `paste.collapse`, `complete.path`, `complete.slash`.

**Model auth (3):** `model.options`, `model.save_key`, `model.disconnect`.

**Slash exec (1):** `slash.exec` — dispatches to slash worker subprocess (see §3.5).

**Voice (3):** `voice.toggle`, `voice.record`, `voice.tts`.

**Rollback (3):** `rollback.list`, `rollback.restore`, `rollback.diff`.

**Browser (1):** `browser.manage`.

**Tools/toolsets/agents (5):** `tools.list`, `tools.show`, `tools.configure`, `toolsets.list`, `agents.list`.

**Cron (1):** `cron.manage`.

**Skills (2):** `skills.manage`, `skills.reload`.

**Shell (1):** `shell.exec`.

### 3.4 Complete Server-Emitted Event Catalog (35 event types)

**Gateway lifecycle (5):** `gateway.ready` (once per boot, payload: `{skin: GatewaySkin}`), `gateway.stderr` (TS-synthesized from subprocess stderr), `gateway.start_timeout` (TS-synthesized after 15s without `gateway.ready`), `gateway.protocol_error` (malformed JSON), `skin.changed`.

**Session lifecycle (1):** `session.info` — the master state-sync event. Emitted after agent build, after any capability-changing `config.set`, after compress, after tools.configure, after `/model`/`/personality`/`/fast` slash commands. Payload is the full `SessionInfo` snapshot:
```ts
{
  model, reasoning_effort, service_tier, fast,
  tools: Record<string, string[]>,   // toolset_name → [tool_names]
  skills: Record<string, string[]>,
  cwd, version, release_date, update_behind, update_command,
  usage, profile_name,
  mcp_servers: Array<McpServerStatus>,
  system_prompt: string,             // agent._cached_system_prompt
  credential_warning?, config_warning?
}
```

**Message streaming (4):** `message.start` (before model call), `message.delta` (`{text, rendered?}`), `message.complete`, `message.error`.

**Tool execution (3):** `tool.start` (`{tool_name, tool_id, args}`), `tool.result` (`{tool_name, tool_id, output, exit_code?}`), `tool.error`.

**Clarify / blocking prompts (4):** `clarify.request`, `sudo.request`, `secret.request`, `approval.request` — gateway pauses agent and emits these; TUI shows interactive prompt; user response goes back via the `*.respond` methods.

**Session branching (2):** `branch.created`, `branch.loaded`.

**Background tasks (3):** `background.start`, `background.delta`, `background.complete`.

**Voice (3):** `voice.start`, `voice.delta`, `voice.complete`.

**Subagent (5):** `subagent.start`, `subagent.delta`, `subagent.complete`, `subagent.error`, `delegation.status`.

**Misc (5):** `notification.push`, `insight.ready`, `checkpoint.created`, `rollback.ready`, `error.fatal`.

### 3.5 Slash Worker Subprocess

Slash commands like `/help`, `/login`, `/cost`, `/config` run in a **separate subprocess** (`_SlashWorker`) because:
- They construct a fresh `HermesCLI` instance — side effects must not leak into the live `AIAgent`.
- Their stdout must not corrupt the JSON-RPC pipe.

Wire protocol (NOT JSON-RPC — simpler):
```python
# Request:  {"id": int, "command": "/help"}
# Response: {"id": int, "ok": true, "output": "..."}  or  {"id": int, "ok": false, "error": "..."}
```

Three tricks for silent construction:
1. `HermesCLI(...)` wrapped in `stdout/stderr → io.StringIO()` at startup to suppress banner.
2. Rich Console hijack: `cli.console = Console(file=buf, ...)` — `redirect_stdout` alone doesn't work because Rich captures its file handle at construction.
3. `cli_mod._cprint` monkey-patch: rebind to plain `print` so it lands in the capture buffer.

Correlation: sequential int ids (`self._seq`), lock ensures one outstanding request per worker. Timeout: `max(5.0, HERMES_TUI_SLASH_TIMEOUT_S or 45)` seconds.

Side-effect mirroring (`_mirror_slash_side_effects`): the slash worker has its own `AIAgent`; some commands (`/model`, `/personality`, `/prompt`, `/compress`, `/fast`, `/reload-mcp`) must mutate the LIVE agent. This handler does the mirror after the worker returns. Commands that mutate are blocked mid-turn: `_MUTATES_WHILE_RUNNING = {"model", "personality", "prompt", "compress"}`.

### 3.6 Client-Side Transport Selection

`HERMES_TUI_GATEWAY_URL` env var → WS attach mode (connects to remote running gateway). Absence → spawn child mode (`python -m tui_gateway.entry`).

Python discovery order: `HERMES_PYTHON` → `PYTHON` → active venv `bin/python` → repo `.venv/bin/python` → `python3`. Makes TUI work without global `pip install`.

Stale child identity guard: spawn captures `const ownedProc = this.proc`. Both `error` and `exit` handlers check `if (this.proc !== ownedProc)` before reacting. `start()` can replace `this.proc` while old child tears down — handlers must not clear the new ready timer.

Log buffer: `CircularBuffer<string>(200)` for stderr lines, truncated to 4,096 bytes each. Buffered events cap at 2,000. Events arriving before any subscriber are buffered, drained on first `drain()`.

URL redaction: `redactUrl()` scrubs bearer tokens from query strings in all logged/surfaced URLs.

---

## 4. Slack Adapter (`HERMES_DEEP_SLACK.md`)

### 4.1 Architecture Overview

- **Transport: Socket Mode only.** No HTTP Events API, no public ingress. `slack_bolt`'s `AsyncSocketModeHandler` drives the persistent WebSocket. Works behind firewalls/localhost.
- **Two tokens:** `xoxb-...` bot token (all REST API calls) + `xapp-...` app-level token with `connections:write` (Socket Mode handshake only).
- **Multi-workspace:** comma-separated `SLACK_BOT_TOKEN` + `~/.hermes/slack_tokens.json` merged + `auth.test`-validated per token. `team_id → AsyncWebClient` map. Primary token's `AsyncApp` drives Socket Mode; all workspaces share the same Socket Mode handler.
- **Zombie handler guard:** explicitly close previous `AsyncSocketModeHandler` before creating a new one on reconnect. Otherwise both connections receive every event and dispatch each twice.
- **Six event handlers, one command pattern, seven action IDs** registered at connect time.

### 4.2 Inbound Event Dispatch

Entry: `_handle_slack_message` (471 lines, `slack.py:1767–2238`).

**Layered guards (early-return chain):**
1. Dedup: `MessageDeduplicator(max_size=2000, ttl_seconds=300)` — catches Socket Mode reconnect redeliveries and `app_mention`/`message` overlap (same `ts`).
2. Bot message filter: three modes via `SLACK_ALLOW_BOTS` — `none` (default), `mentions` (only if @mentioned), `all` (except own echoes).
3. Edit/delete suppression: `message_changed` and `message_deleted` subtypes → silently dropped.
4. `!cmd` prefix rewriting: Slack blocks native slash commands in threads. `!stop` → `/stop` when first token is a registered gateway command.
5. Block Kit text extraction: `_extract_text_from_slack_blocks()` walks the rich_text block tree to recover forwarded/quoted content that the plain `text` field loses.
6. Channel allowlist: `SLACK_ALLOWED_CHANNELS` — DMs exempt.
7. Should-respond decision (5-gate layered check):
   - `free_response_channels` → always respond
   - `require_mention=False` → always respond
   - `strict_mention=True` → only if re-@mentioned
   - Otherwise: check (a) @mentioned, (b) thread where bot posted, (c) thread where bot was @mentioned, (d) existing persisted session for thread.

**Thread memory structures:**
- `_bot_message_ts`: bounded set (cap 5,000) of timestamps of bot's own posts + thread roots the bot replied to.
- `_mentioned_threads`: bounded set (cap 5,000) of thread roots where bot was @mentioned. Eviction: drop oldest 2,500 when cap exceeded.
- `_has_active_session_for_thread`: reads session store via `build_session_key()` — survives gateway restart.

**Thread context prefetch:** when the bot enters a thread for the first time (no existing session), fetches full `conversations.replies` history so the agent has context before responding.

**@mention stripping:** `<@U123>` removed from text before passing to agent. Thread root registered in `_mentioned_threads` for future auto-trigger (skipped in strict_mention mode to prevent agent-to-agent ack loops).

### 4.3 Slack AI Assistant API

Hermes registers as a Slack AI Assistant via `features.assistant_view` in the manifest. Implements status indicator + lifecycle events. Does NOT implement `setSuggestedPrompts` or `setTitle`.

**`assistant_thread_started` three-step pipeline:**
1. Extract identity with multi-field fallback chains (Slack's schema changed during API beta).
2. Cache metadata: `(channel_id, thread_ts)` key, cap 5,000, cross-update `_channel_team` map for workspace routing pre-warm.
3. Seed session: pre-create session keyed as `chat_type="dm"` regardless of originating channel context. `context_channel_id` stored as `chat_topic` so agent knows "you're talking from #engineering" without binding to that channel.

Pre-creating the session ensures the first message joins the existing session rather than starting fresh (important because the message event may not carry the same identity bits).

**Status indicator** (`assistant.threads.setStatus`): emitted on turn start (`"Thinking..."`) and cleared on complete. Appears next to bot name in the AI Assistant sidebar.

### 4.4 Session Keying

Session keys are hierarchical strings: `agent:main:slack:{type}:{channel_id}[:{thread_ts}[:{user_id}]]`.

| Context | Key shape | Notes |
|---------|-----------|-------|
| DM, no thread | `agent:main:slack:dm:D01ABC` | |
| DM, in thread | `agent:main:slack:dm:D01ABC:1700000000.123456` | |
| Channel @mention, top-level | `agent:main:slack:group:C01ABC:{ts}:{user_id}` | Per-user isolation by default |
| Channel thread reply | `agent:main:slack:group:C01ABC:{thread_ts}` | Shared session — all thread participants |
| Assistant thread | `agent:main:slack:dm:{channel_id}:{thread_ts}` | Always `dm` type |

**DM top-level threads as sessions** (`dm_top_level_threads_as_sessions=True` default): each top-level DM message uses its own `ts` as a session key anchor, so each reply thread is its own session with its own context.

**`mpim` (group DM)**: all participants share one session keyed by `D...` channel ID. Known gap: no per-user isolation.

**Workspace isolation**: `team_id` is NOT in the session key. Channel IDs are globally unique in practice (random). `team_id` captured in `_channel_team` for outbound routing only.

### 4.5 Slash Commands and Block Kit Interactive Components

**Slash command naming rules:** lowercase a–z, 0–9, `-`, `_`, max 32 chars, no leading digits, no Slack-reserved names (`/shrug`, `/me`, `/remind`, `/msg`, etc.). Auto-generated from command registry names.

**`!cmd` in threads**: normalizes `!stop` → `/stop` as a thread-safe alternative (Slack blocks native slash commands in threads).

**Approval blocks** (`send_exec_approval`): sent when agent wants to execute a privileged command. Three Block Kit buttons: `hermes_approve_once`, `hermes_approve_session`, `hermes_approve_always`. Handler `_handle_approval_action` reads `action_id` and dispatches to `approval.respond` on the gateway.

**`ack()` pattern**: slash commands must `ack()` within 3 seconds. Hermes acks with an ephemeral "Running…" message, then dispatches asynchronously.

### 4.6 File Attachment Handling

**Inbound:**
- Slack Connect file stubs: resolved via `files.info(file_id)` to get the real URL.
- Images: downloaded with bot-token auth, passed to agent as base64 data URL.
- Audio: downloaded, passed as `audio_url` attachment.
- Documents: downloaded, injected as text (≤100KB limit, for `.md/.txt/.csv/.log/.json/.xml/.yaml/.yml/.toml/.ini/.cfg`) or as base64 binary (≤20MB).
- Authenticated download: `Authorization: Bearer {bot_token}` header, follows redirects, raises on non-2xx.

**Outbound:**
- Single file: `files.upload_v2(channel, file=bytes, filename=name, initial_comment=text, thread_ts=?)`.
- Multi-image: chunked into groups of 10 via `CHUNK=10`, each group uploaded as a `file_uploads` batch in one API call.
- Image with SSRF guard: `send_image` validates the URL against `_SLACK_PROXY_HOSTS` before proxying.

### 4.7 mrkdwn Converter

`format_message()` (`slack.py:1177–1287`): Slack mrkdwn is NOT standard Markdown.

**Placeholder-and-restore pattern** using `\x00SL{N}\x00` null-byte markers. Without this: code blocks have their `**` matched as bold; Slack entities `<@U123>` have their `<` HTML-escaped; already-converted bold `*text*` could be re-matched as italic.

**Conversion sequence (13 steps):**
1. Protect fenced code blocks (triple-backtick)
2. Protect inline code
3. Convert `[text](url)` → `<url|text>`
4. Protect existing Slack entities `<@U>`, `<#C>`, `<!here>`
5. Protect blockquote markers `>`
6. HTML-escape `&`, `<`, `>` in remaining plain text (with prior de-escape to normalize)
7. Headers `## Title` → `*Title*` (Slack renders bold)
8. `***text***` → `*_text_*` (bold+italic)
9. `**text**` → `*text*` (bold)
10. Single-asterisk `*text*` → `_text_` (italic) — requires non-whitespace neighbors
11. `~~text~~` → `~text~` (strikethrough)
12. Blockquotes: already protected
13. Restore placeholders in **reverse** insertion order

**Reverse-order restoration is required**: later placeholders may contain content that earlier passes converted — forward restoration would re-expose text that step 6 then escapes.

**Edge cases handled:** markdown links with nested parens (`[label](url_(bar))`), angle-bracket URLs (`[label](<url>)`), image markdown `![alt](url)` bypassed, headers with embedded bold.

### 4.8 Rate Limiting

**`conversations.replies` retry** (Tier 3, ~50 req/min): `_fetch_thread_context` retries on 429 with `retry_after` seconds from the response header.

**File upload retry** (`_is_retryable_upload_error`): retries on network errors and specific Slack error codes (`ratelimited`, `service_unavailable`).

No global retry on `chat.postMessage` — Hermes trusts Slack's Tier 1 limits (very high) and expects the bolt library to handle low-level reconnects.

**`MAX_MESSAGE_LENGTH = 39,000`**: truncation at this limit with `truncate_message()`.

### 4.9 Constants

| Constant | Value |
|----------|-------|
| `MAX_MESSAGE_LENGTH` | 39,000 chars |
| `_BOT_TS_MAX` | 5,000 entries |
| `_MENTIONED_THREADS_MAX` | 5,000 entries |
| `_ASSISTANT_THREADS_MAX` | 5,000 entries |
| `_THREAD_CACHE_TTL` | 60.0 seconds |
| `_SLASH_CTX_TTL` | 120.0 seconds |
| `MAX_DOC_BYTES` | 20 MB |
| `MAX_TEXT_INJECT_BYTES` | 100 KB |
| `MessageDeduplicator.max_size` | 2,000 |
| `MessageDeduplicator.ttl_seconds` | 300 (5 min) |
| `_SLACK_MAX_SLASH_COMMANDS` | 50 |
| Multi-image chunk size | 10 files per upload batch |

---

## → Verso Implications

### A. Provider / Model Abstraction Layer

**Copy: Declarative ProviderProfile dataclass as the single abstraction point.** The transition from `if provider == 'kimi'` branches to a dataclass with 5 polymorphic hooks is the right pattern for Verso's model router. Every provider quirk (temperature control, auth type, extra_body placement, model catalog probe) lives in one file per provider; the transport never imports provider-specific logic. For Verso: define a `ModelProfile` dataclass with exactly these fields: `api_mode`, `auth_type`, `env_vars`, `base_url`, `fixed_temperature`, `default_max_tokens`, `default_aux_model`, and the same 5 hooks.

**Copy: `OMIT_TEMPERATURE = object()` sentinel pattern.** Three-state disambiguation (use default / strip field / override value) is not expressible with `None` alone. Any framework that routes to multiple providers will eventually hit a provider that errors on receiving a field it doesn't support. The sentinel pattern should be Verso's standard for "actively omit this field from the request."

**Copy: Plugin discovery with zero-touch override.** User plugin in `~/.verso/plugins/model-providers/<name>/__init__.py` overrides bundled profile with no repo changes. Last-writer-wins. Failure isolation: broken plugin logs warning, never crashes the agent. For Verso this is the correct extensibility model for model provider configuration.

**Copy: Per-provider `default_aux_model`.** The main model is expensive; side tasks (compression, title generation, vision description for non-vision contexts) use a cheaper model. Bake this into the profile so the framework routes side tasks automatically.

**Copy: Multi-credential pool with per-error-code cooldowns.** 401 → 5-min cooldown (allows recovery); 429 → 1-hour cooldown. Provider-supplied `reset_at` timestamps override defaults. Rotation strategies (fill_first, round_robin, least_used) are all useful for production deployments. The soft-lease semaphore prevents pileup: never blocks, always routes to least-leased available credential.

**Copy: Adapter normalization to common output shape.** All four api_mode adapters return the same `SimpleNamespace(choices=[...], usage=...)` shape. Verso's multi-provider router should output the same internal message structure regardless of upstream provider.

**Avoid: Growing provider quirks in adapters.** Hermes's `anthropic_adapter.py` is 2,273 lines because quirk detection keeps accumulating (8 endpoint-detection helpers, 3 thinking-signature policies, screenshot eviction, orphan stripping). Verso should push ALL provider quirks into the profile dataclass/plugin, keeping the adapter transport thin and generic.

**Verso could improve by:** Exposing `reasoning_content` as a first-class field in Verso's message model from day one. Hermes had to retrofit four fallback sources for `reasoning_content` because streaming providers accumulate it through deltas but never set it on the final message object. Verso should define a standard `AgentMessage` with `reasoning_content: Optional[str]` and teach every adapter to populate it, preventing the retrofit debt.

### B. Tool Execution / Sandbox Layer

**Copy: `BaseEnvironment` with exactly two abstract methods.** Hermes's `_run_bash` + `cleanup` abstract interface is minimal but sufficient. The `ProcessHandle` Protocol (duck-typed) means SDK-only backends work without inheriting from a heavyweight base. Verso's tool execution layer should define the same duck-typed `ProcessHandle` so local subprocesses and cloud sandboxes are interchangeable.

**Copy: `_ThreadedProcessHandle` for SDK-only backends.** The blocking SDK call runs in a daemon thread; output goes through an `os.pipe`; the drain loop sees an indistinguishable `ProcessHandle`. This is the right pattern for any cloud sandbox SDK that doesn't expose a real subprocess handle.

**Copy: Session snapshot for cross-command env persistence.** `export -p > $SNAP` + re-source at command start is how Hermes makes each isolated subprocess invocation see the accumulated env state. Verso's terminal tool should do the same if it needs cross-turn shell state.

**Copy: The `_wrap_command` pattern.** The wrapping script's invariants are production-proven: `>/dev/null` for macOS bash source leak, `builtin cd -- ... || exit 126` for safe cd, `exit $__hermes_ec` to preserve user exit code, CWD marker with leading `\n`. Copy these exactly.

**Copy: Adaptive poll sleep (5ms → ×1.5 → 200ms ceiling).** 195ms savings on fast `echo` commands, same steady-state for long builds. The idle-after-exit counter (3 cycles × 100ms) solves the grandchild pipe-deadlock bug — this is a non-obvious production edge case.

**Copy: Process-group kill sequence (SIGTERM → wait 1s → SIGKILL → wait 2s).** Killing only the process (not the group) leaves zombie background tasks. Verso's local execution backend should implement this sequence.

**Avoid: Building all 8 backends at once.** Verso should start with Local + Docker and add Modal/Vercel/Daytona as they become needed. The key design insight from Hermes: the `BaseEnvironment` interface is stable enough that adding a new backend is ~300 lines without touching existing backends.

**Verso could improve by:** Exposing sandbox backend selection as a first-class part of the agent configuration API rather than an env var. `TERMINAL_ENV` is fine for a CLI tool but a framework should surface this as a typed configuration object.

### C. Gateway / IPC Protocol

**Copy: JSON-RPC 2.0 over newline-delimited JSON as the gateway protocol.** The same frame shape works for stdio (spawn child) and WebSocket (attach to remote). The `method = "event"` convention for server-pushed events reuses the envelope without needing a separate event frame type. The client demultiplexes by `id` (RPC response) vs no-`id`/`method="event"` (server push).

**Copy: `lazy: true` pattern for deferred initialization.** `session.create` returns immediately with `lazy: true` and schedules a 50ms-deferred agent build so the UI can paint before the heavy import. The follow-up `session.info` event carries the full state. Verso's session init should use this pattern to avoid blocking the first render on heavyweight imports.

**Copy: `session.info` as a full-snapshot master state-sync event.** Rather than incremental state updates, emit one event with the complete current state every time anything capability-related changes. This eliminates state-consistency bugs in clients that may have missed intermediate events (e.g. after reconnect).

**Copy: Slash worker subprocess isolation.** Commands that construct their own heavy state (like Verso's equivalent of `/config`, `/model`, `/help`) should run in a subprocess with JSON-line IPC rather than in-process. The three tricks (silent construction via stdout redirect, Rich Console hijack, `_cprint` monkey-patch) are the implementation cost of this isolation.

**Copy: Side-effect mirroring for live-agent mutation.** When the subprocess-isolated command changes something the live agent must know about (model, personality), explicitly mirror those side effects to the live agent after the subprocess returns. Block these mutations mid-turn.

**Copy: Startup crash log discipline.** Write exit reason to a named log file on every abnormal exit. Without it, "gateway exited" is an unactionable error. Verso's gateway process should write `~/.verso/logs/gateway_crash.log` on every abnormal exit.

**Copy: URL redaction before logging.** Bearer tokens in query strings are a common mistake. The `redactUrl()` pattern (WHATWG URL parser + fallback regex for non-standard URLs) should be in Verso's logging utilities from day one.

**Avoid: Growing the method catalog organically.** Hermes's 64 methods evolved incrementally; many overlap (e.g. `session.compress` + `session.save` + `session.close` have overlapping semantics). Verso should define a minimal 15–20 method API upfront and avoid adding convenience methods until there's a proven need.

**Verso could improve by:** Making the gateway protocol transport-agnostic from the start. Hermes added WS support after stdio; the architecture accommodated it well but required adding `WSTransport` and `TeeTransport`. Verso should define the `Transport` protocol interface upfront with both stdio and WS implementations, so switching or adding transports has no API surface changes.

### D. Slack / Chat Surface

**Copy: Socket Mode over HTTP Events API for internal deployments.** Socket Mode requires no public ingress, works behind firewalls, and removes the request-signing complexity. The tradeoff (persistent WebSocket, reconnect handling) is managed entirely by `slack-bolt`.

**Copy: Zombie handler guard.** On reconnect, close the previous `AsyncSocketModeHandler` before creating a new one. Otherwise duplicate event dispatch occurs (each event fires twice).

**Copy: Layered message routing with early-return guards.** Hermes's 5-gate routing (allowlist → free-response → strict-mention → mention/thread/session check) is the right architecture. Each guard returns early so later guards never run on dropped messages. Verso's chat adapter should structure inbound dispatch the same way.

**Copy: Thread memory as bounded sets.** `_bot_message_ts` (cap 5,000) + `_mentioned_threads` (cap 5,000) for implicit thread continuation. The session store provides explicit persistence across restarts. Eviction: drop oldest 2,500 when cap exceeded (CPython set insertion-order as implementation detail — DESIGNED replicators should use `OrderedDict`).

**Copy: Pre-seeding assistant sessions on `assistant_thread_started`.** Create the session before the first message arrives so identity fields are stable. The message event may not carry the same identity bits the lifecycle event did.

**Copy: mrkdwn converter's placeholder-and-restore discipline.** Whenever building a multi-pass text converter, protect already-converted regions with null-byte markers before running later passes. Reverse-order restoration. This pattern generalizes beyond Slack to any multi-pass text transformation pipeline.

**Copy: Session key hierarchy.** `platform:agent:type:channel_id[:thread_ts[:user_id]]`. Thread vs DM vs channel have different sharing semantics. Thread replies default to shared sessions (collaborative UX). Top-level channel messages default to per-user sessions. These defaults should be configurable per Verso deployment.

**Avoid: Duplicating config in two places.** Hermes has both `slack:` YAML keys and `platforms.slack.extra:` config — they shadow each other and both need to be maintained. Verso should have one config path per platform, using env vars only as overrides.

**Verso could improve by:** Implementing `setSuggestedPrompts` and `setTitle` on the Slack AI Assistant API. Hermes leaves these unimplemented. A framework shipping in 2026 should treat these as table stakes for the Assistant surface — they significantly improve first-run UX.

**Verso could improve by:** Keeping `team_id` in the session key for multi-workspace deployments. Hermes relies on channel ID global uniqueness, which is practically safe but theoretically a collision risk for very large cross-workspace deployments. A framework targeting enterprise should include `team_id` as a prefix.
