/**
 * 同步状态管理 — Zustand Store
 *
 * 管理：同步中/成功/失败状态、同步结果、同步历史
 */
import { create } from 'zustand';
import * as syncService from '@/services/syncService';
import type { SyncResponse, SyncStatusResponse, SyncLogResponse, SyncStatus } from '@/types/sync';

interface SyncStoreState {
  // 同步状态
  syncStatus: SyncStatus;
  lastSyncResult: SyncResponse | null;
  syncError: string | null;
  syncHistory: SyncLogResponse[];
  lastSyncAt: string | null;

  // 权限状态
  healthPermissions: Array<{ key: string; label: string; status: string }>;

  // Actions
  triggerManualSync: (days?: number) => Promise<void>;
  fetchSyncStatus: () => Promise<void>;
  fetchSyncHistory: () => Promise<void>;
  fetchHealthPermissions: () => Promise<void>;
  requestHealthPermissions: () => Promise<boolean>;
}

export const useSyncStore = create<SyncStoreState>((set, get) => ({
  syncStatus: 'idle' as SyncStatus,
  lastSyncResult: null,
  syncError: null,
  syncHistory: [],
  lastSyncAt: null,
  healthPermissions: [],

  triggerManualSync: async (days: number = 7) => {
    set({ syncStatus: 'syncing', syncError: null });
    try {
      const result = await syncService.triggerSync(days);
      set({
        syncStatus: 'success',
        lastSyncResult: result,
        lastSyncAt: new Date().toISOString(),
      });
      // 同步成功后刷新历史
      get().fetchSyncHistory();
      get().fetchSyncStatus();
    } catch (err) {
      const message = err instanceof Error ? err.message : '同步失败';
      set({ syncStatus: 'error', syncError: message });
    }
  },

  fetchSyncStatus: async () => {
    try {
      const status: SyncStatusResponse = await syncService.getSyncStatus();
      set({
        lastSyncAt: status.last_sync_at,
      });
    } catch {
      // 静默处理
    }
  },

  fetchSyncHistory: async () => {
    try {
      const history = await syncService.getSyncHistory(1, 20);
      set({ syncHistory: history });
    } catch {
      // 静默处理
    }
  },

  fetchHealthPermissions: async () => {
    try {
      const permissions = await syncService.getHealthPermissionStatuses();
      set({ healthPermissions: permissions });
    } catch {
      // 静默处理
    }
  },

  requestHealthPermissions: async () => {
    try {
      const granted = await syncService.requestHealthPermissions();
      await get().fetchHealthPermissions();
      return granted;
    } catch {
      return false;
    }
  },
}));
