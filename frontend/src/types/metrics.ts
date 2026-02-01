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

// Sleep entry from backend
export interface SleepEntry {
  id: string
  user_id: string
  date: string
  bedtime: string
  wake_time: string
  duration_hours: number
  quality_score: number
  deep_sleep_minutes?: number
  rem_sleep_minutes?: number
  awakenings?: number
  notes?: string
  created_at: string
  }

// Nutrition summary from backend
export interface NutritionSummary {
  date: string
    total_calories: number
  total_protein_g: number
  total_carbs_g: number
  total_fats_g: number
  total_sugar_g: number
  total_fiber_g: number
  total_sodium_mg: number
  meal_count: number
  entries: unknown[]
}

// Exercise entry from backend
export interface ExerciseEntry {
  id: string
  user_id: string
  date: string
  exercise_type: string
  exercise_name: string
  duration_minutes: number
  intensity?: string
  calories_burned?: number
  heart_rate_avg?: number
  heart_rate_max?: number
  distance_km?: number
  notes?: string
  created_at: string
}

// Vital signs from backend
export interface VitalSignsEntry {
  id: string
  user_id: string
  date: string
  time_of_day?: string
  resting_heart_rate?: number
    hrv_ms?: number
    blood_pressure_systolic?: number
    blood_pressure_diastolic?: number
  respiratory_rate?: number
  body_temperature?: number
    spo2?: number
  created_at: string
}

// Body metrics from backend
export interface BodyMetricsEntry {
  id: string
  user_id: string
  date: string
  weight_kg?: number
  body_fat_pct?: number
  muscle_mass_kg?: number
  bmi?: number
  waist_cm?: number
  notes?: string
  created_at: string
}

// Chronic metrics from backend
export interface ChronicMetricsEntry {
  id: string
  user_id: string
  date: string
  time_of_day?: string
  condition_type?: string
  blood_glucose_mgdl?: number
  insulin_units?: number
  hba1c_pct?: number
  cholesterol_total?: number
  cholesterol_ldl?: number
  cholesterol_hdl?: number
  triglycerides?: number
  notes?: string
  created_at: string
}

// Anomaly from backend
export interface AnomalyEntry {
  id: string
  user_id: string
  date: string
  source_table: string
  metric_name: string
  metric_value: number
  baseline_value?: number
  detector_type: string
  severity: string
  anomaly_score: number
  explanation?: string
  is_acknowledged: boolean
  detected_at: string
}

// Daily summary matching backend DailySummary schema
export interface DailySummary {
  date: string
  nutrition?: NutritionSummary
  sleep?: SleepEntry
  exercises: ExerciseEntry[]
  vitals: VitalSignsEntry[]
  body_metrics?: BodyMetricsEntry
  chronic_metrics: ChronicMetricsEntry[]
  anomalies: AnomalyEntry[]
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
