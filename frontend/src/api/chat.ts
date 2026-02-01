import apiClient from './client'
import type { ChatSession, ChatMessage } from '@/types'

export interface CreateSessionParams {
  title?: string
}

export interface UpdateSessionParams {
  title?: string
}

export interface SendMessageParams {
  content: string
}

export interface QuickInsightParams {
  insight_type: 'summary' | 'tips' | 'anomalies'
}

export interface QuickInsightResponse {
  insight: string
  insight_type: string
  generated_at: string
}

export interface PaginatedMessagesResponse {
  messages: ChatMessage[]
  has_more: boolean
  next_cursor: string | null
}

export const chatApi = {
  // Sessions
  createSession: async (params: CreateSessionParams = {}): Promise<ChatSession> => {
    const response = await apiClient.post<ChatSession>('/chat/sessions', params)
    return response.data
  },

  getSessions: async (activeOnly: boolean = true, limit: number = 50): Promise<ChatSession[]> => {
    const response = await apiClient.get<ChatSession[]>('/chat/sessions', {
      params: { active_only: activeOnly, limit },
    })
    return response.data
  },

  getSession: async (sessionId: string): Promise<ChatSession & { messages: ChatMessage[] }> => {
    const response = await apiClient.get(`/chat/sessions/${sessionId}`)
    return response.data
  },

  updateSession: async (sessionId: string, params: UpdateSessionParams): Promise<ChatSession> => {
    const response = await apiClient.patch<ChatSession>(`/chat/sessions/${sessionId}`, params)
    return response.data
  },

  deleteSession: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/chat/sessions/${sessionId}`)
  },

  // Messages with pagination
  getMessages: async (
    sessionId: string, 
    limit: number = 50,
    before?: string
  ): Promise<PaginatedMessagesResponse> => {
    const response = await apiClient.get<PaginatedMessagesResponse>(
      `/chat/sessions/${sessionId}/messages`,
      { params: { limit, before } }
    )
    return response.data
  },

  sendMessage: async (sessionId: string, params: SendMessageParams): Promise<ChatMessage> => {
    const response = await apiClient.post<ChatMessage>(`/chat/sessions/${sessionId}/messages`, params)
    return response.data
  },

  // Quick insights
  getQuickInsight: async (params: QuickInsightParams): Promise<QuickInsightResponse> => {
    const response = await apiClient.post<QuickInsightResponse>('/chat/quick-insight', params)
    return response.data
  },
}
