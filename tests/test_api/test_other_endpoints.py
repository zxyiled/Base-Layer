import json

import pytest

from app import create_app
from app.extensions import db
from tests.test_api.helpers import post_image


def assert_error(response, status, code):
    assert response.status_code == status
    body = response.get_json()
    assert set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["code"] == code


def test_stats_returns_aggregates(client, image_bytes):
    post_image(client, image_bytes, source="camera")
    post_image(client, image_bytes, source="upload")

    response = client.get("/api/v1/stats")

    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] == 2
    assert body["by_label"] == [{"label": "manzana", "count": 2}]
    assert {item["source"] for item in body["by_source"]} == {"camera", "upload"}


def test_model_returns_labels_and_preprocessing(client):
    response = client.get("/api/v1/model")

    assert response.status_code == 200
    body = response.get_json()
    assert body["architecture"] == "fake_mobilenet"
    assert body["num_classes"] == 2
    assert body["labels"] == ["manzana", "pera"]
    assert body["preprocessing"]["image_size"] == 224
    assert body["metrics"] is None


def test_model_includes_the_metrics_report_when_available(app, client, tmp_path):
    metrics_file = tmp_path / "metrics.json"
    metrics_file.write_text(json.dumps({"official_test": {"accuracy": 0.99, "samples": 10}}), encoding="utf-8")
    app.config["MODEL_METRICS_FILE"] = str(metrics_file)

    body = client.get("/api/v1/model").get_json()

    assert body["metrics"]["official_test"]["accuracy"] == 0.99


def test_logs_returns_the_requested_tail(app, client):
    log_file = app.config["LOG_FILE"]
    with open(log_file, "w", encoding="utf-8") as handle:
        handle.write("2026-11-19T17:00:00Z INFO app.test: uno\n")
        handle.write("2026-11-19T17:00:01Z WARNING app.test: dos\n")

    response = client.get("/api/v1/logs?limit=1")

    assert response.status_code == 200
    entries = response.get_json()["entries"]
    assert len(entries) == 1
    assert entries[0]["level"] == "WARNING"
    assert entries[0]["message"] == "dos"


@pytest.mark.parametrize("query", ["limit=0", "limit=501", "limit=abc"])
def test_logs_rejects_invalid_limits(client, query):
    response = client.get(f"/api/v1/logs?{query}")
    assert_error(response, 422, "validation_error")


def test_health_reports_database_and_model(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok", "model": "loaded"}


def test_health_returns_503_when_the_database_is_unreachable(tmp_path):
    app = create_app(
        {
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}",
            "TESTING": True,
            "LOG_FILE": str(tmp_path / "app.log"),
        }
    )
    try:
        response = app.test_client().get("/api/v1/health")
        assert response.status_code == 503
        assert response.get_json()["database"] == "error"
    finally:
        with app.app_context():
            db.session.remove()


def test_unknown_route_returns_json_404(client):
    response = client.get("/api/v1/does-not-exist")
    assert_error(response, 404, "not_found")


def test_api_http_errors_are_in_spanish(client):
    not_found = client.get("/api/v1/does-not-exist").get_json()["error"]
    assert not_found["message"] == "El recurso solicitado no existe."
    response = client.delete("/api/v1/stats")
    assert_error(response, 405, "method_not_allowed")
    assert response.get_json()["error"]["message"] == "Método no permitido para esta ruta."


def test_custom_http_descriptions_are_kept(client):
    response = client.post("/api/v1/predictions", json={})
    assert "multipart/form-data" in response.get_json()["error"]["message"]


def test_routes_outside_the_api_keep_html_errors(client):
    response = client.get("/pagina-que-no-existe")
    assert response.status_code == 404
    assert response.mimetype == "text/html"
