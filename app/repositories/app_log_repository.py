"""Database access for application logs."""

from typing import Any

from app.extensions import db
from app.models import AppLog
from app.repositories.pagination import paginate


def create(
    level: str,
    logger: str,
    message: str,
    context: dict[str, Any] | None = None,
) -> AppLog:
    """Insert one log entry."""
    app_log = AppLog(level=level.upper(), logger=logger, message=message, context=context)
    db.session.add(app_log)
    db.session.commit()
    db.session.refresh(app_log)
    return app_log


def list_paginated(
    page: int = 1,
    per_page: int = 20,
    level: str | None = None,
) -> dict[str, Any]:
    """Return a page of log entries, optionally filtered by level."""
    statement = db.select(AppLog)
    if level:
        statement = statement.where(AppLog.level == level.upper())
    statement = statement.order_by(AppLog.created_at.desc(), AppLog.id.desc())
    return paginate(statement, page=page, per_page=per_page)
