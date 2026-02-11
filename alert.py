import cv2
import os
import datetime

def save_violation(frame):
    """
    Saves the current frame as evidence when littering is detected.
    Organizes files into a /violations folder with precise timestamps.
    """
    # 1. Ensure the violations directory exists
    folder = "violations"
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"📁 Created directory: {folder}")

    # 2. Generate a unique filename using the current timestamp
    # Format: violation_YYYYMMDD_HHMMSS.jpg
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"violation_{timestamp}.jpg"
    filepath = os.path.join(folder, filename)

    # 3. Add a timestamp overlay directly on the saved image (Metadata for proof)
    annotated_frame = frame.copy()
    readable_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(annotated_frame, readable_time, (10, frame.shape[0] - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # 4. Save the file
    success = cv2.imwrite(filepath, annotated_frame)

    if success:
        print(f"🚨 ALERT: Evidence saved to {filepath}")
    else:
        print(f"❌ ERROR: Failed to save evidence at {filepath}")

    return filepath