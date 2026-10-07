# detector.py
import os
from ultralytics import YOLO

class EcoDetector:
    def __init__(self, model_path="yolo26n.pt"):
        # Resolve relative model path against this file's folder if needed
        if not os.path.isabs(model_path) and not os.path.exists(model_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            candidate = os.path.join(base_dir, model_path)
            if os.path.exists(candidate):
                model_path = candidate

        # Load the model for detection
        self.model = YOLO(model_path)
        
        # COCO classes relevant to actual littering:
        # 0=person, 24=backpack, 25=umbrella, 26=handbag
        # 39=bottle, 40=wine glass, 41=cup, 43=fork, 44=knife, 46=banana, 47=apple
        # (Excluded phones, books, vases, scissors, suitcases to prevent false positives)
        self.person_class = [0]
        self.litter_classes = [24, 25, 26, 39, 40, 41, 43, 44, 46, 47]
        self.target_classes = self.person_class + self.litter_classes

    def get_detections(self, frame):
        if frame is None or getattr(frame, "size", 0) == 0:
            return []

        # Use 640 resolution for much better small-object detection
        results = self.model(frame, imgsz=640, verbose=False)[0]
        detections = []
        
        if results.boxes is None or len(results.boxes) == 0:
            return detections

        for box in results.boxes:
            cls_id = int(box.cls[0].item() if hasattr(box.cls[0], "item") else box.cls[0])
            if cls_id in self.target_classes:
                conf = float(box.conf[0].item() if hasattr(box.conf[0], "item") else box.conf[0])
                # Lower threshold for litter objects (they're small)
                min_conf = 0.25 if cls_id in self.litter_classes else 0.4
                if conf > min_conf:
                    coords = box.xyxy[0].tolist() if hasattr(box.xyxy[0], "tolist") else list(box.xyxy[0])
                    x1, y1, x2, y2 = [int(v) for v in coords]
                    # Format for DeepSORT: [left, top, w, h]
                    w, h = x2 - x1, y2 - y1
                    label = self.model.names[cls_id]
                    detections.append(([x1, y1, w, h], conf, label))
        return detections
    
    def is_litter_class(self, class_name):
        """Check if a class name is a litter-type object (not a person)."""
        return class_name != "person"

if __name__ == "__main__":
    import cv2
    print("Testing EcoDetector initialization...")
    detector = EcoDetector()
    print("EcoDetector loaded successfully with model:", detector.model)
    test_img = os.path.join(os.path.dirname(os.path.abspath(__file__)), "violations", "violation_20260517_232905.jpg")
    if os.path.exists(test_img):
        sample_frame = cv2.imread(test_img)
        res = detector.get_detections(sample_frame)
        print(f"Test detection succeeded! Found {len(res)} object(s): {res}")
    else:
        print("EcoDetector ready for real-time inference.")