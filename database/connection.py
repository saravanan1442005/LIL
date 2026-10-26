"""Database connection factory for EcoLifyBuddy.
Supports Neon Postgres (pooler endpoint for app, direct endpoint for migrations)
via SQLAlchemy + psycopg driver, with pool_pre_ping and cold-start retry logic.
Falls back to a local SQLite database for offline demos and testing when DATABASE_URL is unset.
NEVER logs or exposes database credentials.
"""
import os
import time
import logging
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import OperationalError

# Load environment variables from .env if present
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

logger = logging.getLogger("ecolifybuddy.db")
Base = declarative_base()

_engine = None
_SessionFactory = None


def get_database_url(direct: bool = False) -> str:
    """Retrieve normalized database URL from environment.
    App uses DATABASE_URL (pooler endpoint).
    Alembic migrations use DATABASE_URL_DIRECT (direct endpoint).
    """
    raw_url = os.getenv("DATABASE_URL_DIRECT" if direct else "DATABASE_URL", "").strip()

    # Detect unset or placeholder URLs
    if not raw_url or "ep-xxxx" in raw_url or "USER:PASSWORD" in raw_url:
        # Fallback to local SQLite for offline demos / unit testing
        db_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(db_dir, exist_ok=True)
        return f"sqlite:///{os.path.join(db_dir, 'ecolifybuddy_dev.db')}"

    # Ensure postgresql+psycopg driver prefix
    if raw_url.startswith("postgres://"):
        raw_url = "postgresql+psycopg://" + raw_url[len("postgres://"):]
    elif raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+"):
        raw_url = "postgresql+psycopg://" + raw_url[len("postgresql://"):]

    return raw_url


def is_postgres(url: str) -> bool:
    return url.startswith("postgresql")


def create_app_engine(max_retries: int = 3, retry_delay: float = 1.5):
    """Create SQLAlchemy engine with Neon cold-start retry handling and pool_pre_ping."""
    url = get_database_url(direct=False)
    engine_kwargs = {
        "echo": False,
        "pool_pre_ping": True,
    }

    if is_postgres(url):
        engine_kwargs["pool_recycle"] = 300
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20
        # Connect timeout and disable server-side prepared statements for Supabase/Neon connection poolers
        engine_kwargs["connect_args"] = {
            "connect_timeout": 15,
            "prepare_threshold": None,
        }
    else:
        # SQLite compatibility flags
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    # Attempt connection with retries for Neon cold starts
    for attempt in range(1, max_retries + 1):
        try:
            engine = create_engine(url, **engine_kwargs)
            # Test connection with a quick ping
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            db_type = "Neon Postgres (pooler)" if is_postgres(url) else "SQLite (Local Fallback)"
            logger.info("Connected to database: %s", db_type)
            return engine
        except OperationalError as exc:
            if attempt == max_retries:
                logger.warning("Database connection failed after %d attempts. Error: %s", max_retries, exc)
                # Fallback to SQLite if Postgres unreachable during offline dev
                if is_postgres(url):
                    logger.warning("Falling back to local SQLite for resilient offline execution.")
                    db_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
                    os.makedirs(db_dir, exist_ok=True)
                    fallback_url = f"sqlite:///{os.path.join(db_dir, 'ecolifybuddy_dev.db')}"
                    fallback_engine = create_engine(fallback_url, connect_args={"check_same_thread": False})
                    return fallback_engine
                raise
            time.sleep(retry_delay * attempt)


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_app_engine()
    return _engine


def get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionFactory


def get_db() -> Generator[Session, None, None]:
    """FastAPI/Flask request session generator."""
    session_factory = get_session_factory()
    session: Session = session_factory()
    try:
        yield session
    finally:
        session.close()
