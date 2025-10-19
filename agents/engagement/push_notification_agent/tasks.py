import logging
from core_infra.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="send_push_notification")
def send_push_notification_task(user_device_token: str, title: str, message: str):
    """
    This is the background task that sends a push notification.
    In a real system, this would contain the logic to call Firebase Cloud Messaging (FCM)
    or Apple Push Notification service (APNs).
    """
    logger.info(
        f"--- SENDING PUSH NOTIFICATION (Task ID: {send_push_notification_task.request.id}) ---"
    )
    logger.info(f"  -> To Device Token: {user_device_token}")
    logger.info(f"  -> Title: {title}")
    logger.info(f"  -> Message: {message}")

    # --- MOCK IMPLEMENTATION ---
    # Simulate an API call to a push notification service
    import time

    time.sleep(1)  # Simulate network latency
    # --- END MOCK ---

    logger.info("--- PUSH NOTIFICATION SENT SUCCESSFULLY ---")
    return {"status": "sent", "token": user_device_token}
