"""Aggregate statistics over the stored predictions."""

from typing import Any

from app.repositories import prediction_repository


class StatsService:
    """Totals, per-label and per-source counts with the mean confidence."""

    def __init__(self, repository: Any = prediction_repository) -> None:
        self.repository = repository

    def get_stats(self) -> dict[str, Any]:
        """Return the aggregated statistics."""
        return self.repository.stats()
