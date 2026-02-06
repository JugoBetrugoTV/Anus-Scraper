"""
Notebooksbilliger.de provider — German electronics retailer.

To activate, implement search() and set ``enabled = True``.
"""

import re
import logging
from typing import Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from app.models import Product
from app.providers import ShopProvider, HTTP_ERRORS, save_debug_html

logger = logging.getLogger(__name__)


class NotebooksbilligerProvider(ShopProvider):
    """Notebooksbilliger.de product search."""

    name = "Notebooksbilliger"

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
        if progress_callback:
            progress_callback("Suche auf Notebooksbilliger.de...", 10)

        search_url = (
            f"https://www.notebooksbilliger.de/productlist.php"
            f"?s={quote_plus(query)}"
        )
        logger.info(f"Notebooksbilliger search: {search_url}")

        try:
            resp = self.session.get(
                search_url, timeout=20,
                headers={"Referer": "https://www.notebooksbilliger.de/"},
            )
            logger.info(f"Notebooksbilliger status: {resp.status_code}")

            if resp.status_code != 200:
                save_debug_html(
                    "notebooksbilliger_error.html", resp.text, search_url,
                )
                return []

            save_debug_html(
                "notebooksbilliger_search.html", resp.text, search_url,
            )
            soup = BeautifulSoup(resp.text, "lxml")

            products: list[Product] = []

            for card in soup.select(
                ".product-card, .js-product-card, .product_listing_box"
            ):
                title_el = card.select_one(
                    ".product-card__title, .product_listing_box_title a"
                )
                price_el = card.select_one(
                    ".product-card__price, .product_listing_box_price"
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
                        link = (
                            href if href.startswith("http")
                            else f"https://www.notebooksbilliger.de{href}"
                        )

                avail_el = card.select_one(
                    ".product-card__availability, .availability"
                )
                availability = avail_el.get_text(strip=True) if avail_el else ""

                products.append(Product(
                    rank=0,
                    title=title,
                    price=price,
                    currency="€",
                    merchant="Notebooksbilliger",
                    link=link,
                    source="Notebooksbilliger",
                    availability=availability,
                ))

            if progress_callback:
                progress_callback(
                    f"{len(products)} Notebooksbilliger-Ergebnisse", 80,
                )

            logger.info(
                f"Notebooksbilliger extracted {len(products)} products"
            )
            return products

        except HTTP_ERRORS as e:
            logger.error(f"Notebooksbilliger request error: {e}")
            return []
