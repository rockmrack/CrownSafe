"""
Evidence generation utilities for chat responses.
Provides helper functions to create properly formatted evidence items.
"""

from typing import List, Dict, Any, Optional


def label_to_evidence(
    evidence_id: str, url: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generate evidence items for product label information.

    Args:
        evidence_id: Identifier for the type of label information
        url: Optional URL to the evidence source

    Returns:
        List of evidence dictionaries
    """
    return [{"type": "label", "source": "Product label", "id": evidence_id, "url": url}]


def regulatory_to_evidence(
    agency: str, title: Optional[str] = None, url: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generate evidence item for regulatory guidance.

    Args:
        agency: Regulatory agency (e.g., "FDA", "CPSC", "EU Safety Gate")
        title: Optional title of the guidance
        url: Optional URL to the guidance

    Returns:
        List of evidence dictionaries
    """
    return [{"type": "regulatory", "source": agency, "id": title, "url": url}]


def recalls_to_evidence(recalls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert recall records to evidence items.

    Args:
        recalls: List of recall dictionaries with id, agency, url, etc.

    Returns:
        List of evidence dictionaries
    """
    evidence = []
    for recall in recalls:
        evidence.append(
            {
                "type": "recall",
                "source": recall.get("agency", "Unknown Agency"),
                "id": recall.get("id", ""),
                "url": recall.get("url"),
            }
        )
    return evidence


def datasheet_to_evidence(
    source: str, product_id: str, url: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generate evidence item for product datasheet.

    Args:
        source: Source of the datasheet (e.g., manufacturer name)
        product_id: Product identifier
        url: Optional URL to the datasheet

    Returns:
        List of evidence dictionaries
    """
    return [{"type": "datasheet", "source": source, "id": product_id, "url": url}]


def guideline_to_evidence(
    organization: str, guideline_name: str, url: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generate evidence item for safety guidelines.

    Args:
        organization: Organization that published the guideline
        guideline_name: Name of the guideline
        url: Optional URL to the guideline

    Returns:
        List of evidence dictionaries
    """
    return [
        {
            "type": "guideline",
            "source": organization,
            "id": guideline_name,
            "url": url,
        }
    ]
