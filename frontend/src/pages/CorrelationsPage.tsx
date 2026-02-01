import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { correlationsApi } from '@/api'
import { cn } from '@/lib/utils'
import { GlassCard } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  GitBranch,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Lightbulb,
  ArrowRight,
  Zap,
} from 'lucide-react'
import type { Correlation } from '@/types'

export function CorrelationsPage() {
  const [filter, setFilter] = useState<'all' | 'actionable'>('actionable')
  const queryClient = useQueryClient()

  const { data: correlations, isLoading } = useQuery({
    queryKey: ['correlations', 'all'],
    queryFn: () =>
      correlationsApi.getCorrelations({
        actionable_only: filter === 'actionable',
        limit: 100,
      }),
  })

  const { data: insights, isLoading: insightsLoading } = useQuery({
    queryKey: ['correlations', 'insights'],
    queryFn: () => correlationsApi.getCorrelationInsights(60),
  })

  const detectMutation = useMutation({
    mutationFn: () =>
      correlationsApi.detectCorrelations({
        days: 60,
        include_granger: true,
        include_pearson: true,
        include_cross_correlation: true,
        include_mutual_info: true,
        generate_insights: true,
      }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['correlations'] })
      toast.success(
        `Analysis complete: ${result.new_correlations} new correlations discovered`
      )
    },
    onError: () => {
      toast.error('Failed to run correlation analysis')
    },
  })

  const strengthGroups = correlations?.reduce(
    (acc, c) => {
      const strength = c.strength || 'unknown'
      acc[strength] = [...(acc[strength] || []), c]
      return acc
    },
    {} as Record<string, Correlation[]>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Correlations</h1>
          <p className="text-muted-foreground">
            Discover patterns between your health metrics
          </p>
        </div>
        <Button
          onClick={() => detectMutation.mutate()}
          disabled={detectMutation.isPending}
        >
          <RefreshCw
            className={cn('mr-2 h-4 w-4', detectMutation.isPending && 'animate-spin')}
          />
          Analyze
        </Button>
      </div>

      {/* Insights */}
      {insights && (
        <GlassCard className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Lightbulb className="h-5 w-5 text-nutrition" />
            <h3 className="font-medium">Key Findings</h3>
          </div>
          <p className="text-sm text-muted-foreground mb-4">{insights.summary}</p>
          {insights.key_findings.length > 0 && (
            <div className="space-y-2">
              {insights.key_findings.map((finding, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <Zap className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                  <span>{finding}</span>
                </div>
              ))}
            </div>
          )}
          {insights.recommendations.length > 0 && (
            <div className="mt-4 pt-4 border-t border-border">
              <p className="text-sm font-medium mb-2">Recommendations</p>
              <div className="space-y-2">
                {insights.recommendations.map((rec, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm">
                    <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-exercise" />
                    <span className="text-muted-foreground">{rec}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </GlassCard>
      )}

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <GlassCard className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-recovery/10">
              <GitBranch className="h-5 w-5 text-recovery" />
            </div>
            <div>
              <p className="text-2xl font-bold">{correlations?.length || 0}</p>
              <p className="text-xs text-muted-foreground">Total Correlations</p>
            </div>
          </div>
        </GlassCard>
        {['very_strong', 'strong', 'moderate'].map((strength) => (
          <GlassCard key={strength} className="p-4">
            <div className="flex items-center gap-3">
              <div
                className={cn(
                  'flex h-10 w-10 items-center justify-center rounded-lg',
                  strength === 'very_strong' && 'bg-exercise/10',
                  strength === 'strong' && 'bg-primary/10',
                  strength === 'moderate' && 'bg-nutrition/10'
                )}
              >
                <GitBranch
                  className={cn(
                    'h-5 w-5',
                    strength === 'very_strong' && 'text-exercise',
                    strength === 'strong' && 'text-primary',
                    strength === 'moderate' && 'text-nutrition'
                  )}
                />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {strengthGroups?.[strength]?.length || 0}
                </p>
                <p className="text-xs text-muted-foreground capitalize">
                  {strength.replace('_', ' ')}
                </p>
              </div>
            </div>
          </GlassCard>
        ))}
      </div>

      {/* Filter tabs */}
      <Tabs value={filter} onValueChange={(v) => setFilter(v as 'all' | 'actionable')}>
        <TabsList>
          <TabsTrigger value="actionable">Actionable</TabsTrigger>
          <TabsTrigger value="all">All</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Correlations list */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : correlations?.length === 0 ? (
        <GlassCard className="p-12">
          <div className="flex flex-col items-center text-center">
            <GitBranch className="h-12 w-12 text-muted-foreground/50" />
            <h3 className="mt-4 font-medium">No correlations found</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Run the analysis to discover patterns in your data
            </p>
          </div>
        </GlassCard>
      ) : (
        <div className="space-y-3">
          {correlations?.map((correlation) => (
            <CorrelationCard key={correlation.id} correlation={correlation} />
          ))}
        </div>
      )}
    </div>
  )
}

function CorrelationCard({ correlation }: { correlation: Correlation }) {
  const isPositive = correlation.correlation_value > 0

  const strengthColors: Record<string, string> = {
    weak: 'text-muted-foreground',
    moderate: 'text-nutrition',
    strong: 'text-primary',
    very_strong: 'text-exercise',
  }

  const formatMetricName = (name: string) =>
    name
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase())

  return (
    <GlassCard className="p-4">
      <div className="flex items-start gap-4">
        <div
          className={cn(
            'mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
            isPositive ? 'bg-exercise/10' : 'bg-heart/10'
          )}
        >
          {isPositive ? (
            <TrendingUp className="h-5 w-5 text-exercise" />
          ) : (
            <TrendingDown className="h-5 w-5 text-heart" />
          )}
        </div>

        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{formatMetricName(correlation.metric_a)}</span>
            <ArrowRight className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium">{formatMetricName(correlation.metric_b)}</span>
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
            <span
              className={cn(
                'font-medium capitalize',
                strengthColors[correlation.strength]
              )}
            >
              {correlation.strength.replace('_', ' ')}
            </span>
            <span className="text-muted-foreground">
              r = {correlation.correlation_value.toFixed(2)}
            </span>
            {correlation.lag_days && correlation.lag_days > 0 && (
              <span className="text-muted-foreground">
                {correlation.lag_days}d lag
              </span>
            )}
            {correlation.causal_direction && correlation.causal_direction !== 'none' && (
              <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                Causal
              </span>
            )}
            <span className="text-xs text-muted-foreground">
              {correlation.correlation_type.replace('_', ' ')}
            </span>
          </div>

          {correlation.insight && (
            <div className="mt-3 rounded-lg bg-background/50 p-3">
              <div className="flex items-start gap-2">
                <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-nutrition" />
                <p className="text-sm">{correlation.insight}</p>
              </div>
            </div>
          )}

          {correlation.recommendation && (
            <div className="mt-2 flex items-start gap-2 text-sm">
              <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-exercise" />
              <p className="text-muted-foreground">{correlation.recommendation}</p>
            </div>
          )}
        </div>
      </div>
    </GlassCard>
  )
}
