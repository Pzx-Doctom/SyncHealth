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
