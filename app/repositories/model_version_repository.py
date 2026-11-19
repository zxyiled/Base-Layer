"""Database access for model versions."""

from typing import Any

from app.extensions import db
from app.models import ModelVersion


def create(
    name: str,
    architecture: str,
    labels: list[str],
    artifact_path: str | None = None,
    is_active: bool = False,
) -> ModelVersion:
    """Insert a model version and optionally make it the active one."""
    if is_active:
        _deactivate_all()
    model_version = ModelVersion(
        name=name,
        architecture=architecture,
        artifact_path=artifact_path,
        labels=labels,
        is_active=is_active,
    )
    db.session.add(model_version)
    db.session.commit()
    db.session.refresh(model_version)
    return model_version


def get_by_id(model_version_id: int) -> ModelVersion | None:
    """Return one model version or ``None``."""
    return db.session.get(ModelVersion, model_version_id)


def get_by_name(name: str) -> ModelVersion | None:
    """Return one model version by its unique name, if any."""
    statement = db.select(ModelVersion).where(ModelVersion.name == name)
    return db.session.scalar(statement)


def get_or_create_active(
    name: str,
    architecture: str,
    labels: list[str],
    artifact_path: str | None = None,
) -> ModelVersion:
    """Return the model version ``name``, creating or activating it if needed."""
    existing = get_by_name(name)
    if existing is not None:
        return existing if existing.is_active else activate(existing.id)
    return create(
        name=name,
        architecture=architecture,
        labels=labels,
        artifact_path=artifact_path,
        is_active=True,
    )


def get_active() -> ModelVersion | None:
    """Return the active model version, if any."""
    statement = (
        db.select(ModelVersion)
        .where(ModelVersion.is_active.is_(True))
        .order_by(ModelVersion.created_at.desc())
        .limit(1)
    )
    return db.session.scalar(statement)


def list_all() -> list[ModelVersion]:
    """Return every model version, newest first."""
    statement = db.select(ModelVersion).order_by(ModelVersion.created_at.desc(), ModelVersion.id.desc())
    return list(db.session.scalars(statement).all())


def activate(model_version_id: int) -> ModelVersion | None:
    """Make one model version active and deactivate the rest."""
    model_version = db.session.get(ModelVersion, model_version_id)
    if model_version is None:
        return None
    _deactivate_all()
    model_version.is_active = True
    db.session.commit()
    db.session.refresh(model_version)
    return model_version


def _deactivate_all() -> None:
    db.session.execute(db.update(ModelVersion).values(is_active=False))
