import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth'
import type { UserResponse } from '../types/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserResponse | null>(null)
  const accessToken = ref(localStorage.getItem('access_token') || '')
  const isAuthenticated = computed(() => !!accessToken.value)

  async function login(email: string, password: string) {
    const res = await authApi.login({ email, password })
    accessToken.value = res.data.access_token
    localStorage.setItem('access_token', res.data.access_token)
    localStorage.setItem('refresh_token', res.data.refresh_token)
    await fetchUser()
  }

  async function register(email: string, password: string, displayName: string) {
    const res = await authApi.register({ email, password, display_name: displayName })
    accessToken.value = res.data.access_token
    localStorage.setItem('access_token', res.data.access_token)
    localStorage.setItem('refresh_token', res.data.refresh_token)
    await fetchUser()
  }

  async function fetchUser() {
    try {
      const res = await authApi.me()
      user.value = res.data
    } catch {
      logout()
    }
  }

  function logout() {
    user.value = null
    accessToken.value = ''
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  return { user, accessToken, isAuthenticated, login, register, fetchUser, logout }
})
