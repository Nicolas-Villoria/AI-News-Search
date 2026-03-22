'use client'

import { ArticleCard } from './article-card'
import type { Article } from '@/hooks/use-news-api'

interface ArticleListProps {
  articles: Article[]
  query?: string
}

export function ArticleList({ articles, query }: ArticleListProps) {
  if (articles.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <p className="text-lg text-muted-foreground">
          {query ? `No results found for "${query}"` : 'No articles available'}
        </p>
        <p className="mt-2 text-sm text-muted-foreground/70">
          Try a different search term or check back later
        </p>
      </div>
    )
  }

  return (
    <div className="divide-y divide-border">
      {articles.map((article, index) => (
        <ArticleCard 
          key={`${article.link}-${index}`} 
          article={article} 
          index={index}
        />
      ))}
    </div>
  )
}
