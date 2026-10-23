"""Event logging, anomaly detection, video snapshot persistence, and alert engine.
Applies rule-based anomaly detection (loitering, restricted zones, odd hours, unattended objects)
and dispatches real-time alerts.
"""
import os
import cv2
import queue
import datetime
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from database.models import Event, Alert, Visitor, Zone, Camera

logger = logging.getLogger("ecolifybuddy.events")

SNAPSHOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "snapshots")
os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

# In-memory alert broadcast subscribers for real-time SSE streaming
_alert_subscribers: List[queue.Queue] = []


def subscribe_alerts() -> queue.Queue:
    """Subscribe to live alert broadcast queue."""
    q = queue.Queue(maxsize=100)
    _alert_subscribers.append(q)
    return q


def unsubscribe_alerts(q: queue.Queue):
    """Unsubscribe from alert broadcast."""
    if q in _alert_subscribers:
        _alert_subscribers.remove(q)


def broadcast_alert(alert_dict: Dict[str, Any]):
    """Broadcast alert to all active SSE client streams."""
    for q in list(_alert_subscribers):
        try:
            q.put_nowait(alert_dict)
        except queue.Full:
            pass


def save_event_thumbnail(crop_bgr, event_id: int, blur_faces: bool = False) -> str:
    """Save event thumbnail to disk, optionally applying DPDP privacy blur."""
    if crop_bgr is None or crop_bgr.size == 0:
        return ""

    img = crop_bgr.copy()
    if blur_faces:
        # Gaussian blur over head area (top 30%)
        h, w = img.shape[:2]
        head_h = max(int(h * 0.30), 1)
        ksize = (head_h // 2 * 2 + 1, head_h // 2 * 2 + 1)
        img[0:head_h, :] = cv2.GaussianBlur(img[0:head_h, :], ksize, 15)

    filename = f"event_{event_id}_{int(datetime.datetime.now().timestamp())}.jpg"
    path = os.path.join(SNAPSHOTS_DIR, filename)
    cv2.imwrite(path, img)
    return f"/data/snapshots/{filename}"


def log_event(
    session: Session,
    event_type: str,
    camera_id: int,
    visitor_id: Optional[int] = None,
    zone_id: Optional[int] = None,
    track_id: Optional[int] = None,
    duration_seconds: float = 0.0,
    detected_objects: Optional[List[str]] = None,
    confidence: float = 1.0,
    crop_bgr=None,
    details: Optional[Dict[str, Any]] = None,
) -> Event:
    """Persist an activity event and check for anomaly alert conditions."""
    now = datetime.datetime.now(datetime.timezone.utc)

    event = Event(
        event_type=event_type,
        visitor_id=visitor_id,
        camera_id=camera_id,
        zone_id=zone_id,
        track_id=track_id,
        timestamp=now,
        duration_seconds=duration_seconds,
        detected_objects=detected_objects or [],
        confidence=confidence,
        details=details or {},
    )
    session.add(event)
    session.commit()

    # Save thumbnail crop
    if crop_bgr is not None:
        thumb_path = save_event_thumbnail(crop_bgr, event.id)
        event.thumbnail_path = thumb_path
        session.commit()

    # Evaluate Anomaly Rules
    check_and_trigger_anomalies(session, event)

    return event


def check_and_trigger_anomalies(session: Session, event: Event):
    """Evaluate rule-based heuristics to trigger alerts."""
    alerts_to_create = []

    # 1. Restricted Zone Intrusion
    if event.event_type == "RESTRICTED_ZONE":
        alerts_to_create.append({
            "alert_type": "RESTRICTED_ZONE_INTRUSION",
            "severity": "CRITICAL",
            "message": f"Unauthorized person entered restricted zone on Camera #{event.camera_id}."
        })

    # 2. Loitering Anomaly
    if event.event_type == "LOITERING" or (event.duration_seconds and event.duration_seconds > 180):
        alerts_to_create.append({
            "alert_type": "PROLONGED_LOITERING",
            "severity": "HIGH",
            "message": f"Individual dwell time exceeded limit ({int(event.duration_seconds)}s) in Zone #{event.zone_id}."
        })

    # 3. Odd-Hour Activity (between 23:00 and 05:00 local time)
    hour = event.timestamp.hour
    if hour >= 23 or hour < 5:
        if event.event_type in ("ENTRY", "RESTRICTED_ZONE"):
            alerts_to_create.append({
                "alert_type": "ODD_HOUR_VISIT",
                "severity": "MEDIUM",
                "message": f"Unscheduled entry detected during night hours ({event.timestamp.strftime('%H:%M')} UTC)."
            })

    # 4. Unattended Object Left Behind
    if event.event_type == "OBJECT_LEFT_BEHIND":
        obj_name = event.detected_objects[0] if event.detected_objects else "package"
        alerts_to_create.append({
            "alert_type": "UNATTENDED_OBJECT",
            "severity": "HIGH",
            "message": f"Unattended {obj_name} detected with no person nearby for over 30 seconds."
        })

    # Save alerts and broadcast
    for a_data in alerts_to_create:
        alert = Alert(
            event_id=event.id,
            alert_type=a_data["alert_type"],
            severity=a_data["severity"],
            message=a_data["message"],
            status="NEW",
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        session.add(alert)
        session.commit()

        # Send to real-time subscribers
        broadcast_alert(alert.to_dict())
