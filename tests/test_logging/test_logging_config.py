import logging
import re

from app import create_app
from app.core.logging_config import configure_logging

LINE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z INFO app\.test: hola$")


def _own_handlers() -> list[logging.Handler]:
    return [h for h in logging.getLogger().handlers if getattr(h, "_fruits_app_handler", False)]


def _flush() -> None:
    for handler in _own_handlers():
        handler.flush()


def test_writes_timestamp_level_and_module_to_file(tmp_path):
    log_file = tmp_path / "nested" / "logs" / "app.log"
    configure_logging(log_file)
    logging.getLogger("app.test").info("hola")
    _flush()
    assert log_file.parent.is_dir()
    assert LINE_PATTERN.match(log_file.read_text(encoding="utf-8").strip())


def test_installs_console_and_file_handler_without_duplicates(tmp_path):
    configure_logging(tmp_path / "app.log")
    configure_logging(tmp_path / "app.log")
    handler_types = sorted(type(h).__name__ for h in _own_handlers())
    assert handler_types == ["RotatingFileHandler", "StreamHandler"]


def test_respects_level(tmp_path):
    log_file = tmp_path / "app.log"
    configure_logging(log_file, level="warning")
    logging.getLogger("app.test").info("oculto")
    logging.getLogger("app.test").warning("visible")
    _flush()
    content = log_file.read_text(encoding="utf-8")
    assert "visible" in content and "oculto" not in content


def test_rotates_and_keeps_backup_count(tmp_path):
    log_file = tmp_path / "app.log"
    configure_logging(log_file, max_bytes=200, backup_count=2)
    for number in range(50):
        logging.getLogger("app.test").info("mensaje de relleno %d", number)
    _flush()
    assert (tmp_path / "app.log.1").is_file()
    assert (tmp_path / "app.log.2").is_file()
    assert not (tmp_path / "app.log.3").exists()


def test_create_app_configures_logging_from_config(tmp_path):
    log_file = tmp_path / "from_app.log"
    create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://", "LOG_FILE": str(log_file), "TESTING": True})
    logging.getLogger("app.test").info("desde la app")
    _flush()
    assert "desde la app" in log_file.read_text(encoding="utf-8")


def test_file_output_has_no_ansi_colors(tmp_path):
    log_file = tmp_path / "app.log"
    configure_logging(log_file)
    logging.getLogger("werkzeug").info("\x1b[33mGET / HTTP/1.1\x1b[0m")
    _flush()
    content = log_file.read_text(encoding="utf-8")
    assert "\x1b[" not in content and "GET / HTTP/1.1" in content
