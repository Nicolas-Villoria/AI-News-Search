"""
api/main.py — FastAPI backend for AI News Search.

Uses PostgreSQL + pgvector for article storage and semantic search.
ML models (embedding + summarizer) are loaded once at startup and
held in memory.

Run with:
    uvicorn api.main:app --reload --port 8000
"""

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:3000",
).split(",")

API_KEY = os.environ.get("API_KEY")

from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Header, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Article, PipelineRun
from db.init_db import init_db
from indexer.build_index import load_embedding_model
from engine.ranker import search_db
from engine.summarizer import load_summarizer, summarize_text
from pipeline.run_pipeline import run_pipeline
from utils.helpers import get_logger
from api.models import (
    SearchRequest, SearchResponse, SummarizeRequest, SummarizeResponse, TopicsResponse
)

logger = get_logger(__name__)


# ── Application state — ML models only ──────────────────────────────

class AppState:
    """Holds expensive ML models in memory across requests.

    Article data and search now live in PostgreSQL.
    """

    def __init__(self):
        self.embedding_model = None
        self.summarizer = None
        self.pipeline_running = False

    def load_models(self):
        logger.info("Loading ML models (this happens once) ...")
        self.embedding_model = load_embedding_model()
        self.summarizer = load_summarizer()
        logger.info("All models loaded")


state = AppState()


# ── Lifespan — startup / shutdown hook ──────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    state.load_models()
    yield


# ── FastAPI app ─────────────────────────────────────────────────────

app = FastAPI(
    title="AI News Search API",
    description="Semantic news search powered by PostgreSQL + pgvector + DistilBART",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


# ── Endpoints ───────────────────────────────────────────────────────

@app.get("/topics", response_model=TopicsResponse)
def get_topics(db: Session = Depends(get_db)):
    """Fetch all active topic clusters."""
    from db.models import TopicCluster
    topics = (
        db.query(TopicCluster)
        .filter(TopicCluster.article_count > 0)
        .order_by(TopicCluster.article_count.desc())
        .all()
    )
    
    return TopicsResponse(
        topics=[{
            "id": t.id,
            "label": t.label,
            "summary": t.summary,
            "article_count": t.article_count
        } for t in topics]
    )


@app.post("/search", response_model=SearchResponse)
def search_articles(request: SearchRequest, db: Session = Depends(get_db)):
    """Semantic search with composite ranking (semantic + freshness + keyword)."""
    article_count = db.query(func.count(Article.id)).scalar()
    if article_count == 0:
        raise HTTPException(
            status_code=503,
            detail="No articles in the database. Run the pipeline first.",
        )

    results = search_db(
        query=request.query,
        db=db,
        model=state.embedding_model,
        top_k=request.top_k,
        weights=None,
        cluster_id=request.cluster_id
    )

    return SearchResponse(
        query=request.query,
        total_results=len(results),
        results=results,
    )


@app.post("/summarize", response_model=SummarizeResponse)
def summarize_article(request: SummarizeRequest):
    """Generate an abstractive summary using DistilBART."""
    if state.summarizer is None:
        raise HTTPException(status_code=503, detail="Summarizer not loaded.")
    summary = summarize_text(request.text, state.summarizer)
    return SummarizeResponse(summary=summary)


@app.get("/")
def read_root():
    """Root endpoint for health checks (e.g., Hugging Face Spaces)."""
    return {"message": "AI News Search API is running"}


@app.get("/health")
def get_health(db: Session = Depends(get_db)):
    """API status + latest pipeline run statistics."""
    article_count = db.query(func.count(Article.id)).filter(
        Article.is_duplicate == False,  # noqa: E712
    ).scalar()

    latest_run = (
        db.query(PipelineRun)
        .order_by(PipelineRun.id.desc())
        .first()
    )

    pipeline_stats = latest_run.stats if latest_run else None

    return {
        "api_status": "running",
        "index_loaded": article_count > 0,
        "articles_count": article_count,
        "models_loaded": {
            "embedding": state.embedding_model is not None,
            "summarizer": state.summarizer is not None,
        },
        "pipeline_running": state.pipeline_running,
        "pipeline_stats": pipeline_stats,
    }


@app.post("/pipeline/run")
async def trigger_pipeline(
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(None),
):
    """Trigger a full pipeline run (crawl -> filter -> embed -> store) in the background."""
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key.")
    if state.pipeline_running:
        raise HTTPException(
            status_code=409,
            detail="Pipeline is already running.",
        )

    def _run():
        state.pipeline_running = True
        try:
            run_pipeline()
            logger.info("Pipeline complete.")
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
        finally:
            state.pipeline_running = False

    background_tasks.add_task(_run)
    return {"message": "Pipeline started in background", "status": "running"}
