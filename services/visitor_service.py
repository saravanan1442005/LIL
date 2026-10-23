"""Visitor management and Re-ID matching service.
Handles cross-camera recurring visitor recognition, profile aggregation,
human-in-the-loop manual corrections (label, merge, split), and DPDP right-to-be-forgotten erasure.
"""
import uuid
import datetime
import logging
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy.orm import Session
from database.models import Visitor, VisitorEmbedding, Event, Track, AuditLog
from services.reid_service import get_reid_extractor
from services.vector_store import get_vector_store
from services.audit_service import log_audit_event

logger = logging.getLogger("ecolifybuddy.visitor")

DEFAULT_SIMILARITY_THRESHOLD = 0.68


def generate_visitor_code(session: Session) -> str:
    """Generate sequential unique visitor identifier, e.g. VIS-10042."""
    count = session.query(Visitor).count()
    return f"VIS-{10001 + count}"


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
    extractor = get_reid_extractor()
    embedding = extractor.extract_embedding(person_crop_bgr)
    vstore = get_vector_store(session)

    # Search top match above threshold
    matches = vstore.search_similar(embedding, top_k=1, threshold=threshold, embedding_type="reid")

    now = datetime.datetime.now(datetime.timezone.utc)

    if matches:
        visitor_id, similarity = matches[0]
        visitor = session.query(Visitor).filter(Visitor.id == visitor_id).first()
        if visitor:
            # Update returning visitor
            visitor.last_seen = now
            visitor.total_visits = (visitor.total_visits or 0) + 1

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
    v_dict["recent_events"] = [e.to_dict() for e in events[:10]]
    return v_dict


def merge_visitor_profiles(session: Session, source_id: int, target_id: int, reason: str = "") -> bool:
    """Human-in-the-loop: Merge duplicate visitor profiles."""
    source = session.query(Visitor).filter(Visitor.id == source_id).first()
    target = session.query(Visitor).filter(Visitor.id == target_id).first()
    if not source or not target:
        return False

    # Re-link embeddings, tracks, and events to target
    session.query(VisitorEmbedding).filter(VisitorEmbedding.visitor_id == source_id).update({"visitor_id": target_id})
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
