import { useState, useRef, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { chatApi, type PaginatedMessagesResponse } from '@/api/chat'
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
  ChevronDown,
  ChevronUp,
  Clock,
  Pencil,
  Check,
  X,
} from 'lucide-react'
import type { ChatSession, ChatMessage as ChatMessageType } from '@/types'

interface ChatDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

export function ChatDrawer({ open, onOpenChange }: ChatDrawerProps) {
  const [input, setInput] = useState('')
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [showSessions, setShowSessions] = useState(false)
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null)
  const [editingTitle, setEditingTitle] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const editInputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  // Get sessions
  const { data: sessions, isLoading: sessionsLoading } = useQuery({
    queryKey: ['chat', 'sessions'],
    queryFn: () => chatApi.getSessions(true, 20),
    enabled: open,
  })

  // Get messages for active session with infinite scroll
  const {
    data: messagesData,
    isLoading: messagesLoading,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['chat', 'messages', activeSessionId],
    queryFn: ({ pageParam }) => 
      chatApi.getMessages(activeSessionId!, 30, pageParam as string | undefined),
    getNextPageParam: (lastPage: PaginatedMessagesResponse) => 
      lastPage.has_more ? lastPage.next_cursor : undefined,
    enabled: !!activeSessionId,
    initialPageParam: undefined as string | undefined,
  })

  // Flatten messages from all pages
  const messages = messagesData?.pages.flatMap(p => p.messages) ?? []

  // Create new session
  const createSession = useMutation({
    mutationFn: () => chatApi.createSession(),
    onSuccess: (session) => {
      setActiveSessionId(session.id)
      setShowSessions(false)
      queryClient.invalidateQueries({ queryKey: ['chat', 'sessions'] })
    },
  })

  // Update session (rename)
  const updateSession = useMutation({
    mutationFn: ({ sessionId, title }: { sessionId: string; title: string }) =>
      chatApi.updateSession(sessionId, { title }),
    onSuccess: () => {
      setEditingSessionId(null)
      setEditingTitle('')
      queryClient.invalidateQueries({ queryKey: ['chat', 'sessions'] })
      toast.success('Conversation renamed')
    },
    onError: () => {
      toast.error('Failed to rename conversation')
    },
  })

  // Send message
  const sendMessage = useMutation({
    mutationFn: ({ sessionId, content }: { sessionId: string; content: string }) =>
      chatApi.sendMessage(sessionId, { content }),
    onSuccess: () => {
      setInput('')
      queryClient.invalidateQueries({ queryKey: ['chat', 'messages', activeSessionId] })
      queryClient.invalidateQueries({ queryKey: ['chat', 'sessions'] })
    },
    onError: () => {
      toast.error('Failed to send message')
    },
  })

  // Delete session
  const deleteSession = useMutation({
    mutationFn: (sessionId: string) => chatApi.deleteSession(sessionId),
    onSuccess: (_, deletedSessionId) => {
      // If we deleted the active session, select the next one
      if (activeSessionId === deletedSessionId) {
        const remainingSessions = sessions?.filter(s => s.id !== deletedSessionId)
        setActiveSessionId(remainingSessions?.[0]?.id ?? null)
      }
      queryClient.invalidateQueries({ queryKey: ['chat', 'sessions'] })
      toast.success('Conversation deleted')
    },
    onError: () => {
      toast.error('Failed to delete conversation')
    },
  })

  // Handle scroll to load more messages
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget
    // Load more when scrolled near the top
    if (target.scrollTop < 100 && hasNextPage && !isFetchingNextPage) {
      fetchNextPage()
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage])

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current && !isFetchingNextPage) {
      // Only auto-scroll if we're near the bottom
      const scrollArea = scrollRef.current
      const isNearBottom = scrollArea.scrollHeight - scrollArea.scrollTop - scrollArea.clientHeight < 100
      if (isNearBottom || messages.length <= 2) {
        scrollArea.scrollTop = scrollArea.scrollHeight
      }
    }
  }, [messages.length, isFetchingNextPage])

  // Auto-select first session or create new one
  useEffect(() => {
    if (open && sessions && sessions.length > 0 && !activeSessionId) {
      setActiveSessionId(sessions[0].id)
    }
  }, [open, sessions, activeSessionId])

  // Focus edit input when editing starts
  useEffect(() => {
    if (editingSessionId && editInputRef.current) {
      editInputRef.current.focus()
    }
  }, [editingSessionId])

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

  const handleSelectSession = (sessionId: string) => {
    if (editingSessionId) return // Don't switch while editing
    setActiveSessionId(sessionId)
    setShowSessions(false)
  }

  const handleStartEdit = (e: React.MouseEvent, session: ChatSession) => {
    e.stopPropagation()
    setEditingSessionId(session.id)
    setEditingTitle(session.title || '')
  }

  const handleSaveEdit = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (editingSessionId && editingTitle.trim()) {
      updateSession.mutate({ sessionId: editingSessionId, title: editingTitle.trim() })
    } else {
      setEditingSessionId(null)
      setEditingTitle('')
    }
  }

  const handleCancelEdit = (e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingSessionId(null)
    setEditingTitle('')
  }

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    e.stopPropagation()
    if (e.key === 'Enter') {
      if (editingSessionId && editingTitle.trim()) {
        updateSession.mutate({ sessionId: editingSessionId, title: editingTitle.trim() })
      }
    } else if (e.key === 'Escape') {
      setEditingSessionId(null)
      setEditingTitle('')
    }
  }

  const handleDeleteSession = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation()
    if (confirm('Delete this conversation?')) {
      deleteSession.mutate(sessionId)
    }
  }

  const activeSession = sessions?.find(s => s.id === activeSessionId)

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-full flex-col p-0 sm:max-w-md">
        <SheetHeader className="border-b px-4 py-3">
          <div className="flex items-center justify-between pr-8">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              <SheetTitle>AI Assistant</SheetTitle>
            </div>
            <div className="flex items-center gap-1">
              {activeSessionId && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => deleteSession.mutate(activeSessionId)}
                  disabled={deleteSession.isPending}
                  title="Delete conversation"
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              )}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => createSession.mutate()}
                disabled={createSession.isPending}
                title="New conversation"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </SheetHeader>

        {/* Session Switcher */}
        <div className="border-b">
          <button
            onClick={() => setShowSessions(!showSessions)}
            className="flex w-full items-center justify-between px-4 py-2 text-sm hover:bg-muted/50 transition-colors"
          >
            <div className="flex items-center gap-2 text-left min-w-0">
              <MessageCircle className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
              <span className="truncate font-medium">
                {activeSession?.title || 'New conversation'}
              </span>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {sessions && sessions.length > 1 && (
                <span className="text-xs text-muted-foreground">
                  {sessions.length} chats
                </span>
              )}
              {showSessions ? (
                <ChevronUp className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
          </button>

          {/* Session List */}
          {showSessions && (
            <div className="max-h-64 overflow-y-auto border-t bg-muted/30">
              {sessionsLoading ? (
                <div className="p-4 space-y-2">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ) : sessions && sessions.length > 0 ? (
                sessions.map((session) => (
                  <div
                    key={session.id}
                    onClick={() => handleSelectSession(session.id)}
                    className={cn(
                      'flex items-center justify-between px-4 py-2.5 cursor-pointer hover:bg-muted/80 transition-colors group',
                      session.id === activeSessionId && 'bg-muted'
                    )}
                  >
                    {editingSessionId === session.id ? (
                      // Edit mode
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        <Input
                          ref={editInputRef}
                          value={editingTitle}
                          onChange={(e) => setEditingTitle(e.target.value)}
                          onKeyDown={handleEditKeyDown}
                          onClick={(e) => e.stopPropagation()}
                          className="h-7 text-sm"
                          placeholder="Conversation name..."
                        />
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 flex-shrink-0"
                          onClick={handleSaveEdit}
                          disabled={updateSession.isPending}
                        >
                          <Check className="h-3.5 w-3.5 text-green-500" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 flex-shrink-0"
                          onClick={handleCancelEdit}
                        >
                          <X className="h-3.5 w-3.5 text-muted-foreground" />
                        </Button>
                      </div>
                    ) : (
                      // Display mode
                      <>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">
                            {session.title || 'New conversation'}
                          </p>
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            <span>{formatRelativeTime(session.updated_at)}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={(e) => handleStartEdit(e, session)}
                            title="Rename"
                          >
                            <Pencil className="h-3.5 w-3.5 text-muted-foreground" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={(e) => handleDeleteSession(e, session.id)}
                            disabled={deleteSession.isPending}
                            title="Delete"
                          >
                            <Trash2 className="h-3.5 w-3.5 text-destructive" />
                          </Button>
                        </div>
                        {session.id === activeSessionId && (
                          <div className="h-2 w-2 rounded-full bg-primary flex-shrink-0 ml-2" />
                        )}
                      </>
                    )}
                  </div>
                ))
              ) : (
                <div className="p-4 text-center text-sm text-muted-foreground">
                  No conversations yet
                </div>
              )}
            </div>
          )}
        </div>

        {/* Messages */}
        <div 
          ref={scrollRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto px-4"
        >
          <div className="space-y-4 py-4">
            {/* Load more indicator */}
            {isFetchingNextPage && (
              <div className="flex justify-center py-2">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            )}
            
            {/* Has more indicator */}
            {hasNextPage && !isFetchingNextPage && (
              <button
                onClick={() => fetchNextPage()}
                className="w-full text-center text-xs text-muted-foreground hover:text-foreground py-2"
              >
                Load earlier messages
              </button>
            )}

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
        </div>

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
