/**
 * 同步编排服务 — 协调健康数据采集和 API 上传
 *
 * 通过 Platform.select 自动切换：
 * - iOS → 使用 healthService（真实 HealthKit 数据）
 * - Android/Web/ExpoGo → 使用 mockHealthService（模拟数据）
 */
import { Platform } from 'react-native';
import { apiRequest } from './apiClient';
import type { SyncPayload, SyncResponse, SyncStatusResponse, SyncLogResponse } from '@/types/sync';
import type { HealthPermissionStatus } from '@/types/health';

// 根据平台选择服务实现
// 使用 try-catch 兼容 Expo Go（iOS 上 HealthKit 不可用的情况）
let healthService: {
  requestHealthPermissions: () => Promise<boolean>;
  getHealthPermissionStatuses: () => Promise<HealthPermissionStatus[]>;
  fetchHealthData: (days?: number) => Promise<SyncPayload>;
};

try {
  if (Platform.OS === 'ios') {
    // 尝试加载真实的 HealthKit 服务（仅 Development Build 可用）
    require('@kingstinct/react-native-healthkit');
    healthService = require('./healthService').default || require('./healthService');
  } else if (Platform.OS === 'android') {
    healthService = require('./mockHealthService').default || require('./mockHealthService');
  } else {
    healthService = require('./mockHealthService').default || require('./mockHealthService');
  }
} catch (error) {
  // HealthKit 不可用时（Expo Go 等），降级到 mock 数据
  console.warn('[syncService] HealthKit not available, using mock data:', error.message);
  healthService = require('./mockHealthService').default || require('./mockHealthService');
}

const {
  requestHealthPermissions,
  getHealthPermissionStatuses,
  fetchHealthData,
} = healthService;

/** 请求健康数据权限 */
export { requestHealthPermissions, getHealthPermissionStatuses };

/** 手动触发同步：采集数据 → 上传到后端 */
export async function triggerSync(days: number = 7): Promise<SyncResponse> {
  const payload: SyncPayload = await fetchHealthData(days);
  return apiRequest<SyncResponse>('/sync/upload', {
    method: 'POST',
    body: payload,
  });
}

/** 获取同步状态 — GET /sync/status */
export async function getSyncStatus(): Promise<SyncStatusResponse> {
  return apiRequest<SyncStatusResponse>('/sync/status');
}

/** 获取同步历史 — GET /sync/history */
export async function getSyncHistory(
  page: number = 1,
  pageSize: number = 20,
): Promise<SyncLogResponse[]> {
  return apiRequest<SyncLogResponse[]>(
    `/sync/history?page=${page}&page_size=${pageSize}`,
  );
}
