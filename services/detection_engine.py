"""Detection and tracking pipeline using Ultralytics YOLO + ByteTrack.
Detects persons and carried objects of interest, maintains per-camera track IDs,
and evaluates virtual tripwires and zone containment rules.
"""
import os
import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Tuple, Optional
from ultralytics import YOLO
from services.geometry import check_line_crossing, point_in_polygon

logger = logging.getLogger("ecolifybuddy.detector")

# Configurable COCO classes of interest
# 0: person
# 24: backpack, 25: umbrella, 26: handbag, 28: suitcase, 39: bottle, 67: cell phone, 73: book
COCO_CLASSES_OF_INTEREST = {
    0: "person",
    24: "backpack",
    25: "umbrella",
    26: "handbag",
    28: "suitcase",
    39: "bottle",
    67: "cell phone",
    73: "box",
}

OBJECT_CLASS_IDS = [24, 25, 26, 28, 39, 67, 73]


class VideoDetectionEngine:
    """YOLO + ByteTrack detector for persons and carried accessories."""

    def __init__(self, model_path: Optional[str] = None, conf: float = 0.25):
        if not model_path:
            model_path = os.getenv("DETECTION_MODEL", "yolo26n.pt")
            if not os.path.exists(model_path):
                # Fallback to any local weights if yolo26n.pt is missing
                for alt in ["yolo26m.pt", "yolov8m.pt", "yolov8n.pt"]:
                    if os.path.exists(alt):
                        model_path = alt
                        break

        self.model_path = model_path
        self.conf = conf
        self.model = YOLO(model_path)
        logger.info("Loaded detection model: %s", self.model_path)

        # Track history per camera: {camera_id: {track_id: {"trajectory": [(cx, cy)], "first_seen": t, ...}}}
        self.camera_tracks: Dict[int, Dict[int, Dict[str, Any]]] = {}

    def process_frame(
        self,
        frame: np.ndarray,
        camera_id: int,
        zones: Optional[List[Dict[str, Any]]] = None,
        timestamp: float = 0.0,
    ) -> Dict[str, Any]:
        """Run YOLO + ByteTrack on a video frame.
        Evaluates virtual tripwires and zone containment.
        Returns:
            {
                "persons": [
                    {
                        "track_id": int,
                        "box": [x1, y1, x2, y2],
                        "conf": float,
                        "crop": np.ndarray,
                        "carried_objects": [str],
                        "events": [str],  # e.g. ["ENTRY", "LOITERING"]
                        "active_zone_id": Optional[int]
                    }
                ],
                "objects": [{"class_name": str, "box": [x1, y1, x2, y2], "conf": float}],
                "emitted_events": [dict]
            }
        """
        if frame is None or frame.size == 0:
            return {"persons": [], "objects": [], "emitted_events": []}

        h, w = frame.shape[:2]
        if camera_id not in self.camera_tracks:
            self.camera_tracks[camera_id] = {}

        active_camera_tracks = self.camera_tracks[camera_id]

        # Run ByteTrack multi-object tracking
        results = self.model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=list(COCO_CLASSES_OF_INTEREST.keys()),
            conf=self.conf,
            verbose=False,
        )

        detected_persons = []
        detected_objects = []
        emitted_events = []

        if not results or not results[0].boxes:
            return {"persons": [], "objects": [], "emitted_events": []}

        boxes = results[0].boxes

        # First pass: collect detected carried objects
        for box in boxes:
            cls_id = int(box.cls[0].item())
            if cls_id in OBJECT_CLASS_IDS:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().tolist()
                c = float(box.conf[0].item())
                detected_objects.append({
                    "class_name": COCO_CLASSES_OF_INTEREST.get(cls_id, "object"),
                    "box": [int(x1), int(y1), int(x2), int(y2)],
                    "conf": round(c, 2),
                })

        # Second pass: process tracked persons
        for box in boxes:
            cls_id = int(box.cls[0].item())
            if cls_id != 0:  # 0 is 'person'
                continue

            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].cpu().numpy().tolist()]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            track_id = int(box.id[0].item()) if box.id is not None else -1
            conf = float(box.conf[0].item())

            # Person center point (bottom center of bounding box gives ground position)
            cx, cy = (x1 + x2) // 2, y2

            # Person crop
            crop = frame[y1:y2, x1:x2].copy() if (x2 > x1 and y2 > y1) else None

            # Associate carried objects (objects overlapping person bounding box)
            carried = []
            for obj in detected_objects:
                ox1, oy1, ox2, oy2 = obj["box"]
                ocx, ocy = (ox1 + ox2) // 2, (oy1 + oy2) // 2
                if x1 <= ocx <= x2 and y1 <= ocy <= y2:
                    carried.append(obj["class_name"])

            person_events = []
            active_zone_id = None

            # Track trajectory update & tripwire line crossing
            if track_id != -1:
                if track_id not in active_camera_tracks:
                    active_camera_tracks[track_id] = {
                        "trajectory": [(cx, cy)],
                        "first_seen": timestamp,
                        "last_seen": timestamp,
                        "zone_dwell": {},  # {zone_id: seconds}
                    }
                else:
                    prev_pos = active_camera_tracks[track_id]["trajectory"][-1]
                    active_camera_tracks[track_id]["trajectory"].append((cx, cy))
                    active_camera_tracks[track_id]["last_seen"] = timestamp

                    # Evaluate virtual tripwire lines
                    if zones:
                        for z in zones:
                            tripwire = z.get("entry_line_coords")
                            if tripwire and len(tripwire) >= 2:
                                crossing = check_line_crossing(prev_pos, (cx, cy), tripwire)
                                if crossing:
                                    person_events.append(crossing)
                                    emitted_events.append({
                                        "event_type": crossing,
                                        "track_id": track_id,
                                        "camera_id": camera_id,
                                        "zone_id": z.get("id"),
                                        "carried_objects": carried,
                                        "box": [x1, y1, x2, y2],
                                        "crop": crop,
                                    })

                            # Evaluate polygon zone containment
                            poly = z.get("polygon_coords")
                            if poly and point_in_polygon((cx, cy), poly):
                                active_zone_id = z.get("id")
                                z_type = z.get("zone_type", "GENERAL")
                                if z_type == "RESTRICTED":
                                    person_events.append("RESTRICTED_ZONE")
                                    emitted_events.append({
                                        "event_type": "RESTRICTED_ZONE",
                                        "track_id": track_id,
                                        "camera_id": camera_id,
                                        "zone_id": z.get("id"),
                                        "carried_objects": carried,
                                        "box": [x1, y1, x2, y2],
                                        "crop": crop,
                                    })

            detected_persons.append({
                "track_id": track_id,
                "box": [x1, y1, x2, y2],
                "conf": round(conf, 2),
                "crop": crop,
                "carried_objects": carried,
                "events": person_events,
                "active_zone_id": active_zone_id,
            })

        return {
            "persons": detected_persons,
            "objects": detected_objects,
            "emitted_events": emitted_events,
        }
