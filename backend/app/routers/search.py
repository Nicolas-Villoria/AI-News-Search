from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

router = APIRouter()

@router.get("/")
async def search_intelligence(
    q: str = Query(..., description="The search query text"),
    db: AsyncSession = Depends(get_db)
):
    """
    Full-text search over intelligence items.
    """
    # TODO: Implement postgres full text search (`tsvector` / `pg_trgm`) or semantic search
    return {"results": []}
