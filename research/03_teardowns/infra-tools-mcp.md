# Tools & MCP — Verso Research Note
## Cluster: infra-tools-mcp
### Systems: fastmcp (PrefectHQ) · MCP Spec 2025-11-25 · Klavis Strata · Arcade.dev · Nango · Pipedream Connect · Toolhouse · Smithery · Apify MCP Server · mcp-use
*Sources: cloned `github.com/PrefectHQ/fastmcp` @ e1b52d0 (2026-06-05, v3.x), `github.com/modelcontextprotocol/modelcontextprotocol` (schema/2025-11-25), `github.com/Klavis-AI/klavis` (open-strata/), `arcadepy==1.10.0` + `arcade-tdk==3.8.0` wheels, `github.com/NangoHQ/nango`, `github.com/PipedreamHQ/mcp-chat`, `toolhouse==1.4.0` wheel + `github.com/toolhouseai/toolhouse-sdk-python`, `github.com/smithery-ai/cli`, `github.com/apify/apify-mcp-server`, `github.com/mcp-use/mcp-use`*

> **Scope.** This note extracts the *tool-layer mechanisms* Verso needs: the `@tool`→JSON-Schema contract (auto-generated from Python type hints), deferred/progressive tool loading (so a 100+ tool registry doesn't blow the context window), the three-tier tool error model (transport / protocol / application `isError:true`), auth-gated tool HITL interrupts, and lazy per-user scoping. Cross-references: Composio is covered at R4 depth in `03_teardowns/fw-composio-browseruse.md` + `infra-retrieval-tools.md` (auth delegation, trigger arch, MCP adapter) — not re-RE'd here; ADK `FunctionTool`/`MCPToolset`, Mastra MCP adapter, and Pydantic-AI `@agent.tool`/RunContext are covered elsewhere and referenced where the design space overlaps.
>
> **Labels:** KNOWN = read from source (file:line / wheel) · INFERRED = derived from probing/docs · DESIGNED = our engineering fill for a gap.

---

## fastmcp (PrefectHQ)

### What It Is

fastmcp is the de-facto Python MCP server/client framework — the v1 codebase was absorbed into the official MCP Python SDK in 2024, then forked back out as a standalone project. v3.x (cloned here at `e1b52d0`, June 2026) restructured the package into `fastmcp_slim/` (core) + `fastmcp_remote/` and introduced **Providers** as the composition primitive (a `Provider` exposes tools/resources/prompts; `ProxyProvider`, `FastMCPProvider`, `TransformingProvider`, `OpenAPIProvider` are the concrete kinds). For Verso the three load-bearing subsystems are: (1) the `@tool`→JSON-Schema generator, (2) the `ProxyProvider` (multi-server aggregation with a 300s cache + lazy session init), and (3) the three-tier error model.

### The `@tool` → JSON-Schema Contract (KNOWN — `tools/function_parsing.py`, `tools/function_tool.py`)

The entire schema-gen path is **Pydantic's `TypeAdapter.json_schema()` applied to the function object itself**, not to a hand-written model. This is the single most reusable mechanism in the file. The pipeline (`ParsedFunction.from_function`, `function_parsing.py:130-314`):

1. **Reject unsupported signatures** (`:141-147`): functions with `*args` (`VAR_POSITIONAL`) or `**kwargs` (`VAR_KEYWORD`) raise `ValueError` — a tool schema must enumerate every parameter, so variadics are forbidden. `exclude_args` names must exist *and* have a default (`:150-160`).
2. **Docstring parse** (`:163-184`): `parse_docstring(fn)` extracts the description + per-parameter docs. For callable classes the *class* docstring supplies the description but the *`__call__`* docstring supplies parameter docs (avoids leaking `__init__` docs into the schema).
3. **Context-annotation transform** (`:186-195`): `transform_context_annotations(fn)` rewrites `Context`-typed params into `Depends()` markers, then `without_injected_parameters(fn)` strips DI params (Context, Docket deps) so they never appear in the public schema. This is the seam that lets a tool take `ctx: Context` without that showing up as an LLM-visible argument.
4. **Schema generation** (`:202-203`): `get_cached_typeadapter(wrapper_fn).json_schema()`. `get_cached_typeadapter` (`utilities/types.py:45-120`) is where the type-hint→schema magic lives: it resolves forward refs with `get_type_hints(include_extras=True)`, then **rewrites `Annotated[T, "a string"]` into `Annotated[T, Field(description="a string")]`** (`:67-76`) so bare-string annotations become schema descriptions. It rebuilds a fresh `FunctionType` carrying the processed annotations and feeds it to Pydantic's `TypeAdapter` (`:100-118`). The whole thing is cached because `TypeAdapter` construction is expensive per-function.
5. **Schema compression** (`:207-209`): `compress_schema(input_schema, prune_params=…, prune_titles=True)` (`utilities/json_schema.py:645-685`). Single-tree-traversal that: resolves the root-level `$ref` (MCP requires `type:"object"` at the root), prunes excluded params, removes `title` fields, and prunes unused `$defs`. **It deliberately does NOT strip `additionalProperties:false`** (`:658-660`) — "some clients (e.g. Claude) require additionalProperties:false for strict validation." That's a concrete interop constant Verso must keep.
6. **Docstring → schema description injection** (`:214-221`): for each param without an explicit `description` (from `Field`/`Annotated`), copy the docstring's parameter doc in. Explicit annotations win.

**Output schema** (`:223-305`) is generated separately from the *return* annotation, with a hard MCP rule: output schemas must be object types. When the return type is a scalar/list (non-object), fastmcp wraps it: `_WrappedResult[T]` → schema gets `"x-fastmcp-wrap-result": True` (`:292-297`), and at call time the value is wrapped as `{"result": value}` (`base.py:335-338`). A roster of types is force-excluded from output-schema generation by `replace_type(...→_UnserializableType)` (`:265-282`): `bytes`, `Image`/`Audio`/`File`, `ToolResult`, and all MCP content blocks (`TextContent`, `ImageContent`, `ResourceLink`, `EmbeddedResource`). These already *are* MCP content, so they don't form structured content.

**The `tool` decorator itself** (`function_tool.py:440-551`) is thin: it does NOT eagerly build the schema. By default (`decorator_mode != "object"`) it just **attaches a frozen `ToolMeta` dataclass to `fn.__fastmcp__`** (`:504-524`) and returns the original function unchanged. Schema generation is deferred to `FunctionTool.from_function` when the tool is actually registered with a server. `ToolMeta` (`:68-90`) carries: `name, version, title, description, icons, tags, output_schema, annotations, meta, task, exclude_args, serializer, timeout, auth, enabled, run_in_thread`. **This deferral is itself a deferred-loading pattern**: the decorator is cheap; the expensive `TypeAdapter` build only happens at registration.

**`run_in_thread` constant + the timeout-incompatibility guard** (`:227-239`): sync tool functions are dispatched to a worker threadpool by default so they don't block the event loop. `run_in_thread=False` runs inline (for thread-affinity libs like Windows COM/tkinter) — but combining `timeout=...` with `run_in_thread=False` on a *sync* function is rejected at registration, because inline execution has no `anyio` cancellation checkpoints so the timeout would be a silent no-op. The timeout path (`:299-327`) wraps execution in `anyio.fail_after(self.timeout)`; on `TimeoutError` it raises `McpError(ErrorData(code=-32000, …))`.

**Schema-compression subtleties Verso must replicate** (`json_schema.py:455-560`, `_single_pass_optimize`): one tree walk that (a) collects every `$ref` (even inside user extension keys like `x-ui` — a ref there still pins the `$def` as used) to drive dead-`$defs` removal via a `root_refs`/`def_dependencies` reachability graph; (b) prunes `title` **only when the node is a real schema** — guarded by `isinstance(node["title"], str)` (so a user property literally named `title` isn't deleted) and by the node containing a structural keyword OR being all-metadata (Pydantic emits bare `{"title":"X"}` for `Any`-typed fields, and *Gemini 2.5 Flash rejects bare-title nodes with `MALFORMED_FUNCTION_CALL`* — a real interop bug this guards against); (c) a depth cap of 50 to prevent infinite recursion on self-referential schemas. The `in_schema` flag stops cleanups from mutating opaque user-extension payloads while still ref-collecting through them.

**Reimplementable reference (the whole `@tool`→schema contract, DESIGNED port for Verso):**
```python
import inspect
from pydantic import TypeAdapter, Field
from typing import Annotated, get_origin, get_args

def build_tool_schema(fn) -> dict:
    sig = inspect.signature(fn)
    for p in sig.parameters.values():                       # 1. reject variadics
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            raise ValueError("tools cannot take *args/**kwargs")
    hints = inspect.get_type_hints(fn, include_extras=True)  # 2. resolve forward refs
    processed = {}
    for name, ann in hints.items():
        if get_origin(ann) is Annotated and len(get_args(ann)) == 2 \
           and isinstance(get_args(ann)[1], str):            # 3. Annotated[T,"str"]→Field(desc)
            base, desc = get_args(ann)
            processed[name] = Annotated[base, Field(description=desc)]
        else:
            processed[name] = ann
    wrapper = strip_di_params(fn)                            # 4. drop ctx:Context / Depends()
    wrapper.__annotations__ = processed
    schema = TypeAdapter(wrapper).json_schema()              # 5. Pydantic does the work
    schema = resolve_root_ref(schema)                        # 6a. root must be type:object
    schema = prune_titles_and_dead_defs(schema)              # 6b. KEEP additionalProperties:false
    inject_docstring_param_descs(schema, parse_docstring(fn))# 7. docstring → descriptions
    return schema                                            # output schema: same on return ann,
                                                             # object-wrap scalars w/ x-wrap-result
```
**Verso's `@tool` can be a near-verbatim port of this — Pydantic does 95% of the work; the load-bearing 5% is the variadic rejection, the `Annotated[T,"str"]`→`Field` rewrite, DI-param stripping, root-`$ref` resolution, and the title-prune guards.**

### ProxyProvider — Multi-Server Aggregation, 300s Cache, Lazy Session (KNOWN — `server/providers/proxy.py`, 1239 lines)

`ProxyProvider(client_factory, cache_ttl=None)` (`:604-625`) wraps a remote MCP server as a local provider; `mcp.add_provider(proxy.with_namespace("remote"))` aggregates it into a tool namespace.

**Cache design** (`:553-668`): four independent `_CacheEntry` slots — tools, resources, templates, prompts — each holding `(items, monotonic_timestamp)`. `is_fresh(ttl)` = `(time.monotonic() - timestamp) < ttl`. **`_DEFAULT_CACHE_TTL = 300.0`** (`:566`). `_list_tools()` (`:638-653`) opens the client (`async with client:`), calls `client.list_tools()`, wraps each raw MCP tool as a `ProxyTool` via `from_mcp_tool`, and refreshes the cache stamp. `_get_tool(name)` (`:655-668`) reads from cache if fresh, else triggers a fresh `_list_tools()`. `cache_ttl=0` disables caching — recommended "for backends whose component lists change dynamically." Critically, the docstring records the design intent: *"The cache stores the backend's raw component metadata and is shared across all sessions; per-session visibility and auth filtering are applied after cache lookup by the server layer."* The cache is content-shared, the filtering is per-session.

**`METHOD_NOT_FOUND` graceful degradation** (`:647-651`): if the upstream doesn't implement `tools/list`, the proxy treats it as an empty list rather than failing — a backend that exposes only resources still proxies.

**Lazy bridge session init** (`ProxyInitializeMiddleware`, `:79-114`): the proxy does *not* connect upstream at server start. It registers a middleware on `on_initialize` — so the upstream connection (`client.initialize()`) only fires when a downstream client first sends `initialize`. This is the exact deferred-connection pattern Verso wants: the MCP edge is dormant until first use. Connection errors (`RuntimeError`, `TimeoutError`, `httpx.HTTPError`, `anyio.ClosedResourceError/EndOfStream/BrokenResourceError`) are converted to `_proxy_upstream_error` → `McpError(INTERNAL_ERROR)` (`:70-76`).

**Per-request session strategy** (`_create_client_factory`, `:803-867`): the factory decides session reuse vs fresh per backend type. A *connected* `ProxyClient` → `client.new()` per request (fresh session, avoids request-context leakage). A *connected* plain client → reuse one session for all requests (logs a warning about concurrent context mixing). Anything else → wrap in `ProxyClient` and `.new()` per request. `StatefulProxyClient` (`:1127-1213`) is the exception: it *reuses* sessions across requests (for stateful backends like Playwright MCP) and therefore has to fix up stale `request_ctx` ContextVars — `ProxyTool.run` stashes the live `(RequestContext, weakref[FastMCP])` into a shared mutable `_proxy_rc_ref[0]` (`:188-192`) before each backend call, and context-restoring handler wrappers read it to detect/correct staleness. The receive-loop reuse → ContextVar-staleness problem is a real footgun for any stateful proxy and Verso should note it.

**Header forwarding** (`ProxyClient.__init__`, `:1117-1124`): proxy clients set `transport.forward_incoming_headers = True` so the downstream caller's `Authorization` header is propagated to the upstream MCP server. This is the credential-passthrough seam — the proxy doesn't store creds, it forwards them.

### Three-Tier Error Model (KNOWN — `server/server.py:1281-1312`, `exceptions.py`, `proxy.py:213-226`)

fastmcp distinguishes three error tiers, which is exactly the split Verso's tool executor needs to route retries:

1. **Transport tier** — connection/network failures (`httpx.HTTPError`, `anyio.ClosedResourceError`). In the proxy these become `McpError(INTERNAL_ERROR)` (`proxy.py:70-76`). At the JSON-RPC layer this is a *protocol error* the LLM never sees as content — the request itself failed.
2. **Protocol tier (JSON-RPC error)** — a raised exception in the tool body. `call_tool` (`server.py:1281-1312`) catches `FastMCPError` (logs + re-raises), `PydanticValidationError` (bad arguments → re-raise), and the catch-all `Exception` → wrapped in `ToolError`. The MCP SDK turns a raised `ToolError` into `CallToolResult(isError=True)` at the boundary. **`mask_error_details`** (`server.py:358-362`, default from settings): when True, the error message is replaced with a generic `"Error calling tool {name!r}"` so internal details don't leak to the model; when False the real exception string is included.
3. **Application tier (`isError: true`)** — a tool that *succeeds at the protocol level* but returns a failure result. `ToolResult(is_error=True)` round-trips through `CallToolResult.isError` (`base.py:139-150`). The proxy preserves this faithfully (`proxy.py:213-226`): an upstream `isError:true` result is passed through with its content + structuredContent + meta intact rather than collapsed into a raised error — "the client still raises on isError by default" but the *content* survives so the LLM can read and retry.

**The actionable-error escape hatch** (`server.py:1300-1308`): even when masking is on, two cases bypass it because the LLM should act on them — `httpx.HTTPStatusError` 429 → `ToolError("Rate limited by upstream API, please retry later")`, and `httpx.TimeoutException` → `ToolError("Upstream request timed out, please retry")`. This is a hand-built version of the MCP "retryable error" category. (The framework has no first-class `@tool(on_error=…)` decorator yet — FastMCP issue #2882 tracks this gap; Verso can fill it.)

### Aggregation, Namespacing & Tool Transforms (KNOWN — `server/providers/aggregate.py`, `tools/tool_transform.py`)

`AggregateProvider` (`aggregate.py:47-137`) composes N providers into one tool surface. `add_provider(provider, namespace="api")` (`:90-114`) wraps the provider in a `Namespace` transform: tools become `api_toolname`, resources `protocol://api/path`, prompts `api_promptname`. **Cross-provider name-collision handling** (`:123-137`): when two providers expose the same MCP identity, the default `provider_error_strategy="warn"` logs and the first-wins (matching highest-version semantics); `"raise"` propagates the first provider error. This is the multi-server aggregation Verso needs — namespace-prefix to avoid collisions, with a configurable collision policy.

**`ArgTransform` (`tool_transform.py:103-188`) is the mechanism for adapting a third-party tool's schema without rewriting it** — critical for Verso wrapping MCP-sourced tools. A transform can: `rename` an argument (`ArgTransform(name="new")`), change its `description`/`type`, inject a `default`/`default_factory`, mark `required`, or **`hide` it from the LLM while passing a constant** (`ArgTransform(hide=True, default="const")` — e.g. hide an API-version arg and pin it). The transformed tool's body calls `forward(**kwargs)` (`:46-73`) to invoke the parent tool with the *transformed* arg names, or `forward_raw(**kwargs)` (`:76-97`) to pass the original names. So Verso can take a verbose/leaky MCP tool, hide its noise args, rename for clarity, and re-expose a clean schema — all without touching the upstream. (Cf. mcp-use's lack of any transform layer — a gap.)

### Auth-Gated Tools & HITL Elicitation (KNOWN — `utilities/authorization.py`, `server/elicitation.py`)

**`AuthCheck`** (`authorization.py`, 101 lines): a tool can carry `auth: AuthCheck | list[AuthCheck]`. An `AuthCheck` is a callable `(AuthContext) -> bool` that returns False to deny or raises `AuthorizationError` (`:50-99`). `require_scopes(*scopes)` and `restrict_tag(tag, scopes=[...])` are the built-in factories. `run_auth_checks` (`:76-99`) runs them before tool execution; a raised `AuthorizationError` propagates (becomes a protocol error). This is *authorization-as-predicate* — synchronous, no interrupt. (Contrast Arcade below, which does an *interrupt*.)

**Elicitation** (`server/elicitation.py`) is fastmcp's HITL primitive: a tool calls `ctx.elicit(message, response_type)` mid-execution and the loop pauses for the user. The response is one of three actions — `AcceptedElicitation[T]` (`action:"accept"`, carries validated `data`), `DeclinedElicitation`, `CancelledElicitation`. Scalar/shorthand response types are wrapped (`ScalarElicitationType`), full BaseModel/dataclass types pass through `handle_elicit_accept` (`:309-340`) which validates the returned content against the requested schema. **For Verso this is the in-loop human-input seam** (analogous to a "ask the user" tool); the auth-interrupt seam is separate and Arcade models it better.

### For Verso

- **Port the `@tool` schema-gen verbatim.** `pydantic.TypeAdapter(fn).json_schema()` over the function object is the whole contract. Steps Verso must replicate exactly: reject `*args`/`**kwargs`; rewrite `Annotated[T,"str"]`→`Field(description=)`; strip DI params (`ctx: Context`) before schema-gen; compress (resolve root `$ref` to `type:object`, prune titles, prune unused `$defs`) but **keep `additionalProperties:false`** (Claude strict-mode needs it); object-wrap scalar return types with an `x-...-wrap-result` flag.
- **Defer schema-gen to registration, not decoration.** `@tool` should attach cheap metadata and return the unchanged function; build the `TypeAdapter`/schema only when the tool is added to a registry. This is free deferred-loading at the single-tool granularity.
- **Adopt the 300s component cache for MCP edges.** A `ProxyProvider`-equivalent should cache `list_tools` results with a monotonic-clock TTL (default 300s, `0` to disable) and resolve single-tool lookups from cache to avoid re-opening the upstream connection. Cache the *raw* metadata, apply per-session visibility/auth *after* lookup.
- **Lazy-connect the MCP edge on first `initialize`, never at startup.** Register an `on_initialize` hook that opens the upstream client lazily. Verso's deferred tool loader should treat remote MCP servers as dormant until first use.
- **Implement the three-tier error split explicitly.** transport failure → abort/retry-connection (don't show LLM); raised exception → JSON-RPC error (mask details by default, with an actionable-error escape hatch for 429/timeout); returned-failure → `isError:true` passthrough that **keeps the content** so the LLM can read and self-correct. Verso's executor must route these three differently — retries belong only on transport + retryable-application errors, never on validation errors.
- **Forward the caller's `Authorization` header to upstream MCP servers; don't store creds in the proxy.** Per-user credential isolation is a header-forwarding problem at the edge (cf. Pipedream `external_user_id` below).
- **Fill the `@tool(on_error=…)` gap fastmcp left open.** A first-class per-tool error-category map (transient/validation/business/permission + `is_retryable`) is the clean version of fastmcp's hand-coded 429/timeout special-cases.

---

## MCP Spec — 2025-11-25 (modelcontextprotocol)

### What It Is

The 2025-11-25 revision is the current stable MCP spec. It is the *wire contract* Verso's MCP edge must produce and consume — not a product. The TS source of truth is `schema/2025-11-25/schema.ts` (2587 lines); the prose is under `docs/specification/2025-11-25/`. For Verso the load-bearing parts are the tool message shapes (pagination, `isError` vs JSON-RPC error split), the Streamable HTTP session lifecycle, and the OAuth discovery model.

### Tool Message Shapes (KNOWN — `schema.ts`)

**`tools/list` is paginated via an opaque cursor** (`schema.ts:629-648, 1088-1099`). `ListToolsRequest extends PaginatedRequest` → optional `params.cursor?: Cursor` (`Cursor = string`, "opaque token"). `ListToolsResult extends PaginatedResult` → `{ tools: Tool[], nextCursor?: Cursor }`. The contract: pass no cursor for page 1; the server returns `nextCursor` if more pages exist; pass it back to fetch the next page; absence of `nextCursor` = last page. The cursor is **opaque** — the client must not parse or synthesize it. This is the protocol primitive a deferred tool loader builds on: don't `tools/list` the whole 100-tool catalog up front; page it.

**The `Tool` shape** (`:1251-1298`): `name` (from `BaseMetadata`), `description?`, `inputSchema` (`{ $schema?, type:"object", properties?, required? }` — root MUST be `type:"object"`), `outputSchema?` (same shape, also root-`type:"object"`-only; "Defaults to JSON Schema 2020-12 when no explicit `$schema`"), `execution?: ToolExecution`, `icons?` (new in this rev — SEP-973), `annotations?: ToolAnnotations`, `_meta?`. **`ToolAnnotations`** (`:1182-1224`) are *hints only* (clients "should never make tool use decisions based on ToolAnnotations from untrusted servers"): `readOnlyHint` (default false), `destructiveHint` (default true, meaningful only when not read-only), `idempotentHint` (default false), `openWorldHint` (default true). **`ToolExecution.taskSupport`** (`:1231-1244`): `"forbidden"` (default) | `"optional"` | `"required"` — declares whether the tool supports the new task-augmented (durable/pollable) execution.

**Concrete wire messages Verso must produce/consume** (verbatim shapes from `schema.ts` + `lifecycle.mdx`):
```jsonc
// tools/list request (page 2)
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{"cursor":"eyJvZmZzZXQiOjUwfQ"}}
// tools/list result
{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"create_issue","description":"…",
  "inputSchema":{"type":"object","properties":{…},"required":["title"]},
  "annotations":{"readOnlyHint":false,"destructiveHint":true,"idempotentHint":false,"openWorldHint":true},
  "execution":{"taskSupport":"optional"}}], "nextCursor":"eyJvZmZzZXQiOjEwMH0"}}
// tools/call request
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"create_issue","arguments":{"title":"bug"}}}
// tools/call SUCCESS (application result; isError omitted == false)
{"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"created #42"}],"structuredContent":{"id":42}}}
// tools/call APPLICATION FAILURE (HTTP 200, valid result, isError:true — LLM sees & retries)
{"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"title too long, max 80 chars"}],"isError":true}}
// tools/call PROTOCOL ERROR (tool not found / unsupported)
{"jsonrpc":"2.0","id":3,"error":{"code":-32601,"message":"Unknown tool: create_issue"}}
```
The `initialize` handshake (`lifecycle.mdx:53-126`): client sends `{protocolVersion:"2025-11-25", capabilities:{roots,sampling,elicitation:{form,url},tasks}, clientInfo}`; server replies `{protocolVersion, capabilities:{tools:{listChanged:true}, resources:{subscribe,listChanged}, tasks:{…}}}`; client then sends `notifications/initialized`. The `elicitation:{url:{}}` client capability is what gates whether a server may use the `-32042` URL-elicitation interrupt.

**The `isError:true` vs JSON-RPC-error split** (`CallToolResult`, `:1106-1132`) — the single most important contract for Verso's executor. `CallToolResult = { content: ContentBlock[], structuredContent?: object, isError?: boolean }`. The spec text is explicit: *"Any errors that originate from the tool SHOULD be reported inside the result object, with `isError` set to true, NOT as an MCP protocol-level error response. Otherwise the LLM would not be able to see that an error occurred and self-correct. However, any errors in finding the tool, an error indicating the server does not support tool calls, or any other exceptional conditions, should be reported as an MCP error response."*
- **Application error** (tool ran, failed logically): `CallToolResult{isError:true, content:[…explanation…]}` — HTTP 200, valid JSON-RPC *result*. The model sees it and retries.
- **Protocol error** (tool not found, tools unsupported, malformed request): `JSONRPCErrorResponse{ error: { code, message, data? } }` (`:161-165`). Standard codes (`:174-179`): `PARSE_ERROR=-32700`, `INVALID_REQUEST=-32600`, `METHOD_NOT_FOUND=-32601`, `INVALID_PARAMS=-32602`, `INTERNAL_ERROR=-32603`. Implementation-specific range `[-32000,-32099]`.

**SEP-1303 clarification (changelog minor #5):** *input validation errors should be returned as Tool Execution Errors (`isError:true`) rather than Protocol Errors* — so the model can self-correct a bad argument. This refines the split: a *schema-validation failure of the arguments* is now application-tier (`isError:true`), not `INVALID_PARAMS`. fastmcp's choice to re-raise `PydanticValidationError` as a protocol error is the older behavior; the 2025-11-25 spec wants it surfaced to the model. **Verso must default argument-validation failures to `isError:true` content the LLM can read.**

**New JSON-RPC error `URL_ELICITATION_REQUIRED = -32042`** (`:181-201`): a server can answer a request with this error code + `data.elicitations: ElicitRequestURLParams[]` to say "the client must complete a URL-mode elicitation (e.g. open this OAuth URL) before I can proceed." This is the spec-level *interrupt-via-error* primitive — directly analogous to the Arcade authorization interrupt below, but standardized into the protocol.

### Streamable HTTP Session Lifecycle (KNOWN — `basic/transports.mdx`)

Streamable HTTP replaced the old HTTP+SSE dual-endpoint transport. One **MCP endpoint** path supporting both POST and GET (`transports.mdx:71`). Session lifecycle:
1. **Init** (`:198-205`): the server MAY assign a session ID, returned in the `MCP-Session-Id` HTTP header on the response carrying `InitializeResult`. SHOULD be globally unique + cryptographically secure; MUST be visible ASCII (0x21-0x7E).
2. **Subsequent requests** (`:207-215`): the client MUST echo `MCP-Session-Id` on every request. A server requiring a session SHOULD reply `400 Bad Request` to requests lacking it; if the session expired, the server replies `404 Not Found`. On `404` the client MUST start a new session (fresh `InitializeRequest` without a session ID).
3. **Termination** (`:217-219`): client SHOULD send `HTTP DELETE` with the session ID to end it; server MAY reply `405 Method Not Allowed` if it doesn't allow client-initiated termination.
4. **Message rules** (`:88-131`): every JSON-RPC message is a new HTTP POST. POST `Accept` header MUST list both `application/json` and `text/event-stream`. Server answers a POST containing a *request* with either `application/json` (single response) or `text/event-stream` (an SSE stream that eventually carries the response). POSTs containing only *notifications/responses* get `202 Accepted` with no body.
5. **GET stream** (`:135-162`): client MAY open a standalone SSE stream via GET (server→client messages); server returns `text/event-stream` or `405`.
6. **Resumability** (`:170-187`): SSE events carry IDs; on disconnect the client reconnects with `Last-Event-ID`; **resumption is always via GET regardless of the original stream's origin** (SEP-1699), and event IDs SHOULD encode stream identity so the server can correlate.
7. **Version header** (`:265-280`): after init, HTTP requests MUST carry `MCP-Protocol-Version: 2025-11-25`. Missing header → server assumes `2025-03-26` for back-compat; unsupported version → `400`.

### Task-Augmented Execution — Durable, Pollable Tool Calls (KNOWN — `basic/utilities/tasks.mdx`, experimental SEP-1686)

New in 2025-11-25: a `tools/call` (or `sampling`/`elicitation`) request can be **augmented with a task** so a long-running tool returns immediately with a task handle and the result is fetched later. This is the protocol-native answer to Verso's long-running-tool problem (cf. Arcade's `run_at` scheduling, fastmcp's `task=True`).

- **Capability-gated** (`:35-105`): both parties declare a `tasks` capability at `initialize`, structured by request category — `tasks.requests.tools.call: {}` means the server accepts task-augmented tool calls; `tasks.list`/`tasks.cancel` gate those ops. A tool *also* declares `execution.taskSupport: "forbidden"|"optional"|"required"` in `tools/list`. The matrix (`:113-117`): `forbidden`/absent → calling as task → `-32601`; `optional` → client may use either; `required` → client *must* use a task else `-32601`.
- **Create** (`:126-169`): client sends `tools/call` with `params.task: {ttl: 60000}` (desired lifetime ms). Server replies with a **`CreateTaskResult`** (NOT the tool result) carrying `{taskId, status:"working", statusMessage, createdAt, ttl, pollInterval:5000}`. An optional `_meta["io.modelcontextprotocol/model-immediate-response"]` string can be fed to the model as a placeholder immediate result.
- **State machine**: `working → {completed | failed | cancelled}`, plus an `input_required` interrupt status (the task needs more input mid-flight). Terminal = completed/failed/cancelled.
- **Poll** (`:192-223`): `tasks/get {taskId}` returns the current `Task`. Requestor SHOULD respect the server's `pollInterval` (e.g. 5000ms) and poll until terminal or `input_required`. Optional `notifications/tasks/status` (`:282-303`) pushes the full Task on change — but requestors MUST NOT rely on it; keep polling.
- **Result** (`:238-250`): `tasks/result {taskId}` blocks until terminal and returns the original result type (`CallToolResult` for a tool call). `tasks/get` polling may continue in parallel.

### Authorization Discovery (KNOWN — `basic/authorization.mdx`)

The 2025-11-25 auth model (changelog major #1, #3, #8): clients discover auth servers via **OAuth 2.0 Protected Resource Metadata (RFC 9728)** — servers MUST implement it. Discovery is two-path (`:91-101`): parse the `WWW-Authenticate` header (`resource_metadata="…"`) on a `401`, else fall back to `.well-known/oauth-protected-resource[/path]`. Auth-server metadata is fetched by trying OAuth AS Metadata + OpenID Connect Discovery well-known endpoints in a defined order (`:131-144`). **Client ID Metadata Documents (CIMD, SEP-991)** replace Dynamic Client Registration as the recommended registration mechanism. **Resource Indicators (RFC 8707, `:402-471`):** clients MUST send the `resource` parameter (canonical MCP-server URI) on token requests so the issued token is *audience-bound* to that server; servers MUST validate they are the intended audience. **Incremental scope consent (SEP-835):** a server can demand more scopes mid-session via a `WWW-Authenticate` challenge listing the additional `scope`.

### For Verso

- **Page `tools/list`; never bulk-load.** Treat `cursor`/`nextCursor` as the protocol foundation for deferred loading. Verso's MCP client should expose tool discovery as an async generator over pages, and the registry should be able to stop after the first page (or a relevance filter) without materializing the whole catalog.
- **Default argument-validation failures to `isError:true`, not `INVALID_PARAMS`.** Per SEP-1303, a bad-argument result should be application-tier content the LLM reads and retries. Reserve JSON-RPC errors strictly for tool-not-found / unsupported / transport. This is a divergence from fastmcp's current behavior — Verso should follow the newer spec.
- **Model the interrupt as `URL_ELICITATION_REQUIRED (-32042)` at the protocol edge.** When a tool needs the user to complete an OAuth/consent URL, the spec-native answer is this error code + `data.elicitations[]`. Verso's HITL seam for *auth* should emit/consume this, distinct from in-loop `ctx.elicit` input.
- **Treat `MCP-Session-Id` 404 as "re-initialize", and resume SSE via GET + `Last-Event-ID`.** Verso's MCP edge needs a session state machine: on `404` discard the session and re-handshake; on stream disconnect reconnect via GET with the last event ID. Carry `MCP-Protocol-Version: 2025-11-25` on every post-init request.
- **Be a Protected-Resource-Metadata client.** Discover auth servers from `WWW-Authenticate`/`.well-known`, send RFC 8707 `resource` on token requests (audience-binding), support CIMD registration and incremental `WWW-Authenticate` scope upgrades. This is the prod path for Verso authenticating to remote MCP servers.
- **`ToolAnnotations` are hints, not gates.** `readOnlyHint`/`destructiveHint`/`idempotentHint`/`openWorldHint` are useful for Verso's planner (e.g. don't auto-retry a `destructiveHint:true` non-idempotent tool) but MUST NOT be trusted for security decisions from untrusted servers.
- **Adopt task-augmented execution for long-running tools.** A tool that may run minutes should declare `execution.taskSupport:"optional"` and return a `CreateTaskResult{taskId, pollInterval}` so the agent loop isn't blocked; the loop polls `tasks/get` at `pollInterval` until terminal, then `tasks/result`. Pair the `input_required` task status with the elicitation seam, and `ttl` with cleanup. This unifies Arcade's `run_at`, fastmcp's `task=True`, and Apify's `taskSupport:'optional'` under the protocol — Verso's executor should treat "sync result" vs "task handle" as one branch in the call path.

---

## Klavis AI — Strata (open-strata)

### What It Is

Strata is a "unified MCP router": instead of exposing N upstream servers' full tool catalogs (which floods the context window), Strata exposes exactly **5 meta-tools** and makes the agent *progressively* discover → inspect → execute the real actions on demand. The open-source implementation is `open-strata/src/strata/` (Python). Klavis's published benchmark claims this progressive loading yields ~15.2% higher tool-selection accuracy and 60–80% context reduction vs. flat tool injection (INFERRED — marketing/blog number, not in source; usable as a calibration target, not a verified constant). The mechanism, however, is fully readable.

### The 5 Meta-Tools (KNOWN — `tools.py:14-145`)

Strata's `list_tools` returns only these (`server.py:81-87` → `get_tool_definitions(user_available_servers)`), regardless of how many real actions exist upstream:
1. `discover_server_actions` — "**PREFERRED STARTING POINT**: Discover available actions from servers based on user query." Inputs: `user_query` (NL, required), `server_names` (array, items enum-constrained to `user_available_servers`, required).
2. `get_action_details` — Inputs: `server_name` (enum), `action_name` (string).
3. `execute_action` — Inputs: `server_name` (enum), `action_name`, plus the parameter-carrying fields `path_params`, `query_params`, `body_schema` — **all typed as JSON-string** (`{"type":"string", "description":"JSON string containing …"}`, `body_schema` default `"{}"`). This is a deliberate design choice: the meta-tool's own schema stays tiny and fixed because the *real* parameters are passed as an opaque JSON string, not as a per-action expanded schema.
4. `search_documentation` — Inputs: `query`, `server_name` (enum), `max_results` (int, 1–50, default 10). Keyword/BM25 search over one server's actions.
5. `handle_auth_failure` — Inputs: `server_name` (enum), `intention` (enum `["get_auth_url","save_auth_data"]`), optional `auth_data`. The auth-recovery seam.

Note the `enum: user_available_servers` constraint on every `server_name`/`server_names` field — the server list is the *only* thing eagerly injected into the model's context. Everything below that (action names, schemas) is fetched lazily.

### The 4-Stage Progressive Call Sequence + Per-Stage Data Shape (KNOWN — `tools.py:148-375`)

This is the exact protocol Verso wants. `execute_tool(name, arguments, client_manager)` dispatches:

**Stage 1 — `discover_server_actions`** (`:155-203`). For each requested `server_name`: `client = client_manager.get_client(server_name)` → `tools = await client.list_tools()` (the upstream's *real* full tool list, fetched live). If `user_query` is present, it builds a `UniversalToolSearcher({server_name: tools})` and runs `searcher.search(user_query, max_results=50)` to **filter to relevant action names only**. Output shape:
```json
{"servers": {"<server>": {"action_count": 12, "actions": ["create_issue","list_issues", …]}}}
```
Critically — **stage 1 returns only `action_count` + a list of action *names*, never schemas.** A 200-tool server collapses to a name list filtered by BM25 relevance. Errors per-server are isolated: `{"error": "Server '…' not found or not connected"}`.

**Stage 2 — `get_action_details`** (`:205-244`). Given `server_name`+`action_name`: re-lists the upstream tools, finds the matching one, and returns the *full schema for that one action only*:
```json
{"server":"<server>","action":{"name":"create_issue","description":"…","inputSchema":{…}}}
```
This is where the expensive `inputSchema` finally enters context — for exactly the one action the agent chose. (Optional `search_documentation` is a parallel path: BM25 search returning `[{name, description, category_name, title?, summary?}]` for fuzzy discovery within a server.)

**Stage 3 — `execute_action`** (`:246-292`). Given `server_name`, `action_name`, and the JSON-string params: it `json.loads` each of `path_params`/`query_params`/`body_schema` (skipping `"{}"`), merges them into one `action_params` dict, then `return await client.call_tool(action_name, action_params)` — the upstream tool result is passed straight through as MCP `ContentBlock`s. Invalid JSON in any param → `TextContent("Error: Invalid JSON in {param_name}")`.

**Stage 4 (recovery) — `handle_auth_failure`** (`:322-360`). `intention="get_auth_url"` returns an instruction payload (`required_fields:{token:…}`); `intention="save_auth_data"` persists credentials. This is invoked when stage 3 fails with an auth error — the agent self-heals by getting an auth URL, having the user authenticate, then retrying `execute_action`.

All non-passthrough results are serialized with `json.dumps(result, separators=(",", ":"))` — compact JSON, no whitespace, to minimize tokens (`:366-375`).

**Reimplementable progressive loader (DESIGNED for Verso, distilled from Strata's exact sequence):**
```python
META_TOOLS = ["discover_actions", "get_action_details", "execute_action", "search_docs", "handle_auth"]

async def discover_actions(user_query: str, namespaces: list[str]) -> dict:
    out = {}
    for ns in namespaces or all_namespaces():
        tools = await client(ns).list_tools()              # live upstream list
        if user_query:
            ranked = bm25_field_search({ns: tools}, user_query, max_results=50)
            names = [t["name"] for t in ranked]            # NAMES ONLY — no schemas
        else:
            names = [t["name"] for t in tools]
        out[ns] = {"action_count": len(names), "actions": names}
    return {"servers": out}                                # → compact json.dumps

async def get_action_details(namespace: str, action: str) -> dict:
    t = next(t for t in await client(namespace).list_tools() if t["name"] == action)
    return {"server": namespace, "action": {"name": t["name"],
            "description": t["description"], "inputSchema": t["inputSchema"]}}  # ONE schema

async def execute_action(namespace: str, action: str, path_params="{}",
                         query_params="{}", body_schema="{}") -> list:
    params = {}
    for raw in (path_params, query_params, body_schema):
        if raw and raw != "{}": params.update(json.loads(raw))  # opaque json-string params
    return await client(namespace).call_tool(action, params)    # passthrough result
```
The entire context-saving comes from `discover_actions` returning **names only** and `execute_action` taking **opaque JSON-string params** — the meta-tool schemas never grow with the catalog.

### The Relevance Ranker — Weighted-Field BM25+ (KNOWN — `utils/shared_search.py`, `utils/bm25_search.py`)

The stage-1 filter and `search_documentation` both use `UniversalToolSearcher`, which is a **field-weighted BM25+** over each tool's metadata. `_build_index` (`shared_search.py:47-151`) flattens every tool into weighted `(field_key, value, weight)` triples:
- weight **30**: `category` (=server name), `operation` (=tool name), `title`, `description`, `summary`, `tag`, `path`
- weight **15**: `method`, each `path_params`/`query_params` name + its description, each `body_schema` property name + description
- weight **5**: `response_schema` property names + descriptions

The BM25 engine (`bm25_search.py`) uses the `bm25s` library with `method="bm25+"` and an English `Stemmer`, **stopwords disabled** (`stopwords=[]`, twice — at index and query — "for better field matching"). Field values are preprocessed (`_preprocess_field_value`, `:154+`): `_`→space, `-`→space, camelCase split — so `create_project`/`getUserProjects` tokenize into word units. Each field is indexed as a *separate* BM25 document, then `search` (`:100-152`) retrieves across all flattened field-docs and **aggregates per original tool by weighted sum**: `doc_score = Σ(field_bm25_score × field_weight)`, sorted descending, top-k. The weighting is the whole trick: a query term hitting the tool *name* or *description* (×30) dominates one hitting a response-field name (×5).

### Lazy Connection Management (KNOWN — `mcp_client_manager.py`)

`MCPClientManager` holds `active_clients: Dict[str, MCPClient]`. `initialize_from_config` connects enabled servers; `get_client(name)` returns the live client; `sync_with_config` (`:139-191`) hot-reconnects on config change (add/remove/reconfigure servers without restart). Stage-1 discovery calls `list_tools()` live against the upstream each time — there is no Strata-side tool-schema cache in open-strata (contrast fastmcp's 300s cache); freshness is favored over latency.

### For Verso

- **Adopt the 4-stage protocol as Verso's deferred-loading default for large tool registries.** Expose a small fixed set of meta-tools — `discover(query, namespaces) → name list only`, `inspect(namespace, action) → one schema`, `execute(namespace, action, json_params)` — and only ever inject the *namespace list* eagerly. Action names enter context at discover, schemas at inspect, nothing before. This is the single most reusable pattern in this note for keeping a 100+ tool registry inside the window.
- **Pass execute-params as an opaque JSON string, not an expanded per-action schema, in the meta-tool.** Strata's `execute_action` keeps its own schema fixed and tiny by taking `path_params`/`query_params`/`body_schema` as JSON strings; the real schema is what the agent saw at `inspect`. This decouples the meta-tool schema from the N action schemas.
- **Use field-weighted BM25+ for tool discovery, with name/description/title at the highest weight.** Verso's `discover` should rank candidate tools by a weighted-field BM25 (weights ~30 for name/desc/title/tags, ~15 for params, ~5 for response fields), stopwords off, with `_`/`-`/camelCase tokenization. This is a keyless, local, fast alternative to embedding-based tool retrieval (and a good baseline to calibrate any embedding ranker against). Cross-ref: cf. Anthropic ToolSearch and Apify's meta-tool (below) for the design-space alternatives.
- **Make auth recovery a first-class stage, not an error.** Strata's `handle_auth_failure` lets the agent get an auth URL and retry in-loop rather than aborting. Verso's executor should, on a tool auth error, surface an auth-URL action the loop can act on (this is the same shape as MCP's `URL_ELICITATION_REQUIRED` and Arcade's interrupt — three converging designs).
- **Serialize meta-tool results as compact JSON (`separators=(",",":")`).** Token-frugal output matters when the agent is calling discover/inspect repeatedly.
- **Decide freshness-vs-cache explicitly.** Strata re-lists upstream tools on every discover (fresh, higher latency); fastmcp caches for 300s. Verso's loader should expose this as a per-namespace knob (default: short TTL cache, `0` for dynamic catalogs).

---

## Arcade.dev

### What It Is

Arcade treats agent tool-calling as an *authorization problem*: every tool can require per-user OAuth, and the agent loop must pause for user consent without breaking. The Engine is closed SaaS (live probe below confirms the whole `/v1/*` surface is behind developer-auth + Cloudflare), but two SDKs are open and authoritative for the contracts: `arcadepy` (the client, Stainless-generated from Arcade's OpenAPI spec) and `arcade-tdk` / `arcade-core` (the Tool Development Kit — the `@tool` decorator and auth models). Tool names use dot-notation: `Gmail.ListEmails`, `Gmail.SendEmail`, `GoogleSearch.Search` (KNOWN — docs + `snake_to_pascal_case` util).

### The 3-Step Interrupt: authorize → poll → execute (KNOWN — `arcadepy/resources/auth.py`, `tools/tools.py`)

The canonical flow when a tool requires auth (`auth.py:209-234`, docstring verbatim):
```py
auth_response = client.auth.start("you@example.com", "github")
auth_response = client.auth.wait_for_completion(auth_response)
```
**Step 1 — authorize.** `tools.authorize(tool_name, user_id, next_uri=…)` → `POST /v1/tools/authorize` (`tools.py:134-182`), or the lower-level `auth.authorize`/`auth.start(user_id, provider, scopes)` → `POST /v1/auth/authorize` (`auth.py:47-119`). Returns an `AuthorizationResponse`. `next_uri` is the post-consent redirect; `user_id` is "Required only when calling with an API key."

**Step 2 — poll / long-poll.** `auth.status(id, wait=…)` → `GET /v1/auth/status` (`auth.py:160-207`). The `wait` param (max **59** seconds) is a server-side long-poll: "does not respond until either the auth status becomes completed or the timeout is reached." `wait_for_completion(auth_response_or_id)` (`:209-234`) is the convenience loop:
```py
while auth_response.status != "completed":
    auth_response = self.status(id=auth_id_val, wait=_DEFAULT_LONGPOLL_WAIT_TIME)  # 45
return auth_response
```
`_DEFAULT_LONGPOLL_WAIT_TIME = 45` (`:24`) — long-poll in 45s windows until `status=="completed"`. This is a blocking, resumable interrupt: each `status` call hangs up to 45s server-side, then the client re-polls.

**Step 3 — execute.** `tools.execute(tool_name, input, user_id, tool_version, run_at)` → `POST /v1/tools/execute` (`tools.py:184-240`). `input` is `Dict[str,object]` ("JSON input to the tool"). `run_at` (ISO 8601) schedules deferred execution; absent = run immediately.

### The Interrupt Schema — Auth Embedded in the Execute Response (KNOWN — `types/execute_tool_response.py`, `shared/authorization_response.py`)

This is the highest-value finding and the live-probe target the brief asked for. Arcade does NOT use a separate error code for "needs auth" — **the `tools/execute` response itself carries the interrupt**. `ExecuteToolResponse.output` is an `Output` with three mutually-relevant fields:
```python
class Output(BaseModel):
    authorization: Optional[AuthorizationResponse] = None   # ← the interrupt
    error: Optional[OutputError] = None
    logs: Optional[List[OutputLog]] = None
    value: Optional[object] = None                          # ← the success value
```
When a tool needs auth, `output.authorization` is populated with an **`AuthorizationResponse`** (`authorization_response.py`):
```python
class AuthorizationResponse(BaseModel):
    id: Optional[str]                    # the auth id to poll on /v1/auth/status
    context: Optional[AuthorizationContext]   # { token, user_info } once completed
    provider_id: Optional[str]
    scopes: Optional[List[str]]
    status: Optional[Literal["not_started","pending","completed","failed"]]
    url: Optional[str]                   # the consent URL to send the user to
    user_id: Optional[str]
```
So the interrupt contract is: call `execute` → if `output.authorization.status != "completed"`, the loop must surface `output.authorization.url` to the user, poll `auth.status(id=output.authorization.id, wait=45)` until `completed`, then re-call `execute`. The `AuthorizationContext.token` (`authorization_context.py`: `{token, user_info}`) is the resolved per-user credential after consent.

**Reimplementable auth-interrupt loop (DESIGNED for Verso, from Arcade's exact contract):**
```python
async def call_with_auth_interrupt(tool_name, user_id, inp, *, surface_to_user, checkpoint):
    resp = await engine.execute(tool_name=tool_name, user_id=user_id, input=inp)
    auth = resp.output.authorization
    if auth and auth.status != "completed":               # INTERRUPT: consent needed
        surface_to_user(auth.url)                          # HITL: show the OAuth URL
        checkpoint({"auth_id": auth.id, "tool": tool_name, "input": inp})  # resumable token
        while auth.status != "completed":
            auth = await engine.auth_status(id=auth.id, wait=45)  # long-poll 45s windows
            if auth.status == "failed":
                return ToolError(kind="UPSTREAM_RUNTIME_AUTH_ERROR", can_retry=False)
        resp = await engine.execute(tool_name=tool_name, user_id=user_id, input=inp)  # resume
    err = resp.output.error
    if err:
        return ToolError(kind=err.kind, can_retry=err.can_retry,
                         retry_after_ms=err.retry_after_ms,
                         prompt_content=err.additional_prompt_content)  # → back to LLM
    return resp.output.value
```
The `{auth_id, tool, input}` checkpoint is the resumable interrupt token — exactly what Verso's checkpoint/resume contract needs for auth-gated tools.

**Live probe (2026-06-05, KNOWN):** `POST https://api.arcade.dev/v1/tools/execute` with `{"tool_name":"Gmail.ListEmails","user_id":"…","input":{}}` and no API key → `HTTP 401 {"name":"invalid_authorization","message":"Missing Authorization header"}`. Same for `/v1/tools/authorize` and `/v1/auth/status`. Headers: `server: cloudflare`, `cf-ray`, `x-request-id`, `x-content-type-options: nosniff`, `x-frame-options: DENY`. The Engine API is fully developer-auth-gated behind Cloudflare; the *interrupt schema* is therefore recovered from the SDK models (authoritative — Stainless-generated from the OpenAPI spec), not from a live unauthenticated call.

### Three-Tier Error Taxonomy with `can_retry` (KNOWN — `OutputError`)

`OutputError` (`execute_tool_response.py`) is a fully-enumerated error model — exactly the categorized retry contract Verso needs:
```python
class OutputError(BaseModel):
    can_retry: bool                 # ← the retry routing bit
    kind: Literal[                  # the error taxonomy
        "TOOLKIT_LOAD_FAILED", "TOOL_DEFINITION_BAD_DEFINITION",
        "TOOL_DEFINITION_BAD_INPUT_SCHEMA", "TOOL_DEFINITION_BAD_OUTPUT_SCHEMA",
        "TOOL_REQUIREMENTS_NOT_MET",           # auth/secrets missing
        "TOOL_RUNTIME_BAD_INPUT_VALUE", "TOOL_RUNTIME_BAD_OUTPUT_VALUE",
        "TOOL_RUNTIME_RETRY", "TOOL_RUNTIME_CONTEXT_REQUIRED", "TOOL_RUNTIME_FATAL",
        "UPSTREAM_RUNTIME_BAD_REQUEST", "UPSTREAM_RUNTIME_AUTH_ERROR",
        "UPSTREAM_RUNTIME_NOT_FOUND", "UPSTREAM_RUNTIME_VALIDATION_ERROR",
        "UPSTREAM_RUNTIME_RATE_LIMIT", "UPSTREAM_RUNTIME_SERVER_ERROR",
        "UPSTREAM_RUNTIME_UNMAPPED", "UNKNOWN"]
    message: str
    additional_prompt_content: Optional[str]   # text fed back to the LLM to self-correct
    developer_message: Optional[str]
    retry_after_ms: Optional[int]              # backoff hint (e.g. for RATE_LIMIT)
    status_code: Optional[int]
    stacktrace: Optional[str]
```
Note `additional_prompt_content` — error text *purpose-built to be appended to the model's context* so it can retry intelligently. `retry_after_ms` pairs with `can_retry` for backoff. This separates the tool/runtime/upstream layers (the three tiers) and tags each with a machine-readable retryability bit. (Cf. fastmcp's hand-coded 429/timeout cases and the MCP `isError` split — Arcade's model is the most complete of the three.)

### The `@tool` Decorator + Per-Tool Auth Declaration (KNOWN — `arcade_tdk/tool.py`, `arcade_core/auth.py`)

`@tool(requires_auth=…, requires_secrets=…, adapters=…)` (`tool.py:133-184`): attaches `__tool_name__` (PascalCased from the function name via `snake_to_pascal_case`), `__tool_description__` (from `desc` or the cleaned docstring), `__tool_requires_auth__`, `__tool_requires_secrets__`. Crucially it **wraps the function in an error-handling shim** (`func_with_error_handling`, `:156-180`): any exception that isn't already a `ToolRuntimeError` is run through an *adapter chain* (`_build_adapter_chain(adapters, requires_auth)`) and re-raised as an Arcade error — this is how arbitrary Python exceptions map onto the `OutputError.kind` taxonomy (provider-specific adapters live in `arcade_tdk/providers/{google,microsoft,http,graphql,slack}/error_adapter.py`).

`requires_auth` takes a `ToolAuthorization` (`arcade_core/auth.py`):
```python
class ToolAuthorization(BaseModel):
    provider_id: Optional[str]          # e.g. "github", "google"
    provider_type: AuthProviderType     # oauth2 | …
    id: Optional[str]
    scopes: Optional[list[str]]
class OAuth2(ToolAuthorization): ...    # provider_type=oauth2
# + 20+ provider subclasses: Google(provider_id="google"), GitHub("github"),
#   Slack, Microsoft, Notion, Linear, X, Zoom, … each just fixes provider_id
```
So a tool declares `@tool(requires_auth=Google(scopes=["gmail.readonly"]))` and the Engine knows which OAuth provider + scopes to interrupt for.

### For Verso

- **Model the auth interrupt as a value in the tool result, not a thrown error.** Arcade's design — `execute` returns `output.authorization{status,url,id}` when consent is needed — is the cleanest fit for a ReAct loop: the loop inspects the result, and if `status != "completed"` it surfaces `url` to the user (HITL pause), polls on `id`, and re-executes. This becomes Verso's checkpoint/resume contract for auth-gated tools: the `(auth_id, url, status)` triple is the resumable interrupt token. (This is the same shape as MCP's `URL_ELICITATION_REQUIRED` and Strata's `handle_auth_failure` — three converging designs; Arcade's is the most field-tested.)
- **Long-poll, don't busy-poll.** Verso's auth-wait should use a server-side long-poll window (Arcade: 45s default, 59s max) and loop until `completed` — not tight client polling. The interrupt is *blocking-but-resumable*: each poll hangs server-side, so the agent can checkpoint between windows.
- **Adopt a categorized `OutputError` with `can_retry` + `retry_after_ms` + `additional_prompt_content`.** This is the concrete `@tool(on_error=…)` contract fastmcp lacks. Verso's tool error type should carry: a `kind` enum split across tool-definition / tool-runtime / upstream-runtime tiers, a `can_retry` bool the executor reads to decide retry, a `retry_after_ms` backoff hint, and an `additional_prompt_content` string injected into the model's context so it self-corrects. `TOOL_REQUIREMENTS_NOT_MET` / `UPSTREAM_RUNTIME_AUTH_ERROR` should route to the auth-interrupt path, not a retry.
- **Per-tool auth declaration via the decorator.** `@tool(requires_auth=Provider(scopes=[…]))` is the ergonomic seam: the tool author declares the provider + scopes; the framework owns the OAuth dance. Verso's `@tool` should accept an optional `requires_auth` carrying `(provider_id, scopes)` so the executor can pre-empt the interrupt (request consent before the first call) rather than discovering it via an error.
- **Wrap tool bodies in an error-adapter shim.** Arcade's `@tool` wrapping that maps raw exceptions to the categorized taxonomy via provider-specific adapters is worth porting: Verso should normalize `httpx`/provider exceptions into its error categories at the tool boundary, so the executor never sees a raw stack trace it can't classify.

---

## Nango

### What It Is

Nango is an open-source, self-hostable integration runtime (TypeScript monorepo, ~30 packages). Three tiers: **Auth** (OAuth/API-key storage + refresh across 800+ APIs), **Proxy** (authenticated pass-through HTTP), **Functions** (your TS integration code — `actions` and `syncs` — deployed to Nango's runner). The architecturally interesting bit for Verso is that **a single Function definition deploys as both a scheduled job AND an MCP tool** from the same compiled artifact. (Composio is already covered in `infra-retrieval-tools.md`; Nango is the code-first, you-own-the-credential-DB contrast.)

### Function → (scheduled job + MCP tool) Dual Deploy (KNOWN — `packages/cli/lib/zeroYaml/`, `packages/server/lib/controllers/mcp/`)

At **deploy time** the CLI compiles each Function's Zod schema to JSON Schema once and stores it on the DB record. `packages/cli/lib/zeroYaml/json-schema.ts:10` uses `z.toJSONSchema(schema, {...})` (Zod 4's native converter) — with a custom override mapping date types to `{type:"string", format:"date-time"}` (`:16-17`) and stripping the `$schema` key (`:23`). `deploy.ts` writes the result onto the sync/action record as `models_json_schema: action.json_schema` (`:227, :266`). So the same `DBSyncConfig` carries: `sync_name`, `type` (`action`|`sync`), `input` (the input model name), `models_json_schema` (the compiled `{definitions:{…}}`), `endpoints`, `metadata`. A `sync` additionally has a schedule/frequency (scheduled job); an `action` is on-demand.

At **runtime** the MCP server derives tool schemas from that exact stored artifact. `mcp/server.ts:66-90` — `actionToTool(action)`:
```ts
let inputSchema = action.input ? action.models_json_schema?.definitions?.[action.input] : undefined;
if (inputSchema && inputSchema.type === 'null') inputSchema = undefined;
if (inputSchema && inputSchema.type !== 'object') return null;   // skip non-object inputs
return {
  name: action.sync_name,
  inputSchema: { type:'object', properties: inputSchema?.properties, required: inputSchema?.required, description: inputSchema?.description },
  description: action.metadata.description || action.sync_name
};
```
`ListToolsRequestSchema` (`:44-56`) flatMaps over the connection's actions, skipping disabled ones and any whose input schema isn't an object. **`CallToolRequestSchema` (`callToolRequestHandler`, `:92-169`)** routes the tool call through the *same orchestrator that runs scheduled syncs*: `getOrchestrator().triggerAction({ accountId, connection, actionName: action.sync_name, input, async:false, retryMax:3, maxConcurrency: ACTION_ENVIRONMENT_MAX_CONCURRENCY, logCtx })`. The result is wrapped as MCP content: `{ content:[{type:'text', text: JSON.stringify(actionResponse.value.data, null, 2)}] }` on success; on failure it `throw`s `JSON.stringify(error)` (→ JSON-RPC error). The same execution path, retry policy (`retryMax:3`), and concurrency cap serve both the cron-scheduled invocation and the MCP tool call — one codebase, two deploy surfaces.

### MCP Connection Scoping (KNOWN — `mcp/mcp.ts`)

The MCP edge is per-connection and uses **Streamable HTTP**. `mcp.ts`: headers `connection-id` + `provider-config-key` select the connection (`:31-34` → `connectionService.getConnection(...)`); a fresh `StreamableHTTPServerTransport` + MCP `Server` are created per request (`:50`), wired to the connection's actions, and torn down on `res.close` (`:52-54`). `server.connect(transport)` then `transport.handleRequest(req, res, req.body)`. A GET to the MCP endpoint returns **405** (`:64`) — stateless POST-only, no server-initiated SSE stream. So tool *scope* = the actions enabled for one (connection, integration) pair; the credential isolation is the connection lookup, not a header forwarded to a third party (contrast Pipedream's `external_user_id` and fastmcp's header-forwarding).

### Function Sandbox Isolation (KNOWN — `packages/runner/lib/exec.ts`)

Nango Functions are arbitrary user TS, so they run in a hardened Node `vm` sandbox (`exec.ts:88-130`) — a model for Verso if it ever runs untrusted tool code in-process. The sandbox: an **allowlisted `require`** (`:101-118` — only `url`, `crypto`, `zod`, `botbuilder`, `soap`, `unzipper`; anything else throws `Module '…' is not allowed`); a **no-op `console` Proxy** (`:95-100`); `constructor: undefined`; an exposed-globals allowlist (`Buffer`, `setTimeout`, `Error`, `URL`, `URLSearchParams`); **`Object.setPrototypeOf(sandbox, null)`** (`:125`) to break prototype-chain escapes; and `vm.createContext(sandbox, {codeGeneration:{strings:false}})` (`:127-129`) which **disables `eval`/`new Function`** inside the sandbox. (The `lambda-runner` package is the alternative isolation tier for heavier workloads.) The runner monitor (`monitor.ts:142-162`) idles out after 10s, backing off to 2 min after a successful idle.

### Auth & Proxy Tiers (KNOWN — `proxy/allProxy.ts`)

The Proxy tier (`allProxy.ts`) is the credential-injection seam decoupled from execution: it `refreshOrTestCredentials` (`:18`) for the connection, then forwards the request to the provider's base URL, injecting the stored/refreshed credentials. Knobs surfaced as headers: `retries` (default 0, `:48`), `base-url-override` (gated by a denylist, `:78-79`), `forward-headers-on-redirect` (`:55, :96-97`). This is the "authenticated pass-through" — the agent (or a Function) calls Nango's Proxy with a connection ID and Nango handles the OAuth refresh + credential injection transparently. The three tiers compose: **Auth stores creds → Proxy injects them on pass-through → Functions wrap multi-step logic and are exposed as both schedules and MCP tools.**

### For Verso

- **One tool definition, multiple deploy surfaces.** Nango's pattern — compile the schema once at deploy, then drive both a scheduled runner and an MCP `callTool` from the same record through one orchestrator with one retry/concurrency policy — is the model for Verso's "dual-mode (in-memory vs event-sourced) tool execution." A Verso `@tool` should be registerable as an in-process function, a scheduled task, and an exported MCP tool without rewriting it; the schema and execution path are shared.
- **Compile the schema at deploy/registration, store it, derive the MCP `inputSchema` from the stored artifact.** Don't re-introspect at every `tools/list`. Nango stores `models_json_schema.definitions[input]` and the MCP layer just reshapes it (`type:object`, lift `properties`/`required`/`description`). Skip non-object input schemas (MCP requires object roots — same rule as fastmcp and the spec).
- **Separate credential storage from execution (the Proxy tier).** Verso's pluggable auth edge should model "inject refreshed credentials on a pass-through request" as a distinct capability from "run a tool" — so a tool body can make authenticated calls via the auth edge without owning the OAuth refresh. `retries`/`base-url-override`/`forward-headers-on-redirect` as per-request knobs are a reasonable surface.
- **Scope tools by (connection, integration), create the MCP server per-request, tear down on close.** Nango's per-connection ephemeral MCP server + StreamableHTTP POST-only (GET→405) is a clean stateless pattern for a multi-tenant tool edge where each tenant sees only their enabled actions.
- **If Verso ever runs untrusted tool code in-process, copy Nango's `vm` hardening.** Allowlisted `require`, null sandbox prototype, `codeGeneration.strings:false` (no `eval`/`new Function`), no-op console, exposed-globals allowlist, and an idle-timeout monitor. This is the lightweight isolation tier (Verso's heavier tier should be a separate process / microVM, cf. `infra-serving.md` Together's Firecracker code-interpreter).

---

## Pipedream Connect

### What It Is

Pipedream Connect is managed MCP infrastructure exposing 10,000+ tools across 3,000+ APIs. The engine is closed SaaS (`remote.mcp.pipedream.net`, behind an Express gateway, project-JWT-gated — live probe below); the open `mcp-chat` repo is the reference agent. The Verso-relevant mechanism is **per-user credential isolation via `external_user_id` + lazy tool scoping by app slug**, so a 10k-tool registry is sub-selected per connection without loading everything.

### The Header / URL Scoping Contract (KNOWN — `mcp-chat/lib/pd-backend-client.ts`, `mods/mcp-client.ts`; URL pattern from docs)

Developer auth is OAuth `client_credentials` → bearer token: `pdHeaders(exuid)` (`pd-backend-client.ts:11-22`) returns:
```ts
{
  Authorization: `Bearer ${accessToken}`,        // dev token via client_credentials
  "x-pd-project-id": PIPEDREAM_PROJECT_ID,
  "x-pd-environment": PIPEDREAM_PROJECT_ENVIRONMENT,   // development | production
  "x-pd-external-user-id": exuid,                 // ← per-end-user credential scope
  "x-pd-tool-mode": "full-config",
  "x-pd-app-discovery": "true",                   // dynamic discovery of all apps
}
```
The **`external_user_id`** is the whole multi-tenancy story: the developer authenticates once (project bearer token), but `x-pd-external-user-id` scopes every tool call to *that end-user's* stored OAuth credentials. The transport adds `x-pd-mcp-chat-id` (`mcp-client.ts:154`) for stateless session restoration (the server is stateless; chat state is keyed off that header).

**Lazy scoping by app slug is a path parameter, not a query string** (KNOWN — Pipedream MCP README, verbatim): two routing patterns — **app-specific** `/{external_user_id}/{app}` (e.g. `…/{exuid}/slack` → only Slack's tools surface in `tools/list`) and **dynamic** `/{external_user_id}` (the experimental mode powering chat.pipedream.com → all apps discoverable). So *which* sub-registry of the 10k tools the agent sees is selected **at connection-URL time**: pin an app slug → small fixed toolset; omit it + `x-pd-app-discovery:true` → the agent navigates the full catalog. This is the connection-time equivalent of Strata's runtime discover stage and Apify's pinned-vs-dynamic switch.

`mcp-chat` itself uses dynamic mode (`MCP_BASE_URL = "https://remote.mcp.pipedream.net"`, `mcp-client.ts:29`) and converts MCP tools to executable tools with `jsonSchema(mcpTool.inputSchema)` + a **180_000 ms (3 min) per-tool execute timeout** (`mcp-client.ts:233-237`). It caches the converted tool set (`toolsCache`, `:122,209-217`).

**Live probe (2026-06-05, KNOWN):** `POST https://remote.mcp.pipedream.net/v3` (and `?app=gmail`) with an `initialize` request and no JWT → `HTTP 401 {"jsonrpc":"2.0","error":{"code":-32001,"message":"Unauthorized. A valid API JWT with project credentials is required."},"id":null}`. Header `x-powered-by: Express`. The error is a **JSON-RPC error (-32001)**, not an `isError` result — auth-missing is correctly modeled as a protocol error (consistent with the MCP spec's "errors in finding/authorizing the tool are protocol errors" rule). The implementation-specific code `-32001` sits in the `[-32000,-32099]` MCP range.

### For Verso

- **`external_user_id` is the minimal multi-tenant tool-scoping primitive.** Verso's tool edge should accept a per-request end-user identifier that selects that user's stored credentials, while the *developer/app* authenticates once. This is simpler than per-user OAuth tokens at the edge: one developer token + a user-id header, credentials resolved server-side.
- **Select the tool sub-registry at connection time, not load-time.** Pipedream's path-param app slug (`/{user}/{app}` vs `/{user}`) shows the cleanest lazy-scoping knob: pinning a namespace yields a small fixed toolset; omitting it enables full discovery. Verso's MCP edge should let the *connection URL/config* pick a namespace subset before any `tools/list`, complementing the runtime discover stage (Strata) — two layers of deferral.
- **Model auth-missing as a JSON-RPC `-32001` protocol error, success/logical-failure as `isError`.** Pipedream's `-32001` confirms the spec split in production. Verso's edge should return implementation-range protocol errors for connection/auth problems and reserve `isError:true` for tool-ran-but-failed.
- **Cap per-tool execution (Pipedream: 3 min) and cache the converted tool set.** A generous-but-bounded execute timeout plus a tool-set cache per session is the baseline; pair with the auth-interrupt path for tools needing consent.

---

## Toolhouse

### What It Is

Toolhouse is cloud BaaS for agent tools: tools (RAG, code exec, browser, web search) run remotely in Toolhouse's cloud. The contract is two methods — `get_tools()` fetches schemas, `run_tools()` executes calls — plus local-tool registration. Engine is closed; SDK (`toolhouse==1.4.0`) is open and is the full contract. Base URL `https://api.toolhouse.ai/v1` (`net/environment.py:13`).

### The Two-Method Contract (KNOWN — `toolhouse/sdk.py`, `services/tools.py`)

**`get_tools(bundle="default")`** (`sdk.py:161-170`): builds `GetToolsRequest(provider, metadata, bundle)` → `services/tools.py:16-24` POSTs to **`/get_tools`** and returns tool schemas **in the provider's native format** (OpenAI function-calling format or Anthropic tools format, depending on the SDK's `provider`). A LlamaIndex provider gets a further conversion. So the returned schemas are dropped straight into the LLM call (`client.chat.completions.create(tools=th.get_tools())`). The `bundle` is a server-side named grouping of tools — `get_tools(bundle="email")` returns only that bundle's tools; default is `"default"`. This is the simplest deferred-loading knob in this note: a single string selects a curated subset (coarser than Strata's 4-stage, finer than "all tools").

**`run_tools(response, append=True)`** (`sdk.py:172-233`): takes the *raw LLM response* and executes whatever tool calls it contains. Provider-branched:
- *OpenAI* (`:189-217`): if `finish_reason != "tool_calls"` → return `[]` (nothing to run). Strips `audio`/`refusal` None fields for cross-model compat. For each `tool_call`: if the name is in the locally-registered set → run in-process; else → `RunToolsRequest(tool, provider, metadata, bundle)` → POST `/run_tools` (`services/tools.py:34-44`) and append `run_response.content` as a tool message.
- *Anthropic* (`:219-233`): mirror logic keyed on `stop_reason == "tool_use"`, building a `{"role":"user","content":[…]}` message with `tool_result` blocks.

The key design point: **`run_tools` consumes the provider's response object directly and returns ready-to-append messages** — the SDK owns the parse-tool-calls → execute → format-result loop, so the agent only does two calls (`get_tools` before the LLM call, `run_tools` after). Streaming responses are first collapsed via `stream_to_chat_completion` (`:190-193`).

### Local / Cloud Tool Merge (KNOWN — `services/local_tools.py`)

`register_local_tool(local_tool)` (`sdk.py:101-103` → `local_tools.py:24-38`) is a decorator keyed by an **explicit string name** (`self.local_tools[local_tool] = wrapper`, `:36`), not the function's `__name__` — so registration name and function name are decoupled. The wrapper enforces the function returns a `str` (else `TypeError`, `:31-34`). Notably, **local tools carry NO schema** — Toolhouse's local tools are execute-only; the *cloud* `get_tools` supplies all schemas, and a local tool's name must match a schema the cloud returned (or be a purely-local convention the LLM already knows). `_run_local_tools` (`:40-48`) splats args: Anthropic `tool.input` dict, OpenAI `json.loads(tool.function.arguments)`. Results are wrapped per-provider — `AnthropicToolResponse(type="tool_result", content, tool_use_id)` or `OpenAIToolResponse(tool_call_id, name, content, role="tool")` (`:50-67`). At `run_tools` time every tool call checks `get_registered_tools()` first — local in-process, else cloud `/run_tools`. This is the cloud+local merge: union namespace, name-based dispatch, local precedence. (Bundles only affect the *cloud* set returned by `get_tools`.) The architectural lesson: the *schema source* and the *execution location* are independent axes — a tool's schema can come from the cloud while its execution is local.

### For Verso

- **The `get_tools()`/`run_tools(response)` split is the minimum viable adapter — Verso must beat it on ergonomics, not lose to it.** The whole agent integration is: `tools = adapter.get_tools()`; call LLM; `messages += adapter.run_tools(llm_response)`. Verso's executor should expose an equivalent two-call surface (`tools_for(scope)` / `run(llm_response) -> messages`) so swapping the tool backend (in-process, MCP, cloud) is transparent to the loop. The fact that `run_tools` takes the *raw provider response* and returns *append-ready messages* is the right abstraction boundary.
- **Name-based local-vs-remote dispatch with local precedence.** Verso mixes `@tool` functions (local) and MCP-sourced tools (remote); Toolhouse's pattern — check the registered-local set first, fall through to remote — is the correct merge. The union is one namespace; dispatch is by name.
- **A `bundle` string is a cheap middle-ground deferred-loading knob.** Between "all tools" and Strata's full 4-stage discovery sits "named curated subset." Verso's registry should support a coarse `scope`/`bundle` selector (return only the tools tagged for this task) as a low-effort default before reaching for progressive discovery.
- **Constrain local tool return types.** Toolhouse forces local tools to return `str`; Verso should at minimum normalize tool returns to MCP `ContentBlock`s at the boundary (cf. fastmcp's `convert_result`) so the loop never has to special-case tool output shapes.

---

## Smithery

### What It Is

Smithery is an MCP registry + hosting platform (7,000+ servers). The open `smithery-ai/cli` (TypeScript) is the reference for *runtime tool discovery* — how an agent finds a server, resolves its connection config, and searches its tools. The registry API (`registry.smithery.ai`) is queryable without auth (live probe below).

### Registry Query (KNOWN — live probe + `src/lib/registry.ts`)

**Live probe (2026-06-05):** `GET https://registry.smithery.ai/servers?q=github&pageSize=2` → `HTTP 200`, schema:
```json
{"servers":[{"id":"…","qualifiedName":"github","namespace":"github","slug":"",
  "displayName":"GitHub","description":"…","iconUrl":"…","verified":true,
  "useCount":3991,"remote":true,"isDeployed":true,"bySmithery":true,
  "score":0.0573}, …],
 "pagination":{"currentPage":1,"pageSize":2,"totalPages":74,"totalCount":148}}
```
So a registry server entry carries: `qualifiedName` (the addressing key, `namespace/slug`), `verified`, `useCount` (popularity signal), `remote`/`isDeployed` (hosted vs self-host), and a `score` (relevance rank for the query). Pagination is page/pageSize/totalCount. This is the discovery surface: query by intent string → ranked server list.

`resolveServer({namespace, serverName})` (`registry.ts:47-121`) calls the Smithery SDK `servers.get("namespace/serverName")`, then **picks the first connection** from `result.connections[]` (`:97-105`) and returns `{server, connection}`. So a server can advertise multiple connection options; the CLI defaults to the first. `searchServers(term, apiKey, {verified, namespace, pageSize, page})` (`:129+`) is the programmatic search.

### Local Connection Config Format (KNOWN — `src/types/registry.ts`)

The on-disk config Verso would persist is `MCPConfig = { mcpServers: Record<string, ConfiguredServer> }` (`:29-31`) — the same `mcpServers` key Claude Desktop/Cursor use. A `ConfiguredServer` is a discriminated union:
- **stdio** (`StdioConnectionSchema`, `:34-43`): `{ command, args?, env? }` — spawn a local process.
- **streamable-http** (`:46-54`): `{ type:"http", url, headers? }` — connect to a remote MCP endpoint, with optional headers (where the auth token lives).

For Smithery-hosted servers the URL is `https://server.smithery.ai/{qualifiedName}/mcp` (`lib/client-config-io.ts:654,663`). So a resolved Smithery server becomes an `mcpServers[name] = {type:"http", url, headers:{Authorization:…}}` entry — the connection config is portable across any MCP client.

### Tool Search Across Connected Servers (KNOWN — `src/commands/mcp/search.ts`, `api.ts`)

`findTools(query, {connection, match, …})` (`search.ts:173+`) connects to a server, `listToolsForConnection(conn)` (across all connections via `Promise.allSettled`, `:232-234`), and filters with three **match modes** (`:20-21, 68-103`): `fuzzy` (default when a query is present — uses a search index), `substring`, `exact`. So "search tools by intent" is a *client-side* fuzzy match over the connected server's `tools/list`, not a server-side semantic search — a simpler design than Strata's BM25 (and notably it requires connecting first, then searching the live tool list). `callTool(connection, tool, args)` (`call.ts:62-84`, `api.ts:169`) executes.

### Server vs Skill Distinction (KNOWN — `src/lib/skill-install.ts`)

Smithery distinguishes **servers** (protocol-level MCP tool providers, `namespace/slug`, addressed at `server.smithery.ai/{qualifiedName}/mcp`) from **skills** (higher-level curated bundles at `smithery.ai/skills/{namespace}/{slug}`). The user-facing `smithery skill` command was *removed* (SMI-1682) in favor of the upstream `npx skills` installer — install attribution is tracked server-side when the skill is fetched. So the CLI now only manages servers; skills are a separate, higher-altitude artifact installed by a different tool.

### For Verso

- **Use the registry shape as Verso's runtime tool-discovery contract.** `qualifiedName` + `verified` + `useCount` + `score` + pagination is the right metadata for an agent to pick a server at runtime. Verso's tool registry plug-point should accept a registry adapter that returns this shape for an intent query, then resolve `qualifiedName` → connection config.
- **Persist connections as the portable `mcpServers` discriminated union (stdio | streamable-http).** This is the de-facto standard config format; Verso should read/write it so its tool connections interop with Claude Desktop/Cursor/etc. Auth tokens live in the `headers` of the http variant.
- **A resolved server can advertise multiple connections — pick deterministically (Smithery: first).** Verso should make this an explicit policy (prefer streamable-http remote, fall back to stdio) rather than blindly taking `[0]`.
- **Decide where tool search runs.** Smithery searches the *live* tool list client-side after connecting (fuzzy/substring/exact); Strata searches server-side with BM25 *before* injecting schemas. Verso's deferred loader should prefer the Strata model (rank before connect/inject) for large registries, but the Smithery model (connect-then-fuzzy-filter) is fine for a handful of pinned servers.
- **Separate "server" (protocol provider) from "skill/bundle" (curated namespace) in Verso's mental model.** This maps to Verso's `@tool` (local) vs MCP server (remote protocol) vs curated tool bundle — three distinct registry kinds, as Smithery, Toolhouse (bundles), and Strata (servers) each show.

---

## Apify MCP Server

### What It Is

Apify's MCP server (`apify/apify-mcp-server`, TypeScript) exposes 5,000+ Actors (scrapers/automation) as MCP tools. It is the clearest production example of the **dynamic meta-tool vs pinned-schema** tradeoff at scale — the same problem as Verso's deferred loading: 5,000 tools is too many to inject, so you either expose a single `call-actor` meta-tool that routes to any Actor, or you let the agent *pin* a handful of Actors and surface their full schemas.

### `call-actor` Meta-Tool vs `add-actor` Pinning (KNOWN — `tools/core/call_actor_common.ts`, `tools/common/add_actor.ts`, `const.ts`)

Tool names (`const.ts:26-28`): `ACTOR_ADD='add-actor'`, `ACTOR_CALL='call-actor'`, `ACTOR_CALL_WIDGET='call-actor-widget'`.

**`call-actor` — the dynamic meta-tool** (`call_actor_common.ts:231-256`). Its schema (`callActorArgs`, compiled via `z.toJSONSchema`) is tiny and *fixed* regardless of which Actor runs:
```ts
callActorArgs = z.object({
  actor: z.string().describe("…apify/instagram-scraper…"),     // which Actor (and optional :tool)
  input: z.object({}).passthrough().describe("The input JSON to pass to the Actor. Required."),
  waitSecs: z.number().min(0).max(45).default(30)              // 0–45, default 30
    .describe("Returns with current run status if not terminal within waitSecs."),
})
```
The decisive design choice: `input` is `z.object({}).passthrough()` — **an opaque any-object**, so the meta-tool's schema does NOT enumerate the chosen Actor's parameters. The agent supplies the Actor name + a free-form input JSON. The description (`:52`) tells the LLM: *"Use this when a dedicated tool is not available or when you want to run any Actor dynamically… especially useful if your client does not support dynamic tool registration."* Annotations mark it `destructiveHint:true, idempotentHint:false, openWorldHint:true`; `execution.taskSupport:'optional'` (long-running). Wait contract: default 30s, max 45s, task-mode waits until terminal (`actor_executor.ts:13,26-27`). This is context-efficient (one tool, fixed small schema for the whole catalog) but gives the LLM *less signal* — it must know the Actor's input shape itself or call `fetch-actor-details` first.

**`add-actor` — the pinning path** (`add_actor.ts:16-72`). Schema: `{actor: string}`. Behavior: if the Actor isn't already loaded, `apifyMcpServer.loadActorsAsTools([actor], client)` fetches its definition, **prunes it** (`build.ts:72-92` → `{id, actorFullName, input:{type, properties}, description, defaultRunOptions, …}` — the Actor's *real* input schema becomes the tool's `inputSchema`), registers it as a first-class pinned tool, then fires **`notifications/tools/list_changed`** (`add_actor.ts:64`). So `add-actor` converts the opaque meta-tool into a concrete tool with the full expanded schema the LLM can see — the inverse of `call-actor`'s opacity. (Description, `add_actor.ts:20`: "This does not execute the Actor; it only registers it so it can be called later.")

### The Mode Switch (KNOWN — `mcp/server.ts`, `stdio.ts`, `server_card.ts`)

Whether `add-actor` / dynamic registration is available is gated two ways:
1. **Config flag** `enableAddingActors` (`stdio.ts:156`, env `ENABLE_ADDING_ACTORS`) — opt-in dynamic actor loading.
2. **Client capability** — the server advertises `tools.listChanged: true` (`server_card.ts:29`, `server.ts:242`) and `tools:'dynamic'` (`server_card.ts:35`). The `initialize` handler resolves the server *mode* from the *client's* capabilities (`server.ts:323-338`, `resolveServerMode('auto', clientSupportsUi)`) — set-once per connection. So a client that supports `tools/list_changed` notifications gets the progressive (pin-on-demand) experience; a client that doesn't falls back to the static `call-actor` meta-tool. This is the key insight for Verso: **the deferred loader must degrade gracefully for clients that can't handle dynamic tool-list changes** — keep a meta-tool fallback. Actor definitions are cached `ACTOR_CACHE_TTL_SECS = 30*60` (30 min, `const.ts:68`).

### For Verso

- **Offer both a meta-tool and a pin-on-demand path; pick by client capability.** Apify's two modes are the two ends of Verso's deferred-loading design space. The meta-tool (`run(tool_id, opaque_input, wait)`) works for any client and keeps context flat; the pinning path (`add(tool_id)` → expand schema → `notifications/tools/list_changed`) gives the LLM full parameter signal. Verso should resolve which to use from the client's `tools.listChanged` capability at `initialize`, defaulting to the meta-tool when notifications aren't supported.
- **The opaque-input meta-tool schema is the trick that keeps the catalog flat.** `input: passthrough-object` (Apify) ≡ Strata's `execute_action(json_string params)` — both decouple the meta-tool's own schema from the N target schemas. Verso's universal `execute` tool should take an opaque input object, not a union of all tool schemas.
- **`add-X` must fire `notifications/tools/list_changed`.** When Verso's loader pins a new tool, it must emit the MCP list-changed notification so the client re-fetches `tools/list`. This is the wire mechanism that makes progressive loading work for capable clients.
- **Cache fetched tool definitions with a TTL (Apify: 30 min).** Fetching+pruning an upstream tool's full schema is expensive; cache it. (Compare fastmcp's 300s component cache and Strata's no-cache freshness — 30 min is the slow-changing-catalog end.)
- **Carry `destructiveHint`/`idempotentHint` on meta-tool-routed calls and a bounded `waitSecs` (Apify: 0–45, default 30).** A meta-tool that can run *anything* is inherently `openWorldHint:true, destructiveHint:true` — Verso's planner should treat such calls with more caution (no blind auto-retry) and bound their wait.

---

## mcp-use

### What It Is

mcp-use (`mcp-use/mcp-use`, Python ≥3.11, now a multi-lang monorepo under `libraries/python/`) is the most direct existing Python analog to Verso: an agent loop that consumes MCP tools. Reading it is most valuable for *what not to copy* — its `MCPAgent` is a thin wrapper over LangChain, so the loop itself is outsourced; the interesting original code is its server-manager deferred-loading and multi-server unification.

### `MCPAgent` Is a LangChain Wrapper (KNOWN — `agents/mcpagent.py`)

`MCPAgent.__init__` (`mcpagent.py:69-175`): key params `max_steps=5` (`:74`), `use_server_manager=False` (`:82`), `disallowed_tools` (`:80`), `auto_initialize=False`. The loop is **not hand-written** — `_create_agent` (`:347-389`) calls LangChain's `create_agent(model, tools=self._tools, …)` which returns a `CompiledStateGraph`, wraps it with `ModelCallLimitMiddleware(run_limit=self.max_steps)` (`:370`), and sets `recursion_limit = max_steps * 2` (`:134, :386`). So the ReAct/tool-calling loop, the termination conditions, and the message-state machine are all LangChain's; mcp-use contributes the MCP connection lifecycle, tool adaptation, and the optional server manager. The cap is enforced two ways belt-and-suspenders: model-call-limit middleware (`max_steps` LLM calls) AND graph recursion limit (`max_steps*2` graph steps).

### Multi-Server Tool Unification (KNOWN — `agents/adapters/langchain_adapter.py`)

`LangChainAdapter._create_tools_from_connectors` converts each connected MCP server's `tools/list` into LangChain `BaseTool`s, **filtering `disallowed_tools` by name** (`:138-139`). All servers' tools are flattened into one `self._tools` list — a single unified namespace, no per-server prefixing (which means name collisions across servers are possible; a gap Verso should close with namespacing, cf. fastmcp's `with_namespace`).

### Server Manager = Thin Deferred Loading (KNOWN — `agents/managers/server_manager.py`, `tools/*.py`)

When `use_server_manager=True`, instead of injecting all tools, `MCPAgent` exposes only **management tools** (`server_manager.py:93-104`): `ListServersTool`, `ConnectServerTool`, `SearchToolsTool` (`search_mcp_tools`), `GetActiveServerTool`, `DisconnectServerTool`. The agent flow: list servers → connect to one (`active_server`) → only then are *that* server's tools exposed (`get_active_server_tools`, `:83-90`); `tools` property (`:120-130`) = management tools + active server's tools. Tools for all servers are pre-fetched into `_server_tools` to populate a search index (`:45-76`). This is the same shape as Strata's progressive loading but coarser (server-granular, not action-granular) and **stateful** (a single `active_server`, not a per-call selection).

**`SearchToolsTool` uses embeddings, not BM25** (`tools/search_tools.py`) — the key contrast with Strata. `ToolSearchEngine` (`:58+`) loads `fastembed.TextEmbedding(model_name="BAAI/bge-small-en-v1.5")` (`:108`, optional `[search]` extra), embeds each tool's text, and ranks by **pure-Python cosine similarity** (`_cosine_similarity`, `:306`; `search`, `:176-227`) with `top_k` default 100. Its description coaches the LLM: *"search for the tool, not for the goal… Do not be too specific."* So the two open deferred-loaders use opposite retrieval: Strata = field-weighted BM25 (keyless, fast, exact-match-friendly), mcp-use = bge-small embeddings + cosine (semantic, needs the model). Both are valid; the choice is keyless-lexical vs semantic-vector.

### For Verso

- **Don't outsource the agent loop to a graph framework if the loop *is* your product.** mcp-use delegating to LangChain's `create_agent` means it inherits LangChain's state machine, termination, and middleware — fine for a thin client, wrong for Verso, whose value is the loop itself. Verso should own its ReAct loop (cf. `infra-serving.md` cross-system patterns); copy mcp-use's *connection lifecycle* and *adapter*, not its loop.
- **Belt-and-suspenders step caps.** mcp-use caps via both a model-call-limit middleware (`max_steps` LLM calls) and a graph recursion limit (`max_steps*2`). Verso should similarly distinguish "max LLM turns" from "max total steps" — a single counter conflates tool-call expansion with reasoning turns.
- **Namespace tools across servers — mcp-use doesn't, and that's a bug.** Flattening multiple servers' tools into one list with no prefix risks name collisions. Verso must namespace (fastmcp's `with_namespace` / Strata's `server::tool` doc-id / Arcade's `Gmail.ListEmails` dot-notation are three precedents).
- **Offer both lexical (BM25) and semantic (embedding) tool search; default to keyless lexical.** mcp-use proves the embedding path works (bge-small + cosine), but it requires a model and an extra dependency. For a keyless default, prefer Strata's field-weighted BM25; expose embedding search as an opt-in for large semantic registries. Both should feed the same `discover` meta-tool.
- **Server-manager mode is coarse (one `active_server`); Verso's deferred loader should be per-call, not stateful.** mcp-use's single active server forces the agent to connect/disconnect to switch contexts. Verso should let a single reasoning step pull tools from multiple namespaces (Strata/Pipedream allow per-request multi-namespace), avoiding the stateful active-server bottleneck.

---

## Cross-System Synthesis — The Tool Layer for Verso

### The Two Universal Contracts

**1. `@tool` → JSON-Schema (port fastmcp verbatim).** Every Python framework here that generates schemas does it the same way: `pydantic.TypeAdapter(fn).json_schema()` over the function object (fastmcp), or `zod.toJSONSchema` in TS (Nango, Apify, Smithery). The reusable recipe: introspect signature → strip DI/context params → TypeAdapter → compress (root-`$ref`→`type:object`, prune titles + unused `$defs`, **keep `additionalProperties:false`** for Claude strict mode) → inject docstring descriptions → object-wrap scalar returns. Defer the build to *registration*, not decoration.

**2. The deferred-loading meta-tool protocol (synthesize Strata + Apify + Pipedream).** Five converging implementations of "don't inject N tool schemas":
| System | Granularity | Selection point | Ranker | Caching |
|---|---|---|---|---|
| Klavis Strata | action | runtime (discover→inspect→execute) | field-weighted BM25+ | none (fresh) |
| Apify | actor | client-cap (meta-tool vs pin + `list_changed`) | (search-actors tool) | 30 min |
| Pipedream | app | connection URL (`/{user}/{app}` vs `/{user}`) | — | tool-set cache |
| mcp-use | server | stateful `active_server` | bge-small + cosine | index pre-fetch |
| Toolhouse | bundle | `get_tools(bundle)` string | — | — |

Verso's loader should: keep only the *namespace list* eagerly in context; expose `discover(query, namespaces)→names`, `inspect(ns, action)→one schema`, `execute(ns, action, opaque_json)→result`; rank with keyless field-weighted BM25 by default (embedding opt-in); pass execute-params as an opaque object (decouples meta-tool schema from N action schemas); fire `notifications/tools/list_changed` when pinning; and **degrade to a flat meta-tool for clients without `tools.listChanged`** (Apify's lesson).

### The Three Converging Auth-Interrupt Designs

Arcade (`output.authorization{status,url,id}` in the execute result), MCP spec (`URL_ELICITATION_REQUIRED = -32042` + `data.elicitations[]`), and Strata (`handle_auth_failure` meta-tool) all answer "how does a ReAct loop pause for OAuth consent." The shared shape: a resumable `(auth_id, consent_url, status)` triple. Verso's HITL seam for auth should model the interrupt as a *value in the tool result* (Arcade) that the loop inspects — surface `url`, long-poll on `id` (45s windows, Arcade's constant), re-execute on `completed` — and emit it as MCP `-32042` at the protocol edge. This is distinct from in-loop input elicitation (fastmcp's `ctx.elicit` → accept/decline/cancel).

### The Three-Tier Error Model (Arcade is the reference)

transport (connection failure → protocol error, don't show LLM) / protocol (tool-not-found/unsupported → JSON-RPC error) / application (tool ran, failed → `isError:true` *with content the LLM reads*). Arcade's `OutputError{kind, can_retry, retry_after_ms, additional_prompt_content}` is the most complete: a categorized `kind` enum across tool-def/tool-runtime/upstream tiers, a `can_retry` routing bit, a backoff hint, and error text purpose-built for model self-correction. Per MCP spec SEP-1303, **argument-validation failures belong in the application tier (`isError:true`)**, not as `INVALID_PARAMS` — so the model can fix its own bad arguments. This fills the `@tool(on_error=…)` gap fastmcp explicitly left open (issue #2882).

### Cross-references

- Tool auth delegation / credential storage at depth: `03_teardowns/fw-composio-browseruse.md`, `infra-retrieval-tools.md` (Composio R4).
- Pydantic-native tool registration (`@agent.tool` + RunContext): `PYDANTIC_AI.md` — directly informs Verso's DI-param-stripping in the schema-gen path.
- The agent loop, streaming, disconnect/cancellation, and watchdog contracts that wrap this tool layer: `03_teardowns/infra-serving.md` (vLLM `@with_cancellation`, three-state health, post-200 error invisibility).
- ADK `FunctionTool`/`MCPToolset`/`ToolContext`: `ADK_RE_NOTES/03_TOOLS.md`.
