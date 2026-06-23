<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { appleHealthApi, type ImportStatus, type SyncLogResponse } from '../api/appleHealth'

const file = ref<File | null>(null)
const isDragging = ref(false)
const uploading = ref(false)
const uploadError = ref('')
const currentTask = ref<ImportStatus | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

const history = ref<SyncLogResponse[]>([])
const historyLoading = ref(false)

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    pickFile(input.files[0])
  }
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  const dropped = e.dataTransfer?.files
  if (dropped && dropped.length > 0) {
    pickFile(dropped[0])
  }
}

function pickFile(f: File) {
  const name = f.name.toLowerCase()
  if (!name.endsWith('.xml') && !name.endsWith('.zip')) {
    uploadError.value = '仅支持 .xml 或 .zip 格式的 Apple Health 导出文件'
    file.value = null
    return
  }
  uploadError.value = ''
  file.value = f
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

async function startUpload() {
  if (!file.value) return
  uploading.value = true
  uploadError.value = ''
  currentTask.value = null
  try {
    const res = await appleHealthApi.upload(file.value)
    currentTask.value = {
      task_id: res.data.task_id,
      status: 'pending',
      total_records: 0,
      inserted: 0,
      deduplicated: 0,
      batches: 0,
      error: null,
      started_at: new Date().toISOString(),
      completed_at: null,
    }
    file.value = null
    startPolling(res.data.task_id)
  } catch (e: any) {
    uploadError.value = e.response?.data?.detail || e.message || '上传失败'
  } finally {
    uploading.value = false
  }
}

function startPolling(taskId: string) {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const res = await appleHealthApi.getStatus(taskId)
      currentTask.value = res.data
      if (res.data.status === 'completed' || res.data.status === 'failed') {
        stopPolling()
        loadHistory()
      }
    } catch {
      // 查询失败时停止轮询，避免无限报错
      stopPolling()
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const statusText: Record<string, string> = {
  pending: '等待中',
  processing: '解析中',
  completed: '已完成',
  failed: '失败',
}

const statusColor: Record<string, string> = {
  pending: '#FBBF24',
  processing: '#60A5FA',
  completed: '#34D399',
  failed: '#F87171',
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const res = await appleHealthApi.getHistory({ page: 1, page_size: 10 })
    history.value = res.data
  } catch {
    // 忽略
  } finally {
    historyLoading.value = false
  }
}

onMounted(() => {
  loadHistory()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div>
    <div class="page-header">
      <h1>数据导入</h1>
      <p>上传 Apple Health 导出的 export.xml 或 .zip 文件，后台自动解析入库</p>
    </div>

    <!-- 上传区 -->
    <div class="card upload-card">
      <div
        class="drop-zone"
        :class="{ dragging: isDragging }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop"
      >
        <input
          type="file"
          accept=".xml,.zip"
          id="file-input"
          @change="onFileChange"
          hidden
        />
        <label for="file-input" class="drop-content">
          <span class="upload-icon">📁</span>
          <span class="drop-text">点击选择文件，或拖拽到此处</span>
          <span class="drop-hint">支持 .xml / .zip（Apple Health 导出）</span>
        </label>
      </div>

      <div v-if="file" class="file-info">
        <span class="file-name">{{ file.name }}</span>
        <span class="file-size">{{ formatSize(file.size) }}</span>
      </div>

      <div v-if="uploadError" class="error-msg">{{ uploadError }}</div>

      <button
        class="btn-upload"
        :disabled="!file || uploading"
        @click="startUpload"
      >
        {{ uploading ? '上传中...' : '开始上传' }}
      </button>
    </div>

    <!-- 当前任务状态 -->
    <div v-if="currentTask" class="card task-card">
      <h3>导入任务</h3>
      <div class="task-status">
        <span class="status-badge" :style="{ background: statusColor[currentTask.status] + '22', color: statusColor[currentTask.status] }">
          {{ statusText[currentTask.status] }}
        </span>
        <span v-if="currentTask.status === 'processing'" class="spinner"></span>
      </div>

      <div class="task-stats">
        <div class="stat-item">
          <span class="stat-label">已接收记录</span>
          <span class="stat-value">{{ currentTask.total_records }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">已写入</span>
          <span class="stat-value highlight">{{ currentTask.inserted }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">去重跳过</span>
          <span class="stat-value">{{ currentTask.deduplicated }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">批次数</span>
          <span class="stat-value">{{ currentTask.batches }}</span>
        </div>
      </div>

      <div v-if="currentTask.error" class="error-msg">{{ currentTask.error }}</div>
      <div v-if="currentTask.completed_at" class="task-time">
        完成于 {{ new Date(currentTask.completed_at).toLocaleString('zh-CN') }}
      </div>
    </div>

    <!-- 导入历史 -->
    <div class="card">
      <h3 style="margin-bottom: 12px; font-size: 16px">导入历史</h3>
      <div v-if="historyLoading" class="empty">加载中...</div>
      <div v-else-if="history.length === 0" class="empty">暂无导入记录</div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>状态</th>
            <th>接收</th>
            <th>写入</th>
            <th>去重</th>
            <th>错误</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in history" :key="log.id">
            <td>{{ new Date(log.started_at).toLocaleString('zh-CN') }}</td>
            <td>
              <span class="status-badge" :style="{ background: statusColor[log.status] + '22', color: statusColor[log.status] }">
                {{ statusText[log.status] || log.status }}
              </span>
            </td>
            <td>{{ log.records_received }}</td>
            <td>{{ log.records_inserted }}</td>
            <td>{{ log.records_deduplicated }}</td>
            <td class="err-cell">{{ log.error_message || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.upload-card {
  margin-bottom: 24px;
}

.drop-zone {
  border: 2px dashed var(--color-border);
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 16px;
}

.drop-zone:hover {
  border-color: var(--color-primary);
  background: rgba(129, 140, 248, 0.04);
}

.drop-zone.dragging {
  border-color: var(--color-primary);
  background: rgba(129, 140, 248, 0.08);
}

.drop-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.upload-icon {
  font-size: 40px;
}

.drop-text {
  font-size: 15px;
  color: var(--color-text);
}

.drop-hint {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.file-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(129, 140, 248, 0.06);
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 14px;
}

.file-name {
  font-weight: 600;
  color: var(--color-text);
}

.file-size {
  color: var(--color-text-secondary);
}

.btn-upload {
  width: 100%;
  padding: 12px;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-upload:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-upload:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-msg {
  color: #F87171;
  font-size: 14px;
  margin-bottom: 12px;
  padding: 10px 14px;
  background: rgba(248, 113, 113, 0.1);
  border-radius: 8px;
}

.task-card {
  margin-bottom: 24px;
}

.task-card h3 {
  font-size: 16px;
  margin-bottom: 12px;
}

.task-status {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(96, 165, 250, 0.3);
  border-top-color: #60A5FA;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.task-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.stat-item {
  background: rgba(129, 140, 248, 0.05);
  padding: 14px;
  border-radius: 8px;
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}

.stat-value {
  display: block;
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
}

.stat-value.highlight {
  color: #34D399;
}

.task-time {
  margin-top: 12px;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.empty {
  text-align: center;
  padding: 40px;
  color: var(--color-text-secondary);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.data-table th {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 2px solid var(--color-border);
  color: var(--color-text-secondary);
  font-weight: 600;
  font-size: 13px;
}

.data-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-border);
}

.err-cell {
  color: var(--color-text-secondary);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
