import { cn } from '@/lib/utils'
import { GlassCard } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface HealthScoreRingProps {
  score?: number
  trend?: 'improving' | 'stable' | 'declining' | 'unknown'
  percentChange?: number
  isLoading?: boolean
  className?: string
}

export function HealthScoreRing({
  score = 0,
  trend = 'unknown',
  percentChange,
  isLoading = false,
  className,
}: HealthScoreRingProps) {
  // Calculate stroke-dashoffset for the ring (circumference = 2 * PI * r = 2 * 3.14159 * 45 ≈ 283)
  const circumference = 283
  const progress = (score / 100) * circumference
  const offset = circumference - progress

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-exercise stroke-exercise'
    if (score >= 60) return 'text-primary stroke-primary'
    if (score >= 40) return 'text-nutrition stroke-nutrition'
    return 'text-heart stroke-heart'
  }

  const getTrendIcon = () => {
    switch (trend) {
      case 'improving':
        return <TrendingUp className="h-4 w-4 text-exercise" />
      case 'declining':
        return <TrendingDown className="h-4 w-4 text-heart" />
      default:
        return <Minus className="h-4 w-4 text-muted-foreground" />
    }
  }

  const getTrendText = () => {
    if (percentChange === undefined || percentChange === 0) return 'Stable'
    const sign = percentChange > 0 ? '+' : ''
    return `${sign}${percentChange.toFixed(1)}%`
  }

  if (isLoading) {
    return (
      <GlassCard className={cn('p-6', className)}>
        <div className="flex items-center gap-6">
          <Skeleton className="h-32 w-32 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-5 w-24" />
            <Skeleton className="h-8 w-16" />
            <Skeleton className="h-4 w-20" />
          </div>
        </div>
      </GlassCard>
    )
  }

  return (
    <GlassCard className={cn('p-6', className)}>
      <div className="flex items-center gap-6">
        {/* Score ring */}
        <div className="relative h-32 w-32">
          <svg className="h-32 w-32 -rotate-90 transform">
            {/* Background ring */}
            <circle
              cx="64"
              cy="64"
              r="45"
              fill="none"
              stroke="currentColor"
              strokeWidth="10"
              className="text-muted/30"
            />
            {/* Progress ring */}
            <circle
              cx="64"
              cy="64"
              r="45"
              fill="none"
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              className={cn('health-score-ring transition-all duration-1000', getScoreColor(score))}
            />
          </svg>
          {/* Score number */}
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={cn('text-4xl font-bold tabular-nums', getScoreColor(score).split(' ')[0])}>
              {score}
            </span>
          </div>
        </div>

        {/* Score details */}
        <div className="space-y-2">
          <h3 className="text-lg font-medium text-muted-foreground">Health Score</h3>
          <div className="flex items-center gap-2">
            {getTrendIcon()}
            <span
              className={cn(
                'text-sm font-medium',
                trend === 'improving' && 'text-exercise',
                trend === 'declining' && 'text-heart',
                (trend === 'stable' || trend === 'unknown') && 'text-muted-foreground'
              )}
            >
              {getTrendText()}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            {score >= 80
              ? 'Excellent! Keep it up'
              : score >= 60
              ? 'Good progress'
              : score >= 40
              ? 'Room for improvement'
              : 'Let\'s work on this together'}
          </p>
        </div>
      </div>
    </GlassCard>
  )
}
