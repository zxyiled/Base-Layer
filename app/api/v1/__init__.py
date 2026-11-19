"""Versioned REST API (``/api/v1``)."""

from flask import Blueprint

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

from app.api.v1 import health, logs, model, predictions, stats  # noqa: E402,F401

__all__ = ["api_v1_bp"]
