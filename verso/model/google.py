# verso/model/google.py
from __future__ import annotations
from typing import Any, Sequence

from verso.model.base import Message, ModelResponse, ToolCall
from verso.tools.tool import Tool
from verso.types import Usage


class GoogleModel:
    """Gemini adapter (google-genai) implementing the Model Protocol. Mirrors AnthropicModel/OpenAIModel:
    lazy/injectable client, OMIT discipline, raw `extra_config` escape. Gemini specifics: assistant role
    is 'model', a separate system_instruction, parts-based content, function_call.args is a dict (not a
    JSON string), function_response is keyed by tool NAME (Gemini has no per-call ids)."""

    def __init__(self, model_id: str, *, client: Any = None, max_output_tokens: int | None = None,
                 temperature: float | None = None, top_p: float | None = None,
                 stop_sequences: list[str] | None = None, extra_config: dict | None = None):
        self.model_id = model_id
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.stop_sequences = stop_sequences
        self.extra_config = extra_config
        self._client = client  # injected in tests; created lazily in prod

    @property
    def client(self) -> Any:
        if self._client is None:
            from google import genai
            self._client = genai.Client()
        return self._client

    def _to_contents(self, messages: Sequence[Message]) -> list[dict]:
        contents: list[dict] = []
        for m in messages:
            if m.role == "user":
                contents.append({"role": "user", "parts": [{"text": m.content}]})
            elif m.role == "assistant":
                parts: list[dict] = []
                if m.content:
                    parts.append({"text": m.content})
                for tc in m.tool_calls:
                    parts.append({"function_call": {"name": tc.name, "args": tc.arguments}})
                contents.append({"role": "model", "parts": parts})
            elif m.role == "tool":
                contents.append({"role": "user", "parts": [
                    {"function_response": {"name": m.name, "response": {"result": m.content}}}
                ]})
        return contents

    def _to_tools(self, tools: Sequence[Tool]) -> list[dict]:
        return [{"function_declarations": [
            {"name": t.name, "description": t.description, "parameters": t.parameters} for t in tools
        ]}]

    async def complete(self, messages: Sequence[Message], tools: Sequence[Tool],
                       *, system: str | None = None) -> ModelResponse:
        config: dict[str, Any] = {}
        if system:
            config["system_instruction"] = system
        if tools:
            config["tools"] = self._to_tools(tools)
        for key, val in (("max_output_tokens", self.max_output_tokens), ("temperature", self.temperature),
                         ("top_p", self.top_p), ("stop_sequences", self.stop_sequences)):
            if val is not None:
                config[key] = val
        if self.extra_config:
            config.update(self.extra_config)
        kwargs: dict[str, Any] = {"model": self.model_id, "contents": self._to_contents(messages)}
        if config:
            kwargs["config"] = config
        resp = await self.client.aio.models.generate_content(**kwargs)

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for part in resp.candidates[0].content.parts:
            if getattr(part, "text", None):
                text_parts.append(part.text)
            fc = getattr(part, "function_call", None)
            if fc is not None:
                tool_calls.append(ToolCall(id=getattr(fc, "id", None) or fc.name,
                                           name=fc.name, arguments=dict(fc.args or {})))
        um = resp.usage_metadata
        return ModelResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            usage=Usage(input_tokens=getattr(um, "prompt_token_count", 0) or 0,
                        output_tokens=getattr(um, "candidates_token_count", 0) or 0),
        )
