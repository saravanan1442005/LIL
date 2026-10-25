"""Sensor ingestion blueprint (/api/v2/sensors).
Receives HTTP webhook events from PIR motion sensors, magnetic door contacts, and RFID gate badges.
"""
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.connection import get_session_factory
from database.models import SensorEvent
from services.sensor_service import ingest_sensor_event
from api.pagination import parse_pagination

sensors_bp = Blueprint("sensors", __name__, url_prefix="/api/v2/sensors")


@sensors_bp.route("/event", methods=["POST"])
def receive_sensor_event():
    data = request.get_json(silent=True) or {}
    sensor_id = data.get("sensor_id", "").strip()
    sensor_type = data.get("sensor_type", "").strip().upper()
    zone_id = data.get("zone_id")
    event_data = data.get("event_data", {})
    linked_visitor_id = data.get("linked_visitor_id")

    if not sensor_id or not sensor_type:
        return jsonify({"error": "sensor_id and sensor_type are required."}), 400

    session: Session = get_session_factory()()
    try:
        rec = ingest_sensor_event(
            session=session,
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            zone_id=int(zone_id) if zone_id else None,
            event_data=event_data,
            linked_visitor_id=int(linked_visitor_id) if linked_visitor_id else None,
        )
        return jsonify({"status": "SUCCESS", "sensor_event": rec.to_dict()}), 201
    finally:
        session.close()


@sensors_bp.route("/events", methods=["GET"])
def list_sensor_events():
    session: Session = get_session_factory()()
    try:
        limit, _, pagination_error = parse_pagination(
            request.args.get("limit"), None, max_limit=100
        )
        if pagination_error:
            return jsonify({"error": pagination_error}), 400
        events = (
            session.query(SensorEvent)
            .order_by(SensorEvent.timestamp.desc())
            .limit(limit)
            .all()
        )
        return jsonify({"sensor_events": [s.to_dict() for s in events]})
    finally:
        session.close()
