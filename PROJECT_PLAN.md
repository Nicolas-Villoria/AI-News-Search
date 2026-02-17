# AI News Search — Implementation Plan

## Project Context

This is an **AI News Intelligence System** designed as a portfolio project targeting an ML Engineer internship at Dow Jones (AI Engineering team). The project demonstrates the core skills they need: **NLP pipelines, information retrieval, search evaluation, deduplication, topic classification, summarization, and entity extraction** — all of which map directly to Factiva, WSJ, and Dow Jones's AI infrastructure.

The system crawls AI-related news from 9 RSS sources, embeds articles with Sentence-Transformers, indexes with FAISS for semantic search, ranks results using a composite scoring formula, and evaluates everything with proper IR metrics.

### Target Role Alignment

| Dow Jones Requirement | Project Feature |
|---|---|
| *"ML pipelines for AI applications"* | End-to-end pipeline: crawl → filter → embed → index → rank |
| *"Information retrieval applications"* | FAISS semantic search + composite ranking + **nDCG/MRR evaluation** |
| *"NLP modeling, algorithm selection"* | Topic classification (zero-shot vs. fine-tuned comparison) |
| *"Summarization tools"* | DistilBART summaries + **ROUGE evaluation** + model comparison |
| *"Analyze and clean large datasets"* | RSS dedup, text extraction, **MinHash near-duplicate detection** |
| *"Evaluate machine systems"* | IR metrics, ablation studies, summarization benchmarks |
| *"Bots and intelligent AI systems"* | NER entity extraction + entity-faceted search |

---

## Current State (What's Built)

| Module | File | Status |
|---|---|---|
| Config | `config/settings.py` | ✅ Done — feeds, keywords, models, weights |
| Crawler | `crawler/rss_crawler.py` | ✅ Done — 9 feeds, newspaper3k extraction, dedup |
| Filter | `filter/ai_filter.py` | ✅ Done — keyword scoring + threshold filter |
| Indexer | `indexer/build_index.py` | ✅ Done — MiniLM embeddings + FAISS IndexFlatIP |
| Ranker | `engine/ranker.py` | ✅ Done — composite: semantic + time decay + keyword |
| Summarizer | `engine/summarizer.py` | ✅ Done — DistilBART direct model invocation |
| Pipeline | `pipeline/run_pipeline.py` | ✅ Done — end-to-end orchestrator |
| Helpers | `utils/helpers.py` | ✅ Done — logging, JSON I/O, time utilities |
| Data | `data/` | ✅ Done — articles.json, faiss_index.bin, embeddings.npy |
| UI | `ui/app.py` | ❌ Not built yet |

---

## New Features to Build

### Feature 1 — IR Evaluation Framework (nDCG, MRR, Precision@K)

**Priority:** 🥇 Highest — They said "information retrieval." You MUST have metrics.

**Files to create:**
- `evaluation/__init__.py`
- `evaluation/ir_metrics.py` — metric computation functions
- `evaluation/test_queries.json` — hand-labeled relevance judgments
- `evaluation/run_eval.py` — run evaluation, print report, save results

**What to implement:**

1. **`evaluation/test_queries.json`** — 15–20 hand-labeled test queries:
   - Each query has a search string and a list of article titles rated 0 (not relevant), 1 (somewhat), 2 (highly relevant)
   - Example: `{"query": "LLM safety research", "judgments": {"Article Title A": 2, "Article Title B": 1, ...}}`
   - Label these by running the ranker, reviewing the top 15 results, and assigning scores manually

2. **`evaluation/ir_metrics.py`** — Pure metric functions:
   - `precision_at_k(relevant: list[int], k: int) -> float` — fraction of top-k results that are relevant
   - `reciprocal_rank(relevant: list[int]) -> float` — 1/rank of first relevant result
   - `dcg_at_k(scores: list[int], k: int) -> float` — discounted cumulative gain: `Σ (2^rel - 1) / log2(i + 2)`
   - `ndcg_at_k(scores: list[int], k: int) -> float` — DCG normalized by ideal DCG
   - `mean_metric(per_query_scores: list[float]) -> float` — average across all queries

3. **`evaluation/run_eval.py`** — Evaluation harness:
   - Load index + model + test queries
   - For each query, run `search()`, match returned titles against judgments
   - Compute per-query nDCG@10, MRR, P@5
   - Compute mean across all queries
   - **Ablation study:** re-run with modified weights:
     - Semantic only: `{semantic: 1.0, time_decay: 0.0, keyword: 0.0}`
     - No time decay: `{semantic: 0.6, time_decay: 0.0, keyword: 0.4}`
     - No keywords: `{semantic: 0.6, time_decay: 0.4, keyword: 0.0}`
   - Print comparison table and save to `data/eval_results.json`

**Expected output:**
```
── IR Evaluation Report ────────────────────────
Config                  nDCG@10   MRR     P@5
Default (50/30/20)      0.742     0.831   0.680
Semantic only           0.695     0.790   0.620
No time decay           0.718     0.805   0.640
No keywords             0.729     0.820   0.660

→ Time decay contributes +3.3% nDCG (freshness matters for news)
→ Keyword signal contributes +1.8% nDCG (modest but positive)
```

**Effort:** 3–4 hours

---

### Feature 2 — Near-Duplicate Detection (MinHash / LSH)

**Priority:** 🥈 — Core Factiva problem. Shows IR depth beyond just search.

**Files to create:**
- `dedup/__init__.py`
- `dedup/minhash.py` — MinHash signature generation + LSH bucketing
- `dedup/dedup_pipeline.py` — cluster articles, pick canonical, log stats

**What to implement:**

1. **`dedup/minhash.py`** — MinHash + LSH core:
   - `shinglize(text: str, k: int = 3) -> set[str]` — extract character k-shingles (word-level 3-grams also fine)
   - `minhash_signature(shingles: set[str], num_hashes: int = 128) -> list[int]` — generate MinHash signature using `num_hashes` random hash functions
   - `jaccard_from_signatures(sig_a, sig_b) -> float` — approximate Jaccard similarity
   - `lsh_buckets(signatures: list, bands: int = 16, rows: int = 8) -> dict[str, list[int]]` — band-based LSH for candidate pairs
   - The key insight: split each signature into `bands` bands of `rows` rows. Two articles are candidates if they share a bucket in any band. With bands=16, rows=8: catches pairs with Jaccard > ~0.5

2. **`dedup/dedup_pipeline.py`** — Integration:
   - `deduplicate_articles(articles: list[dict], threshold: float = 0.6) -> list[dict]`
   - For each candidate pair from LSH, compute exact Jaccard and merge if above threshold
   - Use Union-Find to build clusters from pairwise matches
   - For each cluster, pick the "canonical" article: longest text + earliest publish date
   - Attach `cluster_id` and `is_canonical` fields to each article
   - Log: *"Reduced 180 → 145 unique stories (19% dedup rate)"*

3. **Integration point:** After crawling, before filtering. Insert into `pipeline/run_pipeline.py` between Step 1 (Crawl) and Step 2 (Filter).

**Effort:** 3–4 hours

---

### Feature 3 — Multi-Label Topic Classification

**Priority:** 🥉 — Core NLP task. Shows model comparison skills.

**Files to create:**
- `classification/__init__.py`
- `classification/zero_shot.py` — zero-shot baseline with bart-large-mnli
- `classification/train_classifier.py` — fine-tune distilbert on hand-labeled data
- `classification/labeled_data.json` — 50–100 hand-labeled articles
- `classification/evaluate.py` — compare both approaches

**What to implement:**

1. **Topic label set** (add to `config/settings.py`):
   ```python
   TOPIC_LABELS = [
       "AI Research",
       "AI Policy & Regulation",
       "AI Business & Funding",
       "AI Products & Launches",
       "AI Ethics & Safety",
       "Robotics & Autonomous Systems",
       "Computer Vision",
       "NLP & Large Language Models",
   ]
   ```

2. **`classification/zero_shot.py`** — Zero-shot baseline:
   - Load `facebook/bart-large-mnli` via `transformers` zero-shot pipeline
   - `classify_article(text: str, labels: list[str]) -> dict` — returns `{"labels": ["NLP & LLMs", "AI Research"], "scores": [0.82, 0.71]}`
   - Apply to title + first 300 chars (stay within model context)
   - Multi-label: keep all labels above a confidence threshold (0.4)
   - Measure latency per article

3. **`classification/labeled_data.json`** — Hand-label 50–100 articles:
   - After running the zero-shot classifier, review and correct its predictions
   - Format: `{"title": "...", "text": "...", "topics": ["AI Research", "NLP & LLMs"]}`
   - This double-serves as training data AND evaluation data (use 80/20 split)

4. **`classification/train_classifier.py`** — Fine-tuned model:
   - Fine-tune `distilbert-base-uncased` for multi-label classification
   - Use the hand-labeled data with an 80/20 train/test split
   - Train for 5–10 epochs with a simple classification head
   - Save the model to `data/topic_classifier/`

5. **`classification/evaluate.py`** — Head-to-head comparison:
   - Run both models on the test set
   - Compute per-label and macro F1, precision, recall
   - Compare latency (ms per article) and model size (MB)
   - Print a comparison table:
     ```
     Model           Macro-F1   Latency    Size
     Zero-shot       0.71       850ms      ~1.6 GB
     Fine-tuned      0.83       45ms       ~250 MB
     ```
   - Save results to `data/classification_results.json`

6. **Integration point:** After filtering. Each article gets a `topics` field (list of strings) and `topic_scores` field (list of floats).

**Effort:** 3–4 hours (labeling ~1h, zero-shot ~1h, fine-tune ~1h, eval ~30min)

---

### Feature 4 — Summarization Evaluation (ROUGE Benchmark)

**Priority:** 4th — They said "summarization tools." ROUGE shows rigor.

**Files to create:**
- `evaluation/summarization_eval.py` — ROUGE scoring + model comparison

**What to implement:**

1. **Reference summaries:** Use each article's first paragraph (first `\n\n` split) as a human-written reference. News articles use the inverted pyramid — the lede IS the summary.

2. **Models to compare:**
   - **Extractive baseline:** First 2 sentences (split by `. `)
   - **DistilBART:** Current model (already built)
   - **T5-small:** Lighter alternative (~240 MB vs. ~1.2 GB)

3. **Metrics:**
   - ROUGE-1 (unigram overlap), ROUGE-2 (bigram), ROUGE-L (longest common subsequence)
   - Use the `rouge-score` Python package
   - Also measure latency per article and model size

4. **Output:**
   ```
   Model             ROUGE-1   ROUGE-2   ROUGE-L   Latency   Size
   Extractive (2s)   0.42      0.18      0.38      <1ms      0 MB
   DistilBART        0.47      0.22      0.41      3.5s      1.2 GB
   T5-small          0.44      0.19      0.39      1.8s      240 MB
   
   → DistilBART wins on quality but extractive is 3500x faster
   → T5-small is a practical middle ground for production
   ```

5. **Save** results to `data/summarization_eval.json`

**Effort:** 2–3 hours

---

### Feature 5 — Named Entity Recognition + Entity Search

**Priority:** 5th — Rounds out the NLP portfolio. Do this if time permits.

**Files to create:**
- `ner/__init__.py`
- `ner/entity_extractor.py` — NER pipeline + post-processing
- `ner/entity_index.py` — inverted index: entity → article list

**What to implement:**

1. **`ner/entity_extractor.py`:**
   - Load `dslim/bert-base-NER` via transformers pipeline
   - `extract_entities(text: str) -> dict` returns `{"ORG": ["OpenAI", "Microsoft"], "PER": ["Sam Altman"], "LOC": ["San Francisco"]}`
   - Post-process: merge B-ORG/I-ORG spans, deduplicate, title-case normalize
   - Run on title + first 500 chars

2. **`ner/entity_index.py`:**
   - `build_entity_index(articles: list[dict]) -> dict[str, list[int]]` — inverted index mapping entity name → article indices
   - `search_by_entity(entity: str, index, articles) -> list[dict]` — return all articles mentioning that entity
   - `entity_cooccurrence(articles) -> list[tuple]` — which entities appear together most often
   - Log: *"Extracted 312 unique entities from 109 articles. Top: OpenAI (28), Google (22), Microsoft (18)"*

3. **Integration point:** After filtering, before indexing. Each article gets an `entities` field.

**Effort:** 2–3 hours

---

### Feature 6 — Streamlit Dashboard

**Priority:** Build LAST, after all ML features work.

**Files to create:**
- `ui/app.py` — main Streamlit app
- `.streamlit/config.toml` — dark theme

**What to implement:**

The dashboard has 4 tabs. It lazy-loads models only when needed to avoid the segfault issue (embedding model at startup, summarizer only on click).

1. **🔍 Search** — main tab:
   - Search bar with semantic search
   - Ranked article cards: title, source, date, relevance score bar
   - Score breakdown (semantic / freshness / keyword)
   - Topic tags as colored pills
   - Entity tags
   - Expandable AI summary (lazy-loads summarizer on first click)

2. **📊 Evaluation** — IR metrics tab:
   - nDCG@10, MRR, P@5 as metric cards
   - Ablation study results as a bar chart
   - Summarization ROUGE comparison table
   - Classification F1 comparison table

3. **🔗 Entities** — entity explorer tab:
   - Entity frequency bar chart (top 20)
   - Click an entity → shows all articles mentioning it
   - Co-occurrence network (optional, plotly)

4. **ℹ️ About** — architecture & methodology:
   - Pipeline diagram
   - Ranking formula explanation
   - Tech stack badges

**Sidebar:**
- Ranking weight sliders (live re-ranking)
- Dedup toggle (show/hide near-duplicates)
- Topic filter checkboxes

**Critical design:** The summarizer loads ONLY when a user clicks "AI Summary" on an article. This avoids loading 3 models at startup (which caused the segfault). Use `@st.cache_resource` on all model loaders.

**Effort:** 4–5 hours

---

## Implementation Schedule

| Day | Features | Hours | Deliverable |
|---|---|---|---|
| **Day 1** | Feature 2 (MinHash dedup) | 3–4h | `dedup/` module, integrated into pipeline |
| **Day 2** | Feature 1 (IR evaluation) — label queries + write metrics | 3–4h | `evaluation/` module, eval report |
| **Day 3** | Feature 3 (Topic classification) — zero-shot + labeling | 3–4h | `classification/` zero-shot + labeled data |
| **Day 4** | Feature 3 (continued) — fine-tune + evaluate | 2–3h | Fine-tuned model + comparison table |
| **Day 5** | Feature 4 (Summarization eval) + Feature 5 (NER) | 4–5h | ROUGE benchmark + `ner/` module |
| **Day 6** | Feature 6 (Streamlit dashboard) | 4–5h | Full UI with all tabs |
| **Day 7** | README rewrite + polish + deploy to Streamlit Cloud | 2–3h | Production-ready repo |

**Total: ~22–28 hours across 7 days**

---

## Final Project Structure

```
AI News Search/
├── config/
│   └── settings.py
├── crawler/
│   └── rss_crawler.py
├── filter/
│   └── ai_filter.py
├── dedup/                          ← NEW
│   ├── minhash.py                  # MinHash signatures + LSH
│   └── dedup_pipeline.py           # Cluster + pick canonical articles
├── classification/                 ← NEW
│   ├── zero_shot.py                # bart-large-mnli baseline
│   ├── train_classifier.py         # Fine-tune distilbert
│   ├── labeled_data.json           # 50–100 hand-labeled articles
│   └── evaluate.py                 # Head-to-head comparison
├── ner/                            ← NEW
│   ├── entity_extractor.py         # dslim/bert-base-NER
│   └── entity_index.py             # Entity → article inverted index
├── indexer/
│   └── build_index.py
├── engine/
│   ├── ranker.py
│   └── summarizer.py
├── evaluation/                     ← NEW
│   ├── ir_metrics.py               # nDCG, MRR, P@K functions
│   ├── test_queries.json           # Hand-labeled relevance judgments
│   ├── run_eval.py                 # Evaluation harness + ablation
│   └── summarization_eval.py       # ROUGE benchmark
├── pipeline/
│   └── run_pipeline.py             # Updated: crawl → dedup → filter → classify → NER → index
├── ui/
│   └── app.py                      # Streamlit dashboard (4 tabs)
├── utils/
│   └── helpers.py
├── data/
│   ├── articles.json
│   ├── faiss_index.bin
│   ├── embeddings.npy
│   ├── eval_results.json           ← NEW
│   ├── classification_results.json ← NEW
│   ├── summarization_eval.json     ← NEW
│   └── topic_classifier/           ← NEW (fine-tuned model)
├── .streamlit/
│   └── config.toml
├── requirements.txt
└── README.md
```

---

## Updated Pipeline Flow

```
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌──────────┐   ┌─────────┐   ┌─────────┐
│  Crawl  │ → │  Dedup  │ → │ Filter  │ → │ Classify │ → │   NER   │ → │  Embed  │
│  RSS    │   │ MinHash │   │ Keywords│   │  Topics  │   │ Entities│   │  FAISS  │
│  ~200   │   │  ~160   │   │  ~100   │   │  +tags   │   │  +tags  │   │  Index  │
└─────────┘   └─────────┘   └─────────┘   └──────────┘   └─────────┘   └─────────┘
```

---

## Interview Pitch (30-second version)

> *"I built an end-to-end AI news intelligence system that crawls 200+ articles, deduplicates them with MinHash-LSH, classifies topics with both zero-shot and fine-tuned models, extracts named entities, and ranks results using a composite formula in FAISS. I evaluated the search system with nDCG and MRR on hand-labeled queries, ran ablation studies on the ranking signals, and benchmarked three summarization models with ROUGE scores. The whole pipeline is modular, tested, and deployed on Streamlit Cloud."*
