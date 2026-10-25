"""Guard-led visitor enrollment, lookup, and confirmed entry logging."""

import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, request, send_from_directory
from sqlalchemy.orm import Session
from werkzeug.utils import secure_filename

from database.connection import get_session_factory
from database.models import OTPChallenge, Visitor, VisitorEntry
from services.audit_service import log_audit_event
from services.auth_service import roles_required
from services.reid_service import get_reid_extractor
from services.vector_store import get_vector_store
from services.anpr_service import ANPRService, aggregate_plate_reads

registration_bp = Blueprint("registration", __name__, url_prefix="/api/v2/registration")
OTP_TTL_MINUTES = 5
MAX_OTP_ATTEMPTS = 5
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
_anpr_service = None


def _phone_hash(phone: str) -> str:
    normalized = "".join(ch for ch in phone if ch.isdigit())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _normalize_phone(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit())


def _otp_hash(otp: str) -> str:
    secret = os.getenv("JWT_SECRET", "ecolifybuddy-development-secret")
    return hmac.new(secret.encode("utf-8"), otp.encode("utf-8"), hashlib.sha256).hexdigest()


def _utc(value: datetime) -> datetime:
    """Normalize SQLite's naive timestamps and Postgres aware timestamps."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _send_otp(phone: str, otp: str) -> None:
    """Use a configured provider later; development mode logs instead of sending."""
    if os.getenv("OTP_PROVIDER", "console").lower() != "console":
        raise RuntimeError("OTP provider is configured but no provider adapter is installed.")
    current_app.logger.info("Development OTP for phone ending %s: %s", phone[-4:], otp)


def _get_anpr_service() -> ANPRService:
    global _anpr_service
    if _anpr_service is None:
        _anpr_service = ANPRService(os.getenv("ANPR_MODEL_PATH") or None)
    return _anpr_service


def _save_photo(upload) -> str:
    filename = secure_filename(upload.filename or "")
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Photo must be JPG, JPEG, PNG, or WEBP.")
    directory = Path(current_app.root_path) / "data" / "visitor_photos"
    directory.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}.{extension}"
    upload.save(directory / stored)
    return f"visitor_photos/{stored}"


@registration_bp.route("/photos/<path:filename>", methods=["GET"])
@roles_required("Admin", "Security Officer")
def visitor_photo(filename):
    safe_name = Path(filename).name
    return send_from_directory(Path(current_app.root_path) / "data" / "visitor_photos", safe_name)


@registration_bp.route("/anpr/read", methods=["POST"])
@roles_required("Admin", "Security Officer")
def read_plate():
    """Analyze one high-resolution frame without making an admission decision."""
    upload = request.files.get("frame")
    if not upload:
        return jsonify({"error": "A frame image is required."}), 400
    import cv2
    import numpy as np

    raw = np.frombuffer(upload.read(), dtype=np.uint8)
    frame = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if frame is None:
        return jsonify({"error": "The frame image could not be decoded."}), 400

    profile = {
        "roi": request.form.get("roi"),
        "detector_threshold": request.form.get("detector_threshold", 0.35),
    }
    if profile["roi"]:
        try:
            profile["roi"] = [int(value.strip()) for value in profile["roi"].split(",")]
            if len(profile["roi"]) != 4:
                raise ValueError
        except ValueError:
            return jsonify({"error": "roi must contain x1,y1,x2,y2 integer coordinates."}), 400
    else:
        profile["roi"] = None

    result = _get_anpr_service().read_frame(frame, profile)
    for read in result.get("reads", []):
        read["matches"] = []
        with_session = get_session_factory()()
        try:
            matches = (
                with_session.query(Visitor)
                .filter(Visitor.status == "ACTIVE", Visitor.vehicle_number == read["normalized_text"])
                .limit(5)
                .all()
            )
            read["matches"] = [visitor.to_dict() for visitor in matches]
        finally:
            with_session.close()
    result["requires_guard_confirmation"] = True
    return jsonify(result)


@registration_bp.route("/start-otp", methods=["POST"])
@roles_required("Admin", "Security Officer")
def start_otp():
    data = request.get_json(silent=True) or {}
    phone = _normalize_phone(str(data.get("phone", "")))
    if len(phone) < 10:
        return jsonify({"error": "Enter a valid phone number."}), 400

    otp = f"{secrets.randbelow(1_000_000):06d}"
    session: Session = get_session_factory()()
    try:
        challenge = OTPChallenge(
            phone_hash=_phone_hash(phone),
            otp_hash=_otp_hash(otp),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES),
        )
        session.add(challenge)
        session.commit()
        _send_otp(phone, otp)
        response = {
            "message": "OTP sent.",
            "expires_in_seconds": OTP_TTL_MINUTES * 60,
            "phone_last4": phone[-4:],
        }
        if os.getenv("OTP_PROVIDER", "console").lower() == "console":
            response["development_otp"] = otp
        return jsonify(response), 201
    finally:
        session.close()


@registration_bp.route("/verify-otp", methods=["POST"])
@roles_required("Admin", "Security Officer")
def verify_otp():
    data = request.get_json(silent=True) or {}
    phone = _normalize_phone(str(data.get("phone", "")))
    otp = str(data.get("otp", "")).strip()
    if len(phone) < 10 or len(otp) != 6 or not otp.isdigit():
        return jsonify({"error": "Phone number and six-digit OTP are required."}), 400

    session: Session = get_session_factory()()
    try:
        challenge = (
            session.query(OTPChallenge)
            .filter(OTPChallenge.phone_hash == _phone_hash(phone), OTPChallenge.verified_at.is_(None))
            .order_by(OTPChallenge.created_at.desc())
            .first()
        )
        now = datetime.now(timezone.utc)
        if not challenge or _utc(challenge.expires_at) < now:
            return jsonify({"error": "OTP is missing or expired."}), 400
        if challenge.attempts >= MAX_OTP_ATTEMPTS:
            return jsonify({"error": "Too many OTP attempts. Request a new OTP."}), 429
        challenge.attempts += 1
        if not hmac.compare_digest(challenge.otp_hash, _otp_hash(otp)):
            session.commit()
            return jsonify({"error": "Invalid OTP.", "attempts_remaining": MAX_OTP_ATTEMPTS - challenge.attempts}), 400
        challenge.verified_at = now
        session.commit()
        return jsonify({"verified": True, "phone_last4": phone[-4:]})
    finally:
        session.close()


@registration_bp.route("/visitors", methods=["POST"])
@roles_required("Admin", "Security Officer")
def register_visitor():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    phone = _normalize_phone(str(data.get("phone", "")))
    phone_hash = _phone_hash(phone)
    if len(phone) < 10:
        return jsonify({"error": "A verified phone number is required."}), 400
    if not data.get("full_name", "").strip():
        return jsonify({"error": "Full name is required."}), 400

    session: Session = get_session_factory()()
    try:
        verified = (
            session.query(OTPChallenge)
            .filter(
                OTPChallenge.phone_hash == phone_hash,
                OTPChallenge.verified_at.is_not(None),
                OTPChallenge.verified_at >= datetime.now(timezone.utc) - timedelta(minutes=15),
            )
            .order_by(OTPChallenge.verified_at.desc())
            .first()
        )
        if not verified:
            return jsonify({"error": "Verify the phone number with OTP before registration."}), 400
        existing = session.query(Visitor).filter(Visitor.phone_hash == phone_hash, Visitor.status != "REDACTED").first()
        if existing:
            return jsonify({"error": "A visitor with this phone number already exists.", "visitor": existing.to_dict()}), 409

        visitor = Visitor(
            visitor_code=f"VIS-{10001 + session.query(Visitor).count()}",
            full_name=data.get("full_name", "").strip(),
            phone_hash=phone_hash,
            phone_last4=phone[-4:],
            phone_verified=True,
            company=(data.get("company") or "").strip() or None,
            vehicle_number=(data.get("vehicle_number") or "").strip().upper() or None,
            plate_enrolled=bool((data.get("vehicle_number") or "").strip()),
            category=(data.get("category") or "Unknown").strip(),
            label=(data.get("label") or "").strip() or None,
            consent_status="GRANTED" if str(data.get("face_consent", "")).lower() == "true" else "DECLINED",
            status="ACTIVE",
        )
        photo = request.files.get("photo")
        if photo:
            visitor.profile_photo_path = _save_photo(photo)
        session.add(visitor)
        session.commit()

        if visitor.profile_photo_path:
            photo_path = Path(current_app.root_path) / "data" / visitor.profile_photo_path
            import cv2
            image = cv2.imread(str(photo_path))
            if image is not None:
                embedding = get_reid_extractor().extract_embedding(image)
                get_vector_store(session).add_embedding(visitor.id, embedding, embedding_type="reid", confidence=1.0)
                session.commit()
                visitor.plate_enrolled = bool(visitor.vehicle_number)
                session.commit()

        log_audit_event(session, "REGISTER_VISITOR", "Visitor", str(visitor.id), details={"source": "GUARD"})
        return jsonify({"visitor": visitor.to_dict(), "message": "Visitor registered successfully."}), 201
    except ValueError as error:
        session.rollback()
        return jsonify({"error": str(error)}), 400
    finally:
        session.close()


@registration_bp.route("/visitors/<int:visitor_id>/plate", methods=["POST"])
@roles_required("Admin", "Security Officer")
def enroll_plate(visitor_id: int):
    data = request.get_json(silent=True) or {}
    vehicle_number = "".join(str(data.get("vehicle_number", "")).upper().split())
    if len(vehicle_number) < 4:
        return jsonify({"error": "A valid vehicle number is required."}), 400
    session: Session = get_session_factory()()
    try:
        visitor = session.query(Visitor).filter(Visitor.id == visitor_id).first()
        if not visitor:
            return jsonify({"error": "Visitor not found."}), 404
        visitor.vehicle_number = vehicle_number
        visitor.plate_enrolled = True
        session.commit()
        log_audit_event(session, "ENROLL_PLATE", "Visitor", str(visitor_id), details={"vehicle_number": vehicle_number})
        return jsonify({"visitor": visitor.to_dict()})
    finally:
        session.close()


@registration_bp.route("/search", methods=["GET"])
@roles_required("Admin", "Security Officer")
def search_candidates():
    last4 = "".join(ch for ch in request.args.get("last4", "") if ch.isdigit())
    query = request.args.get("q", "").strip().upper()
    if len(last4) != 4 and not query:
        return jsonify({"error": "Provide exactly four phone digits or a name/plate search."}), 400
    session: Session = get_session_factory()()
    try:
        candidates = session.query(Visitor).filter(Visitor.status == "ACTIVE")
        if last4:
            candidates = candidates.filter(Visitor.phone_last4 == last4)
        else:
            pattern = f"%{query}%"
            candidates = candidates.filter(
                (Visitor.full_name.ilike(pattern))
                | (Visitor.vehicle_number.ilike(pattern))
                | (Visitor.company.ilike(pattern))
            )
        return jsonify({"visitors": [visitor.to_dict() for visitor in candidates.order_by(Visitor.last_seen.desc()).limit(20).all()]})
    finally:
        session.close()


@registration_bp.route("/match", methods=["POST"])
@roles_required("Admin", "Security Officer")
def match_candidate():
    """Return candidates for guard review; never creates an entry automatically."""
    vehicle_number = "".join(str(request.form.get("vehicle_number", "")).upper().split())
    session: Session = get_session_factory()()
    try:
        candidates = {}
        if vehicle_number:
            matches = (
                session.query(Visitor)
                .filter(Visitor.status == "ACTIVE", Visitor.vehicle_number == vehicle_number)
                .all()
            )
            for visitor in matches:
                candidates[visitor.id] = {"visitor": visitor.to_dict(), "source": "PLATE", "confidence": 1.0}

        photo = request.files.get("photo")
        if photo:
            filename = secure_filename(photo.filename or "")
            extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if extension not in ALLOWED_IMAGE_EXTENSIONS:
                return jsonify({"error": "Photo must be JPG, JPEG, PNG, or WEBP."}), 400
            import cv2
            import numpy as np
            data = np.frombuffer(photo.read(), dtype=np.uint8)
            image = cv2.imdecode(data, cv2.IMREAD_COLOR)
            if image is None:
                return jsonify({"error": "The uploaded image could not be read."}), 400
            embedding = get_reid_extractor().extract_embedding(image)
            for visitor_id, confidence in get_vector_store(session).search_similar(
                embedding, top_k=5, threshold=0.68, embedding_type="reid"
            ):
                visitor = session.query(Visitor).filter(Visitor.id == visitor_id, Visitor.status == "ACTIVE").first()
                if visitor:
                    existing = candidates.get(visitor_id)
                    if not existing or confidence > existing["confidence"]:
                        candidates[visitor_id] = {
                            "visitor": visitor.to_dict(), "source": "REID", "confidence": confidence
                        }

        result = sorted(candidates.values(), key=lambda item: item["confidence"], reverse=True)
        return jsonify({"matches": result, "requires_guard_confirmation": True})
    finally:
        session.close()


@registration_bp.route("/entry", methods=["POST"])
@roles_required("Admin", "Security Officer")
def confirm_entry():
    data = request.get_json(silent=True) or {}
    visitor_id = data.get("visitor_id")
    source = str(data.get("source", "MANUAL")).upper()
    if not visitor_id or source not in {"FACE", "PLATE", "REID", "PHONE", "MANUAL"}:
        return jsonify({"error": "visitor_id and a valid source are required."}), 400
    session: Session = get_session_factory()()
    try:
        visitor = session.query(Visitor).filter(Visitor.id == int(visitor_id), Visitor.status == "ACTIVE").first()
        if not visitor:
            return jsonify({"error": "Active visitor not found."}), 404
        entry = VisitorEntry(
            visitor_id=visitor.id,
            camera_id=data.get("camera_id"),
            source=source,
            confidence=data.get("confidence"),
            guard_user_id=g.current_user.get("user_id"),
            confirmed=True,
            snapshot_path=data.get("snapshot_path"),
        )
        visitor.last_seen = datetime.now(timezone.utc)
        visitor.total_visits = (visitor.total_visits or 0) + 1
        session.add(entry)
        session.commit()
        log_audit_event(session, "CONFIRM_VISITOR_ENTRY", "Visitor", str(visitor.id), details={"source": source, "entry_id": entry.id})
        return jsonify({"entry_id": entry.id, "visitor": visitor.to_dict()}), 201
    finally:
        session.close()
