# verso/__init__.py
from verso.agent import Agent
from verso.tools.tool import tool, Tool
from verso.tools.coerce import CoercionError, StructuredOutputError
from verso.types import AgentResult, StopReason, Usage
from verso.model.base import Model, Message, ModelResponse, ToolCall

__version__ = "0.0.1"
__all__ = [
    "Agent", "tool", "Tool", "AgentResult", "StopReason", "Usage",
    "Model", "Message", "ModelResponse", "ToolCall", "init_model",
    "CoercionError", "StructuredOutputError",
]


def init_model(spec: str):
    """Build a Model from a 'provider:model_id' string. Only 'anthropic' in Phase 0."""
    provider, _, model_id = spec.partition(":")
    if provider == "anthropic":
        from verso.model.anthropic import AnthropicModel
        return AnthropicModel(model_id)
    raise ValueError(f"unknown provider '{provider}' (Phase 0 supports 'anthropic')")
