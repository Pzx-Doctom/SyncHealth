/**
 * HealthKit 数据类型标识符映射
 * 将后端 metric_type 字段映射到 @kingstinct/react-native-healthkit 的 QuantityTypeIdentifier
 */
import {
  QuantityTypeIdentifier,
  CategoryTypeIdentifier,
} from '@kingstinct/react-native-healthkit';

/** 需要请求的 HealthKit 读取权限列表 */
export const HEALTHKIT_READ_PERMISSIONS = [
  // 数值类型
  QuantityTypeIdentifier.HeartRate,
  QuantityTypeIdentifier.HeartRateVariabilitySDNN,
  QuantityTypeIdentifier.StepCount,
  QuantityTypeIdentifier.DistanceWalkingRunning,
  QuantityTypeIdentifier.BasalEnergyBurned,
  QuantityTypeIdentifier.ActiveEnergyBurned,
  QuantityTypeIdentifier.BloodOxygenSaturation,
  QuantityTypeIdentifier.BodyTemperature,
  QuantityTypeIdentifier.RespiratoryRate,
  QuantityTypeIdentifier.EnvironmentalAudioExposure,
  // 分类类型
  CategoryTypeIdentifier.SleepAnalysis,
  CategoryTypeIdentifier.MindfulSession,
] as string[];

/** 数据类型中英文映射（用于 UI 展示） */
export const HEALTH_DATA_LABELS: Record<string, string> = {
  heartRate: '心率',
  hrv: '心率变异性 (HRV)',
  steps: '步数',
  distance: '步行/跑步距离',
  basalEnergy: '基础能量消耗',
  activeEnergy: '活动能量消耗',
  sleep: '睡眠分析',
  bloodOxygen: '血氧饱和度',
  bodyTemperature: '体温',
  workout: '运动记录',
  ecg: '心电图 (ECG)',
  respiratoryRate: '呼吸频率',
  noiseExposure: '环境噪声',
  mindfulness: '正念会话',
};

/** HealthKit 数据类型分组（用于设置页展示） */
export const HEALTH_DATA_GROUPS = [
  { key: 'heart', label: '心脏', types: ['heartRate', 'hrv', 'ecg'] },
  { key: 'activity', label: '活动', types: ['steps', 'distance', 'basalEnergy', 'activeEnergy', 'workout'] },
  { key: 'sleep', label: '睡眠', types: ['sleep', 'mindfulness'] },
  { key: 'vitals', label: '生命体征', types: ['bloodOxygen', 'bodyTemperature', 'respiratoryRate'] },
  { key: 'environment', label: '环境', types: ['noiseExposure'] },
] as const;
