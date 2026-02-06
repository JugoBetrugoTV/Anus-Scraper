"""
Amazon provider — placeholder for future implementation.

Amazon product data can be obtained via:
- Amazon Product Advertising API (PA-API 5.0) – requires an affiliate account
- Amazon SP-API – requires a seller/developer account
- Affiliate feeds (e.g. via AWIN, Tradedoubler)

To activate this provider, implement the search() method with one of the
above data sources and set ``enabled = True`` on the instance.
"""

import logging
from typing import Optional

from app.models import Product
from app.providers import ShopProvider

logger = logging.getLogger(__name__)


class AmazonProvider(ShopProvider):
    """Amazon product search (placeholder)."""

    name = "Amazon"

    def __init__(self):
        super().__init__()
        self.enabled = False  # disabled until implemented

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
            f"Amazon provider not yet configured (query: '{query}'). "
            "Set up PA-API 5.0 credentials to enable."
        )
        # Example structure for a future implementation:
        #
        # from paapi5 import SearchItemsRequest
        # request = SearchItemsRequest(keywords=query, ...)
        # response = self._api.search_items(request)
        # for item in response.search_result.items:
        #     products.append(Product(
        #         rank=0,
        #         title=item.item_info.title.display_value,
        #         price=item.offers.listings[0].price.amount,
        #         merchant="Amazon",
        #         link=item.detail_page_url,
        #         source="Amazon",
        #     ))
        return []
