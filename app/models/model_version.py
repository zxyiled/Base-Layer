"""Model version persisted alongside its predictions."""

from datetime import datetime, timezone
from typing import Any

from app.extensions import db


def utcnow() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(timezone.utc)


class ModelVersion(db.Model):
    """A trained artifact that can be activated to serve predictions."""

    __tablename__ = "model_versions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    architecture = db.Column(db.String(80), nullable=False)
    artifact_path = db.Column(db.String(255))
    labels = db.Column(db.JSON, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    predictions = db.relationship(
        "Prediction",
        back_populates="model_version",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<ModelVersion {self.name!r} active={self.is_active}>"

    def as_dict(self) -> dict[str, Any]:
        """Serialize the model version for the API layer."""
        return {
            "id": self.id,
            "name": self.name,
            "architecture": self.architecture,
            "artifact_path": self.artifact_path,
            "labels": self.labels,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
