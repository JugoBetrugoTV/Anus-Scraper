"""
PyQt6 GUI for Anus Scraper — European price comparison tool.
Modern dark-themed interface with search, provider selection, filters,
results table, and product detail view.
"""

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
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

from app.price_engine import PriceEngine
from app.providers import EU_COUNTRIES
from app.models import Product, AvailabilityStatus
from app.detail_view import ProductDetailDialog
from app.product_filter import (
    detect_gpu_variants, parse_gpu_query, parse_gpu_title,
)

logger = logging.getLogger(__name__)


# ── Dark theme stylesheet ──────────────────────────────────────────

DARK_STYLE = """
/* ── Base ──────────────────────────────────────────────── */
QMainWindow {
    background-color: #080818;
}
QWidget {
    background-color: #080818;
    color: #e2e8f0;
    font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
    font-size: 13px;
}

/* ── Cards / GroupBoxes ───────────────────────────────── */
QGroupBox {
    background-color: #0e0e24;
    border: 1px solid #1c1c3a;
    border-radius: 12px;
    margin-top: 14px;
    padding-top: 22px;
    font-weight: 600;
    font-size: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 10px;
    color: #a78bfa;
    font-size: 12px;
}

/* ── Inputs ───────────────────────────────────────────── */
QLineEdit {
    background-color: #0e0e24;
    border: 2px solid #1c1c3a;
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 14px;
    color: #e2e8f0;
    selection-background-color: #6366f1;
}
QLineEdit:focus {
    border-color: #6366f1;
    background-color: #12122a;
}

/* ── Buttons ──────────────────────────────────────────── */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6366f1, stop:1 #8b5cf6);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 12px 28px;
    font-size: 13px;
    font-weight: 700;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #818cf8, stop:1 #a78bfa);
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4f46e5, stop:1 #7c3aed);
}
QPushButton:disabled {
    background: #1c1c3a;
    color: #475569;
}
QPushButton#cancelBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #dc2626, stop:1 #ef4444);
}
QPushButton#cancelBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ef4444, stop:1 #f87171);
}

/* ── ComboBox ─────────────────────────────────────────── */
QComboBox {
    background-color: #0e0e24;
    border: 2px solid #1c1c3a;
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 12px;
    color: #e2e8f0;
    min-width: 120px;
}
QComboBox:focus {
    border-color: #6366f1;
}
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox QAbstractItemView {
    background-color: #0e0e24;
    border: 1px solid #1c1c3a;
    color: #e2e8f0;
    selection-background-color: #6366f1;
    border-radius: 8px;
}

/* ── SpinBox ──────────────────────────────────────────── */
QDoubleSpinBox {
    background-color: #0e0e24;
    border: 2px solid #1c1c3a;
    border-radius: 10px;
    padding: 8px 10px;
    font-size: 12px;
    color: #e2e8f0;
}
QDoubleSpinBox:focus {
    border-color: #6366f1;
}

/* ── Table ────────────────────────────────────────────── */
QTableWidget {
    background-color: #0a0a1e;
    alternate-background-color: #0e0e24;
    border: 1px solid #1c1c3a;
    border-radius: 12px;
    gridline-color: #151530;
    font-size: 12px;
    selection-background-color: rgba(99, 102, 241, 0.25);
    outline: none;
}
QTableWidget::item {
    padding: 10px 12px;
    border-bottom: 1px solid #151530;
}
QTableWidget::item:selected {
    background-color: rgba(99, 102, 241, 0.2);
    color: #e2e8f0;
}
QHeaderView::section {
    background-color: #08081a;
    color: #8b5cf6;
    padding: 12px 12px;
    border: none;
    border-right: 1px solid #151530;
    border-bottom: 2px solid #6366f1;
    font-weight: 700;
    font-size: 11px;
}

/* ── Progress ─────────────────────────────────────────── */
QProgressBar {
    background-color: #0e0e24;
    border: none;
    border-radius: 4px;
    text-align: center;
    font-size: 11px;
    color: #94a3b8;
    height: 8px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6366f1, stop:0.5 #8b5cf6, stop:1 #a78bfa);
    border-radius: 4px;
}

/* ── Status bar ───────────────────────────────────────── */
QStatusBar {
    background-color: #060614;
    color: #8b5cf6;
    font-size: 11px;
    border-top: 1px solid #1c1c3a;
    padding: 4px 8px;
}

/* ── Labels ───────────────────────────────────────────── */
QLabel {
    font-size: 12px;
    background: transparent;
}
QLabel#titleLabel {
    font-size: 30px;
    font-weight: 900;
    color: #ffffff;
}
QLabel#subtitleLabel {
    font-size: 12px;
    color: #64748b;
    letter-spacing: 0.5px;
}
QLabel#accentLine {
    background: transparent;
}

/* ── Checkboxes ───────────────────────────────────────── */
QCheckBox {
    font-size: 12px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border: 2px solid #1c1c3a;
    border-radius: 6px;
    background-color: #0e0e24;
}
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #6366f1, stop:1 #8b5cf6);
    border-color: #6366f1;
}
QCheckBox::indicator:hover {
    border-color: #6366f1;
}

/* ── Scrollbars ───────────────────────────────────────── */
QScrollBar:vertical {
    background-color: #080818;
    width: 8px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #1c1c3a;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #6366f1;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background-color: #080818;
    height: 8px;
    border: none;
}
QScrollBar::handle:horizontal {
    background-color: #1c1c3a;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #6366f1;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Message Boxes ────────────────────────────────────── */
QMessageBox {
    background-color: #0e0e24;
}
QMessageBox QLabel {
    color: #e2e8f0;
}
"""

# Source badge colors
SOURCE_COLORS = {
    "Geizhals": "#f97316",
    "Google Shopping": "#3b82f6",
    "Idealo": "#06b6d4",
    "Notebooksbilliger": "#ec4899",
    "Mindfactory": "#14b8a6",
    "Amazon": "#f59e0b",
    "MediaMarkt": "#ef4444",
    "Alternate": "#22d3ee",
}


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
        self.display_rows: list[Product] = []
        self.model_groups: dict[str, list[Product]] = {}
        self._is_model_view = False
        self._provider_checkboxes: dict[str, QCheckBox] = {}
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Anus Scraper - Preisvergleich")
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
        title = QLabel("ANUS SCRAPER")
        title.setObjectName("titleLabel")
        # Glow effect on title
        title_glow = QGraphicsDropShadowEffect()
        title_glow.setBlurRadius(30)
        title_glow.setColor(QColor("#6366f1"))
        title_glow.setOffset(0, 0)
        title.setGraphicsEffect(title_glow)

        subtitle = QLabel(
            "Preise vergleichen. Geld sparen."
        )
        subtitle.setObjectName("subtitleLabel")
        title_layout = QVBoxLayout()
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        title_layout.setSpacing(4)
        header.addLayout(title_layout)
        header.addStretch()
        layout.addLayout(header)

        # Gradient accent line
        accent_line = QLabel()
        accent_line.setObjectName("accentLine")
        accent_line.setFixedHeight(2)
        accent_line.setStyleSheet(
            "background: qlineargradient("
            "  x1:0, y1:0, x2:1, y2:0,"
            "  stop:0 #6366f1, stop:0.5 #a78bfa, stop:1 #6366f1"
            ");"
            "border-radius: 1px;"
        )
        layout.addWidget(accent_line)

        # ── Search bar ───────────────────────────────────────
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Produkt eingeben (z.B. 'RTX 4090', 'iPhone 15 Pro', "
            "'Samsung S24')..."
        )
        self.search_input.setMinimumHeight(44)
        font = self.search_input.font()
        font.setPointSize(13)
        self.search_input.setFont(font)
        self.search_input.returnPressed.connect(self._on_search)

        self.search_btn = QPushButton("Suchen")
        self.search_btn.setMinimumHeight(44)
        self.search_btn.setMinimumWidth(130)
        self.search_btn.clicked.connect(self._on_search)

        self.cancel_btn = QPushButton("Abbrechen")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.setMinimumHeight(44)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._on_cancel)

        search_layout.addWidget(self.search_input, stretch=1)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.cancel_btn)
        layout.addLayout(search_layout)

        # ── Provider selection + Filters in one row ──────────
        config_row = QHBoxLayout()
        config_row.setSpacing(12)

        # Provider group
        provider_group = QGroupBox("Datenquellen")
        provider_layout = QHBoxLayout(provider_group)
        provider_layout.setSpacing(12)

        for provider in self.engine.providers:
            cb = QCheckBox(provider.name)
            cb.setChecked(provider.enabled)
            cb.toggled.connect(
                lambda checked, p=provider: setattr(p, "enabled", checked)
            )
            if not provider.enabled:
                cb.setToolTip("Noch nicht aktiviert")
                cb.setStyleSheet("color: #666;")
            provider_layout.addWidget(cb)
            self._provider_checkboxes[provider.name] = cb

        provider_layout.addStretch()
        config_row.addWidget(provider_group, stretch=2)

        # Filter group
        filter_group = QGroupBox("Filter")
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.setSpacing(12)

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
        filter_layout.addWidget(QLabel("Preis:"))
        self.price_min = QDoubleSpinBox()
        self.price_min.setRange(0, 99999)
        self.price_min.setValue(0)
        self.price_min.setSuffix(" €")
        self.price_min.setDecimals(0)
        self.price_min.setSpecialValueText("Min")
        filter_layout.addWidget(self.price_min)

        filter_layout.addWidget(QLabel("—"))
        self.price_max = QDoubleSpinBox()
        self.price_max.setRange(0, 99999)
        self.price_max.setValue(0)
        self.price_max.setSuffix(" €")
        self.price_max.setDecimals(0)
        self.price_max.setSpecialValueText("Max")
        filter_layout.addWidget(self.price_max)

        filter_layout.addStretch()
        config_row.addWidget(filter_group, stretch=3)
        layout.addLayout(config_row)

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
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "#", "Produkt", "Preis", "Versand",
            "Händler", "Quelle", "Verfügbarkeit",
        ])

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)

        self.table.setColumnWidth(0, 36)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 110)
        self.table.setColumnWidth(4, 180)
        self.table.setColumnWidth(5, 120)
        self.table.setColumnWidth(6, 150)

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
                os.path.expanduser("~"), "AnusScraper_debug",
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

        query = self.search_input.text().strip()
        is_gpu = parse_gpu_query(query) is not None

        if is_gpu:
            self._show_model_grouped(results)
        else:
            self.model_groups = {}
            self._is_model_view = False
            self.display_rows = results
            self._populate_table(results)
            cheapest = results[0]
            self.status_bar.showMessage(
                f"{len(results)} Ergebnisse — Günstigster Preis: "
                f"{cheapest.price_display} bei {cheapest.merchant}"
            )

    def _show_model_grouped(self, results: list[Product]):
        """Group results by model_id and display one row per model."""
        from collections import defaultdict

        groups: dict[str, list[Product]] = defaultdict(list)
        for p in results:
            mid = p.model_id if p.model_id else p.title
            groups[mid].append(p)

        self.model_groups = dict(groups)
        self._is_model_view = True

        # Build representative list — cheapest offer per model group
        representatives: list[Product] = []
        for model_id, offers in self.model_groups.items():
            offers.sort(key=lambda p: p.price)
            representatives.append(offers[0])

        representatives.sort(key=lambda p: p.price)
        for i, p in enumerate(representatives, 1):
            p.rank = i

        self.display_rows = representatives
        self._populate_model_table(representatives)

        n_models = len(representatives)
        n_offers = len(results)
        cheapest = representatives[0]
        if n_models != n_offers:
            self.status_bar.showMessage(
                f"{n_models} Modelle gefunden ({n_offers} Angebote) — "
                f"Günstigster Preis: {cheapest.price_display}"
            )
        else:
            self.status_bar.showMessage(
                f"{n_models} Ergebnisse — Günstigster Preis: "
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
        # Reset headers (may have been changed by model table)
        self.table.setHorizontalHeaderLabels([
            "#", "Produkt", "Preis", "Versand",
            "Händler", "Quelle", "Verfügbarkeit",
        ])
        self.table.setRowCount(len(products))

        # Check if this is a GPU search — show variant tags if so
        query = self.search_input.text().strip()
        is_gpu_search = parse_gpu_query(query) is not None

        # Find the cheapest price for highlighting
        cheapest_price = min(p.price for p in products) if products else 0

        for row, product in enumerate(products):
            is_best = (product.price == cheapest_price)

            # #
            rank_item = QTableWidgetItem(str(product.rank))
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_best:
                rank_item.setBackground(QColor("#1a3a1a"))
            self.table.setItem(row, 0, rank_item)

            # Produkt (with variant tags for GPU searches)
            display_title = product.title
            if is_gpu_search:
                variants = detect_gpu_variants(product.title)
                if variants:
                    tags = " | ".join(variants)
                    display_title = f"{product.title}  [{tags}]"
            title_item = QTableWidgetItem(display_title)
            title_item.setToolTip(product.title)
            if is_best:
                title_item.setBackground(QColor("#1a3a1a"))
            self.table.setItem(row, 1, title_item)

            # Preis
            price_item = QTableWidgetItem(product.price_display)
            price_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            )
            if is_best:
                price_item.setForeground(QColor("#4caf50"))
                price_item.setBackground(QColor("#1a3a1a"))
            elif row < 3:
                price_item.setForeground(QColor("#8bc34a"))
            elif row < 8:
                price_item.setForeground(QColor("#ffeb3b"))
            else:
                price_item.setForeground(QColor("#ff9800"))
            font = price_item.font()
            font.setBold(True)
            price_item.setFont(font)
            self.table.setItem(row, 2, price_item)

            # Versand
            ship_text = product.shipping_display
            ship_item = QTableWidgetItem(ship_text)
            ship_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if "kostenlos" in ship_text.lower() or ship_text == "—":
                ship_item.setForeground(QColor("#4caf50"))
            else:
                ship_item.setForeground(QColor("#aaa"))
            if is_best:
                ship_item.setBackground(QColor("#1a3a1a"))
            self.table.setItem(row, 3, ship_item)

            # Händler
            merchant_item = QTableWidgetItem(product.merchant)
            merchant_item.setToolTip(product.merchant)
            if is_best:
                merchant_item.setBackground(QColor("#1a3a1a"))
            self.table.setItem(row, 4, merchant_item)

            # Quelle (with color badge)
            source_text = product.source or "—"
            source_item = QTableWidgetItem(source_text)
            source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            source_color = SOURCE_COLORS.get(source_text, "#888")
            source_item.setForeground(QColor(source_color))
            font = source_item.font()
            font.setBold(True)
            source_item.setFont(font)
            if is_best:
                source_item.setBackground(QColor("#1a3a1a"))
            self.table.setItem(row, 5, source_item)

            # Verfügbarkeit (with status color)
            avail_status = product.availability_status
            avail_text = product.availability or avail_status.label
            avail_item = QTableWidgetItem(avail_text)
            avail_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            avail_item.setForeground(QColor(avail_status.color))
            font = avail_item.font()
            font.setBold(True)
            avail_item.setFont(font)
            if is_best:
                avail_item.setBackground(QColor("#1a3a1a"))
            self.table.setItem(row, 6, avail_item)

        self.table.resizeRowsToContents()

    # ── Model-grouped table ───────────────────────────────────

    def _populate_model_table(self, representatives: list[Product]):
        """Populate table with one row per model (GPU grouped view)."""
        self.table.setHorizontalHeaderLabels([
            "#", "Modell", "ab Preis", "Versand",
            "Händler", "Quelle", "Verfügbarkeit",
        ])
        self.table.setRowCount(len(representatives))

        cheapest_price = (
            min(p.price for p in representatives) if representatives else 0
        )

        for row, product in enumerate(representatives):
            model_id = product.model_id
            offers = self.model_groups.get(model_id, [product])
            n_offers = len(offers)
            is_best = (product.price == cheapest_price)

            # #
            rank_item = QTableWidgetItem(str(product.rank))
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_best:
                rank_item.setBackground(QColor("#1a3a1a"))
            self.table.setItem(row, 0, rank_item)

            # Modell (parsed display name)
            identity = parse_gpu_title(product.title)
            display_name = (
                identity.display_name if identity.chip else product.title
            )
            title_item = QTableWidgetItem(display_name)
            title_item.setToolTip(product.title)
            if is_best:
                title_item.setBackground(QColor("#1a3a1a"))
            self.table.setItem(row, 1, title_item)

            # ab Preis
            price_text = f"ab {product.price_display}"
            price_item = QTableWidgetItem(price_text)
            price_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter,
            )
            if is_best:
                price_item.setForeground(QColor("#4caf50"))
                price_item.setBackground(QColor("#1a3a1a"))
            elif row < 3:
                price_item.setForeground(QColor("#8bc34a"))
            elif row < 8:
                price_item.setForeground(QColor("#ffeb3b"))
            else:
                price_item.setForeground(QColor("#ff9800"))
            font = price_item.font()
            font.setBold(True)
            price_item.setFont(font)
            self.table.setItem(row, 2, price_item)

            # Versand (from cheapest offer)
            ship_text = product.shipping_display
            ship_item = QTableWidgetItem(ship_text)
            ship_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if "kostenlos" in ship_text.lower() or ship_text == "—":
                ship_item.setForeground(QColor("#4caf50"))
            else:
                ship_item.setForeground(QColor("#aaa"))
            if is_best:
                ship_item.setBackground(QColor("#1a3a1a"))
            self.table.setItem(row, 3, ship_item)

            # Händler (count or single name)
            if n_offers > 1:
                merchant_text = f"{n_offers} Händler"
                tooltip_lines = [
                    f"• {o.merchant} — {o.price_display}"
                    for o in offers
                ]
                tooltip = "\n".join(tooltip_lines)
            else:
                merchant_text = product.merchant
                tooltip = product.merchant
            merchant_item = QTableWidgetItem(merchant_text)
            merchant_item.setToolTip(tooltip)
            if is_best:
                merchant_item.setBackground(QColor("#1a3a1a"))
            self.table.setItem(row, 4, merchant_item)

            # Quelle
            source_text = product.source or "—"
            source_item = QTableWidgetItem(source_text)
            source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            source_color = SOURCE_COLORS.get(source_text, "#888")
            source_item.setForeground(QColor(source_color))
            font = source_item.font()
            font.setBold(True)
            source_item.setFont(font)
            if is_best:
                source_item.setBackground(QColor("#1a3a1a"))
            self.table.setItem(row, 5, source_item)

            # Verfügbarkeit (best from group)
            best_avail = self._best_availability(offers)
            avail_text = best_avail.label
            avail_item = QTableWidgetItem(avail_text)
            avail_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            avail_item.setForeground(QColor(best_avail.color))
            font = avail_item.font()
            font.setBold(True)
            avail_item.setFont(font)
            if is_best:
                avail_item.setBackground(QColor("#1a3a1a"))
            self.table.setItem(row, 6, avail_item)

        self.table.resizeRowsToContents()

    @staticmethod
    def _best_availability(offers: list[Product]) -> AvailabilityStatus:
        """Return the best availability status from a list of offers."""
        priority = [
            AvailabilityStatus.IN_STOCK,
            AvailabilityStatus.LOW_STOCK,
            AvailabilityStatus.SHORTLY,
            AvailabilityStatus.PREORDER,
            AvailabilityStatus.UNKNOWN,
            AvailabilityStatus.OUT_OF_STOCK,
        ]
        statuses = {p.availability_status for p in offers}
        for status in priority:
            if status in statuses:
                return status
        return AvailabilityStatus.UNKNOWN

    # ── Cell interaction ───────────────────────────────────────

    def _on_cell_double_click(self, row: int, col: int):
        if row >= len(self.display_rows):
            return
        product = self.display_rows[row]

        if self._is_model_view:
            offers = self.model_groups.get(
                product.model_id, [product],
            )
            dlg = ProductDetailDialog(product, self, offers=offers)
        else:
            dlg = ProductDetailDialog(product, self)
        dlg.exec()
