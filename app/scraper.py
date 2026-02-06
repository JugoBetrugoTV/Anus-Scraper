"""
Price comparison scraper - searches Google Shopping for European product prices.
Uses multiple extraction strategies for resilience against HTML changes.
"""

import re
import time
import random
import logging
from typing import Optional
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup, Tag

from app.models import Product

logger = logging.getLogger(__name__)

# Rotate user agents to reduce blocking
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

# European country codes for Google Shopping
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


class PriceScraper:
    """Scrapes Google Shopping for product prices across European markets."""

    BASE_URL = "https://www.google.com/search"

    def __init__(self):
        self.session = requests.Session()
        self._update_headers()

    def _update_headers(self):
        ua = random.choice(USER_AGENTS)
        self.session.headers.update({
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        })

    def _build_url(
        self,
        query: str,
        country: str = "de",
        sort: str = "relevanz",
        condition: str = "alle",
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        page: int = 0,
    ) -> str:
        params = {
            "q": query,
            "tbm": "shop",
            "gl": country,
            "hl": "de",
            "num": "40",
        }
        if page > 0:
            params["start"] = str(page * 20)

        tbs_parts = []
        sort_val = SORT_OPTIONS.get(sort, "")
        if sort_val:
            tbs_parts.append(sort_val)

        cond_val = CONDITION_OPTIONS.get(condition, "")
        if cond_val:
            tbs_parts.append(f"mr:1,condition:{cond_val}")

        if price_min is not None or price_max is not None:
            price_filter = "mr:1,price:1"
            if price_min is not None:
                price_filter += f",ppr_min:{int(price_min)}"
            if price_max is not None:
                price_filter += f",ppr_max:{int(price_max)}"
            tbs_parts.append(price_filter)

        if tbs_parts:
            params["tbs"] = ",".join(tbs_parts)

        query_string = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        return f"{self.BASE_URL}?{query_string}"

    def _extract_price(self, text: str) -> Optional[float]:
        if not text:
            return None
        cleaned = text.strip()
        # Handle European price format: 1.234,56 € or 1234,56€
        cleaned = re.sub(r'[^\d.,]', '', cleaned)
        if not cleaned:
            return None
        # European format: dots as thousands separator, comma as decimal
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
            return float(cleaned)
        except ValueError:
            return None

    def _extract_products_strategy1(self, soup: BeautifulSoup) -> list[Product]:
        """Strategy 1: Use sh-dgr__grid-result containers."""
        products = []
        cards = soup.select("div.sh-dgr__grid-result")
        if not cards:
            cards = soup.select("div.sh-dgr__content")

        for card in cards:
            try:
                product = self._parse_card(card)
                if product:
                    products.append(product)
            except Exception as e:
                logger.debug(f"Strategy 1 card parse error: {e}")
                continue
        return products

    def _extract_products_strategy2(self, soup: BeautifulSoup) -> list[Product]:
        """Strategy 2: Look for product cards by structural patterns."""
        products = []
        # Find all links that go to Google Shopping product pages
        links = soup.select('a[href*="/shopping/product/"]')
        seen = set()
        for link in links:
            try:
                href = link.get("href", "")
                if href in seen:
                    continue
                seen.add(href)

                # Find the parent container
                parent = link.parent
                for _ in range(5):
                    if parent and parent.parent:
                        parent = parent.parent
                    else:
                        break

                product = self._parse_card(parent or link)
                if product:
                    product.link = urljoin("https://www.google.com", href)
                    products.append(product)
            except Exception as e:
                logger.debug(f"Strategy 2 card parse error: {e}")
                continue
        return products

    def _extract_products_strategy3(self, soup: BeautifulSoup) -> list[Product]:
        """Strategy 3: Regex extraction from raw HTML for prices and merchants."""
        products = []
        text = str(soup)

        # Find price patterns like "123,45 €" or "€ 123.45"
        price_pattern = re.compile(
            r'(?:(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))\s*€|€\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})))'
        )
        matches = list(price_pattern.finditer(text))

        for match in matches[:30]:
            try:
                price_str = match.group(1) or match.group(2)
                price = self._extract_price(price_str)
                if price and 0.01 < price < 100000:
                    # Try to find context around this price
                    start = max(0, match.start() - 500)
                    end = min(len(text), match.end() + 500)
                    context = text[start:end]

                    # Extract title from nearby h3/h4 tags
                    title_match = re.search(r'<h[34][^>]*>([^<]+)</h[34]>', context)
                    title = title_match.group(1).strip() if title_match else "Unbekanntes Produkt"

                    products.append(Product(
                        rank=0,
                        title=title,
                        price=price,
                        currency="€",
                        merchant="Unbekannt",
                        link="",
                    ))
            except Exception:
                continue
        return products

    def _parse_card(self, card: Tag) -> Optional[Product]:
        """Parse a product card element into a Product."""
        # Title extraction (multiple strategies)
        title = ""
        for selector in ["h3", "h4", "[role='heading']", "a[aria-label]"]:
            el = card.select_one(selector)
            if el:
                title = el.get_text(strip=True) or el.get("aria-label", "")
                if title:
                    break
        if not title:
            return None

        # Price extraction
        price = None
        price_text = ""
        for selector in [
            "span.a8Pemb", ".OFFNJ", "[data-price]",
            "span.HRLxBb", "span.kHxwFf",
        ]:
            el = card.select_one(selector)
            if el:
                price_text = el.get_text(strip=True)
                price = self._extract_price(price_text)
                if price:
                    break

        if price is None:
            # Fallback: search all spans for price patterns
            for span in card.find_all("span"):
                txt = span.get_text(strip=True)
                if "€" in txt or re.match(r'^\d+[.,]\d{2}$', txt):
                    price = self._extract_price(txt)
                    if price and 0.01 < price < 100000:
                        break
                    price = None

        if price is None:
            return None

        # Merchant extraction
        merchant = ""
        for selector in [".aULzUe", ".IuHnof", "[data-merchant]"]:
            el = card.select_one(selector)
            if el:
                merchant = el.get_text(strip=True)
                if merchant:
                    break
        if not merchant:
            # Look for small text elements that could be merchant names
            divs = card.find_all("div")
            for div in divs:
                txt = div.get_text(strip=True)
                if txt and len(txt) < 50 and "€" not in txt and txt != title:
                    if not any(c.isdigit() for c in txt[:3]):
                        merchant = txt
                        break
        if not merchant:
            merchant = "Unbekannter Händler"

        # Link extraction
        link = ""
        link_el = card.select_one("a[href]")
        if link_el:
            href = link_el.get("href", "")
            if href.startswith("/"):
                link = f"https://www.google.com{href}"
            elif href.startswith("http"):
                link = href

        # Rating extraction
        rating = 0.0
        for selector in [".Rsc7Yb", "[aria-label*='Stern']", "[aria-label*='star']"]:
            el = card.select_one(selector)
            if el:
                txt = el.get_text(strip=True).replace(",", ".")
                try:
                    rating = float(re.search(r'[\d.]+', txt).group())
                except (ValueError, AttributeError):
                    pass
                break

        # Reviews count
        reviews = 0
        review_el = card.select_one(".NzUzee div, [aria-label*='Bewertung']")
        if review_el:
            txt = review_el.get_text(strip=True)
            nums = re.findall(r'[\d.]+', txt.replace('.', ''))
            if nums:
                try:
                    reviews = int(nums[0])
                except ValueError:
                    pass

        # Delivery info
        delivery = ""
        for selector in [".vEjMR", "[data-delivery]"]:
            el = card.select_one(selector)
            if el:
                delivery = el.get_text(strip=True)
                break

        # Image URL
        image_url = ""
        img = card.select_one("img[src]")
        if img:
            image_url = img.get("src", "")

        return Product(
            rank=0,
            title=title,
            price=price,
            currency="€",
            merchant=merchant,
            link=link,
            image_url=image_url,
            rating=rating,
            reviews=reviews,
            delivery_info=delivery,
        )

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
        Search for products and return up to max_results sorted by price.

        Args:
            query: Product search term
            country: 2-letter country code (de, at, fr, etc.)
            sort: Sort order key
            condition: Product condition filter
            price_min: Minimum price filter
            price_max: Maximum price filter
            max_results: Maximum number of results to return
            progress_callback: Optional callback(message, percent) for progress updates
        """
        all_products = []

        if progress_callback:
            progress_callback("Suche wird gestartet...", 5)

        # Search across multiple EU countries to get diverse results
        countries_to_search = [country]
        # Add more EU countries for broader coverage
        for code in EU_COUNTRIES:
            if code != country and len(countries_to_search) < 3:
                countries_to_search.append(code)

        total_steps = len(countries_to_search) * 2  # pages per country
        current_step = 0

        for c in countries_to_search:
            for page in range(2):  # 2 pages per country
                current_step += 1
                pct = int(10 + (current_step / total_steps) * 70)

                if progress_callback:
                    country_name = EU_COUNTRIES.get(c, c.upper())
                    progress_callback(
                        f"Durchsuche {country_name} (Seite {page + 1})...",
                        pct,
                    )

                try:
                    self._update_headers()
                    url = self._build_url(
                        query=query,
                        country=c,
                        sort=sort,
                        condition=condition,
                        price_min=price_min,
                        price_max=price_max,
                        page=page,
                    )

                    logger.debug(f"Fetching: {url}")
                    response = self.session.get(url, timeout=15)

                    if response.status_code == 429:
                        logger.warning(f"Rate limited on {c} page {page}")
                        time.sleep(random.uniform(3, 6))
                        continue

                    if response.status_code != 200:
                        logger.warning(f"HTTP {response.status_code} for {c}")
                        continue

                    soup = BeautifulSoup(response.text, "lxml")

                    # Try multiple extraction strategies
                    products = self._extract_products_strategy1(soup)
                    if not products:
                        products = self._extract_products_strategy2(soup)
                    if not products:
                        products = self._extract_products_strategy3(soup)

                    logger.info(f"Found {len(products)} products from {c} page {page}")
                    all_products.extend(products)

                    # Polite delay between requests
                    time.sleep(random.uniform(1.0, 2.5))

                except requests.RequestException as e:
                    logger.error(f"Request error for {c}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Parse error for {c}: {e}")
                    continue

        if progress_callback:
            progress_callback("Ergebnisse werden verarbeitet...", 85)

        # Deduplicate by title + merchant
        seen = set()
        unique = []
        for p in all_products:
            key = (p.title.lower().strip(), p.merchant.lower().strip())
            if key not in seen:
                seen.add(key)
                unique.append(p)

        # Apply price filters (backup in case URL params didn't work)
        if price_min is not None:
            unique = [p for p in unique if p.price >= price_min]
        if price_max is not None:
            unique = [p for p in unique if p.price <= price_max]

        # Sort by price (ascending by default)
        if sort == "preis_absteigend":
            unique.sort(key=lambda p: p.price, reverse=True)
        elif sort == "bewertung":
            unique.sort(key=lambda p: p.rating, reverse=True)
        else:
            unique.sort(key=lambda p: p.price)

        # Assign ranks and limit results
        results = unique[:max_results]
        for i, p in enumerate(results, 1):
            p.rank = i

        if progress_callback:
            progress_callback(f"{len(results)} Ergebnisse gefunden!", 100)

        return results
