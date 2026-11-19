"""Prediction record stored for every classified image."""

from typing import Any

from app.extensions import db
from app.models.model_version import utcnow

SOURCES = ("camera", "upload", "video")


class Prediction(db.Model):
    """Result of classifying one image."""

    __tablename__ = "predictions"
    __table_args__ = (
        db.CheckConstraint(
            "source IN ('camera', 'upload', 'video')",
            name="ck_predictions_source",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    model_version_id = db.Column(
        db.Integer,
        db.ForeignKey("model_versions.id", ondelete="SET NULL"),
        index=True,
    )
    source = db.Column(db.String(16), nullable=False, index=True)
    original_filename = db.Column(db.String(255))
    predicted_label = db.Column(db.String(64), nullable=False, index=True)
    confidence = db.Column(db.Float, nullable=False)
    top3 = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    model_version = db.relationship("ModelVersion", back_populates="predictions")

    def __repr__(self) -> str:
        return f"<Prediction {self.predicted_label!r} {self.confidence:.3f}>"

    def as_dict(self) -> dict[str, Any]:
        """Serialize the prediction for the API layer."""
        return {
            "id": self.id,
            "model_version_id": self.model_version_id,
            "source": self.source,
            "original_filename": self.original_filename,
            "label": self.predicted_label,
            "confidence": self.confidence,
            "top3": self.top3,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
