"""Authentication blueprint (/api/v2/auth):
- User login with bcrypt verification and JWT generation
- Session inspection (/me)
- User administration with RBAC enforcement (Admin only)
"""
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from database.connection import get_session_factory
from database.models import User
from services.auth_service import (
    verify_password, hash_password, create_access_token,
    jwt_required, roles_required, VALID_ROLES
)
from services.audit_service import log_audit_event

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v2/auth")


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    session: Session = get_session_factory()()
    try:
        user = session.query(User).filter(User.email == email, User.is_active.is_(True)).first()
        if not user or not verify_password(password, user.password_hash):
            return jsonify({"error": "Invalid email or password."}), 401

        token = create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
            full_name=user.full_name
        )

        log_audit_event(
            session=session,
            action="LOGIN",
            target_type="User",
            target_id=str(user.id),
            user_id=user.id,
            user_email=user.email,
            role=user.role,
            details={"ip": request.remote_addr}
        )

        resp = jsonify({
            "token": token,
            "user": user.to_dict()
        })
        resp.set_cookie("auth_token", token, httponly=True, samesite="Lax", max_age=3600 * 8)
        return resp
    finally:
        session.close()


@auth_bp.route("/logout", methods=["POST"])
def logout():
    resp = jsonify({"message": "Logged out successfully."})
    resp.delete_cookie("auth_token")
    return resp


@auth_bp.route("/me", methods=["GET"])
@jwt_required
def me():
    session: Session = get_session_factory()()
    try:
        user_id = g.current_user.get("user_id")
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({"error": "User not found."}), 404
        return jsonify({
            "user": user.to_dict(),
            "claims": g.current_user
        })
    finally:
        session.close()


@auth_bp.route("/users", methods=["GET"])
@roles_required("Admin", "Auditor")
def list_users():
    session: Session = get_session_factory()()
    try:
        users = session.query(User).order_by(User.id.asc()).all()
        return jsonify({"users": [u.to_dict() for u in users]})
    finally:
        session.close()


@auth_bp.route("/users", methods=["POST"])
@roles_required("Admin")
def create_user():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()
    role = data.get("role", "Viewer").strip()

    if not email or not password or not full_name:
        return jsonify({"error": "Email, password, and full name are required."}), 400

    if role not in VALID_ROLES:
        return jsonify({"error": f"Invalid role. Must be one of: {sorted(list(VALID_ROLES))}"}), 400

    session: Session = get_session_factory()()
    try:
        existing = session.query(User).filter(User.email == email).first()
        if existing:
            return jsonify({"error": "A user with this email already exists."}), 409

        new_user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
            is_active=True
        )
        session.add(new_user)
        session.commit()

        log_audit_event(
            session=session,
            action="CREATE_USER",
            target_type="User",
            target_id=str(new_user.id),
            details={"email": email, "role": role}
        )

        return jsonify({"user": new_user.to_dict()}), 201
    finally:
        session.close()
