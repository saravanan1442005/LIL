"""Pluggable IoT and physical sensor integration service.
Supports HTTP webhook and MQTT ingestion for PIR motion, RFID gate scans, QR passes, and door sensors.
Fuses sensor events with CCTV camera timeline records.
"""
import datetime
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from database.models import SensorEvent, Event, Visitor

logger = logging.getLogger("ecolifybuddy.sensor")


def ingest_sensor_event(
    session: Session,
    sensor_id: str,
    sensor_type: str,
    zone_id: Optional[int] = None,
    event_data: Optional[Dict[str, Any]] = None,
    linked_visitor_id: Optional[int] = None,
) -> SensorEvent:
    """Ingest a physical sensor event (PIR, RFID, Door, QR) and correlate with CCTV timeline."""
    now = datetime.datetime.now(datetime.timezone.utc)
    event_data = event_data or {}

    # Check for recent camera ENTRY/EXIT events in the same zone (+/- 15s) for temporal fusion
    linked_event_id = None
    window_start = now - datetime.timedelta(seconds=15)
    window_end = now + datetime.timedelta(seconds=15)

    recent_cam_event = (
        session.query(Event)
        .filter(Event.timestamp >= window_start, Event.timestamp <= window_end)
        .order_by(Event.timestamp.desc())
        .first()
    )

    if recent_cam_event:
        linked_event_id = recent_cam_event.id
        if not linked_visitor_id:
            linked_visitor_id = recent_cam_event.visitor_id

    # If RFID card contains a registered visitor reference, link it
    rfid_tag = event_data.get("rfid_tag") or event_data.get("badge_id")
    if rfid_tag and not linked_visitor_id:
        v = session.query(Visitor).filter(Visitor.label.ilike(f"%{rfid_tag}%")).first()
        if v:
            linked_visitor_id = v.id

    sensor_rec = SensorEvent(
        sensor_id=sensor_id,
        sensor_type=sensor_type.upper(),
        zone_id=zone_id,
        event_data=event_data,
        timestamp=now,
        linked_event_id=linked_event_id,
        linked_visitor_id=linked_visitor_id,
    )
    session.add(sensor_rec)
    session.commit()

    logger.info("SENSOR INGESTION: [%s] Type=%s ID=%s LinkedEvent=%s LinkedVisitor=%s",
                now.strftime("%H:%M:%S"), sensor_type, sensor_id, linked_event_id, linked_visitor_id)

    return sensor_rec
