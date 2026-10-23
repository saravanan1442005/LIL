"""Cameras & Zones management blueprint (/api/v2/cameras and /api/v2/zones).
Enforces RBAC on modifications and logs administrative actions to the immutable audit log.
"""
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from database.connection import get_session_factory
from database.models import Camera, Zone
from services.auth_service import jwt_required, roles_required
from services.audit_service import log_audit_event

cameras_bp = Blueprint("cameras", __name__, url_prefix="/api/v2")


# ---------------------------------------------------------------------------
# CAMERAS CRUD
# ---------------------------------------------------------------------------
@cameras_bp.route("/cameras", methods=["GET"])
def list_cameras():
    session: Session = get_session_factory()()
    try:
        cams = session.query(Camera).order_by(Camera.id.asc()).all()
        result = []
        for c in cams:
            c_dict = c.to_dict()
            c_dict["zones"] = [z.to_dict() for z in c.zones]
            result.append(c_dict)
        return jsonify({"cameras": result})
    finally:
        session.close()


@cameras_bp.route("/cameras", methods=["POST"])
@roles_required("Admin", "Security Officer")
def create_camera():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    location = data.get("location", "").strip()
    stream_source = data.get("stream_source", "").strip()
    stream_type = data.get("stream_type", "RTSP").strip().upper()
    fps = data.get("fps", 15)
    resolution = data.get("resolution", "1280x720")
    enabled = bool(data.get("enabled", True))

    if not name or not stream_source:
        return jsonify({"error": "Camera name and stream_source are required."}), 400

    session: Session = get_session_factory()()
    try:
        cam = Camera(
            name=name,
            location=location,
            stream_source=stream_source,
            stream_type=stream_type,
            fps=fps,
            resolution=resolution,
            enabled=enabled,
        )
        session.add(cam)
        session.commit()

        log_audit_event(
            session=session,
            action="CREATE_CAMERA",
            target_type="Camera",
            target_id=str(cam.id),
            details={"name": name, "stream_type": stream_type, "location": location}
        )

        return jsonify({"camera": cam.to_dict()}), 201
    finally:
        session.close()


@cameras_bp.route("/cameras/<int:camera_id>", methods=["GET"])
def get_camera(camera_id: int):
    session: Session = get_session_factory()()
    try:
        cam = session.query(Camera).filter(Camera.id == camera_id).first()
        if not cam:
            return jsonify({"error": "Camera not found."}), 404
        c_dict = cam.to_dict()
        c_dict["zones"] = [z.to_dict() for z in cam.zones]
        return jsonify({"camera": c_dict})
    finally:
        session.close()


@cameras_bp.route("/cameras/<int:camera_id>", methods=["PUT"])
@roles_required("Admin", "Security Officer")
def update_camera(camera_id: int):
    data = request.get_json(silent=True) or {}
    session: Session = get_session_factory()()
    try:
        cam = session.query(Camera).filter(Camera.id == camera_id).first()
        if not cam:
            return jsonify({"error": "Camera not found."}), 404

        if "name" in data:
            cam.name = data["name"].strip()
        if "location" in data:
            cam.location = data["location"].strip()
        if "stream_source" in data:
            cam.stream_source = data["stream_source"].strip()
        if "stream_type" in data:
            cam.stream_type = data["stream_type"].strip().upper()
        if "fps" in data:
            cam.fps = int(data["fps"])
        if "resolution" in data:
            cam.resolution = str(data["resolution"])
        if "enabled" in data:
            cam.enabled = bool(data["enabled"])

        session.commit()

        log_audit_event(
            session=session,
            action="UPDATE_CAMERA",
            target_type="Camera",
            target_id=str(cam.id),
            details=data
        )

        return jsonify({"camera": cam.to_dict()})
    finally:
        session.close()


@cameras_bp.route("/cameras/<int:camera_id>", methods=["DELETE"])
@roles_required("Admin")
def delete_camera(camera_id: int):
    session: Session = get_session_factory()()
    try:
        cam = session.query(Camera).filter(Camera.id == camera_id).first()
        if not cam:
            return jsonify({"error": "Camera not found."}), 404

        cam_name = cam.name
        session.delete(cam)
        session.commit()

        log_audit_event(
            session=session,
            action="DELETE_CAMERA",
            target_type="Camera",
            target_id=str(camera_id),
            details={"name": cam_name}
        )

        return jsonify({"message": f"Camera '{cam_name}' deleted successfully."})
    finally:
        session.close()


# ---------------------------------------------------------------------------
# ZONES CRUD
# ---------------------------------------------------------------------------
@cameras_bp.route("/cameras/<int:camera_id>/zones", methods=["GET"])
def list_zones_for_camera(camera_id: int):
    session: Session = get_session_factory()()
    try:
        zones = session.query(Zone).filter(Zone.camera_id == camera_id).order_by(Zone.id.asc()).all()
        return jsonify({"zones": [z.to_dict() for z in zones]})
    finally:
        session.close()


@cameras_bp.route("/cameras/<int:camera_id>/zones", methods=["POST"])
@roles_required("Admin", "Security Officer")
def create_zone(camera_id: int):
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    zone_type = data.get("zone_type", "GENERAL").strip().upper()
    polygon_coords = data.get("polygon_coords")
    entry_line_coords = data.get("entry_line_coords")
    dwell_threshold_seconds = data.get("dwell_threshold_seconds", 60)

    if not name:
        return jsonify({"error": "Zone name is required."}), 400

    session: Session = get_session_factory()()
    try:
        cam = session.query(Camera).filter(Camera.id == camera_id).first()
        if not cam:
            return jsonify({"error": "Camera not found."}), 404

        zone = Zone(
            camera_id=camera_id,
            name=name,
            zone_type=zone_type,
            polygon_coords=polygon_coords,
            entry_line_coords=entry_line_coords,
            dwell_threshold_seconds=dwell_threshold_seconds,
            is_active=True,
        )
        session.add(zone)
        session.commit()

        log_audit_event(
            session=session,
            action="CREATE_ZONE",
            target_type="Zone",
            target_id=str(zone.id),
            details={"camera_id": camera_id, "name": name, "zone_type": zone_type}
        )

        return jsonify({"zone": zone.to_dict()}), 201
    finally:
        session.close()


@cameras_bp.route("/zones/<int:zone_id>", methods=["PUT"])
@roles_required("Admin", "Security Officer")
def update_zone(zone_id: int):
    data = request.get_json(silent=True) or {}
    session: Session = get_session_factory()()
    try:
        zone = session.query(Zone).filter(Zone.id == zone_id).first()
        if not zone:
            return jsonify({"error": "Zone not found."}), 404

        if "name" in data:
            zone.name = data["name"].strip()
        if "zone_type" in data:
            zone.zone_type = data["zone_type"].strip().upper()
        if "polygon_coords" in data:
            zone.polygon_coords = data["polygon_coords"]
        if "entry_line_coords" in data:
            zone.entry_line_coords = data["entry_line_coords"]
        if "dwell_threshold_seconds" in data:
            zone.dwell_threshold_seconds = int(data["dwell_threshold_seconds"])
        if "is_active" in data:
            zone.is_active = bool(data["is_active"])

        session.commit()

        log_audit_event(
            session=session,
            action="UPDATE_ZONE",
            target_type="Zone",
            target_id=str(zone.id),
            details=data
        )

        return jsonify({"zone": zone.to_dict()})
    finally:
        session.close()


@cameras_bp.route("/zones/<int:zone_id>", methods=["DELETE"])
@roles_required("Admin", "Security Officer")
def delete_zone(zone_id: int):
    session: Session = get_session_factory()()
    try:
        zone = session.query(Zone).filter(Zone.id == zone_id).first()
        if not zone:
            return jsonify({"error": "Zone not found."}), 404

        z_name = zone.name
        session.delete(zone)
        session.commit()

        log_audit_event(
            session=session,
            action="DELETE_ZONE",
            target_type="Zone",
            target_id=str(zone_id),
            details={"name": z_name}
        )

        return jsonify({"message": f"Zone '{z_name}' deleted successfully."})
    finally:
        session.close()
