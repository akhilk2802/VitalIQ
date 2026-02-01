import apiClient from './client'
import type { Anomaly, AnomalyDetectionResult, AnomalySummary } from '@/types'

export interface AnomaliesParams {
  start_date?: string
  end_date?: string
  acknowledged?: boolean
  limit?: number
}

export interface DetectAnomaliesParams {
  days?: number
  include_explanation?: boolean
  use_robust?: boolean
  use_adaptive?: boolean
  use_ewma_baseline?: boolean
}

export const anomaliesApi = {
  getAnomalies: async (params: AnomaliesParams = {}): Promise<Anomaly[]> => {
    const response = await apiClient.get<Anomaly[]>('/anomalies', { params })
    return response.data
  },

  detectAnomalies: async (params: DetectAnomaliesParams = {}): Promise<AnomalyDetectionResult> => {
    const response = await apiClient.post<AnomalyDetectionResult>('/anomalies/detect', params)
    return response.data
  },

  acknowledgeAnomaly: async (anomalyId: string): Promise<Anomaly> => {
    const response = await apiClient.patch<Anomaly>(`/anomalies/${anomalyId}/acknowledge`)
    return response.data
  },

  getAnomalySummary: async (days: number = 30): Promise<AnomalySummary> => {
    const response = await apiClient.get<AnomalySummary>('/anomalies/summary', {
      params: { days },
    })
    return response.data
  },

  getAnomalyInsights: async (days: number = 30): Promise<{ summary: string; key_findings: string[]; recommendations: string[] }> => {
    const response = await apiClient.get('/anomalies/insights', {
      params: { days },
    })
    return response.data
  },
}
