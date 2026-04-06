/**
 * 认证服务 — 封装所有认证相关 API 调用
 * 对应 backend/app/api/auth.py 的四个端点
 */
import { apiRequest } from './apiClient';
import {
  setAccessToken,
  setRefreshToken,
  clearTokens,
} from './apiClient';
import type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  UserResponse,
} from '@/types/auth';

/** 登录 — POST /auth/login */
export async function login(data: LoginRequest): Promise<TokenResponse> {
  const response = await apiRequest<TokenResponse>('/auth/login', {
    method: 'POST',
    body: data,
    skipAuth: true,
  });

  // 保存 token 到 SecureStore
  await setAccessToken(response.access_token);
  await setRefreshToken(response.refresh_token);

  return response;
}

/** 注册 — POST /auth/register */
export async function register(data: RegisterRequest): Promise<TokenResponse> {
  const response = await apiRequest<TokenResponse>('/auth/register', {
    method: 'POST',
    body: data,
    skipAuth: true,
  });

  // 注册成功自动保存 token
  await setAccessToken(response.access_token);
  await setRefreshToken(response.refresh_token);

  return response;
}

/** 刷新 Token — POST /auth/refresh */
export async function refreshToken(refreshToken: string): Promise<TokenResponse> {
  const response = await apiRequest<TokenResponse>('/auth/refresh', {
    method: 'POST',
    body: { refresh_token: refreshToken },
    skipAuth: true,
  });

  await setAccessToken(response.access_token);
  await setRefreshToken(response.refresh_token);

  return response;
}

/** 获取当前用户信息 — GET /auth/me */
export async function getMe(): Promise<UserResponse> {
  return apiRequest<UserResponse>('/auth/me');
}

/** 登出（仅清除本地 token） */
export async function logout(): Promise<void> {
  await clearTokens();
}
