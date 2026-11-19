"""Model information endpoint."""

from flask import jsonify

from app.api.v1 import api_v1_bp
from app.api.v1.dependencies import get_model_info_service, get_predictor
from app.core.errors import ModelUnavailableError


@api_v1_bp.get("/model")
def get_model():
    """Return architecture, classes, preprocessing and the evaluation metrics."""
    if get_predictor() is None:
        raise ModelUnavailableError("El modelo no está cargado.")
    return jsonify(get_model_info_service().get_info()), 200
