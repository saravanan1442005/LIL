# alert_system.py — Enhanced alert system with sound, logging, email, and evidence saving
import cv2
import os
import datetime
import threading
import json
import winsound
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage


VIOLATIONS_DIR = "violations"
ALERT_LOG_FILE = "alert_log.json"


class AlertSystem:
    """Manages alerts, evidence saving, logging, and notifications."""

    def __init__(self, config):
        self.config = config.get("alert_settings", {})
        self.sound_enabled = self.config.get("sound_enabled", True)
        self.save_evidence_enabled = self.config.get("save_evidence", True)
        self.email_enabled = self.config.get("email_enabled", False)
        self.cooldown_seconds = min(self.config.get("cooldown_seconds", 3), 3)

        # Track cooldowns per camera
        self._last_alert_time = {}  # {cam_id: timestamp}
        self._alert_log = []
        self._lock = threading.Lock()

        # Ensure directories exist
        os.makedirs(VIOLATIONS_DIR, exist_ok=True)

        # Load existing alert log
        self._load_log()

    def _load_log(self):
        """Load the alert log from disk."""
        if os.path.exists(ALERT_LOG_FILE):
            try:
                with open(ALERT_LOG_FILE, "r") as f:
                    self._alert_log = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._alert_log = []

    def _save_log(self):
        """Persist the alert log to disk."""
        try:
            with open(ALERT_LOG_FILE, "w") as f:
                json.dump(self._alert_log, f, indent=2, default=str)
        except IOError:
            pass

    def _is_on_cooldown(self, cam_id):
        """Check if this camera is still in alert cooldown."""
        last_time = self._last_alert_time.get(cam_id, 0)
        return (datetime.datetime.now().timestamp() - last_time) < self.cooldown_seconds

    def trigger_alert(self, cam_id, camera_name, frame, zone="General Area",
                      violation_type="Littering", num_violations=1):
        """Trigger a full alert for a detected violation.
        
        Returns the alert record or None if on cooldown.
        """
        if self._is_on_cooldown(cam_id):
            return None

        with self._lock:
            self._last_alert_time[cam_id] = datetime.datetime.now().timestamp()

        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        readable_time = now.strftime("%Y-%m-%d %H:%M:%S")

        # Build alert record
        alert_record = {
            "timestamp": readable_time,
            "camera_id": cam_id,
            "camera_name": camera_name,
            "zone": zone,
            "violation_type": violation_type,
            "num_violations": num_violations,
            "evidence_path": None,
            "acknowledged": False,
        }

        # Save evidence screenshot
        if self.save_evidence_enabled and frame is not None:
            evidence_path = self._save_evidence(frame, cam_id, camera_name,
                                                 timestamp_str, readable_time)
            alert_record["evidence_path"] = evidence_path

        # Play alert sound
        if self.sound_enabled:
            self._play_alert_sound()

        # Send email notification (async)
        if self.email_enabled:
            evidence_path = alert_record.get("evidence_path")
            threading.Thread(
                target=self._send_email_alert,
                args=(alert_record, evidence_path),
                daemon=True
            ).start()

        # Log the alert
        with self._lock:
            self._alert_log.append(alert_record)
            # Keep only the last 500 alerts in memory
            if len(self._alert_log) > 500:
                self._alert_log = self._alert_log[-500:]
            self._save_log()

        return alert_record

    def _save_evidence(self, frame, cam_id, camera_name, timestamp_str, readable_time):
        """Save annotated screenshot directly into violations directory."""
        os.makedirs(VIOLATIONS_DIR, exist_ok=True)
        filename = f"violation_{timestamp_str}.jpg"
        filepath = os.path.join(VIOLATIONS_DIR, filename)

        # Annotate the frame
        annotated = frame.copy()
        h, w = annotated.shape[:2]
        # Red evidence banner at top
        cv2.rectangle(annotated, (0, 0), (w, 64), (180, 20, 20), -1)
        cv2.putText(annotated, "LITTERING EVIDENCE CAPTURED",
                    (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(annotated, f"Camera: {camera_name}  |  {readable_time}",
                    (15, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 230, 245), 1, cv2.LINE_AA)
        # Timestamp at bottom right
        cv2.putText(annotated, readable_time,
                    (w - 220, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        cv2.imwrite(filepath, annotated, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"📸 AUTO-SNAPPED EVIDENCE: {filepath}")
        return filepath

    def _play_alert_sound(self):
        """Play a Windows alert sound."""
        try:
            # Play the system exclamation sound asynchronously
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except Exception:
            try:
                # Fallback: system beep
                winsound.Beep(1000, 300)
            except Exception:
                pass

    def _send_email_alert(self, alert_record, evidence_path=None):
        """Send email notification to authorities (runs in background thread)."""
        try:
            smtp_server = self.config.get("smtp_server", "")
            smtp_port = self.config.get("smtp_port", 587)
            email_from = self.config.get("email_from", "")
            email_to = self.config.get("email_to", "")
            email_password = self.config.get("email_password", "")

            if not all([smtp_server, email_from, email_to]):
                return

            msg = MIMEMultipart()
            msg["From"] = email_from
            msg["To"] = email_to
            msg["Subject"] = f"🚨 Littering Alert - {alert_record['camera_name']} - {alert_record['timestamp']}"

            body = f"""
LITTERING VIOLATION DETECTED

Camera: {alert_record['camera_name']}
Zone: {alert_record['zone']}
Time: {alert_record['timestamp']}
Type: {alert_record['violation_type']}
Number of Violations: {alert_record['num_violations']}

This is an automated alert from the LitterGuard CCTV Monitoring System.
Please take appropriate action.
"""
            msg.attach(MIMEText(body, "plain"))

            # Attach evidence image if available
            if evidence_path and os.path.exists(evidence_path):
                with open(evidence_path, "rb") as f:
                    img = MIMEImage(f.read(), name=os.path.basename(evidence_path))
                    msg.attach(img)

            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                server.starttls()
                if email_password:
                    server.login(email_from, email_password)
                server.send_message(msg)

        except Exception as e:
            print(f"Email alert failed: {e}")

    def get_recent_alerts(self, count=50):
        """Get the most recent alerts."""
        with self._lock:
            return list(reversed(self._alert_log[-count:]))

    def get_alert_count(self):
        """Get total number of alerts."""
        return len(self._alert_log)

    def get_today_alert_count(self):
        """Get number of alerts from today."""
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        return sum(1 for a in self._alert_log if a["timestamp"].startswith(today))

    def acknowledge_alert(self, index):
        """Mark an alert as acknowledged."""
        with self._lock:
            if 0 <= index < len(self._alert_log):
                self._alert_log[index]["acknowledged"] = True
                self._save_log()

    def clear_alerts(self):
        """Clear all alerts."""
        with self._lock:
            self._alert_log.clear()
            self._save_log()

    def update_settings(self, config):
        """Update alert settings from config."""
        self.config = config.get("alert_settings", {})
        self.sound_enabled = self.config.get("sound_enabled", True)
        self.save_evidence_enabled = self.config.get("save_evidence", True)
        self.email_enabled = self.config.get("email_enabled", False)
        self.cooldown_seconds = self.config.get("cooldown_seconds", 10)
