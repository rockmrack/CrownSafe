# workers/tasks/chat_cleanup.py
from __future__ import annotations
from uuid import UUID
from typing import Optional

from core_infra.database import SessionLocal  # adjust to your DB session factory

try:
    from core_infra.celery_tasks import celery_app as celery  # existing Celery app
except Exception:  # fallback shim if Celery not wired in tests
    celery = None  # type: ignore

from api.crud.chat_memory import purge_conversations_for_user, mark_erase_requested

TASK_NAME = "chat.cleanup.purge_user_history"


def _run_purge(user_id: UUID) -> int:
    db = SessionLocal()
    try:
        deleted = purge_conversations_for_user(db, user_id)
        return deleted
    finally:
        db.close()


if celery:

    @celery.task(name=TASK_NAME, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
    def purge_user_history_task(user_id_str: str) -> int:
        return _run_purge(UUID(user_id_str))  # Celery passes strings

else:
    # direct callable fallback (for local/dev/tests without Celery)
    def purge_user_history_task(user_id_str: str) -> int:
        return _run_purge(UUID(user_id_str))
