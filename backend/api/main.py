"""
api/main.py — FastAPI backend for AI News Search.

Loads ML models once at startup (embedding + summarizer + FAISS index)
and exposes endpoints for search, summarization, pipeline health, and
pipeline execution.

Run with:
    uvicorn api.main:app --reload --port 8000
"""

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from indexer.build_index import load_index, load_embedding_model
from engine.ranker import search
from engine.summarizer import load_summarizer, summarize_text
from pipeline.run_pipeline import run_pipeline, load_pipeline_stats
from utils.helpers import get_logger
from api.models import SearchRequest, SearchResponse, SummarizeRequest, SummarizeResponse

logger = get_logger(__name__)


# ── Application state — holds models and index in memory ────────────

class AppState:
    """Mutable singleton that keeps expensive objects alive across requests."""

    def __init__(self):
        self.embedding_model = None
        self.summarizer = None
        self.faiss_index = None
        self.articles: list[dict] = []
        self.embeddings = None
        self.pipeline_running = False

    def load_models(self):
        logger.info("Loading models (this happens once) ...")
        self.embedding_model = load_embedding_model()
        self.summarizer = load_summarizer()
        logger.info("All models loaded")

    def load_search_index(self):
        try:
            self.faiss_index, self.embeddings, self.articles = load_index()
            logger.info(f"Search index loaded: {len(self.articles)} articles")
        except FileNotFoundError:
            logger.warning("No index found on disk — run the pipeline first.")
            self.faiss_index = None
            self.articles = []
            self.embeddings = None


state = AppState()


# ── Lifespan — startup / shutdown hook ──────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    state.load_models()
    state.load_search_index()
    yield


# ── FastAPI app ─────────────────────────────────────────────────────

app = FastAPI(
    title="AI News Search API",
    description="Semantic news search powered by FAISS + DistilBART summarization",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ───────────────────────────────────────────────────────

@app.post("/search", response_model=SearchResponse)
def search_articles(request: SearchRequest):
    """
    Semantic search with composite ranking (semantic + freshness + keyword).
    """
    if state.faiss_index is None or not state.articles:
        raise HTTPException(
            status_code=503,
            detail="No index available. Run the pipeline first.",
        )

    results = search(
        query=request.query,
        index=state.faiss_index,
        articles=state.articles,
        model=state.embedding_model,
        top_k=request.top_k,
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


@app.get("/health")
async def get_health():
    """API status + latest pipeline run statistics."""
    pipeline_stats = load_pipeline_stats()

    return {
        "api_status": "running",
        "index_loaded": state.faiss_index is not None,
        "articles_count": len(state.articles),
        "models_loaded": {
            "embedding": state.embedding_model is not None,
            "summarizer": state.summarizer is not None,
        },
        "pipeline_running": state.pipeline_running,
        "pipeline_stats": pipeline_stats,
    }


@app.post("/pipeline/run")
async def trigger_pipeline(background_tasks: BackgroundTasks):
    """Trigger a full pipeline run (crawl -> filter -> index) in the background."""
    if state.pipeline_running:
        raise HTTPException(
            status_code=409,
            detail="Pipeline is already running.",
        )

    def _run_and_reload():
        state.pipeline_running = True
        try:
            run_pipeline()
            state.load_search_index()
            logger.info("Pipeline complete, index reloaded.")
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
        finally:
            state.pipeline_running = False

    background_tasks.add_task(_run_and_reload)
    return {"message": "Pipeline started in background", "status": "running"}
