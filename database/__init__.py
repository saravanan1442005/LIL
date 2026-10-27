"""Database package initialization for EcoLifyBuddy.
Exposes models, sessions, and database lifecycle initializers.
"""
import os
import json
import logging
from sqlalchemy import text
from database.connection import Base, get_db, get_engine, get_session_factory, is_postgres
from database.models import (
    User, AuditLog, Camera, Zone, Visitor, VisitorEmbedding,
    Consent, FaceEnrollment, OTPChallenge, VisitorEntry, PlateRead, Track, Event, Alert, SensorEvent
)
from services.auth_service import hash_password

logger = logging.getLogger("ecolifybuddy.db")


def init_db(seed_admin: bool = True, seed_default_cameras: bool = True):
    """Initialize database tables, extensions, and default records."""
    engine = get_engine()
    session_factory = get_session_factory()

    with engine.connect() as conn:
        # Enable pgvector extension on Postgres
        if engine.dialect.name == "postgresql":
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
                logger.info("pgvector extension verified.")
            except Exception as e:
                logger.warning("Could not execute CREATE EXTENSION vector: %s", e)

        # Create all tables
        Base.metadata.create_all(bind=conn)
        conn.commit()
        _ensure_visitor_columns(conn)
        _ensure_camera_columns(conn)

        # Create HNSW vector index on Postgres
        if engine.dialect.name == "postgresql":
            try:
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_visitor_embeddings_hnsw "
                    "ON visitor_embeddings USING hnsw (embedding vector_cosine_ops);"
                ))
                conn.commit()
                logger.info("HNSW index created on visitor_embeddings.")
            except Exception as e:
                logger.warning("HNSW index creation note: %s", e)

    # Seed Admin User & Default Cameras
    with session_factory() as session:
        if seed_admin:
            admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com").strip()
            admin_pass = os.getenv("ADMIN_PASSWORD", "Admin@12345").strip()

            existing_admin = session.query(User).filter(User.email == admin_email).first()
            if not existing_admin:
                admin_user = User(
                    email=admin_email,
                    password_hash=hash_password(admin_pass),
                    full_name="System Administrator",
                    role="Admin",
                    is_active=True
                )
                session.add(admin_user)
                session.commit()
                logger.info("Seeded initial Admin user: %s", admin_email)

        if seed_default_cameras:
            camera_count = session.query(Camera).count()
            if camera_count == 0:
                # Seed default cameras
                c1 = Camera(
                    name="Main Entrance Gate",
                    location="Gate 1 (Visitor Access)",
                    stream_source="https://www.youtube.com/watch?v=QMN4_62A3As",
                    stream_type="YOUTUBE",
                    purpose="VISITOR",
                    enabled=True,
                    fps=15,
                    resolution="1280x720"
                )
                c2 = Camera(
                    name="Public Promenade & Crosswalk",
                    location="Perimeter Boulevard",
                    stream_source="https://www.youtube.com/watch?v=zMCea32gpmg",
                    stream_type="YOUTUBE",
                    purpose="LITTER",
                    enabled=True,
                    fps=15,
                    resolution="1280x720"
                )
                c3 = Camera(
                    name="Workstation Webcam",
                    location="Local Station",
                    stream_source="0",
                    stream_type="WEBCAM",
                    purpose="LITTER",
                    enabled=True,
                    fps=30,
                    resolution="640x480"
                )
                session.add_all([c1, c2, c3])
                session.commit()

                # Seed initial zones for Camera 1
                z1 = Zone(
                    camera_id=c1.id,
                    name="Entry Tripwire Line",
                    zone_type="ENTRY_EXIT",
                    polygon_coords=[[100, 300], [540, 300], [540, 360], [100, 360]],
                    entry_line_coords=[[100, 330], [540, 330]],
                    dwell_threshold_seconds=45,
                    is_active=True
                )
                z2 = Zone(
                    camera_id=c1.id,
                    name="Delivery Drop Zone",
                    zone_type="GENERAL",
                    polygon_coords=[[350, 200], [600, 200], [600, 450], [350, 450]],
                    dwell_threshold_seconds=120,
                    is_active=True
                )
                session.add_all([z1, z2])
                session.commit()
                logger.info("Seeded default cameras and zones.")


def _ensure_visitor_columns(conn):
    """Add enrollment fields to databases created before the registration module."""
    from sqlalchemy import inspect

    inspector = inspect(conn)
    existing = {column["name"] for column in inspector.get_columns("visitors")}
    columns = {
        "full_name": "VARCHAR(150)",
        "phone_number": "VARCHAR(20)",
        "phone_hash": "VARCHAR(128)",
        "phone_last4": "VARCHAR(4)",
        "phone_verified": "BOOLEAN NOT NULL DEFAULT 0",
        "company": "VARCHAR(150)",
        "vehicle_number": "VARCHAR(32)",
        "profile_photo_path": "VARCHAR(500)",
        "face_enrolled": "BOOLEAN NOT NULL DEFAULT 0",
        "plate_enrolled": "BOOLEAN NOT NULL DEFAULT 0",
        "consent_status": "VARCHAR(30) NOT NULL DEFAULT 'NOT_REQUIRED'",
    }
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(text(f"ALTER TABLE visitors ADD COLUMN {name} {definition}"))
    conn.commit()


def _ensure_camera_columns(conn):
    """Add purpose metadata for separation of litter vs visitor workflows."""
    from sqlalchemy import inspect

    inspector = inspect(conn)
    existing = {column["name"] for column in inspector.get_columns("cameras")}
    if "purpose" not in existing:
        conn.execute(text("ALTER TABLE cameras ADD COLUMN purpose VARCHAR(20) NOT NULL DEFAULT 'LITTER'"))
    conn.commit()
