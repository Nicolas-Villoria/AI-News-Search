'use client'

import { useState } from 'react'
import { ArrowUpRight, Sparkles, ChevronDown, ChevronUp } from 'lucide-react'
import { useSummarize, type Article } from '@/hooks/use-news-api'
import { formatDistanceToNow } from 'date-fns'

interface ArticleCardProps {
  article: Article
  index: number
}

export function ArticleCard({ article, index }: ArticleCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [summary, setSummary] = useState<string | null>(null)
  const { trigger: summarize, isMutating: isSummarizing } = useSummarize()

  const handleSummarize = async () => {
    if (summary) {
      setExpanded(!expanded)
      return
    }
    
    if (article.text) {
      try {
        const result = await summarize({ text: article.text, title: article.title })
        setSummary(result.summary)
        setExpanded(true)
      } catch {
        // Handle error silently
      }
    }
  }

  const formattedDate = article.published
    ? formatDistanceToNow(new Date(article.published), { addSuffix: true })
    : null

  return (
    <article 
      className="group border-b border-border py-6 transition-colors first:pt-0 last:border-0"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex items-center gap-3 text-xs text-muted-foreground">
            {formattedDate && (
              <time className="uppercase tracking-wider">{formattedDate}</time>
            )}
            {article.source && (
              <>
                <span className="text-border">·</span>
                <span className="font-medium text-foreground/70">{article.source}</span>
              </>
            )}
            {article.relevance_score !== undefined && (
              <>
                <span className="text-border">·</span>
                <span className="text-accent">{Math.round(article.relevance_score * 100)}% match</span>
              </>
            )}
          </div>
          
          <h3 className="mb-2 font-serif text-xl leading-snug text-foreground transition-colors group-hover:text-accent md:text-2xl">
            <a
              href={article.link}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-start gap-2"
            >
              <span className="text-balance">{article.title}</span>
              <ArrowUpRight className="mt-1 h-4 w-4 flex-shrink-0 opacity-0 transition-opacity group-hover:opacity-100" />
            </a>
          </h3>

          {article.text && (
            <button
              onClick={handleSummarize}
              disabled={isSummarizing}
              className="mt-3 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span>{summary ? 'AI Summary' : 'Generate summary'}</span>
              {summary && (
                expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />
              )}
              {isSummarizing && (
                <div className="ml-1 h-3 w-3 animate-spin rounded-full border border-current border-t-transparent" />
              )}
            </button>
          )}

          {expanded && summary && (
            <div className="mt-3 rounded-lg bg-secondary/50 p-4 text-sm leading-relaxed text-foreground/80">
              {summary}
            </div>
          )}
        </div>
      </div>
    </article>
  )
}
