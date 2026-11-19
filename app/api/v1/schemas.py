"""Small helpers to validate query parameters and build error payloads."""

from datetime import datetime, timezone
from typing import Any

from app.core.errors import UnsupportedSourceError, ValidationError
from app.models.prediction import SOURCES


def error_payload(code: str, message: str, details: Any = None) -> dict[str, Any]:
    """Return the error envelope used by every endpoint."""
    return {"error": {"code": code, "message": message, "details": details}}


def parse_int(value: str | None, field: str, default: int, minimum: int = 1, maximum: int | None = None) -> int:
    """Parse a bounded integer query parameter or raise ``ValidationError``."""
    if value is None or value == "":
        return default
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"El parámetro '{field}' debe ser un entero.", {"field": field}) from exc
    if number < minimum:
        raise ValidationError(f"El parámetro '{field}' debe ser mayor o igual que {minimum}.", {"field": field})
    if maximum is not None and number > maximum:
        raise ValidationError(f"El parámetro '{field}' no puede superar {maximum}.", {"field": field})
    return number


def parse_datetime(value: str | None, field: str) -> datetime | None:
    """Parse an ISO 8601 query parameter into an aware UTC datetime."""
    if value is None or value == "":
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(
            f"El parámetro '{field}' debe tener formato ISO 8601.",
            {"field": field, "value": value},
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_source(value: str | None) -> str | None:
    """Validate an optional ``source`` filter or raise ``UnsupportedSourceError``."""
    if value is None or value == "":
        return None
    if value not in SOURCES:
        raise UnsupportedSourceError(
            f"Fuente no válida: {value!r}. Valores permitidos: {', '.join(SOURCES)}."
        )
    return value
