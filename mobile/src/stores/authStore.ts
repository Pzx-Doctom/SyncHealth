/**
 * 认证状态管理 — Zustand Store
 *
 * 管理：用户信息、JWT Token、登录/注册/登出
 * Token 持久化通过 expo-secure-store 实现（apiClient.ts 中已处理）
 */
import { create } from 'zustand';
import storage from '@/utils/secureStorage';
import * as authService from '@/services/authService';
import { setOnAuthFailure } from '@/services/apiClient';
import type { UserResponse } from '@/types/auth';

interface AuthStoreState {
  user: UserResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthStoreState>((set, get) => {
  // 设置认证失败回调（由 apiClient 401 拦截器触发）
  setOnAuthFailure(() => {
    get().logout();
  });

  return {
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,

    login: async (email: string, password: string) => {
      set({ isLoading: true, error: null });
      try {
        await authService.login({ email, password });
        const user = await authService.getMe();
        set({ user, isAuthenticated: true, isLoading: false });
      } catch (err) {
        const message = err instanceof Error ? err.message : '登录失败';
        set({ error: message, isLoading: false });
        throw err;
      }
    },

    register: async (email: string, password: string, displayName: string) => {
      set({ isLoading: true, error: null });
      try {
        await authService.register({ email, password, display_name: displayName });
        const user = await authService.getMe();
        set({ user, isAuthenticated: true, isLoading: false });
      } catch (err) {
        const message = err instanceof Error ? err.message : '注册失败';
        set({ error: message, isLoading: false });
        throw err;
      }
    },

    logout: async () => {
      await authService.logout();
      set({ user: null, isAuthenticated: false, error: null });
      // 强制刷新页面（确保路由守卫重新执行）
      if (typeof window !== 'undefined') {
        window.location.reload();
      }
    },

    checkAuth: async () => {
      // 检查本地是否有 token
      const token = await storage.getItemAsync('access_token');
      if (!token) {
        set({ isAuthenticated: false, user: null });
        return;
      }

      // 尝试用 token 获取用户信息
      set({ isLoading: true });
      try {
        const user = await authService.getMe();
        set({ user, isAuthenticated: true, isLoading: false });
      } catch {
        // token 失效
        await authService.logout();
        set({ user: null, isAuthenticated: false, isLoading: false });
      }
    },

    clearError: () => set({ error: null }),
  };
});
