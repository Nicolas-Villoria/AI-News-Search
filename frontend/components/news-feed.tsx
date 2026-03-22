'use client'

import { useState, useCallback } from 'react'
import { SearchBar } from './search-bar'
import { ArticleList } from './article-list'
import { StatusPanel } from './status-panel'
import { QuickFilters } from './quick-filters'
import { useSearch, type Article } from '@/hooks/use-news-api'

export function NewsFeed() {
  const [articles, setArticles] = useState<Article[]>([])
  const [lastQuery, setLastQuery] = useState<string>('')
  const [hasSearched, setHasSearched] = useState(false)
  const { trigger: search, isMutating: isSearching } = useSearch()

  const handleSearch = useCallback(
    async (query: string) => {
      try {
        const result = await search({ query, top_k: 20 })
        setArticles(result.results)
        setLastQuery(query)
        setHasSearched(true)
      } catch {
        setArticles([])
        setHasSearched(true)
      }
    },
    [search]
  )

  return (
    <div className="min-h-screen">
      <div className="mx-auto max-w-6xl px-4 py-8 md:py-12">
        <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
          {/* Main Content */}
          <main>
            <div className="mb-8">
              <h2 className="mb-2 font-serif text-4xl tracking-tight md:text-5xl">
                Discover what matters
              </h2>
              <p className="text-lg text-muted-foreground">
                AI-powered semantic search across thousands of articles
              </p>
            </div>

            <div className="mb-6">
              <SearchBar onSearch={handleSearch} isLoading={isSearching} />
            </div>

            {!hasSearched && (
              <div className="mb-8">
                <p className="mb-3 text-sm text-muted-foreground">Popular topics</p>
                <QuickFilters onSelect={handleSearch} />
              </div>
            )}

            {hasSearched && (
              <div className="mb-6 flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  {articles.length} results for <span className="font-medium text-foreground">"{lastQuery}"</span>
                </p>
                {articles.length > 0 && (
                  <button
                    onClick={() => {
                      setHasSearched(false)
                      setArticles([])
                      setLastQuery('')
                    }}
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    Clear results
                  </button>
                )}
              </div>
            )}

            {hasSearched ? (
              <ArticleList articles={articles} query={lastQuery} />
            ) : (
              <div className="rounded-xl border border-dashed border-border bg-card/50 p-12 text-center">
                <p className="font-serif text-xl text-muted-foreground">
                  Enter a search query or select a topic to begin
                </p>
              </div>
            )}
          </main>

          {/* Sidebar */}
          <aside className="hidden lg:block">
            <div className="sticky top-24">
              <StatusPanel />
              
              <div className="mt-6 rounded-xl border border-border bg-card p-5">
                <h3 className="mb-3 text-sm font-medium text-foreground">How it works</h3>
                <ul className="space-y-3 text-sm text-muted-foreground">
                  <li className="flex items-start gap-2">
                    <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-medium text-secondary-foreground">1</span>
                    <span>Search uses semantic understanding, not just keywords</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-medium text-secondary-foreground">2</span>
                    <span>Results are ranked by relevance, freshness, and quality</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-medium text-secondary-foreground">3</span>
                    <span>Generate AI summaries for quick reading</span>
                  </li>
                </ul>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  )
}
