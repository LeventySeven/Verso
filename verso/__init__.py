# verso/__init__.py
import os

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
    Eval, Assertion, TraceCheck, VersoSpan, VersoScore, define_outcome, LLMJudge,
    JudgePanel, CalibrationReport, BestOfN, PredictReport, LiftReport, to_otel_attrs,
)
from verso.memory import Memory, MemoryType
from verso.memory.store import load_skills
from verso.scaffolds import Scaffold, find_scaffolds
from verso.safety.hooks import Hooks, PermissionDecision
from verso.safety.policy import (
    PermissionPolicy, PermissionRule, allow_all, ask_every, ask_once, confidence_router,
)
from verso.safety.reinforce import reinforce_objective
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
    "Eval", "Assertion", "TraceCheck", "VersoSpan", "VersoScore", "define_outcome", "LLMJudge",
    "JudgePanel", "CalibrationReport", "BestOfN", "PredictReport", "LiftReport", "to_otel_attrs",
    "Memory", "MemoryType", "load_skills",
    "Scaffold", "find_scaffolds",
    "Hooks", "PermissionDecision",
    "PermissionPolicy", "PermissionRule", "allow_all", "ask_every", "ask_once", "confidence_router",
    "reinforce_objective",
    "RunContext", "InMemoryCheckpointStore", "SqliteCheckpointStore",
]


# OpenAI-compatible providers: prefix -> (base_url, api_key_env). The whole zoo speaks the same
# Chat Completions wire format, so one OpenAIModel adapter reaches all of them by swapping base_url
# + key. `openai` itself has base_url None (the SDK default) so it stays byte-identical.
_OPENAI_COMPATIBLE = {
    "openai":     (None, "OPENAI_API_KEY"),
    "groq":       ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "together":   ("https://api.together.ai/v1", "TOGETHER_API_KEY"),
    "fireworks":  ("https://api.fireworks.ai/inference/v1", "FIREWORKS_API_KEY"),
    "deepseek":   ("https://api.deepseek.com/v1", "DEEPSEEK_API_KEY"),
    "xai":        ("https://api.x.ai/v1", "XAI_API_KEY"),
    "mistral":    ("https://api.mistral.ai/v1", "MISTRAL_API_KEY"),
    "ollama":     ("http://localhost:11434/v1", "OLLAMA_API_KEY"),
}


def init_model(spec: str, **kwargs):
    """Build a Model from a ``'provider:model_id'`` string; ``**kwargs`` pass through to the
    constructor (and override anything the registry inferred — e.g. a custom ``base_url`` /
    ``api_key`` / sampling params).

    Providers: ``anthropic``, ``google``, and every OpenAI-compatible endpoint in
    :data:`_OPENAI_COMPATIBLE` (``openai``, ``groq``, ``openrouter``, ``together``, ``fireworks``,
    ``deepseek``, ``xai``, ``mistral``, ``ollama``). For an OpenAI-compatible server not listed,
    construct :class:`~verso.model.openai.OpenAIModel` directly with its ``base_url``, or pass
    ``base_url=`` here via kwargs on the ``openai`` prefix.
    """
    provider, _, model_id = spec.partition(":")
    if provider == "anthropic":
        from verso.model.anthropic import AnthropicModel
        return AnthropicModel(model_id, **kwargs)
    if provider == "google":
        from verso.model.google import GoogleModel
        return GoogleModel(model_id, **kwargs)
    if provider in _OPENAI_COMPATIBLE:
        from verso.model.openai import OpenAIModel
        base_url, env = _OPENAI_COMPATIBLE[provider]
        opts: dict = {}
        if base_url:
            opts["base_url"] = base_url
        key = os.environ.get(env)
        if provider == "ollama":
            key = key or "ollama"      # local servers ignore the key but the OpenAI SDK requires a non-empty one
        if key:
            opts["api_key"] = key
        opts.update(kwargs)            # explicit kwargs win (custom base_url / api_key / params)
        return OpenAIModel(model_id, **opts)
    raise ValueError(
        f"unknown provider '{provider}' (supported: anthropic, google, "
        f"{', '.join(_OPENAI_COMPATIBLE)} — or construct the Model class directly for any "
        f"OpenAI-compatible base_url)"
    )
