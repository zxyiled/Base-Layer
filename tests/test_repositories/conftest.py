import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app(tmp_path):
    database_uri = f"sqlite:///{tmp_path / 'test.db'}"
    app = create_app({"SQLALCHEMY_DATABASE_URI": database_uri, "TESTING": True})
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def session(app):
    return db.session
