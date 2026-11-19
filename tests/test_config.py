import pytest

from app import create_app
from app.config import normalize_database_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("postgresql://u:p@db:5432/fruits", "postgresql+psycopg://u:p@db:5432/fruits"),
        ("postgres://u:p@db:5432/fruits", "postgresql+psycopg://u:p@db:5432/fruits"),
        ("postgresql+psycopg://u:p@db:5432/fruits", "postgresql+psycopg://u:p@db:5432/fruits"),
        ("sqlite:///local.db", "sqlite:///local.db"),
    ],
)
def test_normalize_database_url(url, expected):
    assert normalize_database_url(url) == expected


def test_create_app_requires_database_url():
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        create_app({"SQLALCHEMY_DATABASE_URI": None})


def test_create_app_accepts_overrides(tmp_path):
    app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'app.db'}", "TESTING": True})
    assert app.config["TESTING"] is True
    assert "init-db" in app.cli.commands
