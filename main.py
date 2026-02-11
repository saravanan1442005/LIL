import cv2
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
        # Fetch current states from engine to display them
        current_states = engine.tracking_states 
        
        for track in tracks:
            if not track.is_confirmed():
                continue
            
            track_id = track.track_id
            ltrb = track.to_ltrb()
            class_name = track.get_det_class()
            
            # --- Visual Feedback Logic ---
            # Default colors
            color = (0, 255, 0) if class_name == "person" else (200, 200, 200)
            status_label = "SCANNING"

            # Overlay State if this object is a bottle being tracked
            if class_name == "bottle":
                # Find if this bottle ID exists in any active tracking pair
                for (p_id, b_id), state in current_states.items():
                    if b_id == track_id:
                        status_label = f"STATE: {state}"
                        # Yellow for HELD, Orange for SEPARATION/TRACKING
                        color = (0, 255, 255) if state == "HELD" else (0, 165, 255)

            # Draw Bounding Box
            cv2.rectangle(frame, (int(ltrb[0]), int(ltrb[1])), 
                          (int(ltrb[2]), int(ltrb[3])), color, 2)
            
            # Draw Detailed Label
            cv2.putText(frame, f"{class_name} #{track_id} | {status_label}", 
                        (int(ltrb[0]), int(ltrb[1])-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # --- STEP 4: Violation Trigger ---
        if engine.is_littering(tracks):
            # Draw a prominent red banner at the top
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 65), (0, 0, 255), -1)
            cv2.putText(frame, "🚨 LITTERING DETECTED! 🚨", (frame.shape[1]//4, 45), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
            
            # Save the frame as evidence via your alert module
            save_violation(frame)

        # --- STEP 5: Display ---
        cv2.imshow("Eco Life Buddy - Behavior Analysis", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()