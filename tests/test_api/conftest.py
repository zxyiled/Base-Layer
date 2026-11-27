import io

import pytest
from PIL import Image

from app import create_app
from app.extensions import db
from app.ml.preprocessing import get_preprocessing_params

LABELS = ["manzana", "pera"]


class FakePredictor:
    """Deterministic predictor injected into the app in the API tests."""

    def __init__(self) -> None:
        self.labels = list(LABELS)
        self.config = {
            **get_preprocessing_params(),
            "architecture": "fake_mobilenet",
            "num_classes": len(LABELS),
        }

    def predict(self, image) -> dict:
        return {
            "label": "manzana",
            "confidence": 0.9,
            "top3": [
                {"label": "manzana", "confidence": 0.9},
                {"label": "pera", "confidence": 0.1},
            ],
        }


@pytest.fixture
def app(tmp_path):
    app = create_app(
        {
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'api.db'}",
            "TESTING": True,
            "LOG_FILE": str(tmp_path / "app.log"),
            "MODEL_METRICS_FILE": str(tmp_path / "missing_metrics.json"),
            "MAX_CONTENT_LENGTH": 1_000_000,
        }
    )
    app.extensions["predictor"] = FakePredictor()
    app.extensions["model_version_id"] = None
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (100, 100), (200, 40, 40)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def gif_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("P", (100, 100), color=1).save(buffer, format="GIF")
    return buffer.getvalue()
