import pytest

from app.core.errors import NotFoundError, UnsupportedSourceError
from app.services.history_service import HistoryService
from app.services.prediction_service import PredictionService
from app.services.stats_service import StatsService


def _seed(predictor, image_bytes):
    service = PredictionService(predictor)
    service.predict(image_bytes, source="camera", original_filename="uno.png")
    service.predict(image_bytes, source="upload", original_filename="dos.png")
    service.predict(image_bytes, source="video", original_filename="tres.png")


def test_list_predictions_serializes_and_paginates(app, predictor, image_bytes):
    _seed(predictor, image_bytes)
    page = HistoryService().list_predictions(page=1, per_page=2)

    assert page["total"] == 3
    assert page["pages"] == 2
    assert page["page"] == 1
    assert page["per_page"] == 2
    assert len(page["items"]) == 2
    assert page["items"][0]["original_filename"] == "tres.png"
    assert isinstance(page["items"][0], dict)


def test_list_predictions_filters_by_source(app, predictor, image_bytes):
    _seed(predictor, image_bytes)
    page = HistoryService().list_predictions(source="video")
    assert page["total"] == 1
    assert page["items"][0]["source"] == "video"


def test_list_predictions_rejects_unknown_source_filter(app):
    with pytest.raises(UnsupportedSourceError):
        HistoryService().list_predictions(source="scanner")


def test_get_prediction_raises_not_found(app):
    with pytest.raises(NotFoundError) as error:
        HistoryService().get_prediction(999)
    assert error.value.code == "not_found"


def test_stats_service_aggregates(app, predictor, image_bytes):
    _seed(predictor, image_bytes)
    stats = StatsService().get_stats()

    assert stats["total"] == 3
    assert stats["mean_confidence"] == pytest.approx(0.9)
    assert stats["by_label"] == [{"label": "manzana", "count": 3}]
    assert {item["source"] for item in stats["by_source"]} == {"camera", "upload", "video"}
