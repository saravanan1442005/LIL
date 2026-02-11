# detector.py
from ultralytics import YOLO

class EcoDetector:
    def __init__(self, model_path="yolov8n.pt"):
        # Load the Medium model for better accuracy on small trash
        self.model = YOLO(model_path)
        # COCO classes: 0 is person, 39 is bottle, 41 is cup
        self.target_classes = [0, 39, 41] 

    def get_detections(self, frame):
        # Force the model to look at a smaller version of the image
        results = self.model(frame, imgsz=320, verbose=False)[0]
        detections = []
        
        for box in results.boxes:
            cls_id = int(box.cls[0])
            if cls_id in self.target_classes:
                conf = float(box.conf[0])
                if conf > 0.4:  # Confidence threshold
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    # Format for DeepSORT: [left, top, w, h]
                    w, h = x2 - x1, y2 - y1
                    label = self.model.names[cls_id]
                    detections.append(([x1, y1, w, h], conf, label))
        return detections