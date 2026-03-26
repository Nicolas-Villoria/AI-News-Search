FROM python:3.12-slim

WORKDIR /app

# Install system deps for psycopg2 and lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download ML models during build so startup is fast
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
RUN python -c "from transformers import AutoTokenizer, AutoModelForSeq2SeqLM; AutoTokenizer.from_pretrained('sshleifer/distilbart-cnn-12-6'); AutoModelForSeq2SeqLM.from_pretrained('sshleifer/distilbart-cnn-12-6')"
RUN python -m spacy download en_core_web_sm

COPY backend/ ./

EXPOSE 7860

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
