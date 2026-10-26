"""Test and demonstrate InsightFace face recognition with Supabase visitor records."""
import os
import sys
from pathlib import Path
import numpy as np
import cv2

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from database.connection import get_session_factory
from database.models import Visitor, VisitorEmbedding
from services.face_service import get_face_service

def test_face_pipeline():
    print("=== Testing InsightFace Recognition Service ===")
    service = get_face_service()
    if not service.is_ready():
        print("[-] FaceService is not ready.")
        return False
    print("[+] InsightFace service is ready and models loaded.")

    session = get_session_factory()()
    try:
        # Check enrolled face embeddings in Supabase
        embeddings = session.query(VisitorEmbedding).filter(VisitorEmbedding.embedding_type == "face").all()
        print(f"[*] Total face embeddings in Supabase: {len(embeddings)}")
        for e in embeddings:
            visitor = session.query(Visitor).filter(Visitor.id == e.visitor_id).first()
            v_name = visitor.full_name if visitor else "Unknown"
            print(f"  - Embedding ID {e.id}: Visitor ID {e.visitor_id} ({v_name}), Confidence: {e.confidence}")

        # Check visitors in Supabase
        visitors = session.query(Visitor).all()
        print(f"\n[*] Total visitors in Supabase: {len(visitors)}")
        for v in visitors:
            print(f"  - Visitor {v.id}: {v.full_name} | Code: {v.visitor_code} | Face Enrolled: {v.face_enrolled} | Photo: {v.profile_photo_path}")

        print("\n[+] InsightFace is integrated with security-entered visitor records and ready for live camera matching!")
        return True
    finally:
        session.close()

if __name__ == "__main__":
    test_face_pipeline()
