import json

import pytest
import torch
from PIL import Image

from app.ml.model_factory import build_model
from app.ml.predictor import LABELS_FILE, PREPROCESSING_FILE, WEIGHTS_FILE, Predictor
from app.ml.preprocessing import get_preprocessing_params

LABELS = ["fresa", "limon", "uva", "pera"]


@pytest.fixture
def artifacts_dir(tmp_path):
    torch.manual_seed(0)
    torch.save(build_model(num_classes=len(LABELS)).state_dict(), tmp_path / WEIGHTS_FILE)
    (tmp_path / LABELS_FILE).write_text(json.dumps(LABELS), encoding="utf-8")
    (tmp_path / PREPROCESSING_FILE).write_text(json.dumps(get_preprocessing_params()), encoding="utf-8")
    return tmp_path


def test_predict_returns_label_confidence_and_top3(artifacts_dir):
    result = Predictor.from_artifacts(artifacts_dir).predict(Image.new("RGB", (100, 100), (250, 220, 0)))
    assert set(result) == {"label", "confidence", "top3"}
    assert result["label"] in LABELS
    assert 0.0 <= result["confidence"] <= 1.0
    assert len(result["top3"]) == 3
    confidences = [item["confidence"] for item in result["top3"]]
    assert confidences == sorted(confidences, reverse=True)
    assert result["top3"][0] == {"label": result["label"], "confidence": result["confidence"]}
    assert sum(confidences) <= 1.0 + 1e-6


def test_predict_is_deterministic(artifacts_dir):
    predictor = Predictor.from_artifacts(artifacts_dir)
    image = Image.effect_noise((100, 100), 50).convert("RGB")
    assert predictor.predict(image) == predictor.predict(image)


def test_missing_artifact_raises_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="model.pt"):
        Predictor.from_artifacts(tmp_path)
