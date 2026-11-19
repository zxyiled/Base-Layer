"""Application factory."""

from typing import Any

from flask import Flask

from app.api.v1 import api_v1_bp
from app.api.v1.errors import register_error_handlers
from app.config import Config
from app.core.logging_config import configure_logging
from app.extensions import db, migrate
from app.ml.predictor import DEFAULT_ARTIFACTS_DIR, Predictor


def create_app(overrides: dict[str, Any] | None = None) -> Flask:
    """Build the Flask application, its extensions and the loaded model.

    The model artifact is loaded once here and shared through
    ``app.extensions["predictor"]``. The API and web routes (M5 and M7) extend
    this factory.
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    configure_logging(
        app.config["LOG_FILE"],
        level=app.config["LOG_LEVEL"],
        max_bytes=app.config["LOG_MAX_BYTES"],
        backup_count=app.config["LOG_BACKUP_COUNT"],
    )

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and configure it.")

    db.init_app(app)
    migrate.init_app(app, db)
    register_error_handlers(app)
    app.register_blueprint(api_v1_bp)

    with app.app_context():
        from app import models  # noqa: F401  (register the models' metadata)

    artifacts_dir = app.config.get("MODEL_ARTIFACTS_DIR") or DEFAULT_ARTIFACTS_DIR
    try:
        predictor = Predictor.from_artifacts(artifacts_dir)
    except FileNotFoundError as exc:
        app.logger.warning("Model artifact not loaded: %s", exc)
        predictor = None
    app.extensions["predictor"] = predictor
    app.extensions["model_artifacts_dir"] = str(artifacts_dir)
    app.extensions["model_version_id"] = None

    return app
