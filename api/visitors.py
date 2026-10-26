"""Visitors management blueprint (/api/v2/visitors).
Provides listing, profile inspection, human-in-the-loop category/label editing,
profile merging, and DPDP Act 2023 right-to-be-forgotten data erasure.
"""
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from database.connection import get_session_factory
from database.models import Visitor
from services.auth_service import jwt_required, roles_required
from services.visitor_service import (
    get_visitor_details, is_visitor_present, link_event_to_visitor,
    merge_visitor_profiles, purge_visitor_data
)
from services.audit_service import log_audit_event
from api.pagination import parse_pagination

visitors_bp = Blueprint("visitors", __name__, url_prefix="/api/v2/visitors")


@visitors_bp.route("", methods=["GET"])
@roles_required("Admin", "Security Officer", "Viewer", "Auditor")
def list_visitors():
    session: Session = get_session_factory()()
    try:
        query = session.query(Visitor).filter(Visitor.status != "MERGED")

        category = request.args.get("category")
        q = request.args.get("q")
        limit, offset, pagination_error = parse_pagination(
            request.args.get("limit"), request.args.get("offset")
        )
        if pagination_error:
            return jsonify({"error": pagination_error}), 400

        if category and category != "ALL":
            query = query.filter(Visitor.category == category)
        if q:
            query = query.filter(
                (Visitor.visitor_code.ilike(f"%{q}%")) |
                (Visitor.label.ilike(f"%{q}%")) |
                (Visitor.notes.ilike(f"%{q}%")) |
                (Visitor.phone_last4 == q) |
                (Visitor.full_name.ilike(f"%{q}%")) |
                (Visitor.company.ilike(f"%{q}%")) |
                (Visitor.vehicle_number.ilike(f"%{q}%"))
            )

        total = query.count()
        visitors = query.order_by(Visitor.last_seen.desc()).offset(offset).limit(limit).all()
        visitor_list = []
        for v in visitors:
            payload = v.to_dict() | {"is_present": is_visitor_present(session, v.id)}
            payload["updated_at"] = v.updated_at.isoformat() if v.updated_at else None
            payload["last_seen_iso"] = v.last_seen.isoformat() if v.last_seen else None
            visitor_list.append(payload)

        return jsonify({
            "total": total,
            "limit": limit,
            "offset": offset,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "visitors": visitor_list
        })
    finally:
        session.close()


@visitors_bp.route("/<int:visitor_id>", methods=["GET"])
@roles_required("Admin", "Security Officer", "Viewer", "Auditor")
def get_visitor(visitor_id: int):
    session: Session = get_session_factory()()
    try:
        details = get_visitor_details(session, visitor_id)
        if not details:
            return jsonify({"error": "Visitor not found."}), 404
        return jsonify({"visitor": details})
    finally:
        session.close()


@visitors_bp.route("/<int:visitor_id>/violations", methods=["POST"])
@roles_required("Admin", "Security Officer")
def link_visitor_violation(visitor_id: int):
    """Link an existing violation event after an officer verifies its identity."""
    data = request.get_json(silent=True) or {}
    event_id = data.get("event_id")
    if not event_id:
        return jsonify({"error": "event_id is required."}), 400

    session: Session = get_session_factory()()
    try:
        try:
            event = link_event_to_visitor(
                session,
                int(event_id),
                visitor_id,
                str(data.get("reason", "Manual visitor attribution")).strip(),
            )
        except (LookupError, ValueError) as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({"event": event.to_dict(), "visitor_id": visitor_id}), 200
    finally:
        session.close()


@visitors_bp.route("/<int:visitor_id>", methods=["PUT"])
@roles_required("Admin", "Security Officer")
def update_visitor(visitor_id: int):
    data = request.get_json(silent=True) or {}
    session: Session = get_session_factory()()
    try:
        visitor = session.query(Visitor).filter(Visitor.id == visitor_id).first()
        if not visitor:
            return jsonify({"error": "Visitor not found."}), 404

        if "category" in data:
            visitor.category = data["category"]
        if "label" in data:
            visitor.label = data["label"]
        if "notes" in data:
            visitor.notes = data["notes"]

        session.commit()

        log_audit_event(
            session=session,
            action="UPDATE_VISITOR",
            target_type="Visitor",
            target_id=str(visitor_id),
            details=data
        )

        return jsonify({"visitor": visitor.to_dict()})
    finally:
        session.close()


@visitors_bp.route("/merge", methods=["POST"])
@roles_required("Admin", "Security Officer")
def merge_visitors():
    data = request.get_json(silent=True) or {}
    source_id = data.get("source_id")
    target_id = data.get("target_id")
    reason = data.get("reason", "Manual correction: same individual detected across profiles")

    if not source_id or not target_id or source_id == target_id:
        return jsonify({"error": "Valid source_id and target_id are required and cannot be identical."}), 400

    session: Session = get_session_factory()()
    try:
        success = merge_visitor_profiles(session, source_id, target_id, reason)
        if not success:
            return jsonify({"error": "Could not merge profiles. Verify IDs."}), 404
        return jsonify({"message": f"Successfully merged visitor #{source_id} into #{target_id}."})
    finally:
        session.close()


@visitors_bp.route("/<int:visitor_id>/purge", methods=["DELETE"])
@roles_required("Admin")
def purge_visitor(visitor_id: int):
    data = request.get_json(silent=True) or {}
    reason = data.get("reason", "Data Principal Right-to-be-Forgotten Request under DPDP Act 2023")

    session: Session = get_session_factory()()
    try:
        success = purge_visitor_data(session, visitor_id, reason)
        if not success:
            return jsonify({"error": "Visitor not found."}), 404
        return jsonify({"message": f"All personal data and appearance embeddings for visitor #{visitor_id} permanently erased."})
    finally:
        session.close()
