export interface DashboardSummary {
  date: string
  steps: number
  active_energy_kcal: number
  resting_energy_kcal: number
  distance_meters: number
  flights_climbed: number
  avg_heart_rate?: number
  resting_heart_rate?: number
  sleep_hours?: number
  spo2_percent?: number
  stand_hours: number
  last_sync_at?: string
}

export interface TrendDataPoint {
  date: string
  value?: number
}

export interface DashboardTrends {
  period: string
  steps: TrendDataPoint[]
  heart_rate: TrendDataPoint[]
  sleep: TrendDataPoint[]
  active_energy: TrendDataPoint[]
  spo2: TrendDataPoint[]
}

export interface HealthScore {
  overall_score: number
  activity_score: number
  sleep_score: number
  heart_score: number
  vitals_score: number
  computed_at: string
}
