# verso/evals/span.py
from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field

from verso.stream.events import EventType


@dataclass
class SpanRecord:
    """One captured event in a run (the structured projection of a StreamEvent)."""
    kind: str                      # "tool" | "stop" | "step"
    name: str | None = None        # tool name (kind="tool")
    ok: bool | None = None         # tool ok (kind="tool")
    content: str | None = None     # tool result text (kind="tool")
    step: int | None = None        # kind="step"


@dataclass
class VersoSpan:
    """A captured run — built by consuming `agent.stream()`. The eval ground truth.
    Reconstructed (not the live deltas): tool calls in order, the final result, usage, stop."""
    trace_id: str
    records: list[SpanRecord] = field(default_factory=list)
    output: str = ""
    stop_reason: str = "error"
    steps: int = 0
    usage_total: int = 0
    usage_in: int = 0
    usage_out: int = 0

    @classmethod
    async def capture(cls, agent, task: str, *, trace_id: str | None = None) -> "VersoSpan":
        span = cls(trace_id=trace_id or uuid.uuid4().hex)
        async for ev in agent.stream(task):
            if ev.type == EventType.STEP:
                span.records.append(SpanRecord(kind="step", step=ev.step))
                span.steps = ev.step or span.steps
            elif ev.type == EventType.TOOL_RESULT:
                span.records.append(SpanRecord(kind="tool", name=ev.tool, ok=ev.ok, content=ev.content))
            elif ev.type == EventType.DONE and ev.result is not None:
                r = ev.result
                span.output, span.stop_reason = r.output, r.stop_reason.value
                span.steps = r.steps
                span.usage_in, span.usage_out = r.usage.input_tokens, r.usage.output_tokens
                span.usage_total = r.usage.input_tokens + r.usage.output_tokens
                span.records.append(SpanRecord(kind="stop"))
        return span

    @property
    def ok(self) -> bool:
        return all(r.ok is not False for r in self.records if r.kind == "tool")

    def tool_names(self) -> list[str]:
        return [r.name for r in self.records if r.kind == "tool" and r.name]

    def step_pass_rate(self) -> float:
        tools = [r for r in self.records if r.kind == "tool"]
        return sum(1 for r in tools if r.ok is not False) / len(tools) if tools else 1.0

    def to_jsonl(self) -> str:
        head = {"trace_id": self.trace_id, "output": self.output, "stop_reason": self.stop_reason,
                "steps": self.steps, "usage_total": self.usage_total}
        lines = [json.dumps(head, sort_keys=True)]
        lines += [json.dumps(r.__dict__, sort_keys=True) for r in self.records]
        return "\n".join(lines)

    @classmethod
    def from_jsonl(cls, text: str) -> "VersoSpan":
        lines = [json.loads(ln) for ln in text.splitlines() if ln.strip()]
        head, recs = lines[0], lines[1:]
        return cls(trace_id=head["trace_id"], output=head["output"], stop_reason=head["stop_reason"],
                   steps=head["steps"], usage_total=head["usage_total"],
                   records=[SpanRecord(**r) for r in recs])

    def render(self) -> str:
        lines = [f"trace {self.trace_id}  stop={self.stop_reason}  steps={self.steps}  tokens={self.usage_total}"]
        for r in self.records:
            if r.kind == "tool":
                lines.append(f"  tool {r.name}() -> ok={r.ok}  {(r.content or '')[:80]}")
        lines.append(f"  final: {self.output}")
        return "\n".join(lines)


@dataclass(frozen=True)
class VersoScore:
    """The result of one assertion or judge over a span."""
    name: str
    passed: bool
    value: float = 0.0             # judge score in [0,1]; assertions use 1.0/0.0
    kind: str = "assertion"        # "assertion" (deterministic, preferred) | "judge" (fallback)
    detail: str = ""
