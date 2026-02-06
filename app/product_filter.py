"""
Strict product validation and model identity parsing for Anus Scraper.

Two responsibilities:
1. Filter: reject products that don't match the search query (wrong GPU, accessories)
2. Identity: parse product titles into structured model identities so different
   models are shown separately and same models are grouped correctly.

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
    "aufkleber", "sticker", "dummy", "attrappe",
    "netzteil", "power supply", " psu ",
    "mainboard", "motherboard",
    "monitor", "bildschirm", "display",
    "gehäuse", " case ", "tower",
    "mousepad", "mauspad", "t-shirt", "tasse", "poster", "figur",
    "schlüsselanhänger", "keychain",
    "laptop", "notebook",
]

GPU_EXCLUDE_SAFE_WORDS = [
    "powercolor", "power color",
]

# ---------------------------------------------------------------------------
#  Variant patterns — same GPU chip, different cooler/design
# ---------------------------------------------------------------------------

VARIANT_PATTERNS: dict[str, list[str]] = {
    "OC": [r"\boc\b", r"\boverclocked\b", r"\bo/c\b"],
    "Liquid": [r"\bliquid\b", r"\baio\b", r"\bhybrid\b",
               r"\bwaterforce\b", r"\bwater\s*cool", r"\blc\b"],
    "White": [r"\bwhite\b", r"\bweiß\b"],
    "Mini/ITX": [r"\bmini\b", r"\bitx\b", r"\bcompact\b", r"\bslim\b"],
}

# ---------------------------------------------------------------------------
#  Known board partners (GPU vendors)
# ---------------------------------------------------------------------------

KNOWN_VENDORS: dict[str, str] = {
    "asus": "ASUS",
    "msi": "MSI",
    "gigabyte": "Gigabyte",
    "zotac": "ZOTAC",
    "evga": "EVGA",
    "palit": "Palit",
    "gainward": "Gainward",
    "inno3d": "Inno3D",
    "pny": "PNY",
    "sapphire": "Sapphire",
    "powercolor": "PowerColor",
    "xfx": "XFX",
    "asrock": "ASRock",
    "biostar": "Biostar",
    "galax": "GALAX",
    "kfa2": "KFA2",
    "manli": "Manli",
    "nvidia": "NVIDIA",
    "amd": "AMD",
    "intel": "Intel",
}

# ---------------------------------------------------------------------------
#  Known model lines — sorted longest-first for greedy matching
# ---------------------------------------------------------------------------

_MODEL_LINES_RAW: dict[str, str] = {
    # ASUS
    "rog strix oc": "ROG STRIX OC",
    "rog strix lc": "ROG STRIX LC",
    "rog strix": "ROG STRIX",
    "tuf gaming oc": "TUF GAMING OC",
    "tuf gaming": "TUF GAMING",
    "tuf": "TUF",
    "dual oc": "DUAL OC",
    "dual": "DUAL",
    "proart": "ProArt",
    "prime oc": "PRIME OC",
    "prime": "PRIME",
    "megalodon": "MEGALODON",
    # MSI
    "suprim x": "SUPRIM X",
    "suprim liquid": "SUPRIM LIQUID",
    "suprim": "SUPRIM",
    "gaming x trio": "GAMING X TRIO",
    "gaming x slim": "GAMING X SLIM",
    "gaming x": "GAMING X",
    "gaming trio": "GAMING TRIO",
    "ventus 3x oc": "VENTUS 3X OC",
    "ventus 3x": "VENTUS 3X",
    "ventus 2x oc": "VENTUS 2X OC",
    "ventus 2x": "VENTUS 2X",
    "ventus": "VENTUS",
    "mech 2x oc": "MECH 2X OC",
    "mech 2x": "MECH 2X",
    "mech": "MECH",
    "aero": "AERO",
    # Gigabyte
    "aorus xtreme waterforce": "AORUS XTREME WATERFORCE",
    "aorus xtreme": "AORUS XTREME",
    "aorus master": "AORUS MASTER",
    "aorus elite": "AORUS ELITE",
    "aorus": "AORUS",
    "gaming oc": "GAMING OC",
    "eagle oc": "EAGLE OC",
    "eagle": "EAGLE",
    "windforce oc": "WINDFORCE OC",
    "windforce": "WINDFORCE",
    # ZOTAC
    "trinity oc": "TRINITY OC",
    "trinity": "TRINITY",
    "amp extreme airo": "AMP EXTREME AIRO",
    "amp extreme": "AMP EXTREME",
    "amp": "AMP",
    "solid": "SOLID",
    # EVGA
    "ftw3 ultra": "FTW3 ULTRA",
    "ftw3": "FTW3",
    "xc3 ultra": "XC3 ULTRA",
    "xc3": "XC3",
    "xc gaming": "XC GAMING",
    "xc": "XC",
    # Sapphire
    "nitro+ oc": "NITRO+ OC",
    "nitro+": "NITRO+",
    "nitro": "NITRO",
    "pulse oc": "PULSE OC",
    "pulse": "PULSE",
    "toxic": "TOXIC",
    "vapor-x": "VAPOR-X",
    # PowerColor
    "red devil oc": "RED DEVIL OC",
    "red devil": "RED DEVIL",
    "hellhound oc": "HELLHOUND OC",
    "hellhound": "HELLHOUND",
    "fighter oc": "FIGHTER OC",
    "fighter": "FIGHTER",
    # XFX
    "speedster merc 310": "SPEEDSTER MERC 310",
    "speedster merc": "SPEEDSTER MERC",
    "speedster swft 210": "SPEEDSTER SWFT 210",
    "speedster swft": "SPEEDSTER SWFT",
    "speedster qick": "SPEEDSTER QICK",
    "speedster": "SPEEDSTER",
    # PNY
    "xlr8 uprising": "XLR8 UPRISING",
    "xlr8 oc": "XLR8 OC",
    "xlr8": "XLR8",
    "uprising": "UPRISING",
    "verto oc": "VERTO OC",
    "verto": "VERTO",
    # Palit
    "gamerock oc": "GAMEROCK OC",
    "gamerock": "GAMEROCK",
    "jetstream oc": "JETSTREAM OC",
    "jetstream": "JETSTREAM",
    "gamepro oc": "GAMEPRO OC",
    "gamepro": "GAMEPRO",
    # Gainward
    "phantom gs oc": "PHANTOM GS OC",
    "phantom gs": "PHANTOM GS",
    "phantom": "PHANTOM",
    "phoenix gs oc": "PHOENIX GS OC",
    "phoenix gs": "PHOENIX GS",
    "phoenix": "PHOENIX",
    # ASRock
    "phantom gaming oc": "PHANTOM GAMING OC",
    "phantom gaming": "PHANTOM GAMING",
    "challenger oc": "CHALLENGER OC",
    "challenger": "CHALLENGER",
    "steel legend oc": "STEEL LEGEND OC",
    "steel legend": "STEEL LEGEND",
    # Inno3D
    "ichill x3 oc": "ICHILL X3 OC",
    "ichill x3": "ICHILL X3",
    "ichill x4": "ICHILL X4",
    "ichill frostbite": "ICHILL FROSTBITE",
    "twin x2 oc": "TWIN X2 OC",
    "twin x2": "TWIN X2",
    # KFA2
    "sg oc": "SG OC",
    "sg": "SG",
    "ex gamer oc": "EX GAMER OC",
    "ex gamer": "EX GAMER",
    # NVIDIA / AMD reference
    "founders edition": "FOUNDERS EDITION",
    "reference": "REFERENCE",
}

# Pre-sort by key length descending → greedy matching
KNOWN_MODEL_LINES = dict(
    sorted(_MODEL_LINES_RAW.items(), key=lambda kv: len(kv[0]), reverse=True)
)


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
#  ModelIdentity — parsed from product title
# ---------------------------------------------------------------------------

@dataclass
class ModelIdentity:
    """Structured identity of a GPU product model."""
    vendor: str       # "ASUS", "MSI", "Gigabyte", ...
    model_line: str   # "ROG STRIX", "SUPRIM X", "AORUS MASTER", ...
    chip: str         # "RTX 4090", "RX 7900 XTX"
    variant: str      # "OC", "Liquid", "White", "Standard"

    @property
    def model_id(self) -> str:
        """Deterministic unique key for this model.

        Example: ``ASUS-ROG_STRIX-RTX_4090-OC``

        Does NOT include merchant or price — pure product identity.
        """
        parts = [
            self.vendor.upper().replace(" ", "_"),
            self.model_line.upper().replace(" ", "_").replace("+", "PLUS"),
            self.chip.upper().replace(" ", "_"),
            self.variant.upper().replace("/", "_"),
        ]
        return "-".join(p for p in parts if p)

    @property
    def display_name(self) -> str:
        """Human-readable model name, e.g. 'ASUS ROG STRIX RTX 4090 OC'."""
        parts = [self.vendor, self.model_line, self.chip]
        if self.variant and self.variant != "Standard":
            parts.append(self.variant)
        return " ".join(p for p in parts if p)


# ---------------------------------------------------------------------------
#  Query parsing
# ---------------------------------------------------------------------------

def parse_gpu_query(query: str) -> Optional[GPUQuery]:
    """
    Parse a search query to extract GPU identifiers.

    Returns GPUQuery if the query contains a recognizable GPU model,
    None otherwise (in which case no GPU filtering is applied).
    """
    q_lower = query.lower().strip()

    pattern = re.compile(
        r"(?:nvidia\s+|amd\s+|intel\s+)?"
        r"(?:geforce\s+|radeon\s+)?"
        r"(rtx|gtx|rx|arc)\s+"
        r"(a?\d{3,5})"
        r"(?:\s+(ti|super|xtx|xt))?",
        re.IGNORECASE,
    )

    m = pattern.search(q_lower)
    if not m:
        return None

    series = m.group(1).upper()
    if series == "ARC":
        series = "Arc"
    model = m.group(2).upper()
    suffix = (m.group(3) or "").upper()
    if suffix == "TI":
        suffix = "Ti"

    manufacturer = GPU_SERIES.get(series.lower(), "")
    if not manufacturer:
        return None

    result = GPUQuery(
        manufacturer=manufacturer, series=series, model=model,
        suffix=suffix, raw_query=query,
    )
    logger.info(f"GPU query parsed: '{query}' -> {result.full_model} ({manufacturer})")
    return result


# ---------------------------------------------------------------------------
#  GPU title parsing — extract structured model identity
# ---------------------------------------------------------------------------

def _extract_chip(title_lower: str) -> str:
    """Extract the GPU chip string from a title, e.g. 'RTX 4090 Ti'."""
    m = re.search(
        r"(rtx|gtx|rx|arc)\s+(a?\d{3,5})(?:\s+(ti|super|xtx|xt))?",
        title_lower,
    )
    if not m:
        return ""
    series = m.group(1).upper()
    if series == "ARC":
        series = "Arc"
    model = m.group(2).upper()
    suffix = (m.group(3) or "").capitalize()
    if suffix.lower() == "xtx":
        suffix = "XTX"
    elif suffix.lower() == "xt":
        suffix = "XT"
    elif suffix.lower() == "super":
        suffix = "SUPER"
    parts = [series, model]
    if suffix:
        parts.append(suffix)
    return " ".join(parts)


def _extract_vendor(title_lower: str) -> str:
    """Extract the board partner / GPU vendor from a title."""
    # Check each known vendor at word boundary
    for key, display in KNOWN_VENDORS.items():
        pattern = r"(?<![a-z])" + re.escape(key) + r"(?![a-z])"
        if re.search(pattern, title_lower):
            return display
    return ""


def _extract_model_line(title_lower: str) -> str:
    """Extract the model line from a title using greedy longest-match."""
    for key, display in KNOWN_MODEL_LINES.items():
        if key in title_lower:
            return display
    return ""


def _extract_variant(title_lower: str) -> str:
    """Extract variant tag (OC, Liquid, White, Mini/ITX, or Standard)."""
    for tag, patterns in VARIANT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, title_lower):
                return tag
    return "Standard"


def parse_gpu_title(title: str) -> ModelIdentity:
    """
    Parse a GPU product title into structured model identity.

    Deterministic, no fuzzy matching. Uses known vendor and model line
    databases for exact extraction.

    Examples::

        "ASUS ROG Strix GeForce RTX 4090 OC 24GB GDDR6X"
        → ModelIdentity(ASUS, ROG STRIX, RTX 4090, OC)

        "MSI GeForce RTX 4090 SUPRIM X 24GB GDDR6X"
        → ModelIdentity(MSI, SUPRIM X, RTX 4090, Standard)

        "Gigabyte GeForce RTX 4090 GAMING OC 24GB"
        → ModelIdentity(Gigabyte, GAMING OC, RTX 4090, OC)

        "ZOTAC GAMING GeForce RTX 4090 Trinity OC 24GB"
        → ModelIdentity(ZOTAC, TRINITY OC, RTX 4090, OC)
    """
    t = title.lower()

    chip = _extract_chip(t)
    vendor = _extract_vendor(t)
    model_line = _extract_model_line(t)
    variant = _extract_variant(t)

    # If model line already contains OC suffix, ensure variant reflects it
    if model_line.endswith(" OC") and variant == "Standard":
        variant = "OC"

    return ModelIdentity(
        vendor=vendor or "Unbekannt",
        model_line=model_line,
        chip=chip,
        variant=variant,
    )


def compute_model_id(title: str) -> str:
    """
    Compute a unique model ID from a product title.

    For GPU titles: returns structured key like ``ASUS-ROG_STRIX-RTX_4090-OC``
    For non-GPU titles: returns a normalized version of the title.
    """
    identity = parse_gpu_title(title)
    if identity.chip:
        mid = identity.model_id
        logger.debug(f"Model ID: '{title[:60]}' -> {mid}")
        return mid

    # Fallback for non-GPU: normalize the title
    return re.sub(r"\s+", "_", title.strip().lower()[:80])


# ---------------------------------------------------------------------------
#  Title matching — deterministic, no fuzzy
# ---------------------------------------------------------------------------

def _is_gpu_accessory(title_lower: str) -> bool:
    """Check if a product title is an accessory / wrong category."""
    for safe in GPU_EXCLUDE_SAFE_WORDS:
        if safe in title_lower:
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
    3. If suffix specified: must appear after model
    4. If NO suffix: must NOT have Ti/SUPER/XT/XTX after model
    5. Must not be an accessory or wrong product category
    """
    t = title.lower()
    series_lower = gpu.series.lower()
    model_lower = gpu.model.lower()

    if series_lower not in t:
        return False

    model_pat = r"(?<![a-z\d])" + re.escape(model_lower) + r"(?!\d)"
    model_match = re.search(model_pat, t)
    if not model_match:
        return False

    after_model = t[model_match.end():]
    after_stripped = re.sub(r"^[\s\-/]+", "", after_model)

    if gpu.suffix:
        suffix_lower = gpu.suffix.lower()
        first_token = re.match(r"([a-z]+)", after_stripped)
        if not first_token or first_token.group(1) != suffix_lower:
            nearby = after_model[:30].lower()
            if not re.search(
                r"(?<![a-z])" + re.escape(suffix_lower) + r"(?![a-z])",
                nearby,
            ):
                return False
    else:
        first_token = re.match(r"([a-z]+)", after_stripped)
        if first_token and first_token.group(1) in GPU_MODEL_SUFFIXES:
            return False

    if _is_gpu_accessory(t):
        return False

    return True


# ---------------------------------------------------------------------------
#  Variant detection (kept for backward compat)
# ---------------------------------------------------------------------------

def detect_gpu_variants(title: str) -> list[str]:
    """Extract variant tags from a GPU product title."""
    t = title.lower()
    variants: list[str] = []
    for tag, patterns in VARIANT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, t):
                variants.append(tag)
                break
    return variants


# ---------------------------------------------------------------------------
#  Public API — filter function
# ---------------------------------------------------------------------------

def filter_products(products: list[Product], query: str) -> list[Product]:
    """
    Apply strict product validation based on the search query.

    For GPU queries: rejects products that don't match series+model+suffix.
    For non-GPU queries: returns products unchanged.
    """
    gpu = parse_gpu_query(query)
    if gpu is None:
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
        f"GPU filter: {len(products)} input -> {len(filtered)} passed "
        f"(query: {gpu.full_model})"
    )
    return filtered
