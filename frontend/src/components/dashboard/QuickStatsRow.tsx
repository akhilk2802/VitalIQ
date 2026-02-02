import { useMemo } from 'react'
import { cn } from '@/lib/utils'
import { MetricCard } from './MetricCard'
import type { DashboardResponse } from '@/types'

interface QuickStatsRowProps {
  data?: DashboardResponse
  isLoading?: boolean
  className?: string
}

// Estimate steps from exercise data
// Walking: ~1300 steps/km, Running: ~1100 steps/km, Cycling: ~0 steps
// Also estimate from duration: ~100 steps/min for walking-type activities
function estimateStepsFromExercise(exercise: { 
  exercise_type?: string; 
  distance_km?: number; 
  duration_minutes?: number 
}): number {
  const type = exercise.exercise_type?.toLowerCase() || ''
  const distance = exercise.distance_km || 0
  const duration = exercise.duration_minutes || 0
  
  // Cardio activities that involve walking/running
  const walkingTypes = ['walking', 'hiking', 'walk']
  const runningTypes = ['running', 'jogging', 'run', 'cardio']
  
  if (walkingTypes.some(t => type.includes(t))) {
    // Prefer distance if available, else estimate from duration
    return distance > 0 ? Math.round(distance * 1300) : Math.round(duration * 100)
  }
  
  if (runningTypes.some(t => type.includes(t))) {
    return distance > 0 ? Math.round(distance * 1100) : Math.round(duration * 150)
  }
  
  // General activity baseline (HIIT, circuits, etc.)
  if (['hiit', 'circuit', 'crossfit', 'aerobics'].some(t => type.includes(t))) {
    return Math.round(duration * 80)
  }
  
  return 0
}

export function QuickStatsRow({ data, isLoading, className }: QuickStatsRowProps) {
  // Calculate averages from daily_summaries
  const averages = useMemo(() => {
    if (!data?.daily_summaries?.length) {
      return { sleep: 0, exercise: 0, calories: 0, heartRate: 0, hrv: 0, steps: 0 }
    }

    const summaries = data.daily_summaries

    // Sleep: average duration_hours
    const sleepEntries = summaries.filter((d) => d.sleep?.duration_hours)
    const avgSleep = sleepEntries.length > 0
      ? sleepEntries.reduce((sum, d) => sum + (d.sleep?.duration_hours || 0), 0) / sleepEntries.length
      : 0

    // Exercise: average daily minutes (sum all exercises per day, then average)
    const exerciseByDay = summaries.map((d) =>
      (d.exercises || []).reduce((sum, e) => sum + (e.duration_minutes || 0), 0)
    )
    const avgExercise = exerciseByDay.length > 0
      ? exerciseByDay.reduce((sum, mins) => sum + mins, 0) / exerciseByDay.length
      : 0

    // Steps: estimate from exercise data (distance and duration of cardio activities)
    const stepsByDay = summaries.map((d) =>
      (d.exercises || []).reduce((sum, e) => sum + estimateStepsFromExercise(e), 0)
    )
    // Add baseline daily steps (assume ~3000 steps from general daily activity)
    const avgSteps = stepsByDay.length > 0
      ? stepsByDay.reduce((sum, steps) => sum + steps, 0) / stepsByDay.length + 3000
      : 0

    // Calories: average total_calories
    const nutritionEntries = summaries.filter((d) => d.nutrition?.total_calories)
    const avgCalories = nutritionEntries.length > 0
      ? nutritionEntries.reduce((sum, d) => sum + (d.nutrition?.total_calories || 0), 0) / nutritionEntries.length
      : 0

    // Heart rate: average resting_heart_rate from vitals
    const heartRates: number[] = []
    summaries.forEach((d) => {
      (d.vitals || []).forEach((v) => {
        if (v.resting_heart_rate) heartRates.push(v.resting_heart_rate)
      })
    })
    const avgHeartRate = heartRates.length > 0
      ? heartRates.reduce((sum, hr) => sum + hr, 0) / heartRates.length
      : 0

    // HRV: average hrv_ms from vitals
    const hrvValues: number[] = []
    summaries.forEach((d) => {
      (d.vitals || []).forEach((v) => {
        if (v.hrv_ms) hrvValues.push(v.hrv_ms)
      })
    })
    const avgHrv = hrvValues.length > 0
      ? hrvValues.reduce((sum, hrv) => sum + hrv, 0) / hrvValues.length
      : 0

    return {
      sleep: Math.round(avgSleep * 10) / 10,
      exercise: Math.round(avgExercise),
      calories: Math.round(avgCalories),
      heartRate: Math.round(avgHeartRate),
      hrv: Math.round(avgHrv),
      steps: Math.round(avgSteps),
    }
  }, [data?.daily_summaries])

  const metrics = [
    {
      label: 'Avg Sleep',
      value: averages.sleep || undefined,
      unit: 'h',
      color: 'sleep' as const,
      icon: 'Moon',
      formatAsTime: true,
    },
    {
      label: 'Avg Steps',
      value: averages.steps || undefined,
      unit: 'steps',
      color: 'exercise' as const,
      icon: 'Footprints',
    },
    {
      label: 'Avg Exercise',
      value: averages.exercise || undefined,
      unit: 'min',
      color: 'exercise' as const,
      icon: 'Activity',
    },
    {
      label: 'Avg Calories',
      value: averages.calories || undefined,
      unit: 'kcal',
      color: 'nutrition' as const,
      icon: 'Utensils',
    },
    {
      label: 'Avg Heart Rate',
      value: averages.heartRate || undefined,
      unit: 'bpm',
      color: 'heart' as const,
      icon: 'Heart',
    },
    {
      label: 'Avg HRV',
      value: averages.hrv || undefined,
      unit: 'ms',
      color: 'hrv' as const,
      icon: 'HeartPulse',
    },
  ]

  return (
    <div
      className={cn(
        'grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6',
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
