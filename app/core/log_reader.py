"""Read the latest entries of the application log file (for the API and the UI)."""

import os
import re
from pathlib import Path
from typing import Any

MAX_LIMIT = 500
_MAX_WINDOW_LINES = 100_000
_CHUNK_SIZE = 8192
_ENTRY_PATTERN = re.compile(r"^(\S+Z) (DEBUG|INFO|WARNING|ERROR|CRITICAL) (\S+): (.*)$")


def tail_lines(path: Path | str, limit: int) -> list[str]:
    """Return the last ``limit`` lines of ``path``, reading from the end of the file."""
    path = Path(path)
    if limit <= 0 or not path.is_file():
        return []
    with path.open("rb") as file:
        file.seek(0, os.SEEK_END)
        position = file.tell()
        data = b""
        while position > 0 and data.count(b"\n") <= limit:
            step = min(_CHUNK_SIZE, position)
            position -= step
            file.seek(position)
            data = file.read(step) + data
    lines = data.decode("utf-8", errors="replace").splitlines()
    return lines[-limit:]


def parse_entries(lines: list[str]) -> list[dict[str, Any]]:
    """Group lines into log entries; lines that are not a new entry (tracebacks) join the previous one."""
    entries: list[dict[str, Any]] = []
    for line in lines:
        match = _ENTRY_PATTERN.match(line)
        if match:
            timestamp, level, logger, message = match.groups()
            entries.append({"timestamp": timestamp, "level": level, "logger": logger, "message": message})
        elif entries:
            entries[-1]["message"] += "\n" + line
        else:
            entries.append({"timestamp": None, "level": None, "logger": None, "message": line})
    return entries


def read_last_entries(path: Path | str, limit: int = 100) -> list[dict[str, Any]]:
    """Return up to ``limit`` (max ``MAX_LIMIT``) latest complete log entries, oldest first.

    The read window grows until it holds ``limit`` entries, so multi-line entries
    (tracebacks) keep their header line. Only the current file is read, not the
    rotated backups. A missing file returns [].
    """
    limit = max(0, min(int(limit), MAX_LIMIT))
    if limit == 0:
        return []
    window = limit * 4
    while True:
        lines = tail_lines(path, window)
        entries = parse_entries(lines)
        whole_file = len(lines) < window
        if not whole_file and entries and entries[0]["level"] is None:
            entries = entries[1:]  # the window started in the middle of an entry
        if whole_file or len(entries) >= limit or window >= _MAX_WINDOW_LINES:
            return entries[-limit:]
        window = min(window * 4, _MAX_WINDOW_LINES)
