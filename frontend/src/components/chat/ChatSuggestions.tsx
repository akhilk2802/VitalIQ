import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

const suggestions = [
  'How did I sleep last week?',
  'What affects my HRV the most?',
  'Give me a summary of today',
  'Why was my heart rate high yesterday?',
  'Tips to improve my sleep',
  'What patterns do you see in my data?',
]

interface ChatSuggestionsProps {
  onSelect: (suggestion: string) => void
  className?: string
}

export function ChatSuggestions({ onSelect, className }: ChatSuggestionsProps) {
  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {suggestions.map((suggestion) => (
        <Button
          key={suggestion}
          variant="outline"
          size="sm"
          onClick={() => onSelect(suggestion)}
          className="text-xs"
        >
          {suggestion}
        </Button>
      ))}
    </div>
  )
}
