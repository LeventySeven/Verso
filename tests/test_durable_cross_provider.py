# tests/test_durable_cross_provider.py
# D1: the durable seam promises a paused run resumes on a DIFFERENT provider. msg_to_dict/msg_from_dict
# store the NEUTRAL internal Message shape (role/content/tool_calls(id,name,arguments)/tool_call_id/name)
# — never Anthropic `tool_use` or OpenAI `tool_calls`/`function` wire formats. These tests prove that:
# pause under model A, resume under model B, and assert the serialized history carried no provider shape
# (the resuming adapter re-serializes the neutral history to ITS wire format on the next call). They also
# pin the forward-compat `version` marker and its tolerant absence in old blobs.
import json

from verso import Agent, tool
from verso.durable.inmem import InMemoryCheckpointStore
from verso.durable.sqlite import SqliteCheckpointStore
from verso.safety.hooks import Hooks, PermissionDecision
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.model.openai import OpenAIModel
from verso.types import Usage, StopReason


RAN: list[str] = []


@tool
def send_email(to: str) -> str:
    "Send an email."
    RAN.append(to)
    return f"sent to {to}"


def _pause_under_model_a(store):
    """Model A produces an assistant turn with a tool call; an ASK gate pauses → PAUSED + checkpoint."""
    fm_a = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="send_email", arguments={"to": "x@y.z"})], usage=Usage()),
    ])
    hooks = Hooks(pre_tool=[lambda call: PermissionDecision.ASK])
    return Agent(model=fm_a, tools=[send_email], hooks=hooks, checkpointer=store)


# --- fake OpenAI client (mirrors tests/test_openai_model.py) so resume can drive a REAL adapter ---

class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Completions:
    def __init__(self, resp):
        self.kwargs = None
        self._resp = resp

    async def create(self, **kwargs):
        self.kwargs = kwargs            # capture the wire request the adapter built from neutral history
        return self._resp


class _Chat:
    def __init__(self, resp):
        self.completions = _Completions(resp)


class _OpenAIClient:
    def __init__(self, resp):
        self.chat = _Chat(resp)


def _openai_text_resp(text: str):
    msg = _Obj(content=text, tool_calls=None)
    return _Obj(choices=[_Obj(message=msg)], usage=_Obj(prompt_tokens=4, completion_tokens=2))


async def test_resume_on_a_different_fake_model_finishes():
    # checkpoint under model A, resume under a SECOND, distinct FakeModel B via resume(token, model=B)
    store = InMemoryCheckpointStore()
    agent = _pause_under_model_a(store)
    paused = await agent.run("email x")
    assert paused.stop_reason == StopReason.PAUSED and paused.resume_token

    RAN.clear()
    model_b = FakeModel([ModelResponse(text="all done", tool_calls=[], usage=Usage())])
    resumed = await agent.resume(paused.resume_token, approve=True, model=model_b)
    assert resumed.stop_reason == StopReason.END_TURN and resumed.output == "all done"
    assert RAN == ["x@y.z"]                          # the held tool actually ran on resume
    assert model_b.calls, "the continuation turn was served by model B, not model A"


async def test_resume_on_a_real_openai_adapter_reserializes_neutral_history():
    # The strongest proof: pause under a FakeModel, then resume under a REAL OpenAIModel whose injected
    # fake client continues the run. The adapter must rebuild the OpenAI wire format from the NEUTRAL
    # history alone — proving the checkpoint stored no provider-specific shape.
    store = InMemoryCheckpointStore()
    agent = _pause_under_model_a(store)
    paused = await agent.run("email x")
    assert paused.stop_reason == StopReason.PAUSED

    RAN.clear()
    client = _OpenAIClient(_openai_text_resp("done via openai"))
    model_b = OpenAIModel("gpt-x", client=client)
    resumed = await agent.resume(paused.resume_token, approve=True, model=model_b)
    assert resumed.stop_reason == StopReason.END_TURN and resumed.output == "done via openai"
    assert RAN == ["x@y.z"]

    # the OpenAI adapter produced its OWN wire shape from the neutral history on the continuation call
    wire = client.chat.completions.kwargs["messages"]
    asst = next(m for m in wire if m["role"] == "assistant" and m.get("tool_calls"))
    # OpenAI-specific shape exists ONLY because the adapter built it now (it was NOT in the checkpoint):
    assert asst["tool_calls"][0]["type"] == "function"
    assert asst["tool_calls"][0]["function"]["name"] == "send_email"
    assert any(m["role"] == "tool" and m["tool_call_id"] == "t1" for m in wire)


async def test_stored_history_dicts_contain_only_neutral_keys():
    # the checkpoint's serialized history must be the neutral Message shape — no Anthropic/OpenAI/Gemini keys.
    store = InMemoryCheckpointStore()
    paused = await _pause_under_model_a(store).run("email x")
    cp = store.load(paused.resume_token)
    assert cp is not None and cp.history

    allowed = {"role", "content", "tool_calls", "tool_call_id", "name", "id"}
    forbidden = {"tool_use", "input_schema", "function", "candidates", "function_call",
                 "function_response", "parts", "type"}
    for m in cp.history:
        assert set(m.keys()) <= allowed, f"non-neutral key in history dict: {set(m.keys()) - allowed}"
        assert not (set(m.keys()) & forbidden)
        for tc in m.get("tool_calls", []):
            assert set(tc.keys()) == {"id", "name", "arguments"}   # neutral tool-call shape, not provider wire


def _read_blob(store: SqliteCheckpointStore, trace_id: str) -> dict:
    row = store.db.execute("SELECT data FROM checkpoint WHERE trace_id=?", (trace_id,)).fetchone()
    return json.loads(row[0])


async def test_sqlite_blob_has_version_marker_and_neutral_history(tmp_path):
    path = str(tmp_path / "ck.db")
    store = SqliteCheckpointStore(path)
    paused = await _pause_under_model_a(store).run("email x")

    blob = _read_blob(store, paused.resume_token)
    assert blob["version"] == 1                       # forward-compat marker is present in new blobs
    forbidden = {"tool_use", "input_schema", "function", "candidates", "function_call"}
    for m in blob["history"]:
        assert not (set(m.keys()) & forbidden)


def test_old_blob_without_version_still_loads(tmp_path):
    # a checkpoint written by an OLDER process (no `version` key, no `human_prompt` in pending) must still
    # load — load() reads specific keys and tolerates the marker's absence.
    path = str(tmp_path / "old.db")
    store = SqliteCheckpointStore(path)
    legacy = json.dumps({
        # NOTE: deliberately NO "version" key
        "trace_id": "old1", "task": "t", "instructions": None,
        "history": [
            {"role": "user", "content": "hi", "tool_calls": [], "tool_call_id": None, "name": None},
            {"role": "assistant", "content": "",
             "tool_calls": [{"id": "t1", "name": "send_email", "arguments": {"to": "x@y.z"}}],
             "tool_call_id": None, "name": None},
        ],
        "usage_in": 1, "usage_out": 2, "step": 1,
        # NOTE: legacy pending has NO "human_prompt" key
        "pending": {"prompt": "Approve tool 'send_email'?", "key": "default", "kind": "approve",
                    "tool_name": "send_email", "tool_call_id": "t1"},
    })
    store.db.execute("INSERT OR REPLACE INTO checkpoint(trace_id, data) VALUES(?, ?)", ("old1", legacy))
    store.db.commit()

    cp = store.load("old1")
    assert cp is not None
    assert cp.trace_id == "old1" and cp.step == 1 and cp.usage_in == 1 and cp.usage_out == 2
    assert cp.pending is not None and cp.pending.kind == "approve"
    assert cp.pending.tool_name == "send_email" and cp.pending.tool_call_id == "t1"
    assert cp.pending.human_prompt is None                   # absent in legacy → None
    assert cp.pending.display == "Approve tool 'send_email'?"  # falls back to prompt
    assert cp.history[1]["tool_calls"][0] == {"id": "t1", "name": "send_email", "arguments": {"to": "x@y.z"}}
