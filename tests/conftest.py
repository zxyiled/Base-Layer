"""Shared test setup.

Imported by pytest before any test module (and before app.config), so the app
never writes test logs into the repository's logs/ folder.
"""

import os
import tempfile
from pathlib import Path

os.environ["LOG_FILE"] = str(Path(tempfile.mkdtemp(prefix="fruits-tests-")) / "app.log")
