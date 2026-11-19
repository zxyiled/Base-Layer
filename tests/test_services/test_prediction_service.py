import logging

import pytest

from app.core.errors import InvalidImageError, ModelUnavailableError, UnsupportedSourceError
from app.repositories import model_version_repository, prediction_repository
from app.services.history_service import HistoryService
from app.services.prediction_service import PredictionService


def test_predict_persists_and_returns_the_prediction(app, predictor, image_bytes):
    result = PredictionService(predictor).predict(image_bytes, source="camera", original_filename="foto.png")

    assert result["id"] > 0
    assert result["source"] == "camera"
    assert result["original_filename"] == "foto.png"
    assert result["file_size_bytes"] == len(image_bytes)
    assert result["label"] == "manzana"
    assert result["confidence"] == pytest.approx(0.9)
    assert result["top3"][0] == {"label": "manzana", "confidence": 0.9}
    assert result["inference_ms"] >= 0
    assert result["created_at"].endswith("+00:00")
    assert predictor.calls == 1
    assert HistoryService().get_prediction(result["id"]) == result


def test_source_defaults_to_upload(app, predictor, image_bytes):
    result = PredictionService(predictor).predict(image_bytes)
    assert result["source"] == "upload"
    assert result["original_filename"] is None


@pytest.mark.parametrize("source", ["camera", "upload", "video"])
def test_accepts_every_allowed_source(app, predictor, image_bytes, source):
    assert PredictionService(predictor).predict(image_bytes, source=source)["source"] == source


def test_rejects_unknown_source_without_predicting(app, predictor, image_bytes):
    with pytest.raises(UnsupportedSourceError) as error:
        PredictionService(predictor).predict(image_bytes, source="scanner")
    assert error.value.code == "unsupported_source"
    assert predictor.calls == 0
    assert prediction_repository.list_paginated()["total"] == 0


def test_rejects_empty_bytes(app, predictor):
    with pytest.raises(InvalidImageError):
        PredictionService(predictor).predict(b"")
    assert predictor.calls == 0


def test_rejects_corrupt_image(app, predictor):
    with pytest.raises(InvalidImageError, match="imagen válida"):
        PredictionService(predictor).predict(b"\x89PNG\r\n\x1a\n not really an image")
    assert predictor.calls == 0


def test_rejects_non_image_content(app, predictor):
    with pytest.raises(InvalidImageError):
        PredictionService(predictor).predict(b"just text, no image here")


def test_requires_a_loaded_model(app, image_bytes):
    with pytest.raises(ModelUnavailableError):
        PredictionService(None).predict(image_bytes)


def test_links_the_active_model_version(app, predictor, image_bytes):
    version = model_version_repository.create(
        name="v-test", architecture="fake_mobilenet", labels=predictor.labels
    )
    result = PredictionService(predictor, model_version_id=version.id).predict(image_bytes)
    assert result["model_version_id"] == version.id


def test_logs_metadata_but_not_image_bytes(app, predictor, image_bytes, caplog):
    with caplog.at_level(logging.INFO, logger="app.services.prediction_service"):
        PredictionService(predictor).predict(image_bytes, original_filename="camera.png")

    assert "label=manzana" in caplog.text
    assert "source=upload" in caplog.text
    assert "camera.png" in caplog.text
    assert f"size={len(image_bytes)}" in caplog.text
    assert "PNG" not in caplog.text
