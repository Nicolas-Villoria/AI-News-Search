"""
config/settings.py — Central configuration for AI News Search.

All magic numbers, file paths, and tunable parameters live here.
Import this module everywhere instead of hard-coding values.
"""

import os
from pathlib import Path

# Paths and directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ARTICLES_PATH = DATA_DIR / "articles.json"
FAISS_INDEX_PATH = DATA_DIR / "faiss_index.bin"
EMBEDDINGS_PATH = DATA_DIR / "embeddings.npy"

# Ensure data directory exists on import
DATA_DIR.mkdir(parents=True, exist_ok=True)

# RSS Feeds 
# Curated list of feeds that consistently publish AI/tech content.
RSS_FEEDS = [
    # General tech with strong AI coverage
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
    # AI-specific outlets
    "https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml",
    "https://www.marktechpost.com/feed/",
    "https://venturebeat.com/category/ai/feed/",
    # Broader tech (will be filtered by AI keywords)
    "https://www.wired.com/feed/tag/ai/latest/rss",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
]

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
    "speech recognition", "text-to-image", "ai startup",
]

# Embedding Model 
# MiniLM is tiny (~80 MB), fast, and produces quality 384-dim embeddings.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384  

# Summarization Model 
# DistilBART gives decent summaries and is much lighter than full BART.
SUMMARIZER_MODEL_NAME = "sshleifer/distilbart-cnn-12-6"
SUMMARY_MAX_LENGTH = 120
SUMMARY_MIN_LENGTH = 30

# Ranking Weights 
# Final score = w_semantic * cosine_sim + w_time * time_score + w_keyword * kw_score
#
# Semantic similarity: how close the article embedding is to the query.
# Time decay:          exponential decay based on article age in hours.
# Keyword score:       bonus for articles mentioning more AI keywords.
RANKING_WEIGHTS = {
    "semantic": 0.50,   # Cosine similarity to search query
    "time_decay": 0.30, # Freshness — exponential decay
    "keyword": 0.20,    # AI-keyword density bonus
}

# Time-decay half-life: after this many hours an article's freshness
# score drops to 0.5. 48 h means yesterday's news still scores ~0.7.
TIME_DECAY_HALF_LIFE_HOURS = 48

# General 
MAX_ARTICLES_DISPLAY = 30      # Cap for the Streamlit UI
CRAWL_TIMEOUT_SECONDS = 15     # Per-feed HTTP timeout
