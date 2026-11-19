import pytest

from app.models import ModelVersion
from app.repositories import model_version_repository, prediction_repository

TOP3 = [{"label": "uva", "confidence": 0.8}]


def _create(source="camera", label="uva", confidence=0.8):
    return prediction_repository.create(
        source=source,
        predicted_label=label,
        confidence=confidence,
        top3=TOP3,
        original_filename="foto.jpg",
    )


def test_create_and_get_prediction(app):
    created = _create()
    stored = prediction_repository.get_by_id(created.id)
    assert stored is not None
    assert stored.predicted_label == "uva"
    assert stored.original_filename == "foto.jpg"
    assert stored.top3 == TOP3


def test_create_rejects_unsupported_source(app):
    with pytest.raises(ValueError):
        _create(source="scanner")


def test_create_links_model_version(app):
    model_version = model_version_repository.create(
        name="v1", architecture="mobilenet_v3_small", labels=["uva"]
    )
    prediction = prediction_repository.create(
        source="upload",
        predicted_label="uva",
        confidence=0.7,
        top3=TOP3,
        model_version_id=model_version.id,
    )
    assert prediction.model_version_id == model_version.id
    assert isinstance(model_version, ModelVersion)


def test_list_is_paginated_and_newest_first(app):
    created = [_create(label=label) for label in ("uva", "pera", "uva", "fresa", "uva")]

    first_page = prediction_repository.list_paginated(page=1, per_page=2)
    assert first_page["total"] == 5
    assert first_page["pages"] == 3
    assert first_page["page"] == 1
    assert len(first_page["items"]) == 2
    assert [item.id for item in first_page["items"]] == [created[-1].id, created[-2].id]

    last_page = prediction_repository.list_paginated(page=3, per_page=2)
    assert len(last_page["items"]) == 1
    assert last_page["items"][0].id == created[0].id


def test_list_filters_by_label_and_source(app):
    _create(label="uva", source="camera")
    _create(label="uva", source="upload")
    _create(label="pera", source="camera")

    by_label = prediction_repository.list_paginated(label="uva")
    assert by_label["total"] == 2

    by_both = prediction_repository.list_paginated(label="uva", source="upload")
    assert by_both["total"] == 1
    assert by_both["items"][0].source == "upload"


def test_stats_aggregates_counts_and_confidence(app):
    _create(label="uva", source="camera", confidence=0.9)
    _create(label="uva", source="upload", confidence=0.7)
    _create(label="pera", source="camera", confidence=0.5)

    stats = prediction_repository.stats()
    assert stats["total"] == 3
    assert stats["mean_confidence"] == pytest.approx(0.7)
    assert stats["by_label"] == [{"label": "uva", "count": 2}, {"label": "pera", "count": 1}]
    assert stats["by_source"] == [{"source": "camera", "count": 2}, {"source": "upload", "count": 1}]


def test_stats_on_empty_table(app):
    stats = prediction_repository.stats()
    assert stats == {"total": 0, "mean_confidence": None, "by_label": [], "by_source": []}


def test_create_stores_file_size_and_inference_time(app):
    created = prediction_repository.create(
        source="video",
        predicted_label="uva",
        confidence=0.8,
        top3=TOP3,
        original_filename="frame.jpg",
        file_size_bytes=20480,
        inference_ms=12.5,
    )
    data = prediction_repository.get_by_id(created.id).as_dict()
    assert data["file_size_bytes"] == 20480
    assert data["inference_ms"] == 12.5


def test_as_dict_serializes_created_at_in_utc(app):
    created_at = _create().as_dict()["created_at"]
    assert created_at.endswith("+00:00")


def test_list_filters_by_date_range(app):
    from datetime import datetime, timedelta, timezone

    from app.extensions import db

    base = datetime(2026, 11, 1, tzinfo=timezone.utc)
    for days in (0, 1, 2):
        prediction = _create()
        prediction.created_at = base + timedelta(days=days)
    db.session.commit()

    window = prediction_repository.list_paginated(date_from=base + timedelta(days=1), date_to=base + timedelta(days=2))
    assert window["total"] == 1
    assert prediction_repository.list_paginated(date_from=base + timedelta(days=1))["total"] == 2
    assert prediction_repository.list_paginated(date_to=base + timedelta(days=1))["total"] == 1


def test_confidence_out_of_range_is_rejected(app):
    from sqlalchemy.exc import IntegrityError

    from app.extensions import db

    with pytest.raises(IntegrityError):
        _create(confidence=1.5)
    db.session.rollback()
