"""Config pin on resume — PRD §14.9.

"Checkpoint pins the full config (model version + system prompt + tool set), not just event state;
fast model-rollback is a named failure mode."

`instructions` (the system prompt) was already pinned and RESTORED from the checkpoint. The model id
and tool set were not: `resume_loop` rebuilt the bundle with `tools=list(tools)` — the CURRENT list —
and ran on whatever model the Agent happened to hold. So swapping a model or dropping a tool between
pause and resume silently continued the run as a different agent, replaying a history the old config
produced and re-dispatching the held tool call against the new registry.
"""
import pytest

from verso import Agent, ConfigDriftError, tool
from verso.durable.inmem import InMemoryCheckpointStore
from verso.durable.sqlite import SqliteCheckpointStore
from verso.safety.hooks import Hooks, PermissionDecision
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage, StopReason
from verso.core.loop import config_fingerprint, _drift


RAN: list[str] = []


@tool
def send_email(to: str) -> str:
    "Send an email."
    RAN.append(to)
    return f"sent to {to}"


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


def _fm(model_id: str = "fake-1") -> FakeModel:
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="send_email", arguments={"to": "x@y.z"})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    fm.model_id = model_id
    return fm


def _paused(store, *, model_id: str = "fake-1", tools=None):
    hooks = Hooks(pre_tool=[lambda call: PermissionDecision.ASK])
    return Agent(model=_fm(model_id), tools=tools if tools is not None else [send_email],
                 hooks=hooks, checkpointer=store)


def _finisher(store, *, model_id: str, tools=None):
    """An agent for the RESUME side. Its model is scripted with only the final turn: resume replays
    the held tool, then calls the model once. A fresh 2-response script would re-emit the tool call
    and pause again, which is a fixture artifact, not the behaviour under test."""
    fm = FakeModel([ModelResponse(text="done", tool_calls=[], usage=Usage())])
    fm.model_id = model_id
    hooks = Hooks(pre_tool=[lambda call: PermissionDecision.ASK])
    return Agent(model=fm, tools=tools if tools is not None else [send_email],
                 hooks=hooks, checkpointer=store)


# ---------------------------------------------------------------- the fingerprint


def test_fingerprint_is_order_insensitive_so_registration_order_is_not_drift():
    a = config_fingerprint("m", [send_email, add])
    b = config_fingerprint("m", [add, send_email])
    assert a == b
    assert a == {"model": "m", "tools": ["add", "send_email"]}


def test_legacy_checkpoint_without_config_is_never_drift():
    # Checkpoints written before this field existed carry config=None. Resuming them must behave
    # exactly as before rather than guessing at an identity we never recorded.
    assert _drift(None, config_fingerprint("anything", [add]), False) == []
    assert _drift({}, config_fingerprint("anything", [add]), False) == []


def test_drift_reports_model_and_both_directions_of_tool_change():
    was = {"model": "m1", "tools": ["a", "b"]}
    now = {"model": "m2", "tools": ["b", "c"]}
    lines = _drift(was, now, False)
    joined = "\n".join(lines)
    assert "m1" in joined and "m2" in joined
    assert "removed" in joined and "'a'" in joined
    assert "added" in joined and "'c'" in joined


def test_explicit_model_override_is_not_model_drift_but_still_catches_tools():
    was = {"model": "m1", "tools": ["a"]}
    # model_overridden=True → the caller used resume(model=…), the documented feature.
    assert _drift(was, {"model": "m2", "tools": ["a"]}, True) == []
    # …but an override must NOT smuggle a tool change past the guard.
    assert _drift(was, {"model": "m2", "tools": ["b"]}, True) != []


# ---------------------------------------------------------------- end to end


async def test_checkpoint_records_the_config_it_ran_under():
    store = InMemoryCheckpointStore()
    r = await _paused(store).run("email x")
    cp = store.load(r.resume_token)
    assert cp.config == {"model": "fake-1", "tools": ["send_email"]}


async def test_resume_with_the_same_config_still_works():
    RAN.clear()
    store = InMemoryCheckpointStore()
    agent = _paused(store)                    # same agent for both halves: the no-drift baseline
    r = await agent.run("email x")
    assert r.stop_reason == StopReason.PAUSED
    out = await agent.resume(r.resume_token, approve=True)
    assert out.stop_reason == StopReason.END_TURN
    assert RAN == ["x@y.z"]


async def test_resume_onto_a_different_model_raises_before_any_side_effect():
    RAN.clear()
    store = InMemoryCheckpointStore()
    r = await _paused(store, model_id="fake-1").run("email x")

    with pytest.raises(ConfigDriftError) as exc:
        await _paused(store, model_id="fake-2").resume(r.resume_token, approve=True)

    assert "fake-1" in str(exc.value) and "fake-2" in str(exc.value)
    # The guard must fire BEFORE the held tool is re-dispatched — that is the whole point.
    assert RAN == []


async def test_resume_with_a_removed_tool_raises():
    store = InMemoryCheckpointStore()
    r = await _paused(store, tools=[send_email, add]).run("email x")
    with pytest.raises(ConfigDriftError) as exc:
        await _paused(store, tools=[send_email]).resume(r.resume_token, approve=True)
    assert "removed" in str(exc.value) and "add" in str(exc.value)


async def test_allow_config_drift_opts_back_in():
    RAN.clear()
    store = InMemoryCheckpointStore()
    r = await _paused(store, model_id="fake-1").run("email x")
    out = await _finisher(store, model_id="fake-2").resume(
        r.resume_token, approve=True, allow_config_drift=True
    )
    assert out.stop_reason == StopReason.END_TURN
    assert RAN == ["x@y.z"]


async def test_explicit_model_override_resumes_without_tripping_the_guard():
    # README/docstring promise: "a paused/forked run can resume on a different model."
    RAN.clear()
    store = InMemoryCheckpointStore()
    r = await _paused(store, model_id="fake-1").run("email x")
    finisher = FakeModel([ModelResponse(text="done", tool_calls=[], usage=Usage())])
    finisher.model_id = "fake-2"
    out = await _paused(store, model_id="fake-1").resume(
        r.resume_token, approve=True, model=finisher
    )
    assert out.stop_reason == StopReason.END_TURN
    assert RAN == ["x@y.z"]


async def test_config_survives_the_sqlite_round_trip():
    store = SqliteCheckpointStore(":memory:")
    r = await _paused(store).run("email x")
    assert store.load(r.resume_token).config == {"model": "fake-1", "tools": ["send_email"]}
    with pytest.raises(ConfigDriftError):
        await _paused(store, model_id="other").resume(r.resume_token, approve=True)


def test_old_sqlite_blob_without_config_decodes_and_resumes_as_before():
    # Backward compat at the storage layer: a blob written by the previous version has no "config"
    # key at all. It must decode to config=None (not KeyError) so legacy runs stay resumable.
    import json
    store = SqliteCheckpointStore(":memory:")
    legacy = json.dumps({
        "version": 1, "trace_id": "old", "task": "t", "instructions": None,
        "history": [], "usage_in": 0, "usage_out": 0, "step": 1, "pending": None,
    })
    store.db.execute("INSERT INTO checkpoint(trace_id, data) VALUES(?,?)", ("old", legacy))
    store.db.commit()
    cp = store.load("old")
    assert cp is not None and cp.config is None
