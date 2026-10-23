"""Person Re-Identification (Re-ID) feature extractor for EcoLifyBuddy.
Produces 512-dimensional L2-normalized feature vectors for cross-camera & cross-day matching.
Uses OSNet (via ONNX / PyTorch) with an automatic spatial-pyramid colour-histogram fallback.
"""
import os
import cv2
import numpy as np
import logging

logger = logging.getLogger("ecolifybuddy.reid")


class ReIDExtractor:
    """Extracts 512-d appearance embeddings from person image crops."""

    def __init__(self, model_path: str = "models/osnet_x0_25.onnx"):
        self.model_path = model_path
        self.onnx_session = None
        self.model_loaded = False
        self._init_model()

    def _init_model(self):
        """Attempt to load ONNX OSNet model if present."""
        if os.path.exists(self.model_path):
            try:
                import onnxruntime as ort
                self.onnx_session = ort.InferenceSession(
                    self.model_path,
                    providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
                )
                self.model_loaded = True
                logger.info("Loaded OSNet Re-ID ONNX model from %s", self.model_path)
                return
            except Exception as e:
                logger.warning("Could not initialize ONNX runtime for OSNet: %s", e)

        logger.info("Using resilient spatial-pyramid colour-histogram fallback for Re-ID.")

    def extract_embedding(self, crop_bgr: np.ndarray) -> list[float]:
        """Extract a 512-dimensional L2-normalized feature vector from a person crop."""
        if crop_bgr is None or crop_bgr.size == 0 or crop_bgr.shape[0] < 10 or crop_bgr.shape[1] < 10:
            return [0.0] * 512

        # 1. Try OSNet model if available
        if self.model_loaded and self.onnx_session:
            try:
                resized = cv2.resize(crop_bgr, (128, 256))
                # Normalize (ImageNet mean & std)
                rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
                mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
                std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
                normed = (rgb - mean) / std
                # CHW -> NCHW
                tensor = np.transpose(normed, (2, 0, 1))[np.newaxis, ...]

                input_name = self.onnx_session.get_inputs()[0].name
                feats = self.onnx_session.run(None, {input_name: tensor})[0].flatten()

                # Ensure 512 dimensions and L2-normalize
                if len(feats) > 512:
                    feats = feats[:512]
                elif len(feats) < 512:
                    feats = np.pad(feats, (0, 512 - len(feats)))

                norm = np.linalg.norm(feats)
                if norm > 1e-6:
                    feats = feats / norm
                return [round(float(x), 6) for x in feats]
            except Exception as err:
                logger.warning("OSNet forward pass failed, falling back to colour histogram: %s", err)

        # 2. Resilient Spatial-Pyramid Colour-Histogram Fallback
        return self._extract_spatial_histogram(crop_bgr)

    def _extract_spatial_histogram(self, crop_bgr: np.ndarray) -> list[float]:
        """Extract multi-part spatial HSV + Lab colour-texture histogram (512-d, normalized).
        Partitions the person into Head (15%), Torso (45%), and Legs (40%).
        """
        h, w = crop_bgr.shape[:2]
        hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2LAB)

        # Vertical slices
        slices = [
            (0, int(h * 0.20)),          # Head / upper shoulders
            (int(h * 0.20), int(h * 0.65)), # Torso / jacket / shirt
            (int(h * 0.65), h),          # Legs / trousers / skirt
        ]

        features = []

        for y1, y2 in slices:
            if y2 <= y1:
                features.extend([0.0] * 128)
                continue
            hsv_slice = hsv[y1:y2, :]
            lab_slice = lab[y1:y2, :]

            # HSV: 16 Hue bins, 8 Sat bins, 8 Val bins = 32 bins
            h_hist = cv2.calcHist([hsv_slice], [0], None, [16], [0, 180]).flatten()
            s_hist = cv2.calcHist([hsv_slice], [1], None, [12], [0, 256]).flatten()
            v_hist = cv2.calcHist([hsv_slice], [2], None, [12], [0, 256]).flatten()

            # LAB: L: 8 bins, A: 12 bins, B: 12 bins = 32 bins
            l_hist = cv2.calcHist([lab_slice], [0], None, [12], [0, 256]).flatten()
            a_hist = cv2.calcHist([lab_slice], [1], None, [16], [0, 256]).flatten()
            b_hist = cv2.calcHist([lab_slice], [2], None, [16], [0, 256]).flatten()

            slice_hist = np.concatenate([h_hist, s_hist, v_hist, l_hist, a_hist, b_hist])
            norm = np.linalg.norm(slice_hist)
            if norm > 0:
                slice_hist = slice_hist / norm
            features.extend(slice_hist.tolist())

        # Global full-body histogram
        g_hsv = cv2.calcHist([hsv], [0, 1], None, [12, 8], [0, 180, 0, 256]).flatten()
        g_norm = np.linalg.norm(g_hsv)
        if g_norm > 0:
            g_hsv = g_hsv / g_norm
        features.extend(g_hsv.tolist())

        # Pad or truncate to exactly 512 dimensions
        vec = np.array(features, dtype=np.float32)
        if len(vec) < 512:
            vec = np.pad(vec, (0, 512 - len(vec)))
        else:
            vec = vec[:512]

        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec = vec / norm

        return [round(float(x), 6) for x in vec]


# Global singleton instance
_extractor = None


def get_reid_extractor() -> ReIDExtractor:
    global _extractor
    if _extractor is None:
        _extractor = ReIDExtractor()
    return _extractor
