import apiClient from './client'
import type { TokenResponse, UserResponse, LoginRequest, RegisterRequest } from '../types/auth'

export const authApi = {
  login(data: LoginRequest) {
    return apiClient.post<TokenResponse>('/auth/login', data)
  },
  register(data: RegisterRequest) {
    return apiClient.post<TokenResponse>('/auth/register', data)
  },
  refresh(refreshToken: string) {
    return apiClient.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken })
  },
  me() {
    return apiClient.get<UserResponse>('/auth/me')
  },
}
