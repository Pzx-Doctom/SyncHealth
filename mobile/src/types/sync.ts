/**
 * 同步相关类型定义
 * 严格对应 backend/app/schemas/sync.py
 */

import type {
  HeartRateIn,
  HRVSampleIn,
  ActivitySampleIn,
  SleepSessionIn,
  BloodOxygenSampleIn,
  BodyTemperatureSampleIn,
  WorkoutRecordIn,
  ECGRecordIn,
  RespiratoryRateSampleIn,
  NoiseExposureSampleIn,
  MindfulnessSessionIn,
} from './health';

// ========== 上传模型 ==========

/** 设备信息 — 对应 DeviceInfo */
export interface DeviceInfo {
  model: string;
  os_version: string;
  app_version: string;
}

/** 同步时间窗口 — 对应 SyncWindow */
export interface SyncWindow {
  start: string; // ISO 8601 datetime
  end: string; // ISO 8601 datetime
}

/** 同步上传数据载荷 — 对应 SyncPayload */
export interface SyncPayload {
  device_info: DeviceInfo;
  sync_window: SyncWindow;
  heart_rates: HeartRateIn[];
  hrv_samples: HRVSampleIn[];
  activity_samples: ActivitySampleIn[];
  sleep_sessions: SleepSessionIn[];
  blood_oxygen_samples: BloodOxygenSampleIn[];
  body_temperature_samples: BodyTemperatureSampleIn[];
  workout_records: WorkoutRecordIn[];
  ecg_records: ECGRecordIn[];
  respiratory_rate_samples: RespiratoryRateSampleIn[];
  noise_exposure_samples: NoiseExposureSampleIn[];
  mindfulness_sessions: MindfulnessSessionIn[];
}

// ========== 响应模型 ==========

/** 同步上传响应 — 对应 SyncResponse */
export interface SyncResponse {
  sync_id: number;
  records_received: number;
  records_inserted: number;
  records_deduplicated: number;
  status: string;
}

/** 同步状态响应 — 对应 SyncStatusResponse */
export interface SyncStatusResponse {
  last_sync_at: string | null;
  last_sync_status: string | null;
  records_inserted: number;
}

/** 同步历史日志 — 对应 SyncLogResponse */
export interface SyncLogResponse {
  id: number;
  started_at: string;
  completed_at: string | null;
  status: string;
  records_received: number;
  records_inserted: number;
  records_deduplicated: number;
  error_message: string | null;
}

// ========== 本地状态类型（非后端模型） ==========

/** 同步状态枚举 */
export type SyncStatus = 'idle' | 'syncing' | 'success' | 'error';

/** 同步结果（本地存储） */
export interface SyncResult {
  status: SyncStatus;
  response?: SyncResponse;
  error?: string;
  timestamp: string; // ISO 8601
}

/** 创建空的 SyncPayload */
export function createEmptyPayload(window: SyncWindow, deviceInfo: DeviceInfo): SyncPayload {
  return {
    device_info: deviceInfo,
    sync_window: window,
    heart_rates: [],
    hrv_samples: [],
    activity_samples: [],
    sleep_sessions: [],
    blood_oxygen_samples: [],
    body_temperature_samples: [],
    workout_records: [],
    ecg_records: [],
    respiratory_rate_samples: [],
    noise_exposure_samples: [],
    mindfulness_sessions: [],
  };
}
