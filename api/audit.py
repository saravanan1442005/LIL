"""Audit log blueprint (/api/v2/audit).
Exposes the immutable audit trail to Admin and Auditor roles for compliance inspections.
"""
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.connection import get_session_factory
from database.models import AuditLog
from services.auth_service import roles_required
from api.pagination import parse_pagination

audit_bp = Blueprint("audit", __name__, url_prefix="/api/v2")


@audit_bp.route("/audit", methods=["GET"])
@roles_required("Admin", "Auditor")
def get_audit_logs():
    session: Session = get_session_factory()()
    try:
        query = session.query(AuditLog)

        action = request.args.get("action")
        role = request.args.get("role")
        user_email = request.args.get("user_email")
        target_type = request.args.get("target_type")
        limit, offset, pagination_error = parse_pagination(
            request.args.get("limit"), request.args.get("offset")
        )
        if pagination_error:
            return jsonify({"error": pagination_error}), 400

        if action:
            query = query.filter(AuditLog.action == action)
        if role:
            query = query.filter(AuditLog.role == role)
        if user_email:
            query = query.filter(AuditLog.user_email.ilike(f"%{user_email}%"))
        if target_type:
            query = query.filter(AuditLog.target_type == target_type)

        total = query.count()
        logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

        return jsonify({
            "total": total,
            "limit": limit,
            "offset": offset,
            "logs": [log.to_dict() for log in logs]
        })
    finally:
        session.close()
