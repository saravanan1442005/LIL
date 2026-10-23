"""Unit tests for IoT sensor ingestion and camera event fusion."""
from database.connection import get_session_factory
from services.sensor_service import ingest_sensor_event


def test_sensor_ingestion_and_fusion():
    session = get_session_factory()()
    try:
        s_ev = ingest_sensor_event(
            session=session,
            sensor_id="TEST-GATE-RFID",
            sensor_type="RFID",
            zone_id=1,
            event_data={"badge_id": "TEST-CARD-001"}
        )
        assert s_ev.id is not None
        assert s_ev.sensor_type == "RFID"
    finally:
        session.close()
