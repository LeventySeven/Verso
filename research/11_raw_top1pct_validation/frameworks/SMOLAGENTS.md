# SMOLAGENTS — raw extraction (for Verso top-1% validation)

> Source read: `/Users/seventyleven/Desktop/researchfms/teardowns/SMOLAGENTS.md` (983 lines, full read).
> Upstream: `huggingface/smolagents`, Apache 2.0, commit `406520d` (`smolagents==1.27.0.dev0`).
> All findings labeled KNOWN(file:line from teardown) vs INFERRED.

---

## 0. The thesis: code-as-action

KNOWN (teardown §0, `agents.py:1505/1215`). smolagents is organized around ONE paradigm: **code-as-action**. Instead of emitting JSON tool calls, the `CodeAgent` emits **Python code blocks** executed in a sandboxed Python interpreter. "The 'tools' the LLM 'calls' are just Python functions in scope."

Two agent flavors, both subclass `MultiStepAgent(ABC)` (`agents.py:268`) and SHARE the `_run_stream` loop, memory, planning, callbacks, telemetry:
- **`CodeAgent`** (`agents.py:1505`) — "the marquee agent." LLM emits `<code>...</code>` blocks executed by AST interpreter.
- **`ToolCallingAgent`** (`agents.py:1215`) — conventional JSON-tool-call agent. "Useful for models that don't reliably emit code."

Claimed benefits of code-as-action (KNOWN §0):
- "One LLM emission can contain a multi-step program (control flow, variables, function composition) rather than one tool call per round-trip — fewer LLM calls, lower latency, lower cost."
- LLM's Python "can loop, branch, accumulate variables, and use built-in libraries within the same code block."
- "code-action agents take ~30% fewer steps on average" (HF benchmark figures, INFERRED).
- GAIA Open Level 1 ~44% with smolagents + open 70B models (INFERRED — public claim).

---

## 1. The minimal loop (`_run_stream`, `agents.py:540-611`) — KNOWN

```python
def _run_stream(self, task, max_steps, images=None):
    self.step_number = 1
    returned_final_answer = False
    while not returned_final_answer and self.step_number <= max_steps:   # :545
        if self.interrupt_switch: raise AgentError("Agent interrupted.") # :546
        # planning step on schedule (planning_interval)
        if planning_interval is not None and (step==1 or (step-1)%planning_interval==0):  # :550
            ... yield PlanningStep ...
        action_step = ActionStep(step_number=..., observations_images=images)  # :571
        try:
            for output in self._step_stream(action_step):                # :578
                yield output
                if isinstance(output, ActionOutput) and output.is_final_answer:  # :582
                    final_answer = output.output
                    if self.final_answer_checks: self._validate_final_answer(final_answer)  # :589
                    returned_final_answer = True
        except AgentGenerationError as e:
            raise e                      # :594  OUR bug -> EXIT
        except AgentError as e:
            action_step.error = e        # :597  MODEL error -> log into memory, ITERATE
        finally:
            self._finalize_step(...); self.memory.steps.append(action_step); yield action_step; step+=1
    if not returned_final_answer and step == max_steps+1:
        final_answer = self._handle_max_steps_reached(task)   # :607  ONE forced final LLM call
    yield FinalAnswerStep(handle_agent_output_types(final_answer))   # :609
```

**Error taxonomy (the key design, KNOWN §R2.4):** `AgentGenerationError` (a bug in *our* code / model API call) **re-raises and EXITS**; any other `AgentError` (model produced bad code/tool-call) is **caught, written into the step's `error`, loop CONTINUES** — model sees its own error next turn and self-corrects.

**Max-steps policy (KNOWN §R2.4, `:607,810`):** at `step_number > max_steps`, `_handle_max_steps_reached` / `provide_final_answer` does **ONE final LLM call** to extract a best-effort answer, with `AgentMaxStepsError` recorded.

**Retry coach line (KNOWN §R2.3, `memory.py:142`):** on an errored step, `ActionStep.to_messages()` appends verbatim:
> "Now let's retry: take care not to repeat previous errors! If you have retried several times, try a completely different approach."

`final_answer_checks: list[Callable]` (`:589`) = user predicates that can REJECT a final answer and force continuation.

---

## 2. CodeAgent `_step_stream` (`agents.py:1638-1764`) — KNOWN

One step: (1) `write_memory_to_messages()` → input messages (`:1646`); (2) generate with stop sequences `["Observation:", "Calling tools:"]` + the closing code tag (`:1651`) — closing tag as stop makes model halt right after the code block; (3) parse: `parse_code_blobs(output_text, code_block_tags)` then `fix_final_answer_code` (`:1708`); (4) wrap whole code as ONE `ToolCall(name="python_interpreter", arguments=code_action, id=f"call_{len(memory.steps)}")` (`:1715`); (5) execute `code_output = self.python_executor(code_action)` (`:1726`); (6) observation = `"Execution logs:\n{logs}" + "Last output from code snippet:\n{truncated}"` (`:1733,1753`); (7) `yield ActionOutput(output=..., is_final_answer=code_output.is_final_answer)` (`:1764`).

- `_use_structured_outputs_internally` → model returns JSON `{"code": ...}` via `CODEAGENT_RESPONSE_FORMAT` instead of tagged text (`:1658,1705`).
- closing code tag auto-appended to stored output if missing (`:1693`) to "nudge subsequent LLM calls to finish with this end code sequence."
- on unauthorized-import error, logs a hint to add the import to `additional_authorized_imports` (`:1745`).

Code parsing: configured tags first (`<code>...</code>`), falling back to markdown fences (`utils.py:212`). Regex `r"<code>\s*([\s\S]*?)\s*</code>"`.

`fix_final_answer_code` (KNOWN §3.11, `local_python_executor.py:332`): if last statement is a bare `Expr` and `final_answer` is a static tool, wraps it `final_answer(<expr>)`. "Improves success rate on weaker models."

---

## 3. The `final_answer` terminate trick (`local_python_executor.py:1583-1667`) — KNOWN, the heart of code-as-action

```python
if "final_answer" in static_tools:                 # :1630
    previous_final_answer = static_tools["final_answer"]
    def final_answer(*args, **kwargs):
        raise FinalAnswerException(previous_final_answer(*args, **kwargs))  # :1634
    static_tools["final_answer"] = final_answer
def _execute_code():
    try:
        for node in expression.body:
            result = evaluate_ast(node, state, static_tools, custom_tools, authorized_imports)  # :1643
        return result, False                        # is_final_answer=False
    except FinalAnswerException as e:
        return e.value, True                         # :1654  is_final_answer=True
    except Exception as e:
        raise InterpreterError(f"Code execution failed at line '{ast.get_source_segment(code, node)}' ...")  # :1659
```

**"the agent's 'I'm done' signal is just a tool call inside the executed code, not a separate protocol."** Errors wrapped with the exact failing source segment (`ast.get_source_segment`) so the model gets a precise retry target.

---

## 4. `LocalPythonExecutor` — AST interpreter sandbox (1768 L) — KNOWN, the novel primitive

Does NOT use `exec()`. `ast.parse(code)` then a hand-written recursive `evaluate_ast` (`:1417`) dispatching on ~50 node types (`Assign/AnnAssign/AugAssign/Call/Constant/Tuple/List/Set/Dict/GeneratorExp/ListComp/.../Lambda/FunctionDef/ClassDef/For/While/If/Try/Raise/Return/Break/Continue/Subscript/Attribute/JoinedStr/Name`). Anything not in dispatch → `InterpreterError(... not supported)`.

**Three-way DoS bound (the safety guarantee, KNOWN §R2.1):**
- `MAX_OPERATIONS = 10_000_000` (`:58`) — every AST node eval increments a counter; abort at cap.
- `MAX_WHILE_ITERATIONS = 1_000_000` (`:59`, enforced `:457`).
- `MAX_EXECUTION_TIME_SECONDS = 30` (`:60`) — wall clock via `timeout()` context manager (signal.alarm POSIX / threaded timer Windows), `ExecutionTimeoutError`. **[CORRECTION: 30s, not 60.]**

**Dunder block (`nodunder_getattr`, KNOWN §3.3, `:68`):**
```python
def nodunder_getattr(obj, name, default=None):
    if name.startswith("__") and name.endswith("__"):
        raise InterpreterError(f"Forbidden access to dunder attribute: {name}")
    return getattr(obj, name, default)
```
Blocks the escape family: `().__class__.__bases__[0].__subclasses__()`, `<func>.__globals__`, `<obj>.__dict__`. Enforced at EVERY `Attribute` eval (`:390`), not just explicit `getattr()`.

**`DANGEROUS_MODULES` (10, KNOWN `:130`):** `builtins, io, multiprocessing, os, pathlib, pty, shutil, socket, subprocess, sys` — NEVER importable even if in `authorized_imports`.

**`DANGEROUS_FUNCTIONS` (9, KNOWN `:143`):** `builtins.{compile,eval,exec,globals,locals,__import__}, os.popen, os.system, posix.system`.

**Import allow-list:** `check_import_authorized` walks a dotted-path tree (`build_import_tree`) — submodule-precise (`numpy.linalg` allowed iff `numpy`/`numpy.*`/`*` authorized). `get_safe_module` (`:1280`) recursively rebuilds an allowed module stripping dunder-exposing attributes. Default `BASE_BUILTIN_MODULES` (11, `utils.py:49`): `collections, datetime, itertools, math, queue, random, re, stat, statistics, time, unicodedata`. Stdlib-only, no network/fs.

**Safe builtins whitelist (KNOWN §3.2):** `print,range,enumerate,zip,len,min,max,sum,abs,round,pow,int,float,str,bool,list,tuple,dict,set,frozenset,bytes,bytearray,sorted,all,any,map,filter,ord,chr,next,iter,divmod,callable,getattr(=nodunder),hasattr,setattr,issubclass,type,complex` + exceptions + `custom_print`→`PrintContainer`. NOT included: `exec,eval,compile,__import__,globals,locals,dir,vars,id,memoryview,open,input,breakpoint,help`.

**Output cap:** `DEFAULT_MAX_LEN_OUTPUT = 50000` chars (`:57`), `PrintContainer` truncates.

**Control flow via sentinel exceptions:** `BreakException`, `ContinueException`, `ReturnException`. LLM-defined functions/classes supported (`create_function` closure captures body AST; `evaluate_class_def` via `type(name,bases,ns)`) — "LLM can write helper functions in step 1 and use them in step 2."

---

## 5. Five executor backends (`create_python_executor`, `agents.py:1598`) — KNOWN

`executor_type ∈ {local, blaxel, e2b, modal, docker}` (`:1599`):
- `local` → `LocalPythonExecutor` (AST interpreter).
- `e2b/docker/modal/blaxel` → `RemotePythonExecutor` subclasses ship code to a remote sandbox.

Executor interface: `__call__(code) -> (output, logs, is_final_answer)` + `send_tools(tools)` + `send_variables(state)`.

**Managed agents NOT supported with remote execution** (`:1608` raises) — sub-agents are injected as callables into the executor namespace, can't cross to a remote sandbox.

**Remote wire protocol (KNOWN §R2.11, `remote_executors.py`):**
- Var transport: prefix-tagged strings — `"safe:"+json` / `"pickle:"+base64(pickle)`. **`allow_pickle=False` by DEFAULT** (`:74`); docstring warns "Pickle deserialization can execute arbitrary code."
- `FinalAnswerException` crosses sandbox boundary as a string marker `FINAL_ANSWER_EXCEPTION = "FinalAnswerException"` (`:68`); `_deserialize_final_answer` rejects `pickle:` when `allow_pickle=False` (`:328`).
- pip install in sandbox: `!pip install {imports}` (`:139`).

---

## 6. ToolCallingAgent `_step_stream` (`agents.py:1276-1400`) — KNOWN, the contrast path

Generate with `tools_to_call_from=self.tools_and_managed_agents` (native provider tool-calling). If unstructured, `parse_tool_calls` extracts from text; args via `parse_json_if_needed`. `process_tool_calls` executes. Differences from CodeAgent:
- **Parallel tool calls** — `parallel_calls: dict[str, ToolCall]` (`:1373`) executes multiple calls from one turn.
- **Multiple final_answer guard** — rejects >1 tool_call when one is final_answer, or final_answer twice (`got_final_answer`) — one final answer per turn (`:1340`).
- **State var resolution** — if final answer string is a key in `self.state`, resolved to stored value (`:1354`).

Both agents share the §1 base loop + memory; differ only in `_step_stream`.

---

## 7. Memory (`memory.py`) — KNOWN, append-only, NO condenser

`AgentMemory(system_prompt)` holds `steps: list[MemoryStep]`. Typed steps: `TaskStep`, `PlanningStep`, `ActionStep`, `SystemPromptStep`, `FinalAnswerStep`. `ToolCall(name, arguments, id)`.

`ActionStep` (`:51-89`): `step_number, timing, model_input_messages, model_output_message, model_output, tool_calls, error, code_action (CodeAgent only), observations, observations_images, action_output, token_usage, is_final_answer`. Every step has `dict()` (JSON, replay/save) + `to_messages()` (context assembly). `write_memory_to_messages()` concatenates each step's `to_messages()`.

**Explicitly minimalist:** "There is no condenser / context-window manager built in — memory just grows. For long-horizon runs, users must wrap the model with their own truncation... Compared to OpenHands (`LLMSummarizingCondenser`), smolagents is intentionally minimalist here." (KNOWN §6.)

---

## 8. Tools & schema generation (`tools.py`, `_function_type_hints_utils.py`) — KNOWN

`Tool` (`tools.py:106`): `name, description, inputs: dict[str,dict], output_type: str, forward()`. `inputs/output_type` constrained to `AUTHORIZED_TYPES` (11, `:82`): `string, boolean, integer, number, image, audio, array, object, any, null` + `CONVERSION_DICT` (`str→string, int→integer, float→number`). `validate_arguments` enforces signature↔inputs match + nullable marking.

**`@tool` decorator path:** `get_json_schema(func)` (`_function_type_hints_utils.py:97`) builds schema from **type hints + docstring** (requires docstring; Google-style arg parsing; supports `(choices: ...)` enum blocks). "smolagents extracts the tool schema the same way OpenAI Agents SDK does (signature+docstring → JSON schema)" — but constrains to 11-type vocab because outputs can be images/audio (`AgentImage`/`AgentAudio`).

Default tools (`default_tools.py`): `PythonInterpreterTool, FinalAnswerTool, UserInputTool (HITL via input()), DuckDuckGoSearchTool, GoogleSearchTool (Serper), ApiWebSearchTool, WebSearchTool, VisitWebpageTool (→markdown), WikipediaSearchTool, SpeechToTextTool (Whisper)`. `add_base_tools=True` adds DDG + VisitWebpage (+ PythonInterpreter for ToolCalling only).

---

## 9. Managed agents = callables in the executor namespace (`agents.py:369-376,490-492`) — KNOWN

`_setup_managed_agents` requires each to have `name` + `description` (`assert all(agent.name and agent.description)`, `:373`); stored `self.managed_agents = {agent.name: agent}`. Before each CodeAgent run, `send_tools({**self.tools, **self.managed_agents})` injects them into executor namespace. "a sub-agent is just another callable the generated Python can invoke by name" — `result = research_agent("find X")` calls the managed agent's `__call__`, which runs its own full loop. Tree topology. No special protocol.

Parent's view of a sub-agent call = formatted report string (`managed_agent.report` template). Names must be unique across tools + managed_agents.

---

## 10. Constants table — KNOWN

| Constant | Value | Source |
|---|---|---|
| `MAX_OPERATIONS` (AST op cap) | 10_000_000 | `local_python_executor.py:58` |
| `MAX_WHILE_ITERATIONS` | 1_000_000 | `:59` |
| `MAX_EXECUTION_TIME_SECONDS` | 30 (corrected from 60) | `:60` |
| `DEFAULT_MAX_LEN_OUTPUT` | 50000 chars | `:57` |
| `DANGEROUS_MODULES` | 10 | `:130` |
| `DANGEROUS_FUNCTIONS` | 9 | `:143` |
| Default `max_steps` | 20 | `agents.py:278` |
| Default `planning_interval` | None (never plan) | `agents.py` |
| Default `executor_type` | "local" | CodeAgent |
| Default code tags | `("<code>", "</code>")` | `agents.py:1558` |
| Stop sequences (CodeAgent) | `["Observation:", "Calling tools:"]` + closing tag | `:1651` |
| `BASE_BUILTIN_MODULES` | 11 | `utils.py:49` |
| `AUTHORIZED_TYPES` (tool I/O) | 11 | `tools.py:82` |
| Final-answer signal | `FinalAnswerException` from patched `final_answer` | `:1634` |
| Remote pickle default | `allow_pickle=False` | `remote_executors.py:74` |

---

## 11. Verso relation verdict

**The big question — "agent writes code as its action": STEAL-ADDITIVE judged NO / largely OFF-THESIS for Verso.** Verso's stated path is "native @tool is THE path." Code-as-action would mean the action space is arbitrary model-written Python, which forces the entire `LocalPythonExecutor` complexity (1768-line AST interpreter, DANGEROUS_MODULES/FUNCTIONS lists, nodunder_getattr, three-way DoS bound, remote sandbox backends). That is exactly the "complexity-for-its-own-sake" Verso's law refuses, and it is NOT byte-identical-when-unused (it ships a whole interpreter + sandbox). A `PythonInterpreterTool`-as-one-`@tool` (the way ToolCallingAgent uses it) is the additive-safe version, and Verso already supports that via `@tool`. So: **avoid-overkill** as a default paradigm; the narrow sandboxed-code-execution-tool is achievable today with existing primitives.

What Verso already has (mapped): single clean loop, stuck/grace-at-max-steps + done() termination, @tool docstring→schema, structured-output reask, typed memory, Failover/Retry, HITL pause/resume, multi-provider, parallel tools.

Genuinely additive candidates are narrow (see structured output).
