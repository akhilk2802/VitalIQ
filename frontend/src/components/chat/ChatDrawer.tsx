import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { chatApi } from '@/api'
import { cn } from '@/lib/utils'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { ChatMessage } from './ChatMessage'
import { ChatSuggestions } from './ChatSuggestions'
import {
  MessageCircle,
  Send,
  Loader2,
  Trash2,
  Plus,
  Sparkles,
} from 'lucide-react'
import type { ChatSession, ChatMessage as ChatMessageType } from '@/types'

interface ChatDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ChatDrawer({ open, onOpenChange }: ChatDrawerProps) {
  const [input, setInput] = useState('')
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()

  // Get sessions
  const { data: sessions, isLoading: sessionsLoading } = useQuery({
    queryKey: ['chat', 'sessions'],
    queryFn: () => chatApi.getSessions(true, 10),
    enabled: open,
  })

  // Get messages for active session
  const { data: messages, isLoading: messagesLoading } = useQuery({
    queryKey: ['chat', 'messages', activeSessionId],
    queryFn: () => chatApi.getMessages(activeSessionId!, 50),
    enabled: !!activeSessionId,
  })

  // Create new session
  const createSession = useMutation({
    mutationFn: () => chatApi.createSession(),
    onSuccess: (session) => {
      setActiveSessionId(session.id)
      queryClient.invalidateQueries({ queryKey: ['chat', 'sessions'] })
    },
  })

  // Send message
  const sendMessage = useMutation({
    mutationFn: ({ sessionId, content }: { sessionId: string; content: string }) =>
      chatApi.sendMessage(sessionId, { content }),
    onSuccess: () => {
      setInput('')
      queryClient.invalidateQueries({ queryKey: ['chat', 'messages', activeSessionId] })
    },
    onError: () => {
      toast.error('Failed to send message')
    },
  })

  // Delete session
  const deleteSession = useMutation({
    mutationFn: (sessionId: string) => chatApi.deleteSession(sessionId),
    onSuccess: () => {
      setActiveSessionId(null)
      queryClient.invalidateQueries({ queryKey: ['chat', 'sessions'] })
    },
  })

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // Auto-select first session or create new one
  useEffect(() => {
    if (open && sessions && sessions.length > 0 && !activeSessionId) {
      setActiveSessionId(sessions[0].id)
    }
  }, [open, sessions, activeSessionId])

  const handleSend = () => {
    if (!input.trim()) return

    if (!activeSessionId) {
      // Create new session first
      createSession.mutate(undefined, {
        onSuccess: (session) => {
          sendMessage.mutate({ sessionId: session.id, content: input })
        },
      })
    } else {
      sendMessage.mutate({ sessionId: activeSessionId, content: input })
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSuggestion = (suggestion: string) => {
    setInput(suggestion)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-full flex-col p-0 sm:max-w-md">
        <SheetHeader className="border-b px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              <SheetTitle>AI Assistant</SheetTitle>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => createSession.mutate()}
                disabled={createSession.isPending}
              >
                <Plus className="h-4 w-4" />
              </Button>
              {activeSessionId && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => deleteSession.mutate(activeSessionId)}
                  disabled={deleteSession.isPending}
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              )}
            </div>
          </div>
        </SheetHeader>

        {/* Messages */}
        <ScrollArea className="flex-1 px-4" ref={scrollRef}>
          <div className="space-y-4 py-4">
            {messagesLoading ? (
              <>
                <Skeleton className="h-16 w-3/4" />
                <Skeleton className="ml-auto h-12 w-2/3" />
                <Skeleton className="h-20 w-4/5" />
              </>
            ) : messages && messages.length > 0 ? (
              messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <MessageCircle className="h-12 w-12 text-muted-foreground/50" />
                <p className="mt-4 font-medium">Start a conversation</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Ask about your health data, get insights, or explore trends
                </p>
                <ChatSuggestions onSelect={handleSuggestion} className="mt-6" />
              </div>
            )}

            {sendMessage.isPending && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm">Thinking...</span>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Input */}
        <div className="border-t p-4">
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your health..."
              disabled={sendMessage.isPending}
            />
            <Button
              size="icon"
              onClick={handleSend}
              disabled={!input.trim() || sendMessage.isPending}
            >
              {sendMessage.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
