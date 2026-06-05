# Public API Ergonomics + Peer Positioning — Verso Design Resolution

**Subsystem:** `api-and-peers`
**Date:** 2026-06-05
**Source teardowns:** `fw-py-peers.md` (Burr, Marvin, PocketFlow, Atomic Agents, Griptape, Julep) · `fw-ts-peers.md` (Inngest AgentKit, CF Agents SDK, OpenAI Agents JS, LangGraph.js, Convex Agent, VoltAgent, ElizaOS, Motia)
**PRD section resolved:** §7 Public API surface + §10 open decisions relevant to surface shape

---

## Decisions Resolved

---

### Decision 1: The one-flag seam — how `durable=True` compiles

**Choice:** `durable=True` on `agent.run()` or `agent.submit()` appends exactly one `PersisterHook` (a `PostRunStepHook`) to the loop's `LifecycleAdapterSet`. The loop itself is **byte-identical** in both modes — it never branches on `if durable`. In tactical mode the adapter set is empty; in durable mode it contains one hook. Everything else (HITL, event sourcing, resume) derives from this single difference.

**Rationale:** Burr is the only open-source framework with a production-tested implementation of "one flag, same loop." Its mechanism is cleaner than LangGraph's checkpoint-threaded-into-compile (which requires a different `.compile({checkpointer})` path that changes the object type) and cleaner than CF Agents (where the DO itself IS the durable mode — no tactical path at all). The Verso claim "zero loop-code changes" is only credible if the loop is provably unaware of persistence. Burr proves this is achievable.

**Evidence:**
- `burr/core/application.py:2565` — `_set_sync_state_persister()` appends `PersisterHook(persister)` to `self.lifecycle_adapters`. Nothing else changes.
- `burr/core/application.py:949-993` — `Application._step` calls `call_all_lifecycle_hooks_sync("post_run_step", ...)` in a `finally` block with **zero** awareness of whether a persister is registered.
- `burr/core/persistence.py:214` — `PersisterHook` is a 4-line `PostRunStepHook`; the entire seam is this one class.
- `fw-py-peers.md:64` — "The seam in one sentence: in-memory = empty `LifecycleAdapterSet`; durable = the same set plus one `PersisterHook`."

**Alternatives rejected:**
- LangGraph's `compile({checkpointer})` — the checkpointer is woven into the graph compile, producing a different object class; tactical and durable agents are not the same object with one flag.
- CF Durable Objects — durability is a deployment target, not a runtime flag; there is no in-memory mode.
- Inngest AgentKit's ambient-context detection — elegant, but Verso is not tied to Inngest's runtime; we need a framework-owned seam, not a dependency-injected one.

---

### Decision 2: The HITL surface — `await ctx.hitl.request(...)` hides the generator return

**Choice:** The public HITL API is `answer = await ctx.hitl.request("Approve?")`. Internally this compiles to a **generator return** (Burr's `halt_before`/`halt_after` model) in tactical mode and a durable wait in durable mode. The `(action, result, state)` tuple Burr surfaces to the caller is hidden behind `ctx.hitl`; the user never sees `Command(resume=)`. LangGraph's `Command` shape is adopted for the **internal** return value unifying resume + state-patch + goto, but it stays internal.

**Rationale:** Burr's HITL is the cleanest because pause and durability share one mechanism (persist-per-step, resume from last row). LangGraph's `interrupt()`/`Command(resume=)` is more powerful (supports re-run-from-top with indexed resume values) but requires the user to understand the re-entry model. VoltAgent's `suspend()`/`resume()` snapshot is more portable (serialized-checkpoint) but exposes the snapshot format to users. The Verso goal is "checkpoint-backed pause, resume hours later / a different process" (PRD §6.1) with `await` syntax that hides all of it — none of the peers expose this combination as a clean high-level API; they all require knowing the internals.

**Evidence:**
- `fw-py-peers.md:118-122` — Burr's halt_before result tuple: `(next_action, None, state)` (action not yet run) vs `(prior_action, result, state)` (action ran). The `result=None` vs `result=present` distinction tells the caller exactly where the boundary is — Verso's `hitl.request()` must carry the same signal.
- `fw-py-peers.md:147` — "The HITL pause and the durability seam are the same mechanism: persist on every step, resume from the last row."
- `fw-ts-peers.md:374-376` — LangGraph's `Command({resume?, update?, goto?})` is the right internal shape: unifies resume + state-patch + dynamic routing.
- `fw-ts-peers.md:276-300` — OpenAI Agents JS uses `next_step_interruption` as a discriminated union value in the loop's step enum — interrupt = return to caller with the serialized RunState, same path as HITL and sandbox.
- PRD §10, item 10: "high-level `await ctx.hitl.request()` is the API; `Command(resume=)` stays internal." **Confirmed.**

**Alternatives rejected:**
- Exposing `interrupt()`/`Command` directly (LangGraph) — requires users to reason about re-entry counters and idempotent prefixes; complexity that belongs in the framework, not the user's agent code.
- VoltAgent's `suspend()/resume(input)` — close, but VoltAgent exposes the snapshot format (step index, completedStepsData, etc.) at the suspension call site; Verso keeps the snapshot internal to the runtime layer.

---

### Decision 3: `Agent()` constructor shape — steal Burr's builder clarity, Marvin's ContextVar scope, Atomic Agents' docstring enforcement

**Choice:** `Agent(model, tools, instructions, memory, max_steps, model_policy)` with flat named arguments. No builder pattern (Burr's `ApplicationBuilder` is cleaner than LangGraph's `StateGraph.compile()` but still more ceremony than needed for the 90% path). `instructions` is a string or `Callable[[RunContext], str]` (dynamic). The model id is `"provider:model"` (one string, no object instantiation on the happy path).

Three concrete steals from peers:
1. **Docstring-as-description enforcement** (Atomic Agents `BaseIOSchema`) — `@tool`-decorated functions whose docstring is empty raise at decoration time, not at runtime. The description the LLM sees comes from the docstring; a missing docstring is a hard build error.
2. **ContextVar-scoped current run** (Marvin's `with thread: → ContextVar`) — `RunContext[T]` is available anywhere in the call stack via `contextvars` without explicit parameter threading. `with agent._run_scope():` sets the ContextVar; tools and hooks resolve it via `RunContext.current()`.
3. **Readable instructions, never hidden** (PRD §7 invariant, Atomic Agents `system_prompt_generator`) — `agent.inspect()` returns byte-identical content to what the model receives. The instructions string is a first-class attribute on the agent, not buried in a closure.

**Evidence:**
- `fw-py-peers.md:343-360` — Atomic Agents `BaseIOSchema.__pydantic_init_subclass__` raises `ValueError` if the class has no non-empty docstring. The same discipline applies to `@tool`: missing docstring = hard error at decoration.
- `fw-py-peers.md:162-163` — Marvin's `Thread.__enter__` sets `_current_thread = ContextVar.set(self)`; `get_current_thread()` resolves it anywhere. Zero parameter threading.
- `fw-py-peers.md:346-352` — Atomic Agents `ContextProvider.get_info() -> str` is the pull-model: evaluated fresh each `run()`, never stale.
- PRD §7: "`instructions` readable/editable, never hidden."

**Alternatives rejected:**
- Builder pattern (Burr's `ApplicationBuilder.with_state_persister().build()`) — clean for Burr's graph-building phase, unnecessary ceremony for Verso's flat agent. Verso's "durable" is a run-time flag, not a build-time compile.
- LangGraph's `StateGraph(annotation).addNode(...).compile()` — the foil. Explicitly rejected by the PRD ("the 3-line wedge").

---

### Decision 4: `@tool` decorator contract — typed I/O + `ctx` injection + `{data,error,ok}` envelope

**Choice:** `@tool` produces the tool's JSON schema from the function's type hints and docstring. `ctx: RunContext` is detected by name in the signature and **injected by the framework**, filtered from the LLM's schema view. Tool functions raise freely; the framework wraps all exceptions into `{data: None, error: str, ok: False}`. The tool's return value is wrapped into `{data: result, error: None, ok: True}`. The LLM always sees the envelope, never a raw exception.

The `@tool` decorator takes optional policy kwargs: `read_only: bool = False`, `destructive: bool = False`, `idempotent: bool = True`, `timeout: float = None`, `max_result_chars: int = None`. These drive permission routing and dispatch behavior without requiring subclassing.

**No generic type parameter approach** (Atomic Agents `AtomicAgent[In, Out]`). Verso uses **explicit `input_model=`/`output_model=`** optional kwargs on `@tool` for rich structured I/O, with plain type-hints as the default. The `__init_subclass__` + `__orig_class__` fallback dance is explicitly rejected as "ugly plumbing forced by Python's unreliable runtime generics" (`fw-py-peers.md:372`).

**Marvin's typed-terminal-tool**: the agent finishes a task by emitting a typed object. Verso adopts this as an **opt-in** pattern via `agent.define_outcome(result_type=MyModel, rubric="...")` which installs a `MarkDone(result: MyModel)` terminal tool. Default agents terminate on `stop_reason == end_turn` (not on a typed terminal call). The typed-terminal is the opt-in structured-output path.

**Evidence:**
- `fw-py-peers.md:181-203` — Marvin `create_mark_task_successful` builds a dataclass with `result: task.get_result_type()` dynamically; `__post_init__` re-validates. This is the opt-in terminal-tool pattern.
- `fw-py-peers.md:372-373` — "Verso should decide up front whether tools are typed by generics ... or by explicit `input_model=/output_model=` args — the explicit arg is less magic."
- `fw-ts-peers.md:80-81` — AgentKit: "state is the side-channel, tool return is the LLM-channel — a tool does both at once." Verso's `{data,error,ok}` envelope is the LLM-channel; `ctx.state` mutation (or memory write) is the side channel.
- PRD §5.3: "Dispatch ALWAYS returns `{data, error, ok}` — never raises into the loop."

**Alternatives rejected:**
- Instructor/Pydantic-AI as the structured-output engine (Atomic Agents, Marvin) — Verso owns the tool dispatch layer and does not want an external structured-output retry loop in the hot path. Instructor's retry logic is useful for batch operations, not for a ReAct loop that handles errors by showing them to the model.
- Generic type parameters for tools (`Tool[In, Out]`) — the `__orig_class__` fallback is unreliable Python; explicit kwargs are cleaner.

---

### Decision 5: `Memory` public interface — one object, three read modes, tool-callable

**Choice:** `Memory.default()` returns a `Memory` instance backed by `sqlite-vec` (dev). The public interface for agent code:

```python
await ctx.memory.remember(type="fact", content="...", confidence=0.9)
await ctx.memory.recall(query="...", types=["fact"], scope="user")
await ctx.memory.recall_as_of(query="...", date=datetime)
```

For the LLM: memory is **tool-callable** — `remember`, `recall`, `recall_as_of` are tools injected from `Memory` and available in the agent's tool set by default. The LLM manages its own memory observably, via tool calls.

**Evidence:**
- `fw-py-peers.md:225-230` — Marvin's two recall modes: ambient (`auto_use=True` → search on last 3 messages, inject as info-message) and on-demand (`auto_use=False` → exposed as a tool the agent calls). Verso offers both: auto-recall at context assembly time (injected into `ContextBundle.retrieved`) + on-demand via the `recall` tool.
- `fw-py-peers.md:241` — "Marvin deprecated `Team`. The surviving pattern is ... handoff-as-tool-call." Memory as tool-call follows the same principle: keep all side effects in the observable tool-call channel.
- PRD §5.4: "Memory-as-tool-calls: `remember / recall / recall_as_of`. Writes are additive (ADD-only extraction)."

---

### Decision 6: `run` / `stream` / `submit` — the three entry points and their return contracts

**Choice:**

```
agent.run(task, *, effort=None, durable=False)      -> AgentResult
agent.stream(task, *, effort=None, durable=False)   -> AsyncIterable[StreamEvent]
agent.submit(task, *, effort=None)                  -> RunHandle
```

`run()` is the synchronous (awaitable) path. Returns `AgentResult(output, stop_reason: StopReason, usage: UsageStats, cost_usd, trace_id)`. `stop_reason` is **always** a named `StopReason` enum — never a string, never None.

`stream()` yields `StreamEvent` discriminated by `.type` (one of `message.delta`, `reasoning.delta`, `tool.start`, `tool.result`, `status`, `error`). True-delta convention globally: consumers buffer, senders never un-accumulate.

`submit()` returns a `RunHandle(id, status)` immediately and executes the run in the background durable runtime. The caller reconnects via `agent.attach(handle.id, starting_after=seq)`.

**Monotonic `seq_id` on all stream frames** (adopted from Inngest AgentKit `sequenceNumber` on `publishEvent`, `fw-ts-peers.md:135`) — enables `starting_after=N` cursor replay on reconnect.

**Evidence:**
- `fw-ts-peers.md:135` — AgentKit: "each event has a `scope: 'network'|'agent'` and is stamped with a monotonic `sequenceNumber` from a shared counter... Network and agent contexts share one sequence counter so events across the whole run are totally ordered."
- `fw-ts-peers.md:108-123` — AgentKit's ReAct loop terminates on `stop_reason !== "stop"` AND `iter < maxIter`. Reasoning messages explicitly filtered from the stop check (`:352`, "a ReasoningMessage has no stop_reason and would cause an infinite loop"). Verso must do the same: filter reasoning deltas before testing stop condition.
- PRD §5.6: "true-delta convention, globally... SSE `data: {json}\n\n` + `[DONE]` terminator."
- PRD §6.1: "`submit()` → `{id, status: queued}`; `attach(id, starting_after=last_seq)`; reconnect-safe."

---

### Decision 7: `agent.inspect()` — the transparency surface

**Choice:** `agent.inspect()` returns a `ContextBundle` that is **byte-equal** to what will be sent to the model on the next call. It is not a summary, not a debug dump — it is the actual serialized prompt structure: `{instructions, memory_retrieved, history, tools_schemas, budget_used, budget_total}`. The output is human-readable (formatted JSON/markdown) but deterministically identical to the wire payload.

**Rationale:** This is a design forcing-function (PRD §12 W3). Hidden prompts are bugs; `inspect()` is the architectural commitment that no part of the context assembly is opaque. No peer implements this as a first-class method — they all have debug logging or tracer hooks, but none commit to byte-equality as a success criterion. Verso does.

**Evidence:**
- PRD §9: "`agent.inspect()` is honest: what it prints byte-equals what the model receives."
- `fw-py-peers.md:344-352` — Atomic Agents' `ContextProvider.get_info()` is the pull-model that makes `inspect()` possible: each context source is a named callable, so a dry-run of all providers produces the exact context without a round-trip.

---

### Decision 8: Multi-agent entry point — `from verso.orchestrate import Orchestration, fan_out`

**Choice:** Multi-agent is a **separate import**, never the default. Single-agent is the default. The import boundary is the enforcement mechanism.

Three explicit multi-agent shapes, each a distinct function/class:
1. **`fan_out(tasks, agents, max_concurrency=4)`** — parallel dispatch, no router.
2. **`Orchestration(lead=agent, workers=[...], pattern="orchestrator_workers")`** — orchestrator-workers with typed state store.
3. **`Handoff`** (inline in core) — `agent.handoff_to(other_agent)` as a tool the LLM calls; active-agent switches, conversation history carries over. This is the OpenAI Agents JS model: `transfer_to_<agent>` tool, `setCurrentAgent()` on trigger (`fw-ts-peers.md:269-271`).

Subagent-as-tool: `agent.as_tool(name=..., description=...)` wraps an agent as a `Tool` whose handler runs a nested `agent.run()` and returns the final output. Distinct from handoff — the calling agent keeps control. (OpenAI Agents JS `asTool()`, `fw-ts-peers.md:317`.)

**VoltAgent's `delegate_task` pattern** (supervisor = ordinary agent + one auto-generated delegation tool) is adopted for the orchestrator: the lead agent receives a `delegate_task(task, agents=[...])` tool that fans out to workers in parallel under a shared `run_id`.

**Evidence:**
- `fw-ts-peers.md:317` — OpenAI: "The SDK thus offers BOTH coordination models explicitly: handoff (transfer control) vs asTool (call and return). Don't conflate them — conflating them loses the typed control-transfer."
- `fw-ts-peers.md:467-471` — VoltAgent: "the supervisor is a normal agent whose only special tool is `delegate_task`... fan out to multiple sub-agents in parallel under one shared `conversationId`."
- `fw-ts-peers.md:610` — Cross-framework synthesis: "Verso should make router-between-agents the default (closest to its non-graph philosophy), offer handoff and subagent-as-tool as explicit distinct primitives."
- PRD §6.2: "Multi-agent is never implicit... Single agent + tool parallelism is the default."

---

### Decision 9: Router shape — code-first OR LLM, same slot (AgentKit's union type)

**Choice:** The `router` in `Orchestration` is typed as `Union[Callable[..., Agent | list[Agent] | None], Agent]` — a plain Python function (code-based) OR an Agent that acts as a router (LLM-based). Dispatch is `isinstance` on the runtime type. A code router may return an Agent that then routes (hybrid). This is Inngest AgentKit's `FnRouter | RoutingAgent` union (`fw-ts-peers.md:54-58`) ported to Python.

The default in `Orchestration` is a code router that reads `state.last_result` — no LLM router by default. LLM routing is opt-in by passing an `Agent` as the router.

**Evidence:**
- `fw-ts-peers.md:54-58` — AgentKit: `Network.Router<T> = RoutingAgent<T> | Router.FnRouter<T>`. `getNextAgents()` branches on `instanceof RoutingAgent`. "A code FnRouter may return a RoutingAgent, so code decides 'now use the LLM router'."
- `fw-ts-peers.md:137` — "Verso should: copy the Router union type (CodeFn | LLMRouter) so deterministic and LLM routing are the same slot, switchable per-run."
- PRD §4.2: "per-node router" in the model layer. Same principle: the router is config, not structure.

---

### Decision 10: Lifecycle hooks — 5-stage, typed, async

**Choice:** Hooks are registered via `@agent.hook("pre_tool")` decorator or `agent.add_hook("pre_tool", fn)`. The five stages:

```
pre_model(ctx, bundle: ContextBundle) -> ContextBundle | None
post_model(ctx, response: ModelResponse) -> ModelResponse | None
pre_tool(ctx, call: ToolCall) -> ToolCall | PermissionDecision | None
post_tool(ctx, result: ToolResult) -> ToolResult | None
on_stop(ctx, result: AgentResult) -> None
```

A hook returning `None` passes through unchanged. A hook returning a modified object replaces it. `pre_tool` returning a `PermissionDecision` (`allow | deny | ask | defer`) intercepts tool execution without running the tool.

Hooks are **async by default** and run sequentially in registration order. On error, a hook that raises is logged and skipped (never breaks the run) — same discipline as ElizaOS `_dispatch_hook` (`fw-py-peers.md:332`: "error-isolated dispatch... a failing hook logs a warning, never interrupts the run").

**Evidence:**
- `fw-ts-peers.md:127` — AgentKit: `Agent.Lifecycle<T>` hooks: `enabled`, `onStart`, `onResponse`, `onFinish`. Verso adds `pre_model`/`post_model`/`pre_tool`/`post_tool` to match PRD §6.3 ("5-stage lifecycle hooks").
- `fw-py-peers.md:332` — Atomic Agents `_dispatch_hook`: error-isolated, warning-logged, never propagates.
- `fw-ts-peers.md:538` — ElizaOS Provider/Action/Evaluator triad maps to Verso's hook stages: providers = `pre_model` (context assembly), actions = tool execution, evaluators = `on_stop` (post-hoc reflection + memory write).
- PRD §6.3: "5-stage lifecycle hooks as the extensibility mechanism (not core-loop edits): `pre_model · post_model · pre_tool · post_tool · on_stop/on_error/on_idle`."

---

### Decision 11: Counter-position sharpening — where each peer cannot follow

The six Python peers and eight TS peers define the design space. Verso's counter-position is:

| Peer | Their ceiling | Why Verso is structurally uncopyable |
|---|---|---|
| **LangGraph** | Forced graph DSL, `DEFAULT_RECURSION_LIMIT=10007`, `compile({checkpointer})` changes the type | Cannot drop the graph — it's their installed base. Verso: "we don't force the graph." |
| **Burr** | State-machine-first (`@action(reads=[...], writes=[...])` + graph of actions) — the correct seam, wrong default surface | Their graph IS the product; Verso's loop is the product. Burr lacks context engineering, evals, typed memory tiers. |
| **Marvin** | Always durable (every message hits SQLAlchemy, no tactical mode), `Team` deprecated, LLM-delegated loop | No tactical path. Verso: same code, two runtimes. |
| **Atomic Agents** | Single typed LLM call (no loop), no durability, no memory | Too minimal. Verso adds the loop, durability seam, memory, evals. |
| **Griptape** | Good context-by-exclusion (TaskMemory), but graph-of-structures + verbose driver DSL | The driver abstraction is correct, the structure graph adds ceremony. |
| **Inngest AgentKit** | Forces in-network agents to `maxIter:0` — kills per-agent multi-step | Cannot give agents their own loop AND be re-routable; Verso can. |
| **CF Agents** | Durability = deployment target (DO), no in-memory mode, every state write hits SQLite | No tactical path, vendor-locked to Cloudflare. |
| **LangGraph.js** | Pregel/BSP graph, `StateGraph.compile()` — same as Python LangGraph | Same foil, TypeScript. |

**The one-sentence counter-position** (unchanged from PRD §12): *"We don't force the graph."*

The secondary counter-positions sharpened by this RE pass:
- *"Context engineering is first-class — `agent.inspect()` shows you exactly what the model sees, and no other framework ships this as a success criterion."*
- *"Evals are in the box — not an afterthought, not a separate service."*
- *"The seam works: same code, one flag, tactical or durable — zero frameworks ship this without either forcing a graph or forcing a runtime."*

---

## Component Spec

### `Agent` — the 90% path constructor

```python
@dataclass
class Agent(Generic[T]):
    model: str                              # "provider:model" — one string format globally
    tools: list[Callable] = field(default_factory=list)
    instructions: str | Callable[[RunContext], str] = ""
    memory: Memory | None = None            # None → no memory; Memory.default() → sqlite-vec
    max_steps: int = 25                     # visible default (not 10007)
    model_policy: ModelPolicy | None = None # fallback chain, require_parameters, etc.
    # --- knobs (override per-run via run/stream kwargs) ---
    effort: Literal["low", "medium", "high"] = "medium"
    verbosity: Literal["quick", "normal", "verbose"] = "normal"
```

Key invariants:
- `model` is parsed on first use via `init_model("provider:model")` — no object instantiation required at constructor time.
- `instructions` is accessible as `agent.instructions` — never hidden in a closure, never encrypted.
- `memory=None` means no memory writes/reads. `Memory.default()` is the opt-in that adds sqlite-vec.

### `run` / `stream` / `submit` signatures

```python
async def run(
    self,
    task: str,
    *,
    effort: Literal["low","medium","high"] | None = None,
    mode: Literal["plan","act","verify"] | None = None,
    durable: bool = False,
    **kwargs,
) -> AgentResult: ...

async def stream(
    self,
    task: str,
    *,
    effort: Literal["low","medium","high"] | None = None,
    durable: bool = False,
    **kwargs,
) -> AsyncIterable[StreamEvent]: ...

async def submit(
    self,
    task: str,
    *,
    effort: Literal["low","medium","high"] | None = None,
    **kwargs,
) -> RunHandle: ...

async def attach(
    self,
    run_id: str,
    *,
    starting_after: int | None = None,
) -> AsyncIterable[StreamEvent]: ...

def inspect(self) -> ContextBundle: ...
```

### `AgentResult`

```python
@dataclass(frozen=True)
class AgentResult:
    output: str
    stop_reason: StopReason           # NEVER None, NEVER a string
    usage: UsageStats                 # {input_tokens, output_tokens, cache_read, cache_write}
    cost_usd: float
    trace_id: str

class StopReason(str, Enum):
    end_turn = "end_turn"
    max_steps = "max_steps"
    max_tokens = "max_tokens"
    tool_rule_stop = "tool_rule_stop"
    cancelled = "cancelled"
    error = "error"
    budget_exhausted = "budget_exhausted"
    stuck = "stuck"
```

### `StreamEvent`

```python
@dataclass(frozen=True)
class StreamEvent:
    type: Literal[
        "message.delta",
        "reasoning.delta",
        "tool.start",
        "tool.result",
        "status",
        "error",
        "stream.end",
    ]
    seq: int          # monotonic, globally ordered across network + agent (AgentKit pattern)
    data: dict        # type-specific payload
```

True-delta invariant: every `message.delta.data["text"]` is an incremental chunk, never a full accumulation.

### `@tool` decorator

```python
@tool(
    read_only: bool = False,
    destructive: bool = False,
    idempotent: bool = True,
    timeout: float | None = None,
    max_result_chars: int | None = None,
)
async def my_tool(arg: str, ctx: RunContext) -> dict:
    """Docstring is required. Raises ValueError at decoration if empty."""
    ...
```

Rules enforced at decoration time (not runtime):
- Non-empty docstring → `ValueError("@tool 'my_tool' must have a non-empty docstring to serve as its LLM description")`. Stolen from Atomic Agents `BaseIOSchema._validate_description`.
- `ctx` parameter detected by name and filtered from the JSON schema sent to the model.
- `destructive=True` implies `idempotent=False` and `max_attempts=1` (auto-retrying state-changing actions is a correctness bug — PRD §5.3).

Dispatch return envelope (always, wraps any exception):
```python
@dataclass(frozen=True)
class ToolResult:
    data: Any          # None on error
    error: str | None  # None on success
    ok: bool
```

### `Memory.default()` — public interface

```python
class Memory:
    @staticmethod
    def default() -> "Memory":
        """Returns sqlite-vec backed memory (dev; zero-infra)."""
        ...

    async def remember(
        self,
        content: str,
        type: Literal["scratchpad","episodic","fact","procedural"] = "episodic",
        confidence: float = 1.0,
        scope: dict | None = None,   # {"user_id": ..., "agent_id": ..., "run_id": ...}
    ) -> str:                        # returns memory id
        ...

    async def recall(
        self,
        query: str,
        types: list[str] | None = None,
        scope: dict | None = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        ...

    async def recall_as_of(
        self,
        query: str,
        date: datetime,
        **kwargs,
    ) -> list[MemoryEntry]:
        ...
```

### `ContextBundle` — what `agent.inspect()` returns

```python
@dataclass(frozen=True)
class ContextBundle:
    instructions: str                  # the exact system prompt
    memory: list[MemoryEntry]          # retrieved memories (what was injected)
    history: list[Message]             # conversation turns in prompt order
    tools: list[dict]                  # JSON schemas as sent to the model
    retrieved: list[str]               # off-prompt content refs (Griptape-style exclusion)
    budget_used: int                   # tokens currently consumed
    budget_total: int                  # total window
```

`agent.inspect()` is a **dry-run of context assembly** — no model call, no tool call. It assembles the `ContextBundle` using the current memory state and the pending task (if any) and returns it. The formatted output (for human display) renders as markdown with labelled sections. Byte-equality to the wire payload is the success criterion.

### `ModelPolicy`

```python
@dataclass
class ModelPolicy:
    require_parameters: bool = True      # CRITICAL for tool agents (PRD §6.4 — a fallback that silently
                                         # drops tools returns text instead of a tool call)
    fallback: list[str] = field(default_factory=list)    # ["openai:gpt-5.1", "google:gemini-3-pro"]
    data_collection: bool = True
    max_price_per_1m_tokens: float | None = None
    sort: Literal["price","latency","quality"] = "quality"
```

### Lifecycle hooks — registration API

```python
# Decorator form:
@agent.hook("pre_tool")
async def gate(ctx: RunContext, call: ToolCall) -> ToolCall | PermissionDecision | None:
    return PermissionDecision.ask if call.tool.destructive else None

# Programmatic form:
agent.add_hook("pre_tool", gate)

# Hook stages and their I/O contracts:
HOOK_CONTRACTS = {
    "pre_model":  (RunContext, ContextBundle) -> ContextBundle | None,
    "post_model": (RunContext, ModelResponse) -> ModelResponse | None,
    "pre_tool":   (RunContext, ToolCall)      -> ToolCall | PermissionDecision | None,
    "post_tool":  (RunContext, ToolResult)    -> ToolResult | None,
    "on_stop":    (RunContext, AgentResult)   -> None,
    "on_error":   (RunContext, Exception)     -> None,
    "on_idle":    (RunContext,)               -> None,
}
```

Hook error isolation: any hook that raises is logged (WARNING level) and skipped. The run continues. Never propagates. (Atomic Agents `_dispatch_hook` pattern.)

### Multi-agent (separate import) — public surface

```python
from verso.orchestrate import Orchestration, fan_out, Handoff

# Pattern 1: parallel fan-out (no router)
results = await fan_out(
    tasks=["task A", "task B", "task C"],
    agent=worker_agent,              # or list of agents
    max_concurrency=4,
)

# Pattern 2: orchestrator-workers with a router
team = Orchestration(
    lead=orchestrator_agent,
    workers=[agent_a, agent_b, agent_c],
    router=lambda state: agent_a if state.last_result.needs_data else agent_b,  # code router
    # OR:
    router=routing_agent,            # LLM router (Agent instance) — same slot, isinstance dispatch
    pattern="orchestrator_workers",
)
result = await team.run("complex task")

# Pattern 3: handoff (control transfer, conversation carries)
handoff = Handoff(to=specialist_agent, description="Hands off to specialist for X")
agent = Agent(model=..., tools=[..., handoff])   # handoff is a tool the LLM calls

# Pattern 4: subagent-as-tool (call + return, caller keeps control)
sub = other_agent.as_tool(name="run_analysis", description="Runs deep analysis and returns summary")
agent = Agent(model=..., tools=[..., sub])
```

### Constants and defaults (attributed)

| Constant | Value | Source |
|---|---|---|
| `max_steps` default | `25` | PRD §10 item 1 (vs LangGraph's hidden 10007) |
| Stream `seq` counter | monotonic int, shared across network+agent | AgentKit `createContextWithSharedSequence` `fw-ts-peers.md:135` |
| Tool `max_concurrency` (read-only) | `5` | PRD §5.3 (from Hermes/Composio) |
| Tool `max_concurrency` (mutating) | `1` | PRD §5.3 |
| Fan-out `max_concurrency` | `4` | PRD §6.2 |
| Depth cap (nested orchestrators) | `1` by default | PRD §6.2 |
| `model_policy.require_parameters` | `True` | PRD §6.4 (OpenRouter: silent tools-drop) |
| Retry: `attempts` | `6` | PRD §6.4 (battle-tested) |
| Retry: `initial_interval` | `4s` | PRD §6.4 |
| Retry: `max_interval` | `240s` | PRD §6.4 |
| Stuck: repeated identical (action,args) | `4` | PRD §5.1 (OpenHands) |
| Stuck: error-loop | `3` | PRD §5.1 (OpenHands) |
| Hook error isolation | log + skip | Atomic Agents `_dispatch_hook` |
| `inspect()` | dry-run, byte-equal | PRD §9, W3 |

---

## Open Unknowns

1. **`Agent.from_yaml("agent.yaml")` scope** — PRD §7 mentions a YAML config path for "simple stateless agents." What fields belong in YAML vs code? Needs a concrete use-case before speccing — defer until Phase 0 dogfood reveals the repeating constructor pattern.

2. **`mode="plan"` three-phase gate UX** — PRD §5.1 describes a `PLANNING → EXECUTION → VERIFICATION` FSM enforced by a `task_boundary` tool. The API knob is `agent.run("...", mode="plan")`. What happens when mode is set and the agent is already mid-task (continuation)? Need to prototype: does mode apply per-`run()` call or per-session?

3. **`Handoff` as a tool vs `Handoff` as a top-level construct** — OpenAI Agents JS models handoff as a `transfer_to_<agent>` function tool discovered via `handoffs: Agent[]` on the Agent (and auto-named). Verso could do the same (Agent accepts `handoffs=[agent_b]`, framework auto-generates the tool) or require explicit `Handoff(to=agent_b)` in the `tools` list. The auto-generation is more ergonomic but more magical. Needs dogfooding to find the right trade-off.

4. **`fan_out` return type** — should it return `list[AgentResult]` (parallel, wait-all) or `AsyncIterable[AgentResult]` (yield as each completes)? Both are useful; `as_completed` semantics (yield as done) is more efficient for long tasks. Needs a real parallel task before deciding.

5. **`ctx.hitl.request()` in tactical mode** — in durable mode this is a checkpoint-backed pause. In tactical mode (no persister), the only sensible behavior is to block (await user input via stdin or a callback). Is there a default tactical HITL implementation, or is it a user-supplied callback? Needs to be resolved before Phase 2 begins.

6. **`agent.inspect()` formatting** — the spec says "byte-equal to wire payload" for correctness and "human-readable markdown" for the display. These conflict if the wire format is compact JSON. Resolution: `inspect()` returns the structured `ContextBundle` object; `print(agent.inspect())` is the formatted display; the object's `__repr__` is the wire-serializable form. The success criterion is `ContextBundle.to_wire() == actual_wire_payload`, not `str(bundle) == wire_str`. Need to confirm this interpretation holds across the eval suite in Phase 1.

7. **Plugin discovery for `model-providers`** (PRD §6.4: `~/.verso/plugins/model-providers/`, last-writer-wins) — the API shape for plugin-contributed model providers is not fully specified. ElizaOS's `models: {[ModelType]: handler}` plugin contribution is the right model but needs a Verso-specific registration API and priority/fallback resolution contract. Defer to Phase 0's second provider integration.
