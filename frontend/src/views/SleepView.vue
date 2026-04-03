<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { healthApi } from '../api/health'
import type { SleepSessionOut } from '../types/health'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const sessions = ref<SleepSessionOut[]>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const res = await healthApi.getSleep({ page_size: 30 })
    sessions.value = res.data.items
  } finally {
    loading.value = false
  }
})

const stageColors: Record<string, string> = {
  deep: '#3730A3',
  core: '#6366F1',
  rem: '#818CF8',
  awake: '#E2E8F0',
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1>睡眠数据</h1>
      <p>Apple Watch 睡眠分析</p>
    </div>
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="sessions.length === 0" class="empty">暂无睡眠数据</div>
    <template v-else>
      <div class="card" style="margin-bottom: 24px">
        <h3 style="margin-bottom: 12px; font-size: 16px">睡眠时长趋势</h3>
        <v-chart :option="{
          tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].axisValue}<br/>睡眠: ${p[0].value} 小时` },
          xAxis: { type: 'category', data: sessions.map(s => new Date(s.start_time).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })).reverse() },
          yAxis: { type: 'value', name: '小时', max: 12 },
          series: [{ type: 'bar', data: sessions.map(s => (s.total_duration_minutes / 60).toFixed(1)).reverse(), itemStyle: { color: '#6366F1', borderRadius: [4,4,0,0] } }],
          grid: { left: 50, right: 20, top: 30, bottom: 30 },
        }" style="height: 280px" />
      </div>
      <div class="sessions-list">
        <div class="card session-card" v-for="s in sessions" :key="s.id">
          <div class="session-header">
            <span class="session-date">{{ new Date(s.start_time).toLocaleDateString('zh-CN') }}</span>
            <span class="session-duration">{{ (s.total_duration_minutes / 60).toFixed(1) }} 小时</span>
          </div>
          <div class="session-time">
            {{ new Date(s.start_time).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }}
            - {{ new Date(s.end_time).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }}
          </div>
          <div class="stages-bar" v-if="s.stages.length > 0">
            <div v-for="stage in s.stages" :key="stage.id" class="stage-segment"
              :style="{ width: (stage.duration_minutes / s.total_duration_minutes * 100) + '%', background: stageColors[stage.stage] || '#ccc' }"
              :title="stage.stage + ': ' + stage.duration_minutes.toFixed(0) + ' 分钟'">
            </div>
          </div>
          <div class="stage-legend" v-if="s.stages.length > 0">
            <span v-for="(color, name) in stageColors" :key="name" class="legend-item">
              <span class="legend-dot" :style="{ background: color }"></span>
              {{ name === 'deep' ? '深睡' : name === 'core' ? '核心' : name === 'rem' ? 'REM' : '清醒' }}
            </span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.loading, .empty { text-align: center; padding: 60px; color: var(--color-text-secondary); }
.sessions-list { display: flex; flex-direction: column; gap: 12px; }
.session-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.session-date { font-weight: 700; }
.session-duration { font-size: 20px; font-weight: 700; color: var(--color-primary); }
.session-time { font-size: 13px; color: var(--color-text-secondary); margin-bottom: 12px; }
.stages-bar { display: flex; height: 16px; border-radius: 8px; overflow: hidden; margin-bottom: 8px; }
.stage-segment { min-width: 2px; }
.stage-legend { display: flex; gap: 16px; font-size: 12px; color: var(--color-text-secondary); }
.legend-item { display: flex; align-items: center; gap: 4px; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; }
</style>
