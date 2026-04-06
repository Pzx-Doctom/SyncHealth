/**
 * 认证相关类型定义
 * 严格对应 backend/app/schemas/auth.py
 */

/** 登录请求 — 对应 UserLogin */
export interface LoginRequest {
  email: string;
  password: string;
}

/** 注册请求 — 对应 UserRegister */
export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
}

/** Token 响应 — 对应 TokenResponse */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

/** Token 刷新请求 — 对应 TokenRefresh */
export interface TokenRefreshRequest {
  refresh_token: string;
}

/** 用户信息响应 — 对应 UserResponse */
export interface UserResponse {
  id: number;
  email: string;
  display_name: string;
  created_at: string;
  last_sync_at?: string | null;
}

/** 认证状态（本地扩展，非后端模型） */
export interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: UserResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
