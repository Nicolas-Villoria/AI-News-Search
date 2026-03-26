"""
engine/topic_engine.py — Intelligence layer for Entities and Topics.

Handles:
1. NER (Named Entity Recognition) using spaCy to extract key people/orgs.
2. Clustering using scikit-learn K-Means on pgvector embeddings.
"""

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session
from sklearn.cluster import KMeans
import numpy as np

from db.models import Article, Entity, TopicCluster
from utils.helpers import get_logger

logger = get_logger(__name__)

# Lazy-loaded spaCy model (small English model)
_nlp = None


def get_nlp():
    """Load the spaCy NER model lazily."""
    global _nlp
    if _nlp is None:
        import spacy
        logger.info("Loading spaCy NER model (en_core_web_sm)...")
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def extract_entities_from_text(text: str, max_entities: int = 6) -> list[dict]:
    """
    Extracts high-value named entities (ORG, PERSON, PRODUCT) from text.
    Returns a list of dicts: [{"name": "OpenAI", "label": "ORG", "count": 2}, ...]
    """
    if not text:
        return []

    nlp = get_nlp()
    # Process up to 5000 chars to save time (we just need the main topics)
    doc = nlp(text[:5000])

    # Filter to interesting entity types
    ALLOWED_LABELS = {"ORG", "PERSON", "PRODUCT", "GPE"}
    
    # Clean and count entities
    entity_counts = Counter()
    entity_labels = {}

    for ent in doc.ents:
        if ent.label_ in ALLOWED_LABELS:
            name = ent.text.strip()
            # Basic cleanup (e.g., remove leading "The ")
            if name.lower().startswith("the "):
                name = name[4:]
            
            # Avoid single character junk or massive sentences
            if 1 < len(name) < 40:
                entity_counts[name] += 1
                # Save the mapping of name to label
                if name not in entity_labels:
                    entity_labels[name] = ent.label_

    # Return the top N most frequent entities
    results = []
    for name, count in entity_counts.most_common(max_entities):
        results.append({
            "name": name,
            "label": entity_labels[name],
            "count": count
        })

    return results


def process_article_entities(db: Session, article: Article):
    """Run NER on an article's text and save to the entities table."""
    text_to_process = f"{article.title}. {article.body or ''}"
    extracted = extract_entities_from_text(text_to_process)
    
    for ent_data in extracted:
        entity = Entity(
            article_id=article.id,
            name=ent_data["name"],
            label=ent_data["label"],
            count=ent_data["count"]
        )
        db.add(entity)


def generate_topic_label(cluster_articles: list[Article]) -> str:
    """Guess a topic name based on the most common entities across its articles."""
    global_counts = Counter()
    for auth in cluster_articles:
        for ent in auth.entities:
            # Weight the entity by how many times it appeared in the article
            global_counts[ent.name] += ent.count

    if not global_counts:
        return "General Tech News"
        
    # Pick the top 2 highest scoring named entities to form a label
    top_entities = [name for name, _ in global_counts.most_common(2)]
    return " & ".join(top_entities)


def cluster_recent_articles(db: Session, n_clusters: int = 8):
    """
    Groups recent articles into topics using K-Means clustering on their embeddings.
    Updates the TopicCluster table and assigns Article.cluster_id.
    """
    logger.info("Starting article clustering...")
    
    # 1. Fetch all articles that have embeddings but no cluster, or recent articles
    # For simplicity, we'll re-cluster everything in the DB if it's manageable (< 1000)
    # If the app grows, this should be limited to the last 7 days.
    articles = db.scalars(
        select(Article).where(Article.embedding.is_not(None))
    ).all()
    
    if len(articles) < n_clusters:
        logger.warning(f"Not enough articles to cluster. Have {len(articles)}, need {n_clusters}")
        return

    # Extract raw numpy arrays
    embeddings = np.array([a.embedding for a in articles])
    
    # 2. Run K-Means
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(embeddings)
    
    # 3. Wipe old TopicClusters and create new ones
    # (Because K-means regenerates completely new groupings)
    # Note: If we had a persistent "Trend" tracking, we'd use incremental clustering
    db.query(TopicCluster).delete()
    db.commit()
    
    # 4. Group articles by their new cluster label
    clusters_map = {i: [] for i in range(n_clusters)}
    for article, cluster_idx in zip(articles, labels):
        clusters_map[cluster_idx].append(article)
        
    # 5. Create TopicCluster records and update articles
    for cluster_idx, cluster_articles in clusters_map.items():
        if not cluster_articles:
            continue
            
        topic_name = generate_topic_label(cluster_articles)

        if topic_name == "General Tech News":
            # check if there is already a general tech news cluster
            existing_general_cluster = db.scalars(
                    select(TopicCluster).where(TopicCluster.label == "General Tech News")
                ).first()
            if existing_general_cluster:
                existing_general_cluster.article_count += len(cluster_articles)
                existing_general_cluster.summary += f"\n\n{len(cluster_articles)} new articles about General Tech News."
                db.add(existing_general_cluster)
                db.flush()
                topic_id = existing_general_cluster.id
        else:
            # Create topic
            topic = TopicCluster(
                label=topic_name,
                article_count=len(cluster_articles),
                summary=f"A collection of {len(cluster_articles)} articles about {topic_name}."
            )
            db.add(topic)
            db.flush() # get topic.id
            topic_id = topic.id
        
        # Update articles with the new FK
        for article in cluster_articles:
            article.cluster_id = topic_id

    db.commit()
    logger.info(f"Successfully generated {n_clusters} topic clusters.")
