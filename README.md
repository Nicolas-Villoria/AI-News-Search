# Hawker

Hawker is an AI-powered news aggregator and search engine. It automatically crawls tech RSS feeds, filters for AI-related content, embeds articles into vector space, and ranks search results using a composite formula of semantic similarity, exponential time decay, and keyword density.

## Core Features

- **Semantic Search**: Find articles based on meaning rather than exact keyword matches.
- **Dynamic Topic Clustering**: Automatically groups recent news into distinct trending topics without relying on predefined categories.
- **Named Entity Extraction**: Identifies and tags key organizations, people, and products in every story.
- **On-Demand Summarization**: Generates abstractive summaries of long-form articles instantly using a transformer model.

## Technologies and Libraries

- **[pgvector](https://github.com/pgvector/pgvector)**: An open-source vector similarity search for Postgres. It handles both embedding storage and fast approximate nearest-neighbor search through HNSW indices.
- **[Sentence-Transformers](https://sbert.net/)**: Specifically the `all-MiniLM-L6-v2` model, used to efficiently generate 384-dimensional dense semantic vectors. 
- **[spaCy](https://spacy.io/)**: An industrial-strength NLP library used for Named Entity Recognition (NER) to surface people, organizations, and products within the articles.
- **[scikit-learn](https://scikit-learn.org/)**: The K-Means clustering implementation used to dynamically group articles with similar semantic vectors into trending topics.
- **[feedparser](https://github.com/kurtmckee/feedparser)** and **[newspaper3k](https://github.com/codelucas/newspaper)**: A dependable pairing for scraping RSS feeds and extracting clean article body text from raw HTML.
- **[SWR](https://swr.vercel.app/)**: Next.js data fetching state management used in the frontend for robust search querying, request deduplication, and triggering initial chronological data loads on component mount.
- **Typography**: The frontend UI utilizes **[Inter](https://fonts.google.com/specimen/Inter)** for clean sans-serif UI elements and **[Instrument Serif](https://fonts.google.com/specimen/Instrument+Serif)** for an elegant, editorial feel on article titles.

## Project Structure

```text
.
├── backend
│   ├── api
│   ├── config
│   ├── crawler
│   ├── db
│   ├── engine
│   ├── filter
│   ├── indexer
│   └── pipeline
├── docs
├── frontend
│   ├── app
│   ├── components
│   ├── hooks
│   └── lib
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

- [backend/engine](/backend/engine): Contains the core intelligence logic. This includes the ranking engines pushing math down to Postgres, the `spaCy` NER extraction, and the `scikit-learn` K-Means topic clustering. 
- [backend/pipeline](/backend/pipeline): The orchestrator scripts that crawl feeds, process text, generate embeddings, and clean up orphaned clusters sequentially.
- [frontend/components](/frontend/components): The React building blocks, housing the interactive trending topic chips and the entity-tagged article cards.
