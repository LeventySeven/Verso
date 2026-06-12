# verso/__init__.py
from verso.agent import Agent
from verso.tools.tool import tool, Tool
from verso.tools.coerce import CoercionError, StructuredOutputError
from verso.types import AgentResult, StopReason, Usage
from verso.model.base import Model, Message, ModelResponse, ToolCall
from verso.context.bundle import ContextBundle
from verso.model.failover import FailoverModel, AllCandidatesFailed
from verso.model.retry import RetryPolicy, AttemptRecord, call_with_retry
from verso.model.errors import FailureKind, classify
from verso.stream.events import StreamEvent, EventType
from verso.evals import (
    Eval, Assertion, VersoSpan, VersoScore, define_outcome, LLMJudge,
    JudgePanel, to_otel_attrs,
)
from verso.memory import Memory, MemoryType
from verso.safety.hooks import Hooks, PermissionDecision
from verso.durable import RunContext, InMemoryCheckpointStore, SqliteCheckpointStore

__version__ = "0.0.1"
__all__ = [
    "Agent", "tool", "Tool", "AgentResult", "StopReason", "Usage",
    "Model", "Message", "ModelResponse", "ToolCall", "init_model",
    "CoercionError", "StructuredOutputError", "ContextBundle",
    "FailoverModel", "AllCandidatesFailed", "RetryPolicy", "AttemptRecord",
    "call_with_retry", "FailureKind", "classify",
    "StreamEvent", "EventType",
    "Eval", "Assertion", "VersoSpan", "VersoScore", "define_outcome", "LLMJudge",
    "JudgePanel", "to_otel_attrs",
    "Memory", "MemoryType",
    "Hooks", "PermissionDecision",
    "RunContext", "InMemoryCheckpointStore", "SqliteCheckpointStore",
]


def init_model(spec: str):
    """Build a Model from a 'provider:model_id' string. Only 'anthropic' in Phase 0."""
    provider, _, model_id = spec.partition(":")
    if provider == "anthropic":
        from verso.model.anthropic import AnthropicModel
        return AnthropicModel(model_id)
    raise ValueError(f"unknown provider '{provider}' (Phase 0 supports 'anthropic')")
