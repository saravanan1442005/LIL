"""InsightFace Recognition Service for Visitor Identification.
Uses InsightFace (det_500m + w600k_mbf ArcFace 512-d embeddings) to detect,
enroll, and recognize security-registered visitor faces.
Integrates with Supabase / PostgreSQL pgvector cosine similarity search.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
import cv2

logger = logging.getLogger("ecolifybuddy.face")

_face_app = None


def get_face_app():
    """Singleton initializer for InsightFace FaceAnalysis."""
    global _face_app
    if _face_app is None:
        try:
            from insightface.app import FaceAnalysis

            models_root = os.getenv("FACE_MODEL_PATH", "d:/LIL/face_recognition/models")
            _face_app = FaceAnalysis(
                name="buffalo_sc",
                root=models_root,
                providers=["CPUExecutionProvider"]
            )
            # Detection input size 320x320 for fast real-time CCTV inference
            _face_app.prepare(ctx_id=-1, det_size=(320, 320))
            logger.info("InsightFace FaceAnalysis (buffalo_sc) successfully initialized from %s", models_root)
        except Exception as e:
            logger.error("Failed to initialize InsightFace: %s", e)
            _face_app = None
    return _face_app


class FaceService:
    """Handles face detection, feature extraction, enrollment, and recognition."""

    def __init__(self):
        self.app = get_face_app()

    def is_ready(self) -> bool:
        return self.app is not None

    def detect_and_extract(self, image_bgr: np.ndarray) -> List[Dict[str, Any]]:
        """Detect all faces in an image and return their bounding boxes and 512-d embeddings."""
        if image_bgr is None or image_bgr.size == 0 or not self.is_ready():
            return []

        try:
            faces = self.app.get(image_bgr)
            results = []
            for face in faces:
                normed_emb = face.normed_embedding
                if normed_emb is None:
                    # Fallback to manual normalization
                    emb = face.embedding
                    norm = np.linalg.norm(emb)
                    normed_emb = (emb / norm) if norm > 1e-6 else emb

                # Convert to standard 512-element Python float list
                emb_list = [round(float(x), 6) for x in normed_emb[:512]]

                bbox = [int(x) for x in face.bbox] if face.bbox is not None else []
                results.append({
                    "embedding": emb_list,
                    "bbox": bbox,
                    "det_score": round(float(face.det_score), 4) if face.det_score is not None else 1.0,
                    "kps": face.kps.tolist() if face.kps is not None else []
                })
            return results
        except Exception as e:
            logger.error("Face detection and extraction error: %s", e)
            return []

    def get_primary_face_embedding(self, image_bgr: np.ndarray) -> Tuple[Optional[List[float]], Optional[Dict[str, Any]]]:
        """Extract the largest / highest confidence face in a visitor portrait."""
        faces = self.detect_and_extract(image_bgr)
        if not faces:
            return None, None
        # Sort by bounding box area (width * height) descending
        faces.sort(
            key=lambda f: (f["bbox"][2] - f["bbox"][0]) * (f["bbox"][3] - f["bbox"][1]) if len(f["bbox"]) == 4 else 0,
            reverse=True
        )
        primary = faces[0]
        return primary["embedding"], primary

    def enroll_visitor_face(self, session, visitor_id: int, image_bgr: np.ndarray) -> bool:
        """Enroll a visitor's face into the Supabase database.
        Saves 512-d embedding with embedding_type='face' and updates visitor.face_enrolled.
        """
        from database.models import Visitor, VisitorEmbedding
        from services.vector_store import get_vector_store

        embedding, face_info = self.get_primary_face_embedding(image_bgr)
        if not embedding:
            logger.warning("No face detected in photo for visitor_id=%s", visitor_id)
            return False

        # Persist embedding vector to Supabase
        vstore = get_vector_store(session)
        det_score = face_info["det_score"] if face_info else 1.0
        vstore.add_embedding(
            visitor_id=visitor_id,
            embedding=embedding,
            embedding_type="face",
            confidence=det_score
        )

        visitor = session.query(Visitor).filter(Visitor.id == visitor_id).first()
        if visitor:
            visitor.face_enrolled = True
            session.commit()
            logger.info("Successfully enrolled face for visitor %s (code=%s)", visitor.full_name, visitor.visitor_code)
            return True

        return False

    def recognize_face(
        self,
        session,
        image_bgr: np.ndarray,
        threshold: float = 0.50,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Recognize visitors appearing in an image using InsightFace + pgvector cosine similarity."""
        from database.models import Visitor
        from services.vector_store import get_vector_store

        detected_faces = self.detect_and_extract(image_bgr)
        if not detected_faces:
            return []

        vstore = get_vector_store(session)
        recognitions = []

        for face in detected_faces:
            matches = vstore.search_similar(
                query_embedding=face["embedding"],
                top_k=top_k,
                threshold=threshold,
                embedding_type="face"
            )

            for visitor_id, similarity in matches:
                visitor = session.query(Visitor).filter(
                    Visitor.id == visitor_id,
                    Visitor.status == "ACTIVE"
                ).first()
                if visitor:
                    recognitions.append({
                        "visitor_id": visitor.id,
                        "visitor": visitor.to_dict(),
                        "confidence": similarity,
                        "match_type": "FACE_INSIGHTFACE",
                        "bbox": face["bbox"],
                        "det_score": face["det_score"],
                        "is_frequent": (visitor.total_visits or 0) >= 2,
                    })

        # Sort by confidence descending
        recognitions.sort(key=lambda r: r["confidence"], reverse=True)
        return recognitions


_service_instance = None

def get_face_service() -> FaceService:
    global _service_instance
    if _service_instance is None:
        _service_instance = FaceService()
    return _service_instance
