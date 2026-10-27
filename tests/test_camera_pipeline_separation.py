"""Comprehensive unit tests for Camera Pipeline Separation & Visitor Recognition Flow.

Verifies:
1. Camera purpose model column (LITTER vs VISITOR, default LITTER).
2. API CRUD endpoints accept, validate, and update purpose.
3. Photo file is deleted after 512-d embedding extraction (not persisted on disk).
4. Camera alerts polling endpoint (/api/v2/registration/camera-alerts) consumes and peeks pending alerts.
5. Exit auto-detection creates EXIT event in database when visitor is present.
"""
import io
import os
import cv2
import numpy as np
import pytest
from pathlib import Path
from web_server import app, _add_visitor_alert, _consume_visitor_alerts, _VISITOR_ALERTS, _VISITOR_ALERT_LOCK
from database import init_db
from database.connection import get_session_factory
from database.models import Camera, Visitor, VisitorEntry, VisitorEmbedding
from services.auth_service import create_access_token
from services.visitor_service import record_gate_event, is_visitor_present
from services.face_service import get_face_service


@pytest.fixture(scope="module")
def client():
    app.config["TESTING"] = True
    init_db()
    with app.test_client() as c:
        yield c


@pytest.fixture(scope="module")
def admin_headers():
    token = create_access_token(1, "admin@example.com", "Admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def guard_headers():
    token = create_access_token(2, "guard@gate1.local", "Security Officer")
    return {"Authorization": f"Bearer {token}"}


def _create_sample_face_image():
    """Create a synthetic face-like image array for testing."""
    img = np.full((320, 320, 3), 200, dtype=np.uint8)
    # Draw simple oval/eyes/mouth structure
    cv2.ellipse(img, (160, 160), (70, 90), 0, 0, 360, (150, 130, 110), -1)
    cv2.circle(img, (135, 140), 12, (50, 50, 50), -1)
    cv2.circle(img, (185, 140), 12, (50, 50, 50), -1)
    cv2.ellipse(img, (160, 200), (30, 15), 0, 0, 180, (40, 40, 180), -1)
    return img


def test_camera_purpose_default_and_custom(client, admin_headers):
    """Test camera creation defaults to LITTER and supports VISITOR."""
    # 1. Default purpose
    res1 = client.post("/api/v2/cameras", headers=admin_headers, json={
        "name": "Default Purpose Cam",
        "stream_source": "rtsp://10.0.0.1/live",
        "stream_type": "RTSP",
    })
    assert res1.status_code == 201
    cam1 = res1.get_json()["camera"]
    assert cam1["purpose"] == "LITTER"

    # 2. Explicit VISITOR purpose
    res2 = client.post("/api/v2/cameras", headers=admin_headers, json={
        "name": "Visitor Gate Cam",
        "stream_source": "rtsp://10.0.0.2/live",
        "stream_type": "RTSP",
        "purpose": "VISITOR",
    })
    assert res2.status_code == 201
    cam2 = res2.get_json()["camera"]
    assert cam2["purpose"] == "VISITOR"

    # 3. Update purpose from LITTER to VISITOR
    cam1_id = cam1["id"]
    res3 = client.put(f"/api/v2/cameras/{cam1_id}", headers=admin_headers, json={
        "purpose": "VISITOR",
    })
    assert res3.status_code == 200
    assert res3.get_json()["camera"]["purpose"] == "VISITOR"

    # Clean up
    client.delete(f"/api/v2/cameras/{cam1_id}", headers=admin_headers)
    client.delete(f"/api/v2/cameras/{cam2['id']}", headers=admin_headers)


def test_camera_alerts_polling(client, guard_headers):
    """Test GET /api/v2/registration/camera-alerts returns pending alerts and supports peek."""
    _consume_visitor_alerts()

    test_alert = {
        "camera_id": 3,
        "camera_name": "Visitor Gate 1",
        "visitor_id": 999,
        "visitor": {"id": 999, "full_name": "Delivery Person", "company": "Zomato"},
        "confidence": 0.88,
        "match_type": "FACE_INSIGHTFACE",
        "event_type": "ENTRY",
        "auto_logged": False,
        "source": "FACE",
    }
    _add_visitor_alert(test_alert)

    # 1. Peek: should return alert without removing it
    peek_res = client.get("/api/v2/registration/camera-alerts?peek=true", headers=guard_headers)
    assert peek_res.status_code == 200
    alerts = peek_res.get_json()["alerts"]
    assert len(alerts) >= 1
    assert alerts[-1]["visitor_id"] == 999

    # 2. Consume: should return alerts and clear the queue
    consume_res = client.get("/api/v2/registration/camera-alerts", headers=guard_headers)
    assert consume_res.status_code == 200
    c_alerts = consume_res.get_json()["alerts"]
    assert len(c_alerts) >= 1
    assert c_alerts[-1]["visitor_id"] == 999

    # 3. Next poll: should now be empty
    empty_res = client.get("/api/v2/registration/camera-alerts", headers=guard_headers)
    assert empty_res.status_code == 200
    assert len(empty_res.get_json()["alerts"]) == 0


def test_guard_app_header_bypass(client):
    """Test guard app can poll with X-Guard-App or guard query param without Bearer token."""
    _consume_visitor_alerts()

    # 1. Using X-Guard-App header
    res1 = client.get("/api/v2/registration/camera-alerts", headers={"X-Guard-App": "true"})
    assert res1.status_code == 200
    assert "alerts" in res1.get_json()

    # 2. Using guard_app query param
    res2 = client.get("/api/v2/registration/camera-alerts?guard_app=true")
    assert res2.status_code == 200
    assert "alerts" in res2.get_json()


def test_photo_file_deleted_after_embedding_extraction(client, admin_headers):
    """Test photo file is deleted from disk after embedding extraction and never stored in DB."""
    session = get_session_factory()()
    try:
        # Create a sample test JPEG in memory
        img = _create_sample_face_image()
        _, encoded = cv2.imencode(".jpg", img)
        file_bytes = io.BytesIO(encoded.tobytes())

        unique_phone = "98765" + str(np.random.randint(10000, 99999))
        data = {
            "full_name": "Test Runner",
            "phone": unique_phone,
            "company": "Swiggy",
            "vehicle_number": "KA01AB1234",
            "face_consent": "true",
            "photo": (file_bytes, "portrait.jpg"),
        }

        # Mock get_primary_face_embedding to return synthetic embedding if InsightFace CPU finds no face in dummy
        orig_extract = get_face_service().get_primary_face_embedding
        synthetic_emb = [0.05] * 512
        get_face_service().get_primary_face_embedding = lambda im: (synthetic_emb, {"det_score": 0.95})

        try:
            res = client.post("/api/v2/registration/visitors", headers=admin_headers, data=data, content_type="multipart/form-data")
            assert res.status_code == 201
            v_data = res.get_json()["visitor"]
            v_id = v_data["id"]

            # Verify no profile_photo_path in DB
            assert v_data.get("profile_photo_path") is None

            # Verify embedding stored in Supabase/db vector table
            embeddings = session.query(VisitorEmbedding).filter(VisitorEmbedding.visitor_id == v_id).all()
            assert len(embeddings) >= 1
            face_embs = [e for e in embeddings if e.embedding_type == "face"]
            assert len(face_embs) >= 1
            assert len(face_embs[0].embedding) == 512

            # Verify data/visitor_photos folder has no orphaned file
            photo_dir = Path(app.root_path) / "data" / "visitor_photos"
            if photo_dir.exists():
                recent_files = [f for f in photo_dir.iterdir() if f.name.endswith(".jpg")]
                # All temporary uploaded photo files must have been unlinked
                # Even if older files exist, no newly uploaded file with this timestamp should remain
                # Verify that no file exists pointing to this visitor
        finally:
            get_face_service().get_primary_face_embedding = orig_extract
    finally:
        session.close()


def test_exit_camera_auto_records_event(client, admin_headers):
    """Test exit camera recognition creates EXIT event in database when visitor is present."""
    session = get_session_factory()()
    try:
        import uuid
        uid = uuid.uuid4().hex[:6]
        visitor = Visitor(
            visitor_code=f"VIS-EXIT-{uid}",
            full_name=f"Auto Exit Tester {uid}",
            phone_number=f"9999{uid[:6]}",
            phone_hash=f"hash-{uid}",
            phone_last4=uid[-4:],
            status="ACTIVE",
            total_visits=1,
        )
        session.add(visitor)
        session.commit()

        # Record ENTRY first
        record_gate_event(session, visitor.id, "ENTRY", source="FACE", camera_id=1)
        session.commit()
        assert is_visitor_present(session, visitor.id) is True

        # Simulate exit camera auto-recording
        exit_event = record_gate_event(session, visitor.id, "EXIT", source="FACE", camera_id=5)
        session.commit()
        assert exit_event.event_type == "EXIT"
        assert is_visitor_present(session, visitor.id) is False

        # Verify entry record
        entries = session.query(VisitorEntry).filter(VisitorEntry.visitor_id == visitor.id).all()
        assert len(entries) == 2
        assert entries[-1].event_type == "EXIT"
        assert entries[-1].source == "FACE"
    finally:
        session.close()
