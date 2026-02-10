"""Ollama lifecycle manager: detect, install, start, stop."""

import logging
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class OllamaManager:
    """Manages the Ollama binary: detection, installation, server lifecycle."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self._process: subprocess.Popen | None = None
        self._ollama_path: str | None = None
        self.base_url = base_url.rstrip("/")

    # --- Detection ---

    def find_ollama(self) -> str | None:
        """Find the ollama binary. Returns path or None."""
        if self._ollama_path:
            return self._ollama_path

        # Check PATH first
        path = shutil.which("ollama")
        if path:
            self._ollama_path = path
            logger.info("Ollama found in PATH: %s", path)
            return path

        # Check common install locations
        system = platform.system()
        candidates = []
        if system == "Linux":
            candidates = [
                "/usr/local/bin/ollama",
                "/usr/bin/ollama",
                str(Path.home() / ".local" / "bin" / "ollama"),
            ]
        elif system == "Darwin":
            candidates = [
                "/usr/local/bin/ollama",
                "/opt/homebrew/bin/ollama",
            ]
        elif system == "Windows":
            local_app = os.environ.get("LOCALAPPDATA", "")
            if local_app:
                candidates.append(str(Path(local_app) / "Programs" / "Ollama" / "ollama.exe"))
            candidates.append(r"C:\Program Files\Ollama\ollama.exe")

        for candidate in candidates:
            if Path(candidate).is_file():
                self._ollama_path = candidate
                logger.info("Ollama found at: %s", candidate)
                return candidate

        logger.warning("Ollama not found on this system")
        return None

    def is_installed(self) -> bool:
        return self.find_ollama() is not None

    # --- Server management ---

    def is_server_running(self) -> bool:
        """Check if ollama serve is already running (by our process or externally)."""
        # Check our own managed process first
        if self._process and self._process.poll() is None:
            return True
        # Try connecting to the API
        import requests
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def start_server(self) -> bool:
        """Start ollama serve as a background subprocess."""
        if self.is_server_running():
            logger.info("Ollama server already running")
            return True

        ollama_path = self.find_ollama()
        if not ollama_path:
            logger.error("Cannot start server: ollama not found")
            return False

        try:
            system = platform.system()
            kwargs = {
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }
            if system == "Windows":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            self._process = subprocess.Popen(
                [ollama_path, "serve"],
                **kwargs,
            )
            logger.info("Started ollama serve (PID %d)", self._process.pid)

            # Wait for server to be ready (up to 15 seconds)
            for _ in range(30):
                time.sleep(0.5)
                if self.is_server_running():
                    logger.info("Ollama server is ready")
                    return True
                # Check if process crashed
                if self._process.poll() is not None:
                    logger.error("Ollama process exited with code %d", self._process.returncode)
                    self._process = None
                    return False

            logger.warning("Ollama server did not become ready in time")
            return False

        except Exception as e:
            logger.error("Failed to start ollama: %s", e)
            self._process = None
            return False

    def stop_server(self):
        """Stop our managed ollama server process."""
        if self._process and self._process.poll() is None:
            logger.info("Stopping ollama server (PID %d)...", self._process.pid)
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=3)
            logger.info("Ollama server stopped")
        self._process = None

    @property
    def is_managed_process(self) -> bool:
        """True if we started the server ourselves."""
        return self._process is not None and self._process.poll() is None

    # --- Installation ---

    def get_install_command(self) -> str:
        """Get the platform-specific install command/URL."""
        system = platform.system()
        if system in ("Linux", "Darwin"):
            return "curl -fsSL https://ollama.com/install.sh | sh"
        elif system == "Windows":
            return "https://ollama.com/download/OllamaSetup.exe"
        return ""

    def install_ollama(self, progress_callback=None) -> tuple[bool, str]:
        """Attempt to install Ollama. Returns (success, message)."""
        system = platform.system()

        if system in ("Linux", "Darwin"):
            try:
                if progress_callback:
                    progress_callback("Lade Ollama Installer herunter...")

                result = subprocess.run(
                    ["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode == 0:
                    self._ollama_path = None  # Reset cache to re-detect
                    if self.find_ollama():
                        return True, "Ollama erfolgreich installiert!"
                    return False, "Installation abgeschlossen, aber ollama nicht gefunden."
                return False, f"Installation fehlgeschlagen:\n{result.stderr[:200]}"
            except subprocess.TimeoutExpired:
                return False, "Installation Timeout (5 Min)"
            except Exception as e:
                return False, f"Installationsfehler: {e}"

        elif system == "Windows":
            try:
                if progress_callback:
                    progress_callback("Lade OllamaSetup.exe herunter...")

                import requests
                url = "https://ollama.com/download/OllamaSetup.exe"
                dl_path = Path.home() / "Downloads" / "OllamaSetup.exe"

                r = requests.get(url, stream=True, timeout=120)
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                downloaded = 0

                with open(dl_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total > 0:
                            pct = int(downloaded / total * 100)
                            progress_callback(f"Download: {pct}%")

                # Run installer
                if progress_callback:
                    progress_callback("Starte Installer...")
                subprocess.Popen([str(dl_path)], creationflags=subprocess.CREATE_NO_WINDOW)
                return True, f"Installer gestartet: {dl_path}\nBitte folge den Anweisungen."

            except Exception as e:
                return False, f"Download fehlgeschlagen: {e}"

        return False, f"Automatische Installation auf {system} nicht unterstützt."
