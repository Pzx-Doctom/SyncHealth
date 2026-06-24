<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
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
  { value: 'steps', label: '步数', unit: '步' },
  { value: 'active_energy_kcal', label: '活动能量', unit: 'kcal' },
  { value: 'distance_meters', label: '距离', unit: 'm' },
  { value: 'flights_climbed', label: '爬楼', unit: '层' },
  { value: 'stand_hours', label: '站立时间', unit: '小时' },
  { value: 'exercise_time', label: '锻炼时长', unit: '分钟' },
]

// 客户端分页
const tablePage = ref(0)
const perPage = 20

const selectedDate = ref('')

const dateStart = computed(() => selectedDate.value + 'T00:00:00')
const dateEnd = computed(() => {
  const d = new Date(selectedDate.value)
  d.setDate(d.getDate() + 1)
  return d.toISOString().slice(0, 10) + 'T00:00:00'
})

// 兼容旧数据：站立时间单位为分钟，大于 24 则为旧数据，需要除以 60
function displayValue(val: number): number {
  if (metric.value === 'stand_hours' && val > 24) return val / 60
  return val
}
function formatValue(val: number): string {
  const v = displayValue(val)
  if (metric.value === 'distance_meters') return (v / 1000).toFixed(2) + ' km'
  return v.toFixed(0) + ' ' + currentMetricUnit.value
}

// 当日总量
const dailyTotal = computed(() => displayValue(activities.value.reduce((s, a) => s + a.value, 0)))

const currentMetricLabel = computed(() => metricOptions.find(m => m.value === metric.value)?.label || '')
const currentMetricUnit = computed(() => metricOptions.find(m => m.value === metric.value)?.unit || '')

// 启动时找到最近有数据的日期
onMounted(async () => {
  try {
    const res = await healthApi.getActivity({ page: 1, page_size: 1 })
    if (res.data.items.length > 0) {
      selectedDate.value = new Date(res.data.items[0].recorded_at).toISOString().slice(0, 10)
    } else {
      selectedDate.value = new Date().toISOString().slice(0, 10)
    }
  } catch {
    selectedDate.value = new Date().toISOString().slice(0, 10)
  }
})

async function fetchData() {
  loading.value = true
  try {
    const res = await healthApi.getActivity({
      metric: metric.value,
      start: dateStart.value,
      end: dateEnd.value,
      page: 1,
      page_size: 1000,
    })
    // Watch 优先过滤
    let items = res.data.items
    const watchItems = items.filter(i => i.source_device?.toLowerCase().includes('watch'))
    if (watchItems.length > 0) items = watchItems
    activities.value = items
  } finally {
    loading.value = false
  }
}

function changeDate(e: Event) {
  const input = e.target as HTMLInputElement
  selectedDate.value = input.value
}

// 图表数据（按时间排序）
const chartOption = computed(() => {
  const sorted = [...activities.value].sort((a, b) =>
    new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime()
  )
  return {
    tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].axisValue}<br/>${currentMetricLabel.value}: ${displayValue(p[0].value).toFixed(1)} ${currentMetricUnit.value}` },
    xAxis: { type: 'category', data: sorted.map(a => new Date(a.recorded_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })) },
    yAxis: { type: 'value', name: currentMetricUnit.value },
    series: [{ type: 'bar', data: sorted.map(a => displayValue(a.value)), itemStyle: { color: '#4F46E5', borderRadius: [4, 4, 0, 0] } }],
    grid: { left: 60, right: 20, top: 30, bottom: 30 },
  }
})

// 表格数据（最新在前）
const chartItems = computed(() =>
  [...activities.value].sort((a, b) => new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime())
)

const pagedItems = computed(() => {
  const start = tablePage.value * perPage
  return chartItems.value.slice(start, start + perPage)
})
const tableTotalPages = computed(() => Math.ceil(chartItems.value.length / perPage))

function prevPage() { if (tablePage.value > 0) tablePage.value-- }
function nextPage() { if (tablePage.value < tableTotalPages.value - 1) tablePage.value++ }

watch(selectedDate, () => { tablePage.value = 0; fetchData() })
watch(metric, () => { tablePage.value = 0; fetchData() })
</script>

<template>
  <div>
    <div class="page-header">
      <h1>活动数据</h1>
      <p>步数、能量消耗、距离等活动指标</p>
    </div>

    <div class="toolbar">
      <label class="date-label">
        选择日期：
        <input type="date" class="date-input" :value="selectedDate" @change="changeDate" />
      </label>
    </div>

    <div class="filter-bar">
      <button v-for="opt in metricOptions" :key="opt.value"
        :class="['tab', { active: metric === opt.value }]"
        @click="metric = opt.value">
        {{ opt.label }}
      </button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="activities.length === 0" class="empty">暂无活动数据，请先通过"数据导入"上传 Apple Health 文件</div>
    <template v-else>
      <!-- 当日汇总 -->
      <div class="card summary-card">
        <div class="summary-item">
          <span class="summary-label">当日{{ currentMetricLabel }}总量</span>
          <span class="summary-value">{{ metric === 'distance_meters' ? (dailyTotal / 1000).toFixed(2) + ' km' : dailyTotal.toFixed(1) + ' ' + currentMetricUnit }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">数据条数</span>
          <span class="summary-value">{{ chartItems.length }}</span>
        </div>
      </div>

      <div class="card" style="margin-bottom: 24px">
        <h3 style="margin-bottom: 12px; font-size: 16px">{{ currentMetricLabel }}分布</h3>
        <v-chart :option="chartOption" style="height: 350px" />
      </div>

      <div class="card">
        <h3 style="margin-bottom: 12px; font-size: 16px">数据列表（共 {{ chartItems.length }} 条）</h3>
        <table class="data-table">
          <thead>
            <tr><th>时间</th><th>{{ currentMetricLabel }} ({{ currentMetricUnit }})</th><th>来源</th></tr>
          </thead>
          <tbody>
            <tr v-for="a in pagedItems" :key="a.id">
              <td>{{ new Date(a.recorded_at).toLocaleString('zh-CN') }}</td>
              <td><strong>{{ formatValue(a.value) }}</strong></td>
              <td>{{ a.source_device || '-' }}</td>
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
  </div>
</template>

<style scoped>
.loading, .empty { text-align: center; padding: 60px; color: var(--color-text-secondary); }
.toolbar { margin-bottom: 12px; display: flex; align-items: center; gap: 16px; }
.date-label { font-size: 14px; color: var(--color-text-secondary); display: flex; align-items: center; gap: 8px; }
.date-input { padding: 6px 10px; border: 1px solid var(--color-border); border-radius: 6px; background: var(--color-card); color: var(--color-text); font-size: 14px; }

.filter-bar { display: flex; gap: 6px; margin-bottom: 20px; flex-wrap: wrap; }
.tab { padding: 6px 14px; border-radius: 6px; font-size: 13px; background: transparent; color: var(--color-text-secondary); border: 1px solid var(--color-border); cursor: pointer; transition: all 0.15s; }
.tab.active { background: var(--color-primary); color: white; border-color: var(--color-primary); }

/* 汇总卡片 */
.summary-card { padding: 20px; display: flex; justify-content: space-around; margin-bottom: 24px; }
.summary-item { text-align: center; }
.summary-label { display: block; font-size: 13px; color: var(--color-text-secondary); margin-bottom: 4px; }
.summary-value { font-size: 26px; font-weight: 700; color: var(--color-text); }

.data-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.data-table th { text-align: left; padding: 10px 12px; border-bottom: 2px solid var(--color-border); color: var(--color-text-secondary); font-weight: 600; font-size: 13px; }
.data-table td { padding: 10px 12px; border-bottom: 1px solid var(--color-border); }
.pagination { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 16px; font-size: 14px; color: var(--color-text-secondary); }
.pagination button { padding: 6px 14px; border: 1px solid var(--color-border); border-radius: 6px; background: var(--color-card); color: var(--color-text); cursor: pointer; font-size: 13px; }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
