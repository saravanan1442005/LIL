# rule_engine.py — Precise Behavior Analysis & Anti-False-Positive Rule Engine
import math

class EcoRuleEngine:
    def __init__(self):
        # Attribute used by main.py & web_server.py for visual feedback
        self.tracking_states = {}
        self.active_violations = set()

        # Stability tracking: object must remain stationary for N frames after being dropped
        self.min_stable_frames = 4
        self.stability_counters = {}

        # Position history: {track_id: [(cx, cy), ...]}
        self.object_positions = {}
        self.person_positions = {}
        self.position_history_len = 30

        # Motion & Carriage Metadata:
        # {obj_id: {"total_movement": float, "was_carried": bool, "carrier_id": int, "frames_near": int}}
        self.object_metadata = {}

    def _get_center(self, track):
        """Get center point of a track's bounding box."""
        ltrb = track.to_ltrb()
        return ((ltrb[0] + ltrb[2]) / 2, (ltrb[1] + ltrb[3]) / 2)

    def _get_bbox_size(self, track):
        """Get width and height of a track's bounding box."""
        ltrb = track.to_ltrb()
        return (ltrb[2] - ltrb[0], ltrb[3] - ltrb[1])

    def _compute_iou(self, track_a, track_b):
        """Compute Intersection over Union between two tracks."""
        a = track_a.to_ltrb()
        b = track_b.to_ltrb()
        
        x1 = max(a[0], b[0])
        y1 = max(a[1], b[1])
        x2 = min(a[2], b[2])
        y2 = min(a[3], b[3])
        
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        if intersection == 0:
            return 0.0
        
        area_a = (a[2] - a[0]) * (a[3] - a[1])
        area_b = (b[2] - b[0]) * (b[3] - b[1])
        union = area_a + area_b - intersection
        
        return intersection / union if union > 0 else 0.0

    def _is_inside_person(self, obj_track, person_track):
        """Check if the litter object is inside the person's bounding box."""
        p = person_track.to_ltrb()
        o_cx, o_cy = self._get_center(obj_track)
        p_w, p_h = p[2] - p[0], p[3] - p[1]
        margin_x, margin_y = p_w * 0.15, p_h * 0.15
        
        return (p[0] - margin_x <= o_cx <= p[2] + margin_x and 
                p[1] - margin_y <= o_cy <= p[3] + margin_y)

    def _adaptive_threshold(self, person_track):
        """Calculate distance thresholds based on person size in camera frame."""
        p_w, p_h = self._get_bbox_size(person_track)
        person_size = max(p_w, p_h)
        
        held_threshold = max(person_size * 0.45, 55)
        litter_threshold = max(person_size * 1.1, 120)
        return held_threshold, litter_threshold

    def _update_object(self, obj_id, center):
        """Track object position and cumulative displacement."""
        if obj_id not in self.object_positions:
            self.object_positions[obj_id] = []
            self.object_metadata[obj_id] = {
                "total_movement": 0.0,
                "was_carried": False,
                "carrier_id": None,
                "frames_near": 0,
            }

        hist = self.object_positions[obj_id]
        if hist:
            step_dist = math.dist(center, hist[-1])
            self.object_metadata[obj_id]["total_movement"] += step_dist

        hist.append(center)
        if len(hist) > self.position_history_len:
            hist.pop(0)

    def _update_person(self, p_id, center):
        """Track person position history."""
        if p_id not in self.person_positions:
            self.person_positions[p_id] = []
        hist = self.person_positions[p_id]
        hist.append(center)
        if len(hist) > self.position_history_len:
            hist.pop(0)

    def _is_object_stationary(self, obj_id):
        """Check if an object has come to rest (barely moving in recent frames)."""
        hist = self.object_positions.get(obj_id, [])
        if len(hist) < 4:
            return False
        recent = hist[-4:]
        max_movement = max(math.dist(recent[i], recent[i - 1]) for i in range(1, len(recent)))
        return max_movement < 6.0

    def is_littering(self, tracks):
        """
        Evaluate tracking states to detect genuine littering while rejecting static background objects.
        A violation ONLY triggers if:
        1. Object was genuinely CARRIED/HELD by a person (not just a static item someone walked past).
        2. The person SEPARATED from the object.
        3. The object came to REST (stationary).
        4. The person WALKED AWAY from the resting object (abandonment).
        """
        active_people = {}
        active_objects = {}

        for t in tracks:
            if not t.is_confirmed():
                continue
            cls = t.get_det_class()
            if cls == "person":
                active_people[t.track_id] = t
            else:
                active_objects[t.track_id] = t

        # Update person movements
        for p_id, p in active_people.items():
            self._update_person(p_id, self._get_center(p))

        # Update and evaluate objects
        for obj_id, obj in active_objects.items():
            obj_center = self._get_center(obj)
            self._update_object(obj_id, obj_center)
            is_stat = self._is_object_stationary(obj_id)
            meta = self.object_metadata[obj_id]

            for p_id, p in active_people.items():
                p_center = self._get_center(p)
                dist = math.dist(obj_center, p_center)
                pair_key = (p_id, obj_id)
                held_thresh, litter_thresh = self._adaptive_threshold(p)

                iou = self._compute_iou(obj, p)
                is_inside = self._is_inside_person(obj, p)
                is_near = (iou > 0.06) or is_inside or (dist < held_thresh)

                curr_state = self.tracking_states.get(pair_key)

                # ==============================================================
                # 1. NEAR PERSON: HELD vs STATIC BACKGROUND FILTER
                # ==============================================================
                if is_near:
                    # An object is only HELD if it was carried (has real movement).
                    # If it has been static and hasn't moved (>20px), person just walked near it!
                    if meta["was_carried"] or meta["total_movement"] > 22.0:
                        self.tracking_states[pair_key] = "HELD"
                        meta["was_carried"] = True
                        meta["carrier_id"] = p_id
                        self.active_violations.discard(obj_id)
                        self.stability_counters[obj_id] = 0
                    else:
                        # Static background object near person (e.g. coffee mug on desk, bag on chair)
                        # DO NOT mark as HELD!
                        self.tracking_states[pair_key] = "STATIC"
                    continue

                # ==============================================================
                # 2. SEPARATION & DROP (Object was held, now separated)
                # ==============================================================
                if curr_state == "HELD":
                    self.tracking_states[pair_key] = "SEPARATING"
                    self.stability_counters[obj_id] = 0

                # ==============================================================
                # 3. ABANDONMENT & LITTERING DETECTION
                # ==============================================================
                if curr_state in ("SEPARATING", "TRACKING"):
                    # Only objects that were legitimately carried can become litter
                    if meta["was_carried"]:
                        if dist > litter_thresh:
                            self.tracking_states[pair_key] = "TRACKING"
                            # Person is far away and object is at rest
                            if is_stat:
                                self.stability_counters[obj_id] = self.stability_counters.get(obj_id, 0) + 1
                                if self.stability_counters[obj_id] >= self.min_stable_frames:
                                    self.active_violations.add(obj_id)
                        elif dist <= held_thresh:
                            # Person returned and retrieved the object
                            self.tracking_states[pair_key] = "HELD"
                            self.active_violations.discard(obj_id)
                            self.stability_counters[obj_id] = 0

        # ==============================================================
        # 4. CLEANUP: Objects no longer in scene
        # ==============================================================
        for obj_id in list(self.active_violations):
            if obj_id not in active_objects:
                self.active_violations.discard(obj_id)
                keys_to_del = [k for k in self.tracking_states if k[1] == obj_id]
                for k in keys_to_del:
                    del self.tracking_states[k]
                self.object_positions.pop(obj_id, None)
                self.object_metadata.pop(obj_id, None)

        for obj_id in list(self.object_positions.keys()):
            if obj_id not in active_objects:
                del self.object_positions[obj_id]
                self.object_metadata.pop(obj_id, None)

        for p_id in list(self.person_positions.keys()):
            if p_id not in active_people:
                del self.person_positions[p_id]

        return len(self.active_violations) > 0