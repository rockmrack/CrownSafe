from typing import Union
from uuid import UUID

from sqlalchemy.orm import Session

from api.models.analytics import ExplainFeedback


def create_explain_feedback(
    db: Session,
    *,
    scan_id: str,
    helpful: bool,
    user_id: Union[UUID, None] = None,
    trace_id: str | None = None,
    reason: str | None = None,
    comment: str | None = None,
    platform: str | None = None,
    app_version: str | None = None,
    locale: str | None = None,
    jurisdiction_code: str | None = None,
) -> int:
    """Create a new explain feedback record.

    Returns the ID of the created record.
    """
    row = ExplainFeedback(
        user_id=user_id,
        scan_id=scan_id,
        trace_id=trace_id,
        helpful=helpful,
        reason=reason,
        comment=comment,
        platform=platform,
        app_version=app_version,
        locale=locale,
        jurisdiction_code=jurisdiction_code,
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    return int(row.id)
