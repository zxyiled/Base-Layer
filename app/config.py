"""Application configuration read from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()


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
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
