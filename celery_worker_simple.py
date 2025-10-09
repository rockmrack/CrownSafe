"""
Simple Celery worker for testing
Handles missing dependencies gracefully
"""

from celery import Celery
import os
import time

# Create Celery app
app = Celery(
    "babyshield",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
)

# Configure Celery
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_soft_time_limit=30,
    task_time_limit=60,
)


@app.task(name="test_task")
def test_task(message):
    """Simple test task"""
    print(f"Processing: {message}")
    time.sleep(2)
    return f"Completed: {message}"


@app.task(name="process_safety_check")
def process_safety_check(product_name):
    """Process safety check asynchronously"""
    print(f"Checking safety for: {product_name}")
    # Simulate processing
    time.sleep(3)
    return {
        "product": product_name,
        "status": "checked",
        "risk_level": "low",
        "timestamp": time.time(),
    }


@app.task(name="process_barcode")
def process_barcode(barcode):
    """Process barcode asynchronously"""
    print(f"Processing barcode: {barcode}")
    time.sleep(1)
    return {"barcode": barcode, "type": "UPC", "decoded": True}


if __name__ == "__main__":
    print("✅ Celery worker configured!")
    print("\n💡 To start the worker, run:")
    print("   celery -A celery_worker_simple worker --loglevel=info")
    print("\n💡 For Windows:")
    print("   celery -A celery_worker_simple worker --loglevel=info --pool=solo")
