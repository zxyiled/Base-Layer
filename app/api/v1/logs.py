"""Application log tail endpoint."""

from flask import current_app, jsonify, request

from app.api.v1 import api_v1_bp
from app.api.v1.schemas import parse_int
from app.core.log_reader import MAX_LIMIT
from app.services import LogService


@api_v1_bp.get("/logs")
def get_logs():
    """Return the latest log entries, oldest first."""
    limit = parse_int(request.args.get("limit"), "limit", 100, maximum=MAX_LIMIT)
    entries = LogService(current_app.config["LOG_FILE"]).recent_entries(limit=limit)
    return jsonify({"entries": entries}), 200
