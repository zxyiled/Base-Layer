from app.repositories import app_log_repository


def test_create_normalizes_level_and_persists_context(app):
    created = app_log_repository.create(
        level="warning", logger="app.test", message="algo", context={"item": 1}
    )
    assert created.level == "WARNING"
    assert created.context == {"item": 1}


def test_list_filters_by_level_and_paginates(app):
    app_log_repository.create(level="INFO", logger="app.test", message="uno")
    app_log_repository.create(level="ERROR", logger="app.test", message="dos")
    app_log_repository.create(level="ERROR", logger="app.test", message="tres")

    errors = app_log_repository.list_paginated(level="error", page=1, per_page=1)
    assert errors["total"] == 2
    assert errors["pages"] == 2
    assert len(errors["items"]) == 1
    assert errors["items"][0].level == "ERROR"

    all_logs = app_log_repository.list_paginated(page=1, per_page=10)
    assert all_logs["total"] == 3
    assert [item.message for item in all_logs["items"]] == ["tres", "dos", "uno"]
