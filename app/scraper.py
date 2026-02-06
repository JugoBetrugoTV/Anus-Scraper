"""
Backward-compatibility wrapper around the new provider-based PriceEngine.

Previous code imported ``PriceScraper`` and constants from this module.
This shim delegates everything to ``app.price_engine.PriceEngine`` and
re-exports the shared constants so existing call-sites keep working.
"""

from app.price_engine import PriceEngine
from app.providers import EU_COUNTRIES, SORT_OPTIONS, CONDITION_OPTIONS


class PriceScraper:
    """Thin wrapper — delegates to PriceEngine for backward compatibility."""

    def __init__(self):
        self._engine = PriceEngine()

    def search(self, **kwargs):
        return self._engine.search(**kwargs)
