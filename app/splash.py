"""
Animated splash / intro screen for Anus Scraper.

Shows a cinematic loading screen with progress animation before
the main window appears.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar,
    QGraphicsDropShadowEffect, QApplication,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont


class SplashScreen(QDialog):
    """Frameless animated splash screen with progress bar."""

    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setFixedSize(640, 400)
        self.setStyleSheet("background-color: #080818;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 40, 50, 30)
        layout.setSpacing(0)

        layout.addStretch(3)

        # ── Title with glow ────────────────────────────────
        self._title = QLabel("ANUS SCRAPER")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setFont(QFont("Segoe UI", 38, QFont.Weight.Black))
        self._title.setStyleSheet("color: #ffffff; background: transparent;")

        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(40)
        glow.setColor(QColor("#6366f1"))
        glow.setOffset(0, 0)
        self._title.setGraphicsEffect(glow)

        layout.addWidget(self._title)

        # ── Gradient accent line ───────────────────────────
        line = QLabel()
        line.setFixedHeight(3)
        line.setStyleSheet(
            "background: qlineargradient("
            "  x1:0, y1:0, x2:1, y2:0,"
            "  stop:0 transparent, stop:0.15 #6366f1,"
            "  stop:0.5 #a78bfa, stop:0.85 #6366f1,"
            "  stop:1 transparent"
            ");"
            "margin: 14px 40px;"
        )
        layout.addWidget(line)

        # ── Subtitle ──────────────────────────────────────
        subtitle = QLabel("Europaeischer Preisvergleich")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(
            "color: #94a3b8; font-size: 14px; "
            "letter-spacing: 3px; background: transparent;"
        )
        layout.addWidget(subtitle)

        layout.addStretch(3)

        # ── Status text ───────────────────────────────────
        self._status = QLabel("Initialisiere...")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet(
            "color: #475569; font-size: 11px; "
            "background: transparent; margin-bottom: 6px;"
        )
        layout.addWidget(self._status)

        # ── Progress bar ──────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setFixedHeight(4)
        self._progress.setTextVisible(False)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setStyleSheet(
            "QProgressBar {"
            "  background-color: #151530;"
            "  border: none;"
            "  border-radius: 2px;"
            "}"
            "QProgressBar::chunk {"
            "  background: qlineargradient("
            "    x1:0, y1:0, x2:1, y2:0,"
            "    stop:0 #6366f1, stop:1 #a78bfa"
            "  );"
            "  border-radius: 2px;"
            "}"
        )
        layout.addWidget(self._progress)

        # ── Version ───────────────────────────────────────
        version = QLabel("v1.0.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet(
            "color: #334155; font-size: 10px; "
            "background: transparent; margin-top: 10px;"
        )
        layout.addWidget(version)

        # ── Animation timer ───────────────────────────────
        self._step = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self._messages = [
            (0, "Initialisiere..."),
            (15, "Lade Provider..."),
            (35, "Verbinde mit Geizhals.de..."),
            (55, "Konfiguriere Suchfilter..."),
            (75, "Lade Modell-Datenbank..."),
            (90, "Fast fertig..."),
            (100, "Bereit!"),
        ]

    def start(self):
        """Show the splash and begin the progress animation."""
        self._center_on_screen()
        self.show()
        self._timer.start(28)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.width()) // 2
            y = (geo.height() - self.height()) // 2
            self.move(x, y)

    def _tick(self):
        self._step += 1
        if self._step > 100:
            self._timer.stop()
            self.finished.emit()
            self.close()
            return

        self._progress.setValue(self._step)

        for threshold, msg in self._messages:
            if self._step == threshold:
                self._status.setText(msg)
                break

    def mousePressEvent(self, event):
        """Click anywhere to skip the splash."""
        self._timer.stop()
        self.finished.emit()
        self.close()
