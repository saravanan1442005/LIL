# detector.py
from ultralytics import YOLO

class EcoDetector:
    def __init__(self, model_path="yolo26n.pt"):
        # Load the model for detection
        self.model = YOLO(model_path)
        
        # COCO classes relevant to littering
        # 0=person, 24=backpack, 25=umbrella, 26=handbag, 28=suitcase
        # 39=bottle, 40=wine glass, 41=cup, 43=fork, 44=knife, 46=banana
        # 47=apple, 67=cell phone, 73=book, 75=vase, 76=scissors
        self.person_class = [0]
        self.litter_classes = [24, 25, 26, 28, 39, 40, 41, 43, 44, 46, 47, 67, 73, 75, 76]
        self.target_classes = self.person_class + self.litter_classes

    def get_detections(self, frame):
        # Use 640 resolution for much better small-object detection
        results = self.model(frame, imgsz=640, verbose=False)[0]
        detections = []
        
        for box in results.boxes:
            cls_id = int(box.cls[0])
            if cls_id in self.target_classes:
                conf = float(box.conf[0])
                # Lower threshold for litter objects (they're small)
                min_conf = 0.25 if cls_id in self.litter_classes else 0.4
                if conf > min_conf:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    # Format for DeepSORT: [left, top, w, h]
                    w, h = x2 - x1, y2 - y1
                    label = self.model.names[cls_id]
                    detections.append(([x1, y1, w, h], conf, label))
        return detections
    
    def is_litter_class(self, class_name):
        """Check if a class name is a litter-type object (not a person)."""
        return class_name != "person"