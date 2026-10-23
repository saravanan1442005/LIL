"""Unit tests for Vector Store interface and NumPy cosine similarity search fallback."""
import numpy as np
from database import init_db
from database.connection import get_session_factory
from database.models import Visitor, VisitorEmbedding
from services.vector_store import NumPyVectorStore, get_vector_store


def test_vector_store_cosine_similarity():
    init_db()
    session = get_session_factory()()
    try:
        # Create a test visitor
        test_vis = Visitor(
            visitor_code="TEST-VIS-001",
            category="Delivery",
            label="Test Delivery Courier"
        )
        session.add(test_vis)
        session.commit()

        vstore = NumPyVectorStore(session)

        # 512-d base vector
        vec_base = [0.0] * 512
        vec_base[0] = 1.0
        vec_base[1] = 0.5

        # 512-d similar vector
        vec_similar = [0.0] * 512
        vec_similar[0] = 0.95
        vec_similar[1] = 0.48

        # 512-d orthogonal / dissimilar vector
        vec_dissimilar = [0.0] * 512
        vec_dissimilar[100] = 1.0

        rec_id = vstore.add_embedding(
            visitor_id=test_vis.id,
            embedding=vec_base,
            embedding_type="reid",
            confidence=0.98
        )
        assert rec_id is not None

        # Search with similar vector -> should match with high similarity (>0.90)
        matches = vstore.search_similar(query_embedding=vec_similar, top_k=5, threshold=0.70)
        assert len(matches) >= 1
        matched_id, similarity = matches[0]
        assert matched_id == test_vis.id
        assert similarity >= 0.90

        # Search with dissimilar vector -> should not match threshold
        no_matches = vstore.search_similar(query_embedding=vec_dissimilar, top_k=5, threshold=0.70)
        assert len(no_matches) == 0

        # Clean up test visitor
        session.delete(test_vis)
        session.commit()
    finally:
        session.close()
