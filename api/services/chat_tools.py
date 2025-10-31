"""Chat tools service - stub implementation for chat router"""

from typing import Any

from sqlalchemy.orm import Session


def run_tool_for_intent(intent: str, db: Session, scan_data: dict[str, Any]) -> dict[str, Any]:
    """Run appropriate tool based on intent"""
    # Simple stub responses based on intent
    if intent == "recall_check":
        return {
            "recalls_found": 0,
            "safety_status": "safe",
            "message": "No recalls found for this product",
        }

    elif intent == "alternatives":
        return {
            "alternatives": {
                "items": [
                    {"name": "Similar Product A", "safety_rating": "A"},
                    {"name": "Similar Product B", "safety_rating": "A+"},
                ],
            },
        }

    elif intent == "safety_guidance":
        return {
            "guidance": [
                "Check product label for age recommendations",
                "Inspect for small parts if toy",
                "Verify expiration date if consumable",
            ],
        }

    else:
        return {
            "message": "General safety information available",
            "status": "completed",
        }
