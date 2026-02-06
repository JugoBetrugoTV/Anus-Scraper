"""
Idealo provider — German price comparison platform.

Idealo aggressively blocks automated requests. This provider attempts
to fetch search results via their public website.

To activate, set ``enabled = True``.
"""

import re
import logging
from typing import Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from app.models import Product
from app.providers import ShopProvider, HTTP_ERRORS, save_debug_html

logger = logging.getLogger(__name__)


class IdealoProvider(ShopProvider):
    """Idealo.de price comparison search."""

    name = "Idealo"

    def __init__(self):
        super().__init__()
        self.enabled = False  # Disabled by default — aggressive bot protection

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
        if progress_callback:
            progress_callback("Suche auf Idealo.de...", 10)

        search_url = (
            f"https://www.idealo.de/preisvergleich/MainSearchProductCategory.html"
            f"?q={quote_plus(query)}"
        )
        logger.info(f"Idealo search: {search_url}")

        try:
            resp = self.session.get(
                search_url, timeout=20,
                headers={"Referer": "https://www.idealo.de/"},
            )
            logger.info(f"Idealo status: {resp.status_code}")

            if resp.status_code != 200:
                save_debug_html("idealo_error.html", resp.text, search_url)
                logger.warning(f"Idealo returned {resp.status_code}")
                return []

            save_debug_html("idealo_search.html", resp.text, search_url)
            soup = BeautifulSoup(resp.text, "lxml")

            products: list[Product] = []

            # Try data-testid selectors (stable)
            for card in soup.select("[data-testid='resultItem'], .offerList-item"):
                title_el = card.select_one(
                    "[data-testid='productTitle'], .offerList-item-description-title"
                )
                price_el = card.select_one(
                    "[data-testid='productPrice'], .offerList-item-price"
                )
                link_el = card.select_one("a[href]")

                if not title_el or not price_el:
                    continue

                title = title_el.get_text(strip=True)
                price = self.extract_price(price_el.get_text(strip=True))
                if not price:
                    continue

                link = ""
                if link_el:
                    href = link_el.get("href", "")
                    if href:
                        link = href if href.startswith("http") else f"https://www.idealo.de{href}"

                products.append(Product(
                    rank=0,
                    title=title,
                    price=price,
                    currency="€",
                    merchant="Idealo",
                    link=link,
                    source="Idealo",
                ))

            if progress_callback:
                progress_callback(f"{len(products)} Idealo-Ergebnisse", 80)

            logger.info(f"Idealo extracted {len(products)} products")
            return products

        except HTTP_ERRORS as e:
            logger.error(f"Idealo request error: {e}")
            return []
