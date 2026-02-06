"""
MediaMarkt provider — placeholder for future implementation.

MediaMarkt/Saturn product data can be obtained via:
- Public product search API (JSON endpoints used by their SPA frontend)
- Affiliate feeds (e.g. via AWIN)

To activate, implement search() and set ``enabled = True``.
"""

import logging
from typing import Optional

from app.models import Product
from app.providers import ShopProvider

logger = logging.getLogger(__name__)


class MediaMarktProvider(ShopProvider):
    """MediaMarkt / Saturn product search (placeholder)."""

    name = "MediaMarkt"

    def __init__(self):
        super().__init__()
        self.enabled = False

    def search(
        self,
        query: str,
        country: str = "de",
        sort: str = "preis_aufsteigend",
        condition: str = "alle",
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        progress_callback=None,
    ) -> list[Product]:
        logger.info(
            f"MediaMarkt provider not yet configured (query: '{query}')."
        )
        # Example structure for a future implementation:
        #
        # api_url = f"https://www.mediamarkt.de/de/search.html?query={query}"
        # resp = self.session.get(api_url, timeout=15)
        # data = resp.json()
        # for item in data["products"]:
        #     products.append(Product(
        #         rank=0,
        #         title=item["name"],
        #         price=item["price"],
        #         merchant="MediaMarkt",
        #         link=item["url"],
        #         availability=item.get("availability", ""),
        #         shipping_cost=item.get("shippingCost", 0),
        #         source="MediaMarkt",
        #     ))
        return []
