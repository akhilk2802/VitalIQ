import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { anomaliesApi } from '@/api'
import { cn, getRelativeTime } from '@/lib/utils'
import { SEVERITY_CONFIG, METRIC_COLORS } from '@/lib/constants'
import { GlassCard } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import {
  AlertTriangle,
  CheckCircle2,
  Zap,
  RefreshCw,
  Filter,
  Lightbulb,
} from 'lucide-react'
import type { Anomaly } from '@/types'

export function AlertsPage() {
  const [filter, setFilter] = useState<'all' | 'unacknowledged'>('unacknowledged')
  const queryClient = useQueryClient()

  const { data: anomalies, isLoading } = useQuery({
    queryKey: ['anomalies', 'all'],
    queryFn: () => anomaliesApi.getAnomalies({ limit: 100 }),
  })

  const { data: insights, isLoading: insightsLoading } = useQuery({
    queryKey: ['anomalies', 'insights'],
    queryFn: () => anomaliesApi.getAnomalyInsights(30),
  })

  const detectMutation = useMutation({
    mutationFn: () =>
      anomaliesApi.detectAnomalies({
        days: 30,
        include_explanation: true,
        use_robust: true,
        use_adaptive: true,
      }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['anomalies'] })
      toast.success(`Detection complete: ${result.new_anomalies} new anomalies found`)
    },
    onError: () => {
      toast.error('Failed to run anomaly detection')
    },
  })

  const acknowledgeMutation = useMutation({
    mutationFn: (id: string) => anomaliesApi.acknowledgeAnomaly(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['anomalies'] })
    },
  })

  const filteredAnomalies = anomalies?.filter((a) =>
    filter === 'all' ? true : !a.is_acknowledged
  )

  const severityCounts = anomalies?.reduce(
    (acc, a) => {
      acc[a.severity] = (acc[a.severity] || 0) + 1
      return acc
    },
    {} as Record<string, number>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Alerts</h1>
          <p className="text-muted-foreground">
            Monitor anomalies in your health metrics
          </p>
        </div>
        <Button
          onClick={() => detectMutation.mutate()}
          disabled={detectMutation.isPending}
        >
          <RefreshCw
            className={cn('mr-2 h-4 w-4', detectMutation.isPending && 'animate-spin')}
          />
          Run Detection
        </Button>
      </div>

      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <GlassCard className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
              <AlertTriangle className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <p className="text-2xl font-bold">{anomalies?.length || 0}</p>
              <p className="text-xs text-muted-foreground">Total Alerts</p>
            </div>
          </div>
        </GlassCard>
        {Object.entries(SEVERITY_CONFIG).map(([key, config]) => (
          <GlassCard key={key} className="p-4">
            <div className="flex items-center gap-3">
              <div
                className="flex h-10 w-10 items-center justify-center rounded-lg"
                style={{ backgroundColor: config.bgColor }}
              >
                <Zap className="h-5 w-5" style={{ color: config.color }} />
              </div>
              <div>
                <p className="text-2xl font-bold">{severityCounts?.[key] || 0}</p>
                <p className="text-xs text-muted-foreground">{config.label}</p>
              </div>
            </div>
          </GlassCard>
        ))}
      </div>

      {/* Insights */}
      {insights && (
        <GlassCard className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Lightbulb className="h-5 w-5 text-nutrition" />
            <h3 className="font-medium">AI Insights</h3>
          </div>
          <p className="text-sm text-muted-foreground mb-4">{insights.summary}</p>
          {insights.key_findings.length > 0 && (
            <div className="space-y-2">
              {insights.key_findings.slice(0, 3).map((finding, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <span className="text-muted-foreground">•</span>
                  <span>{finding}</span>
                </div>
              ))}
            </div>
          )}
        </GlassCard>
      )}

      {/* Filter tabs */}
      <Tabs value={filter} onValueChange={(v) => setFilter(v as 'all' | 'unacknowledged')}>
        <TabsList>
          <TabsTrigger value="unacknowledged">
            Unacknowledged ({anomalies?.filter((a) => !a.is_acknowledged).length || 0})
          </TabsTrigger>
          <TabsTrigger value="all">All ({anomalies?.length || 0})</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Anomaly list */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : filteredAnomalies?.length === 0 ? (
        <GlassCard className="p-12">
          <div className="flex flex-col items-center text-center">
            <CheckCircle2 className="h-12 w-12 text-exercise" />
            <h3 className="mt-4 font-medium">All clear!</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              No {filter === 'unacknowledged' ? 'unacknowledged' : ''} anomalies found
            </p>
          </div>
        </GlassCard>
      ) : (
        <div className="space-y-3">
          {filteredAnomalies?.map((anomaly) => (
            <AnomalyCard
              key={anomaly.id}
              anomaly={anomaly}
              onAcknowledge={() => acknowledgeMutation.mutate(anomaly.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function AnomalyCard({
  anomaly,
  onAcknowledge,
}: {
  anomaly: Anomaly
  onAcknowledge: () => void
}) {
  const severityConfig = SEVERITY_CONFIG[anomaly.severity]

  return (
    <GlassCard
      className={cn(
        'p-4',
        anomaly.is_acknowledged && 'opacity-60'
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4" style={{ color: severityConfig.color }} />
            <span className="font-medium capitalize">
              {anomaly.metric_name.replace(/_/g, ' ')}
            </span>
            <Badge
              variant="outline"
              className="text-xs"
              style={{
                color: severityConfig.color,
                borderColor: severityConfig.color,
              }}
            >
              {severityConfig.label}
            </Badge>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            {anomaly.explanation ||
              `Value of ${anomaly.metric_value.toFixed(1)} deviates ${anomaly.anomaly_score.toFixed(1)}σ from baseline (${anomaly.baseline_value.toFixed(1)})`}
          </p>
          <p className="mt-2 text-xs text-muted-foreground/70">
            Detected {getRelativeTime(anomaly.detected_at)} • {anomaly.detector_type}
          </p>
        </div>
        {!anomaly.is_acknowledged && (
          <Button variant="outline" size="sm" onClick={onAcknowledge}>
            Dismiss
          </Button>
        )}
      </div>
    </GlassCard>
  )
}
