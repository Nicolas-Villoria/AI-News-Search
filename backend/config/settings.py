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
PIPELINE_STATS_PATH = DATA_DIR / "pipeline_stats.json"

# Ensure data directory exists on import
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://ainews:ainews_dev@localhost:5432/ainews",
)

# RSS Feeds 
# Master list of RSS feeds for AI News Aggregation
RSS_FEEDS = [
    # PRIMARY RESEARCH LABS 
    "https://openai.com/news/rss.xml",                # OpenAI
    "https://deepmind.google/blog/rss.xml",           # Google DeepMind
    "https://www.microsoft.com/en-us/research/feed/", # Microsoft Research
    "https://ai.meta.com/blog/rss.xml",               # Meta AI (Facebook)
    "https://developer.nvidia.com/blog/feed",         # NVIDIA (Hardware/Software)
    "https://aws.amazon.com/blogs/machine-learning/feed/", # AWS ML
    "https://bair.berkeley.edu/blog/feed.xml",        # Berkeley AI Research (Academic)
    "https://research.google/blog/rss",               # Google Research (Broader than DeepMind)

    # DEVELOPER & OPEN SOURCE 
    "https://huggingface.co/blog/feed.xml",           # Hugging Face (The Hub)
    "https://pytorch.org/feed.xml",                   # PyTorch
    "https://blog.langchain.dev/rss/",                # LangChain (Agents/Engineering)
    "https://stackdiary.com/feed/",                   # Engineering focused
    
    # HIGH-SIGNAL AI NEWSLETTERS 
    "https://lastweekin.ai/feed",                     # Last Week in AI
    "https://jack-clark.net/feed/",                   # Import AI (Policy/Safety)
    "https://thesequence.substack.com/feed",          # The Sequence (Technical)
    "https://www.interconnects.ai/feed",              # Interconnects (Model Strategy)

    # GENERAL TECH (Mainstream Coverage)
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml",
    "https://www.marktechpost.com/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.wired.com/feed/tag/ai/latest/rss",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
]

# Source Name Overrides
SOURCE_NAME_OVERRIDES: dict[str, str] = {
    "https://aws.amazon.com/blogs/machine-learning/feed/": "AWS Machine Learning Blog",
}

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
