"""Unit tests for Camera and Zone management APIs."""
import pytest
from web_server import app
from database import init_db
from services.auth_service import create_access_token


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


def test_list_cameras(client):
    res = client.get("/api/v2/cameras")
    assert res.status_code == 200
    data = res.get_json()
    assert "cameras" in data
    assert len(data["cameras"]) >= 1


def test_create_update_delete_camera(client, admin_headers):
    # 1. Create camera
    new_cam = {
        "name": "Test Perimeter Camera",
        "location": "North Wall",
        "stream_source": "rtsp://192.168.1.200:554/live",
        "stream_type": "RTSP",
        "purpose": "VISITOR",
        "fps": 20,
        "resolution": "1920x1080",
        "enabled": True,
    }
    create_res = client.post("/api/v2/cameras", headers=admin_headers, json=new_cam)
    assert create_res.status_code == 201
    cam_id = create_res.get_json()["camera"]["id"]

    # 2. Get camera details
    get_res = client.get(f"/api/v2/cameras/{cam_id}")
    assert get_res.status_code == 200
    assert get_res.get_json()["camera"]["name"] == "Test Perimeter Camera"
    assert get_res.get_json()["camera"]["purpose"] == "VISITOR"

    # 3. Create a zone with tripwire line
    new_zone = {
        "name": "North Gate Tripwire",
        "zone_type": "ENTRY_EXIT",
        "entry_line_coords": [[50, 350], [600, 350]],
        "polygon_coords": [[50, 300], [600, 300], [600, 400], [50, 400]],
        "dwell_threshold_seconds": 30,
    }
    zone_res = client.post(f"/api/v2/cameras/{cam_id}/zones", headers=admin_headers, json=new_zone)
    assert zone_res.status_code == 201
    zone_id = zone_res.get_json()["zone"]["id"]

    # 4. Update zone
    update_zone_res = client.put(f"/api/v2/zones/{zone_id}", headers=admin_headers, json={"name": "Updated North Tripwire"})
    assert update_zone_res.status_code == 200
    assert update_zone_res.get_json()["zone"]["name"] == "Updated North Tripwire"

    # 5. Delete zone
    del_zone_res = client.delete(f"/api/v2/zones/{zone_id}", headers=admin_headers)
    assert del_zone_res.status_code == 200

    # 6. Delete camera
    del_cam_res = client.delete(f"/api/v2/cameras/{cam_id}", headers=admin_headers)
    assert del_cam_res.status_code == 200
