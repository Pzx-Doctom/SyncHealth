<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const navItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/heart', label: '心率', icon: '❤️' },
  { path: '/sleep', label: '睡眠', icon: '🌙' },
  { path: '/activity', label: '活动', icon: '🏃' },
  { path: '/workouts', label: '运动', icon: '💪' },
  { path: '/upload', label: '数据导入', icon: '📥' },
  { path: '/chat', label: 'AI 对话', icon: '🤖' },
  { path: '/agents', label: '智能体', icon: '⚙️' },
]

function logout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar-header">
        <h2>SyncHealth</h2>
      </div>
      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: route.path === item.path }"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <div class="user-info" v-if="authStore.user">
          <span class="user-name">{{ authStore.user.display_name }}</span>
          <span class="user-email">{{ authStore.user.email }}</span>
        </div>
        <button class="btn-logout" @click="logout">退出登录</button>
      </div>
    </aside>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 240px;
  background: var(--color-sidebar);
  color: white;
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 100;
}

.sidebar-header {
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.sidebar-header h2 {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, #818CF8, #34D399);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.sidebar-nav {
  flex: 1;
  padding: 12px 8px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
  transition: all 0.2s;
  margin-bottom: 2px;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.nav-item.active {
  background: var(--color-primary);
  color: white;
}

.nav-icon { font-size: 18px; }

.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.user-info {
  display: flex;
  flex-direction: column;
  margin-bottom: 12px;
}

.user-name { font-size: 14px; font-weight: 600; }
.user-email { font-size: 12px; color: rgba(255, 255, 255, 0.5); }

.btn-logout {
  width: 100%;
  padding: 8px;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.8);
  border-radius: 6px;
  font-size: 13px;
  transition: background 0.2s;
}
.btn-logout:hover { background: rgba(239, 68, 68, 0.3); }

.main-content {
  flex: 1;
  margin-left: 240px;
  padding: 32px;
  max-width: 1400px;
}
</style>
