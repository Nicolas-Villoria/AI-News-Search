'use client'

const SUGGESTED_TOPICS = [
  'Technology',
  'AI & Machine Learning',
  'Climate',
  'Finance',
  'Politics',
  'Science',
  'Health',
  'Sports',
]

interface QuickFiltersProps {
  onSelect: (topic: string) => void
}

export function QuickFilters({ onSelect }: QuickFiltersProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {SUGGESTED_TOPICS.map((topic) => (
        <button
          key={topic}
          onClick={() => onSelect(topic)}
          className="rounded-full border border-border bg-card px-4 py-2 text-sm text-muted-foreground transition-all hover:border-accent hover:text-foreground"
        >
          {topic}
        </button>
      ))}
    </div>
  )
}
