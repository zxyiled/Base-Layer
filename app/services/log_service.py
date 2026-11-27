"""Read the latest application log entries for the API and the UI."""

from pathlib import Path
from typing import Any

from app.core.log_reader import read_last_entries


class LogService:
    """Expose the tail of ``logs/app.log`` as structured entries."""

    def __init__(self, log_file: Path | str) -> None:
        self.log_file = log_file

    def recent_entries(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return up to ``limit`` latest entries, oldest first."""
        return read_last_entries(self.log_file, limit=limit)
