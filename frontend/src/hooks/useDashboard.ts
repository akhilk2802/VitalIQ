import { useQuery } from '@tanstack/react-query'
import { dashboardApi, type DashboardParams } from '@/api/dashboard'
import { anomaliesApi } from '@/api/anomalies'
import { correlationsApi } from '@/api/correlations'
import { briefingApi } from '@/api/briefing'

export function useDashboard(params: DashboardParams = {}) {
  return useQuery({
    queryKey: ['dashboard', params],
    queryFn: () => dashboardApi.getDashboard(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useHealthScore(days: number = 30) {
  return useQuery({
    queryKey: ['healthScore', days],
    queryFn: () => dashboardApi.getHealthScore(days),
    staleTime: 10 * 60 * 1000, // 10 minutes
  })
}

export function useRecentAnomalies(limit: number = 5) {
  return useQuery({
    queryKey: ['anomalies', 'recent', limit],
    queryFn: () => anomaliesApi.getAnomalies({ limit, acknowledged: false }),
    staleTime: 5 * 60 * 1000,
  })
}

export function useTopCorrelations(limit: number = 5) {
  return useQuery({
    queryKey: ['correlations', 'top', limit],
    queryFn: () => correlationsApi.getTopCorrelations(limit),
    staleTime: 10 * 60 * 1000,
  })
}

export function useMorningBriefing() {
  return useQuery({
    queryKey: ['briefing', 'today'],
    queryFn: () => briefingApi.getMorningBriefing(),
    staleTime: 30 * 60 * 1000, // 30 minutes (briefing doesn't change much)
    retry: 1,
  })
}
