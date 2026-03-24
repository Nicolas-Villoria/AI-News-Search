"""
db/database.py — SQLAlchemy engine and session factory.

Reads DATABASE_URL from the environment (or falls back to the local
Docker Compose default).  Every request handler gets a session via
``get_db()`` and FastAPI's dependency injection.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config.settings import DATABASE_URL


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a DB session and auto-closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
