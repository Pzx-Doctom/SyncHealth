export interface HealthSampleBase {
  sample_uuid: string
  source_device?: string
  recorded_at: string
}

export interface HeartRateOut extends HealthSampleBase {
  id: number
  synced_at: string
  bpm: number
  motion_context?: string
  measurement_type: string
}

export interface HRVSampleOut extends HealthSampleBase {
  id: number
  synced_at: string
  sdnn_ms: number
}

export interface ActivitySampleOut extends HealthSampleBase {
  id: number
  synced_at: string
  metric_type: string
  value: number
  duration_seconds?: number
}

export interface SleepStageOut {
  id: number
  stage: string
  start_time: string
  end_time: string
  duration_minutes: number
}

export interface SleepSessionOut {
  id: number
  sample_uuid: string
  source_device?: string
  recorded_at: string
  synced_at: string
  start_time: string
  end_time: string
  total_duration_minutes: number
  in_bed_duration_minutes?: number
  stages: SleepStageOut[]
}

export interface BloodOxygenSampleOut extends HealthSampleBase {
  id: number
  synced_at: string
  spo2_percent: number
  measurement_condition?: string
}

export interface BodyTemperatureSampleOut extends HealthSampleBase {
  id: number
  synced_at: string
  temperature_celsius: number
  measurement_location?: string
}

export interface WorkoutHRZoneOut {
  id: number
  zone_index: number
  lower_bound_bpm: number
  upper_bound_bpm: number
  duration_seconds: number
}

export interface WorkoutRecordOut {
  id: number
  sample_uuid: string
  source_device?: string
  recorded_at: string
  synced_at: string
  workout_type: string
  start_time: string
  end_time: string
  duration_seconds: number
  total_energy_kcal?: number
  active_energy_kcal?: number
  distance_meters?: number
  avg_heart_rate?: number
  max_heart_rate?: number
  min_heart_rate?: number
  hr_zones: WorkoutHRZoneOut[]
}

export interface ECGRecordOut extends HealthSampleBase {
  id: number
  synced_at: string
  classification: string
  average_heart_rate?: number
  symptoms_status?: string
  voltage_measurements?: string
}

export interface RespiratoryRateSampleOut extends HealthSampleBase {
  id: number
  synced_at: string
  breaths_per_minute: number
}

export interface NoiseExposureSampleOut extends HealthSampleBase {
  id: number
  synced_at: string
  decibels: number
  duration_seconds?: number
}

export interface MindfulnessSessionOut extends HealthSampleBase {
  id: number
  synced_at: string
  start_time: string
  end_time: string
  duration_minutes: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
