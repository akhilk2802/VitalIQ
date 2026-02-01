import apiClient from './client'
import type { Correlation, CorrelationSummary } from '@/types'

export interface CorrelationsParams {
  correlation_type?: string
  actionable_only?: boolean
  limit?: number
}

export interface DetectCorrelationsParams {
  days?: number
  include_granger?: boolean
  include_pearson?: boolean
  include_cross_correlation?: boolean
  include_mutual_info?: boolean
  include_population_comparison?: boolean
  min_confidence?: number
  generate_insights?: boolean
}

export interface CorrelationDetectionResult {
  total_correlations: number
  significant_correlations: number
  actionable_count: number
  new_correlations: number
  by_type: Record<string, number>
  by_strength: Record<string, number>
  top_findings: string[]
  correlations: Correlation[]
}

export interface CorrelationInsights {
  summary: string
  key_findings: string[]
  recommendations: string[]
  total_correlations: number
  actionable_count: number
  period_days: number
  generated_at: string
}

export const correlationsApi = {
  getCorrelations: async (params: CorrelationsParams = {}): Promise<Correlation[]> => {
    const response = await apiClient.get<Correlation[]>('/correlations', { params })
    return response.data
  },

  detectCorrelations: async (params: DetectCorrelationsParams = {}): Promise<CorrelationDetectionResult> => {
    const response = await apiClient.post<CorrelationDetectionResult>('/correlations/detect', params)
    return response.data
  },

  getTopCorrelations: async (limit: number = 5): Promise<{ correlations: CorrelationSummary[]; total_actionable: number }> => {
    const response = await apiClient.get('/correlations/top', {
      params: { limit },
    })
    return response.data
  },

  getCorrelationInsights: async (days: number = 30): Promise<CorrelationInsights> => {
    const response = await apiClient.get<CorrelationInsights>('/correlations/insights', {
      params: { days },
    })
    return response.data
  },

  getCorrelation: async (correlationId: string): Promise<Correlation> => {
    const response = await apiClient.get<Correlation>(`/correlations/${correlationId}`)
    return response.data
  },
}
