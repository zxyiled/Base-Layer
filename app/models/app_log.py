"""Application log entries persisted in the database."""

from typing import Any

from app.extensions import db
from app.models.model_version import utcnow


class AppLog(db.Model):
    """One structured log record."""

    __tablename__ = "app_logs"

    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(16), nullable=False, index=True)
    logger = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    context = db.Column(db.JSON)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    def __repr__(self) -> str:
        return f"<AppLog {self.level} {self.logger!r}>"

    def as_dict(self) -> dict[str, Any]:
        """Serialize the log entry for the API layer."""
        return {
            "id": self.id,
            "level": self.level,
            "logger": self.logger,
            "message": self.message,
            "context": self.context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
