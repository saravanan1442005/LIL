import cv2
import time
from detector import EcoDetector
from tracker import EcoTracker
from rule_engine import EcoRuleEngine
from alert import save_violation

def main():
    # 1. Initialize our modules
    detector = EcoDetector(model_path="yolov8m.pt")
    tracker = EcoTracker()
    engine = EcoRuleEngine()

    # 2. Setup Webcam (0 is default laptop cam)
    cap = cv2.VideoCapture(0)
    
    # Standard resolution for balanced performance
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # Violation save cooldown (avoid saving hundreds of duplicate screenshots)
    last_violation_save = 0
    violation_cooldown = 3  # seconds between saves

    print("🔥 Eco Life Buddy System Active. Press 'q' to quit.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # --- STEP 1: Detection ---
        detections = detector.get_detections(frame)

        # --- STEP 2: Tracking ---
        tracks = tracker.update(detections, frame)

        # --- STEP 3: State & Visual Logic ---
        current_states = engine.tracking_states
        
        for track in tracks:
            if not track.is_confirmed():
                continue
            
            track_id = track.track_id
            ltrb = track.to_ltrb()
            class_name = track.get_det_class()
            
            # --- Visual Feedback Logic ---
            if class_name == "person":
                color = (0, 255, 0)  # Green for person
                status_label = "SCANNING"
            else:
                # This is a litter-type object
                color = (200, 200, 200)  # Default gray
                status_label = "DETECTED"

                # Check if this object is being tracked by the rule engine
                for (p_id, obj_id), state in current_states.items():
                    if obj_id == track_id:
                        status_label = f"STATE: {state}"
                        if state == "HELD":
                            color = (0, 255, 255)  # Yellow
                        elif state == "SEPARATING":
                            color = (0, 165, 255)  # Orange
                        elif state == "TRACKING":
                            color = (0, 100, 255)  # Deep orange
                        break

                # If this object is an active violation, override to RED
                if track_id in engine.active_violations:
                    color = (0, 0, 255)  # Red
                    status_label = "⚠ VIOLATION"

            # Draw Bounding Box
            cv2.rectangle(frame, (int(ltrb[0]), int(ltrb[1])), 
                          (int(ltrb[2]), int(ltrb[3])), color, 2)
            
            # Draw Label
            label_text = f"{class_name} #{track_id} | {status_label}"
            cv2.putText(frame, label_text, 
                        (int(ltrb[0]), int(ltrb[1])-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # --- STEP 4: Violation Trigger ---
        if engine.is_littering(tracks):
            # Draw a prominent red banner at the top
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 65), (0, 0, 255), -1)
            cv2.putText(frame, "LITTERING DETECTED!", (frame.shape[1]//4, 45), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
            
            # Save evidence with cooldown to avoid spam
            current_time = time.time()
            if current_time - last_violation_save > violation_cooldown:
                save_violation(frame)
                last_violation_save = current_time

        # --- STEP 5: Display ---
        # Show detection count info at bottom
        num_people = sum(1 for t in tracks if t.is_confirmed() and t.get_det_class() == "person")
        num_objects = sum(1 for t in tracks if t.is_confirmed() and t.get_det_class() != "person")
        info_text = f"People: {num_people} | Objects: {num_objects} | Violations: {len(engine.active_violations)}"
        cv2.putText(frame, info_text, (10, frame.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow("Eco Life Buddy - Behavior Analysis", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()