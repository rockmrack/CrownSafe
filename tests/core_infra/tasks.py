# core_infra/tasks.py

import logging
import asyncio
from .celery_app import celery_app

# --- START OF FIX ---
# Corrected the import path to match your directory structure: agents/engagement/push_notification_agent
from agents.engagement.push_notification_agent.agent_logic import PushNotificationAgentLogic

# --- END OF FIX ---

from agents.business.metrics_agent.agent_logic import MetricsAgentLogic
from .database import get_db_session, User

logger = logging.getLogger(__name__)

# Initialize agent logic instances that the task will use.
push_agent = PushNotificationAgentLogic(agent_id="bg_push_agent")
metrics_agent = MetricsAgentLogic(agent_id="bg_metrics_agent")


@celery_app.task(name="tasks.check_for_new_recalls_and_alert")
def check_for_new_recalls_and_alert():
    """
    A Celery task that simulates the entire background alert workflow.
    """
    logger.info("--- [Celery Task] Starting: Check for new recalls and alert ---")

    # 1. Simulate finding a new, high-risk recall.
    mock_new_recall = {
        "product_name": "Happy Baby Super-Puffs",
        "reason": "URGENT: Potential choking hazard from small parts.",
    }
    logger.info(f"[Celery Task] Found a new high-risk recall: {mock_new_recall['product_name']}")

    # 2. Simulate finding an affected user.
    mock_affected_user = {
        "user_id": "user_test_123",
        "device_token": "fake_device_token_for_testing_12345",
    }
    logger.info(f"[Celery Task] Found affected user: {mock_affected_user['user_id']}")

    # 3. Use PushNotificationAgent to send the alert.
    push_task_inputs = {
        "device_token": mock_affected_user["device_token"],
        "title": f"URGENT SAFETY ALERT: {mock_new_recall['product_name']}",
        "body": mock_new_recall["reason"],
    }
    # We need to run the async process_task in a sync context for this test
    push_result = asyncio.run(push_agent.process_task(push_task_inputs))
    if push_result["status"] == "COMPLETED":
        logger.info("[Celery Task] Push notification sent successfully.")
    else:
        logger.error("[Celery Task] Failed to send push notification.")

    # 4. Use MetricsAgent to track the event.
    metrics_task_inputs = {
        "user_id": mock_affected_user["user_id"],
        "event_name": "Emergency Alert Sent",
        "properties": {
            "product_name": mock_new_recall["product_name"],
            "reason": mock_new_recall["reason"],
        },
    }
    metrics_result = asyncio.run(metrics_agent.process_task(metrics_task_inputs))
    if metrics_result["status"] == "COMPLETED":
        logger.info("[Celery Task] Metrics event tracked successfully.")
    else:
        logger.error("[Celery Task] Failed to track metrics event.")

    logger.info("--- [Celery Task] Finished: Check for new recalls and alert ---")
    return "Workflow completed."
