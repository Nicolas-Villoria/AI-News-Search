# Hawker Backend Scaffolding

This backend is set up with FastAPI, async SQLAlchemy (PostgreSQL), and Pydantic. 
The core directory structure, config, ORM models, schemas, and empty API routers have been scaffolded for you.

## Your Mission

Since you want to learn and work on this yourself, here is how you can continue:

### 1. Database Setup
1. Ensure you have PostgreSQL running (`brew install postgresql` if on Mac, then start the service).
2. Create the database: `createdb hawker`
3. We have `alembic` ready. Run `alembic init alembic` to set it up (or write a quick python script using `app.database.init_db()` to create the tables natively).

### 2. Implement Data Ingestion (The Services)
Inside `app/services/`:
- **`fmp_service.py`**: Pick up an API key from Financial Modeling Prep. Use Python's `httpx` component to asynchronously hit their endpoints for Company Profiles and Earnings Calendars.
- **`edgar_service.py`**: Look at the `edgartools` library! It's fantastic for fetching 10-K and 10-Q SEC filings. Fetch a company's recent filings, extract the text, and prepare to summarize.
- **`finnhub_service.py`**: Get an API key from Finnhub to fetch Analyst Ratings and recent Market News.
- **`nlp_service.py`**: Take the raw data from EDGAR/News that you fetched, and prompt the `openai` client (`gpt-4o-mini`) using the Pydantic schema `IntelligenceItemSchema` via OpenAI's *Structured Outputs*.

### 3. Implement the Routers
Inside `app/routers/`:
Fill out the `# TODO` sections. Map the database queries from `app/models/models.py` into the Pydantic models in `app/schemas/schemas.py`.
- e.g. In `feed.py`, query the `IntelligenceItem` table, sort by `impact_score DESC`, limit to 20, and return.

### Give it a spin
Run the server with `uvicorn app.main:app --reload`.
Check the swagger docs at `http://localhost:8000/docs`.
