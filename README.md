# AI News Search (Hawker)

An AI-powered news aggregation and search system that crawls tech news from RSS feeds, filters for AI-related content, ranks articles using a composite scoring formula (semantic similarity + freshness + keyword density), and generates summaries with DistilBART.

---

## What It Does

1. **Crawls** ~200 articles from 25+ curated RSS feeds (OpenAI, DeepMind, TechCrunch, etc.)
2. **Filters** down to AI-related articles using keyword matching (~70% pass rate)
3. **Extracts Entities (NER)** using **spaCy** to identify People, Organizations, and GPEs
4. **Embeds** article text with Sentence-Transformers (`all-MiniLM-L6-v2`)
5. **Clusters** articles using **K-Means (scikit-learn)** to discover trending topics
6. **Indexes** in **PostgreSQL + pgvector** using HNSW for fast semantic search
7. **Ranks** results using a weighted composite of semantic similarity, time decay, and keyword density
8. **Summarizes** articles on demand with **DistilBART**

---

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  RSS Crawl  │ →  │  AI Filter  │ →  │  NER Extr.  │ →  │  Cluster    │
│  25+ feeds  │    │  keywords   │    │  spaCy      │    │  K-Means    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                ↓
                    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
   User query  →    │  Ranker     │ ←  │  Postgres   │ ←  │  Embed      │
                    │  pgvector   │    │  + pgvector │    │  MiniLM     │
                    └─────────────┘    └─────────────┘    └─────────────┘
                           ↓
                    ┌─────────────┐
                    │  Summarizar │
                    │  DistilBART  │
                    └─────────────┘
```

---

## Ranking Formula

Articles are ranked using a weighted composite score:
```
score = w_semantic × cosine_sim + w_time × time_decay + w_keyword × keyword_score
```

| Signal | Weight | Description |
|---|---|---|
| **Semantic similarity** | 0.50 | Cosine similarity between query and article embeddings |
| **Time decay** | 0.20 | Exponential freshness: `2^(−hours / 48)` |
| **Keyword density** | 0.30 | Ratio of distinct AI keywords found in the article |

---

## Project Structure

```
AI News Search/
├── backend/
│   ├── api/                 # FastAPI routes + Pydantic models
│   ├── crawler/             # RSS fetching + full-text extraction
│   ├── db/                  # SQLAlchemy models + migrations (pgvector)
│   ├── engine/              # Ranking logic + Summarization
│   ├── filter/              # AI keyword filtering
│   ├── indexer/             # Embedding logic
│   └── pipeline/            # End-to-end orchestrator
├── frontend/                # Next.js 15 app (Tailwind, Radix, SWR)
├── Dockerfile               # Backend production build (pre-downloads models)
├── docker-compose.yml       # Local dev environment (pgvector container)
└── requirements.txt         # Backend Python dependencies
```

---

## Quick Start (Local Dev)

1. **Clone and enter the project**
   ```bash
   git clone <repo-url>
   cd AI-News-Search
   ```

2. **Start the Database**
   ```bash
   docker-compose up -d
   ```

3. **Backend Setup**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r ../requirements.txt
   # Run the pipeline to populate the DB
   python -m pipeline.run_pipeline
   # Start the API
   uvicorn api.main:app --reload
   ```

4. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## Deployment Recommendations

### Backend (Hosting Alternatives)

If you lack Railway credit, these are the best options for ML-intensive Python backends:

1. **Hugging Face Spaces (Docker):** **Highly Recommended.**
   - Free CPU tier has **16GB RAM**, perfect for Torch + Transformers.
   - Use the provided `Dockerfile` (pre-downloads models for fast startup).
2. **Oracle Cloud "Always Free":** Most powerful free tier (24GB RAM).
3. **Google Cloud Run:** Use the $300 trial credit; perfect for containerized APIs.

### Frontend

- **Vercel:** Optimized for Next.js. Set `NEXT_PUBLIC_API_URL` to your backend URL.

---

## Production Hardening

The following fixes have been implemented for production readiness:
- **CORS Restricted:** Lock to specific domains via `ALLOWED_ORIGINS` env var.
- **Protected Pipeline:** `/pipeline/run` requires `X-API-Key` header.
- **Model Caching:** Singleton pattern avoids reloading 1GB of models in RAM.
- **Pre-downloaded Models:** Docker build downloads ML weights to avoid startup latency.
- **Typed API:** Full Pydantic `ArticleResult` models for OpenAPI documentation.
- **Health Checks:** Lightweight `/ping` endpoint for load balancers.
