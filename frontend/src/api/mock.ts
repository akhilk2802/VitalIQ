import apiClient from './client'
import type { PersonaInfo, MockDataResult } from '@/types'

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
      },
    })
    return response.data
  },

  clearAllData: async (): Promise<{ message: string; deleted_counts: Record<string, number>; total_deleted: number }> => {
    const response = await apiClient.delete('/mock/clear')
    return response.data
  },
}
