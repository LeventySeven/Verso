# verso/model/openai.py
from __future__ import annotations
import json
from typing import Any, Sequence

from verso.model.base import Message, ModelResponse, ToolCall
from verso.tools.tool import Tool
from verso.types import Usage


class OpenAIModel:
    """Chat Completions adapter, mirroring :class:`AnthropicModel` behind the ``Model`` Protocol.

    Works with ANY OpenAI-compatible endpoint — not just OpenAI. Groq, OpenRouter, Together,
    Fireworks, DeepSeek, xAI (Grok), Mistral, and local servers (Ollama, vLLM) all speak the same
    Chat Completions wire format at a different ``base_url`` + API key. Point this model at one by
    passing ``base_url=`` + ``api_key=``, or use the registry shortcut ``init_model("groq:…")``.

    The client is lazy and injectable: pass ``client=`` (used by tests) or let it construct an
    ``AsyncOpenAI`` on first use. Sampling params follow OMIT discipline — only keys the user set
    are sent, so an unconfigured model is byte-identical to the minimal request. ``extra_body`` /
    ``extra_headers`` are the escape hatch for anything not modeled here. Note ``max_tokens``
    defaults to ``None`` (omitted): OpenAI does not require it, and o-series models reject it in
    favor of ``max_completion_tokens`` — set ``max_tokens=N`` for chat models, or pass
    ``extra_body={"max_completion_tokens": N}`` for o-series. No ``stream`` method by design: the
    framework wraps ``complete()`` for streaming.
    """

    def __init__(self, model_id: str, *, client: Any = None, base_url: str | None = None,
                 api_key: str | None = None, max_tokens: int | None = None,
                 temperature: float | None = None, top_p: float | None = None,
                 stop: list[str] | None = None, extra_body: dict | None = None,
                 extra_headers: dict | None = None):
        self.model_id = model_id
        self.base_url = base_url
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.stop = stop
        self.extra_body = extra_body
        self.extra_headers = extra_headers
        self._client = client  # injected in tests; created lazily in prod

    @property
    def client(self) -> Any:
        if self._client is None:
            from openai import AsyncOpenAI
            opts: dict[str, Any] = {}
            if self.base_url:
                opts["base_url"] = self.base_url
            if self.api_key:
                opts["api_key"] = self.api_key
            self._client = AsyncOpenAI(**opts)
        return self._client

    def _to_openai_messages(self, messages: Sequence[Message], system: str | None) -> list[dict]:
        out: list[dict] = []
        if system:
            out.append({"role": "system", "content": system})
        for m in messages:
            if m.role == "user":
                out.append({"role": "user", "content": m.content})
            elif m.role == "assistant":
                msg: dict[str, Any] = {"role": "assistant", "content": m.content or None}
                if m.tool_calls:
                    msg["tool_calls"] = [
                        {"id": tc.id, "type": "function",
                         "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)}}
                        for tc in m.tool_calls
                    ]
                out.append(msg)
            elif m.role == "tool":
                out.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content})
        return out

    def _to_openai_tools(self, tools: Sequence[Tool]) -> list[dict]:
        return [{"type": "function",
                 "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
                for t in tools]

    async def complete(self, messages: Sequence[Message], tools: Sequence[Tool],
                       *, system: str | None = None) -> ModelResponse:
        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "messages": self._to_openai_messages(messages, system),
        }
        if tools:
            kwargs["tools"] = self._to_openai_tools(tools)
        for key, val in (("max_tokens", self.max_tokens), ("temperature", self.temperature),
                         ("top_p", self.top_p), ("stop", self.stop)):
            if val is not None:
                kwargs[key] = val
        if self.extra_body:
            kwargs["extra_body"] = self.extra_body
        if self.extra_headers:
            kwargs["extra_headers"] = self.extra_headers
        resp = await self.client.chat.completions.create(**kwargs)

        msg = resp.choices[0].message
        text = msg.content or ""
        tool_calls = [
            ToolCall(id=tc.id, name=tc.function.name,
                     arguments=json.loads(tc.function.arguments) if tc.function.arguments else {})
            for tc in (getattr(msg, "tool_calls", None) or [])
        ]
        usage = Usage(input_tokens=resp.usage.prompt_tokens, output_tokens=resp.usage.completion_tokens)
        return ModelResponse(text=text, tool_calls=tool_calls, usage=usage)
