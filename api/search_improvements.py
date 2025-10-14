from api.pydantic_base import AppModel

"""
Improved search functionality for better recall matching
Handles compound searches, partial matches, and brand-product combinations
"""

from sqlalchemy import or_, and_, func
from typing import List, Optional
import re
import logging

logger = logging.getLogger(__name__)


def tokenize_search_query(query: str) -> List[str]:
    """
    Tokenize search query into meaningful parts
    Handles brand-product combinations and special characters
    """
    # Remove extra spaces and normalize
    query = re.sub(r"\s+", " ", query.strip())

    # Check for brand - product pattern (common in recalls)
    if " - " in query:
        parts = query.split(" - ", 1)
        return [p.strip() for p in parts if p.strip()]

    # For long queries, also create word tokens
    if len(query) > 50:
        # Split into significant words (>= 3 chars)
        words = [w for w in query.split() if len(w) >= 3]
        # Keep first 5 most significant words
        significant_words = []
        for word in words:
            # Skip common words
            if word.lower() not in ["the", "and", "for", "with", "llc", "inc", "corp"]:
                significant_words.append(word)
                if len(significant_words) >= 5:
                    break
        return significant_words

    return [query]


def build_smart_search_conditions(RecallDB, search_term: str):
    """
    Build intelligent search conditions that handle various search patterns
    """
    conditions = []

    # Always search for the full term
    full_term_conditions = or_(
        RecallDB.product_name.ilike(f"%{search_term}%"),
        RecallDB.brand.ilike(f"%{search_term}%"),
        RecallDB.hazard.ilike(f"%{search_term}%"),
        RecallDB.description.ilike(f"%{search_term}%"),
        RecallDB.manufacturer.ilike(f"%{search_term}%"),
        RecallDB.recall_reason.ilike(f"%{search_term}%"),
    )
    conditions.append(full_term_conditions)

    # Tokenize and search for parts
    tokens = tokenize_search_query(search_term)

    if len(tokens) > 1:
        # Search for each token
        for token in tokens:
            if len(token) >= 3:  # Only search for meaningful tokens
                token_conditions = or_(
                    RecallDB.product_name.ilike(f"%{token}%"),
                    RecallDB.brand.ilike(f"%{token}%"),
                    RecallDB.hazard.ilike(f"%{token}%"),
                    RecallDB.description.ilike(f"%{token}%"),
                )
                conditions.append(token_conditions)

        # Special handling for brand - product pattern
        if " - " in search_term:
            parts = search_term.split(" - ", 1)
            if len(parts) == 2:
                brand_part = parts[0].strip()
                product_part = parts[1].strip()

                # Search for brand AND product match
                brand_product_condition = and_(
                    or_(
                        RecallDB.brand.ilike(f"%{brand_part}%"),
                        RecallDB.manufacturer.ilike(f"%{brand_part}%"),
                    ),
                    or_(
                        RecallDB.product_name.ilike(f"%{product_part}%"),
                        RecallDB.description.ilike(f"%{product_part}%"),
                    ),
                )
                conditions.append(brand_product_condition)

    # Return OR of all conditions
    if len(conditions) > 1:
        return or_(*conditions)
    return conditions[0] if conditions else None


def score_search_result(result, search_term: str) -> float:
    """
    Score a search result based on relevance to the search term
    Higher score = more relevant
    """
    score = 0.0
    search_lower = search_term.lower()

    # Check for exact matches (highest score)
    if result.product_name and search_lower in result.product_name.lower():
        score += 10.0
    if result.brand and search_lower in result.brand.lower():
        score += 8.0

    # Check for token matches
    tokens = tokenize_search_query(search_term)
    for token in tokens:
        token_lower = token.lower()

        # Product name matches
        if result.product_name and token_lower in result.product_name.lower():
            score += 5.0

        # Brand matches
        if result.brand and token_lower in result.brand.lower():
            score += 4.0

        # Description matches
        if result.description and token_lower in result.description.lower():
            score += 2.0

        # Hazard matches
        if result.hazard and token_lower in result.hazard.lower():
            score += 3.0

    # Boost score for recent recalls
    if hasattr(result, "recall_date") and result.recall_date:
        from datetime import datetime, timedelta

        if result.recall_date > (datetime.now().date() - timedelta(days=365)):
            score += 1.0  # Recent recall
        if result.recall_date > (datetime.now().date() - timedelta(days=30)):
            score += 2.0  # Very recent recall

    # Boost for FDA/CPSC (major agencies)
    if hasattr(result, "source_agency"):
        if result.source_agency in ["FDA", "CPSC"]:
            score += 1.0

    return score


def deduplicate_results(results, key_fields=["recall_id", "product_name"]):
    """
    Remove duplicate results based on key fields
    """
    seen = set()
    unique_results = []

    for result in results:
        # Create a unique key from the specified fields
        key_parts = []
        for field in key_fields:
            value = getattr(result, field, None)
            if value:
                key_parts.append(str(value).lower())

        key = "|".join(key_parts)

        if key not in seen:
            seen.add(key)
            unique_results.append(result)

    return unique_results


def format_search_response(result):
    """
    Format a search result for API response
    Ensures consistent structure
    """
    # Convert to dict first
    if hasattr(result, "to_dict"):
        data = result.to_dict()
    else:
        data = {c.name: getattr(result, c.name) for c in result.__table__.columns}

    # Ensure required fields
    response = {
        "id": data.get("recall_id") or data.get("id"),
        "agencyCode": data.get("source_agency", "UNKNOWN"),
        "title": None,  # Will be constructed
        "description": data.get("description") or data.get("hazard") or "",
        "productName": data.get("product_name", ""),
        "brand": data.get("brand", ""),
        "model": data.get("model_number"),
        "upc": data.get("upc"),
        "hazard": data.get("hazard") or data.get("recall_reason", ""),
        "riskCategory": data.get("hazard_category", "unknown"),
        "severity": "medium",  # Default if not specified
        "status": "active",
        "imageUrl": None,
        "affectedCountries": [],
        "recallDate": data.get("recall_date"),
        "lastUpdated": data.get("last_updated") or data.get("recall_date"),
        "sourceUrl": data.get("url"),
    }

    # Construct title from brand and product name
    if response["brand"] and response["productName"]:
        response["title"] = f"{response['brand']} - {response['productName']}"
    else:
        response["title"] = response["productName"] or response["brand"] or "Unknown Product"

    # Determine affected countries based on agency
    agency = response["agencyCode"]
    if agency in ["FDA", "CPSC", "NHTSA", "USDA_FSIS"]:
        response["affectedCountries"] = ["United States"]
    elif agency in ["Health_Canada", "CFIA", "Transport_Canada"]:
        response["affectedCountries"] = ["Canada"]
    elif agency.startswith("EU_"):
        response["affectedCountries"] = ["European Union"]
    elif agency == "UK_FSA" or agency == "UK_OPSS":
        response["affectedCountries"] = ["United Kingdom"]
    else:
        response["affectedCountries"] = ["Unknown"]

    # Determine severity based on hazard
    hazard_lower = (response["hazard"] or "").lower()
    if any(word in hazard_lower for word in ["death", "fatal", "lethal"]):
        response["severity"] = "critical"
    elif any(word in hazard_lower for word in ["injury", "burn", "choking", "poison"]):
        response["severity"] = "high"
    elif any(word in hazard_lower for word in ["risk", "potential", "may"]):
        response["severity"] = "medium"
    else:
        response["severity"] = "low"

    # Clean up None values
    for key, value in response.items():
        if value is None:
            if key in ["affectedCountries"]:
                response[key] = []
            else:
                response[key] = ""

    return response
