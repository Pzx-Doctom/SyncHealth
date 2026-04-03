import apiClient from './client'
import type { DashboardSummary, DashboardTrends, HealthScore } from '../types/dashboard'

export const dashboardApi = {
  getSummary() {
    return apiClient.get<DashboardSummary>('/dashboard/summary')
  },
  getTrends(period: string = '7d') {
    return apiClient.get<DashboardTrends>('/dashboard/trends', { params: { period } })
  },
  getHealthScore() {
    return apiClient.get<HealthScore>('/dashboard/health-score')
  },
}
