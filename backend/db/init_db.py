"""
db/init_db.py — Create all tables and enable the pgvector extension.

Run once after starting the PostgreSQL container:
    python -m db.init_db
"""

from sqlalchemy import text

from db.database import engine, Base
from db import models  # noqa: F401 — registers ORM models with Base
from utils.helpers import get_logger

logger = get_logger(__name__)


def init_db() -> None:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    logger.info("pgvector extension enabled")

    Base.metadata.create_all(bind=engine)
    logger.info("All tables created successfully")


if __name__ == "__main__":
    init_db()
