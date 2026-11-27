"""Tests for the web interface served at /."""

import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    app = create_app(
        {
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'web.db'}",
            "TESTING": True,
            "LOG_FILE": str(tmp_path / "app.log"),
            "MODEL_ARTIFACTS_DIR": str(tmp_path / "missing-artifacts"),
            "MODEL_METRICS_FILE": str(tmp_path / "missing_metrics.json"),
        }
    )
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_web_blueprint_is_registered(app) -> None:
    assert "web" in app.blueprints


def test_index_renders_the_spanish_interface(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    html = response.get_data(as_text=True)
    expected_fragments = [
        '<html lang="es">',
        "Saltar al contenido principal",
        "Vista previa de la cámara",
        'id="camera-preview"',
        'id="camera-start"',
        'id="image-upload"',
        'id="result"',
        "Historial",
        "Estadísticas",
        "Información del modelo",
        "Registros",
        "/static/vendor/chart.umd.min.js",
        '<select id="history-label">',
    ]
    for fragment in expected_fragments:
        assert fragment in html
    assert "cdn.jsdelivr.net" not in html


def test_static_assets_are_served(client) -> None:
    css = client.get("/static/css/styles.css")
    script = client.get("/static/js/app.js")

    assert css.status_code == 200
    assert "text/css" in css.content_type
    assert script.status_code == 200
    assert "javascript" in script.content_type

    source = script.get_data(as_text=True)
    assert 'const API_BASE = "/api/v1"' in source
    assert "predictions: `${API_BASE}/predictions`" in source
    assert "stats: `${API_BASE}/stats`" in source
    assert "Permiso de cámara denegado" in source
    assert "function sampleFrame" in source
    assert "drawToCanvas" not in source
    assert "captureVideoFrame" not in source
    assert "function fillLabelFilter" in source
    assert "function formatRealTest" in source


def test_chart_js_is_served_locally(client) -> None:
    response = client.get("/static/vendor/chart.umd.min.js")

    assert response.status_code == 200
    assert "javascript" in response.content_type
    assert "Chart.js v4.6.1" in response.get_data(as_text=True)
