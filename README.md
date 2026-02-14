# AI News Search

An AI-powered news aggregation and search system that crawls tech news from RSS feeds, filters for AI-related content, ranks articles using a composite scoring formula (semantic similarity + freshness + keyword density), and generates summaries with DistilBART.

---

## What It Does

1. **Crawls** ~200 articles from 9 curated RSS feeds (BBC Tech, TechCrunch AI, MIT News, Wired, etc.)
2. **Filters** down to AI-related articles using keyword matching (~60% pass rate)
3. **Embeds** article text with Sentence-Transformers and indexes with FAISS for semantic search
4. **Ranks** results using a weighted composite of semantic similarity, time decay, and keyword density
5. **Summarizes** top articles on demand with DistilBART

---

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  RSS Crawl  │ →  │  AI Filter  │ →  │  Embed +    │ →  │   Save to   │
│  feedparser │    │  keywords   │    │  FAISS Index │    │   disk      │
│  newspaper  │    │  scoring    │    │  MiniLM-L6   │    │   .json/.bin│
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     ~200               ~110              109×384           3 artifacts
   articles           AI articles        embeddings

                    ┌─────────────┐    ┌─────────────┐
   User query  →    │  Ranker     │ →  │  Summarizer │
                    │  FAISS +    │    │  DistilBART  │
                    │  composite  │    │  on-demand   │
                    └─────────────┘    └─────────────┘
```

---

## Ranking Formula

Articles are ranked using a weighted composite score:

```
score = w_semantic × cosine_sim + w_time × time_decay + w_keyword × keyword_score
```

| Signal | Weight | Description |
|---|---|---|
| **Semantic similarity** | 0.50 | Cosine similarity between query embedding and article embedding (FAISS inner product on L2-normalized vectors) |
| **Time decay** | 0.30 | Exponential freshness: `2^(−hours / 48)`. A 24h-old article scores ~0.71, 48h → 0.50, 1 week → 0.04 |
| **Keyword density** | 0.20 | Ratio of distinct AI keywords found in the article (from a curated list of ~50 terms) |

**Why a blend?** Pure semantic search favors evergreen content. Pure recency ignores relevance. The weighted blend rewards articles that are *both relevant and fresh*.

---

## Project Structure

```
AI News Search/
├── config/
│   ├── __init__.py
│   └── settings.py          # Central config: feeds, keywords, model names, weights
├── crawler/
│   ├── __init__.py
│   └── rss_crawler.py       # RSS fetching + newspaper3k text extraction
├── filter/
│   ├── __init__.py
│   └── ai_filter.py         # Keyword-based AI topic filter + scoring
├── indexer/
│   ├── __init__.py
│   └── build_index.py       # Sentence embedding + FAISS index builder
├── engine/
│   ├── __init__.py
│   ├── ranker.py             # Composite ranking (semantic + time + keyword)
│   └── summarizer.py         # DistilBART article summarization
├── pipeline/
│   ├── __init__.py
│   └── run_pipeline.py       # End-to-end orchestrator: crawl → filter → index
├── utils/
│   ├── __init__.py
│   └── helpers.py             # Logging, JSON I/O, time utilities
├── data/                      # Generated artifacts (gitignored)
│   ├── articles.json          # Filtered article metadata + text
│   ├── faiss_index.bin        # FAISS binary index
│   └── embeddings.npy         # Raw embedding vectors
├── requirements.txt
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.9+
- macOS / Linux (Windows should work but untested)

### Setup

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd "AI News Search"

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (macOS only) Fix SSL certificates if you get SSL errors
# Run the "Install Certificates" command for your Python version:
/Applications/Python\ 3.11/Install\ Certificates.command
```

### Run

```bash
# Run the full pipeline (crawl → filter → embed → index)
# Takes ~2 minutes on first run
python -m pipeline.run_pipeline

# Test the ranker with sample queries
python -m engine.ranker

# Test the summarizer on a few articles
python -m engine.summarizer
```

Each module can also be run standalone for testing:

```bash
python -m crawler.rss_crawler     # Crawl only
python -m filter.ai_filter        # Filter only (needs articles.json)
python -m indexer.build_index     # Index only (needs articles.json)
```

---

## Configuration

All configuration lives in [`config/settings.py`](config/settings.py):

| Setting | Default | Description |
|---|---|---|
| `RSS_FEEDS` | 9 feeds | List of RSS feed URLs to crawl |
| `AI_KEYWORDS` | ~50 terms | Keywords for the AI topic filter |
| `EMBEDDING_MODEL_NAME` | `all-MiniLM-L6-v2` | Sentence-transformer model (384-dim) |
| `SUMMARIZER_MODEL_NAME` | `sshleifer/distilbart-cnn-12-6` | Summarization model |
| `RANKING_WEIGHTS` | `{sem: 0.5, time: 0.3, kw: 0.2}` | Composite ranking weights |
| `TIME_DECAY_HALF_LIFE_HOURS` | `48` | Hours until freshness score halves |
| `MAX_ARTICLES_DISPLAY` | `30` | Max results returned per query |

### Adding new RSS feeds

Add any RSS feed URL to the `RSS_FEEDS` list in `settings.py`. The crawler handles failures gracefully — broken feeds are skipped without crashing.

---

## Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| RSS Crawling | `feedparser` + `newspaper3k` | Fetch feeds + extract full article text |
| Embeddings | `sentence-transformers` (MiniLM-L6-v2) | Encode articles into 384-dim dense vectors |
| Vector Search | `FAISS` (IndexFlatIP) | Fast exact nearest-neighbor search via inner product |
| Summarization | `transformers` (DistilBART-CNN-12-6) | Generate concise article summaries |
| Data Storage | JSON + NumPy + FAISS binary | Simple local persistence — no database needed |
| Language | Python 3.11 | Modular, typed, documented |

---

## Pipeline Performance

Typical run (MacBook Pro, CPU only):

| Stage | Count | Time |
|---|---|---|
| Crawl (9 feeds) | ~200 articles | ~90s |
| Filter (keywords) | ~110 kept | <1s |
| Embed (MiniLM) | 110 × 384 vectors | ~5s |
| Index (FAISS) | 110 vectors | <1s |
| **Total pipeline** | | **~100s** |
| Summarize (per article) | 1 article | ~3–5s |

---

## Future Improvements

Planned enhancements (each achievable in 1 day or less):

| Feature | Effort | What it demonstrates |
|---|---|---|
| **Streamlit UI** | 3–4 hours | Full-stack delivery: search bar, ranked cards, score visualizations, on-demand summaries |
| **Zero-shot AI filter** (bart-large-mnli) | 2–3 hours | NLP depth beyond keyword matching |
| **Async crawling** (aiohttp + asyncio) | 2 hours | 10× faster crawling, concurrency patterns |
| **FastAPI wrapper** | 2 hours | REST API layer for the search engine |
| **Docker + docker-compose** | 1 hour | Containerized deployment |
| **Daily cron / GitHub Actions** | 1 hour | Automated data refresh |
| **Article deduplication** (MinHash/LSH) | 2 hours | IR knowledge — near-duplicate detection |
| **Evaluation metrics** (MRR, nDCG) | 3 hours | ML rigor — measuring search quality |
| **Click tracking** | 2 hours | Product thinking — implicit relevance feedback |

---

## Design Decisions

**Why FAISS IndexFlatIP?**
Brute-force exact inner product search. For <100k vectors it's fast enough and gives perfect recall. For millions of vectors you'd switch to `IndexIVFFlat` (approximate search with Voronoi clustering).

**Why normalize + inner product instead of L2 distance?**
For unit-length vectors, inner product equals cosine similarity, which is the standard metric for text similarity. FAISS's IP index then returns cosine scores directly.

**Why keywords over zero-shot classification for filtering?**
Zero-shot classification (~2s per article on CPU) is too slow for 200 articles in an MVP. Keywords are instant and ~90%+ accurate for this use case. Zero-shot is logged as a planned upgrade.

**Why not summarize all articles in the pipeline?**
DistilBART takes ~3–5s per article on CPU. Summarizing 100 articles would add ~5 minutes to the pipeline. Instead, summaries are generated on-demand when a user views an article.

---

## License

MIT
