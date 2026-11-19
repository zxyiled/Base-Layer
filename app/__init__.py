"""Application factory."""

from typing import Any

import click
from flask import Flask

from app.config import Config
from app.extensions import db


def create_app(overrides: dict[str, Any] | None = None) -> Flask:
    """Build the Flask application and initialize its extensions.

    Modules that need the API, services or inference (M4 and M5) extend this
    factory. Here it only wires configuration and the database.
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and configure it.")

    db.init_app(app)

    with app.app_context():
        from app import models  # noqa: F401  (register the models' metadata)

    @app.cli.command("init-db")
    def init_db() -> None:
        """Create every table declared by the models."""
        db.create_all()
        click.echo("Tablas creadas.")

    return app
