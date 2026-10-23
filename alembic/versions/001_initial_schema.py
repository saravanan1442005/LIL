"""Initial schema with pgvector extension and core tables.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-21 20:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # 1. Enable pgvector on Postgres
    if is_pg:
        op.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

    # 2. Users Table (RBAC)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="Viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1" if not is_pg else "true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # 3. Immutable Audit Logs Table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])

    # 4. Cameras Table
    op.create_table(
        "cameras",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("location", sa.String(length=150), nullable=True),
        sa.Column("stream_source", sa.String(length=500), nullable=False),
        sa.Column("stream_type", sa.String(length=20), nullable=False, server_default="RTSP"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1" if not is_pg else "true")),
        sa.Column("fps", sa.Integer(), nullable=True, server_default="15"),
        sa.Column("resolution", sa.String(length=20), nullable=True, server_default="1280x720"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 5. Zones Table
    op.create_table(
        "zones",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("zone_type", sa.String(length=30), nullable=False, server_default="GENERAL"),
        sa.Column("polygon_coords", sa.JSON(), nullable=True),
        sa.Column("entry_line_coords", sa.JSON(), nullable=True),
        sa.Column("dwell_threshold_seconds", sa.Integer(), nullable=True, server_default="60"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1" if not is_pg else "true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_zones_camera_id", "zones", ["camera_id"])

    # 6. Visitors Table
    op.create_table(
        "visitors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("visitor_code", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False, server_default="Unknown"),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("first_seen", sa.DateTime(), nullable=False),
        sa.Column("last_seen", sa.DateTime(), nullable=False),
        sa.Column("total_visits", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("avg_dwell_time", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("visitor_code"),
    )
    op.create_index("ix_visitors_visitor_code", "visitors", ["visitor_code"])
    op.create_index("ix_visitors_last_seen", "visitors", ["last_seen"])

    # 7. Visitor Embeddings Table (pgvector 512-d or JSON fallback)
    embedding_col = text("vector(512)") if is_pg else sa.JSON()
    op.create_table(
        "visitor_embeddings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("visitor_id", sa.Integer(), sa.ForeignKey("visitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("embedding_type", sa.String(length=20), nullable=False, server_default="reid"),
        sa.Column("embedding", embedding_col, nullable=False),
        sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_visitor_embeddings_visitor_id", "visitor_embeddings", ["visitor_id"])
    op.create_index("ix_visitor_embeddings_created_at", "visitor_embeddings", ["created_at"])

    # HNSW Cosine vector index on Postgres
    if is_pg:
        op.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_visitor_embeddings_hnsw "
            "ON visitor_embeddings USING hnsw (embedding vector_cosine_ops);"
        ))

    # 8. Consents Table
    op.create_table(
        "consents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("person_name", sa.String(length=150), nullable=False),
        sa.Column("consent_type", sa.String(length=50), nullable=False, server_default="FACE_RECOGNITION"),
        sa.Column("consent_granted", sa.Boolean(), nullable=False, server_default=sa.text("0" if not is_pg else "false")),
        sa.Column("proof_document_ref", sa.String(length=255), nullable=True),
        sa.Column("granted_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # 9. Face Enrollments Table
    op.create_table(
        "face_enrollments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("visitor_id", sa.Integer(), sa.ForeignKey("visitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consent_id", sa.Integer(), sa.ForeignKey("consents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("face_image_path", sa.String(length=500), nullable=True),
        sa.Column("enrolled_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("enrolled_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1" if not is_pg else "true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("visitor_id"),
    )

    # 10. Tracks Table
    op.create_table(
        "tracks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("visitor_id", sa.Integer(), sa.ForeignKey("visitors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("dwell_seconds", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("objects_detected", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1" if not is_pg else "true")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tracks_camera_id", "tracks", ["camera_id"])
    op.create_index("ix_tracks_visitor_id", "tracks", ["visitor_id"])

    # 11. Events Table
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("visitor_id", sa.Integer(), sa.ForeignKey("visitors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("zone_id", sa.Integer(), sa.ForeignKey("zones.id", ondelete="SET NULL"), nullable=True),
        sa.Column("track_id", sa.Integer(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("detected_objects", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True, server_default="1.0"),
        sa.Column("thumbnail_path", sa.String(length=500), nullable=True),
        sa.Column("clip_path", sa.String(length=500), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_camera_id", "events", ["camera_id"])
    op.create_index("ix_events_visitor_id", "events", ["visitor_id"])
    op.create_index("ix_events_timestamp", "events", ["timestamp"])

    # 12. Alerts Table
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="MEDIUM"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="NEW"),
        sa.Column("acknowledged_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_alert_type", "alerts", ["alert_type"])
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])

    # 13. Sensor Events Table
    op.create_table(
        "sensor_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sensor_id", sa.String(length=100), nullable=False),
        sa.Column("sensor_type", sa.String(length=30), nullable=False),
        sa.Column("zone_id", sa.Integer(), sa.ForeignKey("zones.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_data", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("linked_event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("linked_visitor_id", sa.Integer(), sa.ForeignKey("visitors.id", ondelete="SET NULL"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sensor_events_sensor_id", "sensor_events", ["sensor_id"])
    op.create_index("ix_sensor_events_timestamp", "sensor_events", ["timestamp"])


def downgrade() -> None:
    op.drop_table("sensor_events")
    op.drop_table("alerts")
    op.drop_table("events")
    op.drop_table("tracks")
    op.drop_table("face_enrollments")
    op.drop_table("consents")
    op.drop_table("visitor_embeddings")
    op.drop_table("visitors")
    op.drop_table("zones")
    op.drop_table("cameras")
    op.drop_table("audit_logs")
    op.drop_table("users")
