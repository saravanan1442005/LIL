"""SQLAlchemy models for EcoLifyBuddy:
- Users & RBAC (Admin, Security Officer, Viewer, Auditor)
- Immutable Audit Logs
- Cameras & Zones (polygons and virtual tripwire entry/exit coordinates)
- Visitors & Vector Embeddings (pgvector HNSW with cosine similarity)
- Face Recognition Consents & Enrollments (feature-flagged OFF by default)
- Multi-Camera Tracks & Time-stamped Events
- Alerts & IoT Sensor Ingestion Events
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON, Index, TypeDecorator
)
from sqlalchemy.orm import relationship
from database.connection import Base

# Dynamic vector type decorator: uses pgvector on Postgres, JSON array on SQLite fallback
try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False


class Vector512(TypeDecorator):
    """Custom SQLAlchemy type that renders as pgvector Vector(512) on Postgres and JSON on SQLite."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and HAS_PGVECTOR:
            return dialect.type_descriptor(Vector(512))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            if dialect.name == "postgresql" and HAS_PGVECTOR:
                return [float(x) for x in value]
            return list(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            import json
            try:
                return json.loads(value)
            except Exception:
                return [float(x) for x in value.strip("[]").split(",") if x.strip()]
        return value


# ---------------------------------------------------------------------------
# 1. USERS & RBAC
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(String(50), nullable=False, default="Viewer")  # Admin, Security Officer, Viewer, Auditor
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# 2. IMMUTABLE AUDIT LOGS (DPDP Act 2023 Compliance)
# ---------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_email = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False, index=True)  # LOGIN, SEARCH, VIEW_UNMASKED, EXPORT_TIMELINE, DELETE_PROFILE
    target_type = Column(String(50), nullable=True)           # Visitor, Event, Camera, User, System
    target_id = Column(String(100), nullable=True)
    reason = Column(Text, nullable=True)                      # Mandatory for unmasking / deletion
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "role": self.role,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "reason": self.reason,
            "details": self.details,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# ---------------------------------------------------------------------------
# 3. CAMERAS & ZONES
# ---------------------------------------------------------------------------
class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    location = Column(String(150), nullable=True)
    stream_source = Column(String(500), nullable=False)  # RTSP URL, webcam index '0', video file path
    stream_type = Column(String(20), nullable=False, default="RTSP")  # RTSP, WEBCAM, FILE, YOUTUBE
    enabled = Column(Boolean, default=True, nullable=False)
    fps = Column(Integer, default=15)
    resolution = Column(String(20), default="1280x720")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    zones = relationship("Zone", back_populates="camera", cascade="all, delete-orphan")
    tracks = relationship("Track", back_populates="camera")
    events = relationship("Event", back_populates="camera")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "stream_source": self.stream_source,
            "stream_type": self.stream_type,
            "enabled": self.enabled,
            "fps": self.fps,
            "resolution": self.resolution,
            "zones_count": len(self.zones) if self.zones else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    zone_type = Column(String(30), nullable=False, default="GENERAL")  # ENTRY_EXIT, RESTRICTED, GENERAL, LOITERING
    polygon_coords = Column(JSON, nullable=True)                      # e.g. [[x1, y1], [x2, y2], ...]
    entry_line_coords = Column(JSON, nullable=True)                   # Virtual tripwire: [[x1, y1], [x2, y2]]
    dwell_threshold_seconds = Column(Integer, default=60)             # Dwell alert threshold
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    camera = relationship("Camera", back_populates="zones")
    events = relationship("Event", back_populates="zone")

    def to_dict(self):
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "name": self.name,
            "zone_type": self.zone_type,
            "polygon_coords": self.polygon_coords,
            "entry_line_coords": self.entry_line_coords,
            "dwell_threshold_seconds": self.dwell_threshold_seconds,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# 4. VISITORS & VECTOR EMBEDDINGS
# ---------------------------------------------------------------------------
class Visitor(Base):
    __tablename__ = "visitors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    visitor_code = Column(String(50), unique=True, nullable=False, index=True)  # e.g. VIS-10023
    category = Column(String(50), nullable=False, default="Unknown")            # Delivery, Technician, Vendor, Domestic Worker, Guest, Unknown
    label = Column(String(100), nullable=True)                                  # e.g. "Amazon Courier", "Ramesh - Electrician"
    notes = Column(Text, nullable=True)
    full_name = Column(String(150), nullable=True)
    phone_hash = Column(String(128), nullable=True, index=True)
    phone_last4 = Column(String(4), nullable=True, index=True)
    phone_verified = Column(Boolean, default=False, nullable=False)
    company = Column(String(150), nullable=True)
    vehicle_number = Column(String(32), nullable=True, index=True)
    profile_photo_path = Column(String(500), nullable=True)
    face_enrolled = Column(Boolean, default=False, nullable=False)
    plate_enrolled = Column(Boolean, default=False, nullable=False)
    consent_status = Column(String(30), default="NOT_REQUIRED", nullable=False)
    first_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    total_visits = Column(Integer, default=1, nullable=False)
    avg_dwell_time = Column(Float, default=0.0)                                 # in seconds
    status = Column(String(20), default="ACTIVE")                               # ACTIVE, MERGED, REDACTED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    embeddings = relationship("VisitorEmbedding", back_populates="visitor", cascade="all, delete-orphan")
    tracks = relationship("Track", back_populates="visitor")
    events = relationship("Event", back_populates="visitor")
    face_enrollment = relationship("FaceEnrollment", back_populates="visitor", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "visitor_code": self.visitor_code,
            "category": self.category,
            "label": self.label,
            "notes": self.notes,
            "full_name": self.full_name,
            "phone_last4": self.phone_last4,
            "phone_verified": self.phone_verified,
            "company": self.company,
            "vehicle_number": self.vehicle_number,
            "profile_photo_path": self.profile_photo_path,
            "face_enrolled": self.face_enrolled,
            "plate_enrolled": self.plate_enrolled,
            "consent_status": self.consent_status,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "total_visits": self.total_visits,
            "avg_dwell_time": self.avg_dwell_time,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class VisitorEmbedding(Base):
    __tablename__ = "visitor_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    visitor_id = Column(Integer, ForeignKey("visitors.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding_type = Column(String(20), nullable=False, default="reid")  # reid, face
    embedding = Column(Vector512, nullable=False)                        # 512-d vector
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    visitor = relationship("Visitor", back_populates="embeddings")


# ---------------------------------------------------------------------------
# 5. FACE RECOGNITION CONSENTS & ENROLLMENT (FLAGGED OFF BY DEFAULT)
# ---------------------------------------------------------------------------
class Consent(Base):
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    person_name = Column(String(150), nullable=False)
    consent_type = Column(String(50), default="FACE_RECOGNITION", nullable=False)
    consent_granted = Column(Boolean, default=False, nullable=False)
    proof_document_ref = Column(String(255), nullable=True)
    granted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)


class FaceEnrollment(Base):
    __tablename__ = "face_enrollments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    visitor_id = Column(Integer, ForeignKey("visitors.id", ondelete="CASCADE"), nullable=False, unique=True)
    consent_id = Column(Integer, ForeignKey("consents.id", ondelete="RESTRICT"), nullable=False)
    face_image_path = Column(String(500), nullable=True)
    enrolled_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    enrolled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    visitor = relationship("Visitor", back_populates="face_enrollment")
    consent = relationship("Consent")


class OTPChallenge(Base):
    __tablename__ = "otp_challenges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_hash = Column(String(128), nullable=False, index=True)
    otp_hash = Column(String(128), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class VisitorEntry(Base):
    __tablename__ = "visitor_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    visitor_id = Column(Integer, ForeignKey("visitors.id", ondelete="SET NULL"), nullable=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(20), nullable=False, default="ENTRY")
    source = Column(String(30), nullable=False)  # FACE, PLATE, REID, PHONE, MANUAL
    confidence = Column(Float, nullable=True)
    guard_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed = Column(Boolean, default=False, nullable=False)
    snapshot_path = Column(String(500), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    visitor = relationship("Visitor")


class PlateRead(Base):
    __tablename__ = "plate_reads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    visitor_id = Column(Integer, ForeignKey("visitors.id", ondelete="SET NULL"), nullable=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    raw_text = Column(String(64), nullable=False)
    normalized_text = Column(String(32), nullable=False, index=True)
    detector_confidence = Column(Float, nullable=False)
    ocr_confidence = Column(Float, nullable=False)
    quality = Column(Float, nullable=False, default=0.0)
    crop_path = Column(String(500), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    status = Column(String(30), default="PENDING", nullable=False)


# ---------------------------------------------------------------------------
# 6. TRACKS, EVENTS & ALERTS
# ---------------------------------------------------------------------------
class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    track_id = Column(Integer, nullable=False)                           # ByteTrack ID on this camera
    visitor_id = Column(Integer, ForeignKey("visitors.id", ondelete="SET NULL"), nullable=True, index=True)
    start_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    end_time = Column(DateTime, nullable=True)
    dwell_seconds = Column(Float, default=0.0)
    objects_detected = Column(JSON, nullable=True)                       # list of detected items (box, backpack, etc)
    is_active = Column(Boolean, default=True, nullable=False)

    camera = relationship("Camera", back_populates="tracks")
    visitor = relationship("Visitor", back_populates="tracks")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(40), nullable=False, index=True)          # ENTRY, EXIT, ZONE_ENTER, ZONE_EXIT, OBJECT_CARRIED, LOITERING, etc.
    visitor_id = Column(Integer, ForeignKey("visitors.id", ondelete="SET NULL"), nullable=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="SET NULL"), nullable=True, index=True)
    track_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    duration_seconds = Column(Float, default=0.0)
    detected_objects = Column(JSON, nullable=True)
    confidence = Column(Float, default=1.0)
    thumbnail_path = Column(String(500), nullable=True)
    clip_path = Column(String(500), nullable=True)
    details = Column(JSON, nullable=True)

    camera = relationship("Camera", back_populates="events")
    zone = relationship("Zone", back_populates="events")
    visitor = relationship("Visitor", back_populates="events")
    alerts = relationship("Alert", back_populates="event")

    def to_dict(self):
        return {
            "id": self.id,
            "event_type": self.event_type,
            "visitor_id": self.visitor_id,
            "camera_id": self.camera_id,
            "zone_id": self.zone_id,
            "track_id": self.track_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "duration_seconds": self.duration_seconds,
            "detected_objects": self.detected_objects or [],
            "confidence": self.confidence,
            "thumbnail_path": self.thumbnail_path,
            "clip_path": self.clip_path,
            "details": self.details or {},
        }


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    alert_type = Column(String(50), nullable=False, index=True)          # LOITERING, RESTRICTED_ZONE, UNATTENDED_OBJECT, ODD_HOUR
    severity = Column(String(20), default="MEDIUM", nullable=False)      # INFO, LOW, MEDIUM, HIGH, CRITICAL
    message = Column(Text, nullable=False)
    status = Column(String(20), default="NEW", nullable=False)           # NEW, ACKNOWLEDGED, RESOLVED
    acknowledged_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    event = relationship("Event", back_populates="alerts")

    def to_dict(self):
        return {
            "id": self.id,
            "event_id": self.event_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "status": self.status,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# 7. IOT SENSOR EVENTS
# ---------------------------------------------------------------------------
class SensorEvent(Base):
    __tablename__ = "sensor_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sensor_id = Column(String(100), nullable=False, index=True)          # e.g. "GATE-1-PIR", "DOOR-B2-MAG"
    sensor_type = Column(String(30), nullable=False)                     # PIR, DOOR, RFID, QR
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="SET NULL"), nullable=True)
    event_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    linked_event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    linked_visitor_id = Column(Integer, ForeignKey("visitors.id", ondelete="SET NULL"), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "sensor_id": self.sensor_id,
            "sensor_type": self.sensor_type,
            "zone_id": self.zone_id,
            "event_data": self.event_data or {},
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "linked_event_id": self.linked_event_id,
            "linked_visitor_id": self.linked_visitor_id,
        }
