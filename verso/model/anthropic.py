# verso/model/anthropic.py
from __future__ import annotations
from typing import Any, Sequence

from verso.model.base import Message, ModelResponse, ToolCall
from verso.tools.tool import Tool
from verso.types import Usage

DEFAULT_MAX_TOKENS = 4096


class AnthropicModel:
    def __init__(self, model_id: str, *, client: Any = None, max_tokens: int = DEFAULT_MAX_TOKENS):
        self.model_id = model_id
        self.max_tokens = max_tokens
        self._client = client  # injected in tests; created lazily in prod

    @property
    def client(self) -> Any:
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic()
        return self._client

    def _to_anthropic_messages(self, messages: Sequence[Message]) -> list[dict]:
        out: list[dict] = []
        for m in messages:
            if m.role == "user":
                out.append({"role": "user", "content": m.content})
            elif m.role == "assistant":
                blocks: list[dict] = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    blocks.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
                out.append({"role": "assistant", "content": blocks})
            elif m.role == "tool":
                out.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": m.tool_call_id, "content": m.content}
                ]})
        return out

    def _to_anthropic_tools(self, tools: Sequence[Tool]) -> list[dict]:
        return [{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tools]

    async def complete(self, messages: Sequence[Message], tools: Sequence[Tool],
                       *, system: str | None = None) -> ModelResponse:
        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "max_tokens": self.max_tokens,
            "messages": self._to_anthropic_messages(messages),
        }
        anthropic_tools = self._to_anthropic_tools(tools) if tools else None
        if system:
            # One ephemeral cache breakpoint on the system block. Render order is tools → system →
            # messages, so this single breakpoint caches the whole byte-stable prefix (tools + system);
            # the per-turn messages after it stay uncached. (Silently no-ops below the model's min prefix.)
            kwargs["system"] = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
            if anthropic_tools:
                kwargs["tools"] = anthropic_tools
        elif anthropic_tools:
            # No system prompt → move the single breakpoint to the last tool so the tool prefix still caches.
            anthropic_tools[-1] = {**anthropic_tools[-1], "cache_control": {"type": "ephemeral"}}
            kwargs["tools"] = anthropic_tools
        resp = await self.client.messages.create(**kwargs)

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
            elif getattr(block, "type", None) == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=dict(block.input)))

        return ModelResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            usage=Usage(input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens),
        )
