export interface DifyReference {
  document_name: string
  score: number | null
  keywords: string[]
  content: string
}

export interface ChatMessageOut {
  id: number
  session_id: number
  role: string
  content: string
  created_at: string
  dify_references?: DifyReference[] | null
}

export interface ChatSessionOut {
  id: number
  agent_id?: number
  title: string
  started_at: string
  last_message_at: string
}

export interface AgentOut {
  id: number
  name: string
  description?: string
  system_prompt: string
  health_data_scope?: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AgentCreate {
  name: string
  description?: string
  system_prompt: string
  health_data_scope?: string[]
}

// Ollama 本地模型信息
export interface OllamaModel {
  name: string
  size: number
  digest?: string
  family?: string
  parameter_size?: string
  quantization?: string
  modified_at?: string
  is_cloud?: boolean
}

// 单个 provider 健康状态
export interface ProviderStatus {
  status: 'online' | 'offline' | 'error' | 'unknown'
  models_count: number
  models: string[]
  error?: string | null
}

// 双 provider 健康状态汇总
export interface AIHealth {
  primary: ProviderStatus
  ollama: ProviderStatus
  fallback_enabled: boolean
}

// 模型列表响应
export interface ModelsResponse {
  cloud_models: OllamaModel[]
  local_models: OllamaModel[]
  default_model: string
  fallback_enabled: boolean
}
