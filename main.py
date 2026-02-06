"""
PreisHai - European Price Comparison Tool
Searches Google Shopping across EU markets and displays the 20 cheapest offers.
"""

import sys
import logging

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from app.gui import MainWindow


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )


def main():
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("PreisHai")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("PreisHai")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
