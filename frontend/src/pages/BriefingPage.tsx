import { useQuery } from '@tanstack/react-query'
import { briefingApi } from '@/api'
import { formatDateFull } from '@/lib/utils'
import { cn } from '@/lib/utils'
import { GlassCard } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import {
  Sun,
  Battery,
  Cookie,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Lightbulb,
  Clock,
} from 'lucide-react'

export function BriefingPage() {
  const { data: briefing, isLoading } = useQuery({
    queryKey: ['briefing', 'full'],
    queryFn: () => briefingApi.getMorningBriefing(),
  })

  const { data: recommendations, isLoading: recsLoading } = useQuery({
    queryKey: ['briefing', 'recommendations'],
    queryFn: () => briefingApi.getRecommendations(7, true, 10),
  })

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
        <Skeleton className="h-48" />
      </div>
    )
  }

  const recoveryScore = briefing?.recovery.score || 0
  const recoveryColor =
    recoveryScore >= 7 ? 'text-exercise' : recoveryScore >= 4 ? 'text-nutrition' : 'text-heart'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-muted-foreground">
          <Sun className="h-5 w-5 text-nutrition" />
          <span className="text-sm">
            {formatDateFull(briefing?.briefing_date || new Date())}
          </span>
        </div>
        <h1 className="mt-2 text-2xl font-bold tracking-tight">
          {briefing?.greeting || 'Good morning!'}
        </h1>
      </div>

      {/* Recovery & Cravings */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recovery */}
        <GlassCard className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Battery className="h-5 w-5 text-recovery" />
            <h2 className="font-medium">Recovery Status</h2>
          </div>

          <div className="flex items-center gap-6">
            <div className="relative">
              <svg className="h-32 w-32 -rotate-90 transform">
                <circle
                  cx="64"
                  cy="64"
                  r="50"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="8"
                  className="text-muted/30"
                />
                <circle
                  cx="64"
                  cy="64"
                  r="50"
                  fill="none"
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeDasharray={314}
                  strokeDashoffset={314 - (recoveryScore / 10) * 314}
                  className={cn(
                    'transition-all duration-1000',
                    recoveryColor === 'text-exercise' && 'stroke-exercise',
                    recoveryColor === 'text-nutrition' && 'stroke-nutrition',
                    recoveryColor === 'text-heart' && 'stroke-heart'
                  )}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className={cn('text-4xl font-bold', recoveryColor)}>
                  {recoveryScore}
                </span>
              </div>
            </div>

            <div className="flex-1">
              <p className="text-lg font-medium capitalize">
                {briefing?.recovery.status?.replace(/_/g, ' ')}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {briefing?.recovery.message}
              </p>
              {briefing?.recovery.top_factor && (
                <p className="mt-3 text-xs text-muted-foreground">
                  Top factor: <span className="capitalize">{briefing.recovery.top_factor.replace(/_/g, ' ')}</span>
                </p>
              )}
            </div>
          </div>
        </GlassCard>

        {/* Cravings */}
        <GlassCard className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Cookie className="h-5 w-5 text-nutrition" />
            <h2 className="font-medium">Cravings Forecast</h2>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm">Risk Level</span>
                <span
                  className={cn(
                    'font-medium capitalize',
                    briefing?.cravings.risk_level === 'low' && 'text-exercise',
                    briefing?.cravings.risk_level === 'moderate' && 'text-nutrition',
                    briefing?.cravings.risk_level === 'high' && 'text-heart'
                  )}
                >
                  {briefing?.cravings.risk_level}
                </span>
              </div>
              <Progress
                value={
                  briefing?.cravings.risk_level === 'low'
                    ? 25
                    : briefing?.cravings.risk_level === 'moderate'
                    ? 60
                    : 90
                }
                className="h-2"
                indicatorClassName={cn(
                  briefing?.cravings.risk_level === 'low' && 'bg-exercise',
                  briefing?.cravings.risk_level === 'moderate' && 'bg-nutrition',
                  briefing?.cravings.risk_level === 'high' && 'bg-heart'
                )}
              />
            </div>

            <div>
              <p className="text-sm font-medium capitalize">
                Primary: {briefing?.cravings.primary_type}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {briefing?.cravings.reasoning}
              </p>
            </div>

            {briefing?.cravings.peak_time && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Clock className="h-4 w-4" />
                <span>Peak time: {briefing.cravings.peak_time}</span>
              </div>
            )}

            {briefing?.cravings.countermeasures && briefing.cravings.countermeasures.length > 0 && (
              <div className="rounded-lg bg-background/50 p-3">
                <p className="text-xs font-medium text-muted-foreground mb-2">
                  Countermeasures
                </p>
                <ul className="space-y-1">
                  {briefing.cravings.countermeasures.map((measure, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-exercise" />
                      <span>{measure}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </GlassCard>
      </div>

      {/* Today's Recommendations */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Lightbulb className="h-5 w-5 text-nutrition" />
          <h2 className="font-medium">Today's Recommendations</h2>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {recommendations?.recommendations?.map((rec, i) => (
            <div
              key={i}
              className={cn(
                'rounded-lg p-4',
                rec.priority === 'high' && 'bg-heart/10',
                rec.priority === 'medium' && 'bg-nutrition/10',
                rec.priority === 'low' && 'bg-muted'
              )}
            >
              <div className="flex items-center gap-2 mb-2">
                <span
                  className={cn(
                    'text-xs font-medium uppercase',
                    rec.priority === 'high' && 'text-heart',
                    rec.priority === 'medium' && 'text-nutrition',
                    rec.priority === 'low' && 'text-muted-foreground'
                  )}
                >
                  {rec.type}
                </span>
              </div>
              <p className="text-sm font-medium">{rec.message}</p>
              {rec.reasoning && (
                <p className="mt-1 text-xs text-muted-foreground">{rec.reasoning}</p>
              )}
            </div>
          )) || (
            <p className="col-span-2 text-sm text-muted-foreground text-center py-4">
              No recommendations available
            </p>
          )}
        </div>
      </GlassCard>

      {/* Alerts summary */}
      {briefing?.anomalies_yesterday && briefing.anomalies_yesterday.count > 0 && (
        <GlassCard className="p-6">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-heart/10">
              <AlertTriangle className="h-6 w-6 text-heart" />
            </div>
            <div>
              <p className="font-medium">
                {briefing.anomalies_yesterday.count} anomal
                {briefing.anomalies_yesterday.count === 1 ? 'y' : 'ies'} detected yesterday
              </p>
              <p className="text-sm text-muted-foreground">
                {briefing.anomalies_yesterday.most_recent &&
                  `Most recent: ${briefing.anomalies_yesterday.most_recent.replace(/_/g, ' ')}`}
              </p>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Confidence */}
      <p className="text-xs text-muted-foreground text-center">
        Prediction confidence: {((briefing?.confidence || 0) * 100).toFixed(0)}%
      </p>
    </div>
  )
}
