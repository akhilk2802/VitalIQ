import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  useDashboard,
  useHealthScore,
  useRecentAnomalies,
  useTopCorrelations,
  useMorningBriefing,
} from '@/hooks/useDashboard'
import { anomaliesApi } from '@/api'
import {
  HealthScoreRing,
  MorningBriefingCard,
  QuickStatsRow,
  TimeRangeTabs,
  AnomalySection,
  CorrelationSection,
} from '@/components/dashboard'

export function DashboardPage() {
  const [timeRange, setTimeRange] = useState(7)
  const queryClient = useQueryClient()

  // Queries
  const { data: dashboardData, isLoading: dashboardLoading } = useDashboard({
    days: timeRange,
  })
  const { data: healthScore, isLoading: scoreLoading } = useHealthScore(timeRange)
  const { data: anomalies, isLoading: anomaliesLoading } = useRecentAnomalies(10)
  const { data: correlationsData, isLoading: correlationsLoading } = useTopCorrelations(5)
  const { data: briefing, isLoading: briefingLoading } = useMorningBriefing()

  // Mutations
  const acknowledgeAnomaly = useMutation({
    mutationFn: (id: string) => anomaliesApi.acknowledgeAnomaly(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['anomalies'] })
      toast.success('Anomaly acknowledged')
    },
    onError: () => {
      toast.error('Failed to acknowledge anomaly')
    },
  })

  return (
    <div className="space-y-6">
      {/* Page header with time range tabs */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Your health overview at a glance
          </p>
        </div>
        <TimeRangeTabs value={timeRange} onChange={setTimeRange} />
      </div>

      {/* Hero section - Health Score & Morning Briefing */}
      <div className="grid gap-6 lg:grid-cols-2">
        <HealthScoreRing
          score={healthScore?.overall_score}
          trend={healthScore?.trend}
          isLoading={scoreLoading}
        />
        <MorningBriefingCard briefing={briefing} isLoading={briefingLoading} />
      </div>

      {/* Quick stats row */}
      <QuickStatsRow data={dashboardData} isLoading={dashboardLoading} />

      {/* Anomalies and Correlations */}
      <div className="grid gap-6 lg:grid-cols-2">
        <AnomalySection
          anomalies={anomalies}
          isLoading={anomaliesLoading}
          onAcknowledge={(id) => acknowledgeAnomaly.mutate(id)}
        />
        <CorrelationSection
          correlations={correlationsData?.correlations}
          totalActionable={correlationsData?.total_actionable}
          isLoading={correlationsLoading}
        />
      </div>
    </div>
  )
}
