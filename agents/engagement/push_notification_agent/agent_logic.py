# agents/engagement/push_notification_agent/agent_logic.py
import os
import asyncio
import logging
from typing import Dict, Any, Optional

try:
    import firebase_admin
    from firebase_admin import credentials, messaging

    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    firebase_admin = None
    credentials = None
    messaging = None

# Setup logger
logger = logging.getLogger(__name__)

# --- Firebase Initialization ---
if FIREBASE_AVAILABLE:
    try:
        if not firebase_admin._apps:
            key_path = os.path.join(os.path.dirname(__file__), "../../../secrets/serviceAccountKey.json")
            if os.path.exists(key_path):
                cred = credentials.Certificate(key_path)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized.")
            else:
                logger.warning(f"Firebase service account key not found at {key_path}")
                FIREBASE_AVAILABLE = False
    except Exception as e:
        logger.warning(f"Failed to initialize Firebase: {e}")
        FIREBASE_AVAILABLE = False
else:
    logger.warning("Firebase Admin SDK not available - push notifications will be mocked")


class PushNotificationAgentLogic:
    """
    Handles sending push notifications using Firebase Cloud Messaging (HTTP v1 via Admin SDK).
    """

    def __init__(self, agent_id: str, logger_instance: Optional[logging.Logger] = None):
        self.agent_id = agent_id
        self.logger = logger_instance or logger
        self.logger.info(f"PushNotificationAgentLogic initialized for agent {self.agent_id}.")

    def send_notification(
        self,
        device_token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Sends a single push notification to a device using Firebase Admin SDK.
        """
        self.logger.info(f"Sending notification to device: {device_token[:10]}...")

        if not FIREBASE_AVAILABLE:
            self.logger.warning("Firebase not available - returning mock response")
            return {
                "status": "mocked",
                "message": "Firebase not available - notification mocked",
                "notification_id": f"mock_{device_token[:10]}",
                "title": title,
                "body": body,
            }

        try:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                token=device_token,
                data=data or {},
            )
            response = messaging.send(message)
            self.logger.info(f"Message sent successfully: {response}")
            return {"status": "success", "message_id": response}
        except Exception as e:
            self.logger.error(f"Failed to send push notification: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def process_task(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point: processes inputs and sends notification.
        """
        self.logger.info(f"Received task inputs: {inputs}")
        device_token = inputs.get("device_token")
        title = inputs.get("title")
        body = inputs.get("body")
        data = inputs.get("data", {})

        if not all([device_token, title, body]):
            return {
                "status": "FAILED",
                "error": "Missing one of: device_token, title, body",
            }

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self.send_notification, device_token, title, body, data)

        if result.get("status") == "success":
            return {"status": "COMPLETED", "message_id": result.get("message_id")}
        else:
            return {"status": "FAILED", "error": result.get("message")}
