from verso.tools.tool import tool_from_schema
from verso.tools.dispatch import dispatch
from verso.durable.context import RunContext


def test_from_schema_keeps_the_raw_schema_and_is_not_signature_introspected():
    schema = {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
    t = tool_from_schema("weather", "Get weather.", schema, lambda city: f"sunny in {city}")
    assert t.name == "weather" and t.description == "Get weather."
    assert t.parameters == schema           # raw schema preserved verbatim
    assert t.wants_ctx is False


async def test_from_schema_dispatches_with_passthrough_args():
    schema = {"type": "object", "properties": {"city": {"type": "string"}}}
    t = tool_from_schema("weather", "Get weather.", schema, lambda city: f"sunny in {city}")
    res = await dispatch(t, {"city": "NYC"})
    assert res.ok and res.data == "sunny in NYC"


async def test_from_schema_can_receive_ctx():
    schema = {"type": "object", "properties": {}}
    def grab(ctx) -> str:
        return ctx.deps["uid"]
    t = tool_from_schema("grab", "Grab uid.", schema, grab, wants_ctx=True)
    res = await dispatch(t, {}, ctx=RunContext(trace_id="x", deps={"uid": "u1"}))
    assert res.ok and res.data == "u1"
