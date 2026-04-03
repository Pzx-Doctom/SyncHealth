<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { healthApi } from '../api/health'
import type { ActivitySampleOut } from '../types/health'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const activities = ref<ActivitySampleOut[]>([])
const loading = ref(false)
const metric = ref('steps')

const metricOptions = [
  { value: 'steps', label: '步数' },
  { value: 'active_energy_kcal', label: '活动能量' },
  { value: 'distance_meters', label: '距离' },
  { value: 'flights_climbed', label: '爬楼' },
  { value: 'stand_hours', label: '站立时间' },
]

async function fetchData() {
  loading.value = true
  try {
    const res = await healthApi.getActivity({ metric: metric.value, page_size: 200 })
    activities.value = res.data.items.reverse()
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<template>
  <div>
    <div class="page-header">
      <h1>活动数据</h1>
      <p>步数、能量消耗、距离等活动指标</p>
    </div>
    <div class="filter-bar">
      <button v-for="opt in metricOptions" :key="opt.value" :class="['tab', { active: metric === opt.value }]"
        @click="metric = opt.value; fetchData()">
        {{ opt.label }}
      </button>
    </div>
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="activities.length === 0" class="empty">暂无活动数据</div>
    <template v-else>
      <div class="card">
        <v-chart :option="{
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: activities.map(a => new Date(a.recorded_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })) },
          yAxis: { type: 'value' },
          series: [{ type: 'bar', data: activities.map(a => a.value), itemStyle: { color: '#4F46E5', borderRadius: [4,4,0,0] } }],
          grid: { left: 60, right: 20, top: 20, bottom: 30 },
        }" style="height: 350px" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.loading, .empty { text-align: center; padding: 60px; color: var(--color-text-secondary); }
.filter-bar { display: flex; gap: 6px; margin-bottom: 20px; flex-wrap: wrap; }
.tab { padding: 6px 14px; border-radius: 6px; font-size: 13px; background: transparent; color: var(--color-text-secondary); border: 1px solid var(--color-border); }
.tab.active { background: var(--color-primary); color: white; border-color: var(--color-primary); }
</style>
