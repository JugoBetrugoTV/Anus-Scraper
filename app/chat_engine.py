"""Chat engine with Ollama API integration for local LLM inference."""

import json
import requests
from typing import Generator

DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaClient:
    """Client for the Ollama REST API."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def set_base_url(self, url: str):
        self.base_url = url.rstrip("/")

    def is_available(self) -> bool:
        try:
            r = self.session.get(f"{self.base_url}/api/tags", timeout=3)
            return r.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            return False

    def list_models(self) -> list[str]:
        try:
            r = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            r.raise_for_status()
            data = r.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def chat_stream(
        self,
        messages: list[dict],
        model: str = "dolphin-mistral",
        temperature: float = 0.8,
    ) -> Generator[str, None, None]:
        """Stream chat completion tokens from Ollama."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
            },
        }
        try:
            r = self.session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=(10, 300),
            )
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
        except requests.ConnectionError:
            yield "\n\n[FEHLER] Keine Verbindung zu Ollama. Starte Ollama mit: ollama serve"
        except requests.Timeout:
            yield "\n\n[FEHLER] Timeout - Ollama antwortet nicht."
        except Exception as e:
            yield f"\n\n[FEHLER] {e}"

    def pull_model(self, model: str) -> Generator[dict, None, None]:
        """Pull/download a model with progress updates."""
        try:
            r = self.session.post(
                f"{self.base_url}/api/pull",
                json={"name": model, "stream": True},
                stream=True,
                timeout=(10, 600),
            )
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    chunk = json.loads(line)
                    yield chunk
        except Exception as e:
            yield {"status": f"[FEHLER] {e}", "error": True}
