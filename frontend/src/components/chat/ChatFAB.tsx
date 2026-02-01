import { useState } from 'react'
import { MessageCircle, Sparkles, X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatFABProps {
  onClick: () => void
  isOpen?: boolean
  className?: string
}

export function ChatFAB({ onClick, isOpen = false, className }: ChatFABProps) {
  const [isHovered, setIsHovered] = useState(false)

  return (
    <div
      className={cn(
        'fixed z-50',
        'sm:bottom-6 sm:right-6 bottom-6 right-4',
        className
      )}
    >
      {/* Tooltip */}
      <div
        className={cn(
          'absolute right-full mr-3 top-1/2 -translate-y-1/2',
          'whitespace-nowrap rounded-lg px-3 py-2',
          'bg-card text-card-foreground text-sm font-medium',
          'shadow-xl border border-border',
          'transition-all duration-200',
          isHovered && !isOpen
            ? 'opacity-100 translate-x-0'
            : 'opacity-0 translate-x-2 pointer-events-none'
        )}
      >
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <span>AI Health Assistant</span>
        </div>
      </div>

      {/* Animated rings (only when closed) */}
      {!isOpen && (
        <>
          <span className="absolute inset-0 rounded-full bg-blue-500/20 animate-ping" />
          <span className="absolute -inset-1 rounded-full bg-gradient-to-r from-blue-500/20 to-cyan-500/20 blur-sm animate-pulse" />
        </>
      )}

      {/* Main button */}
      <button
        onClick={onClick}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={cn(
          'relative flex items-center justify-center',
          'h-14 w-14 rounded-full',
          // Gradient background - blue to cyan
          'bg-gradient-to-br from-blue-500 via-blue-600 to-cyan-600',
          // Shadow and glow
          'shadow-lg shadow-blue-500/25',
          'hover:shadow-xl hover:shadow-blue-500/40',
          // Transitions
          'transition-all duration-300 ease-out',
          'hover:scale-110 active:scale-95',
          // Focus states
          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-background',
        )}
        aria-label={isOpen ? 'Close chat' : 'Open chat'}
      >
        {/* Shine overlay */}
        <div className="absolute inset-0 rounded-full overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-t from-transparent via-white/5 to-white/20" />
          <div className="absolute top-0 left-1/4 right-1/4 h-px bg-gradient-to-r from-transparent via-white/50 to-transparent" />
        </div>
        
        {/* Icon */}
        <div className={cn(
          'relative text-white transition-transform duration-300',
          isOpen && 'rotate-90'
        )}>
          {isOpen ? (
            <X className="h-6 w-6" />
          ) : (
            <div className="relative">
              <MessageCircle className="h-6 w-6" />
              {/* AI sparkle badge */}
              <span className="absolute -top-1.5 -right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 shadow-sm">
                <Sparkles className="h-2.5 w-2.5 text-white" />
              </span>
            </div>
          )}
        </div>
      </button>
    </div>
  )
}
