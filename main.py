"""
Anus Scraper - European Price Comparison Tool
Scrapes Geizhals.de and Google Shopping for the cheapest European offers.
"""

import sys
import os
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from app.gui import MainWindow
from app.splash import SplashScreen


def setup_logging():
    log_dir = Path(os.path.expanduser("~")) / "AnusScraper_debug"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "anusscraper.log"

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(str(log_file), encoding="utf-8"),
        ],
    )


def main():
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("Anus Scraper")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Anus Scraper")

    window = MainWindow()

    splash = SplashScreen()
    splash.finished.connect(window.show)
    splash.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
