"""Repositories: the only layer that talks to the database."""

from app.repositories import model_version_repository, prediction_repository

__all__ = ["model_version_repository", "prediction_repository"]
