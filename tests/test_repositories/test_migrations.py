from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask_migrate import upgrade

from app import create_app
from app.extensions import db


def test_migrations_build_the_same_schema_as_the_models(tmp_path):
    app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'migrated.db'}", "TESTING": True})
    with app.app_context():
        upgrade()
        with db.engine.connect() as connection:
            differences = compare_metadata(MigrationContext.configure(connection), db.metadata)
        assert differences == []
        assert {"predictions", "model_versions", "app_logs", "alembic_version"} <= set(db.inspect(db.engine).get_table_names())
