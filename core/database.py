"""
Database Engine and Session Management with High-Concurrency Pooling.

Configures connection pooling with pre-ping validation, automatic recycling,
and binds all ORM entities to the dedicated 'schema_whrm' PostgreSQL schema.
"""

from typing import Generator
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from core.config import settings

# ---------------------------------------------------------------------------
# Engine Configuration
# ---------------------------------------------------------------------------
# Configured to support dozens of concurrent LAN client applications
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,  # Discards dropped/dead connections automatically
    connect_args={
        "options": f"-csearch_path={settings.DB_SCHEMA},public"
    }
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Bind all SQLAlchemy models to schema_whrm automatically
metadata = MetaData(schema=settings.DB_SCHEMA)
Base = declarative_base(metadata=metadata)


def ensure_schema_exists():
    """Guarantees that the target schema exists in PostgreSQL before creating tables."""
    with engine.connect() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA};"))
        connection.commit()
        print(f"INFO: Schema `{settings.DB_SCHEMA}` verified/created successfully.")


def get_db() -> Generator[Session, None, None]:
    """Yields a database session scoped to a single request lifecycle."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()