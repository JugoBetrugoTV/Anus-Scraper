"""
Shop provider framework for Anus Scraper.

Each provider implements the ShopProvider base class to fetch product data
from a specific source (Geizhals, Google Shopping, Amazon, etc.).

Architecture:
    ShopProvider (ABC)           – search interface & shared utilities
    ├── GeizhalsProvider         – geizhals.de price aggregator
    ├── GoogleShoppingProvider   – Google Shopping fallback
    ├── IdealoProvider            – idealo.de price comparison
    ├── NotebooksbilligerProvider – notebooksbilliger.de
    ├── MindfactoryProvider      – mindfactory.de PC hardware
    ├── AmazonProvider           – placeholder
    ├── MediaMarktProvider       – placeholder
    └── AlternateProvider        – placeholder
"""

import re
import os
import time
import random
import logging
from abc import ABC, abstractmethod
from typing import Optional
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

# ---------------------------------------------------------------------------
#  Shared constants
# ---------------------------------------------------------------------------

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

DEBUG_DIR = Path(os.path.expanduser("~")) / "AnusScraper_debug"

# ---------------------------------------------------------------------------
#  Unified HTTP error tuple (covers requests + curl_cffi)
# ---------------------------------------------------------------------------

_HTTP_ERRORS = [requests.RequestException, OSError]
if HAS_CURL_CFFI:
    try:
        _HTTP_ERRORS.append(curl_requests.errors.RequestsError)
    except (AttributeError, TypeError):
        pass
HTTP_ERRORS = tuple(_HTTP_ERRORS)

# ---------------------------------------------------------------------------
#  Utility helpers
# ---------------------------------------------------------------------------


def save_debug_html(filename: str, content: str, url: str):
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


def create_session():
    """Create an HTTP session with browser-grade TLS fingerprinting.

    Returns (session, is_curl_cffi) tuple.
    """
    if HAS_CURL_CFFI:
        try:
            session = curl_requests.Session(impersonate="chrome120")
            session.headers.update({
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            })
            logger.info("Created curl_cffi session with Chrome TLS impersonation")
            return session, True
        except Exception as e:
            logger.warning(f"curl_cffi session failed ({e}), falling back to requests")

    session = requests.Session()
    ua = random.choice(USER_AGENTS)
    session.headers.update({
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                  "image/avif,image/webp,image/apng,*/*;q=0.8",
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
    if not HAS_CURL_CFFI:
        logger.info("curl_cffi not available – using requests")
    return session, False


# ---------------------------------------------------------------------------
#  Base class
# ---------------------------------------------------------------------------


class ShopProvider(ABC):
    """Abstract base class for all shop data providers."""

    name: str = "Unknown"

    def __init__(self):
        self.session, self._using_curl_cffi = create_session()
        self.enabled = True

    @abstractmethod
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
        """Search for products.  Returns a list of Product objects."""
        ...

    # ------ shared utilities available to all providers ------

    def extract_price(self, text: str) -> Optional[float]:
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
