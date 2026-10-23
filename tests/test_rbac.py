"""Unit tests for JWT Authentication and Role-Based Access Control (RBAC)."""
import pytest
from web_server import app
from database import init_db
from database.connection import get_session_factory
from database.models import User
from services.auth_service import hash_password, verify_password, create_access_token, decode_access_token


@pytest.fixture(scope="module")
def client():
    app.config["TESTING"] = True
    init_db()
    with app.test_client() as c:
        yield c


def test_password_hashing():
    raw = "SecureSecret123!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_generation_and_decoding():
    token = create_access_token(user_id=42, email="officer@example.com", role="Security Officer", full_name="John Doe")
    assert isinstance(token, str)
    payload = decode_access_token(token)
    assert payload["user_id"] == 42
    assert payload["email"] == "officer@example.com"
    assert payload["role"] == "Security Officer"


def test_login_endpoint_success(client):
    # Default seeded admin
    res = client.post("/api/v2/auth/login", json={"email": "admin@example.com", "password": "Admin@12345"})
    assert res.status_code == 200
    data = res.get_json()
    assert "token" in data
    assert data["user"]["email"] == "admin@example.com"
    assert data["user"]["role"] == "Admin"


def test_login_endpoint_invalid_credentials(client):
    res = client.post("/api/v2/auth/login", json={"email": "admin@example.com", "password": "WrongPassword"})
    assert res.status_code == 401


def test_rbac_admin_vs_viewer_permissions(client):
    admin_token = create_access_token(1, "admin@example.com", "Admin")
    viewer_token = create_access_token(2, "viewer@example.com", "Viewer")

    # Viewer attempting to create a user -> 403 Forbidden
    res_viewer = client.post(
        "/api/v2/auth/users",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"email": "newbie@example.com", "password": "Pass", "full_name": "New", "role": "Viewer"}
    )
    assert res_viewer.status_code == 403

    # Admin attempting to create a user -> 201 Created (or 409 if already exists)
    res_admin = client.post(
        "/api/v2/auth/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "officer_test@example.com", "password": "SecurePass123", "full_name": "Test Officer", "role": "Security Officer"}
    )
    assert res_admin.status_code in (201, 409)
