# verso/durable/context.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from verso.types import Usage

T = TypeVar("T")


@dataclass
class HumanRequest:
    """A request for an out-of-band human decision that paused a durable run."""
    prompt: str
    key: str = "default"
    tool_name: str | None = None
    tool_call_id: str | None = None
    kind: str = "input"        # "input" = a tool asked via ctx.hitl.request; "approve" = a pre_tool ASK gate.


class Paused(Exception):
    """Raised to pause a durable run for human input. Carries the HumanRequest to surface."""
    def __init__(self, request: HumanRequest):
        super().__init__(request.prompt)
        self.request = request


class Hitl:
    """The human-in-the-loop handle on RunContext. On the first run `request()` raises Paused to pause
    the durable run; on RESUME the answer is pre-loaded (via `_resolve`) and `request()` returns it, so
    the re-running tool body continues past the call. Tools using this must be idempotent up to the
    request (no irreversible side-effect before it) — resume re-executes the tool from the top."""
    def __init__(self) -> None:
        self._answers: dict[str, object] = {}

    def request(self, prompt: str, *, key: str = "default"):
        if key in self._answers:
            return self._answers[key]            # resumed → return the human's answer
        raise Paused(HumanRequest(prompt=prompt, key=key, kind="input"))

    def _resolve(self, key: str, answer: object) -> None:
        self._answers[key] = answer


@dataclass
class RunContext(Generic[T]):
    """The typed run context threaded through a durable run. `deps` is the caller's typed payload.
    `store` being non-None is THE flag that makes a run durable; when None the run is tactical."""
    trace_id: str
    deps: T | None = None
    step: int = 0
    usage: Usage = field(default_factory=Usage)        # read-only view: cumulative usage at the tool's/hook's turn
    messages: list = field(default_factory=list)        # read-only view: a live ref to the run's history
    model: str = ""                                     # read-only view: the model id driving this run ("" if unknown)
    store: object | None = None        # CheckpointStore | None — typed as object to avoid an import cycle
    hitl: Hitl = field(default_factory=Hitl)
