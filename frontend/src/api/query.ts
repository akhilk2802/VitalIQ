import apiClient from './client'
import type { QueryResponse } from '@/types'

export interface QueryParams {
  query: string
}

export interface QuerySuggestion {
  name: string
  examples: string[]
}

export const queryApi = {
  query: async (params: QueryParams): Promise<QueryResponse> => {
    const response = await apiClient.post<QueryResponse>('/query', params)
    return response.data
  },

  getSuggestions: async (): Promise<{ categories: QuerySuggestion[] }> => {
    const response = await apiClient.get('/query/suggestions')
    return response.data
  },
}
