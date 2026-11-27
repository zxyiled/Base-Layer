import io

import pytest
from PIL import Image

from app import create_app
from app.extensions import db
from app.ml.preprocessing import get_preprocessing_params

LABELS = ["manzana", "pera"]


class FakePredictor:
    """Deterministic stand-in for ``app.ml.predictor.Predictor``."""

    def __init__(self) -> None:
        self.labels = list(LABELS)
        self.calls = 0
        self.config = {
            **get_preprocessing_params(),
            "architecture": "fake_mobilenet",
            "num_classes": len(LABELS),
        }

    def predict(self, image) -> dict:
        self.calls += 1
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
    app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}", "TESTING": True})
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def predictor() -> FakePredictor:
    return FakePredictor()


@pytest.fixture
def image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (100, 100), (220, 40, 40)).save(buffer, format="PNG")
    return buffer.getvalue()
