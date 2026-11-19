"""Describe the loaded model and register it as a model version."""

import json
import logging
from pathlib import Path
from typing import Any

from app.repositories import model_version_repository

logger = logging.getLogger(__name__)

DEFAULT_METRICS_FILE = Path(__file__).resolve().parents[2] / "ml_training" / "reports" / "metrics.json"

_SUMMARY_FIELDS = (
    "status",
    "samples",
    "accuracy",
    "macro_precision",
    "macro_recall",
    "macro_f1",
    "per_class",
    "confusion_matrix",
)


def _load_metrics(metrics_path: Path | str | None) -> dict[str, Any] | None:
    """Load the evaluation report and summarize it, or return ``None``."""
    if not metrics_path:
        return None
    path = Path(metrics_path)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read the metrics report %s: %s", path, exc)
        return None

    official = data.get("official_test")
    return {
        "official_test": (
            {field: official.get(field) for field in _SUMMARY_FIELDS} if isinstance(official, dict) else None
        ),
        "real_test": data.get("real_test"),
    }


class ModelInfoService:
    """Expose the model metadata and its evaluation results."""

    def __init__(
        self,
        predictor: Any,
        metrics_path: Path | str | None = None,
        artifacts_dir: Path | str | None = None,
        repository: Any = model_version_repository,
    ) -> None:
        self.predictor = predictor
        self.metrics_path = DEFAULT_METRICS_FILE if metrics_path is None else metrics_path
        self.artifacts_dir = Path(artifacts_dir) if artifacts_dir else None
        self.repository = repository

    def get_info(self) -> dict[str, Any]:
        """Return architecture, classes, preprocessing, training and metrics."""
        config = getattr(self.predictor, "config", None) or {}
        labels = list(getattr(self.predictor, "labels", []) or [])
        return {
            "architecture": config.get("architecture"),
            "num_classes": len(labels),
            "labels": labels,
            "preprocessing": {
                key: config.get(key)
                for key in ("source_image_size", "image_size", "resize", "mean", "std", "color_mode")
                if key in config
            },
            "training": config.get("training"),
            "metrics": _load_metrics(self.metrics_path),
        }

    def ensure_active_version(self) -> int | None:
        """Register the loaded artifact as the active model version.

        The version name includes the artifact modification time, so re-training
        creates a new row instead of reusing an older one. Returns ``None`` when
        the artifact directory is unknown.
        """
        if self.artifacts_dir is None:
            return None
        config = getattr(self.predictor, "config", None) or {}
        labels = list(getattr(self.predictor, "labels", []) or [])
        weights = self.artifacts_dir / "model.pt"
        stamp = int(weights.stat().st_mtime) if weights.is_file() else 0
        architecture = config.get("architecture") or "unknown"
        name = f"{architecture}-{len(labels)}cls-{stamp}"
        version = self.repository.get_or_create_active(
            name=name,
            architecture=architecture,
            labels=labels,
            artifact_path=str(weights),
        )
        return version.id
