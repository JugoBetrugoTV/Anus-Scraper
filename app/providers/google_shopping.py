"""
Google Shopping provider — fallback / supplementary source.

Queries Google Shopping (supports both tbm=shop and udm=28 redirect)
and parses results with multiple strategies.
"""

import re
import logging
from typing import Optional
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup, Tag

from app.models import Product
from app.providers import (
    ShopProvider, HTTP_ERRORS, save_debug_html,
    SORT_OPTIONS, CONDITION_OPTIONS,
)

logger = logging.getLogger(__name__)


class GoogleShoppingProvider(ShopProvider):
    """Scrapes Google Shopping for product prices."""

    name = "Google Shopping"

    def __init__(self):
        super().__init__()
        self._consent_handled = False

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
        self._handle_consent()

        if progress_callback:
            progress_callback(
                f"Durchsuche Google Shopping ({country.upper()})...", 60,
            )

        params = {
            "q": query,
            "tbm": "shop",
            "gl": country,
            "hl": "de",
            "num": "40",
        }

        tbs_parts = []
        sort_val = SORT_OPTIONS.get(sort, "")
        if sort_val:
            tbs_parts.append(sort_val)
        cond_val = CONDITION_OPTIONS.get(condition, "")
        if cond_val:
            tbs_parts.append(f"mr:1,condition:{cond_val}")
        if price_min is not None or price_max is not None:
            pf = "mr:1,price:1"
            if price_min is not None:
                pf += f",ppr_min:{int(price_min)}"
            if price_max is not None:
                pf += f",ppr_max:{int(price_max)}"
            tbs_parts.append(pf)
        if tbs_parts:
            params["tbs"] = ",".join(tbs_parts)

        query_str = "&".join(
            f"{k}={quote_plus(str(v))}" for k, v in params.items()
        )
        url = f"https://www.google.com/search?{query_str}"

        products: list[Product] = []
        try:
            resp = self.session.get(url, timeout=15)
            logger.info(
                f"Google Shopping status: {resp.status_code}, "
                f"final URL: {resp.url}"
            )
            logger.info(
                f"Response encoding: {resp.encoding}, "
                f"length: {len(resp.text)}"
            )

            if resp.status_code != 200:
                save_debug_html("google_error.html", resp.text, resp.url)
                logger.warning(f"Google Shopping returned {resp.status_code}")
                return []

            if "sorry" in resp.url or "/sorry/" in resp.url:
                logger.warning("Google blocked with CAPTCHA")
                save_debug_html("google_captcha.html", resp.text, resp.url)
                return []

            html_text = resp.text
            soup = BeautifulSoup(html_text, "lxml")
            save_debug_html("google_shopping.html", html_text, resp.url)

            page_title = soup.title.string if soup.title else "NO TITLE"
            logger.info(f"Google page title: {page_title}")
            logger.debug(f"HTML first 500 chars: {html_text[:500]}")

            products = self._parse_results(soup, html_text)
            logger.info(f"Google Shopping extracted {len(products)} products")

        except HTTP_ERRORS as e:
            logger.error(f"Google Shopping error: {e}")

        return products

    # ------------------------------------------------------------------
    #  Consent & session helpers
    # ------------------------------------------------------------------

    def _handle_consent(self):
        if self._consent_handled:
            return
        try:
            resp = self.session.get("https://www.google.de/", timeout=10)
            if (
                "consent.google" in resp.url
                or "consent" in resp.text[:5000].lower()
            ):
                soup = BeautifulSoup(resp.text, "lxml")
                form = soup.find("form", action=re.compile(r'consent|save'))
                if form:
                    action = form.get("action", "")
                    if not action.startswith("http"):
                        action = urljoin(resp.url, action)
                    data = {}
                    for inp in form.find_all("input"):
                        name = inp.get("name")
                        if name:
                            data[name] = inp.get("value", "")
                    self.session.post(action, data=data, timeout=10)
                    logger.info("Google consent submitted")
            self._consent_handled = True
        except Exception as e:
            logger.debug(f"Consent handling error: {e}")

    # ------------------------------------------------------------------
    #  Parsing strategies
    # ------------------------------------------------------------------

    def _parse_results(
        self, soup: BeautifulSoup, raw_html: str,
    ) -> list[Product]:
        products: list[Product] = []

        # Strategy 1: classic shopping grid cards
        cards = soup.select(
            "div.sh-dgr__grid-result, div.sh-dgr__content, "
            "div.sh-pr__product-results-grid div.sh-dlr__list-result"
        )
        logger.debug(f"Strategy 1 (classic cards): found {len(cards)} cards")
        for card in cards:
            p = self._parse_card(card)
            if p:
                products.append(p)
        if products:
            logger.info(f"Strategy 1 found {len(products)} products")
            return products

        # Strategy 2: h3 + price containers
        h3_tags = soup.find_all("h3")
        logger.debug(f"Strategy 2 (h3 scan): found {len(h3_tags)} h3 tags")
        for h3 in h3_tags:
            title = h3.get_text(strip=True)
            if not title or len(title) < 3:
                continue
            container = h3.parent
            for _ in range(6):
                if container is None or container.name == "body":
                    break
                text = container.get_text(" ", strip=True)
                pm = re.search(
                    r'([\d]{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*€|'
                    r'€\s*([\d]{1,3}(?:[.,]\d{3})*[.,]\d{2})',
                    text,
                )
                if pm:
                    price = self.extract_price(pm.group(1) or pm.group(2))
                    if price:
                        merchant = self._merchant_from_container(
                            container, title,
                        )
                        link = ""
                        a = container.find("a", href=True)
                        if a:
                            href = a.get("href", "")
                            link = (
                                href if href.startswith("http")
                                else f"https://www.google.com{href}"
                            )
                        products.append(Product(
                            rank=0, title=title, price=price, currency="€",
                            merchant=merchant, link=link,
                            source="Google Shopping",
                        ))
                        break
                container = container.parent
        if products:
            logger.info(f"Strategy 2 found {len(products)} products")
            return products

        # Strategy 3: link scan
        all_links = soup.find_all("a", href=True)
        logger.debug(f"Strategy 3 (link scan): {len(all_links)} total links")
        for a in all_links:
            href = a.get("href", "")
            if not any(
                x in href
                for x in ["/shopping/product/", "/url?", "merchant", "shop"]
            ):
                continue
            parent = a.parent
            for _ in range(4):
                if parent and parent.parent and parent.parent.name != "body":
                    parent = parent.parent
                else:
                    break
            if parent:
                text = parent.get_text(" ", strip=True)
                pm = re.search(
                    r'([\d]{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*€', text,
                )
                if pm:
                    price = self.extract_price(pm.group(1))
                    if price:
                        title = a.get_text(strip=True)
                        h = parent.find(["h3", "h4"])
                        if h:
                            title = h.get_text(strip=True)
                        if title and len(title) > 3:
                            link = (
                                href if href.startswith("http")
                                else f"https://www.google.com{href}"
                            )
                            products.append(Product(
                                rank=0, title=title, price=price, currency="€",
                                merchant="Google Shopping", link=link,
                                source="Google Shopping",
                            ))
        if products:
            logger.info(f"Strategy 3 found {len(products)} products")
            return products

        # Strategy 4: raw regex fallback
        logger.debug("Strategy 4 (regex fallback)")
        price_pat = re.compile(r'([\d]{1,3}(?:\.\d{3})*,\d{2})\s*€')
        title_pat = re.compile(r'<h3[^>]*>([^<]{5,120})</h3>')

        titles_found = title_pat.findall(raw_html)
        prices_found = price_pat.findall(raw_html)
        logger.debug(
            f"Regex found {len(titles_found)} titles, "
            f"{len(prices_found)} prices"
        )

        for tm in title_pat.finditer(raw_html):
            title = tm.group(1).strip()
            after = raw_html[tm.end():tm.end() + 500]
            pm = price_pat.search(after)
            if pm:
                price = self.extract_price(pm.group(1))
                if price:
                    products.append(Product(
                        rank=0, title=title, price=price, currency="€",
                        merchant="Google Shopping", link="",
                        source="Google Shopping",
                    ))

        logger.info(f"Strategy 4 found {len(products)} products")
        return products

    def _parse_card(self, card: Tag) -> Optional[Product]:
        title = ""
        for sel in ["h3", "h4", "[role='heading']", "[aria-level]"]:
            el = card.select_one(sel)
            if el:
                title = el.get_text(strip=True)
                if title:
                    break
        if not title:
            return None

        price = None
        for span in card.find_all("span"):
            txt = span.get_text(strip=True)
            if "€" in txt:
                price = self.extract_price(txt)
                if price:
                    break
        if not price:
            return None

        merchant = self._merchant_from_container(card, title)
        link = ""
        a = card.select_one("a[href]")
        if a:
            href = a.get("href", "")
            link = (
                href if href.startswith("http")
                else f"https://www.google.com{href}"
            )

        return Product(
            rank=0, title=title, price=price, currency="€",
            merchant=merchant, link=link, source="Google Shopping",
        )

    def _merchant_from_container(self, container: Tag, title: str) -> str:
        for sel in [
            ".aULzUe", ".IuHnof", "[data-merchant]",
            ".sh-np__seller-container",
        ]:
            el = container.select_one(sel)
            if el:
                name = el.get_text(strip=True)
                if name:
                    return name

        skip = {
            "suche", "filter", "ergebnis", "seite", "mehr", "anzeige",
        }
        for el in container.find_all(["span", "div"]):
            txt = el.get_text(strip=True)
            if (
                txt and 3 < len(txt) < 40
                and "€" not in txt
                and txt != title
                and not txt.startswith("http")
                and not any(c.isdigit() for c in txt[:2])
            ):
                if not any(w in txt.lower() for w in skip):
                    return txt

        return "Unbekannter Händler"
