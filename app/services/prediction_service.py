"""Orchestrates one prediction: validate, decode, infer, persist and log."""

import io
import logging
import time
from typing import Any

from PIL import Image, UnidentifiedImageError

from app.core.errors import InvalidImageError, ModelUnavailableError, UnsupportedSourceError
from app.models.prediction import SOURCES
from app.repositories import prediction_repository

logger = logging.getLogger(__name__)


def decode_image(image_bytes: bytes) -> Image.Image:
    """Decode image bytes with Pillow, rejecting corrupt or non-image data.

    The extension and ``Content-Type`` are never trusted: only a successful
    ``Image.open``/``load`` proves the bytes are an image.
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.load()
            return image.copy()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise InvalidImageError("El archivo no es una imagen válida o está dañado.") from exc


class PredictionService:
    """Classify one image and store the result through the repository layer."""

    def __init__(
        self,
        predictor: Any,
        model_version_id: int | None = None,
        repository: Any = prediction_repository,
    ) -> None:
        self.predictor = predictor
        self.model_version_id = model_version_id
        self.repository = repository

    def predict(
        self,
        image_bytes: bytes,
        source: str = "upload",
        original_filename: str | None = None,
    ) -> dict[str, Any]:
        """Return the persisted prediction as a dict."""
        source = source or "upload"
        if source not in SOURCES:
            raise UnsupportedSourceError(
                f"Fuente no válida: {source!r}. Valores permitidos: {', '.join(SOURCES)}."
            )
        if self.predictor is None:
            raise ModelUnavailableError("El modelo no está cargado.")
        if not image_bytes:
            raise InvalidImageError("La imagen está vacía.")

        image = decode_image(image_bytes)
        started = time.perf_counter()
        result = self.predictor.predict(image)
        inference_ms = (time.perf_counter() - started) * 1000

        prediction = self.repository.create(
            source=source,
            predicted_label=result["label"],
            confidence=result["confidence"],
            top3=result["top3"],
            original_filename=original_filename,
            file_size_bytes=len(image_bytes),
            inference_ms=round(inference_ms, 3),
            model_version_id=self.model_version_id,
        )
        logger.info(
            "Prediction id=%s label=%s confidence=%.4f source=%s file=%s size=%d inference_ms=%.2f",
            prediction.id,
            prediction.predicted_label,
            prediction.confidence,
            source,
            original_filename,
            len(image_bytes),
            prediction.inference_ms,
        )
        return prediction.as_dict()
