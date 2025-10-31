import asyncio
import logging
import time
from threading import Thread

import schedule

from .agent_logic import CommunityAlertAgentLogic

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AGENT_ID = "community_alert_agent_01"
SCRAPE_INTERVAL_HOURS = 6  # Run every 6 hours


class CommunityAlertAgent:
    def __init__(self):
        self.agent_id = AGENT_ID
        self.logic = CommunityAlertAgentLogic(agent_id=self.agent_id)
        self.scheduler_thread = None
        self.is_running = False
        logger.info(f"CommunityAlertAgent initialized: {self.agent_id}")

    async def _run_scrape_job(self):
        """The async job that the scheduler will run."""
        logger.info("Scheduler triggered: Running community scrape cycle.")
        try:
            await self.logic.scrape_for_signals()
        except Exception as e:
            logger.error(f"An error occurred in the scheduled scrape job: {e}", exc_info=True)

    def start(self):
        """Starts the agent's scheduled data scraping."""
        logger.info(f"Starting {self.agent_id}...")

        schedule.every(SCRAPE_INTERVAL_HOURS).hours.do(lambda: asyncio.run(self._run_scrape_job()))

        self.is_running = True

        def run_scheduler():
            logger.info("Scheduler thread started.")
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
            logger.info("Scheduler thread stopped.")

        self.scheduler_thread = Thread(target=run_scheduler)
        self.scheduler_thread.start()

        logger.info(f"{self.agent_id} started. Scraping will run every {SCRAPE_INTERVAL_HOURS} hour(s).")
        # Run one initial scrape immediately on startup
        logger.info("Performing initial scrape on startup...")
        asyncio.run(self._run_scrape_job())

    def stop(self):
        # ... (Standard stop method) ...
        pass


def main():
    agent = CommunityAlertAgent()
    # ... (Standard main execution block) ...
    agent.start()


if __name__ == "__main__":
    main()
