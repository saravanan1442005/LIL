import uuid
import pytest  # pyrefly: ignore[missing-import]  # type: ignore
from web_server import app
from database.connection import get_session_factory
from database.models import Visitor
from services.visitor_service import is_visitor_present


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_voice_parse_duration_hours_and_minutes(client):
    """Test voice parse handles both hours and minutes in Tamil & English."""
    # Test 1: Tamil hour
    resp = client.post("/api/v2/registration/kiosk/voice-parse", json={
        "transcript": "என் பெயர் முருகன் எலக்ட்ரீசியன் 1 மணி நேரம்",
        "language": "ta-IN"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    extracted = data["extracted"]
    assert extracted["name"] == "முருகன்"
    assert extracted["purpose"] == "Electrician"
    assert extracted["expected_duration_minutes"] == 60

    # Test 2: English hours
    resp2 = client.post("/api/v2/registration/kiosk/voice-parse", json={
        "transcript": "Hello I am Alex from Swiggy 2 hours",
        "language": "en-US"
    })
    assert resp2.status_code == 200
    ext2 = resp2.get_json()["extracted"]
    assert ext2["name"] == "Alex"
    assert ext2["company"] == "Swiggy"
    assert ext2["expected_duration_minutes"] == 120

    # Test 3: Tamil plural minutes (10 நிமிடங்கள்)
    resp3 = client.post("/api/v2/registration/kiosk/voice-parse", json={
        "transcript": "என் பெயர் கார்த்திக் ஸ்விக்கி 10 நிமிடங்கள்",
        "language": "ta-IN"
    })
    assert resp3.status_code == 200
    assert resp3.get_json()["extracted"]["expected_duration_minutes"] == 10

    # Test 4: Tamil half hour (அரை மணி நேரம்)
    resp4 = client.post("/api/v2/registration/kiosk/voice-parse", json={
        "transcript": "என் பெயர் குமார் டெலிவரி அரை மணி நேரம்",
        "language": "ta-IN"
    })
    assert resp4.status_code == 200
    assert resp4.get_json()["extracted"]["expected_duration_minutes"] == 30

    # Test 5: Verify AI asks for stay duration when duration is missing
    resp5 = client.post("/api/v2/registration/kiosk/voice-parse", json={
        "transcript": "என் பெயர் விஜய்",
        "language": "ta-IN"
    })
    assert resp5.status_code == 200
    data5 = resp5.get_json()
    assert "நேரம்" in data5["reply_tamil"]

    # Test 6: English days parsing (e.g. "I will be here for 2 days")
    resp6 = client.post("/api/v2/registration/kiosk/voice-parse", json={
        "transcript": "I will be here for 2 days",
        "language": "en-US"
    })
    assert resp6.status_code == 200
    assert resp6.get_json()["extracted"]["expected_duration_minutes"] == 2880

    # Test 7: Tamil days parsing (e.g. "நான் 2 நாட்கள் இருப்பேன்")
    resp7 = client.post("/api/v2/registration/kiosk/voice-parse", json={
        "transcript": "நான் 2 நாட்கள் இருப்பேன்",
        "language": "ta-IN"
    })
    assert resp7.status_code == 200
    assert resp7.get_json()["extracted"]["expected_duration_minutes"] == 2880


def test_kiosk_identify_face_no_image(client):
    """Identify face endpoint validates input."""
    resp = client.post("/api/v2/registration/kiosk/identify-face", json={})
    assert resp.status_code == 400


def test_kiosk_quick_checkin_flow(client):
    """Test returning visitor quick checkin updates duration and logs entry."""
    session = get_session_factory()()
    try:
        uid = uuid.uuid4().hex[:6]
        visitor = Visitor(
            visitor_code=f"VIS-QK-{uid}",
            full_name=f"Quick Visitor {uid}",
            phone_number=f"9876{uid[:6]}",
            phone_hash=f"hash-qk-{uid}",
            phone_last4=uid[-4:],
            status="ACTIVE",
        )
        session.add(visitor)
        session.commit()

        # Perform quick checkin for 45 minutes
        resp = client.post("/api/v2/registration/kiosk/quick-checkin", json={
            "visitor_id": visitor.id,
            "expected_duration_minutes": 45,
            "company": "Swiggy"
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "CHECKED_IN"
        assert data["expected_duration_minutes"] == 45
        assert is_visitor_present(session, visitor.id) is True

        # Second tap checks out
        resp_out = client.post("/api/v2/registration/kiosk/quick-checkin", json={
            "visitor_id": visitor.id
        })
        assert resp_out.status_code == 200
        assert resp_out.get_json()["status"] == "CHECKED_OUT"
        assert is_visitor_present(session, visitor.id) is False
    finally:
        session.close()


def test_confirmation_intent_classification(client):
    """Test voice parse returns correct confirmation_intent for Tamil & English."""
    from services.voice_agent_service import classify_confirmation_intent

    # Positive Tamil & English
    assert classify_confirmation_intent("ஆமாம், உள்ளே நுழைகிறேன்") is True
    assert classify_confirmation_intent("சரி, வெளியேறுகிறேன்") is True
    assert classify_confirmation_intent("ஆம்") is True
    assert classify_confirmation_intent("Yes, entering now") is True
    assert classify_confirmation_intent("Sure, confirm") is True

    # Negative Tamil & English
    assert classify_confirmation_intent("இல்லை வேண்டாம்") is False
    assert classify_confirmation_intent("நோ, நுழையவில்லை") is False
    assert classify_confirmation_intent("வேண்டாம் cancel") is False
    assert classify_confirmation_intent("No, not now") is False

    # Via API endpoint
    resp_pos = client.post("/api/v2/registration/kiosk/voice-parse", json={
        "transcript": "ஆமாம், உள்ளே போகிறேன்",
        "language": "ta-IN"
    })
    assert resp_pos.status_code == 200
    assert resp_pos.get_json()["confirmation_intent"] == "positive"

    resp_neg = client.post("/api/v2/registration/kiosk/voice-parse", json={
        "transcript": "இல்லை வேண்டாம்",
        "language": "ta-IN"
    })
    assert resp_neg.status_code == 200
    assert resp_neg.get_json()["confirmation_intent"] == "negative"


def test_entry_gate_strict_duplicate_rejection(client):
    """Test entry gate strictly rejects duplicate check-in with 409 when visitor is already present."""
    session = get_session_factory()()
    try:
        uid = uuid.uuid4().hex[:6]
        visitor = Visitor(
            visitor_code=f"VIS-DUP-{uid}",
            full_name=f"Duplicate Visitor {uid}",
            phone_number=f"9871{uid[:6]}",
            phone_hash=f"hash-dup-{uid}",
            phone_last4=uid[-4:],
            status="ACTIVE",
        )
        session.add(visitor)
        session.commit()

        # 1. First entry
        resp1 = client.post("/api/v2/registration/kiosk/quick-checkin", json={
            "visitor_id": visitor.id,
            "gate_mode": "entry",
            "expected_duration_minutes": 60,
        })
        assert resp1.status_code == 201
        assert resp1.get_json()["status"] == "CHECKED_IN"
        assert is_visitor_present(session, visitor.id) is True

        # 2. Second entry attempt must be rejected with 409 ALREADY_ENTERED
        resp2 = client.post("/api/v2/registration/kiosk/quick-checkin", json={
            "visitor_id": visitor.id,
            "gate_mode": "entry",
        })
        assert resp2.status_code == 409
        data2 = resp2.get_json()
        assert data2["status"] == "ALREADY_ENTERED"
        assert "ஏற்கனவே உள்ளே நுழைந்துவிட்டீர்கள்" in data2["reply_tamil"]
        assert is_visitor_present(session, visitor.id) is True
    finally:
        session.close()


def test_exit_gate_strict_rejection_when_not_present(client):
    """Test exit gate strictly rejects checkout with 404 when visitor is not inside."""
    session = get_session_factory()()
    try:
        uid = uuid.uuid4().hex[:6]
        visitor = Visitor(
            visitor_code=f"VIS-EXT-{uid}",
            full_name=f"Exit Visitor {uid}",
            phone_number=f"9872{uid[:6]}",
            phone_hash=f"hash-ext-{uid}",
            phone_last4=uid[-4:],
            status="ACTIVE",
        )
        session.add(visitor)
        session.commit()

        # Visitor has never entered; attempting exit must return 404 NOT_PRESENT
        resp = client.post("/api/v2/registration/kiosk/quick-checkin", json={
            "visitor_id": visitor.id,
            "gate_mode": "exit",
        })
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["status"] == "NOT_PRESENT"
        assert "செயலில் உள்ள என்ட்ரி இல்லை" in data["reply_tamil"]
        assert is_visitor_present(session, visitor.id) is False
    finally:
        session.close()

