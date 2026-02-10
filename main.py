"""Unzensierter KI Chat - Main Entry Point."""

import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from app.gui import MainWindow, DARK_STYLE, THEMES, _generate_stylesheet, _get_theme_colors, _set_active_theme
from app.ollama_manager import OllamaManager
from app.models import load_settings, save_settings


def setup_logging():
    log_dir = Path.home() / ".ki-chat" / "logs"
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

    # Initialize Ollama manager with configured URL
    settings = load_settings()
    base_url = settings.get("ollama_url", "http://localhost:11434")
    manager = OllamaManager(base_url=base_url)

    app = QApplication(sys.argv)
    app.setApplicationName("Unzensierter KI Chat")
    theme_name = settings.get("theme", "Lila (Standard)")
    theme = _get_theme_colors(theme_name)
    _set_active_theme(theme)
    app.setStyleSheet(_generate_stylesheet(theme))

    window = MainWindow(ollama_manager=manager)
    window.show()

    # Show setup wizard on first launch or if Ollama is not installed
    if not settings.get("setup_done") or not manager.is_installed():
        window.show_setup_wizard()
        settings["setup_done"] = True
        save_settings(settings)

    logger.info("Application ready.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
