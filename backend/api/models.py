from pydantic import BaseModel, Field


# ── Pydantic request / response models ──────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(default=10, ge=1, le=50)


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1)


class ArticleResult(BaseModel):
    """A single ranked article in the search response."""
    id: int
    title: str
    link: str
    source: str | None = None
    published: str | None = None
    text: str | None = None
    semantic_score: float
    time_score: float
    keyword_score: float
    relevance_score: float


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: list[ArticleResult]


class SummarizeResponse(BaseModel):
    summary: str