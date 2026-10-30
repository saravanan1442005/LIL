"""Visitor management and Re-ID matching service.
Handles cross-camera recurring visitor recognition, profile aggregation,
human-in-the-loop manual corrections (label, merge, split), and DPDP right-to-be-forgotten erasure.
"""
import uuid
import datetime
import logging
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy.orm import Session  # type: ignore
from database.models import Visitor, VisitorEmbedding, VisitorEntry, Event, Track, AuditLog
from services.reid_service import get_reid_extractor
from services.face_service import get_face_service
from services.vector_store import get_vector_store
from services.audit_service import log_audit_event

logger = logging.getLogger("ecolifybuddy.visitor")

DEFAULT_SIMILARITY_THRESHOLD = 0.68

import threading

_GATE_LOCK = threading.Lock()


class AlreadyPresentError(ValueError):
    """Raised when an ENTRY is attempted for a visitor with an active visit."""


class NotPresentError(ValueError):
    """Raised when an EXIT is attempted for a visitor without an active visit."""



def generate_visitor_code(session: Session) -> str:
    """Generate sequential unique visitor identifier, e.g. VIS-10042."""
    latest = (
        session.query(Visitor.visitor_code)
        .filter(Visitor.visitor_code.like("VIS-%"))
        .order_by(Visitor.id.desc())
        .first()
    )
    try:
        next_number = int(latest[0].split("-", 1)[1]) + 1 if latest else 10001
    except (ValueError, AttributeError):
        next_number = 10001 + session.query(Visitor).count()
    return f"VIS-{next_number}"


def is_visitor_present(session: Session, visitor_id: int) -> bool:
    """Return whether the visitor's latest confirmed gate record is an entry."""
    latest = (
        session.query(VisitorEntry)
        .filter(VisitorEntry.visitor_id == visitor_id, VisitorEntry.confirmed.is_(True))
        .order_by(VisitorEntry.timestamp.desc(), VisitorEntry.id.desc())
        .first()
    )
    return bool(latest and latest.event_type == "ENTRY")


def record_gate_event(
    session: Session,
    visitor_id: int,
    event_type: str,
    source: str,
    camera_id: Optional[int] = None,
    confidence: Optional[float] = None,
    snapshot_path: Optional[str] = None,
    user_id: Optional[int] = None,
    expected_duration_minutes: Optional[int] = 60,
    purpose: Optional[str] = None,
) -> VisitorEntry:
    """Persist a confirmed entry/exit event and update the visitor's presence."""
    event_type = event_type.upper()
    source = source.upper()
    if any(k in source for k in ["GUARD", "MANUAL", "CONFIRM", "BUTTON", "KIOSK", "VOICE"]):
        source = "KIOSK" if "KIOSK" in source or "VOICE" in source else "MANUAL"
    elif "FACE" in source:
        source = "FACE"
    elif any(k in source for k in ["PLATE", "ANPR"]):
        source = "PLATE"
    elif "PHONE" in source:
        source = "PHONE"
    elif "REID" in source:
        source = "REID"
    elif source not in {"FACE", "PLATE", "REID", "PHONE", "MANUAL", "KIOSK"}:
        source = "MANUAL"

    if event_type not in {"ENTRY", "EXIT"}:
        raise ValueError("event_type must be ENTRY or EXIT")

    visitor = session.query(Visitor).filter(
        Visitor.id == visitor_id, Visitor.status == "ACTIVE"
    ).first()
    if not visitor:
        raise LookupError("Active visitor not found.")

    with _GATE_LOCK:
        # Re-check presence inside the lock against the database (source of truth)
        session.expire_all()
        present = is_visitor_present(session, visitor_id)
        if event_type == "ENTRY" and present:
            raise AlreadyPresentError("Visitor is already marked as present.")
        if event_type == "EXIT" and not present:
            raise NotPresentError("Visitor is not currently marked as present.")

        entry = VisitorEntry(
            visitor_id=visitor.id,
            camera_id=camera_id,
            event_type=event_type,
            source=source,
            confidence=confidence,
            guard_user_id=user_id,
            confirmed=True,
            snapshot_path=snapshot_path,
            expected_duration_minutes=expected_duration_minutes or 60,
            purpose=(purpose or None),
        )
        visitor.last_seen = datetime.datetime.now(datetime.timezone.utc)
        if event_type == "ENTRY":
            visitor.total_visits = (visitor.total_visits or 0) + 1
        session.add(entry)
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise
        return entry


def match_or_create_visitor(
    session: Session,
    person_crop_bgr,
    camera_id: Optional[int] = None,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    carried_objects: Optional[List[str]] = None,
) -> Tuple[Visitor, bool, float]:
    """Recognise returning visitor via 512-d Re-ID embedding search.
    Returns (Visitor, is_new_visitor, similarity_score).
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    vstore = get_vector_store(session)

    # 1. InsightFace Facial Recognition (ArcFace 512-d)
    import os
    if os.getenv("FACE_RECOGNITION_ENABLED", "false").lower() == "true":
        try:
            face_matches = get_face_service().recognize_face(session, person_crop_bgr, threshold=0.48, top_k=1)
            if face_matches:
                v_match = face_matches[0]
                matched_visitor = session.query(Visitor).filter(Visitor.id == v_match["visitor_id"]).first()
                if matched_visitor:
                    matched_visitor.last_seen = now
                    session.commit()
                    logger.info("Recognized visitor %s via InsightFace (score=%.3f)", matched_visitor.full_name, v_match["confidence"])
                    return matched_visitor, False, float(v_match["confidence"])
        except Exception as fe:
            logger.warning("InsightFace recognition pass error: %s", fe)

    # 2. Appearance Re-ID Embedding Fallback
    extractor = get_reid_extractor()
    embedding = extractor.extract_embedding(person_crop_bgr)

    # Search top match above threshold
    matches = vstore.search_similar(embedding, top_k=1, threshold=threshold, embedding_type="reid")


    if matches:
        visitor_id, similarity = matches[0]
        visitor = session.query(Visitor).filter(Visitor.id == visitor_id).first()
        if visitor:
            # Update returning visitor
            visitor.last_seen = now

            # Auto-suggest category if still unknown and carrying package/backpack
            if visitor.category == "Unknown" and carried_objects:
                for obj in carried_objects:
                    if obj in ("backpack", "suitcase", "box", "package"):
                        visitor.category = "Delivery"
                        break

            # Add embedding to enrich profile
            vstore.add_embedding(visitor.id, embedding, embedding_type="reid", camera_id=camera_id, confidence=similarity)
            session.commit()
            return visitor, False, similarity

    # Create new visitor profile
    code = generate_visitor_code(session)
    category = "Unknown"
    if carried_objects:
        for obj in carried_objects:
            if obj in ("backpack", "suitcase", "box", "package"):
                category = "Delivery"
                break

    new_visitor = Visitor(
        visitor_code=code,
        category=category,
        first_seen=now,
        last_seen=now,
        total_visits=1,
        avg_dwell_time=0.0,
        status="ACTIVE"
    )
    session.add(new_visitor)
    session.commit()

    # Store initial embedding
    vstore.add_embedding(new_visitor.id, embedding, embedding_type="reid", camera_id=camera_id, confidence=1.0)
    session.commit()

    return new_visitor, True, 1.0


def link_event_to_visitor(
    session: Session,
    event_id: int,
    visitor_id: int,
    reason: str = "Manual visitor attribution",
) -> Event:
    """Attach an existing camera event to a visitor after human verification."""
    event = session.query(Event).filter(Event.id == event_id).first()
    visitor = session.query(Visitor).filter(
        Visitor.id == visitor_id, Visitor.status == "ACTIVE"
    ).first()
    if not event:
        raise LookupError("Event not found.")
    if not visitor:
        raise LookupError("Active visitor not found.")
    if event.event_type not in {"VIOLATION", "LITTERING", "OBJECT_LEFT_BEHIND"}:
        raise ValueError("Only violation events can be linked to a visitor.")

    event.visitor_id = visitor.id
    details = dict(event.details or {})
    details["visitor_attribution"] = "human_verified"
    event.details = details
    session.commit()
    log_audit_event(
        session,
        "LINK_VISITOR_VIOLATION",
        "Event",
        str(event.id),
        reason=reason,
        details={"visitor_id": visitor.id},
    )
    return event


def get_visitor_details(session: Session, visitor_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve full visitor profile with aggregated statistics and timeline events."""
    visitor = session.query(Visitor).filter(Visitor.id == visitor_id).first()
    if not visitor:
        return None

    events = (
        session.query(Event)
        .filter(Event.visitor_id == visitor_id)
        .order_by(Event.timestamp.desc())
        .limit(50)
        .all()
    )

    cameras_visited = set()
    objects_seen = set()
    for ev in events:
        if ev.camera_id:
            cameras_visited.add(ev.camera_id)
        if ev.detected_objects:
            for obj in ev.detected_objects:
                objects_seen.add(obj)

    v_dict = visitor.to_dict()
    v_dict["cameras_visited_count"] = len(cameras_visited)
    v_dict["distinct_objects"] = sorted(list(objects_seen))
    v_dict["violation_count"] = sum(
        1 for event in events
        if event.event_type in {"VIOLATION", "LITTERING", "OBJECT_LEFT_BEHIND"}
    )
    v_dict["recent_events"] = [e.to_dict() for e in events[:10]]
    entries = (
        session.query(VisitorEntry)
        .filter(VisitorEntry.visitor_id == visitor_id)
        .order_by(VisitorEntry.timestamp.desc(), VisitorEntry.id.desc())
        .limit(20)
        .all()
    )
    v_dict["is_present"] = is_visitor_present(session, visitor_id)
    v_dict["gate_events"] = [
        {
            "id": item.id,
            "event_type": item.event_type,
            "source": item.source,
            "camera_id": item.camera_id,
            "confidence": item.confidence,
            "confirmed": item.confirmed,
            "timestamp": item.timestamp.isoformat() if item.timestamp else None,
        }
        for item in entries
    ]
    return v_dict


def purge_expired_non_violators(session: Session, retention_hours: int = 24) -> int:
    """Redact non-violating profiles whose last observation is past retention."""
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=retention_hours)
    candidates = session.query(Visitor).filter(
        Visitor.status == "ACTIVE", Visitor.last_seen < cutoff
    ).all()
    purged = 0
    for visitor in candidates:
        has_violation = session.query(Event.id).filter(
            Event.visitor_id == visitor.id,
            Event.event_type.in_(("VIOLATION", "LITTERING", "OBJECT_LEFT_BEHIND")),
        ).first()
        if not has_violation and purge_visitor_data(session, visitor.id, "Automatic non-violator retention purge"):
            purged += 1
    return purged


def merge_visitor_profiles(session: Session, source_id: int, target_id: int, reason: str = "") -> bool:
    """Human-in-the-loop: Merge duplicate visitor profiles."""
    source = session.query(Visitor).filter(Visitor.id == source_id).first()
    target = session.query(Visitor).filter(Visitor.id == target_id).first()
    if not source or not target:
        return False

    # Re-link all identity-associated records to the target profile.
    session.query(VisitorEmbedding).filter(VisitorEmbedding.visitor_id == source_id).update({"visitor_id": target_id})
    session.query(VisitorEntry).filter(VisitorEntry.visitor_id == source_id).update({"visitor_id": target_id})
    session.query(Track).filter(Track.visitor_id == source_id).update({"visitor_id": target_id})
    session.query(Event).filter(Event.visitor_id == source_id).update({"visitor_id": target_id})

    target.total_visits = (target.total_visits or 1) + (source.total_visits or 1)
    if source.first_seen < target.first_seen:
        target.first_seen = source.first_seen
    if source.last_seen > target.last_seen:
        target.last_seen = source.last_seen

    source.status = "MERGED"
    source.notes = f"Merged into {target.visitor_code}. Reason: {reason}"
    session.commit()

    log_audit_event(
        session=session,
        action="MERGE_VISITORS",
        target_type="Visitor",
        target_id=str(target_id),
        reason=reason,
        details={"source_code": source.visitor_code, "target_code": target.visitor_code}
    )
    return True


def purge_visitor_data(session: Session, visitor_id: int, reason: str = "Data Principal Erasure Request") -> bool:
    """DPDP Act 2023 Right-to-be-Forgotten: Permanently erase biometric-adjacent embeddings and snapshots."""
    visitor = session.query(Visitor).filter(Visitor.id == visitor_id).first()
    if not visitor:
        return False

    # Delete all embeddings
    session.query(VisitorEmbedding).filter(VisitorEmbedding.visitor_id == visitor_id).delete()

    # Redact visitor fields
    original_code = visitor.visitor_code
    visitor.visitor_code = f"REDACTED-{visitor.id}"
    visitor.label = "[DATA_PRINCIPAL_ERASED]"
    visitor.notes = f"Personal data purged on {datetime.datetime.now(datetime.timezone.utc).isoformat()}. Reason: {reason}"
    visitor.status = "REDACTED"
    session.commit()

    log_audit_event(
        session=session,
        action="PURGE_VISITOR_DATA",
        target_type="Visitor",
        target_id=str(visitor_id),
        reason=reason,
        details={"original_code": original_code}
    )
    return True


def delete_visitor_completely(session: Session, visitor_id: int) -> bool:
    """Permanently delete visitor profile and cleanly handle references."""
    from database.models import VisitorEntry, PlateRead, Track, Event, FaceEnrollment

    visitor = session.query(Visitor).filter(Visitor.id == visitor_id).first()
    if not visitor:
        return False

    v_code = visitor.visitor_code

    # Remove embeddings & face enrollments
    session.query(VisitorEmbedding).filter(VisitorEmbedding.visitor_id == visitor_id).delete()
    session.query(FaceEnrollment).filter(FaceEnrollment.visitor_id == visitor_id).delete()

    # Unlink or clean entries, plate reads, tracks, events
    session.query(VisitorEntry).filter(VisitorEntry.visitor_id == visitor_id).delete()
    session.query(PlateRead).filter(PlateRead.visitor_id == visitor_id).update({"visitor_id": None})
    session.query(Track).filter(Track.visitor_id == visitor_id).update({"visitor_id": None})
    session.query(Event).filter(Event.visitor_id == visitor_id).update({"visitor_id": None})

    session.delete(visitor)
    session.commit()

    log_audit_event(
        session=session,
        action="DELETE_VISITOR_PROFILE",
        target_type="Visitor",
        target_id=str(visitor_id),
        reason="Manual permanent profile deletion",
        details={"visitor_code": v_code}
    )
    return True
