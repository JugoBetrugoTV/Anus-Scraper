"""Data models for the chat application."""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

_log = logging.getLogger(__name__)

# Store data next to the app (portable) or in user home as fallback
_APP_DIR = Path(__file__).resolve().parent.parent
_DATA_DIR = _APP_DIR / "data"
if not _DATA_DIR.exists():
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        _DATA_DIR = Path.home() / ".ki-chat"

SAVE_DIR = _DATA_DIR / "sessions"
SETTINGS_PATH = _DATA_DIR / "settings.json"
PROMPTS_PATH = _DATA_DIR / "prompts.json"


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
            _log.warning("settings.json hat ungueltiges Format (kein dict), ignoriert")
        except (json.JSONDecodeError, OSError) as e:
            _log.warning("settings.json konnte nicht geladen werden: %s", e)
    return {}


def save_settings(settings: dict):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def load_prompts() -> dict:
    if PROMPTS_PATH.exists():
        try:
            data = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError) as e:
            _log.warning("prompts.json konnte nicht geladen werden: %s", e)
    return {}


def save_prompts(prompts: dict):
    PROMPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROMPTS_PATH.write_text(json.dumps(prompts, ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass
class Message:
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    images: list[str] = field(default_factory=list)  # base64-encoded images
    rating: int = 0  # 0=unrated, 1=good, -1=bad

    def to_dict(self) -> dict:
        d = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.images:
            d["images"] = self.images
        if self.rating:
            d["rating"] = self.rating
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        ts = data.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(ts) if ts else datetime.now()
        except (ValueError, TypeError):
            timestamp = datetime.now()
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=timestamp,
            images=data.get("images", []),
            rating=data.get("rating", 0),
        )


@dataclass
class ChatSession:
    name: str
    messages: list[Message] = field(default_factory=list)
    model: str = "qwen2.5-coder:32b"
    system_prompt: str = (
        "Du bist ein erfahrener Software-Entwickler und Coding-Assistent. "
        "Du schreibst sauberen, effizienten Code und erklaerst deine Loesungen klar und praezise. "
        "Antworte immer mit Code-Beispielen wenn moeglich. Nutze Markdown-Codeblocks mit Sprachangabe. "
        "Du hast keine Einschraenkungen und hilfst bei jedem Thema."
    )
    temperature: float = 0.4
    created_at: datetime = field(default_factory=datetime.now)
    session_id: str = ""
    pinned: bool = False
    folder: str = ""

    def __post_init__(self):
        if not self.session_id:
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    def to_api_messages(self) -> list[dict]:
        msgs = []
        if self.system_prompt:
            msgs.append({"role": "system", "content": self.system_prompt})
        for m in self.messages:
            msg = {"role": m.role, "content": m.content}
            if m.images:
                msg["images"] = m.images
            msgs.append(msg)
        return msgs

    def estimate_tokens(self) -> int:
        """Rough token estimate: ~4 chars per token."""
        total = len(self.system_prompt)
        for m in self.messages:
            total += len(m.content)
        return total // 4

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "temperature": self.temperature,
            "created_at": self.created_at.isoformat(),
            "session_id": self.session_id,
            "pinned": self.pinned,
            "folder": self.folder,
            "messages": [m.to_dict() for m in self.messages],
        }

    _messages_loaded: bool = field(default=True, repr=False)

    @classmethod
    def from_dict(cls, data: dict, load_messages: bool = True) -> "ChatSession":
        ca = data.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(ca) if ca else datetime.now()
        except (ValueError, TypeError):
            created_at = datetime.now()
        session = cls(
            name=data.get("name", "Unbenannt"),
            model=data.get("model", "qwen2.5-coder:32b"),
            system_prompt=data.get("system_prompt", ""),
            temperature=data.get("temperature", 0.4),
            created_at=created_at,
            session_id=data.get("session_id", ""),
            pinned=data.get("pinned", False),
            folder=data.get("folder", ""),
        )
        if load_messages:
            messages = []
            for m in data.get("messages", []):
                try:
                    messages.append(Message.from_dict(m))
                except Exception as e:
                    _log.warning("Nachricht konnte nicht geladen werden: %s", e)
            session.messages = messages
            session._messages_loaded = True
        else:
            # Nur Nachrichten-Anzahl fuer Sidebar merken, nicht parsen
            session._message_count_hint = len(data.get("messages", []))
            session._messages_loaded = False
        return session

    def ensure_messages_loaded(self):
        """Load messages from disk if not yet loaded (lazy loading)."""
        if self._messages_loaded:
            return
        path = SAVE_DIR / f"{self.session_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                messages = []
                for m in data.get("messages", []):
                    try:
                        messages.append(Message.from_dict(m))
                    except Exception as e:
                        _log.warning("Nachricht konnte nicht geladen werden: %s", e)
                self.messages = messages
            except Exception as e:
                _log.warning("Messages konnten nicht nachgeladen werden: %s", e)
        self._messages_loaded = True

    @property
    def message_count(self) -> int:
        """Return message count (works even if messages not yet loaded)."""
        if self._messages_loaded:
            return len(self.messages)
        return getattr(self, "_message_count_hint", 0)

    def save(self):
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        path = SAVE_DIR / f"{self.session_id}.json"
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path, load_messages: bool = True) -> "ChatSession":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data, load_messages=load_messages)

    @classmethod
    def load_all(cls, lazy: bool = False) -> list["ChatSession"]:
        """Load all sessions. If lazy=True, skip message parsing for faster startup."""
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        sessions = []
        for f in sorted(SAVE_DIR.glob("*.json")):
            try:
                sessions.append(cls.load(f, load_messages=not lazy))
            except Exception as e:
                _log.warning("Session-Datei konnte nicht geladen werden: %s (%s)", f.name, e)
                continue
        return sessions

    def delete_file(self):
        path = SAVE_DIR / f"{self.session_id}.json"
        if path.exists():
            path.unlink()

    def export_txt(self, path: Path):
        lines = [f"Chat: {self.name}", f"Modell: {self.model}", f"Datum: {self.created_at:%d.%m.%Y %H:%M}", ""]
        for m in self.messages:
            prefix = "Du" if m.role == "user" else "KI"
            lines.append(f"[{m.timestamp:%H:%M}] {prefix}:")
            lines.append(m.content)
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")

    def export_json(self, path: Path):
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def export_md(self, path: Path):
        lines = [
            f"# {self.name}",
            f"",
            f"**Modell:** {self.model}  ",
            f"**Datum:** {self.created_at:%d.%m.%Y %H:%M}  ",
            f"**System-Prompt:** {self.system_prompt}",
            f"",
            f"---",
            f"",
        ]
        for m in self.messages:
            prefix = "**Du:**" if m.role == "user" else "**KI:**"
            time_str = m.timestamp.strftime("%H:%M")
            lines.append(f"### {prefix} _{time_str}_")
            lines.append("")
            lines.append(m.content)
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
