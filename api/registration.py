"""Guard-led visitor enrollment, lookup, and confirmed entry logging."""

import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, request, send_from_directory
from sqlalchemy.orm import Session
from werkzeug.utils import secure_filename

from database.connection import get_session_factory
from database.models import Visitor, VisitorEntry
from services.audit_service import log_audit_event
from services.auth_service import roles_required
from services.reid_service import get_reid_extractor
from services.vector_store import get_vector_store
from services.visitor_service import (
    generate_visitor_code,
    get_visitor_details,
    is_visitor_present,
    purge_expired_non_violators,
    record_gate_event,
)
from services.anpr_service import ANPRService, aggregate_plate_reads
from services.face_service import get_face_service

registration_bp = Blueprint("registration", __name__, url_prefix="/api/v2/registration")
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
_anpr_service = None


def _phone_hash(phone: str) -> str:
    normalized = "".join(ch for ch in phone if ch.isdigit())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _normalize_phone(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit())


def _get_anpr_service() -> ANPRService:
    global _anpr_service
    if _anpr_service is None:
        _anpr_service = ANPRService(os.getenv("ANPR_MODEL_PATH") or None)
    return _anpr_service


def _normalize_vehicle_number(value: object) -> str | None:
    if value is None:
        return None
    cleaned = "".join(ch for ch in str(value).upper() if ch.isalnum())
    return cleaned or None


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


def _delete_saved_photo(relative_path: str | None) -> None:
    if not relative_path:
        return
    photo_path = Path(current_app.root_path) / "data" / relative_path
    try:
        photo_path.unlink(missing_ok=True)
    except OSError:
        current_app.logger.warning("Unable to remove visitor photo: %s", relative_path)


@registration_bp.route("/camera-alerts", methods=["GET"])
@roles_required("Admin", "Security Officer")
def camera_alerts():
    """Return any pending face-recognition alerts for the guard app polling loop."""
    from web_server import _consume_visitor_alerts, _VISITOR_ALERTS, _VISITOR_ALERT_LOCK
    if request.args.get("peek") in ("true", "1"):
        with _VISITOR_ALERT_LOCK:
            return jsonify({"alerts": list(_VISITOR_ALERTS)})
    alerts = _consume_visitor_alerts()
    return jsonify({"alerts": alerts})


@registration_bp.route("/kiosk/voice-parse", methods=["POST"])
def voice_parse():
    """Parse visitor speech into structured details via Gemini or fast local NLP."""
    data = request.get_json(silent=True) or {}
    transcript = str(data.get("transcript", "")).strip()
    language = str(data.get("language", "ta-IN")).strip()

    from services.voice_agent_service import extract_visitor_details_from_speech
    extracted = extract_visitor_details_from_speech(transcript, language=language)
    return jsonify({"extracted": extracted})


@registration_bp.route("/kiosk/voice-audio", methods=["POST"])
def voice_audio():
    """Receive recorded WAV audio from tablet microphone and transcribe via server-side Google STT."""
    language = request.form.get("language", "ta-IN")
    audio_file = request.files.get("audio")

    if not audio_file:
        data = request.get_json(silent=True) or {}
        language = data.get("language", "ta-IN")
        audio_b64 = data.get("audio_base64", "")
        if audio_b64:
            import base64
            if "," in audio_b64:
                audio_b64 = audio_b64.split(",", 1)[1]
            raw_bytes = base64.b64decode(audio_b64)
        else:
            return jsonify({"error": "No audio file or audio_base64 provided"}), 400
    else:
        raw_bytes = audio_file.read()

    from services.voice_agent_service import transcribe_and_extract_from_audio_bytes
    extracted = transcribe_and_extract_from_audio_bytes(raw_bytes, language=language)
    return jsonify({"extracted": extracted, "transcript": extracted.get("raw_transcript", "")})


@registration_bp.route("/kiosk/tts", methods=["GET"])
def kiosk_tts():
    """Synthesize Tamil or English speech into natural MP3 audio with disk caching."""
    text = request.args.get("text", "").strip()
    lang = request.args.get("lang", "ta").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    from services.voice_agent_service import generate_tts_audio_bytes
    audio_bytes = generate_tts_audio_bytes(text, lang=lang)
    if not audio_bytes:
        return jsonify({"error": "TTS audio generation failed"}), 500

    from flask import Response
    return Response(audio_bytes, mimetype="audio/mpeg", headers={"Cache-Control": "public, max-age=86400"})


@registration_bp.route("/kiosk/voice-checkin", methods=["POST"])
def voice_checkin():
    """Direct kiosk check-in: accepts visitor details, creates/matches visitor, logs entry with duration."""
    data = request.get_json(silent=True) or {}
    full_name = str(data.get("name") or data.get("full_name") or "Visitor").strip()
    phone = _normalize_phone(str(data.get("phone", "")))
    company = data.get("company")
    category = data.get("category") or data.get("purpose") or "Visitor"
    expected_duration = int(data.get("expected_duration_minutes") or 30)

    session: Session = get_session_factory()()
    try:
        visitor = None
        if len(phone) >= 10:
            p_hash = _phone_hash(phone)
            visitor = session.query(Visitor).filter(Visitor.phone_hash == p_hash, Visitor.status == "ACTIVE").first()

        if not visitor:
            # Create new visitor record
            import uuid
            visitor = Visitor(
                visitor_code=generate_visitor_code(session),
                full_name=full_name,
                phone_number=phone if len(phone) >= 10 else None,
                phone_hash=_phone_hash(phone) if len(phone) >= 10 else None,
                phone_last4=phone[-4:] if len(phone) >= 4 else None,
                company=company,
                category=category,
                status="ACTIVE",
            )
            session.add(visitor)
            session.commit()
        else:
            if company and not visitor.company:
                visitor.company = company
            if category and visitor.category == "Unknown":
                visitor.category = category
            session.commit()

        photo_b64 = data.get("photo_base64")
        if photo_b64 and visitor:
            try:
                import base64
                import cv2
                import numpy as np
                if "," in photo_b64:
                    photo_b64 = photo_b64.split(",", 1)[1]
                img_bytes = base64.b64decode(photo_b64)
                arr = np.frombuffer(img_bytes, dtype=np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if img is not None:
                    visitor.consent_status = "GRANTED"
                    session.commit()
                    get_face_service().enroll_visitor_face(session, visitor.id, img)
            except Exception as e:
                current_app.logger.warning("Kiosk face capture enrollment skipped: %s", e)

        # Check if already present; if not, record ENTRY
        if not is_visitor_present(session, visitor.id):
            entry = record_gate_event(
                session,
                visitor_id=visitor.id,
                event_type="ENTRY",
                source="KIOSK",
                expected_duration_minutes=expected_duration,
            )
            log_audit_event(session, "VOICE_KIOSK_ENTRY", "Visitor", str(visitor.id), details={
                "source": "VOICE_KIOSK",
                "expected_duration_minutes": expected_duration,
                "entry_id": entry.id
            })
            return jsonify({
                "status": "CHECKED_IN",
                "event_type": "ENTRY",
                "visitor": visitor.to_dict(),
                "expected_duration_minutes": expected_duration,
                "message": f"வருகை பதிவு செய்யப்பட்டது ({expected_duration} நிமிடம் அனுமதிக்கப்பட்டுள்ளது)."
            }), 201
        else:
            # If already present, treat as auto-EXIT check
            exit_entry = record_gate_event(
                session,
                visitor_id=visitor.id,
                event_type="EXIT",
                source="KIOSK",
            )
            log_audit_event(session, "VOICE_KIOSK_EXIT", "Visitor", str(visitor.id), details={
                "source": "VOICE_KIOSK",
                "exit_id": exit_entry.id
            })
            return jsonify({
                "status": "CHECKED_OUT",
                "event_type": "EXIT",
                "visitor": visitor.to_dict(),
                "message": "வெளியேறுதல் பதிவு செய்யப்பட்டது. நன்றி!"
            }), 200
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        session.close()


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
        normalized = _normalize_vehicle_number(read.get("normalized_text"))
        if not normalized:
            continue
        with_session = get_session_factory()()
        try:
            matches = (
                with_session.query(Visitor)
                .filter(Visitor.status == "ACTIVE")
                .filter(Visitor.vehicle_number.isnot(None))
                .filter(Visitor.vehicle_number == normalized)
                .limit(5)
                .all()
            )
            read["matches"] = [visitor.to_dict() for visitor in matches]
        finally:
            with_session.close()
    result["requires_guard_confirmation"] = True
    return jsonify(result)


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
        existing = session.query(Visitor).filter(Visitor.phone_hash == phone_hash, Visitor.status != "REDACTED").first()
        if existing:
            replacement_photo = request.files.get("photo")
            if replacement_photo:
                import cv2
                replacement_path = _save_photo(replacement_photo)
                replacement_file = Path(current_app.root_path) / "data" / replacement_path
                replacement_image = cv2.imread(str(replacement_file))
                if replacement_image is None or get_face_service().get_primary_face_embedding(replacement_image)[0] is None:
                    _delete_saved_photo(replacement_path)
                    return jsonify({
                        "error": "No clear face was detected. Upload a well-lit, front-facing photo with one visible face.",
                        "face_enrolled": False,
                    }), 422
                existing.consent_status = "GRANTED"
                session.commit()
                try:
                    if not get_face_service().enroll_visitor_face(session, existing.id, replacement_image):
                        return jsonify({
                            "error": "Face enrollment failed. The photo was not retained.",
                            "face_enrolled": False,
                        }), 422
                except Exception as error:
                    current_app.logger.warning("Replacement face enrollment failed: %s", error)
                    return jsonify({
                        "error": "Face enrollment failed. The photo was not retained.",
                        "face_enrolled": False,
                    }), 422
                finally:
                    _delete_saved_photo(replacement_path)
                return jsonify({
                    "visitor": existing.to_dict(),
                    "message": "Visitor photo and face enrollment updated successfully.",
                }), 200
            return jsonify({"error": "A visitor with this phone number already exists.", "visitor": existing.to_dict()}), 409

        vehicle_number = _normalize_vehicle_number(data.get("vehicle_number"))
        visitor = Visitor(
            visitor_code=generate_visitor_code(session),
            full_name=data.get("full_name", "").strip(),
            phone_number=phone,
            phone_hash=phone_hash,
            phone_last4=phone[-4:],
            phone_verified=False,
            company=(data.get("company") or "").strip() or None,
            vehicle_number=vehicle_number,
            plate_enrolled=bool(vehicle_number),
            category=(data.get("category") or "Unknown").strip(),
            label=(data.get("label") or "").strip() or None,
            consent_status="GRANTED" if str(data.get("face_consent", "")).lower() == "true" else "DECLINED",
            status="ACTIVE",
        )
        photo = request.files.get("photo")
        face_image = None
        photo_path = None
        if photo:
            photo_path = _save_photo(photo)
            import cv2
            face_image = cv2.imread(str(Path(current_app.root_path) / "data" / photo_path))
            if face_image is None or get_face_service().get_primary_face_embedding(face_image)[0] is None:
                _delete_saved_photo(photo_path)
                return jsonify({
                    "error": "No clear face was detected. Upload a well-lit, front-facing photo with one visible face.",
                    "face_enrolled": False,
                }), 422
        session.add(visitor)
        session.commit()

        if photo_path:
            image = face_image
            if image is not None:
                try:
                    # 1. Appearance Re-ID embedding
                    reid_emb = get_reid_extractor().extract_embedding(image)
                    get_vector_store(session).add_embedding(visitor.id, reid_emb, embedding_type="reid", confidence=1.0)

                    # 2. InsightFace 512-d ArcFace facial embedding
                    face_ok = get_face_service().enroll_visitor_face(session, visitor.id, image)
                    if not face_ok:
                        session.delete(visitor)
                        session.commit()
                        return jsonify({"error": "Face enrollment failed. The photo was not retained."}), 422
                    visitor.face_enrolled = True
                except Exception as error:
                    current_app.logger.warning("Visitor embedding enrollment failed: %s", error)
                    session.rollback()
                    session.delete(visitor)
                    session.commit()
                    return jsonify({"error": "Face enrollment failed. The photo was not retained."}), 422
                finally:
                    _delete_saved_photo(photo_path)

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
    vehicle_number = _normalize_vehicle_number(data.get("vehicle_number"))
    if not vehicle_number or len(vehicle_number) < 4:
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
            # 1. InsightFace Facial Recognition (ArcFace 512-d)
            try:
                face_matches = get_face_service().recognize_face(session, image, threshold=0.50, top_k=5)
                for fm in face_matches:
                    v_id = fm["visitor_id"]
                    candidates[v_id] = {
                        "visitor": fm["visitor"],
                        "source": "FACE",
                        "confidence": fm["confidence"],
                        "bbox": fm.get("bbox"),
                        "is_frequent": fm.get("is_frequent", False)
                    }
            except Exception as fe:
                current_app.logger.warning("InsightFace recognition note: %s", fe)

            # 2. Appearance Re-ID matching fallback / complement
            embedding = get_reid_extractor().extract_embedding(image)
            for visitor_id, confidence in get_vector_store(session).search_similar(
                embedding, top_k=5, threshold=0.68, embedding_type="reid"
            ):
                visitor = session.query(Visitor).filter(Visitor.id == visitor_id, Visitor.status == "ACTIVE").first()
                if visitor:
                    existing = candidates.get(visitor_id)
                    if not existing or (existing["source"] != "FACE" and confidence > existing["confidence"]):
                        candidates[visitor_id] = {
                            "visitor": visitor.to_dict(), "source": "REID", "confidence": confidence
                        }

        result = sorted(candidates.values(), key=lambda item: item["confidence"], reverse=True)
        return jsonify({"matches": result, "requires_guard_confirmation": True})
    finally:
        session.close()


@registration_bp.route("/entry", methods=["POST"])
@registration_bp.route("/entries", methods=["POST"])
@roles_required("Admin", "Security Officer")
def confirm_entry():
    data = request.get_json(silent=True) or {}
    visitor_id = data.get("visitor_id")
    source = str(data.get("source", "MANUAL")).upper()
    if any(k in source for k in ["GUARD", "MANUAL", "CONFIRM", "BUTTON"]):
        source = "MANUAL"
    elif "FACE" in source:
        source = "FACE"
    elif any(k in source for k in ["PLATE", "ANPR"]):
        source = "PLATE"
    elif "PHONE" in source:
        source = "PHONE"
    elif "REID" in source:
        source = "REID"
    elif source not in {"FACE", "PLATE", "REID", "PHONE", "MANUAL"}:
        source = "MANUAL"

    if not visitor_id:
        return jsonify({"error": "visitor_id is required."}), 400
    session: Session = get_session_factory()()
    try:
        visitor = session.query(Visitor).filter(Visitor.id == int(visitor_id), Visitor.status == "ACTIVE").first()
        if not visitor:
            return jsonify({"error": "Active visitor not found."}), 404
        try:
            entry = record_gate_event(
                session,
                visitor.id,
                "ENTRY",
                source,
                camera_id=data.get("camera_id"),
                confidence=data.get("confidence"),
                snapshot_path=data.get("snapshot_path"),
                user_id=g.current_user.get("user_id"),
                expected_duration_minutes=data.get("expected_duration_minutes") or 60,
            )
        except (LookupError, ValueError) as error:
            return jsonify({"error": str(error)}), 409
        log_audit_event(session, "CONFIRM_VISITOR_ENTRY", "Visitor", str(visitor.id), details={"source": source, "entry_id": entry.id})
        return jsonify({"entry_id": entry.id, "visitor": visitor.to_dict(), "expected_duration_minutes": entry.expected_duration_minutes}), 201
    finally:
        session.close()


@registration_bp.route("/exit", methods=["POST"])
@roles_required("Admin", "Security Officer")
def confirm_exit():
    """Confirm a visitor's departure; recognition alone never locks or clears access."""
    data = request.get_json(silent=True) or {}
    visitor_id = data.get("visitor_id")
    source = str(data.get("source", "MANUAL")).upper()
    if not visitor_id:
        return jsonify({"error": "visitor_id is required."}), 400
    session: Session = get_session_factory()()
    try:
        try:
            exit_event = record_gate_event(
                session,
                int(visitor_id),
                "EXIT",
                source,
                camera_id=data.get("camera_id"),
                confidence=data.get("confidence"),
                snapshot_path=data.get("snapshot_path"),
                user_id=g.current_user.get("user_id"),
            )
        except (LookupError, ValueError) as error:
            return jsonify({"error": str(error)}), 409
        log_audit_event(session, "CONFIRM_VISITOR_EXIT", "Visitor", str(visitor_id), details={"source": source, "exit_id": exit_event.id})
        visitor = session.query(Visitor).filter(Visitor.id == int(visitor_id)).first()
        return jsonify({"exit_id": exit_event.id, "visitor": visitor.to_dict()}), 201
    finally:
        session.close()


@registration_bp.route("/active", methods=["GET"])
@roles_required("Admin", "Security Officer", "Viewer")
def active_visitors():
    session: Session = get_session_factory()()
    try:
        visitors = session.query(Visitor).filter(Visitor.status == "ACTIVE").order_by(Visitor.last_seen.desc()).all()
        return jsonify({"visitors": [
            visitor.to_dict() | {"is_present": is_visitor_present(session, visitor.id)}
            for visitor in visitors if is_visitor_present(session, visitor.id)
        ]})
    finally:
        session.close()


@registration_bp.route("/retention/purge", methods=["POST"])
@roles_required("Admin")
def purge_retention():
    data = request.get_json(silent=True) or {}
    try:
        retention_hours = int(data.get("retention_hours", 24))
    except (TypeError, ValueError):
        return jsonify({"error": "retention_hours must be an integer."}), 400
    if retention_hours < 1 or retention_hours > 24 * 365:
        return jsonify({"error": "retention_hours must be between 1 and 8760."}), 400
    session: Session = get_session_factory()()
    try:
        count = purge_expired_non_violators(session, retention_hours)
        return jsonify({"purged": count, "retention_hours": retention_hours})
    finally:
        session.close()


@registration_bp.route("/face/recognize", methods=["POST"])
@roles_required("Admin", "Security Officer")
def recognize_visitor_face():
    """Detect and recognize visitor faces in an image using InsightFace ArcFace models."""
    import cv2
    import numpy as np

    upload = request.files.get("photo") or request.files.get("frame")
    image = None
    if upload:
        raw = np.frombuffer(upload.read(), dtype=np.uint8)
        image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    else:
        data = request.get_json(silent=True) or {}
        b64_str = data.get("image") or data.get("frame") or data.get("photo")
        if b64_str:
            import base64
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]
            try:
                raw = np.frombuffer(base64.b64decode(b64_str), dtype=np.uint8)
                image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
            except Exception:
                pass

    if image is None:
        return jsonify({"error": "A valid photo, frame, or base64 image is required."}), 400

    session: Session = get_session_factory()()
    try:
        matches = get_face_service().recognize_face(session, image, threshold=0.48, top_k=5)
        return jsonify({
            "matches": matches,
            "count": len(matches),
            "requires_guard_confirmation": True
        })
    finally:
        session.close()


@registration_bp.route("/visitors/<int:visitor_id>/face", methods=["POST"])
@roles_required("Admin", "Security Officer")
def enroll_face(visitor_id: int):
    """Enroll or update a visitor's facial recognition embedding using InsightFace."""
    upload = request.files.get("photo")
    if not upload:
        return jsonify({"error": "A photo is required for face enrollment."}), 400

    import cv2
    import numpy as np

    session: Session = get_session_factory()()
    try:
        visitor = session.query(Visitor).filter(Visitor.id == visitor_id).first()
        if not visitor:
            return jsonify({"error": "Visitor not found."}), 404

        raw = np.frombuffer(upload.read(), dtype=np.uint8)
        image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
        if image is None:
            return jsonify({"error": "The image could not be decoded."}), 400

        # Use a temporary file only while extracting the embedding.
        upload.seek(0)
        photo_path = _save_photo(upload)

        success = get_face_service().enroll_visitor_face(session, visitor.id, image)
        if not success:
            _delete_saved_photo(photo_path)
            return jsonify({"error": "No clear face detected in the uploaded photo."}), 400
        _delete_saved_photo(photo_path)

        log_audit_event(session, "ENROLL_FACE", "Visitor", str(visitor_id), details={"model": "InsightFace ArcFace"})
        return jsonify({
            "message": "Face enrolled successfully.",
            "visitor": visitor.to_dict()
        })
    finally:
        session.close()
