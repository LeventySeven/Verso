# RE Targets — Tool / MCP Infrastructure

> Category: `tools-mcp`
> Verso relevance axis: tool auth, deferred/meta-tool loading, tool error contracts, MCP server/registry patterns, Python @tool decorator design, pluggable tool sources.
> Generated: 2026-06-05

---

## Already covered

- **Composio** — full R4 teardown across 7 files (`COMPOSIO.md`, `COMPOSIO_DEEP.md`, `COMPOSIO_R4_AUTH.md`, `COMPOSIO_R4_CORE.md`, `COMPOSIO_R4_TOOLS.md`, `COMPOSIO_R4_MCP_TRIGGERS.md`, `COMPOSIO_R4_ROUTER.md`). Auth delegation, trigger architecture, tool routing, MCP adapter all covered at reimplementable depth. Do not re-RE.
- **ADK tools** — covered in `ADK_RE_NOTES/03_TOOLS.md` + `03b_TOOLS_DEEP.md`. Google ADK's `FunctionTool`, `MCPToolset`, `OpenAPIToolset` + `ToolContext` patterns.
- **Mastra** — `MASTRA.md` covers the TypeScript framework including its MCP adapter pattern. Background context only — Verso is Python-first.
- **Pydantic AI** — `PYDANTIC_AI.md`. Python-native tool registration via `@agent.tool`, RunContext injection. Directly relevant to Verso's `@tool` design.

---

## RE Targets

### fastmcp (PrefectHQ)

**what**: The de-facto standard Python MCP server/client framework. v3.x (current: 3.4.0, June 2026) ships Providers + Transforms + Proxy composition as first-class primitives. Powered the official MCP Python SDK (v1 was incorporated in 2024); now maintained as a standalone project downloaded ~1M times/day, claimed to power 70% of deployed MCP servers.

**why_for_verso**: Verso needs an MCP adapter that is an *opt-in edge*, not the default tool path. fastmcp is the reference implementation for (a) `@mcp.tool` → JSON-Schema auto-generation from Python type hints — Verso needs to match this ergonomic contract, (b) `ProxyProvider` + `server.mount()` multi-server composition — the exact pattern Verso would use to aggregate tool namespaces, (c) `ProxyProvider` cache TTL (default 300 s) — sets the right default for Verso's lazy tool registry, (d) the three-tier error model (transport / protocol / application `isError:true`) — Verso's tool executor must understand this split to route retries correctly, (e) lazy "bridge" session init — upstream connects only on first `initialize`, not at server start — a critical pattern for Verso's deferred tool loading.

**what_to_RE**: `src/fastmcp/` — specifically `server/proxy.py` (ProxyProvider, ProxyClient, `create_proxy()`), `server/server.py` (mount logic, component registry), `client/client.py` (programmatic client API), `tools/tool.py` (schema generation path from Python annotations). Also read the `v3.2.0` "Show Don't Tool" release notes for the new app/UI primitives. Cross-check the `CHANGELOG.mdx` for every breaking change from v2→v3.

**source_pointer**: `github.com/PrefectHQ/fastmcp` (MIT) — fully open source, `pip install fastmcp` to get the wheel. Docs at `gofastmcp.com`.

**priority**: P0 — directly shapes Verso's MCP adapter interface, `@tool` decorator, and the deferred/lazy tool loading design.

---

### Arcade.dev

**what**: Closed SaaS MCP runtime that treats agent tool calling as an *authorization problem*. Core primitive: per-user OAuth 2.1 delegation tokens that gate every tool call; authorization "interrupts" pause the agent loop until the user grants consent, then resume. Co-authored the MCP authorization spec (OAuth 2.1 + Resource Indicators + PKCE).

**why_for_verso**: Verso's `@tool` decorator needs a story for user-delegated auth — the question is whether to bake it in or leave it to the caller. Arcade's three-step interrupt pattern (`authorize()` → poll `waitForCompletion()` → `execute()`) is the cleanest production answer to "how does a ReAct loop pause for human consent without breaking the loop?". This maps directly to Verso's HITL seam. Specific things to extract: the `auth_response` data model (status + URL + user_id + tool_name), the namespaced tool-name convention (`Gmail.ListEmails`), how authorization state is persisted across agent turns, and whether the interrupt is synchronous-blocking or async-resumable. The answer shapes Verso's checkpoint/resume contract for auth-gated tools.

**what_to_RE**: The Arcade Python SDK (`pip install arcadai`) — read every source file in `arcadai/`. Focus on `tools/client.py` (execute + authorize methods), the `AuthResponse` / `ToolAuthorization` models, and the Engine's HTTP API (error codes when auth is missing — these reveal the interrupt contract). Also probe the live API: send a `tools.execute` for a tool that requires auth without having authorized — the error body reveals the exact interrupt schema. Check `docs.arcade.dev/en/home/auth/` for the authorization server design.

**source_pointer**: `pip install arcadai` (SDK is open, engine is closed SaaS). Docs at `docs.arcade.dev`. No public GitHub for the engine.

**priority**: P0 — the authorization interrupt pattern is the most underspecified part of Verso's HITL seam for tool calls.

---

### Klavis AI (YC X25)

**what**: Open-source MCP infrastructure platform with "Strata" — a 4-stage progressive tool loading protocol that reduces context usage 60–80% by deferring full schema injection. Instead of loading all tool schemas at startup, agents query: (1) server categories, (2) action types within a service, (3) detailed schemas for selected actions, then (4) execute. 100+ prebuilt MCP integrations + OAuth. Also ships an MCP Sandbox for LLM training/RL.

**why_for_verso**: Strata is the most concrete published implementation of *deferred/meta-tool loading* — a first-class Verso concern. The four-stage protocol (`discover_server_actions` → `get_action_details` → `execute_action`) is the production answer to "how do you give an agent 100+ tools without blowing the context window?" Verso's tool registry needs an equivalent lazy-load pattern; Strata gives numbers (15.2% accuracy improvement, 60–80% context reduction) that can be used as calibration targets. The `open-strata` directory in the repo is specifically the open-source implementation to read.

**what_to_RE**: Clone `github.com/Klavis-AI/klavis`, read `open-strata/` in full (all Python + TypeScript source). Map the exact 4-stage API call sequence and the data shape at each stage. Read `mcp_servers/` for how individual integration servers implement the Strata protocol. Read `_oauth_support/` for the auth flow. The codebase is Python (39%), Go (24%), TypeScript (22%) — focus on Python + TypeScript for Verso relevance.

**source_pointer**: `github.com/Klavis-AI/klavis` (open source, Apache 2.0). Cloud hosted at `api.klavis.ai`.

**priority**: P0 — Strata is the reference implementation for Verso's deferred/lazy tool schema loading strategy.

---

### MCP Spec (modelcontextprotocol / 2025-11-25)

**what**: The protocol specification itself — not a product but the canonical contract. The 2025-11-25 revision is the current stable spec. Key additions: Streamable HTTP transport (replaces HTTP+SSE), OAuth 2.1 Resource Indicators (RFC 8707) + Client ID Metadata Documents (replaces DCR), tool list pagination, `isError: true` in tool results (application-level vs protocol-level error split), `_meta` field standardization, `icons` on tools/resources, incremental scope consent via `WWW-Authenticate`.

**why_for_verso**: Verso's MCP adapter must conform to 2025-11-25, not the older 2024-11-05 spec. The most Verso-relevant additions: (a) tool list pagination — the spec now defines how to batch tool discovery, which is the foundation for Verso's lazy loader to implement correctly, (b) `isError: true` semantics — Verso's tool executor must distinguish `isError:true` (application failure, LLM can see and retry) from a JSON-RPC error (protocol failure, abort), (c) Streamable HTTP session model — the new transport's session lifecycle determines how Verso's MCP edge manages connection state, (d) CIMD auth discovery — how Verso authenticates to remote MCP servers in prod.

**what_to_RE**: Read `github.com/modelcontextprotocol/specification` — specifically `schema/2025-11-25/schema.ts` (the TypeScript source of truth for all message shapes), `docs/specification/2025-11-25/server/tools.md` (tool call, list, pagination), `docs/specification/2025-11-25/basic/transports.md` (Streamable HTTP session lifecycle), `docs/specification/2025-11-25/basic/authorization.md` (CIMD, Resource Indicators). Also read the `changelog/` between 2024-11-05 and 2025-11-25 to understand what changed and why.

**source_pointer**: `github.com/modelcontextprotocol/specification` (open, Apache 2.0). Human-readable at `modelcontextprotocol.io/specification/2025-11-25`.

**priority**: P0 — spec compliance is non-negotiable for the adapter; reading source.ts reveals the exact wire format Verso must produce and consume.

---

### Nango

**what**: Open-source, self-hostable integration runtime. Three primitives: Auth (OAuth / API-key storage + refresh across 800+ APIs), Proxy (authenticated pass-through requests), Functions (TypeScript integration logic deployed to Nango's infra). Exposes integrations as a native MCP server. In production at Replit, Mercor, Ramp — billions of API requests/month. The key differentiator vs Composio: Nango is code-first (integrations live in your repo, deploy via CI/CD), you own the credential database, and it adds unified data sync + webhooks (not just tool calls).

**why_for_verso**: Composio is already covered, but Nango's code-first model is architecturally different and more relevant to Verso's design philosophy. Specifically: (a) how Nango's Functions deploy as both scheduled jobs AND MCP tool definitions from the same codebase — this is the pattern Verso wants for dual-mode (in-memory vs event-sourced) tool execution, (b) the Auth → Proxy → Functions three-tier stack shows how to separate credential storage from execution, which Verso's pluggable auth edge needs to model, (c) how the MCP server exposes a subset of Action Functions as tool schemas — the selection and schema-generation logic is directly relevant to Verso's `@tool` → MCP export path.

**what_to_RE**: Clone `github.com/NangoHQ/nango`. Read `packages/server/` (auth storage, proxy logic), `packages/runner/` (how Functions execute), `packages/shared/` (data models, integration manifest format). Focus on the MCP server implementation — likely in `packages/server/lib/mcp/` or similar. Read how `ActionFunction` → MCP tool schema conversion works. Also read `docs/nango.dev/docs/integrate/guides/` for the integration authoring contract.

**source_pointer**: `github.com/NangoHQ/nango` (MIT). Self-hostable. Docs at `nango.dev/docs`.

**priority**: P1 — strong reference for Verso's auth edge and the tool-as-function deployment model; lower than Klavis/Arcade because Composio already covers the credential-delegation space at depth.

---

### Pipedream Connect

**what**: Managed MCP infrastructure with 10,000+ tools across 3,000+ APIs. Core architecture: per-user OAuth credential isolation via `external_user_id` header, tool execution routed through four headers (`x-pd-project-id`, `x-pd-environment`, `x-pd-external-user-id`, `x-pd-app-slug`), developer auth via client_credentials OAuth bearer token. Tool schemas dynamically generated from app-slug registrations. One of the most mature MCP deployments in prod (GA early 2026). Now owned by Workday (acquired Nov 2025, closed Jan 2026).

**why_for_verso**: The `external_user_id` pattern is the simplest production answer to "how do you scope a 10k-tool registry to a single user's credentials per request?" — Verso's multi-tenant tool routing needs exactly this. The URL structure (`https://remote.mcp.pipedream.net/v3?externalUserId=...&app=...`) reveals how to select a sub-registry of tools at connection time rather than loading all 10k. The open-source `mcp-chat` repo is a reference agent implementation showing how a Verso-like loop would consume this.

**what_to_RE**: Read `github.com/PipedreamHQ/mcp-chat` (reference agent, open source). Read `raw.githubusercontent.com/pipedreamhq/pipedream/HEAD/modelcontextprotocol/README.md` for the server-side architecture. Probe the live API: connect to `remote.mcp.pipedream.net/v3` with a test `external_user_id`, call `list_tools` without an app slug (gets all), then with `?app=gmail` (gets subset) — this reveals the lazy scoping mechanism. Send a tool call without proper auth headers to extract the error schema.

**source_pointer**: `github.com/PipedreamHQ/mcp-chat` (open, reference impl). Engine is closed SaaS at `remote.mcp.pipedream.net`. Acquired by Workday Jan 2026 — long-term availability uncertain.

**priority**: P1 — the external_user_id + app-slug scoping pattern is the best available reference for multi-tenant tool routing; acquisition adds uncertainty about longevity as a reference.

---

### Toolhouse

**what**: Cloud BaaS for agent tools. Core SDK contract: `get_tools(bundle?)` fetches tool JSON schemas from cloud (OpenAI-compatible format), `run_tools(response)` executes tool calls in Toolhouse's cloud and returns results as messages. Three-line integration. Tools include RAG, code execution, browser use, web search — all running remotely. Built-in tool bundles for contextual grouping. Multi-provider: switches between OpenAI/Anthropic/etc at `Toolhouse(provider=...)` init.

**why_for_verso**: The `get_tools()` / `run_tools()` split is the simplest possible cloud-tool adapter interface. Verso's MCP adapter will be more capable, but this two-method contract establishes the minimum viable interface that Verso needs to be at least as ergonomic as. The `bundle` concept (contextual tool grouping at `get_tools(bundle="email")`) is a simpler version of Klavis's Strata — useful for understanding the design space between "all tools" and "full progressive discovery." Also: `register_local_tool()` shows how cloud and local tools are merged before injection — relevant to Verso's mix of `@tool` functions and MCP-sourced tools.

**what_to_RE**: `pip install toolhouse`, read `toolhouse/` source (especially `client.py`, `tools.py`, the bundle resolution logic). Also read `github.com/toolhouseai/toolhouse-sdk-python`. Focus on: how `get_tools()` constructs the request to Toolhouse's API (what parameters, what auth), how `run_tools()` dispatches tool calls to the cloud executor and waits for results (sync? async? streaming?), and how the `provider` parameter changes the schema format returned.

**source_pointer**: `github.com/toolhouseai/toolhouse-sdk-python` (open source). `pip install toolhouse`. Engine is closed SaaS.

**priority**: P1 — useful ergonomic reference and the bundle/local-merge pattern, but narrower scope than Arcade/Klavis; the cloud-execution model is not Verso's target.

---

### Smithery

**what**: MCP registry + hosting platform. 7,000+ servers discoverable via a searchable registry. Hosting: servers run on Smithery's infra with managed OAuth modals (server authors don't write auth flows). CLI (`smithery-ai/cli`, TypeScript) manages connections: `smithery mcp add <url>`, `smithery tool list`, `smithery mcp search`. Distinguishes "servers" (granular MCP tool providers) from "skills" (higher-level curated bundles, installable via `npx skills add`). REST + MCP SDK + AI SDK integration paths.

**why_for_verso**: Verso needs a discovery story — how does a Verso agent find and add tools at runtime? Smithery's registry API + CLI is the reference for that. The server/skill distinction (protocol-level vs semantic-bundle level) maps directly to Verso's `@tool` (local) vs MCP server (remote protocol) vs tool bundle (curated namespace). The `search tools by name or intent` CLI feature hints at semantic tool routing — relevant to Verso's deferred loading where the agent queries for a tool by description.

**what_to_RE**: Clone `github.com/smithery-ai/cli`. Read `src/` in full — focus on registry query implementation (how `mcp search` hits the Smithery API), the on-disk connection config format (where MCP server URLs and auth tokens are persisted), and the `skills/` directory for the bundle format. Also fetch `registry.smithery.ai/servers?q=...` API to understand the registry schema (tool counts, server metadata, install commands). Check `smithery.ai/servers/smithery` for the registry-as-MCP-server pattern (Smithery exposes itself via MCP).

**source_pointer**: `github.com/smithery-ai/cli` (open source). Registry at `registry.smithery.ai`. Official MCP registry at `registry.modelcontextprotocol.io`.

**priority**: P1 — reference for Verso's runtime tool discovery interface; not directly shaping core loop design but necessary for the tool registry plug point.

---

### Apify MCP Server

**what**: Open-source MCP server that exposes Apify's 3,000+ Actors (web scrapers, crawlers, automation) as MCP tools. Two modes: (1) dynamic — exposes a `call-actor` meta-tool that takes an Actor ID, agent navigates the full catalog; (2) pinned — you select 3–5 Actors in the UI, each gets its full input schema surfaced. Dropped SSE transport for Streamable HTTP before April 2026. RAG Web Browser is the recommended default Actor (structured web search + scrape).

**why_for_verso**: Apify is the clearest example of the "dynamic meta-tool vs pinned explicit schema" tradeoff at scale. This is Verso's deferred tool loading problem in concrete form: 3,000 tools is too many to load; a meta-tool that routes to any tool on demand is context-efficient but gives the LLM less signal. The architectural decision between these two modes (and when to switch) is a design decision Verso's tool registry must make. The `add-actor` vs `call-actor` dual-mode switch (triggered by whether the client supports dynamic tool discovery) also reveals how to make Verso's deferred loader progressive without breaking simple clients.

**what_to_RE**: Clone `github.com/apify/apify-mcp-server`. Read the full TypeScript source — focus on `src/main.ts` (tool registration logic, dynamic vs pinned mode switch), how Actor input schemas are fetched and converted to MCP tool schemas, and the output schema inference system for structured results. Also read `github.com/apify/actor-mcp-servers` for the curated MCP server collection pattern.

**source_pointer**: `github.com/apify/apify-mcp-server` (open source, Apache 2.0). Hosted at `mcp.apify.com`.

**priority**: P2 — concrete reference for the meta-tool / deferred loading tradeoff at scale, but primarily a domain-specific tool provider rather than a framework primitive. Useful calibration, not a design driver.

---

### mcp-use

**what**: Lightweight open-source Python MCP client framework (MIT, released March 2026, Python >=3.11). Provides: `MCPAgent` (agent that connects to MCP servers and runs tool-calling loops), `MCPClient` (programmatic server connection), `MCPServer` (server creation). Extras for `anthropic`, `openai`, `e2b` integrations. Designed as the "fullstack MCP framework for Python" — covers both client (consuming tools) and server (exposing tools) sides.

**why_for_verso**: mcp-use's `MCPAgent` is the most direct existing Python analog to what Verso is building — a Python agent loop that consumes MCP tools. Reading its source reveals (a) how a Python async loop manages MCP server connection lifecycle (connect, list tools, execute, disconnect/reconnect), (b) what friction points emerge when you wrap a raw MCP client in an agent loop, (c) how multi-server connection is managed in Python. Verso will learn most from understanding where mcp-use's design falls short (it's a thin client, not a framework) vs. where it nails the ergonomics.

**what_to_RE**: `pip install mcp-use`, read all source in the package. Focus on `MCPAgent` (the ReAct loop implementation), `MCPClient` (connection management, how it wraps the official MCP Python SDK), and how tools from multiple servers are unified into a single tool namespace. Cross-reference with `github.com/mcp-use/mcp-use`.

**source_pointer**: `github.com/mcp-use/mcp-use` (MIT). `pip install mcp-use`.

**priority**: P2 — thin but directly comparable to Verso; most valuable as a "what to not copy" read and a quick calibration of the minimum Python MCP client surface.

---

## Notes

**On Composio**: Already covered at exceptional depth (7 files, R4 round). The auth delegation model, trigger architecture, and MCP adapter are all in `COMPOSIO_R4_*`. Do not re-RE; use existing teardowns as the baseline for tool auth comparisons.

**On the deferred/lazy loading priority**: Three distinct approaches exist and are all worth reading in order: Klavis Strata (4-stage progressive discovery, open source), Anthropic's ToolSearch (GA Feb 2026, built into Claude Code — read the Claude Code teardown for implementation), and Apify's pinned/dynamic dual-mode. These represent the design space Verso's lazy registry must navigate.

**On error contracts**: The MCP spec's `isError:true` + error category (transient/validation/business/permission) + `isRetryable` pattern is the production answer. FastMCP issue #2882 tracks the fact that there's no standardized error-handling decorator yet — a gap Verso can fill with a first-class `@tool(on_error=...)` contract.

**On the OAuth seam**: Arcade is the deepest existing implementation of the authorization interrupt pattern that maps to Verso's HITL seam. Composio covers the credential storage / OAuth flow side. Nango covers the code-first credential ownership side. Together these three define the full auth stack Verso needs to support as pluggable edges.

**Closed targets**: Arcade's engine is closed SaaS — probe via SDK install + live API error mining. Toolhouse's executor is closed — SDK is open. Pipedream's MCP server is closed (acquired by Workday) — probe via `mcp-chat` reference impl + live server. Smithery's registry is partially open (CLI is open, registry API is queryable without auth).

**New in 2026 (post-seeding)**: Klavis AI (YC X25, launched 2026) was not on the seed list and is P0. Nango is significantly more architecturally relevant than its brief seed mention suggested — it is the only open-source, self-hostable, code-first alternative to Composio with a native MCP server.
