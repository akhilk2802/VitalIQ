import { cn } from '@/lib/utils'
import { MetricCard } from './MetricCard'
import type { DashboardResponse } from '@/types'

interface QuickStatsRowProps {
  data?: DashboardResponse
  isLoading?: boolean
  className?: string
}

export function QuickStatsRow({ data, isLoading, className }: QuickStatsRowProps) {
  const metrics = [
    {
      label: 'Sleep',
      value: data?.averages?.sleep_hours,
      unit: 'h',
      color: 'sleep' as const,
      icon: 'Moon',
      formatAsTime: true,
    },
    {
      label: 'Exercise',
      value: data?.totals?.exercise_minutes
        ? Math.round(data.totals.exercise_minutes / (data.period?.days || 1))
        : undefined,
      unit: 'min',
      color: 'exercise' as const,
      icon: 'Activity',
    },
    {
      label: 'Calories',
      value: data?.averages?.daily_calories,
      unit: 'kcal',
      color: 'nutrition' as const,
      icon: 'Utensils',
    },
    {
      label: 'Heart Rate',
      value: data?.averages?.resting_hr,
      unit: 'bpm',
      color: 'heart' as const,
      icon: 'Heart',
    },
    {
      label: 'HRV',
      value: data?.averages?.hrv_ms,
      unit: 'ms',
      color: 'hrv' as const,
      icon: 'HeartPulse',
    },
  ]

  return (
    <div
      className={cn(
        'grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5',
        className
      )}
    >
      {metrics.map((metric) => (
        <MetricCard
          key={metric.label}
          label={metric.label}
          value={metric.value}
          unit={metric.unit}
          color={metric.color}
          icon={metric.icon}
          isLoading={isLoading}
          formatAsTime={metric.formatAsTime}
        />
      ))}
    </div>
  )
}
