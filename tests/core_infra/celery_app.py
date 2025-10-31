import os

from celery import Celery

# Get the Redis host from environment variables, defaulting to localhost
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)

# The broker URL tells Celery where to send messages.
# The backend URL tells Celery where to store task results.
BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
BACKEND_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"

# Create the Celery application instance
celery_app = Celery(
    "babyshield_tasks",
    broker=BROKER_URL,
    backend=BACKEND_URL,
    include=["agents.engagement.push_notification_agent.tasks"],  # IMPORTANT: Tell Celery where to find our tasks
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

if __name__ == "__main__":
    celery_app.start()
