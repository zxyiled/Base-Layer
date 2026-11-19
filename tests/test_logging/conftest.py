import logging

import pytest


@pytest.fixture(autouse=True)
def restore_root_logger():
    """Undo the handlers and level a test installs on the root logger."""
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    yield
    for handler in list(root.handlers):
        if handler not in handlers:
            root.removeHandler(handler)
            handler.close()
    for handler in handlers:
        if handler not in root.handlers:
            root.addHandler(handler)
    root.setLevel(level)
