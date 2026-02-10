"""Unzensierter KI Chat - Main Entry Point."""

import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from app.gui import MainWindow, DARK_STYLE


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

    app = QApplication(sys.argv)
    app.setApplicationName("Unzensierter KI Chat")
    app.setStyleSheet(DARK_STYLE)

    window = MainWindow()
    window.show()

    logger.info("Application ready.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
