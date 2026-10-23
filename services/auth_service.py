"""Authentication and Role-Based Access Control (RBAC) service for EcoLifyBuddy.
Supports Admin, Security Officer, Viewer, and Auditor roles.
Password hashing with bcrypt; JWT token generation and validation.
"""
import os
import datetime
from functools import wraps
import bcrypt
import jwt
from flask import request, jsonify, g

JWT_SECRET = os.getenv("JWT_SECRET", "ecolifybuddy-super-secret-jwt-key-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60 * 8  # 8 hours default session

VALID_ROLES = {"Admin", "Security Officer", "Viewer", "Auditor"}


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify raw password against bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: int, email: str, role: str, full_name: str = "", expires_minutes: int = JWT_EXPIRATION_MINUTES) -> str:
    """Create signed JWT access token containing user identity and role claims."""
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": str(user_id),
        "user_id": user_id,
        "email": email,
        "role": role,
        "full_name": full_name,
        "iat": now,
        "exp": now + datetime.timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate JWT access token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired. Please sign in again.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid authentication token.")


def get_token_from_request() -> str | None:
    """Extract JWT token from Authorization header or cookie."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return request.cookies.get("auth_token")


def jwt_required(f):
    """Decorator to require valid JWT token on protected endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_request()
        if not token:
            return jsonify({"error": "Authentication required. Missing token."}), 401
        try:
            payload = decode_access_token(token)
            g.current_user = payload
        except ValueError as err:
            return jsonify({"error": str(err)}), 401
        return f(*args, **kwargs)
    return decorated


def roles_required(*allowed_roles):
    """Decorator to enforce RBAC permissions.
    Allowed roles: 'Admin', 'Security Officer', 'Viewer', 'Auditor'.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = get_token_from_request()
            if not token:
                return jsonify({"error": "Authentication required. Missing token."}), 401
            try:
                payload = decode_access_token(token)
                g.current_user = payload
            except ValueError as err:
                return jsonify({"error": str(err)}), 401

            user_role = payload.get("role")
            if user_role not in allowed_roles:
                return jsonify({
                    "error": "Forbidden. Insufficient permissions.",
                    "required_roles": list(allowed_roles),
                    "current_role": user_role
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator
