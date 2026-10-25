"""Search and incident timeline blueprint (/api/v2/search and /api/v2/timeline).
Supports free-text natural-language queries, structured multi-field filtering,
incident timeline generation, and verified forensic export.
"""
import datetime
from flask import Blueprint, request, jsonify, Response, g
from sqlalchemy.orm import Session
from database.connection import get_session_factory
from services.search_service import (
    parse_natural_language_query, search_events,
    generate_incident_timeline, export_timeline_html
)
from services.audit_service import log_audit_event
from services.auth_service import jwt_required
from api.pagination import parse_pagination

search_bp = Blueprint("search", __name__, url_prefix="/api/v2")


@search_bp.route("/search", methods=["GET"])
def search():
    nl_query = request.args.get("q", "").strip()
    filters = {}

    if nl_query:
        filters = parse_natural_language_query(nl_query)

    # Override/supplement with explicit query parameters
    for key in ["event_type", "camera_id", "zone_id", "visitor_id", "category", "time_start", "time_end"]:
        val = request.args.get(key)
        if val:
            filters[key] = val

    limit, offset, pagination_error = parse_pagination(
        request.args.get("limit"), request.args.get("offset")
    )
    if pagination_error:
        return jsonify({"error": pagination_error}), 400

    session: Session = get_session_factory()()
    try:
        results = search_events(session, filters, limit=limit, offset=offset)

        # Log search query in immutable audit trail
        log_audit_event(
            session=session,
            action="FORENSIC_SEARCH",
            target_type="Event",
            details={"raw_query": nl_query, "parsed_filters": filters, "matched": results.get("total", 0)}
        )

        results["parsed_query"] = filters
        return jsonify(results)
    finally:
        session.close()


@search_bp.route("/timeline/generate", methods=["POST"])
def generate_timeline():
    data = request.get_json(silent=True) or {}
    now = datetime.datetime.now(datetime.timezone.utc)

    start_str = data.get("time_start")
    end_str = data.get("time_end")

    try:
        start_time = datetime.datetime.fromisoformat(start_str) if start_str else now - datetime.timedelta(hours=24)
        end_time = datetime.datetime.fromisoformat(end_str) if end_str else now
    except Exception:
        return jsonify({"error": "Invalid date format. Use ISO 8601 (YYYY-MM-DDTHH:MM:SS)."}), 400

    camera_id = data.get("camera_id")
    visitor_id = data.get("visitor_id")

    session: Session = get_session_factory()()
    try:
        timeline = generate_incident_timeline(
            session=session,
            time_start=start_time,
            time_end=end_time,
            camera_id=int(camera_id) if camera_id else None,
            visitor_id=int(visitor_id) if visitor_id else None,
        )

        log_audit_event(
            session=session,
            action="GENERATE_TIMELINE",
            target_type="Timeline",
            details={
                "time_window": [start_time.isoformat(), end_time.isoformat()],
                "camera_id": camera_id,
                "visitor_id": visitor_id,
                "event_count": timeline["summary"]["total_events"]
            }
        )

        return jsonify(timeline)
    finally:
        session.close()


@search_bp.route("/timeline/export", methods=["GET"])
def export_timeline():
    now = datetime.datetime.now(datetime.timezone.utc)
    start_str = request.args.get("time_start")
    end_str = request.args.get("time_end")
    export_format = request.args.get("format", "json").lower()

    try:
        start_time = datetime.datetime.fromisoformat(start_str) if start_str else now - datetime.timedelta(hours=24)
        end_time = datetime.datetime.fromisoformat(end_str) if end_str else now
    except Exception:
        return jsonify({"error": "Invalid date format."}), 400

    camera_id = request.args.get("camera_id")
    visitor_id = request.args.get("visitor_id")

    session: Session = get_session_factory()()
    try:
        timeline = generate_incident_timeline(
            session=session,
            time_start=start_time,
            time_end=end_time,
            camera_id=int(camera_id) if camera_id else None,
            visitor_id=int(visitor_id) if visitor_id else None,
        )

        log_audit_event(
            session=session,
            action="EXPORT_TIMELINE",
            target_type="Timeline",
            details={"format": export_format, "total_events": timeline["summary"]["total_events"]}
        )

        if export_format == "html":
            html_content = export_timeline_html(timeline)
            return Response(html_content, mimetype="text/html")

        return jsonify(timeline)
    finally:
        session.close()
