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
            detail="Each feed is parsed with feedparser, then full article text is extracted using newspaper3k with 8 parallel workers. Articles older than 7 days and those that have been crawled in previous runs are dropped before extraction to save bandwidth."
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
            icon={<Zap className="h-5 w-5" />}
            title="Named Entity Recognition (NER)"
            description="Extracts key entities (PERSON, ORG, GPE) using spaCy's en_core_web_sm model from the cleaned article text."
            detail="Entities are stored as tags, allowing us to identify the main actors in every story (e.g., 'Sam Altman', 'Google', 'NVIDIA') and use them for topic labeling."
          />
          <StepArrow />
          <PipelineStep
            number={4}
            icon={<Brain className="h-5 w-5" />}
            title="Embed & Cluster"
            description="Articles are converted into 384-dim vectors with MiniLM-L6-v2 and grouped into clusters using scikit-learn's K-Means."
            detail="Clustering groups semantically similar stories into 'Trending Topics'. Topics are dynamically labeled by looking at the most frequent entities inside each cluster."
          />
          <StepArrow />
          <PipelineStep
            number={5}
            icon={<Database className="h-5 w-5" />}
            title="Store in PostgreSQL + pgvector"
            description="Normalized embeddings and topic associations are stored in PostgreSQL using the pgvector extension with an HNSW index."
            detail="The system supports both vector searching (for queries) and relational filtering (for topic chips), combined into a single performant pipeline."
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
              description="Exponential freshness score: 2^(-hours / 48). Rewards recent news while slightly penalizing older evergreen content."
            />
            <SignalRow
              icon={<BarChart3 className="h-4 w-4" />}
              name="Keyword Density"
              weight="30%"
              description="Ratio of distinct AI keywords found in the article. Gives a bonus to articles deeply focused on specialist AI topics."
            />
          </div>
        </div>
      </div>


      {/* Tech stack */}
      <div className="mb-16">
        <h3 className="mb-6 text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Tech Stack
        </h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <TechItem label="NER" value="spaCy (en_core_web_sm)" />
          <TechItem label="Clustering" value="scikit-learn (K-Means)" />
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
            <div className="flex w-full max-w-md gap-3">
              <div className="flex-1 rounded-lg border border-border bg-secondary/30 p-2 text-center text-[10px]">
                <Filter className="mx-auto mb-1 h-3 w-3" />
                AI Keyword Filter
              </div>
              <div className="flex-1 rounded-lg border border-border bg-secondary/30 p-2 text-center text-[10px]">
                <Zap className="mx-auto mb-1 h-3 w-3" />
                NER Extraction
              </div>
              <div className="flex-1 rounded-lg border border-border bg-secondary/30 p-2 text-center text-[10px]">
                <Brain className="mx-auto mb-1 h-3 w-3" />
                K-Means Clustering
              </div>
            </div>
            <ArrowDown className="h-4 w-4 text-muted-foreground" />
            <ArchBlock icon={<Database />} label="PostgreSQL + pgvector" sub="HNSW index, cosine similarity" />
            <ArrowDown className="h-4 w-4 text-muted-foreground" />
            <div className="flex w-full max-w-md gap-3">
              <div className="flex-1 rounded-lg border border-border bg-secondary/30 p-3 text-center">
                <Search className="mx-auto mb-1 h-4 w-4 text-muted-foreground" />
                <p className="text-xs font-medium">Composite Ranker</p>
                <p className="text-xs text-muted-foreground">semantic + filter</p>
              </div>
              <div className="flex-1 rounded-lg border border-border bg-secondary/30 p-3 text-center">
                <FileText className="mx-auto mb-1 h-4 w-4 text-muted-foreground" />
                <p className="text-xs font-medium">Summarizer</p>
                <p className="text-xs text-muted-foreground">DistilBART</p>
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
