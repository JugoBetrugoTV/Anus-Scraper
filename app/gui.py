"""
PyQt6 GUI for PreisHai — European price comparison tool.
Modern dark-themed interface with search, provider selection, filters,
results table, and product detail view.
"""

import webbrowser
import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QComboBox, QDoubleSpinBox, QProgressBar,
    QGroupBox, QHeaderView, QMessageBox, QStatusBar,
    QApplication, QCheckBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from app.price_engine import PriceEngine
from app.providers import EU_COUNTRIES
from app.models import Product
from app.detail_view import ProductDetailDialog

logger = logging.getLogger(__name__)


# ── Dark theme stylesheet ──────────────────────────────────────────

DARK_STYLE = """
QMainWindow {
    background-color: #1a1a2e;
}
QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QGroupBox {
    border: 1px solid #3a3a5c;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 20px;
    font-weight: bold;
    font-size: 13px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #7c83ff;
}
QLineEdit {
    background-color: #16213e;
    border: 2px solid #3a3a5c;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 14px;
    color: #e0e0e0;
    selection-background-color: #7c83ff;
}
QLineEdit:focus {
    border-color: #7c83ff;
}
QPushButton {
    background-color: #7c83ff;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #9198ff;
}
QPushButton:pressed {
    background-color: #5a60cc;
}
QPushButton:disabled {
    background-color: #3a3a5c;
    color: #666;
}
QPushButton#cancelBtn {
    background-color: #cc4444;
}
QPushButton#cancelBtn:hover {
    background-color: #ee5555;
}
QComboBox {
    background-color: #16213e;
    border: 2px solid #3a3a5c;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    color: #e0e0e0;
    min-width: 120px;
}
QComboBox:focus {
    border-color: #7c83ff;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #16213e;
    border: 1px solid #3a3a5c;
    color: #e0e0e0;
    selection-background-color: #7c83ff;
}
QDoubleSpinBox {
    background-color: #16213e;
    border: 2px solid #3a3a5c;
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 12px;
    color: #e0e0e0;
}
QDoubleSpinBox:focus {
    border-color: #7c83ff;
}
QTableWidget {
    background-color: #16213e;
    border: 1px solid #3a3a5c;
    border-radius: 8px;
    gridline-color: #2a2a4c;
    font-size: 12px;
    selection-background-color: #3a3a8c;
}
QTableWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #2a2a4c;
}
QTableWidget::item:selected {
    background-color: #3a3a8c;
}
QHeaderView::section {
    background-color: #0f3460;
    color: #7c83ff;
    padding: 8px 10px;
    border: none;
    border-right: 1px solid #2a2a4c;
    border-bottom: 2px solid #7c83ff;
    font-weight: bold;
    font-size: 12px;
}
QProgressBar {
    background-color: #16213e;
    border: 1px solid #3a3a5c;
    border-radius: 4px;
    text-align: center;
    font-size: 11px;
    color: #e0e0e0;
    height: 22px;
}
QProgressBar::chunk {
    background-color: #7c83ff;
    border-radius: 3px;
}
QStatusBar {
    background-color: #0f3460;
    color: #7c83ff;
    font-size: 11px;
}
QLabel {
    font-size: 12px;
}
QLabel#titleLabel {
    font-size: 22px;
    font-weight: bold;
    color: #7c83ff;
}
QLabel#subtitleLabel {
    font-size: 12px;
    color: #888;
}
QCheckBox {
    font-size: 12px;
    spacing: 4px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #3a3a5c;
    border-radius: 3px;
    background-color: #16213e;
}
QCheckBox::indicator:checked {
    background-color: #7c83ff;
    border-color: #7c83ff;
}
"""


# ── Search worker (background thread) ─────────────────────────────

class SearchWorker(QThread):
    """Runs PriceEngine.search() on a background thread."""

    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(str, int)

    def __init__(
        self,
        engine: PriceEngine,
        query: str,
        country: str,
        sort: str,
        condition: str,
        price_min: Optional[float],
        price_max: Optional[float],
    ):
        super().__init__()
        self.engine = engine
        self.query = query
        self.country = country
        self.sort = sort
        self.condition = condition
        self.price_min = price_min
        self.price_max = price_max
        self._cancelled = False

    def run(self):
        try:
            results = self.engine.search(
                query=self.query,
                country=self.country,
                sort=self.sort,
                condition=self.condition,
                price_min=self.price_min,
                price_max=self.price_max,
                max_results=20,
                progress_callback=self._on_progress,
            )
            if not self._cancelled:
                self.finished.emit(results)
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))

    def _on_progress(self, message: str, percent: int):
        if not self._cancelled:
            self.progress.emit(message, percent)

    def cancel(self):
        self._cancelled = True


# ── Main window ────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.engine = PriceEngine()
        self.worker: Optional[SearchWorker] = None
        self.current_results: list[Product] = []
        self._provider_checkboxes: dict[str, QCheckBox] = {}
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("PreisHai - Preisvergleich für Europa")
        self.setMinimumSize(1080, 720)
        self.resize(1280, 850)
        self.setStyleSheet(DARK_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 12, 16, 8)

        # ── Header ───────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("PreisHai")
        title.setObjectName("titleLabel")
        subtitle = QLabel(
            "Europäischer Preisvergleich — Finde die besten Deals"
        )
        subtitle.setObjectName("subtitleLabel")
        title_layout = QVBoxLayout()
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        title_layout.setSpacing(2)
        header.addLayout(title_layout)
        header.addStretch()
        layout.addLayout(header)

        # ── Search bar ───────────────────────────────────────
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Produkt eingeben (z.B. 'RTX 4090', 'iPhone 15 Pro', "
            "'Samsung S24')..."
        )
        self.search_input.setMinimumHeight(42)
        font = self.search_input.font()
        font.setPointSize(13)
        self.search_input.setFont(font)
        self.search_input.returnPressed.connect(self._on_search)

        self.search_btn = QPushButton("Suchen")
        self.search_btn.setMinimumHeight(42)
        self.search_btn.setMinimumWidth(120)
        self.search_btn.clicked.connect(self._on_search)

        self.cancel_btn = QPushButton("Abbrechen")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.setMinimumHeight(42)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._on_cancel)

        search_layout.addWidget(self.search_input, stretch=1)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.cancel_btn)
        layout.addLayout(search_layout)

        # ── Provider selection ───────────────────────────────
        provider_group = QGroupBox("Datenquellen")
        provider_layout = QHBoxLayout(provider_group)
        provider_layout.setSpacing(16)

        for provider in self.engine.providers:
            cb = QCheckBox(provider.name)
            cb.setChecked(provider.enabled)
            cb.toggled.connect(
                lambda checked, p=provider: setattr(p, "enabled", checked)
            )
            if not provider.enabled:
                cb.setToolTip("Platzhalter — noch nicht implementiert")
            provider_layout.addWidget(cb)
            self._provider_checkboxes[provider.name] = cb

        provider_layout.addStretch()
        layout.addWidget(provider_group)

        # ── Filters ──────────────────────────────────────────
        filter_group = QGroupBox("Filter")
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.setSpacing(16)

        # Country
        filter_layout.addWidget(QLabel("Land:"))
        self.country_combo = QComboBox()
        for code, name in EU_COUNTRIES.items():
            self.country_combo.addItem(f"{name} ({code.upper()})", code)
        filter_layout.addWidget(self.country_combo)

        # Sort
        filter_layout.addWidget(QLabel("Sortierung:"))
        self.sort_combo = QComboBox()
        sort_labels = {
            "relevanz": "Relevanz",
            "preis_aufsteigend": "Preis aufsteigend",
            "preis_absteigend": "Preis absteigend",
            "bewertung": "Beste Bewertung",
        }
        for key, label in sort_labels.items():
            self.sort_combo.addItem(label, key)
        self.sort_combo.setCurrentIndex(1)
        filter_layout.addWidget(self.sort_combo)

        # Condition
        filter_layout.addWidget(QLabel("Zustand:"))
        self.condition_combo = QComboBox()
        condition_labels = {
            "alle": "Alle",
            "neu": "Neu",
            "gebraucht": "Gebraucht",
        }
        for key, label in condition_labels.items():
            self.condition_combo.addItem(label, key)
        filter_layout.addWidget(self.condition_combo)

        # Price range
        filter_layout.addWidget(QLabel("Preis von:"))
        self.price_min = QDoubleSpinBox()
        self.price_min.setRange(0, 99999)
        self.price_min.setValue(0)
        self.price_min.setSuffix(" €")
        self.price_min.setDecimals(0)
        self.price_min.setSpecialValueText("Min")
        filter_layout.addWidget(self.price_min)

        filter_layout.addWidget(QLabel("bis:"))
        self.price_max = QDoubleSpinBox()
        self.price_max.setRange(0, 99999)
        self.price_max.setValue(0)
        self.price_max.setSuffix(" €")
        self.price_max.setDecimals(0)
        self.price_max.setSpecialValueText("Max")
        filter_layout.addWidget(self.price_max)

        filter_layout.addStretch()
        layout.addWidget(filter_group)

        # ── Progress ─────────────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)

        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar, stretch=1)
        layout.addLayout(progress_layout)

        # ── Results table ────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "#", "Produkt", "Preis", "Versand", "Händler",
            "Quelle", "Verfügbarkeit", "Link",
        ])

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 36)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 170)
        self.table.setColumnWidth(5, 110)
        self.table.setColumnWidth(6, 120)
        self.table.setColumnWidth(7, 70)

        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows,
        )
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._on_cell_double_click)

        layout.addWidget(self.table, stretch=1)

        # ── Status bar ───────────────────────────────────────
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(
            "Bereit — Gib einen Suchbegriff ein und klicke auf 'Suchen'"
        )

    # ── Actions ────────────────────────────────────────────────

    def _on_search(self):
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(
                self, "Hinweis", "Bitte gib einen Suchbegriff ein.",
            )
            return

        if self.worker and self.worker.isRunning():
            return

        country = self.country_combo.currentData()
        sort_key = self.sort_combo.currentData()
        condition = self.condition_combo.currentData()
        p_min = self.price_min.value() if self.price_min.value() > 0 else None
        p_max = self.price_max.value() if self.price_max.value() > 0 else None

        self.search_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Starte Suche...")
        self.table.setRowCount(0)
        self.status_bar.showMessage(f"Suche nach '{query}'...")

        self.worker = SearchWorker(
            self.engine, query, country, sort_key, condition, p_min, p_max,
        )
        self.worker.finished.connect(self._on_results)
        self.worker.error.connect(self._on_error)
        self.worker.progress.connect(self._on_progress)
        self.worker.start()

    def _on_cancel(self):
        if self.worker:
            self.worker.cancel()
        self._reset_search_ui()
        self.status_bar.showMessage("Suche abgebrochen.")

    def _on_progress(self, message: str, percent: int):
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)

    def _on_results(self, results: list[Product]):
        self._reset_search_ui()
        self.current_results = results

        if not results:
            import os
            debug_dir = os.path.join(
                os.path.expanduser("~"), "PreisHai_debug",
            )
            self.status_bar.showMessage(
                "Keine Ergebnisse gefunden. Versuche einen anderen "
                "Suchbegriff."
            )
            QMessageBox.information(
                self,
                "Keine Ergebnisse",
                "Es wurden keine Produkte gefunden.\n\n"
                "Tipps:\n"
                "  Versuche einen anderen oder kürzeren Suchbegriff\n"
                "  Entferne Preisfilter\n"
                "  Wähle ein anderes Land\n\n"
                f"Debug-HTML wurde gespeichert in:\n{debug_dir}\n\n"
                "Falls das Problem bestehen bleibt, schicke die\n"
                "HTML-Dateien aus dem Debug-Ordner zur Analyse.",
            )
            return

        self._populate_table(results)

        cheapest = results[0]
        self.status_bar.showMessage(
            f"{len(results)} Ergebnisse — Günstigster Preis: "
            f"{cheapest.price_display} bei {cheapest.merchant}"
        )

    def _on_error(self, error_msg: str):
        self._reset_search_ui()
        self.status_bar.showMessage(f"Fehler: {error_msg}")
        QMessageBox.critical(
            self,
            "Fehler bei der Suche",
            f"Es ist ein Fehler aufgetreten:\n\n{error_msg}\n\n"
            "Bitte prüfe deine Internetverbindung und versuche es erneut.",
        )

    def _reset_search_ui(self):
        self.search_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

    # ── Table population ───────────────────────────────────────

    def _populate_table(self, products: list[Product]):
        self.table.setRowCount(len(products))

        for row, product in enumerate(products):
            # #
            rank_item = QTableWidgetItem(str(product.rank))
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, rank_item)

            # Produkt
            title_item = QTableWidgetItem(product.title)
            title_item.setToolTip(product.title)
            self.table.setItem(row, 1, title_item)

            # Preis (color-coded)
            price_item = QTableWidgetItem(product.price_display)
            price_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            )
            if row == 0:
                price_item.setForeground(QColor("#4caf50"))
            elif row < 5:
                price_item.setForeground(QColor("#8bc34a"))
            elif row < 10:
                price_item.setForeground(QColor("#ffeb3b"))
            else:
                price_item.setForeground(QColor("#ff9800"))
            font = price_item.font()
            font.setBold(True)
            price_item.setFont(font)
            self.table.setItem(row, 2, price_item)

            # Versand
            ship_item = QTableWidgetItem(product.shipping_display)
            ship_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, ship_item)

            # Händler
            merchant_item = QTableWidgetItem(product.merchant)
            merchant_item.setToolTip(product.merchant)
            self.table.setItem(row, 4, merchant_item)

            # Quelle
            source_item = QTableWidgetItem(product.source or "—")
            source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            source_item.setForeground(QColor("#888"))
            self.table.setItem(row, 5, source_item)

            # Verfügbarkeit
            avail_item = QTableWidgetItem(product.availability or "—")
            self.table.setItem(row, 6, avail_item)

            # Link
            if product.link:
                link_item = QTableWidgetItem("Details")
                link_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                link_item.setForeground(QColor("#7c83ff"))
                link_item.setToolTip(
                    "Doppelklick: Produktdetails — "
                    "Link-Spalte: Im Browser öffnen"
                )
            else:
                link_item = QTableWidgetItem("—")
            self.table.setItem(row, 7, link_item)

        self.table.resizeRowsToContents()

    # ── Cell interaction ───────────────────────────────────────

    def _on_cell_double_click(self, row: int, col: int):
        if row >= len(self.current_results):
            return
        product = self.current_results[row]

        # Double-click on "Link" column → open browser directly
        if col == 7 and product.link:
            webbrowser.open(product.link)
            return

        # Everything else → show detail dialog
        dlg = ProductDetailDialog(product, self)
        dlg.exec()
