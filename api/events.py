"""Events logging blueprint (/api/v2/events).
Exposes timestamped person arrival, tripwire crossing, and carried object records.
"""
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.connection import get_session_factory
from database.models import Event, Visitor, Camera

events_bp = Blueprint("events", __name__, url_prefix="/api/v2/events")


@events_bp.route("", methods=["GET"])
def list_events():
    session: Session = get_session_factory()()
    try:
        query = session.query(Event)

        event_type = request.args.get("event_type")
        camera_id = request.args.get("camera_id")
        visitor_id = request.args.get("visitor_id")
        limit = min(int(request.args.get("limit", 50)), 200)
        offset = int(request.args.get("offset", 0))

        if event_type:
            query = query.filter(Event.event_type == event_type)
        if camera_id:
            query = query.filter(Event.camera_id == int(camera_id))
        if visitor_id:
            query = query.filter(Event.visitor_id == int(visitor_id))

        total = query.count()
        events = query.order_by(Event.timestamp.desc()).offset(offset).limit(limit).all()

        results = []
        for ev in events:
            d = ev.to_dict()
            if ev.visitor:
                d["visitor_code"] = ev.visitor.visitor_code
                d["visitor_category"] = ev.visitor.category
                d["visitor_label"] = ev.visitor.label
            if ev.camera:
                d["camera_name"] = ev.camera.name
            results.append(d)

        return jsonify({
            "total": total,
            "limit": limit,
            "offset": offset,
            "events": results
        })
    finally:
        session.close()


@events_bp.route("/<int:event_id>", methods=["GET"])
def get_event(event_id: int):
    session: Session = get_session_factory()()
    try:
        ev = session.query(Event).filter(Event.id == event_id).first()
        if not ev:
            return jsonify({"error": "Event not found."}), 404
        d = ev.to_dict()
        if ev.visitor:
            d["visitor"] = ev.visitor.to_dict()
        if ev.camera:
            d["camera"] = ev.camera.to_dict()
        if ev.zone:
            d["zone"] = ev.zone.to_dict()
        return jsonify({"event": d})
    finally:
        session.close()
