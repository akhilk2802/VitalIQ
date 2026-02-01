import type { DailySummary, HealthScore } from './metrics'

// Dashboard types
export interface DashboardResponse {
  period: {
    start_date: string
    end_date: string
    days: number
  }
  daily_summaries: DailySummary[]
  totals: {
    sleep_hours: number
    exercise_minutes: number
    total_calories: number
    meals_logged: number
    workouts_logged: number
  }
  averages: {
    sleep_hours: number
    sleep_quality: number
    daily_calories: number
    daily_protein: number
    resting_hr: number
    hrv_ms: number
  }
}

// Anomaly types
export interface Anomaly {
  id: string
  user_id: string
  date: string
  metric_name: string
  value: number
  baseline_value: number
  deviation: number
  severity: 'low' | 'medium' | 'high'
  detector_type: 'zscore' | 'isolation_forest' | 'ensemble'
  explanation?: string
  is_acknowledged: boolean
  detected_at: string
}

export interface AnomalyDetectionResult {
  total_anomalies: number
  new_anomalies: number
  anomalies: Anomaly[]
}

export interface AnomalySummary {
  total: number
  by_severity: Record<string, number>
  by_metric: Record<string, number>
  most_common_metric?: string
}

// Correlation types
export interface Correlation {
  id: string
  user_id: string
  metric_a: string
  metric_b: string
  correlation_type: 'same_day' | 'time_lagged' | 'granger_causal' | 'mutual_info'
  correlation_value: number
  p_value?: number
  confidence_score: number
  strength: 'weak' | 'moderate' | 'strong' | 'very_strong'
  direction: 'positive' | 'negative'
  lag_days?: number
  causal_direction?: 'a_causes_b' | 'b_causes_a' | 'bidirectional' | 'none'
  is_significant: boolean
  is_actionable: boolean
  insight?: string
  recommendation?: string
  created_at: string
}

export interface CorrelationSummary {
  metric_a: string
  metric_b: string
  correlation_type: string
  correlation_value: number
  strength: string
  lag_days?: number
  causal_direction?: string
  insight?: string
  is_actionable: boolean
}

// Briefing types
export interface RecoveryPrediction {
  score: number
  status: string
  message: string
  factors: Record<string, number>
  confidence: number
  recommendations: string[]
}

export interface CravingPrediction {
  craving_type: string
  risk_level: number
  intensity: string
  reasoning: string
  peak_time?: string
  countermeasures: string[]
}

export interface CravingsForecast {
  primary_craving: CravingPrediction
  secondary_cravings: CravingPrediction[]
  overall_risk: string
  contributing_factors: string[]
}

export interface MorningBriefing {
  briefing_date: string
  greeting: string
  recovery: {
    score: number
    status: string
    message: string
    top_factor?: string
  }
  cravings: {
    primary_type: string
    risk_level: string
    reasoning: string
    countermeasures: string[]
    peak_time?: string
  }
  recommendations: Recommendation[]
  anomalies_yesterday: {
    count: number
    most_recent?: string
    severity?: string
  }
  correlations_to_watch: {
    metrics: string
    insight: string
  }[]
  health_score?: number
  generated_at: string
  confidence: number
}

export interface Recommendation {
  type: 'exercise' | 'nutrition' | 'sleep' | 'wellness'
  priority: 'high' | 'medium' | 'low'
  message: string
  reasoning?: string
}

// Chat types
export interface ChatSession {
  id: string
  user_id: string
  title?: string
  is_active: boolean
  created_at: string
  updated_at: string
  message_count?: number
}

export interface ChatMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  context_used?: boolean
  tokens_used?: number
  created_at: string
}

// Natural language query types
export interface QueryResponse {
  query: string
  intent: string
  answer: string
  data?: Record<string, unknown>
  confidence: number
  follow_up_suggestions: string[]
}

// Integration types
export interface Provider {
  id: string
  name: string
  description: string
  supported_data_types: string[]
  requires_mobile?: boolean
}

export interface Connection {
  id: string
  user_id: string
  provider: string
  status: 'pending' | 'connected' | 'disconnected' | 'error'
  last_sync_at?: string
  created_at: string
}

// Mock data types
export interface PersonaInfo {
  id: string
  name: string
  description: string
}

export interface MockDataResult {
  message: string
  persona: string
  persona_name: string
  days: number
  entries_created: Record<string, number>
  total_entries: number
  anomaly_days: number[]
  embedded_patterns: string[]
  data_cleared: boolean
}

// Export types
export interface ExportSummary {
  period: {
    start: string
    end: string
  }
  sections: {
    sleep?: {
      total_nights: number
      avg_duration: number
      avg_quality: number
      best_night: number
      worst_night: number
    }
    exercise?: {
      total_workouts: number
      active_days: number
      total_minutes: number
      total_calories: number
      avg_workout_duration: number
    }
    nutrition?: {
      total_meals: number
      avg_daily_calories: number
      avg_daily_protein: number
    }
    anomalies?: {
      total: number
      by_severity: Record<string, number>
      most_common_metric?: string
    }
  }
}
