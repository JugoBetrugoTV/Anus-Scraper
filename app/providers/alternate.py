"""
Alternate provider — placeholder for future implementation.

Alternate.de product data can be obtained via:
- Their public website (structured HTML)
- Affiliate feeds

To activate, implement search() and set ``enabled = True``.
"""

import logging
from typing import Optional

from app.models import Product
from app.providers import ShopProvider

logger = logging.getLogger(__name__)


class AlternateProvider(ShopProvider):
    """Alternate.de product search (placeholder)."""

    name = "Alternate"

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
            f"Alternate provider not yet configured (query: '{query}')."
        )
        # Example structure:
        #
        # search_url = f"https://www.alternate.de/listing.xhtml?q={query}"
        # resp = self.session.get(search_url, timeout=15)
        # soup = BeautifulSoup(resp.text, "lxml")
        # for card in soup.select(".productBox"):
        #     title = card.select_one(".product-name").get_text(strip=True)
        #     price = self.extract_price(
        #         card.select_one(".price").get_text(strip=True)
        #     )
        #     products.append(Product(
        #         rank=0, title=title, price=price,
        #         merchant="Alternate", source="Alternate", ...
        #     ))
        return []
