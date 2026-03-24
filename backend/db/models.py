"""
db/models.py — SQLAlchemy ORM models for AI News Search.

Tables:
    articles        — Crawled articles with text, metadata, and pgvector embeddings.
    entities        — Named entities extracted per article (ORG, PERSON, GPE, PRODUCT).
    topic_clusters  — Groups of related articles with auto-generated summaries.
    pipeline_runs   — Audit log of pipeline executions with timing stats.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Integer, Text, Float, Boolean, DateTime, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from db.database import Base
from config.settings import EMBEDDING_DIM


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    source: Mapped[str | None] = mapped_column(Text)
    published: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    body: Mapped[str | None] = mapped_column(Text)
    keyword_score: Mapped[float] = mapped_column(Float, default=0.0)
    embedding = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("topic_clusters.id"), nullable=True,
    )
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("articles.id"), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    entities: Mapped[list["Entity"]] = relationship(
        back_populates="article", cascade="all, delete-orphan",
    )
    cluster: Mapped["TopicCluster | None"] = relationship(back_populates="articles")

    __table_args__ = (
        Index("ix_articles_embedding_hnsw", embedding,
              postgresql_using="hnsw",
              postgresql_with={"m": 16, "ef_construction": 64},
              postgresql_ops={"embedding": "vector_cosine_ops"}),
    )


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=1)

    article: Mapped["Article"] = relationship(back_populates="entities")


class TopicCluster(Base):
    __tablename__ = "topic_clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    article_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    articles: Mapped[list["Article"]] = relationship(back_populates="cluster")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    status: Mapped[str] = mapped_column(Text, default="running")
    stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
