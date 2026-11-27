"""JSON error handlers for the API.

Requests under ``/api/`` always get the ``{"error": {...}}`` envelope. Other
routes (the web UI, M7) keep Flask's default HTML error pages.
"""

import logging

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException, InternalServerError

from app.api.v1.schemas import error_payload
from app.core.errors import (
    InvalidImageError,
    ModelUnavailableError,
    NotFoundError,
    ServiceError,
    UnsupportedImageTypeError,
    UnsupportedSourceError,
    ValidationError,
)

logger = logging.getLogger(__name__)

_ERROR_STATUSES = (
    (UnsupportedSourceError, 422),
    (UnsupportedImageTypeError, 415),
    (InvalidImageError, 422),
    (NotFoundError, 404),
    (ModelUnavailableError, 503),
    (ValidationError, 422),
)

_HTTP_CODES = {
    400: "bad_request",
    404: "not_found",
    405: "method_not_allowed",
    413: "payload_too_large",
    415: "unsupported_media_type",
}

# Werkzeug's default descriptions are in English; the API answers in Spanish.
_HTTP_MESSAGES = {
    400: "Solicitud inválida.",
    404: "El recurso solicitado no existe.",
    405: "Método no permitido para esta ruta.",
    413: "El archivo supera el tamaño máximo permitido.",
    415: "Tipo de contenido no soportado.",
}
API_PREFIX = "/api/"


def _is_api_request() -> bool:
    return request.path.startswith(API_PREFIX)


def status_for(error: ServiceError) -> int:
    """Map a domain error to its HTTP status."""
    for error_type, status in _ERROR_STATUSES:
        if isinstance(error, error_type):
            return status
    return 400


def register_error_handlers(app: Flask) -> None:
    """Register handlers that always answer with the JSON error envelope."""

    @app.errorhandler(ServiceError)
    def handle_service_error(error: ServiceError):
        return jsonify(error_payload(error.code, error.message, error.details)), status_for(error)

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        if not _is_api_request():
            return error
        code = _HTTP_CODES.get(error.code, f"http_{error.code}")
        # Keep custom descriptions (abort(415, description=...)); translate Werkzeug defaults.
        default_description = type(error).description
        message = error.description
        if message == default_description:
            message = _HTTP_MESSAGES.get(error.code, message)
        return jsonify(error_payload(code, message, None)), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        logger.exception("Unhandled error: %s", error)
        if not _is_api_request():
            return InternalServerError()
        return jsonify(error_payload("internal_error", "Error interno del servidor.", None)), 500
