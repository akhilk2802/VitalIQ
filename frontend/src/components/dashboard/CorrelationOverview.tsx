import { useMemo, useState } from 'react'
import { useDashboard } from '@/hooks/useDashboard'
import { useQuery } from '@tanstack/react-query'
import { correlationsApi } from '@/api/correlations'
import { GlassCard } from '@/components/ui/card'
import { ChartContainer, LineChart } from '@/components/charts'
import { Skeleton } from '@/components/ui/skeleton'
import { METRIC_COLORS } from '@/lib/constants'
import { cn } from '@/lib/utils'
import { Info, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import type { MetricColor } from '@/types'

interface MetricConfig {
  key: string
  label: string
  color: MetricColor
  getValue: (d: any) => number
  unit: string
}

const METRICS: MetricConfig[] = [
  { 
    key: 'sleep_hours', 
    label: 'Sleep', 
    color: 'sleep', 
    getValue: (d) => d.sleep?.duration_hours || 0, 
    unit: 'hrs' 
  },
  { 
    key: 'sleep_quality', 
    label: 'Sleep Quality', 
    color: 'hrv', 
    getValue: (d) => d.sleep?.quality_score || 0, 
    unit: '%' 
  },
  { 
    key: 'total_calories', 
    label: 'Calories', 
    color: 'nutrition', 
    getValue: (d) => d.nutrition?.total_calories || 0, 
    unit: 'kcal' 
  },
  { 
    key: 'exercise_minutes', 
    label: 'Exercise', 
    color: 'exercise', 
    getValue: (d) => (d.exercises || []).reduce((s: number, e: any) => s + (e.duration_minutes || 0), 0), 
    unit: 'min' 
  },
  { 
    key: 'resting_hr', 
    label: 'Heart Rate', 
    color: 'heart', 
    getValue: (d) => d.vitals?.[0]?.resting_heart_rate || 0, 
    unit: 'bpm' 
  },
  { 
    key: 'hrv', 
    label: 'HRV', 
    color: 'recovery', 
    getValue: (d) => d.vitals?.[0]?.hrv_ms || 0, 
    unit: 'ms' 
  },
]

interface CorrelationOverviewProps {
  days?: number
  className?: string
}

export function CorrelationOverview({ days = 30, className }: CorrelationOverviewProps) {
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([
    'sleep_hours', 
    'exercise_minutes', 
    'hrv'
  ])
  const { data: dashboardData, isLoading: dashboardLoading } = useDashboard({ days })
  
  const { data: correlations, isLoading: correlationsLoading } = useQuery({
    queryKey: ['correlations', 'list', 'all'],
    queryFn: () => correlationsApi.getCorrelations({ limit: 100 }),
  })

  // Normalize all metrics to 0-100 scale for overlay comparison
  const normalizedData = useMemo(() => {
    if (!dashboardData?.daily_summaries) return []

    // Calculate min/max for each metric
    const ranges: Record<string, { min: number; max: number }> = {}
    METRICS.forEach(m => {
      const values = dashboardData.daily_summaries
        .map(d => m.getValue(d))
        .filter(v => v > 0)
      
      if (values.length > 0) {
        ranges[m.key] = {
          min: Math.min(...values),
          max: Math.max(...values),
        }
      }
    })

    // Normalize data to 0-100 scale
    return dashboardData.daily_summaries.map(d => {
      const normalized: Record<string, any> = { date: d.date }
      METRICS.forEach(m => {
        const val = m.getValue(d)
        const range = ranges[m.key]
        if (range && range.max > range.min && val > 0) {
          normalized[m.key] = ((val - range.min) / (range.max - range.min)) * 100
        } else if (val > 0) {
          normalized[m.key] = 50 // Default to middle if no range
        } else {
          normalized[m.key] = null // Don't plot zero values
        }
      })
      return normalized
    })
  }, [dashboardData])

  // Build correlation matrix from API data
  const correlationMatrix = useMemo(() => {
    if (!correlations) return {}
    const matrix: Record<string, Record<string, number>> = {}
    
    correlations.forEach(c => {
      if (!matrix[c.metric_a]) matrix[c.metric_a] = {}
      if (!matrix[c.metric_b]) matrix[c.metric_b] = {}
      matrix[c.metric_a][c.metric_b] = c.correlation_value
      matrix[c.metric_b][c.metric_a] = c.correlation_value
    })
    
    return matrix
  }, [correlations])

  const toggleMetric = (key: string) => {
    setSelectedMetrics(prev => 
      prev.includes(key) 
        ? prev.filter(k => k !== key)
        : [...prev, key]
    )
  }

  const selectedLines = METRICS
    .filter(m => selectedMetrics.includes(m.key))
    .map(m => ({ dataKey: m.key, color: m.color, name: m.label }))

  const isLoading = dashboardLoading || correlationsLoading

  if (isLoading) {
    return (
      <div className={cn('space-y-6', className)}>
        <Skeleton className="h-16" />
        <Skeleton className="h-80" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* Metric Selector */}
      <GlassCard className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium">Select Metrics to Compare</h3>
          <span className="text-xs text-muted-foreground">
            {selectedMetrics.length} selected
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {METRICS.map(m => (
            <button
              key={m.key}
              onClick={() => toggleMetric(m.key)}
              className={cn(
                'px-3 py-1.5 rounded-full text-sm font-medium transition-all border',
                selectedMetrics.includes(m.key)
                  ? 'text-white border-transparent'
                  : 'bg-background border-border text-muted-foreground hover:border-muted-foreground'
              )}
              style={selectedMetrics.includes(m.key) ? { 
                backgroundColor: METRIC_COLORS[m.color],
                borderColor: METRIC_COLORS[m.color]
              } : {}}
            >
              {m.label}
            </button>
          ))}
        </div>
      </GlassCard>

      {/* Multi-Metric Overlay Chart */}
      <ChartContainer
        title="Metrics Comparison"
        subtitle="All metrics normalized to 0-100% scale for visual pattern comparison"
        isLoading={false}
        isEmpty={normalizedData.length === 0 || selectedMetrics.length === 0}
      >
        {selectedMetrics.length === 0 ? (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            Select metrics above to compare
          </div>
        ) : (
          <LineChart data={normalizedData} lines={selectedLines} showLegend />
        )}
      </ChartContainer>

      {/* Correlation Heatmap */}
      <GlassCard className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-medium">Correlation Matrix</h3>
            <p className="text-sm text-muted-foreground mt-1">
              How your health metrics relate to each other
            </p>
          </div>
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Info className="h-3.5 w-3.5" />
            <span>Hover for details</span>
          </div>
        </div>
        
        {correlations && correlations.length > 0 ? (
          <div className="overflow-x-auto">
            <CorrelationHeatmap matrix={correlationMatrix} metrics={METRICS} />
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <p>No correlations detected yet.</p>
            <p className="text-sm mt-1">Run correlation analysis from the Correlations page to see the matrix.</p>
          </div>
        )}
      </GlassCard>

      {/* Key Correlations Summary */}
      {correlations && correlations.length > 0 && (
        <GlassCard className="p-6">
          <h3 className="font-medium mb-4">Key Relationships</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {correlations
              .filter(c => Math.abs(c.correlation_value) >= 0.3)
              .slice(0, 6)
              .map((c, i) => (
                <CorrelationSummaryCard key={i} correlation={c} />
              ))}
          </div>
        </GlassCard>
      )}
    </div>
  )
}

function CorrelationHeatmap({ 
  matrix, 
  metrics 
}: { 
  matrix: Record<string, Record<string, number>>
  metrics: MetricConfig[]
}) {
  const getColor = (value: number | undefined): string => {
    if (value === undefined) return 'bg-muted/30'
    const intensity = Math.abs(value)
    if (value > 0) {
      // Positive: green shades
      if (intensity > 0.7) return 'bg-exercise text-white'
      if (intensity > 0.4) return 'bg-exercise/60 text-white'
      if (intensity > 0.2) return 'bg-exercise/30'
      return 'bg-exercise/10'
    } else {
      // Negative: red shades
      if (intensity > 0.7) return 'bg-heart text-white'
      if (intensity > 0.4) return 'bg-heart/60 text-white'
      if (intensity > 0.2) return 'bg-heart/30'
      return 'bg-heart/10'
    }
  }

  const getStrengthLabel = (value: number | undefined): string => {
    if (value === undefined) return 'No data'
    const abs = Math.abs(value)
    const direction = value > 0 ? 'Positive' : 'Negative'
    if (abs > 0.7) return `Strong ${direction}`
    if (abs > 0.4) return `Moderate ${direction}`
    if (abs > 0.2) return `Weak ${direction}`
    return 'Negligible'
  }

  return (
    <div className="space-y-4">
      <div className="inline-block min-w-full">
        <div 
          className="grid gap-1" 
          style={{ gridTemplateColumns: `100px repeat(${metrics.length}, 1fr)` }}
        >
          {/* Header row */}
          <div className="h-10" />
          {metrics.map(m => (
            <div 
              key={m.key} 
              className="h-10 text-xs text-muted-foreground flex items-end justify-center pb-1 font-medium"
            >
              <span className="truncate px-1 -rotate-45 origin-bottom-left translate-y-2">
                {m.label}
              </span>
            </div>
          ))}
          
          {/* Data rows */}
          {metrics.map(row => (
            <div key={row.key} className="contents">
              <div className="h-12 text-xs text-muted-foreground flex items-center font-medium">
                {row.label}
              </div>
              {metrics.map(col => {
                const value = row.key === col.key ? undefined : matrix[row.key]?.[col.key]
                const isSelf = row.key === col.key
                return (
                  <div
                    key={`${row.key}-${col.key}`}
                    className={cn(
                      'h-12 rounded-md flex items-center justify-center text-xs font-medium transition-all cursor-default',
                      isSelf ? 'bg-muted/20' : getColor(value),
                      !isSelf && value !== undefined && 'hover:ring-2 hover:ring-primary hover:ring-offset-2 hover:ring-offset-background'
                    )}
                    title={isSelf 
                      ? `${row.label}` 
                      : `${row.label} ↔ ${col.label}: ${value?.toFixed(2) || 'N/A'}\n${getStrengthLabel(value)}`
                    }
                  >
                    {isSelf ? (
                      <span className="text-muted-foreground">—</span>
                    ) : value !== undefined ? (
                      value.toFixed(2)
                    ) : (
                      <span className="text-muted-foreground/50">·</span>
                    )}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </div>
      
      {/* Legend */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 pt-2 text-xs text-muted-foreground border-t border-border">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-heart" />
          <span>Strong Negative</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-heart/30" />
          <span>Weak Negative</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-muted/30" />
          <span>No Correlation</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-exercise/30" />
          <span>Weak Positive</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-exercise" />
          <span>Strong Positive</span>
        </div>
      </div>
    </div>
  )
}

function CorrelationSummaryCard({ correlation }: { correlation: any }) {
  const isPositive = correlation.correlation_value > 0
  const strength = Math.abs(correlation.correlation_value)
  
  const formatMetric = (name: string) => 
    name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

  return (
    <div className="p-3 rounded-lg bg-muted/30 border border-border/50">
      <div className="flex items-center gap-2 mb-2">
        {isPositive ? (
          <TrendingUp className="h-4 w-4 text-exercise" />
        ) : (
          <TrendingDown className="h-4 w-4 text-heart" />
        )}
        <span className={cn(
          'text-xs font-medium',
          isPositive ? 'text-exercise' : 'text-heart'
        )}>
          {isPositive ? '+' : ''}{correlation.correlation_value.toFixed(2)}
        </span>
      </div>
      <p className="text-sm">
        <span className="font-medium">{formatMetric(correlation.metric_a)}</span>
        <span className="text-muted-foreground"> → </span>
        <span className="font-medium">{formatMetric(correlation.metric_b)}</span>
      </p>
      {correlation.insight && (
        <p className="text-xs text-muted-foreground mt-1.5 line-clamp-2">
          {correlation.insight}
        </p>
      )}
    </div>
  )
}
