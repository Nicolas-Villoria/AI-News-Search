'use client'

import { useHealth } from '@/hooks/use-news-api'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import clsx from 'clsx'

export function Header() {
  const { data: health } = useHealth()
  const pathname = usePathname()
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <div className="flex items-center gap-8">
          <h1 className="font-serif text-2xl tracking-tight">Hawker</h1>
          <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
            <Link href="/" className={clsx('cursor-pointer transition-colors hover:text-foreground', pathname === '/' && 'text-foreground font-bold')} >Feed</Link>
            <Link href="/pipeline" className={clsx('cursor-pointer transition-colors hover:text-foreground', pathname === '/pipeline' && 'text-foreground font-bold')} >Pipeline</Link>
            <Link href="/how-it-works" className={clsx('cursor-pointer transition-colors hover:text-foreground', pathname === '/how-it-works' && 'text-foreground font-bold')} >How it works</Link>
          </nav>
        </div>
        
        <div className="flex items-center gap-4">
          {health && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className={`h-1.5 w-1.5 rounded-full ${health.index_loaded ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              <span className="hidden sm:inline">
                {health.articles_count.toLocaleString()} articles
              </span>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
