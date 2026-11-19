"""Prediction endpoints: create one prediction and browse the history."""

from flask import abort, jsonify, request

from app.api.v1 import api_v1_bp
from app.api.v1.dependencies import get_model_version_id, get_predictor
from app.api.v1.schemas import parse_datetime, parse_int, parse_source
from app.core.errors import ModelUnavailableError, ValidationError
from app.repositories.pagination import MAX_PER_PAGE
from app.services import HistoryService, PredictionService


@api_v1_bp.post("/predictions")
def create_prediction():
    """Classify an uploaded image and store the result (201)."""
    if not (request.mimetype or "").startswith("multipart/form-data"):
        abort(415, description="La predicción requiere multipart/form-data con el campo 'image'.")

    image_file = request.files.get("image")
    if image_file is None:
        raise ValidationError("Falta el archivo 'image'.", {"field": "image"})
    image_bytes = image_file.read()
    if not image_bytes:
        raise ValidationError("El archivo 'image' está vacío.", {"field": "image"})

    source = (request.form.get("source") or "upload").strip() or "upload"
    predictor = get_predictor()
    if predictor is None:
        raise ModelUnavailableError("El modelo no está cargado.")

    service = PredictionService(predictor, model_version_id=get_model_version_id())
    result = service.predict(image_bytes, source=source, original_filename=image_file.filename)
    return jsonify(result), 201


@api_v1_bp.get("/predictions")
def list_predictions():
    """Return a filtered, paginated page of predictions."""
    page = parse_int(request.args.get("page"), "page", 1)
    per_page = parse_int(request.args.get("per_page"), "per_page", 20, maximum=MAX_PER_PAGE)
    source = parse_source(request.args.get("source"))
    date_from = parse_datetime(request.args.get("date_from"), "date_from")
    date_to = parse_datetime(request.args.get("date_to"), "date_to")
    if date_from and date_to and date_from > date_to:
        raise ValidationError("'date_from' no puede ser posterior a 'date_to'.")

    history = HistoryService().list_predictions(
        page=page,
        per_page=per_page,
        label=request.args.get("label"),
        source=source,
        date_from=date_from,
        date_to=date_to,
    )
    return jsonify(history), 200


@api_v1_bp.get("/predictions/<int:prediction_id>")
def get_prediction(prediction_id: int):
    """Return one prediction or a JSON 404."""
    return jsonify(HistoryService().get_prediction(prediction_id)), 200
