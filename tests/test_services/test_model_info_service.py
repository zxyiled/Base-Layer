import json

from app.repositories import model_version_repository
from app.services.model_info_service import ModelInfoService

METRICS = {
    "official_test": {
        "status": "ok",
        "samples": 10,
        "accuracy": 0.9,
        "macro_precision": 0.91,
        "macro_recall": 0.92,
        "macro_f1": 0.93,
        "per_class": {"manzana": {"precision": 1.0}},
        "confusion_matrix": [[5, 0], [1, 4]],
        "accuracy_by_variety": {"Apple 1": {"accuracy": 1.0, "samples": 5}},
    },
    "real_test": {"status": "pendiente"},
}


def test_get_info_describes_the_loaded_model(predictor, tmp_path):
    info = ModelInfoService(predictor, metrics_path=tmp_path / "missing.json").get_info()

    assert info["architecture"] == "fake_mobilenet"
    assert info["num_classes"] == 2
    assert info["labels"] == ["manzana", "pera"]
    assert info["preprocessing"]["image_size"] == 224
    assert info["metrics"] is None


def test_get_info_summarizes_the_metrics_report(predictor, tmp_path):
    metrics_file = tmp_path / "metrics.json"
    metrics_file.write_text(json.dumps(METRICS), encoding="utf-8")

    metrics = ModelInfoService(predictor, metrics_path=metrics_file).get_info()["metrics"]

    assert metrics["official_test"]["accuracy"] == 0.9
    assert metrics["official_test"]["confusion_matrix"] == [[5, 0], [1, 4]]
    assert "accuracy_by_variety" not in metrics["official_test"]
    assert metrics["real_test"] == {"status": "pendiente"}


def test_get_info_ignores_a_broken_metrics_report(predictor, tmp_path):
    metrics_file = tmp_path / "metrics.json"
    metrics_file.write_text("{not json", encoding="utf-8")
    assert ModelInfoService(predictor, metrics_path=metrics_file).get_info()["metrics"] is None


def test_ensure_active_version_registers_and_reuses_the_artifact(app, predictor, tmp_path):
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "model.pt").write_bytes(b"fake weights")

    service = ModelInfoService(predictor, artifacts_dir=artifacts_dir)
    first_id = service.ensure_active_version()
    second_id = service.ensure_active_version()

    assert first_id is not None
    assert second_id == first_id
    active = model_version_repository.get_active()
    assert active.id == first_id
    assert active.architecture == "fake_mobilenet"
    assert active.labels == ["manzana", "pera"]
    assert active.artifact_path.endswith("model.pt")


def test_ensure_active_version_without_artifacts_dir_returns_none(app, predictor):
    assert ModelInfoService(predictor).ensure_active_version() is None
