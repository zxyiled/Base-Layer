"""Health check for the application, the database and the model."""

import logging

from flask import jsonify
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1 import api_v1_bp
from app.api.v1.dependencies import get_predictor
from app.extensions import db

logger = logging.getLogger(__name__)


@api_v1_bp.get("/health")
def health():
    """Return 200 when the database answers; 503 otherwise."""
    try:
        db.session.execute(db.text("SELECT 1"))
        database_ok = True
    except SQLAlchemyError as exc:
        logger.warning("Health check failed: %s", exc)
        db.session.rollback()
        database_ok = False

    payload = {
        "status": "ok" if database_ok else "degraded",
        "database": "ok" if database_ok else "error",
        "model": "loaded" if get_predictor() is not None else "unavailable",
    }
    return jsonify(payload), 200 if database_ok else 503
