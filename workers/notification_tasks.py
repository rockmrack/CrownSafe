"""Stub worker task module for notifications

This is a stub implementation for Phase 1 testing.
Real implementation to be added later.
"""

from core_infra.celery_tasks import app


# Mock FirebaseMessaging for testing
class FirebaseMessaging:
    """Mock Firebase Messaging service."""

    def __init__(self):
        pass

    def send_batch(self, notifications):
        """Send batch of notifications."""
        return {"success_count": len(notifications), "failure_count": 0}

    def send(self, user_id, message):
        """Send single notification."""
        return {"success": True, "message_id": f"msg-{user_id}"}


@app.task(name="send_notification_batch")
def send_notification_batch_task(notifications):
    """Send batch of notifications

    Args:
        notifications: List of notification dictionaries

    Returns:
        dict: Result summary with counts
    """
    # Stub implementation
    fcm = FirebaseMessaging()
    result = fcm.send_batch(notifications)
    return {
        "total_sent": len(notifications),
        "success_count": result["success_count"],
        "failure_count": result["failure_count"],
        "failed_ids": [],
    }


@app.task(name="send_single_notification")
def send_single_notification_task(user_id, message, notification_type):
    """Send single notification to user

    Args:
        user_id: User identifier
        message: Notification message
        notification_type: Type of notification

    Returns:
        dict: Send result
    """
    # Stub implementation
    return {"success": True, "user_id": user_id, "notification_type": notification_type}
