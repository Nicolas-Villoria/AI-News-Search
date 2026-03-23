from pydantic import BaseModel, Field


# ── Pydantic request / response models ──────────────────────────────
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(default=10, ge=1, le=50)


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1)


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: list[dict]


class SummarizeResponse(BaseModel):
    summary: str