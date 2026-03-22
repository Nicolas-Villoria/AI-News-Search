Day 1: FastAPI Backend + Streamlit Search Tab
FastAPI backend -- single process, models loaded once at startup:

POST /search -- query -> ranked results with score breakdowns
POST /summarize -- article text -> DistilBART summary
GET /health -- pipeline stats (articles indexed, feed success rates, timing)
POST /pipeline/run -- trigger a fresh crawl->filter->index run
Streamlit frontend -- thin HTTP client, no ML imports:

Search tab: search bar, ranked result cards with score breakdown bars (semantic / freshness / keyword), one-click "Summarize" button per article
Clean, modern layout
Pipeline instrumentation -- modify the pipeline to track metrics (per-feed timing, success/failure, article counts at each stage) and save them to a pipeline_stats.json.

Day 2: Pipeline Health Tab + Evaluation Framework
Pipeline Health tab in Streamlit:

Total articles crawled / filtered / indexed
Per-feed success vs. failure rates (bar chart)
Average time per embedding, total pipeline duration
Article age distribution (histogram)
Last run timestamp, "Re-run Pipeline" button
Evaluation framework:

Create a golden test set: ~10-12 curated queries with manually labeled relevant articles
Compute MRR and Precision@5
Ablation study: run the same queries with (a) semantic only, (b) time only, (c) keyword only, (d) full composite -- show how composite outperforms individual signals
Evaluation tab in Streamlit with charts showing the results
Day 3: NLP Enrichment + Docker + Polish
Zero-shot classification (facebook/bart-large-mnli):

Classify articles into AI subtopics (LLMs, Computer Vision, Robotics, AI Ethics, AI Infrastructure)
Add topic tags to search results, topic filter dropdown in sidebar
Production packaging:

Docker + docker-compose (one command: docker-compose up)
README overhaul with architecture diagram, screenshots, evaluation results
Polish:

Error handling, empty states, loading spinners
Demo preparation: pick 3-4 queries that showcase the system's strengths
Architecture Overview

┌─────────────────────────────────────────────────────┐
│                  Streamlit Frontend                   │
│  ┌──────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │  Search   │  │ Pipeline Health │  │  Evaluation  │ │
│  │   Tab     │  │     Tab         │  │     Tab      │ │
│  └────┬─────┘  └──────┬─────────┘  └──────┬───────┘ │
│       │               │                    │          │
└───────┼───────────────┼────────────────────┼──────────┘
        │  HTTP calls   │                    │
        ▼               ▼                    ▼
┌─────────────────────────────────────────────────────┐
│                   FastAPI Backend                     │
│  ┌──────────────────────────────────────────┐        │
│  │  Models loaded once at startup:           │        │
│  │  • MiniLM-L6-v2 (embeddings)             │        │
│  │  • DistilBART (summarization)            │        │
│  │  • FAISS index (search)                  │        │
│  └──────────────────────────────────────────┘        │
│  POST /search  │ POST /summarize │ GET /health       │
│  POST /pipeline/run │ GET /evaluate                  │
└─────────────────────────────────────────────────────┘