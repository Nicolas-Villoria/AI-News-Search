import useSWR from 'swr'
import useSWRMutation from 'swr/mutation'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Matches the FastAPI backend response field names exactly
interface Article {
  title: string
  link: string
  source: string
  published: string
  text?: string
  keyword_score?: number
  semantic_score?: number
  time_score?: number
  relevance_score?: number
}

interface SearchResponse {
  query: string
  total_results: number
  results: Article[]
}

interface HealthResponse {
  api_status: string
  index_loaded: boolean
  articles_count: number
  models_loaded: {
    embedding: boolean | string
    summarizer: boolean | string
  }
  pipeline_running: boolean
  pipeline_stats: {
    started_at?: string
    finished_at?: string
    total_seconds?: number
    status?: string
    crawl?: { articles: number; seconds: number }
    filter?: { input: number; output: number; pass_rate: number; seconds: number }
    index?: { vectors: number; avg_embed_seconds: number; seconds: number }
    feed_stats?: Array<{
      source: string
      url: string
      article_count: number
      status: string
      elapsed_seconds: number
      error: string | null
    }>
    source_distribution?: Array<{
      source: string
      count: number
      percentage: number
    }>
  } | null
}

interface SummarizeResponse {
  summary: string
}

const fetcher = async (url: string) => {
  const res = await fetch(url)
  if (!res.ok) throw new Error('API request failed')
  return res.json()
}

const searchFetcher = async (url: string, { arg }: { arg: { query: string; top_k?: number } }) => {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(arg),
  })
  if (!res.ok) throw new Error('Search failed')
  return res.json()
}

const summarizeFetcher = async (url: string, { arg }: { arg: { text: string; title?: string } }) => {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(arg),
  })
  if (!res.ok) throw new Error('Summarization failed')
  return res.json()
}

const pipelineFetcher = async (url: string) => {
  const res = await fetch(url, { method: 'POST' })
  if (!res.ok) throw new Error('Pipeline trigger failed')
  return res.json()
}

export function useHealth() {
  return useSWR<HealthResponse>(`${API_BASE}/health`, fetcher, {
    refreshInterval: 5000,
  })
}

export function useSearch() {
  return useSWRMutation<SearchResponse, Error, string, { query: string; top_k?: number }>(
    `${API_BASE}/search`,
    searchFetcher
  )
}

export function useSummarize() {
  return useSWRMutation<SummarizeResponse, Error, string, { text: string; title?: string }>(
    `${API_BASE}/summarize`,
    summarizeFetcher
  )
}

export function usePipelineRun() {
  return useSWRMutation(`${API_BASE}/pipeline/run`, pipelineFetcher)
}

export type { Article, SearchResponse, HealthResponse, SummarizeResponse }
