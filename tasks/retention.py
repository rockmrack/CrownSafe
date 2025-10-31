from datetime import datetime, timedelta, UTC

from sqlalchemy import text

from core_infra.celery_tasks import app as celery_app  # your existing Celery app
from core_infra.database import get_db_session

RETENTION_DAYS_LEGAL = 30  # purge deleted users' residuals after 30d
RETENTION_DAYS_AUDIT = 365  # keep audit trail for 1y


@celery_app.task(name="retention.purge_legal_retention")
def purge_legal_retention():
    now = datetime.now(UTC)
    cutoff_legal = now - timedelta(days=RETENTION_DAYS_LEGAL)
    cutoff_audit = now - timedelta(days=RETENTION_DAYS_AUDIT)

    db = next(get_db_session())
    try:
        # Orphaned push tokens
        db.execute(
            text(
                """
            DELETE FROM device_push_tokens
            WHERE user_id IN (SELECT id FROM "user" WHERE deleted_at IS NOT NULL AND deleted_at < :cutoff)
        """,
            ),
            {"cutoff": cutoff_legal},
        )

        # Server-side sessions
        db.execute(
            text(
                """
            DELETE FROM user_sessions
            WHERE user_id IN (SELECT id FROM "user" WHERE deleted_at IS NOT NULL AND deleted_at < :cutoff)
               OR updated_at < :old
        """,
            ),
            {"cutoff": cutoff_legal, "old": now - timedelta(days=30)},
        )

        # Refresh tokens (defence in depth)
        db.execute(
            text(
                """
            DELETE FROM refresh_tokens
            WHERE user_id IN (SELECT id FROM "user" WHERE deleted_at IS NOT NULL AND deleted_at < :cutoff)
        """,
            ),
            {"cutoff": cutoff_legal},
        )

        # Trim audit log older than 1 year
        db.execute(
            text(
                """
            DELETE FROM account_deletion_audit
            WHERE created_at < :cutoff_audit
        """,
            ),
            {"cutoff_audit": cutoff_audit},
        )

        db.commit()
        return {
            "ok": True,
            "cutoff_legal": cutoff_legal.isoformat(),
            "cutoff_audit": cutoff_audit.isoformat(),
        }
    finally:
        db.close()
