"""WSGI entry point used by Flask and the production containers."""

from app import create_app

app = create_app()
