"""Application configuration read from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[1]


def normalize_database_url(url: str) -> str:
    """Return a SQLAlchemy URL that uses the installed psycopg 3 driver.

    SQLAlchemy maps ``postgresql://`` to psycopg2, but the project installs
    psycopg 3, whose SQLAlchemy dialect is ``postgresql+psycopg``.
    """
    for prefix in ("postgresql+psycopg://", "sqlite://", "sqlite+pysqlite://"):
        if url.startswith(prefix):
            return url
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def get_database_url() -> str | None:
    """Read ``DATABASE_URL`` and normalize it for SQLAlchemy."""
    url = os.getenv("DATABASE_URL")
    return normalize_database_url(url) if url else None


class Config:
    """Default configuration used by the application factory."""

    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = get_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    MODEL_ARTIFACTS_DIR = os.getenv("MODEL_ARTIFACTS_DIR")
    MODEL_METRICS_FILE = os.getenv("MODEL_METRICS_FILE")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", str(ROOT_DIR / "logs" / "app.log"))
    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "1000000"))
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
