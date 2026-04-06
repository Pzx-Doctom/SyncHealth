/**
 * HealthKit 健康数据服务 — iOS Only
 *
 * 使用 @kingstinct/react-native-healthkit 从 Apple Health 读取 11 种健康数据，
 * 并转换为后端 SyncPayload 所需的 In 类型格式。
 *
 * Android 端不会调用此文件，由 mockHealthService.ts 代替。
 */
import {
  requestAuthorization,
  authorizationStatusFor,
  queryQuantitySamples,
  queryCategorySamples,
  queryWorkoutSamples,
  QuantityTypeIdentifier,
  CategoryTypeIdentifier,
} from '@kingstinct/react-native-healthkit';
import type {
  HeartRateIn,
  HRVSampleIn,
  ActivitySampleIn,
  SleepSessionIn,
  SleepStageIn,
  BloodOxygenSampleIn,
  BodyTemperatureSampleIn,
  WorkoutRecordIn,
  RespiratoryRateSampleIn,
  NoiseExposureSampleIn,
  MindfulnessSessionIn,
} from '@/types/health';
import { HEALTHKIT_READ_PERMISSIONS } from '@/constants/healthDataTypes';
import type { HealthPermissionStatus } from '@/types/health';
import { HEALTH_DATA_LABELS } from '@/constants/healthDataTypes';
import type { SyncPayload } from '@/types/sync';
import { getDeviceInfo } from '@/utils/platformUtils';

/** 同步时间窗口（默认 7 天） */
const DEFAULT_SYNC_DAYS = 7;

// ========== 权限管理 ==========

/** 请求 HealthKit 权限 */
export async function requestHealthPermissions(): Promise<boolean> {
  try {
    const granted = await requestAuthorization({
      read: HEALTHKIT_READ_PERMISSIONS,
      write: [],
    });
    return granted;
  } catch (error) {
    console.error('请求 HealthKit 权限失败:', error);
    return false;
  }
}

/** 获取各数据类型的权限状态 */
export async function getHealthPermissionStatuses(): Promise<HealthPermissionStatus[]> {
  const statuses: HealthPermissionStatus[] = [];

  const typeMap: Array<{ key: string; identifier: string }> = [
    { key: 'heartRate', identifier: QuantityTypeIdentifier.HeartRate },
    { key: 'hrv', identifier: QuantityTypeIdentifier.HeartRateVariabilitySDNN },
    { key: 'steps', identifier: QuantityTypeIdentifier.StepCount },
    { key: 'bloodOxygen', identifier: QuantityTypeIdentifier.BloodOxygenSaturation },
    { key: 'bodyTemperature', identifier: QuantityTypeIdentifier.BodyTemperature },
    { key: 'respiratoryRate', identifier: QuantityTypeIdentifier.RespiratoryRate },
    { key: 'noiseExposure', identifier: QuantityTypeIdentifier.EnvironmentalAudioExposure },
    { key: 'sleep', identifier: CategoryTypeIdentifier.SleepAnalysis },
    { key: 'mindfulness', identifier: CategoryTypeIdentifier.MindfulSession },
  ];

  for (const { key, identifier } of typeMap) {
    try {
      const status = authorizationStatusFor(identifier);
      const mappedStatus: HealthPermissionStatus['status'] =
        status === 'authorized' ? 'authorized' :
        status === 'denied' ? 'denied' : 'notDetermined';

      statuses.push({
        key,
        label: HEALTH_DATA_LABELS[key] || key,
        status: mappedStatus,
      });
    } catch {
      statuses.push({
        key,
        label: HEALTH_DATA_LABELS[key] || key,
        status: 'notDetermined',
      });
    }
  }

  return statuses;
}

// ========== 数据查询 ==========

/** 查询所有健康数据并构建 SyncPayload */
export async function fetchHealthData(days: number = DEFAULT_SYNC_DAYS): Promise<SyncPayload> {
  const now = new Date();
  const startDate = new Date(now);
  startDate.setDate(startDate.getDate() - days);

  const syncWindow = {
    start: startDate.toISOString(),
    end: now.toISOString(),
  };

  const deviceInfo = getDeviceInfo();

  // 并行查询所有数据类型
  const [
    heartRates,
    hrvSamples,
    activitySamples,
    sleepSessions,
    bloodOxygenSamples,
    bodyTemperatureSamples,
    workoutRecords,
    respiratoryRateSamples,
    noiseExposureSamples,
    mindfulnessSessions,
  ] = await Promise.all([
    queryHeartRates(startDate, now),
    queryHRV(startDate, now),
    queryActivities(startDate, now),
    querySleep(startDate, now),
    queryBloodOxygen(startDate, now),
    queryBodyTemperature(startDate, now),
    queryWorkouts(startDate, now),
    queryRespiratoryRate(startDate, now),
    queryNoiseExposure(startDate, now),
    queryMindfulness(startDate, now),
  ]);

  return {
    device_info: deviceInfo,
    sync_window: syncWindow,
    heart_rates: heartRates,
    hrv_samples: hrvSamples,
    activity_samples: activitySamples,
    sleep_sessions: sleepSessions,
    blood_oxygen_samples: bloodOxygenSamples,
    body_temperature_samples: bodyTemperatureSamples,
    workout_records: workoutRecords,
    ecg_records: [], // ECG 需要特殊处理，暂留空
    respiratory_rate_samples: respiratoryRateSamples,
    noise_exposure_samples: noiseExposureSamples,
    mindfulness_sessions: mindfulnessSessions,
  };
}

// ========== 各数据类型查询实现 ==========

/** 查询心率数据 */
async function queryHeartRates(start: Date, end: Date): Promise<HeartRateIn[]> {
  try {
    const samples = await queryQuantitySamples(
      QuantityTypeIdentifier.HeartRate,
      { from: start, to: end, limit: 1000 },
    );
    return samples.map((s) => ({
      sample_uuid: s.uuid,
      source_device: s.sourceRevision?.source?.bundleIdentifier ?? null,
      recorded_at: s.startDate,
      bpm: s.quantity,
      motion_context: null,
      measurement_type: 'heart_rate',
    }));
  } catch (error) {
    console.error('查询心率失败:', error);
    return [];
  }
}

/** 查询 HRV 数据 */
async function queryHRV(start: Date, end: Date): Promise<HRVSampleIn[]> {
  try {
    const samples = await queryQuantitySamples(
      QuantityTypeIdentifier.HeartRateVariabilitySDNN,
      { from: start, to: end, limit: 500 },
    );
    return samples.map((s) => ({
      sample_uuid: s.uuid,
      source_device: s.sourceRevision?.source?.bundleIdentifier ?? null,
      recorded_at: s.startDate,
      sdnn_ms: s.quantity,
    }));
  } catch (error) {
    console.error('查询 HRV 失败:', error);
    return [];
  }
}

/** 查询活动数据（步数 + 能量 + 距离） */
async function queryActivities(start: Date, end: Date): Promise<ActivitySampleIn[]> {
  const results: ActivitySampleIn[] = [];

  const metricQueries: Array<{ type: string; identifier: string }> = [
    { type: 'steps', identifier: QuantityTypeIdentifier.StepCount },
    { type: 'active_energy', identifier: QuantityTypeIdentifier.ActiveEnergyBurned },
    { type: 'basal_energy', identifier: QuantityTypeIdentifier.BasalEnergyBurned },
    { type: 'distance', identifier: QuantityTypeIdentifier.DistanceWalkingRunning },
  ];

  await Promise.all(
    metricQueries.map(async ({ type, identifier }) => {
      try {
        const samples = await queryQuantitySamples(identifier, {
          from: start,
          to: end,
          limit: 500,
        });
        for (const s of samples) {
          results.push({
            sample_uuid: s.uuid,
            source_device: s.sourceRevision?.source?.bundleIdentifier ?? null,
            recorded_at: s.startDate,
            metric_type: type,
            value: s.quantity,
            duration_seconds: null,
          });
        }
      } catch (error) {
        console.error(`查询 ${type} 失败:`, error);
      }
    }),
  );

  return results;
}

/** 查询睡眠数据 */
async function querySleep(start: Date, end: Date): Promise<SleepSessionIn[]> {
  try {
    const samples = await queryCategorySamples(
      CategoryTypeIdentifier.SleepAnalysis,
      { from: start, to: end, limit: 200 },
    );

    // 将连续的睡眠样本合并为会话
    const sessions: SleepSessionIn[] = [];
    const grouped: Map<string, typeof samples> = new Map();

    for (const s of samples) {
      const dateKey = s.startDate.split('T')[0];
      if (!grouped.has(dateKey)) grouped.set(dateKey, []);
      grouped.get(dateKey)!.push(s);
    }

    for (const [dateKey, daySamples] of grouped) {
      if (daySamples.length === 0) continue;

      const sorted = daySamples.sort(
        (a, b) => new Date(a.startDate).getTime() - new Date(b.startDate).getTime(),
      );

      const firstSample = sorted[0];
      const lastSample = sorted[sorted.length - 1];
      const startMs = new Date(firstSample.startDate).getTime();
      const endMs = new Date(lastSample.endDate).getTime();
      const totalMinutes = (endMs - startMs) / 60000;

      const stages: SleepStageIn[] = sorted.map((s) => ({
        stage: mapSleepValue(s.value as number),
        start_time: s.startDate,
        end_time: s.endDate,
        duration_minutes: (new Date(s.endDate).getTime() - new Date(s.startDate).getTime()) / 60000,
      }));

      sessions.push({
        sample_uuid: `sleep-${dateKey}-${sorted[0].uuid.slice(0, 8)}`,
        source_device: firstSample.sourceRevision?.source?.bundleIdentifier ?? null,
        recorded_at: firstSample.startDate,
        start_time: firstSample.startDate,
        end_time: lastSample.endDate,
        total_duration_minutes: totalMinutes,
        in_bed_duration_minutes: null,
        stages,
      });
    }

    return sessions;
  } catch (error) {
    console.error('查询睡眠失败:', error);
    return [];
  }
}

/** HealthKit 睡眠值映射到后端枚举 */
function mapSleepValue(value: number): string {
  switch (value) {
    case 0: return 'in_bed';
    case 1: return 'asleep'; // SleepAnalysis value 1 = asleep (core)
    case 2: return 'awake';
    default: return 'core';
  }
}

/** 查询血氧数据 */
async function queryBloodOxygen(start: Date, end: Date): Promise<BloodOxygenSampleIn[]> {
  try {
    const samples = await queryQuantitySamples(
      QuantityTypeIdentifier.BloodOxygenSaturation,
      { from: start, to: end, limit: 500 },
    );
    return samples.map((s) => ({
      sample_uuid: s.uuid,
      source_device: s.sourceRevision?.source?.bundleIdentifier ?? null,
      recorded_at: s.startDate,
      spo2_percent: s.quantity,
      measurement_condition: null,
    }));
  } catch (error) {
    console.error('查询血氧失败:', error);
    return [];
  }
}

/** 查询体温数据 */
async function queryBodyTemperature(start: Date, end: Date): Promise<BodyTemperatureSampleIn[]> {
  try {
    const samples = await queryQuantitySamples(
      QuantityTypeIdentifier.BodyTemperature,
      { from: start, to: end, limit: 100 },
    );
    return samples.map((s) => ({
      sample_uuid: s.uuid,
      source_device: s.sourceRevision?.source?.bundleIdentifier ?? null,
      recorded_at: s.startDate,
      temperature_celsius: s.quantity,
      measurement_location: null,
    }));
  } catch (error) {
    console.error('查询体温失败:', error);
    return [];
  }
}

/** 查询运动记录 */
async function queryWorkouts(start: Date, end: Date): Promise<WorkoutRecordIn[]> {
  try {
    const samples = await queryWorkoutSamples({ from: start, to: end, limit: 100 });
    return samples.map((w) => ({
      sample_uuid: w.uuid,
      source_device: w.sourceRevision?.source?.bundleIdentifier ?? null,
      recorded_at: w.startDate,
      workout_type: w.workoutActivityType,
      start_time: w.startDate,
      end_time: w.endDate,
      duration_seconds: w.duration,
      total_energy_kcal: w.totalEnergyBurned ?? null,
      active_energy_kcal: w.totalEnergyBurned ?? null,
      distance_meters: w.totalDistance ?? null,
      avg_heart_rate: null,
      max_heart_rate: null,
      min_heart_rate: null,
      hr_zones: [],
    }));
  } catch (error) {
    console.error('查询运动失败:', error);
    return [];
  }
}

/** 查询呼吸率数据 */
async function queryRespiratoryRate(start: Date, end: Date): Promise<RespiratoryRateSampleIn[]> {
  try {
    const samples = await queryQuantitySamples(
      QuantityTypeIdentifier.RespiratoryRate,
      { from: start, to: end, limit: 500 },
    );
    return samples.map((s) => ({
      sample_uuid: s.uuid,
      source_device: s.sourceRevision?.source?.bundleIdentifier ?? null,
      recorded_at: s.startDate,
      breaths_per_minute: s.quantity,
    }));
  } catch (error) {
    console.error('查询呼吸率失败:', error);
    return [];
  }
}

/** 查询环境噪声数据 */
async function queryNoiseExposure(start: Date, end: Date): Promise<NoiseExposureSampleIn[]> {
  try {
    const samples = await queryQuantitySamples(
      QuantityTypeIdentifier.EnvironmentalAudioExposure,
      { from: start, to: end, limit: 500 },
    );
    return samples.map((s) => ({
      sample_uuid: s.uuid,
      source_device: s.sourceRevision?.source?.bundleIdentifier ?? null,
      recorded_at: s.startDate,
      decibels: s.quantity,
      duration_seconds: null,
    }));
  } catch (error) {
    console.error('查询噪声失败:', error);
    return [];
  }
}

/** 查询正念会话数据 */
async function queryMindfulness(start: Date, end: Date): Promise<MindfulnessSessionIn[]> {
  try {
    const samples = await queryCategorySamples(
      CategoryTypeIdentifier.MindfulSession,
      { from: start, to: end, limit: 200 },
    );
    return samples.map((s) => ({
      sample_uuid: s.uuid,
      source_device: s.sourceRevision?.source?.bundleIdentifier ?? null,
      recorded_at: s.startDate,
      start_time: s.startDate,
      end_time: s.endDate,
      duration_minutes: (new Date(s.endDate).getTime() - new Date(s.startDate).getTime()) / 60000,
    }));
  } catch (error) {
    console.error('查询正念失败:', error);
    return [];
  }
}
