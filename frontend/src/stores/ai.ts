import { defineStore } from 'pinia'
import { ref } from 'vue'
import { aiApi } from '../api/ai'
import type { ChatMessageOut, ChatSessionOut } from '../types/ai'

export const useAIStore = defineStore('ai', () => {
  const sessions = ref<ChatSessionOut[]>([])
  const currentSessionId = ref<number | null>(null)
  const messages = ref<ChatMessageOut[]>([])
  const loading = ref(false)
  const streamingContent = ref('')

  async function fetchSessions() {
    const res = await aiApi.getSessions()
    sessions.value = res.data
  }

  async function loadSession(sessionId: number) {
    currentSessionId.value = sessionId
    const res = await aiApi.getSessionMessages(sessionId)
    messages.value = res.data
  }

  async function sendMessage(message: string, agentId?: number) {
    loading.value = true
    streamingContent.value = ''

    // Add user message to UI immediately
    messages.value.push({
      id: Date.now(),
      session_id: currentSessionId.value || 0,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    })

    try {
      const res = await aiApi.chat(message, currentSessionId.value || undefined, agentId)
      currentSessionId.value = res.data.session_id

      messages.value.push({
        id: Date.now() + 1,
        session_id: res.data.session_id,
        role: 'assistant',
        content: res.data.response,
        created_at: new Date().toISOString(),
        dify_references: res.data.dify_references?.length ? res.data.dify_references : null,
      })

      await fetchSessions()
    } finally {
      loading.value = false
    }
  }

  function newChat() {
    currentSessionId.value = null
    messages.value = []
    streamingContent.value = ''
  }

  async function deleteSession(sessionId: number) {
    await aiApi.deleteSession(sessionId)
    sessions.value = sessions.value.filter((s) => s.id !== sessionId)
    if (currentSessionId.value === sessionId) {
      newChat()
    }
  }

  return {
    sessions, currentSessionId, messages, loading, streamingContent,
    fetchSessions, loadSession, sendMessage, newChat, deleteSession,
  }
})
