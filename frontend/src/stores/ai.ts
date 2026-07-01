import { defineStore } from 'pinia'
import { ref } from 'vue'
import { aiApi } from '../api/ai'
import type { ChatSessionOut } from '../types/ai'

interface StreamMessage {
  id: number
  session_id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
  dify_references?: any[] | null
  streaming?: boolean  // 是否正在流式输出
}

export const useAIStore = defineStore('ai', () => {
  const sessions = ref<ChatSessionOut[]>([])
  const currentSessionId = ref<number | null>(null)
  const messages = ref<StreamMessage[]>([])
  const loading = ref(false)

  let ws: WebSocket | null = null

  async function fetchSessions() {
    const res = await aiApi.getSessions()
    sessions.value = res.data
  }

  async function loadSession(sessionId: number) {
    closeWs()
    currentSessionId.value = sessionId
    const res = await aiApi.getSessionMessages(sessionId)
    messages.value = res.data.map(m => ({ ...m, streaming: false } as StreamMessage))
  }

  function getWsUrl(): string {
    const token = localStorage.getItem('access_token') || ''
    // 动态适配：开发环境直连后端 127.0.0.1:8000，生产环境走 Nginx 同源（IP:8080）
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const isDev = import.meta.env.DEV
    const host = isDev ? '127.0.0.1:8000' : window.location.host
    return `${protocol}//${host}/api/v1/ai/chat/ws?token=${token}`
  }

  function closeWs() {
    if (ws) {
      ws.close()
      ws = null
    }
  }

  async function sendMessage(message: string, agentId?: number) {
    loading.value = true

    // 添加用户消息
    messages.value.push({
      id: Date.now(),
      session_id: currentSessionId.value || 0,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
      streaming: false,
    })

    // 创建占位 assistant 消息
    const assistantId = Date.now() + 1
    const streamingMsg: StreamMessage = {
      id: assistantId,
      session_id: currentSessionId.value || 0,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      streaming: true,
    }
    messages.value.push(streamingMsg)

    // 通过 WebSocket 发送消息
    closeWs()
    ws = new WebSocket(getWsUrl())

    ws.onopen = () => {
      ws!.send(JSON.stringify({
        message,
        session_id: currentSessionId.value || undefined,
        agent_id: agentId,
      }))
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'token') {
        // 流式追加 token
        streamingMsg.content += data.content
      } else if (data.type === 'done') {
        // 完成
        streamingMsg.streaming = false
        streamingMsg.session_id = data.session_id
        if (data.dify_references?.length) {
          streamingMsg.dify_references = data.dify_references
        }
        currentSessionId.value = data.session_id
        loading.value = false
        closeWs()
        fetchSessions()
      }
    }

    ws.onerror = () => {
      streamingMsg.streaming = false
      streamingMsg.content = streamingMsg.content || '连接失败，请重试'
      loading.value = false
      closeWs()
    }

    ws.onclose = () => {
      if (streamingMsg.streaming) {
        streamingMsg.streaming = false
        if (!streamingMsg.content) {
          streamingMsg.content = '连接已断开'
        }
        loading.value = false
      }
    }
  }

  function newChat() {
    closeWs()
    currentSessionId.value = null
    messages.value = []
  }

  async function deleteSession(sessionId: number) {
    await aiApi.deleteSession(sessionId)
    sessions.value = sessions.value.filter((s) => s.id !== sessionId)
    if (currentSessionId.value === sessionId) {
      newChat()
    }
  }

  return {
    sessions, currentSessionId, messages, loading,
    fetchSessions, loadSession, sendMessage, newChat, deleteSession,
  }
})
