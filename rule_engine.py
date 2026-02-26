import math

class EcoRuleEngine:
    def __init__(self):
        # This is the attribute main.py uses for visual feedback
        self.tracking_states = {}
        self.active_violations = set()

        # Stability tracking
        self.min_stable_frames = 5  # Reduced from 10 for quicker detection
        self.stability_counters = {}

        # Object position history for stationary detection
        self.object_positions = {}  # {obj_id: [(cx, cy), ...]}
        self.position_history_len = 15

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
        
        # Intersection
        x1 = max(a[0], b[0])
        y1 = max(a[1], b[1])
        x2 = min(a[2], b[2])
        y2 = min(a[3], b[3])
        
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        if intersection == 0:
            return 0.0
        
        # Union
        area_a = (a[2] - a[0]) * (a[3] - a[1])
        area_b = (b[2] - b[0]) * (b[3] - b[1])
        union = area_a + area_b - intersection
        
        return intersection / union if union > 0 else 0.0

    def _is_inside_person(self, obj_track, person_track):
        """Check if the litter object is mostly inside the person's bounding box."""
        p = person_track.to_ltrb()
        o = obj_track.to_ltrb()
        
        # Check if object center is inside person box (expanded by 20%)
        o_cx, o_cy = self._get_center(obj_track)
        p_w, p_h = p[2] - p[0], p[3] - p[1]
        margin_x, margin_y = p_w * 0.2, p_h * 0.2
        
        return (p[0] - margin_x <= o_cx <= p[2] + margin_x and 
                p[1] - margin_y <= o_cy <= p[3] + margin_y)

    def _adaptive_threshold(self, person_track):
        """Calculate distance thresholds based on person bounding box size.
        Larger person = closer to camera = larger thresholds needed."""
        p_w, p_h = self._get_bbox_size(person_track)
        person_size = max(p_w, p_h)
        
        # Held threshold: ~40% of person size (object near person)
        held_threshold = person_size * 0.5
        # Litter threshold: ~100% of person size (object far from person)
        litter_threshold = person_size * 1.2
        
        return max(held_threshold, 60), max(litter_threshold, 120)

    def _is_object_stationary(self, obj_id, current_center):
        """Track if an object has become stationary (placed down)."""
        if obj_id not in self.object_positions:
            self.object_positions[obj_id] = []
        
        history = self.object_positions[obj_id]
        history.append(current_center)
        
        # Keep only recent history
        if len(history) > self.position_history_len:
            history.pop(0)
        
        # Need enough history to judge
        if len(history) < 5:
            return False
        
        # Check if object has barely moved in recent frames
        recent = history[-5:]
        max_movement = 0
        for i in range(1, len(recent)):
            movement = math.dist(recent[i], recent[i-1])
            max_movement = max(max_movement, movement)
        
        # If max frame-to-frame movement is < 8 pixels, it's stationary
        return max_movement < 8

    def is_littering(self, tracks):
        # 1. Separate people from litter objects
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

        # 2. Process each litter object against each person
        for obj_id, obj in active_objects.items():
            obj_center = self._get_center(obj)
            
            # Track object position for stationary detection
            is_stationary = self._is_object_stationary(obj_id, obj_center)

            for p_id, person in active_people.items():
                p_center = self._get_center(person)
                dist = math.dist(obj_center, p_center)
                pair_key = (p_id, obj_id)

                # Get adaptive thresholds based on person size
                held_thresh, litter_thresh = self._adaptive_threshold(person)

                # --- HELD DETECTION (IoU + Distance + Containment) ---
                iou = self._compute_iou(obj, person)
                is_inside = self._is_inside_person(obj, person)
                
                if iou > 0.05 or is_inside or dist < held_thresh:
                    self.tracking_states[pair_key] = "HELD"
                    if obj_id in self.active_violations:
                        self.active_violations.discard(obj_id)
                    self.stability_counters[obj_id] = 0
                    continue

                # --- SEPARATION DETECTION ---
                current_state = self.tracking_states.get(pair_key)
                
                if current_state == "HELD" and dist > held_thresh:
                    self.tracking_states[pair_key] = "SEPARATING"
                    self.stability_counters[obj_id] = 0

                if current_state in ("SEPARATING", "TRACKING"):
                    if dist > litter_thresh:
                        self.tracking_states[pair_key] = "TRACKING"
                        self.stability_counters[obj_id] = self.stability_counters.get(obj_id, 0) + 1
                        
                        # Trigger violation if object is far AND stationary for enough frames
                        if self.stability_counters[obj_id] > self.min_stable_frames:
                            self.active_violations.add(obj_id)
                    elif dist > held_thresh:
                        # In the gray zone between held and litter thresholds
                        self.tracking_states[pair_key] = "SEPARATING"
                        # Still count if object is stationary (dropped at person's feet)
                        if is_stationary:
                            self.stability_counters[obj_id] = self.stability_counters.get(obj_id, 0) + 1
                            if self.stability_counters[obj_id] > self.min_stable_frames:
                                self.active_violations.add(obj_id)

        # 3. Cleanup: Remove objects that left the frame
        for obj_id in list(self.active_violations):
            if obj_id not in active_objects:
                self.active_violations.discard(obj_id)
                keys_to_del = [k for k in self.tracking_states if k[1] == obj_id]
                for k in keys_to_del:
                    del self.tracking_states[k]
                self.object_positions.pop(obj_id, None)

        # Cleanup position history for objects no longer tracked
        for obj_id in list(self.object_positions.keys()):
            if obj_id not in active_objects:
                del self.object_positions[obj_id]

        return len(self.active_violations) > 0