# verso/__init__.py
from verso.agent import Agent
from verso.tools.tool import tool, Tool, tool_from_schema
from verso.tools.coerce import CoercionError, StructuredOutputError
from verso.tools.errors import Retry
from verso.types import AgentResult, StopReason, Usage
from verso.model.base import Model, Message, ModelResponse, ToolCall
from verso.context.bundle import ContextBundle
from verso.context.history import merge_messages, RemoveMessage, REMOVE_ALL_MESSAGES
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
from verso.safety.policy import (
    PermissionPolicy, PermissionRule, allow_all, ask_every, ask_once, confidence_router,
)
from verso.durable import RunContext, InMemoryCheckpointStore, SqliteCheckpointStore

__version__ = "0.0.1"
__all__ = [
    "Agent", "tool", "Tool", "tool_from_schema", "AgentResult", "StopReason", "Usage",
    "Model", "Message", "ModelResponse", "ToolCall", "init_model",
    "CoercionError", "StructuredOutputError", "Retry", "ContextBundle",
    "merge_messages", "RemoveMessage", "REMOVE_ALL_MESSAGES",
    "FailoverModel", "AllCandidatesFailed", "RetryPolicy", "AttemptRecord",
    "call_with_retry", "FailureKind", "classify",
    "StreamEvent", "EventType",
    "Eval", "Assertion", "VersoSpan", "VersoScore", "define_outcome", "LLMJudge",
    "JudgePanel", "to_otel_attrs",
    "Memory", "MemoryType",
    "Hooks", "PermissionDecision",
    "PermissionPolicy", "PermissionRule", "allow_all", "ask_every", "ask_once", "confidence_router",
    "RunContext", "InMemoryCheckpointStore", "SqliteCheckpointStore",
]


def init_model(spec: str):
    """Build a Model from a 'provider:model_id' string. Only 'anthropic' in Phase 0."""
    provider, _, model_id = spec.partition(":")
    if provider == "anthropic":
        from verso.model.anthropic import AnthropicModel
        return AnthropicModel(model_id)
    raise ValueError(f"unknown provider '{provider}' (Phase 0 supports 'anthropic')")
