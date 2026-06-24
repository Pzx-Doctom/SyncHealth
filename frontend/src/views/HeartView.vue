<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
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
const viewMode = ref<'detail' | 'compact'>('detail')

// 客户端分页（详细视图表格）
const tablePage = ref(0)
const perPage = 20

const selectedDate = ref('')

const dateStart = computed(() => selectedDate.value + 'T00:00:00')
const dateEnd = computed(() => {
  const d = new Date(selectedDate.value)
  d.setDate(d.getDate() + 1)
  return d.toISOString().slice(0, 10) + 'T00:00:00'
})

// 启动时找到最近有数据的日期
onMounted(async () => {
  try {
    const res = await healthApi.getHeartRates({ page: 1, page_size: 1 })
    if (res.data.items.length > 0) {
      selectedDate.value = new Date(res.data.items[0].recorded_at).toISOString().slice(0, 10)
    } else {
      selectedDate.value = new Date().toISOString().slice(0, 10) // 回退到今天
    }
  } catch {
    selectedDate.value = new Date().toISOString().slice(0, 10)
  }
})

async function fetchData() {
  loading.value = true
  try {
    const res = await healthApi.getHeartRates({
      measurement_type: 'heart_rate',
      start: dateStart.value,
      end: dateEnd.value,
      page: 1,
      page_size: 1000, // 一天数据，全量拉取
    })
    heartRates.value = res.data.items.reverse()
  } finally {
    loading.value = false
  }
}

function changeDate(e: Event) {
  const input = e.target as HTMLInputElement
  selectedDate.value = input.value
}

// ---- 每小时统计 ----
interface HourStat { hour: number; min: number | null; max: number | null; avg: number | null; count: number }
const hourlyData = computed<HourStat[]>(() => {
  const hours: HourStat[] = []
  for (let h = 0; h < 24; h++) {
    const records = heartRates.value.filter(r => new Date(r.recorded_at).getHours() === h)
    if (records.length === 0) {
      hours.push({ hour: h, min: null, max: null, avg: null, count: 0 })
    } else {
      const bpms = records.map(r => r.bpm)
      hours.push({ hour: h, min: Math.min(...bpms), max: Math.max(...bpms), avg: bpms.reduce((a, b) => a + b, 0) / bpms.length, count: bpms.length })
    }
  }
  return hours
})

const BLOCKS = [
  { label: '0:00 — 6:00', hours: [0, 1, 2, 3, 4, 5] },
  { label: '6:00 — 12:00', hours: [6, 7, 8, 9, 10, 11] },
  { label: '12:00 — 18:00', hours: [12, 13, 14, 15, 16, 17] },
  { label: '18:00 — 24:00', hours: [18, 19, 20, 21, 22, 23] },
]

function barColor(hour: number): string {
  if (hour >= 0 && hour < 6) return '#6366F1'
  if (hour >= 6 && hour < 12) return '#F59E0B'
  if (hour >= 12 && hour < 18) return '#EF4444'
  return '#8B5CF6'
}

// ---- 详细视图 ----
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

const chartItems = computed(() =>
  [...heartRates.value].sort((a, b) => new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime())
)

const pagedItems = computed(() => {
  const start = tablePage.value * perPage
  return chartItems.value.slice(start, start + perPage)
})
const tableTotalPages = computed(() => Math.ceil(chartItems.value.length / perPage))

function prevPage() { if (tablePage.value > 0) tablePage.value-- }
function nextPage() { if (tablePage.value < tableTotalPages.value - 1) tablePage.value++ }

watch(selectedDate, () => { tablePage.value = 0; fetchData() }, { immediate: true })
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
      <div class="view-toggle">
        <button :class="['toggle-btn', { active: viewMode === 'detail' }]" @click="viewMode = 'detail'">详细</button>
        <button :class="['toggle-btn', { active: viewMode === 'compact' }]" @click="viewMode = 'compact'">简略</button>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="heartRates.length === 0" class="empty">暂无心率数据，请先通过"数据导入"上传 Apple Health 文件</div>

    <!-- 详细视图 -->
    <template v-else-if="viewMode === 'detail'">
      <div class="card" style="margin-bottom: 24px">
        <h3 style="margin-bottom: 12px; font-size: 16px">心率变化</h3>
        <v-chart :option="chartOption" style="height: 350px" />
      </div>
      <div class="card">
        <h3 style="margin-bottom: 12px; font-size: 16px">数据列表（共 {{ chartItems.length }} 条）</h3>
        <table class="data-table">
          <thead>
            <tr><th>时间</th><th>心率 (bpm)</th><th>状态</th></tr>
          </thead>
          <tbody>
            <tr v-for="hr in pagedItems" :key="hr.id">
              <td>{{ new Date(hr.recorded_at).toLocaleString('zh-CN') }}</td>
              <td><strong>{{ hr.bpm.toFixed(0) }}</strong></td>
              <td>{{ hr.motion_context || '-' }}</td>
            </tr>
          </tbody>
        </table>
        <div class="pagination" v-if="tableTotalPages > 1">
          <button :disabled="tablePage <= 0" @click="prevPage">上一页</button>
          <span>{{ tablePage + 1 }} / {{ tableTotalPages }}</span>
          <button :disabled="tablePage >= tableTotalPages - 1" @click="nextPage">下一页</button>
        </div>
      </div>
    </template>

    <!-- 简略视图 -->
    <template v-else>
      <div class="card compact-summary" style="margin-bottom: 24px">
        <div class="summary-row">
          <div class="summary-item">
            <span class="summary-label">当日最低</span>
            <span class="summary-value low">{{ Math.min(...heartRates.map(h => h.bpm)).toFixed(0) }}</span>
            <span class="summary-unit">bpm</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">当日最高</span>
            <span class="summary-value high">{{ Math.max(...heartRates.map(h => h.bpm)).toFixed(0) }}</span>
            <span class="summary-unit">bpm</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">当日平均</span>
            <span class="summary-value avg">{{ (heartRates.reduce((s, h) => s + h.bpm, 0) / heartRates.length).toFixed(0) }}</span>
            <span class="summary-unit">bpm</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">数据条数</span>
            <span class="summary-value count">{{ heartRates.length }}</span>
          </div>
        </div>
      </div>

      <div class="blocks-grid">
        <div v-for="block in BLOCKS" :key="block.label" class="card block-card">
          <h3 class="block-title">{{ block.label }}</h3>
          <div v-for="h in block.hours" :key="h" class="hour-row">
            <span class="hour-label">{{ h }}时</span>
            <div class="hour-bar-track">
              <template v-if="hourlyData[h].count > 0">
                <div
                  class="hour-bar"
                  :style="{
                    marginLeft: ((hourlyData[h].min! - 40) / 140 * 100).toFixed(1) + '%',
                    width: Math.max(2, ((hourlyData[h].max! - hourlyData[h].min!) / 140 * 100)).toFixed(1) + '%',
                    background: barColor(h),
                  }"
                ></div>
              </template>
              <span v-else class="hour-empty">—</span>
            </div>
            <span v-if="hourlyData[h].count > 0" class="hour-range">{{ hourlyData[h].min?.toFixed(0) }}–{{ hourlyData[h].max?.toFixed(0) }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.loading, .empty { text-align: center; padding: 60px; color: var(--color-text-secondary); }
.toolbar { margin-bottom: 16px; display: flex; align-items: center; gap: 16px; }
.date-label { font-size: 14px; color: var(--color-text-secondary); display: flex; align-items: center; gap: 8px; }
.date-input { padding: 6px 10px; border: 1px solid var(--color-border); border-radius: 6px; background: var(--color-card); color: var(--color-text); font-size: 14px; }

/* 视图切换 */
.view-toggle { display: flex; border: 1px solid var(--color-border); border-radius: 6px; overflow: hidden; }
.toggle-btn { padding: 5px 14px; font-size: 13px; border: none; background: transparent; color: var(--color-text-secondary); cursor: pointer; transition: all 0.15s; }
.toggle-btn.active { background: var(--color-primary); color: white; }

/* 详细视图 */
.data-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.data-table th { text-align: left; padding: 10px 12px; border-bottom: 2px solid var(--color-border); color: var(--color-text-secondary); font-weight: 600; font-size: 13px; }
.data-table td { padding: 10px 12px; border-bottom: 1px solid var(--color-border); }
.pagination { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 16px; font-size: 14px; color: var(--color-text-secondary); }
.pagination button { padding: 6px 14px; border: 1px solid var(--color-border); border-radius: 6px; background: var(--color-card); color: var(--color-text); cursor: pointer; font-size: 13px; }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }

/* 简略视图 - 摘要 */
.compact-summary { padding: 20px; }
.summary-row { display: flex; justify-content: space-around; }
.summary-item { text-align: center; }
.summary-label { display: block; font-size: 13px; color: var(--color-text-secondary); margin-bottom: 4px; }
.summary-value { font-size: 28px; font-weight: 700; }
.summary-unit { font-size: 13px; color: var(--color-text-secondary); }
.summary-value.low { color: #3B82F6; }
.summary-value.high { color: #EF4444; }
.summary-value.avg { color: #6366F1; }
.summary-value.count { color: var(--color-text); }

/* 简略视图 - 时间块 */
.blocks-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.block-card { padding: 16px 20px; }
.block-title { font-size: 14px; font-weight: 600; margin-bottom: 12px; color: var(--color-text-secondary); padding-bottom: 8px; border-bottom: 1px solid var(--color-border); }
.hour-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.hour-label { width: 32px; font-size: 13px; color: var(--color-text-secondary); text-align: right; flex-shrink: 0; }
.hour-bar-track { flex: 1; height: 8px; background: rgba(255,255,255,0.05); border-radius: 4px; position: relative; min-width: 0; }
.hour-bar { height: 100%; border-radius: 4px; min-width: 2px; }
.hour-empty { font-size: 12px; color: var(--color-text-secondary); }
.hour-range { width: 52px; font-size: 12px; color: var(--color-text-secondary); text-align: right; flex-shrink: 0; }
</style>
