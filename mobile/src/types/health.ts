/**
 * 健康数据类型定义（In 模型，用于上传到后端）
 * 严格对应 backend/app/schemas/health.py 中的 *In 模型
 *
 * 所有 *In 模型用于 POST /api/v1/sync/upload 的 SyncPayload
 * 所有 *Out 模型用于后端响应（移动端仅上传，不使用 Out）
 */

// ========== 基类 ==========

/** 健康样本基类 — 对应 HealthSampleBase */
export interface HealthSampleBase {
  sample_uuid: string;
  source_device?: string | null;
  recorded_at: string; // ISO 8601 datetime
}

// ========== 心率 ==========

/** 心率样本（上传） — 对应 HeartRateIn */
export interface HeartRateIn extends HealthSampleBase {
  bpm: number;
  motion_context?: string | null;
  measurement_type: string; // 默认 "heart_rate"
}

// ========== HRV ==========

/** HRV 样本（上传） — 对应 HRVSampleIn */
export interface HRVSampleIn extends HealthSampleBase {
  sdnn_ms: number;
}

// ========== 活动 ==========

/** 活动样本（上传） — 对应 ActivitySampleIn */
export interface ActivitySampleIn extends HealthSampleBase {
  metric_type: string; // steps / distance / basal_energy / active_energy 等
  value: number;
  duration_seconds?: number | null;
}

// ========== 睡眠 ==========

/** 睡眠阶段（上传） — 对应 SleepStageIn（独立模型，不继承 HealthSampleBase） */
export interface SleepStageIn {
  stage: string; // "awake" | "rem" | "core" | "deep"
  start_time: string; // ISO 8601 datetime
  end_time: string; // ISO 8601 datetime
  duration_minutes: number;
}

/** 睡眠会话（上传） — 对应 SleepSessionIn */
export interface SleepSessionIn extends HealthSampleBase {
  start_time: string; // ISO 8601 datetime
  end_time: string; // ISO 8601 datetime
  total_duration_minutes: number;
  in_bed_duration_minutes?: number | null;
  stages: SleepStageIn[];
}

// ========== 血氧 ==========

/** 血氧样本（上传） — 对应 BloodOxygenSampleIn */
export interface BloodOxygenSampleIn extends HealthSampleBase {
  spo2_percent: number;
  measurement_condition?: string | null;
}

// ========== 体温 ==========

/** 体温样本（上传） — 对应 BodyTemperatureSampleIn */
export interface BodyTemperatureSampleIn extends HealthSampleBase {
  temperature_celsius: number;
  measurement_location?: string | null;
}

// ========== 运动 ==========

/** 运动心率区间（上传） — 对应 WorkoutHRZoneIn（独立模型） */
export interface WorkoutHRZoneIn {
  zone_index: number;
  lower_bound_bpm: number;
  upper_bound_bpm: number;
  duration_seconds: number;
}

/** 运动记录（上传） — 对应 WorkoutRecordIn */
export interface WorkoutRecordIn extends HealthSampleBase {
  workout_type: string;
  start_time: string; // ISO 8601 datetime
  end_time: string; // ISO 8601 datetime
  duration_seconds: number;
  total_energy_kcal?: number | null;
  active_energy_kcal?: number | null;
  distance_meters?: number | null;
  avg_heart_rate?: number | null;
  max_heart_rate?: number | null;
  min_heart_rate?: number | null;
  hr_zones: WorkoutHRZoneIn[];
}

// ========== 心电图 ==========

/** ECG 记录（上传） — 对应 ECGRecordIn */
export interface ECGRecordIn extends HealthSampleBase {
  classification: string;
  average_heart_rate?: number | null;
  symptoms_status?: string | null;
  voltage_measurements?: string | null; // JSON 字符串
}

// ========== 呼吸率 ==========

/** 呼吸率样本（上传） — 对应 RespiratoryRateSampleIn */
export interface RespiratoryRateSampleIn extends HealthSampleBase {
  breaths_per_minute: number;
}

// ========== 噪声 ==========

/** 噪声暴露样本（上传） — 对应 NoiseExposureSampleIn */
export interface NoiseExposureSampleIn extends HealthSampleBase {
  decibels: number;
  duration_seconds?: number | null;
}

// ========== 正念 ==========

/** 正念会话（上传） — 对应 MindfulnessSessionIn */
export interface MindfulnessSessionIn extends HealthSampleBase {
  start_time: string; // ISO 8601 datetime
  end_time: string; // ISO 8601 datetime
  duration_minutes: number;
}

// ========== HealthKit 权限状态 ==========

/** 单个数据类型的权限状态（本地 UI 用，非后端模型） */
export interface HealthPermissionStatus {
  key: string; // 数据类型 key（如 'heartRate'）
  label: string; // 中文标签（如 '心率'）
  status: 'authorized' | 'denied' | 'notDetermined';
}
