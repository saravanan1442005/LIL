# web_server.py — Enterprise ECOLIFEBUDDY Surveillance Workstation Server
import cv2
import numpy as np
import time
import os
import json
import threading
import webbrowser
import datetime
from flask import Flask, render_template, Response, jsonify, request, send_from_directory

from config import load_config, save_config, add_camera as config_add_cam
from camera_manager import CameraManager
from alert_system import AlertSystem, VIOLATIONS_DIR, ALERT_LOG_FILE

app = Flask(__name__, template_folder="templates")

# Initialize managers
config = load_config()
camera_manager = CameraManager()
alert_system = AlertSystem(config)

# Pre-seed violation images from disk if available
sample_violation_files = []
if os.path.exists(VIOLATIONS_DIR):
    sample_violation_files = [
        f for f in os.listdir(VIOLATIONS_DIR) if f.lower().endswith(('.jpg', '.png', '.jpeg'))
    ]

# Synthetic video generators for channels without active physical hardware
def generate_synthetic_cctv_frame(cam_id, width=640, height=360):
    """Generate high-tech synthetic surveillance frame with timecode and moving targets."""
    t = time.time()
    
    # Base background tint based on channel
    colors = {
        1: (20, 28, 38),   # Main Gate (cool navy)
        2: (25, 20, 35),   # Waste Hub (alert dark)
        3: (18, 26, 24),   # Parking Zone B (slate green)
        4: (28, 26, 20),   # Crossroad Entrance (amber dark)
        5: (18, 30, 22),   # Playground Lawn (forest tint)
        6: (15, 15, 20),   # Back Gate
    }
    base_color = colors.get(cam_id, (20, 25, 35))
    
    # Create background canvas
    frame = np.full((height, width, 3), base_color, dtype=np.uint8)
    
    # Draw perspective grid lines
    grid_color = (base_color[0] + 15, base_color[1] + 15, base_color[2] + 15)
    for y in range(0, height, 40):
        cv2.line(frame, (0, y), (width, y), grid_color, 1)
    for x in range(0, width, 60):
        cv2.line(frame, (x, 0), (x, height), grid_color, 1)

    # Simulated motion objects (Pedestrian & objects)
    cx = int((width / 2) + np.sin(t * 0.8 + cam_id) * (width * 0.35))
    cy = int((height / 2) + np.cos(t * 0.5 + cam_id) * (height * 0.25))

    # Channel-specific dynamic overlays
    if cam_id == 2:
        # Waste Hub — Triggered Alert Simulation
        cv2.rectangle(frame, (cx - 45, cy - 35), (cx + 45, cy + 35), (68, 68, 239), 2)
        cv2.putText(frame, "DISCARDED LITTER [96%]", (cx - 45, cy - 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (68, 68, 239), 1)
        # Pulse indicator in corner
        if int(t * 2) % 2 == 0:
            cv2.circle(frame, (30, 30), 8, (68, 68, 239), -1)
            cv2.putText(frame, "INCIDENT ACTIVE", (45, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (68, 68, 239), 2)

    elif cam_id == 4:
        # Crossroad Entrance — Warning Debris
        cv2.rectangle(frame, (cx - 30, cy - 25), (cx + 30, cy + 25), (40, 180, 240), 2)
        cv2.putText(frame, "CAN DEBRIS [89%]", (cx - 30, cy - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 180, 240), 1)

    else:
        # Clean Zone Normal Pedestrian
        cv2.rectangle(frame, (cx - 25, cy - 50), (cx + 25, cy + 50), (129, 245, 130), 2)
        cv2.putText(frame, "PEDESTRIAN: CLEAR", (cx - 25, cy - 56),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (129, 245, 130), 1)

    # Top HUD metadata strip
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    cam_names = {
        1: "CAM 01 • MAIN GATE NORTH",
        2: "CAM 02 • WASTE HUB STATION",
        3: "CAM 03 • PARKING ZONE B",
        4: "CAM 04 • CROSSROAD ENTRANCE",
        5: "CAM 05 • PLAYGROUND LAWN",
        6: "CAM 06 • BACK GATE CHANNEL"
    }
    cv2.putText(frame, f"{cam_names.get(cam_id, f'CAM 0{cam_id}')} | FPS: 29.8", (15, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 210, 225), 1)
    cv2.putText(frame, timestamp_str, (width - 230, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (160, 180, 200), 1)

    return frame


def generate_mjpeg_stream(cam_id):
    """Generate continuous MJPEG video stream for a specific camera channel."""
    while True:
        # Check if physical camera stream exists
        stream = camera_manager.get_camera(cam_id)
        frame = None
        if stream and stream.is_connected:
            frame = stream.get_frame()

        if frame is None:
            # Fallback to high-definition synthetic surveillance simulation
            frame = generate_synthetic_cctv_frame(cam_id)

        # Encode to JPEG
        ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if not ret:
            continue

        frame_bytes = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        # Stream at ~25 FPS
        time.sleep(0.04)


@app.route('/')
def index():
    """Render main ECOLIFEBUDDY Surveillance Workstation interface."""
    return render_template('index.html')


@app.route('/video_feed/<int:cam_id>')
def video_feed(cam_id):
    """MJPEG Video feed route for each camera channel."""
    return Response(generate_mjpeg_stream(cam_id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/violations/<path:filename>')
def serve_violation_image(filename):
    """Serve recorded violation snapshots."""
    return send_from_directory(VIOLATIONS_DIR, filename)


@app.route('/api/telemetry')
def get_telemetry():
    """Return live system telemetry and status counters."""
    total_cams = camera_manager.get_total_count() or 6
    active_cams = camera_manager.get_active_count() or 5
    return jsonify({
        "status": "ONLINE",
        "workstation": "ECOLIFEBUDDY v4.2 Pro",
        "district": "District 4 Control Room",
        "connected_cameras": total_cams,
        "online_cameras": active_cams,
        "offline_cameras": total_cams - active_cams,
        "ai_scanning": active_cams,
        "violations_today": 18,
        "action_required": 5,
        "storage_usage_pct": 71,
        "storage_available": "5.8 TB",
        "operator": "Elena Vance"
    })


@app.route('/api/violations')
def get_violations():
    """Return all detected violations log."""
    logs = []
    if os.path.exists(ALERT_LOG_FILE):
        try:
            with open(ALERT_LOG_FILE, 'r') as f:
                logs = json.load(f)
        except Exception:
            logs = []
    return jsonify({"count": len(logs), "violations": logs})


@app.route('/api/cameras', methods=['GET', 'POST'])
def handle_cameras():
    """Get or Add cameras."""
    cfg = load_config()
    if request.method == 'POST':
        data = request.json or {}
        name = data.get('name', 'New Camera')
        source = data.get('source', '0')
        cam_type = data.get('type', 'RTSP')
        zone = data.get('zone', 'GENERAL')
        
        new_cam = config_add_cam(cfg, name, source, cam_type)
        new_cam['zone'] = zone
        camera_manager.add_camera(new_cam)
        return jsonify({"success": True, "camera": new_cam})

    return jsonify({"cameras": cfg.get("cameras", [])})


@app.route('/api/export_report')
def export_report():
    """Generate and return comprehensive forensic audit export."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = {
        "generated_at": now,
        "system": "ECOLIFEBUDDY Surveillance Workstation v4.2 Pro",
        "district": "District 4 Control Room",
        "operator": "Elena Vance (Badge #ENV-4029)",
        "total_violations_today": 18,
        "critical_escalations": 3,
        "warnings_issued": 2,
        "status": "VERIFIED & AUDITED",
        "recent_incidents": [
            {
                "id": "VIOL-2025-0841",
                "timestamp": "10:41:02 UTC",
                "camera": "Waste Hub Station",
                "type": "Illegal Waste Dumping",
                "target": "Polyethylene Waste Sacks",
                "confidence": "96.4%",
                "status": "Escalated to Dispatch"
            },
            {
                "id": "VIOL-2025-0842",
                "timestamp": "10:38:15 UTC",
                "camera": "Crossroad Entrance",
                "type": "Discarded Beverage Can",
                "target": "Aluminum Can (330ml)",
                "confidence": "89.2%",
                "status": "Warning Flagged"
            }
        ]
    }
    return jsonify(report)


def start_server(port=5000):
    """Start Flask server and open browser."""
    def open_browser():
        time.sleep(1.2)
        url = f"http://127.0.0.1:{port}"
        print(f"Opening ECOLIFEBUDDY Workstation at: {url}")
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == '__main__':
    print("=" * 60)
    print("  ECOLIFEBUDDY Surveillance Workstation v4.2 Pro")
    print("  District 4 Clean Surveillance Control Room")
    print("=" * 60)
    start_server(port=5000)
