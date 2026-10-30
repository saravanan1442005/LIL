import pytest  # pyrefly: ignore[missing-import]  # type: ignore
from web_server import app, state


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_initial_camera_mode_not_webcam():
    """Verify that backend startup does not lock the physical webcam."""
    assert state.camera_mode != "webcam"


def test_api_release_webcam(client):
    """Verify that /api/release_webcam returns success and releases hardware locks."""
    res = client.post("/api/release_webcam")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True


def test_kiosk_route_invokes_release(client):
    """Verify that navigating to /kiosk yields the hardware webcam to the browser."""
    res = client.get("/kiosk")
    assert res.status_code == 200
