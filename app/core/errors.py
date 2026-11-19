"""Domain errors raised by the service layer.

The API layer (M5) maps each ``code`` to an HTTP status and serializes it as
``{"error": {"code", "message", "details"}}``.
"""

from typing import Any


class ServiceError(Exception):
    """Base class for errors originated in the service layer."""

    code = "service_error"

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class ValidationError(ServiceError):
    """The input does not satisfy the service requirements."""

    code = "validation_error"


class UnsupportedSourceError(ValidationError):
    """``source`` is not one of the allowed values."""

    code = "unsupported_source"


class InvalidImageError(ServiceError):
    """The uploaded bytes are not a decodable image."""

    code = "invalid_image"


class NotFoundError(ServiceError):
    """The requested resource does not exist."""

    code = "not_found"


class ModelUnavailableError(ServiceError):
    """The prediction model is not loaded."""

    code = "model_unavailable"
