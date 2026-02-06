"""
Price comparison scraper - uses Geizhals.de and Google Shopping.
Geizhals already aggregates prices from hundreds of European retailers,
which is exactly what we need.
"""

import re
import os
import time
import random
import logging
from typing import Optional
from urllib.parse import quote_plus, urljoin, urlparse, parse_qs
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag

# curl_cffi provides browser-grade TLS fingerprinting to bypass Cloudflare & bot detection
try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    curl_requests = None
    HAS_CURL_CFFI = False

from app.models import Product

logger = logging.getLogger(__name__)

# Unified exception tuple for HTTP errors from either library
_HTTP_ERRORS = [requests.RequestException, OSError]
if HAS_CURL_CFFI:
    try:
        _HTTP_ERRORS.append(curl_requests.errors.RequestsError)
    except (AttributeError, TypeError):
        pass
HTTP_ERRORS = tuple(_HTTP_ERRORS)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]

EU_COUNTRIES = {
    "de": "Deutschland",
    "at": "Österreich",
    "fr": "Frankreich",
    "it": "Italien",
    "es": "Spanien",
    "nl": "Niederlande",
    "be": "Belgien",
    "pl": "Polen",
    "pt": "Portugal",
}

SORT_OPTIONS = {
    "relevanz": "",
    "preis_aufsteigend": "p_ord:p",
    "preis_absteigend": "p_ord:pd",
    "bewertung": "p_ord:rv",
}

CONDITION_OPTIONS = {
    "alle": "",
    "neu": "new",
    "gebraucht": "used",
}

# Debug directory for saving HTML when scraping fails
DEBUG_DIR = Path(os.path.expanduser("~")) / "PreisHai_debug"


def _save_debug_html(filename: str, content: str, url: str):
    """Save HTML to debug directory for troubleshooting."""
    try:
        DEBUG_DIR.mkdir(exist_ok=True)
        filepath = DEBUG_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"<!-- URL: {url} -->\n")
            f.write(content)
        logger.info(f"Debug HTML saved to {filepath}")
    except Exception as e:
        logger.debug(f"Could not save debug HTML: {e}")


class PriceScraper:
    """Scrapes Geizhals.de and Google Shopping for European product prices."""

    def __init__(self):
        self._using_curl_cffi = False
        self._geizhals_ready = False
        self._consent_handled = False
        self._setup_session()

    def _setup_session(self):
        """Set up HTTP session with browser-like TLS fingerprinting.

        Uses curl_cffi with Chrome impersonation when available, which provides
        a genuine browser TLS fingerprint that bypasses Cloudflare and Google
        bot detection.  Falls back to plain requests with manual headers.
        """
        if HAS_CURL_CFFI:
            try:
                self.session = curl_requests.Session(impersonate="chrome120")
                self._using_curl_cffi = True
                logger.info("Using curl_cffi with Chrome TLS impersonation")
            except Exception as e:
                logger.warning(f"curl_cffi init failed ({e}), falling back to requests")
                self.session = requests.Session()
                self._using_curl_cffi = False
        else:
            logger.info(
                "curl_cffi not available – using requests "
                "(install curl_cffi for better anti-bot bypass)"
            )
            self.session = requests.Session()
            self._using_curl_cffi = False

        if self._using_curl_cffi:
            # Impersonation already sets User-Agent, Sec-CH-UA, Accept-Encoding
            # etc.  We only need to add German language preference.
            self.session.headers.update({
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            })
        else:
            # Full manual header set for plain requests library
            ua = random.choice(USER_AGENTS)
            self.session.headers.update({
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            })

    def _extract_price(self, text: str) -> Optional[float]:
        """Parse European price format (1.234,56 €) to float."""
        if not text:
            return None
        cleaned = text.strip()
        cleaned = re.sub(r'[^\d.,]', '', cleaned)
        if not cleaned:
            return None
        if ',' in cleaned and '.' in cleaned:
            if cleaned.rindex(',') > cleaned.rindex('.'):
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        try:
            val = float(cleaned)
            if 0.01 <= val <= 999999:
                return val
            return None
        except ValueError:
            return None

    # =========================================================
    #  GEIZHALS.DE SCRAPER
    # =========================================================

    def _geizhals_warmup(self):
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

    def _geizhals_search(self, query: str, progress_callback=None) -> list[dict]:
        """Search Geizhals.de and return list of product dicts with URL + name."""
        self._geizhals_warmup()

        search_url = f"https://geizhals.de/?fs={quote_plus(query)}&hloc=at&hloc=de&hloc=eu"
        logger.info(f"Geizhals search: {search_url}")

        if progress_callback:
            progress_callback("Durchsuche Geizhals.de...", 10)

        try:
            resp = None
            # Retry loop – Cloudflare may challenge the first request
            for attempt in range(3):
                resp = self.session.get(
                    search_url,
                    timeout=20,
                    headers={"Referer": "https://geizhals.de/"},
                )
                logger.info(f"Geizhals search status: {resp.status_code} (attempt {attempt + 1})")

                if resp.status_code == 200:
                    break

                if resp.status_code == 403 and attempt < 2:
                    wait = (attempt + 1) * 2
                    logger.info(f"Cloudflare challenge detected, retrying in {wait}s...")
                    _save_debug_html(f"geizhals_cf_{attempt}.html", resp.text, search_url)
                    time.sleep(wait)
                    # Re-warm to get fresh cookies
                    self._geizhals_ready = False
                    self._geizhals_warmup()
                    continue

                # Non-retryable status
                break

            if resp is None or resp.status_code != 200:
                if resp is not None:
                    _save_debug_html("geizhals_search_error.html", resp.text, search_url)
                    logger.warning(f"Geizhals search returned {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.text, "lxml")
            _save_debug_html("geizhals_search.html", resp.text, search_url)

            products = []

            # Strategy 1: Look for product list items with links to product pages
            # Geizhals product URLs look like: /product-name-a1234567.html
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

                # Avoid duplicates
                if not any(p["url"] == href for p in products):
                    products.append({"name": name, "url": href})

            # Strategy 2: Look for links in category listing divs
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
            return products[:10]  # Top 10 matches

        except HTTP_ERRORS as e:
            logger.error(f"Geizhals search request error: {e}")
            return []

    def _geizhals_get_offers(self, product_url: str, product_name: str,
                              progress_callback=None, progress_base: int = 30) -> list[Product]:
        """Get all retailer offers for a specific Geizhals product page."""
        logger.info(f"Geizhals offers: {product_url}")

        try:
            resp = self.session.get(
                product_url, timeout=20,
                headers={"Referer": "https://geizhals.de/"},
            )
            if resp.status_code != 200:
                _save_debug_html("geizhals_offers_error.html", resp.text, product_url)
                return []

            soup = BeautifulSoup(resp.text, "lxml")
            _save_debug_html("geizhals_offers.html", resp.text, product_url)

            offers = []

            # Get the actual product title from the page
            page_title = product_name
            h1 = soup.select_one("h1")
            if h1:
                page_title = h1.get_text(strip=True) or product_name

            # Strategy 1: Offer table/list - look for price + merchant pairs
            # Geizhals has offer rows with merchant name, price, and link
            offer_rows = soup.select(".offer, .offers__row, tr.offer__row, [class*='offer']")
            if not offer_rows:
                # Try broader selectors
                offer_rows = soup.select("div.variant, .product-offer, .price-list-row")

            for row in offer_rows:
                offer = self._parse_geizhals_offer_row(row, page_title)
                if offer:
                    offers.append(offer)

            # Strategy 2: If no structured offers found, look for price+merchant patterns
            if not offers:
                offers = self._geizhals_extract_by_pattern(soup, page_title, product_url)

            # Strategy 3: Parse the full page looking for shop names next to prices
            if not offers:
                offers = self._geizhals_extract_by_text(soup, page_title)

            logger.info(f"Geizhals extracted {len(offers)} offers for '{page_title}'")
            return offers

        except HTTP_ERRORS as e:
            logger.error(f"Geizhals offers request error: {e}")
            return []

    def _parse_geizhals_offer_row(self, row: Tag, product_title: str) -> Optional[Product]:
        """Parse a single offer row from Geizhals product page."""
        # Extract price - look for € amounts
        price = None
        price_text = ""

        # Try specific price selectors
        for sel in [".offer__price", ".price", "[class*='price']", "span.gh_price"]:
            el = row.select_one(sel)
            if el:
                price_text = el.get_text(strip=True)
                price = self._extract_price(price_text)
                if price:
                    break

        # Fallback: scan all text nodes for € prices
        if price is None:
            all_text = row.get_text(" ", strip=True)
            price_match = re.search(r'([\d.,]+)\s*€|€\s*([\d.,]+)', all_text)
            if price_match:
                price_str = price_match.group(1) or price_match.group(2)
                price = self._extract_price(price_str)

        if price is None:
            return None

        # Extract merchant name
        merchant = ""
        for sel in [".offer__shop", ".merchant", ".shop-name", "[class*='merchant']",
                     "[class*='shop']", "a[class*='logo']", ".offer__clickout"]:
            el = row.select_one(sel)
            if el:
                merchant = el.get_text(strip=True)
                if not merchant:
                    merchant = el.get("title", "") or el.get("alt", "")
                if merchant:
                    break

        # Try image alt text for shop name
        if not merchant:
            img = row.select_one("img[alt]")
            if img:
                alt = img.get("alt", "").strip()
                if alt and len(alt) < 50:
                    merchant = alt

        if not merchant:
            merchant = "Unbekannter Händler"

        # Extract shop link
        link = ""
        for sel in [".offer__clickout", "a[href*='redir']", "a[href*='click']",
                     "a[rel='nofollow']", "a[target='_blank']"]:
            el = row.select_one(sel)
            if el:
                href = el.get("href", "")
                if href:
                    link = href if href.startswith("http") else f"https://geizhals.de{href}"
                    break

        if not link:
            a = row.select_one("a[href]")
            if a:
                href = a.get("href", "")
                if href:
                    link = href if href.startswith("http") else f"https://geizhals.de{href}"

        # Delivery info
        delivery = ""
        for sel in [".offer__delivery", "[class*='delivery']", "[class*='shipping']", "[class*='avail']"]:
            el = row.select_one(sel)
            if el:
                delivery = el.get_text(strip=True)
                if delivery:
                    break

        return Product(
            rank=0,
            title=product_title,
            price=price,
            currency="€",
            merchant=merchant,
            link=link,
            delivery_info=delivery,
        )

    def _geizhals_extract_by_pattern(self, soup: BeautifulSoup, title: str, url: str) -> list[Product]:
        """Extract offers by finding price patterns near merchant-like text."""
        products = []
        html = str(soup)

        # Find all € price occurrences
        price_pattern = re.compile(r'([\d]{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*€')

        for match in price_pattern.finditer(html):
            price = self._extract_price(match.group(1))
            if not price:
                continue

            # Look for merchant info in surrounding context
            start = max(0, match.start() - 300)
            end = min(len(html), match.end() + 300)
            context = html[start:end]

            # Try to find shop name from links or text
            merchant = "Unbekannter Händler"
            shop_match = re.search(r'title="([^"]{3,40})"', context)
            if shop_match:
                candidate = shop_match.group(1).strip()
                if "€" not in candidate and not candidate.startswith("http"):
                    merchant = candidate

            # Find link
            link = ""
            link_match = re.search(r'href="(https?://[^"]+)"', context)
            if link_match:
                link = link_match.group(1)

            products.append(Product(
                rank=0, title=title, price=price, currency="€",
                merchant=merchant, link=link,
            ))

        return products

    def _geizhals_extract_by_text(self, soup: BeautifulSoup, title: str) -> list[Product]:
        """Last resort: find all prices on page and try to associate with merchants."""
        products = []
        seen_prices = set()

        # Find all elements containing € prices
        for el in soup.find_all(string=re.compile(r'\d+[.,]\d{2}\s*€|€\s*\d+[.,]\d{2}')):
            text = el.strip()
            price = self._extract_price(text)
            if not price or price in seen_prices:
                continue
            seen_prices.add(price)

            # Walk up to find merchant info
            parent = el.parent
            merchant = "Unbekannter Händler"
            link = ""
            for _ in range(8):
                if parent is None:
                    break
                # Look for links or merchant text in parent
                a = parent.find("a", href=True) if isinstance(parent, Tag) else None
                if a:
                    link_text = a.get_text(strip=True)
                    href = a.get("href", "")
                    if link_text and len(link_text) < 50 and "€" not in link_text:
                        merchant = link_text
                    if href:
                        link = href if href.startswith("http") else f"https://geizhals.de{href}"
                    if merchant != "Unbekannter Händler":
                        break
                parent = parent.parent if isinstance(parent, Tag) else None

            products.append(Product(
                rank=0, title=title, price=price, currency="€",
                merchant=merchant, link=link,
            ))

        return products

    # =========================================================
    #  GOOGLE SHOPPING SCRAPER (fallback)
    # =========================================================

    def _handle_google_consent(self):
        """Handle Google's EU cookie consent page."""
        if self._consent_handled:
            return

        try:
            resp = self.session.get("https://www.google.de/", timeout=10)
            if "consent.google" in resp.url or "consent" in resp.text[:5000].lower():
                soup = BeautifulSoup(resp.text, "lxml")
                # Find and submit the consent form
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

    def _google_shopping_search(
        self, query: str, country: str = "de",
        sort: str = "preis_aufsteigend",
        condition: str = "alle",
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        progress_callback=None,
    ) -> list[Product]:
        """Search Google Shopping (supports both tbm=shop and udm=28 redirect)."""
        self._handle_google_consent()

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

        query_str = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        url = f"https://www.google.com/search?{query_str}"

        products = []
        try:
            if progress_callback:
                progress_callback(f"Durchsuche Google Shopping ({country.upper()})...", 60)

            resp = self.session.get(url, timeout=15)
            logger.info(f"Google Shopping status: {resp.status_code}, final URL: {resp.url}")
            logger.info(f"Response encoding: {resp.encoding}, length: {len(resp.text)}")

            if resp.status_code != 200:
                _save_debug_html("google_error.html", resp.text, resp.url)
                logger.warning(f"Google Shopping returned {resp.status_code}")
                return []

            # Check for CAPTCHA/block
            if "sorry" in resp.url or "/sorry/" in resp.url:
                logger.warning("Google blocked with CAPTCHA")
                _save_debug_html("google_captcha.html", resp.text, resp.url)
                return []

            html_text = resp.text
            soup = BeautifulSoup(html_text, "lxml")
            _save_debug_html("google_shopping.html", html_text, resp.url)

            # Log what we found for debugging
            page_title = soup.title.string if soup.title else "NO TITLE"
            logger.info(f"Google page title: {page_title}")
            logger.debug(f"HTML first 500 chars: {html_text[:500]}")

            # Extract products with multiple strategies
            products = self._parse_google_results(soup, html_text)
            logger.info(f"Google Shopping extracted {len(products)} products")

        except HTTP_ERRORS as e:
            logger.error(f"Google Shopping error: {e}")

        return products

    def _parse_google_results(self, soup: BeautifulSoup, raw_html: str) -> list[Product]:
        """Parse Google Shopping results with multiple strategies for both
        old (tbm=shop) and new (udm=28) formats."""
        products = []

        # === STRATEGY 1: Classic Shopping grid cards ===
        cards = soup.select("div.sh-dgr__grid-result, div.sh-dgr__content, div.sh-pr__product-results-grid div.sh-dlr__list-result")
        logger.debug(f"Strategy 1 (classic cards): found {len(cards)} cards")
        for card in cards:
            p = self._parse_google_card(card)
            if p:
                products.append(p)

        if products:
            logger.info(f"Strategy 1 found {len(products)} products")
            return products

        # === STRATEGY 2: Generic product containers with h3 + price ===
        # Google udm=28 uses various div structures
        # Find all h3 tags that could be product titles
        h3_tags = soup.find_all("h3")
        logger.debug(f"Strategy 2 (h3 scan): found {len(h3_tags)} h3 tags")
        for h3 in h3_tags:
            title = h3.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            # Walk up to find the product container
            container = h3.parent
            for _ in range(6):
                if container is None or container.name == "body":
                    break
                # Look for price in this container
                container_text = container.get_text(" ", strip=True)
                price_match = re.search(r'([\d]{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*€|€\s*([\d]{1,3}(?:[.,]\d{3})*[.,]\d{2})', container_text)
                if price_match:
                    price_str = price_match.group(1) or price_match.group(2)
                    price = self._extract_price(price_str)
                    if price:
                        # Found title + price pair
                        merchant = self._extract_merchant_from_container(container, title)
                        link = ""
                        a = container.find("a", href=True)
                        if a:
                            href = a.get("href", "")
                            link = href if href.startswith("http") else f"https://www.google.com{href}"

                        products.append(Product(
                            rank=0, title=title, price=price, currency="€",
                            merchant=merchant, link=link,
                        ))
                        break
                container = container.parent

        if products:
            logger.info(f"Strategy 2 found {len(products)} products")
            return products

        # === STRATEGY 3: Find all links with product-like structure ===
        all_links = soup.find_all("a", href=True)
        logger.debug(f"Strategy 3 (link scan): {len(all_links)} total links")
        for a in all_links:
            href = a.get("href", "")
            # Skip non-product links
            if not any(x in href for x in ["/shopping/product/", "/url?", "merchant", "shop"]):
                continue

            # Get text content of the link and its parent
            parent = a.parent
            for _ in range(4):
                if parent and parent.parent and parent.parent.name != "body":
                    parent = parent.parent
                else:
                    break

            if parent:
                text = parent.get_text(" ", strip=True)
                price_match = re.search(r'([\d]{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*€', text)
                if price_match:
                    price = self._extract_price(price_match.group(1))
                    if price:
                        # Try to get title from the link or heading
                        title = a.get_text(strip=True)
                        h = parent.find(["h3", "h4"])
                        if h:
                            title = h.get_text(strip=True)
                        if title and len(title) > 3:
                            link = href if href.startswith("http") else f"https://www.google.com{href}"
                            products.append(Product(
                                rank=0, title=title, price=price, currency="€",
                                merchant="Google Shopping", link=link,
                            ))

        if products:
            logger.info(f"Strategy 3 found {len(products)} products")
            return products

        # === STRATEGY 4: Raw HTML regex - last resort ===
        logger.debug("Strategy 4 (regex fallback)")
        price_pattern = re.compile(r'([\d]{1,3}(?:\.\d{3})*,\d{2})\s*€')
        title_pattern = re.compile(r'<h3[^>]*>([^<]{5,120})</h3>')

        titles_found = title_pattern.findall(raw_html)
        prices_found = price_pattern.findall(raw_html)
        logger.debug(f"Regex found {len(titles_found)} titles, {len(prices_found)} prices")

        # Try to pair titles with nearby prices
        for title_match in title_pattern.finditer(raw_html):
            title = title_match.group(1).strip()
            # Look for price within 500 chars after the title
            after_title = raw_html[title_match.end():title_match.end() + 500]
            price_m = price_pattern.search(after_title)
            if price_m:
                price = self._extract_price(price_m.group(1))
                if price:
                    products.append(Product(
                        rank=0, title=title, price=price, currency="€",
                        merchant="Google Shopping", link="",
                    ))

        logger.info(f"Strategy 4 found {len(products)} products")
        return products

    def _parse_google_card(self, card: Tag) -> Optional[Product]:
        """Parse a single Google Shopping product card."""
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
                price = self._extract_price(txt)
                if price:
                    break
        if not price:
            return None

        merchant = self._extract_merchant_from_container(card, title)

        link = ""
        a = card.select_one("a[href]")
        if a:
            href = a.get("href", "")
            link = href if href.startswith("http") else f"https://www.google.com{href}"

        return Product(
            rank=0, title=title, price=price, currency="€",
            merchant=merchant, link=link,
        )

    def _extract_merchant_from_container(self, container: Tag, title: str) -> str:
        """Try to extract merchant name from a product container."""
        # Try known merchant selectors
        for sel in [".aULzUe", ".IuHnof", "[data-merchant]", ".sh-np__seller-container"]:
            el = container.select_one(sel)
            if el:
                name = el.get_text(strip=True)
                if name:
                    return name

        # Look for small text elements that might be merchant names
        for el in container.find_all(["span", "div"]):
            txt = el.get_text(strip=True)
            if (txt and 3 < len(txt) < 40
                    and "€" not in txt
                    and txt != title
                    and not txt.startswith("http")
                    and not any(c.isdigit() for c in txt[:2])):
                # Check if this looks like a merchant (no common non-merchant patterns)
                if not any(w in txt.lower() for w in ["suche", "filter", "ergebnis", "seite", "mehr", "anzeige"]):
                    return txt

        return "Unbekannter Händler"

    # =========================================================
    #  MAIN SEARCH
    # =========================================================

    def search(
        self,
        query: str,
        country: str = "de",
        sort: str = "preis_aufsteigend",
        condition: str = "alle",
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        max_results: int = 20,
        progress_callback=None,
    ) -> list[Product]:
        """
        Search for products across multiple sources.
        Primary: Geizhals.de (best for EU price comparison)
        Fallback: Google Shopping
        """
        all_products = []

        # === SOURCE 1: GEIZHALS.DE ===
        if progress_callback:
            progress_callback("Suche auf Geizhals.de...", 5)

        geizhals_results = self._geizhals_search(query, progress_callback)

        if geizhals_results:
            if progress_callback:
                progress_callback(
                    f"{len(geizhals_results)} Produkte auf Geizhals gefunden, lade Angebote...",
                    20,
                )

            # Get offers for the top matching products
            for i, product_info in enumerate(geizhals_results[:3]):
                pct = 20 + int((i / min(3, len(geizhals_results))) * 40)
                if progress_callback:
                    progress_callback(
                        f"Lade Angebote für: {product_info['name'][:50]}...",
                        pct,
                    )

                offers = self._geizhals_get_offers(
                    product_info["url"], product_info["name"],
                    progress_callback, pct,
                )
                all_products.extend(offers)
                time.sleep(random.uniform(0.5, 1.5))

                if len(all_products) >= max_results:
                    break

        # === SOURCE 2: GOOGLE SHOPPING (fallback) ===
        if len(all_products) < max_results:
            if progress_callback:
                progress_callback("Durchsuche Google Shopping als Ergänzung...", 65)

            google_results = self._google_shopping_search(
                query, country, sort, condition, price_min, price_max,
                progress_callback,
            )
            all_products.extend(google_results)

        if progress_callback:
            progress_callback("Ergebnisse werden sortiert...", 90)

        # === POST-PROCESSING ===
        # Deduplicate by merchant + similar price
        seen = set()
        unique = []
        for p in all_products:
            key = (p.merchant.lower().strip(), round(p.price, 2))
            if key not in seen:
                seen.add(key)
                unique.append(p)

        # Apply price filters
        if price_min is not None:
            unique = [p for p in unique if p.price >= price_min]
        if price_max is not None:
            unique = [p for p in unique if p.price <= price_max]

        # Sort
        if sort == "preis_absteigend":
            unique.sort(key=lambda p: p.price, reverse=True)
        elif sort == "bewertung":
            unique.sort(key=lambda p: p.rating, reverse=True)
        else:
            unique.sort(key=lambda p: p.price)

        # Assign ranks
        results = unique[:max_results]
        for i, p in enumerate(results, 1):
            p.rank = i

        if progress_callback:
            if results:
                progress_callback(f"{len(results)} Angebote gefunden!", 100)
            else:
                progress_callback("Keine Ergebnisse gefunden.", 100)

        return results
