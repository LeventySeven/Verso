# tests/test_durable_timetravel.py
from __future__ import annotations
import pytest

from verso import Agent, tool
from verso.durable.inmem import InMemoryCheckpointStore
from verso.durable.sqlite import SqliteCheckpointStore
from verso.model.base import ModelResponse, ToolCall
from verso.model.fake import FakeModel
from verso.safety.hooks import Hooks, PermissionDecision
from verso.types import StopReason, Usage


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


@tool
def send_email(to: str) -> str:
    "Send an email."
    RAN.append(to)
    return f"sent to {to}"


RAN: list[str] = []   # records tool-body executions across fork branches


def _two_tool_then_finish() -> FakeModel:
    # step 1: add, step 2: add (both ALLOW → checkpointed, pending=None), step 3: finish (END_TURN, not checkpointed)
    return FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage()),
        ModelResponse(text="", tool_calls=[ToolCall(id="t2", name="add", arguments={"a": 3, "b": 4})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])


@pytest.mark.parametrize("make_store", [
    lambda tmp_path: InMemoryCheckpointStore(),
    lambda tmp_path: SqliteCheckpointStore(str(tmp_path / "ck.db")),
], ids=["inmem", "sqlite"])
async def test_history_retains_every_step_and_load_is_latest(make_store, tmp_path):
    store = make_store(tmp_path)
    agent = Agent(model=_two_tool_then_finish(), tools=[add], checkpointer=store)
    result = await agent.run("add twice")
    assert result.stop_reason == StopReason.END_TURN and result.output == "done"

    # steps 1 and 2 each checkpointed (the terminal END_TURN step 3 is not checkpointed by the loop).
    # resume_token is None on a clean finish, so pull the single trace_id from the store directly.
    trace_id = _only_trace(store)
    hist = store.history(trace_id)
    assert [c.step for c in hist] == [1, 2]                     # ascending, one per step
    assert all(c.pending is None for c in hist)                 # crash-recovery checkpoints, no human gate

    latest = store.load(trace_id)
    assert latest is not None and latest.step == hist[-1].step  # load == the last history entry (latest)
    assert latest.history == hist[-1].history
    assert latest.usage_in == hist[-1].usage_in and latest.usage_out == hist[-1].usage_out


def _only_trace(store) -> str:
    if isinstance(store, InMemoryCheckpointStore):
        (tid,) = store._cps.keys()
        return tid
    (tid,) = [r[0] for r in store.db.execute("SELECT trace_id FROM checkpoint").fetchall()]
    return tid


async def test_history_of_unknown_trace_is_empty():
    assert InMemoryCheckpointStore().history("nope") == []
    assert SqliteCheckpointStore().history("nope") == []


async def test_inmem_history_returns_deep_copies_not_aliases():
    # mutating a checkpoint handed out by history() must NOT corrupt the store (deep-copy discipline,
    # the property that keeps the in-memory store honest — fails if history() returns the stored ref).
    store = InMemoryCheckpointStore()
    agent = Agent(model=_two_tool_then_finish(), tools=[add], checkpointer=store)
    await agent.run("add twice")
    trace_id = _only_trace(store)

    leaked = store.history(trace_id)[0]                          # step-1 checkpoint
    leaked.step = -999
    leaked.history.append({"role": "user", "content": "tampered"})

    fresh = store.history(trace_id)[0]
    assert fresh.step == 1                                       # store untouched by the mutation
    assert all(m.get("content") != "tampered" for m in fresh.history)
    assert store.load(trace_id).step == 2                        # latest also intact


@pytest.mark.parametrize("make_store", [
    lambda tmp_path: InMemoryCheckpointStore(),
    lambda tmp_path: SqliteCheckpointStore(str(tmp_path / "ck.db")),
], ids=["inmem", "sqlite"])
async def test_delete_clears_history_and_load(make_store, tmp_path):
    store = make_store(tmp_path)
    agent = Agent(model=_two_tool_then_finish(), tools=[add], checkpointer=store)
    await agent.run("add twice")
    trace_id = _only_trace(store)
    assert store.history(trace_id) and store.load(trace_id) is not None
    store.delete(trace_id)
    assert store.history(trace_id) == []
    assert store.load(trace_id) is None


def _paused_agent(store, model: FakeModel | None = None) -> Agent:
    fm = model or FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="e1", name="send_email", arguments={"to": "x@y.z"})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    hooks = Hooks(pre_tool=[lambda call: PermissionDecision.ASK])
    return Agent(model=fm, tools=[send_email], hooks=hooks, checkpointer=store)


async def test_fork_branches_independently_from_a_paused_run():
    RAN.clear()
    store = InMemoryCheckpointStore()
    paused = await _paused_agent(store).run("email x")
    assert paused.stop_reason == StopReason.PAUSED and paused.pending is not None
    token = paused.resume_token

    before = agent_history_len(store, token)
    # a brand-new agent over the SAME store does the forking + resuming (its model finishes the branch)
    forker = _paused_agent(store, FakeModel([ModelResponse(text="branch-done", tool_calls=[], usage=Usage())]))
    new = forker.fork(token)
    assert new != token
    assert agent_history_len(store, token) == before          # forking did not touch the original's history
    assert forker.history(token)[-1].step == store.load(token).step

    resumed = await forker.resume(new, approve=True)
    assert resumed.stop_reason == StopReason.END_TURN and resumed.output == "branch-done"
    assert RAN == ["x@y.z"]                                    # branch approved → held tool ran once

    # the ORIGINAL token still resumes independently — the branch did not corrupt it
    RAN.clear()
    orig = _paused_agent(store, FakeModel([ModelResponse(text="orig-done", tool_calls=[], usage=Usage())]))
    resumed_orig = await orig.resume(token, approve=True)
    assert resumed_orig.stop_reason == StopReason.END_TURN and resumed_orig.output == "orig-done"
    assert RAN == ["x@y.z"]


def agent_history_len(store, token: str) -> int:
    return len(store.history(token))


async def test_fork_at_specific_pending_none_step_resumes_and_continues():
    store = InMemoryCheckpointStore()
    agent = Agent(model=_two_tool_then_finish(), tools=[add], checkpointer=store)
    await agent.run("add twice")
    trace_id = _only_trace(store)

    hist = store.history(trace_id)
    early = next(c for c in hist if c.pending is None)         # step 1, the earliest non-paused checkpoint
    assert early.step == 1

    # fork at step 1; resume RE-RUNS from cp.step+1 (=2) — give the branch a model that finishes there
    forker = Agent(model=FakeModel([ModelResponse(text="forked-finish", tool_calls=[], usage=Usage())]),
                   tools=[add], checkpointer=store)
    new = forker.fork(trace_id, at_step=early.step)
    assert new != trace_id
    forked_cp = store.load(new)
    assert forked_cp.step == 1 and forked_cp.pending is None   # the clone is the step-1 state

    resumed = await forker.resume(new)
    assert resumed.stop_reason == StopReason.END_TURN and resumed.output == "forked-finish"


async def test_fork_at_missing_step_raises():
    store = InMemoryCheckpointStore()
    agent = Agent(model=_two_tool_then_finish(), tools=[add], checkpointer=store)
    await agent.run("add twice")
    trace_id = _only_trace(store)
    with pytest.raises(ValueError):
        agent.fork(trace_id, at_step=9999)


async def test_history_and_fork_require_a_checkpointer():
    agent = Agent(model=FakeModel([ModelResponse(text="x", tool_calls=[], usage=Usage())]), tools=[])
    with pytest.raises(ValueError):
        agent.history("x")
    with pytest.raises(ValueError):
        agent.fork("x")
