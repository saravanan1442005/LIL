# camera_manager.py — Manages multiple CCTV camera streams with thread-safe access
import cv2
import threading
import time
import queue
from stream_resolver import resolve_stream_source, is_youtube_url, resolve_youtube_stream


class CameraStream:
    """A single camera stream running in its own thread for non-blocking capture."""

    def __init__(self, camera_config, detection_pipeline=None):
        self.config = camera_config
        self.cam_id = camera_config["id"]
        self.name = camera_config["name"]
        self.source = camera_config["source"]
        self.cam_type = camera_config.get("type", "RTSP")
        self.enabled = camera_config.get("enabled", True)
        self.zone = camera_config.get("zone", "General Area")

        self.cap = None
        self.frame = None
        self.last_frame_time = 0
        self.fps = 0
        self.is_running = False
        self.is_connected = False
        self.error_message = ""
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5  # seconds

        # Detection results for this camera
        self.detection_pipeline = detection_pipeline
        self.detections = []
        self.tracks = []
        self.violation_active = False
        self.violation_count = 0

        # Thread-safe frame buffer
        self._lock = threading.Lock()
        self._thread = None
        self._stop_event = threading.Event()

    def _parse_source(self):
        """Convert source string to OpenCV-compatible source."""
        if self.cam_type == "USB":
            try:
                return int(self.source)
            except ValueError:
                return 0
        elif self.cam_type == "FILE":
            return str(self.source)
        elif self.cam_type == "YOUTUBE" or is_youtube_url(str(self.source)):
            resolved, meta = resolve_stream_source(self.source)
            if meta and meta.get("title") and self.name in ("Live Camera", "Camera 1", "kk"):
                self.name = meta.get("title")
            return resolved
        else:
            # RTSP or HTTP URL
            return str(self.source)

    def start(self):
        """Start the camera capture thread."""
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        self.is_running = True

    def stop(self):
        """Stop the camera capture thread."""
        self._stop_event.set()
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.is_connected = False

    def _connect(self):
        """Attempt to connect to the camera source."""
        source = self._parse_source()
        try:
            self.cap = cv2.VideoCapture(source)
            if self.cam_type in ("RTSP", "HTTP"):
                # Optimize for network streams
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            if self.cap.isOpened():
                ret, test_frame = self.cap.read()
                if ret and test_frame is not None:
                    self.is_connected = True
                    self.error_message = ""
                    self.reconnect_attempts = 0
                    return True

            self.is_connected = False
            self.error_message = f"Cannot open source: {source}"
            return False
        except Exception as e:
            self.is_connected = False
            self.error_message = str(e)
            return False

    def _capture_loop(self):
        """Main capture loop running in a separate thread."""
        if not self._connect():
            # Retry connection loop
            while not self._stop_event.is_set():
                self.reconnect_attempts += 1
                if self.reconnect_attempts > self.max_reconnect_attempts:
                    self.error_message = "Max reconnect attempts reached"
                    return
                self.error_message = f"Reconnecting... ({self.reconnect_attempts}/{self.max_reconnect_attempts})"
                time.sleep(self.reconnect_delay)
                if self._connect():
                    break

        frame_count = 0
        fps_start_time = time.time()

        while not self._stop_event.is_set():
            if not self.cap or not self.cap.isOpened():
                self.is_connected = False
                self.error_message = "Connection lost"
                # Try to reconnect
                time.sleep(self.reconnect_delay)
                if not self._connect():
                    continue

            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.is_connected = False
                self.error_message = "Frame read failed"
                time.sleep(0.5)
                continue

            self.is_connected = True
            self.error_message = ""

            # Calculate FPS
            frame_count += 1
            elapsed = time.time() - fps_start_time
            if elapsed >= 1.0:
                self.fps = frame_count / elapsed
                frame_count = 0
                fps_start_time = time.time()

            # Store frame thread-safely
            with self._lock:
                self.frame = frame
                self.last_frame_time = time.time()

            # Small sleep to prevent CPU overload
            time.sleep(0.01)

        # Cleanup
        if self.cap and self.cap.isOpened():
            self.cap.release()

    def get_frame(self):
        """Get the latest frame (thread-safe)."""
        with self._lock:
            if self.frame is not None:
                return self.frame.copy()
        return None

    def get_status(self):
        """Get camera status information."""
        return {
            "id": self.cam_id,
            "name": self.name,
            "connected": self.is_connected,
            "running": self.is_running,
            "fps": round(self.fps, 1),
            "error": self.error_message,
            "violations": self.violation_count,
            "zone": self.zone,
        }


class CameraManager:
    """Manages all camera streams."""

    def __init__(self):
        self.cameras = {}  # {cam_id: CameraStream}

    def add_camera(self, camera_config):
        """Add and start a new camera."""
        cam_id = camera_config["id"]
        if cam_id in self.cameras:
            self.cameras[cam_id].stop()
        stream = CameraStream(camera_config)
        self.cameras[cam_id] = stream
        if camera_config.get("enabled", True):
            stream.start()
        return stream

    def remove_camera(self, cam_id):
        """Stop and remove a camera."""
        if cam_id in self.cameras:
            self.cameras[cam_id].stop()
            del self.cameras[cam_id]

    def get_camera(self, cam_id):
        """Get a camera stream by ID."""
        return self.cameras.get(cam_id)

    def get_all_cameras(self):
        """Get all camera streams."""
        return self.cameras

    def get_all_frames(self):
        """Get the latest frame from every camera."""
        frames = {}
        for cam_id, stream in self.cameras.items():
            frame = stream.get_frame()
            if frame is not None:
                frames[cam_id] = frame
        return frames

    def get_all_statuses(self):
        """Get status of all cameras."""
        return {cam_id: stream.get_status() for cam_id, stream in self.cameras.items()}

    def stop_all(self):
        """Stop all camera streams."""
        for stream in self.cameras.values():
            stream.stop()
        self.cameras.clear()

    def get_active_count(self):
        """Number of cameras currently connected."""
        return sum(1 for s in self.cameras.values() if s.is_connected)

    def get_total_count(self):
        """Total number of configured cameras."""
        return len(self.cameras)
