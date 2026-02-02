import apiClient from './client'
import type { MorningBriefing, RecoveryPrediction, CravingsForecast, Recommendation } from '@/types'

export const briefingApi = {
  getMorningBriefing: async (): Promise<MorningBriefing> => {
    const response = await apiClient.get<MorningBriefing>('/briefing/today')
    return response.data
  },

  getRecoveryPrediction: async (targetDate?: string): Promise<RecoveryPrediction> => {
    const response = await apiClient.get<RecoveryPrediction>('/briefing/recovery', {
      params: targetDate ? { target_date: targetDate } : {},
    })
    return response.data
  },

  getCravingsForecast: async (targetDate?: string): Promise<CravingsForecast> => {
    const response = await apiClient.get<CravingsForecast>('/briefing/cravings', {
      params: targetDate ? { target_date: targetDate } : {},
    })
    return response.data
  },

  getRecommendations: async (days: number = 7, includeAi: boolean = true, maxItems: number = 8): Promise<{ count: number; recommendations: Recommendation[] }> => {
    const response = await apiClient.get('/briefing/recommendations', {
      params: { days, include_ai: includeAi, max_items: maxItems },
    })
    return response.data
  },
}
