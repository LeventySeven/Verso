# verso/tools/errors.py
from __future__ import annotations


class Retry(Exception):
    """Raise from a tool body OR an output validator to tell the model WHY its output was wrong and let
    it try again — the self-healing signal. The feedback becomes a model-visible message; a per-tool /
    per-output retry budget bounds it. (Unlike returning an error, this explicitly re-asks the model.)"""
    def __init__(self, feedback: str):
        super().__init__(feedback)
        self.feedback = feedback
