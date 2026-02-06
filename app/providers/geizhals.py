"""
Geizhals.de provider — primary European price aggregator.

Geizhals already aggregates prices from hundreds of European retailers,
so a single Geizhals query returns offers across many shops.
"""

import re
import time
import random
import logging
from typing import Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup, Tag

from app.models import Product
from app.providers import (
    ShopProvider, HTTP_ERRORS, save_debug_html, create_session,
)

logger = logging.getLogger(__name__)


class GeizhalsProvider(ShopProvider):
    """Scrapes Geizhals.de for product prices across EU retailers."""

    name = "Geizhals"

    def __init__(self):
        super().__init__()
        self._geizhals_ready = False

    # ------------------------------------------------------------------
    #  Public interface
    # ------------------------------------------------------------------

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
            progress_callback("Suche auf Geizhals.de...", 5)

        product_links = self._search(query, progress_callback)
        if not product_links:
            return []

        if progress_callback:
            progress_callback(
                f"{len(product_links)} Produkte auf Geizhals gefunden, lade Angebote...",
                20,
            )

        all_offers: list[Product] = []
        for i, info in enumerate(product_links[:3]):
            pct = 20 + int((i / min(3, len(product_links))) * 40)
            if progress_callback:
                progress_callback(
                    f"Lade Angebote für: {info['name'][:50]}...", pct,
                )
            offers = self._get_offers(info["url"], info["name"])
            all_offers.extend(offers)
            time.sleep(random.uniform(0.5, 1.5))
            if len(all_offers) >= 20:
                break

        return all_offers

    # ------------------------------------------------------------------
    #  Internals
    # ------------------------------------------------------------------

    def _warmup(self):
        """Visit Geizhals homepage to establish Cloudflare cookies."""
        if self._geizhals_ready:
            return
        try:
            logger.info("Warming up Geizhals session (homepage visit)...")
            resp = self.session.get("https://geizhals.de/", timeout=15)
            logger.info(f"Geizhals homepage status: {resp.status_code}")
            if resp.status_code == 200:
                self._geizhals_ready = True
            time.sleep(random.uniform(0.5, 1.0))
        except HTTP_ERRORS as e:
            logger.debug(f"Geizhals warmup failed: {e}")

    def _search(self, query: str, progress_callback=None) -> list[dict]:
        """Search Geizhals.de and return list of {name, url} dicts."""
        self._warmup()

        search_url = (
            f"https://geizhals.de/?fs={quote_plus(query)}"
            f"&hloc=at&hloc=de&hloc=eu"
        )
        logger.info(f"Geizhals search: {search_url}")

        if progress_callback:
            progress_callback("Durchsuche Geizhals.de...", 10)

        try:
            resp = None
            for attempt in range(3):
                resp = self.session.get(
                    search_url, timeout=20,
                    headers={"Referer": "https://geizhals.de/"},
                )
                logger.info(
                    f"Geizhals search status: {resp.status_code} "
                    f"(attempt {attempt + 1})"
                )
                if resp.status_code == 200:
                    break
                if resp.status_code == 403 and attempt < 2:
                    wait = (attempt + 1) * 2
                    logger.info(
                        f"Cloudflare challenge detected, retrying in {wait}s..."
                    )
                    save_debug_html(
                        f"geizhals_cf_{attempt}.html", resp.text, search_url,
                    )
                    time.sleep(wait)
                    self._geizhals_ready = False
                    self._warmup()
                    continue
                break

            if resp is None or resp.status_code != 200:
                if resp is not None:
                    save_debug_html(
                        "geizhals_search_error.html", resp.text, search_url,
                    )
                    logger.warning(
                        f"Geizhals search returned {resp.status_code}"
                    )
                return []

            soup = BeautifulSoup(resp.text, "lxml")
            save_debug_html("geizhals_search.html", resp.text, search_url)

            products: list[dict] = []
            product_pattern = re.compile(r'-a\d+\.html')

            for a_tag in soup.find_all("a", href=product_pattern):
                href = a_tag.get("href", "")
                name = a_tag.get_text(strip=True)
                if not name or len(name) < 5:
                    continue
                if href.startswith("/"):
                    href = f"https://geizhals.de{href}"
                elif not href.startswith("http"):
                    href = f"https://geizhals.de/{href}"
                if not any(p["url"] == href for p in products):
                    products.append({"name": name, "url": href})

            if not products:
                for a_tag in soup.select("a[href*='geizhals']"):
                    href = a_tag.get("href", "")
                    name = a_tag.get_text(strip=True)
                    if product_pattern.search(href) and name and len(name) > 5:
                        if not href.startswith("http"):
                            href = f"https://geizhals.de{href}"
                        if not any(p["url"] == href for p in products):
                            products.append({"name": name, "url": href})

            logger.info(f"Geizhals found {len(products)} product links")
            return products[:10]

        except HTTP_ERRORS as e:
            logger.error(f"Geizhals search request error: {e}")
            return []

    def _get_offers(self, product_url: str, product_name: str) -> list[Product]:
        """Get all retailer offers for a specific Geizhals product page."""
        logger.info(f"Geizhals offers: {product_url}")
        try:
            resp = self.session.get(
                product_url, timeout=20,
                headers={"Referer": "https://geizhals.de/"},
            )
            if resp.status_code != 200:
                save_debug_html(
                    "geizhals_offers_error.html", resp.text, product_url,
                )
                return []

            soup = BeautifulSoup(resp.text, "lxml")
            save_debug_html("geizhals_offers.html", resp.text, product_url)

            page_title = product_name
            h1 = soup.select_one("h1")
            if h1:
                page_title = h1.get_text(strip=True) or product_name

            offers: list[Product] = []

            # Primary: div.offer rows (Geizhals structured offer list)
            offer_rows = soup.select("div.offer")
            if not offer_rows:
                # Broader fallback
                offer_rows = soup.select(
                    ".offers__row, tr.offer__row, "
                    "[class*='offerlist'] > div"
                )

            for row in offer_rows:
                offer = self._parse_offer_row(row, page_title)
                if offer:
                    offers.append(offer)

            # Strategy 2: pattern-based
            if not offers:
                offers = self._extract_by_pattern(soup, page_title, product_url)

            # Strategy 3: text-based fallback
            if not offers:
                offers = self._extract_by_text(soup, page_title)

            logger.info(
                f"Geizhals extracted {len(offers)} offers for '{page_title}'"
            )
            return offers

        except HTTP_ERRORS as e:
            logger.error(f"Geizhals offers request error: {e}")
            return []

    # ------------------------------------------------------------------
    #  Parsing helpers
    # ------------------------------------------------------------------

    def _parse_offer_row(self, row: Tag, product_title: str) -> Optional[Product]:
        """Parse a single Geizhals offer row with correct CSS selectors."""

        # --- Price ---
        price = None
        price_el = row.select_one("span.gh_price")
        if price_el:
            price = self.extract_price(price_el.get_text(strip=True))
        if price is None:
            for sel in [".offer__price", ".price"]:
                el = row.select_one(sel)
                if el:
                    price = self.extract_price(el.get_text(strip=True))
                    if price:
                        break
        if price is None:
            all_text = row.get_text(" ", strip=True)
            m = re.search(r'([\d.,]+)\s*€|€\s*([\d.,]+)', all_text)
            if m:
                price = self.extract_price(m.group(1) or m.group(2))
        if price is None:
            return None

        # --- Merchant ---
        merchant = ""
        # Primary: span.notrans inside .offer__merchant
        merchant_el = row.select_one(".offer__merchant span.notrans")
        if merchant_el:
            merchant = merchant_el.get_text(strip=True)
        if not merchant:
            merchant_el = row.select_one("span.notrans")
            if merchant_el:
                merchant = merchant_el.get_text(strip=True)
        if not merchant:
            for sel in [".offer__merchant a", "a.offer__clickout",
                        "a[data-merchant-name]"]:
                el = row.select_one(sel)
                if el:
                    merchant = (
                        el.get("data-merchant-name", "")
                        or el.get("title", "")
                        or el.get_text(strip=True)
                    )
                    if merchant:
                        break
        if not merchant:
            img = row.select_one(".offer__merchant img[alt]")
            if not img:
                img = row.select_one("img[alt]")
            if img:
                alt = img.get("alt", "").strip()
                if alt and len(alt) < 60 and "€" not in alt:
                    merchant = alt
        if not merchant:
            merchant = "Unbekannter Händler"

        # --- Link ---
        link = ""
        for sel in ["a.offer_bt", "a.gh_offerlist__offerurl",
                     "a.offer__clickout", "a[href*='redir']"]:
            el = row.select_one(sel)
            if el:
                href = el.get("href", "")
                if href:
                    link = (
                        href if href.startswith("http")
                        else f"https://geizhals.de{href}"
                    )
                    break
        if not link:
            a = row.select_one("a[href]")
            if a:
                href = a.get("href", "")
                if href:
                    link = (
                        href if href.startswith("http")
                        else f"https://geizhals.de{href}"
                    )

        # --- Availability ---
        availability = ""
        row_classes = " ".join(row.get("class", []))
        if "offer--available" in row_classes:
            availability = "Auf Lager"
        elif "offer--shortly" in row_classes:
            availability = "Kurzfristig lieferbar"
        elif "offer--unavailable" in row_classes:
            availability = "Nicht verfügbar"

        if not availability:
            delivery_time_el = row.select_one(".offer__delivery-time")
            if delivery_time_el:
                availability = delivery_time_el.get_text(strip=True)

        # --- Shipping ---
        shipping_cost = 0.0
        delivery_info = ""
        shipping_el = row.select_one(".offer__delivery-payment")
        if shipping_el:
            ship_text = shipping_el.get_text(strip=True)
            ship_upper = ship_text.upper()
            if ("GRATISVERSAND" in ship_upper or "GRATIS" in ship_upper
                    or "KOSTENLOS" in ship_upper):
                delivery_info = "Kostenloser Versand"
                shipping_cost = 0.0
            else:
                ship_match = re.search(
                    r'([\d.,]+)\s*€|€\s*([\d.,]+)', ship_text,
                )
                if ship_match:
                    parsed = self.extract_price(
                        ship_match.group(1) or ship_match.group(2),
                    )
                    if parsed:
                        shipping_cost = parsed
                        delivery_info = f"Versand: {shipping_cost:.2f} €"
                else:
                    delivery_info = ship_text

        if not delivery_info:
            delivery_el = row.select_one(".offer__delivery")
            if delivery_el:
                delivery_info = delivery_el.get_text(" ", strip=True)[:80]

        # --- Rating ---
        rating = 0.0
        reviews = 0
        stars_el = row.select_one("span.gh_stars")
        if stars_el:
            title = stars_el.get("title", "")
            r_match = re.search(r'([\d.,]+)\s*von\s*5', title)
            if r_match:
                try:
                    rating = float(r_match.group(1).replace(",", "."))
                except ValueError:
                    pass
        reviews_el = row.select_one(
            ".rating_amount span, .offer__merchant-rating span",
        )
        if reviews_el:
            r_text = reviews_el.get_text(strip=True)
            r_num = re.search(r'(\d+)', r_text)
            if r_num:
                reviews = int(r_num.group(1))

        return Product(
            rank=0,
            title=product_title,
            price=price,
            currency="€",
            merchant=merchant,
            link=link,
            delivery_info=delivery_info,
            source="Geizhals",
            availability=availability,
            shipping_cost=shipping_cost,
            rating=rating,
            reviews=reviews,
        )

    def _extract_by_pattern(
        self, soup: BeautifulSoup, title: str, url: str,
    ) -> list[Product]:
        products = []
        html = str(soup)
        price_pattern = re.compile(r'([\d]{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*€')

        for match in price_pattern.finditer(html):
            price = self.extract_price(match.group(1))
            if not price:
                continue
            start = max(0, match.start() - 300)
            end = min(len(html), match.end() + 300)
            context = html[start:end]

            merchant = "Unbekannter Händler"
            shop_m = re.search(
                r'class="notrans"[^>]*>([^<]{3,40})<', context,
            )
            if shop_m:
                merchant = shop_m.group(1).strip()
            else:
                shop_m = re.search(r'title="([^"]{3,40})"', context)
                if shop_m:
                    cand = shop_m.group(1).strip()
                    if "€" not in cand and not cand.startswith("http"):
                        merchant = cand

            link = ""
            link_m = re.search(r'href="(https?://[^"]+)"', context)
            if link_m:
                link = link_m.group(1)

            products.append(Product(
                rank=0, title=title, price=price, currency="€",
                merchant=merchant, link=link, source="Geizhals",
            ))
        return products

    def _extract_by_text(self, soup: BeautifulSoup, title: str) -> list[Product]:
        products = []
        seen_prices: set[float] = set()

        for el in soup.find_all(
            string=re.compile(r'\d+[.,]\d{2}\s*€|€\s*\d+[.,]\d{2}')
        ):
            text = el.strip()
            price = self.extract_price(text)
            if not price or price in seen_prices:
                continue
            seen_prices.add(price)

            parent = el.parent
            merchant = "Unbekannter Händler"
            link = ""
            for _ in range(8):
                if parent is None:
                    break
                notrans = (
                    parent.select_one("span.notrans")
                    if isinstance(parent, Tag) else None
                )
                if notrans:
                    merchant = notrans.get_text(strip=True)
                    if merchant:
                        a = (
                            parent.find("a", href=True)
                            if isinstance(parent, Tag) else None
                        )
                        if a:
                            href = a.get("href", "")
                            if href:
                                link = (
                                    href if href.startswith("http")
                                    else f"https://geizhals.de{href}"
                                )
                        break
                a = (
                    parent.find("a", href=True)
                    if isinstance(parent, Tag) else None
                )
                if a:
                    link_text = a.get_text(strip=True)
                    href = a.get("href", "")
                    if (link_text and len(link_text) < 50
                            and "€" not in link_text):
                        merchant = link_text
                    if href:
                        link = (
                            href if href.startswith("http")
                            else f"https://geizhals.de{href}"
                        )
                    if merchant != "Unbekannter Händler":
                        break
                parent = parent.parent if isinstance(parent, Tag) else None

            products.append(Product(
                rank=0, title=title, price=price, currency="€",
                merchant=merchant, link=link, source="Geizhals",
            ))
        return products
