# tests/test_durable_checkpoint.py
import pytest
from verso.durable.checkpoint import Checkpoint
from verso.durable.inmem import InMemoryCheckpointStore
from verso.durable.context import HumanRequest


def _cp(trace_id="r1", step=2):
    return Checkpoint(
        trace_id=trace_id, task="do the thing", instructions="be terse",
        history=[{"role": "user", "content": "do the thing", "tool_calls": [], "tool_call_id": None, "name": None}],
        usage_in=10, usage_out=4, step=step,
        pending=HumanRequest(prompt="approve send_email?", tool_name="send_email", tool_call_id="t1"),
    )


@pytest.fixture(params=["inmem"])     # sqlite param added in a later batch
def store(request):
    return InMemoryCheckpointStore()


def test_save_then_load_round_trips(store):
    store.save(_cp())
    got = store.load("r1")
    assert got is not None
    assert got.trace_id == "r1" and got.step == 2 and got.task == "do the thing"
    assert got.pending is not None and got.pending.tool_name == "send_email"
    assert got.history[0]["content"] == "do the thing"


def test_load_missing_is_none_and_delete_removes(store):
    assert store.load("nope") is None
    store.save(_cp(trace_id="r2"))
    store.delete("r2")
    assert store.load("r2") is None
