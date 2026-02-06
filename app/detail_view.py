"""
Product detail dialog — shows full product info with mock price history.
"""

import random
import webbrowser

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath

from app.models import Product


class PriceHistoryWidget(QFrame):
    """Simple line chart showing mock 30-day price history."""

    def __init__(self, current_price: float, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(160)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed,
        )
        self.setStyleSheet(
            "background-color: #0d1b2a; border: 1px solid #3a3a5c; "
            "border-radius: 6px;"
        )
        # Generate plausible mock data around current price
        self._points = self._generate_history(current_price, days=30)

    @staticmethod
    def _generate_history(price: float, days: int = 30) -> list[float]:
        rng = random.Random(int(price * 100))
        pts = []
        p = price * rng.uniform(1.02, 1.12)  # start slightly higher
        for _ in range(days):
            p += rng.uniform(-price * 0.02, price * 0.015)
            p = max(price * 0.85, min(price * 1.2, p))
            pts.append(round(p, 2))
        pts[-1] = price  # end at current price
        return pts

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._points:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        pad_l, pad_r, pad_t, pad_b = 50, 16, 20, 28

        chart_w = w - pad_l - pad_r
        chart_h = h - pad_t - pad_b

        lo = min(self._points) * 0.98
        hi = max(self._points) * 1.02
        if hi == lo:
            hi = lo + 1

        def to_x(i):
            return pad_l + (i / (len(self._points) - 1)) * chart_w

        def to_y(v):
            return pad_t + (1 - (v - lo) / (hi - lo)) * chart_h

        # Grid lines
        painter.setPen(QPen(QColor("#2a2a4c"), 1))
        for frac in [0, 0.25, 0.5, 0.75, 1.0]:
            y = pad_t + frac * chart_h
            painter.drawLine(int(pad_l), int(y), int(w - pad_r), int(y))
            val = hi - frac * (hi - lo)
            painter.setPen(QPen(QColor("#666"), 1))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(
                QRectF(0, y - 8, pad_l - 4, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{val:.0f}",
            )
            painter.setPen(QPen(QColor("#2a2a4c"), 1))

        # Line path
        path = QPainterPath()
        path.moveTo(to_x(0), to_y(self._points[0]))
        for i in range(1, len(self._points)):
            path.lineTo(to_x(i), to_y(self._points[i]))

        painter.setPen(QPen(QColor("#7c83ff"), 2))
        painter.drawPath(path)

        # Current price dot
        last_x = to_x(len(self._points) - 1)
        last_y = to_y(self._points[-1])
        painter.setBrush(QColor("#4caf50"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(last_x) - 4, int(last_y) - 4, 8, 8)

        # X-axis labels
        painter.setPen(QPen(QColor("#666"), 1))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(
            QRectF(pad_l, h - pad_b + 4, 60, 16),
            Qt.AlignmentFlag.AlignLeft,
            "vor 30 T.",
        )
        painter.drawText(
            QRectF(w - pad_r - 40, h - pad_b + 4, 60, 16),
            Qt.AlignmentFlag.AlignLeft,
            "Heute",
        )

        painter.end()


class ProductDetailDialog(QDialog):
    """Shows detailed product information with mock price history."""

    def __init__(self, product: Product, parent=None):
        super().__init__(parent)
        self.product = product
        self.setWindowTitle(f"Produktdetails — {product.title[:60]}")
        self.setMinimumSize(520, 520)
        self.resize(560, 580)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
                color: #e0e0e0;
            }
            QLabel { font-size: 13px; }
            QLabel#detailTitle {
                font-size: 17px;
                font-weight: bold;
                color: #7c83ff;
            }
            QLabel#detailPrice {
                font-size: 22px;
                font-weight: bold;
                color: #4caf50;
            }
            QLabel#sectionHeader {
                font-size: 13px;
                font-weight: bold;
                color: #7c83ff;
                margin-top: 8px;
            }
            QPushButton#shopBtn {
                background-color: #7c83ff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 28px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#shopBtn:hover { background-color: #9198ff; }
            QPushButton#closeBtn {
                background-color: #3a3a5c;
                color: #ccc;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 12px;
            }
            QPushButton#closeBtn:hover { background-color: #4a4a6c; }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)
        p = self.product

        # Title
        title = QLabel(p.title)
        title.setObjectName("detailTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        # Price section
        price_row = QHBoxLayout()
        price_label = QLabel(p.price_display)
        price_label.setObjectName("detailPrice")
        price_row.addWidget(price_label)

        if p.shipping_cost > 0:
            ship_label = QLabel(f"+ {p.shipping_cost:.2f} € Versand")
            ship_label.setStyleSheet("color: #aaa; font-size: 13px;")
            price_row.addWidget(ship_label)
            total = QLabel(f"= {p.total_price_display} gesamt")
            total.setStyleSheet("color: #8bc34a; font-size: 13px; font-weight: bold;")
            price_row.addWidget(total)

        price_row.addStretch()
        layout.addLayout(price_row)

        # Info grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(6)
        row = 0

        def _add(label_text, value_text):
            nonlocal row
            lbl = QLabel(f"<b>{label_text}:</b>")
            lbl.setStyleSheet("color: #888;")
            val = QLabel(value_text or "—")
            val.setWordWrap(True)
            grid.addWidget(lbl, row, 0, Qt.AlignmentFlag.AlignTop)
            grid.addWidget(val, row, 1, Qt.AlignmentFlag.AlignTop)
            row += 1

        _add("Händler", p.merchant)
        _add("Quelle", p.source)
        _add("Zustand", p.condition)
        if p.availability:
            _add("Verfügbarkeit", p.availability)
        _add("Versand", p.shipping_display)
        if p.rating > 0:
            stars = "★" * int(p.rating) + "☆" * (5 - int(p.rating))
            _add("Bewertung", f"{p.rating:.1f} {stars} ({p.reviews} Bewertungen)")

        layout.addLayout(grid)

        # Price history section
        hist_label = QLabel("Preisverlauf (30 Tage)")
        hist_label.setObjectName("sectionHeader")
        layout.addWidget(hist_label)

        chart = PriceHistoryWidget(p.price, self)
        layout.addWidget(chart)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        if p.link:
            shop_btn = QPushButton("Zum Shop")
            shop_btn.setObjectName("shopBtn")
            shop_btn.clicked.connect(lambda: webbrowser.open(p.link))
            btn_row.addWidget(shop_btn)

        close_btn = QPushButton("Schließen")
        close_btn.setObjectName("closeBtn")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)
