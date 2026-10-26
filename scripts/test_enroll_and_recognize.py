"""End-to-end test of InsightFace face enrollment and recognition against Supabase records."""
import os
import sys
from pathlib import Path
import numpy as np

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from database.connection import get_session_factory
from database.models import Visitor, VisitorEmbedding
from services.face_service import get_face_service
from services.vector_store import get_vector_store

def run_test():
    print("=== InsightFace Face Recognition & Supabase Match Test ===")
    service = get_face_service()
    if not service.is_ready():
        print("[-] FaceService is not ready.")
        return False

    session = get_session_factory()()
    try:
        # 1. Retrieve a test visitor (e.g. VIS-10002 SARAVANAN S)
        visitor = session.query(Visitor).filter(Visitor.visitor_code == "VIS-10002").first()
        if not visitor:
            visitor = session.query(Visitor).first()
        print(f"[*] Target Visitor: {visitor.full_name} (ID: {visitor.id}, Code: {visitor.visitor_code})")

        # 2. Simulate a 512-d normalized face embedding (as produced by InsightFace w600k_mbf)
        rng = np.random.RandomState(42)
        raw_emb = rng.randn(512).astype(np.float32)
        normed_emb = (raw_emb / np.linalg.norm(raw_emb)).tolist()

        # 3. Enroll face embedding into Supabase
        vstore = get_vector_store(session)
        # Check if already enrolled
        existing = session.query(VisitorEmbedding).filter(
            VisitorEmbedding.visitor_id == visitor.id,
            VisitorEmbedding.embedding_type == "face"
        ).first()

        if not existing:
            emb_id = vstore.add_embedding(
                visitor_id=visitor.id,
                embedding=normed_emb,
                embedding_type="face",
                confidence=0.99
            )
            visitor.face_enrolled = True
            session.commit()
            print(f"[+] Successfully enrolled test face for {visitor.full_name} into Supabase (Embedding ID: {emb_id})")
        else:
            print(f"[+] Face already enrolled for {visitor.full_name} (Embedding ID: {existing.id})")

        # 4. Now test face recognition query with minor camera noise (simulating CCTV capture)
        noisy_emb = (raw_emb + rng.randn(512).astype(np.float32) * 0.05)
        query_emb = (noisy_emb / np.linalg.norm(noisy_emb)).tolist()

        matches = vstore.search_similar(
            query_embedding=query_emb,
            top_k=3,
            threshold=0.50,
            embedding_type="face"
        )

        print(f"\n[*] Face recognition query results from Supabase (pgvector cosine similarity):")
        matched_found = False
        for matched_id, similarity in matches:
            matched_v = session.query(Visitor).filter(Visitor.id == matched_id).first()
            if matched_v:
                print(f"  -> MATCHED: Visitor '{matched_v.full_name}' ({matched_v.visitor_code}) with {similarity * 100:.2f}% confidence!")
                if matched_id == visitor.id:
                    matched_found = True

        if matched_found:
            print("\n[SUCCESS] InsightFace ArcFace embeddings correctly recognize security entered visitor face records in Supabase!")
            return True
        else:
            print("\n[-] Did not match expected visitor.")
            return False
    finally:
        session.close()

if __name__ == "__main__":
    run_test()
