"""Helpers that build the services with the objects loaded in ``create_app``."""

from flask import current_app

from app.services import ModelInfoService


def get_predictor():
    """Return the predictor loaded at startup (or ``None``)."""
    return current_app.extensions.get("predictor")


def get_model_info_service() -> ModelInfoService:
    """Build the model information service with the app configuration."""
    return ModelInfoService(
        get_predictor(),
        metrics_path=current_app.config.get("MODEL_METRICS_FILE"),
        artifacts_dir=current_app.extensions.get("model_artifacts_dir"),
    )


def get_model_version_id() -> int | None:
    """Register (once per process) and return the active model version id."""
    version_id = current_app.extensions.get("model_version_id")
    if version_id is None:
        version_id = get_model_info_service().ensure_active_version()
        current_app.extensions["model_version_id"] = version_id
    return version_id
