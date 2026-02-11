"""Unzensierter KI Chat - Main Entry Point."""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Sicherstellen dass das Projektverzeichnis im Python-Pfad ist,
# egal von wo main.py gestartet wird (z.B. start.bat, Shortcut, etc.)
_APP_ROOT = str(Path(__file__).resolve().parent)
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from app.gui import MainWindow, DARK_STYLE, THEMES, _generate_stylesheet, _get_theme_colors, _set_active_theme
from app.ollama_manager import OllamaManager
from app.models import load_settings, save_settings


def setup_logging():
    app_dir = Path(__file__).resolve().parent
    log_dir = app_dir / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            RotatingFileHandler(
                log_dir / "chat.log", encoding="utf-8",
                maxBytes=5 * 1024 * 1024, backupCount=3,
            ),
            logging.StreamHandler(),
        ],
    )


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Unzensierter KI Chat...")

    # Set OLLAMA_MODELS to store models next to the app (same drive)
    app_dir = Path(__file__).resolve().parent
    models_dir = app_dir / "ollama_models"
    if not os.environ.get("OLLAMA_MODELS"):
        models_dir.mkdir(exist_ok=True)
        os.environ["OLLAMA_MODELS"] = str(models_dir)
        logger.info("OLLAMA_MODELS set to: %s", models_dir)

    # High-DPI support for Windows 11 fractional scaling (125%, 150%, etc.)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Initialize Ollama manager with configured URL
    settings = load_settings()
    base_url = settings.get("ollama_url", "http://localhost:11434")
    manager = OllamaManager(base_url=base_url)

    app = QApplication(sys.argv)
    app.setApplicationName("Unzensierter KI Chat")
    theme_name = settings.get("theme", "Blau (Standard)")
    theme = _get_theme_colors(theme_name)
    _set_active_theme(theme)
    app.setStyleSheet(_generate_stylesheet(theme))

    window = MainWindow(ollama_manager=manager)
    window.show()

    # Show setup wizard on first launch or if Ollama is not installed
    if not settings.get("setup_done") or not manager.is_installed():
        window.show_setup_wizard()
        # Only mark as done if Ollama is actually working now
        if manager.is_installed() and manager.is_server_running():
            settings["setup_done"] = True
            save_settings(settings)

    logger.info("Application ready.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
