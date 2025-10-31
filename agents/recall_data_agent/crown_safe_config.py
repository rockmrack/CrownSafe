"""Crown Safe - Recall Agent Configuration
Adapts recall_data_agent to filter for hair/cosmetic products only

Changes from BabyShield:
- Filter for cosmetic/hair product categories
- Add FDA Cosmetics connector (if available)
- Remove baby-specific categories
- Focus on: hair relaxers, hair dyes, shampoos, conditioners, styling products
"""

# ============================================================================
# CROWN SAFE PRODUCT CATEGORIES (for recall filtering)
# ============================================================================

CROWN_SAFE_CATEGORIES = [
    # Hair care products
    "shampoo",
    "conditioner",
    "hair treatment",
    "hair mask",
    "hair oil",
    "hair serum",
    "leave-in conditioner",
    "deep conditioner",
    # Styling products
    "hair gel",
    "hair mousse",
    "hair cream",
    "hair pomade",
    "hair wax",
    "hair spray",
    "curl cream",
    "edge control",
    # Chemical treatments
    "hair relaxer",
    "hair straightener",
    "hair color",
    "hair dye",
    "bleach",
    "perming solution",
    "texturizer",
    # Scalp care
    "scalp treatment",
    "scalp oil",
    "dandruff shampoo",
    "medicated shampoo",
    # General cosmetics (may affect hair)
    "cosmetic",
    "personal care",
    "beauty product",
]

# Keywords to search for in recall descriptions
CROWN_SAFE_KEYWORDS = [
    "hair",
    "scalp",
    "shampoo",
    "conditioner",
    "relaxer",
    "straightener",
    "curl",
    "styling",
    "cosmetic",
    "beauty",
    "salon",
    "barber",
]

# Exclude baby-specific recalls (keep children's hair products)
EXCLUDE_KEYWORDS = [
    "baby bottle",
    "pacifier",
    "crib",
    "stroller",
    "car seat",
    "infant formula",
    "baby food",
    "diaper",
    "teething",
]


# ============================================================================
# RECALL SEVERITY MAPPING (for Crown Safe context)
# ============================================================================

SEVERITY_MAPPING = {
    # Hair/scalp damage
    "hair_loss": "CRITICAL",
    "chemical_burn": "CRITICAL",
    "scalp_burn": "CRITICAL",
    "blistering": "HIGH",
    "severe_reaction": "HIGH",
    # Allergic reactions
    "allergic_reaction": "HIGH",
    "skin_irritation": "MEDIUM",
    "rash": "MEDIUM",
    "itching": "LOW",
    # Product quality
    "contamination": "HIGH",
    "mislabeled": "MEDIUM",
    "undeclared_ingredient": "HIGH",
    # Chemical hazards
    "formaldehyde": "CRITICAL",
    "lead": "CRITICAL",
    "mercury": "CRITICAL",
    "asbestos": "CRITICAL",
    "carcinogen": "HIGH",
}


# ============================================================================
# AGENCY PRIORITY (for Crown Safe)
# ============================================================================

# Agencies relevant for hair/cosmetic products
CROWN_SAFE_AGENCIES = [
    "FDA",  # US Food & Drug Administration (Cosmetics)
    "CPSC",  # US Consumer Product Safety Commission
    "UKPSD",  # UK Product Safety Database
    "Health Canada",
    "EU RAPEX",  # EU Rapid Alert System
    "TGA",  # Australia Therapeutic Goods Administration
    "ANVISA",  # Brazil health regulator
]

# Agencies to deprioritize (baby-focused)
DEPRIORITIZE_AGENCIES = [
    "NHTSA",  # Car seats, not relevant
]


# ============================================================================
# FILTERING FUNCTION
# ============================================================================


def is_crown_safe_recall(recall_title: str, recall_description: str, product_category: str) -> bool:
    """Determine if a recall is relevant for Crown Safe (hair/cosmetic products).

    Args:
        recall_title: Recall title/product name
        recall_description: Detailed recall description
        product_category: Product category from agency

    Returns:
        True if recall is relevant for hair/cosmetic safety

    """
    # Combine all text for searching
    text = f"{recall_title} {recall_description} {product_category}".lower()

    # Exclude baby-specific products
    if any(exclude in text for exclude in EXCLUDE_KEYWORDS):
        return False

    # Check if matches Crown Safe categories
    if any(category in text for category in CROWN_SAFE_CATEGORIES):
        return True

    # Check if matches Crown Safe keywords
    if any(keyword in text for keyword in CROWN_SAFE_KEYWORDS):
        return True

    return False


# ============================================================================
# INTEGRATION INSTRUCTIONS
# ============================================================================

"""
To apply this configuration to recall_data_agent:

1. Modify agents/recall_data_agent/agent_logic.py:
   - Import this config file
   - Add is_crown_safe_recall() filter to query results
   - Filter ingestion to only save Crown Safe relevant recalls

2. Update connectors.py:
   - Add FDA Cosmetics API connector (if available)
   - Prioritize CROWN_SAFE_AGENCIES

3. Update README.md:
   - Note Crown Safe filtering
   - Update category examples

Example modification in agent_logic.py:

```python
from agents.recall_data_agent.crown_safe_config import is_crown_safe_recall

def query_recalls(self, product_name: str):
    results = self._database_query(product_name)
    
    # Filter for Crown Safe relevance
    filtered_results = [
        r for r in results
        if is_crown_safe_recall(
            r.get("title", ""),
            r.get("description", ""),
            r.get("category", "")
        )
    ]
    
    return filtered_results
```
"""
