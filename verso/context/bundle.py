# verso/context/bundle.py
from __future__ import annotations
import json
from dataclasses import dataclass, field

from verso.context.tokens import estimate_tokens
from verso.model.base import Message
from verso.tools.tool import Tool


def _message_text(m: Message) -> str:
    parts = [m.content or ""]
    for tc in m.tool_calls:
        parts.append(f"{tc.name}({json.dumps(tc.arguments, sort_keys=True)})")
    return " ".join(p for p in parts if p)


@dataclass
class ContextBundle:
    """The named, inspectable assembly of everything sent to the model this turn."""
    instructions: str | None = None
    history: list[Message] = field(default_factory=list)
    tools: list[Tool] = field(default_factory=list)

    @property
    def system(self) -> str | None:
        return self.instructions

    def to_messages(self) -> list[Message]:
        return list(self.history)

    def tool_schema_text(self) -> str:
        # deterministic (sorted-key) serialization — the cache-stable tool prefix
        return json.dumps(
            [{"name": t.name, "description": t.description, "parameters": t.parameters} for t in self.tools],
            sort_keys=True,
        )

    def stable_prefix(self) -> str:
        # the KV-cache prefix: system + tool schemas; must be byte-identical across turns
        return (self.instructions or "") + "\n" + self.tool_schema_text()

    def sections(self) -> dict[str, int]:
        return {
            "instructions": estimate_tokens(self.instructions or ""),
            "tools": estimate_tokens(self.tool_schema_text()),
            "history": sum(estimate_tokens(_message_text(m)) for m in self.history),
        }

    def estimate_tokens(self) -> int:
        return sum(self.sections().values())

    def render(self) -> str:
        lines: list[str] = []
        if self.instructions:
            lines.append(f"[system]\n{self.instructions}")
        if self.tools:
            lines.append(f"[tools]\n{self.tool_schema_text()}")
        for m in self.history:
            extra = ""
            if m.tool_calls:
                extra = " -> " + ", ".join(
                    f"{tc.name}({json.dumps(tc.arguments, sort_keys=True)})" for tc in m.tool_calls
                )
            lines.append(f"[{m.role}] {m.content}{extra}")
        return "\n".join(lines)
