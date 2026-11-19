"""Read access to the prediction history."""

from datetime import datetime
from typing import Any

from app.core.errors import NotFoundError, UnsupportedSourceError
from app.models.prediction import SOURCES
from app.repositories import prediction_repository


class HistoryService:
    """Paginated listing and detail of stored predictions."""

    def __init__(self, repository: Any = prediction_repository) -> None:
        self.repository = repository

    def list_predictions(
        self,
        page: int = 1,
        per_page: int = 20,
        label: str | None = None,
        source: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, Any]:
        """Return one page of predictions serialized for the API."""
        if source is not None and source not in SOURCES:
            raise UnsupportedSourceError(
                f"Fuente no válida: {source!r}. Valores permitidos: {', '.join(SOURCES)}."
            )
        result = self.repository.list_paginated(
            page=page,
            per_page=per_page,
            label=label or None,
            source=source or None,
            date_from=date_from,
            date_to=date_to,
        )
        return {
            "items": [prediction.as_dict() for prediction in result["items"]],
            "total": result["total"],
            "page": result["page"],
            "per_page": result["per_page"],
            "pages": result["pages"],
        }

    def get_prediction(self, prediction_id: int) -> dict[str, Any]:
        """Return one prediction or raise ``NotFoundError``."""
        prediction = self.repository.get_by_id(prediction_id)
        if prediction is None:
            raise NotFoundError(f"No existe la predicción {prediction_id}.")
        return prediction.as_dict()
