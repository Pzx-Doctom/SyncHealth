/**
 * 跨平台安全存储
 * - 原生平台: 使用 expo-secure-store
 * - Web/开发环境: 降级到 localStorage
 */
import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

const isWeb = Platform.OS === 'web' || typeof window !== 'undefined';

const storage = {
  async getItemAsync(key: string): Promise<string | null> {
    try {
      if (isWeb) {
        return localStorage.getItem(key);
      }
      return await SecureStore.getItemAsync(key);
    } catch {
      // SecureStore 不可用时降级到内存（或 localStorage）
      if (isWeb) return null;
      return localStorage.getItem(key);
    }
  },

  async setItemAsync(key: string, value: string): Promise<void> {
    try {
      if (isWeb) {
        localStorage.setItem(key, value);
        return;
      }
      await SecureStore.setItemAsync(key, value);
    } catch {
      if (isWeb) return;
      localStorage.setItem(key, value);
    }
  },

  async deleteItemAsync(key: string): Promise<void> {
    try {
      if (isWeb) {
        localStorage.removeItem(key);
        return;
      }
      await SecureStore.deleteItemAsync(key);
    } catch {
      if (isWeb) return;
      localStorage.removeItem(key);
    }
  },
};

export default storage;
