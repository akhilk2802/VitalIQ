import apiClient from './client'
import type { DashboardResponse, HealthScore, HealthScoreDetailed } from '@/types'

export interface DashboardParams {
  start_date?: string
  end_date?: string
  days?: number
}

export const dashboardApi = {
  getDashboard: async (params: DashboardParams = {}): Promise<DashboardResponse> => {
    const response = await apiClient.get<DashboardResponse>('/dashboard', { params })
    return response.data
  },

  getHealthScore: async (days: number = 30): Promise<HealthScore> => {
    const response = await apiClient.get<HealthScore>('/dashboard/health-score', {
      params: { days },
    })
    return response.data
  },

  getHealthScoreDetailed: async (days: number = 30): Promise<HealthScoreDetailed> => {
    const response = await apiClient.get<HealthScoreDetailed>('/dashboard/health-score/detailed', {
      params: { days },
    })
    return response.data
  },
}
