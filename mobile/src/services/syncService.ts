/**
 * 同步编排服务 — 协调健康数据采集和 API 上传
 *
 * 通过 Platform.select 自动切换：
 * - iOS → 使用 healthService（真实 HealthKit 数据）
 * - Android → 使用 mockHealthService（模拟数据）
 */
import { Platform } from 'react-native';
import { apiRequest } from './apiClient';
import type { SyncPayload, SyncResponse, SyncStatusResponse, SyncLogResponse } from '@/types/sync';
import type { HealthPermissionStatus } from '@/types/health';

// 根据平台选择服务实现
const healthService = Platform.select({
  ios: () => require('./healthService'),
  android: () => require('./mockHealthService'),
  // web fallback
  web: () => require('./mockHealthService'),
})();

const {
  requestHealthPermissions,
  getHealthPermissionStatuses,
  fetchHealthData,
} = healthService;

/** 请求健康数据权限 */
export { requestHealthPermissions, getHealthPermissionStatuses };

/** 手动触发同步：采集数据 → 上传到后端 */
export async function triggerSync(days: number = 7): Promise<SyncResponse> {
  // 1. 从 HealthKit / Mock 获取健康数据
  const payload: SyncPayload = await fetchHealthData(days);

  // 2. 上传到后端
  const response = await apiRequest<SyncResponse>('/sync/upload', {
    method: 'POST',
    body: payload,
  });

  return response;
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
