"""Alerts blueprint (/api/v2/alerts).
Provides alert listing, real-time Server-Sent Events (SSE) push streaming,
and acknowledge/resolve workflows.
"""
import json
import time
import datetime
from flask import Blueprint, request, jsonify, Response, stream_with_context, g
from sqlalchemy.orm import Session
from database.connection import get_session_factory
from database.models import Alert
from services.auth_service import jwt_required, roles_required
from services.event_service import subscribe_alerts, unsubscribe_alerts
from services.audit_service import log_audit_event

alerts_bp = Blueprint("alerts", __name__, url_prefix="/api/v2/alerts")


@alerts_bp.route("", methods=["GET"])
def list_alerts():
    session: Session = get_session_factory()()
    try:
        query = session.query(Alert)

        status = request.args.get("status")
        severity = request.args.get("severity")
        limit = min(int(request.args.get("limit", 50)), 200)
        offset = int(request.args.get("offset", 0))

        if status:
            query = query.filter(Alert.status == status)
        if severity:
            query = query.filter(Alert.severity == severity)

        total = query.count()
        alerts = query.order_by(Alert.created_at.desc()).offset(offset).limit(limit).all()

        return jsonify({
            "total": total,
            "limit": limit,
            "offset": offset,
            "alerts": [a.to_dict() for a in alerts]
        })
    finally:
        session.close()


@alerts_bp.route("/<int:alert_id>/acknowledge", methods=["POST"])
@roles_required("Admin", "Security Officer")
def acknowledge_alert(alert_id: int):
    session: Session = get_session_factory()()
    try:
        alert = session.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return jsonify({"error": "Alert not found."}), 404

        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_by = g.current_user.get("user_id")
        alert.acknowledged_at = datetime.datetime.now(datetime.timezone.utc)
        session.commit()

        log_audit_event(
            session=session,
            action="ACKNOWLEDGE_ALERT",
            target_type="Alert",
            target_id=str(alert_id),
            details={"severity": alert.severity, "type": alert.alert_type}
        )

        return jsonify({"alert": alert.to_dict()})
    finally:
        session.close()


@alerts_bp.route("/<int:alert_id>/resolve", methods=["POST"])
@roles_required("Admin", "Security Officer")
def resolve_alert(alert_id: int):
    session: Session = get_session_factory()()
    try:
        alert = session.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return jsonify({"error": "Alert not found."}), 404

        alert.status = "RESOLVED"
        alert.resolved_by = g.current_user.get("user_id")
        alert.resolved_at = datetime.datetime.now(datetime.timezone.utc)
        session.commit()

        log_audit_event(
            session=session,
            action="RESOLVE_ALERT",
            target_type="Alert",
            target_id=str(alert_id),
            details={"severity": alert.severity, "type": alert.alert_type}
        )

        return jsonify({"alert": alert.to_dict()})
    finally:
        session.close()


@alerts_bp.route("/stream", methods=["GET"])
def alert_stream():
    """Server-Sent Events (SSE) live push endpoint for client dashboard."""
    def event_generator():
        q = subscribe_alerts()
        try:
            # Yield initial connection ping
            yield f"data: {json.dumps({'type': 'CONNECTED', 'time': time.time()})}\n\n"
            while True:
                try:
                    alert_item = q.get(timeout=20.0)
                    yield f"data: {json.dumps(alert_item)}\n\n"
                except Exception:
                    # Keep-alive heartbeat ping
                    yield f": heartbeat\n\n"
        finally:
            unsubscribe_alerts(q)

    return Response(stream_with_context(event_generator()), mimetype="text/event-stream")
