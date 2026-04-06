/**
 * API 客户端 — fetch 封装 + JWT 自动附加 + 401 自动刷新
 *
 * 参照 frontend/src/api/client.ts 的拦截器逻辑，适配 React Native：
 * - localStorage → 由调用方通过 getAccessToken / getRefreshToken 回调提供
 * - axios → 原生 fetch API
 * - window.location.href → 通过 onAuthFailure 回调处理
 */
import storage from '@/utils/secureStorage';

const STORAGE_KEYS = {
  accessToken: 'access_token',
  refreshToken: 'refresh_token',
  serverUrl: 'server_url',
} as const;

/** 获取默认服务器地址 */
export async function getServerUrl(): Promise<string> {
  const url = await storage.getItemAsync(STORAGE_KEYS.serverUrl);
  return url || 'http://127.0.0.1:8000/api/v1';
}

/** 保存服务器地址 */
export async function setServerUrl(url: string): Promise<void> {
  await storage.setItemAsync(STORAGE_KEYS.serverUrl, url);
}

/** 获取 access_token */
export async function getAccessToken(): Promise<string | null> {
  return storage.getItemAsync(STORAGE_KEYS.accessToken);
}

/** 保存 access_token */
export async function setAccessToken(token: string): Promise<void> {
  await storage.setItemAsync(STORAGE_KEYS.accessToken, token);
}

/** 获取 refresh_token */
export async function getRefreshToken(): Promise<string | null> {
  return storage.getItemAsync(STORAGE_KEYS.refreshToken);
}

/** 保存 refresh_token */
export async function setRefreshToken(token: string): Promise<void> {
  await storage.setItemAsync(STORAGE_KEYS.refreshToken, token);
}

/** 清除所有 token */
export async function clearTokens(): Promise<void> {
  await storage.deleteItemAsync(STORAGE_KEYS.accessToken);
  await storage.deleteItemAsync(STORAGE_KEYS.refreshToken);
}

// ========== 401 刷新队列（防止并发刷新） ==========

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason: unknown) => void;
}> = [];

function processQueue(error: unknown) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(undefined);
  });
  failedQueue = [];
}

// ========== 核心请求函数 ==========

/** 认证失败回调（由 authStore 设置） */
let onAuthFailure: (() => void) | null = null;

/** 设置认证失败回调 */
export function setOnAuthFailure(callback: () => void) {
  onAuthFailure = callback;
}

/** fetch 封装：自动附加 JWT，401 自动刷新 */
export async function apiRequest<T>(
  path: string,
  options: {
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
    body?: unknown;
    headers?: Record<string, string>;
    skipAuth?: boolean;
  } = {},
): Promise<T> {
  const { method = 'GET', body, headers = {}, skipAuth = false } = options;
  const baseURL = await getServerUrl();
  const url = `${baseURL}${path}`;

  // 构建请求头
  const requestHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...headers,
  };

  // 附加 JWT（除非明确跳过）
  if (!skipAuth) {
    const token = await getAccessToken();
    if (token) {
      requestHeaders['Authorization'] = `Bearer ${token}`;
    }
  }

  const response = await fetch(url, {
    method,
    headers: requestHeaders,
    body: body ? JSON.stringify(body) : undefined,
  });

  // 401 处理：尝试刷新 token
  if (response.status === 401 && !skipAuth) {
    if (isRefreshing) {
      // 已有刷新请求在进行，排队等待
      return new Promise<T>((resolve, reject) => {
        failedQueue.push({
          resolve: () => apiRequest<T>(path, options).then(resolve).catch(reject),
          reject,
        });
      });
    }

    isRefreshing = true;
    const refreshToken = await getRefreshToken();

    if (!refreshToken) {
      // 没有 refresh token，直接登出
      await clearTokens();
      processQueue(new Error('No refresh token'));
      isRefreshing = false;
      onAuthFailure?.();
      throw new Error('认证已过期，请重新登录');
    }

    try {
      // 刷新 token
      const refreshResponse = await fetch(`${baseURL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!refreshResponse.ok) {
        throw new Error('刷新 token 失败');
      }

      const newTokens = await refreshResponse.json();
      await setAccessToken(newTokens.access_token);
      await setRefreshToken(newTokens.refresh_token);
      processQueue(null);

      // 用新 token 重试原始请求
      return apiRequest<T>(path, options);
    } catch (refreshError) {
      processQueue(refreshError);
      await clearTokens();
      onAuthFailure?.();
      throw new Error('认证已过期，请重新登录');
    } finally {
      isRefreshing = false;
    }
  }

  // 非 401 错误处理
  if (!response.ok) {
    let errorMessage = `请求失败 (${response.status})`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorMessage;
    } catch {
      // 响应体不是 JSON，使用默认错误消息
    }
    throw new Error(errorMessage);
  }

  // 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}
