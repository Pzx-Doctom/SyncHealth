import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dashboardApi } from '../api/dashboard'
import type { DashboardSummary, DashboardTrends, HealthScore } from '../types/dashboard'

export const useDashboardStore = defineStore('dashboard', () => {
  const summary = ref<DashboardSummary | null>(null)
  const trends = ref<DashboardTrends | null>(null)
  const healthScore = ref<HealthScore | null>(null)
  const loading = ref(false)

  async function fetchSummary() {
    loading.value = true
    try {
      const res = await dashboardApi.getSummary()
      summary.value = res.data
    } finally {
      loading.value = false
    }
  }

  async function fetchTrends(period: string = '7d') {
    const res = await dashboardApi.getTrends(period)
    trends.value = res.data
  }

  async function fetchHealthScore() {
    const res = await dashboardApi.getHealthScore()
    healthScore.value = res.data
  }

  async function fetchAll(period: string = '7d') {
    loading.value = true
    try {
      await Promise.all([fetchSummary(), fetchTrends(period), fetchHealthScore()])
    } finally {
      loading.value = false
    }
  }

  return { summary, trends, healthScore, loading, fetchSummary, fetchTrends, fetchHealthScore, fetchAll }
})
