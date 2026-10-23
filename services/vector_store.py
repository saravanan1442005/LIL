"""Vector store service for appearance Re-ID and face feature matching.
Implements pgvector on Neon Postgres (HNSW index) with a NumPy cosine fallback
behind a unified interface for unit tests and offline execution.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session
from database.models import VisitorEmbedding, Visitor


class VectorStoreInterface(ABC):
    """Abstract interface for vector similarity search."""

    @abstractmethod
    def add_embedding(
        self,
        visitor_id: int,
        embedding: List[float],
        embedding_type: str = "reid",
        camera_id: Optional[int] = None,
        confidence: float = 1.0,
    ) -> int:
        """Persist embedding vector. Returns the created record ID."""
        pass

    @abstractmethod
    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.65,
        embedding_type: str = "reid",
    ) -> List[Tuple[int, float]]:
        """Find most similar visitors. Returns list of (visitor_id, cosine_similarity_score)."""
        pass


class PgVectorStore(VectorStoreInterface):
    """Postgres vector store utilizing the pgvector extension and HNSW cosine index."""

    def __init__(self, session: Session):
        self.session = session

    def add_embedding(
        self,
        visitor_id: int,
        embedding: List[float],
        embedding_type: str = "reid",
        camera_id: Optional[int] = None,
        confidence: float = 1.0,
    ) -> int:
        record = VisitorEmbedding(
            visitor_id=visitor_id,
            embedding_type=embedding_type,
            embedding=embedding,
            camera_id=camera_id,
            confidence=confidence,
        )
        self.session.add(record)
        self.session.commit()
        return record.id

    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.65,
        embedding_type: str = "reid",
    ) -> List[Tuple[int, float]]:
        """Executes pgvector cosine similarity search (<=> operator).
        Cosine similarity = 1 - cosine_distance.
        """
        # Convert embedding list to string format for pgvector query
        vec_str = "[" + ",".join(str(float(x)) for x in query_embedding) + "]"
        query = text("""
            SELECT visitor_id, 1 - (embedding <=> :vec::vector) AS similarity
            FROM visitor_embeddings
            WHERE embedding_type = :etype
            ORDER BY embedding <=> :vec::vector ASC
            LIMIT :k
        """)
        results = self.session.execute(
            query,
            {"vec": vec_str, "etype": embedding_type, "k": top_k}
        ).fetchall()

        matched = []
        for row in results:
            sim = float(row.similarity)
            if sim >= threshold:
                matched.append((int(row.visitor_id), round(sim, 4)))
        return matched


class NumPyVectorStore(VectorStoreInterface):
    """Resilient in-memory/database NumPy cosine similarity search fallback.
    Used for unit testing, offline execution, and SQLite mode.
    """

    def __init__(self, session: Session):
        self.session = session

    def add_embedding(
        self,
        visitor_id: int,
        embedding: List[float],
        embedding_type: str = "reid",
        camera_id: Optional[int] = None,
        confidence: float = 1.0,
    ) -> int:
        record = VisitorEmbedding(
            visitor_id=visitor_id,
            embedding_type=embedding_type,
            embedding=embedding,
            camera_id=camera_id,
            confidence=confidence,
        )
        self.session.add(record)
        self.session.commit()
        return record.id

    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.65,
        embedding_type: str = "reid",
    ) -> List[Tuple[int, float]]:
        # Retrieve all candidate embeddings of the given type
        records = (
            self.session.query(VisitorEmbedding)
            .filter(VisitorEmbedding.embedding_type == embedding_type)
            .all()
        )
        if not records:
            return []

        q = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []

        scored = []
        for rec in records:
            if not rec.embedding:
                continue
            v = np.array(rec.embedding, dtype=np.float32)
            v_norm = np.linalg.norm(v)
            if v_norm == 0:
                continue
            cos_sim = float(np.dot(q, v) / (q_norm * v_norm))
            if cos_sim >= threshold:
                scored.append((rec.visitor_id, cos_sim))

        # Sort descending by similarity
        scored.sort(key=lambda x: x[1], reverse=True)
        return [(vid, round(sim, 4)) for vid, sim in scored[:top_k]]


def get_vector_store(session: Session) -> VectorStoreInterface:
    """Factory selecting PgVectorStore if on Postgres with pgvector, else NumPyVectorStore."""
    bind = session.get_bind()
    if bind and bind.dialect.name == "postgresql":
        try:
            return PgVectorStore(session)
        except Exception:
            pass
    return NumPyVectorStore(session)
