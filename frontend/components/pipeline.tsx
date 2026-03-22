'use client'

import { useHealth, usePipelineRun } from '@/hooks/use-news-api'
import { formatDistanceToNow } from 'date-fns'
import {
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Database,
  Filter,
  Cpu,
  Rss,
  Timer,
  Activity,
} from 'lucide-react'

export function Pipeline() {
  const { data: health, mutate } = useHealth()
  const { trigger: runPipeline, isMutating: isRunning } = usePipelineRun()

  const handleRefresh = async () => {
    try {
      await runPipeline()
      const poll = setInterval(() => mutate(), 2000)
      setTimeout(() => clearInterval(poll), 120000)
    } catch {
      // silently handle
    }
  }

  if (!health) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-12">
        <p className="text-muted-foreground">Connecting to API...</p>
      </div>
    )
  }

  const ps = health.pipeline_stats
  const feeds = ps?.feed_stats ?? []
  const successCount = feeds.filter((f) => f.status === 'success').length
  const failCount = feeds.length - successCount

  const lastRun = ps?.finished_at
    ? formatDistanceToNow(new Date(ps.finished_at), { addSuffix: true })
    : 'Never'

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 md:py-12">
      {/* Header */}
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h2 className="mb-2 font-serif text-4xl tracking-tight md:text-5xl">
            Pipeline Health
          </h2>
          <p className="text-lg text-muted-foreground">
            Monitor the data ingestion pipeline — crawl, filter, embed, index
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isRunning || health.pipeline_running}
          className="flex items-center gap-2 rounded-lg bg-foreground px-4 py-2.5 text-sm font-medium text-background transition-colors hover:bg-foreground/90 disabled:opacity-50"
        >
          <RefreshCw
            className={`h-4 w-4 ${isRunning || health.pipeline_running ? 'animate-spin' : ''}`}
          />
          {health.pipeline_running ? 'Running...' : 'Run Pipeline'}
        </button>
      </div>

      {!ps ? (
        <div className="rounded-xl border border-dashed border-border bg-card/50 p-12 text-center">
          <p className="font-serif text-xl text-muted-foreground">
            No pipeline has been run yet. Click &quot;Run Pipeline&quot; to start.
          </p>
        </div>
      ) : (
        <>
          {/* Top metrics */}
          <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              icon={<Database className="h-5 w-5" />}
              label="Articles Crawled"
              value={ps.crawl?.articles.toLocaleString() ?? '—'}
            />
            <MetricCard
              icon={<Filter className="h-5 w-5" />}
              label="After AI Filter"
              value={ps.filter?.output.toLocaleString() ?? '—'}
              sub={ps.filter ? `${(ps.filter.pass_rate * 100).toFixed(0)}% pass rate` : undefined}
            />
            <MetricCard
              icon={<Cpu className="h-5 w-5" />}
              label="Vectors Indexed"
              value={ps.index?.vectors.toLocaleString() ?? '—'}
            />
            <MetricCard
              icon={<Timer className="h-5 w-5" />}
              label="Total Duration"
              value={ps.total_seconds ? `${ps.total_seconds}s` : '—'}
              sub={`Last run ${lastRun}`}
            />
          </div>

          {/* Stage timing */}
          <div className="mb-8">
            <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-muted-foreground">
              Stage Breakdown
            </h3>
            <div className="grid gap-4 sm:grid-cols-3">
              <StageCard
                title="Crawl"
                icon={<Rss className="h-4 w-4" />}
                time={ps.crawl?.seconds}
                detail={`${ps.crawl?.articles ?? 0} articles from ${feeds.length} feeds`}
              />
              <StageCard
                title="Filter"
                icon={<Filter className="h-4 w-4" />}
                time={ps.filter?.seconds}
                detail={`${ps.filter?.input ?? 0} → ${ps.filter?.output ?? 0} articles`}
              />
              <StageCard
                title="Embed + Index"
                icon={<Cpu className="h-4 w-4" />}
                time={ps.index?.seconds}
                detail={
                  ps.index
                    ? `${ps.index.vectors} vectors · ${ps.index.avg_embed_seconds.toFixed(3)}s avg`
                    : ''
                }
              />
            </div>
          </div>

          {/* Feed health table */}
          <div>
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
                Feed Health
              </h3>
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  {successCount} succeeded
                </span>
                {failCount > 0 && (
                  <span className="flex items-center gap-1.5">
                    <XCircle className="h-3.5 w-3.5 text-red-500" />
                    {failCount} failed
                  </span>
                )}
              </div>
            </div>

            <div className="overflow-hidden rounded-xl border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-secondary/50">
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Source</th>
                    <th className="px-4 py-3 text-right font-medium text-muted-foreground">Articles</th>
                    <th className="px-4 py-3 text-center font-medium text-muted-foreground">Status</th>
                    <th className="px-4 py-3 text-right font-medium text-muted-foreground">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {[...feeds]
                    .sort((a, b) => b.article_count - a.article_count)
                    .map((feed, i) => (
                      <tr
                        key={feed.url}
                        className={i % 2 === 0 ? 'bg-card' : 'bg-card/50'}
                      >
                        <td className="max-w-[300px] truncate px-4 py-3 text-foreground">
                          {feed.source}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums text-foreground">
                          {feed.article_count.toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {feed.status === 'success' ? (
                            <CheckCircle2 className="mx-auto h-4 w-4 text-emerald-500" />
                          ) : (
                            <span title={feed.error ?? ''}>
                              <XCircle className="mx-auto h-4 w-4 text-red-500" />
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">
                          {feed.elapsed_seconds}s
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Run info footer */}
          <div className="mt-8 flex items-center gap-6 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5" />
              Status: <strong className="text-foreground">{ps.status}</strong>
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5" />
              Started: {ps.started_at ? new Date(ps.started_at).toLocaleString() : '—'}
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5" />
              Finished: {ps.finished_at ? new Date(ps.finished_at).toLocaleString() : '—'}
            </span>
          </div>
        </>
      )}
    </div>
  )
}

function MetricCard({
  icon,
  label,
  value,
  sub,
}: {
  icon: React.ReactNode
  label: string
  value: string
  sub?: string
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-3 flex items-center gap-2 text-muted-foreground">
        {icon}
        <span className="text-sm">{label}</span>
      </div>
      <p className="text-3xl font-semibold tabular-nums text-foreground">{value}</p>
      {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
    </div>
  )
}

function StageCard({
  title,
  icon,
  time,
  detail,
}: {
  title: string
  icon: React.ReactNode
  time?: number
  detail: string
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-foreground">
          {icon}
          {title}
        </div>
        <span className="text-2xl font-semibold tabular-nums text-foreground">
          {time != null ? `${time}s` : '—'}
        </span>
      </div>
      <p className="text-xs text-muted-foreground">{detail}</p>
    </div>
  )
}
