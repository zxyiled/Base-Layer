import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.repositories import model_version_repository


def test_create_without_active_has_no_active_model(app):
    model_version = model_version_repository.create(
        name="v1", architecture="mobilenet_v3_small", labels=["uva"]
    )
    assert model_version.is_active is False
    assert model_version_repository.get_active() is None


def test_create_active_deactivates_previous(app):
    first = model_version_repository.create(
        name="v1", architecture="mobilenet_v3_small", labels=["uva"], is_active=True
    )
    second = model_version_repository.create(
        name="v2", architecture="mobilenet_v3_small", labels=["uva"], is_active=True
    )

    db.session.refresh(first)
    assert first.is_active is False
    assert second.is_active is True
    assert model_version_repository.get_active().id == second.id


def test_activate_switches_the_active_model(app):
    first = model_version_repository.create(
        name="v1", architecture="mobilenet_v3_small", labels=["uva"], is_active=True
    )
    second = model_version_repository.create(
        name="v2", architecture="mobilenet_v3_small", labels=["uva"]
    )

    activated = model_version_repository.activate(second.id)
    assert activated is not None
    assert activated.is_active is True
    assert db.session.get(type(first), first.id).is_active is False


def test_activate_returns_none_for_unknown_id(app):
    assert model_version_repository.activate(999) is None


def test_duplicate_name_is_rejected(app):
    model_version_repository.create(name="v1", architecture="mobilenet_v3_small", labels=["uva"])
    with pytest.raises(IntegrityError):
        model_version_repository.create(
            name="v1", architecture="mobilenet_v3_small", labels=["uva"]
        )
    db.session.rollback()


def test_list_all_returns_newest_first(app):
    first = model_version_repository.create(
        name="v1", architecture="mobilenet_v3_small", labels=["uva"]
    )
    second = model_version_repository.create(
        name="v2", architecture="mobilenet_v3_small", labels=["uva"]
    )
    assert [item.id for item in model_version_repository.list_all()] == [second.id, first.id]
