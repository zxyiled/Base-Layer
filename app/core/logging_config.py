"""Central logging configuration: console and rotating file (logs/app.log).

Every record uses ``<UTC timestamp> <LEVEL> <logger>: <message>``, for example
``2026-11-19T17:00:00Z INFO app.ml.predictor: Model loaded``. Never log image bytes.
"""

import logging
import re
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DEFAULT_MAX_BYTES = 1_000_000
DEFAULT_BACKUP_COUNT = 5

# Marks the handlers installed here so a second call replaces them instead of duplicating.
_HANDLER_FLAG = "_fruits_app_handler"
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


class PlainFormatter(logging.Formatter):
    """Formatter that removes ANSI color codes (werkzeug colors its request lines)."""

    def format(self, record: logging.LogRecord) -> str:
        return _ANSI_ESCAPE.sub("", super().format(record))


def build_formatter(plain: bool = False) -> logging.Formatter:
    """Formatter with timestamp (UTC), level and module; ``plain`` strips colors for files."""
    formatter = (PlainFormatter if plain else logging.Formatter)(LOG_FORMAT, datefmt=DATE_FORMAT)
    formatter.converter = time.gmtime
    return formatter


def _remove_own_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        if getattr(handler, _HANDLER_FLAG, False):
            logger.removeHandler(handler)
            handler.close()


def configure_logging(
    log_file: Path | str,
    level: str = "INFO",
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> None:
    """Send the root logger to the console and to a rotating file.

    Creates the log folder if needed. Calling it again replaces the previous
    handlers, so the app factory can run several times (tests) without duplicates.
    """
    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    console_handler = logging.StreamHandler(sys.stderr)
    file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    root = logging.getLogger()
    _remove_own_handlers(root)
    console_handler.setFormatter(build_formatter())
    file_handler.setFormatter(build_formatter(plain=True))
    for handler in (console_handler, file_handler):
        setattr(handler, _HANDLER_FLAG, True)
        root.addHandler(handler)
    root.setLevel(level.upper())
