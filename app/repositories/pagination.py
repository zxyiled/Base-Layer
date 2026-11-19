"""Shared pagination helper for the repository layer."""

from typing import Any

from app.extensions import db

DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100


def paginate(statement: Any, page: int = DEFAULT_PAGE, per_page: int = DEFAULT_PER_PAGE) -> dict[str, Any]:
    """Return one page of ``statement`` with the pagination metadata."""
    page = max(int(page), 1)
    per_page = min(max(int(per_page), 1), MAX_PER_PAGE)
    result = db.paginate(statement, page=page, per_page=per_page, error_out=False)
    return {
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "per_page": result.per_page,
        "pages": result.pages,
    }
