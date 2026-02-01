import { Button } from '@/components/ui/button'
import { MessageCircle } from 'lucide-react'

interface ChatFABProps {
  onClick: () => void
}

export function ChatFAB({ onClick }: ChatFABProps) {
  return (
    <Button
      onClick={onClick}
      size="lg"
      className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg z-40"
    >
      <MessageCircle className="h-6 w-6" />
      <span className="sr-only">Open chat</span>
    </Button>
  )
}
