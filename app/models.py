from dataclasses import dataclass, field


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
