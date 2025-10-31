import logging
from datetime import datetime, UTC

from sqlalchemy.orm import Session

from api.schemas.ingestion import IngestionSource, IngestionStatus
from core_infra.config import Config
from core_infra.database import get_db_session
from db.models.ingestion_run import IngestionRun

# Configure logging
logger = logging.getLogger(__name__)


class IngestionRunner:
    """Manages the lifecycle of data ingestion runs, recording their status in the database."""

    def __init__(self, db_session: Session, config: Config = None) -> None:
        self.db_session = db_session
        self.config = config or Config()

    def start_run(self, source: IngestionSource, run_name: str | None = None) -> IngestionRun:
        """Records the start of an ingestion run."""
        logger.info(f"Starting new ingestion run for source: {source.value}")
        ingestion_run = IngestionRun(
            agency=source.value,
            mode="manual",
            status=IngestionStatus.IN_PROGRESS.value,
            started_at=datetime.now(UTC),
        )
        self.db_session.add(ingestion_run)
        self.db_session.commit()
        self.db_session.refresh(ingestion_run)
        logger.info(f"Ingestion run {ingestion_run.id} started successfully.")
        return ingestion_run

    def end_run(
        self,
        run: IngestionRun,
        status: IngestionStatus,
        records_processed: int = 0,
        errors: int = 0,
        details: str | None = None,
    ) -> IngestionRun:
        """Records the completion or failure of an ingestion run."""
        logger.info(f"Ending ingestion run {run.id} with status: {status.value}")
        run.finished_at = datetime.now(UTC)
        run.status = status.value
        run.items_inserted = records_processed
        run.items_failed = errors
        run.error_text = details
        self.db_session.commit()
        self.db_session.refresh(run)

        logger.info(f"Ingestion run {run.id} ended.")
        return run


def main() -> None:
    """Example usage of the IngestionRunner."""
    config = Config()
    with get_db_session() as db_session:
        runner = IngestionRunner(db_session, config)

        # Start a run
        run = runner.start_run(source=IngestionSource.MANUAL_UPLOAD, run_name="Test Run")
        logger.info(f"Started run: {run.id} at {run.started_at}")

        # Simulate work
        import time

        time.sleep(2)
        records_processed = 100
        errors = 5

        # End the run
        run = runner.end_run(
            run=run,
            status=IngestionStatus.COMPLETED,
            records_processed=records_processed,
            errors=errors,
            details=f"Processed {records_processed} records with {errors} errors.",
        )
        logger.info(f"Ended run: {run.id} at {run.finished_at}")
        logger.info(f"Status: {run.status}")


if __name__ == "__main__":
    main()
