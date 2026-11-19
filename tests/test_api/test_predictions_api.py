import io

import pytest

from tests.test_api.helpers import post_image


def assert_error(response, status, code):
    assert response.status_code == status
    body = response.get_json()
    assert set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["code"] == code


def test_create_prediction_returns_201_and_persists(client, image_bytes):
    response = post_image(client, image_bytes, source="camera", filename="manzana.png")

    assert response.status_code == 201
    body = response.get_json()
    assert body["label"] == "manzana"
    assert body["confidence"] == pytest.approx(0.9)
    assert body["source"] == "camera"
    assert body["original_filename"] == "manzana.png"
    assert body["file_size_bytes"] == len(image_bytes)
    assert body["model_version_id"] is not None
    assert body["top3"][0]["label"] == "manzana"
    assert body["created_at"].endswith("+00:00")

    detail = client.get(f"/api/v1/predictions/{body['id']}")
    assert detail.status_code == 200
    assert detail.get_json() == body


def test_create_prediction_defaults_to_upload(client, image_bytes):
    response = post_image(client, image_bytes)
    assert response.status_code == 201
    assert response.get_json()["source"] == "upload"
    assert response.get_json()["original_filename"] == "fruta.png"


@pytest.mark.parametrize("source", ["camera", "upload", "video"])
def test_create_prediction_accepts_every_source(client, image_bytes, source):
    response = post_image(client, image_bytes, source=source)
    assert response.status_code == 201
    assert response.get_json()["source"] == source


def test_create_prediction_rejects_unknown_source(client, image_bytes):
    response = post_image(client, image_bytes, source="scanner")
    assert_error(response, 422, "unsupported_source")


def test_create_prediction_requires_the_image_field(client):
    response = client.post(
        "/api/v1/predictions",
        data={"source": "upload"},
        content_type="multipart/form-data",
    )
    assert_error(response, 422, "validation_error")


def test_create_prediction_rejects_an_empty_file(client):
    response = post_image(client, b"")
    assert_error(response, 422, "validation_error")


def test_create_prediction_rejects_a_corrupt_image(client):
    response = post_image(client, b"\x89PNG\r\n\x1a\n corrupted")
    assert_error(response, 422, "invalid_image")


def test_create_prediction_rejects_a_non_image(client):
    response = post_image(client, b"this is just text")
    assert_error(response, 422, "invalid_image")


def test_create_prediction_rejects_an_unsupported_format(client, gif_bytes):
    response = post_image(client, gif_bytes, filename="fruta.gif", content_type="image/gif")
    assert_error(response, 415, "unsupported_media_type")


def test_create_prediction_requires_multipart(client):
    response = client.post("/api/v1/predictions", json={"source": "upload"})
    assert_error(response, 415, "unsupported_media_type")


def test_create_prediction_rejects_an_oversized_file(app, client, image_bytes):
    app.config["MAX_CONTENT_LENGTH"] = 100
    response = post_image(client, image_bytes)
    assert_error(response, 413, "payload_too_large")


def test_create_prediction_fails_when_the_model_is_missing(app, client, image_bytes):
    app.extensions["predictor"] = None
    response = post_image(client, image_bytes)
    assert_error(response, 503, "model_unavailable")


def test_list_predictions_is_paginated(client, image_bytes):
    for _ in range(3):
        assert post_image(client, image_bytes).status_code == 201

    response = client.get("/api/v1/predictions?page=1&per_page=2")

    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] == 3
    assert body["pages"] == 2
    assert body["page"] == 1
    assert body["per_page"] == 2
    assert len(body["items"]) == 2


def test_list_predictions_filters_by_source(client, image_bytes):
    post_image(client, image_bytes, source="camera")
    post_image(client, image_bytes, source="video")

    body = client.get("/api/v1/predictions?source=video").get_json()

    assert body["total"] == 1
    assert body["items"][0]["source"] == "video"


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page=abc",
        "per_page=0",
        "per_page=101",
        "source=scanner",
        "date_from=no-es-fecha",
        "date_from=2026-11-02T00:00:00Z&date_to=2026-11-01T00:00:00Z",
    ],
)
def test_list_predictions_rejects_invalid_query_parameters(client, query):
    response = client.get(f"/api/v1/predictions?{query}")
    assert_error(response, 422, "validation_error" if "source" not in query else "unsupported_source")


def test_list_predictions_accepts_a_date_filter(client, image_bytes):
    post_image(client, image_bytes)
    response = client.get("/api/v1/predictions?date_from=2000-01-01T00:00:00Z")
    assert response.status_code == 200
    assert response.get_json()["total"] == 1


def test_get_unknown_prediction_returns_json_404(client):
    response = client.get("/api/v1/predictions/999")
    assert_error(response, 404, "not_found")


def test_predictions_history_contains_seeded_rows(client, image_bytes):
    post_image(client, image_bytes, source="upload")
    body = client.get("/api/v1/predictions").get_json()
    assert body["items"][0]["inference_ms"] is not None
    assert body["items"][0]["file_size_bytes"] == len(image_bytes)
