import re
from dataclasses import dataclass, field
from enum import Enum


class AvailabilityStatus(Enum):
    """Normalized availability states with display info."""
    IN_STOCK = ("Auf Lager", "#4caf50")
    LOW_STOCK = ("Wenig verfügbar", "#ff9800")
    PREORDER = ("Vorbestellbar", "#2196f3")
    SHORTLY = ("Kurzfristig lieferbar", "#ffeb3b")
    OUT_OF_STOCK = ("Nicht verfügbar", "#f44336")
    UNKNOWN = ("Unbekannt", "#888888")

    def __init__(self, label: str, color: str):
        self.label = label
        self.color = color

    @staticmethod
    def normalize(text: str) -> "AvailabilityStatus":
        """Map raw availability text to a normalized status."""
        if not text:
            return AvailabilityStatus.UNKNOWN
        t = text.lower().strip()
        if any(k in t for k in ["auf lager", "sofort", "in stock", "lieferbar",
                                 "1-2", "lagernd", "verfügbar", "available"]):
            if any(k in t for k in ["wenig", "low", "letzte", "bald"]):
                return AvailabilityStatus.LOW_STOCK
            return AvailabilityStatus.IN_STOCK
        if any(k in t for k in ["kurzfristig", "shortly", "1-3 tage",
                                 "2-4 tage", "3-5 tage"]):
            return AvailabilityStatus.SHORTLY
        if any(k in t for k in ["vorbestell", "preorder", "pre-order"]):
            return AvailabilityStatus.PREORDER
        if any(k in t for k in ["nicht verfügbar", "ausverkauft",
                                 "out of stock", "nicht lieferbar",
                                 "nicht auf lager"]):
            return AvailabilityStatus.OUT_OF_STOCK
        return AvailabilityStatus.UNKNOWN


@dataclass
class Product:
    rank: int
    title: str
    price: float
    currency: str = "€"
    merchant: str = ""
    link: str = ""
    image_url: str = ""
    rating: float = 0.0
    reviews: int = 0
    delivery_info: str = ""
    condition: str = "Neu"
    shipping_cost: float = 0.0
    availability: str = ""
    source: str = ""
    description: str = ""
    model_id: str = ""

    @property
    def price_display(self) -> str:
        return f"{self.price:.2f} {self.currency}"

    @property
    def total_price(self) -> float:
        return self.price + self.shipping_cost

    @property
    def total_price_display(self) -> str:
        if self.shipping_cost > 0:
            return f"{self.total_price:.2f} {self.currency}"
        return self.price_display

    @property
    def shipping_display(self) -> str:
        if self.shipping_cost > 0:
            return f"{self.shipping_cost:.2f} {self.currency}"
        if self.shipping_cost == 0 and self.delivery_info:
            return self.delivery_info
        return "—"

    @property
    def availability_status(self) -> AvailabilityStatus:
        return AvailabilityStatus.normalize(self.availability)
