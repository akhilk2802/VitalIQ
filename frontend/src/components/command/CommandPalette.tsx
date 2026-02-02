import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { queryApi } from '@/api'
import { cn } from '@/lib/utils'
import { NAV_ITEMS, NAV_ITEMS_SECONDARY, DATA_ENTRY_ITEMS } from '@/lib/constants'
import {
  Dialog,
  DialogContent,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Search,
  ArrowRight,
  LayoutDashboard,
  TrendingUp,
  Bell,
  GitBranch,
  Sun,
  Plug,
  Database,
  Settings,
  Utensils,
  Moon,
  Dumbbell,
  HeartPulse,
  Sparkles,
  Loader2,
  type LucideIcon,
} from 'lucide-react'

const iconMap: Record<string, LucideIcon> = {
  LayoutDashboard,
  TrendingUp,
  Bell,
  GitBranch,
  Sun,
  Plug,
  Database,
  Settings,
  Utensils,
  Moon,
  Dumbbell,
  HeartPulse,
}

interface CommandPaletteProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const navigate = useNavigate()

  // NL Query mutation
  const nlQuery = useMutation({
    mutationFn: (q: string) => queryApi.query({ query: q }),
  })

  const handleSelect = (path: string) => {
    navigate(path)
    onOpenChange(false)
    setQuery('')
  }

  const handleNLQuery = () => {
    if (query.trim().length > 3) {
      nlQuery.mutate(query)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && query.trim().length > 3) {
      e.preventDefault()
      handleNLQuery()
    }
  }

  // Keyboard shortcut
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        onOpenChange(!open)
      }
    }
    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [open, onOpenChange])

  // Filter navigation items
  const allNavItems = [...NAV_ITEMS, ...NAV_ITEMS_SECONDARY, ...DATA_ENTRY_ITEMS]
  const filteredItems = query
    ? allNavItems.filter((item) =>
        item.label.toLowerCase().includes(query.toLowerCase())
      )
    : allNavItems

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl gap-0 overflow-hidden p-0">
        {/* Search input */}
        <div className="flex items-center border-b px-4">
          <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              nlQuery.reset()
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search or ask a question..."
            className="border-0 bg-transparent px-3 py-4 text-base focus-visible:ring-0"
          />
          {nlQuery.isPending && (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          )}
        </div>

        <ScrollArea className="max-h-[60vh]">
          {/* NL Query Result */}
          {nlQuery.data && (
            <div className="border-b p-4">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium">AI Answer</span>
              </div>
              <p className="text-sm text-muted-foreground">
                {nlQuery.data.answer}
              </p>
              {nlQuery.data.follow_up_suggestions.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {nlQuery.data.follow_up_suggestions.slice(0, 3).map((suggestion, i) => (
                    <button
                      key={i}
                      onClick={() => {
                        setQuery(suggestion)
                        nlQuery.mutate(suggestion)
                      }}
                      className="rounded-full bg-muted px-3 py-1 text-xs hover:bg-accent"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Navigation items */}
          <div className="p-2">
            {query && !filteredItems.length && !nlQuery.data && (
              <div className="px-2 py-6 text-center text-sm text-muted-foreground">
                <p>No results found.</p>
                <p className="mt-1">Press Enter to ask AI</p>
              </div>
            )}

            {filteredItems.length > 0 && (
              <>
                <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
                  Navigation
                </div>
                {filteredItems.map((item) => {
                  const Icon = iconMap[item.icon] || ArrowRight
                  return (
                    <button
                      key={item.path}
                      onClick={() => handleSelect(item.path)}
                      className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm hover:bg-accent"
                    >
                      <Icon className="h-4 w-4 text-muted-foreground" />
                      <span>{item.label}</span>
                    </button>
                  )
                })}
              </>
            )}

            {!query && (
              <>
                <div className="mt-2 px-2 py-1.5 text-xs font-medium text-muted-foreground">
                  Quick Questions
                </div>
                {[
                  'How did I sleep this week?',
                  'What affects my heart rate?',
                  'Show me my exercise trends',
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => {
                      setQuery(q)
                      nlQuery.mutate(q)
                    }}
                    className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm hover:bg-accent"
                  >
                    <Sparkles className="h-4 w-4 text-primary" />
                    <span>{q}</span>
                  </button>
                ))}
              </>
            )}
          </div>
        </ScrollArea>

        {/* Footer */}
        <div className="flex items-center justify-between border-t px-4 py-2">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <kbd className="rounded border bg-muted px-1.5 py-0.5 font-mono">↵</kbd>
            <span>Select / Ask AI</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <kbd className="rounded border bg-muted px-1.5 py-0.5 font-mono">esc</kbd>
            <span>Close</span>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
