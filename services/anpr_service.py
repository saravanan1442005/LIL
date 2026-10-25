"""Adaptive license-plate detection, OCR normalization, and frame consensus.

The detector and OCR engines are optional so the application can start without
ANPR model weights. An unavailable engine is reported explicitly, never treated
as an unknown or successful read.
"""

from __future__ import annotations

import re
import logging
import os
from collections import Counter
from dataclasses import dataclass
from typing import Any, Optional

import cv2
import numpy as np

logger = logging.getLogger("ecolifybuddy.anpr")


@dataclass
class PlateRead:
    raw_text: str
    normalized_text: str
    detector_confidence: float
    ocr_confidence: float
    bbox: list[int]
    quality: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "detector_confidence": round(self.detector_confidence, 4),
            "ocr_confidence": round(self.ocr_confidence, 4),
            "bbox": self.bbox,
            "quality": round(self.quality, 4),
        }


def normalize_plate(text: str) -> str:
    """Normalize OCR output without blindly replacing ambiguous characters."""
    return re.sub(r"[^A-Z0-9]", "", str(text).upper())


def plate_format_score(text: str) -> float:
    """Return a conservative score for common Indian private vehicle plates."""
    value = normalize_plate(text)
    if not 8 <= len(value) <= 12:
        return 0.0
    if not re.match(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{1,4}$", value):
        return 0.0
    return 1.0


def _quality(crop: np.ndarray) -> float:
    if crop is None or crop.size == 0:
        return 0.0
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    sharpness = min(float(cv2.Laplacian(gray, cv2.CV_64F).var()) / 500.0, 1.0)
    brightness = 1.0 - min(abs(float(gray.mean()) - 128.0) / 128.0, 1.0)
    return max(0.0, min(1.0, sharpness * 0.7 + brightness * 0.3))


def preprocess_plate(crop: np.ndarray) -> list[np.ndarray]:
    """Generate restrained variants for different lighting and plate finishes."""
    if crop is None or crop.size == 0:
        return []
    enlarged = cv2.resize(crop, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(enlarged, cv2.COLOR_BGR2GRAY)
    denoised = cv2.bilateralFilter(gray, 7, 50, 50)
    equalized = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(denoised)
    thresholded = cv2.adaptiveThreshold(
        equalized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 7
    )
    return [enlarged, equalized, thresholded]


class ANPRService:
    """Camera-agnostic ANPR service with optional detector and OCR adapters."""

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.detector = None
        self.ocr = None
        self._load_optional_engines()

    def _load_optional_engines(self) -> None:
        if self.model_path:
            try:
                from ultralytics import YOLO
                self.detector = YOLO(self.model_path)
            except (ImportError, OSError, RuntimeError) as error:
                logger.warning("ANPR detector unavailable: %s", error)
        try:
            import pytesseract
            tesseract_cmd = os.getenv("TESSERACT_CMD")
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            pytesseract.get_tesseract_version()
            self.ocr = pytesseract
        except (ImportError, OSError, RuntimeError):
            logger.warning("ANPR OCR unavailable: install pytesseract and the Tesseract OCR binary.")

    def _detect_plates(self, frame: np.ndarray, profile: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
        if self.detector is None:
            return []
        region = frame
        offset_x, offset_y = 0, 0
        roi = (profile or {}).get("roi")
        if roi and len(roi) == 4:
            x1, y1, x2, y2 = [max(0, int(value)) for value in roi]
            region = frame[y1:y2, x1:x2]
            offset_x, offset_y = x1, y1
        results = self.detector.predict(region, conf=float((profile or {}).get("detector_threshold", 0.35)), verbose=False)
        detections = []
        if not results:
            return detections
        for box in results[0].boxes:
            x1, y1, x2, y2 = [int(value) for value in box.xyxy[0].cpu().numpy()]
            detections.append({
                "bbox": [x1 + offset_x, y1 + offset_y, x2 + offset_x, y2 + offset_y],
                "confidence": float(box.conf[0].item()),
            })
        return detections

    def _read_crop(self, crop: np.ndarray, detector_confidence: float, bbox: list[int]) -> Optional[PlateRead]:
        if self.ocr is None:
            return None
        candidates = []
        for variant in preprocess_plate(crop):
            try:
                result = self.ocr.image_to_data(
                    variant,
                    config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                    output_type=self.ocr.Output.DICT,
                )
                for index, raw in enumerate(result.get("text", [])):
                    text = normalize_plate(raw)
                    confidence = float(result.get("conf", ["-1"])[index]) / 100.0
                    if text and confidence > 0:
                        candidates.append((text, max(0.0, confidence)))
            except (RuntimeError, ValueError) as error:
                logger.warning("ANPR OCR failed for plate crop: %s", error)
        if not candidates:
            return None
        text, ocr_confidence = max(candidates, key=lambda item: (plate_format_score(item[0]), item[1]))
        if plate_format_score(text) == 0:
            return None
        return PlateRead(
            raw_text=text,
            normalized_text=text,
            detector_confidence=detector_confidence,
            ocr_confidence=ocr_confidence,
            bbox=bbox,
            quality=_quality(crop),
        )

    def read_frame(self, frame: np.ndarray, profile: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        if frame is None or frame.size == 0:
            return {"status": "INVALID_FRAME", "reads": []}
        detections = self._detect_plates(frame, profile)
        reads = []
        height, width = frame.shape[:2]
        for detection in detections:
            x1, y1, x2, y2 = detection["bbox"]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(width, x2), min(height, y2)
            if x2 - x1 < 40 or y2 - y1 < 12:
                continue
            read = self._read_crop(frame[y1:y2, x1:x2], detection["confidence"], [x1, y1, x2, y2])
            if read:
                reads.append(read)
        if not self.detector:
            return {"status": "DETECTOR_UNAVAILABLE", "reads": []}
        if not self.ocr:
            return {"status": "OCR_UNAVAILABLE", "reads": []}
        return {"status": "OK", "reads": [read.to_dict() for read in reads]}

    def readiness(self) -> dict[str, Any]:
        return {
            "detector_ready": self.detector is not None,
            "ocr_ready": self.ocr is not None,
            "ready": self.detector is not None and self.ocr is not None,
            "model_path": self.model_path,
        }


def aggregate_plate_reads(reads: list[dict[str, Any]], minimum_frames: int = 2) -> Optional[dict[str, Any]]:
    """Select a stable plate across frames; one noisy read is never enough."""
    valid = [
        read for read in reads
        if read.get("normalized_text") and float(read.get("ocr_confidence", 0)) >= 0.55
    ]
    if not valid:
        return None
    counts = Counter(read["normalized_text"] for read in valid)
    text, count = counts.most_common(1)[0]
    matching = [read for read in valid if read["normalized_text"] == text]
    if count < minimum_frames and max(float(read.get("ocr_confidence", 0)) for read in matching) < 0.9:
        return None
    return {
        "normalized_text": text,
        "confidence": round(sum(float(read.get("ocr_confidence", 0)) for read in matching) / len(matching), 4),
        "frame_count": count,
        "status": "CANDIDATE",
    }
