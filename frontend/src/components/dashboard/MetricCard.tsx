import { cn } from '@/lib/utils'
import { formatNumber, formatDuration, formatHours } from '@/lib/utils'
import { METRIC_COLORS, METRIC_BG_COLORS } from '@/lib/constants'
import { Skeleton } from '@/components/ui/skeleton'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import {
  Moon,
  Activity,
  Utensils,
  Heart,
  Scale,
  Droplet,
  HeartPulse,
  Battery,
  Footprints,
  type LucideIcon,
} from 'lucide-react'
import type { MetricColor } from '@/types'

const iconMap: Record<string, LucideIcon> = {
  Moon,
  Activity,
  Utensils,
  Heart,
  Scale,
  Droplet,
  HeartPulse,
  Battery,
  Footprints,
}

interface MetricCardProps {
  label: string
  value: number | null | undefined
  unit: string
  color: MetricColor
  icon: string
  trend?: 'up' | 'down' | 'stable'
  percentChange?: number
  isLoading?: boolean
  onClick?: () => void
  className?: string
  formatAsTime?: boolean
}

export function MetricCard({
  label,
  value,
  unit,
  color,
  icon,
  trend,
  percentChange,
  isLoading = false,
  onClick,
  className,
  formatAsTime = false,
}: MetricCardProps) {
  const Icon = iconMap[icon] || Activity
  const metricColor = METRIC_COLORS[color]
  const metricBgColor = METRIC_BG_COLORS[color]

  const getTrendIcon = () => {
    if (trend === 'up') return <TrendingUp className="h-3 w-3" />
    if (trend === 'down') return <TrendingDown className="h-3 w-3" />
    return <Minus className="h-3 w-3" />
  }

  const formatValue = (val: number) => {
    if (formatAsTime) {
      // formatAsTime is used for sleep which is in hours
      return formatHours(val)
    }
    if (val >= 1000) {
      return formatNumber(val / 1000, 1) + 'k'
    }
    return formatNumber(val, val % 1 !== 0 ? 1 : 0)
  }

  if (isLoading) {
    return (
      <div className={cn('metric-card p-4', className)}>
        <div className="flex items-start justify-between">
          <Skeleton className="h-10 w-10 rounded-lg" />
          <Skeleton className="h-4 w-12" />
        </div>
        <div className="mt-3">
          <Skeleton className="h-7 w-20" />
          <Skeleton className="mt-1 h-4 w-16" />
        </div>
      </div>
    )
  }

  return (
    <div
      className={cn(
        'metric-card cursor-pointer p-4 transition-all',
        onClick && 'hover:scale-[1.02]',
        className
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <div className="flex items-start justify-between">
        <div
          className="flex h-10 w-10 items-center justify-center rounded-lg"
          style={{ backgroundColor: metricBgColor }}
        >
          <Icon className="h-5 w-5" style={{ color: metricColor }} />
        </div>
        {trend && percentChange !== undefined && (
          <div
            className={cn(
              'flex items-center gap-1 text-xs font-medium',
              trend === 'up' && 'text-exercise',
              trend === 'down' && 'text-heart',
              trend === 'stable' && 'text-muted-foreground'
            )}
          >
            {getTrendIcon()}
            <span>{Math.abs(percentChange).toFixed(0)}%</span>
          </div>
        )}
      </div>

      <div className="mt-3">
        <div className="flex items-baseline gap-1">
          <span
            className="text-2xl font-bold tabular-nums"
            style={{ color: value === null || value === undefined ? undefined : metricColor }}
          >
            {value === null || value === undefined ? '—' : formatValue(value)}
          </span>
          {value !== null && value !== undefined && unit && !formatAsTime && (
            <span className="text-sm text-muted-foreground">{unit}</span>
          )}
        </div>
        <p className="mt-0.5 text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  )
}
