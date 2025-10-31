# agents/engagement/community_alert_agent/agent_logic.py
# Version 1.0 - Live Logic Implementation

import asyncio
import logging
from typing import Any

try:
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    BeautifulSoup = None

logger = logging.getLogger(__name__)

# Keywords that indicate a potential safety concern in community discussions.
SAFETY_KEYWORDS = ["rash", "choking", "hazard", "safety issue", "bad batch", "concern"]


class CommunityAlertAgentLogic:
    """Scrapes web pages to find early, unofficial warnings about product safety.
    """

    def __init__(self, agent_id: str, logger_instance: logging.Logger | None = None) -> None:
        self.agent_id = agent_id
        self.logger = logger_instance or logger
        self.logger.info(f"CommunityAlertAgentLogic initialized for agent {self.agent_id}.")

    async def scrape_and_analyze(self, html_content: str, product_name: str) -> dict[str, Any]:
        """Parses HTML content and analyzes it for safety keywords related to a product.
        """
        await asyncio.sleep(0.1)  # Simulate processing time
        self.logger.info(f"Scraping content for mentions of '{product_name}'...")

        if not BS4_AVAILABLE:
            self.logger.warning("BeautifulSoup not available - using simple text extraction")
            page_text = html_content.lower() if html_content else ""
        else:
            soup = BeautifulSoup(html_content, "html.parser")  # Use html.parser instead of lxml
            page_text = soup.get_text().lower()

        # Check if the product name is even mentioned on the page
        if product_name.lower() not in page_text:
            return {"mentions_found": 0, "risks": []}

        found_risks = []
        for keyword in SAFETY_KEYWORDS:
            if keyword in page_text:
                found_risks.append(keyword)

        self.logger.info(f"Found {len(found_risks)} potential risk keywords: {found_risks}")
        return {"mentions_found": 1, "risks": found_risks}

    async def process_task(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Main entry point for the agent.
        """
        self.logger.info(f"Received community alert task with inputs: {inputs}")
        html_content = inputs.get("html_content")
        product_name = inputs.get("product_name")

        if not all([html_content, product_name]):
            return {
                "status": "FAILED",
                "error": "html_content and product_name are required.",
            }

        try:
            analysis = await self.scrape_and_analyze(html_content, product_name)

            return {"status": "COMPLETED", "result": analysis}
        except Exception as e:
            self.logger.error(f"An error occurred during community alert analysis: {e}", exc_info=True)
            return {"status": "FAILED", "error": str(e)}
