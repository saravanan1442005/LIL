import math

class EcoRuleEngine:
    def __init__(self):
        # This is the attribute main.py is looking for
        self.tracking_states = {} 
        self.active_violations = set()

        # Thresholds (Tweak these based on your room size)
        self.threshold_held = 150
        self.threshold_litter = 350
        self.min_stable_frames = 10
        self.stability_counters = {}

    def is_littering(self, tracks):
        # 1. Get current confirmed objects
        active_people = {t.track_id: t for t in tracks if t.get_det_class() == "person" and t.is_confirmed()}
        active_bottles = {t.track_id: t for t in tracks if t.get_det_class() == "bottle" and t.is_confirmed()}

        for b_id, b in active_bottles.items():
            b_ltrb = b.to_ltrb()
            b_center = ((b_ltrb[0] + b_ltrb[2]) / 2, (b_ltrb[1] + b_ltrb[3]) / 2)

            for p_id, p in active_people.items():
                p_ltrb = p.to_ltrb()
                p_center = ((p_ltrb[0] + p_ltrb[2]) / 2, (p_ltrb[1] + p_ltrb[3]) / 2)
                dist = math.dist(b_center, p_center)
                pair_key = (p_id, b_id)

                # --- RE-ARM LOGIC ---
                if dist < self.threshold_held:
                    self.tracking_states[pair_key] = "HELD"
                    if b_id in self.active_violations:
                        self.active_violations.remove(b_id)
                    self.stability_counters[b_id] = 0
                    continue

                # --- SEPARATION LOGIC ---
                if self.tracking_states.get(pair_key) == "HELD" and dist > self.threshold_litter:
                    # Change state to TRACKING while it moves away
                    self.tracking_states[pair_key] = "TRACKING"
                    
                if self.tracking_states.get(pair_key) == "TRACKING" and dist > self.threshold_litter:
                    self.stability_counters[b_id] = self.stability_counters.get(b_id, 0) + 1
                    
                    if self.stability_counters[b_id] > self.min_stable_frames:
                        self.active_violations.add(b_id)

        # Cleanup: Remove objects that left the frame
        for b_id in list(self.active_violations):
            if b_id not in active_bottles:
                self.active_violations.remove(b_id)
                # Clear tracking states for that bottle
                keys_to_del = [k for k in self.tracking_states if k[1] == b_id]
                for k in keys_to_del: del self.tracking_states[k]

        return len(self.active_violations) > 0