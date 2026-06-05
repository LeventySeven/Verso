# Tools + MCP Adapter — Verso Design Resolution

**Subsystem:** `tools/` + `tools/adapters/mcp.py`
**PRD refs:** §5.3, §10 item 7
**Teardown source:** `03_teardowns/infra-tools-mcp.md` (fastmcp e1b52d0, MCP spec 2025-11-25,
  Klavis Strata `open-strata/`, arcadepy 1.10.0 + arcade-tdk 3.8.0, Nango, Pipedream Connect,
  Toolhouse 1.4.0, Smithery CLI, Apify MCP Server, mcp-use)
**Date:** 2026-06-05

---

## Decisions Resolved

### Decision 1 — `@tool` → JSON-Schema Contract

**Choice:** Port fastmcp's `ParsedFunction`/`get_cached_typeadapter` pipeline verbatim as the
single schema-generation path. `pydantic.TypeAdapter(fn).json_schema()` applied to the processed
function object is the whole contract; the load-bearing 5% is six ordered transforms Verso must
replicate exactly.

**Rationale:** Every framework in the survey (fastmcp Python, Nango/Apify/Smithery TypeScript via
Zod) converges on the same approach: let the type system do the work, then apply a small set of
protocol-correctness transforms. The transforms are non-obvious but fully specced by fastmcp source.

**Evidence:** `fastmcp/tools/function_parsing.py:130-314` + `utilities/types.py:45-120` +
`utilities/json_schema.py:645-685`. Six concrete steps:

1. **Reject variadics** (`:141-147`): `*args`/`**kwargs` raise `ValueError` — a schema must
   enumerate every parameter.
2. **Resolve forward refs + rewrite `Annotated[T,"str"]`→`Field(description=)`** (`:67-76`): bare
   string annotations become schema `description` fields; `get_type_hints(include_extras=True)`.
3. **Strip DI params before schema-gen** (`:186-195`): `ctx: Context` / `Depends()` params are
   removed from the wrapper function before `TypeAdapter` sees it — they never appear in the LLM-
   visible schema.
4. **Compress** (`json_schema.py:645-685`): one tree walk — resolve root `$ref` to `type:"object"`
   (MCP requires object root), prune `title` fields (Gemini 2.5 Flash rejects bare-title nodes with
   `MALFORMED_FUNCTION_CALL`), prune unused `$defs` via reachability graph. Depth cap = 50 (prevent
   infinite recursion on self-referential schemas).
5. **Keep `additionalProperties:false`** (`:658-660`): explicitly NOT stripped — Claude strict mode
   requires it.
6. **Object-wrap scalar returns** (`function_tool.py:292-297`): when return type is non-object,
   emit `{"result": value}` + flag `x-verso-wrap-result: true`.

**Alternatives rejected:**
- Hand-written Pydantic `BaseModel` per tool: verbose, loses the "native `@tool` feels like a plain
  Python function" promise.
- `inspect`-only schema (no Pydantic): can't handle complex nested types, Optional, Union, Literal.
- TypeAdapter at decoration time (not registration): expensive `TypeAdapter` construction per
  decorator call; fastmcp benchmarks this as measurably slow on server start.

---

### Decision 2 — `@tool` Metadata Attachment Model (lazy vs eager)

**Choice:** `@tool` attaches a cheap frozen `ToolMeta` dataclass to `fn.__verso__` and returns the
**original function unchanged**. Schema generation is deferred to `ToolRegistry.add(fn)`. The
decorator is zero-cost at import time.

**Rationale:** fastmcp's `ToolMeta` (`function_tool.py:68-90`, `:504-524`) proves this is safe and
desirable: `TypeAdapter` construction is expensive; deferring it to registration means you pay it
once per server start rather than once per module import, and the original function remains callable
without framework interference.

**Evidence:** `fastmcp/tools/function_tool.py:504-524` — `@tool` default mode attaches
`fn.__fastmcp__ = ToolMeta(...)` and `return fn`. Schema built only in `FunctionTool.from_function`
at registration.

**`ToolMeta` fields Verso adopts (subset, with additions):**
```python
@dataclass(frozen=True)
class ToolMeta:
    name: str | None = None              # override; default = fn.__name__
    description: str | None = None       # override; default = docstring
    read_only: bool = False              # → permission routing (allow auto-parallel)
    destructive: bool = True             # → no blind auto-retry; require approval gate
    idempotent: bool = False             # → safe to retry on transient failure
    timeout: float | None = None        # per-tool hard cap (anyio.fail_after)
    max_result_chars: int | None = None  # truncate result before returning to loop
    requires_auth: ToolAuthorization | None = None  # → auth-interrupt path pre-empt
    on_error: ErrorPolicy | None = None  # → error-category routing (Decision 5)
    run_in_thread: bool = True           # sync fns → threadpool (don't block event loop)
    tags: frozenset[str] = field(default_factory=frozenset)  # bundle/scope selector
    version: str = "1.0.0"
```

**Alternatives rejected:**
- Eager schema at decoration: import-time cost, DI params not yet stripped (no RunContext
  available), makes testing harder (decorated fns become non-plain).
- Single `@tool(...)` class that replaces the function: breaks `isinstance(fn, Callable)` checks
  and makes mocking harder.

---

### Decision 3 — Tool Error Contract: `{data, error, ok}` Envelope + Categorized `ToolError`

**Choice:** Every tool dispatch returns `ToolResult(data, error, ok)`. Tool functions may `raise`
freely; the executor wraps all exceptions. The `error` field is a structured `ToolError` with an
Arcade-derived `kind` enum, `can_retry` bit, `retry_after_ms` hint, and `prompt_content` for model
self-correction.

**Rationale:** PRD §5.3 locks the `{data,error,ok}` envelope (sourced from Hermes/Composio). The
open question was the *structure* of `error`. Arcade's `OutputError` (`arcadepy/types/
execute_tool_response.py`) is the most complete categorized model in the survey — three tiers,
machine-readable retryability, and a purpose-built `additional_prompt_content` field. It directly
fills fastmcp's open `@tool(on_error=…)` gap (issue #2882 cited in teardown). MCP spec SEP-1303
resolves the `isError` placement: argument-validation failures are **application-tier** (`isError:
true`, model reads and fixes), not `INVALID_PARAMS` protocol errors.

**Evidence:**
- `arcadepy/types/execute_tool_response.py` — `OutputError{can_retry, kind, additional_prompt_content, retry_after_ms}`.
- `arcadepy/types/shared/authorization_response.py` — `{id, status, url}` interrupt triple.
- MCP spec `schema.ts:1106-1132` + SEP-1303 — `isError:true` with `content[]` for arg-validation.
- fastmcp `server.py:1300-1308` — 429/timeout escape hatch (Verso formalizes this into the `kind` enum).

**`ToolError` schema:**
```python
from typing import Literal, Optional
from dataclasses import dataclass

ErrorKind = Literal[
    # tool-definition tier (schema/setup bugs — NOT retryable)
    "TOOL_BAD_DEFINITION", "TOOL_BAD_INPUT_SCHEMA", "TOOL_BAD_OUTPUT_SCHEMA",
    # tool-runtime tier
    "TOOL_BAD_INPUT_VALUE",      # validation failure → model self-corrects (isError:true)
    "TOOL_TIMEOUT",              # per-tool deadline exceeded → can_retry=True
    "TOOL_REQUIREMENTS_NOT_MET", # auth/secrets missing → route to auth-interrupt
    "TOOL_RUNTIME_FATAL",        # unrecoverable exception
    "TOOL_RUNTIME_RETRY",        # transient, retryable
    # upstream tier
    "UPSTREAM_RATE_LIMIT",       # 429 → can_retry=True, retry_after_ms populated
    "UPSTREAM_AUTH_ERROR",       # 401/403 → route to auth-interrupt
    "UPSTREAM_NOT_FOUND",        # 404 → can_retry=False
    "UPSTREAM_VALIDATION_ERROR", # bad request to upstream API → model self-corrects
    "UPSTREAM_SERVER_ERROR",     # 5xx → can_retry=True
    "UPSTREAM_TIMEOUT",          # upstream timeout → can_retry=True
    "UNKNOWN",
]

@dataclass
class ToolError:
    kind: ErrorKind
    can_retry: bool
    message: str                         # human-readable (masked in prod, see Decision 4)
    prompt_content: str | None = None    # injected into model context for self-correction
    retry_after_ms: int | None = None    # backoff hint (populated for RATE_LIMIT)
    developer_message: str | None = None # full traceback / details, never sent to model

@dataclass
class ToolResult:
    ok: bool
    data: object | None = None           # tool return value (None on error)
    error: ToolError | None = None       # None on success
```

**Routing rules (executor reads `error.kind`):**
| kind | executor action |
|---|---|
| `TOOL_BAD_INPUT_VALUE`, `UPSTREAM_VALIDATION_ERROR` | isError:true → model sees `prompt_content`, self-corrects |
| `TOOL_BAD_DEFINITION`, `TOOL_BAD_INPUT_SCHEMA` | raise into loop as `ToolDefinitionError` — stop run |
| `TOOL_TIMEOUT`, `TOOL_RUNTIME_RETRY`, `UPSTREAM_SERVER_ERROR`, `UPSTREAM_TIMEOUT` | retry (max_attempts from ToolMeta, exp backoff + jitter) |
| `UPSTREAM_RATE_LIMIT` | retry with `retry_after_ms` |
| `TOOL_REQUIREMENTS_NOT_MET`, `UPSTREAM_AUTH_ERROR` | route to auth-interrupt (Decision 6) |
| `TOOL_RUNTIME_FATAL`, `UPSTREAM_NOT_FOUND` | return error as content (isError:true), no retry |

**Alternatives rejected:**
- Raise exceptions from dispatch into the loop: violates PRD §5.3 contract; the loop must never
  handle raw exceptions.
- Flat `{ok, data, error_message: str}`: loses the routing bit — the executor can't decide whether
  to retry without `can_retry` and `kind`.
- Re-raise `PydanticValidationError` as `INVALID_PARAMS` (fastmcp current behavior): violates MCP
  SEP-1303; prevents model self-correction.

---

### Decision 4 — Error Masking Default

**Choice:** `mask_error_details=True` by default. The `message` field in `ToolError` is replaced
with `"Error calling tool {name!r}"` in production; `developer_message` carries the full trace and
is **never** injected into model context. Two categories bypass masking because the model must act:
`UPSTREAM_RATE_LIMIT` → `"Rate limited, please retry later"` and `TOOL_TIMEOUT` → `"Tool timed out,
please retry"`. `prompt_content`, when set, is always surfaced (it is purpose-built for the model).

**Rationale:** fastmcp `server.py:358-362` + `1300-1308` prove the escape hatch is necessary and
that the hand-coded 429/timeout cases cover the most common retryable categories. Masking prevents
internal details from leaking to adversarial prompts via the LLM's tool output channel.

**Evidence:** fastmcp `server.py:358-362` (`mask_error_details` setting), `1300-1308` (429 +
timeout bypass).

**Alternatives rejected:**
- `mask_error_details=False` default (expose full tracebacks): leaks internal state; a real
  security issue for multi-tenant deployments.
- No masking at all: same problem.

---

### Decision 5 — `isError: true` vs JSON-RPC Error Placement (MCP spec compliance)

**Choice:** Follow MCP spec 2025-11-25 + SEP-1303 exactly.

**Application-tier failures (tool ran, failed logically including bad arguments):** return
`CallToolResult{isError:True, content:[TextContent(text=prompt_content)]}` — HTTP 200, valid JSON-
RPC *result*. The model sees it, reads `prompt_content`, and self-corrects.

**Protocol-tier failures (tool not found, tools unsupported, malformed request, auth-missing):**
return `JSONRPCErrorResponse{error:{code, message}}` using standard codes: `METHOD_NOT_FOUND=
-32601`, `INVALID_PARAMS=-32602`, `INTERNAL_ERROR=-32603`; implementation-specific range
`[-32000, -32099]` (e.g. `AUTH_MISSING=-32001`). Auth-missing at the MCP edge is protocol-tier
(`-32001`), confirmed by Pipedream live probe.

**Transport-tier failures (connection failure):** abort + retry-connection; never reaches the LLM.

**Rationale:** The spec text is unambiguous (`schema.ts:1106-1132`): "Any errors that originate
from the tool SHOULD be reported inside the result object, with `isError` set to true, NOT as an
MCP protocol-level error response. Otherwise the LLM would not be able to see that an error
occurred and self-correct." SEP-1303 clarifies that argument-validation specifically should be
application-tier. Pipedream's live probe (`-32001` for missing JWT) confirms protocol-tier for
auth-missing.

**Evidence:**
- MCP `schema.ts:1106-1132` — explicit spec text.
- MCP SEP-1303 — argument validation = application tier.
- Pipedream live probe 2026-06-05 — `HTTP 401 {"error":{"code":-32001,"message":"Unauthorized…"}}`.

**Alternatives rejected:**
- `INVALID_PARAMS` for bad arguments (fastmcp current behavior): spec-violating post SEP-1303;
  prevents model self-correction on argument mistakes.
- `isError:true` for tool-not-found: wrong direction — the LLM cannot act on a missing tool by
  reading an error message; it needs the framework to fail the call.

---

### Decision 6 — HITL for Auth: Arcade Interrupt Model

**Choice:** When a tool's `requires_auth` is set and consent is needed, the executor returns an
`AuthInterrupt` value (NOT raises an exception) embedded in the `ToolResult`. The loop inspects it,
surfaces `url` to the user (HITL pause via `ctx.hitl.request`), long-polls on `auth_id` in 45-
second windows (Arcade's constant), and re-executes the tool on `completed`. The checkpoint
serializes `{auth_id, tool_name, input}` so the interrupt is resumable across process restarts.

**Rationale:** Three converging designs (Arcade `output.authorization`, MCP `-32042`, Strata
`handle_auth_failure`) all produce the same shape: a `(auth_id, consent_url, status)` triple.
Arcade's is the most production-field-tested (from the SDK source, not just the spec). The key
design insight: the interrupt is a *value* in the result, not an exception — this keeps the loop
code clean (one `if` branch, not a try/except around every tool call) and makes it checkpointable
without special-casing.

**Evidence:**
- `arcadepy/types/execute_tool_response.py` — `Output.authorization: Optional[AuthorizationResponse]`.
- `arcadepy/resources/auth.py:24` — `_DEFAULT_LONGPOLL_WAIT_TIME = 45`.
- `arcadepy/resources/auth.py:209-234` — `wait_for_completion` polling loop.
- MCP `schema.ts:181-201` — `URL_ELICITATION_REQUIRED = -32042` (spec-native wire form).
- Strata `tools.py:322-360` — `handle_auth_failure` meta-tool (same shape, agent-native form).

**`AuthInterrupt` schema:**
```python
@dataclass
class AuthInterrupt:
    auth_id: str           # poll token for status checks
    url: str               # OAuth consent URL to surface to user
    status: Literal["not_started", "pending", "completed", "failed"]
    provider_id: str       # e.g. "github", "google"
    scopes: list[str]      # what was requested
    user_id: str           # the end-user this auth is for

# Embedded in ToolResult when auth is needed:
# ToolResult(ok=False, data=None,
#   error=ToolError(kind="TOOL_REQUIREMENTS_NOT_MET", can_retry=True, ...),
#   auth_interrupt=AuthInterrupt(...))
```

**Auth-interrupt loop (Verso executor):**
```python
async def _call_with_auth(tool, user_id, inp, ctx):
    result = await _call_tool(tool, inp, ctx)
    interrupt = result.auth_interrupt
    if interrupt and interrupt.status != "completed":
        # HITL: surface the consent URL
        await ctx.hitl.request(f"Auth required: {interrupt.url}")
        checkpoint = {"auth_id": interrupt.auth_id,
                      "tool": tool.name, "input": inp}  # resumable token
        ctx.checkpoint(checkpoint)
        # long-poll in 45s windows (Arcade constant)
        while interrupt.status != "completed":
            interrupt = await _poll_auth(interrupt.auth_id, wait_secs=45)
            if interrupt.status == "failed":
                return ToolResult(ok=False,
                    error=ToolError("UPSTREAM_AUTH_ERROR", can_retry=False,
                        prompt_content="Authorization failed. User declined or timeout."))
        result = await _call_tool(tool, inp, ctx)  # re-execute after consent
    return result
```

**MCP wire form (for Verso's MCP server edge):** emit `JSON-RPC error{code:-32042,
data:{elicitations:[{url, message}]}}` when an incoming `tools/call` requires auth the caller
hasn't yet provided. The executor receives `-32042` from an upstream MCP server and routes to the
same interrupt path.

**Alternatives rejected:**
- Raising an `AuthRequired` exception: breaks the `{data,error,ok}` contract; requires special
  try/except in the loop.
- Separate `authorize()` pre-flight call before every tool call: adds a round-trip for tools that
  don't need auth; Arcade's model (discover auth-needed *in the execute response*) is lazier and
  correct.
- Busy-polling: Arcade's 45s server-side long-poll means the client loop sleeps inside the HTTP
  call, not in a tight spin. Verso must respect the long-poll window, not poll every second.

---

### Decision 7 — Deferred/Meta-Tool Loading: Strata 4-Stage as Default for Large Sources

**Choice:** For any tool source with >20 tools (configurable threshold `DEFERRED_LOADING_THRESHOLD =
20`), Verso's `ToolSourceAdapter` exposes **five fixed meta-tools** instead of all N schemas. The
eager context injection is only the *namespace list* (server/bundle names). All action
names/schemas enter context lazily via the 4-stage Strata protocol.

**Rationale:** Five systems independently arrive at "don't inject N schemas." Strata's 4-stage is
the most granular (action-granular, not server-granular like mcp-use), keyless (BM25, no embedding
model needed), and open-source with readable source. Its measured benefit (≈15% tool accuracy,
60-80% context reduction — INFERRED from Klavis marketing, usable as calibration target) is in the
right direction; the mechanism is KNOWN. The opaque-execute-params trick (Strata + Apify) keeps the
meta-tool schemas permanently fixed regardless of catalog size.

**Evidence:**
- Strata `tools.py:14-145` — 5 meta-tool definitions.
- Strata `tools.py:155-375` — 4-stage dispatch implementation.
- Strata `utils/shared_search.py:47-151` + `utils/bm25_search.py` — field-weighted BM25+.
- Apify `tools/core/call_actor_common.ts:231-256` — `input: z.object({}).passthrough()` opaque pattern.
- Apify `mcp/server.ts:323-338` — mode switch on `tools.listChanged` capability.
- Pipedream `mcp-chat/lib/pd-backend-client.ts` — path-param scoping as connection-time coarse filter.
- Toolhouse `sdk.py:161-170` — `bundle` string as coarse curated-subset selector.

**The five meta-tools Verso exposes for large sources:**
```python
@tool(name="discover_tools", description=(
    "PREFERRED STARTING POINT. Discover available tools in one or more namespaces "
    "matching a natural-language query. Returns action NAMES only — no schemas. "
    "Call get_tool_details for the schema of one specific action before executing it."))
async def discover_tools(
    query: Annotated[str, "What you want to do, in natural language"],
    namespaces: Annotated[list[str], "Which namespaces to search (enum from registry)"],
    ctx: RunContext,
) -> dict:
    # returns {"servers": {ns: {"action_count": N, "actions": [...names...]}}}

@tool(name="get_tool_details", description=(
    "Get the full input schema for exactly one action before calling execute_tool."))
async def get_tool_details(
    namespace: Annotated[str, "The namespace (server name)"],
    action: Annotated[str, "The action name, from discover_tools"],
    ctx: RunContext,
) -> dict:
    # returns {"server": ns, "action": {"name":…, "description":…, "inputSchema":{…}}}

@tool(name="execute_tool", description=(
    "Execute an action. Call get_tool_details first to learn the input schema. "
    "Pass all parameters as a single JSON-encoded string in 'params'."),
    destructive=True, idempotent=False)
async def execute_tool(
    namespace: Annotated[str, "Namespace (server name)"],
    action: Annotated[str, "Action name"],
    params: Annotated[str, "JSON string with all parameters. Use '{}' if none."] = "{}",
    ctx: RunContext,
) -> list:  # MCP ContentBlock list (passthrough)

@tool(name="search_tool_docs", description=(
    "BM25 keyword search within a namespace for tools matching a term."))
async def search_tool_docs(
    query: Annotated[str, "Search term"],
    namespace: Annotated[str, "Namespace to search in"],
    max_results: Annotated[int, "Max results (1–50)"] = 10,
    ctx: RunContext,
) -> list:  # [{name, description, tags}]

@tool(name="handle_auth", description=(
    "When execute_tool returns an auth error: get the auth URL or save auth data."))
async def handle_auth(
    namespace: Annotated[str, "Namespace that returned an auth error"],
    intention: Annotated[Literal["get_auth_url", "save_auth_data"], "What to do"],
    auth_data: Annotated[str | None, "Completed auth token (for save_auth_data)"] = None,
    ctx: RunContext,
) -> dict:
```

**Degradation for clients without `tools.listChanged`:** fall back to a single `run_tool(namespace,
action, params)` meta-tool (Apify's `call-actor` pattern). Verso resolves the mode from the MCP
client's `initialize` capabilities.

**Namespace list injection (the only eager context):** at agent start, inject a compact namespace
manifest — `{"namespaces": ["github", "slack", "linear"], "total_tools": 312}`. No schemas, no
action names. Everything else is lazy.

**Alternatives rejected:**
- Inject all N tool schemas up front: directly causes the context-flooding anti-pattern PRD §5.3
  calls out (77K→8.7K token gap from Claude Code teardown).
- mcp-use's stateful `active_server`: forces the agent to serially connect/disconnect; blocks multi-
  namespace single-step reasoning.
- Embedding-based discover (mcp-use bge-small): requires an embedding model dependency; keyless
  BM25 is sufficient for structured tool metadata and is faster. Offer as an opt-in `EmbeddingRanker`
  plugin.

---

### Decision 8 — BM25+ Field-Weighted Ranker (keyless default)

**Choice:** Verso's `discover_tools` meta-tool ranks candidate actions with field-weighted BM25+
using the `bm25s` library (`method="bm25+"`), English stemmer, **stopwords disabled**. Field weights:
name/description/title/tags = 30, parameter names + descriptions = 15, response field names = 5.
Tokenization: `_`→space, `-`→space, camelCase split (so `create_project` and `getUserProjects`
both tokenize into word units). Top-k default = 50 at discover, 10 at search_docs.

**Rationale:** Strata's source proves this simple ranker is sufficient for structured tool metadata
(action names, descriptions, param names are well-structured text where exact-ish match matters
more than semantic approximation). Keyless = zero infra cost. The weighting is calibrated: a query
term hitting the tool *name* or *description* (×30) should dominate one hitting a response-field
name (×5).

**Evidence:** Strata `utils/shared_search.py:47-151` — exact field-weights dict; `utils/
bm25_search.py` — `method="bm25+"`, `Stemmer`, `stopwords=[]`.

**Alternatives rejected:**
- Pure substring/fuzzy match (Smithery): less discriminating for 100+ tool catalogs.
- Embedding cosine similarity (mcp-use bge-small+cosine): correct approach for semantic queries,
  but adds a non-trivial model dependency. Offer as opt-in `EmbeddingToolRanker(model="BAAI/bge-
  small-en-v1.5")`.
- OpenAI embeddings for ranking: adds API call to the discover path, breaks keyless operation.

---

### Decision 9 — MCP Adapter Conformance (spec 2025-11-25)

**Choice:** Verso's MCP adapter layer (`tools/adapters/mcp.py`) is a full 2025-11-25 client and
server. Specific conformance points:

**As MCP client (consuming upstream servers):**
- Page `tools/list` via `cursor`/`nextCursor` — never bulk-load (spec `schema.ts:629-648`).
- Cache component metadata with `_DEFAULT_CACHE_TTL = 300` seconds, monotonic clock, `ttl=0`
  to disable (fastmcp `proxy.py:566`). Cache raw metadata; apply per-session auth filtering after
  lookup.
- Lazy-connect on first `initialize` via a middleware hook; upstream connection is dormant at start
  (fastmcp `proxy.py:79-114`).
- Handle `MCP-Session-Id` 404 → discard session + re-initialize; reconnect SSE via GET +
  `Last-Event-ID` (spec `transports.mdx:207-219`).
- Carry `MCP-Protocol-Version: 2025-11-25` on every post-init HTTP request.
- Be a Protected-Resource-Metadata client: discover auth servers from `WWW-Authenticate` header or
  `.well-known/oauth-protected-resource`, send RFC 8707 `resource` parameter on token requests
  (audience-binding), support incremental `WWW-Authenticate` scope upgrades.
- Forward the caller's `Authorization` header to upstream; don't store credentials in the proxy
  (fastmcp `proxy.py:1117-1124`, `transport.forward_incoming_headers = True`).
- Treat `METHOD_NOT_FOUND` on `tools/list` as empty list, not an error (fastmcp `proxy.py:647-651`).

**As MCP server (exposing Verso tools to MCP clients):**
- Emit `tools/listChanged` notification when the registry changes (Apify `add_actor.ts:64`).
- Support paginated `tools/list` with opaque cursor (even if Verso's own tool count is small — the
  protocol must be correct for any aggregated source).
- Implement `ToolAnnotations` from `ToolMeta`: `readOnlyHint = read_only`, `destructiveHint =
  destructive`, `idempotentHint = idempotent`, `openWorldHint = True` for meta-tools.
- Emit `execution.taskSupport` per tool: `"optional"` for any tool with `timeout > 30s` or marked
  long-running; `"forbidden"` otherwise.
- Session lifecycle: assign a cryptographically random `MCP-Session-Id`; return `404` on expired
  sessions; accept `HTTP DELETE` for client-initiated termination.

**Long-running tools (task-augmented execution):** tools with `execution.taskSupport:"optional"`
return `CreateTaskResult{taskId, status:"working", pollInterval:5000}` on the initial call. The
loop polls `tasks/get` at `pollInterval` until terminal, then `tasks/result`. The `input_required`
task status routes to the elicitation seam.

**`ToolAnnotations` trust rule:** treat annotations from untrusted servers as hints only — never
use them for security decisions (spec note, `schema.ts:1182`).

**Evidence:**
- MCP `schema.ts:629-648` — paginated `tools/list`.
- MCP `schema.ts:1251-1298` — `Tool` shape with `execution.taskSupport`.
- MCP `transports.mdx:198-219` — session lifecycle.
- MCP `basic/utilities/tasks.mdx` — task-augmented execution.
- fastmcp `proxy.py:566` — `_DEFAULT_CACHE_TTL = 300.0`.
- fastmcp `proxy.py:79-114` — `ProxyInitializeMiddleware`.
- fastmcp `proxy.py:1117-1124` — header forwarding.

**Alternatives rejected:**
- Old HTTP+SSE dual-endpoint: deprecated in 2025-11-25; do not implement.
- Trusting `ToolAnnotations` for permission routing: spec explicitly says don't from untrusted
  servers.

---

### Decision 10 — Multi-Server Namespacing + Collision Policy

**Choice:** Every MCP source gets a namespace prefix. Tool names in Verso are always `namespace:
action` (internal) and `namespace_action` (MCP wire form, fastmcp convention). No two sources
share a flat namespace. Collision policy: `"warn"` default (log + first-registered wins, highest-
version semantics); `"raise"` available as strict mode.

**Per-request end-user scoping:** carry a `user_id` header (`x-verso-user-id`, analogous to
Pipedream's `x-pd-external-user-id`) on every tool-source adapter call. The developer authenticates
once; per-user credentials are resolved server-side from the `user_id`. Connection-URL-level app
scoping: a namespace can be pinned to a specific sub-app (`github`, `slack`) at connection time,
reducing the tool catalog before any runtime filtering.

**Evidence:**
- fastmcp `aggregate.py:90-137` — `with_namespace`, `provider_error_strategy="warn"`.
- Pipedream `pd-backend-client.ts:11-22` — `x-pd-external-user-id` header + path-param scoping.
- mcp-use `langchain_adapter.py:138-139` — flat namespace (identified as a gap, not a pattern to copy).
- Arcade `tool.py` — `Gmail.ListEmails` dot-notation (alternative namespacing; Verso uses `:`/`_`
  to stay MCP-wire-compatible).

**Alternatives rejected:**
- Flat namespace (mcp-use): name collisions across servers are a real bug at scale.
- Per-user separate MCP servers (Nango per-connection model): correct for multi-tenant SaaS; overkill
  for Verso's single-developer dogfood phase. Adopt Nango's per-connection scoping in Phase 3
  multi-tenant.

---

### Decision 11 — Tool Source Registry + `ToolSourceAdapter` Interface

**Choice:** A `ToolSourceAdapter` is a protocol (duck-typed) with two required methods:
`tools_for(scope)` and `run(tool_name, arguments, ctx)`. This is the `get_tools`/`run_tools`
abstraction from Toolhouse, generalized. The registry maps `namespace → ToolSourceAdapter`. Three
concrete adapters ship:
- `NativeAdapter` (default): `@tool`-registered functions.
- `MCPAdapter`: wraps a remote MCP server (fastmcp `ProxyProvider`-equivalent).
- `OpenAPIAdapter`: imports an OpenAPI spec as tools (Phase 3).

Local (`@tool`) tools take precedence over same-name remote tools (Toolhouse's local-precedence rule).
Schema source and execution location are independent axes (Nango's insight): a tool's schema can be
pulled from the registry at `tools_for()` time while execution is delegated to a remote server.

**Evidence:**
- Toolhouse `sdk.py:161-233` — `get_tools(bundle)` + `run_tools(response)` two-method contract.
- Toolhouse `services/local_tools.py:24-38` — local-precedence dispatch.
- Nango `mcp/server.ts:66-90` — schema compiled at deploy, re-derived from stored artifact at MCP call.

---

## Component Spec

### `ToolMeta` (attached to `fn.__verso__` by `@tool`)

```python
# verso/tools/meta.py
from dataclasses import dataclass, field
from typing import Optional, Literal, TYPE_CHECKING
if TYPE_CHECKING:
    from .auth import ToolAuthorization

@dataclass(frozen=True)
class ToolMeta:
    name: Optional[str] = None           # None → fn.__name__
    description: Optional[str] = None    # None → docstring first paragraph
    read_only: bool = False
    destructive: bool = True
    idempotent: bool = False
    open_world: bool = False             # MCP openWorldHint
    timeout: Optional[float] = None     # seconds; None = no cap
    max_result_chars: Optional[int] = None
    requires_auth: Optional["ToolAuthorization"] = None
    run_in_thread: bool = True           # sync fn → threadpool
    tags: frozenset = field(default_factory=frozenset)
    version: str = "1.0.0"
    # Note: on_error routing is derived from ErrorKind + can_retry; not a separate field
```

### `@tool` Decorator Signature

```python
# verso/tools/decorator.py
def tool(
    fn=None, *,
    name: str | None = None,
    description: str | None = None,
    read_only: bool = False,
    destructive: bool = True,
    idempotent: bool = False,
    open_world: bool = False,
    timeout: float | None = None,
    max_result_chars: int | None = None,
    requires_auth: "ToolAuthorization | None" = None,
    run_in_thread: bool = True,
    tags: frozenset | set | None = None,
    version: str = "1.0.0",
) -> Callable:
    """Attach ToolMeta to fn.__verso__; return fn unchanged. Schema deferred to registration."""
    def _attach(f):
        object.__setattr__(f, "__verso__", ToolMeta(
            name=name, description=description, read_only=read_only,
            destructive=destructive, idempotent=idempotent, open_world=open_world,
            timeout=timeout, max_result_chars=max_result_chars,
            requires_auth=requires_auth, run_in_thread=run_in_thread,
            tags=frozenset(tags or ()), version=version,
        ))
        return f
    return _attach(fn) if fn is not None else _attach
```

### `ToolRegistry` (schema build at registration)

```python
# verso/tools/registry.py
from pydantic import TypeAdapter
from typing import Callable

DEFERRED_LOADING_THRESHOLD = 20  # tools from a single source above this → meta-tool mode

class RegisteredTool:
    fn: Callable
    meta: ToolMeta
    schema: dict          # built at registration via build_tool_schema(fn)
    namespace: str        # default "local"

class ToolRegistry:
    """Central registry; namespace:action keys; local-first dispatch."""

    def add(self, fn: Callable, namespace: str = "local") -> RegisteredTool:
        """Build schema (TypeAdapter, compress, inject docstring), store."""

    def get(self, name: str) -> RegisteredTool | None:
        """Lookup by namespace:action or local action name (local-first)."""

    def tools_for_llm(self, namespaces: list[str] | None = None) -> list[dict]:
        """Return MCP-shaped tool dicts for the LLM call. Respects deferred threshold."""

    def namespace_manifest(self) -> dict:
        """{'namespaces': [...], 'total_tools': N} — the only eager injection for large sources."""
```

### `build_tool_schema(fn)` — six-step pipeline

```python
# verso/tools/schema.py
import inspect
from pydantic import TypeAdapter, Field
from typing import Annotated, get_origin, get_args, get_type_hints
from functools import lru_cache

SCHEMA_CACHE: dict = {}  # keyed by id(fn); cleared on GC

def build_tool_schema(fn: Callable) -> dict:
    """Full fastmcp-equivalent pipeline. Call once at registration."""
    # Step 1: reject variadics
    sig = inspect.signature(fn)
    for p in sig.parameters.values():
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            raise ValueError(f"@tool '{fn.__name__}' cannot take *args/**kwargs")

    # Step 2: resolve forward refs + rewrite Annotated[T,"str"] → Field(description=)
    hints = get_type_hints(fn, include_extras=True)
    processed = {}
    for param_name, ann in hints.items():
        if get_origin(ann) is Annotated:
            args = get_args(ann)
            if len(args) == 2 and isinstance(args[1], str):
                processed[param_name] = Annotated[args[0], Field(description=args[1])]
            else:
                processed[param_name] = ann
        else:
            processed[param_name] = ann

    # Step 3: strip DI params (ctx: RunContext, ctx: Context, Depends(...))
    wrapper = _strip_di_params(fn, processed)

    # Step 4: TypeAdapter → raw schema (cached by fn id)
    cache_key = id(wrapper)
    if cache_key not in SCHEMA_CACHE:
        SCHEMA_CACHE[cache_key] = TypeAdapter(wrapper).json_schema()
    raw = SCHEMA_CACHE[cache_key].copy()

    # Step 5: compress (root $ref → type:object; prune titles; prune dead $defs;
    #          KEEP additionalProperties:false; depth cap 50)
    compressed = _compress_schema(raw)

    # Step 6: inject docstring param descriptions (explicit Field/Annotated wins)
    _inject_docstring_descs(compressed, _parse_docstring(fn))

    # Return type: wrap scalars with x-verso-wrap-result: true
    return_ann = hints.get("return")
    if return_ann and not _is_object_type(return_ann):
        compressed["x-verso-wrap-result"] = True

    return compressed

# Constants
COMPRESS_DEPTH_CAP = 50          # fastmcp json_schema.py depth guard
_DEFAULT_CACHE_TTL = 300.0       # seconds, fastmcp proxy.py:566
```

### `ToolResult` + `ToolError` + `AuthInterrupt`

```python
# verso/tools/result.py
from dataclasses import dataclass
from typing import Optional, Literal

ErrorKind = Literal[
    "TOOL_BAD_DEFINITION", "TOOL_BAD_INPUT_SCHEMA", "TOOL_BAD_OUTPUT_SCHEMA",
    "TOOL_BAD_INPUT_VALUE", "TOOL_TIMEOUT", "TOOL_REQUIREMENTS_NOT_MET",
    "TOOL_RUNTIME_FATAL", "TOOL_RUNTIME_RETRY",
    "UPSTREAM_RATE_LIMIT", "UPSTREAM_AUTH_ERROR", "UPSTREAM_NOT_FOUND",
    "UPSTREAM_VALIDATION_ERROR", "UPSTREAM_SERVER_ERROR", "UPSTREAM_TIMEOUT",
    "UNKNOWN",
]

@dataclass
class ToolError:
    kind: ErrorKind
    can_retry: bool
    message: str                        # masked in prod (see mask_error_details)
    prompt_content: Optional[str] = None   # always surfaced to model when set
    retry_after_ms: Optional[int] = None
    developer_message: Optional[str] = None  # never sent to model

@dataclass
class AuthInterrupt:
    auth_id: str
    url: str
    status: Literal["not_started", "pending", "completed", "failed"]
    provider_id: str
    scopes: list[str]
    user_id: str

@dataclass
class ToolResult:
    ok: bool
    data: object = None
    error: Optional[ToolError] = None
    auth_interrupt: Optional[AuthInterrupt] = None  # non-None triggers auth-interrupt path

    def to_mcp_content(self) -> dict:
        """Produce MCP CallToolResult shape."""
        if self.ok:
            return {"content": [{"type": "text", "text": _serialize(self.data)}],
                    "isError": False}
        # auth interrupt → surface as isError:true with the URL
        if self.auth_interrupt:
            return {"content": [{"type": "text",
                "text": f"Authorization required: {self.auth_interrupt.url}"}],
                "isError": True}
        # application-tier error → isError:true (model reads + self-corrects)
        prompt = self.error.prompt_content or _masked_message(self.error)
        return {"content": [{"type": "text", "text": prompt}], "isError": True}
```

### `ToolDispatcher`

```python
# verso/tools/dispatcher.py
import anyio
from typing import Sequence

MAX_PARALLEL_READS = 5     # bounded concurrency for read-only tools (PRD §5.3)
MASK_ERROR_DETAILS = True  # default; disable for local dev

class ToolDispatcher:
    """Wraps tool execution: auth-check → validate → call → wrap → error-handle."""

    async def dispatch(
        self, calls: Sequence[ToolCall], ctx: RunContext
    ) -> list[ToolResult]:
        """Execute tool calls. Read-only → concurrent; mutating → sequential.
        Results appended in original call order (order preservation).
        Concurrency forced to 1 if any call needs approval."""
        ...

    async def _call_one(self, call: ToolCall, ctx: RunContext) -> ToolResult:
        tool = self.registry.get(call.name)
        if tool is None:
            return ToolResult(ok=False, error=ToolError(
                "TOOL_BAD_DEFINITION", can_retry=False,
                message=f"Unknown tool: {call.name!r}"))

        # validate args against schema (PydanticValidationError → TOOL_BAD_INPUT_VALUE)
        try:
            validated = _validate_args(call.arguments, tool.schema)
        except ValidationError as e:
            return ToolResult(ok=False, error=ToolError(
                "TOOL_BAD_INPUT_VALUE", can_retry=True,
                message="Invalid arguments",
                prompt_content=f"Invalid arguments for {call.name}: {e}"))

        # pre-execution validate() hook
        if tool.meta.validate:
            outcome = await tool.meta.validate(validated, ctx)
            if outcome != "ok":
                return _route_validate_outcome(outcome, tool)

        # auth check before execution
        if tool.meta.requires_auth:
            result = await _call_with_auth(tool, validated, ctx)
        elif tool.meta.timeout:
            with anyio.fail_after(tool.meta.timeout):
                result = await _invoke(tool, validated, ctx)
        else:
            result = await _invoke(tool, validated, ctx)

        # truncate oversized results
        if tool.meta.max_result_chars and result.ok:
            result = _truncate(result, tool.meta.max_result_chars)

        return result

# Constants
_AUTH_LONGPOLL_WAIT_SECS = 45  # Arcade arcadepy/resources/auth.py:24
_AUTH_LONGPOLL_MAX_SECS = 59   # Arcade auth.py:203 (server max)
```

### `MCPAdapter` (fastmcp ProxyProvider-equivalent)

```python
# verso/tools/adapters/mcp.py

MCP_PROTOCOL_VERSION = "2025-11-25"
_COMPONENT_CACHE_TTL = 300.0      # fastmcp proxy.py:566; 0 = disable (live catalogs)
_ACTOR_CACHE_TTL = 1800.0         # Apify const.ts:68 (30 min for slow-changing defs)
_EXECUTE_TIMEOUT_MS = 180_000     # Pipedream mcp-client.ts:233-237 (3 min per-tool cap)
_TASK_DEFAULT_WAIT_SECS = 30      # Apify waitSecs default
_TASK_MAX_WAIT_SECS = 45          # Apify waitSecs max

class MCPConnectionConfig:
    """Portable config; same shape as Claude Desktop/Cursor mcpServers."""
    type: Literal["stdio", "http"]
    # stdio: command, args?, env?
    # http:  url, headers?
    namespace: str                   # Verso-assigned namespace prefix

class MCPAdapter(ToolSourceAdapter):
    """Wraps a remote MCP server as a Verso tool source."""

    def __init__(self, config: MCPConnectionConfig,
                 cache_ttl: float = _COMPONENT_CACHE_TTL):
        self._config = config
        self._cache_ttl = cache_ttl
        self._tools_cache: tuple[list, float] | None = None  # (tools, monotonic_ts)
        self._session_id: str | None = None
        self._client: MCPClient | None = None  # None until first initialize

    async def _ensure_connected(self):
        """Lazy-connect on first use (fastmcp ProxyInitializeMiddleware pattern)."""
        if self._client is None:
            self._client = await _open_mcp_client(self._config)
            await self._client.initialize()

    async def tools_for(self, scope: str | None = None) -> list[dict]:
        """Paginate tools/list; cache; return raw MCP tool dicts."""
        await self._ensure_connected()
        if self._is_cache_fresh():
            return self._tools_cache[0]
        tools = []
        cursor = None
        while True:
            page = await self._client.list_tools(cursor=cursor)
            tools.extend(page.tools)
            cursor = page.next_cursor
            if not cursor:
                break
        self._tools_cache = (tools, time.monotonic())
        return tools

    async def run(self, tool_name: str, arguments: dict,
                  ctx: RunContext) -> ToolResult:
        await self._ensure_connected()
        try:
            raw = await self._client.call_tool(tool_name, arguments)
        except MCPTransportError as e:
            return ToolResult(ok=False, error=ToolError(
                "UPSTREAM_SERVER_ERROR", can_retry=True, message=str(e)))
        except MCPProtocolError as e:
            if e.code == -32601:  # METHOD_NOT_FOUND
                return ToolResult(ok=False, error=ToolError(
                    "TOOL_BAD_DEFINITION", can_retry=False,
                    message=f"Tool not found: {tool_name!r}"))
            if e.code == -32042:  # URL_ELICITATION_REQUIRED
                return _parse_auth_interrupt(e.data, ctx)
            return ToolResult(ok=False, error=ToolError(
                "UPSTREAM_SERVER_ERROR", can_retry=False, message=str(e)))
        # application tier: raw.is_error → isError:true passthrough (content preserved)
        if raw.is_error:
            content_text = _extract_text(raw.content)
            return ToolResult(ok=False, error=ToolError(
                "UPSTREAM_RUNTIME_FATAL", can_retry=False,
                message="Tool returned error",
                prompt_content=content_text))
        return ToolResult(ok=True, data=raw.content)

    def _is_cache_fresh(self) -> bool:
        if self._cache_ttl == 0 or not self._tools_cache:
            return False
        _, ts = self._tools_cache
        return (time.monotonic() - ts) < self._cache_ttl

    async def _handle_session_expired(self):
        """404 → discard session + re-initialize."""
        self._session_id = None
        self._client = None
        await self._ensure_connected()
```

### Deferred Loader (meta-tool mode)

```python
# verso/tools/deferred_loader.py

DEFERRED_LOADING_THRESHOLD = 20   # tools from one source above this → meta-tool mode

class DeferredLoader:
    """Exposes 5 meta-tools when a source is too large to inject fully.
    Falls back to single run_tool meta-tool for MCP clients without tools.listChanged."""

    BM25_FIELD_WEIGHTS = {
        "name": 30, "description": 30, "title": 30, "summary": 30, "tags": 30,
        "param_name": 15, "param_description": 15,
        "response_field": 5,
    }
    BM25_METHOD = "bm25+"
    BM25_STOPWORDS: list = []       # disabled — Strata bm25_search.py explicit choice
    BM25_TOP_K_DISCOVER = 50        # Strata tools.py max_results default
    BM25_TOP_K_SEARCH = 10          # Strata tools.py max_results default for search_docs
    RESULT_SERIALIZER = {"separators": (",", ":")}  # compact json — Strata tools.py:366-375

    META_TOOL_NAMES = frozenset([
        "discover_tools", "get_tool_details", "execute_tool",
        "search_tool_docs", "handle_auth",
    ])
    META_TOOL_FALLBACK_NAME = "run_tool"  # Apify call-actor pattern for no-listChanged clients
```

### Auth Interrupt Protocol

```python
# verso/tools/auth.py
from dataclasses import dataclass

@dataclass
class ToolAuthorization:
    provider_id: str          # "github", "google", "slack", …
    provider_type: str = "oauth2"
    scopes: list[str] = None  # None = provider default

# Provider shortcuts (Arcade arcade_core/auth.py pattern)
class Google(ToolAuthorization):
    def __init__(self, scopes=None):
        super().__init__(provider_id="google", scopes=scopes)

class GitHub(ToolAuthorization):
    def __init__(self, scopes=None):
        super().__init__(provider_id="github", scopes=scopes)

# … Slack, Microsoft, Linear, Notion, etc.

# Auth status polling constants
AUTH_LONGPOLL_WAIT_SECS = 45    # Arcade arcadepy/resources/auth.py:24 _DEFAULT_LONGPOLL_WAIT_TIME
AUTH_LONGPOLL_MAX_SECS = 59     # Arcade auth.py (server side max)
```

### Smithery / MCP Registry Config Format

```python
# verso/tools/adapters/registry.py
# Portable mcpServers config (Claude Desktop / Cursor compatible)
from typing import TypedDict, Literal, Union

class StdioConfig(TypedDict):
    command: str
    args: list[str] | None
    env: dict[str, str] | None

class HttpConfig(TypedDict):
    type: Literal["http"]
    url: str
    headers: dict[str, str] | None

MCPServerConfig = Union[StdioConfig, HttpConfig]

class MCPConfig(TypedDict):
    mcpServers: dict[str, MCPServerConfig]   # Smithery/Claude Desktop standard key
```

### Key Constants Summary

| Constant | Value | Source |
|---|---|---|
| `_DEFAULT_CACHE_TTL` | `300.0` s | fastmcp `proxy.py:566` |
| `_ACTOR_CACHE_TTL` | `1800.0` s (30 min) | Apify `const.ts:68` |
| `_EXECUTE_TIMEOUT_MS` | `180_000` ms (3 min) | Pipedream `mcp-client.ts:233-237` |
| `_TASK_DEFAULT_WAIT_SECS` | `30` s | Apify `call_actor_common.ts` |
| `_TASK_MAX_WAIT_SECS` | `45` s | Apify `const.ts` |
| `AUTH_LONGPOLL_WAIT_SECS` | `45` s | Arcade `auth.py:24` |
| `AUTH_LONGPOLL_MAX_SECS` | `59` s | Arcade `auth.py:203` |
| `COMPRESS_DEPTH_CAP` | `50` | fastmcp `json_schema.py` |
| `DEFERRED_LOADING_THRESHOLD` | `20` tools | DESIGNED |
| `MAX_PARALLEL_READS` | `5` | PRD §5.3 |
| `BM25_TOP_K_DISCOVER` | `50` | Strata `tools.py` |
| `BM25_TOP_K_SEARCH` | `10` | Strata `tools.py` |
| `MCP_PROTOCOL_VERSION` | `"2025-11-25"` | MCP spec |
| `AUTH_MISSING_CODE` | `-32001` | Pipedream live probe |
| `URL_ELICITATION_CODE` | `-32042` | MCP spec `schema.ts:181-201` |
| `STUCK_REPEATED_THRESHOLD` | `4` | PRD §5.1 (OpenHands) |

---

## Open Unknowns

1. **`DEFERRED_LOADING_THRESHOLD = 20` needs calibration.** Below 20, full injection is assumed
   safe; above 20, meta-tool mode kicks in. The right number depends on average schema size per
   tool and the target model's context window. Strata's claimed 60-80% context reduction needs
   empirical measurement on Verso's own registry before committing to this threshold.

2. **Embedding-based tool search opt-in API.** The `EmbeddingToolRanker` plugin for mcp-use-style
   bge-small+cosine discovery is DESIGNED but its interface (`RankerProtocol`) isn't yet specified.
   Need to prototype before locking the plugin API so the BM25 and embedding rankers are
   interchangeable.

3. **OAuth provider adapter library scope.** Arcade ships 20+ provider subclasses (`Google`,
   `GitHub`, `Slack`, `Microsoft`, `Linear`, …). Verso's v1 needs a minimal set (GitHub + Google
   cover 80% of dogfood use). Full provider library is Phase 3 work; need to decide whether to
   depend on `arcade-tdk`'s auth models or implement from scratch.

4. **Multi-tenant `user_id` credential storage in v1.** Pipedream/Arcade/Nango all store per-user
   OAuth tokens server-side. Verso's dogfood phase is single-developer; the credential storage
   backend (sqlite-backed token store vs delegating to Arcade/Nango) is unresolved. Defer until
   Phase 2 (durable runtime), when the auth-interrupt path needs a real backend.

5. **`ToolAnnotations` vs `ToolMeta` for permission routing.** `ToolMeta.destructive` and
   `read_only` map onto `ToolAnnotations.destructiveHint/readOnlyHint` for MCP wire use, but the
   spec says annotations from untrusted servers must not be trusted for security decisions. The
   boundary between "trusted (from our `@tool` decorator) vs untrusted (from upstream MCP)" needs
   a concrete policy in the dispatcher — currently DESIGNED as "local tools are trusted, MCP-
   sourced tools are untrusted hints only."

6. **Task-augmented execution + durable loop interaction.** The `CreateTaskResult{taskId,
   pollInterval}` path for long-running tools is specified but its interaction with Verso's
   durable checkpoint model (§6.1) is unresolved. Specifically: when a long-running tool returns
   a task handle, does the durable runtime checkpoint between polls, or does it block? This is a
   Phase 2 design question.

7. **`vm` sandboxing threshold for user-defined tools.** Nango's `vm` sandbox (allowlisted
   `require`, null prototype, no `eval`) applies to *untrusted* tool code. Verso's `@tool`
   functions are trusted (developer-authored); if Verso ever exposes a plugin API for third-party
   tools (Phase 3), the isolation boundary needs to be defined. Not blocking Phase 0-1.

8. **`notify-on-deferred-load` for non-MCP clients.** When the deferred loader pins a new tool
   (via `get_tool_details` → expand schema), it fires `notifications/tools/list_changed` for MCP
   clients. For non-MCP consumers (direct Python `ToolRegistry` use), the notification mechanism
   is unspecified. An `on_registry_change` async callback hook covers it but hasn't been designed
   yet.
