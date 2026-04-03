<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const displayName = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value = ''
  loading.value = true
  try {
    await authStore.register(email.value, password.value, displayName.value)
    router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card card">
      <h1>SyncHealth</h1>
      <p class="subtitle">创建您的账号</p>
      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label>昵称</label>
          <input v-model="displayName" type="text" class="input" placeholder="您的昵称" required />
        </div>
        <div class="form-group">
          <label>邮箱</label>
          <input v-model="email" type="email" class="input" placeholder="your@email.com" required />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="password" type="password" class="input" placeholder="设置密码" required minlength="6" />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" class="btn btn-primary btn-full" :disabled="loading">
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>
      <p class="switch-link">
        已有账号？<router-link to="/login">立即登录</router-link>
      </p>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.auth-card { width: 400px; text-align: center; }
.auth-card h1 { font-size: 28px; font-weight: 700; color: var(--color-primary); margin-bottom: 4px; }
.subtitle { color: var(--color-text-secondary); margin-bottom: 32px; }
.form-group { text-align: left; margin-bottom: 16px; }
.form-group label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; color: var(--color-text-secondary); }
.error { color: var(--color-danger); font-size: 13px; margin-bottom: 12px; }
.btn-full { width: 100%; margin-top: 8px; }
.switch-link { margin-top: 20px; font-size: 13px; color: var(--color-text-secondary); }
.switch-link a { color: var(--color-primary); font-weight: 600; }
</style>
