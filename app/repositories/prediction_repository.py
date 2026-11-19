"""Database access for predictions."""

from typing import Any

from app.extensions import db
from app.models import Prediction
from app.models.prediction import SOURCES
from app.repositories.pagination import paginate


def create(
    source: str,
    predicted_label: str,
    confidence: float,
    top3: list[dict[str, Any]],
    original_filename: str | None = None,
    model_version_id: int | None = None,
) -> Prediction:
    """Insert one prediction."""
    if source not in SOURCES:
        raise ValueError(f"Unsupported source: {source!r}")
    prediction = Prediction(
        source=source,
        predicted_label=predicted_label,
        confidence=confidence,
        top3=top3,
        original_filename=original_filename,
        model_version_id=model_version_id,
    )
    db.session.add(prediction)
    db.session.commit()
    db.session.refresh(prediction)
    return prediction


def get_by_id(prediction_id: int) -> Prediction | None:
    """Return one prediction or ``None``."""
    return db.session.get(Prediction, prediction_id)


def list_paginated(
    page: int = 1,
    per_page: int = 20,
    label: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """Return a page of predictions filtered by label and/or source."""
    statement = db.select(Prediction)
    if label:
        statement = statement.where(Prediction.predicted_label == label)
    if source:
        statement = statement.where(Prediction.source == source)
    statement = statement.order_by(Prediction.created_at.desc(), Prediction.id.desc())
    return paginate(statement, page=page, per_page=per_page)


def stats() -> dict[str, Any]:
    """Return aggregate counts and the mean confidence."""
    total = db.session.scalar(db.select(db.func.count()).select_from(Prediction)) or 0
    mean_confidence = db.session.scalar(db.select(db.func.avg(Prediction.confidence)))

    by_label_rows = db.session.execute(
        db.select(Prediction.predicted_label, db.func.count().label("count"))
        .group_by(Prediction.predicted_label)
        .order_by(db.func.count().desc(), Prediction.predicted_label)
    ).all()
    by_source_rows = db.session.execute(
        db.select(Prediction.source, db.func.count().label("count"))
        .group_by(Prediction.source)
        .order_by(db.func.count().desc(), Prediction.source)
    ).all()

    return {
        "total": total,
        "mean_confidence": float(mean_confidence) if mean_confidence is not None else None,
        "by_label": [{"label": label, "count": count} for label, count in by_label_rows],
        "by_source": [{"source": source, "count": count} for source, count in by_source_rows],
    }
