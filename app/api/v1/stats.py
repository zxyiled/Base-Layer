"""Aggregated statistics endpoint."""

from flask import jsonify

from app.api.v1 import api_v1_bp
from app.services import StatsService


@api_v1_bp.get("/stats")
def get_stats():
    """Return totals, counts per label and source, and the mean confidence."""
    return jsonify(StatsService().get_stats()), 200
