/**
 * 模拟健康数据服务 — Android 调试用
 *
 * 在 Android 端（Windows 开发环境）无法使用 HealthKit，
 * 此服务生成格式合规的模拟数据，确保完整的同步流程可以调试。
 *
 * iOS 端由 healthService.ts 代替，通过 Platform.select 自动切换。
 */
import type { HealthPermissionStatus } from '@/types/health';
import type { SyncPayload } from '@/types/sync';
import { getDeviceInfo } from '@/utils/platformUtils';

/** 随机数工具 */
function randomBetween(min: number, max: number): number {
  return Math.round((Math.random() * (max - min) + min) * 100) / 100;
}

function randomUUID(): string {
  return `mock-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

/** 生成过去 N 天内的随机 ISO 日期 */
function randomPastDate(daysAgo: number): string {
  const now = Date.now();
  const past = now - Math.floor(Math.random() * daysAgo * 86400000);
  return new Date(past).toISOString();
}

// ========== 模拟权限（Android 永远返回 authorized） ==========

export async function requestHealthPermissions(): Promise<boolean> {
  // Android 模拟：始终授权
  return true;
}

export async function getHealthPermissionStatuses(): Promise<HealthPermissionStatus[]> {
  return [
    { key: 'heartRate', label: '心率', status: 'authorized' },
    { key: 'hrv', label: '心率变异性 (HRV)', status: 'authorized' },
    { key: 'steps', label: '步数', status: 'authorized' },
    { key: 'bloodOxygen', label: '血氧饱和度', status: 'authorized' },
    { key: 'bodyTemperature', label: '体温', status: 'authorized' },
    { key: 'respiratoryRate', label: '呼吸频率', status: 'authorized' },
    { key: 'noiseExposure', label: '环境噪声', status: 'authorized' },
    { key: 'sleep', label: '睡眠分析', status: 'authorized' },
    { key: 'mindfulness', label: '正念会话', status: 'authorized' },
  ];
}

// ========== 模拟数据生成 ==========

export async function fetchHealthData(days: number = 7): Promise<SyncPayload> {
  const now = new Date();
  const startDate = new Date(now);
  startDate.setDate(startDate.getDate() - days);

  // 模拟少量延迟，让 UI 显示加载状态
  await new Promise((resolve) => setTimeout(resolve, 800));

  const deviceInfo = getDeviceInfo();

  // 生成模拟心率数据（最近 7 天，每天约 10 条）
  const heartRates = Array.from({ length: 50 }, () => ({
    sample_uuid: randomUUID(),
    source_device: 'MockDevice',
    recorded_at: randomPastDate(days),
    bpm: randomBetween(55, 100),
    motion_context: null,
    measurement_type: 'heart_rate',
  }));

  // 模拟 HRV 数据
  const hrvSamples = Array.from({ length: 30 }, () => ({
    sample_uuid: randomUUID(),
    source_device: 'MockDevice',
    recorded_at: randomPastDate(days),
    sdnn_ms: randomBetween(20, 80),
  }));

  // 模拟活动数据（步数 + 能量 + 距离）
  const activitySamples = [
    ...Array.from({ length: 7 }, () => ({
      sample_uuid: randomUUID(),
      source_device: 'MockDevice',
      recorded_at: randomPastDate(days),
      metric_type: 'steps',
      value: randomBetween(3000, 12000),
      duration_seconds: null,
    })),
    ...Array.from({ length: 7 }, () => ({
      sample_uuid: randomUUID(),
      source_device: 'MockDevice',
      recorded_at: randomPastDate(days),
      metric_type: 'active_energy',
      value: randomBetween(150, 600),
      duration_seconds: null,
    })),
  ];

  // 模拟睡眠数据（最近 7 天，每天 1 条会话）
  const sleepSessions = Array.from({ length: 7 }, (_, i) => {
    const baseDate = new Date(startDate);
    baseDate.setDate(baseDate.getDate() + i);
    baseDate.setHours(23, 0, 0, 0);
    const start = baseDate.toISOString();
    const endMs = baseDate.getTime() + randomBetween(6, 9) * 3600000;
    const end = new Date(endMs).toISOString();
    const totalMinutes = (endMs - baseDate.getTime()) / 60000;

    return {
      sample_uuid: randomUUID(),
      source_device: 'MockDevice',
      recorded_at: start,
      start_time: start,
      end_time: end,
      total_duration_minutes: totalMinutes,
      in_bed_duration_minutes: null,
      stages: [
        { stage: 'core', start_time: start, end_time: new Date(baseDate.getTime() + 180 * 60000).toISOString(), duration_minutes: 180 },
        { stage: 'deep', start_time: new Date(baseDate.getTime() + 180 * 60000).toISOString(), end_time: new Date(baseDate.getTime() + 240 * 60000).toISOString(), duration_minutes: 60 },
        { stage: 'rem', start_time: new Date(baseDate.getTime() + 300 * 60000).toISOString(), end_time: new Date(baseDate.getTime() + 360 * 60000).toISOString(), duration_minutes: 60 },
      ],
    };
  });

  // 模拟血氧
  const bloodOxygenSamples = Array.from({ length: 20 }, () => ({
    sample_uuid: randomUUID(),
    source_device: 'MockDevice',
    recorded_at: randomPastDate(days),
    spo2_percent: randomBetween(95, 100),
    measurement_condition: null,
  }));

  // 模拟体温
  const bodyTemperatureSamples = Array.from({ length: 5 }, () => ({
    sample_uuid: randomUUID(),
    source_device: 'MockDevice',
    recorded_at: randomPastDate(days),
    temperature_celsius: randomBetween(36.1, 37.2),
    measurement_location: null,
  }));

  // 模拟运动记录（最近 7 天 2-3 条）
  const workoutTypes = ['running', 'cycling', 'walking', 'yoga'];
  const workoutRecords = Array.from({ length: 3 }, () => {
    const startTime = randomPastDate(days);
    const durationSec = randomBetween(1200, 5400);
    return {
      sample_uuid: randomUUID(),
      source_device: 'MockDevice',
      recorded_at: startTime,
      workout_type: workoutTypes[Math.floor(Math.random() * workoutTypes.length)],
      start_time: startTime,
      end_time: new Date(new Date(startTime).getTime() + durationSec * 1000).toISOString(),
      duration_seconds: durationSec,
      total_energy_kcal: randomBetween(100, 500),
      active_energy_kcal: randomBetween(80, 400),
      distance_meters: randomBetween(1000, 10000),
      avg_heart_rate: randomBetween(100, 160),
      max_heart_rate: randomBetween(150, 190),
      min_heart_rate: randomBetween(60, 80),
      hr_zones: [] as Array<{ zone_index: number; lower_bound_bpm: number; upper_bound_bpm: number; duration_seconds: number }>,
    };
  });

  // 模拟呼吸率
  const respiratoryRateSamples = Array.from({ length: 20 }, () => ({
    sample_uuid: randomUUID(),
    source_device: 'MockDevice',
    recorded_at: randomPastDate(days),
    breaths_per_minute: randomBetween(12, 20),
  }));

  // 模拟噪声暴露
  const noiseExposureSamples = Array.from({ length: 15 }, () => ({
    sample_uuid: randomUUID(),
    source_device: 'MockDevice',
    recorded_at: randomPastDate(days),
    decibels: randomBetween(30, 85),
    duration_seconds: null,
  }));

  // 模拟正念会话
  const mindfulnessSessions = Array.from({ length: 3 }, () => {
    const startTime = randomPastDate(days);
    const durationMin = randomBetween(5, 30);
    return {
      sample_uuid: randomUUID(),
      source_device: 'MockDevice',
      recorded_at: startTime,
      start_time: startTime,
      end_time: new Date(new Date(startTime).getTime() + durationMin * 60000).toISOString(),
      duration_minutes: durationMin,
    };
  });

  return {
    device_info: deviceInfo,
    sync_window: {
      start: startDate.toISOString(),
      end: now.toISOString(),
    },
    heart_rates: heartRates,
    hrv_samples: hrvSamples,
    activity_samples: activitySamples,
    sleep_sessions: sleepSessions,
    blood_oxygen_samples: bloodOxygenSamples,
    body_temperature_samples: bodyTemperatureSamples,
    workout_records: workoutRecords,
    ecg_records: [], // ECG 暂不模拟
    respiratory_rate_samples: respiratoryRateSamples,
    noise_exposure_samples: noiseExposureSamples,
    mindfulness_sessions: mindfulnessSessions,
  };
}
