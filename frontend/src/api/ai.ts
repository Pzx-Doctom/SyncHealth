import apiClient from './client'
import type { ChatMessageOut, ChatSessionOut, AgentOut, AgentCreate } from '../types/ai'

export const aiApi = {
  chat(message: string, sessionId?: number, agentId?: number) {
    return apiClient.post<{ session_id: number; response: string }>('/ai/chat', {
      message,
      session_id: sessionId,
      agent_id: agentId,
    })
  },
  getSessions() {
    return apiClient.get<ChatSessionOut[]>('/ai/sessions')
  },
  getSessionMessages(sessionId: number) {
    return apiClient.get<ChatMessageOut[]>(`/ai/sessions/${sessionId}/messages`)
  },
  deleteSession(sessionId: number) {
    return apiClient.delete(`/ai/sessions/${sessionId}`)
  },
}

export const agentApi = {
  list() {
    return apiClient.get<AgentOut[]>('/agents')
  },
  create(data: AgentCreate) {
    return apiClient.post<AgentOut>('/agents', data)
  },
  update(id: number, data: Partial<AgentCreate> & { is_active?: boolean }) {
    return apiClient.put<AgentOut>(`/agents/${id}`, data)
  },
  delete(id: number) {
    return apiClient.delete(`/agents/${id}`)
  },
}
