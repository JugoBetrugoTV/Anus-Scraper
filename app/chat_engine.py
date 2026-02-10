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
        r = self.session.post(
            f"{self.base_url}/api/chat",
            json=payload,
            stream=True,
            timeout=(10, 300),
        )
        r.raise_for_status()
        try:
            for line in r.iter_lines():
                if line:
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
        finally:
            r.close()

    def delete_model(self, model: str) -> bool:
        """Delete a model from Ollama."""
        try:
            r = self.session.delete(
                f"{self.base_url}/api/delete",
                json={"name": model},
                timeout=10,
            )
            return r.status_code == 200
        except Exception:
            return False

    def pull_model(self, model: str) -> Generator[dict, None, None]:
        """Pull/download a model with progress updates."""
        r = None
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
        finally:
            if r is not None:
                r.close()
