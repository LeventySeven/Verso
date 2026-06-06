# verso/model/failover.py
from __future__ import annotations
from typing import Sequence

from verso.model.base import Message, Model, ModelResponse
from verso.model.errors import FAILOVERABLE, classify
from verso.model.retry import AttemptRecord, RetryPolicy, call_with_retry
from verso.tools.tool import Tool


class AllCandidatesFailed(Exception):
    def __init__(self, attempts: list[AttemptRecord]):
        self.attempts = attempts
        super().__init__("all model candidates failed; see .attempts")


class FailoverModel:
    """A Model that tries candidates in order, retrying each (call_with_retry) and advancing
    to the next on a FAILOVERABLE failure. AUTH/content-policy/other re-raise immediately.

    Note: ``.attempts`` records only the most recent ``complete()`` call — do not share one
    FailoverModel instance across concurrent runs if you intend to read ``.attempts``."""

    def __init__(self, candidates: Sequence[Model], *, retry: RetryPolicy | None = None,
                 require_parameters: bool = True):
        if not candidates:
            raise ValueError("FailoverModel needs at least one candidate")
        if require_parameters:
            for c in candidates:
                if getattr(c, "supports_tools", True) is False:
                    raise ValueError("require_parameters=True but a candidate cannot use tools")
        self.candidates = list(candidates)
        self.retry = retry or RetryPolicy()
        self.attempts: list[AttemptRecord] = []   # from the most recent complete()

    async def complete(self, messages: Sequence[Message], tools: Sequence[Tool],
                       *, system: str | None = None) -> ModelResponse:
        self.attempts = []
        last_exc: BaseException | None = None
        for candidate in self.candidates:
            try:
                return await call_with_retry(
                    lambda c=candidate: c.complete(messages, tools, system=system),
                    self.retry, records=self.attempts,
                )
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if classify(exc) not in FAILOVERABLE:
                    raise                      # auth/content-policy/other → do not try others
                # else: advance to the next candidate
        raise AllCandidatesFailed(self.attempts) from last_exc
