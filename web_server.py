# web_server.py — Simple, Modern ECOLIFEBUDDY AI Surveillance Server
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import cv2
import numpy as np
import time
import os
import glob
import json
import threading
import queue
import webbrowser
import datetime
from urllib.parse import urlparse, urlunparse
from flask import Flask, render_template, Response, jsonify, request, send_from_directory

from detector import EcoDetector
from tracker import EcoTracker
from rule_engine import EcoRuleEngine
from alert_system import AlertSystem, VIOLATIONS_DIR, ALERT_LOG_FILE
from config import load_config, save_config
from stream_resolver import resolve_stream_source, is_youtube_url, resolve_youtube_stream
from services.anpr_service import ANPRService, aggregate_plate_reads
from database.connection import get_session_factory
from database.models import Visitor

app = Flask(__name__, template_folder="templates", static_folder="static")

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Guard-App, X-Requested-With"
    return response

@app.before_request
def handle_preflight():
    from flask import request
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Guard-App, X-Requested-With"
        return response

# New module (Intelligent Visitor Identification & Activity Tracking) blueprints & DB.
from api import register_blueprints
from database import init_db
register_blueprints(app)
init_db()

# Initialize persistent config & alert system
config = load_config()
alert_system = AlertSystem(config)


def open_webcam(preferred_idx=0):
    """
    Robust Windows webcam opener that checks DirectShow and default backends,
    validates actual frame delivery, and avoids locking the driver.
    """
    indices_to_try = [preferred_idx]
    for alt in [0, 1]:
        if alt not in indices_to_try:
            indices_to_try.append(alt)

    for idx in indices_to_try:
        for api in (cv2.CAP_DSHOW, cv2.CAP_ANY):
            try:
                cap = cv2.VideoCapture(idx, api)
                if not cap.isOpened():
                    cap.release()
                    continue
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                # Verify we can read at least one valid frame
                for _ in range(5):
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None and test_frame.size > 0:
                        print(f"📷 Live Webcam Connected on device index {idx} (Backend: {api})")
                        return cap, idx
                    time.sleep(0.04)
                cap.release()
            except Exception as e:
                print(f"Webcam test exception index={idx}, api={api}: {e}")
    return None, None


def normalize_network_source(source):
    """Normalize common IP Webcam URLs for OpenCV."""
    value = str(source or "").strip()
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return value

    host = parsed.hostname.lower()
    port = parsed.port
    is_ip_webcam = port in (8080, 4747) and (
        host == "localhost"
        or host == "127.0.0.1"
        or host.startswith("192.168.")
        or host.startswith("10.")
        or host.startswith("172.16.")
        or host.startswith("172.17.")
        or host.startswith("172.18.")
        or host.startswith("172.19.")
        or host.startswith("172.2")
        or host.startswith("172.30.")
        or host.startswith("172.31.")
    )
    if not is_ip_webcam:
        return value

    path = parsed.path.rstrip("/")
    if not path:
        path = "/video"
    elif path.lower() in ("", "/"):
        path = "/video"

    # IP Webcam normally exposes an HTTP MJPEG endpoint, not HTTPS.
    scheme = "http" if parsed.scheme == "https" else parsed.scheme
    return urlunparse((scheme, parsed.netloc, path, "", parsed.query, ""))


# ==============================================================================
# GLOBAL AI & CAMERA STATE
# ==============================================================================
_VISITOR_ALERTS = []
_VISITOR_ALERT_LOCK = threading.Lock()
_VISITOR_LAST_ALERTS = {}


def _add_visitor_alert(alert):
    with _VISITOR_ALERT_LOCK:
        _VISITOR_ALERTS.append(alert)
        if len(_VISITOR_ALERTS) > 50:
            del _VISITOR_ALERTS[:-50]


def _consume_visitor_alerts():
    with _VISITOR_ALERT_LOCK:
        pending = list(_VISITOR_ALERTS)
        _VISITOR_ALERTS.clear()
        return pending


def _visitor_camera_event_type(camera):
    camera_text = " ".join(
        str(camera.get(key, "")).lower() for key in ("name", "zone", "location")
    )
    return "EXIT" if "exit" in camera_text or "out" in camera_text else "ENTRY"


class LiveMonitorState:
    def __init__(self):
        self.lock = threading.Lock()
        self.open_lock = threading.Lock()
        
        # Load cameras from config
        self.cameras = config.get("cameras", [])
        self.active_camera_id = 1
        self.active_source = "https://www.youtube.com/watch?v=QMN4_62A3As"
        self.camera_title = "Balneário Camboriú - Central"
        self.zone = "Boardwalk / Public Promenade"
        self.camera_mode = "youtube"

        if self.cameras:
            c = self.cameras[0]
            self.active_camera_id = c.get("id", 1)
            self.active_source = normalize_network_source(
                c.get("source", self.active_source)
            )
            self.camera_title = c.get("name", self.camera_title)
            self.zone = c.get("zone", self.zone)
            src = str(self.active_source)
            if is_youtube_url(src):
                self.camera_mode = "youtube"
            elif c.get("type") == "USB" or src.isdigit() or src == "0":
                self.camera_mode = "webcam"
            else:
                self.camera_mode = "custom"

        self.ai_enabled = True
        self.auto_snap = True
        self.show_boxes = True
        self.sound_enabled = True
        self.cap = None
        self.is_connected = False
        self.status_message = "Connecting..."
        self.latest_snapped_file = None
        
        self.latest_display_frame = None
        self.raw_frame = None
        
        self.people_count = 0
        self.object_count = 0
        self.is_alert = False
        self.fps = 0.0
        self.last_alert_time = 0
        self.alert_text = "Clean"
        anpr_settings = config.get("anpr_settings", {})
        self.anpr_enabled = bool(anpr_settings.get("enabled", False))
        self.anpr_profile = anpr_settings
        self.anpr_service = ANPRService(anpr_settings.get("model_path") or os.getenv("ANPR_MODEL_PATH") or None)
        self.anpr_queue = queue.Queue(maxsize=2)
        self.anpr_result = {
            "status": "DISABLED" if not self.anpr_enabled else "STARTING",
            "reads": [],
            "candidate": None,
            "requires_guard_confirmation": True,
        }
        self.anpr_history = []
        
        # AI Modules
        model_name = os.getenv("DETECTION_MODEL", "yolo26n.pt")
        print(f"🧠 Initializing YOLO Detection Engine (Model: {model_name})...")
        self.detector = EcoDetector(model_path=model_name)
        self.tracker = EcoTracker()
        self.engine = EcoRuleEngine()
        print(f"✅ Detection Engine Ready with {model_name}.")

        self.demo_frames = []
        self._load_demo_frames()

    def _load_demo_frames(self):
        files = glob.glob(os.path.join(VIOLATIONS_DIR, "*.jpg"))
        for f in files[:12]:
            img = cv2.imread(f)
            if img is not None:
                self.demo_frames.append(img)

    def reload_cameras(self):
        cams = []
        try:
            from database.connection import get_session_factory
            from database.models import Camera
            session = get_session_factory()()
            db_cams = session.query(Camera).filter(Camera.enabled == True).order_by(Camera.id.asc()).all()
            for c in db_cams:
                cams.append({
                    "id": c.id,
                    "name": c.name,
                    "source": c.stream_source,
                    "type": c.stream_type or "RTSP",
                    "purpose": (c.purpose or "LITTER").upper(),
                    "enabled": c.enabled,
                    "zone": c.location or "Gate Zone"
                })
            session.close()
        except Exception as e:
            print(f"Error loading DB cameras: {e}")

        if not cams:
            cfg = load_config()
            cams = []
            for item in cfg.get("cameras", []):
                cams.append({
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "source": item.get("source"),
                    "type": item.get("type", "RTSP"),
                    "purpose": str(item.get("purpose", "LITTER")).upper(),
                    "enabled": item.get("enabled", True),
                    "zone": item.get("zone", "Gate Zone")
                })

        with self.lock:
            self.cameras = cams

    def open_camera(self):
        # Prevent concurrent open attempts
        if not self.open_lock.acquire(blocking=False):
            return

        try:
            with self.lock:
                old_cap = self.cap
                self.cap = None
                self.is_connected = False
                cur_mode = self.camera_mode
                cur_source = self.active_source
                cur_title = self.camera_title
                self.status_message = f"Connecting to {cur_title}..."

            if old_cap is not None:
                try:
                    old_cap.release()
                except Exception:
                    pass

            new_cap = None
            new_title = cur_title
            new_status = ""
            is_conn = False

            if cur_mode == "youtube" or is_youtube_url(str(cur_source)):
                print(f"📡 Resolving YouTube Live Stream: {cur_source}...")
                stream_url, meta = resolve_stream_source(cur_source, target_height=480)
                if stream_url:
                    try:
                        new_cap = cv2.VideoCapture(stream_url)
                        new_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        if meta and meta.get("title") and ("YouTube" in str(cur_title) or not cur_title):
                            new_title = meta.get("title")
                        if new_cap.isOpened():
                            ret, _ = new_cap.read()
                            if ret:
                                is_conn = True
                                new_status = "LIVE STREAM CONNECTED"
                                print(f"✅ Connected to YouTube Live: {new_title}")
                            else:
                                is_conn = True
                                new_status = "Connected, awaiting frame..."
                        else:
                            new_status = "Unable to open YouTube stream"
                    except Exception as e:
                        print(f"YouTube stream open error: {e}")
                        new_status = str(e)
                else:
                    new_status = "Failed to resolve YouTube live URL"

            elif cur_mode == "webcam":
                try:
                    pref_idx = 0
                    if str(cur_source).isdigit():
                        pref_idx = int(cur_source)
                    cap_wb, actual_idx = open_webcam(pref_idx)
                    if cap_wb is not None:
                        new_cap = cap_wb
                        is_conn = True
                        new_title = f"Laptop Webcam ({actual_idx})"
                        new_status = "LIVE WEBCAM CONNECTED"
                    else:
                        cur_mode = "demo"
                        is_conn = True
                        new_title = "Demo Simulation Feed"
                        new_status = "Webcam unavailable — Switched to Demo"
                except Exception as e:
                    print(f"Webcam open error: {e}")
                    cur_mode = "demo"
                    is_conn = True
                    new_title = "Demo Simulation Feed"
                    new_status = "Demo Simulation"

            elif cur_mode == "custom":
                try:
                    src_str = normalize_network_source(cur_source)
                    # Quick pre-flight check for HTTP/RTSP URLs to avoid long OpenCV socket hang
                    if src_str.lower().startswith(("http://", "https://")):
                        try:
                            import socket
                            parsed = urlparse(src_str)
                            host = parsed.hostname
                            port = parsed.port or 80
                            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                                s.settimeout(1.2)
                                if s.connect_ex((host, port)) != 0:
                                    raise ConnectionError(f"Host {host}:{port} unreachable")
                        except Exception as conn_err:
                            new_status = (
                                f"Cannot reach {src_str} - check that the phone and computer "
                                "are on the same Wi-Fi and IP Webcam is running"
                            )
                            print(f"⚠️ Quick pre-flight check failed for {src_str}: {conn_err}")
                            src_str = None

                    if src_str:
                        new_cap = cv2.VideoCapture(src_str)
                        new_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        if new_cap.isOpened():
                            ret_test, _ = new_cap.read()
                            if ret_test:
                                is_conn = True
                                new_status = "LIVE NETWORK STREAM CONNECTED"
                            else:
                                is_conn = True
                                new_status = "Connected, awaiting frame..."
                        else:
                            new_status = (
                                f"Cannot open stream: {src_str} - verify IP Webcam's "
                                "video stream is enabled"
                            )
                except Exception as e:
                    new_status = str(e)

            else:
                cur_mode = "demo"
                is_conn = True
                new_title = "Demo Simulation Feed"
                new_status = "DEMO SIMULATION"

            with self.lock:
                self.cap = new_cap
                self.camera_mode = cur_mode
                self.is_connected = is_conn
                if new_title:
                    self.camera_title = new_title
                self.status_message = new_status
        finally:
            self.open_lock.release()


state = LiveMonitorState()


def anpr_worker_loop():
    """Process a bounded stream of high-resolution frames without blocking video."""
    while True:
        try:
            camera_id, frame, profile = state.anpr_queue.get()
            result = state.anpr_service.read_frame(frame, profile)
            reads = result.get("reads", [])
            with state.lock:
                state.anpr_history.extend(reads)
                state.anpr_history = state.anpr_history[-12:]
                candidate = aggregate_plate_reads(
                    state.anpr_history,
                    minimum_frames=int(profile.get("minimum_consensus_frames", 2)),
                )
                if candidate:
                    session = get_session_factory()()
                    try:
                        candidate["matches"] = [
                            visitor.to_dict()
                            for visitor in session.query(Visitor)
                            .filter(
                                Visitor.status == "ACTIVE",
                                Visitor.vehicle_number == candidate["normalized_text"],
                            )
                            .limit(5)
                            .all()
                        ]
                    finally:
                        session.close()
                state.anpr_result = {
                    "status": result.get("status", "UNKNOWN"),
                    "camera_id": camera_id,
                    "reads": reads,
                    "candidate": candidate,
                    "requires_guard_confirmation": True,
                }
        except (queue.Empty, ValueError, TypeError, RuntimeError) as error:
            with state.lock:
                state.anpr_result = {
                    "status": "ERROR",
                    "error": str(error),
                    "reads": [],
                    "candidate": None,
                    "requires_guard_confirmation": True,
                }

# ==============================================================================
# BACKGROUND CAMERA & DETECTION WORKER
# ==============================================================================
_VISITOR_CAPS = {}

def visitor_camera_worker():
    """Dedicated background worker for visitor recognition cameras only.
    Processes only cameras with purpose='VISITOR', runs InsightFace recognition,
    matches against Supabase/PostgreSQL vector embeddings, auto-records EXIT events,
    and queues real-time pending alerts for the guard app to poll.
    Does NOT run YOLO litter detection.
    """
    while True:
        try:
            # 1. Fetch enabled VISITOR cameras from DB or state
            visitor_cameras = []
            session = get_session_factory()()
            try:
                from database.models import Camera
                db_cams = session.query(Camera).filter(
                    Camera.enabled == True,
                    Camera.purpose == "VISITOR"
                ).all()
                for c in db_cams:
                    visitor_cameras.append({
                        "id": c.id,
                        "name": c.name,
                        "source": c.stream_source,
                        "type": c.stream_type,
                        "purpose": "VISITOR",
                        "enabled": c.enabled,
                        "location": c.location,
                        "zone": c.location or "Gate Area",
                    })
            except Exception as e:
                with state.lock:
                    cameras = state.cameras
                visitor_cameras = [
                    cam for cam in cameras
                    if str(cam.get("purpose", "LITTER")).upper() == "VISITOR" and cam.get("enabled", True)
                ]
            finally:
                session.close()

            if not visitor_cameras:
                for cap_id, cap_obj in list(_VISITOR_CAPS.items()):
                    try:
                        cap_obj.release()
                    except Exception:
                        pass
                _VISITOR_CAPS.clear()
                time.sleep(1.5)
                continue

            current_ids = {int(cam.get("id") or 0) for cam in visitor_cameras}
            for cap_id in list(_VISITOR_CAPS.keys()):
                if cap_id not in current_ids:
                    try:
                        _VISITOR_CAPS[cap_id].release()
                    except Exception:
                        pass
                    del _VISITOR_CAPS[cap_id]

            for cam in visitor_cameras:
                cam_id = int(cam.get("id") or 0)
                if cam_id <= 0:
                    continue

                frame = None
                with state.lock:
                    active_id = int(state.active_camera_id or 0)
                    if active_id == cam_id and state.raw_frame is not None:
                        frame = state.raw_frame.copy()

                if active_id == cam_id:
                    if cam_id in _VISITOR_CAPS:
                        try:
                            _VISITOR_CAPS[cam_id].release()
                        except Exception:
                            pass
                        del _VISITOR_CAPS[cam_id]

                if frame is None:
                    source = str(cam.get("source") or "").strip()
                    if not source:
                        continue
                    cap = _VISITOR_CAPS.get(cam_id)
                    if cap is None or not cap.isOpened():
                        resolved_source = source
                        if is_youtube_url(source):
                            resolved_source, _ = resolve_stream_source(source, target_height=480)
                        if not resolved_source:
                            continue
                        try:
                            cap = cv2.VideoCapture(
                                int(resolved_source) if str(resolved_source).isdigit() else resolved_source
                            )
                            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            _VISITOR_CAPS[cam_id] = cap
                        except Exception as open_err:
                            print(f"Could not open visitor camera {cam_id}: {open_err}")
                            continue

                    if cap and cap.isOpened():
                        ret, f = cap.read()
                        if ret and f is not None and getattr(f, "size", 0) > 0:
                            frame = f
                        else:
                            cap.release()
                            _VISITOR_CAPS.pop(cam_id, None)
                            continue

                if frame is None or getattr(frame, "size", 0) == 0:
                    continue

                session = get_session_factory()()
                try:
                    from services.face_service import get_face_service
                    from services.visitor_service import is_visitor_present, record_gate_event

                    fs = get_face_service()
                    if not fs.is_ready():
                        continue

                    matches = fs.recognize_face(session, frame, threshold=0.50, top_k=3)
                    event_type = _visitor_camera_event_type(cam)
                    now = time.time()

                    for match in matches:
                        visitor = match.get("visitor")
                        if not visitor:
                            continue
                        visitor_id = int(visitor.get("id") or 0)
                        alert_key = (cam_id, visitor_id, event_type)
                        if now - _VISITOR_LAST_ALERTS.get(alert_key, 0) < 15:
                            continue
                        _VISITOR_LAST_ALERTS[alert_key] = now

                        auto_logged = False
                        if event_type == "EXIT":
                            try:
                                if is_visitor_present(session, visitor_id):
                                    record_gate_event(
                                        session,
                                        visitor_id=visitor_id,
                                        event_type="EXIT",
                                        source="FACE",
                                        camera_id=cam_id,
                                        confidence=match.get("confidence"),
                                    )
                                    session.commit()
                                    auto_logged = True
                                    print(f"🚪 Auto-recorded EXIT for visitor {visitor.get('full_name')} (ID {visitor_id}) via exit camera {cam_id}")
                            except Exception as rec_err:
                                print(f"Note on auto-exit event creation: {rec_err}")

                        alert = {
                            "camera_id": cam_id,
                            "camera_name": cam.get("name", "Visitor Camera"),
                            "gate_location": cam.get("location") or cam.get("zone") or "",
                            "visitor_id": visitor_id,
                            "visitor": visitor,
                            "confidence": match.get("confidence"),
                            "match_type": match.get("match_type", "FACE_INSIGHTFACE"),
                            "event_type": event_type,
                            "auto_logged": auto_logged,
                            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "source": "FACE",
                        }
                        _add_visitor_alert(alert)
                finally:
                    session.close()

            time.sleep(2.0)
        except Exception as error:
            print(f"Visitor camera worker error: {error}")
            time.sleep(1.0)


def camera_worker_loop():
    """Background worker continuously pulling frames, running YOLO and tracking."""
    state.reload_cameras()
    state.open_camera()
    frame_count = 0
    fps_start = time.time()
    demo_idx = 0
    last_demo_switch = time.time()
    fail_count = 0
    frame_idx = 0
    last_tracks = []
    last_is_violating = False

    while True:
        frame = None
        cur_cap = None
        cur_mode = "demo"
        with state.lock:
            cur_cap = state.cap
            cur_mode = state.camera_mode

        if cur_mode in ("youtube", "webcam", "custom") and cur_cap and cur_cap.isOpened():
            try:
                ret, frame = cur_cap.read()
            except (cv2.error, MemoryError, SystemError, Exception) as read_err:
                print(f"⚠️ Video stream frame read error: {read_err}")
                ret, frame = False, None
                import gc; gc.collect()

            if not ret or frame is None or getattr(frame, "size", 0) == 0:
                fail_count += 1
                if fail_count > 25:
                    print(f"⚠️ Reconnecting stream ({cur_mode}) after frame drop...")
                    fail_count = 0
                    threading.Thread(target=state.open_camera, daemon=True).start()
                time.sleep(0.04)
                continue
            fail_count = 0
        elif cur_mode == "demo":
            if state.demo_frames:
                if time.time() - last_demo_switch > 3.0:
                    demo_idx = (demo_idx + 1) % len(state.demo_frames)
                    last_demo_switch = time.time()
                frame = state.demo_frames[demo_idx].copy()
            else:
                frame = np.full((720, 1280, 3), (25, 30, 42), dtype=np.uint8)
                cv2.putText(frame, "ECOLIFEBUDDY AI Demo Stream", (380, 360),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 220, 240), 2)
            time.sleep(0.033)
        else:
            canvas = np.full((720, 1280, 3), (16, 23, 38), dtype=np.uint8)
            msg = f"{state.camera_title}: {state.status_message}".encode('ascii', 'replace').decode('ascii')
            cv2.putText(canvas, msg, (80, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (16, 185, 129), 2)
            src_txt = f"Source URI: {state.active_source}".encode('ascii', 'replace').decode('ascii')
            cv2.putText(canvas, src_txt, (80, 370), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (203, 213, 225), 1)
            hint_txt = "Tip: Make sure phone is on the same Wi-Fi network and IP Webcam is running.".encode('ascii', 'replace').decode('ascii')
            cv2.putText(canvas, hint_txt, (80, 420), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (148, 163, 184), 1)
            with state.lock:
                state.latest_display_frame = canvas
            time.sleep(0.1)
            continue

        if frame is None:
            time.sleep(0.02)
            continue

        h, w = frame.shape[:2]
        with state.lock:
            state.raw_frame = frame.copy()

        frame_count += 1
        elapsed = time.time() - fps_start
        if elapsed >= 1.0:
            with state.lock:
                state.fps = round(frame_count / elapsed, 1)
            frame_count = 0
            fps_start = time.time()

        display_frame = frame.copy()
        people_c = 0
        objects_c = 0
        is_violating = False
        frame_idx += 1

        if state.anpr_enabled and frame_idx % 10 == 0:
            profile = dict(state.anpr_profile)
            profile["detector_threshold"] = profile.get("detector_threshold", 0.35)
            try:
                state.anpr_queue.put_nowait((state.active_camera_id, frame.copy(), profile))
            except queue.Full:
                pass

        current_purpose = "LITTER"
        with state.lock:
            for cam in state.cameras:
                if int(cam.get("id") or 0) == int(state.active_camera_id or 0):
                    current_purpose = str(cam.get("purpose", "LITTER")).upper()
                    break

        if state.ai_enabled and current_purpose == "LITTER":
            try:
                if frame_idx % 2 == 0 or not last_tracks:
                    detections = state.detector.get_detections(frame)
                    tracks = state.tracker.update(detections, frame)
                    is_violating = state.engine.is_littering(tracks)
                    last_tracks = tracks
                    last_is_violating = is_violating
                else:
                    tracks = last_tracks
                    is_violating = last_is_violating

                current_states = state.engine.tracking_states

                for track in tracks:
                    if not track.is_confirmed():
                        continue
                    cls_name = track.get_det_class()
                    ltrb = track.to_ltrb()
                    t_id = track.track_id

                    if cls_name == "person":
                        people_c += 1
                        color = (16, 185, 129)
                        label = f"Person #{t_id}"
                    else:
                        objects_c += 1
                        color = (245, 158, 11)
                        label = f"{cls_name} #{t_id}"

                        for (p_id, obj_id), s in current_states.items():
                            if obj_id == t_id:
                                if s == "STATIC":
                                    color = (140, 150, 165)
                                    label = f"{cls_name} #{t_id} [Static]"
                                elif s == "HELD":
                                    color = (59, 130, 246)
                                    label += f" [{s}]"
                                elif s in ("SEPARATING", "TRACKING"):
                                    color = (249, 115, 22)
                                    label += f" [{s}]"
                                break

                        if t_id in state.engine.active_violations:
                            color = (239, 68, 68)
                            label = f"⚠️ LITTER #{t_id}"

                    if state.show_boxes:
                        x1, y1, x2, y2 = map(int, ltrb)
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                        cv2.rectangle(display_frame, (x1, max(0, y1 - 22)), (x1 + tw + 10, y1), color, -1)
                        cv2.putText(display_frame, label, (x1 + 5, max(12, y1 - 6)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

                if is_violating and state.auto_snap:
                    rec = alert_system.trigger_alert(
                        cam_id=state.active_camera_id or 1,
                        camera_name=state.camera_title or "ECOLIFEBUDDY Camera",
                        frame=display_frame,
                        zone=state.zone or "Monitored Area",
                        violation_type="Litter Discarded",
                        num_violations=len(state.engine.active_violations) or 1
                    )
                    state.last_alert_time = time.time()
                    if rec and rec.get("evidence_path"):
                        state.latest_snapped_file = os.path.basename(rec["evidence_path"])
                        print(f"📸 AUTO-SNAPPED: {state.latest_snapped_file}")

            except Exception:
                pass

        if current_purpose == "LITTER":
            is_alert_active = is_violating or (time.time() - state.last_alert_time < 3.0)
            if is_alert_active and state.show_boxes:
                overlay = display_frame.copy()
                cv2.rectangle(overlay, (0, 0), (w, 54), (220, 38, 38), -1)
                cv2.addWeighted(overlay, 0.85, display_frame, 0.15, 0, display_frame)
                cv2.putText(display_frame, "LITTERING DETECTED  *  EVIDENCE LOGGED", (max(10, w // 2 - 250), 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
        else:
            is_alert_active = False
            if state.show_boxes:
                overlay = display_frame.copy()
                cv2.rectangle(overlay, (0, 0), (w, 42), (15, 23, 42), -1)
                cv2.addWeighted(overlay, 0.75, display_frame, 0.25, 0, display_frame)
                cv2.putText(display_frame, "VISITOR RECOGNITION CAMERA  *  FACIAL AI ACTIVE", (max(10, w // 2 - 270), 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.60, (52, 211, 153), 2, cv2.LINE_AA)

        with state.lock:
            state.people_count = people_c
            state.object_count = objects_c
            state.is_alert = is_alert_active
            state.latest_display_frame = display_frame

        time.sleep(0.015)

# Start background camera capture thread
capture_thread = threading.Thread(target=camera_worker_loop, daemon=True)
capture_thread.start()
visitor_thread = threading.Thread(target=visitor_camera_worker, daemon=True)
visitor_thread.start()
anpr_thread = threading.Thread(target=anpr_worker_loop, daemon=True)
anpr_thread.start()

# ==============================================================================
# STREAMING & WEB ROUTES
# ==============================================================================
def generate_stream():
    """Generates continuous MJPEG video stream."""
    try:
        while True:
            with state.lock:
                frame = state.latest_display_frame

            if frame is None:
                time.sleep(0.03)
                continue

            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 78])
            if not ret:
                time.sleep(0.02)
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            time.sleep(0.033)
    except (GeneratorExit, Exception):
        pass


@app.route('/')
def index():
    """Render the simple, elegant ECOLIFEBUDDY UI."""
    return render_template('index.html')


@app.route('/video_feed')
@app.route('/video_feed/<int:cam_id>')
def video_feed(cam_id=1):
    """MJPEG stream endpoint."""
    return Response(generate_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/violations/<path:filename>')
def serve_violation_image(filename):
    """Serve violation snapshot image."""
    return send_from_directory(VIOLATIONS_DIR, filename)


# ==============================================================================
# REST API FOR INTUITIVE UI
# ==============================================================================
@app.route('/api/status')
@app.route('/api/telemetry')
def get_status():
    """Returns real-time system status and metrics."""
    state.reload_cameras()
    with state.lock:
        return jsonify({
            "status": "ONLINE",
            "system_name": "ECOLIFEBUDDY",
            "active_camera_id": state.active_camera_id,
            "cameras": state.cameras,
            "camera_mode": state.camera_mode,
            "camera_title": state.camera_title,
            "active_source": state.active_source,
            "is_connected": state.is_connected,
            "status_message": state.status_message,
            "ai_enabled": state.ai_enabled,
            "auto_snap": state.auto_snap,
            "show_boxes": state.show_boxes,
            "sound_enabled": state.sound_enabled,
            "is_alert": state.is_alert,
            "people_count": state.people_count,
            "object_count": state.object_count,
            "fps": state.fps,
            "latest_snap": state.latest_snapped_file,
            "anpr": {
                "enabled": state.anpr_enabled,
                "readiness": state.anpr_service.readiness(),
                "result": state.anpr_result,
            },
            "total_violations": len(glob.glob(os.path.join(VIOLATIONS_DIR, "*.jpg")))
        })


@app.route('/api/anpr')
def get_anpr_status():
    """Return the latest non-admission ANPR candidate and runtime readiness."""
    with state.lock:
        return jsonify({
            "enabled": state.anpr_enabled,
            "readiness": state.anpr_service.readiness(),
            "result": state.anpr_result,
        })


@app.route('/api/cameras')
def get_cameras():
    """Returns list of all configured cameras and active camera ID."""
    state.reload_cameras()
    with state.lock:
        return jsonify({
            "system_name": "ECOLIFEBUDDY",
            "active_camera_id": state.active_camera_id,
            "cameras": state.cameras,
            "camera_mode": state.camera_mode,
            "camera_title": state.camera_title
        })


def _apply_camera_selection(cam_id=None, mode=None):
    """Internal helper to switch the active camera by ID or mode."""
    if mode == "demo":
        with state.lock:
            state.camera_mode = "demo"
            state.camera_title = "Demo Simulation Feed"
            state.active_camera_id = 0
            state.active_source = "demo"
        threading.Thread(target=state.open_camera, daemon=True).start()
        return jsonify({
            "success": True,
            "active_camera_id": 0,
            "camera_mode": "demo",
            "camera_title": "Demo Simulation Feed"
        })

    if cam_id is not None:
        try:
            cam_id = int(cam_id)
        except ValueError:
            pass

        state.reload_cameras()
        found = False
        with state.lock:
            for c in state.cameras:
                if c.get("id") == cam_id:
                    found = True
                    state.active_camera_id = cam_id
                    raw_src = normalize_network_source(c.get("source", ""))
                    state.active_source = raw_src
                    state.camera_title = c.get("name")
                    state.zone = c.get("zone", "Monitored Zone")
                    src = str(state.active_source)
                    if is_youtube_url(src):
                        state.camera_mode = "youtube"
                    elif c.get("type") == "USB" or src.isdigit() or src == "0":
                        state.camera_mode = "webcam"
                    else:
                        state.camera_mode = "custom"
                    break

        if found:
            threading.Thread(target=state.open_camera, daemon=True).start()
            return jsonify({
                "success": True,
                "active_camera_id": state.active_camera_id,
                "camera_mode": state.camera_mode,
                "camera_title": state.camera_title,
                "source": state.active_source
            })

    return jsonify({"success": False, "error": f"Camera ID {cam_id} not found"}), 404


@app.route('/api/switch_camera/<int:cam_id>', methods=['GET', 'POST'])
def switch_camera(cam_id):
    """Switch active camera to a configured camera ID via URL parameter."""
    return _apply_camera_selection(cam_id=cam_id)


@app.route('/api/select_camera', methods=['POST'])
def select_camera():
    """Switch active camera to a configured camera ID or demo simulation."""
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    cam_id = data.get("id")
    mode = data.get("mode")
    return _apply_camera_selection(cam_id=cam_id, mode=mode)


@app.route('/api/violations')
def get_violations():
    """Returns all violation evidence records sorted newest first."""
    evidence_files = glob.glob(os.path.join(VIOLATIONS_DIR, "*.jpg"))
    evidence_files.sort(key=os.path.getmtime, reverse=True)

    items = []
    for fpath in evidence_files[:50]:
        fname = os.path.basename(fpath)
        mtime = os.path.getmtime(fpath)
        dt = datetime.datetime.fromtimestamp(mtime)
        
        now = datetime.datetime.now()
        diff = (now - dt).total_seconds()
        if diff < 60:
            time_ago = "Just now"
        elif diff < 3600:
            time_ago = f"{int(diff // 60)}m ago"
        elif diff < 86400:
            time_ago = f"{int(diff // 3600)}h ago"
        else:
            time_ago = dt.strftime("%b %d, %Y")

        items.append({
            "filename": fname,
            "image_url": f"/violations/{fname}",
            "time_ago": time_ago,
            "date_str": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "target": "Discarded Plastic / Debris",
            "confidence": "94%"
        })

    return jsonify({
        "count": len(evidence_files),
        "violations": items
    })


@app.route('/api/toggle_ai', methods=['POST'])
def toggle_ai():
    """Toggle AI detection on or off."""
    with state.lock:
        state.ai_enabled = not state.ai_enabled
        new_val = state.ai_enabled
    return jsonify({"success": True, "ai_enabled": new_val})


@app.route('/api/toggle_autosnap', methods=['POST'])
def toggle_autosnap():
    """Toggle auto-snap on or off."""
    with state.lock:
        state.auto_snap = not state.auto_snap
        new_val = state.auto_snap
    return jsonify({"success": True, "auto_snap": new_val})


@app.route('/api/trigger_test_alert', methods=['POST'])
def trigger_test_alert():
    """Simulate a violation to test auto-snap and evidence capture instantly."""
    with state.lock:
        frame = state.latest_display_frame.copy() if state.latest_display_frame is not None else None
    
    if frame is None:
        with state.lock:
            frame = state.raw_frame.copy() if state.raw_frame is not None else None

    if frame is not None:
        alert_system._last_alert_time[1] = 0
        rec = alert_system.trigger_alert(
            cam_id=state.active_camera_id or 1,
            camera_name=state.camera_title or "ECOLIFEBUDDY Camera",
            frame=frame,
            zone=state.zone or "Monitored Zone",
            violation_type="Littering Incident (Test)",
            num_violations=1
        )
        if rec and rec.get("evidence_path"):
            fname = os.path.basename(rec["evidence_path"])
            with state.lock:
                state.latest_snapped_file = fname
                state.last_alert_time = time.time()
            return jsonify({"success": True, "filename": fname, "image_url": f"/violations/{fname}"})
        else:
            now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"violation_{now_str}.jpg"
            fpath = os.path.join(VIOLATIONS_DIR, fname)
            cv2.imwrite(fpath, frame)
            with state.lock:
                state.latest_snapped_file = fname
                state.last_alert_time = time.time()
            return jsonify({"success": True, "filename": fname, "image_url": f"/violations/{fname}"})

    return jsonify({"success": False, "error": "No frame available"}), 400


@app.route('/api/toggle_mode', methods=['POST'])
def toggle_mode():
    """Cycle or switch camera mode."""
    data = request.get_json(silent=True) or {}
    req_mode = data.get("mode")

    with state.lock:
        if req_mode in ("youtube", "webcam", "demo", "custom"):
            state.camera_mode = req_mode
            if req_mode == "webcam":
                state.active_source = "0"
                state.camera_title = "Laptop Webcam"
            elif req_mode == "demo":
                state.active_source = "demo"
                state.camera_title = "Demo Simulation Feed"
        else:
            mode_cycle = ["youtube", "webcam", "demo"]
            if state.camera_mode in mode_cycle:
                idx = (mode_cycle.index(state.camera_mode) + 1) % len(mode_cycle)
                state.camera_mode = mode_cycle[idx]
            else:
                state.camera_mode = "youtube"
        cur_mode = state.camera_mode

    threading.Thread(target=state.open_camera, daemon=True).start()
    return jsonify({
        "success": True,
        "camera_mode": cur_mode,
        "camera_title": state.camera_title,
        "active_source": state.active_source,
        "active_camera_id": state.active_camera_id
    })


@app.route('/api/set_source', methods=['POST'])
def set_source():
    """Set custom camera source and start detecting immediately."""
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    new_source = normalize_network_source(
        (data.get("source") or request.args.get("source") or "").strip()
    )
    name = (data.get("name") or request.args.get("name") or "").strip()
    zone = (data.get("zone") or request.args.get("zone") or "Monitored Zone").strip()

    if not new_source:
        return jsonify({"success": False, "error": "No source provided"}), 400

    with state.lock:
        state.active_source = new_source
        if is_youtube_url(new_source):
            state.camera_mode = "youtube"
            state.camera_title = name or "YouTube Live Stream"
        elif new_source.isdigit() or new_source == "0":
            state.camera_mode = "webcam"
            state.camera_title = name or f"Webcam ({new_source})"
        else:
            state.camera_mode = "custom"
            state.camera_title = name or "Network Stream"

        # Check if already in cameras list, otherwise append
        existing_idx = None
        for i, c in enumerate(state.cameras):
            if c.get("source") == new_source:
                existing_idx = i
                break

        if existing_idx is not None:
            state.active_camera_id = state.cameras[existing_idx].get("id")
            state.cameras[existing_idx]["name"] = state.camera_title
        else:
            new_id = max([c.get("id", 0) for c in state.cameras] + [0]) + 1
            state.active_camera_id = new_id
            state.cameras.append({
                "id": new_id,
                "name": state.camera_title,
                "source": new_source,
                "type": state.camera_mode.upper(),
                "enabled": True,
                "zone": zone
            })

        config["cameras"] = state.cameras
        save_config(config)

    threading.Thread(target=state.open_camera, daemon=True).start()
    return jsonify({
        "success": True,
        "camera_mode": state.camera_mode,
        "camera_title": state.camera_title,
        "source": new_source,
        "active_camera_id": state.active_camera_id
    })


@app.route('/api/toggle_boxes', methods=['POST'])
def toggle_boxes():
    """Toggle bounding box overlays on the video stream."""
    with state.lock:
        state.show_boxes = not state.show_boxes
        new_val = state.show_boxes
    return jsonify({"success": True, "show_boxes": new_val})


@app.route('/api/toggle_sound', methods=['POST'])
def toggle_sound():
    """Toggle audio alarm."""
    with state.lock:
        state.sound_enabled = not state.sound_enabled
        new_val = state.sound_enabled
    alert_system.sound_enabled = new_val
    return jsonify({"success": True, "sound_enabled": new_val})


@app.route('/api/snapshot', methods=['POST'])
def manual_snapshot():
    """Capture snapshot of current frame."""
    with state.lock:
        frame = state.raw_frame.copy() if state.raw_frame is not None else None

    if frame is None:
        return jsonify({"success": False, "error": "No camera frame available"}), 400

    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"manual_{now_str}.jpg"
    fpath = os.path.join(VIOLATIONS_DIR, fname)
    cv2.imwrite(fpath, frame)

    return jsonify({
        "success": True,
        "filename": fname,
        "image_url": f"/violations/{fname}"
    })


@app.route('/api/violations/<path:filename>', methods=['DELETE'])
def delete_violation(filename):
    """Delete a single violation snapshot."""
    fpath = os.path.join(VIOLATIONS_DIR, filename)
    if os.path.exists(fpath):
        try:
            os.remove(fpath)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": False, "error": "File not found"}), 404


@app.route('/api/violations/clear', methods=['POST'])
def clear_all_violations():
    """Clear all recorded violation images."""
    files = glob.glob(os.path.join(VIOLATIONS_DIR, "*.jpg"))
    for f in files:
        try:
            os.remove(f)
        except Exception:
            pass
    return jsonify({"success": True, "cleared_count": len(files)})


@app.route('/api/export_report')
def export_report():
    """Download forensic audit JSON report."""
    files = glob.glob(os.path.join(VIOLATIONS_DIR, "*.jpg"))
    report = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "system": "ECOLIFEBUDDY AI Litter Detection System",
        "total_incidents": len(files),
        "status": "OPERATIONAL",
        "camera_source": state.camera_mode,
        "active_camera": state.camera_title,
        "incidents": [os.path.basename(f) for f in files[:50]]
    }
    return jsonify(report)


# ==============================================================================
# SERVER LAUNCHER
# ==============================================================================
def start_server(port=5000):
    """Start Flask server and open user browser."""
    def warm_face_recognition():
        try:
            from services.face_service import get_face_service
            get_face_service()
        except Exception as error:
            app.logger.warning("Face recognition warm-up failed: %s", error)

    threading.Thread(target=warm_face_recognition, daemon=True).start()

    def open_browser():
        time.sleep(1.2)
        url = f"http://127.0.0.1:{port}"
        print(f"🌟 ECOLIFEBUDDY AI Ready at: {url}")
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=open_browser, daemon=True).start()
    try:
        app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
    except OSError as e:
        if "10048" in str(e) or "address" in str(e).lower() or "in use" in str(e).lower():
            next_port = port + 1
            print(f"⚠️ Port {port} is occupied. Retrying on port {next_port}...")
            start_server(port=next_port)
        else:
            raise


if __name__ == '__main__':
    print("=" * 60)
    print("  🌱 ECOLIFEBUDDY AI — Smart Litter Detection System")
    print("=" * 60)
    start_server(port=5000)
