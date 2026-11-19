"""JSON error handlers shared by every API endpoint."""

import logging

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

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
        code = _HTTP_CODES.get(error.code, f"http_{error.code}")
        return jsonify(error_payload(code, error.description, None)), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        logger.exception("Unhandled error: %s", error)
        return jsonify(error_payload("internal_error", "Error interno del servidor.", None)), 500
