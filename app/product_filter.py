"""
Strict product validation for PreisHai.

Parses search queries to detect hardware product types (GPUs, CPUs),
then filters results to exclude wrong models, generations, and accessories.

Rules are deterministic — no fuzzy matching.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

from app.models import Product

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  GPU model suffixes — these define a DIFFERENT SKU (not a variant)
# ---------------------------------------------------------------------------

GPU_MODEL_SUFFIXES = {"ti", "super", "xt", "xtx"}

# ---------------------------------------------------------------------------
#  Series → manufacturer mapping
# ---------------------------------------------------------------------------

GPU_SERIES = {
    "rtx": "nvidia",
    "gtx": "nvidia",
    "rx": "amd",
    "arc": "intel",
}

# ---------------------------------------------------------------------------
#  Accessory / wrong-category keywords — always excluded for GPU searches
# ---------------------------------------------------------------------------

GPU_EXCLUDE_KEYWORDS = [
    "kabel", "cable", "adapter", "halterung", "bracket", "backplate",
    "riser", "verlängerung", "extension", "hülle",
    "aufkleber", "sticker", "dummy", "attrappe", "modell",
    "netzteil", "power supply", " psu ",
    "mainboard", "motherboard",
    "monitor", "bildschirm", "display",
    "gehäuse", " case ", "tower",
    "mousepad", "mauspad", "t-shirt", "tasse", "poster", "figur",
    "schlüsselanhänger", "keychain",
    "laptop", "notebook",
]

# Words that protect against false exclusion
# e.g. "PowerColor" contains "power" but is a GPU brand
GPU_EXCLUDE_SAFE_WORDS = [
    "powercolor", "power color",
]

# ---------------------------------------------------------------------------
#  Variant tags — same GPU chip, different cooler/design
# ---------------------------------------------------------------------------

VARIANT_PATTERNS: dict[str, list[str]] = {
    "OC": [r"\boc\b", r"\boverclocked\b", r"\bo/c\b"],
    "Liquid": [r"\bliquid\b", r"\baio\b", r"\bhybrid\b",
               r"\bwaterforce\b", r"\bwater\s*cool", r"\blc\b"],
    "White": [r"\bwhite\b", r"\bweiß\b"],
    "Mini/ITX": [r"\bmini\b", r"\bitx\b", r"\bcompact\b", r"\bslim\b"],
}


# ---------------------------------------------------------------------------
#  GPUQuery — parsed search query
# ---------------------------------------------------------------------------

@dataclass
class GPUQuery:
    """Parsed GPU search query."""
    manufacturer: str   # "nvidia", "amd", "intel"
    series: str         # "RTX", "GTX", "RX", "Arc"
    model: str          # "4090", "7900", "1080", "A770"
    suffix: str         # "Ti", "SUPER", "XT", "XTX", or ""
    raw_query: str      # Original query string

    @property
    def full_model(self) -> str:
        """e.g. 'RTX 4090 Ti' or 'RX 7900 XTX'."""
        parts = [self.series, self.model]
        if self.suffix:
            parts.append(self.suffix)
        return " ".join(parts)


# ---------------------------------------------------------------------------
#  Query parsing
# ---------------------------------------------------------------------------

def parse_gpu_query(query: str) -> Optional[GPUQuery]:
    """
    Parse a search query to extract GPU identifiers.

    Returns GPUQuery if the query contains a recognizable GPU model,
    None otherwise (in which case no GPU filtering is applied).

    Examples::

        "RTX 4090"           → GPUQuery(nvidia, RTX, 4090, "")
        "RTX 4090 Ti"        → GPUQuery(nvidia, RTX, 4090, Ti)
        "GeForce RTX 4090"   → GPUQuery(nvidia, RTX, 4090, "")
        "RX 7900 XTX"        → GPUQuery(amd, RX, 7900, XTX)
        "GTX 1080 Ti"        → GPUQuery(nvidia, GTX, 1080, Ti)
        "RTX 4090 SUPER"     → GPUQuery(nvidia, RTX, 4090, SUPER)
        "Arc A770"            → GPUQuery(intel, Arc, A770, "")
        "Samsung S24"         → None
    """
    q_lower = query.lower().strip()

    # Combined pattern:
    #   [nvidia/amd/intel] [geforce/radeon] <series> <model> [suffix]
    pattern = re.compile(
        r"(?:nvidia\s+|amd\s+|intel\s+)?"          # optional manufacturer
        r"(?:geforce\s+|radeon\s+)?"                # optional brand prefix
        r"(rtx|gtx|rx|arc)\s+"                      # series (required)
        r"(a?\d{3,5})"                              # model (3-5 digits, opt. 'A' for Arc)
        r"(?:\s+(ti|super|xtx|xt))?",               # optional model suffix
        re.IGNORECASE,
    )

    m = pattern.search(q_lower)
    if not m:
        return None

    series_raw = m.group(1)
    model_raw = m.group(2)
    suffix_raw = m.group(3) or ""

    # Normalize casing
    series = series_raw.upper()
    if series == "ARC":
        series = "Arc"

    model = model_raw.upper()

    suffix = suffix_raw.upper()
    if suffix == "TI":
        suffix = "Ti"

    manufacturer = GPU_SERIES.get(series.lower(), "")
    if not manufacturer:
        return None

    result = GPUQuery(
        manufacturer=manufacturer,
        series=series,
        model=model,
        suffix=suffix,
        raw_query=query,
    )

    logger.info(
        f"GPU query parsed: '{query}' → {result.full_model} ({manufacturer})"
    )
    return result


# ---------------------------------------------------------------------------
#  Title matching — deterministic, no fuzzy
# ---------------------------------------------------------------------------

def _is_gpu_accessory(title_lower: str) -> bool:
    """Check if a product title is an accessory / wrong category."""
    # Check safe words first — brands that contain exclude substrings
    for safe in GPU_EXCLUDE_SAFE_WORDS:
        if safe in title_lower:
            # Replace the safe word so it won't trigger exclusion
            title_lower = title_lower.replace(safe, "")

    for kw in GPU_EXCLUDE_KEYWORDS:
        if kw in title_lower:
            return True
    return False


def _title_matches_gpu(title: str, gpu: GPUQuery) -> bool:
    """
    Deterministic check: does this product title match the GPU query?

    Hard rules:
    1. Title MUST contain the GPU series (RTX / GTX / RX / Arc)
    2. Title MUST contain the exact model number at a word boundary
    3. If suffix specified (Ti/SUPER/XT/XTX): must appear after model
    4. If NO suffix specified: must NOT have Ti/SUPER/XT/XTX after model
    5. Must not be an accessory or wrong product category
    """
    t = title.lower()
    series_lower = gpu.series.lower()
    model_lower = gpu.model.lower()

    # ── Rule 1: series must be present ──
    if series_lower not in t:
        return False

    # ── Rule 2: exact model number at word boundary ──
    # (?<![a-z\d]) prevents "14090" or "x4090" matching "4090"
    # (?![a-z\d])  prevents "40900" or "4090x" matching "4090"
    model_pat = r"(?<![a-z\d])" + re.escape(model_lower) + r"(?!\d)"
    model_match = re.search(model_pat, t)
    if not model_match:
        return False

    # ── Rule 3 & 4: suffix handling ──
    # Get text after the model number
    after_model = t[model_match.end():]
    # Strip leading whitespace, hyphens, slashes
    after_stripped = re.sub(r"^[\s\-/]+", "", after_model)

    if gpu.suffix:
        # Suffix is required — must appear right after the model number
        suffix_lower = gpu.suffix.lower()
        # Check first meaningful word after model
        first_token = re.match(r"([a-z]+)", after_stripped)
        if not first_token or first_token.group(1) != suffix_lower:
            # Also accept if suffix appears slightly later (e.g. "4090 16GB Ti")
            # but within a reasonable range
            nearby = after_model[:30].lower()
            if not re.search(
                r"(?<![a-z])" + re.escape(suffix_lower) + r"(?![a-z])",
                nearby,
            ):
                return False
    else:
        # No suffix in query — the model must NOT be a suffixed variant
        first_token = re.match(r"([a-z]+)", after_stripped)
        if first_token and first_token.group(1) in GPU_MODEL_SUFFIXES:
            return False

    # ── Rule 5: exclude accessories ──
    if _is_gpu_accessory(t):
        return False

    return True


# ---------------------------------------------------------------------------
#  Variant detection
# ---------------------------------------------------------------------------

def detect_gpu_variants(title: str) -> list[str]:
    """
    Extract variant tags from a GPU product title.

    Returns a list like ["OC", "White"] or ["Liquid"] or [].
    These help distinguish cards with the same GPU chip but different designs.
    """
    t = title.lower()
    variants: list[str] = []

    for tag, patterns in VARIANT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, t):
                variants.append(tag)
                break

    return variants


# ---------------------------------------------------------------------------
#  Public API — main filter function
# ---------------------------------------------------------------------------

def filter_products(products: list[Product], query: str) -> list[Product]:
    """
    Apply strict product validation based on the search query.

    For GPU queries:
        Parses query → extracts series + model + suffix →
        rejects every product whose title does not match exactly.

    For non-GPU queries:
        Returns products unchanged (no filtering applied).

    This filter is deterministic and exact — no fuzzy matching.
    """
    gpu = parse_gpu_query(query)
    if gpu is None:
        # Not a recognizable GPU query — pass through unchanged
        return products

    filtered: list[Product] = []
    for p in products:
        if _title_matches_gpu(p.title, gpu):
            filtered.append(p)
        else:
            logger.debug(
                f"REJECTED: '{p.title[:80]}' — "
                f"does not match {gpu.full_model}"
            )

    logger.info(
        f"GPU filter: {len(products)} input → {len(filtered)} passed "
        f"(query: {gpu.full_model})"
    )
    return filtered
