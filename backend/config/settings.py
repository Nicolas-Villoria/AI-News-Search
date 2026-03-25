"""
config/settings.py — Central configuration for AI News Search.

All magic numbers, file paths, and tunable parameters live here.
Import this module everywhere instead of hard-coding values.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
import yaml

# Paths and directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent
DATA_DIR = PROJECT_ROOT / "data"
ARTICLES_PATH = DATA_DIR / "articles.json"
PIPELINE_STATS_PATH = DATA_DIR / "pipeline_stats.json"

# Load .env before DATABASE_URL — uvicorn does not read .env automatically.
for _env_path in (REPO_ROOT / ".env", PROJECT_ROOT / ".env"):
    if _env_path.is_file():
        load_dotenv(_env_path, override=False)

# Ensure data directory exists on import
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://ainews:ainews_dev@localhost:5432/ainews",
)

# RSS Feeds — loaded from feeds.yaml so non-developers can edit them.
_FEEDS_YAML = Path(__file__).parent / "feeds.yaml"

def _load_feeds() -> tuple[list[str], dict[str, str]]:
    with open(_FEEDS_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("feeds", []), data.get("source_overrides", {})

RSS_FEEDS, SOURCE_NAME_OVERRIDES = _load_feeds()

# AI Keyword Filter 
# Articles must match at least one keyword (case-insensitive) to pass.
AI_KEYWORDS = [
    "artificial intelligence", "machine learning", "deep learning",
    "neural network", "natural language processing", "nlp",
    "large language model", "llm", "gpt", "chatgpt", "openai",
    "generative ai", "gen ai", "transformer", "bert", "diffusion model",
    "computer vision", "reinforcement learning", "ai model",
    "ai agent", "ai safety", "ai regulation", "ai ethics",
    "robotics", "autonomous", "claude", "gemini", "copilot",
    "stable diffusion", "midjourney", "hugging face",
    "foundation model", "fine-tuning", "rag", "retrieval augmented",
    "prompt engineering", "multimodal", "ai chip", "nvidia",
    "speech recognition", "text-to-image", "ai startup", "ai research",
    "ai breakthrough", "ai innovation", "ai application", "openclaw", 
    "moltbook", "deepseek", "ai news", "ai trends", "ai development",
]

# Embedding Model 
# MiniLM is tiny (~80 MB), fast, and produces quality 384-dim embeddings.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384  

# Summarization (DistilBART)
SUMMARIZER_MODEL_NAME = "sshleifer/distilbart-cnn-12-6"
SUMMARY_MAX_LENGTH = 150
SUMMARY_MIN_LENGTH = 40

# Ranking Weights 
# Final score = w_semantic * cosine_sim + w_time * time_score + w_keyword * kw_score
#
# Semantic similarity: how close the article embedding is to the query.
# Time decay:          exponential decay based on article age in hours.
# Keyword score:       bonus for articles mentioning more AI keywords.
RANKING_WEIGHTS = {
    "semantic": 0.50,   # Cosine similarity to search query
    "time_decay": 0.20, # Freshness — exponential decay
    "keyword": 0.30,    # AI-keyword density bonus
}

# Time-decay half-life: after this many hours an article's freshness
# score drops to 0.5. 48 h means yesterday's news still scores ~0.7.
TIME_DECAY_HALF_LIFE_HOURS = 48

# General 
MAX_ARTICLES_DISPLAY = 30      # Cap for the UI
CRAWL_TIMEOUT_SECONDS = 15     # Per-feed HTTP timeout
MAX_ARTICLE_AGE_DAYS = 7       # Keep only articles from the last N days (None to disable)
MAX_ARTICLE_RETENTION_DAYS = 90 # Garbage-collect articles older than this from the DB
