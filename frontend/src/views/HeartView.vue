<script setup lang="ts">
import { ref, computed, watch } from 'vue'
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
const total = ref(0)
const page = ref(1)
const pageSize = 20

const today = new Date().toISOString().slice(0, 10)
const selectedDate = ref(today)

const dateStart = computed(() => selectedDate.value + 'T00:00:00')
const dateEnd = computed(() => {
  const d = new Date(selectedDate.value)
  d.setDate(d.getDate() + 1)
  return d.toISOString().slice(0, 10) + 'T00:00:00'
})

const totalPages = computed(() => Math.ceil(total.value / pageSize))

async function fetchData() {
  loading.value = true
  try {
    const res = await healthApi.getHeartRates({
      measurement_type: 'heart_rate',
      start: dateStart.value,
      end: dateEnd.value,
      page: page.value,
      page_size: pageSize,
    })
    heartRates.value = res.data.items.reverse()
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

function changeDate(e: Event) {
  const input = e.target as HTMLInputElement
  selectedDate.value = input.value
}

function prevPage() { if (page.value > 1) { page.value--; fetchData() } }
function nextPage() { if (page.value < totalPages.value) { page.value++; fetchData() } }

const chartOption = computed(() => {
  const sorted = [...heartRates.value].sort((a, b) =>
    new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime()
  )
  return {
    tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].axisValue}<br/>心率: ${p[0].value} bpm` },
    xAxis: { type: 'category', data: sorted.map(h => new Date(h.recorded_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })) },
    yAxis: { type: 'value', name: 'bpm', min: (v: any) => Math.floor(v.min - 5) },
    series: [{ type: 'line', data: sorted.map(h => h.bpm), smooth: true, lineStyle: { color: '#EF4444' }, itemStyle: { color: '#EF4444' }, areaStyle: { color: 'rgba(239,68,68,0.08)' }, symbol: 'none' }],
    grid: { left: 60, right: 20, top: 30, bottom: 30 },
  }
})

const chartItems = computed(() => [...heartRates.value].sort((a, b) =>
  new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime()
))

watch(selectedDate, () => { page.value = 1; fetchData() }, { immediate: true })
</script>

<template>
  <div>
    <div class="page-header">
      <h1>心率数据</h1>
      <p>Apple Watch 实时心率监测详情</p>
    </div>

    <div class="toolbar">
      <label class="date-label">
        选择日期：
        <input type="date" class="date-input" :value="selectedDate" @change="changeDate" />
      </label>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="heartRates.length === 0" class="empty">暂无心率数据，请先通过"数据导入"上传 Apple Health 文件</div>
    <template v-else>
      <div class="card" style="margin-bottom: 24px">
        <h3 style="margin-bottom: 12px; font-size: 16px">心率变化</h3>
        <v-chart :option="chartOption" style="height: 350px" />
      </div>
      <div class="card">
        <h3 style="margin-bottom: 12px; font-size: 16px">数据列表（共 {{ total }} 条）</h3>
        <table class="data-table">
          <thead>
            <tr><th>时间</th><th>心率 (bpm)</th><th>状态</th></tr>
          </thead>
          <tbody>
            <tr v-for="hr in chartItems" :key="hr.id">
              <td>{{ new Date(hr.recorded_at).toLocaleString('zh-CN') }}</td>
              <td><strong>{{ hr.bpm.toFixed(0) }}</strong></td>
              <td>{{ hr.motion_context || '-' }}</td>
            </tr>
          </tbody>
        </table>
        <div class="pagination" v-if="totalPages > 1">
          <button :disabled="page <= 1" @click="prevPage">上一页</button>
          <span>{{ page }} / {{ totalPages }}</span>
          <button :disabled="page >= totalPages" @click="nextPage">下一页</button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.loading, .empty { text-align: center; padding: 60px; color: var(--color-text-secondary); }
.toolbar { margin-bottom: 16px; display: flex; align-items: center; gap: 12px; }
.date-label { font-size: 14px; color: var(--color-text-secondary); display: flex; align-items: center; gap: 8px; }
.date-input { padding: 6px 10px; border: 1px solid var(--color-border); border-radius: 6px; background: var(--color-card); color: var(--color-text); font-size: 14px; }
.data-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.data-table th { text-align: left; padding: 10px 12px; border-bottom: 2px solid var(--color-border); color: var(--color-text-secondary); font-weight: 600; font-size: 13px; }
.data-table td { padding: 10px 12px; border-bottom: 1px solid var(--color-border); }
.pagination { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 16px; font-size: 14px; color: var(--color-text-secondary); }
.pagination button { padding: 6px 14px; border: 1px solid var(--color-border); border-radius: 6px; background: var(--color-card); color: var(--color-text); cursor: pointer; font-size: 13px; }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
