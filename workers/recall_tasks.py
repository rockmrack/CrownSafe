"""
Recall ingestion Celery tasks for BabyShield Backend.

This module provides background task processing for regulatory agency recall ingestion.
"""

from typing import Any, Dict, List

from celery import Task


# Mock RecallAgent for testing
class RecallAgent:
    """Mock RecallAgent for testing purposes."""

    def __init__(self):
        pass

    def fetch_recalls(self, agency: str, date_range: Dict[str, str]) -> List[Dict[str, Any]]:
        """Fetch recalls from a specific agency."""
        return [{"recall_id": "TEST-001", "agency": agency, "title": "Test Recall", "date": "2025-01-01"}]

    def process_recall(self, recall_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single recall."""
        return {"status": "processed", "recall_id": recall_data.get("recall_id")}


# Celery app will be imported from core_infra when available
try:
    from core_infra.celery_tasks import app
except ImportError:
    # Mock app for testing
    class MockCeleryApp:
        def task(self, **kwargs):
            def decorator(func):
                return func

            return decorator

    app = MockCeleryApp()


@app.task(
    name="ingest_recalls_from_agency",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=360,
)
def ingest_recalls_from_agency_task(self: Task, agency: str, date_range: Dict[str, str]) -> Dict[str, Any]:
    """
    Ingest recalls from a specific regulatory agency.

    Args:
        self: Celery task instance (when bind=True)
        agency: Agency code (e.g., 'CPSC', 'FDA', 'NHTSA')
        date_range: Dict with 'start_date' and 'end_date'

    Returns:
        Dict with ingestion results
    """
    try:
        agent = RecallAgent()
        recalls = agent.fetch_recalls(agency, date_range)

        processed_count = 0
        failed_count = 0

        for recall in recalls:
            try:
                result = agent.process_recall(recall)
                if result.get("status") == "processed":
                    processed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                print(f"Failed to process recall: {e}")

        return {
            "success": True,
            "agency": agency,
            "total_recalls": len(recalls),
            "processed": processed_count,
            "failed": failed_count,
            "date_range": date_range,
        }

    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=min(60 * (2**self.request.retries), 300)) from exc


@app.task(name="refresh_all_recalls", soft_time_limit=600, time_limit=720)
def refresh_all_recalls_task() -> Dict[str, Any]:
    """
    Refresh recalls from all configured agencies.

    Returns:
        Dict with refresh results for all agencies
    """
    agencies = ["CPSC", "FDA", "NHTSA", "Transport_Canada", "Health_Canada"]
    results = []

    for agency in agencies:
        date_range = {"start_date": "2024-01-01", "end_date": "2025-12-31"}

        # Chain task execution
        result = ingest_recalls_from_agency_task.apply_async(
            args=[agency, date_range],
            countdown=5,  # Stagger requests
        )

        results.append({"agency": agency, "task_id": str(result.id) if hasattr(result, "id") else "mock-task-id"})

    return {"success": True, "agencies_triggered": len(agencies), "task_ids": results}
