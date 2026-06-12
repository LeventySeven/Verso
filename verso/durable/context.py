# verso/durable/context.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Generic, NoReturn, TypeVar

T = TypeVar("T")


@dataclass
class HumanRequest:
    """A request for an out-of-band human decision that paused a durable run."""
    prompt: str
    key: str = "default"
    tool_name: str | None = None
    tool_call_id: str | None = None


class Paused(Exception):
    """Raised to pause a durable run for human input. Carries the HumanRequest to surface."""
    def __init__(self, request: HumanRequest):
        super().__init__(request.prompt)
        self.request = request


class Hitl:
    """The human-in-the-loop handle on RunContext. `request()` pauses the run (durable) by raising
    Paused; the loop catches it, checkpoints, and returns a PAUSED AgentResult."""
    def request(self, prompt: str, *, key: str = "default") -> NoReturn:
        raise Paused(HumanRequest(prompt=prompt, key=key))


@dataclass
class RunContext(Generic[T]):
    """The typed run context threaded through a durable run. `deps` is the caller's typed payload.
    `store` being non-None is THE flag that makes a run durable; when None the run is tactical."""
    trace_id: str
    deps: T | None = None
    step: int = 0
    store: object | None = None        # CheckpointStore | None — typed as object to avoid an import cycle
    hitl: Hitl = field(default_factory=Hitl)
