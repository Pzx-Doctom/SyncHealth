<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { healthApi } from '../api/health'
import type { HeartRateOut } from '../types/health'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

const heartRates = ref<HeartRateOut[]>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const res = await healthApi.getHeartRates({ page_size: 500 })
    heartRates.value = res.data.items.reverse()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <div class="page-header">
      <h1>心率数据</h1>
      <p>Apple Watch 心率监测详情</p>
    </div>
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="heartRates.length === 0" class="empty">暂无心率数据，请先通过 iOS 应用同步数据</div>
    <template v-else>
      <div class="card" style="margin-bottom: 24px">
        <h3 style="margin-bottom: 12px; font-size: 16px">心率变化</h3>
        <v-chart :option="{
          tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].axisValue}<br/>心率: ${p[0].value} bpm` },
          xAxis: { type: 'category', data: heartRates.map(h => new Date(h.recorded_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })) },
          yAxis: { type: 'value', name: 'bpm', min: (v: any) => Math.floor(v.min - 5) },
          series: [{ type: 'line', data: heartRates.map(h => h.bpm), smooth: true, lineStyle: { color: '#EF4444' }, itemStyle: { color: '#EF4444' }, areaStyle: { color: 'rgba(239,68,68,0.08)' }, symbol: 'none' }],
          grid: { left: 60, right: 20, top: 30, bottom: 30 },
        }" style="height: 350px" />
      </div>
      <div class="card">
        <h3 style="margin-bottom: 12px; font-size: 16px">数据列表</h3>
        <table class="data-table">
          <thead>
            <tr><th>时间</th><th>心率 (bpm)</th><th>类型</th><th>状态</th></tr>
          </thead>
          <tbody>
            <tr v-for="hr in heartRates.slice(-20).reverse()" :key="hr.id">
              <td>{{ new Date(hr.recorded_at).toLocaleString('zh-CN') }}</td>
              <td><strong>{{ hr.bpm.toFixed(0) }}</strong></td>
              <td>{{ hr.measurement_type === 'heart_rate' ? '实时心率' : hr.measurement_type === 'resting_heart_rate' ? '静息心率' : '步行心率' }}</td>
              <td>{{ hr.motion_context || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.loading, .empty { text-align: center; padding: 60px; color: var(--color-text-secondary); }
.data-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.data-table th { text-align: left; padding: 10px 12px; border-bottom: 2px solid var(--color-border); color: var(--color-text-secondary); font-weight: 600; font-size: 13px; }
.data-table td { padding: 10px 12px; border-bottom: 1px solid var(--color-border); }
</style>
