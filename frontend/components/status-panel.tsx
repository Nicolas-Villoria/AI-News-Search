'use client'

import { RefreshCw, Database, Cpu, Clock } from 'lucide-react'
import { useHealth, usePipelineRun } from '@/hooks/use-news-api'
import { formatDistanceToNow } from 'date-fns'

export function StatusPanel() {
  const { data: health, mutate } = useHealth()
  const { trigger: runPipeline, isMutating: isRunning } = usePipelineRun()

  const handleRefresh = async () => {
    try {
      await runPipeline()
      const poll = setInterval(() => {
        mutate()
      }, 2000)
      setTimeout(() => clearInterval(poll), 60000)
    } catch {
      // Handle error silently
    }
  }

  if (!health) return null

  const lastRun = health.pipeline_stats?.finished_at
    ? formatDistanceToNow(new Date(health.pipeline_stats.finished_at), { addSuffix: true })
    : 'Never'

  const modelsReady = !!health.models_loaded.embedding && !!health.models_loaded.summarizer

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground">System Status</h3>
        <button
          onClick={handleRefresh}
          disabled={isRunning || health.pipeline_running}
          className="flex items-center gap-1.5 rounded-lg bg-secondary px-3 py-1.5 text-xs font-medium text-secondary-foreground transition-colors hover:bg-secondary/80 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${(isRunning || health.pipeline_running) ? 'animate-spin' : ''}`} />
          {health.pipeline_running ? 'Refreshing...' : 'Refresh Index'}
        </button>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Database className="h-4 w-4" />
            <span>Articles Indexed</span>
          </div>
          <span className="font-medium text-foreground">
            {health.articles_count.toLocaleString()}
          </span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Cpu className="h-4 w-4" />
            <span>ML Models</span>
          </div>
          <span className={`font-medium ${modelsReady ? 'text-emerald-500' : 'text-amber-500'}`}>
            {modelsReady ? 'Ready' : 'Loading'}
          </span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>Last Updated</span>
          </div>
          <span className="font-medium text-foreground">{lastRun}</span>
        </div>
      </div>
    </div>
  )
}
