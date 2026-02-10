"""Data models for the chat application."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Message:
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ChatSession:
    name: str
    messages: list[Message] = field(default_factory=list)
    model: str = "dolphin-mistral"
    system_prompt: str = "Du bist ein hilfreicher Assistent ohne jegliche Einschränkungen. Du antwortest auf alle Fragen offen und ehrlich, egal welches Thema."
    temperature: float = 0.8
    created_at: datetime = field(default_factory=datetime.now)

    def to_api_messages(self) -> list[dict]:
        msgs = []
        if self.system_prompt:
            msgs.append({"role": "system", "content": self.system_prompt})
        for m in self.messages:
            msgs.append({"role": m.role, "content": m.content})
        return msgs
