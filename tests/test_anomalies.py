"""Unit tests for rule-based anomaly detection (loitering, restricted zone intrusion, odd hours)."""
from database.connection import get_session_factory
from database.models import Alert
from services.event_service import log_event


def test_restricted_zone_anomaly_triggers_critical_alert():
    session = get_session_factory()()
    try:
        prev_alert_count = session.query(Alert).filter(Alert.alert_type == "RESTRICTED_ZONE_INTRUSION").count()

        event = log_event(
            session=session,
            event_type="RESTRICTED_ZONE",
            camera_id=1,
            zone_id=1,
            track_id=999,
            duration_seconds=15.0,
        )
        assert event.id is not None

        new_alert_count = session.query(Alert).filter(Alert.alert_type == "RESTRICTED_ZONE_INTRUSION").count()
        assert new_alert_count > prev_alert_count
    finally:
        session.close()


def test_loitering_anomaly_triggers_alert():
    session = get_session_factory()()
    try:
        prev_loitering_count = session.query(Alert).filter(Alert.alert_type == "PROLONGED_LOITERING").count()

        event = log_event(
            session=session,
            event_type="LOITERING",
            camera_id=1,
            zone_id=1,
            track_id=998,
            duration_seconds=200.0,
        )
        assert event.id is not None

        new_loitering_count = session.query(Alert).filter(Alert.alert_type == "PROLONGED_LOITERING").count()
        assert new_loitering_count > prev_loitering_count
    finally:
        session.close()
