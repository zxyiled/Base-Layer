"""Routes for the browser interface."""

from flask import render_template

from app.web import web_bp


@web_bp.get("/")
def index() -> str:
    """Render the single-page classifier interface."""
    return render_template("index.html")
