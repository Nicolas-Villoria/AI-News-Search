'use client'

import {
  Rss,
  Filter,
  Brain,
  Search,
  FileText,
  ArrowDown,
  Database,
  Zap,
  BarChart3,
  Globe,
} from 'lucide-react'
import { useHealth } from '@/hooks/use-news-api'

export function HowItWorks() {
  const { data: health } = useHealth()
  const feedCount = health?.pipeline_stats?.feed_stats?.length ?? 24

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 md:py-12">
      {/* Hero */}
      <div className="mb-12">
        <h2 className="mb-3 font-serif text-4xl tracking-tight md:text-5xl">
          How it works
        </h2>
        <p className="text-lg leading-relaxed text-muted-foreground">
          Hawker is an AI-powered news search engine that crawls RSS feeds, filters for AI-related
          content, embeds articles into vector space, and ranks results using a composite of
          semantic similarity, freshness, and keyword density.
        </p>
      </div>

      {/* Pipeline stages */}
      <div className="mb-16">
        <h3 className="mb-6 text-sm font-medium uppercase tracking-wider text-muted-foreground">
          The Pipeline
        </h3>
        <div className="space-y-2">
          <PipelineStep
            number={1}
            icon={<Rss className="h-5 w-5" />}
            title="Crawl RSS Feeds"
            description={`Fetches articles from ${feedCount} curated RSS feeds spanning research labs (OpenAI, DeepMind, Meta AI), developer blogs (Hugging Face, PyTorch), AI newsletters, and tech publications (TechCrunch, MIT News, Wired).`}
            detail="Each feed is parsed with feedparser, then full article text is extracted using newspaper3k with 8 parallel workers. Articles older than 7 days are dropped before extraction to save bandwidth."
          />
          <StepArrow />
          <PipelineStep
            number={2}
            icon={<Filter className="h-5 w-5" />}
            title="AI Keyword Filter"
            description="Each article is scored against a curated list of ~50 AI-related terms (machine learning, LLM, transformer, computer vision, etc.). Articles matching at least one keyword pass through."
            detail="The keyword score — ratio of distinct matched terms to total terms — is saved and later used as one of three ranking signals. Typical pass rate is ~70%."
          />
          <StepArrow />
          <PipelineStep
            number={3}
            icon={<Brain className="h-5 w-5" />}
            title="Embed with MiniLM-L6-v2"
            description="Each article's title + first 500 characters are encoded into a 384-dimensional dense vector using the all-MiniLM-L6-v2 sentence transformer."
            detail="These embeddings capture semantic meaning, so 'large language model' and 'GPT-4 architecture' are close in vector space even though they share no words. Vectors are L2-normalized so inner product equals cosine similarity."
          />
          <StepArrow />
          <PipelineStep
            number={4}
            icon={<Database className="h-5 w-5" />}
            title="Store in PostgreSQL + pgvector"
            description="Normalized embeddings are stored alongside article metadata in PostgreSQL using the pgvector extension with an HNSW index for fast cosine similarity search."
            detail="pgvector handles both storage and search in a single system. The HNSW index provides sub-millisecond approximate nearest-neighbor search that scales to millions of vectors."
          />
        </div>
      </div>

      {/* Ranking formula */}
      <div className="mb-16">
        <h3 className="mb-6 text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Composite Ranking
        </h3>
        <div className="rounded-xl border border-border bg-card p-6">
          <p className="mb-4 font-mono text-sm text-foreground">
            score = 0.50 x semantic_sim + 0.20 x time_decay + 0.30 x keyword_score
          </p>
          <div className="space-y-4">
            <SignalRow
              icon={<Search className="h-4 w-4" />}
              name="Semantic Similarity"
              weight="50%"
              description="Cosine similarity between the query embedding and the article embedding. Captures meaning, not just keyword overlap."
            />
            <SignalRow
              icon={<Zap className="h-4 w-4" />}
              name="Time Decay"
              weight="20%"
              description="Exponential freshness score: 2^(-hours / 48). A 24h-old article scores ~0.71, 48h → 0.50, 1 week → 0.04. Rewards recent news."
            />
            <SignalRow
              icon={<BarChart3 className="h-4 w-4" />}
              name="Keyword Density"
              weight="30%"
              description="Ratio of distinct AI keywords found in the article. Gives a bonus to articles deeply focused on AI topics."
            />
          </div>
          <p className="mt-4 text-sm text-muted-foreground">
            Pure semantic search favors evergreen content. Pure recency ignores relevance.
            The weighted blend rewards articles that are both relevant and fresh.
          </p>
        </div>
      </div>


      {/* Tech stack */}
      <div className="mb-16">
        <h3 className="mb-6 text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Tech Stack
        </h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <TechItem label="Embeddings" value="sentence-transformers (MiniLM-L6-v2, 384-dim)" />
          <TechItem label="Vector Search" value="PostgreSQL + pgvector (HNSW cosine index)" />
          <TechItem label="RSS Parsing" value="feedparser + newspaper3k" />
          <TechItem label="Summarization" value="DistilBART-CNN-12-6 (abstractive, on-demand)" />
          <TechItem label="API" value="FastAPI + Uvicorn" />
          <TechItem label="Frontend" value="Next.js + Tailwind CSS" />
          <TechItem label="Database" value="PostgreSQL + pgvector (Supabase)" />
          <TechItem label="Language" value="Python 3.12 (backend) + TypeScript (frontend)" />
        </div>
      </div>

      {/* Architecture */}
      <div>
        <h3 className="mb-6 text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Architecture
        </h3>
        <div className="rounded-xl border border-border bg-card p-6">
          <div className="flex flex-col items-center gap-3 text-sm">
            <ArchBlock icon={<Globe />} label={`${feedCount} RSS Feeds`} sub="feedparser + newspaper3k" />
            <ArrowDown className="h-4 w-4 text-muted-foreground" />
            <ArchBlock icon={<Filter />} label="AI Keyword Filter" sub="~50 terms, ~70% pass rate" />
            <ArrowDown className="h-4 w-4 text-muted-foreground" />
            <ArchBlock icon={<Brain />} label="Sentence Embeddings" sub="MiniLM-L6-v2, 384-dim vectors" />
            <ArrowDown className="h-4 w-4 text-muted-foreground" />
            <ArchBlock icon={<Database />} label="PostgreSQL + pgvector" sub="HNSW index, cosine similarity" />
            <ArrowDown className="h-4 w-4 text-muted-foreground" />
            <div className="flex w-full max-w-md gap-3">
              <div className="flex-1 rounded-lg border border-border bg-secondary/30 p-3 text-center">
                <Search className="mx-auto mb-1 h-4 w-4 text-muted-foreground" />
                <p className="text-xs font-medium">Composite Ranker</p>
                <p className="text-xs text-muted-foreground">semantic + time + keyword</p>
              </div>
              <div className="flex-1 rounded-lg border border-border bg-secondary/30 p-3 text-center">
                <FileText className="mx-auto mb-1 h-4 w-4 text-muted-foreground" />
                <p className="text-xs font-medium">Summarizer</p>
                <p className="text-xs text-muted-foreground">DistilBART, on-demand</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function PipelineStep({
  number,
  icon,
  title,
  description,
  detail,
}: {
  number: number
  icon: React.ReactNode
  title: string
  description: string
  detail: string
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-3 flex items-center gap-3">
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-foreground text-sm font-semibold text-background">
          {number}
        </span>
        <div className="flex items-center gap-2 text-foreground">
          {icon}
          <h4 className="font-medium">{title}</h4>
        </div>
      </div>
      <p className="mb-2 text-sm leading-relaxed text-foreground/90">{description}</p>
      <p className="text-xs leading-relaxed text-muted-foreground">{detail}</p>
    </div>
  )
}

function StepArrow() {
  return (
    <div className="flex justify-center py-1">
      <ArrowDown className="h-4 w-4 text-muted-foreground/50" />
    </div>
  )
}

function SignalRow({
  icon,
  name,
  weight,
  description,
}: {
  icon: React.ReactNode
  name: string
  weight: string
  description: string
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary text-secondary-foreground">
        {icon}
      </div>
      <div className="flex-1">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-medium text-foreground">{name}</span>
          <span className="rounded-md bg-secondary px-1.5 py-0.5 text-xs font-medium text-secondary-foreground">
            {weight}
          </span>
        </div>
        <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
      </div>
    </div>
  )
}

function TechItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card/50 px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-sm text-foreground">{value}</p>
    </div>
  )
}

function ArchBlock({
  icon,
  label,
  sub,
}: {
  icon: React.ReactNode
  label: string
  sub: string
}) {
  return (
    <div className="flex w-full max-w-md items-center gap-3 rounded-lg border border-border bg-secondary/30 p-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary text-secondary-foreground">
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="text-xs text-muted-foreground">{sub}</p>
      </div>
    </div>
  )
}
