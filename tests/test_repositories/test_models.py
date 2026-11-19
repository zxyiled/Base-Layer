import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import AppLog, ModelVersion, Prediction


def test_model_version_defaults_and_labels(app):
    model_version = ModelVersion(
        name="mobilenet-v1",
        architecture="mobilenet_v3_small",
        labels=["banano", "uva"],
    )
    db.session.add(model_version)
    db.session.commit()

    stored = db.session.get(ModelVersion, model_version.id)
    assert stored.is_active is False
    assert stored.labels == ["banano", "uva"]
    assert stored.created_at is not None
    assert stored.as_dict()["name"] == "mobilenet-v1"


def test_prediction_persists_top3_and_relationship(app):
    model_version = ModelVersion(name="v1", architecture="mobilenet_v3_small", labels=["uva"])
    db.session.add(model_version)
    db.session.commit()

    top3 = [
        {"label": "uva", "confidence": 0.9},
        {"label": "pera", "confidence": 0.05},
        {"label": "manzana", "confidence": 0.05},
    ]
    prediction = Prediction(
        model_version_id=model_version.id,
        source="camera",
        predicted_label="uva",
        confidence=0.9,
        top3=top3,
    )
    db.session.add(prediction)
    db.session.commit()

    stored = db.session.get(Prediction, prediction.id)
    assert stored.top3 == top3
    assert stored.created_at is not None
    assert stored.model_version.name == "v1"
    assert stored.as_dict()["label"] == "uva"


def test_prediction_rejects_unknown_source(app):
    db.session.add(
        Prediction(source="scanner", predicted_label="uva", confidence=0.5, top3=[])
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_app_log_persists_context(app):
    app_log = AppLog(level="INFO", logger="app.test", message="hola", context={"key": 1})
    db.session.add(app_log)
    db.session.commit()

    stored = db.session.get(AppLog, app_log.id)
    assert stored.context == {"key": 1}
    assert stored.created_at is not None
    assert stored.as_dict()["message"] == "hola"
