from dataclasses import dataclass


@dataclass
class Product:
    rank: int
    title: str
    price: float
    currency: str
    merchant: str
    link: str
    image_url: str = ""
    rating: float = 0.0
    reviews: int = 0
    delivery_info: str = ""
    condition: str = "Neu"

    @property
    def price_display(self) -> str:
        return f"{self.price:.2f} {self.currency}"
