<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useAIStore } from '../stores/ai'
import { marked } from 'marked'

// 配置 marked
marked.setOptions({ breaks: true, gfm: true })

const aiStore = useAIStore()
const messageInput = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const markdownCache = new Map<string, string>()

function renderMarkdown(text: string): string {
  if (!text) return ''
  // 简单缓存，避免每次重渲染
  const key = text.slice(0, 200) + text.length
  if (markdownCache.has(key)) return markdownCache.get(key)!
  const html = marked.parse(text) as string
  if (markdownCache.size > 100) markdownCache.clear()
  markdownCache.set(key, html)
  return html
}

onMounted(() => {
  aiStore.fetchSessions()
  aiStore.fetchModels()
})

onUnmounted(() => {
  // store 在 newChat 时会关闭 ws，这里兜底
})

async function sendMessage() {
  const msg = messageInput.value.trim()
  if (!msg || aiStore.loading) return
  messageInput.value = ''
  await aiStore.sendMessage(msg)
  await nextTick()
  scrollToBottom()
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 新消息或流式内容变化时自动滚动
watch(() => aiStore.messages.length, () => nextTick(scrollToBottom))
watch(() => {
  const msgs = aiStore.messages
  return msgs.length ? msgs[msgs.length - 1].content.length : 0
}, () => nextTick(scrollToBottom))

function selectSession(sessionId: number) {
  aiStore.loadSession(sessionId)
}

function toggleRef(el: EventTarget | null) {
  const target = el as HTMLElement | null
  const detail = target?.nextElementSibling as HTMLElement | null
  if (detail) {
    detail.classList.toggle('ref-open')
  }
}
</script>

<template>
  <div class="chat-layout">
    <!-- Sidebar -->
    <div class="chat-sidebar">
      <button class="btn btn-primary" style="width:100%;margin-bottom:12px" @click="aiStore.newChat()">
        + 新对话
      </button>
      <div class="session-list">
        <div v-for="s in aiStore.sessions" :key="s.id"
          class="session-item" :class="{ active: aiStore.currentSessionId === s.id }"
          @click="selectSession(s.id)">
          <span class="session-title">{{ s.title }}</span>
          <span class="session-time">{{ new Date(s.last_message_at).toLocaleDateString('zh-CN') }}</span>
        </div>
        <div v-if="aiStore.sessions.length === 0" class="empty-sessions">暂无对话记录</div>
      </div>
    </div>

    <!-- Main Chat -->
    <div class="chat-main">
      <!-- 模型选择 & 状态指示灯工具栏 -->
      <div class="chat-toolbar">
        <select v-model="aiStore.currentModel" class="model-selector"
          :class="{ 'selector-warning': aiStore.aiHealth?.primary?.status === 'offline' }">
          <optgroup label="云端模型">
            <option v-for="m in aiStore.cloudModels" :key="m.name" :value="m.name">
              {{ m.name }} (云端)
            </option>
          </optgroup>
          <optgroup label="本地模型" v-if="aiStore.localModels.length > 0">
            <option v-for="m in aiStore.localModels" :key="m.name" :value="m.name">
              {{ m.name }}{{ m.parameter_size ? ` (${m.parameter_size})` : '' }} (本地)
            </option>
          </optgroup>
        </select>
        <div class="status-group">
          <span class="status-item">
            <span class="status-dot"
              :class="aiStore.aiHealth?.primary?.status || 'unknown'"></span>
            <span class="status-label">DeepSeek</span>
          </span>
          <span class="status-item">
            <span class="status-dot"
              :class="aiStore.aiHealth?.ollama?.status || 'unknown'"></span>
            <span class="status-label">Ollama</span>
          </span>
          <span v-if="aiStore.aiHealth?.fallback_enabled" class="fallback-badge" title="DeepSeek 不可用时自动切换到本地模型">
            自动降级
          </span>
        </div>
      </div>

      <div class="messages" ref="messagesContainer">
        <div v-if="aiStore.messages.length === 0" class="chat-welcome">
          <h2>SyncHealth AI</h2>
          <p>基于你的 Apple Watch 健康数据进行智能问答</p>
          <div class="suggestions">
            <button class="suggestion" @click="messageInput = '我最近一周的睡眠质量怎么样？'; sendMessage()">
              我最近一周的睡眠质量怎么样？
            </button>
            <button class="suggestion" @click="messageInput = '分析一下我的心率数据'; sendMessage()">
              分析一下我的心率数据
            </button>
            <button class="suggestion" @click="messageInput = '我的运动量是否足够？'; sendMessage()">
              我的运动量是否足够？
            </button>
          </div>
        </div>
        <div v-for="msg in aiStore.messages" :key="msg.id" :class="['message', msg.role]">
          <div class="message-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
          <div class="message-content">
            <!-- 用户消息直接显示文本 -->
            <div v-if="msg.role === 'user'" class="message-text">{{ msg.content }}</div>
            <!-- AI 消息用 Markdown 渲染 -->
            <div v-else class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
            <!-- 流式输出光标 -->
            <span v-if="msg.streaming" class="streaming-cursor">|</span>
            <!-- RAG References -->
            <div v-if="msg.role === 'assistant' && msg.dify_references?.length" class="rag-section">
              <span class="rag-badge" @click="toggleRef($event.currentTarget)">📚 知识库引用 ({{ msg.dify_references.length }})</span>
              <div class="rag-details">
                <div v-for="(ref, idx) in msg.dify_references" :key="idx" class="rag-item">
                  <div class="rag-item-header">
                    <span class="rag-doc">{{ ref.document_name }}</span>
                    <span v-if="ref.score != null" class="rag-score">{{ (ref.score * 100).toFixed(0) }}%</span>
                  </div>
                  <div v-if="ref.keywords?.length" class="rag-keywords">
                    <span v-for="kw in ref.keywords" :key="kw" class="rag-kw">{{ kw }}</span>
                  </div>
                  <div class="rag-content">{{ ref.content }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="chat-input-area">
        <form @submit.prevent="sendMessage" class="chat-form">
          <input v-model="messageInput" type="text" class="input chat-input" placeholder="输入您的健康问题..."
            :disabled="aiStore.loading" />
          <button type="submit" class="btn btn-primary" :disabled="aiStore.loading || !messageInput.trim()">
            发送
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-layout { display: flex; height: calc(100vh - 64px); margin: -32px; }

.chat-sidebar {
  width: 260px;
  background: var(--color-card);
  border-right: 1px solid var(--color-border);
  padding: 16px;
  overflow-y: auto;
}

.session-list { display: flex; flex-direction: column; gap: 4px; }
.session-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}
.session-item:hover { background: var(--color-bg); }
.session-item.active { background: #EEF2FF; }
.session-title { display: block; font-size: 13px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.session-time { font-size: 11px; color: var(--color-text-secondary); }
.empty-sessions { text-align: center; padding: 20px; font-size: 13px; color: var(--color-text-secondary); }

.chat-main { flex: 1; display: flex; flex-direction: column; }

/* 模型选择工具栏 */
.chat-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 32px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-card);
  gap: 16px;
}
.model-selector {
  width: 240px;
  padding: 6px 10px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: white;
  font-size: 13px;
  color: var(--color-text);
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
}
.model-selector:hover { border-color: var(--color-primary); }
.model-selector:focus { border-color: var(--color-primary); }
.model-selector.selector-warning { border-color: #F59E0B; }

.status-group { display: flex; align-items: center; gap: 16px; }
.status-item { display: flex; align-items: center; gap: 6px; }
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #9CA3AF;
  transition: background-color 0.3s;
}
.status-dot.online { background: #10B981; }
.status-dot.offline { background: #9CA3AF; }
.status-dot.error { background: #EF4444; }
.status-dot.unknown { background: #D1D5DB; }
.status-label { font-size: 12px; color: var(--color-text-secondary); }

.fallback-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #EEF2FF;
  color: #4F46E5;
  font-weight: 500;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

.chat-welcome {
  text-align: center;
  padding: 80px 20px;
}
.chat-welcome h2 { font-size: 24px; margin-bottom: 8px; }
.chat-welcome p { color: var(--color-text-secondary); margin-bottom: 32px; }
.suggestions { display: flex; flex-direction: column; gap: 8px; align-items: center; }
.suggestion {
  padding: 10px 20px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: white;
  font-size: 14px;
  cursor: pointer;
  transition: border-color 0.2s;
}
.suggestion:hover { border-color: var(--color-primary); color: var(--color-primary); }

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  max-width: 860px;
}
.message.user { flex-direction: row-reverse; margin-left: auto; }
.message-avatar { font-size: 24px; flex-shrink: 0; }
.message-content {
  background: var(--color-bg);
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
  min-width: 0;
}
.message.user .message-content { background: var(--color-primary); color: white; }
.message-text { white-space: pre-wrap; }

/* 流式光标 */
.streaming-cursor {
  display: inline;
  color: var(--color-primary);
  font-weight: 700;
  animation: blink 1s step-end infinite;
}
@keyframes blink {
  50% { opacity: 0; }
}

/* Markdown 渲染样式 */
.markdown-body :deep(h1), .markdown-body :deep(h2), .markdown-body :deep(h3) {
  margin: 12px 0 6px;
  font-weight: 600;
}
.markdown-body :deep(h1) { font-size: 1.3em; }
.markdown-body :deep(h2) { font-size: 1.15em; }
.markdown-body :deep(h3) { font-size: 1.05em; }

.markdown-body :deep(p) { margin: 6px 0; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { padding-left: 20px; margin: 6px 0; }
.markdown-body :deep(li) { margin: 2px 0; }

.markdown-body :deep(code) {
  background: rgba(0,0,0,0.06);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.9em;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
.markdown-body :deep(pre) {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 12px 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 10px 0;
}
.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  font-size: 0.85em;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
  font-size: 13px;
}
.markdown-body :deep(th), .markdown-body :deep(td) {
  border: 1px solid var(--color-border);
  padding: 8px 12px;
  text-align: left;
}
.markdown-body :deep(th) {
  background: rgba(0,0,0,0.03);
  font-weight: 600;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid var(--color-primary);
  padding-left: 12px;
  margin: 8px 0;
  color: var(--color-text-secondary);
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--color-border);
  margin: 12px 0;
}

.markdown-body :deep(strong) { font-weight: 700; }

/* RAG References */
.rag-section { margin-top: 10px; border-top: 1px solid #e5e7eb; padding-top: 8px; }
.rag-badge {
  display: inline-block;
  font-size: 12px;
  color: #6366f1;
  cursor: pointer;
  user-select: none;
  padding: 2px 8px;
  border-radius: 4px;
  background: #eef2ff;
  transition: background 0.15s;
}
.rag-badge:hover { background: #e0e7ff; }
.rag-details { display: none; margin-top: 8px; }
.rag-details.ref-open { display: block; }
.rag-item {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 8px 10px;
  margin-bottom: 6px;
  font-size: 12px;
}
.rag-item-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.rag-doc { font-weight: 600; color: #374151; }
.rag-score { font-size: 11px; padding: 1px 6px; border-radius: 10px; background: #dbeafe; color: #1d4ed8; font-weight: 500; }
.rag-keywords { margin-bottom: 4px; display: flex; gap: 4px; flex-wrap: wrap; }
.rag-kw { font-size: 11px; padding: 1px 6px; border-radius: 3px; background: #fef3c7; color: #92400e; }
.rag-content { color: #6b7280; line-height: 1.5; max-height: 80px; overflow: hidden; text-overflow: ellipsis; white-space: pre-wrap; }

.chat-input-area {
  padding: 16px 32px;
  border-top: 1px solid var(--color-border);
  background: var(--color-card);
}
.chat-form { display: flex; gap: 12px; }
.chat-input { flex: 1; }
</style>
