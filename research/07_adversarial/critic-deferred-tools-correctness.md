# Adversarial Critique — Decision: Deferred Tool Loading (Strata 4-Stage + BM25+)
**Lens:** CORRECTNESS
**Date:** 2026-06-05
**Verdict:** REVISE

---

## The Attack

The resolution note's Decision 7 and Decision 8 rest on a single load-bearing claim: that Strata's field-weighted BM25+ ranker indexes **parameter names and descriptions** (at weight 15) alongside tool name/description (at weight 30), producing a richer signal for discovery. The resolution explicitly states:

> "Field weights: name/description/title/tags = 30, parameter names + descriptions = 15, response field names = 5."

This is cited to `utils/shared_search.py:47-151`.

**The claim is true in the source. It is false for Verso's exact case.**

### The Mechanism Mismatch (KNOWN from cloned source)

Strata's `UniversalToolSearcher._build_index` (`shared_search.py:47-151`, read in full) extracts the weight-15 parameter signal by accessing these fields on each tool object:

```python
for param_type in ["path_params", "query_params"]:
    params = self._get_tool_field(tool, param_type, {})  # tool.get("path_params", {})
    ...
body_schema = self._get_tool_field(tool, "body_schema", {})
...
response_schema = self._get_tool_field(tool, "response_schema", {})
```

These are **OpenAPI REST bridge fields** (`path_params`, `query_params`, `body_schema`, `response_schema`). They are the internal field names Klavis uses in its own OpenAPI→MCP translation layer.

Strata's `MCPClient.list_tools()` (`mcp_proxy/client.py:58-96`, read in full) fetches MCP tools and serializes them as:

```python
tool_dict = {
    "name": tool.name,
    "description": tool.description,
    "inputSchema": tool.inputSchema,
}
```

The result dict has **`inputSchema`**, not `path_params`/`query_params`/`body_schema`/`response_schema`.

This is confirmed by Klavis's own production MCP servers (e.g., `mcp_servers/airtable/server.py:101-440`) which expose `types.Tool(name=…, description=…, inputSchema={…})` — the standard MCP wire shape. The integration tests (`tests/test_server_integration.py:43-70`) also define mock tools with `inputSchema`, not the OpenAPI bridge fields.

**Result:** When the BM25 indexer runs against any standard MCP tool source (which is Verso's exact case — `tools/adapters/mcp.py` wraps upstream MCP servers), the parameter-level fields (`path_params`, `query_params`, `body_schema`, `response_schema`) all return `{}`. The weight-15 parameter signal and the weight-5 response-field signal are **silently zero** for every tool from every MCP source.

Verified by simulating the field extraction:
```
path_params:          {} (empty)
query_params:         {} (empty)
body_schema:          {} (empty)
body_schema.properties: {} (empty)
response_schema:      {} (empty)
```

Only `category` (=namespace, weight 30), `operation` (=tool name, weight 30), `description` (weight 30), and optionally `title`/`summary`/`tags` are indexed.

### What This Means for Verso's BM25+

The BM25 ranker Verso plans to adopt is effectively **name + description only** for any tool sourced from a standard MCP server. That is still a valid, useful ranker — name and description are the highest-weight fields. But the resolution note's evidence for the field-weighting scheme is drawn from a source that *happens to have parameter-level structured fields* that Verso's MCP adapter will never produce.

The 15-weight parameter-name signal is the key differentiator for disambiguation cases: when two tools have similar descriptions but different parameter shapes (e.g., `create_issue` and `create_pr` both match "create a GitHub thing"), the parameter names (`title`+`body` vs `title`+`base_branch`+`head_branch`) would distinguish them. Without that signal, BM25 ranking degrades to pure name+description matching — still decent, but missing the stated justification.

### The Line Number Claim

The resolution cites `tools.py:14-145` for the 5 meta-tool definitions. The actual file has definitions at lines 14-145, then `execute_tool` begins at line 148, and the dispatch runs to line 383. The line count cited (`tools.py:155-375`) for "4-stage dispatch implementation" is off (actual: `148-384`) but close enough to be a minor inaccuracy. The `shared_search.py:47-151` citation is accurate — `_build_index` starts at line 47 and the file is 202 lines. These are minor. The critical issue is architectural, not numerical.

### Secondary Correctness Issue: `execute_tool` in Verso vs Strata

The resolution adopts Strata's `execute_action` opaque-JSON-string params pattern. In Strata, `execute_action` receives `path_params`, `query_params`, `body_schema` as JSON strings and merges them. For Verso's native `@tool` tools, the execute path goes through `ToolDispatcher._call_one`, which validates args against the tool's schema via Pydantic. But for MCP-sourced tools, the params come in as an opaque JSON string (`params: str = "{}"`), which is `json.loads`'d and forwarded. This means MCP-sourced tool calls bypass Verso's validation ladder entirely — the `TOOL_BAD_INPUT_VALUE` → `isError:true` self-correction path only fires for native tools. For MCP tools, a bad argument hits the upstream MCP server's validation and returns an application-tier error, which Verso must faithfully pass through. This is probably correct behavior, but the resolution does not acknowledge it, and it creates an invisible asymmetry between native and MCP tool error handling that could confuse debugging.

### Does the Core Design Break?

No. The deferred-loading architecture (5 meta-tools, lazy schema injection, namespace manifest as only eager context) is sound and the Strata source confirms the mechanism works. The 4-stage discover→inspect→execute→auth-recover protocol is real. The context reduction is real. The field-weighted ranker design is correct for the case Strata was built for.

The attack lands specifically on **the ranker's effectiveness claim for Verso's exact adapter path** — not on the architectural decision to use deferred loading, and not on BM25+ as the right algorithm family.

---

## Does It Break the Decision?

**Partially.** The deferred-loading design (Decision 7) is not broken. The BM25 ranker design (Decision 8) is technically correct in algorithm choice, but the evidence for the field-weight scheme does not hold for Verso's MCP adapter case. The "weight-15 parameter signal" will be silent for any tool coming through `MCPAdapter.tools_for()`, which is the entire point of the deferred loader (it handles large MCP sources, not large native `@tool` registries — those are rarely above 20 anyway).

The claim "keyless BM25 is sufficient" probably remains true for name+description matching. But the resolution over-claims by citing the full field-weight breakdown as evidence when that breakdown only activates for OpenAPI bridge tools, not standard MCP tools.

---

## Evidence Checked

| Claim | Source checked | Finding |
|---|---|---|
| `tools.py:14-145` = 5 meta-tool definitions | `/tmp/klavis/open-strata/src/strata/tools.py` cloned at HEAD | CONFIRMED (defs 14-145, execute_tool starts 148) |
| `shared_search.py:47-151` = field-weighted BM25+ | `/tmp/klavis/open-strata/src/strata/utils/shared_search.py` cloned | CONFIRMED — but field access uses OpenAPI field names |
| `bm25_search.py` = `method="bm25+"`, `stopwords=[]` | `/tmp/klavis/open-strata/src/strata/utils/bm25_search.py` cloned | CONFIRMED exactly |
| Weight-15 param signal activates for MCP tools | `mcp_proxy/client.py:58-96` list_tools return shape | FAILS — returns `inputSchema`, not `path_params`/`body_schema` |
| Klavis's own MCP servers use `inputSchema` | `mcp_servers/airtable/server.py`, integration tests | CONFIRMED — standard MCP format throughout |
| Context reduction benefit (~15%, 60-80% tokens) | Klavis marketing, labeled INFERRED in teardown | Still INFERRED; not undermined by this finding |

---

## Recommendation

1. **Decision 7 (deferred loading architecture): SURVIVES unchanged.** The mechanism is real and the source proves it. The context reduction from lazy schema injection is the core benefit and is correctly modeled.

2. **Decision 8 (BM25+ field-weighted ranker): REVISE the evidence claim.** The field weights cited (name/desc 30, params 15, response 5) are the Strata-internal weights for its OpenAPI bridge mode. For Verso's `MCPAdapter`, `list_tools()` returns `{name, description, inputSchema}`, so only the weight-30 fields activate. The BM25 ranker should be described as **name + description + title/tags weighted ranker** for MCP sources, with parameter-name indexing as an **opt-in extension** that requires extracting `inputSchema.properties` into BM25 fields at index-build time.

   Concretely, `DeferredLoader._build_index` needs a branch:
   ```python
   # For MCP tools: extract param names from inputSchema.properties
   input_schema = tool.get("inputSchema", {})
   for param_name, param_info in input_schema.get("properties", {}).items():
       fields.append(("param_name", param_name.lower(), 15))
       desc = param_info.get("description", "")
       if desc:
           fields.append(("param_desc", desc.lower(), 15))
   ```
   Without this, the "weight-15 param signal" is dead code for the MCP path. With it, the full field-weighted scheme actually activates as the resolution claims.

3. **Note the validation asymmetry** in the executor: native `@tool` calls go through Verso's schema validation and produce structured `TOOL_BAD_INPUT_VALUE` errors; MCP-sourced opaque-params calls bypass that path. Document this explicitly so the error-handling routing table is honest about which tier each error originates from.
