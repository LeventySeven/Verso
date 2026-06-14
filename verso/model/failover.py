# verso/model/failover.py
from __future__ import annotations
from dataclasses import replace
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

    With ``instant_failover=True`` (the default), a FAILOVERABLE failure on a candidate that
    still has a spare behind it advances to that spare immediately — the per-candidate retry
    ladder (and its backoff sleeps) is reserved for the LAST candidate, which has nowhere left
    to fail over to. Set ``instant_failover=False`` to retry every candidate to exhaustion
    before advancing (the old behavior).

    Note: ``.attempts`` records only the most recent ``complete()`` call — do not share one
    FailoverModel instance across concurrent runs if you intend to read ``.attempts``."""

    def __init__(self, candidates: Sequence[Model], *, retry: RetryPolicy | None = None,
                 require_parameters: bool = True, instant_failover: bool = True):
        if not candidates:
            raise ValueError("FailoverModel needs at least one candidate")
        if require_parameters:
            for c in candidates:
                if getattr(c, "supports_tools", True) is False:
                    raise ValueError("require_parameters=True but a candidate cannot use tools")
        self.candidates = list(candidates)
        self.retry = retry or RetryPolicy()
        self.instant_failover = instant_failover
        self.attempts: list[AttemptRecord] = []   # from the most recent complete()

    async def complete(self, messages: Sequence[Message], tools: Sequence[Tool],
                       *, system: str | None = None) -> ModelResponse:
        self.attempts = []
        last_exc: BaseException | None = None
        last_idx = len(self.candidates) - 1
        for i, candidate in enumerate(self.candidates):
            # Non-last candidates fail over instantly (no backoff) when instant_failover is on;
            # the last candidate always gets the full configured retry budget.
            policy = self.retry
            if self.instant_failover and i < last_idx:
                policy = replace(self.retry, max_attempts=1)
            try:
                return await call_with_retry(
                    lambda c=candidate: c.complete(messages, tools, system=system),
                    policy, records=self.attempts,
                )
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if classify(exc) not in FAILOVERABLE:
                    raise                      # auth/content-policy/other → do not try others
                # else: advance to the next candidate
        raise AllCandidatesFailed(self.attempts) from last_exc
