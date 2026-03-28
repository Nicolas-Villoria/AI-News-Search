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

_APP_TABLES = ("articles", "entities", "topic_clusters", "pipeline_runs")



def init_db() -> None:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    logger.info("pgvector extension enabled")
    Base.metadata.create_all(bind=engine)
    logger.info("All tables created successfully")
    
    with engine.connect() as conn:
        for tbl in _APP_TABLES:
            # Check if RLS is already enabled for this table to avoid redundant ALTER TABLE calls
            # which require an ACCESS EXCLUSIVE lock and can cause timeouts.
            check_rls_sql = text(f"""
                SELECT relrowsecurity FROM pg_class 
                WHERE oid = 'public."{tbl}"'::regclass;
            """)
            try:
                rls_enabled = conn.execute(check_rls_sql).scalar()
                if not rls_enabled:
                    logger.info(f"Enabling Row Level Security for table '{tbl}'...")
                    conn.execute(text(f'ALTER TABLE public."{tbl}" ENABLE ROW LEVEL SECURITY'))
                else:
                    logger.debug(f"Row Level Security already enabled for table '{tbl}'")
            except Exception as e:
                logger.warning(f"Could not check or enable RLS for table '{tbl}': {e}")
        conn.commit()



if __name__ == "__main__":
    init_db()
