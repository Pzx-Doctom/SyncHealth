<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { healthApi } from '../api/health'
import type { WorkoutRecordOut } from '../types/health'

const workouts = ref<WorkoutRecordOut[]>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const res = await healthApi.getWorkouts({ page_size: 50 })
    workouts.value = res.data.items
  } finally {
    loading.value = false
  }
})

function formatDuration(seconds: number) {
  const m = Math.floor(seconds / 60)
  return m >= 60 ? `${Math.floor(m / 60)}h ${m % 60}m` : `${m}m`
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1>运动记录</h1>
      <p>Apple Watch 运动追踪</p>
    </div>
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="workouts.length === 0" class="empty">暂无运动数据</div>
    <div v-else class="workouts-list">
      <div class="card workout-card" v-for="w in workouts" :key="w.id">
        <div class="workout-header">
          <div>
            <span class="workout-type">{{ w.workout_type }}</span>
            <span class="workout-date">{{ new Date(w.start_time).toLocaleDateString('zh-CN') }}</span>
          </div>
          <span class="workout-duration">{{ formatDuration(w.duration_seconds) }}</span>
        </div>
        <div class="workout-stats">
          <div class="stat" v-if="w.active_energy_kcal">
            <span class="stat-value">{{ w.active_energy_kcal.toFixed(0) }}</span>
            <span class="stat-label">千卡</span>
          </div>
          <div class="stat" v-if="w.distance_meters">
            <span class="stat-value">{{ (w.distance_meters / 1000).toFixed(2) }}</span>
            <span class="stat-label">公里</span>
          </div>
          <div class="stat" v-if="w.avg_heart_rate">
            <span class="stat-value">{{ w.avg_heart_rate.toFixed(0) }}</span>
            <span class="stat-label">平均心率</span>
          </div>
          <div class="stat" v-if="w.max_heart_rate">
            <span class="stat-value">{{ w.max_heart_rate.toFixed(0) }}</span>
            <span class="stat-label">最大心率</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.loading, .empty { text-align: center; padding: 60px; color: var(--color-text-secondary); }
.workouts-list { display: flex; flex-direction: column; gap: 12px; }
.workout-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.workout-type { font-weight: 700; font-size: 16px; margin-right: 12px; }
.workout-date { font-size: 13px; color: var(--color-text-secondary); }
.workout-duration { font-size: 22px; font-weight: 700; color: var(--color-primary); }
.workout-stats { display: flex; gap: 32px; }
.stat { display: flex; flex-direction: column; }
.stat-value { font-size: 18px; font-weight: 700; }
.stat-label { font-size: 12px; color: var(--color-text-secondary); }
</style>
