"""Unit tests for Natural Language search parser and incident timeline compilation."""
import datetime
from services.search_service import parse_natural_language_query, generate_incident_timeline
from database.connection import get_session_factory


def test_natural_language_parser():
    q = "delivery person with a box near Gate 1 yesterday evening"
    filters = parse_natural_language_query(q)

    assert filters.get("category") == "Delivery"
    assert filters.get("object") == "box"
    assert filters.get("camera_id") == 1
    assert "time_start" in filters
    assert "time_end" in filters


def test_timeline_generation():
    session = get_session_factory()()
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        start = now - datetime.timedelta(days=7)
        end = now + datetime.timedelta(hours=1)

        timeline = generate_incident_timeline(session, time_start=start, time_end=end)
        assert "timeline" in timeline
        assert "summary" in timeline
        assert timeline["summary"]["total_events"] >= 1
    finally:
        session.close()
