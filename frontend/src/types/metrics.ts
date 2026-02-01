// Health metric types

export type MetricType = 
  | 'sleep_hours'
  | 'sleep_quality'
  | 'exercise_minutes'
  | 'total_calories'
  | 'protein'
  | 'carbs'
  | 'fats'
  | 'sugar'
  | 'resting_hr'
  | 'hrv_ms'
  | 'blood_pressure_systolic'
  | 'blood_pressure_diastolic'
  | 'weight'
  | 'body_fat'
  | 'glucose'
  | 'recovery_score'

export type MetricColor = 
  | 'sleep'
  | 'exercise'
  | 'nutrition'
  | 'heart'
  | 'body'
  | 'glucose'
  | 'hrv'
  | 'recovery'

export interface MetricValue {
  date: string
  value: number
  unit?: string
}

export interface MetricSummary {
  metric: MetricType
  label: string
  value: number
  unit: string
  color: MetricColor
  trend?: 'up' | 'down' | 'stable'
  percentChange?: number
  optimal?: {
    min: number
    max: number
  }
}

export interface DailySummary {
  date: string
  sleep?: {
    hours: number
    quality: number
    bedtime?: string
    wake_time?: string
  }
  nutrition?: {
    total_calories: number
    protein: number
    carbs: number
    fats: number
    sugar: number
    meals_count: number
  }
  exercise?: {
    total_minutes: number
    total_calories: number
    sessions_count: number
    types: string[]
  }
  vitals?: {
    resting_hr?: number
    hrv_ms?: number
    blood_pressure_systolic?: number
    blood_pressure_diastolic?: number
    spo2?: number
    respiratory_rate?: number
  }
  body?: {
    weight?: number
    body_fat?: number
    muscle_mass?: number
  }
  chronic?: {
    glucose_fasting?: number
    glucose_post_meal?: number
  }
}

export interface HealthScore {
  overall_score: number
  sleep_score: number
  nutrition_score: number
  activity_score: number
  vitals_score: number
  trend: 'improving' | 'stable' | 'declining' | 'unknown'
  computed_at: string
}

export interface HealthScoreDetailed extends HealthScore {
  breakdown: {
    sleep: ScoreFactorDetail
    nutrition: ScoreFactorDetail
    activity: ScoreFactorDetail
    vitals: ScoreFactorDetail
  }
  comparison_to_last_week?: number
  top_improvement_area?: string
  top_strength_area?: string
  insights: string[]
}

export interface ScoreFactorDetail {
  score: number
  factors: string[]
  key_metric?: string
  key_value?: number
}
