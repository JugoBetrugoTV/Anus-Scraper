"""
PriceEngine — aggregates results from all registered shop providers.

Handles provider orchestration, deduplication, filtering, and sorting.
"""

import logging
from typing import Optional

from app.models import Product
from app.providers import ShopProvider
from app.providers.geizhals import GeizhalsProvider
from app.providers.google_shopping import GoogleShoppingProvider
from app.providers.amazon import AmazonProvider
from app.providers.mediamarkt import MediaMarktProvider
from app.providers.alternate import AlternateProvider
from app.providers.idealo import IdealoProvider
from app.providers.notebooksbilliger import NotebooksbilligerProvider
from app.providers.mindfactory import MindfactoryProvider

logger = logging.getLogger(__name__)


def _get_all_providers() -> list[ShopProvider]:
    """Instantiate all known providers."""
    return [
        GeizhalsProvider(),
        GoogleShoppingProvider(),
        IdealoProvider(),
        NotebooksbilligerProvider(),
        MindfactoryProvider(),
        AmazonProvider(),
        MediaMarktProvider(),
        AlternateProvider(),
    ]


class PriceEngine:
    """Orchestrates searches across multiple shop providers."""

    def __init__(self):
        self.providers: list[ShopProvider] = _get_all_providers()

    @property
    def enabled_providers(self) -> list[ShopProvider]:
        return [p for p in self.providers if p.enabled]

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
        Search all enabled providers, aggregate, deduplicate, sort.
        """
        enabled = self.enabled_providers
        if not enabled:
            logger.warning("No providers enabled")
            return []

        all_products: list[Product] = []

        # Distribute progress across providers
        n = len(enabled)
        per_provider = 85 // n  # reserve 85-100% for post-processing

        for idx, provider in enumerate(enabled):
            pct_start = idx * per_provider
            pct_end = (idx + 1) * per_provider

            logger.info(
                f"Querying provider '{provider.name}' "
                f"(progress {pct_start}-{pct_end}%)"
            )

            # Create a wrapper callback that maps provider progress → global
            def _wrap_cb(msg, pct, _start=pct_start, _span=per_provider):
                if progress_callback:
                    global_pct = _start + int(pct / 100 * _span)
                    progress_callback(msg, min(global_pct, 85))

            try:
                results = provider.search(
                    query=query,
                    country=country,
                    sort=sort,
                    condition=condition,
                    price_min=price_min,
                    price_max=price_max,
                    progress_callback=_wrap_cb,
                )
                logger.info(
                    f"Provider '{provider.name}' returned "
                    f"{len(results)} results"
                )
                all_products.extend(results)
            except Exception as e:
                logger.error(
                    f"Provider '{provider.name}' failed: {e}", exc_info=True,
                )

            # Stop early if we have plenty of results
            if len(all_products) >= max_results * 2:
                break

        # --- Post-processing ---
        if progress_callback:
            progress_callback("Ergebnisse werden sortiert...", 90)

        # Deduplicate by (merchant, title-prefix, price)
        seen: set[tuple[str, str, float]] = set()
        unique: list[Product] = []
        for p in all_products:
            key = (
                p.merchant.lower().strip(),
                p.title.lower().strip()[:80],
                round(p.price, 2),
            )
            if key not in seen:
                seen.add(key)
                unique.append(p)

        # Price filters
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

        # Assign ranks & cap
        results = unique[:max_results]
        for i, p in enumerate(results, 1):
            p.rank = i

        if progress_callback:
            if results:
                progress_callback(f"{len(results)} Angebote gefunden!", 100)
            else:
                progress_callback("Keine Ergebnisse gefunden.", 100)

        return results
