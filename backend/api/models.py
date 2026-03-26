from pydantic import BaseModel, Field


# ── Pydantic request / response models ──────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(default="", min_length=0, max_length=500)
    top_k: int = Field(default=10, ge=1, le=50)
    cluster_id: int | None = Field(default=None, description="Optional topic ID to filter by")

class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1)

class EntityResult(BaseModel):
    name: str
    label: str
    count: int

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
    cluster_id: int | None = None
    entities: list[EntityResult] = Field(default_factory=list)

class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: list[ArticleResult]

class SummarizeResponse(BaseModel):
    summary: str

class TopicClusterItem(BaseModel):
    id: int
    label: str
    summary: str | None
    article_count: int

class TopicsResponse(BaseModel):
    topics: list[TopicClusterItem]