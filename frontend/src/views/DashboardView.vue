<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, RadarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, RadarComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { useDashboardStore } from '../stores/dashboard'

use([CanvasRenderer, LineChart, BarChart, RadarChart, GridComponent, TooltipComponent, LegendComponent, RadarComponent])

const dashboardStore = useDashboardStore()
const period = ref('7d')

onMounted(() => {
  dashboardStore.fetchAll(period.value)
})

function changePeriod(p: string) {
  period.value = p
  dashboardStore.fetchTrends(p)
}

function formatNumber(n?: number | null) {
  if (n == null) return '--'
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : n.toFixed(0)
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1>Dashboard</h1>
      <p>今日健康数据概览</p>
    </div>

    <div v-if="dashboardStore.loading" class="loading">加载中...</div>

    <template v-if="dashboardStore.summary">
      <!-- Metric Cards -->
      <div class="metrics-grid">
        <div class="metric-card card">
          <div class="metric-icon" style="background:#EEF2FF;color:#4F46E5">🏃</div>
          <div class="metric-body">
            <span class="metric-value">{{ formatNumber(dashboardStore.summary.steps) }}</span>
            <span class="metric-label">步数</span>
          </div>
        </div>
        <div class="metric-card card">
          <div class="metric-icon" style="background:#FEF2F2;color:#EF4444">❤️</div>
          <div class="metric-body">
            <span class="metric-value">{{ dashboardStore.summary.avg_heart_rate?.toFixed(0) || '--' }}</span>
            <span class="metric-label">平均心率 bpm</span>
          </div>
        </div>
        <div class="metric-card card">
          <div class="metric-icon" style="background:#EFF6FF;color:#3B82F6">🌙</div>
          <div class="metric-body">
            <span class="metric-value">{{ dashboardStore.summary.sleep_hours?.toFixed(1) || '--' }}</span>
            <span class="metric-label">睡眠 小时</span>
          </div>
        </div>
        <div class="metric-card card">
          <div class="metric-icon" style="background:#ECFDF5;color:#10B981">🫁</div>
          <div class="metric-body">
            <span class="metric-value">{{ dashboardStore.summary.spo2_percent?.toFixed(1) || '--' }}</span>
            <span class="metric-label">血氧 %</span>
          </div>
        </div>
        <div class="metric-card card">
          <div class="metric-icon" style="background:#FFF7ED;color:#F59E0B">🔥</div>
          <div class="metric-body">
            <span class="metric-value">{{ formatNumber(dashboardStore.summary.active_energy_kcal) }}</span>
            <span class="metric-label">活动能量 kcal</span>
          </div>
        </div>
        <div class="metric-card card">
          <div class="metric-icon" style="background:#F5F3FF;color:#8B5CF6">💓</div>
          <div class="metric-body">
            <span class="metric-value">{{ dashboardStore.summary.resting_heart_rate?.toFixed(0) || '--' }}</span>
            <span class="metric-label">静息心率 bpm</span>
          </div>
        </div>
      </div>

      <!-- Trends -->
      <div class="section-header" v-if="dashboardStore.trends">
        <h2>趋势</h2>
        <div class="period-tabs">
          <button v-for="p in ['7d','30d','90d']" :key="p" :class="['tab', { active: period === p }]" @click="changePeriod(p)">
            {{ p === '7d' ? '7天' : p === '30d' ? '30天' : '90天' }}
          </button>
        </div>
      </div>

      <div class="charts-grid" v-if="dashboardStore.trends">
        <div class="card chart-card">
          <h3>步数趋势</h3>
          <v-chart :option="{
            tooltip: { trigger: 'axis' },
            xAxis: { type: 'category', data: dashboardStore.trends.steps.map(d => d.date.slice(5)) },
            yAxis: { type: 'value' },
            series: [{ type: 'bar', data: dashboardStore.trends.steps.map(d => d.value || 0), itemStyle: { color: '#4F46E5', borderRadius: [4,4,0,0] } }],
            grid: { left: 50, right: 20, top: 20, bottom: 30 },
          }" style="height: 250px" />
        </div>
        <div class="card chart-card">
          <h3>心率趋势</h3>
          <v-chart :option="{
            tooltip: { trigger: 'axis' },
            xAxis: { type: 'category', data: dashboardStore.trends.heart_rate.map(d => d.date.slice(5)) },
            yAxis: { type: 'value', min: 50 },
            series: [{ type: 'line', data: dashboardStore.trends.heart_rate.map(d => d.value), smooth: true, lineStyle: { color: '#EF4444' }, itemStyle: { color: '#EF4444' }, areaStyle: { color: 'rgba(239,68,68,0.1)' } }],
            grid: { left: 50, right: 20, top: 20, bottom: 30 },
          }" style="height: 250px" />
        </div>
        <div class="card chart-card">
          <h3>睡眠趋势</h3>
          <v-chart :option="{
            tooltip: { trigger: 'axis', formatter: (p: any) => p[0]?.value != null ? p[0].value + ' 小时' : '--' },
            xAxis: { type: 'category', data: dashboardStore.trends.sleep.map(d => d.date.slice(5)) },
            yAxis: { type: 'value', max: 12 },
            series: [{ type: 'bar', data: dashboardStore.trends.sleep.map(d => d.value), itemStyle: { color: '#3B82F6', borderRadius: [4,4,0,0] } }],
            grid: { left: 50, right: 20, top: 20, bottom: 30 },
          }" style="height: 250px" />
        </div>
        <div class="card chart-card">
          <h3>活动能量趋势</h3>
          <v-chart :option="{
            tooltip: { trigger: 'axis' },
            xAxis: { type: 'category', data: dashboardStore.trends.active_energy.map(d => d.date.slice(5)) },
            yAxis: { type: 'value' },
            series: [{ type: 'line', data: dashboardStore.trends.active_energy.map(d => d.value), smooth: true, lineStyle: { color: '#F59E0B' }, itemStyle: { color: '#F59E0B' }, areaStyle: { color: 'rgba(245,158,11,0.1)' } }],
            grid: { left: 50, right: 20, top: 20, bottom: 30 },
          }" style="height: 250px" />
        </div>
      </div>

      <!-- Health Score -->
      <div class="card score-card" v-if="dashboardStore.healthScore">
        <h3>健康评分</h3>
        <v-chart :option="{
          radar: {
            indicator: [
              { name: '活动', max: 100 },
              { name: '睡眠', max: 100 },
              { name: '心脏', max: 100 },
              { name: '生命体征', max: 100 },
            ],
          },
          series: [{
            type: 'radar',
            data: [{
              value: [
                dashboardStore.healthScore.activity_score,
                dashboardStore.healthScore.sleep_score,
                dashboardStore.healthScore.heart_score,
                dashboardStore.healthScore.vitals_score,
              ],
              areaStyle: { color: 'rgba(79,70,229,0.2)' },
              lineStyle: { color: '#4F46E5' },
              itemStyle: { color: '#4F46E5' },
            }],
          }],
        }" style="height: 300px" />
        <div class="overall-score">
          综合评分: <strong>{{ dashboardStore.healthScore.overall_score.toFixed(0) }}</strong> / 100
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.loading { text-align: center; padding: 60px; color: var(--color-text-secondary); }

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.metric-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.metric-body { display: flex; flex-direction: column; }
.metric-value { font-size: 24px; font-weight: 700; line-height: 1.2; }
.metric-label { font-size: 13px; color: var(--color-text-secondary); }

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.section-header h2 { font-size: 18px; font-weight: 700; }

.period-tabs { display: flex; gap: 4px; }
.tab {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}
.tab.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 32px;
}

.chart-card h3 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--color-text-secondary);
}

.score-card {
  max-width: 500px;
  text-align: center;
}
.score-card h3 { font-size: 16px; font-weight: 700; margin-bottom: 8px; }
.overall-score { font-size: 16px; color: var(--color-text-secondary); }
.overall-score strong { font-size: 28px; color: var(--color-primary); }
</style>
