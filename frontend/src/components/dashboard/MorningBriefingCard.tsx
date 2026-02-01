import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { GlassCard } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Sun, Battery, Cookie, ArrowRight, AlertTriangle, CheckCircle2 } from 'lucide-react'
import type { MorningBriefing } from '@/types'

interface MorningBriefingCardProps {
  briefing?: MorningBriefing
  isLoading?: boolean
  className?: string
}

export function MorningBriefingCard({ briefing, isLoading, className }: MorningBriefingCardProps) {
  if (isLoading) {
    return (
      <GlassCard className={cn('p-6', className)}>
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-5" />
            <Skeleton className="h-5 w-32" />
          </div>
          <Skeleton className="h-4 w-full" />
          <div className="grid gap-3">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        </div>
      </GlassCard>
    )
  }

  if (!briefing) {
    return (
      <GlassCard className={cn('p-6', className)}>
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <Sun className="h-10 w-10 text-muted-foreground/50" />
          <p className="mt-3 text-sm text-muted-foreground">
            Not enough data for your morning briefing
          </p>
          <Button asChild variant="link" size="sm" className="mt-2">
            <Link to="/mock-data">Generate sample data</Link>
          </Button>
        </div>
      </GlassCard>
    )
  }

  const recoveryScore = briefing.recovery.score
  const recoveryColor =
    recoveryScore >= 7 ? 'text-exercise' : recoveryScore >= 4 ? 'text-nutrition' : 'text-heart'
  const recoveryBg =
    recoveryScore >= 7
      ? 'bg-exercise/10'
      : recoveryScore >= 4
      ? 'bg-nutrition/10'
      : 'bg-heart/10'

  const cravingRisk = briefing.cravings.risk_level
  const cravingColor =
    cravingRisk === 'low' ? 'text-exercise' : cravingRisk === 'moderate' ? 'text-nutrition' : 'text-heart'
  const cravingBg =
    cravingRisk === 'low'
      ? 'bg-exercise/10'
      : cravingRisk === 'moderate'
      ? 'bg-nutrition/10'
      : 'bg-heart/10'

  return (
    <GlassCard className={cn('p-6', className)}>
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sun className="h-5 w-5 text-nutrition" />
          <h3 className="font-medium">Morning Briefing</h3>
        </div>
        <Button asChild variant="ghost" size="sm" className="text-xs text-muted-foreground">
          <Link to="/briefing">
            View full briefing
            <ArrowRight className="ml-1 h-3 w-3" />
          </Link>
        </Button>
      </div>

      {/* Greeting */}
      <p className="mb-4 text-sm text-muted-foreground">{briefing.greeting}</p>

      {/* Recovery & Cravings */}
      <div className="grid gap-3 sm:grid-cols-2">
        {/* Recovery */}
        <div className={cn('rounded-xl p-4', recoveryBg)}>
          <div className="mb-2 flex items-center gap-2">
            <Battery className={cn('h-4 w-4', recoveryColor)} />
            <span className="text-sm font-medium">Recovery</span>
          </div>
          <div className="mb-2 flex items-baseline gap-2">
            <span className={cn('text-2xl font-bold tabular-nums', recoveryColor)}>
              {recoveryScore}
            </span>
            <span className="text-sm text-muted-foreground">/10</span>
          </div>
          <p className="text-xs text-muted-foreground">{briefing.recovery.message}</p>
        </div>

        {/* Cravings */}
        <div className={cn('rounded-xl p-4', cravingBg)}>
          <div className="mb-2 flex items-center gap-2">
            <Cookie className={cn('h-4 w-4', cravingColor)} />
            <span className="text-sm font-medium">Cravings Risk</span>
          </div>
          <div className="mb-2">
            <span className={cn('text-lg font-medium capitalize', cravingColor)}>
              {cravingRisk}
            </span>
          </div>
          <p className="text-xs text-muted-foreground line-clamp-2">
            {briefing.cravings.reasoning}
          </p>
        </div>
      </div>

      {/* Top Recommendation */}
      {briefing.recommendations.length > 0 && (
        <div className="mt-4 rounded-lg border border-border bg-background/50 p-3">
          <div className="flex items-start gap-2">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <div>
              <p className="text-sm font-medium">{briefing.recommendations[0].message}</p>
              {briefing.recommendations[0].reasoning && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {briefing.recommendations[0].reasoning}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Anomaly alert */}
      {briefing.anomalies_yesterday.count > 0 && (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-heart/10 px-3 py-2">
          <AlertTriangle className="h-4 w-4 text-heart" />
          <span className="text-xs text-heart">
            {briefing.anomalies_yesterday.count} anomal{briefing.anomalies_yesterday.count === 1 ? 'y' : 'ies'} detected yesterday
          </span>
        </div>
      )}
    </GlassCard>
  )
}
