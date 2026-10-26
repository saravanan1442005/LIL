"""Migrate data from SQLite to Supabase PostgreSQL using SQLAlchemy ORM models."""
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database.models import (
    Base, User, AuditLog, Camera, Zone, Visitor, VisitorEmbedding,
    Consent, FaceEnrollment, OTPChallenge, VisitorEntry, PlateRead, Track, Event, Alert, SensorEvent
)

sqlite_path = Path(__file__).parent.parent / "data" / "ecolifybuddy_dev.db"
if not sqlite_path.exists():
    print("No local SQLite database found.")
    sys.exit(0)

# SQLite Session
sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
SqliteSession = sessionmaker(bind=sqlite_engine)

# Supabase Postgres Session
pg_url = os.getenv("DATABASE_URL")
pg_engine = create_engine(pg_url, connect_args={"prepare_threshold": None})
PgSession = sessionmaker(bind=pg_engine)

with SqliteSession() as s_sess, PgSession() as pg_sess:
    # 1. Zones
    for zone in s_sess.query(Zone).all():
        s_sess.expunge(zone)
        pg_sess.merge(zone)
    pg_sess.commit()
    print("Migrated Zones.")

    # 2. Cameras
    for cam in s_sess.query(Camera).all():
        s_sess.expunge(cam)
        pg_sess.merge(cam)
    pg_sess.commit()
    print("Migrated Cameras.")

    # 3. Visitors
    v_count = 0
    for v in s_sess.query(Visitor).all():
        s_sess.expunge(v)
        pg_sess.merge(v)
        v_count += 1
    pg_sess.commit()
    print(f"Migrated {v_count} Visitors.")

    # 4. Consents
    for c in s_sess.query(Consent).all():
        s_sess.expunge(c)
        pg_sess.merge(c)
    pg_sess.commit()

    # 5. Visitor Entries
    ve_count = 0
    for ve in s_sess.query(VisitorEntry).all():
        s_sess.expunge(ve)
        pg_sess.merge(ve)
        ve_count += 1
    pg_sess.commit()
    print(f"Migrated {ve_count} Visitor Entries.")

    # 6. Plate Reads
    for pr in s_sess.query(PlateRead).all():
        s_sess.expunge(pr)
        pg_sess.merge(pr)
    pg_sess.commit()

    # 7. Other models
    for m in [FaceEnrollment, Track, Event, Alert, SensorEvent]:
        for item in s_sess.query(m).all():
            s_sess.expunge(item)
            pg_sess.merge(item)
        pg_sess.commit()

    # Reset postgres ID sequences to avoid duplicate key errors on future inserts
    for table_name in ["visitors", "visitor_entries", "cameras", "zones"]:
        try:
            pg_sess.execute(text(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), coalesce(max(id), 1)) FROM {table_name};"))
            pg_sess.commit()
        except Exception:
            pg_sess.rollback()

print("[+] All existing records successfully migrated to Supabase PostgreSQL!")
