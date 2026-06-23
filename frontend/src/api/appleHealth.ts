import apiClient from './client'

export interface UploadResponse {
  task_id: string
  status: string
  message: string
}

export interface ImportStatus {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  total_records: number
  inserted: number
  deduplicated: number
  batches: number
  error: string | null
  started_at: string
  completed_at: string | null
}

export interface SyncLogResponse {
  id: number
  started_at: string
  completed_at: string | null
  status: string
  records_received: number
  records_inserted: number
  records_deduplicated: number
  error_message: string | null
}

export const appleHealthApi = {
  upload(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    // 全局 axios 默认设置了 Content-Type: application/json，
    // 上传文件时必须删除该头，浏览器才会自动设置 multipart/form-data + boundary
    return apiClient.post<UploadResponse>('/apple-health/upload', formData, {
      headers: { 'Content-Type': undefined },
    })
  },

  getStatus(taskId: string) {
    return apiClient.get<ImportStatus>(`/apple-health/status/${taskId}`)
  },

  getHistory(params: { page?: number; page_size?: number } = {}) {
    return apiClient.get<SyncLogResponse[]>('/apple-health/history', { params })
  },
}
