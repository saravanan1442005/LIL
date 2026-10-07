# config.py — Persistent configuration for the CCTV monitoring system
import json
import os

CONFIG_FILE = "litter_guard_config.json"

DEFAULT_CONFIG = {
    "cameras": [],
    "alert_settings": {
        "sound_enabled": True,
        "save_evidence": True,
        "email_enabled": False,
        "email_to": "",
        "email_from": "",
        "smtp_server": "",
        "smtp_port": 587,
        "cooldown_seconds": 10,
    },
    "detection_settings": {
        "model_path": "yolo26m.pt",
        "confidence_threshold": 0.25,
        "frame_width": 640,
        "frame_height": 480,
    },
    "ui_settings": {
        "grid_columns": 2,
        "show_bounding_boxes": True,
        "show_labels": True,
        "show_fps": True,
    },
}


def load_config():
    """Load configuration from disk, or create default."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            # Merge with defaults for any missing keys
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if sub_key not in config[key]:
                            config[key][sub_key] = sub_value
            return config
        except (json.JSONDecodeError, IOError):
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """Persist configuration to disk."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Failed to save config: {e}")
        return False


def add_camera(config, name, source, cam_type="RTSP"):
    """Add a camera to the configuration.
    
    Args:
        config: The configuration dict.
        name: Human-readable camera name.
        source: Video source (RTSP URL, HTTP URL, or USB device index).
        cam_type: Type of camera - 'RTSP', 'HTTP', 'USB', 'FILE'.
    """
    camera = {
        "id": len(config["cameras"]) + 1,
        "name": name,
        "source": source,
        "type": cam_type,
        "enabled": True,
        "zone": "General Area",
    }
    config["cameras"].append(camera)
    save_config(config)
    return camera


def remove_camera(config, camera_id):
    """Remove a camera by its ID."""
    config["cameras"] = [c for c in config["cameras"] if c["id"] != camera_id]
    save_config(config)


def update_camera(config, camera_id, **kwargs):
    """Update camera properties."""
    for cam in config["cameras"]:
        if cam["id"] == camera_id:
            cam.update(kwargs)
            break
    save_config(config)
