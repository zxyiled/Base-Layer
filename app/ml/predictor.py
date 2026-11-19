"""Loads the trained artifact once and predicts the fruit in an image."""

import json
import logging
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from torch import nn

from app.ml.model_factory import build_model
from app.ml.preprocessing import preprocess_image

logger = logging.getLogger(__name__)

WEIGHTS_FILE = "model.pt"
LABELS_FILE = "labels.json"
PREPROCESSING_FILE = "preprocessing.json"
DEFAULT_ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"


class Predictor:
    """Wraps the model, its labels and its preprocessing parameters."""

    def __init__(self, model: nn.Module, labels: list[str], config: dict[str, Any]) -> None:
        self.model = model.eval()
        self.labels = labels
        self.config = config

    @classmethod
    def from_artifacts(cls, artifacts_dir: Path | str = DEFAULT_ARTIFACTS_DIR) -> "Predictor":
        """Build a predictor from ``model.pt``, ``labels.json`` and ``preprocessing.json``."""
        artifacts_dir = Path(artifacts_dir)
        paths = [artifacts_dir / name for name in (WEIGHTS_FILE, LABELS_FILE, PREPROCESSING_FILE)]
        missing = [str(path) for path in paths if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"Missing model artifact files: {', '.join(missing)}")

        labels = json.loads(paths[1].read_text(encoding="utf-8"))
        config = json.loads(paths[2].read_text(encoding="utf-8"))
        model = build_model(num_classes=len(labels), pretrained=False)
        state_dict = torch.load(paths[0], map_location="cpu", weights_only=True)
        model.load_state_dict(state_dict)
        logger.info("Model loaded from %s with %d classes", artifacts_dir, len(labels))
        return cls(model, labels, config)

    @torch.inference_mode()
    def predict_probabilities(self, batch: torch.Tensor) -> torch.Tensor:
        """Return class probabilities for an already preprocessed batch."""
        return torch.softmax(self.model(batch), dim=1)

    def predict(self, image: Image.Image) -> dict[str, Any]:
        """Predict one image: ``{label, confidence, top3: [{label, confidence}]}``."""
        probabilities = self.predict_probabilities(preprocess_image(image))[0]
        k = min(3, len(self.labels))
        values, indices = torch.topk(probabilities, k)
        top3 = [
            {"label": self.labels[index], "confidence": round(float(value), 6)}
            for value, index in zip(values.tolist(), indices.tolist())
        ]
        return {"label": top3[0]["label"], "confidence": top3[0]["confidence"], "top3": top3}
