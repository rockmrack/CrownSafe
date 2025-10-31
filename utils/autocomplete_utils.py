"""Autocomplete utility functions for query normalization and text processing."""

import re
import unicodedata

# Brand aliases for canonicalization
BRAND_ALIASES = {
    "p&g": "Procter & Gamble",
    "p and g": "Procter & Gamble",
    "procter & gamble": "Procter & Gamble",
    "procter and gamble": "Procter & Gamble",
    "pg": "Procter & Gamble",
    "gerber": "Gerber",
    "nestle": "Nestlé",
    "johnson & johnson": "Johnson & Johnson",
    "j&j": "Johnson & Johnson",
    "j and j": "Johnson & Johnson",
    "unilever": "Unilever",
    "pampers": "Pampers",
    "huggies": "Huggies",
    "similac": "Similac",
    "enfamil": "Enfamil",
}

# Domain categories for baby products
BABY_DOMAINS = {
    "baby",
    "infant",
    "toddler",
    "child",
    "children",
    "formula",
    "food",
    "bottle",
    "pacifier",
    "diaper",
    "stroller",
    "car seat",
    "crib",
    "high chair",
    "toys",
    "clothing",
    "shoes",
    "bath",
    "care",
}


def normalize_query(query: str) -> str:
    """Normalize search query for consistent matching."""
    if not query:
        return ""

    # Unicode normalization
    query = unicodedata.normalize("NFKC", query)

    # Convert to lowercase
    query = query.lower()

    # Remove trademark symbols
    query = query.replace("®", "").replace("™", "")

    # Normalize ampersands
    query = query.replace("&", " and ")

    # Remove special characters except alphanumeric, spaces, and hyphens
    query = re.sub(r"[^a-z0-9\s\-]+", " ", query)

    # Collapse multiple spaces
    return re.sub(r"\s+", " ", query).strip()



def canonicalize_brand(brand: str) -> str:
    """Canonicalize brand names using alias table."""
    if not brand:
        return ""

    normalized = normalize_query(brand)
    return BRAND_ALIASES.get(normalized, brand)


def is_baby_domain(text: str) -> bool:
    """Check if text contains baby-related keywords."""
    if not text:
        return False

    text_lower = text.lower()
    return any(domain in text_lower for domain in BABY_DOMAINS)


def clean_product_name(name: str) -> str:
    """Clean product names by removing trademark symbols and normalizing."""
    if not name:
        return ""

    # Remove trademark symbols
    cleaned = name.replace("®", "").replace("™", "")

    # Remove extra whitespace
    return re.sub(r"\s+", " ", cleaned).strip()



def calculate_suggestion_score(
    query: str,
    product_name: str,
    brand: str | None = None,
    domain: str | None = None,
    is_baby_product: bool = False,
) -> float:
    """Calculate relevance score for autocomplete suggestions."""
    if not query or not product_name:
        return 0.0

    query_norm = normalize_query(query)
    name_norm = normalize_query(product_name)
    brand_norm = normalize_query(brand) if brand else ""

    score = 0.0

    # Exact prefix match boost
    if name_norm.startswith(query_norm):
        score += 3.0

    # Brand prefix match boost
    if brand_norm and brand_norm.startswith(query_norm):
        score += 2.0

    # Baby domain boost
    if is_baby_product or (domain and domain.lower() == "baby"):
        score += 2.0

    # Contains match (lower score)
    if query_norm in name_norm:
        score += 1.0

    # Brand contains match
    if brand_norm and query_norm in brand_norm:
        score += 0.5

    return score


def highlight_match(text: str, query: str) -> str:
    """Highlight matching text (simple implementation)."""
    if not text or not query:
        return text

    # Case-insensitive highlighting
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(f"<mark>{query}</mark>", text)
