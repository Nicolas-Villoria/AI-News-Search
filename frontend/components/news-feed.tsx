'use client'

import { useState, useCallback, useEffect } from 'react'
import { SearchBar } from './search-bar'
import { ArticleList } from './article-list'
import { StatusPanel } from './status-panel'
import { QuickFilters } from './quick-filters'
import { useSearch, useTopics, type Article } from '@/hooks/use-news-api'

export function NewsFeed() {
  const [articles, setArticles] = useState<Article[]>([])
  const [lastQuery, setLastQuery] = useState<string>('')
  const [selectedTopic, setSelectedTopic] = useState<number | null>(null)
  const [hasSearched, setHasSearched] = useState(false)
  const [isInitialLoad, setIsInitialLoad] = useState(true)
  const { trigger: search, isMutating: isSearching } = useSearch()
  const { data: topicsData } = useTopics()

  const handleSearch = useCallback(
    async (query: string, cluster_id?: number | null) => {
      try {
        const payload: { query: string; top_k: number; cluster_id?: number } = {
          query: query.trim(),
          top_k: 20
        }
        if (cluster_id) payload.cluster_id = cluster_id

        const result = await search(payload)
        setArticles(result.results)
        setLastQuery(query)
        setHasSearched(true)
        setIsInitialLoad(false)
        if (cluster_id !== undefined) {
          setSelectedTopic(cluster_id)
        }
      } catch {
        setArticles([])
        setHasSearched(true)
        setIsInitialLoad(false)
      }
    },
    [search]
  )

  // Fetch latest articles on mount
  useEffect(() => {
    handleSearch('')
  }, [handleSearch])

  return (
    <div className="min-h-screen">
      <div className="mx-auto max-w-6xl px-4 py-8 md:py-12">
        <div className="grid gap-8">
          {/* Main Content */}
          <main>
            <div className="mb-8">
              <h2 className="mb-2 font-serif text-4xl tracking-tight md:text-5xl">
                Discover what matters
              </h2>
              <p className="text-lg text-muted-foreground">
                AI-powered hub for AI news and insights
              </p>
            </div>

            <div className="mb-6">
              <SearchBar onSearch={handleSearch} isLoading={isSearching} />
            </div>

            <div className="mb-8">
              <p className="mb-3 text-sm text-muted-foreground">Popular shortcuts</p>
              <QuickFilters onSelect={handleSearch} />
            </div>

            {hasSearched && (
              <div className="mb-6 flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  {selectedTopic && topicsData?.topics && (
                    <span> in <span className="font-medium text-foreground">
                      {topicsData.topics.find(t => t.id === selectedTopic)?.label}
                    </span></span>
                  )}
                </p>
                {articles.length > 0 && (
                  <button
                    onClick={() => {
                      setHasSearched(false)
                    }}
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    Clear results
                  </button>
                )}
              </div>
            )}

            {isSearching && articles.length === 0 ? (
              <div className="flex justify-center py-20">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
              </div>
            ) : articles.length > 0 ? (
              <ArticleList articles={articles} query={lastQuery} />
            ) : !isInitialLoad && (
              <div className="rounded-xl border border-dashed border-border bg-card/50 p-12 text-center">
                <p className="font-serif text-xl text-muted-foreground">
                  No articles found. Try a different query.
                </p>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  )
}
