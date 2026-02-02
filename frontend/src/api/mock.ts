import apiClient from './client'
import type { PersonaInfo, MockDataResult, DataSummary } from '@/types'

export type PersonaType = 
  | 'active_athlete'
  | 'poor_sleeper'
  | 'pre_diabetic'
  | 'stress_prone'
  | 'healthy_balanced'

export interface GenerateMockParams {
  days?: number
  persona?: PersonaType
  include_diabetes?: boolean
  include_heart?: boolean
  clear_existing?: boolean
  init_rag?: boolean
}

export interface RAGStatus {
  openai_configured: boolean
  knowledge_base: {
    total_chunks: number
    by_source?: Record<string, number>
    ready: boolean
  }
  user_history: {
    total_embeddings: number
    ready: boolean
  }
  ready: boolean
  message?: string
  error?: string
}

export interface RAGInitResult {
  success: boolean
  message?: string
  error?: string
  stats?: {
    files_processed: number
    chunks_created: number
    errors: number
  }
  existing_chunks?: number
}

export const mockApi = {
  getPersonas: async (): Promise<{ personas: PersonaInfo[] }> => {
    const response = await apiClient.get('/mock/personas')
    return response.data
  },

  generateMockData: async (params: GenerateMockParams = {}): Promise<MockDataResult> => {
    const response = await apiClient.post<MockDataResult>('/mock/generate', null, {
      params: {
        days: params.days ?? 150,
        persona: params.persona ?? 'healthy_balanced',
        include_diabetes: params.include_diabetes ?? true,
        include_heart: params.include_heart ?? false,
        clear_existing: params.clear_existing ?? false,
        init_rag: params.init_rag ?? true,
      },
    })
    return response.data
  },

  clearAllData: async (): Promise<{ message: string; deleted_counts: Record<string, number>; total_deleted: number }> => {
    const response = await apiClient.delete('/mock/clear')
    return response.data
  },

  getDataSummary: async (): Promise<DataSummary> => {
    const response = await apiClient.get<DataSummary>('/mock/data-summary')
    return response.data
  },

  getRAGStatus: async (): Promise<RAGStatus> => {
    const response = await apiClient.get<RAGStatus>('/mock/rag-status')
    return response.data
  },

  initRAG: async (): Promise<RAGInitResult> => {
    const response = await apiClient.post<RAGInitResult>('/mock/init-rag')
    return response.data
  },
}
